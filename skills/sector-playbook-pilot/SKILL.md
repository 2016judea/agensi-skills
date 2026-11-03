---
name: sector-playbook-pilot
description: Run a two-issue cold direct-mail pilot into a new small-business sector — Issue 1 free (the omission hook: what AI is doing in OTHER sectors, "we skipped yours on purpose"), Issue 2 a paid teaser that names the sector's forces and withholds the moves, selling one shared playbook PDF through a QR to a payment link. Covers scraping the target universe, researching and caching the sector, building the playbook and payment link, both mailers, and one combined print file. Use for a cold, sector-wide mail test where every recipient faces the same problems.
---

# Sector playbook pilot (two-issue cold mail)

Issue 1 earns attention for free. Issue 2 sells **one shared playbook**: the same content for every
recipient, because everyone in a young or fast-moving sector faces the same forces and misses the
same forward-looking fixes. Works best where owners are open-minded and the market is moving.

## The model

| | Issue 1 (free) | Issue 2 (paid teaser) |
|---|---|---|
| Content | what's happening in OTHER sectors, deliberately not theirs | their sector's 3 forces, named but unsolved |
| Hook | omission: "we skipped your industry on purpose" | "we wrote down exactly what to do; one scan away" |
| Back page | a "one more is coming" line | QR -> payment link -> the playbook |
| Gives away | real value, builds curiosity | nothing actionable: the moves are the paid value |

**The omission is the engine.** Issue 1 walks them through everyone else's story and says it skipped
them on purpose. Issue 2 proves you know their sector cold (name the forces) and withholds the
solutions.

## Build order (each step feeds the next)

1. **Scrape the target universe.** Places text search per city, dedupe, save a CSV. A new sector may
   have fewer businesses than your cap: the list is often all of them, not a sample. Know the real count.
2. **Research and cache the sector** (`sector-enrichment`): economics, the shake-out thesis, the forces,
   5 moves. Real numbers only.
3. **Build the playbook.** One PDF: ~5 moves (hook -> why and what it's worth -> what to do -> timeline)
   plus a 90-day order of operations. Host it where a payment can hand it over (a signed or
   post-checkout download link; with Dropbox, **upload through the API**: copying into a synced folder
   doesn't reach the server in time to share). Create one payment link at your price that redirects to
   the download.
4. **Build both mailers.** Same content for all; only the address block varies.
5. **Combine for print**: all Issue 1s, then all Issue 2s, in the same business order, as one PDF for the
   print shop.

## Done when

| Task | Done when |
|---|---|
| Target list | scraped, deduped, tagged by municipality; real count known |
| Sector data | cached, validates, uses real numbers |
| Playbook | PDF renders; download link resolves; payment link active, right amount, redirects to the PDF |
| Mailers | both render; address block has full street and city/postcode; the Issue 2 QR decodes to the payment link |
| Print batch | one combined PDF, Issue 1 first half, Issue 2 second half, right page count |

## Common mistakes

- **Inventing snapshot numbers.** Scrape first.
- **Forcing a rating-gap story.** A young sector can be uniformly highly rated (80% at 4.5 stars+); ratings
  won't differentiate. Lead with the real thesis (regulation, margin, tax).
- **Leaking the solutions in Issue 2.** Name the forces (public knowledge, proves expertise); keep the moves
  paid.
- **Promising personalisation.** Issue 2 is shared: say "your industry", never "your numbers".
- **Mailing law.** Include a real return address and honour any opt-out you offer.

Pre-test both issues on a persona panel (`simulate-campaign`) for copy defects, then measure real QR scans
and payments; a panel doesn't predict response.
