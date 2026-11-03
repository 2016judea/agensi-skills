---
name: reddit-competitor-chatter
description: >-
  Read what Reddit says about a brand and its competitors: mentions by distinct authors,
  praise vs complaint sentences, the themes inside each, who people switch to and why,
  all counted and linked. Use for "what do people say about QuickBooks vs Xero",
  "competitor research on Reddit", "why do customers leave X", "brand sentiment for Y".
compatibility: >-
  Python 3, standard library only. Network access to one host:
  arctic-shift.photon-reddit.com (the public Arctic Shift Reddit archive). No key, no login.
allowed-tools: Bash(python3:*) Read Write
metadata:
  network-hosts: "arctic-shift.photon-reddit.com"
  network-purpose: "read public Reddit posts and comments from the Arctic Shift archive"
  version: "1.0"
---

# Reddit competitor chatter

The deliverable is a **brand scorecard** for a named set of competitors plus the
**themes** of what people praise and complain about for each, with switch reasons. Every
cell is a count from the tally and every claim is pinned to a linked quote.

## Method

**1. Pull the subreddits where buyers compare them**, keyed on the brand names, with
comments (comparisons happen in replies):

```bash
python3 scripts/reddit_pull.py --subreddits smallbusiness Bookkeeping Accounting \
  --queries quickbooks xero freshbooks " wave " --after 2026-08-01 --before 2026-11-01 \
  --top 0 --comments 20 --comments-for 25 > pull.json 2> pull.log
```

A short brand name that is also a word ("wave") needs spaces or a better alias, or it
pulls in every post about a wave of something.

**2. Write `brands.json`** with every alias (`"QuickBooks": ["quickbooks", "qbo", "qb online", "intuit"]`)
and get the scorecard and switch table:

```bash
python3 scripts/reddit_tally.py tools pull.json --tools brands.json --quotes 2
```

**3. Find the themes per brand.** Restrict counting to sentences that mention one brand
with `--about`, and to complaints (or praise) with `--near-preset`:

```bash
python3 scripts/reddit_tally.py phrases pull.json --about quickbooks qbo --near-preset complaint --min-threads 2
python3 scripts/reddit_tally.py themes  pull.json --themes themes.json --about quickbooks qbo --near-preset complaint --quotes 2
```

Use one shared `themes.json` (pricing, support, bank feeds, bugs, migration, payroll...)
across brands so the rows compare. Run it once per brand and once with
`--near-preset praise`.

## The deliverable

1. Corpus line, then the scorecard: brand, threads, authors, praise, complaint, switched
   to, switched away.
2. The switch table, and the reasons people give, quoted and linked.
3. Per brand: top complaint themes and top praise themes with counts and one quote each.
4. Your read, a few lines, each sentence pinned to a number or a quote above.

Don't compare raw counts between brands without saying the pull was keyed on their names:
a brand with more mentions may simply be the bigger brand. Praise-to-complaint ratio and
switch direction compare better than volume.
## Ground rules (every skill in this series)

- **Every number comes from `reddit_tally.py`.** Threads, authors, counts, dates, rates:
  paste them from its output. Never estimate, round up, or count by reading.
- **Every quote is verbatim, short (25 words or fewer), and carries its permalink.**
  The tally prints them that way; don't paraphrase inside quote marks.
- **Print the corpus line.** The tally's first line (documents, threads, authors,
  subreddits, dates) goes at the top of the deliverable, so a reader knows the sample.
- **The keywords shaped the corpus.** A count is a property of *your pull*, not of the
  subreddit: "41 of the threads I pulled" is honest, "41% of r/X" is not.
- **Absence is not proof.** The archive lags live Reddit and has gaps; a zero is
  reported as a zero for this window and these subreddits, nothing wider.
- **Vendor pitches are dropped before counting.** Owner subreddits are full of "I built
  a tool for X, what's your biggest pain?" posts; the tally drops them (and the pitcher's
  own replies) and prints how many (`digest` keeps everything). `--keep-pitches` turns that off.
- Archive quirks (silent truncation, why server-side search is useless, the dead
  alternatives) live in the `reddit-mining` tool skill. Read it if a pull looks thin.

Nothing here bundles, hosts or resells Reddit data: the scripts query the public
Arctic Shift archive from your own machine, and Reddit's terms (and Arctic Shift's)
govern what you do with what you pull.

## Setup

The scripts sit in `scripts/` beside this file: `reddit_pull.py` (fetch) and
`reddit_tally.py` (count). Python 3, standard library only, no key, no login. Pulls
over a busy subreddit take minutes: run them in the background and write to a file.
Part of a set: `reddit-mining` (the tool skill), `reddit-pain-points`,
`reddit-demand-check`, `reddit-tool-stack`, `reddit-competitor-chatter`,
`reddit-customer-language`, `reddit-thread-digest`.

