---
name: vertical-market-agent
description: Build a chat agent that knows one industry in one metro better than any general model because it carries a precomputed digest of real public records (or a mined review corpus) and can pull live records mid-conversation — finding the moat, building a byte-stable substrate, enumerating what the records can't, the data traps that produce plausible wrong numbers, deterministic math in tools, measured prompt cost and cache TTL, shipping as an ad destination, an off-sector ending, and a precomputed spatial "what is this next to" layer. Use when building a vertical AI agent grounded in records rather than general knowledge.
---

# Building a vertical market agent

A chat agent that beats a general model in one industry and one metro, because it carries a
precomputed digest of real data and can pull live records while it talks. **Done** = live on a URL,
answering with figures that trace to the substrate, refusing to invent the ones it doesn't have, and
verified in production with real probes (not a local test).

## Step 0: two questions the owner answers

1. **Which metro, and why that one?** Pick where you already have fieldwork or data that is
   literally true there. Mine a metro, *then* advertise there.
2. **Will it be advertised, and is it linked?** Four engineering decisions hang off this (pixel,
   cache TTL, vanity URLs, attribution). See Step 7.

## Step 1: find the moat before writing code

Two kinds: a **corpus** you mined and own (e.g. tens of thousands of reviews), or a **join** (a live
for-sale feed against county parcel, valuation and tax records: two free sources nobody bothers to
put together). Paid bulk enumeration often fails (credits gone, owner search absent).

**When bulk enumeration is walled, the entry point is the constraint, not the data.** A county app
that answers for any address but lists none is fine once you enumerate addresses elsewhere (Step 3).

**Non-disclosure states are an opportunity**: nobody has sale comps, including competitors, so the
county's own arithmetic organised well becomes the best anchor.

## Step 2: build the substrate

A frozen JSON digest injected server-side into the system prompt on every message.

- **Check panel size first** on a review-corpus agent. "Where you rank among places like yours"
  needs ~50+ businesses with 50+ reviews each. Below that, don't ship a ranking.
- **A model-written sector profile is not substrate.** Loading prose a model wrote tells the model
  what it already knows and creates zero moat. Substrate is *measured*.
- **Missing data is a backlog, not a blocker**: if you own the means to mine a panel, mine it.
- **Check the licence before mining.** Some sources' data can't be redistributed, which decides
  whether a mined panel can ever be a download.
- **Every block carries an `_interpretation`**: 2-4 sentences on what it means and how a professional
  uses it. Highest value per byte; it's the difference between reciting and reasoning.
- **Byte-stable output**: `sort_keys=True`, total sorts with ties broken on a unique field, no
  timestamp except `generated_on`. One varying byte re-bills the cached prefix on every message.
- **Layer, and let better layers supersede** older ones; two blocks giving different numbers for one
  question make the model arbitrate mid-answer. Supersede at **sub-key** level when a block is mixed.
- **Archive full, ship compact** (`.compact.json` twins), falling back to the archive if a twin is
  missing.
- **Scrub personal emails** from merged research: at ad scale the model turns one civil servant's
  inbox into your outbound channel. Department + phone says the same.

## Step 3: enumerate what the records can't

A thin listing feed sees almost nothing. **Places "search nearby" on a grid of small circles**, then
join each hit to the county record (one run: 307 complexes -> 208 matched parcels -> 9,736 units).

- Small circles (~3.5km on a ~3.9km grid): the API caps results per call, so one metro-wide query
  silently returns only the best-known places.
- **Let the public record decide what something is**, not the source you enumerated from (a
  directory "apartment" that the county records as a care facility; a used-car lot tagged
  multifamily).
- In a market where nothing is listed, the people worth talking to are the ones not selling.

## Step 4: the data traps (read twice)

Every bug here produced **a plausible wrong number, never an error.** Budget QA time against a
known-correct fixture.

0. **Re-query the source before planning around its description.** A layer name in a doc is a
   hypothesis. Read the service's metadata (for ArcGIS `?f=json`, `editingInfo.dataLastEditDate`)
   and real field *values* before trusting a field name.
1. **Verify against something you know.** A building known to have 36 units parsed as 10: one
   fixture caught the worst bug. Better still, send a sample of your output back to the publisher's
   own API in a different coordinate frame and compare.
2. **Watch for inversions**, not just outliers: small properties valuing higher per door than large
   ones means the parser is wrong, not the market.
3. **Make the data check itself.** Where a cross-check exists (sqft per unit), compute both readings
   of an ambiguous field and let the plausible band choose; if neither fits, flag and exclude.
4. **Dedupe before aggregating.** A feed listing one property under every asset type it fits: 623
   rows were 206 properties.
5. **Cache RAW, never parsed**, or a parser fix means re-crawling a small county's server.
6. **Address formats differ from the records index.** Abbreviate directions and drop the suffix; a
   variant ladder recovered ~half the misses.
7. **Label small samples with their n**; sometimes the thinness is the finding.
8. **On a review corpus, read the MATCHES, never the share.** Run every taxonomy regex against real
   1-3 star text and read what it matched. **The sector's service verb is often a harm verb**: an
   "injury" pattern on `cut (me|my)` matched 10.7% of salon complaints, mostly "paid $40 to cut my own
   hair". Check `drill` (dental), `pull` (towing), `strip` (detailing), `break` (glass), `shave` /
   `clip` (barbers, grooming), `stick` (phlebotomy). And a theme nobody raises stays out.
