const r = $input.first().json;
let path = 'nothing';
const reasons = [].concat(r.reasons || []);
if (!r.allowed) { path = 'nothing'; reasons.push('preflight_blocked'); }
else if (r.repair_product_id) path = 'repair';
else if (r.idea_id && Array.isArray(r.designs) && r.designs.length > 0) {
  if (r.ai_spec_allowed === true) path = 'new';
  else reasons.push('ai_spec_budget_reached_or_missing');
}
else if (r.idea_id) { reasons.push('designed_idea_without_passed_designs'); }
else reasons.push('no_designed_idea_waiting');
return [{ json: { ...r, path, block_reasons: reasons } }];
