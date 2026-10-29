#!/usr/bin/env python3
"""Wedding line v3 (owner inspiration 29.10.2026): velvet table numbers with gold-foil look in arch / oval /
rectangle shapes, signature-script place cards, greenery diamond frame. Names are set in the real script
fonts by the online editor; this module renders the designs (with or without text) and the style board.

Usage: wedding_v3.py <assets_dir> <out_dir>   (renders the style board)
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk
from wedding_styles2 import linen, tent, shadow_drop

FD = os.path.join(os.path.dirname(__file__), "fonts")


def font(name, sz, var=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(sz))
    if var:
        try:
            f.set_variation_by_name(var)
        except Exception:
            pass
    return f


# ---------- materials ----------

def noise(w, h, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255


def velvet(w, h, rgb, seed=1):
    base = np.ones((h, w, 3), np.float32) * np.array(rgb, np.float32)
    n1 = noise(w, h, 160, seed) - 0.5
    n2 = noise(w, h, 40, seed + 1) - 0.5
    fine = np.random.default_rng(seed + 2).normal(0, 1, (h, w)).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    sheen = np.exp(-(((xx / w - 0.35) * 1.4) ** 2 + ((yy / h - 0.3) * 1.1) ** 2) * 2.2)  # soft light from top left
    k = 0.45 if sum(rgb) > 500 else 1.0  # light velvet shows blotches more: calmer texture
    lum = 1 + k * (0.10 * n1 + 0.05 * n2) + 0.16 * k * sheen - 0.10 * k * (yy / h)
    img = base * lum[..., None] + fine[..., None] * 3.5
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    return im.convert("RGBA")


def gold(w, h, seed=3):
    """Gold-foil look: warm metallic gradient with soft highlights."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (xx / w * 0.7 + yy / h * 0.3)
    band = 0.5 + 0.5 * np.sin(t * 9 + noise(w, h, 90, seed) * 3)
    dark, mid, light = np.array([150, 110, 48], np.float32), np.array([198, 160, 84], np.float32), np.array([240, 214, 146], np.float32)
    col = np.where(band[..., None] < 0.5, dark + (mid - dark) * (band[..., None] * 2), mid + (light - mid) * ((band[..., None] - 0.5) * 2))
    return Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert("RGBA")


def paint(card, mask, material):
    """Paint material (RGBA image same size as card) through an L mask."""
    layer = material.copy()
    layer.putalpha(mask)
    card.alpha_composite(layer)


# ---------- shapes ----------

def shape_mask(kind, w, h, inset=0):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    x0, y0, x1, y1 = inset, inset, w - 1 - inset, h - 1 - inset
    if kind == "arch":
        r = (x1 - x0) // 2
        d.rectangle((x0, y0 + r, x1, y1), fill=255)
        d.ellipse((x0, y0, x1, y0 + 2 * r), fill=255)
    elif kind == "oval":
        d.ellipse((x0, y0, x1, y1), fill=255)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=max(10, int(w * 0.035)), fill=255)
    return m


def outline(kind, w, h, inset, width):
    a = shape_mask(kind, w, h, inset)
    b = shape_mask(kind, w, h, inset + width)
    return ImageChops.subtract(a, b)


# ---------- products ----------

VELVET = {"cream": (233, 224, 205), "emerald": (26, 74, 52), "burgundy": (118, 22, 34), "navy": (28, 38, 70), "blush": (214, 176, 168)}


