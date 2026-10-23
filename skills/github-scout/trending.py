#!/usr/bin/env python3
"""Pull github.com/trending and write a dated digest.

usage: trending.py [daily|weekly|monthly] [--lang python] [--out DIR]
Writes DIR/YYYY-MM-DD-<since>[-lang].md and prints it. No auth; the page is public HTML.
"""
import argparse, datetime, html, os, re, sys, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("since", nargs="?", default="weekly", choices=["daily", "weekly", "monthly"])
ap.add_argument("--lang", default="")
ap.add_argument("--out", default=os.path.expanduser("~/.claude/github-trending"))
a = ap.parse_args()

url = f"https://github.com/trending/{a.lang}?since={a.since}".replace("trending/?", "trending?")
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
page = urllib.request.urlopen(req, timeout=30).read().decode()

def clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())

rows = []
for art in page.split('<article class="Box-row">')[1:]:
    m = re.search(r'<h2[^>]*>.*?href="/([^"]+)"', art, re.S)
    if not m:
        continue
    desc = re.search(r'<p class="col-9[^"]*">(.*?)</p>', art, re.S)
    lang = re.search(r'itemprop="programmingLanguage">(.*?)<', art)
    stars = re.search(r'href="/[^"]+/stargazers"[^>]*>(.*?)</a>', art, re.S)
    gained = re.search(r'([\d,]+) stars (today|this week|this month)', art)
    rows.append(dict(repo=m.group(1), desc=clean(desc.group(1)) if desc else "",
                     lang=lang.group(1) if lang else "-", stars=clean(stars.group(1)) if stars else "?",
                     gained=gained.group(1) if gained else "?"))
if not rows:
    sys.exit(f"0 repos parsed from {url}: GitHub changed the trending markup, fix the regexes")

today = datetime.date.today().isoformat()
lines = [f"# GitHub trending, {a.since}{' / ' + a.lang if a.lang else ''}, {today}", "",
         f"Source: {url}", "", "| repo | lang | stars | gained | what it is |", "|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| [{r['repo']}](https://github.com/{r['repo']}) | {r['lang']} | {r['stars']} | +{r['gained']} | {r['desc'].replace('|', '/')} |")
out = "\n".join(lines) + "\n"
os.makedirs(a.out, exist_ok=True)
path = os.path.join(a.out, f"{today}-{a.since}{'-' + a.lang if a.lang else ''}.md")
open(path, "w").write(out)
print(out); print(f"wrote {path}", file=sys.stderr)
