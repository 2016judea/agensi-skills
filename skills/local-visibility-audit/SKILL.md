---
name: local-visibility-audit
description: Find out why a local business doesn't show up when people search "near me" — a scored, bottom-up checklist of its Google Business Profile category, name/address/phone consistency, profile completeness, map-pack position against named competitors, and website fundamentals, with a fix order. Use when an owner says "we don't show up on Google", "why does the place down the street come up first", or before redoing a listing. Any US business, via the free Brick & Mortar MCP server's local_visibility_audit tool.
---

# Local visibility audit

**In the owner's words:** "Nobody finds us on Google Maps." · "Why does the other shop show up
and we don't?" · "I'm redoing our listing — what should I fix first?"

## Connect the server (once)

The tools live on the free Brick & Mortar Small Business Intelligence MCP server:
`https://brickandmortar.dev/mcp` — Streamable HTTP, **no account, no key, no OAuth**, read-only.

- **Claude Code:** `claude mcp add --transport http brickandmortar https://brickandmortar.dev/mcp`
  (add `--scope user` to have it in every project). Check with `claude mcp list`.
- **Claude.ai / Claude Desktop:** Settings → Connectors → Add custom connector → paste the URL.
- **ChatGPT:** search the app directory for "Brick & Mortar Public Records".
- **Any other MCP client** (Cursor, VS Code, Windsurf…): add a remote HTTP server with that URL.
- Raw HTTP: POST JSON-RPC with `Accept: application/json, text/event-stream`; the reply is an SSE
  `data:` frame. The edge refuses a bare script User-Agent, so send a browser-style one.

Install docs: https://brickandmortar.dev/connect/

## Call

`local_visibility_audit` — required `business_name` and `city_metro`; optional `category`
(narrows which map-pack searches are the right ones to run).

## What comes back, and the one way to get it wrong

This tool **fetches no data**. It returns a research framework with these keys:
`framework` (the method, named), `research_procedure` (numbered steps), `output_schema` (the
shape of the finished deliverable), `quality_rubric` (`good_looks_like`, `common_failure_modes`)
and `caveats`. **You execute the procedure with your own web search, then write the deliverable
in the `output_schema` shape and check it against the rubric.** Handing the framework back to
the user as though it were the finding is the failure this skill exists to prevent.

The method is a **gate-and-rank ladder**: Eligibility (right primary category, consistent
name/address/phone, no duplicate listing) gates Google's three documented local ranking inputs —
Relevance, Distance, Prominence — checked in that order. A failure low on the ladder caps
everything above it, so great reviews never paper over a wrong primary category.

The procedure has you: confirm exactly one active listing; compare the true offering with the
listing's primary and secondary categories; build a NAP matrix across the listing, the site,
Yelp, Facebook, Apple Maps and Bing Places; inventory profile completeness (hours, holiday
hours, photos, posts in the last ~90 days); read reviews as ranking inputs against 2–3 peers;
run the 2–3 searches a stranger would actually type and record pack position; audit on-page
local basics. **Score every item pass / partial / fail with a one-line evidence note before
writing any narrative** — the scored checklist is the primary deliverable.

Fix order follows the gates: category and NAP first, then completeness, then prominence.

## Rules

- A map-pack search is a **snapshot** — results vary by location, device and time. Say so.
- The owner's dashboard (Insights, suspension history) isn't visible from outside.
- A NAP mismatch on an aggregator the owner doesn't control is fix-and-monitor, not same-day.
- This shows whether they *can* be found, not why a customer chose someone else — that's
  `review_intelligence`.

## Finish

- Check the draft against `quality_rubric.common_failure_modes` before answering.
- State the `caveats` that applied. What public signal cannot show is part of the answer.
- Date-stamp anything that moves (ratings, review counts, prices, multiples).
- For a client-ready document, pass your finished write-up(s) to `compose_report`
  (`business_name`, `audience`: owner | broker | buyer | investor | general,
  `completed_analyses: [{tool, summary}]`). It returns the section order (verdict first), a
  contradiction ledger across analyses, and citation rules; you write the report. Pass your
  **finished** analysis as `summary`, never the raw framework.
