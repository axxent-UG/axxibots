#!/usr/bin/env python3
"""Illusion pockets: printable pocket fronts (empty containers), matching pocket backs,
tuck-in pieces that peek out of the pockets, tags, and an assembly guide. Same output
layout as build_products.py, so upload_products.py and the listing agent work unchanged.

Usage: build_pockets.py <pockets.json> <assets_dir> <out_dir>
pockets.json: {"collection": "<collection.json>", "products": [{slug, title, badge_title, badge_sub,
  price_eur, section, cover_lines, inside_lines, facts,
  "pockets": [{"front": key, "inserts": [keys]}], "tuckins": [keys], "tags": [words]}]}
"""
import json, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk
import build_cover as bc
import build_products as bp

SIZES, DPI = bk.SIZES, bk.DPI


def load(assets, key):
    return bk.trim(Image.open(os.path.join(assets, key + ".png")).convert("RGBA"))


def cut_points(spec, n=60):
    """Opening line of a pocket in % of the raw image: {"line": [[x, y], ...]} or
    {"ellipse": [cx, cy, rx, ry]} (lower arc of the inner rim)."""
    if "ellipse" in spec:
        cx, cy, rx, ry = spec["ellipse"]
        pts = [[0, cy]] + [[cx - rx + 2 * rx * i / n, cy + ry * max(0.0, 1 - ((2 * i / n) - 1) ** 2) ** 0.5] for i in range(n + 1)] + [[100, cy]]
        return pts
    return spec["line"]


def pocket_pair(assets, pk):
    """(front, back): back = full illustration incl. the inside; front = same image with
    everything above the opening line removed. Both cropped to the same box."""
    raw = Image.open(os.path.join(assets, pk["front"] + ".png")).convert("RGBA")
    raw = bk.clean_alpha(raw)
    W, H = raw.size
    pts = cut_points(pk["cut"])
    poly = [(0, 0), (W, 0), (W, pts[-1][1] * H / 100)] + [(x * W / 100, y * H / 100) for x, y in reversed(pts)] + [(0, pts[0][1] * H / 100)]
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).polygon(poly, fill=0)
    front = raw.copy()
    from PIL import ImageChops
    front.putalpha(ImageChops.multiply(raw.getchannel("A"), m))
    bb = raw.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    back, front = raw.crop(bb), front.crop(bb)
    opening = (max(y for x, y in pts) * H / 100 - bb[1]) / back.height  # lowest point of the opening, 0..1
    return front, back, opening


