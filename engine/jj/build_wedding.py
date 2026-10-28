#!/usr/bin/env python3
"""Wedding table stationery in the 10 owner-approved styles (28.10.2026).

Per style: place cards (tent fold), menu (4 x 9 in), wine & drinks list (4 x 9 in), table set bundle.
Every product: English + German, a handwrite version (blank lines) and an editable PDF (fillable fields,
Times Italic so it reads like stationery; previews use the metric-identical Liberation Serif Italic).

Usage: build_wedding.py <assets_dir> <out_dir> [style_key ...]
"""
import glob, io, json, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk
import wedding_styles2 as ws
from wedding_styles2 import W as PW, H as PH, font, mot, tint, text, spaced, fit_text, gingham, linen, tent, shadow_drop

DPI = 300
LETTER, A4 = (2550, 3300), (2480, 3508)
TW, TH = 1200, 2700  # tall card 4 x 9 in
SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

TEXT = {
    "en": {"menu": "Menu", "wine": "Wine & Drinks", "menu_secs": ["Starter", "Main Course", "Dessert"],
           "wine_secs": ["Sparkling", "White Wine", "Red Wine", "Signature Cocktail"], "table": "Table", "welcome": "WELCOME",
           "couple": "Sophie & Max", "date": "12 June 2027"},
    "de": {"menu": "Menü", "wine": "Weine & Getränke", "menu_secs": ["Vorspeise", "Hauptgang", "Dessert"],
           "wine_secs": ["Sekt & Champagner", "Weißwein", "Rotwein", "Signature Cocktail"], "table": "Tisch", "welcome": "WILLKOMMEN",
           "couple": "Sophie & Max", "date": "12. Juni 2027"},
}

# name field (cx, cy, w, h) and table field on the place card front, per style (px on the 1050 x 600 front)
STY = [
    dict(key="candlelight", title="Candlelight Supper", fn=ws.s_candle, bg=(247, 241, 214), ink=(44, 74, 132), acc=(44, 74, 132), script="Sacramento-Regular.ttf", serif=("CormorantGaramond[wght].ttf", b"SemiBold"), name=(525, 310, 470, 160), sub=None),
    dict(key="riviera", title="Riviera Stripe", fn=ws.s_stripe, bg=(244, 241, 234), ink=(34, 48, 98), acc=(34, 48, 98), script="PinyonScript-Regular.ttf", serif=("CormorantGaramond[wght].ttf", b"Medium"), name=(525, 270, 560, 150), sub=None),
    dict(key="olive-gold", title="Olive & Gold", fn=ws.s_olive, bg=(255, 255, 255), ink=(40, 40, 40), acc=(184, 150, 82), script="GreatVibes-Regular.ttf", serif=("CormorantGaramond[wght].ttf", b"Medium"), name=(525, 330, 720, 150), sub="line"),
    dict(key="oysters-lemons", title="Oysters & Lemons", fn=ws.s_oyster, bg=(250, 248, 242), ink=(30, 60, 110), acc=(30, 60, 110), script="Sacramento-Regular.ttf", serif=("CormorantGaramond[wght].ttf", b"SemiBold"), name=(525, 300, 440, 150), sub=None),
    dict(key="satin-bow", title="Satin Bow", fn=ws.s_bow, bg=(253, 249, 247), ink=(120, 80, 82), acc=(214, 170, 168), script="PinyonScript-Regular.ttf", serif=("CormorantGaramond[wght].ttf", b"Medium"), name=(525, 350, 640, 140), sub=(525, 470, 420, 60)),
    dict(key="cherry-gingham", title="Cherry Gingham", fn=ws.s_cherry, bg=(255, 253, 250), ink=(176, 32, 42), acc=(176, 32, 42), script="Sacramento-Regular.ttf", serif=("CormorantGaramond[wght].ttf", b"SemiBold"), name=(605, 290, 560, 150), sub=(605, 400, 420, 60)),
    dict(key="toile-bleu", title="Toile Bleu", fn=ws.s_toile, bg=(250, 249, 244), ink=(46, 82, 150), acc=(46, 82, 150), script="PinyonScript-Regular.ttf", serif=("Italiana-Regular.ttf", None), name=(525, 190, 720, 140), sub=(525, 300, 420, 60)),
    dict(key="black-tie-deco", title="Black Tie Deco", fn=ws.s_deco, bg=(22, 22, 24), ink=(206, 176, 108), acc=(206, 176, 108), script="Italiana-Regular.ttf", serif=("Cinzel[wght].ttf", b"Regular"), name=(525, 330, 760, 120), sub=(525, 440, 420, 60), caps=True),
    dict(key="antique-botanical", title="Antique Botanical", fn=ws.s_botanical, bg=(244, 238, 222), ink=(52, 42, 34), acc=(120, 96, 70), script="PinyonScript-Regular.ttf", serif=("IMFeENsc28P.ttf", None), name=(645, 280, 520, 140), sub=(645, 395, 420, 60), paper=True),
    dict(key="eucalyptus-minimal", title="Eucalyptus Minimal", fn=ws.s_eucalyptus, bg=(255, 255, 255), ink=(64, 72, 64), acc=(130, 145, 128), script="CormorantGaramond-Italic[wght].ttf", serif=("CormorantGaramond[wght].ttf", b"Medium"), name=(485, 310, 700, 140), sub=(485, 410, 400, 60)),
]


