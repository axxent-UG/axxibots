#!/usr/bin/env python3
"""Split one collection into single-type products (MyPorchPrints-style price ladder).

Usage: build_products.py <collection.json> <assets_dir> <out_dir>
collection.json: base kit fields (motifs, cards, papers, words, ...) plus "products": [
  {"slug", "title", "badge_sub", "price_eur", "section", "pages": [{"type": "tags"|"stamps"|"journal"|"cards"|"fussy"|"pattern",
   "off": int, "words": [...], "titles": [...], "key": "pp1_damask"}], "facts": {...}, "cover_lines": [...]}]
For each product: <out>/<slug>/pages (US Letter + A4 JPG, 2 PDFs), <out>/<slug>/listing (cover, what's inside, previews).
"""
import copy, glob, json, os, random, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk
import build_cover as bc

SIZES = bk.SIZES
DPI = bk.DPI


def page_pattern(kit, W, H, key, seed):
    """Full-bleed pattern paper (no frame, no footer text on the paper itself)."""
    img = kit.img[key]
    big = bk.cover_crop(img, W, H).filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
    return bk.grain_overlay(big, seed, 0.03).convert("RGBA")


def apply_palette(base):
    """Collection colours for page chrome (frames, words, numbers). Module globals are read at call time."""
    pal = base.get("palette") or {}
    for mod in (bk, bc):
        if "accent" in pal:
            mod.CRAN = tuple(pal["accent"])
        if "gold" in pal:
            mod.GOLD = tuple(pal["gold"])
        if "ink" in pal and hasattr(mod, "INK"):
            mod.INK = tuple(pal["ink"])
        if "green" in pal and hasattr(mod, "PINE"):
            mod.PINE = tuple(pal["green"])
    if "band" in pal:
        bc.BAND = tuple(pal["band"])
    if "ribbon" in pal:
        bc.RIBBON = tuple(pal["ribbon"])


def F_NUM(sz):
    return bk.font("PlayfairDisplay[wght].ttf", sz)


def F_TYPE(sz):
    return bk.font("SpecialElite-Regular.ttf", sz)


