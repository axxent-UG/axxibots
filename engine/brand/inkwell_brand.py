#!/usr/bin/env python3
"""Inkwell Ephemera brand assets: emblem (inkwell + quill), shop icon, Etsy banner, badge for covers.

Usage: inkwell_brand.py <assets_dir> <out_dir>
Palette: ink blue-black, cranberry, aged gold, cream (matches the kit pages).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "jj"))
from build_kit import F_ITAL, F_ROMAN, F_SC, CRAN, GOLD, paper, fit, trim, sticker, text_center, fit_font  # noqa: E402
from build_cover import wood, paste_rot, drop_shadow  # noqa: E402

INK = (30, 36, 54)
CREAM = (247, 240, 224)
NAME = "Inkwell Ephemera"
CLAIM = "Junk Journal Ephemera & Craft Printables"


def bezier(p0, p1, p2, p3, n=80):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t ** 2
        d = t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def emblem(size=600, ink=INK, fill=CREAM):
    """Inkwell with a quill, drawn at 4x and reduced for clean edges. Transparent background."""
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = int(S * 0.012)
    cx = S * 0.42
    # bottle body (squat, rounded), shoulder and neck
    body = (cx - S * 0.25, S * 0.56, cx + S * 0.25, S * 0.90)
    d.rounded_rectangle(body, radius=int(S * 0.08), fill=ink)
    d.polygon([(cx - S * 0.25, S * 0.62), (cx - S * 0.11, S * 0.50), (cx + S * 0.11, S * 0.50), (cx + S * 0.25, S * 0.62)], fill=ink)
    d.rounded_rectangle((cx - S * 0.10, S * 0.43, cx + S * 0.10, S * 0.53), radius=int(S * 0.02), fill=ink)
    d.rounded_rectangle((cx - S * 0.125, S * 0.405, cx + S * 0.125, S * 0.45), radius=int(S * 0.02), fill=ink)
    # label on the bottle
    d.rounded_rectangle((cx - S * 0.17, S * 0.66, cx + S * 0.17, S * 0.81), radius=int(S * 0.02), fill=fill)
    d.rounded_rectangle((cx - S * 0.15, S * 0.68, cx + S * 0.15, S * 0.79), radius=int(S * 0.015), outline=CRAN + (255,), width=lw)
    # highlight
    d.arc((cx - S * 0.22, S * 0.585, cx - S * 0.02, S * 0.88), 190, 250, fill=fill, width=lw)
    # quill: spine from inside the neck up to the upper right, with a tapering vane
    spine = bezier((cx + S * 0.01, S * 0.47), (cx + S * 0.10, S * 0.30), (cx + S * 0.28, S * 0.14), (cx + S * 0.50, S * 0.04))
    left, right = [], []
    n = len(spine)
    for i in range(n - 1):
        (x0, y0), (x1, y1) = spine[i], spine[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        t = i / (n - 1)
        w = 0 if t < 0.18 else S * 0.075 * math.sin(math.pi * min(1, (t - 0.18) / 0.82)) ** 0.7
        wl = w * 1.15
        left.append((x0 + nx * wl, y0 + ny * wl))
        right.append((x0 - nx * w * 0.75, y0 - ny * w * 0.75))
    d.polygon(left + [spine[-1]] + right[::-1], fill=fill, outline=ink)
    d.line(left + [spine[-1]] + right[::-1] + [left[0]], fill=ink, width=lw, joint="curve")
    # barbs
    for i in range(int(n * 0.24), n - 3, 4):
        x0, y0 = spine[i]
        lx, ly = left[min(i + 3, len(left) - 1)]
        rx, ry = right[min(i + 3, len(right) - 1)]
        d.line((x0, y0, lx, ly), fill=ink, width=max(2, lw // 2))
        d.line((x0, y0, rx, ry), fill=ink, width=max(2, lw // 2))
    d.line(spine, fill=ink, width=lw)
    return im.resize((size, size), Image.LANCZOS)


def label_shape(w, h, notch):
    """Apothecary label: rectangle with concave (inward-rounded) corners."""
    m = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(m)
    for (x, y) in ((0, 0), (w, 0), (0, h), (w, h)):
        d.ellipse((x - notch, y - notch, x + notch, y + notch), fill=0)
    return m


def badge(w=1500, h=760, sub=CLAIM, extra=None):
    """Shop badge: emblem, name, claim. Used on the banner and (small) on covers."""
    b = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = label_shape(w, h, int(h * 0.14))
    face = paper(w, h, CREAM, 41, stains=False).convert("RGBA")
    face.putalpha(m)
    b.alpha_composite(face)
    d = ImageDraw.Draw(b)
    for inset, col, wid in ((26, INK, 9), (46, GOLD, 4)):
        mi = label_shape(w - 2 * inset, h - 2 * inset, int(h * 0.14) - inset)
        pad = Image.new("L", (w, h), 0)
        pad.paste(mi, (inset, inset))
        inner = pad.filter(ImageFilter.MinFilter(wid * 2 + 1))
        ring = Image.fromarray(np.clip(np.asarray(pad, np.int16) - np.asarray(inner, np.int16), 0, 255).astype(np.uint8))
        b.paste(Image.new("RGBA", (w, h), col + (255,)), (0, 0), ring)
    e = emblem(int(h * 0.36))
    b.alpha_composite(e, ((w - e.width) // 2, int(h * 0.07)))
    f1 = fit_font(d, NAME.upper(), F_SC, int(w * 0.80), int(h * 0.17))
    text_center(d, w // 2, int(h * 0.56), NAME.upper(), f1, INK + (255,))
    cy = int(h * 0.68)
    d.line((w * 0.22, cy, w * 0.44, cy), fill=GOLD + (255,), width=4)
    d.line((w * 0.56, cy, w * 0.78, cy), fill=GOLD + (255,), width=4)
    d.regular_polygon((w / 2, cy, 13), 4, rotation=45, fill=CRAN + (255,))
    f2 = fit_font(d, sub, F_ITAL, int(w * 0.80), int(h * 0.085))
    text_center(d, w // 2, int(h * 0.79), sub, f2, CRAN + (255,))
    if extra:
        f3 = fit_font(d, extra, F_SC, int(w * 0.6), int(h * 0.055))
        text_center(d, w // 2, int(h * 0.885), extra, f3, INK + (255,))
    return b


def icon(out, size=500):
    c = paper(size, size, CREAM, 51, stains=False).convert("RGBA")
    d = ImageDraw.Draw(c)
    d.ellipse((14, 14, size - 15, size - 15), outline=INK + (255,), width=10)
    d.ellipse((34, 34, size - 35, size - 35), outline=GOLD + (255,), width=4)
    e = emblem(int(size * 0.66))
    c.alpha_composite(e, ((size - e.width) // 2 + 8, int(size * 0.13)))
    c.convert("RGB").save(out, quality=95)


def F_NUM(sz):
    return ImageFont.truetype(os.path.join(os.path.dirname(__file__), "fonts", "PlayfairDisplay[wght].ttf"), sz)


def coupon_card(w, h, codes):
    card = paper(w, h, (236, 228, 208), 61).convert("RGBA")
    d = ImageDraw.Draw(card)
    d.rectangle((14, 14, w - 15, h - 15), outline=INK + (255,), width=6)
    d.rectangle((30, 30, w - 31, h - 31), outline=GOLD + (255,), width=3)
    text_center(d, w // 2, 95, "COUPON CODES", F_SC(66), INK + (255,))
    y = 190
    for label, code in codes:
        text_center(d, w // 2, y, label, F_NUM(40), INK + (255,))
        bw, bh = int(w * 0.72), 74
        d.rounded_rectangle(((w - bw) // 2, y + 36, (w + bw) // 2, y + 36 + bh), 10, fill=CRAN + (255,))
        text_center(d, w // 2, y + 36 + bh // 2, code, F_NUM(46), (250, 242, 226, 255))
        y += 170
    f = F_ITAL(30)
    for i, s in enumerate(["Cannot be combined with a sale.", "Shop currency: EUR."]):
        text_center(d, w // 2, h - 105 + i * 40, s, f, INK + (255,))
    return card


def banner(assets, out, codes=None, W=3360, H=840):
    c = wood(W, H, seed=12)
    # left: papers, cards and stickers fanned out
    for key, x, y, wd, a in [("p02_holly", 230, 470, 430, 8), ("c02_fireside", 520, 430, 400, -6), ("c04_stilllife", 860, 470, 380, 5)]:
        im = Image.open(os.path.join(assets, key + ".png")).convert("RGBA")
        im = im.resize((wd, int(im.height * wd / im.width)), Image.LANCZOS)
        fr = Image.new("RGBA", (im.width + 36, im.height + 36), CREAM + (255,))
        fr.alpha_composite(im, (18, 18))
        paste_rot(c, fr, x, y, a)
    for key, x, y, s, a in [("m03_robin", 300, 160, 300, -10), ("m01_teddy", 960, 680, 300, 6), ("m16_bells", 640, 760, 260, -4)]:
        mo = fit(trim(Image.open(os.path.join(assets, key + ".png")).convert("RGBA")), s, s)
        paste_rot(c, sticker(mo, border=12, cut_line=False), x, y, a)
    # centre badge (inside Etsy's safe area)
    b = badge(1250, 640)
    paste_rot(c, b, W // 2, H // 2, 0)
    # right: coupons or more pieces
    if codes:
        card = coupon_card(640, 760, codes)
        paste_rot(c, card, W - 620, H // 2, 2)
        mo = fit(trim(Image.open(os.path.join(assets, "m13_tree.png")).convert("RGBA")), 240, 240)
        paste_rot(c, sticker(mo, border=12, cut_line=False), W - 170, 700, 8)
    c.convert("RGB").save(out, quality=93)


if __name__ == "__main__":
    assets, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    emblem(1200).save(os.path.join(out, "inkwell_emblem.png"))
    icon(os.path.join(out, "inkwell_icon_500.jpg"))
    badge().save(os.path.join(out, "inkwell_badge.png"))
    codes = [("10% off orders of 10 EUR+", "INKWELL10"), ("15% off orders of 15 EUR+", "INKWELL15"), ("20% off orders of 20 EUR+", "INKWELL20")]
    banner(assets, os.path.join(out, "inkwell_banner_3360x840.jpg"), codes)
    print("ok")
