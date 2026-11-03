---
name: meta-ad-performance
description: Pull a performance read on live Meta (Facebook/Instagram) ad campaigns — per-ad spend, CTR, CPC and frequency, audience breakdown by age/gender and device, the Pixel event funnel, and paid Stripe conversions — and interpret it against benchmarks with rules for when to pause, scale or rewrite. Use after a campaign has run 2-5 days, or for "how are the ads doing", "any movement", or a kill / scale / pivot decision on a variation.
compatibility: >-
  Python 3. Read-only calls to the Meta Marketing API and (optionally) Stripe with the user's own tokens.
metadata:
  network-hosts: "graph.facebook.com api.stripe.com"
  network-purpose: "ad insights, Pixel stats and paid-charge counts"
---

# Meta ad performance

```bash
export META_ACCESS_TOKEN=... META_AD_ACCOUNT_ID=act_...
export META_CAMPAIGN_IDS=123,456 META_PIXEL_ID=789 LAUNCH_DATE=2026-01-15   # optional
export STRIPE_SECRET_KEY=... STRIPE_PRICE_CENTS=4900                         # optional
python3 scripts/meta_ads_report.py
```

Prints active ads (today and last 7 days), breakdowns per campaign, Pixel events since launch, and
paid charges at your price (paged, refunds excluded). Set `LAUNCH_DATE` to the real launch so test
traffic and test payments before it don't count.

## End every read with the funnel

```
Impressions -> Clicks (CTR) -> PageViews (Pixel) -> InitiateCheckout -> Purchases
```

| Step | Rate to compute | Rough goal |
|---|---|---|
| Clicks | clicks / impressions | see benchmarks |
| PageViews | should be close to clicks | a big gap = slow page or broken pixel |
| InitiateCheckout | / PageViews | >10% |
| Purchases | / InitiateCheckout | >30% |

## Benchmarks (small-business paid social, one set of campaigns; recalibrate to yours)

| Metric | Weak | Decent | Strong |
|---|---|---|---|
| CTR | <0.8% | 1-2% | >2.5% |
| CPC | >$3.00 | $1.50-3.00 | <$1.50 |
| Weekly frequency | >3.0 | 1.5-3.0 | <1.5 |
| InitiateCheckout rate | <5% | 5-15% | >15% |
| Checkout -> purchase | <20% | 20-40% | >40% |

## What to do

- **CTR < 0.8%** after 3+ days and 500+ impressions: a scroll-stop problem. Change the headline or
  image (see `meta-ads-launch` for the swap flow). Pause the weakest variation.
- **Good CTR, no InitiateCheckout**: the ad hooks and the page doesn't close. Re-read the page as the
  buyer.
- **Checkouts but no purchases**: checkout friction or price anchoring. Pay through it yourself in
  test mode; check which payment methods are enabled.
- **One variation dominates**: after 500+ impressions each, pause the rest and put budget behind it.
- **Frequency > 3 in week one**: audience too small; widen geo or interests.
- **After accepting any of Meta's suggestions**, re-check targeting automation, interests and budget.

## Reading the audience

Who clicks is not always who buys. A segment with lots of cheap clicks may be staff or family rather
than the decision-maker; a smaller, older segment can be the actual owners. Judge segments on
downstream events, not clicks.

## Hygiene

Wait 3-5 days and 500+ impressions per variation before concluding. Don't raise budget until a winner
is clear. Keep your own test visits out of the read.
