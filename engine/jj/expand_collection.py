#!/usr/bin/env python3
"""Split-and-bundle step, part 1: add every single-type product a collection's EXISTING art supports.

Owner plan 25.10.2026: visibility comes from many different listings, so each collection should yield
10-15 listings without new illustrations. This script reads a collection recipe (build_products.py
format), finds product types it does not have yet, and appends them. It never adds near-duplicates:
one product per type, and a type is only added when the art and texts are there for it.

Usage: expand_collection.py <collection.json> [--write] [--holiday christmas|halloween|none]
Without --write it prints the products it would add. Prices follow the shop ladder below.
"""
import copy, json, sys

# product type -> recipe. pages(c) returns page specs or None when the collection can't support it.
PIECES = {"tags": 6, "cards": 4, "journal": 6, "stamps": 20, "fussy": 9, "advent": 25, "pattern": 1}


def _words(c, n):
    w = c.get("words") or []
    return w[:n] if len(w) >= n else None


TYPES = {
    "fussy-cuts": dict(product_type="Fussy Cuts", price=2.49, section="Fussy Cuts", badge="Fussy Cuts · Printable",
                       need=lambda c: len(c["motifs"]) >= 16,
                       pages=lambda c: [{"type": "fussy", "off": 0, "name": "fussy_cuts_1"}, {"type": "fussy", "off": 9, "name": "fussy_cuts_2"}],
                       contents=lambda c: {"fussy_cuts": 18, "different_motifs": min(18, len(c["motifs"]))},
                       size="each motif up to approx. 2.5 x 3.2 in on US Letter, with a white cutting border"),
    "gift-tags": dict(product_type="Gift Tags", price=2.19, section="Tags & Labels", badge="Gift Tags · Printable",
                      need=lambda c: len(c["motifs"]) >= 12 and len(c.get("words") or []) >= 12,
                      pages=lambda c: [{"type": "tags", "off": 0, "name": "tags_1", "words": c["words"][:6]},
                                       {"type": "tags", "off": 6, "name": "tags_2", "words": c["words"][6:12]}],
                      contents=lambda c: {"gift_tags": 12}, size="approx. 2.4 x 4.8 in each on US Letter"),
    "stamps": dict(product_type="Postage Stamps", price=2.19, section="Tags & Labels", badge="Postage Stamps · Printable",
                   need=lambda c: len(c["motifs"]) >= 16,
                   pages=lambda c: [{"type": "stamps", "off": 0, "name": "stamps_1"}, {"type": "stamps", "off": 9, "name": "stamps_2"}],
                   contents=lambda c: {"postage_stamps": 40}, size="approx. 1.8 x 1.9 in each on US Letter, perforated edge"),
    "journal-cards": dict(product_type="Journal Cards", price=2.29, section="Papers & Journal Pages", badge="Journal Cards · Printable",
                          need=lambda c: len(c["motifs"]) >= 12 and len(c.get("cards") or []) >= 4 and len(c.get("journal_titles") or []) >= 6,
                          pages=lambda c: [{"type": "journal", "off": 0, "name": "journal_cards_1"}, {"type": "journal", "off": 6, "name": "journal_cards_2"},
                                           {"type": "cards", "name": "picture_cards"}],
                          contents=lambda c: {"lined_journal_cards": 12, "picture_cards": 4},
                          size="journal cards approx. 3.6 x 3.2 in, picture cards approx. 3.6 x 4.8 in (US Letter)"),
    "word-strips": dict(product_type="Word Strips", price=1.99, section="Tags & Labels", badge="Word Strips · Printable",
                        need=lambda c: _words(c, 40) is not None,
                        pages=lambda c: [{"type": "words", "name": "word_strips_1", "words": c["words"][:20]},
                                         {"type": "words", "name": "word_strips_2", "words": c["words"][20:40]}],
                        contents=lambda c: {"word_strips": 40}, size="approx. 3.6 x 0.8 in each on US Letter"),
    "paper-pack": dict(product_type="Pattern Paper Pack", price=1.49, section="Papers & Journal Pages", badge="Pattern Papers · Printable",
                       need=lambda c: len(c.get("pattern_papers") or []) >= 6,
                       pages=lambda c: [{"type": "pattern", "key": k, "name": "paper_" + k.split("_", 1)[-1]} for k in c["pattern_papers"][:6]],
                       contents=lambda c: {"pattern_papers": 6}, size="full page, US Letter 8.5 x 11 in and A4"),
    "advent-numbers": dict(product_type="Advent Numbers", price=2.19, section="Tags & Labels", badge="Advent Numbers 1-25",
                           holiday="christmas", need=lambda c: len(c["motifs"]) >= 12,
                           pages=lambda c: [{"type": "advent", "style": "medallion", "name": "advent_round"}, {"type": "advent", "style": "card", "name": "advent_cards"}],
                           contents=lambda c: {"advent_numbers_1_to_25": 50, "styles": 2},
                           size="round labels approx. 1.4 in, number cards approx. 1.4 x 1.7 in (US Letter)"),
    "mini-kit": dict(product_type="Mini Ephemera Kit", price=2.79, section=None, badge="Mini Kit · 4 Pages",
                     need=lambda c: len(c["motifs"]) >= 12 and _words(c, 20) is not None,
                     pages=lambda c: [{"type": "tags", "off": 0, "name": "tags", "words": c["words"][:6]}, {"type": "stamps", "off": 0, "name": "stamps"},
                                      {"type": "fussy", "off": 0, "name": "fussy_cuts"}, {"type": "words", "name": "word_strips", "words": c["words"][:20]}],
                     contents=lambda c: {"gift_tags": 6, "postage_stamps": 20, "fussy_cuts": 9, "word_strips": 20},
                     size="tags approx. 2.4 x 4.8 in, stamps approx. 1.8 x 1.9 in, word strips approx. 3.6 x 0.8 in (US Letter)"),
}

