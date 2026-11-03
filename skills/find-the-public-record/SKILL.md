---
name: find-the-public-record
description: Work out which public record actually settles a question about a local market or a property anywhere in the US — county parcel GIS, recorder, Census business patterns and ACS, BLS series, state registries, licences, inspections — how to reach it directly, what it will and won't answer, and the traps that return a plausible wrong number. Use before researching a local market, or when someone asks "where would I find what this building sold for", "who really owns this", "is this neighborhood growing". Via the free Brick & Mortar MCP server's data_source_atlas tool.
---

# Find the public record

**In the owner's words:** "Where would I even look up what that building sold for?" · "Who
actually owns this strip mall?" · "How do I know if this part of town is growing?"

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

`data_source_atlas` — required `question` (in plain words, not a dataset name) and `place`
("Hennepin County, MN", "Wichita, KS", "the 78704 ZIP" — the state matters: it decides whether
sale prices exist at all); optional `already_tried` so the plan doesn't repeat a dead end.

## What comes back

A **research plan, not research** — the tool makes no outbound calls and holds no data. Keys:
`research_procedure`, `output_schema` (`question_restated`, `families`, `jurisdiction`, `plan`,
`cannot_be_answered_publicly`, `traps_that_apply`, `confidence_after_plan`), `quality_rubric`,
`caveats`. Execute the plan yourself: go to the named administrative record, not an aggregator
that resells it.

The procedure: restate the question as the fact that would settle it and its family (property,
market structure, price/wage/cost, trajectory, operations/reputation); **establish the
jurisdictional fork first** (county, state, disclosure vs. non-disclosure); go to the county's
parcel layer directly (usually an Esri ArcGIS REST service, free, no key); use the Census APIs
for counts; BLS for prices and wages; then state and local records. Write the plan as concrete
pulls — source, endpoint, identifier, the field that settles it, what to do if it comes back
empty — and state what the public record cannot answer.

## Rules

- **Non-disclosure states have no sale price on the deed.** Say so and pivot to what exists
  (assessed value, the assessor's ratio study) instead of an estimate that reads like a record.
- **Name the record, cite the pull, date it.** A vendor figure (Zillow, CoStar) is a product,
  not the administrative answer.
- **"No public record answers this" is a valid, valuable answer.** Revenue, margin, private
  lease terms and private-sale terms are not public anywhere.
- The dangerous failure in public data is never an error — it's a plausible wrong number.
  Establish coordinate system and units first; don't trust ArcGIS `esriSpatialRelTouches` or the
  `units` parameter on distance queries (both measured unreliable); sum assessed value across
  every parcel a building sits on.
- For the seven-county Minneapolis–St. Paul metro the records are already loaded — use
  twin-cities-property-records instead of planning a trip to the county portal.
