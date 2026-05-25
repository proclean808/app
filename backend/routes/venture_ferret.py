"""
Venture Ferret - FastAPI routes
Modular Cognitive Gateway exposing:
  /api/research/*    – workflow trigger + status
  /api/graph/*       – knowledge node/edge access
  /api/retrieve/*    – semantic + hybrid retrieval
  /api/governance/*  – agent action audit trail
  /api/workflows/*   – execution telemetry
"""
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from services.gemini_service import gemini
from services.storage import storage
from workflows.research_pipeline import run_research_pipeline


router = APIRouter(prefix="/api")


# ============================================================================
# Schemas
# ============================================================================
class ResearchTriggerRequest(BaseModel):
    target_domain: str = Field(..., description="URL to scrape (e.g. https://example.com)")
    query: str = Field(..., description="Analyst question or research focus")


class ResearchTriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    category: Optional[str] = None


class NodeCreateRequest(BaseModel):
    category: str
    entity_name: str
    payload: dict = {}
    confidence: float = 0.6
    source_url: Optional[str] = None


# ============================================================================
# Health + meta
# ============================================================================
@router.get("/")
async def root():
    return {
        "service": "Venture Ferret Core Engine",
        "status": "operational",
        "version": "1.0.0",
    }


@router.get("/health")
async def health():
    stats = await storage().stats()
    return {"status": "ok", "storage": stats}


@router.get("/categories")
async def categories():
    return {
        "categories": [
            {"id": "market_signal", "label": "Market Signal",
             "description": "Industry trends, demand indicators"},
            {"id": "technical_dependency", "label": "Technical Dependency",
             "description": "Tech stack, frameworks, libraries"},
            {"id": "competitor_analysis", "label": "Competitor Analysis",
             "description": "Competing products, pricing"},
            {"id": "infrastructure", "label": "Infrastructure",
             "description": "Deployment, hosting, architecture"},
        ]
    }


