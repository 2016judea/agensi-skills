---
name: broker-diligence-prep
description: Prepare to buy (or broker) a small business before the seller shares financials — SDE framing and the add-backs to challenge, a freshly researched and date-stamped category multiple, an asking-price sanity check, a public red-flag scan (reviews, ownership change, lease, licences, discount reliance), and a prioritized list of questions for the seller. Use when someone says "I'm looking at buying this restaurant", "is $650K reasonable for this salon", "what should I ask the seller". Any US metro, via the free Brick & Mortar MCP server's broker_diligence_prep tool.
---

# Broker / buyer pre-diligence

**In the buyer's words:** "This taproom is listed at $650K — is that crazy?" · "What do I ask
the seller before I make an offer?" · "What could be wrong that the listing won't tell me?"

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

`broker_diligence_prep` — required `business_name` and `city_metro`; optional `category`
(sets which multiple range applies) and `asking_price` (a number; used to sanity-check against
the range, never to validate it).

## What comes back, and the one way to get it wrong

This tool **fetches no data**. It returns a research framework with these keys:
`framework` (the method, named), `research_procedure` (numbered steps), `output_schema` (the
shape of the finished deliverable), `quality_rubric` (`good_looks_like`, `common_failure_modes`)
and `caveats`. **You execute the procedure with your own web search, then write the deliverable
in the `output_schema` shape and check it against the rubric.** Handing the framework back to
the user as though it were the finding is the failure this skill exists to prevent.

The method is **SDE-first triage**, three lenses in a fixed order, because running them out of
order is how buyers overpay:

1. **Earnings quality** — what seller's discretionary earnings would plausibly need added back
   (owner's draw, owner's insurance, vehicle, one-offs) *before* any multiple is discussed. Every
   add-back is a hypothesis to verify against receipts.
2. **Deal plausibility** — research a **current** category multiple (recent brokerage market
   reports, trade associations), date-stamp it, adjust for owner-dependency, lease and revenue
   trend, then call the ask "plausible", "rich", "aggressive" or "insufficient data". Never a
   valuation.
3. **Public risk surface** — review trend and the most recent low ratings, ownership or key-staff
   change language, address tenant turnover and lease signals, health/liquor/licence records,
   discount-platform reliance, operational strain (hours not matching reality).

It also underwrites the metro (employment direction) and, if real estate is in the deal, pulls
the county's own record on the parcel rather than accepting the seller's number. Output ends
with **seller questions built from the specific gaps found**.

## Rules

- **This is a pre-diligence screen, not diligence, an appraisal or a valuation.** Nothing here
  goes into a letter of intent as a verified figure.
- The absence of a public red flag is not evidence of a healthy business.
- A franchise unit's economics live in the franchise agreement; ask for it.
- A recorded sale price is a transaction, not an appraisal; assessed value is usually below market.
- In Minneapolis–St. Paul, pull the parcel with `twin_cities_lookup` (twin-cities-property-records).

## Finish

- Check the draft against `quality_rubric.common_failure_modes` before answering.
- State the `caveats` that applied. What public signal cannot show is part of the answer.
- Date-stamp anything that moves (ratings, review counts, prices, multiples).
- For a client-ready document, pass your finished write-up(s) to `compose_report`
  (`business_name`, `audience`: owner | broker | buyer | investor | general,
  `completed_analyses: [{tool, summary}]`). It returns the section order (verdict first), a
  contradiction ledger across analyses, and citation rules; you write the report. Pass your
  **finished** analysis as `summary`, never the raw framework.
