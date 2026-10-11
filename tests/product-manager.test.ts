import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const code = readFileSync(new URL("../ops/product-manager/decide-path.js", import.meta.url), "utf8");
const decide = (row: Record<string, unknown>) => runInNewContext(
  `(function () { ${code} })()`, { $input: { first: () => ({ json: row }) } },
)[0].json;
const ready = { allowed: true, idea_id: "synthetic-idea", designs: [{ id: "design" }] };

test("new product AI requires explicit available budget", () => {
  assert.equal(decide({ ...ready, ai_spec_allowed: true }).path, "new");
  for (const value of [false, null, undefined, "true"]) {
    const r = decide({ ...ready, ai_spec_allowed: value });
    assert.equal(r.path, "nothing");
    assert.ok(r.block_reasons.includes("ai_spec_budget_reached_or_missing"));
  }
});
test("free repair remains available when AI budget is exhausted", () => {
  assert.equal(decide({ ...ready, repair_product_id: "repair", ai_spec_allowed: false }).path, "repair");
});
test("kill switch and inactive-agent preflight still override repairs", () => {
  const r = decide({ ...ready, allowed: false, repair_product_id: "repair", ai_spec_allowed: true });
  assert.equal(r.path, "nothing");
  assert.ok(r.block_reasons.includes("preflight_blocked"));
});
test("missing passed designs never starts paid work", () => {
  assert.equal(decide({ ...ready, designs: [], ai_spec_allowed: true }).path, "nothing");
});

const validateCode = readFileSync(new URL('../ops/product-manager/validate-spec.js', import.meta.url), 'utf8');
const validate = (usageComplete: boolean) => {
  const spec = { product_title: 'Synthetic shapes', buyer_description: 'Three printable shapes',
    price_eur: 4, readme_text: 'Open the files', license_text: 'Personal use', positioning: 'Synthetic test' };
  const nodes: Record<string, object> = {
    'Decide Path': { run_id: 'test', idea_id: 'synthetic', category: 'digital',
      designs: [{ id: 'd', title: 'Shape', svg_path: 'synthetic.svg' }] },
    'Build Product Request': { printable: false },
    'Write Product Spec': { output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify(spec) }] }],
      usage: { input_tokens: 1232, output_tokens: 1060 } },
  };
  return runInNewContext(`(function () { ${validateCode} })()`, {
    $input: { first: () => ({ json: { usage_complete: usageComplete } }) },
    $: (name: string) => ({ first: () => ({ json: nodes[name] }) }),
  })[0].json;
};
test('validation reads the original model response after the usage node', () => {
  const output = validate(true);
  assert.equal(output.title, 'Synthetic shapes');
  assert.equal(output.spec_cost_eur, 0.0024);
  assert.equal(output.files.items.length, 1);
});
test('unknown usage blocks product creation instead of silently claiming zero cost', () => {
  assert.throws(() => validate(false), /usage missing/);
});
