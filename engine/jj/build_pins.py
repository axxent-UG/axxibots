#!/usr/bin/env python3
"""Pinterest pins for every active Etsy listing (Inkwell Ephemera).

Usage: build_pins.py <listings.json> <images_root> <out_dir>
listings.json: [{slug, id, collection, title, tags, desc}] (active listings, from axx.jj_kits)
images_root:   folder that contains <...>/<slug>/listing/01_cover.jpg etc.
Writes <out_dir>/<slug>_<a|b|c>.jpg (1000 x 1500, 2:3) and <out_dir>/pins.json with the pin texts.
Three layouts per listing so Pinterest sees fresh pins, not duplicates:
  a  headline on colour + cover image
  b  full-bleed detail page + headline card
  c  two images with a headline band in between
"""
import glob, json, os, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FD = os.path.join(os.path.dirname(__file__), "fonts")
W, H = 1000, 1500


def font(name, sz, var=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(sz))
    if var:
        try:
            f.set_variation_by_name(var)
        except Exception:
            pass
    return f


SERIF = lambda s: font("CormorantGaramond[wght].ttf", s, b"SemiBold")
SANS = lambda s: font("Jost[wght].ttf", s, b"Medium")
ROUND = lambda s: font("Fredoka[wdth,wght].ttf", s, b"SemiBold")

# collection -> (background, ink on background, accent, family)
THEMES = {
    "Christmas Post": ((38, 58, 44), (246, 238, 222), (196, 160, 98), "journal"),
    "Shabby Pink Christmas": ((236, 214, 210), (98, 52, 60), (176, 112, 118), "journal"),
    "Holly Berry Christmas": ((122, 26, 36), (250, 242, 230), (214, 186, 120), "journal"),
    "Christmas Bundles": ((30, 46, 36), (246, 238, 222), (206, 170, 104), "journal"),
    "Witching Hour": ((26, 22, 26), (240, 226, 204), (214, 120, 48), "journal"),
    "Dino Party": ((34, 150, 138), (255, 255, 255), (255, 176, 46), "party"),
    "Wedding Antique Botanical": ((236, 228, 210), (60, 48, 36), (128, 104, 72), "wedding"),
    "Wedding Black Tie Deco": ((22, 22, 24), (226, 200, 140), (206, 176, 108), "wedding"),
    "Wedding Candlelight Supper": ((246, 238, 226), (92, 54, 40), (176, 126, 76), "wedding"),
    "Wedding Cherry Gingham": ((250, 244, 238), (136, 30, 40), (186, 60, 60), "wedding"),
    "Wedding Eucalyptus Minimal": ((240, 242, 236), (62, 76, 62), (122, 140, 118), "wedding"),
    "Wedding Olive & Gold": ((242, 238, 226), (66, 74, 40), (172, 146, 82), "wedding"),
    "Wedding Oysters & Lemons": ((250, 248, 240), (40, 64, 104), (222, 182, 52), "wedding"),
    "Wedding Riviera Stripe": ((244, 240, 230), (34, 50, 102), (34, 50, 102), "wedding"),
    "Wedding Satin Bow": ((248, 240, 238), (110, 70, 76), (190, 150, 150), "wedding"),
    "Wedding Toile Bleu": ((242, 244, 248), (40, 62, 116), (96, 120, 170), "wedding"),
}

TYPE_WORDS = [
    ("ephemera-mega-bundle", "Ephemera Mega Bundle"), ("fussy-cuts-bundle", "Fussy Cuts Bundle"),
    ("gift-tags-bundle", "Gift Tags Bundle"), ("paper-pack-bundle", "Paper Pack Bundle"),
    ("illusion-pockets", "Illusion Pockets"), ("advent-numbers", "Advent Calendar Numbers"),
    ("fussy-cuts", "Printable Fussy Cuts"), ("gift-tags", "Printable Gift Tags"), ("stamps", "Faux Postage Stamps"),
    ("journal-cards", "Journal Cards"), ("word-strips", "Vintage Word Strips"), ("paper-pack", "Pattern Paper Pack"),
    ("mini-kit", "Mini Ephemera Kit"), ("-kit", "Junk Journal Kit"), ("-test", "Junk Journal Ephemera Kit"),
    ("drinks-menu", "Wedding Drinks Menu"), ("table-set", "Wedding Table Set"), ("place-cards", "Wedding Place Cards"),
    ("-menu", "Wedding Menu"),
    ("invitation", "Dino Birthday Invitation"), ("welcome-sign", "Dino Party Welcome Sign"), ("banner", "Dino Birthday Banner"),
    ("cupcake-toppers", "Dino Cupcake Toppers"), ("food-labels", "Dino Party Food Labels"), ("favor-tags", "Dino Favor Tags"),
    ("bingo", "Dinosaur Bingo Game"), ("would-you-rather", "Dino Would You Rather"), ("bundle", "Dino Party Bundle"),
]