## Example (real run, trimmed)

QuickBooks vs Xero vs FreshBooks vs Wave and others, r/smallbusiness + r/Bookkeeping +
r/Accounting, 2026-08-01 to 2026-11-01, keyed on the brand names, comments on the 25
most-discussed threads per sub.

```
Corpus: 1,693 documents (389 posts, 1,304 comments) in 393 threads by 1,185 authors, r/Accounting, r/Bookkeeping, r/smallbusiness, 2026-08-01 to 2026-11-02. Dropped as vendor pitches / market research…
```

| # | tool | threads | authors | praise | complaint | switched to | switched away | top thread |
| 1 | QuickBooks | 332 | 452 | 23 | 17 | 11 | 10 | https://reddit.com/comments/1vej0nh |
| 2 | Xero | 91 | 119 | 8 | 3 | 3 | 0 | https://reddit.com/comments/1vmbvuc |
| 3 | Excel / spreadsheets | 65 | 91 | 3 | 4 | 0 | 1 | https://reddit.com/comments/1ww4277 |
| 4 | Sage | 19 | 24 | 0 | 1 | 0 | 0 | https://reddit.com/comments/1wxijy1 |
| 5 | Zoho Books | 14 | 24 | 3 | 0 | 3 | 0 | https://reddit.com/comments/1wdufyq/_/p998j2g |
| 6 | Wave | 15 | 20 | 0 | 2 | 1 | 0 | https://reddit.com/comments/1wdufyq/_/p9903jd |
| 7 | Dext | 4 | 9 | 1 | 0 | 0 | 0 | https://reddit.com/comments/1w2kswn |
| 8 | FreshBooks | 6 | 6 | 1 | 0 | 0 | 0 | https://reddit.com/comments/1w90dhu/_/p86rrsd |
| from | to | documents | example |

| from | to | documents | example |
|---|---|---|---|
| 5 | Zoho Books | 14 | 24 | 3 | 0 | 3 | 0 | https://reddit.com/comments/1wdufyq/_/p998j2g |
| 6 | Wave | 15 | 20 | 0 | 2 | 1 | 0 | https://reddit.com/comments/1wdufyq/_/p9903jd |
| ? | QuickBooks | 10 | "We will be transitioning to Quickbooks soon, just finishing up ongoing projects that were done through excel." (https://reddit.com/comments/1wx47gn) |
| QuickBooks | ? | 9 | "For the love of God, please cancel your Intuit Quickbooks subscription." (https://reddit.com/comments/1wdufyq) |
| ? | Zoho Books | 3 | "Switched to Zoho books." (https://reddit.com/comments/1wdufyq/_/p998j2g) |
| QuickBooks | Wave | 1 | "I switched from Quickbooks to Wave about 18 months ago because I was tired of the crappy customer service from Intuit." (https://reddit.com/comments/1vryr7o) |

QuickBooks complaint themes (`--about quickbooks qbo qbd intuit --near-preset complaint`):

```
In scope: 26 documents (sentences mentioning quickbooks, qbo, qbd, intuit; sentences matching complaint). Matched at least one theme: 16. Matched none: 10.
```

| # | theme | threads | in a complaint sentence | authors | mentions | first | last | months active |
| 1 | Price and price increases | 5 | 5 | 8 | 8 | 2026-08-03 | 2026-09-28 | 2 |
| 2 | Desktop phase-out / forced to online | 3 | 3 | 3 | 3 | 2026-08-03 | 2026-08-30 | 1 |
| 3 | Bugs and reliability | 2 | 2 | 2 | 2 | 2026-08-03 | 2026-08-06 | 1 |
| 4 | Payroll | 2 | 2 | 2 | 2 | 2026-08-03 | 2026-10-23 | 2 |
| 5 | Integrations and apps | 2 | 2 | 2 | 2 | 2026-08-03 | 2026-10-20 | 2 |

- Price: "In my experience QuickBooks is awful expensive and fragile." ([link](https://reddit.com/comments/1wdufyq/_/p98skdu))
- Integrations: "I am in retail so I am adding my COGs manually because QBO's integration with Square is garbage." ([link](https://reddit.com/comments/1vej0nh/_/p1i6vmn))
- Switch reason: "I switched from Quickbooks to Wave about 18 months ago because I was tired of the crappy customer service from Intuit." ([link](https://reddit.com/comments/1vryr7o))

Reading it: QuickBooks dominates volume because it dominates the market, so volume says
little. Direction says more: 10 documents move away from it and 11 move to it, while Zoho
Books and Xero only gain (3 and 3, none away). Small counts: name them as such.
