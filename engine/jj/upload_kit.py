#!/usr/bin/env python3
"""Upload a finished kit (download PDFs + listing images) to AXXIBOTS storage via jj-kit-upload.

Usage: JJ_UPLOAD_KEY=<key> upload_kit.py <kit.json> <kit_out_dir> <listing_out_dir>
The key is a short-lived upload key from axx.jj_upload_keys (bound to one kit, expires).
"""
import glob, io, json, os, sys, urllib.error, urllib.parse, urllib.request, zipfile

BASE = os.environ.get("JJ_UPLOAD_URL", "https://xhztnnhrcqwuooezcbgh.supabase.co/functions/v1/jj-kit-upload")
CAPTIONS = {
    "01_cover": "Cover: everything in the kit",
    "02_whats_inside": "What's inside: all printable pages",
}


def put(path, name, kind, rank=None, caption=None):
    q = {"name": name, "kind": kind}
    if rank:
        q["rank"] = str(rank)
    if caption:
        q["caption"] = caption
    data = open(path, "rb").read()
    req = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(q), data=data, method="PUT",
                                 headers={"x-upload-key": os.environ["JJ_UPLOAD_KEY"], "content-type": "application/octet-stream"})
    import time
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                print(name, r.status, json.loads(r.read()).get("bytes"))
                return
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def make_jpg_zip(cfg, kit_dir, out_path, quality=90):
    """All US Letter pages as 300 dpi JPGs in one ZIP (buyers expect PDF + JPG; Etsy limit 20 MB per file)."""
    from PIL import Image
    pages = sorted(glob.glob(os.path.join(kit_dir, "%s_*_letter.jpg" % cfg["slug"])))
    folder = cfg["title"].replace(" Kit", "").replace(" ", "_") + "_JPG/"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
        for p in pages:
            b = io.BytesIO()
            Image.open(p).save(b, "JPEG", quality=quality, dpi=(300, 300), optimize=True)
            zf.writestr(folder + os.path.basename(p).replace(cfg["slug"] + "_", "").replace("_letter", ""), b.getvalue())
    size = os.path.getsize(out_path)
    if size > 19_500_000:
        return make_jpg_zip(cfg, kit_dir, out_path, quality - 6)
    return out_path


def main():
    cfg = json.load(open(sys.argv[1]))
    kit_dir, listing_dir = sys.argv[2], sys.argv[3]
    title = cfg["title"].replace(" ", "_")
    for size in ("letter", "a4"):
        put(os.path.join(kit_dir, "%s_%s.pdf" % (cfg["slug"], size)), "%s_%s.pdf" % (title, "US_Letter" if size == "letter" else "A4"), "download")
    z = make_jpg_zip(cfg, kit_dir, os.path.join(kit_dir, "%s_JPG_US_Letter.zip" % title))
    put(z, os.path.basename(z), "download")
    for i, p in enumerate(sorted(glob.glob(os.path.join(listing_dir, "*.jpg")))[:10]):
        stem = os.path.basename(p)[:-4]
        cap = CAPTIONS.get(stem) or ("Preview: " + stem.split("_", 2)[-1].replace("_letter", "").replace("_", " "))
        put(p, os.path.basename(p), "image", rank=i + 1, caption=cap)


if __name__ == "__main__":
    main()