LABEL = {"fussy_cuts": "fussy cuts", "different_motifs": "different motifs", "gift_tags": "gift tags", "postage_stamps": "postage stamps",
         "lined_journal_cards": "journal cards", "picture_cards": "picture cards", "word_strips": "word strips", "pattern_papers": "pattern papers",
         "advent_numbers_1_to_25": "advent numbers", "styles": "styles"}


def have_types(col):
    out = set()
    for p in col["products"]:
        pt = (p.get("facts") or {}).get("product_type", "")
        for k, t in TYPES.items():
            if pt == t["product_type"] or p["slug"].endswith("-" + k):
                out.add(k)
        if pt == "Ephemera Kit" or p["slug"].endswith("-kit"):
            out.add("kit")
    return out


def base_facts(col):
    for p in col["products"]:
        if p.get("facts", {}).get("licence"):
            f = {k: p["facts"][k] for k in ("theme", "collection", "sizes", "resolution_dpi", "files", "licence") if k in p["facts"]}
            return f
    raise SystemExit("collection has no product with base facts (theme, licence) to copy")


def kit_section(col):
    for p in col["products"]:
        if (p.get("facts") or {}).get("product_type") == "Ephemera Kit":
            return p["section"]
    return col["products"][0]["section"]


def make(col, key, holiday):
    t = TYPES[key]
    if t.get("holiday") and t["holiday"] != holiday:
        return None
    if not t["need"](col):
        return None
    name = col.get("badge_title") or col["title"]
    noun = {"christmas": "Christmas", "halloween": "Halloween"}.get(holiday, "")
    title = " ".join(x for x in (name, noun if noun and noun not in name else "", t["product_type"]) if x)
    pages = t["pages"](col)
    contents = t["contents"](col)
    nice = [("%d %s" % (v, LABEL.get(k, k.replace("_", " ")))) for k, v in contents.items() if k not in ("different_motifs", "styles")]
    facts = dict(base_facts(col), product_type=t["product_type"], section=t["section"] or kit_section(col), pages=len(pages),
                 contents=contents, piece_size=t["size"], generated_by="expand_collection")
    names = next((q["facts"]["motifs"] for q in col["products"] if isinstance((q.get("facts") or {}).get("motifs"), str)), None)
    if key in ("fussy-cuts", "stamps", "mini-kit") and names:
        facts["motifs"] = names
    return {
        "slug": "%s-%s" % (col["slug"], key), "title": title, "badge_sub": t["badge"], "price_eur": t["price"],
        "section": t["section"] or kit_section(col), "pages": pages,
        "cover_lines": [" · ".join(nice[:2]), "%d printable pages" % len(pages), "US Letter & A4"],
        "inside_lines": [" · ".join(nice), "%s collection" % name, "PDF (US Letter & A4) + JPG"],
        "facts": facts,
    }


def main():
    path = sys.argv[1]
    write = "--write" in sys.argv
    holiday = sys.argv[sys.argv.index("--holiday") + 1] if "--holiday" in sys.argv else "none"
    col = json.load(open(path))
    have = have_types(col)
    # phrases: base words plus every phrase already used on product pages (word strips, tags)
    words = list(dict.fromkeys((col.get("words") or []) + [w for q in col["products"] for s in q["pages"] for w in (s.get("words") or [])]))
    view = dict(col, words=words)
    added = []
    for key in TYPES:
        if key in have:
            continue
        p = make(view, key, holiday)
        if p:
            added.append(p)
            print("+", p["slug"], p["price_eur"], p["section"], [s["type"] for s in p["pages"]])
        else:
            print("-", key, "skipped (art or texts missing, or wrong holiday)")
    if write and added:
        col["products"] += added
        json.dump(col, open(path, "w"), indent=1, ensure_ascii=False)
        print("wrote", path)
    print(json.dumps({"have": sorted(have), "added": [p["slug"] for p in added]}))


if __name__ == "__main__":
    main()
