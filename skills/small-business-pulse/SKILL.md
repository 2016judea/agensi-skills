---
name: small-business-pulse
description: Use when asked for a "state of small business in America" read — a macro pulse-check blending real government labor/formation data with actual owner sentiment. Triggers on "how's small business doing", "state of small business", "small business pulse/check-in", or any ask to combine government stats with Reddit/ground-level color on a sector or the economy broadly. Not tied to any one repo topic — general macro research, not a B&M-branded deliverable.
compatibility: >-
  Network access to public government APIs, a grounded web search and a public Reddit archive, from the user's machine.
metadata:
  network-hosts: "api.bls.gov api.census.gov generativelanguage.googleapis.com arctic-shift.photon-reddit.com"
  network-purpose: "labour, formation and sentiment data for the pulse report"
---

# Small Business Pulse

A four-source method for answering "how's small business actually doing
right now" with real numbers plus real ground-level color, not vibes. Extracted from a real end-to-end run, including two mistakes that cost
real time (a wrong Census query shape, and a Reddit pull that rate-limited
itself into uselessness).

**The shape of the finished report**, in order: one-line headline verdict →
JOLTS labor-market table + what it means → Census BFS formation table +
what it means → NFIB owner-survey bullets → Reddit ground-level themes →
one closing paragraph that ties the four together. Don't skip straight to
synthesis — each source answers a different question (is the market
formal/informal expanding, is hiring loosening, what do owners say hurts,
what does the unfiltered complaint sound like) and the report should let
the reader see all four before the synthesis claims anything.

## Step 1 — labor market: BLS JOLTS

**REQUIRED SUB-SKILL:** `federal-labor-data` for the verified series-ID
format. Pull openings (`JOR`), quits (`QUR`), layoffs (`LDR`), and hires
(`HIR`) rates for a small-business-relevant sector set — reuse this list
unless the task calls for a narrower one:

`000000` Total nonfarm, `230000` Construction, `440000` Retail Trade,
`540099` Professional & Business Services, `620000` Health Care & Social
Assistance, `700000` Leisure & Hospitality, `720000` Accommodation & Food
Services, `810000` Other Services.

That's 8 industries × 4 metrics = 32 series — split into two POST calls
(e.g. JOR+QUR, then LDR+HIR) since the unregistered BLS endpoint caps at 25
series/call. Pull `startyear` back to at least the sector's pre-pandemic
baseline (2019) so you can compare latest month vs. 1 year ago vs. 2019,
not just show a flat current snapshot.

**The number that actually tells the story is the quits rate** — it's the
"workers feel confident enough to leave" signal. Falling quits + falling
hires across sectors = a cooling, cautious ("low-hire, low-fire") labor
market; that combination is the single most useful sentence this source
can produce.

## Step 2 — new business formation: Census BFS

**REQUIRED SUB-SKILL:** `federal-labor-data` — its Census BFS section carries
a verified working query shape (`get=cell_value`,
`category_code=NAICS72`-style prefixed codes, not `NAICS2017=72`). Use that
exact shape; the previous version of that section 400'd on every call.

Pull High-Propensity Business Applications (`BA_HBA`) monthly, `2019-01`
through the current month, for `TOTAL` plus the same sector set as Step 1
where a `category_code` exists for it (retail is `NAICSRET`, not a NAICS
number). Sum 12 months for annual totals and compare: pre-pandemic (2019)
→ pandemic-era peak (usually 2021-2023) → most recent complete year. The
useful finding is almost never the headline total — it's which sectors are
still elevated over 2019 and which have round-tripped back down (that
divergence is more interesting than "formation is up" alone).

## Step 3 — owner sentiment: NFIB Small Business Optimism Index

Not a government source — NFIB is a private trade association survey, and
the report should label it as such rather than blending it silently into
"government data." It's still the standard-bearer index every outlet cites,
and it's the only source in this method that asks owners directly what's
hurting.