SUBLINES = {
    "journal": ["Printable · Instant Download", "For junk journals, scrapbooks & cards"],
    "party": ["Printable · Instant Download", "Kids birthday party decor"],
    "wedding": ["Editable or handwrite · English & German", "Printable · Instant Download"],
}


def product_type(slug):
    for k, v in TYPE_WORDS:
        if slug.endswith(k):
            return v
    return "Printable"


def kicker(row):
    c = row["collection"]
    if c.startswith("Wedding "):
        return c[len("Wedding "):]
    if c == "Christmas Bundles":
        return "Vintage Christmas"
    if c == "Dino Party":
        return "Kids Party"
    return c


def images_for(root, slug):
    hits = glob.glob(os.path.join(root, "**", slug, "listing", "01_*.jpg"), recursive=True)
    if not hits and slug == "christmas-post-test":
        hits = glob.glob(os.path.join(root, "listing", "01_*.jpg"))
    if not hits:
        return []
    d = os.path.dirname(hits[0])
    return sorted(glob.glob(os.path.join(d, "*.jpg")))


def crop(img, w, h, cx=0.5, cy=0.5):
    s = max(w / img.width, h / img.height)
    im = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
    x = int((im.width - w) * cx)
    y = int((im.height - h) * cy)
    return im.crop((x, y, x + w, y + h))


def wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


def headline(d, text, cx, cy, max_w, fam, fill, start=104, max_lines=2):
    maker = ROUND if fam == "party" else SERIF
    sz = start
    while sz > 40:
        f = maker(sz)
        lines = wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            break
        sz -= 4
    lh = int(sz * (1.08 if fam == "party" else 1.0))
    y0 = cy - lh * (len(lines) - 1) / 2
    for i, ln in enumerate(lines):
        d.text((cx, y0 + i * lh), ln, font=f, fill=fill, anchor="mm")
    return y0 - lh / 2, y0 + lh * (len(lines) - 0.5)


def spaced(s):
    return "  ".join(" ".join(w) for w in s.upper().split())


def caps_line(d, text, cx, cy, sz, fill, max_w=900):
    s = spaced(text)
    while d.textlength(s, font=SANS(sz)) > max_w and sz > 14:
        sz -= 1
    d.text((cx, cy), s, font=SANS(sz), fill=fill, anchor="mm")


