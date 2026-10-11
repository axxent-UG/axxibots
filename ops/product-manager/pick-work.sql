with p as (select * from axx.preflight('AXXIBOTS_05_PRODUCT_MANAGER')),
budget as (-- Embedded in the existing pickup query. No new budget or higher limit.
-- Missing global limits fail closed. Free package repair remains available.
SELECT coalesce((SELECT ai_spend_allowed FROM axx.v_limit_status), false)
  AND coalesce(
    (SELECT coalesce(sum(w.est_ai_cost_eur), 0) FROM axx.workflow_runs w
      WHERE date_trunc('month', w.started_at AT TIME ZONE 'Europe/Berlin') =
        date_trunc('month', now() AT TIME ZONE 'Europe/Berlin'))
    < (SELECT value FROM axx.operating_limits WHERE key = 'max_api_spend_eur_per_month'),
    false) AS ai_spec_allowed
),
run as (
  insert into axx.workflow_runs (run_id, agent_id, n8n_workflow_id, n8n_execution_id, execution_mode, status, input)
  select $1, 'AXXIBOTS_05_PRODUCT_MANAGER', $2, $3, $4, 'RUNNING', '{}'::jsonb from p where p.allowed
  on conflict (run_id) do nothing returning run_id),
-- repair: a product whose package failed, or (v2) a non-test product compliance sent back, at most 3 compliance checks per product
repair as (
  update axx.products set status = case when status = 'DESIGNING' then 'DESIGNED'::axx.product_status else status end,
    compliance_status = case when status = 'DESIGNING' then 'NOT_CHECKED'::axx.compliance_status else compliance_status end,
    package_nonce = gen_random_uuid(), run_id = $1, updated_at = now()
  where id = (select x.id from axx.products x
               where (x.status = 'DESIGNED' and x.package_path is null)
                  or (x.status = 'DESIGNING' and x.compliance_status = 'FAIL' and not coalesce(x.is_test, false)
                      and (select count(*) from axx.audit_logs a where a.entity_id = x.id::text and a.action = 'compliance_checked') < 3)
               order by x.created_at limit 1)
    and exists (select 1 from run)
  returning id, package_nonce),
idea as (
  select i.* from axx.product_ideas i
  where i.status = 'DESIGNED' and not exists (select 1 from axx.products x where x.product_idea_id = i.id and x.status <> 'REJECTED')
  order by i.created_at limit 1),
dz as (
  select d.* from axx.designs d where d.product_idea_id = (select id from idea) and d.status in ('QA_PASSED', 'APPROVED') order by d.version)
select p.allowed, p.reasons, (select ai_spec_allowed from budget) as ai_spec_allowed, $1::text as run_id,
  (select id from repair) as repair_product_id, (select package_nonce::text from repair) as repair_nonce,
  idea.id as idea_id, idea.title as idea_title, idea.category::text as category, idea.concept, idea.target_audience, idea.is_test,
  idea.proposal, idea.bundle_plan, idea.design_output,
  (select row_to_json(r) from (select niche, keywords, price_min_eur, price_max_eur, differentiation, competitive_positioning, target_audience from axx.research where id = idea.research_id) r) as research,
  (select coalesce(jsonb_agg(jsonb_build_object('id', id, 'version', version, 'title', title, 'kind', kind, 'svg_path', svg_path, 'png_path', png_path, 'dxf_path', dxf_path,
      'content', content, 'qa_summary', qa->'scores'->>'summary', 'originality_risk', qa->'scores'->'originality_risk') order by version), '[]'::jsonb) from dz) as designs,
  (select coalesce(sum(amount_eur), 0) from axx.expenses where product_idea_id = idea.id) as idea_ai_cost_eur,
  coalesce((select value from axx.operating_limits where key = 'min_price_eur'), 1.5) as min_price_eur,
  (select t.payload from axx.tasks t where t.assigned_agent = 'AXXIBOTS_03_DESIGN' and t.payload->>'product_idea_id' = idea.id::text and t.status <> 'CANCELLED' order by t.created_at desc limit 1) as spec
from p left join idea on true;
