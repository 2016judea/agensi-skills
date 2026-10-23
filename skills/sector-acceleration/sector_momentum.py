#!/usr/bin/env python3
"""Sector acceleration scan: which sectors are speeding up, vs the S&P 500.

Answers "which sectors show the most positive acceleration?" with the second
derivative of price, not the first. A sector up 20% over 3 months that went
nowhere last month is DEcelerating; one flat on the year that jumped last month
is accelerating.

Columns, all in percent:
    1m/3m/6m/12m  trailing returns (21/63/126/252 trading days)
    accel         last month's return minus the avg monthly pace of the two
                  months before it. Positive = speeding up. The sort key.
    RS1m          change in the sector/SPY ratio over the last month
    RSpace        avg monthly change in that ratio over the two months before.
                  RS1m > RSpace = the lead over the index is WIDENING.
    RS3m/RS3p     ratio change over the last 3 months / the 3 before that
    v50/v200      distance above the 50- and 200-day moving averages
    offHi         distance below the 52-week high

Reading it: the cleanest signal is a sector where
accel > 0 AND RS1m > RSpace > 0 AND 12m is flat-to-negative -- a turn from a
base, not a crowded trend. A high accel on a name already +70% on the year is a
restart late in a move. Check RSP vs SPY for breadth: if equal-weight lags,
the acceleration is narrow. Then read kalshi_macro.py for the rate path,
because long-duration groups (software) and inflation groups (energy, gold,
copper) are two sides of the same rate bet.

CLI:
    python sector_momentum.py            # default universe, writes a dated CSV
    python sector_momentum.py XLK SMH    # extra tickers appended

Every run writes data/sector_momentum/<last-bar-date>.csv so a later session
can score the call against what actually happened.
"""
from __future__ import annotations

import csv
import pathlib
import statistics as st
import sys

from price_history import daily_bars

UNIVERSE = {
    "SPY": "S&P 500", "RSP": "S&P equal-wt", "IWM": "Small caps",
    # the 11 GICS sector SPDRs
    "XLK": "Tech", "XLC": "Comm Svcs", "XLY": "Cons Disc", "XLF": "Financials",
    "XLI": "Industrials", "XLB": "Materials", "XLE": "Energy",
    "XLV": "Health Care", "XLP": "Staples", "XLU": "Utilities",
    "XLRE": "Real Estate",
    # industries that move apart from their parent sector
    "SMH": "Semis", "IGV": "Software", "KRE": "Reg Banks", "XBI": "Biotech",
    "ITA": "Aero/Def", "XHB": "Homebuilders", "GDX": "Gold miners",
    "COPX": "Copper miners", "URA": "Uranium",
}
COLS = ["1m", "3m", "6m", "12m", "accel", "RS1m", "RSpace", "RS3m", "RS3p",
        "v50", "v200", "offHi"]


def _ret(p, n):
    return p[-1] / p[-1 - n] - 1


def scan(universe: dict[str, str]):
    bars = {t: daily_bars(t, years=2) for t in universe}
    spy = dict(bars["SPY"])
    rows = []
    for t, b in bars.items():
        p = [c for _, c in b]
        r1, r3 = _ret(p, 21), _ret(p, 63)
        # relative-strength line on dates both series share
        rs = [c / spy[d] for d, c in b if d in spy]
        rows.append({
            "ticker": t, "name": universe[t],
            "1m": r1, "3m": r3, "6m": _ret(p, 126), "12m": _ret(p, 252),
            "accel": r1 - ((1 + r3) / (1 + r1) - 1) / 2,
            "RS1m": rs[-1] / rs[-22] - 1,
            "RSpace": (rs[-22] / rs[-64] - 1) / 2,
            "RS3m": rs[-1] / rs[-64] - 1,
            "RS3p": rs[-64] / rs[-127] - 1,
            "v50": p[-1] / st.mean(p[-50:]) - 1,
            "v200": p[-1] / st.mean(p[-200:]) - 1,
            "offHi": p[-1] / max(p[-252:]) - 1,
        })
    rows.sort(key=lambda r: -r["accel"])
    return bars["SPY"][-1][0], rows


def main(argv):
    universe = dict(UNIVERSE)
    for t in argv:
        universe.setdefault(t.upper(), t.upper())
    asof, rows = scan(universe)
    print(f"last bar {asof}")
    print(f"{'tkr':5}{'name':14}" + "".join(f"{c:>7}" for c in COLS))
    for r in rows:
        print(f"{r['ticker']:5}{r['name']:14}"
              + "".join(f"{r[c]*100:7.1f}" for c in COLS))
    out = pathlib.Path(__file__).parent / "data" / "sector_momentum" / f"{asof}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "name"] + COLS)
        w.writeheader()
        w.writerows({**r, **{c: round(r[c] * 100, 2) for c in COLS}} for r in rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
