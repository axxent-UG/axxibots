#!/usr/bin/env python3
"""Kids party printables (Inkwell Ephemera 'Kids Party' line, pilot theme Dino Party).

Usage: build_party.py <party.json> <assets_dir> <out_dir> [slug ...]
party.json: theme fields (title, headline, motifs, palette, texts) + "products": [{slug, title, kind, price_eur, ...}]
kinds: invitation (editable 5x7), sign (editable 8x10 / 16x20), banner, toppers, food_labels, favor_tags,
       bingo, would_you_rather.
Editable products get fillable PDF form fields (free Adobe Acrobat Reader). Field text uses Helvetica Bold
(the only font every PDF reader can edit with); previews draw sample text with the metric-identical
Liberation Sans Bold so the listing images show exactly what buyers get.
Output per product: <out>/<slug>/pages (JPG pages + PDFs) and <out>/<slug>/listing (cover, inside, previews).
"""
import copy, glob, io, json, math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk
import build_cover as bc

DPI = 300
LETTER = (2550, 3300)
A4 = (2480, 3508)
HERE = os.path.dirname(__file__)
FREDOKA = os.path.join(HERE, "fonts", "Fredoka[wdth,wght].ttf")
SANSB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def F(sz, weight=b"Bold"):
    f = ImageFont.truetype(FREDOKA, int(sz))
    f.set_variation_by_name(weight)
    return f


def S(sz):
    return ImageFont.truetype(SANSB, int(sz))


class Theme:
    def __init__(self, cfg, assets):
        self.cfg = cfg
        self.assets = assets
        self.cache = {}
        p = cfg["palette"]
        self.green, self.teal, self.yellow, self.orange, self.coral, self.purple = [tuple(p[k]) for k in ("green", "teal", "yellow", "orange", "coral", "purple")]
        self.ink = tuple(p["ink"])
        self.cream = tuple(p.get("cream", (255, 251, 240)))
        self.colors = [self.green, self.orange, self.teal, self.coral, self.purple, self.yellow]

    def img(self, key):
        if key not in self.cache:
            self.cache[key] = Image.open(os.path.join(self.assets, key + ".png")).convert("RGBA")
        return self.cache[key]

    def motif(self, key, w, h):
        return bk.fit(bk.trim(self.img(key)), w, h)

    def m(self, i):
        ks = self.cfg["motifs"]
        return ks[i % len(ks)]


# ---------- drawing helpers ----------

def text_c(d, cx, cy, s, font, fill, stroke=0, stroke_fill=None):
    d.text((cx, cy), s, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=stroke_fill, align="center")


def fit_f(d, s, maker, maxw, start):
    sz = start
    while sz > 10:
        f = maker(sz)
        b = d.multiline_textbbox((0, 0), s, font=f, align="center")
        if b[2] - b[0] <= maxw:
            return f
        sz -= 4
    return maker(10)


def rounded(w, h, r, fill, outline=None, width=0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=outline, width=width)
    return im


def pattern(t, key, w, h):
    return bk.cover_crop(t.img(key).convert("RGB"), w, h).convert("RGBA")


