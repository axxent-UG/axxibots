#!/usr/bin/env python3
"""Wedding styles v2 (owner feedback 28.10.2026: design-led, one or two ink colours, line drawings,
stripes/cartouche, fine double frames, write-in table line, DE + EN versions, shown as standing tent cards).

Usage: wedding_styles2.py <assets_dir> <out_dir>
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk

FD = os.path.join(os.path.dirname(__file__), "fonts")
W, H = 1050, 600  # place card front, 3.5 x 2 in at 300 dpi


def font(name, sz, var=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(sz))
    if var:
        try:
            f.set_variation_by_name(var)
        except Exception:
            pass
    return f


def mot(assets, key, w, h, flip=False):
    im = bk.fit(bk.trim(Image.open(os.path.join(assets, key + ".png")).convert("RGBA")), w, h)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def tint(im, rgb):
    """Recolour a line drawing to one exact ink colour (keeps alpha and line weight)."""
    a = np.asarray(im.getchannel("A"), np.float32)
    g = np.asarray(im.convert("L"), np.float32)
    alpha = a * np.clip((255 - g) / 200 + 0.15, 0, 1)
    out = Image.new("RGBA", im.size, rgb + (0,))
    out.putalpha(Image.fromarray(alpha.astype(np.uint8)))
    return out


def text(d, xy, s, f, fill, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def spaced(s):
    return " ".join(s)


def fit_text(d, s, fname, maxw, start, var=None):
    sz = start
    while d.textlength(s, font=font(fname, sz, var)) > maxw and sz > 20:
        sz -= 4
    return font(fname, sz, var)


# ---------------- the 10 styles ----------------

def s_candle(assets, name, sub, lang):
    ink, bg = (44, 74, 132), (247, 241, 214)
    c = Image.new("RGBA", (W, H), bg + (255,))
    ca = tint(mot(assets, "l01_candles", 190, 400), ink)
    c.alpha_composite(ca, (60, (H - ca.height) // 2 + 20))
    co = tint(mot(assets, "l02_coupe", 250, 330), ink)
    c.alpha_composite(co, (W - co.width - 40, H - co.height - 70))
    d = ImageDraw.Draw(c)
    x0, x1 = 60 + ca.width + 30, W - co.width - 60
    text(d, ((x0 + x1) // 2, H // 2 + 10), name, fit_text(d, name, "Sacramento-Regular.ttf", x1 - x0, 150), ink + (255,))
    return c


def s_stripe(assets, name, sub, lang):
    navy, cream = (34, 48, 98), (244, 241, 234)
    c = Image.new("RGBA", (W, H), cream + (255,))
    d = ImageDraw.Draw(c)
    for x in range(0, W, 44):
        d.rectangle((x, 0, x + 18, H), fill=navy + (255,))
        d.line((x + 28, 0, x + 28, H), fill=navy + (120,), width=2)
    ow, oh = 760, 430
    ox, oy = (W - ow) // 2, (H - oh) // 2
    d.ellipse((ox - 14, oy - 14, ox + ow + 14, oy + oh + 14), fill=cream + (255,))
    d.ellipse((ox, oy, ox + ow, oy + oh), outline=navy + (255,), width=5)
    d.ellipse((ox + 12, oy + 12, ox + ow - 12, oy + oh - 12), outline=navy + (255,), width=2)
    text(d, (W // 2, H // 2 - 25), name, fit_text(d, name, "PinyonScript-Regular.ttf", 600, 130), navy + (255,))
    text(d, (W // 2, H // 2 + 95), spaced("WILLKOMMEN" if lang == "de" else "WELCOME"), font("CormorantGaramond[wght].ttf", 40, b"Medium"), navy + (255,))
    return c


def s_olive(assets, name, sub, lang):
    gold, ink, bg = (184, 150, 82), (40, 40, 40), (255, 255, 255)
    c = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(c)
    d.rectangle((40, 48, W - 52, H - 40), outline=gold + (255,), width=3)
    d.rectangle((52, 36, W - 40, H - 52), outline=gold + (255,), width=3)
    o = mot(assets, "o01_olive", 380, 130)
    c.alpha_composite(o, ((W - o.width) // 2, 62))
    text(d, (W // 2, 330), name, fit_text(d, name, "GreatVibes-Regular.ttf", 760, 140), ink + (255,))
    line = "Du sitzt am Tisch Nr." if lang == "de" else "You are seated at table"
    f = font("GreatVibes-Regular.ttf", 50)
    tw = d.textlength(line, font=f)
    x0 = (W - tw - 260) // 2
    d.text((x0, 470), line, font=f, fill=ink + (255,), anchor="lm")
    d.line((x0 + tw + 20, 488, x0 + tw + 250, 488), fill=ink + (255,), width=2)
    return c


def s_oyster(assets, name, sub, lang):
    ink, bg = (30, 60, 110), (250, 248, 242)
    c = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(c)
    oy = tint(mot(assets, "l03_oysters", 300, 260), ink)
    c.alpha_composite(oy, (50, H - oy.height - 60))
    le = tint(mot(assets, "l04_lemons", 260, 260), ink)
    c.alpha_composite(le, (W - le.width - 50, 50))
    text(d, (W // 2, H // 2), name, fit_text(d, name, "Sacramento-Regular.ttf", 480, 150), ink + (255,))
    d.rectangle((22, 22, W - 22, H - 22), outline=ink + (255,), width=2)
    return c


def s_bow(assets, name, sub, lang):
    blush, ink, bg = (214, 170, 168), (120, 80, 82), (253, 249, 247)
    c = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(c)
    r, m = 18, 46
    for x in range(m, W - m + 1, 2 * r):  # scalloped inner border
        d.arc((x - r, m - r, x + r, m + r), 0, 180, fill=blush + (255,), width=3)
        d.arc((x - r, H - m - r, x + r, H - m + r), 180, 360, fill=blush + (255,), width=3)
    for y in range(m, H - m + 1, 2 * r):
        d.arc((m - r, y - r, m + r, y + r), 270, 90, fill=blush + (255,), width=3)
        d.arc((W - m - r, y - r, W - m + r, y + r), 90, 270, fill=blush + (255,), width=3)
    b = mot(assets, "b01_bow", 200, 170)
    c.alpha_composite(b, ((W - b.width) // 2, 70))
    text(d, (W // 2, 350), name, fit_text(d, name, "PinyonScript-Regular.ttf", 700, 120), ink + (255,))
    text(d, (W // 2, 470), spaced(sub.upper()), font("CormorantGaramond[wght].ttf", 34, b"Medium"), ink + (255,))
    return c


def gingham(w, h, col, sq=16):
    g = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    for vertical in (True, False):
        lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        if vertical:
            for x in range(0, w, 2 * sq):
                d.rectangle((x, 0, x + sq - 1, h), fill=col + (115,))
        else:
            for y in range(0, h, 2 * sq):
                d.rectangle((0, y, w, y + sq - 1), fill=col + (115,))
        g.alpha_composite(lay)
    return g


def s_cherry(assets, name, sub, lang):
    red, bg = (176, 32, 42), (255, 253, 250)
    c = Image.new("RGBA", (W, H), bg + (255,))
    band = gingham(W, 96, red)
    c.alpha_composite(band, (0, 0))
    c.alpha_composite(band, (0, H - 96))
    d = ImageDraw.Draw(c)
    ch = mot(assets, "c01_cherries", 190, 220)
    c.alpha_composite(ch, (70, (H - ch.height) // 2))
    text(d, (W // 2 + 80, H // 2 - 10), name, fit_text(d, name, "Sacramento-Regular.ttf", 600, 150), red + (255,))
    text(d, (W // 2 + 80, H // 2 + 100), spaced(sub.upper()), font("CormorantGaramond[wght].ttf", 32, b"SemiBold"), red + (255,))
    return c


def s_toile(assets, name, sub, lang):
    blue, bg = (46, 82, 150), (250, 249, 244)
    c = Image.new("RGBA", (W, H), bg + (255,))
    t = tint(mot(assets, "t01_toile", W - 80, 200), blue)
    c.alpha_composite(t, ((W - t.width) // 2, H - t.height - 40))
    d = ImageDraw.Draw(c)
    text(d, (W // 2, 190), name, fit_text(d, name, "PinyonScript-Regular.ttf", 760, 130), blue + (255,))
    text(d, (W // 2, 300), spaced(sub.upper()), font("Italiana-Regular.ttf", 38), blue + (255,))
    d.line((W // 2 - 60, 345, W // 2 + 60, 345), fill=blue + (255,), width=2)
    return c


def s_deco(assets, name, sub, lang):
    gold, bg = (206, 176, 108), (22, 22, 24)
    c = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(c)
    d.rectangle((30, 30, W - 30, H - 30), outline=gold + (255,), width=3)
    d.rectangle((44, 44, W - 44, H - 44), outline=gold + (255,), width=1)
    m = mot(assets, "w03_deco", 360, 140)
    c.alpha_composite(m, ((W - m.width) // 2, 70))
    text(d, (W // 2, 330), name.upper(), fit_text(d, name.upper(), "Cinzel[wght].ttf", 760, 74, b"Regular"), gold + (255,))
    text(d, (W // 2, 440), spaced(sub.upper()), font("Italiana-Regular.ttf", 38), gold + (255,))
    return c


def s_botanical(assets, name, sub, lang):
    ink, bg = (52, 42, 34), (244, 238, 222)
    c = bk.paper(W, H, bg, 7, stains=False).convert("RGBA")
    b = mot(assets, "w09_botanical", 440, 560)
    b = b.rotate(90, expand=True, resample=Image.BICUBIC) if b.width > b.height * 1.3 else b
    b = bk.fit(b, 330, 560)
    c.alpha_composite(b, (40, (H - b.height) // 2))
    d = ImageDraw.Draw(c)
    text(d, (W // 2 + 120, H // 2 - 20), name, fit_text(d, name, "PinyonScript-Regular.ttf", 560, 120), ink + (255,))
    text(d, (W // 2 + 120, H // 2 + 95), sub, font("IMFeENsc28P.ttf", 42), ink + (255,))
    return c


def s_eucalyptus(assets, name, sub, lang):
    ink, bg = (64, 72, 64), (255, 255, 255)
    c = Image.new("RGBA", (W, H), bg + (255,))
    e = mot(assets, "w01_eucalyptus", 300, 140)
    c.alpha_composite(e.rotate(-28, expand=True, resample=Image.BICUBIC), (W - 330, 10))
    d = ImageDraw.Draw(c)
    text(d, (W // 2 - 40, H // 2 + 10), name, fit_text(d, name, "CormorantGaramond-Italic[wght].ttf", 760, 120, b"Medium"), ink + (255,))
    text(d, (W // 2 - 40, H // 2 + 110), spaced(sub.upper()), font("CormorantGaramond[wght].ttf", 30, b"Medium"), (130, 145, 128, 255))
    return c


STYLES = [
    ("Candlelight Supper", s_candle, "Navy ink line drawings on cream"),
    ("Riviera Stripe", s_stripe, "Navy stripes, oval cartouche"),
    ("Olive & Gold", s_olive, "Olive sprig, double gold frame, write-in table line"),
    ("Oysters & Lemons", s_oyster, "Seaside dinner sketches"),
    ("Satin Bow", s_bow, "Blush bow, scalloped border"),
    ("Cherry Gingham", s_cherry, "Red gingham, cherries"),
    ("Toile Bleu", s_toile, "French toile band"),
    ("Black Tie Deco", s_deco, "Black, gold Art Deco"),
    ("Antique Botanical", s_botanical, "Ink engraving on cream paper"),
    ("Eucalyptus Minimal", s_eucalyptus, "One sprig, lots of white space"),
]


# ---------------- presentation: standing tent cards on linen ----------------

def linen(w, h, seed=1, tone=(236, 231, 222)):
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(tone, np.float32)
    rows = rng.normal(0, 5, (h, 1)).repeat(w, 1)
    cols = rng.normal(0, 5, (1, w)).repeat(h, 0)
    fine = rng.normal(0, 4, (h, w))
    img = base + (rows + cols + fine)[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    # soft light falloff
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - 0.18 * (((xx / w - 0.4) ** 2 + (yy / h - 0.35) ** 2) ** 0.5)
    arr = np.asarray(im, np.float32) * v[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def tent(front, scale=0.9, tilt=0.035):
    """Front face of a standing tent card with slight perspective, top-light shading and a visible back flap edge."""
    f = front.resize((int(front.width * scale), int(front.height * scale)), Image.LANCZOS)
    w, h = f.size
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(h):
        a = int(26 * (y / h) ** 1.6)
        sd.line((0, y, w, y), fill=(0, 0, 0, a))
    f.alpha_composite(shade)
    inset = int(w * tilt)
    out = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    # back flap edge peeking out at the top right
    back = Image.new("RGBA", (w - 2 * inset, 14), (225, 221, 214, 255))
    out.alpha_composite(back, (20 + inset + 8, 12))
    quad = (inset, 0, 0, h, w, h, w - inset, 0)  # map output corners -> input
    persp = f.transform((w, h), Image.QUAD, (0, 0, 0, h, w, h, w, 0), Image.BICUBIC)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(inset, 0), (0, h), (w, h), (w - inset, 0)], fill=255)
    face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    face.paste(f.resize((w, h)), (0, 0), mask)
    out.alpha_composite(face, (20, 20))
    return out


def shadow_drop(im, off=(26, 18), blur=22, alpha=95):
    a = im.getchannel("A")
    sh = Image.new("RGBA", (im.width + 120, im.height + 120), (0, 0, 0, 0))
    s = Image.new("RGBA", im.size, (40, 32, 24, alpha))
    s.putalpha(a.point(lambda v: alpha if v > 0 else 0))
    sh.alpha_composite(s, (60 + off[0], 60 + off[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    sh.alpha_composite(im, (60, 60))
    return sh


def tile(assets, idx, title, fn, note, tw=1500, th=1100):
    bg = linen(tw, th, seed=idx + 3)
    names = [("Charlotte Becker", "Table 4", "en"), ("Annalena", "Tisch 2", "de"), ("Max", "Table 7", "en")]
    pos = [(80, 330, 0.95), (720, 170, 0.78), (740, 560, 0.72)]
    for (nm, sub, lang), (x, y, sc) in list(zip(names, pos))[::-1]:
        card = tent(fn(assets, nm, sub, lang), sc)
        s = shadow_drop(card)
        bg.alpha_composite(s, (x - 60, y - 60))
    d = ImageDraw.Draw(bg)
    d.rectangle((0, th - 150, tw, th), fill=(250, 248, 244, 235))
    text(d, (tw // 2, th - 102), "%d  ·  %s" % (idx, title), font("CormorantGaramond[wght].ttf", 70, b"SemiBold"), (52, 46, 42, 255))
    text(d, (tw // 2, th - 42), note, font("CormorantGaramond-Italic[wght].ttf", 42, b"Medium"), (110, 100, 92, 255))
    return bg


if __name__ == "__main__":
    assets, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    tw, th = 1500, 1100
    B = Image.new("RGB", (tw * 2, th * 5), (230, 226, 218))
    for i, (title, fn, note) in enumerate(STYLES):
        t = tile(assets, i + 1, title, fn, note)
        r, c = divmod(i, 2)
        B.paste(t.convert("RGB"), (c * tw, r * th))
        t.convert("RGB").save(os.path.join(out, "style_%02d.jpg" % (i + 1)), quality=88)
    B.save(os.path.join(out, "Wedding_Styles_v2.jpg"), quality=85)
    print("ok")
