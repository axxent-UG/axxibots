-- $1 = run ID. Called only AFTER discovery promotion, scoring and qualification.
UPDATE axx.workflow_runs SET
  status = CASE WHEN coalesce((output->>'tasks_done')::int, 0) > 0
    THEN 'SUCCESS'::axx.run_status ELSE 'FAILED'::axx.run_status END,
  finished_at = now(), updated_at = now(),
  output = coalesce(output, '{}'::jsonb) || jsonb_build_object(
    'postprocessing_complete', true,
    'success', coalesce((output->>'tasks_done')::int, 0) > 0),
  error = CASE WHEN coalesce((output->>'tasks_done')::int, 0) > 0 THEN NULL
    ELSE jsonb_build_object('message', 'No claimed research task completed',
      'failure_class', 'research_task_completion') END
WHERE run_id = $1 AND status = 'RUNNING'
RETURNING run_id, status;
