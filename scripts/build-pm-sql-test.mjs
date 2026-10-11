// Generate isolated PostgreSQL regression tests. Only TEMP tables are written.
// Run the output in one connection against a database with the existing axx enums.
import { readFileSync } from 'node:fs';
const root = new URL('../ops/product-manager/', import.meta.url);
const sql = name => readFileSync(new URL(name, root), 'utf8')
  .replaceAll('axx.products', 'pg_temp.test_products')
  .replaceAll('axx.workflow_runs', 'pg_temp.test_runs')
  .replaceAll('axx.audit_logs', 'pg_temp.test_audit')
  .replaceAll('axx.expenses', 'pg_temp.test_expenses');
const quote = s => "'" + String(s).replaceAll("'", "''") + "'";
const pid = '00000000-0000-4000-8000-000000000001';
const other = '00000000-0000-4000-8000-000000000002';
const body = { product_id: pid, package_path: 'synthetic/package.zip', bytes: 123 };
const valid = { expected_product_id: pid, status_code: 200, body };
const assert = (condition, message) => `DO $test$ BEGIN IF NOT (${condition}) THEN RAISE EXCEPTION ${quote(message)}; END IF; END $test$;`;
const out = [`BEGIN;
CREATE TEMP TABLE test_products (id uuid PRIMARY KEY, run_id text, status axx.product_status,
  package_path text, package_bytes bigint, updated_at timestamptz) ON COMMIT DROP;
CREATE TEMP TABLE test_runs (run_id text PRIMARY KEY, status axx.run_status, finished_at timestamptz,
  updated_at timestamptz, output jsonb, error jsonb, ai_calls int DEFAULT 0,
  ai_tokens_in int DEFAULT 0, ai_tokens_out int DEFAULT 0, est_ai_cost_eur numeric DEFAULT 0,
  input jsonb DEFAULT '{}') ON COMMIT DROP;
CREATE TEMP TABLE test_audit (id bigint GENERATED ALWAYS AS IDENTITY, actor text, action text,
  entity_type text, entity_id text, run_id text, metadata jsonb) ON COMMIT DROP;
CREATE TEMP TABLE test_expenses (id bigint GENERATED ALWAYS AS IDENTITY, expense_key text UNIQUE,
  expense_date date, category text, amount_eur numeric, is_estimate boolean, run_id text,
  description text, source text, product_idea_id uuid) ON COMMIT DROP;
PREPARE pm_complete_test(jsonb,text) AS ${sql('complete-package.sql')}
PREPARE pm_usage_test(jsonb,text,uuid) AS ${sql('record-spec-usage.sql')}`];
const cases = [
  ['valid', valid, '', true],
  ['http_failure', { ...valid, status_code: 500 }, '', false],
  ['missing_body', { expected_product_id: pid, status_code: 200 }, '', false],
  ['wrong_product', { ...valid, body: { ...body, product_id: other } }, '', false],
  ['missing_artifact', valid, 'package_path = NULL', false],
  ['empty_artifact', valid, 'package_bytes = 0', false],
  ['wrong_size', { ...valid, body: { ...body, bytes: 124 } }, '', false],
  ['wrong_path', { ...valid, body: { ...body, package_path: 'other.zip' } }, '', false],
  ['wrong_run', valid, "run_id = 'other-run'", false],
  ['wrong_stage', valid, "status = 'APPROVED'", false],
  ['missing_request_identity', { status_code: 200, body }, '', false],
];
for (const [name, payload, mutation, good] of cases) {
  out.push(`TRUNCATE test_products, test_runs, test_audit;
INSERT INTO test_products VALUES (${quote(pid)}, 'test-run', 'DESIGNED', 'synthetic/package.zip', 123, now()),
  (${quote(other)}, 'test-run', 'DESIGNED', 'synthetic/package.zip', 123, now());
INSERT INTO test_runs (run_id,status) VALUES ('test-run','RUNNING');`);
  if (mutation) out.push(`UPDATE test_products SET ${mutation} WHERE id = ${quote(pid)};`);
  out.push(`EXECUTE pm_complete_test(${quote(JSON.stringify(payload))}, 'test-run');`);
  out.push(assert(`(SELECT status::text FROM test_runs) = '${good ? 'SUCCESS' : 'FAILED'}'`, name));
  out.push(assert(`(SELECT status::text FROM test_products WHERE id = '${other}') = 'DESIGNED'`, name + ': unrelated product changed'));
  if (good) {
    out.push(`EXECUTE pm_complete_test(${quote(JSON.stringify(payload))}, 'test-run');`);
    out.push(assert(`(SELECT count(*) FROM test_audit) = 1 AND (SELECT status::text FROM test_runs) = 'SUCCESS'`, 'idempotent replay'));
  } else {
    out.push(assert(`NOT EXISTS (SELECT 1 FROM test_products WHERE status = 'COMPLIANCE_REVIEW')`, name + ': invalid handoff'));
  }
}
out.push(`TRUNCATE test_runs;
INSERT INTO test_runs (run_id,status) VALUES ('usage-run','RUNNING');
EXECUTE pm_usage_test('{"input_tokens":1232,"output_tokens":1060}', 'usage-run', '${pid}');
EXECUTE pm_usage_test('{"input_tokens":1232,"output_tokens":1060}', 'usage-run', '${pid}');`);
out.push(assert(`(SELECT ai_calls = 1 AND ai_tokens_in = 1232 AND ai_tokens_out = 1060 AND est_ai_cost_eur = 0.0024 FROM test_runs)`, 'usage accounting'));
out.push(assert(`(SELECT count(*) FROM test_expenses) = 1`, 'expense deduplication'));
out.push(`INSERT INTO test_runs (run_id,status) VALUES ('unknown-usage','RUNNING');
EXECUTE pm_usage_test('{}', 'unknown-usage', '${pid}');`);
out.push(assert(`(SELECT input->>'spec_usage_complete' = 'false' FROM test_runs WHERE run_id = 'unknown-usage')`, 'unknown usage explicit'));
out.push(`PREPARE research_complete_test(text) AS ${sql('../research/complete-run.sql')}
PREPARE research_failure_test(text,text) AS ${sql('../research/fail-finalization.sql')}
TRUNCATE test_runs, test_audit;
INSERT INTO test_runs(run_id,status,output,est_ai_cost_eur) VALUES
  ('research-ok','RUNNING','{"tasks_done":1}',0.05),
  ('research-empty','RUNNING','{"tasks_done":0}',0.04),
  ('research-broken','RUNNING','{"tasks_done":1}',0.06);
EXECUTE research_complete_test('research-ok');
EXECUTE research_complete_test('research-empty');
EXECUTE research_failure_test('research-broken','Synthetic post-processing failure');`);
out.push(assert(`(SELECT status = 'SUCCESS' AND output->>'postprocessing_complete' = 'true' FROM test_runs WHERE run_id='research-ok')`, 'research completed'));
out.push(assert(`(SELECT status = 'FAILED' AND error->>'failure_class' = 'research_task_completion' FROM test_runs WHERE run_id='research-empty')`, 'research no completed task'));
out.push(assert(`(SELECT status = 'FAILED' AND output->>'postprocessing_complete' = 'false' AND est_ai_cost_eur=0.06 FROM test_runs WHERE run_id='research-broken')`, 'research downstream failure preserves spend'));
out.push(`EXECUTE research_failure_test('research-broken','Synthetic duplicate');
EXECUTE research_complete_test('research-broken');`);
out.push(assert(`(SELECT count(*) FROM test_audit)=1 AND (SELECT status='FAILED' FROM test_runs WHERE run_id='research-broken')`, 'research failure idempotence; no success overwrite'));
out.push(`DEALLOCATE pm_complete_test; DEALLOCATE pm_usage_test;
DEALLOCATE research_complete_test; DEALLOCATE research_failure_test; ROLLBACK;
SELECT 'PASS: 11 package cases, 3 research outcomes, replay protection and usage accounting; all writes rolled back' AS result;`);
process.stdout.write(out.join('\n'));
