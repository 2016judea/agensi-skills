---
name: reddit-customer-language
description: >-
  Collect the exact words buyers use for a problem, for copy, positioning, landing pages
  and ad headlines: recurring phrases ranked by how many distinct people used them, with
  verbatim quotes and permalinks. Use for "how do customers describe X", "voice of
  customer", "what words should our copy use", "how do owners talk about getting paid late".
compatibility: >-
  Python 3, standard library only. Network access to one host:
  arctic-shift.photon-reddit.com (the public Arctic Shift Reddit archive). No key, no login.
allowed-tools: Bash(python3:*) Read Write
metadata:
  network-hosts: "arctic-shift.photon-reddit.com"
  network-purpose: "read public Reddit posts and comments from the Arctic Shift archive"
  version: "1.0"
---

# Reddit customer language

The deliverable is a **phrase bank**: the phrases buyers repeat when they describe a
problem or what they want, ranked by distinct authors, each with verbatim quotes and links.
It answers "what words do *they* use", which is rarely the words a seller uses.

## Method

**1. Pull the problem, with comments.** Key on the topic loosely; the language you're
after is in how people describe it, so pull comments too.

```bash
python3 scripts/reddit_pull.py --subreddits smallbusiness Entrepreneur --queries invoic \
  --after 2026-05-01 --before 2026-11-01 --top 0 --comments 15 --comments-for 25 \
  > pull.json 2> pull.log
```

**2. Rank the phrases** in sentences about the problem. Three lenses, run each:

```bash
# how they describe the pain
python3 scripts/reddit_tally.py phrases pull.json --near-preset pain --min-threads 2 --top 30 --quotes 3 --quote-rows 10
# what they wish for
python3 scripts/reddit_tally.py phrases pull.json --near-preset desire --min-threads 2 --top 30 --quotes 3
# every sentence naming the topic
python3 scripts/reddit_tally.py phrases pull.json --about invoic --min-threads 3 --top 30 --exclude invoice
```

`--exclude` drops phrases that only restate your keyword. `--min-n 3` gives longer,
more quotable phrases at lower counts.

**3. Pick the language.** Read the table top to bottom and keep phrases a buyer would say
out loud ("paid late", "chasing payments", "net 30"), drop generic ones ("small business").
Keep the counts beside each phrase; a phrase from 2 people is a quote, from 20 it's a market.

## The deliverable

1. The corpus line and the filter line from the tally.
2. Three short lists: pain words, wish words, topic words, each phrase with threads and
   authors and one or two verbatim quotes with links.
3. Optional: five headline or subject-line drafts built **only** from phrases in the lists,
   each tagged with the phrase it uses. Never present a draft as a quote.
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

Getting paid on invoices, r/smallbusiness + r/Entrepreneur, 2026-05-01 to 2026-11-01,
`--queries invoic`, comments on the 25 most-discussed threads per sub.

```
Corpus: 1,456 documents (903 posts, 553 comments) in 909 threads by 1,241 authors, r/Entrepreneur, r/smallbusiness, 2026-05-01 to 2026-10-31. Dropped as vendor pitches / market research: 169 posts (+9…
```

**Topic words** (`--about invoic pay --min-threads 5 --exclude invoice invoices invoicing "small business"`):

| # | phrase | threads | authors | example |
|---|---|---|---|---|
| 1 | follow ups | 40 | 36 | "Every new customer means more onboarding calls, more support tickets, more invoicing follow ups, more updates to documentation." ([link](https://reddit.com/comments/1t339z2)) |
| 3 | payment terms | 20 | 23 | "We give our good accounts standard Net 30 payment terms so they do not have to pay up front every single time." ([link](https://reddit.com/comments/1vjlz67)) |
| 4 | cash flow | 19 | 20 | "How do you guys handle uneven cash flow with big invoices?" ([link](https://reddit.com/comments/1uj7jca)) |
| 5 | due date | 12 | 16 | "I invoiced her back in April with a due date of May 15." ([link](https://reddit.com/comments/1w9na0a)) |
| 8 | late fee | 6 | 12 | "The company I work for builds a small late fee into the price and offers a "discount" if they pay by a certain number of …" ([link](https://reddit.com/comments/1vjlz67/_/p2mtmo3)) |
| 9 | keep track | 13 | 11 | "… you have invoices for payments that people need to send you, how do you keep track of it and ensure that it's paid on time?" ([link](https://reddit.com/comments/1vzl1jz)) |
| 11 | clients pay | 10 | 10 | "which means we're buying materials, paying the guys, running trucks, for 2 months before those clients pay a single dollar." ([link](https://reddit.com/comments/1tevd7y)) |
| 12 | pay on time | 9 | 10 | "For the people who've had a big account do this, what got them to actually pay on time?" ([link](https://reddit.com/comments/1vqq8sr)) |
| 13 | payment reminders | 9 | 9 | "… I spend 2–3 hours a week just sending payment reminders, and I am not even that big yet (maybe 15–20 active invoices at any time)." ([link](https://reddit.com/comments/1tuyjyn)) |

(Rows for generic phrases such as "business owners" and "run a small" cut here.)

**Pain words** (`--near-preset pain`), the phrases that carried a real complaint:

| # | phrase | threads | authors | example |
|---|---|---|---|---|
| 3 | worst part | 6 | 6 | "The worst part is I can't even tell if they've seen the invoice." ([link](https://reddit.com/comments/1vs0ia7)) |
| 5 | frustrating part | 5 | 5 | "The frustrating part is that the business has customers, sales opportunities, and the ability to generate revenue, but my working capital has been severely depleted …" ([link](https://reddit.com/comments/1xek3jc)) |
| 11 | getting overwhelmed | 3 | 3 | "Anyone else slowly getting overwhelmed with invoices?" ([link](https://reddit.com/comments/1t2yycx)) |

**Wish words** (`--near-preset desire --min-threads 2`):

- "simple tool" (2 threads, 2 authors): "I just want a simple tool that sends automated email reminders when a client forgets to pay." ([link](https://reddit.com/comments/1upl4cb))

Headline drafts built only from the lists above, each tagged with its source phrase:

- "Stop sending payment reminders by hand." (payment reminders, 9 authors)
- "Know when a client has seen the invoice." (worst part: "I can't even tell if they've seen the invoice")
- "Net 30 without the follow ups." (payment terms 23 authors, follow ups 36 authors)

Note what the buyers did *not* say: "accounts receivable" appears in 3 threads by 3
authors (`--about "accounts receivable" --min-threads 1`), while "follow ups" came from 36.
That gap is the copy lesson.
