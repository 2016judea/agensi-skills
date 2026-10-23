#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recognition.py -- measure the recognition arbitrage, including its DIRECTION.

Closes an instrument gap: "the recognition test is manual -- '0 sell ratings =
consensus long' is the sharpest filter (it killed CCJ and PODD) and it was googled
per name."

WHAT IS NEW HERE, and it is the point of the tool:
The 0-sells test is a SNAPSHOT. It tells you whether a crowd exists to be wrong.
It does NOT tell you whether the crowd has ALREADY changed its mind -- which is
the difference between being early and being late, and it is the whole edge.

Nasdaq's /api/analyst/<T>/targetprice returns `historicalConsensus`, a ~13-month
monthly series of {buy, hold, sell, consensus, y}. Measured 2026-09-15: **`y` is
the consensus PRICE TARGET, not the stock price.** Proof -- NVDA's last y is
324.3, exactly equal to the stated priceTarget field, against a $212.17 tape.
Read as price it inverts every verdict this tool makes, so `verify_y_semantics()`
re-proves it at runtime and the tool REFUSES to score if the proof fails.

THE THREE STATES, and only the first is tradeable on a recognition-arbitrage edge:

  EARLY        bears exist AND the consensus target is still flat/falling.
               The crowd has not turned. There is a mind left to change.
  MID-FLIGHT   the target has already re-rated up hard off its trough.
               The revision you would be buying has largely happened.
  CONSENSUS    0 sells. No bear to convert. Killed CCJ, PODD, MMS, ACM, ADMA, FOUR.

Worked example that produced the tool -- BAH, 2026-09-15:
  3B/5H/3S is the best bears-exist reading the screen has ever returned, and on
  the snapshot test alone BAH passes where earlier picks passed. But the series
  shows the consensus target bottomed at $60.01 in July and reached $85.40 by
  September -- **+42% in two months, buys 1 -> 3** -- while the stock ran from a
  $59.50 low to $80.06. Consensus upside left: **+6.7%**. CCJ was rejected on
  +33%. MID-FLIGHT, not early. The snapshot said buy; the derivative said the
  trade already happened.

⚠ THE LIMITATION, FOUND THE FIRST TIME THE TOOL WAS RUN WIDE (2026-09-15):
This measures the DERIVATIVE OF OPINION. It cannot tell you whether the opinion is
CORRECT. The scan of 86 names returned exactly one name where the crowd had
demonstrably not turned -- WHR, 0 Buy / 7 Hold / 2 Sell, consensus target still
falling (-6.3% over 3mo) and only +6.0% off its own trough. On the snapshot test it
is the perfect inverse of every name the screen has killed: every kill died on ZERO
SELLS, and Whirlpool has ZERO BUYS.

It is a KILL, and it fails on facts this tool does not see:
  * $33.03 against a 52-week range of $32.86-$94.82 -- 0.3% OF RANGE. A falling
    knife, not a wash-out.
  * forward P/E 17.6 vs TRAILING 11.6 -- the multiple RISES going forward because
    forward EPS is guided $2.93 -> $1.88, -36%. "Cheap" was a trailing artifact.
  * 10.59% dividend yield -- the market pricing a cut, not paying you to wait.
  * beta 1.64 -- amplifies a concentrated book. CCJ was rejected at 2.33.
  * consensus target $93.15 (Sep-2025) -> $37.50 (Aug-2026), -60% in twelve months.

**The crowd had not turned because the crowd was RIGHT.** That is the ZBH
failure mode -- a value screen with no wrong belief to arbitrage -- and this tool
will surface it every time, because a correct bear and an early bear look identical
in the rating distribution. **ALWAYS pair a low off_trough_pct with forward-vs-
trailing EPS and beta before promoting anything.** Shape is a reason to investigate,
never a reason to buy (rule 4b).

THE FOUR TESTS.
The old single rule -- "0 sells = consensus long" -- had accreted four jobs. It is now
four ordered tests and a name must clear ALL of them:

  R1  IS THERE A CROWD?      >= 4 covering SELL-SIDE brokers with live targets.
                             Quant/model services (Zacks, Weiss, CO FORECST, CFRA) are
                             excluded from every count, both directions. Fewer than 4
                             -> UNCOVERED. Killed MMS (2 brokers, opinions 20 and 37
                             months old).                        [automated: classify()]

  R2  IS IT FALSIFIABLE?     >= 1 sell-side SELL. Zero -> CONSENSUS. Killed CCJ, PODD,
                             ACM, ADMA, FOUR, and all six federal-services comps.
                                                                 [automated: classify()]

  R3  HAS IT ALREADY TURNED? consensus target <= ~10% off its own trough, OR >= 20%
                             upside left. Killed BAH: +42% off trough, +6.7% left.
                                                                 [automated: classify()]

  R4  IS THE CROWD WRONG?    ** forward EPS must EXCEED trailing, and forward P/E must
                             be BELOW trailing P/E. ** If the multiple RISES going
                             forward, "cheap" was a trailing artifact.
                                                              [NOT AUTOMATED -- BY HAND]

