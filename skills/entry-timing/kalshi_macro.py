#!/usr/bin/env python3
"""Market-implied macro expectations from Kalshi, read-only.

Kalshi is a CFTC-regulated exchange whose economic contracts price the Fed
path, CPI, payrolls, unemployment and recession timing. Market data is public
-- no key, no account, no auth header. We read these prices; we do not trade
them. See the Fed's own working paper on why they're worth reading:
Diercks, Katz & Wright, "Kalshi and the Rise of Macro Markets", FEDS 2026-010.

Each series is a ladder of "above X" strikes on one underlying, so a single
event is a *survival curve* S(X) = P(value > X). Differencing adjacent strikes
turns that into a distribution over buckets -- the distributionally-rich read
you can't get from a single consensus number.

Used by the `portfolio-review` and `entry-timing` skills as a macro cross-check:
where does a written thesis disagree with the market's odds, and why.

CLI:
    python kalshi_macro.py               # every series, nearest event
    python kalshi_macro.py fed cpi       # just these
    python kalshi_macro.py --json        # machine-readable

Import:
    from kalshi_macro import snapshot, SERIES

--- Traps, each of which silently produces a wrong number -------------------

1. FIELD NAMES ARE SUFFIXED. Prices come back as `yes_bid_dollars` (a *string*,
   in dollars) and size/volume as `volume_fp` / `open_interest_fp` (also
   strings). There is no `volume`, `open_interest`, `yes_bid` or `last_price`
   key. Older Kalshi code and any model trained on it reads integer cents from
   those bare names -- `.get("volume", 0)` returns 0 for every market on the
   exchange and the whole macro complex looks dead. It is not: KXFED alone
   shows ~800k contracts of volume. Parse the suffixed keys, as floats.

2. A MISSING QUOTE IS NOT A PROBABILITY. Illiquid strikes sit 0 bid / 1.00 ask.
   The midpoint of that is 0.50, which is not a 50% chance of anything -- it's
   the absence of a market. `_prob` returns the quote quality alongside the
   number so a caller can't mistake one for the other.

3. THE CURVE CAN GO NON-MONOTONIC. P(>3.5%) should never exceed P(>3.25%), but
   stale quotes on adjacent strikes make it happen. Differencing then yields a
   *negative* probability. We clamp at zero and report the violation rather
   than quietly emitting a clean-looking distribution built on a broken curve.

4. THE BUCKETS DON'T SUM TO 1. They sum to ~1.0x because every strike is read
   at its midpoint and the bid/ask straddles fair value. That excess is the
   spread, not information. Reported as `overround`; deliberately NOT
   normalized away, because its size is the honest measure of how much to
   trust the read.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import requests

_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Concept -> (series ticker, what the underlying is, unit suffix for strikes).
# Tickers verified live against /markets on 2026-08-17; Kalshi keeps retired
# duplicates of most of these under the un-prefixed name (FED, U3, PAYROLLS),
# which return zero open markets. Always the KX-prefixed one.
SERIES: dict[str, tuple[str, str, str]] = {
    "fed": ("KXFED", "Fed funds rate, upper bound, after the meeting", "%"),
    "cpi": ("KXCPIYOY", "US CPI, year over year", "%"),
    "cpi_mom": ("KXCPI", "US CPI, month over month", "%"),
    "payrolls": ("KXPAYROLLS", "US nonfarm payrolls, monthly change", ""),
    "unemployment": ("KXU3", "US unemployment rate (U-3)", "%"),
    "recession": ("KXNBERRECESSQ", "Quarter the next NBER recession begins", ""),
}


def _f(market: dict, key: str) -> float:
    """Kalshi returns numbers as strings. Absent key -> nan, never a silent 0."""
    raw = market.get(key)
    if raw is None or raw == "":
        return float("nan")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float("nan")


def _prob(market: dict) -> tuple[float, str]:
    """(probability, quote quality) for a market's YES side.

    Quality is 'mid' (tight two-sided quote), 'wide' (a real but near-useless
    quote), 'last' (no live quote, a stale trade print) or 'none'.

    Trap 2 has a long tail: an *absolute* spread test passes things it should
    not. The recession ladder quotes 0.3c bid / 2.9c ask -- only 2.6c wide, but
    the ask is ten times the bid, and the 1.6c midpoint is an arithmetic
    artifact rather than anyone's view. So the test is relative as well:
    a quote is tight if it's within 2c OR within a quarter of its own mid.
    """
    bid, ask = _f(market, "yes_bid_dollars"), _f(market, "yes_ask_dollars")
    if bid == bid and ask == ask and ask - bid < 0.99:  # nan-safe: nan != nan
        mid, spread = (bid + ask) / 2, ask - bid
        return mid, "mid" if spread <= 0.02 or spread <= 0.25 * mid else "wide"
    last = _f(market, "last_price_dollars")
    if last == last and last > 0:
        return last, "last"
    return float("nan"), "none"


def fetch(series_ticker: str, status: str = "open") -> list[dict]:
    """Every open market on a series. Public endpoint -- no auth."""
    r = requests.get(
        f"{_BASE}/markets",
        params={"series_ticker": series_ticker, "status": status, "limit": 500},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("markets", [])


def nearest_event(markets: list[dict]) -> list[dict]:
    """The soonest-closing event's strikes. A series holds many months at once."""
    if not markets:
        return []
    soonest = min(markets, key=lambda m: m["close_time"])["event_ticker"]
    return [m for m in markets if m["event_ticker"] == soonest]


