-- n8n parameters: $1 response envelope with expected_product_id, $2 run_id.
-- Trust the requested identity and persisted artifact, never HTTP 200 alone.
WITH p AS (SELECT $1::jsonb AS d),
verified AS (
  SELECT x.id, x.package_bytes
  FROM axx.products x, p
  WHERE x.id::text = p.d->>'expected_product_id'
    AND x.run_id = $2
    AND p.d->>'status_code' = '200'
    AND p.d->'body'->>'product_id' = x.id::text
    AND NULLIF(x.package_path, '') IS NOT NULL
    AND p.d->'body'->>'package_path' = x.package_path
    AND x.package_bytes > 0
    AND p.d->'body'->>'bytes' = x.package_bytes::text
    AND x.status IN ('DESIGNED', 'COMPLIANCE_REVIEW')
),
advanced AS (
  UPDATE axx.products x SET status = 'COMPLIANCE_REVIEW', updated_at = now()
  FROM verified v WHERE x.id = v.id AND x.status = 'DESIGNED'
  RETURNING x.id, x.package_bytes
),
accepted AS (
  SELECT id, package_bytes FROM advanced
  UNION ALL
  SELECT v.id, v.package_bytes FROM verified v
  JOIN axx.products x ON x.id = v.id WHERE x.status = 'COMPLIANCE_REVIEW'
),
outcome AS (
  SELECT EXISTS (SELECT 1 FROM accepted) AS good,
    p.d->>'expected_product_id' AS product_id,
    jsonb_build_object('phase', 'package',
      'status', CASE WHEN EXISTS (SELECT 1 FROM accepted) THEN 'SUCCESS' ELSE 'FAILED' END,
      'success', EXISTS (SELECT 1 FROM accepted),
      'packaged', EXISTS (SELECT 1 FROM accepted),
      'product_id', p.d->>'expected_product_id',
      'package_bytes', (SELECT package_bytes FROM accepted LIMIT 1),
      'http_status', p.d->'status_code') AS evidence
  FROM p
),
logged AS (
  INSERT INTO axx.audit_logs (actor, action, entity_type, entity_id, run_id, metadata)
  SELECT 'AXXIBOTS_05_PRODUCT_MANAGER',
    CASE WHEN good THEN 'product_packaged' ELSE 'product_package_failed' END,
    'product', product_id, $2, evidence FROM outcome
  WHERE NOT EXISTS (
    SELECT 1 FROM axx.audit_logs a WHERE a.run_id = $2
      AND a.action = CASE WHEN good THEN 'product_packaged' ELSE 'product_package_failed' END
  ) RETURNING id
),
finished AS (
  UPDATE axx.workflow_runs w SET
    status = CASE WHEN o.good THEN 'SUCCESS'::axx.run_status ELSE 'FAILED'::axx.run_status END,
    finished_at = now(), updated_at = now(), output = o.evidence,
    error = CASE WHEN o.good THEN NULL ELSE
      jsonb_build_object('message', 'Package response or persisted artifact failed verification',
        'failure_class', 'package_verification', 'product_id', o.product_id,
        'http_status', o.evidence->'http_status') END
  FROM outcome o WHERE w.run_id = $2 RETURNING w.run_id, w.status
)
SELECT o.product_id, o.good AS packaged,
  (SELECT count(*) FROM advanced) AS handed_to_compliance,
  (SELECT package_bytes FROM accepted LIMIT 1) AS package_bytes,
  (SELECT status FROM finished) AS run_status FROM outcome o;