** R4 IS THE LOAD-BEARING TEST AND IT IS DELIBERATELY NOT AUTOMATED. **
R1-R3 all describe the SHAPE OF OPINION. Only R4 asks whether the opinion is RIGHT, and
without it this tool walks into a falling knife -- which it did, within an hour of being
built (see the WHR case below). It is left manual because it needs forward-vs-trailing
EPS from a SECOND feed, and an automated R4 off one feed would be the `previousClose`
failure again, on the number that matters most. Get forward EPS from a second source
(e.g. your broker's quote API -- E*TRADE `/v1/market/quote/<SYM>?detailFlag=ALL` -> estEarnings), and CHECK IT AGAINST CURRENT
COMPANY GUIDANCE -- a consensus figure that predates a guidance cut inverts the test.

  WHR 2026-09-15  fwd P/E 17.6 vs trailing 11.6, EPS guided -36%   -> R4 FAIL, killed
  DKS 2026-09-15  fwd P/E 10.8 vs trailing 14.0, EPS $9.21->$11.42
                  on POST-CUT guidance                             -> R4 PASS, survived

See also: the rule that shape is a reason to investigate, never to buy, and the
category error -- a rating count is only comparable to another rating count
if both are SELL-SIDE BROKERS. Nasdaq's `brokerNames` mixes in quant services
(ZACKS RESEARCH, CO FORECST); `--brokers` prints them so a count can be audited.
"""
import argparse, json, sys, time
import urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
BASE = "https://api.nasdaq.com/api"
# Not sell-side brokers publishing a target: do not average these with brokers.
QUANT = {"ZACKS RESEARCH", "CO FORECST", "WEISS RATINGS", "FORECST", "THE STREET",
         "MARKETBEAT", "CFRA", "argus".upper()}


def _get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == tries - 1:
                return {"__error__": str(e)}
            time.sleep(1.2 * (i + 1))
    return {"__error__": "unreachable"}


def quote(t):
    d = _get(f"{BASE}/quote/{t}/info?assetclass=stocks")
    try:
        p = d["data"]["primaryData"]["lastSalePrice"]
        return float(p.replace("$", "").replace(",", ""))
    except Exception:
        return None


def targets(t):
    d = _get(f"{BASE}/analyst/{t}/targetprice")
    if not d or d.get("__error__") or not d.get("data"):
        return None
    return d["data"]


def brokers(t):
    d = _get(f"{BASE}/analyst/{t}/ratings")
    try:
        return d["data"]["brokerNames"], d["data"].get("meanRatingType")
    except Exception:
        return [], None


def verify_y_semantics(sample=("NVDA", "AAPL")):
    """Re-prove that historicalConsensus.y is the consensus TARGET, not the price.

    The whole tool inverts if this is wrong, so it is proven at runtime rather
    than trusted. Test: the LAST y must equal consensusOverview.priceTarget, and
    must differ materially from the live quote for at least one sample name.
    """
    matched = differs = 0
    for t in sample:
        d = targets(t)
        if not d:
            continue
        h = d.get("historicalConsensus") or []
        if not h:
            continue
        last_y = float(h[-1]["y"])
        pt = float(d["consensusOverview"]["priceTarget"])
        px = quote(t)
        if abs(last_y - pt) < 0.01:
            matched += 1
        if px and abs(last_y - px) / px > 0.05:
            differs += 1
    return matched >= 1 and differs >= 1


def analyse(t):
    d = targets(t)
    if not d:
        return {"ticker": t, "error": "no analyst data"}
    co = d.get("consensusOverview") or {}
    h = d.get("historicalConsensus") or []
    px = quote(t)
    b, ho, s = co.get("buy"), co.get("hold"), co.get("sell")
    tgt = co.get("priceTarget")
    n = sum(x for x in (b, ho, s) if isinstance(x, int))

    series = []
    for p in h:
        z = p["z"]
        series.append({"date": z["date"], "buy": z["buy"], "hold": z["hold"],
                       "sell": z["sell"], "target": float(p["y"])})

    r = {"ticker": t, "price": px, "buy": b, "hold": ho, "sell": s, "n": n,
         "target": tgt, "series": series}

    if px and tgt:
        r["upside_pct"] = (tgt / px - 1) * 100
    if n:
        r["sell_share_pct"] = (s / n) * 100 if isinstance(s, int) else None

    # --- the derivative: where is the consensus target vs its own trough/peak ---
    if len(series) >= 4:
        tg = [x["target"] for x in series]
        trough, peak = min(tg), max(tg)
        cur = tg[-1]
        r["target_trough"] = trough
        r["target_trough_date"] = series[tg.index(trough)]["date"]
        r["target_peak"] = peak
        r["off_trough_pct"] = (cur / trough - 1) * 100 if trough else None
        r["below_peak_pct"] = (cur / peak - 1) * 100 if peak else None
        r["target_3mo_pct"] = (cur / tg[-4] - 1) * 100 if len(tg) >= 4 and tg[-4] else None
        # bear count direction
        r["sell_6mo_ago"] = series[-7]["sell"] if len(series) >= 7 else None
        r["buy_6mo_ago"] = series[-7]["buy"] if len(series) >= 7 else None

    # --- verdict ---
    r["state"], r["why"] = classify(r)
    return r


def classify(r):
    s, n = r.get("sell"), r.get("n") or 0
    up = r.get("upside_pct")
    off = r.get("off_trough_pct")
    rev3 = r.get("target_3mo_pct")

    if n and n < 4:
        return "UNCOVERED", f"only {n} rated opinions - no crowd to re-rate (the MMS death, 9/10)"
    if s == 0:
        return "CONSENSUS", "0 sells - no bear to convert (killed CCJ, PODD, MMS, ACM, ADMA, FOUR)"
    if up is None or off is None:
        return "INCOMPLETE", "missing price or target history"
    # the crowd has already turned
    if rev3 is not None and rev3 >= 15 and up < 15:
        return "MID-FLIGHT", (f"consensus target already +{rev3:.0f}% in 3mo and only "
                              f"{up:.1f}% upside left - the revision has happened")
    if up < 10:
        return "MID-FLIGHT", f"only {up:.1f}% consensus upside - CCJ was rejected at +33%"
    if off is not None and off <= 5 and up >= 20:
        return "EARLY", (f"bears present ({s}/{n}), target still within {off:.1f}% of its "
                         f"own trough, {up:.0f}% upside - the crowd has NOT turned")
    if up >= 20:
        return "EARLY-ISH", f"{s}/{n} sells, {up:.0f}% upside, but target already +{off:.0f}% off trough"
    return "MIXED", f"{s}/{n} sells, {up:.1f}% upside, target +{off:.0f}% off trough"


def fmt(r, show_series=False, show_brokers=False):
    if r.get("error"):
        return f"{r['ticker']:6} ERROR {r['error']}"
    px = r.get("price") or 0
    up = r.get("upside_pct")
    head = f"{r['ticker']:6} ${px:8.2f}  {r.get('buy')}B/{r.get('hold')}H/{r.get('sell')}S (n={r.get('n')})  tgt ${r.get('target')}"
    line = head + (f"  upside {up:+6.1f}%" if up is not None else "")
    if r.get("off_trough_pct") is not None:
        line += (f"  tgt +{r['off_trough_pct']:.0f}% off trough "
                 f"(${r['target_trough']} {r['target_trough_date']})")
    if r.get("target_3mo_pct") is not None:
        line += f"  3mo {r['target_3mo_pct']:+.0f}%"
    out = [line, f"       -> {r['state']}: {r['why']}"]
    if show_series and r.get("series"):
        out.append("       date        buy hold sell   consensus target")
        for x in r["series"]:
            out.append(f"       {x['date']}  {x['buy']:3} {x['hold']:4} {x['sell']:4}   ${x['target']:.2f}")
    if show_brokers:
        bn, mean = brokers(r["ticker"])
        sell_side = [b for b in bn if b.strip().upper() not in QUANT]
        quants = [b for b in bn if b.strip().upper() in QUANT]
        out.append(f"       brokers ({len(bn)}): sell-side {len(sell_side)} | quant/model {len(quants)} {quants}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tickers", nargs="+", help="tickers, or @file with one per line")
    ap.add_argument("--series", action="store_true", help="print the monthly rating/target history")
    ap.add_argument("--brokers", action="store_true", help="print broker names, split sell-side vs quant")
    ap.add_argument("--early-only", action="store_true", help="print only EARLY / EARLY-ISH")
    ap.add_argument("--csv", help="write results to CSV")
    ap.add_argument("--skip-verify", action="store_true", help="skip the y-semantics proof (NOT recommended)")
    a = ap.parse_args()

    ts = []
    for t in a.tickers:
        if t.startswith("@"):
            ts += [x.strip().upper() for x in open(t[1:]) if x.strip() and not x.startswith("#")]
        else:
            ts.append(t.upper())

    if not a.skip_verify:
        if not verify_y_semantics():
            print("REFUSING TO SCORE: could not re-prove that historicalConsensus.y is the "
                  "consensus TARGET.\nIf Nasdaq changed the field's meaning, every verdict "
                  "below would invert. Re-derive before trusting this tool.", file=sys.stderr)
            sys.exit(2)

    rows = []
    for t in ts:
        r = analyse(t)
        rows.append(r)
        if a.early_only and r.get("state") not in ("EARLY", "EARLY-ISH"):
            continue
        print(fmt(r, a.series, a.brokers))
        print()

    if a.csv:
        import csv as _csv
        cols = ["ticker", "price", "buy", "hold", "sell", "n", "target", "upside_pct",
                "sell_share_pct", "target_trough", "target_trough_date", "off_trough_pct",
                "below_peak_pct", "target_3mo_pct", "state", "why"]
        with open(a.csv, "w", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"wrote {a.csv}")


if __name__ == "__main__":
    main()
