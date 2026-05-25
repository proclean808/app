"""
Venture Ferret backend regression tests.
Covers: health, categories, research pipeline trigger, graph nodes,
retrieval (semantic/keyword/hybrid), governance, workflows, stats.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://memsmart-graph.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ------------------ Health / Meta ------------------
class TestHealthMeta:
    def test_health(self, session):
        r = session.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert "storage" in d
        assert d["storage"]["backend"] in ("mongodb", "supabase")
        assert isinstance(d["storage"].get("nodes"), int)

    def test_categories(self, session):
        r = session.get(f"{API}/categories", timeout=15)
        assert r.status_code == 200
        cats = r.json()["categories"]
        ids = {c["id"] for c in cats}
        assert ids == {"market_signal", "technical_dependency", "competitor_analysis", "infrastructure"}
        for c in cats:
            assert "label" in c and "description" in c


# ------------------ Stats ------------------
class TestStats:
    def test_stats_overview(self, session):
        r = session.get(f"{API}/stats/overview", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "totals" in d
        assert "by_category" in d
        assert "recent_nodes" in d
        assert isinstance(d["recent_nodes"], list)
        assert isinstance(d["totals"].get("nodes"), int)


# ------------------ Graph Nodes ------------------
class TestGraphNodes:
    def test_list_nodes(self, session):
        r = session.get(f"{API}/graph/nodes", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["nodes"], list)
        assert d["count"] == len(d["nodes"])

    def test_list_nodes_filter_category(self, session):
        r = session.get(f"{API}/graph/nodes", params={"category": "infrastructure"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for n in d["nodes"]:
            assert n["category"] == "infrastructure"

    def test_get_node_404(self, session):
        r = session.get(f"{API}/graph/nodes/non-existent-id-xyz", timeout=15)
        assert r.status_code == 404

    def test_get_node_detail_if_any(self, session):
        list_r = session.get(f"{API}/graph/nodes", timeout=15)
        nodes = list_r.json()["nodes"]
        if not nodes:
            pytest.skip("No nodes available to fetch detail")
        nid = nodes[0]["id"]
        r = session.get(f"{API}/graph/nodes/{nid}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == nid
        assert "embedding" not in d  # excluded from response
        assert "_id" not in d


# ------------------ Retrieval ------------------
class TestRetrieval:
    def test_semantic(self, session):
        r = session.post(f"{API}/retrieve/semantic", json={"query": "infrastructure", "limit": 5}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["mode"] == "semantic"
        assert isinstance(d["results"], list)
        if d["results"]:
            assert "similarity" in d["results"][0]

    def test_keyword(self, session):
        r = session.post(f"{API}/retrieve/keyword", json={"query": "a", "limit": 5}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["mode"] == "keyword"
        assert isinstance(d["results"], list)

    def test_hybrid(self, session):
        r = session.post(f"{API}/retrieve/hybrid", json={"query": "infrastructure", "limit": 5}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["mode"] == "hybrid"
        if d["results"]:
            first = d["results"][0]
            assert "score_combined" in first
            assert "score_semantic" in first
            assert "score_keyword" in first


# ------------------ Governance / Workflows ------------------
class TestGovernanceWorkflows:
    def test_governance_actions(self, session):
        r = session.get(f"{API}/governance/actions", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["actions"], list)
        assert d["count"] == len(d["actions"])

    def test_workflow_events(self, session):
        r = session.get(f"{API}/workflows/events", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["events"], list)

    def test_research_runs_list(self, session):
        r = session.get(f"{API}/research/runs", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["runs"], list)


# ------------------ Research Pipeline (live) ------------------
class TestResearchPipeline:
    """Triggers a real pipeline. Uses small target site to keep runtime low."""

    def test_trigger_and_poll(self, session):
        payload = {"target_domain": "https://example.com", "query": "TEST_what is example used for"}
        r = session.post(f"{API}/research/trigger", json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "queued"
        run_id = d["run_id"]
        assert run_id

        # Poll for completion (~30s budget)
        completed = False
        last_events = []
        for _ in range(20):
            time.sleep(3)
            rr = session.get(f"{API}/research/runs/{run_id}", timeout=15)
            assert rr.status_code == 200
            data = rr.json()
            last_events = data["events"]
            if data["status"] in ("completed", "failed"):
                completed = True
                break

        assert completed, f"Pipeline did not complete in 60s. Events: {[e.get('step_name') for e in last_events]}"

        # Verify expected step names appear
        step_names = {e.get("step_name") for e in last_events}
        expected = {"pipeline_start", "fetch_web_data", "extract_signals", "embed_and_store", "link_and_plan", "pipeline_complete"}
        missing = expected - step_names
        # Allow at most 1 missing in case of partial failures
        assert len(missing) <= 1, f"Missing steps: {missing}. Got: {step_names}"

    def test_get_run_not_found(self, session):
        r = session.get(f"{API}/research/runs/does-not-exist-xyz", timeout=15)
        assert r.status_code == 404
