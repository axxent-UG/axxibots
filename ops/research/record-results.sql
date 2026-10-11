with s as (
  select
    (select count(*) from axx.research where run_id = $1) as findings_saved,
    (select count(*) from axx.tasks where result->>'run_id' = $1 and status = 'DONE') as tasks_done,
    (select count(*) from axx.agent_memory where related_run_id = $1) as memories_saved,
    (select round(avg(opportunity_score), 2) from axx.research where run_id = $1) as avg_score,
    (select coalesce(sum((result->>'web_search_calls')::int), 0) from axx.tasks where result->>'run_id' = $1) as web_search_calls,
    (select count(*) from axx.research where run_id = $1 and score_breakdown->>'evidence_level' = 'observation') as observation_findings,
    (select coalesce(sum((result->>'est_cost_eur')::numeric), 0) from axx.tasks where result->>'run_id' = $1) as est_cost
)
update axx.workflow_runs w set status = 'RUNNING', finished_at = null, ai_calls = $2::int, est_ai_cost_eur = s.est_cost,
       output = jsonb_build_object('findings_saved', s.findings_saved, 'tasks_done', s.tasks_done, 'memories_saved', s.memories_saved,
                                   'avg_opportunity_score', s.avg_score, 'web_search_calls', s.web_search_calls, 'observation_findings', s.observation_findings,
                                   'est_ai_cost_eur', s.est_cost)
from s where w.run_id = $1
returning w.run_id, w.status, s.tasks_done, s.findings_saved, s.memories_saved, s.avg_score, s.web_search_calls, s.observation_findings, s.est_cost;