def sfont(st, sz):
    return font(st["serif"][0], sz, st["serif"][1])


# ---------------- tall cards (menu / wine) ----------------

def tall_base(st, assets, seed=5):
    c = bk.paper(TW, TH, st["bg"], seed, stains=False).convert("RGBA") if st.get("paper") else Image.new("RGBA", (TW, TH), st["bg"] + (255,))
    d = ImageDraw.Draw(c)
    k = st["key"]
    top = 240  # y where the title area starts
    if k == "candlelight":
        co = tint(mot(assets, "l02_coupe", 300, 300), st["ink"])
        c.alpha_composite(co, ((TW - co.width) // 2, 90))
        ca = tint(mot(assets, "l01_candles", 200, 380), st["ink"])
        c.alpha_composite(ca, ((TW - ca.width) // 2, TH - ca.height - 90))
        top = 470
    elif k == "riviera":
        for band_y in (0, TH - 150):
            for x in range(0, TW, 44):
                d.rectangle((x, band_y, x + 18, band_y + 150), fill=st["ink"] + (255,))
                d.line((x + 28, band_y, x + 28, band_y + 150), fill=st["ink"] + (120,), width=2)
        d.rectangle((60, 190, TW - 60, TH - 190), outline=st["ink"] + (255,), width=4)
        d.rectangle((74, 204, TW - 74, TH - 204), outline=st["ink"] + (255,), width=1)
        ox0, oy0, ox1, oy1 = 150, 290, TW - 150, 555
        d.ellipse((ox0, oy0, ox1, oy1), outline=st["ink"] + (255,), width=5)
        d.ellipse((ox0 + 14, oy0 + 14, ox1 - 14, oy1 - 14), outline=st["ink"] + (255,), width=2)
        top = 330
    elif k == "olive-gold":
        d.rectangle((60, 76, TW - 76, TH - 60), outline=st["acc"] + (255,), width=4)
        d.rectangle((76, 60, TW - 60, TH - 76), outline=st["acc"] + (255,), width=4)
        o = mot(assets, "o01_olive", 520, 170)
        c.alpha_composite(o, ((TW - o.width) // 2, 150))
        top = 420
    elif k == "oysters-lemons":
        d.rectangle((40, 40, TW - 40, TH - 40), outline=st["ink"] + (255,), width=3)
        le = tint(mot(assets, "l04_lemons", 330, 330), st["ink"])
        c.alpha_composite(le, ((TW - le.width) // 2, 90))
        oy = tint(mot(assets, "l03_oysters", 360, 260), st["ink"])
        c.alpha_composite(oy, ((TW - oy.width) // 2, TH - oy.height - 90))
        top = 500
    elif k == "satin-bow":
        r, m = 20, 60
        for x in range(m, TW - m + 1, 2 * r):
            d.arc((x - r, m - r, x + r, m + r), 0, 180, fill=st["acc"] + (255,), width=4)
            d.arc((x - r, TH - m - r, x + r, TH - m + r), 180, 360, fill=st["acc"] + (255,), width=4)
        for y in range(m, TH - m + 1, 2 * r):
            d.arc((m - r, y - r, m + r, y + r), 270, 90, fill=st["acc"] + (255,), width=4)
            d.arc((TW - m - r, y - r, TW - m + r, y + r), 90, 270, fill=st["acc"] + (255,), width=4)
        b = mot(assets, "b01_bow", 280, 240)
        c.alpha_composite(b, ((TW - b.width) // 2, 130))
        sb = mot(assets, "b01_bow", 150, 130)
        c.alpha_composite(sb, ((TW - sb.width) // 2, TH - sb.height - 130))
        top = 440
    elif k == "cherry-gingham":
        band = gingham(TW, 120, st["ink"])
        c.alpha_composite(band, (0, 0))
        c.alpha_composite(band, (0, TH - 120))
        ch = mot(assets, "c01_cherries", 200, 230)
        c.alpha_composite(ch, ((TW - ch.width) // 2, 180))
        top = 470
    elif k == "toile-bleu":
        t = tint(mot(assets, "t01_toile", TW - 120, 260), st["ink"])
        c.alpha_composite(t, ((TW - t.width) // 2, TH - t.height - 70))
        d.rectangle((40, 40, TW - 40, TH - 40), outline=st["ink"] + (255,), width=2)
        top = 200
    elif k == "black-tie-deco":
        d.rectangle((40, 40, TW - 40, TH - 40), outline=st["acc"] + (255,), width=4)
        d.rectangle((58, 58, TW - 58, TH - 58), outline=st["acc"] + (255,), width=1)
        m = mot(assets, "w03_deco", 520, 200)
        c.alpha_composite(m, ((TW - m.width) // 2, 110))
        c.alpha_composite(m.transpose(Image.FLIP_TOP_BOTTOM), ((TW - m.width) // 2, TH - m.height - 110))
        top = 400
    elif k == "antique-botanical":
        b = mot(assets, "w09_botanical", 640, 300)
        c.alpha_composite(b, ((TW - b.width) // 2, 100))
        d.rectangle((50, 50, TW - 50, TH - 50), outline=st["acc"] + (255,), width=2)
        top = 460
    elif k == "eucalyptus-minimal":
        e = mot(assets, "w01_eucalyptus", 460, 220)
        c.alpha_composite(e.rotate(-28, expand=True, resample=Image.BICUBIC), (TW - 470, 30))
        e2 = mot(assets, "w01_eucalyptus", 380, 180).rotate(152, expand=True, resample=Image.BICUBIC)
        c.alpha_composite(e2, (20, TH - e2.height - 20))
        top = 380
    return c, top


def tall_card(st, assets, kind, lang, editable=False, sample=False):
    """Returns (image, fields). kind 'menu' | 'wine'."""
    t = TEXT[lang]
    c, top = tall_base(st, assets)
    d = ImageDraw.Draw(c)
    title = t[kind]
    if st.get("caps"):
        title = title.upper()
    fsz = 200 if not st.get("caps") else 110
    tf = font(st["script"], fsz)
    while d.textlength(title, font=tf) > TW * 0.76:
        fsz -= 6
        tf = font(st["script"], fsz)
    text(d, (TW // 2, top + 90), title, tf, st["ink"] + (255,))
    fields = []
    # couple line: printed sample on previews, editable field or a blank line for handwriting
    cy = top + 250
    if editable:
        fields.append(("couple", t["couple"] + "  ·  " + t["date"], (200, cy - 45, TW - 400, 90), 15))
    else:
        d.line((TW // 2 - 220, cy + 20, TW // 2 + 220, cy + 20), fill=st["acc"] + (160,), width=2)
    secs = t["%s_secs" % kind]
    bottom_reserved = {"candlelight": 520, "oysters-lemons": 400, "toile-bleu": 400, "black-tie-deco": 360, "riviera": 260, "cherry-gingham": 200, "satin-bow": 330, "eucalyptus-minimal": 330}.get(st["key"], 220)
    y0 = cy + 150
    step = (TH - bottom_reserved - y0) // len(secs)
    hf = sfont(st, 54)
    for i, s in enumerate(secs):
        y = y0 + i * step
        text(d, (TW // 2, y), spaced(s.upper()) if len(s) < 14 else s.upper(), hf, st["ink"] + (255,))
        for k in range(3 if kind == "menu" else 2):
            ly = y + 110 + k * 95
            if ly > y + step - 40:
                break
            d.line((200, ly, TW - 200, ly), fill=st["acc"] + (150,), width=2)
            if editable:
                fields.append(("%s_%d_%d" % (kind, i + 1, k + 1), "", (200, ly - 78, TW - 400, 74), 13))
    if sample:
        ws_draw_fields(c, [(n, v, b, p) for n, v, b, p in fields if v], st["ink"])
    return c, fields


def ws_draw_fields(img, fields, ink):
    d = ImageDraw.Draw(img)
    for _, val, (x, y, w, h), pt in fields:
        px = int(pt * 300 / 72)
        f = ImageFont.truetype(SERIF_I, px)
        while d.textlength(val, font=f) > w - 20 and px > 20:
            px -= 4
            f = ImageFont.truetype(SERIF_I, px)
        d.text((x + w // 2, y + h // 2), val, font=f, fill=ink + (255,), anchor="mm")


# ---------------- place cards ----------------

def place_front(st, assets, lang, name="", sub=""):
    t = TEXT[lang]
    if st["key"] == "riviera":
        return ws.s_stripe(assets, name, sub, lang)
    if st["key"] == "olive-gold":
        return ws.s_olive(assets, name, sub, lang)
    return st["fn"](assets, name, sub, lang)


def place_sheet(st, assets, lang, W, H, editable=False, names=None):
    """4 tent cards per page (2 x 2), each 3.5 x 4 in flat: back (blank design colour) on top, front below."""
    p = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    cw, ch = PW, PH * 2
    gx, gy = 120, 120
    mx, my = (W - 2 * cw - gx) // 2, (H - 2 * ch - gy) // 2 - 20
    fields = []
    t = TEXT[lang]
    for i in range(4):
        r, c = divmod(i, 2)
        x, y = mx + c * (cw + gx), my + r * (ch + gy)
        nm = (names or [""] * 4)[i]
        sub = ("%s %d" % (t["table"], i + 1)) if names else ""
        front = place_front(st, assets, lang, nm, sub)
        back = Image.new("RGBA", (cw, PH), st["bg"] + (255,))
        p.alpha_composite(back, (x, y))
        p.alpha_composite(front, (x, y + PH))
        d = ImageDraw.Draw(p)
        for xx in range(x, x + cw, 30):
            d.line((xx, y + PH, xx + 15, y + PH), fill=(170, 170, 170, 255), width=2)
        bk.cut_outline(p, Image.new("L", (cw, ch), 255), x, y, width=2)
        if editable:
            cx, cy, w, h = st["name"]
            fields.append(("name_%d" % (i + 1), "", (x + cx - w // 2, y + PH + cy - h // 2, w, h), 26 if not st.get("caps") else 20))
            if st["sub"] == "line":
                fields.append(("table_%d" % (i + 1), "", (x + 760, y + PH + 430, 230, 70), 16))
            elif st["sub"]:
                sx, sy, sw, sh = st["sub"]
                fields.append(("table_%d" % (i + 1), "", (x + sx - sw // 2, y + PH + sy - sh // 2, sw, sh), 12))
    d = ImageDraw.Draw(p)
    d.text((W // 2, H - 70), "%s  ·  Inkwell Ephemera  ·  fold on the dashed line  ·  for personal use" % st["title"], font=font("CormorantGaramond[wght].ttf", 30, b"Medium"), fill=(150, 150, 150, 255), anchor="mm")
    return p, fields


# ---------------- PDF helpers (fillable) ----------------

def pdf(pages, path, fields_by_page=None, ink=(40, 40, 40)):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import Color
    c = None
    for n, im in enumerate(pages):
        wpt, hpt = im.width * 72 / DPI, im.height * 72 / DPI
        if c is None:
            c = canvas.Canvas(path, pagesize=(wpt, hpt))
        else:
            c.setPageSize((wpt, hpt))
        b = io.BytesIO()
        im.convert("RGB").save(b, "JPEG", quality=90)
        c.drawImage(ImageReader(io.BytesIO(b.getvalue())), 0, 0, wpt, hpt)
        s = 72 / DPI
        for name, val, (x, y, w, h), pt in (fields_by_page or {}).get(n, []):
            c.acroForm.textfield(name="p%d_%s" % (n + 1, name), value=val, x=x * s, y=hpt - (y + h) * s, width=w * s, height=h * s,
                                 fontName="Times-Italic", fontSize=pt, textColor=Color(*(v / 255 for v in ink)),
                                 borderWidth=0, fillColor=None, borderColor=None, forceBorder=False, maxlen=60)
        c.showPage()
    c.save()
    if fields_by_page:
        import build_party
        build_party.center_fields(path)


def two_up(cards, W, H, title):
    """Two 4 x 9 cards side by side on one sheet with crop marks."""
    p = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    gx = 60
    mx, my = (W - 2 * TW - gx) // 2, (H - TH) // 2 - 10
    d = ImageDraw.Draw(p)
    offs = []
    for i, cd in enumerate(cards):
        x = mx + i * (TW + gx)
        p.alpha_composite(cd, (x, my))
        offs.append((x, my))
        for (cx, cy) in [(x, my), (x + TW, my), (x, my + TH), (x + TW, my + TH)]:
            d.line((cx, cy - 50 if cy == my else cy + 15, cx, cy - 15 if cy == my else cy + 50), fill=(120, 120, 120, 255), width=2)
    d.text((W // 2, H - 50), title + "  ·  Inkwell Ephemera  ·  for personal use", font=font("CormorantGaramond[wght].ttf", 28, b"Medium"), fill=(150, 150, 150, 255), anchor="mm")
    return p, offs


# ---------------- products ----------------

SAMPLE_NAMES = {"en": ["Charlotte Becker", "James Miller", "Olivia Brown", "Henry Wilson"], "de": ["Annalena Weber", "Lukas Werner", "Elsa Blum", "Felix Braun"]}


def build_style(st, assets, out):
    res = {}
    k = st["key"]
    # place cards
    slug = "wedding-%s-place-cards" % k
    pdir = os.path.join(out, slug, "pages")
    os.makedirs(pdir, exist_ok=True)
    for size, (W, H) in (("letter", LETTER), ("a4", A4)):
        pages, fbp = [], {}
        for lang in ("en", "de"):
            pg, _ = place_sheet(st, assets, lang, W, H)
            pages.append(pg)
            pe, fl = place_sheet(st, assets, lang, W, H, editable=True)
            fbp[len(pages)] = fl
            pages.append(pe)
        pdf(pages[:1] + pages[2:3], os.path.join(pdir, "%s_handwrite_%s.pdf" % (slug, size)))
        pdf([pages[1], pages[3]], os.path.join(pdir, "%s_editable_%s.pdf" % (slug, size)), {0: fbp[1], 1: fbp[3]}, st["ink"])
        if size == "letter":
            for n, pg in enumerate(pages[:1] + pages[2:3]):
                pg.convert("RGB").save(os.path.join(pdir, "%s_%02d_letter.jpg" % (slug, n + 1)), quality=90, dpi=(DPI, DPI))
    res["place"] = slug
    # menu + wine
    for kind in ("menu", "wine"):
        slug = "wedding-%s-%s" % (k, "menu" if kind == "menu" else "drinks-menu")
        pdir = os.path.join(out, slug, "pages")
        os.makedirs(pdir, exist_ok=True)
        for size, (W, H) in (("letter", LETTER), ("a4", A4)):
            hw_pages, ed_pages, fbp = [], [], {}
            for lang in ("en", "de"):
                card, _ = tall_card(st, assets, kind, lang)
                pg, _ = two_up([card, card], W, H, st["title"])
                hw_pages.append(pg)
                ce, fl = tall_card(st, assets, kind, lang, editable=True)
                pe, offs = two_up([ce], W, H, st["title"])
                fbp[len(ed_pages)] = [(n, v, (x + offs[0][0], y + offs[0][1], w, h), pt) for n, v, (x, y, w, h), pt in fl]
                ed_pages.append(pe)
            pdf(hw_pages, os.path.join(pdir, "%s_handwrite_%s.pdf" % (slug, size)))
            pdf(ed_pages, os.path.join(pdir, "%s_editable_%s.pdf" % (slug, size)), fbp, st["ink"])
            if size == "letter":
                for n, pg in enumerate(hw_pages):
                    pg.convert("RGB").save(os.path.join(pdir, "%s_%02d_letter.jpg" % (slug, n + 1)), quality=90, dpi=(DPI, DPI))
        # single-card 4x9 PDF for print shops (handwrite, EN + DE)
        cards = [tall_card(st, assets, kind, lang)[0] for lang in ("en", "de")]
        pdf(cards, os.path.join(pdir, "%s_4x9_print_shop.pdf" % slug))
        res[kind] = slug
    return res


# ---------------- listing images ----------------

def menu_mock(card, h):
    c = card.resize((int(card.width * h / card.height), h), Image.LANCZOS)
    return c


def scene(st, assets, items, seed, sample_lang="en"):
    """items: list of ('tall', kind) or ('place', name) to arrange on linen."""
    W, H = 3000, 2400
    bg = linen(W, H, seed=seed)
    talls = [i for i in items if i[0] == "tall"]
    places = [i for i in items if i[0] == "place"]
    xs = {1: [1500], 2: [1050, 1950], 3: [700, 1500, 2300]}[max(1, len(talls))] if talls else []
    for (kind_, kind), x in zip(talls, xs):
        card, fl = tall_card(st, assets, kind, sample_lang, editable=True)
        ws_draw_fields(card, [(n, v, b, p) for n, v, b, p in fl if v], st["ink"])
        m = menu_mock(card, 1900 if len(talls) < 3 else 1700)
        s = shadow_drop(m, off=(30, 24), blur=26, alpha=90)
        bg.alpha_composite(s, (x - s.width // 2, 140))
    nm = SAMPLE_NAMES[sample_lang]
    ppos = ([(260, 1500, 1.15), (1850, 1650, 1.05)] if len(talls) < 2 else [(1000, 1550, 1.05)]) if talls else [(170, 140, 1.2), (1560, 430, 1.2), (420, 1180, 1.2)]
    for j, ((_, lang), (x, y, sc)) in enumerate(zip(places, ppos)):
        front = place_front(st, assets, lang, SAMPLE_NAMES[lang][j], "%s %d" % (TEXT[lang]["table"], j + 2))
        card = tent(front, sc)
        s = shadow_drop(card)
        bg.alpha_composite(s, (x - 60, y - 60))
    return bg


def band(img, lines):
    d = ImageDraw.Draw(img)
    W, H = img.size
    d.rectangle((0, H - 230, W, H), fill=(250, 248, 244, 240))
    text(d, (W // 2, H - 150), lines[0], font("CormorantGaramond[wght].ttf", 96, b"SemiBold"), (52, 46, 42, 255))
    text(d, (W // 2, H - 65), lines[1], font("CormorantGaramond-Italic[wght].ttf", 60, b"Medium"), (110, 100, 92, 255))


def listing_images(st, assets, out, slugs):
    W, H = 3000, 2400
    for kind, slug in slugs.items():
        ldir = os.path.join(out, slug, "listing")
        os.makedirs(ldir, exist_ok=True)
        if kind == "place":
            c = scene(st, assets, [("place", "en"), ("place", "de"), ("place", "en")], 11)
            band(c, ["%s Place Cards" % st["title"], "editable or handwrite  ·  English & German  ·  fold-over tent cards"])
        else:
            c = scene(st, assets, [("tall", kind), ("place", "en")], 12)
            band(c, ["%s %s" % (st["title"], "Wedding Menu" if kind == "menu" else "Wine & Drinks Menu"), "editable or handwrite  ·  English & German  ·  4 x 9 in"])
        c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)
        # second image: EN + DE side by side (flat), third: handwrite sheet preview
        if kind == "place":
            pg = Image.open(sorted(glob.glob(os.path.join(out, slug, "pages", "*_01_letter.jpg")))[0]).convert("RGBA")
            pg2 = Image.open(sorted(glob.glob(os.path.join(out, slug, "pages", "*_02_letter.jpg")))[0]).convert("RGBA")
        else:
            pg, _ = tall_card(st, assets, kind, "en")
            pg2, _ = tall_card(st, assets, kind, "de")
        bg = linen(W, H, seed=21)
        for i, im in enumerate((pg, pg2)):
            h = 2050
            im2 = im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
            s = shadow_drop(im2, off=(20, 18), blur=20, alpha=80)
            bg.alpha_composite(s, (W // 4 * (1 + 2 * i) - s.width // 2, 40))
        d = ImageDraw.Draw(bg)
        text(d, (W // 4, H - 90), "English", font("CormorantGaramond-Italic[wght].ttf", 70, b"Medium"), (90, 80, 72, 255))
        text(d, (3 * W // 4, H - 90), "Deutsch", font("CormorantGaramond-Italic[wght].ttf", 70, b"Medium"), (90, 80, 72, 255))
        bg.convert("RGB").save(os.path.join(ldir, "02_english_german.jpg"), quality=90)
        # third: how it works
        bg = linen(W, H, seed=31)
        d = ImageDraw.Draw(bg)
        text(d, (W // 2, 300), "Two ways to use it", font(st["script"] if not st.get("caps") else "PinyonScript-Regular.ttf", 190), st["ink"] + (255,) if st["bg"][0] > 100 else (60, 52, 46, 255))
        rows = [("1", "Write by hand", "print the blank version and add names or dishes with a pen"),
                ("2", "Type and print", "open the editable PDF in the free Adobe Acrobat Reader, type, print"),
                ("3", "Print at home or at a print shop", "US Letter & A4 sheets with crop marks" + (", plus single 4 x 9 in cards" if kind != "place" else ""))]
        for i, (n, a, b) in enumerate(rows):
            y = 760 + i * 440
            d.ellipse((520, y - 90, 700, y + 90), outline=(120, 108, 96, 255), width=5)
            text(d, (610, y), n, font("CormorantGaramond[wght].ttf", 110, b"SemiBold"), (90, 80, 72, 255))
            d.text((800, y - 50), a, font=font("CormorantGaramond[wght].ttf", 90, b"SemiBold"), fill=(60, 52, 46, 255), anchor="lm")
            d.text((800, y + 55), b, font=font("CormorantGaramond-Italic[wght].ttf", 58, b"Medium"), fill=(110, 100, 92, 255), anchor="lm")
        bg.convert("RGB").save(os.path.join(ldir, "03_how_it_works.jpg"), quality=90)


def build_set(st, assets, out, slugs):
    """Table set: place cards + menu + wine list, max 5 Etsy files (2 ZIPs + 2 single-card PDFs)."""
    import zipfile
    slug = "wedding-%s-table-set" % st["key"]
    pdir, ldir = os.path.join(out, slug, "pages"), os.path.join(out, slug, "listing")
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(ldir, exist_ok=True)
    name = "%s_Wedding_Table_Set" % st["title"].replace(" & ", "_and_").replace(" ", "_")
    for size, label in (("letter", "US_Letter"), ("a4", "A4")):
        with zipfile.ZipFile(os.path.join(pdir, "%s_%s.zip" % (name, label)), "w", zipfile.ZIP_DEFLATED) as z:
            for part in ("place", "menu", "wine"):
                for f in sorted(glob.glob(os.path.join(out, slugs[part], "pages", "*_%s.pdf" % size))):
                    z.write(f, os.path.basename(f))
    for part in ("menu", "wine"):
        for f in glob.glob(os.path.join(out, slugs[part], "pages", "*_4x9_print_shop.pdf")):
            import shutil
            shutil.copy(f, os.path.join(pdir, os.path.basename(f)))
    c = scene(st, assets, [("tall", "menu"), ("tall", "wine"), ("place", "en")], 13)
    band(c, ["%s Wedding Table Set" % st["title"], "place cards · menu · wine & drinks  ·  editable or handwrite  ·  English & German"])
    c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)
    for i, part in enumerate(("place", "menu", "wine")):
        src = os.path.join(out, slugs[part], "listing", "01_cover.jpg")
        Image.open(src).save(os.path.join(ldir, "%02d_%s.jpg" % (i + 2, part)), quality=90)
    import shutil
    shutil.copy(os.path.join(out, slugs["place"], "listing", "03_how_it_works.jpg"), os.path.join(ldir, "05_how_it_works.jpg"))
    return slug


if __name__ == "__main__":
    assets, out = sys.argv[1], sys.argv[2]
    only = sys.argv[3:] or None
    for st in STY:
        if only and st["key"] not in only:
            continue
        if "--images-only" in sys.argv or os.environ.get("IMAGES_ONLY"):
            slugs = {"place": "wedding-%s-place-cards" % st["key"], "menu": "wedding-%s-menu" % st["key"], "wine": "wedding-%s-drinks-menu" % st["key"]}
        else:
            slugs = build_style(st, assets, out)
        listing_images(st, assets, out, slugs)
        slugs["set"] = build_set(st, assets, out, slugs)
        print(st["key"], "ok", slugs)


LOOK = {
    "candlelight": "hand-drawn navy ink line drawings of candlesticks and a champagne pour on warm cream, casual handwritten script",
    "riviera": "navy and cream vertical stripes with an oval cartouche frame, classic preppy script",
    "olive-gold": "a single watercolour olive sprig with an offset double gold frame on white, formal calligraphy script",
    "oysters-lemons": "hand-drawn navy ink sketches of oysters and a lemon branch, seaside dinner party look",
    "satin-bow": "a blush pink satin bow with a scalloped border on soft white, romantic script",
    "cherry-gingham": "red gingham bands with glossy red cherries, playful handwritten script",
    "toile-bleu": "a French blue toile de Jouy garden band with elegant script, French country look",
    "black-tie-deco": "black with gold Art Deco fan ornaments and double gold frame, roman capitals",
    "antique-botanical": "an antique botanical engraving of wild roses on cream paper texture, vintage calligraphy",
    "eucalyptus-minimal": "a single eucalyptus sprig with lots of white space and a light italic serif, minimalist",
}
LIC = "personal use for your own event; you may not share, resell or redistribute the files"
EDIT = "Editable version: open the PDF in the free Adobe Acrobat Reader (computer, tablet or phone), click a line and type, then print. Typed text uses an elegant italic serif; the design is fixed. Handwrite version: print the blank cards and write by hand."


def catalog():
    rows = []
    for st in STY:
        k, t = st["key"], st["title"]
        base = {"design": t, "theme": LOOK[k], "collection": "Wedding " + t, "section": "Wedding", "licence": LIC, "languages": "English and German versions included", "resolution_dpi": 300, "how_to_edit": EDIT}
        rows.append(dict(slug="wedding-%s-place-cards" % k, title="%s Wedding Place Cards" % t, price=3.49, meta=dict(base, product_type="Wedding Place Cards",
            sizes=["US Letter 8.5x11 in", "A4"], pages=4, contents={"place_cards_per_sheet": 4, "card_size": "3.5 x 2 in folded (3.5 x 4 in flat), fold-over tent card", "versions": "handwrite (blank) and editable name + table number, each in English and German"},
            files="4 PDFs: handwrite US Letter, handwrite A4, editable US Letter, editable A4 (each with an English and a German page)", note="print as many sheets as you need; recommended: 250-300 gsm matte cardstock")))
        rows.append(dict(slug="wedding-%s-menu" % k, title="%s Wedding Menu" % t, price=3.49, meta=dict(base, product_type="Wedding Menu",
            sizes=["4 x 9 in", "US Letter 8.5x11 in (2 per sheet)", "A4 (2 per sheet)"], pages=2, contents={"menu_design": 1, "courses": "starter, main course, dessert (EN) / Vorspeise, Hauptgang, Dessert (DE)", "versions": "handwrite (blank lines) and editable (names, date and every course line)"},
            files="5 PDFs: handwrite US Letter, handwrite A4, editable US Letter, editable A4, single 4x9 in cards for print shops", note="recommended: 250-300 gsm matte cardstock")))
        rows.append(dict(slug="wedding-%s-drinks-menu" % k, title="%s Wedding Wine & Drinks Menu" % t, price=3.49, meta=dict(base, product_type="Wedding Drinks Menu",
            sizes=["4 x 9 in", "US Letter 8.5x11 in (2 per sheet)", "A4 (2 per sheet)"], pages=2, contents={"drinks_menu_design": 1, "sections": "sparkling, white wine, red wine, signature cocktail (EN) / Sekt & Champagner, Weisswein, Rotwein, Signature Cocktail (DE)", "versions": "handwrite (blank lines) and editable"},
            files="5 PDFs: handwrite US Letter, handwrite A4, editable US Letter, editable A4, single 4x9 in cards for print shops", note="recommended: 250-300 gsm matte cardstock")))
        rows.append(dict(slug="wedding-%s-table-set" % k, title="%s Wedding Table Set" % t, price=6.99, meta=dict(base, product_type="Wedding Table Set",
            sizes=["US Letter 8.5x11 in", "A4", "4 x 9 in"], includes=["place cards (3.5 x 2 in tent cards)", "menu (4 x 9 in)", "wine & drinks menu (4 x 9 in)"],
            contents={"designs": "place cards, menu, wine & drinks menu in one matching design", "versions": "handwrite and editable, English and German"},
            files="4 files: ZIP US Letter (all PDFs), ZIP A4 (all PDFs), menu 4x9 in PDF and drinks menu 4x9 in PDF for print shops", savings="set price 6.99 EUR vs 10.47 EUR when bought separately")))
    return rows


def upload(out, keys):
    import upload_kit as uk
    caps = {"01_cover": "Cover", "02_english_german": "English and German versions", "03_how_it_works": "Handwrite or editable"}
    for r in catalog():
        if r["slug"] not in keys:
            continue
        os.environ["JJ_UPLOAD_KEY"] = keys[r["slug"]]
        pdir, ldir = os.path.join(out, r["slug"], "pages"), os.path.join(out, r["slug"], "listing")
        print("==", r["slug"])
        nice = r["title"].replace(" & ", " and ").replace(" ", "_")
        for f in sorted(glob.glob(os.path.join(pdir, "*.pdf")) + glob.glob(os.path.join(pdir, "*.zip"))):
            b = os.path.basename(f)
            if b.endswith(".zip"):
                nm = b
            else:
                tail = b[len(r["slug"]) + 1:] if b.startswith(r["slug"]) else b
                tail = tail.replace("handwrite_letter", "Handwrite_US_Letter").replace("handwrite_a4", "Handwrite_A4").replace("editable_letter", "Editable_US_Letter").replace("editable_a4", "Editable_A4").replace("4x9_print_shop", "4x9in_Print_Shop")
                nm = (nice + "_" + tail) if b.startswith(r["slug"]) else b
            uk.put(f, nm, "download")
        for i, f in enumerate(sorted(glob.glob(os.path.join(ldir, "*.jpg")))[:10]):
            stem = os.path.basename(f)[:-4]
            uk.put(f, os.path.basename(f), "image", rank=i + 1, caption=caps.get(stem, "Preview"))