def confetti_bg(t, W, H, seed=3, base=None):
    rnd = random.Random(seed)
    bg = Image.new("RGBA", (W, H), base or t.cream + (255,))
    d = ImageDraw.Draw(bg)
    for _ in range(int(W * H / 26000)):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(6, 16)
        c = rnd.choice(t.colors) + (150,)
        if rnd.random() < 0.6:
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            a = rnd.random() * math.pi
            d.line((x - r * 1.6 * math.cos(a), y - r * 1.6 * math.sin(a), x + r * 1.6 * math.cos(a), y + r * 1.6 * math.sin(a)), fill=c, width=max(5, r // 2))
    return bg


def cut_line(page, mask, x, y):
    bk.cut_outline(page, mask, x, y, width=3)


def footer(t, page, W, H, text=None):
    d = ImageDraw.Draw(page)
    text_c(d, W // 2, H - 60, text or (t.cfg["title"] + "  ·  Inkwell Ephemera  ·  for personal use"), F(30, b"Medium"), (150, 150, 150, 255))


def blank(W, H):
    return Image.new("RGBA", (W, H), (255, 255, 255, 255))


# ---------- product pages ----------

def invitation_art(t, w=1500, h=2100, sample=True):
    """5x7 in invitation. Returns (image, fields in px relative to the card)."""
    c = pattern(t, t.cfg["scene"], w, h)
    d = ImageDraw.Draw(c)
    text_c(d, w // 2, 230, t.cfg["headline"], F(250), t.yellow + (255,), 16, t.green + (255,))
    text_c(d, w // 2, 425, t.cfg["subline"], F(105), (255, 255, 255, 255), 10, t.teal + (255,))
    px0, py0, px1, py1 = 140, 540, w - 140, 1700
    panel = rounded(px1 - px0, py1 - py0, 70, t.cream + (240,), t.teal + (255,), 12)
    c.alpha_composite(panel, (px0, py0))
    d = ImageDraw.Draw(c)
    fx0, fw = px0 + 70, (px1 - px0) - 140
    fields = [
        ("child", "LEO IS TURNING 5!", (fx0, 600, fw, 150), 34),
        ("date", "Saturday, May 16th", (fx0, 920, fw, 100), 22),
        ("time", "2:00 - 5:00 PM", (fx0, 1030, fw, 100), 22),
        ("place", "Dino Park, 123 Jurassic Lane", (fx0, 1180, fw, 100), 20),
        ("rsvp", "RSVP to Mom · 555-123-4567", (fx0, 1460, fw, 90), 17),
    ]
    text_c(d, w // 2, 815, t.cfg["invite_line"], F(62, b"SemiBold"), t.orange + (255,))
    for yy in (1330,):
        for i, k in enumerate(["m14_footprints"]):
            mo = t.motif(k, 520, 120)
            c.alpha_composite(mo, ((w - mo.width) // 2, yy - mo.height // 2 + 10))
    # dinos around the panel
    for k, x, y, s in [("m01_trex", 40, 1500, 560), ("m02_triceratops", w - 560, 1610, 480), ("m05_pterodactyl", w - 470, 470, 380), ("m12_balloons", 20, 380, 300)]:
        mo = t.motif(k, s, s)
        c.alpha_composite(mo, (x, y if y + mo.height < h else h - mo.height - 20))
    if sample:
        draw_fields(c, fields)
    return c, fields


def draw_fields(img, fields, dx=0, dy=0):
    d = ImageDraw.Draw(img)
    for _, val, (x, y, w, h), pt in fields:
        px = int(pt * 300 / 72)
        f = S(px)
        while d.textlength(val, font=f) > w - 20 and px > 20:
            px -= 4
            f = S(px)
        d.text((dx + x + w // 2, dy + y + h // 2), val, font=f, fill=(46, 64, 52, 255), anchor="mm")


def sign_art(t, w=2400, h=3000, sample=True):
    c = pattern(t, t.cfg["scene"], w, h)
    d = ImageDraw.Draw(c)
    text_c(d, w // 2, 330, "WELCOME TO", F(170), (255, 255, 255, 255), 14, t.teal + (255,))
    panel = rounded(w - 360, 1500, 90, t.cream + (235,), t.teal + (255,), 16)
    c.alpha_composite(panel, (180, 520))
    d = ImageDraw.Draw(c)
    fields = [("name", "LEO'S", (300, 600, w - 600, 330), 80)]
    text_c(d, w // 2, 1150, t.cfg["sign_title"], F(330), t.yellow + (255,), 22, t.green + (255,))
    fields.append(("line", "ROAR-SOME 5TH BIRTHDAY", (300, 1480, w - 600, 260), 46))
    for k, x, y, s in [("m04_longneck", w - 900, 1900, 1000), ("m01_trex", 60, 1950, 950), ("m07_eggs", w // 2 - 260, 2450, 520), ("m05_pterodactyl", 80, 30, 520), ("m12_balloons", w - 520, 40, 480)]:
        mo = t.motif(k, s, s)
        c.alpha_composite(mo, (x, min(y, h - mo.height - 30)))
    if sample:
        draw_fields(c, fields)
    return c, fields


def pennant(t, w, h, content, i):
    """Triangle pennant pointing down. content: ('char', 'A') | ('motif', key) | ('blank', None)."""
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (w - 1, 0), (w // 2, h - 1)], fill=255)
    keys = t.cfg["papers"]
    p = pattern(t, keys[i % len(keys)], w, h)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(p, (0, 0), mask)
    d = ImageDraw.Draw(out)
    d.rectangle((0, 0, w, 70), fill=t.colors[i % len(t.colors)] + (255,))
    for hx in (90, w - 90):
        d.ellipse((hx - 18, 35 - 18, hx + 18, 35 + 18), fill=(255, 255, 255, 255))
    r = int(w * 0.24)
    cx, cy = w // 2, int(h * 0.38)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255), outline=t.colors[(i + 2) % len(t.colors)] + (255,), width=16)
    kind, val = content
    if kind == "char":
        text_c(d, cx, cy + 10, val, F(int(r * 1.45)), t.colors[i % len(t.colors)] + (255,), 10, (255, 255, 255, 255))
    elif kind == "motif":
        mo = t.motif(val, int(r * 1.6), int(r * 1.6))
        out.alpha_composite(mo, (cx - mo.width // 2, cy - mo.height // 2))
    return out, mask


def page_banner(t, items, start, W, H):
    p = blank(W, H)
    w, h = int(W * 0.78), int(H * 0.44)
    for j, it in enumerate(items):
        x, y = (W - w) // 2, 120 + j * (h + 140)
        pc, mask = pennant(t, w, h, it, start + j)
        p.alpha_composite(pc, (x, y))
        cut_line(p, mask, x, y)
    footer(t, p, W, H)
    return p


def topper(t, dia, content, i):
    out = Image.new("RGBA", (dia, dia), (0, 0, 0, 0))
    mask = Image.new("L", (dia, dia), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, dia - 1, dia - 1), fill=255)
    keys = t.cfg["papers"]
    out.paste(pattern(t, keys[i % len(keys)], dia, dia), (0, 0), mask)
    d = ImageDraw.Draw(out)
    ins = int(dia * 0.1)
    d.ellipse((ins, ins, dia - ins, dia - ins), fill=(255, 255, 255, 255), outline=t.colors[i % len(t.colors)] + (255,), width=10)
    kind, val = content
    if kind == "motif":
        mo = t.motif(val, int(dia * 0.66), int(dia * 0.66))
        out.alpha_composite(mo, ((dia - mo.width) // 2, (dia - mo.height) // 2))
    elif kind == "num":
        text_c(d, dia // 2, dia // 2 + 6, val, F(int(dia * 0.5)), t.colors[i % len(t.colors)] + (255,), 8, t.cream + (255,))
    else:
        f = fit_f(d, val, F, int(dia * 0.66), int(dia * 0.2))
        text_c(d, dia // 2, dia // 2, val, f, t.colors[(i + 1) % len(t.colors)] + (255,), 4, (255, 255, 255, 255))
    return out, mask


def page_toppers(t, items, W, H):
    p = blank(W, H)
    dia, cols, rows, gap = 570, 4, 5, 40
    mx = (W - cols * dia - (cols - 1) * gap) // 2
    my = (H - rows * dia - (rows - 1) * gap) // 2 - 20
    for i, it in enumerate(items[: cols * rows]):
        r, c = divmod(i, cols)
        x, y = mx + c * (dia + gap), my + r * (dia + gap)
        tp, mask = topper(t, dia, it, i)
        p.alpha_composite(tp, (x, y))
        cut_line(p, mask, x, y)
    footer(t, p, W, H)
    return p


def tent_card(t, w, h, label, i, motif):
    """Flat tent card: bottom half front, top half the same design upside down (readable from both sides)."""
    half = Image.new("RGBA", (w, h // 2), (255, 255, 255, 255))
    d = ImageDraw.Draw(half)
    band = pattern(t, t.cfg["papers"][i % len(t.cfg["papers"])], w, 110)
    half.alpha_composite(band, (0, h // 2 - 110))
    mo = t.motif(motif, 360, 380)
    half.alpha_composite(mo, (30, (h // 2 - 110 - mo.height) // 2 + 10))
    if label:
        lab = label.replace(" ", "\n", 1) if d.textlength(label, font=F(150)) > w - 450 else label
        f = fit_f(d, lab, F, w - 450, 150)
        text_c(d, 400 + (w - 400) // 2, (h // 2 - 110) // 2 + 10, lab, f, t.colors[i % len(t.colors)] + (255,), 6, (255, 255, 255, 255))
    card = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    card.alpha_composite(half.rotate(180), (0, 0))
    card.alpha_composite(half, (0, h // 2))
    d = ImageDraw.Draw(card)
    for x in range(0, w, 40):
        d.line((x, h // 2, x + 20, h // 2), fill=(170, 170, 170, 255), width=3)
    return card


def page_food(t, labels, start, W, H, editable=False):
    p = blank(W, H)
    w, h, cols, rows, gx, gy = 1150, 1460, 2, 2, 60, 100
    mx, my = (W - cols * w - gx) // 2, (H - rows * h - gy) // 2 - 30
    fields = []
    for j, lab in enumerate(labels):
        r, c = divmod(j, cols)
        x, y = mx + c * (w + gx), my + r * (h + gy)
        card = tent_card(t, w, h, None if editable else lab, start + j, t.m(start + j))
        p.alpha_composite(card, (x, y))
        cut_line(p, Image.new("L", (w, h), 255), x, y)
        if editable:
            fields.append(("food%d" % (j + 1), lab, (x + 380, y + h // 2 + 60, w - 420, 200), 28))
    footer(t, p, W, H, t.cfg["title"] + "  ·  fold on the dashed line  ·  for personal use")
    return p, fields


def page_tags(t, texts, start, W, H):
    p = blank(W, H)
    w, h, cols, rows, gx, gy = 640, 1000, 3, 3, 90, 60
    mx, my = (W - cols * w - (cols - 1) * gx) // 2, (H - rows * h - (rows - 1) * gy) // 2 - 20
    for j in range(cols * rows):
        r, c = divmod(j, cols)
        x, y = mx + c * (w + gx), my + r * (h + gy)
        i = start + j
        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        cut = 90
        md.polygon([(cut, 0), (w - cut, 0), (w - 1, cut), (w - 1, h - 1), (0, h - 1), (0, cut)], fill=255)
        tag = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tag.paste(pattern(t, t.cfg["papers"][i % len(t.cfg["papers"])], w, h), (0, 0), mask)
        d = ImageDraw.Draw(tag)
        d.rounded_rectangle((45, 170, w - 45, h - 45), 40, fill=(255, 255, 255, 255))
        d.ellipse((w // 2 - 30, 60, w // 2 + 30, 120), fill=(255, 255, 255, 255), outline=t.colors[i % 6] + (255,), width=8)
        mo = t.motif(t.m(i), w - 180, 420)
        tag.alpha_composite(mo, ((w - mo.width) // 2, 200 + (420 - mo.height) // 2))
        s = texts[i % len(texts)]
        s = s.replace(" ", "\n", 1) if len(s) > 14 else s
        f = fit_f(d, s, F, w - 120, 96)
        text_c(d, w // 2, 790, s, f, t.colors[i % 6] + (255,), 3, (255, 255, 255, 255))
        p.alpha_composite(tag, (x, y))
        cut_line(p, mask, x, y)
    footer(t, p, W, H)
    return p


def page_bingo(t, cards, W, H):
    p = blank(W, H)
    for j, keys in enumerate(cards):
        y0 = 90 + j * (H // 2 - 20)
        ch = H // 2 - 160
        cw = W - 260
        card = rounded(cw, ch, 60, t.cream + (255,), t.green + (255,), 14)
        d = ImageDraw.Draw(card)
        text_c(d, cw // 2, 120, t.cfg["bingo_title"], F(130), t.orange + (255,), 10, (255, 255, 255, 255))
        cell = 400
        gx0 = (cw - 3 * cell) // 2
        gy0 = 230
        for k, key in enumerate(keys):
            r, c = divmod(k, 3)
            x, y = gx0 + c * cell, gy0 + r * cell
            d.rounded_rectangle((x + 8, y + 8, x + cell - 8, y + cell - 8), 30, fill=(255, 255, 255, 255), outline=t.colors[k % 6] + (255,), width=8)
            mo = t.motif(key, cell - 80, cell - 80)
            card.alpha_composite(mo, (x + (cell - mo.width) // 2, y + (cell - mo.height) // 2))
        p.alpha_composite(card, (130, y0))
    footer(t, p, W, H)
    return p


def page_calls(t, W, H):
    p = blank(W, H)
    d = ImageDraw.Draw(p)
    text_c(d, W // 2, 170, "Calling Cards", F(120), t.green + (255,))
    text_c(d, W // 2, 290, "cut apart, mix in a bowl, draw one at a time", F(54, b"Medium"), (120, 120, 120, 255))
    keys = t.cfg["motifs"][:16]
    cell, cols = 520, 4
    mx = (W - cols * cell) // 2
    for k, key in enumerate(keys):
        r, c = divmod(k, cols)
        x, y = mx + c * cell, 400 + r * cell
        d.rounded_rectangle((x + 10, y + 10, x + cell - 10, y + cell - 10), 30, outline=t.colors[k % 6] + (255,), width=6)
        mo = t.motif(key, cell - 120, cell - 170)
        p.alpha_composite(mo, (x + (cell - mo.width) // 2, y + 30))
        text_c(d, x + cell // 2, y + cell - 70, t.cfg["motif_names"][key], F(46, b"SemiBold"), t.ink + (255,))
    footer(t, p, W, H)
    return p


def page_wyr(t, qs, start, W, H):
    p = blank(W, H)
    w, h, cols, rows, gx, gy = 1150, 700, 2, 4, 60, 50
    mx, my = (W - cols * w - gx) // 2, (H - rows * h - (rows - 1) * gy) // 2 - 20
    for j, q in enumerate(qs):
        r, c = divmod(j, cols)
        x, y = mx + c * (w + gx), my + r * (h + gy)
        i = start + j
        card = rounded(w, h, 50, (255, 255, 255, 255), t.colors[i % 6] + (255,), 14)
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((14, 14, w - 15, 130), 40, fill=t.colors[i % 6] + (255,))
        text_c(d, w // 2, 74, "Would you rather...", F(64), (255, 255, 255, 255))
        mo = t.motif(t.m(i), 230, 230)
        card.alpha_composite(mo, (w - mo.width - 30, h - mo.height - 30))
        a, b = q
        f = F(60, b"SemiBold")
        y1 = 250
        for line in wrap(d, a, f, w - 320):
            text_c(d, (w - 230) // 2 + 20, y1, line, f, t.ink + (255,))
            y1 += 70
        text_c(d, (w - 230) // 2 + 20, y1 + 20, "OR", F(64), t.colors[(i + 1) % 6] + (255,))
        y1 += 110
        for line in wrap(d, b, f, w - 320):
            text_c(d, (w - 230) // 2 + 20, y1, line, f, t.ink + (255,))
            y1 += 70
        p.alpha_composite(card, (x, y))
        cut_line(p, Image.new("L", (w, h), 255), x, y)
    footer(t, p, W, H)
    return p


def wrap(d, s, f, maxw):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        n = (cur + " " + wd).strip()
        if d.textlength(n, font=f) <= maxw:
            cur = n
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


# ---------- PDFs ----------

def pdf_pages(pages, path, page_in=None, editable=None):
    """pages: list of PIL images (300 dpi unless page_in given). editable: {page_index: [(name, value, (x,y,w,h) px, pt)]}"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import Color
    c = None
    for n, im in enumerate(pages):
        wpt, hpt = page_in if page_in else (im.width * 72 / DPI, im.height * 72 / DPI)
        if page_in:
            wpt, hpt = page_in[0] * 72, page_in[1] * 72
        if c is None:
            c = canvas.Canvas(path, pagesize=(wpt, hpt))
        else:
            c.setPageSize((wpt, hpt))
        b = io.BytesIO()
        im.convert("RGB").save(b, "JPEG", quality=90)
        c.drawImage(ImageReader(io.BytesIO(b.getvalue())), 0, 0, wpt, hpt)
        sx, sy = wpt / im.width, hpt / im.height
        for name, val, (x, y, w, h), pt in (editable or {}).get(n, []):
            scale = sx * DPI / 72
            c.acroForm.textfield(name=name if n == 0 else "%s_p%d" % (name, n + 1), value=val, x=x * sx, y=hpt - (y + h) * sy, width=w * sx, height=h * sy,
                                 fontName="Helvetica-Bold", fontSize=round(pt * scale, 1), textColor=Color(46 / 255, 64 / 255, 52 / 255),
                                 borderWidth=0, fillColor=None, borderColor=None, forceBorder=False, maxlen=60)
        c.showPage()
    c.save()
    if editable:
        center_fields(path)


def center_fields(path):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, NumberObject, BooleanObject
    r = PdfReader(path)
    w = PdfWriter(clone_from=r)
    for page in w.pages:
        for a in page.get("/Annots", []) or []:
            o = a.get_object()
            if o.get("/FT") == "/Tx":
                o[NameObject("/Q")] = NumberObject(1)
    if "/AcroForm" in w._root_object:
        w._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
    with open(path, "wb") as f:
        w.write(f)


def on_sheet(card, W, H, fields=None):
    """Place a card centred on a sheet with crop marks; returns sheet and shifted fields."""
    p = blank(W, H)
    x, y = (W - card.width) // 2, (H - card.height) // 2
    p.alpha_composite(card, (x, y))
    d = ImageDraw.Draw(p)
    for (cx, cy) in [(x, y), (x + card.width, y), (x, y + card.height), (x + card.width, y + card.height)]:
        d.line((cx - 80 if cx == x else cx + 20, cy, cx - 20 if cx == x else cx + 80, cy), fill=(120, 120, 120, 255), width=3)
        d.line((cx, cy - 80 if cy == y else cy + 20, cx, cy - 20 if cy == y else cy + 80), fill=(120, 120, 120, 255), width=3)
    f2 = [(n, v, (fx + x, fy + y, fw, fh), pt) for n, v, (fx, fy, fw, fh), pt in (fields or [])]
    return p, f2


# ---------- products ----------

def build_product(t, prod, out):
    pdir = os.path.join(out, prod["slug"], "pages")
    os.makedirs(pdir, exist_ok=True)
    k = prod["kind"]
    slug = prod["slug"]
    previews = []  # letter-size preview images (with sample text)
    if k == "invitation":
        card_s, fields = invitation_art(t, sample=True)
        card_e, _ = invitation_art(t, sample=False)
        pdf_pages([card_e], os.path.join(pdir, "%s_5x7.pdf" % slug), page_in=(5, 7), editable={0: fields})
        for nm, (W, H) in (("letter", LETTER), ("a4", A4)):
            sheet, f2 = on_sheet(card_e, W, H, fields)
            pdf_pages([sheet], os.path.join(pdir, "%s_%s.pdf" % (slug, nm)), editable={0: f2})
        card_s.convert("RGB").save(os.path.join(pdir, "%s_sample_5x7.jpg" % slug), quality=92, dpi=(DPI, DPI))
        previews = [card_s]
    elif k == "sign":
        art_s, fields = sign_art(t, sample=True)
        art_e, _ = sign_art(t, sample=False)
        pdf_pages([art_e], os.path.join(pdir, "%s_8x10.pdf" % slug), page_in=(8, 10), editable={0: fields})
        pdf_pages([art_e], os.path.join(pdir, "%s_16x20.pdf" % slug), page_in=(16, 20), editable={0: fields})
        sheet, f2 = on_sheet(art_e, *LETTER, fields)
        pdf_pages([sheet], os.path.join(pdir, "%s_letter.pdf" % slug), editable={0: f2})
        art_s.convert("RGB").save(os.path.join(pdir, "%s_sample_8x10.jpg" % slug), quality=92, dpi=(DPI, DPI))
        previews = [art_s]
    else:
        for nm, (W, H) in (("letter", LETTER), ("a4", A4)):
            pages, editable = [], {}
            if k == "banner":
                items = [("char", ch) for ch in "HAPPY"] + [("motif", "m01_trex")] + [("char", ch) for ch in "BIRTHDAY"] + [("motif", "m04_longneck")] \
                    + [("char", str(n)) for n in range(1, 10)] + [("blank", None), ("blank", None), ("motif", "m02_triceratops")]
                for s in range(0, len(items), 2):
                    pages.append(page_banner(t, items[s:s + 2], s, W, H))
            elif k == "toppers":
                ms = [("motif", m) for m in t.cfg["motifs"][:16]]
                words = [("text", "Happy\nBirthday"), ("text", "ROAR!"), ("text", "Dino-mite!"), ("text", "Party\nAnimal")]
                pages.append(page_toppers(t, ms[:16] + words, W, H))
                pages.append(page_toppers(t, [x for pair in zip(ms[:10], [("text", "Happy\nBirthday"), ("text", "ROAR!")] * 5) for x in pair], W, H))
                pages.append(page_toppers(t, [("num", str(n)) for n in range(1, 10)] + [("num", str(n)) for n in range(1, 10)] + [("text", "ROAR!"), ("text", "Happy\nBirthday")], W, H))
            elif k == "food_labels":
                labs = t.cfg["food_labels"]
                for s in range(0, len(labs), 4):
                    pg, _ = page_food(t, labs[s:s + 4], s, W, H)
                    pages.append(pg)
                pg, fl = page_food(t, ["Type your food here"] * 4, 0, W, H, editable=True)
                editable[len(pages)] = fl
                pages.append(pg)
            elif k == "favor_tags":
                pages = [page_tags(t, t.cfg["tag_texts"], s, W, H) for s in (0, 9)]
            elif k == "bingo":
                rnd = random.Random(7)
                cards = [rnd.sample(t.cfg["motifs"][:16], 9) for _ in range(10)]
                pages = [page_bingo(t, cards[s:s + 2], W, H) for s in range(0, 10, 2)] + [page_calls(t, W, H)]
            elif k == "would_you_rather":
                qs = t.cfg["wyr"]
                pages = [page_wyr(t, qs[s:s + 8], s, W, H) for s in range(0, len(qs), 8)]
            else:
                raise ValueError(k)
            for n, pg in enumerate(pages):
                pg.convert("RGB").save(os.path.join(pdir, "%s_%02d_%s.jpg" % (slug, n + 1, nm)), quality=90, dpi=(DPI, DPI))
            pdf_pages(pages, os.path.join(pdir, "%s_%s.pdf" % (slug, nm)), editable=editable or None)
            if nm == "letter":
                previews = pages
                if editable:  # preview of the editable page with sample text
                    for idx, fl in editable.items():
                        pv = pages[idx].copy()
                        draw_fields(pv, [(a, "Your Food Here", b, c) for a, _, b, c in fl])
                        previews[idx] = pv
    return pdir, previews


# ---------- listing images ----------

def party_badge(t, title, sub, w=1400, h=520):
    b = rounded(w, h, 80, (255, 255, 255, 255), t.green + (255,), 14)
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((30, 30, w - 31, h - 31), 60, outline=t.yellow + (255,), width=6)
    f1 = fit_f(d, sub.upper(), lambda s: F(s, b"SemiBold"), w - 240, 56)
    text_c(d, w // 2, 105, sub.upper(), f1, t.orange + (255,))
    f2 = fit_f(d, title, F, w - 160, 170)
    text_c(d, w // 2, h // 2 + 15, title, f2, t.green + (255,), 6, (255, 255, 255, 255))
    text_c(d, w // 2, h - 85, "INKWELL EPHEMERA · KIDS PARTY", F(40, b"Medium"), (140, 140, 140, 255))
    return b


def cover(t, prod, previews, ldir):
    W, H = bc.W, bc.H
    c = confetti_bg(t, W, H, seed=sum(map(ord, prod["slug"])) % 97, base=(236, 248, 238, 255))
    n = len(previews)
    spots = [(560, 1000, 8), (2440, 1000, -8), (1050, 900, -4), (1950, 900, 5), (1500, 820, 1)]
    for i, im in enumerate(previews[:5]):
        x, y, a = spots[i] if n > 1 else (1500, 1000, 0)
        w = 900 if n > 2 else 1150
        if n == 1:
            x, y, a, w = 2170, 1120, 4, int(1500 * im.width / im.height) if im.height > im.width else 1300
        piece = im.convert("RGBA").resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        bc.paste_rot(c, piece, x, y, a)
    for k, (x, y, s, a) in zip(prod.get("cover_motifs", ["m01_trex", "m12_balloons", "m02_triceratops"]), [(380, 1880, 650, 6), (2680, 420, 480, -6), (2650, 1880, 560, -6)]):
        mo = t.motif(k, s, s)
        bc.paste_rot(c, mo, x, y, a, shadow=False)
    if n > 1:  # on single-artwork covers the ribbon would hide the artwork; the badge says it all
        bc.RIBBON = t.teal
        bc.ribbon(c, prod.get("ribbon", "DIGITAL DOWNLOAD · YOU PRINT"))
    bx = 800 if n == 1 else W // 2
    bc.paste_rot(c, party_badge(t, prod["badge_title"], prod["badge_sub"], w=1180 if n == 1 else 1400), bx, 1000 if n == 1 else 1060, 0)
    bc.BAND = t.teal
    bc.info_band(c, prod["cover_lines"])
    c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)


def inside(t, prod, previews, ldir):
    W, H = bc.W, bc.H
    c = confetti_bg(t, W, H, seed=9, base=(236, 248, 238, 255))
    n = len(previews)
    cols = min(n, 3 if n <= 3 else (4 if n <= 8 else 5))
    rows = (n + cols - 1) // cols
    th = min(int((H - 520) / rows) - 60, 1500)
    gx = None
    ims = []
    for im in previews:
        tw = int(th * im.width / im.height)
        ims.append(im.convert("RGBA").resize((tw, th), Image.LANCZOS))
    top = 230
    gy = (H - 260 - top - rows * th) // (rows + 1)
    for r in range(rows):
        row = ims[r * cols:(r + 1) * cols]
        tot = sum(i.width for i in row)
        g = (W - tot) // (len(row) + 1)
        x = g
        for im in row:
            sh, pad = bk.drop_shadow(im, off=(8, 12), blur=12, alpha=110)
            c.alpha_composite(sh, (x - pad, top + gy + r * (th + gy) - pad))
            x += im.width + g
    d = ImageDraw.Draw(c)
    text_c(d, W // 2, 120, prod.get("inside_title", "What's inside: %d printable page%s" % (n, "s" if n != 1 else "")), F(92), t.green + (255,))
    bc.BAND = t.teal
    bc.info_band(c, prod["inside_lines"])
    c.convert("RGB").save(os.path.join(ldir, "02_whats_inside.jpg"), quality=90)
    for i, im in enumerate(previews[:6]):
        bg = confetti_bg(t, W, H, seed=20 + i, base=(236, 248, 238, 255))
        h = int(H * 0.86)
        w = int(im.width * h / im.height)
        if w > W * 0.9:
            w = int(W * 0.9)
            h = int(im.height * w / im.width)
        pim = im.convert("RGBA").resize((w, h), Image.LANCZOS)
        sh, pad = bk.drop_shadow(pim, off=(12, 16), blur=16, alpha=120)
        bg.alpha_composite(sh, ((W - sh.width) // 2, (H - sh.height) // 2))
        wm = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        dw = ImageDraw.Draw(wm)
        for y in range(-200, H + 400, 520):
            for x in range(-400, W + 400, 1100):
                dw.text((x, y), "PREVIEW", font=F(110), fill=(255, 255, 255, 70))
        bg.alpha_composite(wm.rotate(25, resample=Image.BICUBIC))
        bg.convert("RGB").save(os.path.join(ldir, "%02d_page_%d.jpg" % (3 + i, i + 1)), quality=88)


def main():
    cfg = json.load(open(sys.argv[1]))
    assets, out = sys.argv[2], sys.argv[3]
    only = sys.argv[4:] or None
    t = Theme(cfg, assets)
    for prod in cfg["products"]:
        if only and prod["slug"] not in only:
            continue
        pdir, previews = build_product(t, prod, out)
        ldir = os.path.join(out, prod["slug"], "listing")
        os.makedirs(ldir, exist_ok=True)
        cover(t, prod, previews, ldir)
        inside(t, prod, previews, ldir)
        print(prod["slug"], "ok", len(previews))


if __name__ == "__main__":
    main()


def build_bundle(t, cfg, spec, out):
    """Party bundle: all component products in max. 5 Etsy files (editable PDFs kept editable)."""
    import zipfile
    from pypdf import PdfWriter, PdfReader
    comps = [p for p in cfg["products"] if p["slug"] in spec["components"]]
    bdir = os.path.join(out, spec["slug"])
    pdir, ldir = os.path.join(bdir, "pages"), os.path.join(bdir, "listing")
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(ldir, exist_ok=True)
    name = spec["title"].replace(" ", "_")
    files = []
    editable = [p for p in comps if p["kind"] in ("invitation", "sign")]
    zpath = os.path.join(pdir, name + "_Editable_Invitation_and_Sign.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in editable:
            for f in sorted(glob.glob(os.path.join(out, p["slug"], "pages", "*.pdf"))):
                z.write(f, os.path.basename(f))
    files.append(zpath)
    groups = [("Decorations", [p for p in comps if p["kind"] in ("banner", "toppers", "food_labels", "favor_tags")]),
              ("Games", [p for p in comps if p["kind"] in ("bingo", "would_you_rather")])]
    for size, label in (("letter", "US_Letter"), ("a4", "A4")):
        for gname, members in groups:
            if not members:
                continue
            path = os.path.join(pdir, "%s_%s_%s.pdf" % (name, gname, label))
            for q in (85, 78, 70):
                w = PdfWriter()
                for p in members:
                    w.append(PdfReader(os.path.join(out, p["slug"], "pages", "%s_%s.pdf" % (p["slug"], size))))
                for pg in w.pages:
                    for img in pg.images:
                        img.replace(img.image.convert("RGB"), quality=q)
                w.set_need_appearances_writer(True)
                with open(path, "wb") as f:
                    w.write(f)
                if os.path.getsize(path) < 19_000_000:
                    break
            files.append(path)
    # listing images
    W, H = bc.W, bc.H
    covers = [Image.open(os.path.join(out, p["slug"], "listing", "01_cover.jpg")).convert("RGBA") for p in comps]
    c = confetti_bg(t, W, H, seed=5, base=(236, 248, 238, 255))
    spots = [(620, 620, -7), (1500, 520, 3), (2380, 620, 7), (620, 1500, 5), (2380, 1500, -5), (1500, 1650, -2), (1050, 1100, 4), (1950, 1100, -4)]
    for im, (x, y, a) in zip(covers, spots):
        piece = im.resize((900, 720), Image.LANCZOS)
        ImageDraw.Draw(piece).rectangle((0, 0, 899, 719), outline=(255, 255, 255, 255), width=12)
        bc.paste_rot(c, piece, x, y, a)
    bc.paste_rot(c, party_badge(t, spec["badge_title"], spec["badge_sub"]), W // 2, 1080, 0)
    bc.BAND = t.teal
    bc.info_band(c, spec["cover_lines"])
    c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)
    c = confetti_bg(t, W, H, seed=8, base=(236, 248, 238, 255))
    d = ImageDraw.Draw(c)
    text_c(d, W // 2, 120, "What's inside: %d party printables" % len(comps), F(92), t.green + (255,))
    cols, tw, th = 4, 640, 512
    gx = (W - cols * tw) // (cols + 1)
    for i, (im, p) in enumerate(zip(covers, comps)):
        r, k = divmod(i, cols)
        x, y = gx + k * (tw + gx), 280 + r * (th + 230)
        sh, pad = bk.drop_shadow(im.resize((tw, th), Image.LANCZOS), off=(8, 12), blur=12, alpha=110)
        c.alpha_composite(sh, (x - pad, y - pad))
        text_c(d, x + tw // 2, y + th + 70, p["badge_title"], F(50, b"SemiBold"), t.ink + (255,))
    bc.info_band(c, spec["inside_lines"])
    c.convert("RGB").save(os.path.join(ldir, "02_whats_inside.jpg"), quality=90)
    k = 3
    for p in comps:
        src = os.path.join(out, p["slug"], "listing", "03_page_1.jpg")
        if os.path.exists(src) and k <= 10:
            Image.open(src).save(os.path.join(ldir, "%02d_%s.jpg" % (k, p["slug"].split("-", 2)[-1])), quality=88)
            k += 1
    return [(os.path.basename(f), os.path.getsize(f)) for f in files]


def upload(cfg, out, keys):
    """Upload built party products (files + listing images). keys: {slug: upload_key}."""
    import upload_kit as uk
    items = [(p, False) for p in cfg["products"]] + [(b, True) for b in cfg.get("bundles", [])]
    for p, is_bundle in items:
        if p["slug"] not in keys:
            continue
        os.environ["JJ_UPLOAD_KEY"] = keys[p["slug"]]
        pdir, ldir = os.path.join(out, p["slug"], "pages"), os.path.join(out, p["slug"], "listing")
        name = p["title"].replace(" ", "_")
        print("==", p["slug"])
        if is_bundle:
            for f in sorted(glob.glob(os.path.join(pdir, "*.zip")) + glob.glob(os.path.join(pdir, "*.pdf"))):
                uk.put(f, os.path.basename(f), "download")
        elif p["kind"] in ("invitation", "sign"):
            for f in sorted(glob.glob(os.path.join(pdir, "*.pdf"))):
                size = os.path.basename(f)[len(p["slug"]) + 1:-4]
                uk.put(f, "%s_Editable_%s.pdf" % (name, {"letter": "US_Letter", "a4": "A4"}.get(size, size)), "download")
            for f in glob.glob(os.path.join(pdir, "*sample*.jpg")):
                uk.put(f, "%s_Sample.jpg" % name, "download")
        else:
            uk.put(os.path.join(pdir, "%s_letter.pdf" % p["slug"]), name + "_US_Letter.pdf", "download")
            uk.put(os.path.join(pdir, "%s_a4.pdf" % p["slug"]), name + "_A4.pdf", "download")
            z = uk.make_jpg_zip({"slug": p["slug"], "title": p["title"]}, pdir, os.path.join(pdir, name + "_JPG_US_Letter.zip"))
            uk.put(z, os.path.basename(z), "download")
        caps = {"01_cover": "Cover", "02_whats_inside": "What's inside"}
        for i, f in enumerate(sorted(glob.glob(os.path.join(ldir, "*.jpg")))[:10]):
            stem = os.path.basename(f)[:-4]
            uk.put(f, os.path.basename(f), "image", rank=i + 1, caption=caps.get(stem, "Preview"))