def table_number(shape, color, number, word="TABLE", w=1500, h=2100):
    """5 x 7 in table number: velvet in the given shape, gold frame, spaced caps + italic numeral."""
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vel = velvet(w, h, VELVET[color], seed=hash(color) % 50)
    sm = shape_mask(shape, w, h)
    vel.putalpha(sm)
    card.alpha_composite(vel)
    g = gold(w, h)
    paint(card, outline(shape, w, h, 46, 6), g)
    tm = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(tm)
    cy = int(h * (0.34 if shape == "arch" else 0.30))
    d.text((w // 2, cy), " ".join(word), font=font("CormorantGaramond[wght].ttf", 130, b"SemiBold"), fill=255, anchor="mm")
    d.text((w // 2, int(h * 0.60)), str(number), font=font("CormorantGaramond-Italic[wght].ttf", 1120, b"Medium"), fill=255, anchor="mm")
    paint(card, tm, g)
    return card, sm


def paper(w, h, rgb, seed=5):
    """Fine, even paper: flat colour with a faint grain (no blotches)."""
    g = np.random.default_rng(seed).normal(0, 1, (h, w)).astype(np.float32)
    n = noise(w, h, 300, seed) - 0.5
    arr = np.ones((h, w, 3), np.float32) * np.array(rgb, np.float32) + (g * 2.2 + n * 5)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


SIGNATURE_FONTS = [("MrsSaintDelafield-Regular.ttf", 1.0), ("MonsieurLaDoulaise-Regular.ttf", 0.95), ("HerrVonMuellerhoff-Regular.ttf", 1.05), ("Carattere-Regular.ttf", 0.9)]


def signature_card(name, fontname, scale=1.0, sub=None, bg=(247, 242, 232), ink=(38, 36, 34), w=1050, h=600):
    c = paper(w, h, bg, 9)
    d = ImageDraw.Draw(c)
    sz = int(230 * scale)
    f = font(fontname, sz)
    while d.textlength(name, font=f) > w * 0.78 and sz > 60:
        sz -= 8
        f = font(fontname, sz)
    d.text((w // 2, h // 2 + (0 if not sub else -30)), name, font=f, fill=ink + (255,), anchor="mm")
    if sub:
        d.text((w // 2, h - 120), " ".join(sub.upper()), font=font("Jost[wght].ttf", 30, b"Regular"), fill=(110, 104, 98, 255), anchor="mm")
    return c


def diamond(card, cx, cy, rw, rh, col, gap=14, width=3):
    d = ImageDraw.Draw(card)
    for g in (0, gap):
        pts = [(cx, cy - rh - g), (cx + rw + g * 1.6, cy), (cx, cy + rh + g), (cx - rw - g * 1.6, cy)]
        d.line(pts + [pts[0]], fill=col + (255,), width=width, joint="curve")


def place_greens(c, assets, cx, cy, rw, rh, gw, gh):
    """Greenery clusters hugging the top-left and bottom-right edges of a diamond."""
    g1 = bk.fit(bk.trim(Image.open(os.path.join(assets, "g01_greenery.png")).convert("RGBA")), gw, gh)
    g2 = bk.fit(bk.trim(Image.open(os.path.join(assets, "g02_greenery.png")).convert("RGBA")), gw, gh).rotate(180, expand=True)
    c.alpha_composite(g1, (int(cx - rw * 0.55 - g1.width / 2), int(cy - rh * 0.55 - g1.height / 2)))
    c.alpha_composite(g2, (int(cx + rw * 0.55 - g2.width / 2), int(cy + rh * 0.55 - g2.height / 2)))


def diamond_fill(c, cx, cy, rw, rh, col=(252, 252, 250)):
    inner = Image.new("L", c.size, 0)
    ImageDraw.Draw(inner).polygon([(cx, cy - rh), (cx + rw, cy), (cx, cy + rh), (cx - rw, cy)], fill=255)
    white = Image.new("RGBA", c.size, col + (255,))
    white.putalpha(inner)
    c.alpha_composite(white)


def greenery_card(assets, text, w=1050, h=600, mode="caps", sub=None, fontname="MrsSaintDelafield-Regular.ttf"):
    c = paper(w, h, (252, 252, 250), 4)
    cx, cy, rw, rh = w // 2, h // 2, int(w * 0.30), int(h * 0.38)
    place_greens(c, assets, cx, cy, rw, rh, int(w * 0.40), int(h * 0.62))
    diamond_fill(c, cx, cy, rw, rh)
    diamond(c, cx, cy, rw, rh, (36, 86, 58), gap=12, width=3)
    d = ImageDraw.Draw(c)
    if mode == "caps":
        f = font("Jost[wght].ttf", 64, b"Light")
        s = " ".join(text.upper())
        while d.textlength(s, font=f) > rw * 1.5:
            f = font("Jost[wght].ttf", f.size - 4, b"Light")
        d.text((cx, cy), s, font=f, fill=(84, 84, 84, 255), anchor="mm")
    else:
        sz = 150
        f = font(fontname, sz)
        while d.textlength(text, font=f) > rw * 1.4:
            sz -= 6
            f = font(fontname, sz)
        d.text((cx, cy - (24 if sub else 0)), text, font=f, fill=(40, 52, 44, 255), anchor="mm")
        if sub:
            d.text((cx, cy + 82), " ".join(sub.upper()), font=font("Jost[wght].ttf", 26, b"Regular"), fill=(110, 110, 110, 255), anchor="mm")
    return c


def greenery_table(assets, number, word="TISCH", w=1500, h=2100):
    c = paper(w, h, (252, 252, 250), 6)
    cx, cy, rw, rh = w // 2, h // 2, int(w * 0.36), int(h * 0.30)
    place_greens(c, assets, cx, cy, rw, rh, int(w * 0.62), int(h * 0.42))
    diamond_fill(c, cx, cy, rw, rh)
    diamond(c, cx, cy, rw, rh, (36, 86, 58), gap=18, width=5)
    d = ImageDraw.Draw(c)
    d.text((cx, cy - 230), " ".join(word), font=font("Jost[wght].ttf", 64, b"Light"), fill=(84, 84, 84, 255), anchor="mm")
    d.text((cx, cy + 60), str(number), font=font("MrsSaintDelafield-Regular.ttf", 400), fill=(40, 52, 44, 255), anchor="mm")
    return c


def invitation(assets, w=1500, h=2100, names="HELENA & DANIEL", date="12 · 08 · 27", title="Einladung zur Hochzeit"):
    c = paper(w, h, (252, 252, 250), 8)
    cx, cy, rw, rh = w // 2, h // 2, int(w * 0.40), int(h * 0.27)
    place_greens(c, assets, cx, cy, rw, rh, int(w * 0.72), int(h * 0.44))
    diamond_fill(c, cx, cy, rw, rh)
    diamond(c, cx, cy, rw, rh, (36, 86, 58), gap=16, width=4)
    d = ImageDraw.Draw(c)
    sz = 150
    f = font("MrsSaintDelafield-Regular.ttf", sz)
    while d.textlength(title, font=f) > rw * 1.25:
        sz -= 6
        f = font("MrsSaintDelafield-Regular.ttf", sz)
    d.text((cx, cy - 110), title, font=f, fill=(40, 52, 44, 255), anchor="mm")
    d.text((cx, cy + 70), " ".join(names.upper()).replace("   ", "  "), font=font("Jost[wght].ttf", 52, b"Light"), fill=(84, 84, 84, 255), anchor="mm")
    d.text((cx, cy + 165), " ".join(date), font=font("Jost[wght].ttf", 44, b"Light"), fill=(84, 84, 84, 255), anchor="mm")
    return c


# ---------- mockups ----------

def stand(card, mask, scale):
    """Standing table number on a small gold stand."""
    cw, ch = int(card.width * scale), int(card.height * scale)
    c = card.resize((cw, ch), Image.LANCZOS)
    W, H = cw + 80, ch + int(260 * scale) + 60
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = gold(W, H, 7)
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    bx = W // 2
    by = ch + int(200 * scale)
    d.ellipse((bx - int(150 * scale), by - int(28 * scale), bx + int(150 * scale), by + int(32 * scale)), fill=255)
    d.polygon([(bx - int(26 * scale), ch - int(40 * scale)), (bx + int(26 * scale), ch - int(40 * scale)), (bx + int(60 * scale), by), (bx - int(60 * scale), by)], fill=255)
    d.rectangle((bx - int(110 * scale), ch - int(110 * scale), bx + int(110 * scale), ch - int(20 * scale)), fill=255)
    paint(out, m.filter(ImageFilter.GaussianBlur(1)), g)
    out.alpha_composite(c, (40, 0))
    # clip in front of card
    m2 = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m2).rounded_rectangle((bx - int(90 * scale), ch - int(130 * scale), bx + int(90 * scale), ch - int(40 * scale)), 12, fill=255)
    paint(out, m2, g)
    return out


def board(assets, out_path):
    W, Hh = 3000, 1500
    rows = []
    # row 1: velvet table numbers
    bg = linen(W, Hh, seed=41, tone=(238, 234, 226))
    items = [("arch", "cream", 1, "TABLE"), ("oval", "emerald", 4, "TABLE"), ("rect", "burgundy", 3, "TABLE"), ("arch", "navy", 7, "TISCH")]
    for i, (sh, col, n, wd) in enumerate(items):
        card, m = table_number(sh, col, n, wd)
        st = stand(card, m, 0.4)
        s = shadow_drop(st, off=(24, 18), blur=22, alpha=80)
        bg.alpha_composite(s, (90 + i * 730 - 60, 150 - 60))
    rows.append((bg, "Velvet Table Numbers", "arch · oval · rectangle  ·  cream, emerald, burgundy, navy, blush  ·  gold foil look  ·  to cut out"))
    # row 2: signature script place cards
    bg = linen(W, Hh, seed=42, tone=(238, 234, 226))
    names = ["Celine", "Maximilian", "Charlotte", "Annalena"]
    for i, ((fn, sc), nm) in enumerate(zip(SIGNATURE_FONTS, names)):
        card = signature_card(nm, fn, sc, sub=None if i % 2 == 0 else ("Tisch 3" if i == 3 else "Table 5"))
        t = tent(card, 1.15)
        s = shadow_drop(t)
        x = 120 + (i % 2) * 1460
        y = 80 + (i // 2) * 720
        bg.alpha_composite(s, (x - 60, y - 60))
    rows.append((bg, "Signature Script", "your names typed in 4 signature fonts  ·  cream or white  ·  online editor"))
    # row 3: greenery diamond
    bg = linen(W, Hh, seed=43, tone=(238, 234, 226))
    inv = invitation(assets).resize((880, 1232), Image.LANCZOS)
    s = shadow_drop(inv, off=(20, 16), blur=20, alpha=80)
    bg.alpha_composite(s, (2060 - 60, 120 - 60))
    tb = greenery_table(assets, 5).resize((700, 980), Image.LANCZOS)
    s = shadow_drop(tb, off=(20, 16), blur=20, alpha=80)
    bg.alpha_composite(s, (1250 - 60, 300 - 60))
    for j, (txt, mode, sub) in enumerate([("Bräutigam", "caps", None), ("Helena", "script", "Tisch 1")]):
        card = greenery_card(assets, txt, mode=mode, sub=sub)
        t = tent(card, 0.95)
        s = shadow_drop(t)
        bg.alpha_composite(s, (70 - 60, 90 + j * 680 - 60))
    rows.append((bg, "Greenery Diamond", "watercolour greenery  ·  double diamond frame  ·  caps or script names  ·  invitation, place cards, table numbers"))
    B = Image.new("RGB", (W, (Hh + 170) * len(rows)), (250, 248, 244))
    d = ImageDraw.Draw(B)
    for i, (img, t, sub) in enumerate(rows):
        y = i * (Hh + 170)
        B.paste(img.convert("RGB"), (0, y))
        d.text((W // 2, y + Hh + 62), "%d  ·  %s" % (i + 1, t), font=font("CormorantGaramond[wght].ttf", 78, b"SemiBold"), fill=(52, 46, 42), anchor="mm")
        d.text((W // 2, y + Hh + 128), sub, font=font("CormorantGaramond-Italic[wght].ttf", 46, b"Medium"), fill=(110, 100, 92), anchor="mm")
    B.save(out_path, quality=86)


if __name__ == "__main__":
    assets, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    board(assets, os.path.join(out, "Wedding_Styles_v3.jpg"))
    print("ok")
