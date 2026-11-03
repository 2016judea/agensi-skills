#!/usr/bin/env python3
"""Usage ledger: the data that decides when a free skill earns a price.

Every listing starts free. This snapshots what the marketplace reports so the monetize decision rests on
a time series, not a guess. Agensi's `uses` counts every use or download by someone other than us.

  usage/agensi.tsv     date, slug, uses, rating, reviews, pricing   (one row per listing per day)
  usage/benchmark.tsv  date, rank, slug, install_count, price_usd   (Agensi's popular list, for scale)

Usage: usage.py              snapshot today (idempotent), print the 30-day leaders
       usage.py --report     print only, no snapshot

There is no threshold. Aidan reads this when he checks in and decides what "real usage" means then (11/03).
"""
import csv, datetime, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from agensi import call

WINDOW = 30
U = os.path.join(ROOT, "usage")
os.makedirs(U, exist_ok=True)
A, B = os.path.join(U, "agensi.tsv"), os.path.join(U, "benchmark.tsv")
today = datetime.date.today()


def rows(p):
    return list(csv.DictReader(open(p), delimiter="\t")) if os.path.exists(p) else []


def append(p, head, new):
    first = not os.path.exists(p)
    with open(p, "a", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        if first:
            w.writerow(head)
        w.writerows(new)


if "--report" not in sys.argv and not any(r["date"] == today.isoformat() for r in rows(A)):
    mine = call("my_skills", {})["skills"]
    append(A, ["date", "slug", "uses", "rating", "reviews", "pricing"],
           [[today, s["slug"], s["uses"] or 0, s["rating"] or "", s["reviews"] or 0, s["pricing"]] for s in mine])
    pop = call("get_popular", {})
    append(B, ["date", "rank", "slug", "install_count", "price_usd"],
           [[today, i + 1, p["slug"], p["install_count"], p["price_usd"]] for i, p in enumerate(pop)])

# uses gained in the window: latest count minus the count on the earliest day inside the window
hist = {}
for r in rows(A):
    hist.setdefault(r["slug"], []).append((r["date"], int(r["uses"])))
start = (today - datetime.timedelta(days=WINDOW)).isoformat()
gain, total, since = {}, {}, None
for s, h in hist.items():
    h.sort()
    inside = [u for d, u in h if d >= start]
    base = [u for d, u in h if d < start]
    first = base[-1] if base else 0  # a listing younger than the window counts from zero
    gain[s], total[s] = inside[-1] - first if inside else 0, h[-1][1]
    since = min(since or h[0][0], h[0][0])

themes = json.load(open(os.path.join(ROOT, "tools/themes.json")))
folder = {}  # Agensi slug -> our skills/<folder> name; the slug comes from the listing title, not the folder
for l in open(os.path.join(ROOT, "submissions.jsonl")):
    for s in re.findall(r"agensi\.io/skills/([a-z0-9-]+)", l):
        folder[s] = json.loads(l)["skill"]
def theme(slug):
    n = folder.get(slug, slug)
    return next((k for k, v in themes["plugins"].items()
                 if n in v["names"] or any(n.startswith(p) for p in v["prefixes"])), themes["default"])
sets = {}
for s, g in gain.items():
    sets[theme(s)] = sets.get(theme(s), 0) + g

bench = [r for r in rows(B) if r["date"] == max((r["date"] for r in rows(B)), default="")]
print(f"usage since {since}, last {WINDOW} days")
for s in sorted(gain, key=lambda s: -gain[s])[:10]:
    print(f"  {gain[s]:5d}  {total[s]:6d} all-time  {s}")
for g, n in sorted(sets.items(), key=lambda x: -x[1]):
    print(f"  {n:5d}  set  {g}")
if bench:
    print(f"  scale: Agensi #1 {bench[0]['slug']} {bench[0]['install_count']} installs, "
          f"#{bench[-1]['rank']} {bench[-1]['install_count']}")

