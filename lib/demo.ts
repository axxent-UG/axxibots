import { buildSnapshot, departments, type Raw } from "./model";
// Entirely synthetic fixtures. No production records, names or business figures are stored here.
export function demoSnapshot() {
  const now = Date.now(),
    ago = (h: number) => new Date(now - h * 3600000).toISOString();
  const names = [
    "CEO",
    "Research Scout",
    "Product Lead",
    "Design Maker",
    "Listing Curator",
    "Finance Analyst",
    "Infrastructure Watch",
  ];
  const ids = [
    "DEMO_CEO",
    "DEMO_RESEARCH",
    "DEMO_PRODUCT",
    "DEMO_DESIGN",
    "DEMO_ETSY",
    "DEMO_FINANCE",
    "DEMO_IT",
  ];
  const raw: Raw = {
    registry: [],
    agents: names.map((name, i) => ({
      id: ids[i],
      name,
      role: departments[i],
      status: i === 6 ? "paused" : "active",
      is_active: i !== 6,
    })),
    runs: [],
    tasks: [],
    ideas: [],
    products: [],
    expenses: [],
    listings: [],
    sales: [],
  };
  const statuses = [
    "IDEA",
    "RESEARCHED",
    "DESIGNING",
    "DESIGNED",
    "DRAFT",
    "PUBLISHED",
    "PUBLISHED",
    "ARCHIVED",
  ];
  const titles = [
    "Botanical desk planner",
    "Weekend adventure cards",
    "Creative journal kit",
    "Family chore chart",
    "Reading club companion",
    "Budget planner",
    "Garden logbook",
    "Archived concept",
  ];
  statuses.forEach((status, i) => {
    raw.ideas.push({
      id: `idea-${i}`,
      title: titles[i],
      status,
      created_at: ago(80),
      updated_at: ago(i),
      owner_decision: i === 2 ? "approved" : null,
    });
    if (i >= 4)
      raw.products.push({
        id: `product-${i}`,
        product_idea_id: `idea-${i}`,
        title: titles[i],
        status,
        created_at: ago(60),
        updated_at: ago(i),
        compliance_status: "PASS",
      });
    if (i >= 4 && i <= 6)
      raw.listings.push({
        id: `listing-${i}`,
        product_id: `product-${i}`,
        title: titles[i],
        etsy_state: i === 4 ? "draft" : "active",
        etsy_create_attempts: 1,
      });
  });
  for (let i = 0; i < 24; i++) {
    const a = i % 6,
      id = `demo-run-${i}`,
      status = i === 0 ? "RUNNING" : i === 1 ? "FAILED" : "SUCCESS";
    raw.runs.push({
      run_id: id,
      agent_id: ids[a],
      status,
      started_at: ago(i === 0 ? 0.01 : i),
      finished_at: i === 0 ? null : ago(i - 0.02),
      updated_at: ago(i === 0 ? 0.005 : i - 0.02),
      n8n_execution_id: `demo-${100 + i}`,
      est_ai_cost_eur: 0.04 + i * 0.005,
    });
    raw.tasks.push({
      id: `demo-task-${i}`,
      title:
        i === 0
          ? "Evaluate a new product niche"
          : i === 1
            ? "Check product quality"
            : `Process ${titles[i % 7]}`,
      task_type: "demo",
      assigned_agent: ids[a],
      status: i === 0 ? "IN_PROGRESS" : i === 1 ? "BLOCKED" : "DONE",
      run_id: id,
      result: { run_id: id },
      attempts: i === 1 ? 2 : 1,
      max_attempts: 3,
      review_status: i % 4 === 0 ? "ACCEPTED" : "NOT_REVIEWED",
      payload: { product_idea_id: `idea-${i % 7}` },
      created_at: ago(i + 1),
      updated_at: ago(i === 0 ? 0.005 : i),
      completed_at: i > 1 ? ago(i) : null,
      last_error:
        i === 1
          ? { message: "Synthetic demo: quality review needs a decision" }
          : null,
    });
    raw.expenses.push({
      id: `demo-expense-${i}`,
      run_id: id,
      category: "ai_api",
      amount_eur: 0.04 + i * 0.005,
      is_estimate: true,
      expense_date: ago(i).slice(0, 10),
      product_idea_id: `idea-${i % 7}`,
    });
  }
  raw.sales.push({
    id: "demo-sale",
    product_id: "product-6",
    listing_id: "listing-6",
    gross_revenue_eur: 12.5,
    order_date: ago(3),
  });
  return buildSnapshot(raw, "DEMO", now);
}
