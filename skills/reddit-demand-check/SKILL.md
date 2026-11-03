---
name: reddit-demand-check
description: >-
  Validate an idea against Reddit: does anyone actually ask for X? Counts the posts that
  both name the topic and ask for a tool, app, service or way to do it ("is there an app
  that", "looking for software", "what do you use for"), month by month against the
  number of posts scanned, with every asking thread linked. Reports a null result
  honestly. Use for "is there demand for X", "do people want Y", "validate this idea".
compatibility: >-
  Python 3, standard library only. Network access to one host:
  arctic-shift.photon-reddit.com (the public Arctic Shift Reddit archive). No key, no login.
allowed-tools: Bash(python3:*) Read Write
metadata:
  network-hosts: "arctic-shift.photon-reddit.com"
  network-purpose: "read public Reddit posts and comments from the Arctic Shift archive"
  version: "1.0"
---

# Reddit demand check

One question: **in these subreddits, over this window, how many people asked for this
thing to exist, and is that rising or falling?** The answer is a count, a monthly rate
with its denominator, and the list of asking threads. Zero is a legitimate answer.

## Method

**1. Name the topic as regexes**, broad enough to catch how people actually say it:
`invoic` catches invoice, invoicing, invoices. Pick 2-4 subreddits where the buyer posts.

**2. Pull every topic post, with a denominator.** `--stats` records how many posts were
scanned per month, so a rate can be computed; `--top 0` keeps every match.

```bash
python3 scripts/reddit_pull.py --subreddits smallbusiness Entrepreneur \
  --queries invoic --after 2026-05-01 --before 2026-11-01 --top 0 \
  --stats stats.json > pull.json 2> pull.log
```

Run one process per subreddit (each with its own `--stats` file) to go faster on busy
subs, then pass all the JSON files and every stats file to the tally (`--stats a.json b.json`).

**3. Count the asks:**

```bash
python3 scripts/reddit_tally.py asks pull.json --topic invoic --stats stats.json --list 30
```

A post counts when one sentence (or the title) names the topic **and** asks: "is there a",
"looking for a tool/app/software", "what do you use", "recommendations for", "alternative
to", "how do you handle", "anyone use". Add trade-specific asks with `--ask "regex"`.

**4. Read the asking threads** (the tally lists them, newest first) and drop the ones that
are self-promotion dressed as a question. Say how many you dropped and why; re-run with
`--json` and count what remains if the drop is large.

## The deliverable

1. Window, subreddits, posts scanned, topic posts, asks and distinct askers, from the tally.
2. The monthly table (scanned, asks, asks per 1,000 posts). A trend claim needs the rate,
   not the raw count: a sub that doubled in size doubles its raw asks too.
3. The asking threads, verbatim ask, linked. Group them by what they asked for if it helps.
4. The call in one line: demand seen / thin / none in this window. A null is reported as
   "0 asks in N posts scanned across r/A, r/B, DATE to DATE", never as "nobody wants this".
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

"Do small businesses ask for invoicing tools?" r/smallbusiness + r/Entrepreneur,
2026-05-01 to 2026-11-01, `--queries invoic`, one pull per sub.

```
Window: 2026-05-01 to 2026-11-01. Subreddits: r/smallbusiness, r/Entrepreneur. 35,161 posts scanned.
Posts mentioning the topic (invoic): 886.
Posts asking for it: 56 by 54 distinct authors.
```

| month | posts scanned | asks | asks per 1,000 posts |
|---|---|---|---|
| 2026-05 | 9046 | 16 | 1.8 |
| 2026-06 | 6695 | 11 | 1.6 |
| 2026-07 | 6099 | 3 | 0.5 |
| 2026-08 | 5035 | 8 | 1.6 |
| 2026-09 | 4336 | 8 | 1.8 |
| 2026-10 | 3950 | 10 | 2.5 |

| date | sub | ask (verbatim) | score | comments | link |
|---|---|---|---|---|---|
| 2026-10-29 | r/smallbusiness | "What software do you use to manage billing and inventory for your small business?" | 6 | 16 | https://reddit.com/comments/1xigm8i |
| 2026-10-29 | r/smallbusiness | "Small business owners, how do you handle messy financial data?" | 0 | 1 | https://reddit.com/comments/1xii8j3 |
| 2026-10-28 | r/smallbusiness | "Small business owners, how do you handle documents like equipment invoices, warranties, service reports, and supplier contracts?" | 3 | 15 | https://reddit.com/comments/1xhrfsp |
| 2026-10-28 | r/smallbusiness | "How do you handle a client invoice that's 30+ days late?" | 1 | 1 | https://reddit.com/comments/1xhqor7 |
| 2026-10-18 | r/smallbusiness | "I hate typing invoice emails into spreadsheets. What do you use to automate it?" | 0 | 10 | https://reddit.com/comments/1x8zse6 |
| 2026-10-16 | r/smallbusiness | "What software do you use to manage invoices and payments?" | 5 | 28 | https://reddit.com/comments/1x7ijwd |
| 2026-10-07 | r/smallbusiness | "How do you handle invoice follow-ups and document collection before starting work? We wasted 6+ hours weekly just chasing the customers for docs and payments?" | 0 | 1 | https://reddit.com/comments/1wzwo6k |

(49 more in the tally's list.)

Reading it: 56 asks from 54 people in six months, between 0.5 and 2.5 per
1,000 posts and highest in 2026-10. The raw count went from 16 to 10 while the rate went
from 1.8 to 2.5, because the subs posted less (9046 to 3950 posts a month): a
raw-count chart would have shown demand falling. Read the list before quoting the total;
some asks are market research the pitch filter didn't catch ("What's one everyday problem
you wish there was a simple and affordable solution for?" is not an invoicing ask).
r/Entrepreneur alone gave 2 asks from 1 author: a one-sub run would have read as no demand.
