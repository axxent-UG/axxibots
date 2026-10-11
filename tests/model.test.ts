import test from "node:test";
import assert from "node:assert/strict";
import {
  agentState,
  businessOutcome,
  buildSnapshot,
  finance,
  pipelineStage,
  redact,
  type Raw,
} from "../lib/model";
const now = Date.parse("2026-10-11T15:00:00Z");
const empty = (): Raw => ({
  registry: [],
  agents: [],
  runs: [],
  tasks: [],
  ideas: [],
  products: [],
  expenses: [],
  listings: [],
  sales: [],
});
test("n8n SUCCESS does not assert business success without evidence", () =>
  assert.equal(
    businessOutcome({ run_id: "r", status: "SUCCESS" }, []),
    "UNKNOWN",
  ));
test("failed business task overrides technically successful execution, including nested QA failure", () => {
  assert.equal(
    businessOutcome({ run_id: "r", status: "SUCCESS" }, [
      { run_id: "r", status: "FAILED" },
    ]),
    "FAILED",
  );
  assert.equal(
    businessOutcome(
      {
        run_id: "r",
        status: "SUCCESS",
        output: { output: { status: "QA_FAILED" } },
      },
      [],
    ),
    "FAILED",
  );
});
test("confirmed task completion and blocked outcomes", () => {
  assert.equal(
    businessOutcome({ run_id: "r", status: "SUCCESS" }, [
      { result: { run_id: "r" }, status: "DONE" },
    ]),
    "SUCCESS",
  );
  assert.equal(
    businessOutcome({ run_id: "r", status: "SUCCESS" }, [
      { last_error: { run_id: "r" }, status: "BLOCKED" },
    ]),
    "BLOCKED",
  );
});
test("active registry is IDLE without execution evidence; disabled agent is OFFLINE", () => {
  assert.equal(agentState({ status: "active" }, [], [], now).state, "IDLE");
  assert.equal(
    agentState(
      { status: "paused" },
      [],
      [{ status: "RUNNING", updated_at: new Date(now).toISOString() }],
      now,
    ).state,
    "OFFLINE",
  );
});
test("fresh work animates; stale RUNNING is blocked rather than falsely working", () => {
  assert.equal(
    agentState(
      { status: "active" },
      [],
      [{ status: "RUNNING", updated_at: new Date(now - 1000).toISOString() }],
      now,
    ).state,
    "WORKING",
  );
  assert.equal(
    agentState(
      { status: "active" },
      [],
      [
        {
          status: "RUNNING",
          updated_at: new Date(now - 7200000).toISOString(),
        },
      ],
      now,
    ).state,
    "BLOCKED",
  );
});
test("pipeline respects database statuses, listings and sales; unfamiliar states remain unmapped", () => {
  assert.equal(pipelineStage("IDEA", "", "", false), "RESEARCH");
  assert.equal(pipelineStage("RESEARCHED", "", "", false), "APPROVAL");
  assert.equal(pipelineStage("APPROVED", "", "", false), "DESIGN");
  assert.equal(
    pipelineStage("COMPLIANCE_REVIEW", "", "", false),
    "QUALITY CONTROL",
  );
  assert.equal(pipelineStage("DRAFT", "", "draft", false), "ETSY DRAFT");
  assert.equal(pipelineStage("DRAFT", "", "active", false), "PUBLISHED");
  assert.equal(pipelineStage("PUBLISHED", "", "active", true), "SALES");
  assert.equal(pipelineStage("ARCHIVED", "", "active", true), "INACTIVE");
  assert.equal(pipelineStage("NEW_STATUS", "", "", false), "UNMAPPED");
});
test("materialized product and idea counted once, task history correctly joined", () => {
  const r = empty();
  r.ideas = [{ id: "i", title: "Idea", status: "APPROVED" }];
  r.products = [
    { id: "p", product_idea_id: "i", title: "Product", status: "DRAFT" },
  ];
  r.tasks = [{ id: "t", payload: { product_idea_id: "i" }, status: "DONE" }];
  const s = buildSnapshot(r, "LIVE", now);
  assert.equal(s.products.length, 1);
  assert.equal(s.products[0].title, "Product");
  assert.equal(s.products[0].history.length, 1);
});
test("ledger/run estimate deduplication preserves actual vs estimated totals", () => {
  const r = empty();
  r.runs = [
    {
      run_id: "r1",
      agent_id: "a",
      started_at: new Date(now).toISOString(),
      est_ai_cost_eur: 5,
    },
    {
      run_id: "r2",
      agent_id: "a",
      started_at: new Date(now).toISOString(),
      est_ai_cost_eur: 2,
    },
  ];
  r.expenses = [
    {
      run_id: "r1",
      category: "ai_api",
      expense_date: "2026-10-11",
      amount_eur: 3,
      is_estimate: false,
    },
  ];
  const f = finance(r, now);
  assert.equal(f.windows[0].actual, 3);
  assert.equal(f.windows[0].estimated, 2);
  assert.equal(f.actual + f.estimated, 5);
  assert.equal(f.perAgent[0].actual, 3);
});
test("null amounts and unknown basis never turn into known profit; sale fields not double-counted", () => {
  const r = empty();
  r.expenses = [
    {
      category: "ai_api",
      expense_date: "2026-10-11",
      amount_eur: null,
      is_estimate: false,
    },
  ];
  assert.equal(finance(r, now).profit, null);
  assert.equal(finance(r, now).unknown, 1);
  r.expenses = [
    {
      category: "software",
      amount_eur: 4,
      is_estimate: false,
      expense_date: "2026-10-11",
    },
  ];
  r.sales = [{ gross_revenue_eur: 20, etsy_fees_eur: 4 }];
  assert.equal(finance(r, now).profit, 16);
});
test("financial windows use Berlin calendar days and exclude future ledger dates", () => {
  const r = empty();
  r.expenses = [
    {
      category: "ai_api",
      amount_eur: 1,
      is_estimate: true,
      expense_date: "2026-10-12",
    },
    {
      category: "ai_api",
      amount_eur: 2,
      is_estimate: true,
      expense_date: "2026-10-11",
    },
  ];
  const f = finance(r, Date.parse("2026-10-11T22:30:00Z"));
  assert.equal(f.windows[0].estimated, 1);
  assert.equal(f.windows[1].estimated, 3);
});
test("cost trends do not repeat a calendar day across autumn DST transition", () => {
  const f = finance(empty(), Date.parse("2026-11-01T23:15:00Z"));
  assert.equal(new Set(f.trend.map((d) => d.day)).size, 30);
});
test("error projections redact secret keys, bearer tokens and connection URLs", () => {
  const s = redact({
    api_key: "not-public",
    nested: { password: "private" },
    message: "Bearer abcd https://example.com?secret=abc sk-abcd12345",
  });
  assert.ok(!s.includes("not-public"));
  assert.ok(!s.includes("private"));
  assert.ok(!s.includes("abcd"));
  assert.ok(!s.includes("example.com"));
});
test("quality uses the inspected ACCEPTED, REVISION_REQUESTED and REJECTED review constraint", () => {
  const r = empty();
  r.agents = [{ id: "a", name: "Agent", status: "active" }];
  r.tasks = [
    { assigned_agent: "a", status: "DONE", review_status: "ACCEPTED" },
    {
      assigned_agent: "a",
      status: "DONE",
      review_status: "REVISION_REQUESTED",
    },
    { assigned_agent: "a", status: "DONE", review_status: "REJECTED" },
    { assigned_agent: "a", status: "DONE", review_status: "NOT_REVIEWED" },
  ];
  const a = buildSnapshot(r, "LIVE", now).agents[0];
  assert.equal(a.reviewCount, 3);
  assert.equal(a.quality, 33);
});
