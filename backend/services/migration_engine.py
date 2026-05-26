"""
Multi-Tenant Migration Engine
Architected for deterministic, idempotent schema execution across distributed agent nodes.
Integrates transaction safety, structured logging, registry auditing, and graph telemetry.
"""

import os
import sys
import hashlib
import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import psycopg2
from psycopg2 import extensions

# Configure Structured Logging for MCP / Telemetry Ingestion
logger = logging.getLogger("migration_engine")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


@dataclass(frozen=True)
class MigrationPackage:
    tenant_id: str
    app_id: str
    migration_id: str
    sql_payload: str
    rollback_sql: Optional[str]
    checksum: str
    target_schema: str = "public"

    def validate_integrity(self) -> bool:
        """Validates that the payload matches the cryptographic checksum."""
        calculated_hash = hashlib.sha256(self.sql_payload.encode('utf-8')).hexdigest()
        return calculated_hash == self.checksum


class MigrationExecutor:
    def __init__(self, dsn: str, password: str, worker_node_id: str = "worker-local"):
        self.dsn = dsn
        self.password = password
        self.worker_node_id = worker_node_id

    def _ensure_registry_table(self, cursor) -> None:
        """Guarantees the existence of the schema_migrations ledger inside the target database."""
        create_table_ddl = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id VARCHAR(255) PRIMARY KEY,
            app_id VARCHAR(255) NOT NULL,
            tenant_id VARCHAR(255) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INT NOT NULL,
            worker_node VARCHAR(255) NOT NULL,
            success BOOLEAN NOT NULL
        );
        """
        cursor.execute(create_table_ddl)

    def _is_already_applied(self, cursor, migration_id: str) -> bool:
        """Checks the registry table for idempotency enforcement."""
        cursor.execute("SELECT success FROM schema_migrations WHERE migration_id = %s;", (migration_id,))
        result = cursor.fetchone()
        return result is not None and result[0] is True

    def _log_to_memgraph_stub(self, event_type: str, package: MigrationPackage, metrics: Dict[str, Any]) -> None:
        """
        Emits standard JSON telemetry payload to stdout/event bus.
        Designed for direct edge ingestion by Memgraph trace writers to map:
        Tenant (node) -> App (node) -> Migration (node) -> Worker (edge)
        """
        telemetry = {
            "event": event_type,
            "entity_graph": {
                "tenant_id": package.tenant_id,
                "app_id": package.app_id,
                "migration_id": package.migration_id,
                "worker_node": self.worker_node_id
            },
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info(f"GRAPH_TELEMETRY: {json.dumps(telemetry)}")

    def execute(self, package: MigrationPackage) -> bool:
        """Executes a signed migration payload within an isolated transaction boundary."""
        # 1. Verification Gate
        if not package.validate_integrity():
            logger.error(json.dumps({
                "tenant": package.tenant_id,
                "migration": package.migration_id,
                "status": "FAILED_CHECKSUM_VALIDATION"
            }))
            return False

        start_time = datetime.utcnow()
        connection = None

        try:
            # 2. Isolated Connection Management (Targeting Low-Concurrency Migration Pool)
            connection = psycopg2.connect(dsn=self.dsn, password=self.password, connect_timeout=15)

            # Explicitly NOT autocommit. Transactions are strictly enforced.
            connection.autocommit = False

            with connection.cursor() as cursor:
                # Set schema context boundary
                cursor.execute(f"SET search_path TO {package.target_schema};")

                # Ensure tracking infrastructure exists
                self._ensure_registry_table(cursor)

                # 3. Idempotency Check
                if self._is_already_applied(cursor, package.migration_id):
                    logger.info(json.dumps({
                        "tenant": package.tenant_id,
                        "migration": package.migration_id,
                        "status": "SKIPPED_ALREADY_APPLIED"
                    }))
                    connection.rollback()
                    return True

                # 4. Payload Execution
                logger.info(json.dumps({
                    "tenant": package.tenant_id,
                    "migration": package.migration_id,
                    "status": "EXECUTING_DDL"
                }))

                cursor.execute(package.sql_payload)

                # Calculate metrics
                execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                # Log to local database ledger
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (migration_id, app_id, tenant_id, checksum, execution_time_ms, worker_node, success)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE);
                    """,
                    (package.migration_id, package.app_id, package.tenant_id, package.checksum, execution_time_ms, self.worker_node_id)
                )

            # Commit the transaction atomicity boundary
            connection.commit()

            # 5. External Graph Telemetry Write
            self._log_to_memgraph_stub("MIGRATION_SUCCESS", package, {"duration_ms": execution_time_ms})
            return True

        except Exception as error:
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(json.dumps({
                "tenant": package.tenant_id,
                "migration": package.migration_id,
                "status": "CRITICAL_EXECUTION_FAILURE",
                "error": str(error)
            }))

            if connection:
                try:
                    logger.warning(f"Rolling back transaction for tenant: {package.tenant_id}")
                    connection.rollback()

                    # Attempt to log failure metadata into registry if connection is still viable
                    with connection.cursor() as fail_cursor:
                        fail_cursor.execute(
                            """
                            INSERT INTO schema_migrations (migration_id, app_id, tenant_id, checksum, execution_time_ms, worker_node, success)
                            VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                            ON CONFLICT (migration_id) DO UPDATE SET success = FALSE;
                            """,
                            (package.migration_id, package.app_id, package.tenant_id, package.checksum, execution_time_ms, self.worker_node_id)
                        )
                    connection.commit()
                except Exception as rollback_err:
                    logger.critical(f"Rollback logging failed: {str(rollback_err)}")

            self._log_to_memgraph_stub("MIGRATION_FAILURE", package, {"duration_ms": execution_time_ms, "error": str(error)})
            return False

        finally:
            if connection:
                connection.close()


class MigrationRouter:
    """Orchestration layer mapping tenant tokens to high-timeout, dedicated connection paths."""
    @staticmethod
    def resolve_dsn(tenant_id: str) -> str:
        # Resolves via internal secure router mapping, appending Transaction Pooler port parameters
        # Example dynamic mapping template fallback
        base_url = os.environ.get("SUPABASE_URL")
        if not base_url:
            raise ValueError("SUPABASE_URL configuration missing from host environment.")
        return base_url
