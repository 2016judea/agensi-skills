---
name: market-opportunity-scan
description: Decide whether and where a category has room in a city — saturation, demand leaking to other places or substitutes, and geographic or price-tier whitespace, with every "gap" run through a demand-support sanity check before it's called an opportunity. Use when someone asks "is there room for another dog daycare here", "where should I open my second location", "is this neighborhood underserved". Any US metro, via the free Brick & Mortar MCP server's market_opportunity_scan tool.
---

# Market opportunity scan

**In the owner's words:** "Is there room for one more?" · "Where should the second location
go?" · "Everyone drives to the suburbs for this — is that a gap?"

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

`market_opportunity_scan` — required `category` ("coffee shop") and `city_metro` ("Aurora, CO").

## What comes back, and the one way to get it wrong

This tool **fetches no data**. It returns a research framework with these keys:
`framework` (the method, named), `research_procedure` (numbered steps), `output_schema` (the
shape of the finished deliverable), `quality_rubric` (`good_looks_like`, `common_failure_modes`)
and `caveats`. **You execute the procedure with your own web search, then write the deliverable
in the `output_schema` shape and check it against the rubric.** Handing the framework back to
the user as though it were the finding is the failure this skill exists to prevent.

The method is **Saturation / Leakage / Whitespace**, three gap signals scored independently,
gated by a mandatory **demand-support sanity check**: an empty spot on the map is not evidence
of unmet demand — it may be empty for a reason. Each candidate must show enough population, an
income or spend proxy, and the absence of a structural reason it's empty before it may be
labeled an opportunity.

The procedure has you: define the category and its substitutes; size the trade area by visit
type; enumerate supply with searches from several points in the metro; compute density and
benchmark it against 2–3 comparable metros; read reviews for oversaturation (price wars) and
for unmet demand ("always booked", "had to drive to…"); map supply against population and
income by ZIP or neighborhood; check price-tier gaps; check near-term supply (permits,
"coming soon"); test the metro's employment base and how its last two downturns hit it; and
check whether anyone is already acting on the gap (new permits, registrations, licences).
Output: a ranked list with confidence set by how many **independent** signal types corroborate
each candidate, and a genuine-gap-vs-correctly-empty verdict for each.

## Rules

- **This is the most speculative of the tools.** Finding what exists is reliable; inferring an
  absence of adequate supply is not. Say how many signals back each call.
- State the vintage of every population or income figure; ACS estimates carry margins of error.
- Zoning and lease availability usually can't be settled by web search — flag them as checks.
- It describes market conditions, not whether a given operator can execute.

## Finish

- Check the draft against `quality_rubric.common_failure_modes` before answering.
- State the `caveats` that applied. What public signal cannot show is part of the answer.
- Date-stamp anything that moves (ratings, review counts, prices, multiples).
- For a client-ready document, pass your finished write-up(s) to `compose_report`
  (`business_name`, `audience`: owner | broker | buyer | investor | general,
  `completed_analyses: [{tool, summary}]`). It returns the section order (verdict first), a
  contradiction ledger across analyses, and citation rules; you write the report. Pass your
  **finished** analysis as `summary`, never the raw framework.