**REQUIRED SUB-SKILL:** `gemini-web-search`. Query for the latest release
(NFIB publishes monthly, roughly 2 weeks after month-end — check the search
result for what's actually current, don't assume "this month"):

```
NFIB Small Business Optimism Index <current month/year> latest reading and top owner concerns (inflation, labor quality, taxes)
```

Pull: the headline index value + direction, the top 2-3 "single most
important problem" categories with their percentages, and one forward-
looking figure (six-month outlook, hiring plans, or capital-spending plans)
so the report isn't only backward-looking complaints.

## Step 4 — ground-level sentiment: Reddit

**REQUIRED SUB-SKILL:** `reddit-mining`. Two hard lessons from the first
run, both now baked into the sizing below:

1. **Start small — do not fan out.** A first pass across 6 subreddits × 8
   queries × `--comments` (which fires one extra API call per thread found,
   easily 400+ calls) tripped the archive API's rate limiter so hard that even a
   single-subreddit, single-query, no-comments test 20 minutes later still
   429'd. Start with 2-3 subreddits × 3-4 short (1-2 word) queries, **no
   `--comments` flag** on the first pass — submission titles + selftext
   alone usually carry enough color, and comments are the expensive part.
   Only add `--comments` on a second, smaller, targeted pass if specific
   threads need it.
2. **If the Reddit archive API is genuinely down, don't keep retrying — fall back and
   say so.** Run one minimal single-query test
   (`--subreddits smallbusiness --queries "inflation" --limit 5`, no
   comments). If that alone 429s, the service is down for this session,
   not just rate-limited from your own burst — stop and fall back to a
   `gemini-web-search` query scoped with `site:reddit.com`
   (e.g. `site:reddit.com r/smallbusiness OR r/Entrepreneur <year> discussion what small business owners are actually complaining about right now`).
   **Label this fallback explicitly in the report** ("via grounded search,
   not a verbatim pull") and never present its paraphrased content as an
   exact quote — that's a model's summary of real threads, not text you
   pulled and can cite a permalink for. The `reddit-mining` skill's hard
   rule (qualitative color only, never a stat) applies double here since
   you can't even verify exact wording.
3. **`timeout` is not available by default on macOS zsh** (no coreutils) —
   don't rely on it to bound a reddit-mining call; use a backgrounded Bash
   call and check/kill manually if it's clearly stuck (no log progress for
   several minutes on a small pull is the tell).

## Step 5 — synthesize

Write the report in the order given at the top. The closing paragraph
should connect what the *macro* data says (is dynamism up or down) to what
*owners* say hurts (NFIB) to what it *sounds like* on the ground (Reddit) —
three altitudes of the same story, not three unrelated sections.

## Common mistakes

| Mistake | Fix |
|---|---|
| Guessing Census BFS query params from intuition | Use the corrected shape in `federal-labor-data` — `get=cell_value`, `category_code=NAICS72`/`NAICSRET`/`TOTAL`, not `NAICS2017=<number>`. |
| Firing a large multi-sub, multi-query, `--comments` Reddit pull as the first attempt | Start with a 2-3 sub × 3-4 query, no-comments pass. It's fast and usually enough. |
| Continuing to retry a rate-limited Reddit pull for many minutes | One minimal single-query test tells you if it's really down. If it 429s too, stop and fall back to grounded search — say so in the report. |
| Presenting a grounded-search paraphrase of Reddit threads as a verbatim quote | It isn't one. Label the fallback explicitly; don't invent exact wording or a permalink you don't have. |
| Blending NFIB (private survey) into "government data" without labeling it | NFIB is not a government source — say so, even though it's the standard-bearer index everyone cites. |
| Leading with synthesis instead of showing each source | The reader should see JOLTS → BFS → NFIB → Reddit before any "bottom line" claim — that's what makes the conclusion earned rather than asserted. |

## References

`federal-labor-data` (BLS JOLTS/OEWS and Census BFS formats), `gemini-web-search` (the NFIB
pull and the Reddit fallback), `reddit-mining` (the primary Reddit pull and its
qualitative-only rule).
