#!/usr/bin/env python3
"""Backtest a score against a baseline and random on labeled rows.

Input: JSONL rows: {"id": "...", "label": <number>, "<baseline col>": <number>, "<score col>": <number>, ...}
The label is the outcome you actually care about (upside $, converted 0/1, reply 0/1...).
Score columns must be computed ONLY from inputs available at runtime. If the score is LEARNED
from labels, compute it out-of-fold (see SKILL.md) before running this, or you are testing on
the answers.

Usage: python3 backtest.py rows.jsonl --baseline count_problems --score my_score [--score other] [--k 12] [--repeats 200]
Reports precision@K (share of top-K picks in the true top tercile of label) and Spearman rho.
"""
import argparse, json, random, statistics

ap = argparse.ArgumentParser()
ap.add_argument("path"); ap.add_argument("--baseline", required=True)
ap.add_argument("--score", action="append", required=True); ap.add_argument("--k", type=int, default=12)
ap.add_argument("--repeats", type=int, default=200); ap.add_argument("--seed", type=int, default=7)
a = ap.parse_args()
rows = [json.loads(l) for l in open(a.path) if l.strip()]
random.seed(a.seed)
labels = sorted(r["label"] for r in rows)
cut = labels[int(len(labels) * 2 / 3)] if len(labels) >= 3 else labels[-1]
top = {r["id"] for r in rows if r["label"] >= cut}

def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for t in range(i, j + 1): r[o[t]] = (i + j) / 2
        i = j + 1
    return r

def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((p - mx) * (q - my) for p, q in zip(rx, ry))
    den = (sum((p - mx) ** 2 for p in rx) * sum((q - my) ** 2 for q in ry)) ** 0.5
    return num / den if den else 0.0

def prec(col):
    # ties broken randomly, averaged over repeats, so a coarse score is not flattered by order
    out = []
    for _ in range(a.repeats):
        rs = sorted(rows, key=lambda r: (r[col] if col else 0, random.random()), reverse=True)
        out.append(sum(r["id"] in top for r in rs[:a.k]) / a.k)
    return statistics.mean(out)

y = [r["label"] for r in rows]
print(f"n={len(rows)}  top tercile = label >= {cut}  K={a.k}")
print(f"{'selector':28s} precision@K  spearman")
print(f"{'RANDOM':28s} {prec(None):10.1%}  {0.0:8.2f}")
b = prec(a.baseline)
print(f"{'BASELINE ' + a.baseline:28s} {b:10.1%}  {spearman([r[a.baseline] for r in rows], y):8.2f}")
for c in a.score:
    p = prec(c)
    verdict = "beats baseline" if p > b + 0.03 else "does NOT clearly beat baseline"
    print(f"{c:28s} {p:10.1%}  {spearman([r[c] for r in rows], y):8.2f}   {verdict}")
