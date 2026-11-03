---
name: broker-prospecting-dossier
description: Build a first-touch prospecting dossier a commercial real estate broker uses to win a property owner's NEXT transaction before any relationship exists — owner identity, the full portfolio enumerated by mailing-address clustering, allocation, a ripeness-to-sell ranked next move, a trade-up, and a call sheet (who to ask for, the opening line, three facts). Use when a broker wants to prospect owners in a market, especially owners already transacting, or asks "who do I call and what's the pitch".
---

# Broker prospecting dossier (pre-listing, first touch)

Different moment from `cre-broker-brief` (post-listing): this answers *"who do I call, and what
pitch earns the meeting?"* The bar: a broker reads it and can dial the owner knowing who to ask
for, why they'd sell, and the one move to pitch.

## The angle: a deal thesis, not a profile

Not a neutral owner report. A **targeted next-move recommendation**, with the portfolio as a
supporting exhibit. The broker is not a wealth manager; every exhibit drives toward one
transaction. The business model it serves: commission on the next leg(s), sell-side on the
recommended asset plus buy-side on the exchange (e.g. a 1031) upleg.

Six beats: **Owner -> Portfolio / allocation (the map) -> Timing proof (already selling?) -> The
Move (which cluster to sell, ranked) -> Trade-up (a real upleg + scattered-to-scale logic) ->
Call Sheet** (who, opening line, three facts).

**Warmest targets: owners already in motion.** A competitor's live listing means the exchange
clock is coming. Use that listing as *timing proof*, not as the recommendation.

**Next-move selection = ripeness-to-sell rank, excluding what's already listed.** Score remaining
holdings or clusters on management drag (scattered small buildings = high), concentration,
submarket heat and hold length. Recommend the top one.

## The data engine

| Need | Typical source |
|---|---|
| For-sale listings (find movers, find the upleg) | a CRE listings API or site with terms that permit it |
| Owner identity + per-parcel value | the county assessor app (address -> owner, mailing address, income value) |
| **Owner -> full portfolio** (make-or-break) | a paid property-data API that can search by **mailing address** (most have no owner-name search). Use free count queries first, then pull. |
| Submarket caps, expense ratios | grounded web search over brokerage research |
| Imagery | static map with a marker per parcel (the hero chart) + Street View |

Owner-to-portfolio is often walled to every free source in non-disclosure states (no owner search
in the county app, paywalled deeds, bot-walled state registries). Decide up front which of
*free / hands-off / complete* you are giving up.

### Mailing-cluster guard (do not skip)

A cluster of parcels sharing a mailing address is a true portfolio only when the owner **mails to a
property they own** (owner-operator tell). Flag or drop:

- **Suite / PM mailings** (`Ste`, `Suite`, `#`, an office tower): unrelated entities sharing a
  mailbox, often across states.
- **Government and institutional owners** ("City of ..."), and anything with thousands of parcels.
- **Clusters over ~50 parcels**: probably a property manager or agent; verify before treating as one
  owner.
- **Homogeneity**: keep one target metro and the target asset type; drop off-type parcels.

Best targets: a small-multifamily owner-operator mailing to one of their own buildings.

## Valuation firewall

Bulk property APIs' value fields (estimated value, assessed value, portfolio value) are often
badly wrong for small multifamily (one run reported a whole portfolio at a fraction of a single
building's asking price). **Use the API for enumeration and attributes only** (units, type,
lat/lng, mortgage flags). Every dollar shown comes from (1) a real listing ask, (2) the county's
appraised or income value, or (3) NOI ÷ market cap, labelled illustrative. Never let an AVM touch a
number the broker shows.

## Deliverable

Branded HTML -> PDF, charts from real numbers only, images embedded. Standard set: the **scatter
map** (every parcel; "you own 30 scattered fourplexes" in one picture), door/value allocation bars,
valuation anchors, a scattered-vs-scale cap and expense-ratio comparison, and the **Call Sheet**
card. Version every revision.

## Reader QA (required)

A self-grade passes the owner-framing failure, because the model grades its own homework. Before
done, hand the draft to a different reader: a broker persona (see `simulate-campaign`). If it says
the dossier drifts into owner advice, reads as fluff or the numbers look suspect, fix the quoted
lines and re-run. Owner-facing operational advice anywhere is an automatic rewrite.

## Done when

- Passed the broker reader-QA.
- One move, not a profile. Broker first-touch voice throughout.
- Every figure real; AVMs firewalled; caps labelled illustrative; sources footnoted.
- The honest downside is surfaced (a competitor holds the current listing; the scattered portfolio's
  higher headline cap is eaten by its expense ratio).
- Call Sheet present; scatter map verified.
- Owner entities are businesses; if a parcel's owner is an individual, use the record only for the
  call sheet the broker needs and never publish it.
