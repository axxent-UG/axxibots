import "server-only";
import { Pool } from "pg";
import { buildSnapshot, type Raw, type Row } from "./model";
let pool: Pool | undefined;
// Explicit projections match axx columns inspected on 11 Oct 2026. No wildcard/private payload export.
export const queries: Record<keyof Raw, string> = {
  registry:
    "select agent_id,name,role,status,est_monthly_cost_eur from axx.agent_registry",
  agents: "select id,name,role,status,is_active from axx.agents",
  runs: "select run_id,agent_id,n8n_execution_id,status,started_at,finished_at,updated_at,est_ai_cost_eur,error,jsonb_build_object('status',output->'status','success',output->'success','errors',output->'errors','output',jsonb_build_object('status',output->'output'->'status','success',output->'output'->'success')) as output from axx.workflow_runs",
  tasks:
    "select id,run_id,assigned_agent,task_type,title,status,attempts,max_attempts,created_at,updated_at,started_at,completed_at,last_error,review_status,review_feedback,jsonb_build_object('run_id',result->'run_id','status',result->'status','success',result->'success','output',jsonb_build_object('status',result->'output'->'status','success',result->'output'->'success')) as result,jsonb_build_object('product_id',payload->'product_id','product_idea_id',payload->'product_idea_id') as payload from axx.tasks",
  ideas:
    "select id,title,status,owner_decision,created_at,updated_at from axx.product_ideas where is_test is not true",
  products:
    "select id,product_idea_id,title,status,compliance_status,created_at,updated_at from axx.products where is_test is not true",
  expenses:
    "select id,expense_date,category,amount_eur,is_estimate,product_id,product_idea_id,run_id,created_at from axx.expenses",
  listings:
    "select id,product_id,title,etsy_state,etsy_create_attempts,last_error from axx.listings where is_test is not true",
  sales:
    "select id,listing_id,product_id,gross_revenue_eur,order_date from axx.sales",
};
export async function liveSnapshot() {
  if (!process.env.DATABASE_URL) throw new Error("Database is not configured");
  // Override URL SSL flags: certificate verification must not silently be disabled by sslmode=require.
  const url = new URL(process.env.DATABASE_URL);
  for (const key of ["sslmode", "sslcert", "sslkey", "sslrootcert"])
    url.searchParams.delete(key);
  pool ??= new Pool({
    connectionString: url.toString(),
    max: 2,
    idleTimeoutMillis: 10000,
    connectionTimeoutMillis: 8000,
    ssl: {
      rejectUnauthorized: true,
      ...(process.env.DATABASE_CA_CERT
        ? { ca: process.env.DATABASE_CA_CERT }
        : {}),
    },
  });
  const client = await pool.connect();
  try {
    await client.query(
      "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
    );
    await client.query("SET LOCAL statement_timeout = '8s'");
    const raw = {} as Raw;
    for (const [key, sql] of Object.entries(queries)) {
      const rows = (await client.query<Row>(`${sql} limit 10001`)).rows;
      if (rows.length > 10000)
        throw new Error(
          "Dataset exceeds the supported snapshot size; totals have not been silently truncated.",
        );
      // pg date parser is host-local by default. Preserve date-only expense dates and ISO timestamps.
      raw[key as keyof Raw] = rows.map((row) =>
        Object.fromEntries(
          Object.entries(row).map(([k, v]) => [
            k,
            v instanceof Date
              ? k === "expense_date"
                ? `${v.getFullYear()}-${String(v.getMonth() + 1).padStart(2, "0")}-${String(v.getDate()).padStart(2, "0")}`
                : v.toISOString()
              : v,
          ]),
        ),
      );
    }
    await client.query("COMMIT");
    return buildSnapshot(raw, "LIVE");
  } catch (e) {
    await client.query("ROLLBACK");
    throw e;
  } finally {
    client.release();
  }
}
