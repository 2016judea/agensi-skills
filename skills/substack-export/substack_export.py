#!/usr/bin/env python3
"""Export every post from a public Substack via its archive API — no login.

    https://<sub>.substack.com/api/v1/archive   (metadata, paginated)
    https://<sub>.substack.com/api/v1/posts/<slug>  (full body_html)

Usage:
    python3 substack_export.py --sub <subdomain> [--sub <another>] [--out substack_posts.json]

Every --sub is pulled; each row carries `sub`. Bodies are always fetched and
stripped to plain text.

PAGING, measured 2026-10-18: the archive API caps a page at ~24 rows whatever
`limit` asks for (pages of 23 then 28 were seen). A loop that stops on
`len(chunk) < 50` only ever sees the first page — e.g. 23 of 51 posts. The only valid stop is an
EMPTY page, and the cursor advances by rows returned, never by the limit asked.
"""
import argparse
import html
import json
import re
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")


def _get(url: str) -> bytes:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()


def _strip(h: str) -> str:
    # Substack wraps preformatted blocks (often used to hold poem
    # spacing) in a visually-hidden <label class="hide-text"> carrying editor
    # boilerplate — "Text within this block will maintain its original spacing
    # when published". It's chrome, not writing. Drop hide-text elements before tag-stripping.
    h = re.sub(r"<label[^>]*\bhide-text\b[^>]*>.*?</label>", " ", h or "",
               flags=re.I | re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def export(sub: str, bodies: bool = True):
    base = f"https://{sub}.substack.com/api/v1"
    posts, off, seen = [], 0, set()
    while True:
        chunk = json.loads(_get(f"{base}/archive?sort=new&limit=50&offset={off}"))
        # A short page is NOT the last page here (server caps at ~24 < limit).
        # Stop only on an empty page, or on a page that adds nothing new.
        new = [p for p in chunk if p.get("id") not in seen]
        if not new:
            break
        posts += new
        seen.update(p.get("id") for p in new)
        off += len(chunk)
    rows = []
    for p in posts:
        row = {
            "title": p.get("title"),
            "subtitle": p.get("subtitle"),
            "date": (p.get("post_date") or "")[:10],
            "slug": p.get("slug"),
            "wordcount": p.get("wordcount"),
            "id": p.get("id"),
            "url": p.get("canonical_url"),
            "sub": sub,
            "audience": p.get("audience"),
            "cover_image": p.get("cover_image"),
        }
        if bodies and p.get("slug"):
            try:
                d = json.loads(_get(f"{base}/posts/{p['slug']}"))
                row["body"] = _strip(d.get("body_html") or "")
            except Exception as e:
                row["body"] = f"[ERR {e}]"
        rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", action="append",
                    required=True, help="publication subdomain (the <sub> in <sub>.substack.com); repeatable")
    ap.add_argument("--out", default="substack_posts.json")
    ap.add_argument("--bodies", action="store_true", default=True)
    args = ap.parse_args()
    rows = []
    for sub in args.sub:
        got = export(sub, args.bodies)
        print(f"{sub}: {len(got)} posts")
        rows += got
    rows.sort(key=lambda r: r["date"])
    with open(args.out, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(rows)} posts -> {args.out}")
    for r in rows:
        print(f"  {r['date']}  {str(r['wordcount'] or '?'):>5}w  {r['sub']:<11}  {r['title']}")


if __name__ == "__main__":
    main()
