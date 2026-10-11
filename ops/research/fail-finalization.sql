-- $1 = run ID, $2 = bounded error text. Preserve saved findings and their costs.
WITH failed AS (
  UPDATE axx.workflow_runs SET status = 'FAILED', finished_at = now(), updated_at = now(),
    output = coalesce(output, '{}'::jsonb) ||
      jsonb_build_object('postprocessing_complete', false, 'success', false),
    error = jsonb_build_object('message', left($2::text, 500),
      'failure_class', 'research_postprocessing')
  WHERE run_id = $1 AND status = 'RUNNING' RETURNING run_id
)
INSERT INTO axx.audit_logs (actor, action, entity_type, entity_id, run_id, metadata)
SELECT 'AXXIBOTS_02_MARKET_RESEARCH', 'research_postprocessing_failed',
  'workflow', run_id, run_id, jsonb_build_object('error', left($2::text, 500))
FROM failed RETURNING run_id;
