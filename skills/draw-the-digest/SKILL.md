---
name: draw-the-digest
description: A recurring report (daily metrics email, weekly digest, morning summary) gets drawn: tiles for 'did anything happen', a strip for 'is this normal', a funnel for 'where do we lose them'. Keep a plain-text part for lock screens. Use when building or fixing a metrics email, status digest, or dashboard summary that's hard to read.
---

# Draw the Digest, Don't List It

**Rule.** Something that arrives unbidden every morning gets three seconds. Correct numbers in a list don't
survive three seconds.

**Why.** A daily email had eleven labelled figures, each with a 7-day count in brackets. All correct. *"really hard
to grok… maybe some visuals instead?"* Legibility was the problem, and adding correct lines made it worse.

**How to apply.**
- Tiles: did anything happen today. Strip (sparkline of recent days): is this normal. Funnel: where people drop.
- A quiet day keeps the strips and drops the funnel; four zero bars teach people to archive the mail.
- Two strips of the same measure from two trackers make outages visible.
- Names to act on stay as words; only magnitudes get drawn. Keep the plain-text part.

**Related:** `find-the-spread-before-drawing`, `colour-tells-the-story`
