#!/usr/bin/env python3
"""Download the fifteen public-domain Leonardo sheets listed in sheets/meta.json from
Wikimedia Commons, as standard 1280px thumbnails (Commons only serves listed thumbnail sizes to scripts), into sheets/<name>.jpg. Stdlib only."""
import json, pathlib, time, urllib.error, urllib.parse, urllib.request
HERE = pathlib.Path(__file__).resolve().parent.parent / "sheets"
UA = {"User-Agent": "leonardo-skill-fetch/1.0 (personal use)"}

def get(url):
    for attempt in range(6):  # Commons rate-limits bursts with 429
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))
meta = json.load(open(HERE / "meta.json"))
for name, m in meta.items():
    out = HERE / f"{name}.jpg"
    if out.exists():
        print("have", out.name); continue
    title = m["commons"]
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo",
                                "iiprop": "url", "iiurlwidth": 1280, "format": "json"})
    try:
        r = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
        info = next(iter(r["query"]["pages"].values()))["imageinfo"][0]
        url = info.get("thumburl") or info["url"]
        out.write_bytes(get(url))
    except urllib.error.HTTPError as e:
        print("skip", name, e.code, "- rerun later; finished files are kept"); continue
    print("got ", out.name, out.stat().st_size, "bytes")
    time.sleep(5)
