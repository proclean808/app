"""
Venture Ferret Core Engine - Storage Layer
Hybrid storage that supports both Supabase (production) and MongoDB (fallback).
Auto-selects backend based on env config.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StorageBackend:
    """Abstract storage interface for the MemSmart knowledge graph."""

    async def insert_node(self, node: dict) -> dict:
        raise NotImplementedError

    async def insert_edge(self, edge: dict) -> dict:
        raise NotImplementedError

    async def list_nodes(self, category: Optional[str] = None, limit: int = 100) -> list[dict]:
        raise NotImplementedError

    async def get_node(self, node_id: str) -> Optional[dict]:
        raise NotImplementedError

    async def search_text(self, query: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError

    async def search_vector(self, embedding: list[float], limit: int = 10) -> list[dict]:
        raise NotImplementedError

    async def insert_conversation_entry(self, session_id: str, role: str, content: str, metadata: Optional[dict] = None) -> dict:
        raise NotImplementedError

    async def list_conversation_entries(self, session_id: str, limit: int = 50) -> list[dict]:
        raise NotImplementedError

    async def search_conversation_entries(self, session_id: str, query: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError

    async def insert_orchestration_node(self, node: dict) -> dict:
        raise NotImplementedError

    async def insert_orchestration_edge(self, edge: dict) -> dict:
        raise NotImplementedError

    async def list_orchestration_nodes(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError

    async def list_orchestration_edges(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError

    async def get_orchestration_node(self, node_id: str) -> Optional[dict]:
        raise NotImplementedError

    async def get_outgoing_orchestration_edges(self, node_id: str, limit: int = 50) -> list[dict]:
        raise NotImplementedError

    async def log_workflow_event(self, event: dict) -> dict:
        raise NotImplementedError

    async def list_workflow_events(self, run_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        raise NotImplementedError

    async def log_agent_action(self, action: dict) -> dict:
        raise NotImplementedError

    async def list_agent_actions(self, limit: int = 50) -> list[dict]:
        raise NotImplementedError

    async def stats(self) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# MongoDB Backend (fallback / current preview)
# ---------------------------------------------------------------------------
class MongoBackend(StorageBackend):
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.nodes = self.db.knowledge_nodes
        self.edges = self.db.knowledge_edges
        self.events = self.db.workflow_events
        self.actions = self.db.agent_actions
        self.conversation_entries = self.db.conversation_entries
        self.orchestration_nodes = self.db.orchestration_nodes
        self.orchestration_edges = self.db.orchestration_edges

    async def insert_node(self, node: dict) -> dict:
        doc = {
            "id": node.get("id") or str(uuid.uuid4()),
            "category": node["category"],
            "entity_name": node["entity_name"],
            "payload": node.get("payload", {}),
            "embedding": node.get("embedding"),
            "confidence": node.get("confidence", 0.5),
            "source_url": node.get("source_url"),
            "valid_from": node.get("valid_from") or _now_iso(),
            "valid_to": node.get("valid_to"),
            "snapshot_timestamp": _now_iso(),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await self.nodes.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def insert_edge(self, edge: dict) -> dict:
        doc = {
            "id": str(uuid.uuid4()),
            "source_node_id": edge["source_node_id"],
            "target_node_id": edge["target_node_id"],
            "relationship_type": edge["relationship_type"],
            "weight": edge.get("weight", 1.0),
            "created_at": _now_iso(),
        }
        await self.edges.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def list_nodes(self, category: Optional[str] = None, limit: int = 100) -> list[dict]:
        q: dict = {}
        if category:
            q["category"] = category
        cursor = self.nodes.find(q, {"_id": 0, "embedding": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def get_node(self, node_id: str) -> Optional[dict]:
        return await self.nodes.find_one({"id": node_id}, {"_id": 0})

    async def search_text(self, query: str, limit: int = 10) -> list[dict]:
        # Simple regex search across entity_name and payload
        q = {
            "$or": [
                {"entity_name": {"$regex": query, "$options": "i"}},
                {"payload.content": {"$regex": query, "$options": "i"}},
            ]
        }
        cursor = self.nodes.find(q, {"_id": 0, "embedding": 0}).limit(limit)
        return await cursor.to_list(limit)

    async def search_vector(self, embedding: list[float], limit: int = 10) -> list[dict]:
        # Mongo cosine similarity (manual since no vector index)
        import math

        def cos(a: list[float], b: list[float]) -> float:
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            return dot / (na * nb) if na and nb else 0.0

        cursor = self.nodes.find({"embedding": {"$ne": None}}, {"_id": 0})
        candidates = await cursor.to_list(500)
        scored = []
        for doc in candidates:
            sim = cos(embedding, doc.get("embedding") or [])
            doc_out = {k: v for k, v in doc.items() if k != "embedding"}
            doc_out["similarity"] = round(sim, 4)
            scored.append(doc_out)
        scored.sort(key=lambda d: d["similarity"], reverse=True)
        return scored[:limit]

    async def log_workflow_event(self, event: dict) -> dict:
        doc = {
            "id": str(uuid.uuid4()),
            "run_id": event["run_id"],
            "workflow_name": event["workflow_name"],
            "step_name": event.get("step_name"),
            "status": event.get("status", "pending"),
            "input_payload": event.get("input_payload", {}),
            "output_payload": event.get("output_payload", {}),
            "error_message": event.get("error_message"),
            "duration_ms": event.get("duration_ms"),
            "created_at": _now_iso(),
        }
        await self.events.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def list_workflow_events(self, run_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        q: dict = {}
        if run_id:
            q["run_id"] = run_id
        cursor = self.events.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def log_agent_action(self, action: dict) -> dict:
        doc = {
            "id": str(uuid.uuid4()),
            "action_type": action["action_type"],
            "actor": action["actor"],
            "target_node_id": action.get("target_node_id"),
            "confidence": action.get("confidence", {}),
            "citations": action.get("citations", []),
            "metadata": action.get("metadata", {}),
            "created_at": _now_iso(),
        }
        await self.actions.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def list_agent_actions(self, limit: int = 50) -> list[dict]:
        cursor = self.actions.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def insert_conversation_entry(self, session_id: str, role: str, content: str, metadata: Optional[dict] = None) -> dict:
        doc = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": _now_iso(),
        }
        await self.conversation_entries.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def list_conversation_entries(self, session_id: str, limit: int = 50) -> list[dict]:
        cursor = self.conversation_entries.find({"session_id": session_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def search_conversation_entries(self, session_id: str, query: str, limit: int = 10) -> list[dict]:
        q = {
            "session_id": session_id,
            "$or": [
                {"content": {"$regex": query, "$options": "i"}},
                {"metadata": {"$regex": query, "$options": "i"}},
            ]
        }
        cursor = self.conversation_entries.find(q, {"_id": 0}).limit(limit)
        return await cursor.to_list(limit)

    async def insert_orchestration_node(self, node: dict) -> dict:
        doc = {
            "id": node.get("id") or str(uuid.uuid4()),
            "node_type": node["node_type"],
            "name": node["name"],
            "metadata": node.get("metadata", {}),
            "created_at": _now_iso(),
        }
        await self.orchestration_nodes.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def insert_orchestration_edge(self, edge: dict) -> dict:
        doc = {
            "id": str(uuid.uuid4()),
            "source_node_id": edge["source_node_id"],
            "target_node_id": edge["target_node_id"],
            "relationship_type": edge["relationship_type"],
            "condition": edge.get("condition", {}),
            "weight": edge.get("weight", 1.0),
            "created_at": _now_iso(),
        }
        await self.orchestration_edges.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    async def list_orchestration_nodes(self, limit: int = 100) -> list[dict]:
        cursor = self.orchestration_nodes.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def list_orchestration_edges(self, limit: int = 100) -> list[dict]:
        cursor = self.orchestration_edges.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    async def get_orchestration_node(self, node_id: str) -> Optional[dict]:
        return await self.orchestration_nodes.find_one({"id": node_id}, {"_id": 0})

    async def get_outgoing_orchestration_edges(self, node_id: str, limit: int = 50) -> list[dict]:
        cursor = self.orchestration_edges.find({"source_node_id": node_id}, {"_id": 0}).sort("weight", -1).limit(limit)
        return await cursor.to_list(limit)

    async def stats(self) -> dict:
        return {
            "backend": "mongodb",
            "nodes": await self.nodes.count_documents({}),
            "edges": await self.edges.count_documents({}),
            "events": await self.events.count_documents({}),
            "actions": await self.actions.count_documents({}),
            "conversation_entries": await self.conversation_entries.count_documents({}),
            "orchestration_nodes": await self.orchestration_nodes.count_documents({}),
            "orchestration_edges": await self.orchestration_edges.count_documents({}),
        }


# ---------------------------------------------------------------------------
# Supabase Backend (production target)
# ---------------------------------------------------------------------------
class SupabaseBackend(StorageBackend):
    def __init__(self, url: str, service_key: str):
        from supabase import create_client
        self.client = create_client(url, service_key)

    def _to_dict(self, data: Any) -> Any:
        return data

    async def insert_node(self, node: dict) -> dict:
        row = {
            "category": node["category"],
            "entity_name": node["entity_name"],
            "payload": node.get("payload", {}),
            "embedding": node.get("embedding"),
            "confidence": node.get("confidence", 0.5),
            "source_url": node.get("source_url"),
        }
        res = self.client.table("knowledge_nodes").insert(row).execute()
        return res.data[0] if res.data else {}

    async def insert_edge(self, edge: dict) -> dict:
        row = {
            "source_node_id": edge["source_node_id"],
            "target_node_id": edge["target_node_id"],
            "relationship_type": edge["relationship_type"],
            "weight": edge.get("weight", 1.0),
        }
        res = self.client.table("knowledge_edges").insert(row).execute()
        return res.data[0] if res.data else {}

    async def list_nodes(self, category: Optional[str] = None, limit: int = 100) -> list[dict]:
        q = self.client.table("knowledge_nodes").select(
            "id,category,entity_name,payload,confidence,source_url,created_at"
        ).order("created_at", desc=True).limit(limit)
        if category:
            q = q.eq("category", category)
        res = q.execute()
        return res.data or []

    async def get_node(self, node_id: str) -> Optional[dict]:
        res = self.client.table("knowledge_nodes").select("*").eq("id", node_id).execute()
        return res.data[0] if res.data else None

    async def search_text(self, query: str, limit: int = 10) -> list[dict]:
        # Use ilike for text search
        res = self.client.table("knowledge_nodes").select(
            "id,category,entity_name,payload,created_at"
        ).ilike("entity_name", f"%{query}%").limit(limit).execute()
        return res.data or []

    async def search_vector(self, embedding: list[float], limit: int = 10) -> list[dict]:
        # Uses the SQL function match_knowledge_nodes
        res = self.client.rpc("match_knowledge_nodes", {
            "query_embedding": embedding,
            "match_threshold": 0.3,
            "match_count": limit,
        }).execute()
        return res.data or []

    async def log_workflow_event(self, event: dict) -> dict:
        row = {
            "run_id": event["run_id"],
            "workflow_name": event["workflow_name"],
            "step_name": event.get("step_name"),
            "status": event.get("status", "pending"),
            "input_payload": event.get("input_payload", {}),
            "output_payload": event.get("output_payload", {}),
            "error_message": event.get("error_message"),
            "duration_ms": event.get("duration_ms"),
        }
        res = self.client.table("workflow_events").insert(row).execute()
        return res.data[0] if res.data else {}

    async def list_workflow_events(self, run_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        q = self.client.table("workflow_events").select("*").order("created_at", desc=True).limit(limit)
        if run_id:
            q = q.eq("run_id", run_id)
        res = q.execute()
        return res.data or []

    async def log_agent_action(self, action: dict) -> dict:
        row = {
            "action_type": action["action_type"],
            "actor": action["actor"],
            "target_node_id": action.get("target_node_id"),
            "confidence": action.get("confidence", {}),
            "citations": action.get("citations", []),
            "metadata": action.get("metadata", {}),
        }
        res = self.client.table("agent_actions").insert(row).execute()
        return res.data[0] if res.data else {}

    async def list_agent_actions(self, limit: int = 50) -> list[dict]:
        res = self.client.table("agent_actions").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    async def insert_conversation_entry(self, session_id: str, role: str, content: str, metadata: Optional[dict] = None) -> dict:
        row = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        res = self.client.table("conversation_entries").insert(row).execute()
        return res.data[0] if res.data else {}

    async def list_conversation_entries(self, session_id: str, limit: int = 50) -> list[dict]:
        res = self.client.table("conversation_entries").select("*")
        res = res.eq("session_id", session_id).order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    async def search_conversation_entries(self, session_id: str, query: str, limit: int = 10) -> list[dict]:
        res = self.client.table("conversation_entries").select("*")
        res = res.eq("session_id", session_id).ilike("content", f"%{query}%")
        res = res.order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    async def insert_orchestration_node(self, node: dict) -> dict:
        row = {
            "node_type": node["node_type"],
            "name": node["name"],
            "metadata": node.get("metadata", {}),
        }
        res = self.client.table("orchestration_nodes").insert(row).execute()
        return res.data[0] if res.data else {}

    async def insert_orchestration_edge(self, edge: dict) -> dict:
        row = {
            "source_node_id": edge["source_node_id"],
            "target_node_id": edge["target_node_id"],
            "relationship_type": edge["relationship_type"],
            "condition": edge.get("condition", {}),
            "weight": edge.get("weight", 1.0),
        }
        res = self.client.table("orchestration_edges").insert(row).execute()
        return res.data[0] if res.data else {}

    async def list_orchestration_nodes(self, limit: int = 100) -> list[dict]:
        res = self.client.table("orchestration_nodes").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    async def list_orchestration_edges(self, limit: int = 100) -> list[dict]:
        res = self.client.table("orchestration_edges").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data or []

    async def get_orchestration_node(self, node_id: str) -> Optional[dict]:
        res = self.client.table("orchestration_nodes").select("*").eq("id", node_id).execute()
        return res.data[0] if res.data else None

    async def get_outgoing_orchestration_edges(self, node_id: str, limit: int = 50) -> list[dict]:
        res = self.client.table("orchestration_edges").select("*").eq("source_node_id", node_id)
        res = res.order("weight", desc=True).limit(limit).execute()
        return res.data or []

    async def stats(self) -> dict:
        try:
            nodes = self.client.table("knowledge_nodes").select("id", count="exact").execute()
            edges = self.client.table("knowledge_edges").select("id", count="exact").execute()
            events = self.client.table("workflow_events").select("id", count="exact").execute()
            actions = self.client.table("agent_actions").select("id", count="exact").execute()
            convo = self.client.table("conversation_entries").select("id", count="exact").execute()
            orch_nodes = self.client.table("orchestration_nodes").select("id", count="exact").execute()
            orch_edges = self.client.table("orchestration_edges").select("id", count="exact").execute()
            return {
                "backend": "supabase",
                "nodes": nodes.count or 0,
                "edges": edges.count or 0,
                "events": events.count or 0,
                "actions": actions.count or 0,
                "conversation_entries": convo.count or 0,
                "orchestration_nodes": orch_nodes.count or 0,
                "orchestration_edges": orch_edges.count or 0,
            }
        except Exception as e:
            return {"backend": "supabase", "error": str(e)[:200]}


# ---------------------------------------------------------------------------
# Backend selector
# ---------------------------------------------------------------------------
def get_storage() -> StorageBackend:
    """Select the best available backend. Prefers Supabase if a valid
    service_role key is provided, otherwise falls back to MongoDB."""
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    use_supabase = bool(supabase_url and service_key and service_key.lower() != "none")

    if use_supabase:
        try:
            backend = SupabaseBackend(supabase_url, service_key)
            # Verify connection by issuing a head request
            try:
                backend.client.table("knowledge_nodes").select("id", count="exact").limit(1).execute()
                return backend
            except Exception:
                # Fall through to mongo
                pass
        except Exception:
            pass

    return MongoBackend(
        os.environ["MONGO_URL"],
        os.environ["DB_NAME"],
    )


# Singleton
_storage: Optional[StorageBackend] = None


def storage() -> StorageBackend:
    global _storage
    if _storage is None:
        _storage = get_storage()
    return _storage
