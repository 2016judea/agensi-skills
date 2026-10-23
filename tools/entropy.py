#!/usr/bin/env python3
"""Flag long high-entropy tokens (likely secrets) that mix letters and digits."""
import math, os, re, sys
from collections import Counter
TOK = re.compile(r'[A-Za-z0-9+_=-]{24,}')
def ent(s):
    c = Counter(s); n = len(s)
    return -sum(v/n*math.log2(v/n) for v in c.values())
for root, _, files in os.walk(sys.argv[1]):
    for f in files:
        p = os.path.join(root, f)
        try: lines = open(p, encoding='utf-8').read().splitlines()
        except Exception: continue
        for i, line in enumerate(lines, 1):
            for t in TOK.findall(line):
                if re.search(r'\d', t) and re.search(r'[A-Za-z]', t) and ent(t) > 4.0 and not re.fullmatch(r'[A-Za-z]+[A-Za-z0-9]*', t.replace('_','').replace('-','')) or (len(t) > 30 and sum(ch.isdigit() for ch in t) >= 6 and ent(t) > 3.5):
                    print(f"{p}:{i}: possible secret: {t[:12]}...")
