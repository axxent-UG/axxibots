#!/usr/bin/env python3
"""Deterministic QA for generated kit illustrations (runs before the vision check).

Motifs (transparent background) fail when:
  - edge:   the drawing touches the image border (cut off)
  - patch:  the outline of the shape is mostly flat light paper (a background patch instead of transparency)
  - empty:  almost nothing drawn, or no transparency at all
  - colour: (warning) muted, faded or brownish palette; owner standard is rich, saturated colour
Cards/papers fail when they are not fully opaque or look blank.
Prints one JSON line per asset; exit code 0. Usage: qa_assets.py <assets_dir> [keys...]
"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageFilter


# Colour standard (owner 22.10.2026): muted = mostly tan/brown hues and little true red/green accent.
# Calibrated on the muted Christmas Post art (brown 0.46-0.98, accent 0.0-0.37).
BROWN_MAX = 0.6
ACCENT_MIN = 0.25
# A motif must be an isolated object: a silhouette that fills most of its bounding box is a square
# vignette/wreath (calibrated 23.10.2026 on the rejected Witching Hour batch).
BOX_FILL_MAX = 0.88  # only extreme cases; vignettes overlap with good motifs below this -> vision QA


def check_motif(im):
    a = np.asarray(im.getchannel("A"), np.float32)
    rgb = np.asarray(im.convert("RGB"), np.float32)
    h, w = a.shape
    solid = a > 40
    cover = solid.mean()
    b = 6
    edge = max(solid[:b].mean(), solid[-b:].mean(), solid[:, :b].mean(), solid[:, -b:].mean())
    # outline ring of the shape: solid pixels within 10px of transparency
    m = Image.fromarray((solid * 255).astype(np.uint8))
    inner = np.asarray(m.filter(ImageFilter.MinFilter(21))) > 0
    ring = solid & ~inner
    mx, mn = rgb.max(2), rgb.min(2)
    light_flat = (mx > 185) & ((mx - mn) < 60)
    patch = float(light_flat[ring].mean()) if ring.any() else 0.0
    dark_flat = (mx < 70) & ((mx - mn) < 40)
    dark_patch = float(dark_flat[ring].mean()) if ring.any() else 0.0
    ys, xs = np.nonzero(solid)
    box_fill = float(solid.sum() / ((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1))) if ys.size else 0.0
    hsv = np.asarray(im.convert("RGB").convert("HSV"), np.float32) / 255
    hue, sat, val = hsv[..., 0][solid] * 360, hsv[..., 1][solid], hsv[..., 2][solid]
    col = sat > 0.25
    # brown = dull tan/ochre: orange-yellow hues that are NOT bright, saturated pumpkin orange or gold
    brown = float((col & (hue >= 15) & (hue < 55) & ((val < 0.62) | (sat < 0.6))).mean()) if hue.size else 0.0
    vivid_orange = (hue >= 15) & (hue < 45) & (val >= 0.62) & (sat >= 0.6)
    accent = float((col & ((((hue < 12) | (hue > 335)) & (val > 0.35) & (sat > 0.45)) | ((hue >= 75) & (hue < 300)) | vivid_orange)).mean()) if hue.size else 0.0
    reasons, warn = [], []
    if brown > BROWN_MAX and accent < ACCENT_MIN:
        warn.append("muted_colours")
    if cover < 0.04 or cover > 0.92:
        reasons.append("empty_or_no_transparency")
    if edge > 0.2:
        reasons.append("cut_off_at_edge")
    elif edge > 0.02:
        warn.append("touches_edge")
    if patch > 0.45:
        reasons.append("background_patch")
    if dark_patch > 0.45:
        reasons.append("dark_background_patch")
    if box_fill > BOX_FILL_MAX:
        reasons.append("vignette_not_isolated")
    return {"cover": round(float(cover), 3), "edge": round(float(edge), 3), "patch": round(patch, 3), "brown": round(brown, 3), "accent": round(accent, 3), "dark_patch": round(dark_patch, 3), "box_fill": round(box_fill, 3), "pass": not reasons, "reasons": reasons, "warn": warn}


def check_full(im):
    a = np.asarray(im.getchannel("A"))
    g = np.asarray(im.convert("L"), np.float32)
    reasons = []
    if a.min() < 250:
        reasons.append("not_opaque")
    if g.std() < 6:
        reasons.append("blank")
    return {"std": round(float(g.std()), 1), "pass": not reasons, "reasons": reasons}


if __name__ == "__main__":
    d = sys.argv[1]
    keys = sys.argv[2:] or [os.path.basename(p)[:-4] for p in sorted(glob.glob(os.path.join(d, "*.png")))]
    for k in keys:
        im = Image.open(os.path.join(d, k + ".png")).convert("RGBA")
        has_alpha = np.asarray(im.getchannel("A")).min() < 250
        r = check_motif(im) if has_alpha else check_full(im)
        print(json.dumps(dict(key=k, **r)))
