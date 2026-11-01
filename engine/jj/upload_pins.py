#!/usr/bin/env python3
"""Upload pins (texts + images) to AXXIBOTS via jj-pin-upload.

Usage: upload_pins.py <pins_scheduled.json> <pin_img_dir> <keys_file>
keys_file: whitespace-separated "slug:upload_key" pairs (short-lived keys from axx.jj_upload_keys, purpose='pins').
Per pin: first the texts (pin.json -> axx.jj_pins row), then the image (public bucket pins/<slug>/<file>).
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("JJ_PIN_URL", "https://xhztnnhrcqwuooezcbgh.supabase.co/functions/v1/jj-pin-upload")


def put(key, name, variant, data):
    q = urllib.parse.urlencode({"name": name, "variant": variant})
    req = urllib.request.Request(BASE + "?" + q, data=data, method="PUT", headers={"x-upload-key": key, "content-type": "application/octet-stream"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                return {"error": e.code, "body": e.read()[:200].decode(errors="replace")}
            time.sleep(2 * (attempt + 1))


def main():
    pins = json.load(open(sys.argv[1]))
    img_dir = sys.argv[2]
    keys = dict(kv.split(":", 1) for kv in open(sys.argv[3]).read().split())
    def one(p):
        k = keys.get(p["slug"])
        if not k:
            return p["file"], {"error": "no_key"}
        meta = {"title": p["title"], "description": p["description"], "board": p["board"], "keywords": p["keywords"],
                "status": "planned" if p.get("publish_at") else "hold", "publish_at": (p["publish_at"] + "Z") if p.get("publish_at") else None,
                "export_batch": p.get("batch")}
        r1 = put(k, "pin.json", p["variant"], json.dumps(meta).encode())
        if not r1.get("ok"):
            return p["file"], r1
        return p["file"], put(k, p["file"], p["variant"], open(os.path.join(img_dir, p["file"]), "rb").read())
    bad = 0
    with ThreadPoolExecutor(6) as ex:
        for f, r in ex.map(one, pins):
            if not r.get("ok"):
                bad += 1
                print("FAIL", f, r)
    print("done", len(pins), "failed", bad)


if __name__ == "__main__":
    main()
