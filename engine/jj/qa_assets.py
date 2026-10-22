#!/usr/bin/env python3
"""Deterministic QA for generated kit illustrations (runs before the vision check).

Motifs (transparent background) fail when:
  - edge:   the drawing touches the image border (cut off)
  - patch:  the outline of the shape is mostly flat light paper (a background patch instead of transparency)
  - empty:  almost nothing drawn, or no transparency at all
Cards/papers fail when they are not fully opaque or look blank.
Prints one JSON line per asset; exit code 0. Usage: qa_assets.py <assets_dir> [keys...]
"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageFilter


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
    reasons, warn = [], []
    if cover < 0.04 or cover > 0.92:
        reasons.append("empty_or_no_transparency")
    if edge > 0.2:
        reasons.append("cut_off_at_edge")
    elif edge > 0.02:
        warn.append("touches_edge")
    if patch > 0.45:
        reasons.append("background_patch")
    return {"cover": round(float(cover), 3), "edge": round(float(edge), 3), "patch": round(patch, 3), "pass": not reasons, "reasons": reasons, "warn": warn}


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
        r = check_motif(im) if k.startswith("m") else check_full(im)
        print(json.dumps(dict(key=k, **r)))
