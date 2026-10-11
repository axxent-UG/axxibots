-- $1 = response usage ONLY, $2 = run_id, $3 = idea UUID.
-- Retain the existing conservative pricing convention; this is an estimate, not a bill.
WITH p AS (SELECT $1::jsonb AS u), usage AS (
  SELECT CASE WHEN jsonb_typeof(u->'input_tokens') = 'number'
    THEN greatest((u->>'input_tokens')::int, 0) ELSE 0 END AS tokens_in,
    CASE WHEN jsonb_typeof(u->'output_tokens') = 'number'
    THEN greatest((u->>'output_tokens')::int, 0) ELSE 0 END AS tokens_out,
    jsonb_typeof(u->'input_tokens') = 'number' AND
    jsonb_typeof(u->'output_tokens') = 'number' AS complete FROM p
), cost AS (
  SELECT *, round(tokens_in * 0.00000025 + tokens_out * 0.000002, 4) AS eur FROM usage
), expense AS (
  INSERT INTO axx.expenses (expense_key, expense_date, category, amount_eur,
    is_estimate, run_id, description, source, product_idea_id)
  SELECT 'pmspec_' || $2, (now() AT TIME ZONE 'Europe/Berlin')::date, 'ai_api', eur,
    true, $2, 'Product spec (gpt-5-mini)',
    'OpenAI usage tokens x existing estimate (USD treated as EUR)', $3::uuid
  FROM cost WHERE complete
  ON CONFLICT (expense_key) DO NOTHING RETURNING id
), recorded AS (
  UPDATE axx.workflow_runs w SET ai_calls = greatest(w.ai_calls, 1),
    ai_tokens_in = c.tokens_in, ai_tokens_out = c.tokens_out,
    est_ai_cost_eur = greatest(w.est_ai_cost_eur, c.eur), updated_at = now(),
    input = coalesce(w.input, '{}'::jsonb) ||
      jsonb_build_object('spec_usage_complete', coalesce(c.complete, false))
  FROM cost c WHERE w.run_id = $2 RETURNING w.run_id
)
SELECT coalesce(complete, false) AS usage_complete, eur AS spec_cost_eur FROM cost;
