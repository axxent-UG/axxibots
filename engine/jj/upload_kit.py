#!/usr/bin/env python3
"""Upload a finished kit (download PDFs + listing images) to AXXIBOTS storage via jj-kit-upload.

Usage: JJ_UPLOAD_KEY=<key> upload_kit.py <kit.json> <kit_out_dir> <listing_out_dir>
The key is a short-lived upload key from axx.jj_upload_keys (bound to one kit, expires).
"""
import glob, json, os, sys, urllib.parse, urllib.request

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
    with urllib.request.urlopen(req, timeout=120) as r:
        print(name, r.status, json.loads(r.read()).get("bytes"))


def main():
    cfg = json.load(open(sys.argv[1]))
    kit_dir, listing_dir = sys.argv[2], sys.argv[3]
    title = cfg["title"].replace(" ", "_")
    for size in ("letter", "a4"):
        put(os.path.join(kit_dir, "%s_%s.pdf" % (cfg["slug"], size)), "%s_%s.pdf" % (title, "US_Letter" if size == "letter" else "A4"), "download")
    for i, p in enumerate(sorted(glob.glob(os.path.join(listing_dir, "*.jpg")))[:10]):
        stem = os.path.basename(p)[:-4]
        cap = CAPTIONS.get(stem) or ("Preview: " + stem.split("_", 2)[-1].replace("_letter", "").replace("_", " "))
        put(p, os.path.basename(p), "image", rank=i + 1, caption=cap)


if __name__ == "__main__":
    main()