def sticker_fixed(rgba, border=16):
    """White cutting border without trimming, so a front and its back keep the same box."""
    from PIL import ImageChops
    pad = border * 2 + 6
    canvas = Image.new("RGBA", (rgba.width + 2 * pad, rgba.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(rgba, (pad, pad))
    a = canvas.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    grown = a.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(border / 3)).point(lambda v: 255 if v > 110 else 0)
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ring = ImageChops.subtract(grown.filter(ImageFilter.MaxFilter(5)), grown)
    out.paste((150, 140, 128, 255), (0, 0), ring)
    out.paste(Image.new("RGBA", canvas.size, (255, 253, 248, 255)), (0, 0), grown)
    out.alpha_composite(canvas)
    return out


def scaled(img, max_w, max_h):
    return bk.fit(img, max_w, max_h)


def pack(items, W, H, top, bottom=230, mx=130, gap=50):
    """Greedy row packing. items: list of RGBA pieces. Returns (placements, leftover)."""
    out, x, y, row_h = [], mx, top, 0
    for i, it in enumerate(items):
        if x + it.width > W - mx and x > mx:
            x, y, row_h = mx, y + row_h + gap, 0
        if y + it.height > H - bottom:
            return out, items[i:]
        out.append((it, x, y))
        x += it.width + gap
        row_h = max(row_h, it.height)
    # centre each row horizontally
    rows = {}
    for it, px, py in out:
        rows.setdefault(py, []).append((it, px))
    centred = []
    for py, r in rows.items():
        width = r[-1][1] + r[-1][0].width - r[0][1]
        shift = (W - width) // 2 - r[0][1]
        centred += [(it, px + shift, py) for it, px in r]
    return centred, []


def heading(page, W, title, sub):
    d = ImageDraw.Draw(page)
    bk.text_center(d, W // 2, 120, title, bk.F_ITAL(92), bk.CRAN + (255,))
    bk.text_center(d, W // 2, 205, sub, bk.F_SC(40), bk.PINE + (255,))


def piece_pages(kit, W, H, pieces, title, sub, seed):
    pages, rest, n = [], pieces, 0
    while rest:
        page = kit.blank(W, H, seed + n)
        heading(page, W, title, sub)
        placed, rest = pack(rest, W, H, top=300)
        for it, x, y in placed:
            page.alpha_composite(it, (x, y))
        kit.footer(page, W, H)
        pages.append(page)
        n += 1
    return pages


def assembled(assets, pk, h):
    """A finished pocket: back, tuck-ins, front on top (for the guide and the cover)."""
    front, back, opening = pocket_pair(assets, pk)
    s = min(h * 0.72 / back.height, h * 0.95 / back.width)
    size = (int(back.width * s), int(back.height * s))
    front, back = front.resize(size, Image.LANCZOS), back.resize(size, Image.LANCZOS)
    canvas = Image.new("RGBA", (int(size[0] * 1.25), h), (0, 0, 0, 0))
    fx, fy = (canvas.width - size[0]) // 2, h - size[1]
    canvas.alpha_composite(back, (fx, fy))
    ins = pk["inserts"]
    for j, k in enumerate(ins):
        im = bk.fit(load(assets, k), int(size[0] * (0.62 if len(ins) > 1 else 0.8)), int(h * 0.66))
        cx = fx + int(size[0] * ((j + 1) / (len(ins) + 1)))
        bottom = fy + int(size[1] * (opening + (1 - opening) * pk.get("depth", 0.4)))
        canvas.alpha_composite(im, (cx - im.width // 2, max(0, bottom - im.height)))
    canvas.alpha_composite(front, (fx, fy))
    return canvas


def guide_page(kit, W, H, prod, assets, seed):
    p = kit.blank(W, H, seed)
    heading(p, W, "How to make your pockets", "illusion pockets · assembly guide")
    d = ImageDraw.Draw(p)
    steps = [
        ("1", "Print the pages on matte cardstock or thick paper (100% scale, no 'fit to page')."),
        ("2", "Fussy-cut the pocket fronts along the white border; cut the matching backs the same way."),
        ("3", "Glue each front onto its back along the sides and bottom only. Leave the top open."),
        ("4", "Or skip the back: glue the front straight onto a journal page, again with the top left open."),
        ("5", "Cut out the tuck-ins and tags and slide them into the pocket so they peek out."),
    ]
    y = 330
    for num, s in steps:
        d.ellipse((190, y, 270, y + 80), fill=bk.CRAN + (255,))
        bk.text_center(d, 230, y + 40, num, bk.F_SC(54), (250, 240, 220, 255))
        f = bk.F_ROMAN(46)
        words, line, ly = s.split(), "", y + 8
        for w in words:
            t = (line + " " + w).strip()
            if d.textbbox((0, 0), t, font=f)[2] > W - 320 - 200:
                d.text((320, ly), line, font=f, fill=bk.INK + (255,))
                line, ly = w, ly + 58
            else:
                line = t
        d.text((320, ly), line, font=f, fill=bk.INK + (255,))
        y = ly + 110
    exs = [bk.drop_shadow(assembled(assets, pk, int(1100 * W / 2550)), off=(10, 14), blur=14, alpha=90)[0] for pk in prod["pockets"][:2]]
    total = sum(e.width for e in exs)
    x = (W - total) // 2
    for e in exs:
        p.alpha_composite(e, (x, H - 230 - e.height))
        x += e.width
    bk.text_center(d, W // 2, H - 230 - max(e.height for e in exs) - 40, "finished pockets with tuck-ins", bk.F_ITAL(46), bk.PINE + (255,))
    kit.footer(p, W, H)
    return p


def build(base, prod, assets, out):
    kit = bk.Kit(dict(base, title=prod["title"]), assets)
    pdir = os.path.join(out, prod["slug"], "pages")
    os.makedirs(pdir, exist_ok=True)
    for size, (W, H) in SIZES.items():
        k = W / 2550
        pairs = [pocket_pair(assets, pk) for pk in prod["pockets"]]
        front_pieces, back_pieces = [], []
        for fr, ba, _ in pairs:
            sc = min(960 * k / ba.width, 1060 * k / ba.height)
            sz = (int(ba.width * sc), int(ba.height * sc))
            front_pieces.append(sticker_fixed(fr.resize(sz, Image.LANCZOS)))
            back_pieces.append(sticker_fixed(ba.resize(sz, Image.LANCZOS)))
        tucks = [bk.sticker(scaled(load(assets, t), int(620 * k), int(700 * k)), border=14) for t in prod["tuckins"]]
        tags = []
        bgs = [kit.img[x] for x in base["papers"]]
        for i, w in enumerate(prod["tags"]):
            tag, mask = bk.make_tag(int(480 * k), int(900 * k), bgs[i % len(bgs)], kit.m(i + 3), w, 300 + i)
            tags.append(tag)
        pages = []
        pairs_flat = [x for fb in zip(front_pieces, back_pieces) for x in fb]
        pages += piece_pages(kit, W, H, pairs_flat + tags, "Pocket Fronts & Backs", "front left · back right · glue sides and bottom, leave the top open", 1)
        pages += piece_pages(kit, W, H, tucks, "Tuck-ins", "slide them into the pockets so they peek out", 9)
        pages.append(guide_page(kit, W, H, prod, assets, 13))
        names = []
        rgb = []
        for n, pg in enumerate(pages):
            im = pg.convert("RGB")
            im.save(os.path.join(pdir, "%s_%02d_page_%s.jpg" % (prod["slug"], n + 1, size)), quality=93, dpi=(DPI, DPI))
            rgb.append(im)
        rgb[0].save(os.path.join(pdir, "%s_%s.pdf" % (prod["slug"], size)), save_all=True, append_images=rgb[1:], resolution=DPI)
        print(prod["slug"], size, len(pages), "pages")
    return pdir


def cover(base, prod, assets, ldir):
    W, H = bc.W, bc.H
    c = bc.wood(W, H, seed=31)
    spots = [(620, 640, 980, -4), (1560, 620, 980, 2), (1300, 1700, 820, 3), (480, 1700, 820, 3), (2250, 1760, 680, -3)]
    for pk, (x, y, h, a) in zip(prod["pockets"], spots):
        im = assembled(assets, pk, h)
        bc.paste_rot(c, im, x, y, a)
    bc.ribbon(c, "DIGITAL DOWNLOAD · YOU PRINT")
    b = bc.badge(prod["badge_title"], prod["badge_sub"], w=1150, h=520)
    bc.paste_rot(c, b, prod.get("badge_x", W // 2), prod.get("badge_y", 1640), 0)
    bc.info_band(c, prod["cover_lines"])
    os.makedirs(ldir, exist_ok=True)
    c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)


def main():
    cfg = json.load(open(sys.argv[1]))
    assets, out = sys.argv[2], sys.argv[3]
    base = {k: v for k, v in json.load(open(cfg["collection"])).items() if k != "products"}
    bp.apply_palette(base)
    for prod in cfg["products"]:
        pdir = build(base, prod, assets, out)
        ldir = os.path.join(out, prod["slug"], "listing")
        cover(base, prod, assets, ldir)
        bp.previews(prod, pdir, ldir)
        print(prod["slug"], "ok")


if __name__ == "__main__":
    main()
