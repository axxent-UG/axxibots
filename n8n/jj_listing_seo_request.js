const p = $('Pick Kit').first().json.p;
const roots = $input.first().json.results || [];
const flat = [];
(function walk(list, path) { (list || []).forEach(function (n) { const q = path.concat(n.name); if (!n.children || !n.children.length) flat.push({ id: n.id, path: q.join(' > ') }); walk(n.children, q); }); })(roots, []);
const ptype = (p.facts && p.facts.product_type) || 'Ephemera Kit';
const theme = (p.facts && p.facts.theme) || '';
const isParty = (p.facts && p.facts.section === 'Kids Party') || /invitation|welcome sign|banner|cupcake|food label|favor tag|bingo|would you rather/i.test(ptype);
let candidates;
if (isParty) {
  const rankP = function (x) { return /Party Supplies.*Invitation/i.test(x) && /invitation/i.test(ptype) ? 0 : /Party Games/i.test(x) && /bingo|would you rather|game/i.test(ptype) ? 0 : /Party Supplies/i.test(x) ? 1 : /Paper & Party/i.test(x) ? 2 : /Game/i.test(x) ? 3 : 5; };
  candidates = flat.filter(function (n) { return /party|invitation|game|banner|decoration|topper|label|tag/i.test(n.path) && !/^Clothing|^Jewelry|^Pet/i.test(n.path); }).sort(function (a, b) { return rankP(a.path) - rankP(b.path); }).slice(0, 14);
} else {
  const rank = function (x) { return /Scrapbooking Ephemera/i.test(x) ? 0 : /Collage Sheets/i.test(x) ? 1 : /Scrapbook/i.test(x) ? 2 : /Stickers|Labels|Tags/i.test(x) ? 3 : /Paper/i.test(x) ? 4 : 5; };
  candidates = flat.filter(function (n) { return /^Craft Supplies/i.test(n.path) && /collage|scrapbook|paper|sticker|label|tag|journal|ephemera/i.test(n.path); }).sort(function (a, b) { return rank(a.path) - rank(b.path); }).slice(0, 12);
}
if (!candidates.length) throw new Error('no Etsy category candidates');
const TYPES = {
  'illusion pockets': { tags: 'illusion pockets, journal pockets, junk journal pocket', phrase: 'Printable Tuck Ins and Gift Tags' },
  'ephemera kit': { tags: 'ephemera kit, ephemera pack, junk journal supply, collage sheet', phrase: 'Printable Tags, Cards and Fussy Cuts' },
  'mini ephemera kit': { tags: 'mini ephemera kit, ephemera pack, junk journal supply', phrase: 'Printable Tags, Stamps and Fussy Cuts' },
  'fussy cuts': { tags: 'fussy cuts, fussy cut ephemera, printable cut outs', phrase: 'Printable Cut Out Motifs' },
  'gift tags': { tags: 'gift tags, printable tags, journal tags, hang tags', phrase: 'Printable Hang Tags' },
  'word strips': { tags: 'word strips, journal words, sentiment strips, word stickers', phrase: 'Printable Journal Words and Phrases' },
  'pattern paper pack': { tags: 'digital paper, scrapbook paper, pattern paper, background paper', phrase: 'Printable Scrapbook Paper Backgrounds' },
  'postage stamps': { tags: 'faux postage, postage stamps, stamp ephemera', phrase: 'Printable Faux Postage' },
  'journal cards': { tags: 'journal cards, journaling cards, pocket cards', phrase: 'Printable Journaling Cards' },
  'advent numbers': { tags: 'advent numbers, countdown tags, number tags', phrase: 'Printable Countdown Numbers' },
  'bundle': { tags: 'ephemera bundle, junk journal bundle, ephemera pack', phrase: 'Printable Ephemera Bundle' },
  'editable birthday invitation': { tags: 'dinosaur invitation, dino invitation, editable invitation, birthday invitation, kids invitation', phrase: 'Editable Kids Birthday Invite' },
  'editable welcome sign': { tags: 'welcome sign, dinosaur sign, party sign, birthday sign, editable sign', phrase: 'Editable Birthday Welcome Sign' },
  'birthday banner': { tags: 'birthday banner, dinosaur banner, happy birthday banner, party banner', phrase: 'Printable Happy Birthday Banner' },
  'cupcake toppers': { tags: 'cupcake toppers, dinosaur toppers, cake toppers, party circles', phrase: 'Printable Party Circles' },
  'food labels': { tags: 'food labels, food tent cards, buffet labels, party food tags', phrase: 'Printable Food Tent Cards' },
  'favor tags': { tags: 'favor tags, thank you tags, treat bag tags, goodie bag tags', phrase: 'Printable Thank You Tags' },
  'bingo game': { tags: 'dinosaur bingo, picture bingo, kids bingo, party game, preschool game', phrase: 'Printable Party Game for Kids' },
  'would you rather game': { tags: 'would you rather, kids party game, conversation cards, dinosaur game', phrase: 'Printable Party Game for Kids' },
  'party bundle': { tags: 'dinosaur party, dino party bundle, party decorations, birthday printables', phrase: 'Editable Invitation and Decorations' }
};
const TYPE = TYPES[ptype.toLowerCase()] || (/bundle/i.test(ptype) ? TYPES['bundle'] : { tags: 'ephemera pack, junk journal supply', phrase: 'Printable Ephemera' });
const schema = { type: 'object', additionalProperties: false, required: ['title', 'tags', 'description', 'taxonomy_id', 'styles', 'seo_rationale'], properties: { title: { type: 'string' }, tags: { type: 'array', items: { type: 'string' } }, description: { type: 'string' }, taxonomy_id: { type: 'integer' }, styles: { type: 'array', items: { type: 'string' } }, seo_rationale: { type: 'string' } } };
const common_tags = 'tags: 16 distinct buyer search phrases, best first, each at most 20 characters including spaces (count them: longer tags are thrown away, not shortened), lowercase, letters, numbers, spaces, hyphens, apostrophes only. No near-duplicates (singular/plural or reordered words count as duplicates), no single motif words, no trademarks, never only a file format. ';
const common_desc_tail = 'Then WHAT YOU GET (exact counts and approx. sizes from facts), FILES (exactly as in facts.files), PRINTING (print at 100 percent / actual size on matte paper or light cardstock), HOW IT WORKS (digital download right after purchase, nothing is shipped; if facts.how_to_edit or facts.how_it_works exists, explain it plainly in one or two sentences here), LICENCE (from facts), and finally the AI disclosure sentence exactly as given. If facts contain a note, include it plainly. Use only facts given; never invent counts, sizes, bonuses, reviews or sales. Never mention internal checks or tools other than the given AI disclosure. taxonomy_id: best id from candidates. seo_rationale: one sentence. English (US).';
let instructions;
if (isParty) {
  instructions = 'You are the AXXIBOTS Etsy Shop Manager. Write the Etsy listing for ONE printable digital download for a KIDS BIRTHDAY PARTY (the buyer, usually a parent, prints it). Product type: ' + ptype + '. Theme: ' + theme + '. Collection: ' + (p.collection || '') + '. Every title phrase and every tag must describe THIS product and its facts only; never name a piece it does not contain. Never mention junk journals or scrapbooking. If facts.editable_fields exist, the product is EDITABLE in the free Adobe Acrobat Reader: say editable (never Canva, never Corjl, never "instant edit online"). ' +
    'title: 110-140 characters, start with the theme word plus the product type (e.g. "Dinosaur Birthday Invitation", "Dino Party Cupcake Toppers"), then 2-3 comma-separated phrases in Title Case that parents actually type, e.g. "' + TYPE.phrase + '", "Dino Party Decorations", "Boy Birthday Party", "Any Age". Use "Dinosaur" at least once because parents search it. No ALL CAPS, no trademarks (never Jurassic Park, Jurassic World, Land Before Time, Blippi, Bluey, Disney), no emojis. ' +
    common_tags + 'Cover: product type phrases (' + TYPE.tags + '), theme + party intent (dinosaur party, dino birthday, dinosaur birthday, roar party, three rex party), age and audience phrases (boy birthday, toddler birthday, kids party), and printable phrases (party printables, printable decor). ' +
    'styles: exactly 2 Etsy style words, each 1-2 words, letters and spaces only, e.g. Cute, Whimsical, Kawaii, Playful, Colorful. ' +
    'description: plain text, no markdown, with a blank line between every paragraph and section; section headers (PERFECT FOR:, WHAT YOU GET:, FILES:, PRINTING:, HOW IT WORKS:, LICENCE:) each start on their own line and list items start with "- " on their own lines. First paragraph, one or two sentences: a natural sentence that never copies the title, saying what it is, for which party and what is included with real counts. Second short paragraph: the look and the motifs. Then PERFECT FOR: dinosaur birthday parties, kids parties, classroom parties and similar uses that fit. ' + common_desc_tail;
} else {
  instructions = 'You are the AXXIBOTS Etsy Shop Manager. Write the Etsy listing for ONE printable digital download (the buyer prints it). Product type: ' + ptype + '. Theme: ' + theme + '. Collection name: ' + (p.collection || '') + '. It contains pieces FOR junk journals, scrapbooks and cards; it is NOT a journal and NOT a junk journal kit: never call it that. Every title phrase and every tag must describe THIS product and its facts only; never name a product type or piece it does not contain. Examples below show the pattern; write your own wording. ' +
    'SEASON RULE: if the theme or product title names a holiday or season (Halloween, Christmas, Valentine, Easter, Thanksgiving, autumn, winter...), that word must open the title and appear in at least 5 tags, each combined with a buyer intent (e.g. halloween ephemera, halloween journal, printable halloween, halloween scrapbook, halloween + the product type if it fits in 20 characters). Add 2-3 tags for the aesthetic buyers search with this theme (for Halloween e.g. witchy ephemera, gothic ephemera, victorian halloween). ' +
    'title: 110-140 characters, start with the season or theme word plus the product type plus "for Junk Journals" (e.g. "Halloween ' + ptype + ' for Junk Journals"), then 2-3 more comma-separated phrases in Title Case that buyers actually type, each 2-4 words, for this product e.g. "' + TYPE.phrase + '", "Vintage Gothic Ephemera", "Scrapbook Supplies". Never pad with single generic words (printable, vintage, pieces, digital download) and never repeat the product type. The collection name is a brand word: use it at most once and never as the first words. No ALL CAPS, no trademarks, no emojis. ' +
    common_tags + 'Cover: product type phrases for THIS product (' + TYPE.tags + '), season + intent phrases (see SEASON RULE), aesthetic phrases, and use cases (scrapbook supplies, card making supply, junk journal supply). ' +
    'styles: exactly 2 Etsy style words that describe the look, each 1-2 words, letters and spaces only, e.g. Victorian, Gothic, Vintage, Shabby Chic, Cottagecore, Art Nouveau. ' +
    'description: plain text, no markdown, with a blank line between every paragraph and section; section headers (PERFECT FOR:, WHAT YOU GET:, FILES:, PRINTING:, HOW IT WORKS:, LICENCE:) each start on their own line and list items start with "- " on their own lines. First paragraph, one or two sentences (most important, shown by Google): a natural sentence that never starts with or copies the title, saying what it is, for whom and what is included with real counts, containing the main search phrase. Second short paragraph: style and motifs. Then PERFECT FOR: junk journals, scrapbooks, card making, collage and mixed media and seasonal uses where the pieces fit. ' + common_desc_tail;
}
const input = JSON.stringify({ product_title: p.title, product_type: ptype, collection: p.collection, price_eur: p.price_eur, facts: p.facts, downloads: (p.files || []).filter(function (f) { return f.kind === 'download'; }).map(function (f) { return f.name; }), ai_disclosure_exact: p.ai_disclosure, category_candidates: candidates });
return [{ json: { candidates: candidates, request: { model: 'gpt-5-mini', reasoning: { effort: 'low' }, max_output_tokens: 6000, instructions: instructions, input: input, text: { format: { type: 'json_schema', name: 'etsy_listing', strict: true, schema: schema } } } } }];
