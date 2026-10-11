-- Embedded in the existing pickup query. No new budget or higher limit.
-- Missing global limits fail closed. Free package repair remains available.
SELECT coalesce((SELECT ai_spend_allowed FROM axx.v_limit_status), false)
  AND coalesce(
    (SELECT coalesce(sum(w.est_ai_cost_eur), 0) FROM axx.workflow_runs w
      WHERE date_trunc('month', w.started_at AT TIME ZONE 'Europe/Berlin') =
        date_trunc('month', now() AT TIME ZONE 'Europe/Berlin'))
    < (SELECT value FROM axx.operating_limits WHERE key = 'max_api_spend_eur_per_month'),
    false) AS ai_spec_allowed