def shop_mark(d, cy, fill):
    d.text((W // 2, cy), "Inkwell Ephemera", font=font("CormorantGaramond-Italic[wght].ttf", 40, b"Medium"), fill=fill, anchor="mm")


def shadowed(base, im, x, y, blur=18, alpha=110, off=(0, 14)):
    sh = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 40, 40 + im.width, 40 + im.height), 18, fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(sh, (x - 40 + off[0], y - 40 + off[1]))
    base.alpha_composite(im.convert("RGBA"), (x, y))


def pin_a(row, imgs, th):
    bg, ink, acc, fam = th
    im = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(im)
    caps_line(d, kicker(row), W // 2, 110, 30, acc)
    headline(d, product_type(row["slug"]), W // 2, 250, 860, fam, ink, start=108)
    cover = crop(Image.open(imgs[0]).convert("RGB"), 940, 752)
    shadowed(im, cover, 30, 410)
    caps_line(d, SUBLINES[fam][0], W // 2, 1268, 27, ink)
    d.line((W // 2 - 60, 1318, W // 2 + 60, 1318), fill=acc + (255,), width=2)
    caps_line(d, SUBLINES[fam][1], W // 2, 1366, 24, ink)
    shop_mark(d, 1440, acc)
    return im


def pin_b(row, imgs, th):
    bg, ink, acc, fam = th
    src = imgs[2] if len(imgs) > 2 else imgs[-1]
    if fam == "wedding":
        src = imgs[1] if row["slug"].endswith("table-set") and len(imgs) > 1 else imgs[0]
    im = crop(Image.open(src).convert("RGB"), W, H).convert("RGBA")
    card = Image.new("RGBA", (860, 380), (255, 255, 255, 0))
    cd = ImageDraw.Draw(card)
    light = (252, 249, 243) if fam != "party" else (255, 255, 255)
    cd.rounded_rectangle((0, 0, 859, 379), 26, fill=light + (246,))
    dark = bg if sum(bg) < 360 else ink
    cd.rounded_rectangle((14, 14, 845, 365), 18, outline=acc + (255,), width=2)
    caps_line(cd, kicker(row), 430, 70, 26, acc, 760)
    headline(cd, product_type(row["slug"]), 430, 180, 760, fam, dark, start=88)
    caps_line(cd, SUBLINES[fam][0], 430, 300, 22, dark, 760)
    shadowed(im, card, 70, 1060)
    return im


def pin_c(row, imgs, th):
    bg, ink, acc, fam = th
    im = Image.new("RGBA", (W, H), bg + (255,))
    top = crop(Image.open(imgs[0]).convert("RGB"), W, 650)
    second = imgs[1] if len(imgs) > 1 else imgs[0]
    bot = crop(Image.open(second).convert("RGB"), W, 610, cy=0.4)
    im.paste(top, (0, 0))
    im.paste(bot, (0, 890))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 650, W, 890), fill=bg + (255,))
    d.line((0, 652, W, 652), fill=acc + (255,), width=4)
    d.line((0, 888, W, 888), fill=acc + (255,), width=4)
    pt = product_type(row["slug"]).replace("Printable ", "")
    head = pt if fam == "party" else kicker(row) + " " + pt
    headline(d, head, W // 2, 745, 900, fam, ink, start=78)
    caps_line(d, SUBLINES[fam][0], W // 2, 845, 24, acc)
    return im


# ---------- pin texts ----------
BOARDS = {
    "journal_xmas": "Christmas Junk Journal Printables",
    "journal_halloween": "Halloween Junk Journal Printables",
    "wedding_menu": "Wedding Menu & Drinks Menu Ideas",
    "wedding_place": "Wedding Place Cards & Table Decor",
    "party": "Dinosaur Birthday Party Ideas",
}


def board_for(row):
    s, c = row["slug"], row["collection"]
    if c == "Witching Hour":
        return BOARDS["journal_halloween"]
    if c == "Dino Party":
        return BOARDS["party"]
    if c.startswith("Wedding"):
        return BOARDS["wedding_menu"] if s.endswith("menu") else BOARDS["wedding_place"]
    return BOARDS["journal_xmas"]


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def pin_title(row, variant):
    t = product_type(row["slug"]).replace("Printable ", "")
    k = kicker(row)
    fam = THEMES[row["collection"]][3]
    if fam == "journal":
        opts = [f"{k} {t} – Printable Junk Journal Ephemera",
                f"Printable {t} for Junk Journals | {k}",
                f"{k} {t} for Scrapbooking & Card Making"]
    elif fam == "wedding":
        opts = [f"{k} {t} – Editable Printable Template",
                f"{t} Template | {k} Style, English & German",
                f"Elegant {k} {t} – Print at Home"]
    else:
        opts = [f"{t} – Printable Kids Birthday Decor",
                f"Printable {t} | Dinosaur Birthday Party",
                f"{t} for a Dino Party – Instant Download"]
    return opts["abc".index(variant)][:100]


def pin_desc(row, variant):
    first = clean(row.get("desc", "")).split(". ")[0].rstrip(".")
    fam = THEMES[row["collection"]][3]
    tags = [t for t in (row.get("tags") or [])][:6]
    tail = {
        "journal": "Instant digital download – print at home on US Letter or A4.",
        "wedding": "Editable PDF or handwrite – instant download, print at home or at a copy shop.",
        "party": "Instant download – print at home, cut out and celebrate.",
    }[fam]
    lead = [first + ".", tail, "Ideas: " + ", ".join(tags) + "."]
    order = {"a": [0, 1, 2], "b": [1, 0, 2], "c": [0, 2, 1]}[variant]
    txt = " ".join(lead[i] for i in order) + " Shop Inkwell Ephemera on Etsy."
    return txt[:495]


def main():
    listings, root, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    rows = json.load(open(listings))
    pins, missing = [], []
    for row in rows:
        imgs = images_for(root, row["slug"])
        th = THEMES.get(row["collection"])
        if not imgs or not th:
            missing.append(row["slug"])
            continue
        for v, fn in (("a", pin_a), ("b", pin_b), ("c", pin_c)):
            name = f"{row['slug']}_{v}.jpg"
            fn(row, imgs, th).convert("RGB").save(os.path.join(out, name), quality=86, optimize=True, progressive=True)
            pins.append({"slug": row["slug"], "variant": v, "file": name, "collection": row["collection"],
                         "board": board_for(row), "title": pin_title(row, v), "description": pin_desc(row, v),
                         "link": f"https://www.etsy.com/listing/{row['id']}",
                         "keywords": ", ".join((row.get("tags") or [])[:8])})
    json.dump(pins, open(os.path.join(out, "pins.json"), "w"), indent=1, ensure_ascii=False)
    print(len(pins), "pins; missing:", missing)


if __name__ == "__main__":
    main()
