---
name: corpus-signal-mining
description: Mine a labeled corpus for co-occurrence patterns (association rules / market-basket analysis) to learn which problems bundle together and which cheap signals predict hidden ones — and backtest any derived score, ranker or selector against a dumb baseline before wiring it into a pipeline. Use when proposing a new lead score, ranker or signal, exploring "what should we sell" bundles, or whenever a clever heuristic is about to ship without proof. The rule it enforces: never ship a heuristic that doesn't beat a baseline on labeled data.
---

# Corpus signal mining (+ the validate-before-ship rule)

Two jobs, one discipline. If you hold a labeled corpus (businesses, customers, deals, tickets;
each a basket of tags with an outcome you care about), you can (1) mine patterns in it and
(2) **test any heuristic derived from it against a baseline before trusting it.**

The expensive mistake this prevents: wiring a clever-looking score into a pipeline that does
not beat a dumb baseline.

## Part 1: mine co-occurrence

Each **record is a basket**, its **tags are items**. Rules `{A, B} -> C` with **support** (how
often), **confidence** (how reliable), **lift** (how much more than chance).

```bash
# baskets.jsonl: {"id": "...", "items": ["no_website", "thin_reviews", ...]}
python3 scripts/mine_rules.py baskets.jsonl --min-support 6 --min-conf 0.65 --min-lift 1.15
```

Use it for **bundling** (clusters that co-occur at high lift are real bundles to sell together)
and **expected-gap priors** (records with A and B probably also have C, so check C first).

**What lift does NOT tell you: how much.** Association predicts *which* tags travel together,
never the size of the outcome. In practice the dollar size of an opportunity usually tracks the
size of the business, not its tag mix. Don't rank by rules.

## Part 2: THE RULE, backtest before you wire it in

Before any corpus-derived score goes into a pipeline (lead scoring, routing, prioritising),
prove it beats a baseline on labeled data.

1. **Cheap inputs only.** The score may use only what it will actually have at runtime. Using
   data you won't have live is leakage, and it will look brilliant.
2. **Define the label**: the outcome you're predicting (upside $, converted, replied).
3. **Three selectors**: `RANDOM` (floor), `BASELINE` (the dumb heuristic you'd otherwise use,
   e.g. "count of visible problems"), `YOUR_SCORE`.
4. **If the score is learned from labels, compute it out-of-fold**: k-fold (5 is fine), learn on
   the training folds, score the held-out fold, repeat. Then every row carries an honest score.
5. **Metric**: precision@K (share of top-K picks in the true top tercile) and Spearman rank
   correlation, averaged over random tie-breaks.
   ```bash
   python3 scripts/backtest.py rows.jsonl --baseline count_problems --score my_score --k 12
   ```
6. **Ship only if it clearly beats BASELINE, not just RANDOM.** Beating random is not a win.

Re-run per segment as data grows: a rule that fails across sectors can work inside one (less
size variance).

## Worked example (a negative result, on record)

Hypothesis: an association-rule "predicted upside" pre-screen would pick richer targets than a
size/review heuristic. Backtest on 95 labeled businesses:

| selector | precision@12 | spearman |
|---|---|---|
| RANDOM | 38.6% | 0.01 |
| BASELINE (count of visible problems) | **43.3%** | 0.11 |
| RULES (predicted-upside score) | 42.5% | 0.16 |

**Did not ship.** It lost to the naive baseline on precision; both barely beat random. Upside was
driven by business size, which the baseline already captured through review volume. What
survived: the rules as a prior handed to a human/LLM reviewer (faster, more consistent reviews)
and as the backbone for bundling (one cluster co-occurred at 1.7x lift).

## Sample size honesty

With under ~50 labeled rows, report the result as a probe, not a verdict, and say n. A 3-point
precision gap on 30 rows is noise.
