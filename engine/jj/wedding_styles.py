#!/usr/bin/env python3
"""Wedding stationery styles (10 designs) + style board preview.

Usage: wedding_styles.py <assets_dir> <out_dir>
Renders, per style, a place card (tent, 3.5 x 2 in front), a menu (4 x 9 in) and a wine & drinks list
(4 x 9 in) with lines to write on by hand, and composes two style boards (5 styles each).
"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk

FD = os.path.join(os.path.dirname(__file__), "fonts")


def font(name, sz, var=None):
    f = ImageFont.truetype(os.path.join(FD, name), int(sz))
    if var:
        try:
            f.set_variation_by_name(var)
        except Exception:
            pass
    return f


STYLES = [
    dict(key="eucalyptus", name="Eucalyptus Sage", motif="w01_eucalyptus", bg=(251, 250, 245), ink=(70, 82, 68), accent=(122, 140, 118),
         script="GreatVibes-Regular.ttf", serif="CormorantGaramond[wght].ttf", serif_var=b"Medium", caps=True),
    dict(key="peony", name="Blush Peony", motif="w02_peony", bg=(253, 248, 246), ink=(110, 78, 78), accent=(190, 150, 100),
         script="PinyonScript-Regular.ttf", serif="CormorantGaramond[wght].ttf", serif_var=b"Medium", caps=True),
    dict(key="blacktie", name="Black Tie Gold", motif="w03_deco", bg=(22, 22, 24), ink=(206, 176, 108), accent=(206, 176, 108),
         script="Italiana-Regular.ttf", serif="Cinzel[wght].ttf", serif_var=b"Regular", caps=True, script_is_caps=True, double_frame=True),
    dict(key="terracotta", name="Terracotta Boho", motif="w04_pampas", bg=(248, 242, 234), ink=(120, 72, 52), accent=(176, 98, 66),
         script="Parisienne-Regular.ttf", serif="CormorantGaramond[wght].ttf", serif_var=b"SemiBold", caps=True),
    dict(key="whiterose", name="Classic White Rose", motif="w05_whiterose", bg=(255, 255, 255), ink=(52, 52, 52), accent=(120, 140, 110),
         script="GreatVibes-Regular.ttf", serif="Cinzel[wght].ttf", serif_var=b"Regular", caps=True),
    dict(key="dustyblue", name="Dusty Blue Hydrangea", motif="w06_hydrangea", bg=(246, 248, 250), ink=(66, 86, 110), accent=(106, 132, 160),
         script="PinyonScript-Regular.ttf", serif="Italiana-Regular.ttf", caps=True),
    dict(key="burgundy", name="Burgundy Autumn", motif="w07_burgundy", bg=(250, 245, 240), ink=(96, 30, 42), accent=(150, 110, 70),
         script="GreatVibes-Regular.ttf", serif="PlayfairDisplay[wght].ttf", serif_var=b"Regular", caps=True),
    dict(key="amalfi", name="Amalfi Lemon", motif="w08_lemons", bg=(255, 255, 255), ink=(30, 64, 128), accent=(232, 190, 40),
         script="Parisienne-Regular.ttf", serif="Cinzel[wght].ttf", serif_var=b"Regular", caps=True, tile_border=True),
    dict(key="botanical", name="Vintage Botanical", motif="w09_botanical", bg=(244, 238, 222), ink=(52, 42, 34), accent=(120, 96, 70),
         script="PinyonScript-Regular.ttf", serif="IMFeENsc28P.ttf", caps=False, paper=True),
    dict(key="wildflower", name="Wildflower Meadow", motif="w10_wildflower", bg=(252, 251, 247), ink=(92, 80, 110), accent=(140, 120, 170),
         script="Parisienne-Regular.ttf", serif="CormorantGaramond-Italic[wght].ttf", serif_var=b"Medium", caps=False),
]


def base(st, w, h, seed=1):
    if st.get("paper"):
        return bk.paper(w, h, st["bg"], seed, stains=False).convert("RGBA")
    return Image.new("RGBA", (w, h), st["bg"] + (255,))


def frame(st, im):
    d = ImageDraw.Draw(im)
    w, h = im.size
    m = int(min(w, h) * 0.05)
    d.rectangle((m, m, w - m, h - m), outline=st["accent"] + (255,), width=3)
    if st.get("double_frame"):
        d.rectangle((m + 14, m + 14, w - m - 14, h - m - 14), outline=st["accent"] + (255,), width=1)
    if st.get("tile_border"):
        for x in range(0, w, 60):
            d.rectangle((x, 0, x + 30, 18), fill=st["ink"] + (255,))
            d.rectangle((x + 30, h - 18, x + 60, h), fill=st["ink"] + (255,))


def motif(st, assets, w, h, flip=False):
    im = bk.trim(Image.open(os.path.join(assets, st["motif"] + ".png")).convert("RGBA"))
    im = bk.fit(im, w, h)
    return im.transpose(Image.FLIP_TOP_BOTTOM) if flip else im


def tc(d, x, y, s, f, fill):
    d.text((x, y), s, font=f, fill=fill, anchor="mm")


def caps(st, s):
    return s.upper() if st.get("caps") else s


def spaced(s, n=1):
    return (" " * n).join(s)


def place_card(st, assets, name="Charlotte Becker", w=1050, h=600):
    im = base(st, w, h, 3)
    frame(st, im)
    mo = motif(st, assets, int(w * 0.62), int(h * 0.36))
    im.alpha_composite(mo, ((w - mo.width) // 2, int(h * 0.07)))
    d = ImageDraw.Draw(im)
    if st.get("script_is_caps"):
        tc(d, w // 2, int(h * 0.66), name.upper(), font(st["script"], 74), st["ink"] + (255,))
    else:
        tc(d, w // 2, int(h * 0.66), name, font(st["script"], 112), st["ink"] + (255,))
    tc(d, w // 2, int(h * 0.86), spaced(caps(st, "Table 4")), font(st["serif"], 34, st.get("serif_var")), st["accent"] + (255,))
    return im


def lined_card(st, assets, title, sections, w=1200, h=2700):
    im = base(st, w, h, 5)
    frame(st, im)
    mo = motif(st, assets, int(w * 0.78), int(h * 0.16))
    im.alpha_composite(mo, ((w - mo.width) // 2, int(h * 0.045)))
    d = ImageDraw.Draw(im)
    y = int(h * 0.27)
    t = title.upper() if st.get("script_is_caps") else title
    sz = 120 if st.get("script_is_caps") else 190
    while d.textlength(t, font=font(st["script"], sz)) > w * 0.74 and sz > 40:
        sz -= 6
    tc(d, w // 2, y, t, font(st["script"], sz), st["ink"] + (255,))
    tc(d, w // 2, y + 140, spaced(caps(st, "Sophie & Max  ·  12.06.2027")), font(st["serif"], 34, st.get("serif_var")), st["accent"] + (255,))
    y += 300
    step = (h - 260 - y) // len(sections)
    fh = font(st["serif"], 52, st.get("serif_var"))
    for s in sections:
        tc(d, w // 2, y, spaced(caps(st, s)), fh, st["ink"] + (255,))
        for k in range(2):
            ly = y + 95 + k * 95
            d.line((180, ly, w - 180, ly), fill=st["accent"] + (200,), width=2)
        y += step
    sm = motif(st, assets, int(w * 0.32), int(h * 0.05))
    im.alpha_composite(sm, ((w - sm.width) // 2, h - 230))
    return im


def board(styles, assets, out_path, cols=2):
    tw, th = 1500, 1260
    rows = (len(styles) + cols - 1) // cols
    B = Image.new("RGB", (tw * cols, th * rows), (236, 232, 226))
    for i, st in enumerate(styles):
        menu = lined_card(st, assets, "Menu", ["Starter", "Main Course", "Dessert"])
        wine = lined_card(st, assets, "Wine & Drinks", ["White", "Red", "Sparkling", "Signature Cocktail"])
        pc = place_card(st, assets)
        tile = Image.new("RGBA", (tw, th), (236, 232, 226, 255))
        mh = 960
        for j, card in enumerate((menu, wine)):
            c = card.resize((int(card.width * mh / card.height), mh), Image.LANCZOS)
            sh, pad = bk.drop_shadow(c, off=(8, 12), blur=14, alpha=90)
            tile.alpha_composite(sh, (90 + j * 470 - pad, 70 - pad))
        c = pc.resize((560, 320), Image.LANCZOS)
        sh, pad = bk.drop_shadow(c, off=(8, 12), blur=14, alpha=90)
        tile.alpha_composite(sh, (900 - pad, 420 - pad))
        d = ImageDraw.Draw(tile)
        d.text((tw // 2, th - 120), "%d  ·  %s" % (STYLES.index(st) + 1, st["name"]), font=font("CormorantGaramond[wght].ttf", 76, b"SemiBold"), fill=(60, 52, 48), anchor="mm")
        r, c = divmod(i, cols)
        B.paste(tile.convert("RGB"), (c * tw, r * th))
    B.save(out_path, quality=86)


if __name__ == "__main__":
    assets, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    board(STYLES, assets, os.path.join(out, "Wedding_Styles_1-10.jpg"))
    print("ok")
