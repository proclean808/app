# Venture Ferret Core Engine - PRD

## Problem Statement
Build a production-ready autonomous web research, signal-extraction, and execution-planning pipeline ("Venture Ferret Core Engine"). The system runs a multi-step cognitive workflow that scrapes web targets, extracts structured market/competitor/technical signals via LLMs, embeds them as high-dimensional vectors into a knowledge graph, and exposes hybrid semantic + keyword retrieval. The frontend is a "Cognitive Infrastructure Console" - a dense, Swiss/high-contrast dark-theme observability dashboard.

## Architecture
```
React Console (Cognitive Infrastructure Console)
        ↓
FastAPI Cognitive Gateway (/api/*)
        ↓
Research Pipeline Orchestrator (async, background tasks)
        ↓
Storage (Supabase preferred, MongoDB fallback)
        + Firecrawl (web scraping)
        + Gemini (embeddings 1536-dim, signal extraction)
```

## User Personas
- **Venture Analyst**: Triggers research on competitor websites, browses extracted signals, performs semantic search across collected memory.
- **Ops Engineer**: Monitors pipeline telemetry, debugs failed runs via the timeline, audits agent actions for governance.

## Core Requirements (static)
- Knowledge graph with `knowledge_nodes` (category, entity_name, payload, embedding, confidence, source_url, temporal fields) and `knowledge_edges` (source/target/relationship_type/weight).
- Workflow telemetry (`workflow_events`) for every pipeline step with status, duration, input/output payloads.
- Governance audit log (`agent_actions`) for every node creation with confidence breakdown and citations.
- Hybrid retrieval: semantic (Gemini embeddings), keyword (text search), hybrid (weighted combo).
- Supabase schema with pgvector, pg_trgm, pgcrypto + RLS policies + HNSW vector index + `match_knowledge_nodes()` RPC.

## What's Been Implemented (2026-01-25)
### Backend
- `services/storage.py` — Pluggable storage layer with `SupabaseBackend` and `MongoBackend`. Auto-selects based on env config; falls back to Mongo when Supabase service_role key is missing/invalid.
- `services/firecrawl_service.py` — Async Firecrawl v1 /scrape wrapper.
- `services/gemini_service.py` — Google Gemini integration: `gemini-embedding-001` @ 1536 dims for vector embeddings, `gemini-2.5-flash` for structured signal extraction with JSON mode.
- `workflows/research_pipeline.py` — 4-step orchestrator (`fetch_web_data → extract_signals → embed_and_store → link_and_plan`) with per-step telemetry logging and governance audit logging.
- `routes/venture_ferret.py` — Modular FastAPI router: `/api/research/*`, `/api/graph/*`, `/api/retrieve/*`, `/api/governance/*`, `/api/workflows/*`, `/api/stats/*`, `/api/categories`, `/api/health`.
- `migrations/001_venture_ferret_schema.sql` — Complete Supabase schema (extensions, enums, 4 tables, indices including HNSW, RLS policies, `match_knowledge_nodes` RPC).

### Frontend (Cognitive Infrastructure Console)
- Custom Swiss/high-contrast dark theme (`#050505` bg, `#0A0A0A` surface, `#FF4F00` accent, IBM Plex Sans + JetBrains Mono).
- 5 primary views:
  - **Operations**: Telemetry strip, pipeline trigger form, live active-run telemetry (polling 2s), run history, category mix breakdown.
  - **Topology Memory**: Knowledge graph node grid with category filters.
  - **Semantic Retrieval**: Hybrid/semantic/keyword search console with relevance scoring.
  - **Incident Timeline**: Workflow event stream (polling 3s).
  - **Governance**: Agent action audit log with confidence breakdowns.
- All interactive elements have `data-testid` attributes.

### Verified End-to-End
- Pipeline runs successfully (Firecrawl → Gemini extraction → embedding → MongoDB persistence → graph edges in ~16s for a 4-signal extraction).
- Semantic search returns relevance-scored results.
- Hybrid search combines vector + keyword.

## Known Issues / Backlog
- **Supabase service_role key invalid**: User provided keys did not authenticate against the project URL. System auto-falls back to MongoDB (fully functional). Once a valid key is supplied, the system will seamlessly switch.
  - Action: User to provide valid Supabase service_role key from Dashboard → Settings → API → service_role.
- **Schema migration**: `migrations/001_venture_ferret_schema.sql` needs to be run in the Supabase SQL editor before switching backends.

## P0 / P1 / P2 Backlog
- **P0** — Valid Supabase service_role key + run SQL migration; then storage seamlessly upgrades.
- **P1** — Hatchet worker process for durable execution (currently using FastAPI BackgroundTasks which are sufficient for preview but not durable across restarts). The pipeline orchestrator is already architected to drop into a Hatchet step graph.
- **P1** — Google Workspace sync (NotebookLM bridge). User did not supply OAuth refresh token + Doc ID; scaffolded as a future plug-in.
- **P2** — Multimodal Gemini File Search for topology diagrams and Grafana screenshots.
- **P2** — Realtime event bus (Supabase Realtime or NATS) replacing polling.
- **P2** — Drift Analysis view.

## Next Tasks
1. Verify all flows with the testing agent and address any failures.
2. Document Supabase migration runbook for the user.
3. (When the user provides valid Supabase service_role key) — execute SQL migration via the dashboard.
