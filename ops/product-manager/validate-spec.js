const r = $('Decide Path').first().json;
const b = $('Build Product Request').first().json;
if ($input.first().json.usage_complete !== true) throw new Error('Product spec usage missing; cost cannot be verified');
const res = $('Write Product Spec').first().json;
let text = '';
(res.output || []).forEach(function (o) { if (o.type === 'message') (o.content || []).forEach(function (c) { if (c.type === 'output_text') text += c.text; }); });
const s = JSON.parse(text);
const warnings = [];
const banned = /disney|marvel|pokemon|hello kitty|harry potter|star wars|nike|adidas|coca|barbie|lego|grinch|rudolph|frosty the snowman|play-?tested|best-?selling|award-winning|hand-?drawn|cricut\s*(brand)?\s*official|official/i;
['product_title', 'buyer_description', 'readme_text', 'license_text'].forEach(function (k) { if (banned.test(s[k] || '')) warnings.push('banned_term_in_' + k); });
const res0 = r.research || {};
let lo = Number(res0.price_min_eur), hi = Number(res0.price_max_eur);
const minPrice = Number(r.min_price_eur) || 1.5;
if (!(lo > 0)) lo = minPrice; if (!(hi > 0)) hi = Math.max(lo, 30);
let price = Number(s.price_eur);
// v2: the CEO pricing review in the production brief sets the price; the model cannot change it
const specPrice = r.spec && Number(r.spec.price_eur) > 0 ? Number(r.spec.price_eur) : null;
if (specPrice) { if (Math.abs(price - specPrice) > 0.001) warnings.push('price_set_from_ceo_brief'); price = specPrice; lo = Math.min(lo, specPrice); hi = Math.max(hi, specPrice); }
if (!(price > 0)) { price = lo; warnings.push('price_missing_used_min'); }
if (price < lo) { warnings.push('price_raised_to_research_min'); price = lo; }
if (price > hi) { warnings.push('price_lowered_to_research_max'); price = hi; }
price = Math.max(minPrice, Math.round(price * 100) / 100);
const slug = function (t) { return String(t).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'design'; };
const items = [];
let disclosure;
if (b.printable) {
  const f = r.design_output.files;
  const base = String((r.bundle_plan && r.bundle_plan.title) || r.idea_title).replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '');
  [['a4', 'Print - A4/', 'A4_colour'], ['a4_ink', 'Print - A4/', 'A4_ink-saver'], ['letter', 'Print - US Letter/', 'Letter_colour'], ['letter_ink', 'Print - US Letter/', 'Letter_ink-saver'], ['screen', 'Screen edition/', 'screen-16x9']].forEach(function (o) {
    if (o[0] === 'screen' && !b.has_screen) return;
    if (f[o[0]]) items.push({ bucket: 'axx-designs', path: String(f[o[0]].path).replace(/^axx-designs\//, ''), zip_name: o[1] + base + '_' + o[2] + '.pdf', variant: o[0], pages: f[o[0]].pages });
  });
  const need = b.has_screen ? 5 : 4;
  if (items.length !== need) throw new Error('printable product needs ' + need + ' PDFs, found ' + items.length);
  disclosure = 'Game texts were drafted with the help of AI writing tools, then checked, edited and laid out by our studio.';
} else {
  r.designs.forEach(function (d, i) {
    const base = String(i + 1).padStart(2, '0') + '-' + slug(d.title);
    if (d.svg_path) items.push({ bucket: 'axx-designs', path: d.svg_path, zip_name: 'SVG/' + base + '.svg' });
    if (d.png_path) items.push({ bucket: 'axx-designs', path: d.png_path, zip_name: 'PNG-300dpi/' + base + '.png' });
    if (d.dxf_path) items.push({ bucket: 'axx-designs', path: d.dxf_path, zip_name: 'DXF/' + base + '.dxf' });
  });
  disclosure = 'These designs were created by our studio with the help of AI image tools and then cleaned up, converted into cut-ready vector files and quality-checked by us.';
}
if (items.length === 0) throw new Error('no design files to package');
const d8 = new Date().toISOString().slice(2, 10).replace(/-/g, '');
const sku = 'AXX-' + (b.printable ? 'PRT' : String(r.category).slice(0, 3).toUpperCase()) + '-' + d8 + '-' + String(r.idea_id).slice(0, 4).toUpperCase() + (r.is_test ? '-TEST' : '');
const u = res.usage || {};
const cost = Number(u.input_tokens || 0) * 0.25e-6 + Number(u.output_tokens || 0) * 2e-6;
return [{ json: {
  run_id: r.run_id, idea_id: r.idea_id, is_test: !!r.is_test, category: r.category, sku: sku,
  title: String(s.product_title).slice(0, 80) + (r.is_test ? ' (TEST)' : ''),
  description: String(s.buyer_description).slice(0, 1200), price_eur: price, price_rationale: s.price_rationale, positioning: s.positioning,
  ai_disclosure: disclosure, design_ids: r.designs.map(function (d) { return d.id; }), first_design_id: r.designs[0].id,
  files: { items: items, texts: [ { zip_name: 'README.txt', content: String(s.readme_text).slice(0, 3000) + '\n\n' + disclosure }, { zip_name: 'LICENSE.txt', content: String(s.license_text).slice(0, 2000) } ], facts: b.facts || null },
  cost_breakdown: { ai_cost_design_eur: Number(r.idea_ai_cost_eur) || 0, ai_cost_product_spec_eur: Math.round(cost * 10000) / 10000, production_cost_per_sale_eur: 0, note: 'digital download, no per-sale production cost', price_rationale: s.price_rationale, price_source: specPrice ? 'CEO production brief (pricing review)' : 'model within research range' },
  spec_cost_eur: Math.round(cost * 10000) / 10000, warnings: warnings } }];
