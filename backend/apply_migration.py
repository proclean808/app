"""Apply the Supabase migration via the multi-tenant migration engine."""
import os
import sys
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

from services.migration_engine import MigrationPackage, MigrationExecutor, MigrationRouter

# Load the SQL payload
sql_file = Path(__file__).parent / 'migrations' / '001_venture_ferret_schema.sql'
with open(sql_file) as f:
    sql_payload = f.read()

# Calculate cryptographic checksum for integrity validation
checksum = hashlib.sha256(sql_payload.encode('utf-8')).hexdigest()

# Environment configuration
url = os.environ['SUPABASE_URL']
password = os.environ['SUPABASE_DB_PASSWORD']
ref = url.split('//')[1].split('.')[0]

# Construct the migration package with full provenance
package = MigrationPackage(
    tenant_id="default-tenant",
    app_id="venture-ferret-core",
    migration_id="001_venture_ferret_schema",
    sql_payload=sql_payload,
    rollback_sql=None,
    checksum=checksum,
    target_schema="public"
)

# Define connection pooler regions for resilience
regions = [
    ('aws-1', 'us-west-1'),
    ('aws-1', 'us-east-1'),
    ('aws-1', 'us-east-2'),
    ('aws-1', 'us-west-2'),
    ('aws-1', 'eu-west-1'),
    ('aws-1', 'eu-central-1'),
    ('aws-1', 'ap-south-1'),
    ('aws-1', 'ap-southeast-1'),
    ('aws-0', 'us-east-1'),
    ('aws-0', 'us-west-1'),
]

# Attempt execution across regions with deterministic routing
success = False
for prefix, r in regions:
    try:
        dsn = f"postgresql://postgres.{ref}@{prefix}-{r}.pooler.supabase.com:6543/postgres?sslmode=require"
        executor = MigrationExecutor(dsn=dsn, password=password, worker_node_id=f"worker-{prefix}-{r}")
        
        print(f"Attempting region {prefix}-{r}...")
        if executor.execute(package):
            print(f"✓ Migration applied successfully in region {prefix}-{r}")
            success = True
            break
        else:
            print(f"✗ Migration failed in region {prefix}-{r}")
    except Exception as e:
        print(f'{prefix}-{r}: {str(e)[:90]}')

if not success:
    print('FAILED to apply migration across all regions')
    sys.exit(2)

sys.exit(0)