def distribution(markets: list[dict]) -> dict:
    """Turn a ladder of 'above X' strikes into a bucket distribution.

    S(X) = P(value > X) at ascending strikes gives:
        P(<= X_1)          = 1 - S(X_1)
        P(X_i < v <= X_i+1) = S(X_i) - S(X_i+1)
        P(> X_n)           = S(X_n)
    """
    rungs = []
    for m in markets:
        strike = _f(m, "floor_strike")
        p, quality = _prob(m)
        if strike == strike and p == p:
            rungs.append((strike, p, quality))
    rungs.sort()
    if not rungs:
        return {"buckets": [], "overround": float("nan"), "violations": 0, "rungs": 0}

    buckets, violations = [], 0
    prev_strike, prev_s = None, 1.0
    for strike, s, _q in rungs:
        raw = prev_s - s
        if raw < -1e-9:  # trap 3: stale quote inverted the curve
            violations += 1
        lo = "" if prev_strike is None else prev_strike
        buckets.append({"lo": lo, "hi": strike, "p": max(raw, 0.0)})
        prev_strike, prev_s = strike, s
    buckets.append({"lo": prev_strike, "hi": "", "p": max(prev_s, 0.0)})

    return {
        "buckets": buckets,
        "overround": sum(b["p"] for b in buckets),
        "violations": violations,
        "rungs": len(rungs),
        "stale": sum(1 for _s, _p, q in rungs if q != "mid"),
    }