# ============================================================================
# Research workflow
# ============================================================================
@router.post("/research/trigger", response_model=ResearchTriggerResponse)
async def trigger_research(req: ResearchTriggerRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    # Persist the initial event so the UI can show pending immediately
    await storage().log_workflow_event({
        "run_id": run_id,
        "workflow_name": "research_pipeline",
        "step_name": "queued",
        "status": "pending",
        "input_payload": {"target_domain": req.target_domain, "query": req.query},
    })
    # Schedule asynchronous execution
    background_tasks.add_task(
        run_research_pipeline, req.target_domain, req.query, run_id
    )
    return ResearchTriggerResponse(
        run_id=run_id,
        status="queued",
        message=f"Research pipeline initiated for {req.target_domain}",
    )


@router.get("/research/runs/{run_id}")
async def get_run_status(run_id: str):
    events = await storage().list_workflow_events(run_id=run_id, limit=50)
    if not events:
        raise HTTPException(404, "Run not found")

    # Determine overall status from latest pipeline_complete event
    latest_complete = next((e for e in events if e.get("step_name") == "pipeline_complete"), None)
    overall = "running"
    if latest_complete:
        overall = "completed" if latest_complete.get("status") == "completed" else "failed"

    return {
        "run_id": run_id,
        "status": overall,
        "events": events,
        "step_count": len(events),
    }


@router.get("/research/runs")
async def list_runs(limit: int = Query(20, ge=1, le=100)):
    events = await storage().list_workflow_events(limit=500)
    # Group by run_id
    runs: dict = {}
    for e in events:
        rid = e.get("run_id")
        if not rid:
            continue
        if rid not in runs:
            runs[rid] = {
                "run_id": rid,
                "workflow_name": e.get("workflow_name"),
                "events": [],
                "last_status": "running",
                "started_at": e.get("created_at"),
            }
        runs[rid]["events"].append(e)
        if e.get("step_name") == "pipeline_complete":
            runs[rid]["last_status"] = e.get("status")
        # Update started_at to earliest
        if (e.get("created_at") or "") < (runs[rid]["started_at"] or "zzz"):
            runs[rid]["started_at"] = e.get("created_at")

    summary = []
    for rid, r in runs.items():
        first = r["events"][-1] if r["events"] else {}
        inp = first.get("input_payload") or {}
        summary.append({
            "run_id": rid,
            "status": r["last_status"],
            "target_domain": inp.get("target_domain") or inp.get("target"),
            "query": inp.get("query"),
            "step_count": len(r["events"]),
            "started_at": r["started_at"],
        })
    summary.sort(key=lambda x: x.get("started_at") or "", reverse=True)
    return {"runs": summary[:limit]}


# ============================================================================
# Knowledge graph
# ============================================================================
@router.get("/graph/nodes")
async def list_nodes(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    nodes = await storage().list_nodes(category=category, limit=limit)
    return {"nodes": nodes, "count": len(nodes)}


@router.get("/graph/nodes/{node_id}")
async def get_node(node_id: str):
    node = await storage().get_node(node_id)
    if not node:
        raise HTTPException(404, "Node not found")
    # Drop embedding from response for size
    node.pop("embedding", None)
    return node


@router.post("/graph/nodes")
async def create_node(req: NodeCreateRequest):
    # Generate embedding on the fly
    text = f"{req.entity_name}. {req.payload.get('summary', '')}"
    embedding = await gemini().embed(text)
    node = await storage().insert_node({
        "category": req.category,
        "entity_name": req.entity_name,
        "payload": req.payload,
        "embedding": embedding,
        "confidence": req.confidence,
        "source_url": req.source_url,
    })
    node.pop("embedding", None)
    return node


# ============================================================================
# Retrieval (hybrid)
# ============================================================================
@router.post("/retrieve/semantic")
async def semantic_search(req: SearchRequest):
    """Vector similarity search using Gemini embeddings."""
    embedding = await gemini().embed(req.query)
    results = await storage().search_vector(embedding, limit=req.limit)
    # Filter category if requested (Mongo backend lacks server filter)
    if req.category:
        results = [r for r in results if r.get("category") == req.category]
    return {"results": results, "count": len(results), "mode": "semantic"}


@router.post("/retrieve/keyword")
async def keyword_search(req: SearchRequest):
    """Substring/keyword search across entity_name + payload."""
    results = await storage().search_text(req.query, limit=req.limit)
    if req.category:
        results = [r for r in results if r.get("category") == req.category]
    return {"results": results, "count": len(results), "mode": "keyword"}


@router.post("/retrieve/hybrid")
async def hybrid_search(req: SearchRequest):
    """Combine semantic + keyword for stronger recall."""
    embedding = await gemini().embed(req.query)
    sem = await storage().search_vector(embedding, limit=req.limit)
    kw = await storage().search_text(req.query, limit=req.limit)

    merged: dict = {}
    for r in sem:
        rid = r.get("id")
        if not rid:
            continue
        merged[rid] = {**r, "score_semantic": r.get("similarity", 0.0), "score_keyword": 0.0}
    for r in kw:
        rid = r.get("id")
        if not rid:
            continue
        if rid in merged:
            merged[rid]["score_keyword"] = 1.0
        else:
            merged[rid] = {**r, "score_semantic": 0.0, "score_keyword": 1.0}

    # Combined score (weighted)
    for v in merged.values():
        v["score_combined"] = round(0.7 * v["score_semantic"] + 0.3 * v["score_keyword"], 4)

    results = sorted(merged.values(), key=lambda x: x["score_combined"], reverse=True)
    if req.category:
        results = [r for r in results if r.get("category") == req.category]
    return {"results": results[:req.limit], "count": len(results), "mode": "hybrid"}


# ============================================================================
# Governance / Workflows
# ============================================================================
@router.get("/governance/actions")
async def list_actions(limit: int = Query(50, ge=1, le=200)):
    actions = await storage().list_agent_actions(limit=limit)
    return {"actions": actions, "count": len(actions)}


@router.get("/workflows/events")
async def list_events(
    run_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    events = await storage().list_workflow_events(run_id=run_id, limit=limit)
    return {"events": events, "count": len(events)}


@router.get("/stats/overview")
async def stats_overview():
    s = await storage().stats()
    nodes = await storage().list_nodes(limit=500)
    by_cat: dict = {}
    for n in nodes:
        c = n.get("category", "unknown")
        by_cat[c] = by_cat.get(c, 0) + 1
    return {
        "totals": s,
        "by_category": by_cat,
        "recent_nodes": nodes[:5],
    }
