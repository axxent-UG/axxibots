#!/usr/bin/env python3
"""Split-and-bundle step, part 2: bundle already-built products into one listing (no new art).

Usage: build_bundles.py <bundle.json> <out_dir> [--upload]   (upload needs JJ_UPLOAD_KEY)
bundle.json: {"slug", "title", "badge_title", "badge_sub", "price_eur", "section": "Bundles",
  "components": [{"title": "...", "dir": "/path/to/<product>"}],   # dir holds pages/ and listing/
  "cover_lines": [...], "facts": {...}}
Outputs <out>/<slug>/pages (US Letter + A4 PDFs, each under Etsy's 20 MB limit, split into parts if
needed) and <out>/<slug>/listing (cover collage of the component covers, what's inside, previews).
"""
import glob, io, json, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import build_kit as bk
import build_cover as bc

LIMIT = 19_000_000
DPI = 300


def pages_of(comp, size):
    pd = os.path.join(comp["dir"], "pages")
    return sorted(p for p in glob.glob(os.path.join(pd, "*_%s.jpg" % size)))


def pdf_bytes(paths, q):
    ims = []
    for p in paths:
        b = io.BytesIO()
        Image.open(p).convert("RGB").save(b, "JPEG", quality=q, optimize=True)
        ims.append(Image.open(io.BytesIO(b.getvalue())))
    out = io.BytesIO()
    ims[0].save(out, "PDF", save_all=True, append_images=ims[1:], resolution=DPI)
    return out.getvalue()


def write_pdfs(spec, size, pdir):
    """One PDF per size if it fits at quality >= 80, otherwise one part per component group."""
    allp = [p for c in spec["components"] for p in pages_of(c, size)]
    for q in (88, 84, 80):
        data = pdf_bytes(allp, q)
        if len(data) < LIMIT:
            path = os.path.join(pdir, "%s_%s.pdf" % (spec["slug"], size))
            open(path, "wb").write(data)
            return [path]
    # split by component, packing components greedily into parts under the limit
    parts, cur = [], []
    for c in spec["components"]:
        trial = cur + pages_of(c, size)
        if cur and len(pdf_bytes(trial, 84)) >= LIMIT:
            parts.append(cur)
            cur = pages_of(c, size)
        else:
            cur = trial
    parts.append(cur)
    out = []
    for i, ps in enumerate(parts, 1):
        path = os.path.join(pdir, "%s_%s_part%d.pdf" % (spec["slug"], size, i))
        open(path, "wb").write(pdf_bytes(ps, 84))
        out.append(path)
    return out


