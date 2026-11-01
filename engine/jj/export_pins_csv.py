#!/usr/bin/env python3
"""Write Pinterest bulk-create CSVs (one per weekly batch, <=100 rows) from pins_scheduled.json.

Usage: export_pins_csv.py <pins_scheduled.json> <out_dir>
Columns follow Pinterest's bulk template: Title, Media URL, Pinterest board, Thumbnail, Description, Link, Publish date, Keywords.
Publish date is UTC (YYYY-MM-DDTHH:MM:SS). Boards that don't exist yet are created by Pinterest.
"""
import csv, json, os, sys

PUB = "https://xhztnnhrcqwuooezcbgh.supabase.co/storage/v1/object/public/pins/"
pins = json.load(open(sys.argv[1]))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
batches = {}
for p in pins:
    if p.get("batch"):
        batches.setdefault(p["batch"], []).append(p)
for b, rows in sorted(batches.items()):
    rows.sort(key=lambda p: p["publish_at"])
    path = os.path.join(out, f"Pinterest_Pins_{b}_{rows[0]['publish_at'][:10]}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"])
        for p in rows:
            w.writerow([p["title"], PUB + f"{p['slug']}/{p['file']}", p["board"], "", p["description"], p["link"] + "?utm_source=pinterest&utm_medium=social&utm_campaign=" + b,
                        p["publish_at"], p["keywords"]])
    print(path, len(rows))
