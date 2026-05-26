import React, { useEffect, useState } from "react";
import {
  Activity,
  Database,
  Network,
  Search,
  ShieldCheck,
  Layers,
  Cpu,
  History,
  Hexagon,
  Crosshair,
  Plus,
  Zap,
} from "lucide-react";
import {
  Panel,
  Eyebrow,
  Stat,
  StatusPill,
  CategoryTag,
  Button,
  Input,
  Spinner,
  EmptyState,
} from "@/components/Primitives";
import {
  fetchStats,
  fetchRuns,
  fetchRun,
  fetchNodes,
  fetchActions,
  fetchEvents,
  triggerResearch,
  retrieveHybrid,
  retrieveSemantic,
  retrieveKeyword,
  fetchCategories,
  fetchHealth,
} from "@/lib/api";

// ============================================================================
// TopBar
// ============================================================================
function TopBar({ health, activeView, onView }) {
  const tabs = [
    { id: "ops", label: "Operations", icon: Activity },
    { id: "graph", label: "Topology Memory", icon: Network },
    { id: "retrieve", label: "Semantic Retrieval", icon: Search },
    { id: "timeline", label: "Incident Timeline", icon: History },
    { id: "governance", label: "Governance", icon: ShieldCheck },
  ];
  return (
    <header
      className="sticky top-0 z-30 bg-ferret-bg border-b border-ferret-border"
      data-testid="topbar"
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-ferret-border">
        <div className="flex items-center gap-4">
          <div
            className="w-9 h-9 border border-ferret-accent flex items-center justify-center"
            style={{ background: "rgba(255,79,0,0.1)" }}
          >
            <Hexagon size={18} className="text-ferret-accent" strokeWidth={1.5} />
          </div>
          <div>
            <div className="mono text-[10px] uppercase tracking-[0.25em] text-ferret-textSecondary">
              PlatFormula.ONE
            </div>
            <div className="text-base font-semibold tracking-tight text-ferret-textPrimary leading-none mt-0.5">
              Venture Ferret <span className="text-ferret-accent">/ Core Engine</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="hidden md:flex items-center gap-2 mono text-[10px] uppercase tracking-[0.18em] text-ferret-textSecondary">
            <span
              className="w-1.5 h-1.5 animate-pulse-accent"
              style={{
                background:
                  health?.status === "ok" ? "#00FF41" : "#FF3B30",
              }}
            />
            {health?.status === "ok" ? "ENGINE ONLINE" : "DEGRADED"}
            <span className="text-ferret-textTertiary mx-2">|</span>
            <span>BACKEND: {health?.storage?.backend || "—"}</span>
          </div>
          <div className="mono text-[10px] uppercase tracking-[0.18em] text-ferret-textTertiary">
            v1.0.0
          </div>
        </div>
      </div>

      <nav className="flex overflow-x-auto" data-testid="primary-nav">
        {tabs.map((t) => {
          const active = activeView === t.id;
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              data-testid={`nav-${t.id}`}
              onClick={() => onView(t.id)}
              className={`mono uppercase text-[11px] tracking-[0.18em] px-5 py-3 border-r border-ferret-border flex items-center gap-2 transition-colors ${
                active
                  ? "text-ferret-textPrimary bg-ferret-surface border-l-2 border-l-ferret-accent"
                  : "text-ferret-textSecondary hover:text-ferret-textPrimary hover:bg-ferret-surfaceHover"
              }`}
            >
              <Icon size={14} strokeWidth={1.8} />
              {t.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}

// ============================================================================
// OPERATIONS VIEW (default landing)
// ============================================================================
function OperationsView({ refreshSignal, bumpRefresh }) {
  const [stats, setStats] = useState(null);
  const [runs, setRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [activeRunDetail, setActiveRunDetail] = useState(null);

  const [domain, setDomain] = useState("https://example.com");
  const [query, setQuery] = useState("Identify strategic signals, pricing, and infrastructure for the target site.");
  const [triggering, setTriggering] = useState(false);
  const [lastError, setLastError] = useState(null);

  // Polling
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [s, r] = await Promise.all([fetchStats(), fetchRuns()]);
        if (!alive) return;
        setStats(s);
        setRuns(r);
        if (!activeRun && r.length) setActiveRun(r[0].run_id);
      } catch (e) {
        // silent
      }
    };
    load();
    const iv = setInterval(load, 4000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [refreshSignal]); // eslint-disable-line

  // Active run detail polling
  useEffect(() => {
    if (!activeRun) {
      setActiveRunDetail(null);
      return;
    }
    let alive = true;
    const load = async () => {
      try {
        const d = await fetchRun(activeRun);
        if (alive) setActiveRunDetail(d);
      } catch (e) {
        if (alive) setActiveRunDetail(null);
      }
    };
    load();
    const iv = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [activeRun]);

  const onTrigger = async () => {
    if (!domain || !query) return;
    setTriggering(true);
    setLastError(null);
    try {
      const res = await triggerResearch(domain.trim(), query.trim());
      setActiveRun(res.run_id);
      bumpRefresh();
    } catch (e) {
      setLastError(e?.response?.data?.detail || e.message);
    } finally {
      setTriggering(false);
    }
  };

  const byCat = stats?.by_category || {};
  const totals = stats?.totals || {};

  return (
    <div className="space-y-px">
      {/* Telemetry strip */}
      <div className="flex flex-wrap bg-ferret-surface border border-ferret-border">
        <Stat label="Knowledge Nodes" value={totals.nodes ?? "—"} accent testid="stat-nodes" />
        <Stat label="Graph Edges" value={totals.edges ?? "—"} testid="stat-edges" />
        <Stat label="Workflow Events" value={totals.events ?? "—"} testid="stat-events" />
        <Stat label="Agent Actions" value={totals.actions ?? "—"} testid="stat-actions" />
        <Stat
          label="Backend"
          value={totals.backend?.toUpperCase() || "—"}
          hint="storage layer"
          testid="stat-backend"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-px">
        {/* Trigger panel */}
        <Panel
          testid="trigger-panel"
          className="lg:col-span-2"
          eyebrow="01 / Initiate"
          title="Research Pipeline Trigger"
        >
          <div className="p-5 space-y-4">
            <div>
              <Eyebrow>Target Domain</Eyebrow>
              <Input
                testid="input-target"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="https://example.com"
                className="mt-2"
              />
            </div>
            <div>
              <Eyebrow>Analyst Query</Eyebrow>
              <textarea
                data-testid="input-query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={4}
                placeholder="e.g. infrastructure choices, competitor positioning..."
                className="w-full bg-ferret-bg border border-ferret-border text-ferret-textPrimary mono text-sm px-3 py-2.5 mt-2 placeholder:text-ferret-textTertiary focus:outline-none focus:border-ferret-accent transition-colors resize-none"
              />
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-ferret-border">
              <div className="mono text-[10px] uppercase tracking-[0.18em] text-ferret-textTertiary">
                4 steps · firecrawl · gemini · pgvector
              </div>
              <Button
                testid="btn-trigger"
                onClick={onTrigger}
                disabled={triggering || !domain || !query}
              >
                {triggering ? (
                  <Spinner size={12} label="Dispatching" />
                ) : (
                  <>
                    <Zap size={12} /> Execute Pipeline
                  </>
                )}
              </Button>
            </div>
            {lastError && (
              <div className="mono text-xs text-ferret-error border border-ferret-error/30 bg-ferret-error/5 px-3 py-2">
                ERROR: {lastError}
              </div>
            )}
          </div>
        </Panel>

        {/* Active run telemetry */}
        <Panel
          className="lg:col-span-3"
          eyebrow="02 / Active Run"
          title={
            activeRunDetail
              ? `Run · ${activeRunDetail.run_id.slice(0, 8)}`
              : "No active run selected"
          }
          action={
            activeRunDetail && (
              <StatusPill status={activeRunDetail.status} testid="active-run-status" />
            )
          }
          testid="active-run-panel"
        >
          {!activeRunDetail ? (
            <EmptyState
              icon={Crosshair}
              title="Trigger a pipeline to begin"
              hint="Pipeline telemetry will stream here in real-time."
              testid="empty-active-run"
            />
          ) : (
            <div className="divide-y divide-ferret-border">
              {[...activeRunDetail.events]
                .reverse()
                .map((e, idx) => (
                  <RunStepRow event={e} key={`${e.id || idx}`} idx={idx} />
                ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-px">
        {/* Run history */}
        <Panel
          className="lg:col-span-2"
          eyebrow="03 / Run History"
          title="Pipeline Runs"
          testid="run-history-panel"
        >
          {!runs.length ? (
            <EmptyState
              icon={History}
              title="No runs yet"
              hint="History will populate after your first execution."
              testid="empty-runs"
            />
          ) : (
            <div className="divide-y divide-ferret-border max-h-[420px] overflow-y-auto">
              {runs.map((r) => (
                <button
                  key={r.run_id}
                  data-testid={`run-row-${r.run_id}`}
                  onClick={() => setActiveRun(r.run_id)}
                  className={`w-full text-left px-5 py-3 flex items-center justify-between gap-4 transition-colors hover:bg-ferret-surfaceHover ${
                    activeRun === r.run_id
                      ? "bg-ferret-surfaceHover border-l-2 border-l-ferret-accent"
                      : ""
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="mono text-xs text-ferret-textPrimary truncate">
                      {r.target_domain || "—"}
                    </div>
                    <div className="text-xs text-ferret-textSecondary truncate mt-0.5">
                      {r.query || "—"}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="mono text-[10px] text-ferret-textTertiary">
                      {r.step_count} steps
                    </span>
                    <StatusPill status={r.status} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        {/* Category breakdown */}
        <Panel
          eyebrow="04 / Cognitive Mix"
          title="Nodes by Category"
          testid="category-breakdown-panel"
        >
          <div className="p-5 space-y-3">
            {Object.keys(byCat).length === 0 ? (
              <EmptyState
                icon={Layers}
                title="No nodes yet"
                hint="Categories populate once nodes are extracted."
              />
            ) : (
              Object.entries(byCat).map(([cat, n]) => {
                const pct = totals.nodes ? Math.round((n / totals.nodes) * 100) : 0;
                return (
                  <div key={cat} data-testid={`cat-bar-${cat}`}>
                    <div className="flex justify-between items-center mb-1">
                      <CategoryTag category={cat} />
                      <span className="mono text-xs text-ferret-textPrimary">
                        {n} <span className="text-ferret-textTertiary">/ {pct}%</span>
                      </span>
                    </div>
                    <div className="h-1 bg-ferret-border">
                      <div
                        className="h-full bg-ferret-accent"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function RunStepRow({ event, idx }) {
  const ms = event.duration_ms;
  const out = event.output_payload || {};
  return (
    <div className="px-5 py-3 flex items-start gap-4" data-testid={`step-row-${event.step_name}-${idx}`}>
      <div className="mono text-[10px] text-ferret-textTertiary w-8 pt-1">
        {String(idx + 1).padStart(2, "0")}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-3">
          <span className="mono text-xs text-ferret-textPrimary">
            {event.step_name}
          </span>
          <StatusPill status={event.status} />
          {ms != null && (
            <span className="mono text-[10px] text-ferret-textTertiary">
              {ms}ms
            </span>
          )}
        </div>
        {Object.keys(out).length > 0 && (
          <div className="mono text-[11px] text-ferret-textSecondary mt-1 truncate">
            {Object.entries(out)
              .filter(([k]) => k !== "blueprint")
              .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v).slice(0, 40) : v}`)
              .join(" · ")}
          </div>
        )}
        {event.error_message && (
          <div className="mono text-[11px] text-ferret-error mt-1">
            err: {event.error_message}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// TOPOLOGY MEMORY (Knowledge Graph)
// ============================================================================
function TopologyView() {
  const [nodes, setNodes] = useState([]);
  const [cats, setCats] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      setLoading(true);
      try {
        const [n, c] = await Promise.all([
          fetchNodes({ limit: 200, category: filter || undefined }),
          fetchCategories(),
        ]);
        if (!alive) return;
        setNodes(n.nodes || []);
        setCats(c);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    return () => (alive = false);
  }, [filter]);

  return (
    <div className="space-y-px">
      <Panel eyebrow="Memory Surface" title="Topology of Extracted Knowledge" testid="topology-panel">
        <div className="px-5 py-4 border-b border-ferret-border flex flex-wrap items-center gap-2">
          <Eyebrow className="mr-3">Filter</Eyebrow>
          <button
            data-testid="cat-filter-all"
            onClick={() => setFilter("")}
            className={`mono text-[10px] uppercase tracking-[0.18em] px-3 py-1.5 border ${
              filter === "" ? "border-ferret-accent text-ferret-accent" : "border-ferret-border text-ferret-textSecondary hover:text-ferret-textPrimary"
            }`}
          >
            All
          </button>
          {cats.map((c) => (
            <button
              key={c.id}
              data-testid={`cat-filter-${c.id}`}
              onClick={() => setFilter(c.id)}
              className={`mono text-[10px] uppercase tracking-[0.18em] px-3 py-1.5 border ${
                filter === c.id
                  ? "border-ferret-accent text-ferret-accent"
                  : "border-ferret-border text-ferret-textSecondary hover:text-ferret-textPrimary"
              }`}
            >
              {c.label}
            </button>
          ))}
          <span className="ml-auto mono text-[10px] text-ferret-textTertiary">
            {nodes.length} nodes
          </span>
        </div>

        {loading ? (
          <div className="p-12 flex justify-center">
            <Spinner label="Loading nodes" />
          </div>
        ) : nodes.length === 0 ? (
          <EmptyState
            icon={Database}
            title="Empty topology"
            hint="Run a research pipeline to populate the knowledge graph."
            testid="empty-topology"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-px bg-ferret-border">
            {nodes.map((n) => (
              <NodeCard node={n} key={n.id} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function NodeCard({ node }) {
  const p = node.payload || {};
  return (
    <article
      data-testid={`node-card-${node.id}`}
      className="bg-ferret-surface p-5 hover:bg-ferret-surfaceHover transition-colors group"
    >
      <div className="flex items-center justify-between mb-3">
        <CategoryTag category={node.category} />
        <span
          className="mono text-[10px] text-ferret-textTertiary"
          data-testid={`node-conf-${node.id}`}
        >
          conf={(node.confidence ?? 0).toFixed(2)}
        </span>
      </div>
      <h4 className="text-sm font-medium text-ferret-textPrimary leading-snug mb-2">
        {node.entity_name}
      </h4>
      {p.summary && (
        <p className="text-xs text-ferret-textSecondary leading-relaxed mb-3 line-clamp-3">
          {p.summary}
        </p>
      )}
      {p.evidence && (
        <div className="border-l-2 border-ferret-border pl-3 mt-2">
          <div className="label-eyebrow mb-1">Evidence</div>
          <p className="mono text-[11px] text-ferret-textSecondary leading-relaxed line-clamp-2">
            {p.evidence}
          </p>
        </div>
      )}
      <div className="flex justify-between items-center mt-4 pt-3 border-t border-ferret-border">
        <span className="mono text-[10px] text-ferret-textTertiary truncate max-w-[60%]">
          {node.source_url ? new URL(node.source_url).hostname : "—"}
        </span>
        <span className="mono text-[10px] text-ferret-textTertiary">
          {node.id?.slice(0, 8)}
        </span>
      </div>
    </article>
  );
}

// ============================================================================
// SEMANTIC RETRIEVAL
// ============================================================================
function RetrievalView() {
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [results, setResults] = useState([]);
  const [meta, setMeta] = useState(null);
  const [busy, setBusy] = useState(false);

  const onSearch = async () => {
    if (!q.trim()) return;
    setBusy(true);
    try {
      let res;
      if (mode === "semantic") res = await retrieveSemantic(q, 20);
      else if (mode === "keyword") res = await retrieveKeyword(q, 20);
      else res = await retrieveHybrid(q, 20);
      setResults(res.results || []);
      setMeta({ count: res.count, mode: res.mode });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-px">
      <Panel
        eyebrow="Hybrid Memory Retrieval"
        title="Query the Knowledge Graph"
        testid="retrieval-panel"
      >
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-3">
            <Input
              testid="retrieve-query"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. infrastructure choices, pricing models..."
            />
            <div className="flex border border-ferret-border">
              {["semantic", "keyword", "hybrid"].map((m) => (
                <button
                  key={m}
                  data-testid={`mode-${m}`}
                  onClick={() => setMode(m)}
                  className={`mono text-[10px] uppercase tracking-[0.18em] px-3 py-2.5 border-r last:border-r-0 border-ferret-border ${
                    mode === m
                      ? "bg-ferret-accent text-white"
                      : "text-ferret-textSecondary hover:text-ferret-textPrimary"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <Button testid="btn-search" onClick={onSearch} disabled={busy || !q.trim()}>
              {busy ? <Spinner size={12} label="Searching" /> : <><Search size={12} /> Query</>}
            </Button>
          </div>

          {meta && (
            <div className="mono text-[10px] uppercase tracking-[0.2em] text-ferret-textTertiary">
              mode={meta.mode} · results={meta.count}
            </div>
          )}
        </div>

        {results.length === 0 && !busy && (
          <EmptyState
            icon={Search}
            title="No results yet"
            hint="Enter a query and pick a retrieval mode. Semantic uses Gemini embeddings; Hybrid combines vector + keyword."
            testid="empty-retrieval"
          />
        )}

        {results.length > 0 && (
          <div className="divide-y divide-ferret-border">
            {results.map((r, idx) => (
              <RetrievalResultRow result={r} idx={idx} key={r.id} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function RetrievalResultRow({ result, idx }) {
  const p = result.payload || {};
  return (
    <article
      className="px-5 py-4 hover:bg-ferret-surfaceHover transition-colors flex gap-5"
      data-testid={`result-row-${idx}`}
    >
      <div className="mono text-[10px] text-ferret-textTertiary w-8 pt-1">
        {String(idx + 1).padStart(2, "0")}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 flex-wrap">
          <CategoryTag category={result.category} />
          <h5 className="text-sm font-medium text-ferret-textPrimary">{result.entity_name}</h5>
        </div>
        {p.summary && (
          <p className="text-xs text-ferret-textSecondary mt-2 leading-relaxed">{p.summary}</p>
        )}
      </div>
      <div className="text-right shrink-0 mono text-[10px] space-y-1">
        {"similarity" in result && (
          <div>
            <span className="text-ferret-textTertiary">sim </span>
            <span className="text-ferret-accent">{result.similarity?.toFixed(3)}</span>
          </div>
        )}
        {"score_combined" in result && (
          <>
            <div>
              <span className="text-ferret-textTertiary">combined </span>
              <span className="text-ferret-accent">{result.score_combined?.toFixed(3)}</span>
            </div>
            <div className="text-ferret-textTertiary">
              sem={result.score_semantic?.toFixed(2)} kw={result.score_keyword?.toFixed(2)}
            </div>
          </>
        )}
      </div>
    </article>
  );
}

// ============================================================================
// INCIDENT TIMELINE (all workflow events)
// ============================================================================
function TimelineView() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const e = await fetchEvents({ limit: 200 });
        if (alive) setEvents(e);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    const iv = setInterval(load, 3000);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, []);

  return (
    <Panel
      eyebrow="Temporal Replay"
      title="Workflow Event Stream"
      testid="timeline-panel"
      action={
        <span className="mono text-[10px] text-ferret-textTertiary">
          {events.length} events
        </span>
      }
    >
      {loading ? (
        <div className="p-12 flex justify-center">
          <Spinner label="Loading events" />
        </div>
      ) : events.length === 0 ? (
        <EmptyState
          icon={History}
          title="No events"
          hint="Workflow telemetry appears here after running a pipeline."
        />
      ) : (
        <div className="divide-y divide-ferret-border max-h-[70vh] overflow-y-auto">
          {events.map((e, i) => (
            <div
              key={e.id || i}
              className="px-5 py-3 flex items-center gap-4 hover:bg-ferret-surfaceHover"
              data-testid={`timeline-row-${i}`}
            >
              <span className="mono text-[10px] text-ferret-textTertiary w-32 shrink-0 truncate">
                {(e.created_at || "").slice(11, 19)}
              </span>
              <StatusPill status={e.status} />
              <span className="mono text-xs text-ferret-textPrimary w-48 shrink-0 truncate">
                {e.step_name}
              </span>
              <span className="mono text-[11px] text-ferret-textSecondary w-24 shrink-0">
                {e.duration_ms != null ? `${e.duration_ms}ms` : "—"}
              </span>
              <span className="mono text-[10px] text-ferret-textTertiary truncate">
                run={(e.run_id || "").slice(0, 8)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

// ============================================================================
// GOVERNANCE
// ============================================================================
function GovernanceView() {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    fetchActions(100)
      .then((a) => alive && setActions(a))
      .finally(() => alive && setLoading(false));
    return () => (alive = false);
  }, []);

  return (
    <Panel
      eyebrow="Audit Trail"
      title="Agent Action Log"
      testid="governance-panel"
      action={
        <span className="mono text-[10px] text-ferret-textTertiary">
          {actions.length} actions
        </span>
      }
    >
      {loading ? (
        <div className="p-12 flex justify-center">
          <Spinner label="Loading audit log" />
        </div>
      ) : actions.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No agent actions yet"
          hint="Every node creation, edge link and policy decision is logged here."
        />
      ) : (
        <div className="divide-y divide-ferret-border">
          {actions.map((a, i) => (
            <article
              key={a.id || i}
              className="px-5 py-4 hover:bg-ferret-surfaceHover"
              data-testid={`action-row-${i}`}
            >
              <header className="flex items-center justify-between gap-4 mb-2">
                <div className="flex items-center gap-3">
                  <span className="mono text-[10px] uppercase tracking-[0.18em] text-ferret-accent">
                    {a.action_type}
                  </span>
                  <span className="mono text-xs text-ferret-textPrimary">{a.actor}</span>
                </div>
                <span className="mono text-[10px] text-ferret-textTertiary">
                  {(a.created_at || "").slice(0, 19).replace("T", " ")}
                </span>
              </header>
              {a.confidence && Object.keys(a.confidence).length > 0 && (
                <div className="flex flex-wrap gap-4 mt-2">
                  {Object.entries(a.confidence).map(([k, v]) => (
                    <div key={k} className="mono text-[11px]">
                      <span className="text-ferret-textTertiary">{k}: </span>
                      <span
                        className={
                          v > 0.8
                            ? "text-ferret-success"
                            : v > 0.5
                            ? "text-ferret-warning"
                            : "text-ferret-error"
                        }
                      >
                        {Number(v).toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {a.citations && a.citations.length > 0 && (
                <div className="mt-2 mono text-[11px] text-ferret-textSecondary">
                  citations: {a.citations.map((c) => c.source_url || c.title).join(", ")}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

// ============================================================================
// Console root
// ============================================================================
export default function VentureFerretConsole() {
  const [view, setView] = useState("ops");
  const [health, setHealth] = useState(null);
  const [refreshSignal, setRefreshSignal] = useState(0);

  useEffect(() => {
    const load = () => fetchHealth().then(setHealth).catch(() => setHealth({ status: "down" }));
    load();
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="min-h-screen bg-ferret-bg bg-grid-fine text-ferret-textPrimary">
      <TopBar health={health} activeView={view} onView={setView} />

      <main className="px-6 py-6 max-w-[1600px] mx-auto" data-testid={`view-${view}`}>
        {view === "ops" && (
          <OperationsView
            refreshSignal={refreshSignal}
            bumpRefresh={() => setRefreshSignal((s) => s + 1)}
          />
        )}
        {view === "graph" && <TopologyView />}
        {view === "retrieve" && <RetrievalView />}
        {view === "timeline" && <TimelineView />}
        {view === "governance" && <GovernanceView />}
      </main>

      <footer className="px-6 py-6 border-t border-ferret-border mt-12">
        <div className="flex flex-wrap items-center justify-between gap-3 text-ferret-textTertiary">
          <span className="mono text-[10px] uppercase tracking-[0.2em]">
            Venture Ferret · Cognitive Infrastructure Console
          </span>
          <span className="mono text-[10px] uppercase tracking-[0.2em]">
            Firecrawl · Gemini · pgvector · Hatchet
          </span>
        </div>
      </footer>
    </div>
  );
}
