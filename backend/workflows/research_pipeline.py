"""
Venture Ferret - Research Pipeline Orchestrator
Runs the 4-step cognitive flow:
  1. fetch_web_data    (Firecrawl scrape)
  2. extract_signals   (Gemini structured extraction)
  3. embed_and_store   (Gemini embeddings → knowledge_nodes)
  4. link_and_plan     (graph edges + execution blueprint)

Each step logs a workflow_event for full temporal observability.
Designed to run inline (FastAPI BackgroundTasks) or via Hatchet worker.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from services.firecrawl_service import firecrawl
from services.gemini_service import gemini
from services.storage import storage


_VALID_CATEGORIES = {
    "market_signal",
    "technical_dependency",
    "competitor_analysis",
    "infrastructure",
}


class ResearchPipeline:
    """Inline orchestrator. Mirrors the Hatchet step graph."""

    def __init__(self, target_domain: str, query: str, run_id: Optional[str] = None):
        self.target_domain = target_domain
        self.query = query
        self.run_id = run_id or str(uuid.uuid4())
        self.workflow_name = "research_pipeline"
        self.store = storage()

    async def _log(self, step: str, status: str, t0: float,
                   inputs: Optional[dict] = None,
                   outputs: Optional[dict] = None,
                   error: Optional[str] = None):
        await self.store.log_workflow_event({
            "run_id": self.run_id,
            "workflow_name": self.workflow_name,
            "step_name": step,
            "status": status,
            "input_payload": inputs or {},
            "output_payload": outputs or {},
            "error_message": error,
            "duration_ms": int((time.time() - t0) * 1000),
        })

    # --- STEP 1 -------------------------------------------------------------
    async def fetch_web_data(self) -> dict:
        t0 = time.time()
        await self._log("fetch_web_data", "running", t0,
                        inputs={"target": self.target_domain, "query": self.query})
        try:
            result = await firecrawl().scrape(self.target_domain, wait_ms=1500)
            await self._log("fetch_web_data", "completed", t0,
                            outputs={"chars": len(result["markdown"]), "title": result["title"]})
            return result
        except Exception as e:
            await self._log("fetch_web_data", "failed", t0, error=str(e)[:500])
            raise

    # --- STEP 2 -------------------------------------------------------------
    async def extract_signals(self, scrape_result: dict) -> list[dict]:
        t0 = time.time()
        markdown = scrape_result["markdown"]
        await self._log("extract_signals", "running", t0,
                        inputs={"content_chars": len(markdown)})
        try:
            signals = await gemini().extract_signals(markdown, self.query)
            # Sanitize categories
            cleaned = []
            for s in signals:
                cat = (s.get("category") or "").strip()
                if cat not in _VALID_CATEGORIES:
                    cat = "market_signal"
                cleaned.append({
                    "category": cat,
                    "entity_name": (s.get("entity_name") or "Unnamed signal")[:200],
                    "summary": (s.get("summary") or "")[:500],
                    "evidence": (s.get("evidence") or "")[:1000],
                    "confidence": float(s.get("confidence") or 0.6),
                })
            await self._log("extract_signals", "completed", t0,
                            outputs={"signal_count": len(cleaned)})
            return cleaned
        except Exception as e:
            await self._log("extract_signals", "failed", t0, error=str(e)[:500])
            raise

    # --- STEP 3 -------------------------------------------------------------
    async def embed_and_store(self, signals: list[dict], scrape_result: dict) -> list[dict]:
        t0 = time.time()
        await self._log("embed_and_store", "running", t0,
                        inputs={"signal_count": len(signals)})
        try:
            stored: list[dict] = []
            for sig in signals:
                # Compose text for embedding
                embed_text = f"{sig['entity_name']}. {sig['summary']} {sig['evidence']}"
                vec = await gemini().embed(embed_text)

                node = await self.store.insert_node({
                    "category": sig["category"],
                    "entity_name": sig["entity_name"],
                    "payload": {
                        "summary": sig["summary"],
                        "evidence": sig["evidence"],
                        "query": self.query,
                        "source_title": scrape_result.get("title", ""),
                    },
                    "embedding": vec,
                    "confidence": sig["confidence"],
                    "source_url": scrape_result.get("source_url", self.target_domain),
                })
                stored.append(node)

                # Governance audit log
                await self.store.log_agent_action({
                    "action_type": "node_created",
                    "actor": "research_pipeline",
                    "target_node_id": node.get("id"),
                    "confidence": {
                        "extraction": sig["confidence"],
                        "retrieval": 1.0,
                        "policy_alignment": 1.0,
                    },
                    "citations": [{
                        "source_url": scrape_result.get("source_url"),
                        "title": scrape_result.get("title"),
                    }],
                    "metadata": {"run_id": self.run_id, "query": self.query},
                })

            await self._log("embed_and_store", "completed", t0,
                            outputs={"nodes_created": len(stored)})
            return stored
        except Exception as e:
            await self._log("embed_and_store", "failed", t0, error=str(e)[:500])
            raise

    # --- STEP 4 -------------------------------------------------------------
    async def link_and_plan(self, stored: list[dict]) -> dict:
        t0 = time.time()
        await self._log("link_and_plan", "running", t0,
                        inputs={"node_count": len(stored)})
        try:
            # Create co-occurrence edges between sibling signals from the same run
            edges_created = 0
            for i, a in enumerate(stored):
                for b in stored[i + 1:]:
                    if not a.get("id") or not b.get("id"):
                        continue
                    try:
                        await self.store.insert_edge({
                            "source_node_id": a["id"],
                            "target_node_id": b["id"],
                            "relationship_type": "co_observed",
                            "weight": 0.75,
                        })
                        edges_created += 1
                    except Exception:
                        # Duplicate edge or backend constraint - non-fatal
                        pass

            blueprint = {
                "deployment_target": "vercel_edge",
                "infrastructure_state": "active",
                "memsmart_refs": [n.get("id") for n in stored if n.get("id")],
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
                "categories_observed": sorted({n.get("category") for n in stored if n.get("category")}),
            }
            await self._log("link_and_plan", "completed", t0,
                            outputs={"edges": edges_created, "blueprint": blueprint})
            return blueprint
        except Exception as e:
            await self._log("link_and_plan", "failed", t0, error=str(e)[:500])
            raise

    # --- Orchestrator -------------------------------------------------------
    async def run(self) -> dict:
        await self._log("pipeline_start", "running", time.time(),
                        inputs={"target": self.target_domain, "query": self.query})
        try:
            scrape = await self.fetch_web_data()
            signals = await self.extract_signals(scrape)
            stored = await self.embed_and_store(signals, scrape)
            blueprint = await self.link_and_plan(stored)
            await self._log("pipeline_complete", "completed", time.time(),
                            outputs={"node_count": len(stored)})
            return {
                "status": "SUCCESS",
                "run_id": self.run_id,
                "nodes_created": len(stored),
                "node_ids": [n.get("id") for n in stored],
                "blueprint": blueprint,
            }
        except Exception as e:
            await self._log("pipeline_complete", "failed", time.time(), error=str(e)[:500])
            return {
                "status": "FAILED",
                "run_id": self.run_id,
                "error": str(e),
            }


async def run_research_pipeline(target_domain: str, query: str, run_id: Optional[str] = None) -> dict:
    pipeline = ResearchPipeline(target_domain, query, run_id)
    return await pipeline.run()