def cover(spec, ldir):
    W, H = bc.W, bc.H
    import build_pockets
    c = build_pockets.mood_background(W, H, seed=sum(map(ord, spec["slug"])) % 97)
    # fan real pages (two per component) instead of the component covers, which carry their own ribbons
    pages = []
    for x in spec["components"]:
        pages += pages_of(x, "letter")[:2]
    spots = [(520, 980, 9), (2480, 980, -9), (950, 860, -5), (2050, 860, 6), (1500, 760, 1), (700, 1350, -11), (2300, 1350, 10)]
    for p, (x, y, a) in zip(pages[:7], spots):
        bc.paste_rot(c, bc.page_piece(p, 900), x, y, a)
    bc.ribbon(c, "BUNDLE · DIGITAL DOWNLOAD")
    bc.paste_rot(c, bc.badge(spec["badge_title"], spec["badge_sub"]), W // 2, 1180, 0)
    bc.info_band(c, spec["cover_lines"])
    c.convert("RGB").save(os.path.join(ldir, "01_cover.jpg"), quality=92)


def inside(spec, ldir):
    W, H = bc.W, bc.H
    c = bc.wood(W, H, seed=11)
    comps = spec["components"]
    n = len(comps)
    cols = min(n, 3 if n != 4 else 2)
    rows = (n + cols - 1) // cols
    gx = 70
    tw = (W - (cols + 1) * gx) // cols
    th = int(tw * 0.8)
    top = 230
    if rows * (th + 110) > H - 300 - top:  # too tall: shrink to fit
        th = (H - 300 - top) // rows - 110
        tw = int(th / 0.8)
        gx = (W - cols * tw) // (cols + 1)
    gy = max(30, (H - 300 - top - rows * (th + 90)) // (rows + 1))
    d = ImageDraw.Draw(c)
    bk.text_center(d, W // 2, 130, "What's inside: %d products in one download" % n, bk.F_ITAL(96), (247, 236, 214, 255))
    for i, x in enumerate(comps):
        r, k = divmod(i, cols)
        im = bc.page_piece(os.path.join(x["dir"], "listing", "01_cover.jpg"), tw)
        im, pad = bc.drop_shadow(im, off=(8, 12), blur=12, alpha=150)
        px, py = gx + k * (tw + gx), top + gy + r * (th + 90 + gy)
        c.alpha_composite(im, (px - pad, py - pad))
        np_ = len(pages_of(x, "letter"))
        bk.text_center(d, px + tw // 2, py + th + 50, "%s · %d pages" % (x["title"], np_), bk.F_ITAL(58), (247, 236, 214, 255))
    bc.info_band(c, spec["inside_lines"])
    c.convert("RGB").save(os.path.join(ldir, "02_whats_inside.jpg"), quality=90)
    # previews: the component listings' best preview pages (already watermarked)
    k = 3
    for x in comps:
        for p in sorted(glob.glob(os.path.join(x["dir"], "listing", "0[3-9]_*.jpg")))[:2]:
            if k > 10:
                break
            Image.open(p).save(os.path.join(ldir, "%02d_%s" % (k, os.path.basename(p)[3:])), quality=88)
            k += 1


def main():
    spec = json.load(open(sys.argv[1]))
    out = os.path.join(sys.argv[2], spec["slug"])
    pdir, ldir = os.path.join(out, "pages"), os.path.join(out, "listing")
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(ldir, exist_ok=True)
    files = []
    for size in ("letter", "a4"):
        files += write_pdfs(spec, size, pdir)
    # page JPGs for the JPG ZIP (upload step zips <slug>_*_letter.jpg)
    n = 0
    for c in spec["components"]:
        for p in pages_of(c, "letter"):
            n += 1
            Image.open(p).save(os.path.join(pdir, "%s_%03d_letter.jpg" % (spec["slug"], n)), quality=88, dpi=(DPI, DPI))
    cover(spec, ldir)
    inside(spec, ldir)
    print(json.dumps({"slug": spec["slug"], "pages": n, "pdfs": [(os.path.basename(f), os.path.getsize(f)) for f in files]}))




def upload(spec, out_dir):
    """Upload a built bundle (PDF parts + listing images; no JPG ZIP: Etsy allows 5 files). Key in JJ_UPLOAD_KEY."""
    import upload_kit as uk
    out = os.path.join(out_dir, spec["slug"])
    name = spec["title"].replace(" ", "_")
    for p in sorted(glob.glob(os.path.join(out, "pages", "*.pdf"))):
        tail = os.path.basename(p)[len(spec["slug"]) + 1:-4]  # letter_part1 / a4
        size, _, part = tail.partition("_")
        label = ("US_Letter" if size == "letter" else "A4") + ("_" + part.replace("part", "Part_") if part else "")
        uk.put(p, "%s_%s.pdf" % (name, label), "download")
    caps = {"01_cover": "Cover: the Christmas bundle", "02_whats_inside": "What's inside: all products in the bundle"}
    for i, p in enumerate(sorted(glob.glob(os.path.join(out, "listing", "*.jpg")))[:10]):
        stem = os.path.basename(p)[:-4]
        uk.put(p, os.path.basename(p), "image", rank=i + 1, caption=caps.get(stem, "Preview page"))


if __name__ == "__main__":
    if "--upload" in sys.argv:
        upload(json.load(open(sys.argv[1])), sys.argv[2])
    else:
        main()
