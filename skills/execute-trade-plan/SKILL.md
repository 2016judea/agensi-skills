---
name: execute-trade-plan
description: >-
  Decide whether a trade you already pre-committed in your trading journal fires today,
  and produce the exact order to place. Use when you say "what's the game plan", "I'm
  sitting on cash", "what do I do with this cash", "any trades today", "what's my next
  move", "is it time to buy X yet", "should I add to X", "should I place the order", "did
  it fill", or name a ticker with an open tranche or a dated gate. The cash question is the
  giveaway: in a disciplined book the cash is usually already committed to dated tranches,
  so these are execution checks wearing a research question's clothes. Distinct from
  `entry-timing` (underwrites a NEW name) and `portfolio-review` (how's the book doing).
---

# Execute a pre-committed trade plan

The edge is written down *before* conviction is tested. This skill is the motion that
honours that: a plan with a dated gate already exists in `JOURNAL.md`, and the job is to
check whether it fires, compute the exact order, and refuse to re-litigate reasoning that
was settled when the investor was calm.

**Done looks like:** a one-line order to place (side, ticker, share count, limit,
duration) or an explicit "stand down, next gate is <date>" — plus the downstream cash
still reconciling to its earmarks.

Live book via `etrade-pull`. Journal format: `trade-journal`.

---

## Rule 1 — Read the journal before you research anything

**Read `JOURNAL.md` first: the tail of the review log, plus the full position block for
every name with an open gate.** Only then search the web.

**Why:** research-first produces confident "new" findings (e.g. "the divestiture is
mildly EPS-dilutive, so consensus needs a second look") that the position block *already
contains*. Presenting already-underwritten facts as new invites reopening a decision that
was made deliberately — the exact failure the journal exists to prevent.

External research is for what the journal explicitly flags as **unresolved**. Not for
re-deriving the thesis.

## Rule 2 — Cash in the account is committed, not dry powder

Read the earmarks out of the journal before proposing any use of cash. Idle cash that is
earmarked for a dated tranche does not need "a home."

**Quote only `cashAvailableForInvestment`.** In a margin account the broker UI surfaces
much bigger numbers (`netCash`, `marginBuyingPower` can be 7x and 13x real cash). If no
stops are used, position size is the only risk control, and margin is the one thing that
breaks it outright.

## Rule 3 — A gate that fires by a hair fires

Read the pre-committed rule **verbatim**. Evaluate it against live data. Then execute it.

Example: the rule was *"buy GTC if the price is <= $227 after the CPI print."* It closed
$226.74 — inside by 26 cents, having straddled the line all day.

**The margin is not information.** "It's basically at the ceiling, let's wait one more
day" is precisely the rationalization the pre-commitment was built to block. If the rule
fires, say it fires. If it doesn't, stand down and name the next gate; don't stretch it.

**Revising a gate is legitimate — but only before the trigger, and only on logic.** A
ceiling revised a day *ahead* of the print, with the reasoning written into the block "so
it can be judged as revision-on-logic vs. rationalization-after-a-miss", is the model.
Revising a gate at the moment it's tested, in the direction that lets you act, is not a
revision.

## Rule 4 — A tranche is a percent of book. The share count is derived at placement.

**The single most valuable thing in this skill.** A rule that says "buy 37 sh" was never a
decision: it was ~5% of book computed at an older price. At a ~5% higher price it buys
5.23% and overruns the next tranche's earmark. Carrying a stale share count forward
silently inflates position size as price rises.

    shares = round(target_pct × total_account_value ÷ live_price)

Example: 5% × $160,000 ÷ $226.74 = 35.3 -> **35 shares = ~4.9%**, on target.

**Then check the downstream earmark.** Does the order leave enough for the *next*
committed tranche? Always reconcile forward before recommending.

## Rule 5 — GTC when the limit is a valuation line, and confirm it exists

**Good-for-day only for a genuine same-day tactical view. Otherwise GTC.** A GFD limit
that expires overnight, followed by the stock trading through the level the next session
with no order in the market, is the classic execution gap. The level was right; the
duration was the bug. Manual daily re-entry is not "more disciplined."

**Duration is only half of it — placement is the other half.** Gates can be correct,
pre-committed and written, and still not be in the market. Run `order-check` rather than
asking whether it was placed.

## Rule 6 — Size the *next* gate now, not on its day

When one tranche resolves, settle the next one's size immediately while the arithmetic is
in front of you. If post-fill cash funds 3.1% instead of a planned 4%, decide now whether
to trim something to close the gap or cut the tranche — often cutting it is correct. **The
day of a catalyst is the worst moment to be doing sizing arithmetic.**

## Rule 7 — Look through index funds before sizing anything they already hold

A total-market fund's top 10 can be ~30% of the fund, with one mega-cap ~6% of it. At a
~32% fund weight, a direct 4.3% position in that mega-cap is really ~6.3% effective, and
a planned add lands near 9.4%, not 7.4%. Direct weight understates every mega-cap. Compute
the effective figure before sizing an add to any name the fund holds. If lowering that
exposure is the goal, the lever is sizing the add smaller, not adding a new name.

## Rule 8 — A cap breached by price appreciation is not a trade

A name drifting past its cap without a share being bought is a **watch, not a trim**:

1. **If the thesis is waiting out a dated overhang, trimming pre-catalyst inverts the
   trade.** Selling strength before the thing you're waiting for is backwards.
2. **Check the holding period.** A trim before the lot turns long-term is a short-term
   gain taxed as ordinary income.

**Always give a re-visit threshold** ("revisit if it clears ~30%") rather than leaving it open.

## Rule 9 — Verify the fill; never assume the limit price

A buy limit fills **at or below** its limit. Pull the actual execution before journaling
(e.g. limit $227, filled $225.105). Transaction endpoints: `etrade-pull`.

---

## Sequence

1. `etrade-pull` -> live positions + `cashAvailableForInvestment`. Check the CSV's date;
   re-pull if it predates a trade that was mentioned.
1b. `order-check` -> **what is actually resting at the broker**, before reasoning on top
   of anything the register says is live. If it reports an over-cap position with no
   resting stop, **that is the answer to whatever was asked** — it is the one thing that
   can still be fixed today.
2. **Read the gate register** at the top of `JOURNAL.md` — one block indexing every live
   trigger by class: **A** dated, **B** portfolio-state, **C** price/sell-into-strength,
   **D** multiple-based, **E** fundamental invalidations. **Then read the position block
   for anything the register flags** — the register is an index, *the block is the
   authority on reasoning.*
2b. **Fire on the transition, not the state.** Each row carries `ARMED` -> stamp `FIRED
   <date>` on the crossing -> it stays fired until deliberately re-armed with a reason.
   **Update the row's state in the same edit as the trade.**
3. **Resolve only the journal's flagged-unresolved items** via web search — plus any macro
   print the gate is conditioned on.
4. **Evaluate the gate** (Rule 3).
5. **If it fires:** compute shares (Rule 4), pick duration (Rule 5), reconcile the forward
   earmark, produce one line: *side / ticker / shares / limit / duration.*
6. **Report weights, deltas since the last journal entry, and any invalidation check.**
7. **The investor places it.** Wait for confirmation it executed. Never write it up as done
   (or, if using `order-check`'s transmitter, only after an explicit go).
8. **On fill:** verify the real price (Rule 9), then journal it — convert any `CANDIDATE —
   NOT YET OPENED` header to `OPENED <date>` with the real basis, and leave the pre-fill
   reasoning **unedited** underneath.

## Decide vs. the investor's call

- **Decide:** whether the gate fired; the share count; order type and duration; whether a
  cap breach is actionable; what's worth researching; the next tranche's size.
- **Theirs, always:** placing the order, and overriding any of the above. When advising
  "no buy", **name the cost of the discipline out loud** ("if the print is cool and it
  runs, the position is missed and the thesis was right").

## Known gaps

- **Forward-EPS consensus can disagree across sources, and it changes the gate.** When two
  estimates disagree, state both, check whether the decision is robust to the spread, and
  say so explicitly.
- **Stale headlines recur.** An "analyst upgrades X" story citing a target and a drawdown
  that are impossible against today's price and 52-week range is stale. **Sanity-check
  every analyst headline against the live price and range before it enters the
  reasoning**, and log confirmed-stale sources in the position block.

Not investment advice; an execution discipline.
