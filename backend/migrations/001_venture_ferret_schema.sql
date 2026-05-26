-- Venture Ferret Core Engine: Supabase Schema Migration
-- Execute this script in the Supabase SQL Editor (Dashboard → SQL Editor → New Query)

-- ============================================================================
-- EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- MIGRATION AUDIT LEDGER (Multi-Tenant Provisioning Engine)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    migration_id VARCHAR(255) PRIMARY KEY,
    app_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT NOT NULL,
    worker_node VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schema_migrations_tenant ON public.schema_migrations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_schema_migrations_app ON public.schema_migrations(app_id);
CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied ON public.schema_migrations(applied_at DESC);

-- ============================================================================
-- ENUMS / TYPES
-- ============================================================================
DO $$ BEGIN
    CREATE TYPE research_category AS ENUM (
        'market_signal',
        'technical_dependency',
        'competitor_analysis',
        'infrastructure'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE workflow_status AS ENUM (
        'pending',
        'running',
        'completed',
        'failed',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- COGNITIVE MEMORY: knowledge_nodes
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category research_category NOT NULL,
    entity_name TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1536),
    confidence NUMERIC(4,3) DEFAULT 0.500,
    source_url TEXT,
    -- Temporal memory
    valid_from TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    valid_to TIMESTAMPTZ,
    snapshot_timestamp TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================================
-- COGNITIVE MEMORY: knowledge_edges
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.knowledge_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    weight NUMERIC(3,2) DEFAULT 1.00,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_edge_pair UNIQUE(source_node_id, target_node_id, relationship_type)
);

-- ============================================================================
-- OPERATIONAL TELEMETRY: workflow_events
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.workflow_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT NOT NULL,
    workflow_name TEXT NOT NULL,
    step_name TEXT,
    status workflow_status NOT NULL DEFAULT 'pending',
    input_payload JSONB DEFAULT '{}'::jsonb,
    output_payload JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================================
-- GOVERNANCE: agent_actions (audit trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    target_node_id UUID REFERENCES public.knowledge_nodes(id) ON DELETE SET NULL,
    confidence JSONB DEFAULT '{}'::jsonb,
    citations JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================================
-- CONVERSATION MEMORY: conversation_entries (session-level context)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.conversation_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversation_session ON public.conversation_entries(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_created ON public.conversation_entries(created_at DESC);

-- ============================================================================
-- ORCHESTRATION SPINE: orchestration_nodes (deterministic routing topology)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.orchestration_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type TEXT NOT NULL,
    name TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orchestration_nodes_type ON public.orchestration_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_orchestration_nodes_created ON public.orchestration_nodes(created_at DESC);

-- ============================================================================
-- ORCHESTRATION SPINE: orchestration_edges (deterministic execution paths)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.orchestration_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID REFERENCES public.orchestration_nodes(id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES public.orchestration_nodes(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    condition JSONB DEFAULT '{}'::jsonb,
    weight NUMERIC(3,2) DEFAULT 1.00,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orchestration_edges_source ON public.orchestration_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_edges_target ON public.orchestration_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_edges_rel ON public.orchestration_edges(relationship_type);

-- ============================================================================
-- INDICES (Performance Optimization)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_nodes_category ON public.knowledge_nodes(category);
CREATE INDEX IF NOT EXISTS idx_nodes_payload_gin ON public.knowledge_nodes USING gin (payload);
CREATE INDEX IF NOT EXISTS idx_nodes_entity_trgm ON public.knowledge_nodes USING gin (entity_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_nodes_created ON public.knowledge_nodes(created_at DESC);
-- Vector index (HNSW for fast cosine similarity)
CREATE INDEX IF NOT EXISTS idx_nodes_embedding ON public.knowledge_nodes
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_edges_source ON public.knowledge_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON public.knowledge_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_edges_rel ON public.knowledge_edges(relationship_type);

CREATE INDEX IF NOT EXISTS idx_events_run ON public.workflow_events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_status ON public.workflow_events(status);
CREATE INDEX IF NOT EXISTS idx_events_created ON public.workflow_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_actions_actor ON public.agent_actions(actor);
CREATE INDEX IF NOT EXISTS idx_actions_created ON public.agent_actions(created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) — apply early per architecture recommendations
-- ============================================================================
ALTER TABLE public.knowledge_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_actions ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access (default behavior, explicit policy for clarity)
DROP POLICY IF EXISTS service_role_all ON public.knowledge_nodes;
CREATE POLICY service_role_all ON public.knowledge_nodes
    USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS service_role_all ON public.knowledge_edges;
CREATE POLICY service_role_all ON public.knowledge_edges
    USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS service_role_all ON public.workflow_events;
CREATE POLICY service_role_all ON public.workflow_events
    USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS service_role_all ON public.agent_actions;
CREATE POLICY service_role_all ON public.agent_actions
    USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- HYBRID RETRIEVAL: Vector search function
-- ============================================================================
CREATE OR REPLACE FUNCTION public.match_knowledge_nodes (
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    category research_category,
    entity_name TEXT,
    payload JSONB,
    similarity FLOAT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.id,
        n.category,
        n.entity_name,
        n.payload,
        1 - (n.embedding <=> query_embedding) AS similarity,
        n.created_at
    FROM public.knowledge_nodes n
    WHERE
        (filter_category IS NULL OR n.category::TEXT = filter_category)
        AND n.embedding IS NOT NULL
        AND 1 - (n.embedding <=> query_embedding) > match_threshold
    ORDER BY n.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;
