---
name: competitor-landscape
description: Map who a local business really competes with in a category and city — true competitors vs. adjacent players vs. noise, a positioning grid, a saturation verdict and the whitespace. Use when an owner asks "who's my real competition", "is this town already full of coffee shops", "where do we fit", or someone opening or expanding asks "how crowded is this market". Any US metro, via the free Brick & Mortar MCP server's competitor_landscape tool.
---

# Competitor landscape

**In the owner's words:** "Who am I actually up against?" · "There are six salons on this
street — is it saturated?" · "Where's the gap nobody is filling?"

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

`competitor_landscape` — required `category` ("brewery taproom") and `city_metro` ("Denver, CO");
optional `radius_note` for a specific neighborhood or radius when the default trade-area logic
shouldn't apply.

## What comes back, and the one way to get it wrong

This tool **fetches no data**. It returns a research framework with these keys:
`framework` (the method, named), `research_procedure` (numbered steps), `output_schema` (the
shape of the finished deliverable), `quality_rubric` (`good_looks_like`, `common_failure_modes`)
and `caveats`. **You execute the procedure with your own web search, then write the deliverable
in the `output_schema` shape and check it against the rubric.** Handing the framework back to
the user as though it were the finding is the failure this skill exists to prevent.

The method is a **Three-Ring filter**: every candidate from the map search is sorted into
**Core** (true competitor), **Watch** (adjacent, worth monitoring) or **Noise** (shows up in
the same searches, isn't competing) using three tests — category, trade area, price tier.
Only the Core ring goes on the positioning grid and into the saturation count. Letting Watch or
Noise leak in inflates the competition and produces a false "saturated" verdict.

What you produce (`output_schema`): scope, candidate pool, core competitors, watch list, noise
excluded, positioning grid, saturation analysis (density per 10,000 residents with the
population source cited, review-count clustering, entry/exit churn), whitespace, and a ranking
by competitive threat with the single most dominant incumbent named.

## Rules

- **The trade area is set by the kind of visit**: convenience categories get a tight radius,
  destination categories a wide one. State the radius you used.
- **A saturation verdict cites at least two of the three signals** (density, clustering, churn).
- **Check operating status** — map results lag closures.
- Businesses with no website or that run on word of mouth are under-counted by map search; say so.
- This maps the field. To place one named business on the map, pair it with `business_teardown`.

## Finish

- Check the draft against `quality_rubric.common_failure_modes` before answering.
- State the `caveats` that applied. What public signal cannot show is part of the answer.
- Date-stamp anything that moves (ratings, review counts, prices, multiples).
- For a client-ready document, pass your finished write-up(s) to `compose_report`
  (`business_name`, `audience`: owner | broker | buyer | investor | general,
  `completed_analyses: [{tool, summary}]`). It returns the section order (verdict first), a
  contradiction ledger across analyses, and citation rules; you write the report. Pass your
  **finished** analysis as `summary`, never the raw framework.
