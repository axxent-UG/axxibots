"use client";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { departments, stages, type Snapshot } from "@/lib/model";
import Office from "./office";
const views = [
  ["office", "⌘", "Headquarters"],
  ["operations", "◈", "Operations"],
  ["pipeline", "▥", "Product pipeline"],
  ["finance", "◷", "Finance"],
  ["agents", "♧", "Agent performance"],
] as const;
type View = (typeof views)[number][0];
type Selection = {
  type: "agent" | "product" | "run" | "task";
  id: string;
} | null;
const money = (v: number | null | undefined) =>
  v == null
    ? "Unknown"
    : new Intl.NumberFormat("en", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 3,
      }).format(v);
const date = (v: string | null | undefined) =>
  v
    ? new Intl.DateTimeFormat("en-GB", {
        timeZone: "Europe/Berlin",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(v))
    : "No evidence";
const pct = (v: number | null) => (v === null ? "Unknown" : `${v}%`);
function Badge({ text }: { text: string }) {
  return (
    <span className={`badge ${text.toLowerCase().replaceAll(" ", "-")}`}>
      {text}
    </span>
  );
}
function Metric({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  note: string;
  tone?: string;
}) {
  return (
    <div className="metric">
      <span className="eyebrow">{label}</span>
      <strong style={{ color: tone }}>{value}</strong>
      <span className="muted small">{note}</span>
    </div>
  );
}
function Empty({ text = "No records in this snapshot." }: { text?: string }) {
  return <div className="empty">{text}</div>;
}
export default function Cockpit({ demo }: { demo: boolean }) {
  const [view, setView] = useState<View>("office"),
    [data, setData] = useState<Snapshot | null>(null),
    [error, setError] = useState(""),
    [login, setLogin] = useState(false),
    [busy, setBusy] = useState(true),
    [selection, setSelection] = useState<Selection>(null),
    [search, setSearch] = useState(""),
    [filter, setFilter] = useState("ALL");
  const [decisionBusy, setDecisionBusy] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const decideIdea = async (ideaId: string, title: string, decision: "APPROVED" | "REJECTED") => {
    if (!window.confirm(`${decision === "APPROVED" ? "Approve production of" : "Reject"} "${title}"? Approval starts the existing automated design and Etsy draft pipeline, subject to its budgets and quality gates. This does not publish a listing.`)) return;
    setDecisionBusy(ideaId);
    setDecisionError("");
    try {
      const r = await fetch("/api/owner/idea", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ideaId, decision }) });
      const response = await r.json();
      if (!r.ok) throw new Error(response.error || "Decision failed");
      await refresh();
    } catch (e) { setDecisionError(e instanceof Error ? e.message : "Decision failed"); }
    finally { setDecisionBusy(null); }
  };
  const flight = useRef(false),
    controller = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    if (flight.current) return;
    flight.current = true;
    setBusy(true);
    controller.current = new AbortController();
    try {
      const r = await fetch("/api/data", {
        cache: "no-store",
        signal: controller.current.signal,
      });
      const body = await r.json();
      if (!r.ok) {
        setLogin(r.status === 401 && body.kind !== "SITE_ACCESS");
        if (r.status === 401) setData(null);
        throw new Error(body.error ?? "Refresh failed");
      }
      setData(body);
      setError("");
      setLogin(false);
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError") setError(e.message);
    } finally {
      flight.current = false;
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 20000);
    const resume = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("focus", resume);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("focus", resume);
      controller.current?.abort();
    };
  }, [refresh]);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelection(null);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);
  const changeView = (v: View) => {
    setView(v);
    setFilter("ALL");
    setSearch("");
  };
  const select = (type: NonNullable<Selection>["type"], id: string) =>
    setSelection({ type, id });
  const matches = (...v: string[]) =>
    v.join(" ").toLowerCase().includes(search.toLowerCase());
  const stale = !!error;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="/" className="brand">
          <span className="brand-icon">
            a<span>×</span>
          </span>
          <div>
            AXXIBOTS <b>HQ</b>
            <small>THE AUTONOMOUS COMPANY</small>
          </div>
        </a>
        <div className="workspace-label">
          <span className="workspace-dot" /> Axxent workspace <span>⌄</span>
        </div>
        <p className="eyebrow nav-label">CONTROL ROOM</p>
        <nav>
          {views.map(([id, icon, label]) => (
            <button
              className={`nav-item ${view === id ? "active" : ""}`}
              key={id}
              onClick={() => changeView(id)}
              aria-current={view === id ? "page" : undefined}
            >
              <span>{icon}</span>
              {label}
              {id === "operations" && !!data?.counts.stalled && (
                <b>{data.counts.stalled}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="goal-card">
            <span className="eyebrow">NORTH STAR</span>
            <div>
              <strong>
                90<span>%</span>
              </strong>
              <span>
                autonomy
                <br />
                business quality
              </span>
            </div>
            <p>Targets, not measured scores.</p>
          </div>
          <div className="small muted">
            <span className="lock">◇</span> Read-only access
            <br />
            <span className="lock">◷</span> Refresh every 20 seconds
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            <strong>{views.find((v) => v[0] === view)?.[2]}</strong>
          </div>
          <div className="header-actions">
            <span className={`mode ${demo ? "demo" : "live"}`}>
              <i />
              {demo ? "DEMO MODE" : stale ? "LIVE · UNAVAILABLE" : "LIVE MODE"}
            </span>
            <button
              className="icon-button"
              onClick={() => void refresh()}
              disabled={busy}
              aria-label="Refresh data"
            >
              {busy ? "…" : "↻"}
            </button>
            {!demo && !login && data && (
              <button
                className="button subtle"
                onClick={async () => {
                  await fetch("/api/auth", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "logout" }),
                  });
                  setData(null);
                  setLogin(true);
                }}
              >
                Sign out
              </button>
            )}
            <span className="avatar">AX</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                AXXIBOTS /{" "}
                {view === "office" ? "COMMAND CENTER" : view.toUpperCase()}
              </div>
              <h1>
                {
                  {
                    office: "A company in motion.",
                    operations: "Every execution. Every outcome.",
                    pipeline: "From opportunity to market.",
                    finance: "The economics of autonomy.",
                    agents: "Your team, by the numbers.",
                  }[view]
                }
              </h1>
              <p className="muted">
                {
                  {
                    office:
                      "One headquarters for the people, processes and products behind your AI business.",
                    operations:
                      "Technical success is only half the story. Follow the business evidence.",
                    pipeline:
                      "A single product journey, mapped from the real production states.",
                    finance:
                      "Recorded expenses, transparent estimates and honest unknowns.",
                    agents:
                      "Operational evidence across every department. No invented activity.",
                  }[view]
                }
              </p>
            </div>
            <span className="snapshot-label">
              {data ? (
                <>
                  SNAPSHOT · BERLIN
                  <br />
                  {date(data.at)}
                </>
              ) : busy ? (
                "CONNECTING…"
              ) : (
                "AWAITING CONNECTION"
              )}
            </span>
          </div>
          {demo && (
            <div className="notice demo-notice">
              <span>◇</span>
              <div>
                <strong>Demo workspace</strong> — every agent, product and
                amount below is synthetic sample data. Connect your private data
                to enable live operations.
              </div>
            </div>
          )}
          {error && (
            <div className="notice error-notice" role="alert">
              <span>!</span>
              <div>
                {error}
                {data && (
                  <strong>
                    {" "}
                    Showing the last successful snapshot. Agent animations are
                    paused.
                  </strong>
                )}
              </div>
            </div>
          )}
          {login ? (
            <Login onSuccess={() => void refresh()} />
          ) : !data ? (
            <div className="panel connection">
              <span className="eyebrow">
                {busy ? "CONNECTING" : "CONNECTION REQUIRED"}
              </span>
              <h2>
                {busy ? "Opening headquarters…" : "Your data stays private."}
              </h2>
              <p className="muted">
                {busy
                  ? "Preparing your operations snapshot."
                  : "Configure the server environment, or explicitly enable demo mode to explore the sample workspace."}
              </p>
              <button
                className="button"
                disabled={busy}
                onClick={() => void refresh()}
              >
                Retry connection
              </button>
            </div>
          ) : (
            <>
              <div className="metrics">
                <Metric
                  label="Agents at work"
                  value={
                    <>
                      {data.counts.working}
                      <span className="metric-denominator">
                        {" "}
                        / {data.counts.agents}
                      </span>
                    </>
                  }
                  note="Based on fresh execution evidence"
                  tone="#99dfbd"
                />
                <Metric
                  label="Product portfolio"
                  value={
                    data.products.filter(
                      (p) => !["INACTIVE", "UNMAPPED"].includes(p.stage),
                    ).length
                  }
                  note={`${data.products.filter((p) => p.stage === "ETSY DRAFT").length} Etsy drafts · ${data.products.filter((p) => ["PUBLISHED", "SALES"].includes(p.stage)).length} published`}
                />
                <Metric
                  label="AI costs today"
                  value={money(
                    data.finance.windows[0].actual +
                      data.finance.windows[0].estimated,
                  )}
                  note={`Actual ${money(data.finance.windows[0].actual)} · estimated ${money(data.finance.windows[0].estimated)}`}
                />
                <Metric
                  label="Needs attention"
                  value={
                    data.counts.blocked +
                    data.tasks.filter((t) => t.status === "FAILED").length
                  }
                  note={`${data.counts.stalled} potentially stalled tasks`}
                  tone="#edbd77"
                />
              </div>
              <div
                className={`content-grid ${selection ? "has-inspector" : ""}`}
              >
                <div className="main-content">
                  {view === "office" && (
                    <>
                      <section className="panel office-panel">
                        <div className="panel-head">
                          <div>
                            <span className="eyebrow">VIRTUAL OFFICE</span>
                            <h2>
                              Headquarters{" "}
                              <span className="muted small">/ Level 01</span>
                            </h2>
                          </div>
                          <span className="small muted">
                            {departments.length} departments ·{" "}
                            {data.agents.length} agents
                          </span>
                        </div>
                        <Office
                          agents={data.agents}
                          onSelect={(id) => select("agent", id)}
                          selected={
                            selection?.type === "agent"
                              ? selection.id
                              : undefined
                          }
                          stale={stale}
                        />
                        <div className="office-foot">
                          <span>Click a workstation to inspect its agent.</span>
                          <span>
                            Last verified business success{" "}
                            <b>{date(data.lastSuccess)}</b>
                          </span>
                        </div>
                      </section>
                      <div className="two-columns">
                        <section className="panel">
                          <div className="panel-head">
                            <h2>Activity stream</h2>
                            <button
                              className="text-button"
                              onClick={() => changeView("operations")}
                            >
                              View operations ↗
                            </button>
                          </div>
                          <RunRows
                            runs={data.runs.slice(0, 5)}
                            onSelect={(id) => select("run", id)}
                          />
                        </section>
                        <section className="panel">
                          <div className="panel-head">
                            <h2>Attention queue</h2>
                            <span className="eyebrow">BUSINESS SIGNALS</span>
                          </div>
                          <TaskRows
                            tasks={data.tasks
                              .filter(
                                (t) =>
                                  t.stalled ||
                                  ["FAILED", "BLOCKED"].includes(t.status),
                              )
                              .slice(0, 5)}
                            onSelect={(id) => select("task", id)}
                          />
                        </section>
                      </div>
                      <section className="panel">
                        <div className="panel-head">
                          <h2>Production at a glance</h2>
                          <button
                            className="text-button"
                            onClick={() => changeView("pipeline")}
                          >
                            Explore products ↗
                          </button>
                        </div>
                        <div className="pipeline-summary">
                          {stages.slice(0, 7).map((stage, i) => (
                            <button
                              key={stage}
                              onClick={() => {
                                changeView("pipeline");
                                setFilter(stage);
                              }}
                            >
                              <span className="small muted">
                                0{i + 1} / {stage}
                              </span>
                              <strong>
                                {
                                  data.products.filter((p) => p.stage === stage)
                                    .length
                                }
                              </strong>
                              <div
                                className="stage-rule"
                                style={{
                                  background: `hsl(${160 + i * 14} 30% 60%)`,
                                }}
                              />
                            </button>
                          ))}
                        </div>
                      </section>
                    </>
                  )}
                  {view === "operations" && (
                    <>
                      <div className="toolbar">
                        <input
                          aria-label="Search operations"
                          placeholder="Search executions and tasks…"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                        />
                        <select
                          aria-label="Filter business outcome"
                          value={filter}
                          onChange={(e) => setFilter(e.target.value)}
                        >
                          {[
                            "ALL",
                            "SUCCESS",
                            "FAILED",
                            "BLOCKED",
                            "UNKNOWN",
                            "IN PROGRESS",
                          ].map((x) => (
                            <option key={x} value={x}>
                              {x === "ALL" ? "All business outcomes" : x}
                            </option>
                          ))}
                        </select>
                      </div>
                      <section className="panel">
                        <div className="panel-head">
                          <h2>Workflow monitor</h2>
                          <span className="small muted">
                            Workflow status ≠ business outcome
                          </span>
                        </div>
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>Execution / agent</th>
                                <th>Workflow</th>
                                <th>Business</th>
                                <th>Duration</th>
                                <th>Started · Berlin</th>
                              </tr>
                            </thead>
                            <tbody>
                              {data.runs
                                .filter(
                                  (r) =>
                                    matches(r.id, r.agent) &&
                                    (filter === "ALL" || r.business === filter),
                                )
                                .slice(0, 100)
                                .map((r) => (
                                  <tr key={r.id}>
                                    <td>
                                      <button
                                        className="table-link"
                                        onClick={() => select("run", r.id)}
                                      >
                                        {r.id}
                                        <small>
                                          {r.agent.replace("AXXIBOTS_", "")}
                                        </small>
                                      </button>
                                    </td>
                                    <td>
                                      <Badge text={r.status} />
                                    </td>
                                    <td>
                                      <Badge text={r.business} />
                                    </td>
                                    <td>
                                      {r.duration === null
                                        ? "—"
                                        : `${r.duration.toFixed(1)}s`}
                                    </td>
                                    <td className="muted">{date(r.started)}</td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                        </div>
                        <div className="panel-foot">
                          Showing up to 100 recent matching executions. Full
                          loaded history is used for metrics.
                        </div>
                      </section>
                      <section className="panel">
                        <div className="panel-head">
                          <h2>Current work & bottlenecks</h2>
                          <span className="small muted">
                            Running &gt; 1h · queued &gt; 24h = potentially
                            stalled
                          </span>
                        </div>
                        <TaskRows
                          tasks={data.tasks
                            .filter(
                              (t) =>
                                matches(t.title, t.agent) &&
                                [
                                  "PENDING",
                                  "IN_PROGRESS",
                                  "BLOCKED",
                                  "FAILED",
                                ].includes(t.status),
                            )
                            .sort(
                              (a, b) => Number(b.stalled) - Number(a.stalled),
                            )}
                          onSelect={(id) => select("task", id)}
                        />
                      </section>
                    </>
                  )}
                  {view === "pipeline" && (
                    <>
                      <div className="toolbar">
                        <input
                          aria-label="Search products"
                          placeholder="Find a product or idea…"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                        />
                        <select
                          aria-label="Filter pipeline stage"
                          value={filter}
                          onChange={(e) => setFilter(e.target.value)}
                        >
                          <option value="ALL">All stages</option>
                          {stages.map((x) => (
                            <option key={x}>{x}</option>
                          ))}
                        </select>
                      </div>
                      {decisionError && <div className="notice error-notice" role="alert">{decisionError}</div>}
                      {!demo && <p className="small muted">Approve an open proposal to hand it to the existing production pipeline. The agents handle design, checks and Etsy draft creation under current limits. Publishing still requires separate owner approval.</p>}
                      <div className="kanban">
                        {stages
                          .filter((s) => filter === "ALL" || filter === s)
                          .map((stage) => (
                            <section className="kanban-column" key={stage}>
                              <div className="kanban-title">
                                <span>{stage}</span>
                                <b>
                                  {
                                    data.products.filter(
                                      (p) =>
                                        p.stage === stage &&
                                        matches(p.title, p.status),
                                    ).length
                                  }
                                </b>
                              </div>
                              {data.products
                                .filter(
                                  (p) =>
                                    p.stage === stage &&
                                    matches(p.title, p.status),
                                )
                                .map((p) => (
                                  <button
                                    className="product-card"
                                    key={p.id}
                                    onClick={() => select("product", p.id)}
                                  >
                                    <span className="product-icon">
                                      {stage === "ETSY DRAFT"
                                        ? "▧"
                                        : stage === "SALES"
                                          ? "↗"
                                          : "▤"}
                                    </span>
                                    <strong>{p.title}</strong>
                                    <span className="small muted">
                                      {p.status}
                                      {p.ideaStatus && p.ideaStatus !== p.status
                                        ? ` · idea: ${p.ideaStatus}`
                                        : ""}
                                    </span>
                                    {p.blocked && <Badge text="BLOCKED" />}
                                    {!demo && p.ideaId && p.ideaStatus === "IDEA" && !p.decision && (
                                      <span className="small muted">Open proposal — select this card to review; approve below.</span>
                                    )}
                                    <span className="small muted">
                                      Updated {date(p.updated)}
                                    </span>
                                  </button>
                                ))}
                              {!demo && stage === "RESEARCH" && data.products.filter(p => p.stage === stage && p.ideaId && p.ideaStatus === "IDEA" && !p.decision).map(p => (
                                <div key={`decision-${p.ideaId}`} className="product-card" style={{display:"flex",flexDirection:"column",gap:8}}>
                                  <strong>{p.title}</strong>
                                  <span className="small muted">Owner decision required · production only, not publication</span>
                                  <div style={{display:"flex",gap:8}}>
                                    <button className="button" disabled={!!decisionBusy} onClick={() => void decideIdea(p.ideaId,p.title,"APPROVED")}>
                                      {decisionBusy === p.ideaId ? "Saving…" : "Approve & produce draft"}
                                    </button>
                                    <button className="button subtle" disabled={!!decisionBusy} onClick={() => void decideIdea(p.ideaId,p.title,"REJECTED")}>Reject</button>
                                  </div>
                                </div>
                              ))}
                              {!data.products.some(
                                (p) =>
                                  p.stage === stage &&
                                  matches(p.title, p.status),
                              ) && <Empty text="No products here" />}
                            </section>
                          ))}
                      </div>
                      <div className="notice">
                        <span>◇</span>
                        <div>
                          Stages are a display mapping, not database enums.
                          Rejected and archived products stay in Inactive; new
                          statuses appear in Unmapped. History contains recorded
                          events, not a reconstructed transition log.
                        </div>
                      </div>
                    </>
                  )}
                  {view === "finance" && (
                    <>
                      <div className="finance-window-grid">
                        {data.finance.windows.map((w) => (
                          <section className="panel" key={w.days}>
                            <div className="eyebrow">
                              AI API /{" "}
                              {w.days === 1 ? "TODAY" : `${w.days} DAYS`}
                            </div>
                            <div className="finance-total">
                              {money(w.actual + w.estimated)}
                            </div>
                            <dl className="kv">
                              <dt>ACTUAL COST</dt>
                              <dd>{money(w.actual)}</dd>
                              <dt>ESTIMATED COST</dt>
                              <dd>{money(w.estimated)}</dd>
                              <dt>UNKNOWN entries</dt>
                              <dd>{w.unknown}</dd>
                            </dl>
                          </section>
                        ))}
                      </div>
                      <section className="panel">
                        <div className="panel-head">
                          <div>
                            <span className="eyebrow">AI API EXPENSES</span>
                            <h2>30-day cost trend</h2>
                          </div>
                          <div className="chart-legend">
                            <span>
                              <i />
                              Actual
                            </span>
                            <span>
                              <i />
                              Estimated
                            </span>
                          </div>
                        </div>
                        <CostChart trend={data.finance.trend} />
                      </section>
                      <div className="two-columns">
                        <section className="panel">
                          <div className="panel-head">
                            <h2>Business economics</h2>
                            <span className="eyebrow">
                              ALL RECORDED HISTORY
                            </span>
                          </div>
                          <dl className="kv large">
                            <dt>Gross recorded revenue</dt>
                            <dd>{money(data.finance.revenue)}</dd>
                            <dt>Actual operational expenses</dt>
                            <dd>{money(data.finance.actual)}</dd>
                            <dt>Estimated operational expenses</dt>
                            <dd>{money(data.finance.estimated)}</dd>
                            <dt>Unknown expense entries</dt>
                            <dd>{data.finance.unknown}</dd>
                            <dt>Estimated ledger surplus</dt>
                            <dd
                              className={
                                data.finance.profit !== null &&
                                data.finance.profit < 0
                                  ? "negative"
                                  : "positive"
                              }
                            >
                              {money(data.finance.profit)}
                            </dd>
                          </dl>
                          <p className="small muted">
                            Revenue minus recorded actual and estimated
                            expenses. This is not accounting profit: unrecorded
                            fees, taxes, refunds and operating costs may be
                            missing. Sale cost fields are not subtracted twice.
                          </p>
                        </section>
                        <section className="panel">
                          <div className="panel-head">
                            <h2>Cost transparency</h2>
                            <span className="eyebrow">NO ASSUMED BALANCES</span>
                          </div>
                          <dl className="kv">
                            <dt>API credit balance</dt>
                            <dd>UNKNOWN</dd>
                            <dt>Runs without any cost evidence</dt>
                            <dd>{data.finance.unloggedRuns}</dd>
                            <dt>Cost currency</dt>
                            <dd>Recorded EUR</dd>
                            <dt>Day boundary</dt>
                            <dd>Europe/Berlin</dd>
                          </dl>
                          <p className="small muted">
                            Expenses are the canonical ledger. An execution
                            estimate is added only when no AI expense references
                            that run. Estimates are never treated as invoices or
                            remaining API credits.
                          </p>
                        </section>
                      </div>
                      <div className="two-columns">
                        <CostTable
                          title="Cost by agent"
                          rows={data.finance.perAgent}
                          label={(id) =>
                            data.agents.find((a) => a.id === id)?.name ?? id
                          }
                        />
                        <CostTable
                          title="Cost by product"
                          rows={data.finance.perProduct}
                          label={(id) =>
                            data.products.find(
                              (p) => p.id === id || p.ideaId === id,
                            )?.title ?? id
                          }
                        />
                      </div>
                    </>
                  )}
                  {view === "agents" && (
                    <>
                      <div className="toolbar">
                        <input
                          aria-label="Search agents"
                          placeholder="Find an agent or department…"
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                        />
                        <select
                          aria-label="Filter department"
                          value={filter}
                          onChange={(e) => setFilter(e.target.value)}
                        >
                          <option value="ALL">All departments</option>
                          {departments.map((x) => (
                            <option key={x}>{x}</option>
                          ))}
                        </select>
                      </div>
                      <div className="agent-grid">
                        {data.agents
                          .filter(
                            (a) =>
                              matches(a.name, a.role, a.department) &&
                              (filter === "ALL" || a.department === filter),
                          )
                          .map((a) => (
                            <button
                              className="panel agent-card"
                              key={a.id}
                              onClick={() => select("agent", a.id)}
                            >
                              <div className="agent-card-top">
                                <span className="agent-portrait">
                                  {a.name.slice(0, 2).toUpperCase()}
                                </span>
                                <Badge text={a.state} />
                              </div>
                              <div className="eyebrow">{a.department}</div>
                              <h2>{a.name}</h2>
                              <p className="small muted">{a.role}</p>
                              <div className="agent-stats">
                                <div>
                                  <strong>{a.completed}</strong>
                                  <span>tasks completed</span>
                                </div>
                                <div>
                                  <strong>{pct(a.success)}</strong>
                                  <span>business success</span>
                                </div>
                                <div>
                                  <strong>{a.workload}</strong>
                                  <span>current workload</span>
                                </div>
                                <div>
                                  <strong>{pct(a.quality)}</strong>
                                  <span>recorded review pass</span>
                                </div>
                              </div>
                              <div className="agent-card-foot">
                                <span>
                                  {money(a.actualCost)} actual ·{" "}
                                  {money(a.estimatedCost)} est.
                                </span>
                                <span>↗</span>
                              </div>
                            </button>
                          ))}
                      </div>
                      <p className="small muted">
                        Success rate uses business outcomes with confirmed
                        success or failure. Unknown outcomes are excluded, not
                        counted as successes. Quality is only calculated from
                        recorded ACCEPTED / REVISION_REQUESTED / REJECTED task
                        reviews.
                      </p>
                    </>
                  )}
                </div>
                {selection && (
                  <Inspector
                    selection={selection}
                    data={data}
                    close={() => setSelection(null)}
                    select={select}
                  />
                )}
              </div>
            </>
          )}
          <footer>
            <span>
              AXXIBOTS HQ{" "}
              <span className="muted">
                / a clearer view of autonomous work.
              </span>
            </span>
            <span>
              {demo ? "Synthetic demo data" : "Private server-side data"} ·
              Read-only
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
function Login({ onSuccess }: { onSuccess: () => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const fields = new FormData(e.currentTarget);
    try {
      const r = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: fields.get("email"),
          password: fields.get("password"),
        }),
      });
      const b = await r.json();
      if (!r.ok) throw new Error(b.error);
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="panel login-panel">
      <span className="eyebrow">PRIVATE WORKSPACE</span>
      <h2>Welcome to headquarters.</h2>
      <p className="muted">
        Sign in with an existing, authorized Supabase account.
      </p>
      <label>
        Email
        <input name="email" type="email" required autoComplete="username" />
      </label>
      <label>
        Password
        <input
          name="password"
          type="password"
          required
          autoComplete="current-password"
        />
      </label>
      {error && (
        <p className="negative" role="alert">
          {error}
        </p>
      )}
      <button className="button primary" disabled={busy}>
        {busy ? "Signing in…" : "Enter headquarters →"}
      </button>
    </form>
  );
}
function RunRows({
  runs,
  onSelect,
}: {
  runs: Snapshot["runs"];
  onSelect: (id: string) => void;
}) {
  return runs.length ? (
    <div className="rows">
      {runs.map((r) => (
        <button className="event-row" key={r.id} onClick={() => onSelect(r.id)}>
          <span
            className={`event-dot ${r.business.toLowerCase().replaceAll(" ", "-")}`}
          />
          <span className="row-main">
            <strong>
              {r.agent.replace("AXXIBOTS_", "").replaceAll("_", " ")}
            </strong>
            <small>
              {r.id} · {date(r.started)}
            </small>
          </span>
          <Badge text={r.business} />
        </button>
      ))}
    </div>
  ) : (
    <Empty />
  );
}
function TaskRows({
  tasks,
  onSelect,
}: {
  tasks: Snapshot["tasks"];
  onSelect: (id: string) => void;
}) {
  return tasks.length ? (
    <div className="rows">
      {tasks.map((t) => (
        <button className="event-row" key={t.id} onClick={() => onSelect(t.id)}>
          <span className={`event-dot ${t.status.toLowerCase()}`} />
          <span className="row-main">
            <strong>{t.title || t.type}</strong>
            <small>
              {t.agent.replace("AXXIBOTS_", "")} · {t.attempts} attempts
              {t.stalled ? " · potentially stalled" : ""}
            </small>
          </span>
          <Badge text={t.status} />
        </button>
      ))}
    </div>
  ) : (
    <Empty text="No attention items in this snapshot." />
  );
}
function CostChart({ trend }: { trend: Snapshot["finance"]["trend"] }) {
  const max = Math.max(...trend.map((d) => d.actual + d.estimated), 0.01);
  return (
    <div className="cost-chart">
      <svg
        viewBox="0 0 1000 220"
        role="img"
        aria-label="30-day AI expense trend. Solid bars are actual costs; muted bars are estimates."
      >
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line
              x1="55"
              x2="988"
              y1={175 - t * 150}
              y2={175 - t * 150}
              stroke="#2a3949"
              strokeDasharray="4 5"
            />
            <text x="0" y={180 - t * 150} fill="#8495a7" fontSize="11">
              {money(max * t)}
            </text>
          </g>
        ))}
        {trend.map((d, i) => {
          const a = (d.actual / max) * 150,
            e = (d.estimated / max) * 150,
            x = 65 + i * 30.5;
          return (
            <g key={d.day}>
              <rect
                x={x}
                y={175 - a}
                width="17"
                height={a}
                fill="#9dddbf"
                rx="2"
              />
              <rect
                x={x}
                y={175 - a - e}
                width="17"
                height={e}
                fill="#4d8174"
                rx="2"
              />
              <title>{`${d.day}: actual ${money(d.actual)}, estimated ${money(d.estimated)}`}</title>
              {(i % 7 === 0 || i === 29) && (
                <text x={x} y="202" fill="#8495a7" fontSize="11">
                  {d.day.slice(5)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
function CostTable({
  title,
  rows,
  label,
}: {
  title: string;
  rows: Snapshot["finance"]["perAgent"];
  label: (id: string) => string;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <span className="eyebrow">ALL HISTORY</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Actual</th>
              <th>Estimated</th>
              <th>Unknown</th>
            </tr>
          </thead>
          <tbody>
            {rows
              .sort((a, b) => b.actual + b.estimated - (a.actual + a.estimated))
              .map((r) => (
                <tr key={r.id}>
                  <td>{label(r.id)}</td>
                  <td>{money(r.actual)}</td>
                  <td>{money(r.estimated)}</td>
                  <td>{r.unknown}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      {!rows.length && <Empty />}
    </section>
  );
}
function Inspector({
  selection,
  data,
  close,
  select,
}: {
  selection: NonNullable<Selection>;
  data: Snapshot;
  close: () => void;
  select: (type: NonNullable<Selection>["type"], id: string) => void;
}) {
  const a =
      selection.type === "agent"
        ? data.agents.find((a) => a.id === selection.id)
        : null,
    p =
      selection.type === "product"
        ? data.products.find((p) => p.id === selection.id)
        : null,
    r =
      selection.type === "run"
        ? data.runs.find((r) => r.id === selection.id)
        : null,
    t =
      selection.type === "task"
        ? data.tasks.find((t) => t.id === selection.id)
        : null;
  return (
    <aside className="panel inspector" aria-label="Selected record detail">
      <div className="panel-head">
        <span className="eyebrow">
          INSPECTOR / {selection.type.toUpperCase()}
        </span>
        <button
          className="icon-button"
          onClick={close}
          aria-label="Close inspector"
        >
          ×
        </button>
      </div>
      {a ? (
        <>
          <div className="inspector-portrait">
            {a.name.slice(0, 2).toUpperCase()}
          </div>
          <h2>{a.name}</h2>
          <p className="muted small">{a.role}</p>
          <Badge text={a.state} />
          <div className="notice">
            <div>{a.reason}</div>
          </div>
          <dl className="kv">
            <dt>Department</dt>
            <dd>{a.department}</dd>
            <dt>Tasks completed</dt>
            <dd>{a.completed}</dd>
            <dt>Current workload</dt>
            <dd>{a.workload}</dd>
            <dt>Business success</dt>
            <dd>{pct(a.success)}</dd>
            <dt>Known / unknown outcomes</dt>
            <dd>
              {a.knownOutcomes} / {a.unknownOutcomes}
            </dd>
            <dt>Output review pass</dt>
            <dd>
              {pct(a.quality)} ({a.reviewCount} reviews)
            </dd>
            <dt>Actual cost</dt>
            <dd>{money(a.actualCost)}</dd>
            <dt>Estimated cost</dt>
            <dd>{money(a.estimatedCost)}</dd>
            <dt>Last recorded execution</dt>
            <dd>{date(a.lastActivity)}</dd>
          </dl>
          <h3>Recent executions</h3>
          <RunRows
            runs={data.runs.filter((r) => r.agent === a.id).slice(0, 4)}
            onSelect={(id) => select("run", id)}
          />
          <h3>Open workload</h3>
          <TaskRows
            tasks={data.tasks
              .filter(
                (t) =>
                  t.agent === a.id &&
                  ["IN_PROGRESS", "PENDING", "BLOCKED", "FAILED"].includes(
                    t.status,
                  ),
              )
              .slice(0, 8)}
            onSelect={(id) => select("task", id)}
          />
          <code>{a.id}</code>
        </>
      ) : p ? (
        <>
          <h2>{p.title}</h2>
          <Badge text={p.stage} />
          <dl className="kv">
            <dt>Database status</dt>
            <dd>{p.status}</dd>
            <dt>Idea status</dt>
            <dd>{p.ideaStatus || "Unknown"}</dd>
            <dt>Owner decision</dt>
            <dd>{p.decision || "Not recorded"}</dd>
            <dt>Compliance</dt>
            <dd>{p.compliance || "Unknown"}</dd>
            <dt>Created</dt>
            <dd>{date(p.created)}</dd>
            <dt>Updated</dt>
            <dd>{date(p.updated)}</dd>
          </dl>
          {p.listing && (
            <>
              <h3>Etsy record</h3>
              <dl className="kv">
                <dt>State</dt>
                <dd>{p.listing.state}</dd>
                <dt>Create attempts</dt>
                <dd>{p.listing.attempts ?? "Unknown"}</dd>
              </dl>
              {p.listing.error && <pre>{p.listing.error}</pre>}
            </>
          )}
          <h3>Recorded task history</h3>
          <TaskRows
            tasks={[...p.history].sort((a, b) =>
              b.updated.localeCompare(a.updated),
            )}
            onSelect={(id) => select("task", id)}
          />
          <p className="small muted">
            No status transition audit log is assumed. Linked tasks and record
            timestamps are the available history.
          </p>
          <h3>Linked cost</h3>
          {p.costs.length ? (
            p.costs.map((c) => (
              <p key={c.id}>
                {money(c.actual)} actual · {money(c.estimated)} estimated
              </p>
            ))
          ) : (
            <p className="muted">No attributed cost records.</p>
          )}
          <code>{p.id}</code>
        </>
      ) : r ? (
        <>
          <h2>{r.id}</h2>
          <p className="muted small">{r.agent}</p>
          <dl className="kv">
            <dt>Workflow result</dt>
            <dd>
              <Badge text={r.status} />
            </dd>
            <dt>Business outcome</dt>
            <dd>
              <Badge text={r.business} />
            </dd>
            <dt>n8n execution</dt>
            <dd>{r.execution || "Unknown"}</dd>
            <dt>Started</dt>
            <dd>{date(r.started)}</dd>
            <dt>Finished</dt>
            <dd>{date(r.finished)}</dd>
            <dt>Duration</dt>
            <dd>
              {r.duration === null
                ? "Unknown"
                : `${r.duration.toFixed(2)} seconds`}
            </dd>
          </dl>
          {r.business === "UNKNOWN" && (
            <div className="notice">
              No linked completion evidence confirms a business outcome.
            </div>
          )}
          <h3>Error details</h3>
          {r.error ? (
            <pre>{r.error}</pre>
          ) : (
            <p className="muted small">No recorded error.</p>
          )}
          <h3>Linked tasks & retry evidence</h3>
          <TaskRows
            tasks={data.tasks.filter((t) => r.tasks.includes(t.id))}
            onSelect={(id) => select("task", id)}
          />
        </>
      ) : t ? (
        <>
          <h2>{t.title || t.type}</h2>
          <Badge text={t.status} />
          <dl className="kv">
            <dt>Agent</dt>
            <dd>{t.agent}</dd>
            <dt>Type</dt>
            <dd>{t.type}</dd>
            <dt>Attempts / maximum</dt>
            <dd>
              {t.attempts} / {t.maxAttempts ?? "Unknown"}
            </dd>
            <dt>Review</dt>
            <dd>{t.review || "Unknown"}</dd>
            <dt>Created</dt>
            <dd>{date(t.created)}</dd>
            <dt>Updated</dt>
            <dd>{date(t.updated)}</dd>
            <dt>Completed</dt>
            <dd>{date(t.completed)}</dd>
          </dl>
          {t.stalled && (
            <div className="notice">
              Potentially stalled, based on the last update time. This is a
              monitoring heuristic.
            </div>
          )}
          {t.error && (
            <>
              <h3>Error details</h3>
              <pre>{t.error}</pre>
            </>
          )}
          {t.feedback && (
            <>
              <h3>Review feedback</h3>
              <pre>{t.feedback}</pre>
            </>
          )}
          {t.run && (
            <button className="button" onClick={() => select("run", t.run)}>
              Inspect execution ↗
            </button>
          )}
          <code>{t.id}</code>
        </>
      ) : (
        <Empty text="This record is no longer present in the latest snapshot." />
      )}
    </aside>
  );
}
