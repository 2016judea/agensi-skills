#!/usr/bin/env python3
"""Stage 1 of a rotation screen: mechanical, free, wide.

Produces CANDIDATES so they stop being produced by hand -- the biggest gap
found running a rotation by hand.

Scope is deliberately narrow. Stage 1 only: last price, 52-week position,
YTD/1m/1y return, trailing P/E, beta. Ranked on washed-out.
Stage 2 (forward P/E, PEG, ANALYST RATING DISTRIBUTION) has no verified free
source and is a per-name WebSearch on the short list. Stage 3 (overhang,
dated catalyst) is `entry-timing` pass 2, by hand. Neither belongs here.

  A HIGH SCORE IS A REASON TO INVESTIGATE, NEVER A REASON TO BUY.
  The rating distribution is the filter that actually
  kills things (CCJ 20/4/0, PODD 21/3/0, BSX 27-of-31) and it is NOT in here.

SOURCES -- all free, no key, measured 2026-08-30:
  universe  api.nasdaq.com/api/screener/stocks   7,132 rows in ONE request
  bars      api.nasdaq.com  (via price_history.daily_bars)
  eps       api.nasdaq.com/api/quote/<S>/eps     4 actual quarters -> TTM EPS
  Yahoo's chart endpoint is NOT used: it returned HTTP 429 on 2026-08-30, so
  `entry-timing`'s warning is live and the research plan's "it worked all of
  S1" note was wrong -- S1 read prices through price_history.py, i.e. Nasdaq.

CLI:
    python screener.py                 # full band, cached, ranked top 40
    python screener.py --top 25
    python screener.py --limit 300     # cap the universe (largest first)
    python screener.py --refresh       # ignore today's cache
    python screener.py --csv out.csv
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import json
import math
import os
import re
import statistics as st
import sys
import threading
import time

import requests

from price_history import daily_bars, _UA

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "cache", "screener")
UNIVERSE_URL = (
    "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
)
EPS_URL = "https://api.nasdaq.com/api/quote/{sym}/eps?assetclass=stocks"

# --- Your kill ledger: names already researched and rejected, with the reason. --
# A screen that keeps re-surfacing them burns the same session twice; it prints
# them struck through. Fill these in from your own journal.
KILLED: dict[str, str] = {
    # "TICKER": "date  reason it was rejected",
}
HELD: set[str] = set()   # tickers you already hold, flagged in the output

# Nasdaq's feed hands a preferred/note/depositary line the PARENT's market cap,
# so AGNC's 6.875% Series D shows up as a $9B "company". Filter on the name.
NOT_COMMON = re.compile(
    r"preferred|depositary|deposit(a|o)ry|notes? due|% notes|warrant|\brights?\b|"
    r"\bunits?\b|subordinated|debenture|% Series|fixed-to-floating|fixed-rate reset",
    re.I,
)

_print_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# fetch
# --------------------------------------------------------------------------- #
def _cache_path(name: str) -> str:
    os.makedirs(CACHE, exist_ok=True)
    return os.path.join(CACHE, f"{dt.date.today().isoformat()}_{name}.json")


def _cached(name: str, fn, refresh: bool = False):
    """Cache by NAME AND DATE. A stale price is a wrong answer, not a slow one."""
    p = _cache_path(name)
    if not refresh and os.path.exists(p):
        try:
            return json.load(open(p))
        except json.JSONDecodeError:
            pass
    val = fn()
    json.dump(val, open(p, "w"))
    return val


def universe(refresh: bool = False) -> list[dict]:
    def pull():
        r = requests.get(UNIVERSE_URL, headers=_UA, timeout=90)
        r.raise_for_status()
        return r.json()["data"]["rows"]

    return _cached("universe", pull, refresh)


def _f(x) -> float | None:
    try:
        return float(str(x).replace("$", "").replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def ttm_eps(symbol: str) -> tuple[float | None, float | None]:
    """Sum of the four most recent ACTUAL quarters, and the LUMPINESS of that sum.

    `earnings` is the reported number and `consensus` the estimate -- summing
    consensus would print a forward P/E under a trailing label, which is the
    exact class of hand-typed-number error this repo exists to stop.

    ** 2026-09-01, S3 -- READ THIS BEFORE TRUSTING ANY P/E IN THIS FILE. **

    The docstring above is HALF WRONG and is kept because the correction is the
    point. `earnings` is the **ADJUSTED / consensus-comparable** figure, not GAAP:
    it is served beside a `consensus` for the same quarter, which only a
    consensus-comparable number can be. Measured on FIS -- Nasdaq reports
    Mar-2026 `earnings` **1.36**, and FIS's own Q1-2026 release puts GAAP diluted
    EPS at **$4.58** against an adjusted **$1.36**. Exact match on the adjusted leg.

    **So every P/E this screener prints is an ADJUSTED P/E wearing a trailing
    label -- the exact error class this function claims to prevent.** The size of
    it on the name it ranked #1 of 1,491: FIS 6.8x adjusted, against FY2025
    as-reported net income of $382M on 525M diluted shares = **$0.73/sh = 56x**.
    An 8.3x gap. Cross-check the shortlist with `--gaap` (SEC XBRL, as-reported);
    never promote a name to Phase 2 on the adjusted multiple alone.

    `eps_lump` (largest quarter / total absolute quarterly EPS) is returned and
    reported, but it is a **SEASONALITY** measure and NOT a one-time-gain
    detector -- it does not fire on FIS (0.279, four even quarters) and it DOES
    fire on CTVA (0.541), an ag business with a real seasonal cycle. It is
    deliberately NOT scored, because scoring it would mark down exactly the kind
    of seasonal name a value book buys.
    """
    r = requests.get(EPS_URL.format(sym=symbol.upper()), headers=_UA, timeout=30)
    r.raise_for_status()
    rows = (r.json().get("data") or {}).get("earningsPerShare") or []
    actual = [q for q in rows if q.get("type") == "PreviousQuarter" and q.get("earnings")]
    if len(actual) < 4:
        return None, None
    qs = [float(q["earnings"]) for q in actual[-4:]]
    ttm = round(sum(qs), 4)
    # denominated on total ABSOLUTE movement, not the net -- the S2 lesson from
    # Fitness Centres scoring 18.0 on a near-zero denominator.
    denom = sum(abs(q) for q in qs)
    lump = round(max(abs(q) for q in qs) / denom, 3) if denom else None
    return ttm, lump


# --------------------------------------------------------------------------- #
# measures
# --------------------------------------------------------------------------- #
def _monthly_closes(bars) -> dict:
    m = {}
    for d, px in bars:
        m[(d.year, d.month)] = px
    return m


def beta_vs(bars, bench_by_week: dict, years: float = 2.0) -> float | None:
    """Beta on WEEKLY returns over `years`, computed here rather than read off
    a vendor field -- the window is then known instead of assumed."""
    cutoff = bars[-1][0] - dt.timedelta(days=int(365.25 * years))
    wk = {}
    for d, px in bars:
        if d >= cutoff:
            wk[d.isocalendar()[:2]] = px
    keys = sorted(set(wk) & set(bench_by_week))
    if len(keys) < 60:
        return None
    a = [wk[k2] / wk[k1] - 1 for k1, k2 in zip(keys, keys[1:])]
    b = [bench_by_week[k2] / bench_by_week[k1] - 1 for k1, k2 in zip(keys, keys[1:])]
    var = st.pvariance(b)
    if var == 0:
        return None
    mba, mbb = st.mean(a), st.mean(b)
    cov = sum((x - mba) * (y - mbb) for x, y in zip(a, b)) / len(a)
    return round(cov / var, 2)


def measure(symbol: str, bars, bench_by_week: dict, eps: float | None,
            eps_lump: float | None = None) -> dict:
    last_d, last = bars[-1]
    yr = [b for b in bars if b[0] >= last_d - dt.timedelta(days=365)]
    hi = max(p for _, p in yr)
    lo = min(p for _, p in yr)
    rng = hi - lo

    def ret(days):
        prior = [b for b in bars if b[0] <= last_d - dt.timedelta(days=days)]
        return round(100 * (last / prior[-1][1] - 1), 1) if prior else None

    # WORST SINGLE DAY IN THE LAST YEAR. A spin-off, a split or a special
    # dividend leaves an unadjusted series looking exactly like a wash-out:
    # a huge fall off the 52-week high, a low range position, a negative year.
    # HON ranked #2 on this screen off a -50.9% "day" that was the 2026-06-29
    # aerospace separation, and LRN ranked #9 off -54.4% on 2025-10-29.
    # Neither fell. Below about -20% in one session, READ THE DATE FIRST.
    gap, gap_d = 0.0, None
    for (d1, p1), (d2, p2) in zip(yr, yr[1:]):
        ch = 100 * (p2 / p1 - 1)
        if ch < gap:
            gap, gap_d = ch, d2

    ytd_bars = [b for b in bars if b[0] >= dt.date(last_d.year, 1, 1)]
    return {
        "symbol": symbol,
        "last": round(last, 2),
        "as_of": last_d.isoformat(),
        "hi52": round(hi, 2),
        "lo52": round(lo, 2),
        # 0.00 = sitting on the 52w low, 1.00 = making new highs
        "range_pos": round((last - lo) / rng, 3) if rng else None,
        "off_high": round(100 * (last / hi - 1), 1),
        "off_low": round(100 * (last / lo - 1), 1),
        "ytd": round(100 * (last / ytd_bars[0][1] - 1), 1) if ytd_bars else None,
        "m1": ret(30),
        "y1": ret(365),
        "pe": round(last / eps, 1) if eps and eps > 0 else None,
        "eps_ttm": eps,
        # SEASONALITY, not a one-time-gain flag: largest single quarter over total
        # absolute quarterly EPS. Reported, never scored -- see ttm_eps().
        "eps_lump": eps_lump,
        "beta": beta_vs(bars, bench_by_week),
        "max_gap": round(gap, 1),
        "gap_date": gap_d.isoformat() if gap_d else None,
    }


def _band(x, good, bad):
    """1.0 at `good`, 0.0 at `bad`, linear between. Handles either direction."""
    if x is None:
        return None
    if good < bad:
        return max(0.0, min(1.0, (bad - x) / (bad - good)))
    return max(0.0, min(1.0, (x - bad) / (good - bad)))


def score(m: dict) -> dict:
    """Washed-out, weighted. Components are printed, not hidden in one number.

    Weights come from what actually passed and failed, not from taste:
    A low-beta name passed at beta 0.45 and 17.5x; CCJ failed at +41% off its low WHILE UP
    on the year -- a pullback in an uptrend, not a wash-out. So the 1-year term
    has to carry real weight or the screen just finds dip-buys in strong names.
    """
    parts = {
        # 0.00 range_pos = on the low
        "wash": (0.45, None if m["range_pos"] is None else 1 - m["range_pos"]),
        # down 40% over a year scores 1.0; up on the year scores 0.0
        "y1": (0.30, _band(m["y1"], -40, 0)),
        # loss-makers and >25x score 0 -- "cheap vs growth", not cheap vs nothing.
        # NOTE this P/E is ADJUSTED, not GAAP -- see ttm_eps(). Run --gaap on the
        # shortlist before believing any multiple here.
        "cheap": (0.15, _band(m["pe"], 10, 25) if m["pe"] else 0.0),
        # beta 0.5 diversifies a book; 1.4 amplifies it
        "beta": (0.10, _band(m["beta"], 0.5, 1.4)),
    }
    total, wsum = 0.0, 0.0
    out = {}
    for k, (w, v) in parts.items():
        out[f"s_{k}"] = None if v is None else round(v, 3)
        if v is not None:
            total += w * v
            wsum += w
    out["score"] = round(total / wsum, 3) if wsum else 0.0
    return out


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
def build(rows: list[dict], refresh: bool, workers: int) -> list[dict]:
    spy = daily_bars("SPY", 3)
    bench = {}
    for d, px in spy:
        bench[d.isocalendar()[:2]] = px

    done = [0]
    total = len(rows)

    def one(row):
        sym = row["symbol"]
        try:
            cp = os.path.join(CACHE, f"{dt.date.today().isoformat()}_t2_{sym}.json")
            if not refresh and os.path.exists(cp):
                m = json.load(open(cp))
            else:
                bars = daily_bars(sym, 3)
                if len(bars) < 260:
                    return None  # under a year of history: nothing to be washed out from
                try:
                    eps, eps_lump = ttm_eps(sym)
                except Exception:
                    eps, eps_lump = None, None
                m = measure(sym, bars, bench, eps, eps_lump)
                json.dump(m, open(cp, "w"))
            m.update(score(m))
            m["name"] = row["name"]
            m["sector"] = row.get("sector") or ""
            m["mktcap_b"] = round((_f(row["marketCap"]) or 0) / 1e9, 1)
            return m
        except Exception:
            return None
        finally:
            done[0] += 1
            if done[0] % 25 == 0:
                with _print_lock:
                    print(f"  ...{done[0]}/{total}", file=sys.stderr)

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        out = [r for r in ex.map(one, rows) if r]
    return out


# --------------------------------------------------------------------------- #
# GAAP cross-check -- the guard for the adjusted-P/E defect found in S3
# --------------------------------------------------------------------------- #
def gaap_check(symbols: list[str], last_px: dict) -> None:
    """Print the ADJUSTED multiple beside the AS-REPORTED one, per name.

    Built 2026-09-01 (S3) after FIS ranked #1 of 1,491 on a 6.8x that is an
    ADJUSTED multiple -- its FY2025 as-reported net income was $382M on 525M
    diluted shares ($0.73/sh, 56x). `max_gap` guards a single PRICE event faking
    a wash-out; this guards an ACCOUNTING gap faking cheapness. Deliberately run
    on the SHORTLIST only: one SEC call per name is far too slow for 1,500, and
    the multiple only has to be true for names about to cost a Phase 2 session.

    Source is sec_financials.build -> SEC XBRL companyconcept, as reported.
    No number here is typed, and none is solved out of an identity.
    """
    try:
        import sec_financials as sf
    except Exception as e:
        print(f"  (gaap check unavailable: {e})", file=sys.stderr)
        return
    # market caps, for the share-count sanity gate below
    cap_b = {}
    try:
        for r in universe(False):
            c = _f(r.get("marketCap"))
            if c:
                cap_b[r["symbol"]] = c / 1e9
    except Exception:
        pass
    print()
    print("GAAP CROSS-CHECK -- Nasdaq ADJUSTED vs SEC AS-REPORTED. A wide gap is a reason to stop.")
    print(f"  {'sym':5} {'price':>8} {'adjP/E':>7} {'gaapEPS':>8} {'gaapP/E':>8} {'FY':>5}  note")
    for sym in symbols:
        sym = sym.strip().upper()
        if not sym:
            continue
        px = last_px.get(sym)
        try:
            eps_adj, _ = ttm_eps(sym)
        except Exception:
            eps_adj = None
        if px is None:
            try:
                px = daily_bars(sym, 1)[-1][1]
            except Exception:
                px = None
        try:
            d = sf.build(sym, 2)["data"]
        except Exception as e:
            print(f"  {sym:5} {'-':>8} {'-':>7} {'-':>8} {'-':>8} {'-':>5}  SEC lookup failed: {e}")
            continue
        ni, sh = d.get("net_income") or {}, d.get("shares_diluted") or {}
        fys = sorted(set(ni) & set(sh))
        if not fys or px is None:
            print(f"  {sym:5} {'-':>8} {'-':>7} {'-':>8} {'-':>8} {'-':>5}  NO DATA -- check by hand")
            continue
        fy = fys[-1]
        eps_g = ni[fy] / sh[fy] if sh[fy] else None

        # SANITY GATE. `WeightedAverageNumberOfDilutedSharesOutstanding` is not
        # reliably the whole share count: Shift4 (FOUR) tags **1,333,686** where
        # the company has ~90M shares, and the resulting "$89.23 GAAP EPS, 0.5x"
        # reads as the cheapest thing ever screened. Cross the implied market cap
        # against Nasdaq's -- if they disagree by more than 2x, the SHARE COUNT is
        # wrong and every number derived from it is void. Print the failure as a
        # failure; a guard that emits a plausible wrong number is worse than none.
        cap_x = None
        if cap_b.get(sym) and sh[fy]:
            implied = sh[fy] * px / 1e9
            cap_x = implied / cap_b[sym] if cap_b[sym] else None
        if cap_x is not None and not (0.5 <= cap_x <= 2.0):
            print(f"  {sym:5} {px:8.2f} "
                  f"{(f'{px/eps_adj:.1f}' if eps_adj and eps_adj > 0 else '-'):>7} "
                  f"{'VOID':>8} {'VOID':>8} {fy:>5}  "
                  f"XBRL share count is wrong ({sh[fy]:,} -> ${sh[fy]*px/1e9:.2f}B "
                  f"vs ${cap_b[sym]:.1f}B actual). Cannot compute GAAP EPS.")
            continue
        pe_adj = px / eps_adj if eps_adj and eps_adj > 0 else None
        pe_g = px / eps_g if eps_g and eps_g > 0 else None
        note = ""
        if eps_g is not None and eps_g <= 0:
            note = "LOSS-MAKING on GAAP"
        elif pe_adj and pe_g:
            r = pe_g / pe_adj
            if r >= 2.0:
                note = f"** {r:.1f}x GAP -- the adjusted multiple is not the business **"
            elif r >= 1.4:
                note = f"{r:.1f}x gap"
        print(f"  {sym:5} {px:8.2f} "
              f"{(f'{pe_adj:.1f}' if pe_adj else '-'):>7} "
              f"{(f'{eps_g:.2f}' if eps_g is not None else '-'):>8} "
              f"{(f'{pe_g:.1f}' if pe_g else 'n/a'):>8} {fy:>5}  {note}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0, help="cap universe, largest cap first")
    ap.add_argument("--min-cap", type=float, default=2.0, help="$B")
    ap.add_argument("--max-cap", type=float, default=200.0, help="$B; above this it is recognized by definition")
    ap.add_argument("--min-price", type=float, default=5.0)
    ap.add_argument("--sector", default="", help="substring filter")
    ap.add_argument("--max-gap", type=float, default=0.0,
                    help="drop names whose worst single day is below this %% (e.g. -20)")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--csv", default="")
    ap.add_argument("--check", default="", help="comma-separated tickers: are these still listed?")
    ap.add_argument("--gaap", default="", help="comma-separated tickers: adjusted P/E vs SEC as-reported. "
                    "Run this on the shortlist -- the printed P/E is ADJUSTED (see ttm_eps).")
    a = ap.parse_args()

    if a.gaap:
        gaap_check([x for x in a.gaap.split(",") if x.strip()], {})
        return

    rows = universe(a.refresh)

    if a.check:
        # Hand-mapping an industry to tickers from memory quietly serves up
        # DEAD ONES. Mapping the 2026-08-30 NAICS panel produced seven --
        # IPG, ODP, GCI, EHAB, NVEE, MEG, TALK -- all acquired or delisted,
        # and `daily_bars` reports them as "endpoint may be blocked", which
        # reads like a network problem rather than a company that no longer
        # trades. Check the map against the listed universe first.
        have = {r["symbol"]: r for r in rows}
        for sym in [x.strip().upper() for x in a.check.split(",") if x.strip()]:
            r = have.get(sym)
            if r:
                cap = (_f(r["marketCap"]) or 0) / 1e9
                print(f"  {sym:<6} LISTED   {r['name'][:44]:<46} ${cap:,.1f}B  {r.get('sector')}")
            else:
                print(f"  {sym:<6} NOT LISTED -- acquired, delisted, or a bad symbol")
        return

    keep = []
    for r in rows:
        if r.get("country") != "United States":
            continue
        if NOT_COMMON.search(r.get("name") or ""):
            continue
        cap = (_f(r.get("marketCap")) or 0) / 1e9
        px = _f(r.get("lastsale")) or 0
        if not (a.min_cap <= cap < a.max_cap) or px < a.min_price:
            continue
        if a.sector and a.sector.lower() not in (r.get("sector") or "").lower():
            continue
        keep.append(r)
    keep.sort(key=lambda r: -(_f(r["marketCap"]) or 0))
    if a.limit:
        keep = keep[: a.limit]

    print(f"universe {len(rows)} -> {len(keep)} names "
          f"(US common, ${a.min_cap:g}-{a.max_cap:g}B, >=${a.min_price:g})", file=sys.stderr)
    t0 = time.time()
    res = build(keep, a.refresh, a.workers)
    print(f"measured {len(res)}/{len(keep)} in {time.time()-t0:.0f}s", file=sys.stderr)

    res.sort(key=lambda m: -m["score"])
    fresh = [m for m in res if m["symbol"] not in KILLED and m["symbol"] not in HELD]
    if a.max_gap:
        n0 = len(fresh)
        fresh = [m for m in fresh if (m.get("max_gap") or 0) >= a.max_gap]
        print(f"--max-gap {a.max_gap:g}%: dropped {n0-len(fresh)} names with a single-day break",
              file=sys.stderr)

    hdr = f"{'#':>3} {'sym':<6} {'score':>6} {'last':>8} {'52w pos':>8} {'off hi':>7} " \
          f"{'ytd':>7} {'1y':>7} {'P/E':>6} {'beta':>5} {'cap$B':>7} {'worst day':>16}  sector"
    print(f"\nSTAGE 1 -- washed-out rank  ({res[0]['as_of'] if res else 'n/a'})")
    print("A rank is a reason to investigate. Stage 2 (rating distribution) is what kills.")
    print("! = one session did >=20% of the damage. Read that date before reading the rank:")
    print("    a spin-off or a special dividend fakes every wash-out measure in this table.")
    print("-" * len(hdr))
    print(hdr)
    print("-" * len(hdr))
    for i, m in enumerate(fresh[: a.top], 1):
        print(f"{i:>3} {m['symbol']:<6} {m['score']:>6.3f} {m['last']:>8.2f} "
              f"{(m['range_pos'] if m['range_pos'] is not None else float('nan')):>8.2f} "
              f"{m['off_high']:>6.0f}% {(m['ytd'] if m['ytd'] is not None else float('nan')):>6.0f}% "
              f"{(m['y1'] if m['y1'] is not None else float('nan')):>6.0f}% "
              f"{(m['pe'] or float('nan')):>6.1f} {(m['beta'] if m['beta'] is not None else float('nan')):>5.2f} "
              f"{m['mktcap_b']:>7.1f} "
              f"{('! ' if (m.get('max_gap') or 0) <= -20 else '  ')}"
              f"{(m.get('max_gap') or 0):>5.0f}% {m.get('gap_date') or '':<10}"
              f"  {m['sector'][:22]}")

    seen = {m["symbol"]: m for m in res}
    hits = [s for s in KILLED if s in seen]
    if hits:
        print("\nalready killed -- do not re-research:")
        for s in sorted(hits, key=lambda s: -seen[s]["score"]):
            print(f"    {s:<5} score {seen[s]['score']:.3f}  -- {KILLED[s]}")

    if a.csv:
        cols = ["symbol", "name", "sector", "mktcap_b", "last", "as_of", "score",
                "s_wash", "s_y1", "s_cheap", "s_beta", "range_pos", "off_high",
                "off_low", "hi52", "lo52", "ytd", "m1", "y1", "pe", "eps_ttm", "eps_lump", "beta",
                "max_gap", "gap_date"]
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(res)
        print(f"\nwrote {len(res)} rows -> {a.csv}")


if __name__ == "__main__":
    main()
