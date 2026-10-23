---
name: sector-acceleration
description: Tell which stock-market sectors are accelerating or decelerating right now, using the second derivative of price, relative strength vs the S&P 500, breadth, and the market-implied rate path from Kalshi. Use when you ask "which sectors are showing the most positive acceleration", "what's leading the market", "where's the rotation", "which sectors have momentum", "what's hot / rolling over", or want a sector or industry read before picking names. Free data, no API keys.
---

# Sector acceleration

The goal is a ranked call on **which sectors are speeding up**, with the reason and a
dated falsifier. Decision first, then the table.

## Run it

```bash
pip install requests
python sector_momentum.py            # 23 ETFs: 11 SPDRs + SPY/RSP/IWM + 9 industries
python kalshi_macro.py fed cpi       # the rate path the call is contingent on
```

`sector_momentum.py` documents every column. Prices come from `price_history.py`,
which reads Nasdaq's public endpoint (Yahoo's chart API hard-429s and Stooq sits behind
a proof-of-work wall). Kalshi market data is public and read-only; nothing here trades.

## Rules, each with its why

1. **Rank on `accel`, but call on agreement.** `accel` is last month minus the prior two
   months' monthly pace. Alone it mis-ranks: a semiconductor ETF can top it only because
   it is restarting from a summer stall while already +70% on the year. The clean signal
   is **accel > 0 AND RS1m > RSpace > 0 AND 12m flat or negative.** That is a turn off a
   base, not a late restart.
2. **Acceleration means relative to SPY, not absolute.** In a rising tape every sector
   "accelerates". A sector only matters if its lead over the index is widening.
3. **Always read breadth: RSP vs SPY.** If equal-weight lags, the acceleration is narrow.
   Say so. A narrow rally is a different call from a broad one, not a footnote to it.
4. **Name the rate bet.** Long-duration growth (software, biotech) and the inflation
   complex (energy, gold, copper, uranium) are two sides of one bet on the Fed. Read
   `kalshi_macro.py` and tie the call to the next dated print (CPI, FOMC). That date is
   the falsifier. Without it the call can't be scored.
5. **Check the narrative with one news search** (the week's sector recap) before saying
   why. A table says what moved; only the news says whether the driver is rates, earnings
   or a one-off. Cite sources.
6. **Separate the 1-week tape from the 1-month trend.** The month can say software while
   the week says utilities and staples. Report both. Don't let one week overwrite the
   trend, and don't hide it either.
7. **A sector read is not a buy call.** Any single name needs its own entry analysis
   (valuation, overhangs, catalysts, a written exit).

## Next: from sector to a 30-day trade

`thirty-day-catalyst` takes the accelerating sectors down to names with an earnings print
inside a 30-day hold, a value filter, lagging their sector ETF, and a recognition state.

## Leave residue

Append a dated entry to a `SECTOR-READS.md` log: the call, the table, the driver, the
falsifier date and an empty **Scored** line. **Before writing a new entry, score the last
one** by re-running the scan and comparing. A call that is never scored teaches nothing.
Each run also writes `data/sector_momentum/<last-bar-date>.csv` as a local cache.

Not investment advice; a research method.