def page_advent(kit, W, H, style, seed):
    """25 advent numbers 1-25: 'medallion' (round labels) or 'card' (small cards with a motif)."""
    p = kit.blank(W, H, seed)
    cols, rows, mx, my, gap = 5, 5, 130, 150, 34
    cw = (W - 2 * mx - (cols - 1) * gap) // cols
    ch = (H - 2 * my - (rows - 1) * gap) // rows
    papers = [kit.img[k] for k in kit.cfg["pattern_papers"]] if kit.cfg.get("pattern_papers") else [kit.img[k] for k in kit.cfg["papers"]]
    for i in range(25):
        r, c = divmod(i, cols)
        x, y = mx + c * (cw + gap), my + r * (ch + gap)
        num = str(i + 1)
        if style == "medallion":
            dia = min(cw, ch) - 10
            piece = Image.new("RGBA", (dia, dia), (0, 0, 0, 0))
            mask = Image.new("L", (dia, dia), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, dia - 1, dia - 1), fill=255)
            bgp = bk.cover_crop(papers[i % len(papers)], dia, dia).convert("RGBA")
            piece.paste(bgp, (0, 0), mask)
            d = ImageDraw.Draw(piece)
            inset = int(dia * 0.13)
            d.ellipse((inset, inset, dia - inset, dia - inset), fill=bk.CREAM + (255,), outline=bk.GOLD + (255,), width=5)
            d.ellipse((inset + 12, inset + 12, dia - inset - 12, dia - inset - 12), outline=bk.CRAN + (255,), width=3)
            bk.text_center(d, dia // 2, dia // 2 + 4, num, F_NUM(int(dia * 0.36)), bk.CRAN + (255,))
            p.alpha_composite(piece, (x + (cw - dia) // 2, y + (ch - dia) // 2))
            bk.cut_outline(p, mask, x + (cw - dia) // 2, y + (ch - dia) // 2)
        else:
            piece = Image.new("RGBA", (cw, ch))
            piece.paste(bk.cover_crop(papers[(i + 2) % len(papers)], cw, ch), (0, 0))
            m = int(cw * 0.08)
            panel = bk.paper(cw - 2 * m, ch - 2 * m, bk.CREAM, seed + i).convert("RGBA")
            piece.alpha_composite(panel, (m, m))
            d = ImageDraw.Draw(piece)
            d.rectangle((m + 8, m + 8, cw - m - 9, ch - m - 9), outline=bk.GOLD + (255,), width=3)
            mo = bk.fit(bk.trim(kit.m(i)), int(cw * 0.55), int(ch * 0.40))
            piece.alpha_composite(mo, ((cw - mo.width) // 2, m + 16))
            bk.text_center(d, cw // 2, int(ch * 0.73), num, F_NUM(int(ch * 0.30)), bk.CRAN + (255,))
            p.alpha_composite(piece, (x, y))
            bk.cut_outline(p, Image.new("L", (cw, ch), 255), x, y)
    kit.footer(p, W, H)
    return p


def torn_strip(w, h, tone, seed):
    """Paper strip with softly torn short edges."""
    import random as _r
    rnd = _r.Random(seed)
    strip = bk.paper(w, h, tone, seed, stains=False).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    pts = [(rnd.randint(0, 14), 0)]
    for yy in range(0, h + 1, 8):
        pts.append((rnd.randint(0, 16), yy))
    pts.append((rnd.randint(0, 14), h))
    right = [(w - rnd.randint(0, 16), yy) for yy in range(h, -1, -8)]
    ImageDraw.Draw(mask).polygon(pts + right, fill=255)
    strip.putalpha(mask)
    return strip, mask


def page_words(kit, W, H, words, seed):
    """Word strips: 2 columns of typewriter phrases on torn paper strips."""
    p = kit.blank(W, H, seed)
    cols, mx, my, gapx, gapy = 2, 150, 160, 70, 36
    rows = (len(words) + 1) // 2
    sw = (W - 2 * mx - gapx) // cols
    sh = min(230, (H - 2 * my - (rows - 1) * gapy) // rows)
    tones = [tuple(t) for t in kit.cfg.get("strip_tones", [(244, 236, 218), (236, 222, 196), (232, 214, 214)])]
    for i, wd in enumerate(words):
        r, c = divmod(i, cols)
        x, y = mx + c * (sw + gapx), my + r * (sh + gapy)
        strip, mask = torn_strip(sw, sh, tones[i % len(tones)], seed + i)
        d = ImageDraw.Draw(strip)
        f = bk.fit_font(d, wd, F_TYPE, sw - 140, int(sh * 0.40))
        bk.text_center(d, sw // 2, sh // 2, wd, f, bk.INK + (255,))
        p.alpha_composite(strip, (x, y))
        bk.cut_outline(p, mask, x, y, width=2)
    kit.footer(p, W, H)
    return p


def render_page(kit, spec, W, H, n):
    kit.off = spec.get("off", 0)
    cfg = kit.cfg
    if spec.get("words") and spec["type"] == "tags":
        cfg["words"] = spec["words"]
    if spec.get("titles") and spec["type"] == "journal":
        cfg["journal_titles"] = spec["titles"]
    t = spec["type"]
    if t == "tags":
        return kit.page_tags(W, H)
    if t == "stamps":
        return kit.page_stamps(W, H)
    if t == "journal":
        return kit.page_journal(W, H)
    if t == "cards":
        return kit.page_cards(W, H)
    if t == "fussy":
        return kit.page_fussy(W, H, 0)
    if t == "pattern":
        return page_pattern(kit, W, H, spec["key"], 700 + n)
    if t == "advent":
        return page_advent(kit, W, H, spec.get("style", "medallion"), 800 + n)
    if t == "words":
        return page_words(kit, W, H, spec["words"], 900 + n)
    raise ValueError(t)


def build_product(base, prod, assets, out):
    cfg = copy.deepcopy(base)
    keys = set(cfg["motifs"] + cfg["cards"] + cfg["papers"] + [p["key"] for p in prod["pages"] if p.get("key")])
    cfg_load = dict(cfg, motifs=cfg["motifs"], cards=cfg["cards"], papers=sorted(set(cfg["papers"]) | set(cfg.get("pattern_papers", [])) | {k for k in keys if k.startswith("pp")}))
    kit = bk.Kit(cfg_load, assets)
    kit.cfg = cfg  # papers for tag backgrounds stay the collection papers
    kit.cfg["title"] = prod["title"]
    pdir = os.path.join(out, prod["slug"], "pages")
    os.makedirs(pdir, exist_ok=True)
    for size, (W, H) in SIZES.items():
        rgb = []
        for n, spec in enumerate(prod["pages"]):
            im = render_page(kit, copy.deepcopy(spec), W, H, n).convert("RGB")
            name = "%02d_%s" % (n + 1, spec.get("name", spec["type"]))
            im.save(os.path.join(pdir, "%s_%s_%s.jpg" % (prod["slug"], name, size)), quality=93, dpi=(DPI, DPI))
            rgb.append(im)
        rgb[0].save(os.path.join(pdir, "%s_%s.pdf" % (prod["slug"], size)), save_all=True, append_images=rgb[1:], resolution=DPI)
    return pdir


def cover(base, prod, pdir, assets, ldir):
    W, H = bc.W, bc.H
    if base.get("cover_style") == "mood":  # dark warm glow + bokeh (owner standard 22.10.2026)
        import build_pockets
        c = build_pockets.mood_background(W, H, seed=sum(map(ord, prod["slug"])) % 97)
    else:
        c = bc.wood(W, H, seed=hash(prod["slug"]) % 97)
    pages = sorted(glob.glob(os.path.join(pdir, "*_letter.jpg")))
    if prod.get("cover_order"):
        pages = [pages[i] for i in prod["cover_order"]]
    n = len(pages)
    # fan the pages behind the badge
    spots = [(560, 1000, 8), (2440, 1000, -8), (1050, 900, -4), (1950, 900, 5), (1500, 820, 1), (800, 1250, -10)]
    for i, p in enumerate(pages[:6]):
        x, y, a = spots[i % len(spots)]
        bc.paste_rot(c, bc.page_piece(p, 860 if n > 2 else 1000), x, y, a)
    # close-ups of single pieces in front, so small products still fill the cover
    if n <= 3:
        for (box, x, y, wd, a) in [((0.04, 0.04, 0.52, 0.40), 1000, 1780, 760, -6), ((0.48, 0.55, 0.96, 0.92), 2000, 1790, 760, 5)]:
            bc.paste_rot(c, bc.crop_piece(pages[-1 if x > 1500 else 0], box, wd), x, y, a)
    # a few stickers from the collection on top
    random.seed(prod["slug"])
    motifs = random.sample(base["motifs"], 3)
    for k, (x, y, s, a) in zip(motifs, [(330, 1950, 520, 6), (2680, 1950, 500, -8), (2650, 380, 380, 9)]):
        mo = bk.fit(bk.trim(Image.open(os.path.join(assets, k + ".png")).convert("RGBA")), s, s)
        bc.paste_rot(c, bk.sticker(mo, border=14, cut_line=False), x, y, a)
    bc.ribbon(c, "DIGITAL DOWNLOAD · YOU PRINT")
    b = bc.badge(prod.get("badge_title", base.get("badge_title", "Christmas Post")), prod["badge_sub"])
    bc.paste_rot(c, b, W // 2, 1080, 0)
    bc.info_band(c, prod["cover_lines"])
    os.makedirs(ldir, exist_ok=True)
    c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)


def previews(prod, pdir, ldir):
    W, H = bc.W, bc.H
    pages = sorted(glob.glob(os.path.join(pdir, "*_letter.jpg")))
    c = bc.wood(W, H, seed=9)
    n = len(pages)
    cols = min(n, 3 if n <= 3 else (4 if n <= 8 else 5))
    rows = (n + cols - 1) // cols
    th = min(int((H - 260 - 260) / rows) - 60, 1500)
    tw = int(th * 8.5 / 11)
    gx = (W - cols * tw) // (cols + 1)
    top = 230
    gy = (H - 260 - top - rows * th) // (rows + 1)
    for i, p in enumerate(pages):
        r, k = divmod(i, cols)
        im = bc.page_piece(p, tw)
        im, pad = bc.drop_shadow(im, off=(8, 12), blur=12, alpha=150)
        c.alpha_composite(im, (gx + k * (tw + gx) - pad, top + gy + r * (th + gy) - pad))
    d = ImageDraw.Draw(c)
    bk.text_center(d, W // 2, 120, "What's inside: %d printable page%s" % (n, "s" if n != 1 else ""), bk.F_ITAL(96), (247, 236, 214, 255))
    bc.info_band(c, prod["inside_lines"])
    c.convert("RGB").save(os.path.join(ldir, "02_whats_inside.jpg"), quality=90)
    for i, p in enumerate(pages[:6]):
        im = Image.open(p).convert("RGBA")
        im = im.resize((int(im.width * 2400 / im.height * 0.86), int(2400 * 0.86)), Image.LANCZOS)
        bg = bc.wood(W, H, seed=20 + i)
        sh, pad = bc.drop_shadow(im, off=(12, 16), blur=16, alpha=160)
        bg.alpha_composite(sh, ((W - sh.width) // 2, (H - sh.height) // 2))
        wm = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        dw = ImageDraw.Draw(wm)
        for y in range(-200, H + 400, 520):
            for x in range(-400, W + 400, 1100):
                dw.text((x, y), "PREVIEW", font=bk.F_SC(110), fill=(255, 255, 255, 54))
        bg.alpha_composite(wm.rotate(25, resample=Image.BICUBIC))
        bg.convert("RGB").save(os.path.join(ldir, "%02d_page_%d.jpg" % (3 + i, i + 1)), quality=88)


def main():
    col = json.load(open(sys.argv[1]))
    assets, out = sys.argv[2], sys.argv[3]
    only = sys.argv[4:] or None
    base = {k: v for k, v in col.items() if k != "products"}
    apply_palette(base)
    for prod in col["products"]:
        if only and prod["slug"] not in only:
            continue
        pdir = build_product(base, prod, assets, out)
        ldir = os.path.join(out, prod["slug"], "listing")
        cover(base, prod, pdir, assets, ldir)
        previews(prod, pdir, ldir)
        print(prod["slug"], "ok")


if __name__ == "__main__":
    main()
