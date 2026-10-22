#!/usr/bin/env python3
"""AXXIBOTS junk-journal kit engine (M18).

Builds a printable ephemera kit from generated illustrations:
  tags, picture cards, journaling cards, postage stamps, two fussy-cut sheets
  and full-page papers, in US Letter and A4 at 300 dpi, plus one PDF per size.

Usage: build_kit.py <kit.json> <assets_dir> <out_dir>
kit.json: {"slug","title","subtitle","words":[...],"stamp_values":[...],
           "motifs":[keys], "cards":[keys], "papers":[keys]}
assets_dir: <key>.png for every key (motifs with transparent background).
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageChops

DPI = 300
SIZES = {"letter": (2550, 3300), "a4": (2480, 3508)}
FONT_DIR = os.environ.get("JJ_FONTS", os.path.join(os.path.dirname(__file__), "fonts"))
INK = (59, 42, 30)
CRAN = (128, 34, 38)
PINE = (38, 66, 48)
GOLD = (168, 132, 72)
CREAM = (244, 236, 218)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def F_ROMAN(s): return font("IMFeENrm28P.ttf", s)
def F_ITAL(s): return font("IMFeENit28P.ttf", s)
def F_SC(s): return font("IMFeENsc28P.ttf", s)


# ---------- surfaces ----------
def noise(w, h, scale, seed):
    rng = np.random.default_rng(seed)
    sw, sh = max(2, w // scale), max(2, h // scale)
    n = rng.random((sh, sw)).astype(np.float32)
    return np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255.0


def paper(w, h, base=CREAM, seed=1, stains=True):
    """Aged paper: base tone, fibre grain, soft blotches, darker edges."""
    a = np.zeros((h, w, 3), np.float32) + np.array(base, np.float32)
    blot = noise(w, h, 180, seed) * 0.6 + noise(w, h, 60, seed + 1) * 0.4
    grain = noise(w, h, 2, seed + 2)
    a *= (0.93 + 0.07 * blot)[..., None]
    a *= (0.975 + 0.035 * grain)[..., None]
    if stains:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.maximum(np.abs(xx / w - 0.5), np.abs(yy / h - 0.5)) * 2
        a *= (1 - 0.10 * np.clip((d - 0.75) / 0.25, 0, 1) ** 2)[..., None]
        a[..., 2] *= (1 - 0.05 * np.clip((d - 0.6) / 0.4, 0, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def grain_overlay(img, seed=3, amount=0.035):
    w, h = img.size
    g = noise(w, h, 1, seed)
    a = np.asarray(img.convert("RGB"), np.float32) * (1 - amount + 2 * amount * g)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def cover_crop(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.5))


# ---------- motif helpers ----------
def clean_alpha(rgba, keep=0.02):
    """Drop stray alpha islands (specks, slivers) smaller than `keep` x the largest shape."""
    from scipy import ndimage
    a = np.asarray(rgba.getchannel("A"))
    lab, n = ndimage.label(a > 24)
    if n <= 1:
        return rgba
    sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
    good = np.isin(lab, 1 + np.flatnonzero(sizes >= keep * sizes.max()))
    out = np.asarray(rgba).copy()
    out[..., 3] = np.where(good, out[..., 3], 0)
    return Image.fromarray(out, "RGBA")


def trim(rgba, pad=0):
    rgba = clean_alpha(rgba)
    a = rgba.getchannel("A")
    bb = a.point(lambda v: 255 if v > 12 else 0).getbbox()
    if not bb:
        return rgba
    l, t, r, b = bb
    return rgba.crop((max(0, l - pad), max(0, t - pad), min(rgba.width, r + pad), min(rgba.height, b + pad)))


def fit(rgba, w, h):
    s = min(w / rgba.width, h / rgba.height)
    return rgba.resize((max(1, int(rgba.width * s)), max(1, int(rgba.height * s))), Image.LANCZOS)


def sticker(rgba, border=18, cut_line=True):
    """White offset border around the motif (fussy-cut style) with a faint cut line."""
    rgba = trim(rgba)
    pad = border * 2 + 6
    canvas = Image.new("RGBA", (rgba.width + 2 * pad, rgba.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(rgba, (pad, pad))
    a = canvas.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    grown = a.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(border / 3)).point(lambda v: 255 if v > 110 else 0)
    out = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    if cut_line:
        line = grown.filter(ImageFilter.MaxFilter(5))
        ring = ImageChops.subtract(line, grown)
        out.paste((150, 140, 128, 255), (0, 0), ring)
    white = Image.new("RGBA", canvas.size, (255, 253, 248, 255))
    out.paste(white, (0, 0), grown)
    out.alpha_composite(canvas)
    return out


def drop_shadow(rgba, off=(10, 14), blur=14, alpha=110):
    a = rgba.getchannel("A")
    pad = blur * 3
    sh = Image.new("RGBA", (rgba.width + 2 * pad + abs(off[0]), rgba.height + 2 * pad + abs(off[1])), (0, 0, 0, 0))
    m = Image.new("L", sh.size, 0)
    m.paste(a, (pad + off[0], pad + off[1]))
    m = m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * alpha // 255)
    sh.paste((25, 15, 8, 255), (0, 0), m)
    sh.alpha_composite(rgba, (pad, pad))
    return sh, pad


def text_center(d, cx, cy, s, f, fill):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), s, font=f, fill=fill)


def fit_font(d, s, maker, max_w, start):
    size = start
    while size > 10:
        f = maker(size)
        bb = d.textbbox((0, 0), s, font=f)
        if bb[2] - bb[0] <= max_w:
            return f
        size -= 2
    return maker(size)


# ---------- shapes ----------
def tag_mask(w, h, notch=None, hole_r=None):
    notch = notch or int(w * 0.22)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.polygon([(notch, 0), (w - notch, 0), (w, notch), (w, h), (0, h), (0, notch)], fill=255)
    return m


def perforated_mask(w, h, r=13, step=36):
    m = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(m)
    for x in range(step // 2, w, step):
        d.ellipse((x - r, -r, x + r, r), fill=0)
        d.ellipse((x - r, h - r, x + r, h + r), fill=0)
    for y in range(step // 2, h, step):
        d.ellipse((-r, y - r, r, y + r), fill=0)
        d.ellipse((w - r, y - r, w + r, y + r), fill=0)
    return m


def place(page, piece, x, y, mask=None):
    if piece.mode == "RGBA" and mask is None:
        page.alpha_composite(piece, (int(x), int(y)))
    else:
        rgba = piece.convert("RGBA")
        if mask is not None:
            rgba.putalpha(mask)
        page.alpha_composite(rgba, (int(x), int(y)))


def cut_outline(page, mask, x, y, color=(150, 140, 128, 255), width=3):
    edge = mask.filter(ImageFilter.MaxFilter(width * 2 + 1))
    ring = ImageChops.subtract(edge, mask)
    layer = Image.new("RGBA", mask.size, color)
    page.paste(layer, (int(x), int(y)), ring)


# ---------- pieces ----------
def make_tag(w, h, bg, motif, word, seed):
    t = Image.new("RGBA", (w, h))
    t.paste(cover_crop(bg, w, h), (0, 0))
    d = ImageDraw.Draw(t)
    m = int(w * 0.09)
    panel_top = int(h * 0.17)
    panel = paper(w - 2 * m, h - panel_top - m, CREAM, seed)
    t.paste(panel, (m, panel_top))
    d.rectangle((m + 14, panel_top + 14, w - m - 14, h - m - 14), outline=GOLD + (255,), width=4)
    mo = fit(trim(motif), int((w - 2 * m) * 0.82), int((h - panel_top - m) * 0.62))
    t.alpha_composite(mo, ((w - mo.width) // 2, panel_top + int((h - panel_top - m) * 0.08)))
    f = fit_font(d, word, F_ITAL, w - 2 * m - 80, int(w * 0.14))
    text_center(d, w // 2, h - m - int((h - panel_top - m) * 0.14), word, f, CRAN + (255,))
    # reinforced hole
    cx, cy, r = w // 2, int(h * 0.085), int(w * 0.055)
    d.ellipse((cx - r * 2, cy - r * 2, cx + r * 2, cy + r * 2), fill=(214, 196, 160, 255), outline=GOLD + (255,), width=4)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255))
    mask = tag_mask(w, h)
    hm = ImageDraw.Draw(mask)
    hm.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    t.putalpha(mask)
    return t, mask


def make_card(w, h, painting, word=None, seed=1):
    c = Image.new("RGBA", (w, h))
    c.paste(paper(w, h, CREAM, seed), (0, 0))
    m = int(w * 0.055)
    c.paste(cover_crop(painting, w - 2 * m, h - 2 * m), (m, m))
    d = ImageDraw.Draw(c)
    d.rectangle((m, m, w - m - 1, h - m - 1), outline=GOLD + (255,), width=5)
    if word:
        bh = int(h * 0.11)
        y0 = h - m - bh - int(h * 0.05)
        band = paper(int(w * 0.72), bh, CREAM, seed + 9)
        bx = (w - band.width) // 2
        c.paste(band, (bx, y0))
        d.rectangle((bx, y0, bx + band.width - 1, y0 + bh - 1), outline=CRAN + (255,), width=4)
        f = fit_font(d, word, F_ITAL, band.width - 60, int(bh * 0.7))
        text_center(d, w // 2, y0 + bh // 2, word, f, CRAN + (255,))
    return c


def make_journal_card(w, h, bg, motif, title, seed):
    c = Image.new("RGBA", (w, h))
    c.paste(cover_crop(bg, w, h), (0, 0))
    m = int(min(w, h) * 0.07)
    inner = paper(w - 2 * m, h - 2 * m, CREAM, seed)
    c.paste(inner, (m, m))
    d = ImageDraw.Draw(c)
    d.rectangle((m + 10, m + 10, w - m - 11, h - m - 11), outline=GOLD + (255,), width=3)
    f = fit_font(d, title, F_SC, int(w * 0.6), int(h * 0.075))
    d.text((m + 50, m + 40), title, font=f, fill=CRAN + (255,))
    top = m + 40 + int(h * 0.1)
    for y in range(top + 70, h - m - 50, 78):
        d.line((m + 50, y, w - m - int(w * 0.30), y), fill=(150, 128, 100, 255), width=3)
    mo = fit(trim(motif), int(w * 0.30), int(h * 0.48))
    c.alpha_composite(mo, (w - m - mo.width - 24, h - m - mo.height - 24))
    return c


def make_stamp(w, h, motif, value, label, bg_color, seed):
    s = Image.new("RGBA", (w, h), (255, 252, 246, 255))
    d = ImageDraw.Draw(s)
    m = int(w * 0.10)
    inner = Image.new("RGBA", (w - 2 * m, h - 2 * m), bg_color + (255,))
    tex = paper(inner.width, inner.height, bg_color, seed, stains=False)
    inner.paste(tex, (0, 0))
    mo = fit(trim(motif), int(inner.width * 0.84), int(inner.height * 0.66))
    inner.alpha_composite(mo, ((inner.width - mo.width) // 2, int(inner.height * 0.17)))
    di = ImageDraw.Draw(inner)
    f = fit_font(di, label, F_SC, inner.width - 30, int(inner.height * 0.09))
    text_center(di, inner.width // 2, int(inner.height * 0.085), label, f, INK + (255,))
    fv = F_ROMAN(int(inner.height * 0.12))
    di.text((18, inner.height - int(inner.height * 0.16)), value, font=fv, fill=CRAN + (255,))
    s.alpha_composite(inner, (m, m))
    d.rectangle((m - 2, m - 2, w - m + 1, h - m + 1), outline=INK + (255,), width=3)
    mask = perforated_mask(w, h, r=max(8, w // 40), step=max(24, w // 14))
    s.putalpha(mask)
    return s, mask


# ---------- pages ----------
class Kit:
    def __init__(self, cfg, assets):
        self.cfg = cfg
        self.img = {}
        for k in cfg["motifs"] + cfg["cards"] + cfg["papers"]:
            self.img[k] = Image.open(os.path.join(assets, k + ".png")).convert("RGBA")

    def m(self, i):
        ks = self.cfg["motifs"]
        return self.img[ks[i % len(ks)]]

    def blank(self, W, H, seed):
        return paper(W, H, (250, 247, 240), seed, stains=False).convert("RGBA")

    def footer(self, page, W, H):
        d = ImageDraw.Draw(page)
        s = self.cfg["title"] + "  ·  for personal use"
        text_center(d, W // 2, H - 70, s, F_ITAL(34), (140, 125, 105, 255))

    def page_tags(self, W, H):
        p = self.blank(W, H, 11)
        cols, rows, mx, my, gap = 3, 2, 140, 170, 60
        tw = (W - 2 * mx - (cols - 1) * gap) // cols
        th = (H - 2 * my - (rows - 1) * gap) // rows
        bgs = [self.img[k] for k in self.cfg["papers"]]
        words = self.cfg["words"]
        for i in range(cols * rows):
            r, c = divmod(i, cols)
            x, y = mx + c * (tw + gap), my + r * (th + gap)
            tag, mask = make_tag(tw, th, bgs[i % len(bgs)], self.m(i), words[i % len(words)], 100 + i)
            place(p, tag, x, y)
            cut_outline(p, mask, x, y)
        self.footer(p, W, H)
        return p

    def page_cards(self, W, H):
        p = self.blank(W, H, 12)
        cols, rows, mx, my, gap = 2, 2, 150, 160, 70
        cw = (W - 2 * mx - gap) // cols
        ch = (H - 2 * my - gap) // rows
        words = self.cfg["card_words"]
        for i, k in enumerate(self.cfg["cards"][:4]):
            r, c = divmod(i, cols)
            x, y = mx + c * (cw + gap), my + r * (ch + gap)
            card = make_card(cw, ch, self.img[k], words[i] if i < len(words) else None, 200 + i)
            place(p, card, x, y)
            cut_outline(p, Image.new("L", (cw, ch), 255), x, y)
        self.footer(p, W, H)
        return p

    def page_journal(self, W, H):
        p = self.blank(W, H, 13)
        cols, rows, mx, my, gap = 2, 3, 150, 150, 60
        cw = (W - 2 * mx - gap) // cols
        ch = (H - 2 * my - 2 * gap) // rows
        titles = self.cfg["journal_titles"]
        bgs = [self.img[k] for k in self.cfg["papers"]]
        for i in range(6):
            r, c = divmod(i, cols)
            x, y = mx + c * (cw + gap), my + r * (ch + gap)
            card = make_journal_card(cw, ch, bgs[(i + 1) % len(bgs)], self.m(i + 6), titles[i % len(titles)], 300 + i)
            place(p, card, x, y)
            cut_outline(p, Image.new("L", (cw, ch), 255), x, y)
        self.footer(p, W, H)
        return p

    def page_stamps(self, W, H):
        p = self.blank(W, H, 14)
        cols, rows, mx, my, gap = 4, 5, 140, 150, 44
        sw = (W - 2 * mx - (cols - 1) * gap) // cols
        sh = (H - 2 * my - (rows - 1) * gap) // rows
        tones = [(236, 222, 196), (222, 205, 205), (212, 222, 206), (230, 214, 186)]
        vals = self.cfg["stamp_values"]
        for i in range(cols * rows):
            r, c = divmod(i, cols)
            x, y = mx + c * (sw + gap), my + r * (sh + gap)
            st, mask = make_stamp(sw, sh, self.m(i), vals[i % len(vals)], self.cfg["stamp_label"], tones[i % len(tones)], 400 + i)
            place(p, st, x, y)
        self.footer(p, W, H)
        return p

    def page_fussy(self, W, H, start):
        p = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        cols, rows, mx, my, gap = 3, 3, 120, 140, 40
        cw = (W - 2 * mx - (cols - 1) * gap) // cols
        ch = (H - 2 * my - (rows - 1) * gap) // rows
        for i in range(9):
            r, c = divmod(i, cols)
            mo = fit(trim(self.m(start + i)), cw - 70, ch - 70)
            st = sticker(mo, border=16)
            x = mx + c * (cw + gap) + (cw - st.width) // 2
            y = my + r * (ch + gap) + (ch - st.height) // 2
            p.alpha_composite(st, (x, y))
        self.footer(p, W, H)
        return p

    def page_paper(self, W, H, key, seed):
        """Illustrated journal page: the painting framed on aged paper (no cropping, ~240 dpi)."""
        p = paper(W, H, (240, 230, 208), seed).convert("RGBA")
        src = self.img[key].convert("RGB")
        m = int(W * 0.06)
        art = ImageOps.contain(src, (W - 2 * m, H - 2 * m - 90), Image.LANCZOS)
        art = art.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
        art = grain_overlay(art, seed, 0.025)
        x, y = (W - art.width) // 2, m + 10
        p.paste(art, (x, y))
        d = ImageDraw.Draw(p)
        d.rectangle((x - 16, y - 16, x + art.width + 15, y + art.height + 15), outline=GOLD + (255,), width=5)
        d.rectangle((x - 30, y - 30, x + art.width + 29, y + art.height + 29), outline=CRAN + (255,), width=2)
        self.footer(p, W, H)
        return p

    def pages(self, W, H):
        out = [("01_tags", self.page_tags(W, H)), ("02_picture_cards", self.page_cards(W, H)),
               ("03_journal_cards", self.page_journal(W, H)), ("04_stamps", self.page_stamps(W, H)),
               ("05_fussy_cuts_1", self.page_fussy(W, H, 0)), ("06_fussy_cuts_2", self.page_fussy(W, H, 9))]
        for i, k in enumerate(self.cfg["papers"]):
            out.append(("%02d_journal_page_%s" % (7 + i, k.split("_", 1)[-1]), self.page_paper(W, H, k, 500 + i)))
        return out


def main():
    cfg = json.load(open(sys.argv[1]))
    assets, out = sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    kit = Kit(cfg, assets)
    for size, (W, H) in SIZES.items():
        pages = kit.pages(W, H)
        rgb = []
        for name, im in pages:
            im = im.convert("RGB")
            im.save(os.path.join(out, "%s_%s_%s.jpg" % (cfg["slug"], name, size)), quality=93, dpi=(DPI, DPI))
            rgb.append(im)
        rgb[0].save(os.path.join(out, "%s_%s.pdf" % (cfg["slug"], size)), save_all=True, append_images=rgb[1:], resolution=DPI)
        print(size, len(pages), "pages")


if __name__ == "__main__":
    main()