def snapshot(keys: list[str] | None = None) -> dict:
    """Nearest event per series, as market-implied distributions."""
    out: dict = {"pulled": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    for key in keys or list(SERIES):
        ticker, label, unit = SERIES[key]
        markets = nearest_event(fetch(ticker))
        if not markets:
            out[key] = {"series": ticker, "label": label, "error": "no open markets"}
            continue
        entry = {
            "series": ticker,
            "label": label,
            "unit": unit,
            "event": markets[0]["event_ticker"],
            "closes": markets[0]["close_time"],
            "volume": sum(_f(m, "volume_fp") for m in markets),
            "open_interest": sum(_f(m, "open_interest_fp") for m in markets),
        }
        if markets[0].get("strike_type") == "greater":
            entry.update(distribution(markets))
        else:
            # Categorical. NOT a partition: the NBER ladder keeps *past*
            # quarters open, because NBER dates a recession start retroactively
            # and years late, so these are six independent "will it eventually
            # be called from quarter X" bets that correctly sum to well under 1.
            # `subtitle` is null on all but one -- `yes_sub_title` is the name.
            outcomes = []
            for m in markets:
                p, quality = _prob(m)
                name = m.get("yes_sub_title") or m.get("subtitle") or m["ticker"]
                outcomes.append({"name": name, "p": p, "q": quality})
            outcomes.sort(key=lambda o: (-o["p"] if o["p"] == o["p"] else 0))
            entry["outcomes"] = outcomes
            entry["partition"] = False
            entry["total"] = sum(o["p"] for o in outcomes if o["p"] == o["p"])
        out[key] = entry
    return out


def _render(key: str, e: dict, unit: str) -> None:
    if "error" in e:
        print(f"\n{e['label']}\n  {e['error']} ({e['series']})")
        return
    closes = e["closes"][:10]
    print(f"\n{e['label']}")
    print(
        f"  {e['event']} -- resolves {closes} -- "
        f"{e['volume']:,.0f} contracts traded, {e['open_interest']:,.0f} open"
    )

    partition = "buckets" in e
    rows: list[tuple[str, float, str]] = []
    if partition:
        for b in e["buckets"]:
            lo, hi = b["lo"], b["hi"]
            if lo == "":
                name = f"at or below {hi:g}{unit}"
            elif hi == "":
                name = f"above {lo:g}{unit}"
            else:
                name = f"{lo:g}-{hi:g}{unit}"
            rows.append((name, b["p"], "mid"))
    else:
        rows = [(o["name"], o["p"], o["q"]) for o in e["outcomes"]]

    # A 27-strike CPI ladder is mostly empty tails. Print what carries weight
    # and account for the rest in one line -- suppressing them silently would
    # overstate how concentrated the distribution is. Only a partition has a
    # running total, so only a partition gets a median.
    floor, hidden, hidden_p = 0.005, 0, 0.0
    cum = 0.0
    for name, p, quality in rows:
        if p != p:
            continue
        cum += p
        if p < floor and partition:
            hidden, hidden_p = hidden + 1, hidden_p + p
            continue
        bar = "#" * round(p * 40)
        mark = " <- median" if partition and cum >= 0.5 and cum - p < 0.5 else ""
        if quality != "mid":
            mark += f"  [{quality} quote -- not a usable probability]"
        print(f"    {name:<22}{p * 100:5.1f}%  {bar}{mark}")
    if hidden:
        print(f"    {f'({hidden} thinner strikes)':<22}{hidden_p * 100:5.1f}%")

    if not partition:
        print(
            f"  independent contracts, not a partition -- they sum to "
            f"{e['total']:.2f} and should not sum to 1"
        )
        return

    notes = [f"quotes sum to {e['overround']:.2f} (spread, not signal)"]
    if e.get("violations"):
        notes.append(f"{e['violations']} inverted strike(s) -- stale quotes, clamped at 0")
    if e.get("stale"):
        notes.append(f"{e['stale']} of {e['rungs']} strikes priced off a wide or absent quote")
    print("  " + "; ".join(notes))


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keys = [a for a in args if a in SERIES] or None
    bad = [a for a in args if a not in SERIES]
    if bad:
        print(f"unknown series {bad}; known: {list(SERIES)}", file=sys.stderr)
        sys.exit(2)

    snap = snapshot(keys)
    if "--json" in sys.argv:
        print(json.dumps(snap, indent=2))
        return

    print(f"Kalshi market-implied macro -- pulled {snap['pulled']}")
    print("Read-only. These are prices, not forecasts: they carry a spread and a")
    print("crowd's biases, and the exchange's own fee makes small edges unplayable.")
    for key in keys or list(SERIES):
        _render(key, snap[key], SERIES[key][2])


if __name__ == "__main__":
    main()