9. **The publisher's vocabulary is not the buyer's.** A county's "arterial" class may be the freeway
   network, where nothing fronts, while the commercial streets a broker means are "collectors". List
   each bucket's contents before mapping, and name fields for what they contain.
10. **A shared schema shares column names, not conventions.** Across counties one field can carry four
    classification systems, `-9999` vs `0`, a third homestead value. Census each field per county; treat
    a zero from one county as a query bug until proven; prefer derived tests (building value = 0 and
    land value > 0 for vacancy).
11. **One name is several things** (a freeway and its frontage road share a name). Return the
    alternatives and make the model say which it used.
12. **Things that "should" meet once meet many times** (two roads crossing at six places). Averaging the
    points lands in a field; cluster, keep each location, pick by a stated rule.
13. **A derived total silently drops rows you never computed.** Ship the coverage count beside any total
    with partial inputs, and make it read as a floor.

## Step 5: deterministic math goes in a tool, never the prompt

DSCR, IRR, cash-on-cash, dosages, tax: a **tool**, computed, returning its assumptions and warnings. A
model's arithmetic is *plausibly* wrong (a 1.19 DSCR that's really 1.09 goes to a lender). This forces
a real agent loop (stream -> run tools -> feed back -> stream), including `pause_turn` and `max_tokens`
handling.

## Step 6: prompt cost, measured

- **Count tokens with the API.** Dense JSON runs ~2.4 bytes/token, not ~4.
- **Enforce a byte/token ceiling in a test**: shipping the archive instead of the compact twin has no
  symptom except the bill.
- **Cache TTL follows traffic.** Sparse, hand-shared: the 5-minute default (a 1h write is a surcharge
  nobody reuses). Continuous paid traffic: 1h, because visitors share the prefix.

## Step 7: shipping

- **Derive the page from one generator**; every replacement asserts its anchor exists, and guards
  check both directions (removed content is gone *and* the feature survived).
- **If it's an ad destination**: vanity URLs as **temporary** redirects (permanent ones get cached by
  the ad platform), verifying the query string survives; a pixel event name per campaign; cache TTL
  1h; and **attribution pinned to `sessionStorage`** on the landing hit and carried on every turn (not
  `localStorage`, or next week's organic visit gets credited to today's ad).
- **Verify the deploy state, not the build log**; a serverless function cap or an untraced file can
  fail behind a green log. Import data files statically so the bundler includes them.

## Hard rules for the prompt

1. **Never invent a number.** Substrate, a tool call actually run, or a flagged estimate.
2. **Never present a public-record value as a market value.** Say which one you're giving.
3. **State the coverage boundary in the tool description AND the prompt** (which counties). A rule in
   one place gets routed around.
4. **Public record one at a time, not as a list.** Owner lookup for the property asked about is fine;
   bulk name-and-address rosters can breach state open-records law on commercial use.
5. **Re-check what the prompt calls impossible.** A confident falsehood about what can't be known is
   worse than the gap.

## Research agents for context layers

Give parallel research agents a **token** budget (and the 2.4 bytes/token ratio), tell them to **cut
the figure rather than the caveat**, and expect them to correct your earlier work.

## Step 8: the off-sector ending

Some visitors aren't its user (a thrift store in a restaurant agent). The default "I don't have that"
loses the best signal you'll get: a real owner naming the sector to build next.

- A `flag_out_of_scope(sector)` tool: the client renders three **tappable** options; a
  `submit_feature_request` tool files the tap.
- **Everything in the first reply**: median session depth is one turn.
- **Don't inventory what the agent carries instead** (one cut took a reply from 1,275 to 124 chars).
- **Options are client-rendered, never a numbered list in prose** (a bare "2" can trigger skill 2).
- **Tell the model where options render**; it can't see the client.
- Map options to universal capabilities so a filed request names *a capability for a sector*.

## Step 9: the spatial layer ("what is this next to")

- **Find the county's ArcGIS Online org**, not its WAF-blocked GIS host; hosted services often serve
  anonymously. Request geometry in the layer's **native spatial reference**.
- **When two sources meet, request the second in the first one's frame** (`outSR`), and **assert the
  extents overlap** before emitting rows: a frame mismatch intersects nothing and reports "every parcel
  unzoned". In DuckDB, `ST_Transform` needs `always_xy := true` or returns `POINT(inf inf)` silently.
- **Zoning by centroid; split-zoning needs a share threshold** (>5% of the lot), comparing districts
  not polygons. A bare intersects called 37% of parcels split; the threshold gave ~4%.
- **A city's zoning codes are that city's.** The same code means different districts next door; ship
  the city and the published name with every code.
- **Precompute offline, ship a geometry-free index, add no API route**: county GIS -> DuckDB spatial
  mirror -> one committed JSON index; runtime does lookups and haversine only. A failing spatial
  dependency degrades to an empty neighbour list, a confident wrong answer. Validate the index on load
  and **throw**.
- **An inequality anywhere in a spatial join demotes the spatial predicate to a post-filter**
  (`ON a.id < b.id AND ST_Intersects(...)` tested ~29 billion pairs). Let the predicate stand alone,
  `EXPLAIN` for `SPATIAL_JOIN`, emit keys, then dedupe: 7 minutes unfinished became 19 seconds.
- **Scope the shipped index** to what the buyer transacts in plus immediate neighbours, and flag
  "context" parcels that carry less data.
