"""Apply the Supabase migration via the connection pooler."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

import psycopg2

url = os.environ['SUPABASE_URL']
password = os.environ['SUPABASE_DB_PASSWORD']
ref = url.split('//')[1].split('.')[0]

with open(Path(__file__).parent / 'migrations' / '001_venture_ferret_schema.sql') as f:
    sql = f.read()

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

for prefix, r in regions:
    try:
        conn = psycopg2.connect(
            host=f'{prefix}-{r}.pooler.supabase.com',
            port=6543,
            user=f'postgres.{ref}',
            password=password,
            database='postgres',
            connect_timeout=5,
            sslmode='require',
        )
        print(f'Connected pooler region={prefix}-{r}')
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql)
        cur.execute("""
            SELECT count(*) FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name IN ('knowledge_nodes','knowledge_edges','workflow_events','agent_actions')
        """)
        print(f"Tables created: {cur.fetchone()[0]}/4")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f'{prefix}-{r}: {str(e)[:90]}')

print('FAILED to apply migration')
sys.exit(2)
