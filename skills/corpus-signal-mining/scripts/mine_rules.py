#!/usr/bin/env python3
"""Association rules (market-basket) over baskets, pure Python.

Input: JSONL, one basket per line: {"id": "...", "items": ["a", "b", ...]}
Usage: python3 mine_rules.py baskets.jsonl [--min-support 6] [--min-conf 0.65] [--min-lift 1.15] [--max-lhs 2]
Prints rules X -> y with support (count), confidence and lift, strongest lift first.
"""
import argparse, itertools, json
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("path"); ap.add_argument("--min-support", type=int, default=6)
ap.add_argument("--min-conf", type=float, default=0.65); ap.add_argument("--min-lift", type=float, default=1.15)
ap.add_argument("--max-lhs", type=int, default=2)
a = ap.parse_args()

baskets = [frozenset(json.loads(l)["items"]) for l in open(a.path) if l.strip()]
baskets = [b for b in baskets if b]
N = len(baskets)
sup1 = Counter(t for b in baskets for t in b)
items = sorted(t for t, c in sup1.items() if c >= a.min_support)

def s(xs):
    xs = set(xs); return sum(1 for b in baskets if xs <= b)

rules = []
for k in range(1, a.max_lhs + 1):
    for lhs in itertools.combinations(items, k):
        sl = s(lhs)
        if sl < a.min_support: continue
        for y in items:
            if y in lhs: continue
            sxy = s(lhs + (y,))
            if sxy < a.min_support: continue
            conf = sxy / sl; lift = conf / (sup1[y] / N)
            if conf >= a.min_conf and lift >= a.min_lift:
                rules.append((lift, conf, sxy, lhs, y))
print(f"{N} baskets, {len(items)} items at support>={a.min_support}, {len(rules)} rules")
for lift, conf, sxy, lhs, y in sorted(rules, reverse=True)[:60]:
    print(f"{' + '.join(lhs):45s} -> {y:25s} n={sxy:<4d} conf={conf:.2f} lift={lift:.2f}")
