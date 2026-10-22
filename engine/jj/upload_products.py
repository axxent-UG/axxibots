#!/usr/bin/env python3
"""Upload products built by build_products.py. Keys come as JSON {slug: upload_key} in JJ_UPLOAD_KEYS.

Usage: JJ_UPLOAD_KEYS='{"slug": "key", ...}' upload_products.py <collection.json> <products_out_dir>
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import upload_kit as uk


def main():
    col = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    keys = json.loads(os.environ["JJ_UPLOAD_KEYS"])
    for prod in col["products"]:
        if prod["slug"] not in keys:
            continue
        os.environ["JJ_UPLOAD_KEY"] = keys[prod["slug"]]
        pdir = os.path.join(out, prod["slug"], "pages")
        ldir = os.path.join(out, prod["slug"], "listing")
        name = prod["title"].replace(" ", "_")
        print("==", prod["slug"])
        uk.put(os.path.join(pdir, "%s_letter.pdf" % prod["slug"]), name + "_US_Letter.pdf", "download")
        uk.put(os.path.join(pdir, "%s_a4.pdf" % prod["slug"]), name + "_A4.pdf", "download")
        z = uk.make_jpg_zip({"slug": prod["slug"], "title": prod["title"]}, pdir, os.path.join(pdir, name + "_JPG_US_Letter.zip"))
        uk.put(z, os.path.basename(z), "download")
        for i, p in enumerate(sorted(glob.glob(os.path.join(ldir, "*.jpg")))[:10]):
            stem = os.path.basename(p)[:-4]
            cap = uk.CAPTIONS.get(stem) or "Preview page"
            uk.put(p, os.path.basename(p), "image", rank=i + 1, caption=cap)


if __name__ == "__main__":
    main()
