---
name: thirty-day-catalyst
description: Find an undervalued stock the market hasn't recognized yet (or has JUST started to) that can be entered AND exited within 30 days, using an earnings print as the clock. Use when you say "30-day trade", "short-term trade", "undervalued but not realized yet", "someone on Wall Street just saw it", "what can I get in and out of this month", "run the catalyst screen", or "any post-earnings drift names". Free data (Nasdaq, SEC), no keys.
---

# 30-day catalyst trade

**The premise:** undervalued is usually the right trade, and the *what* is usually right.
The failure is *when*. So the trade is constrained: **in and out within 30 calendar days
of entry. Earlier exits are allowed. Anything past 30 days is a non-option, not a
fallback.**

## The one idea that makes this work

Inside 30 days **valuation is the filter, never the clock.** A cheap name with no forcing
event re-rates on the market's schedule, which can take quarters. The clock must be a
dated event inside the window, which in practice means an **earnings print**. Two modes:

- **POST (preferred):** a beat the market under-reacted to, then post-earnings drift
  (Bernard & Thomas 1989) and analyst-revision drift (Womack 1996). This is "someone on
  Wall Street has just seen it", made measurable. Run daily during earnings season.
- **PRE:** hold through a confirmed print, exit within days after it. Binary, so size it
  as money that can take a -15% gap.

## Order of work

1. **Sector first:** `sector-acceleration`. Hunt names in sectors that are speeding up; a
   laggard in an accelerating sector has a tailwind to catch.
2. **Screen:**
   ```bash
   pip install requests
   python catalyst_screen.py --asof <entry date> [--post-days 5]
   ```
   Stages and every column are in its docstring. ~10 min; run it in the background.
   `screener.py` is the wider stage-1 value screen it builds on; fill in its `KILLED`
   (names you've already rejected, with the reason) and `HELD` sets from your own
   journal so it stops re-surfacing them. `recognition.py` scores whether the analyst
   crowd has already turned (EARLY / MID-FLIGHT / CONSENSUS). `screener.py --gaap`
   cross-checks the adjusted P/E against SEC as-reported figures (set
   `SEC_USER_AGENT="Your Name you@example.com"` first).
3. **Kill on the facts the screen can't see.** One news search per finalist: why is it
   down? A crowd that is RIGHT looks identical to an early one. A beat followed by a
   falling stock means the cause is narrative (good). A guidance cut means the cause is
   the P&L (kill).
4. **Finalist -> a written plan:** entry date, the print date, a **hard exit date <= entry
   + 30**, and the early-exit condition (e.g. "sell on the first day the drift stalls after
   the print"). Size as % of book.

## Rules, with why

- **Exit date is written before entry.** If you run no stops, size is your only risk
  control; a time stop is the stop here, and it only holds if written first.
- **Confirmed print dates only for PRE.** Nasdaq/Zacks dates marked `~` are algorithmic
  guesses. A print that slips past day 30 removes the clock.
- **Read the industry, not Nasdaq's sector tag.** It files some industrials under Tech and
  tobacco under Health Care, which mis-benchmarks `rel1m`.
- **P/Es are adjusted, not GAAP** (see `screener.ttm_eps` docstring). Fine for the
  forward-vs-trailing comparison; never quote them as "the" P/E.
- **R4 (is the crowd wrong?) is deliberately manual.** Forward EPS must exceed trailing and
  forward P/E must be below trailing, checked against current company guidance from a
  second source. `recognition.py` explains why automating it off one feed is unsafe.
- **A high rank is a reason to research, never a buy.**

## Residue

Each run -> a dated entry in a `SECTOR-READS.md` log with the call and a **Scored** line.
Score the previous call before writing a new one.

Not investment advice; a research method.
