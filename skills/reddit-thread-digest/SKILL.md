---
name: reddit-thread-digest
description: >-
  Turn one Reddit thread, or a subreddit over a date window, into a linked digest: the
  question, the top answers by score with how much discussion each drew, the pushback,
  what the original poster decided, and every claim that carries a number, each with its
  permalink. Use for "summarize this Reddit thread", "what did r/X say this month",
  "what's the consensus in this thread", or when a link is pasted and the reader wants the gist.
compatibility: >-
  Python 3, standard library only. Network access to one host:
  arctic-shift.photon-reddit.com (the public Arctic Shift Reddit archive). No key, no login.
allowed-tools: Bash(python3:*) Read Write
metadata:
  network-hosts: "arctic-shift.photon-reddit.com"
  network-purpose: "read public Reddit posts and comments from the Arctic Shift archive"
  version: "1.0"
---

# Reddit thread digest

The deliverable is a **digest a reader can audit**: decisions, claims and disagreements,
each linked to the comment that made it. The tally ranks and extracts; you write the
summary on top, citing its links.

## One thread

```bash
python3 scripts/reddit_pull.py --thread https://www.reddit.com/r/smallbusiness/comments/1wu3z5m/ > thread.json
python3 scripts/reddit_tally.py digest thread.json --top 8
```

`--thread` takes an id or any URL with `/comments/<id>/` in it and fetches **every**
comment (the comment tree, not the 100-row search; see `reddit-mining`). The tally prints
the archived comment count against the count the post reports; removed and bot comments
are dropped, so say "49 readable of 70 archived" when they differ.

## A subreddit over a window

```bash
python3 scripts/reddit_pull.py --subreddits restaurateur --after 2026-10-01 --before 2026-11-01 \
  --top 0 --comments 10 --comments-for 25 > window.json
python3 scripts/reddit_tally.py digest window.json --top 10
```

This ranks threads by score plus comments, gives each one's highest-scored answer, and
lists numeric claims across the window.

## Writing the digest

Three sections, a few bullets each, every bullet ending in a permalink from the tally:

- **Decisions / consensus**: what the top answers agree on, and what the OP said they did.
  Say "the top 3 answers by score" rather than "everyone"; the score is right there.
- **Claims**: from the "claims with a number" list. A claim on Reddit is one person's
  report, so attribute it ("one owner reports sales down 30% a year"), never restate it as fact.
- **Disagreements**: from the pushback list, with what was being pushed back on.

If the thread is an ad dressed as a question (the top answer often says so), lead with that.
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

`--thread https://www.reddit.com/r/smallbusiness/comments/1wu3z5m/` then `digest --top 4`:

# Is emailing a PDF invoice actually why I keep getting paid late?
r/smallbusiness, 2026-09-30, score 0, https://reddit.com/comments/1wu3z5m
Readable comments: 49 of 70 archived (rest removed, deleted or bot; post reports 67); distinct commenters: 19; top-level answers: 15.

**Question (verbatim, opening):** "Is emailing a PDF invoice actually why I keep getting paid late? Genuine question because I'm about to change how I bill. Right now I email a PDF like everyone else. It lands in an inbox with 400 other emails, I have no idea if they opened it, and 3 weeks later I'm writing "hey just floating this back to …"

## Top answers by score

| # | score | replies under it | answer (opening, verbatim) | link |
|---|---|---|---|---|
| 1 | 15 | 3 | "Bullshit This is an ad for your invoicing app" | https://reddit.com/comments/1wu3z5m/_/pd0e9so |
| 2 | 8 | 1 | "Please tell us all about your invoice, payment, AI, software tool that will now look like the best option ever!" | https://reddit.com/comments/1wu3z5m/_/pd06jb8 |
| 3 | 7 | 5 | "The standard in our industry for many years is sending Quickbooks Payments invoices with a link to pay. The pdf is attached to the email so it can be printed. …" | https://reddit.com/comments/1wu3z5m/_/pcztdbn |
| 4 | 1 | 5 | "I send pdfs. Many of my clients have asked that I copy someone in the AP department and that person is who actually processes the payment and mails out the …" | https://reddit.com/comments/1wu3z5m/_/pd003v2 |

## Pushback: 1 replies open by disagreeing

- "nah nobody mails me checks, its Zelle or a bank transfer. the wait isn't the payment method, its them getting around to it. invoice sits …" (score 1, https://reddit.com/comments/1wu3z5m/_/pd02wrf) replying to "We're in retail so this is how we pay most vendors and how we bill our customers. Charge …"

## What the original poster said or decided: 22 OP comments, 0 decision/update sentences

## Claims with a number: 20 sentences (top by score)

- "Charge is only 1% for ACH/bank payments." (score 1, https://reddit.com/comments/1wu3z5m/_/pd01s52)
- "invoice sits unopened for 2 weeks then they pay in 30 seconds and 1% ACH still means a $2,000 invoice costs you $20 to collect." (score 1, https://reddit.com/comments/1wu3z5m/_/pd02wrf)
- "maybe, but they didn't open it for 2 weeks." (score 1, https://reddit.com/comments/1wu3z5m/_/pd08ag9)

The written digest on top of it:

- **Consensus:** the two highest-scored answers (15 and 8) say the post is an ad for the
  poster's own invoicing app ([1](https://reddit.com/comments/1wu3z5m/_/pd0e9so),
  [2](https://reddit.com/comments/1wu3z5m/_/pd06jb8)). The third (7) says the norm in
  their industry is an invoice with a pay link and the PDF attached
  ([3](https://reddit.com/comments/1wu3z5m/_/pcztdbn)).
- **Claim:** one reply works the fee: 1% ACH on a $2,000 invoice is $20 to collect
  ([link](https://reddit.com/comments/1wu3z5m/_/pd02wrf)).
- **Disagreement:** 1 reply pushes back that the delay is the payer getting around to it,
  not the payment method ([link](https://reddit.com/comments/1wu3z5m/_/pd02wrf)).
