#!/usr/bin/env python3
"""Listing images for a junk-journal kit: cover collage on dark wood, label badge,
'digital download' corner ribbon and an info band. Then page previews with a watermark.

Usage: build_cover.py <kit.json> <kit_out_dir> <assets_dir> <listing_out_dir>
"""
import glob, json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
sys.path.insert(0, os.path.dirname(__file__))
from build_kit import (F_ITAL, F_ROMAN, F_SC, CRAN, CREAM, GOLD, INK, PINE, drop_shadow, fit, fit_font,
                       noise, paper, sticker, text_center, trim)

W, H = 3000, 2400
BAND = (32, 52, 40)   # info band colour (collection palette may override)
RIBBON = (122, 30, 34)  # corner ribbon colour  # Etsy recommends 2000px+ on the short side; 5:4


def wood(w, h, seed=7):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    planks = 5
    ph = h / planks
    out = np.zeros((h, w, 3), np.float32)
    base = np.array([62, 40, 26], np.float32)
    for i in range(planks):
        y0, y1 = int(i * ph), int((i + 1) * ph)
        n1 = noise(w, y1 - y0, 40, seed + i)
        n2 = noise(w, y1 - y0, 6, seed + 20 + i)
        stretch = np.asarray(Image.fromarray((noise(w // 30 + 2, y1 - y0, 3, seed + 40 + i) * 255).astype(np.uint8)).resize((w, y1 - y0), Image.BICUBIC), np.float32) / 255
        rings = 0.5 + 0.5 * np.sin((yy[y0:y1] - y0) / 7.0 + stretch * 18 + n1 * 6)
        tone = 0.78 + 0.22 * rings * (0.6 + 0.4 * n2)
        tone *= 0.85 + 0.3 * rng.random()
        out[y0:y1] = base * tone[..., None]
        out[y0:y0 + 6] *= 0.45  # plank gap
    yy2, xx2 = yy / h - 0.5, xx / w - 0.5
    vig = 1 - 0.55 * np.clip((np.sqrt(xx2 ** 2 + yy2 ** 2) - 0.25) / 0.5, 0, 1)
    out *= vig[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")


def paste_rot(canvas, piece, cx, cy, angle, shadow=True):
    p = piece.rotate(angle, resample=Image.BICUBIC, expand=True)
    if shadow:
        p, pad = drop_shadow(p, off=(14, 20), blur=18, alpha=150)
    canvas.alpha_composite(p, (int(cx - p.width / 2), int(cy - p.height / 2)))


def page_piece(path, w):
    im = Image.open(path).convert("RGBA")
    h = int(im.height * w / im.width)
    return im.resize((w, h), Image.LANCZOS)


def crop_piece(path, box, w):
    im = Image.open(path).convert("RGBA")
    W0, H0 = im.size
    c = im.crop((int(box[0] * W0), int(box[1] * H0), int(box[2] * W0), int(box[3] * H0)))
    return c.resize((w, int(c.height * w / c.width)), Image.LANCZOS)


def badge(title, sub, w=1250, h=560):
    b = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    r = 60
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    face = paper(w, h, (247, 240, 224), 31, stains=False).convert("RGBA")
    face.putalpha(m)
    b.alpha_composite(face)
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((22, 22, w - 23, h - 23), r - 18, outline=CRAN + (255,), width=8)
    d.rounded_rectangle((40, 40, w - 41, h - 41), r - 30, outline=GOLD + (255,), width=3)
    f1 = fit_font(d, sub.upper(), F_SC, w - 260, 58)
    text_center(d, w // 2, 120, sub.upper(), f1, PINE + (255,))
    f2 = fit_font(d, title, F_ITAL, w - 160, 190)
    text_center(d, w // 2, h // 2 + 20, title, f2, CRAN + (255,))
    # brand line: small inkwell emblem + shop name (Inkwell Ephemera)
    import importlib.util
    spec = importlib.util.spec_from_file_location("inkwell_brand", os.path.join(os.path.dirname(__file__), "..", "brand", "inkwell_brand.py"))
    ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
    cy = h - 105
    e = ib.emblem(86)
    f3 = F_SC(46)
    label = "INKWELL EPHEMERA"
    tw = d.textbbox((0, 0), label, font=f3)[2]
    x0 = (w - (e.width + 18 + tw)) // 2
    b.alpha_composite(e, (x0, cy - 52))
    d.text((x0 + e.width + 18, cy - 28), label, font=f3, fill=(30, 36, 54, 255))
    return b


def ribbon(canvas, text):
    size = 800
    rib = Image.new("RGBA", (size * 2, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(rib)
    d.rectangle((0, 0, size * 2, 150), fill=RIBBON + (255,))
    d.line((0, 14, size * 2, 14), fill=GOLD + (255,), width=4)
    d.line((0, 136, size * 2, 136), fill=GOLD + (255,), width=4)
    f = F_SC(58)
    text_center(d, size, 72, text, f, (250, 240, 220, 255))
    rib = rib.rotate(45, resample=Image.BICUBIC, expand=True)
    rib, _ = drop_shadow(rib, off=(6, 10), blur=10, alpha=140)
    canvas.alpha_composite(rib, (W - rib.width // 2 - 430, -rib.height // 2 + 430))


def info_band(canvas, lines):
    bh = 250
    band = Image.new("RGBA", (W, bh), BAND + (238,))
    d = ImageDraw.Draw(band)
    d.line((0, 10, W, 10), fill=GOLD + (255,), width=4)
    n = len(lines)
    for i, s in enumerate(lines):
        cx = int(W * (i + 0.5) / n)
        f = fit_font(d, s, F_ITAL, int(W / n) - 80, 70)
        text_center(d, cx, bh // 2 + 4, s, f, (247, 236, 214, 255))
        if i:
            d.ellipse((int(W * i / n) - 9, bh // 2 - 5, int(W * i / n) + 9, bh // 2 + 13), fill=GOLD + (255,))
    canvas.alpha_composite(band, (0, H - bh))


def cover(cfg, kit_dir, assets, out):
    slug = cfg["slug"]
    pg = lambda name: sorted(glob.glob(os.path.join(kit_dir, "%s_%s*_letter.jpg" % (slug, name))))[0]
    c = wood(W, H)
    random.seed(4)
    # back layer: papers and full pages fanned out
    paste_rot(c, page_piece(pg("07"), 900), 520, 900, 9)
    paste_rot(c, page_piece(pg("10"), 900), 2480, 900, -8)
    paste_rot(c, page_piece(pg("08"), 860), 1050, 760, -5)
    paste_rot(c, page_piece(pg("09"), 860), 1980, 760, 6)
    # mid layer: cards, tags, stamps
    paste_rot(c, crop_piece(pg("02"), (0.05, 0.04, 0.5, 0.49), 720), 470, 1500, -7)
    paste_rot(c, crop_piece(pg("02"), (0.5, 0.5, 0.95, 0.95), 720), 2560, 1480, 8)
    paste_rot(c, crop_piece(pg("01"), (0.04, 0.04, 0.36, 0.5), 470), 950, 1640, 4)
    paste_rot(c, crop_piece(pg("01"), (0.36, 0.5, 0.68, 0.96), 470), 2070, 1650, -5)
    paste_rot(c, crop_piece(pg("03"), (0.05, 0.04, 0.5, 0.33), 820), 1500, 1620, 2)
    stamps = pg("04")
    for i, (bx, by, cx, cy, a) in enumerate([(0.05, 0.04, 260, 520, -12), (0.28, 0.04, 2760, 560, 10), (0.51, 0.22, 1240, 1980, -6), (0.74, 0.22, 1780, 2000, 7)]):
        paste_rot(c, crop_piece(stamps, (bx, by, bx + 0.215, by + 0.176), 330), cx, cy, a)
    # front: fussy-cut motifs as stickers
    for k, cx, cy, s, a in [("m06_sleigh", 330, 1950, 600, 6), ("m01_teddy", 2700, 1950, 520, -8),
                            ("m03_robin", 900, 320, 420, -10), ("m13_tree", 2150, 330, 430, 8)]:
        mo = fit(trim(Image.open(os.path.join(assets, k + ".png")).convert("RGBA")), s, s)
        paste_rot(c, sticker(mo, border=14, cut_line=False), cx, cy, a)
    b = badge(cfg.get("badge_title", "Christmas Post"), cfg.get("badge_sub", "Junk Journal Ephemera Kit"))
    ribbon(c, "DIGITAL DOWNLOAD · YOU PRINT")
    paste_rot(c, b, W // 2, 1080, 0)
    info_band(c, cfg["cover_lines"])
    c.convert("RGB").save(os.path.join(out, "01_cover.jpg"), quality=92)


def previews(cfg, kit_dir, out):
    """Second image: what's inside (all pages as a spread); then one image per page with watermark."""
    slug = cfg["slug"]
    pages = sorted(glob.glob(os.path.join(kit_dir, "%s_*_letter.jpg" % slug)))
    c = wood(W, H, seed=9)
    cols, rows = 5, 2
    tw = 500
    th = int(tw * 11 / 8.5)
    gx = (W - cols * tw) // (cols + 1)
    top = 200
    gy = (H - 260 - top - rows * th) // (rows + 1)
    for i, p in enumerate(pages[:10]):
        r, k = divmod(i, cols)
        im = page_piece(p, tw)
        im, pad = drop_shadow(im, off=(8, 12), blur=12, alpha=150)
        c.alpha_composite(im, (gx + k * (tw + gx) - pad, top + gy + r * (th + gy) - pad))
    d = ImageDraw.Draw(c)
    text_center(d, W // 2, 110, "What's inside: %d printable pages" % len(pages), F_ITAL(96), (247, 236, 214, 255))
    info_band(c, cfg["inside_lines"])
    c.convert("RGB").save(os.path.join(out, "02_whats_inside.jpg"), quality=90)
    for i, p in enumerate(pages[:6]):
        im = Image.open(p).convert("RGBA")
        im = im.resize((int(im.width * 2400 / im.height), 2400), Image.LANCZOS)
        bg = wood(W, H, seed=20 + i)
        sh, pad = drop_shadow(im.resize((int(im.width * 0.86), int(im.height * 0.86)), Image.LANCZOS), off=(12, 16), blur=16, alpha=160)
        bg.alpha_composite(sh, ((W - sh.width) // 2, (H - sh.height) // 2))
        wm = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        dw = ImageDraw.Draw(wm)
        for y in range(-200, H + 400, 520):
            for x in range(-400, W + 400, 1100):
                dw.text((x, y), "PREVIEW", font=F_SC(110), fill=(255, 255, 255, 54))
        wm = wm.rotate(25, resample=Image.BICUBIC)
        bg.alpha_composite(wm)
        bg.convert("RGB").save(os.path.join(out, "%02d_page_%s" % (3 + i, os.path.basename(p).split("_", 2)[-1])), quality=88)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    os.makedirs(sys.argv[4], exist_ok=True)
    cover(cfg, sys.argv[2], sys.argv[3], sys.argv[4])
    previews(cfg, sys.argv[2], sys.argv[4])
