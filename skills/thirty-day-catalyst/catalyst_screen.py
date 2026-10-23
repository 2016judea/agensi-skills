#!/usr/bin/env python3
"""30-day catalyst screen: undervalued names in an accelerating sector, with a
dated event inside the window that forces the market to look.

The thesis: undervalued is always the right trade, and we
are usually right about WHAT is undervalued. The failure has been WHEN. This
exercise adds a hard constraint: enter and exit within 30 calendar days.

What that constraint changes. A cheap stock with no forcing event re-rates on
the market's schedule, and that can take quarters (no overhang means
"the thesis needs minds to change"). Inside 30 days, valuation can't be the
clock. It can only be the FILTER. The clock has to be an event on the calendar.
For a 30-day window that event is almost always an earnings print. Two
documented effects make it usable:
  * PRE  -- buy before the print, exit after it. You're betting the print
           revises the crowd. Binary, so size it as such.
  * POST -- post-earnings-announcement drift (Ball & Brown 1968; Bernard &
           Thomas 1989). After a beat the market under-reacts, and price
           keeps drifting toward the news for weeks. Analyst revisions drift
           the same way (Womack 1996). This is "someone on Wall Street has
           JUST seen it", made measurable.

Stages, each a filter (see sector-acceleration + entry-timing skills):
  0  universe   Technology + Health Care, market cap >= $2B (a 30-day round
                trip needs liquidity).
  1  clock      earnings between WIN_PRE (enter before, exit after the print
                with days to spare) or reported within POST_DAYS (drift).
  2  value      entry-timing R4 on adjusted figures: NTM EPS > TTM EPS AND
                forward P/E < trailing P/E. Both are adjusted, so the
                comparison is like-for-like (screener.ttm_eps docstring:
                these are NOT GAAP).
  3  unrealised the stock's 1m return trails its sector ETF while the sector
                runs. The sector moved and this name hasn't yet.
  4  just-seen  estimate revisions up > down in the last 4 weeks, and the
                recognition.py state.
Ranked on a simple sum; every column is printed so the rank can be argued with.

  A HIGH RANK IS A REASON TO RUN entry-timing, NEVER A REASON TO BUY.

CLI:
    python catalyst_screen.py                  # today, 30-day window
    python catalyst_screen.py --asof 2026-10-12
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import re
import statistics as st

import requests

from price_history import daily_bars
from recognition import analyse
from screener import _f, ttm_eps, universe

_UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")}
BASE = "https://api.nasdaq.com/api/analyst/{s}/{what}"

SOFTWARE = {"Computer Software: Prepackaged Software",
            "Computer Software: Programming Data Processing", "EDP Services"}


def bench_for(sector: str, industry: str) -> str:
    if industry in SOFTWARE:
        return "IGV"
    if industry == "Semiconductors":
        return "SMH"
    if sector == "Technology":
        return "XLK"
    if industry.startswith("Biotechnology: Pharm") or "Biological" in industry:
        return "XBI"
    return "XLV"


def _get(s, what):
    r = requests.get(BASE.format(s=s, what=what), headers=_UA, timeout=30)
    r.raise_for_status()
    return r.json().get("data") or {}


def earnings_date(s) -> tuple[dt.date | None, bool]:
    """(date, confirmed). Nasdaq's date is a Zacks estimate unless the company
    has announced it; the text says 'estimated' when it is a guess."""
    d = _get(s, "earnings-date")
    m = re.search(r"(\w{3} \d{1,2}, \d{4})", d.get("announcement") or "")
    if not m:
        return None, False
    when = dt.datetime.strptime(m.group(1), "%b %d, %Y").date()
    return when, "estimated" not in (d.get("reportText") or "").lower()


def last_report(s) -> tuple[dt.date | None, float | None]:
    r = requests.get(f"https://api.nasdaq.com/api/company/{s}/earnings-surprise",
                     headers=_UA, timeout=30).json().get("data") or {}
    rows = (r.get("earningsSurpriseTable") or {}).get("rows") or []
    if not rows:
        return None, None
    d = dt.datetime.strptime(rows[0]["dateReported"], "%m/%d/%Y").date()
    return d, _f(rows[0].get("percentageSurprise"))


def beat_rate(s) -> float | None:
    r = requests.get(f"https://api.nasdaq.com/api/company/{s}/earnings-surprise",
                     headers=_UA, timeout=30).json().get("data") or {}
    rows = (r.get("earningsSurpriseTable") or {}).get("rows") or []
    v = [_f(x.get("percentageSurprise")) for x in rows[:4]]
    v = [x for x in v if x is not None]
    return sum(x > 0 for x in v) / len(v) if v else None


def forecast(s):
    """NTM EPS = next four quarterly consensus rows; revisions over 4 weeks."""
    d = _get(s, "earnings-forecast")
    q = ((d.get("quarterlyForecast") or {}).get("rows")) or []
    y = ((d.get("yearlyForecast") or {}).get("rows")) or []
    eps = [_f(x.get("consensusEPSForecast")) for x in q[:4]]
    ntm = sum(eps) if len(eps) == 4 and None not in eps else None
    up = sum(int(x.get("up") or 0) for x in q[:2] + y[:2])
    down = sum(int(x.get("down") or 0) for x in q[:2] + y[:2])
    return ntm, up, down


def ret(bars, n):
    return bars[-1][1] / bars[-1 - n][1] - 1 if len(bars) > n else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--post-days", type=int, default=7)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    asof = dt.date.fromisoformat(a.asof) if a.asof else dt.date.today()
    exit_by = asof + dt.timedelta(days=a.days)
    # a print must land early enough to leave ~4 trading days to exit after it
    pre_lo, pre_hi = asof + dt.timedelta(days=2), exit_by - dt.timedelta(days=6)

    rows = [r for r in universe()
            if r["sector"] in ("Technology", "Health Care")
            and (_f(r.get("marketCap")) or 0) >= 2e9]
    print(f"asof {asof}, hard exit {exit_by}; PRE window {pre_lo}..{pre_hi}; "
          f"POST = reported in last {a.post_days}d; universe {len(rows)}")

    # stage 1: the clock (one call per name)
    def clock(r):
        s = r["symbol"].strip()
        try:
            when, conf = earnings_date(s)
            if when and pre_lo <= when <= pre_hi:
                return {**r, "symbol": s, "mode": "PRE", "event": when, "confirmed": conf}
            last, surprise = last_report(s)
            if last and 0 <= (asof - last).days <= a.post_days and (surprise or 0) > 0:
                return {**r, "symbol": s, "mode": "POST", "event": last,
                        "confirmed": True, "surprise": surprise}
        except Exception:
            return None
        return None

    with cf.ThreadPoolExecutor(a.workers) as ex:
        live = [x for x in ex.map(clock, rows) if x]
    print(f"stage 1 clock: {len(live)} names have an event inside the window")

    benches = {b: daily_bars(b, years=1) for b in ("IGV", "SMH", "XLK", "XBI", "XLV")}

    def deep(r):
        s = r["symbol"]
        try:
            bars = daily_bars(s, years=1)
            px = bars[-1][1]
            ttm, _ = ttm_eps(s)
            ntm, up, down = forecast(s)
            if not (ttm and ntm and ttm > 0 and ntm > 0):
                return None
            b = bench_for(r["sector"], r["industry"])
            rec = analyse(s)
            out = {
                "sym": s, "mode": r["mode"], "event": r["event"],
                "conf": r["confirmed"], "bench": b, "px": px,
                "pe_t": px / ttm, "pe_f": px / ntm, "growth": ntm / ttm - 1,
                "r1m": ret(bars, 21), "rel1m": ret(bars, 21) - ret(benches[b], 21),
                "offHi": px / max(c for _, c in bars[-252:]) - 1,
                "rev_up": up, "rev_dn": down, "beats": beat_rate(s),
                "state": rec.get("state"), "upside": rec.get("upside_pct"),
                "bhs": f"{rec.get('buy')}/{rec.get('hold')}/{rec.get('sell')}",
                "surprise": r.get("surprise"),
                "mcap": (_f(r.get("marketCap")) or 0) / 1e9,
            }
            return out
        except Exception:
            return None

    with cf.ThreadPoolExecutor(a.workers) as ex:
        got = [x for x in ex.map(deep, live) if x]

    # stage 2: value (R4) as a hard filter
    val = [x for x in got if x["pe_f"] < x["pe_t"] and x["growth"] > 0]
    print(f"stage 2 value (R4: NTM EPS > TTM, fwd P/E < trailing): {len(val)} of {len(got)}")

    for x in val:
        sc = 0
        sc += 2 if x["rel1m"] < -0.03 else (1 if x["rel1m"] < 0 else 0)   # not yet realised
        sc += 2 if x["rev_up"] > x["rev_dn"] else (-1 if x["rev_dn"] > x["rev_up"] else 0)
        sc += 1 if (x["beats"] or 0) >= 0.75 else 0
        sc += 1 if (x["upside"] or 0) >= 20 else 0
        sc += 1 if x["state"] in ("EARLY", "EARLY-ISH") else (-1 if x["state"] == "CONSENSUS" else 0)
        sc += 1 if x["pe_f"] < 20 else 0
        x["score"] = sc
    val.sort(key=lambda x: (-x["score"], x["pe_f"]))

    hdr = (f"{'sym':6}{'mode':5}{'event':>11}{'c':>2}{'bm':>4}{'px':>8}{'PEt':>6}{'PEf':>6}"
           f"{'grw%':>6}{'rel1m':>7}{'offHi':>7}{'rev+/-':>7}{'beat':>5}"
           f"{'B/H/S':>9}{'ups%':>6} {'state':11}{'sc':>3}")
    print(hdr)
    for x in val:
        print(f"{x['sym']:6}{x['mode']:5}{x['event'].strftime('%m-%d'):>11}"
              f"{'Y' if x['conf'] else '~':>2}{x['bench']:>4}{x['px']:8.2f}"
              f"{x['pe_t']:6.1f}{x['pe_f']:6.1f}{x['growth']*100:6.0f}"
              f"{x['rel1m']*100:7.1f}{x['offHi']*100:7.1f}"
              f"{str(x['rev_up'])+'/'+str(x['rev_dn']):>7}"
              f"{(x['beats'] or 0)*100:5.0f}{x['bhs']:>9}"
              f"{(x['upside'] or 0):6.0f} {str(x['state']):11}{x['score']:3}")


if __name__ == "__main__":
    main()
