export type Row = Record<string, unknown>;
export type State = "WORKING" | "IDLE" | "BLOCKED" | "ERROR" | "OFFLINE";
export const departments = [
  "CEO / Management",
  "Market Research",
  "Product Management",
  "Design Studio",
  "Etsy Operations",
  "Finance",
  "IT / Infrastructure",
] as const;
export const stages = [
  "RESEARCH",
  "APPROVAL",
  "DESIGN",
  "QUALITY CONTROL",
  "ETSY DRAFT",
  "PUBLISHED",
  "SALES",
  "INACTIVE",
  "UNMAPPED",
] as const;
export type Raw = {
  registry: Row[];
  agents: Row[];
  runs: Row[];
  tasks: Row[];
  ideas: Row[];
  products: Row[];
  expenses: Row[];
  listings: Row[];
  sales: Row[];
};
export const str = (v: unknown) => (typeof v === "string" ? v : "");
export const obj = (v: unknown): Row =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Row) : {};
export const num = (v: unknown): number | null =>
  v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v))
    ? Number(v)
    : null;
const ms = (v: unknown) => Date.parse(str(v)) || 0;
export function redact(v: unknown): string {
  const clean = (x: unknown): unknown =>
    Array.isArray(x)
      ? x.map(clean)
      : x && typeof x === "object"
        ? Object.fromEntries(
            Object.entries(x).map(([k, a]) => [
              k,
              /token|secret|password|authorization|api.?key|cookie/i.test(k)
                ? "[REDACTED]"
                : clean(a),
            ]),
          )
        : typeof x === "string"
          ? x
              .replace(
                /(?:postgres(?:ql)?:\/\/|https?:\/\/)[^\s"']+/gi,
                "[URL REDACTED]",
              )
              .replace(
                /(?:Bearer\s+\S+|sb_secret_\S+|sk-[\w-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+)/gi,
                "[REDACTED]",
              )
          : x;
  return (
    typeof v === "string" ? str(clean(v)) : (JSON.stringify(clean(v)) ?? "")
  ).slice(0, 2500);
}
const activeTask = (t: Row) =>
  ["PENDING", "IN_PROGRESS", "BLOCKED"].includes(str(t.status));
export function linkedTasks(run: Row, tasks: Row[]) {
  return tasks.filter(
    (t) =>
      t.run_id === run.run_id ||
      obj(t.result).run_id === run.run_id ||
      obj(t.last_error).run_id === run.run_id,
  );
}
export function businessOutcome(run: Row, tasks: Row[]) {
  const linked = linkedTasks(run, tasks),
    out = obj(run.output),
    nested = obj(out.output);
  const bad = (o: Row) =>
    o.success === false ||
    /FAILED|FAIL|ERROR|QA_FAILED/.test(str(o.status)) ||
    (Array.isArray(o.errors) && o.errors.length > 0);
  if (
    linked.some(
      (t) =>
        t.status === "FAILED" ||
        bad(obj(t.result)) ||
        bad(obj(obj(t.result).output)),
    ) ||
    bad(out) ||
    bad(nested)
  )
    return "FAILED";
  if (linked.some((t) => t.status === "BLOCKED") || out.status === "BLOCKED")
    return "BLOCKED";
  if (
    run.status === "RUNNING" ||
    linked.some((t) => t.status === "IN_PROGRESS")
  )
    return "IN PROGRESS";
  if (run.status === "FAILED" || run.status === "STOPPED_LIMIT")
    return "FAILED";
  if (linked.length && linked.every((t) => t.status === "DONE"))
    return "SUCCESS";
  // Successful transport or unlinked aggregate counters are not proof of business completion.
  return "UNKNOWN";
}
export function agentState(
  agent: Row,
  tasks: Row[],
  runs: Row[],
  now: number,
): { state: State; reason: string } {
  if (
    agent.is_active === false ||
    ["planned", "paused", "retired"].includes(str(agent.status))
  )
    return {
      state: "OFFLINE",
      reason: `Registry: ${str(agent.status) || "inactive"}`,
    };
  const stale = (v: unknown) => now - ms(v) > 60 * 60 * 1000;
  if (
    tasks.some(
      (t) => t.status === "IN_PROGRESS" && !stale(t.updated_at || t.started_at),
    ) ||
    runs.some(
      (r) => r.status === "RUNNING" && !stale(r.updated_at || r.started_at),
    )
  )
    return {
      state: "WORKING",
      reason: "Fresh in-progress task or RUNNING execution (within 60 min)",
    };
  if (tasks.some((t) => t.status === "BLOCKED"))
    return { state: "BLOCKED", reason: "An assigned task has status BLOCKED" };
  if (tasks.some((t) => t.status === "FAILED"))
    return {
      state: "ERROR",
      reason:
        "An assigned task remains FAILED; inspect before treating as resolved",
    };
  if (
    tasks.some((t) => t.status === "IN_PROGRESS") ||
    runs.some((r) => r.status === "RUNNING")
  )
    return {
      state: "BLOCKED",
      reason: "In-progress evidence is over 60 min old; potentially stalled",
    };
  const latest = [...runs].sort(
    (a, b) => ms(b.started_at) - ms(a.started_at),
  )[0];
  if (latest && businessOutcome(latest, tasks) === "FAILED")
    return { state: "ERROR", reason: "Latest recorded execution failed" };
  return {
    state: "IDLE",
    reason:
      "No current execution evidence. This is not a heartbeat or connectivity check.",
  };
}
export function department(id: string) {
  if (/CEO|DAILY_REPORT|APPROVAL/.test(id)) return departments[0];
  if (/RESEARCH|TREND/.test(id)) return departments[1];
  if (/PRODUCT|COMPLIANCE/.test(id)) return departments[2];
  if (/DESIGN/.test(id)) return departments[3];
  if (/ETSY/.test(id)) return departments[4];
  if (/ANALYTICS|FINANCE/.test(id)) return departments[5];
  return departments[6];
}
export function pipelineStage(
  status: string,
  decision: string,
  listing: string,
  hasSales: boolean,
): (typeof stages)[number] {
  if (["ARCHIVED", "REJECTED"].includes(status)) return "INACTIVE";
  if (hasSales) return "SALES";
  if (listing === "active" || status === "PUBLISHED") return "PUBLISHED";
  if (listing === "draft" || status === "DRAFT") return "ETSY DRAFT";
  if (status === "AWAITING_APPROVAL" || decision === "pending")
    return "APPROVAL";
  if (status === "DESIGNING" || status === "APPROVED") return "DESIGN";
  if (["DESIGNED", "COMPLIANCE_REVIEW"].includes(status))
    return "QUALITY CONTROL";
  if (status === "RESEARCHED")
    return decision === "approved" ? "DESIGN" : "APPROVAL";
  if (status === "IDEA") return decision === "approved" ? "DESIGN" : "RESEARCH";
  return "UNMAPPED";
}
function berlinDay(date: number) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}
export function finance(raw: Raw, now: number) {
  // Expense ledger is canonical. Run estimates are fallback only when no expense references that run.
  const ledger = raw.expenses.map((e) => ({
    ...e,
    category: str(e.category),
    product_id: str(e.product_id),
    product_idea_id: str(e.product_idea_id),
    date: str(e.expense_date) || berlinDay(ms(e.created_at)),
    amount: num(e.amount_eur),
    basis:
      e.is_estimate === true
        ? "ESTIMATED COST"
        : e.is_estimate === false
          ? "ACTUAL COST"
          : "UNKNOWN",
    agent: str(raw.runs.find((r) => r.run_id === e.run_id)?.agent_id),
  }));
  const seen = new Set(
    raw.expenses
      .filter((e) => e.category === "ai_api")
      .map((e) => str(e.run_id))
      .filter(Boolean),
  );
  const fallback = raw.runs
    .filter((r) => !seen.has(str(r.run_id)) && num(r.est_ai_cost_eur) !== null)
    .map((r) => ({
      date: berlinDay(ms(r.started_at)),
      amount: num(r.est_ai_cost_eur),
      basis: "ESTIMATED COST",
      agent: str(r.agent_id),
      category: "ai_api",
      product_id: null,
      product_idea_id: null,
    }));
  const entries = [...ledger, ...fallback];
  const end = berlinDay(now);
  const calendarDay = (offset: number) => {
    const d = new Date(end + "T12:00:00Z");
    d.setUTCDate(d.getUTCDate() - offset);
    return d.toISOString().slice(0, 10);
  };
  const start = (days: number) => calendarDay(days - 1);
  const sum = (es: typeof entries, basis: string) =>
    es
      .filter((e) => e.basis === basis)
      .reduce((a, e) => a + (e.amount ?? 0), 0);
  const windows = [1, 7, 30].map((days) => {
    const es = entries.filter(
      (e) => e.category === "ai_api" && e.date >= start(days) && e.date <= end,
    );
    return {
      days,
      actual: sum(es, "ACTUAL COST"),
      estimated: sum(es, "ESTIMATED COST"),
      unknown: es.filter((e) => e.basis === "UNKNOWN" || e.amount === null)
        .length,
    };
  });
  const grouped = (key: "agent" | "product") =>
    Object.entries(
      entries.reduce<Record<string, typeof entries>>((acc, e) => {
        const k =
          key === "agent"
            ? e.agent
            : str(e.product_id) || str(e.product_idea_id);
        (acc[k || "Unattributed"] ??= []).push(e);
        return acc;
      }, {}),
    ).map(([id, es]) => ({
      id,
      actual: sum(es, "ACTUAL COST"),
      estimated: sum(es, "ESTIMATED COST"),
      unknown: es.filter((e) => e.basis === "UNKNOWN" || e.amount === null)
        .length,
    }));
  const revenue = raw.sales.reduce(
    (a, s) => a + (num(s.gross_revenue_eur) ?? 0),
    0,
  );
  const unknownSales = raw.sales.some((s) => num(s.gross_revenue_eur) === null);
  // Expenses are subtracted once. Sale cost fields are NOT subtracted again (possible ledger overlap).
  const actual = sum(entries, "ACTUAL COST"),
    estimated = sum(entries, "ESTIMATED COST");
  return {
    windows,
    actual,
    estimated,
    unknown: entries.filter((e) => e.basis === "UNKNOWN" || e.amount === null)
      .length,
    revenue: unknownSales ? null : revenue,
    profit:
      unknownSales ||
      entries.some((e) => e.basis === "UNKNOWN" || e.amount === null)
        ? null
        : revenue - actual - estimated,
    perAgent: grouped("agent"),
    perProduct: grouped("product"),
    trend: Array.from({ length: 30 }, (_, i) => {
      const day = calendarDay(29 - i);
      const es = entries.filter(
        (e) => e.category === "ai_api" && e.date === day,
      );
      return {
        day,
        actual: sum(es, "ACTUAL COST"),
        estimated: sum(es, "ESTIMATED COST"),
      };
    }),
    unloggedRuns: raw.runs.filter(
      (r) => !seen.has(str(r.run_id)) && num(r.est_ai_cost_eur) === null,
    ).length,
  };
}
export function buildSnapshot(
  raw: Raw,
  mode: "LIVE" | "DEMO",
  now = Date.now(),
) {
  const allAgents = new Map(raw.agents.map((a) => [str(a.id), a]));
  raw.registry.forEach((a) =>
    allAgents.set(str(a.agent_id), {
      ...allAgents.get(str(a.agent_id)),
      ...a,
      id: a.agent_id,
    }),
  );
  const runViews = [...raw.runs]
    .sort((a, b) => ms(b.started_at) - ms(a.started_at))
    .map((r) => ({
      id: str(r.run_id),
      agent: str(r.agent_id),
      execution: str(r.n8n_execution_id),
      status: str(r.status),
      business: businessOutcome(r, raw.tasks),
      started: str(r.started_at),
      finished: str(r.finished_at),
      duration: r.finished_at
        ? Math.max(0, (ms(r.finished_at) - ms(r.started_at)) / 1000)
        : null,
      error: r.error
        ? redact(r.error)
        : linkedTasks(r, raw.tasks)
            .filter((t) => t.last_error)
            .map((t) => redact(t.last_error))
            .join("\n"),
      tasks: linkedTasks(r, raw.tasks).map((t) => str(t.id)),
    }));
  const taskViews = raw.tasks.map((t) => ({
    id: str(t.id),
    title: str(t.title),
    agent: str(t.assigned_agent),
    status: str(t.status),
    type: str(t.task_type),
    run: str(obj(t.result).run_id) || str(t.run_id),
    attempts: num(t.attempts) ?? 0,
    maxAttempts: num(t.max_attempts),
    created: str(t.created_at),
    updated: str(t.updated_at),
    completed: str(t.completed_at),
    review: str(t.review_status),
    feedback: redact(t.review_feedback),
    error: t.last_error ? redact(t.last_error) : "",
    product:
      str(obj(t.payload).product_idea_id) || str(obj(t.payload).product_id),
    stalled:
      activeTask(t) &&
      now - ms(t.updated_at) >
        (t.status === "IN_PROGRESS" ? 60 : 24 * 60) * 60 * 1000,
  }));
  const f = finance(raw, now);
  const agents = [...allAgents.entries()].map(([id, a]) => {
    const tasks = raw.tasks.filter((t) => t.assigned_agent === id),
      runs = raw.runs.filter((r) => r.agent_id === id),
      outcomes = runs.map((r) => businessOutcome(r, raw.tasks));
    const known = outcomes.filter((o) => o === "SUCCESS" || o === "FAILED");
    const costs = f.perAgent.find((c) => c.id === id);
    const reviews = tasks.filter((t) =>
      ["ACCEPTED", "REVISION_REQUESTED", "REJECTED"].includes(
        str(t.review_status),
      ),
    );
    return {
      id,
      name: str(a.name) || id,
      role: str(a.role),
      department: department(id),
      ...agentState(a, tasks, runs, now),
      completed: tasks.filter((t) => t.status === "DONE").length,
      workload: tasks.filter(activeTask).length,
      success: known.length
        ? Math.round(
            (100 * known.filter((o) => o === "SUCCESS").length) / known.length,
          )
        : null,
      knownOutcomes: known.length,
      unknownOutcomes: outcomes.filter((o) => o === "UNKNOWN").length,
      quality: reviews.length
        ? Math.round(
            (100 *
              reviews.filter((t) => t.review_status === "ACCEPTED").length) /
              reviews.length,
          )
        : null,
      reviewCount: reviews.length,
      lastActivity: runs.reduce(
        (latest, r) =>
          ms(r.started_at) > ms(latest) ? str(r.started_at) : latest,
        "",
      ),
      actualCost: costs?.actual ?? 0,
      estimatedCost: costs?.estimated ?? 0,
      monthlyEstimate: num(a.est_monthly_cost_eur),
    };
  });
  const ideas = new Map(raw.ideas.map((p) => [str(p.id), p]));
  const productViews = raw.products.map((p) => ({
    idea: ideas.get(str(p.product_idea_id)),
    product: p,
  }));
  const materialized = new Set(raw.products.map((p) => str(p.product_idea_id)));
  raw.ideas
    .filter((p) => !materialized.has(str(p.id)))
    .forEach((idea) => productViews.push({ idea, product: {} }));
  const products = productViews.map(({ idea: maybe, product: p }) => {
    const idea = maybe ?? {},
      id = str(p.id) || str(idea.id);
    const listing = raw.listings.find((l) => l.product_id === p.id),
      sale = raw.sales.some((s) => s.product_id === p.id);
    const status = str(p.status) || str(idea.status),
      history = taskViews.filter(
        (t) => t.product === id || t.product === idea.id,
      );
    return {
      id,
      ideaId: str(idea.id),
      title: str(p.title) || str(idea.title),
      status,
      ideaStatus: str(idea.status),
      decision: str(idea.owner_decision),
      stage: pipelineStage(
        status,
        str(idea.owner_decision),
        str(listing?.etsy_state),
        sale,
      ),
      created: str(p.created_at) || str(idea.created_at),
      updated: str(p.updated_at) || str(idea.updated_at),
      listing: listing
        ? {
            id: str(listing.id),
            state: str(listing.etsy_state),
            title: str(listing.title),
            attempts: num(listing.etsy_create_attempts),
            error: listing.last_error ? redact(listing.last_error) : "",
          }
        : null,
      history,
      compliance: str(p.compliance_status),
      blocked: history.some(
        (t) => t.status === "BLOCKED" || t.status === "FAILED",
      ),
      costs: f.perProduct.filter((c) => c.id === id || c.id === idea.id),
    };
  });
  return {
    mode,
    at: new Date(now).toISOString(),
    agents,
    runs: runViews,
    tasks: taskViews,
    products,
    finance: f,
    counts: {
      agents: agents.length,
      working: agents.filter((a) => a.state === "WORKING").length,
      blocked: taskViews.filter((t) => t.status === "BLOCKED").length,
      failed: runViews.filter((r) => r.business === "FAILED").length,
      stalled: taskViews.filter((t) => t.stalled).length,
    },
    lastSuccess:
      runViews.find((r) => r.business === "SUCCESS")?.finished ?? null,
  };
}
export type Snapshot = ReturnType<typeof buildSnapshot>;
