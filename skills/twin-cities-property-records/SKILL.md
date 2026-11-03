---
name: twin-cities-property-records
description: Answer a question about a Minneapolis–St. Paul property or market from joined public records instead of memory — what it sold for, what the assessor values it at, who it's billed to and what else they hold, what shares its lot line, contamination and storage-tank files, floodplain, licences, permits, 911 and 311 volume, SBA loans — and read a document the user brings (a P&L, a lease, a comp set, one claim) against those records. Use for any address or market question inside the seven-county Twin Cities metro. Via the free Brick & Mortar MCP server.
---

# Twin Cities property records

**In the owner's words:** "What did the building next door sell for?" · "Who owns this place
and what else do they own?" · "Is there a contamination file on the lot I'm leasing?" · "The
seller sent me this P&L — does it hold up?"

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

## Which tool

| Need | Tool | Arguments |
|---|---|---|
| One address, everything on file | `twin_cities_lookup` | `address` (include the city) |
| What can be answered | `twin_cities_datasets` | optional `about` ("sales", "who owns it") |
| Answer from one dataset | `twin_cities_records` | `dataset` (required), `scope`, `address`, `within_ft`, `columns` |
| Check their file against the records | `bring_your_document` | `tool` slug, `text` (or `claim`), `context` |
| "What do you have for someone like me?" | `what_we_have_for_you` | none, `role`, or `who` ("I'm an SBA lender") |

## Quick start

1. An address came up → `twin_cities_lookup`. Every field is a value **or a miss with its
   reason**, never a blank; report the reason. A miss means the address didn't resolve in the
   parcel index — it is not a finding about the property. The index carries the number the
   county assigned, which for a large building is often not the number on the door.
2. A market or radius question → `twin_cities_datasets` first. **Never guess a dataset id**;
   take it, its `scopes` and its per-dataset county coverage from that call — the list grows.
3. `twin_cities_records` with that `dataset`; add `address` to answer about one property and its
   surroundings, or omit it for the whole market cut. Returns `answer`, `matching_rows`,
   `columns`, `sample`, `centre`, `download_url`, `documented_at`, `caveats`.
4. Someone hands you a document → get the right slug and what to bring from a
   `what_we_have_for_you` card (cards with `api_tool=true` list `bring`), then
   `bring_your_document`. Pass their text **exactly as given** — don't summarise a P&L first.
   Tell them in one line what was sent and that it was not kept.

## Rules that stop a wrong answer

- **`sample` is at most six rows; `matching_rows` is the truth.** Say "399 sales within half a
  mile; here are the closest", never "here are the sales". `download_url` returns a free sample
  of the file; the complete files are sold. Don't present a sample as the whole answer.
- **Coverage is per dataset**, from one city to all seven counties, and each result states its
  own. Never carry one dataset's counties to another, and never say "no records" when the true
  answer is "that county isn't in this file."
- **An ambiguous address is answered, not failed.** Several cities have a Grand Ave: the tool
  returns candidates; ask which and call again with the city after a comma.
- **`owner` / `taxpayer` is the county's tax-billing name**, not a verified beneficial owner.
  Say "the parcel is billed to X", not "X owns it".
- **Radius:** `within_ft` defaults to 5280 (one mile), caps at 26400; half a mile is 2640. State
  the radius you used.
- **A recorded price is a transaction, not an appraisal** (family transfers and $1 deeds sit in
  the same column), and **assessed value is per parcel and usually below market** — sum every
  parcel a building sits on.
- Read `documented_at` (each dataset's source, licence and columns) before quoting a figure as
  settled.

## What it can't answer

- **Commercial rent and lease terms are in no Minnesota public record** — leases aren't recorded.
  Answer occupancy cost from assessed value and tax per square foot, and say why rent is absent.
- A register is a floor, not a census: an address with no vacancy-register row is one nobody
  filed on.
- Rental-licence contact columns (owner/applicant phone and email) are stripped on this surface;
  they remain in the published file. Don't describe them as nonexistent.
- Outside the seven-county metro, use find-the-public-record (`data_source_atlas`).

## When the tools fall short

If the user wants a city, dataset or column that isn't there, or an answer looks wrong, offer to
file it with `request_a_feature` (their words verbatim; `kind`: feature | data | correction).
If they'd rather a person read the record for them, `start_an_engagement` with no arguments
lists the fixed-fee options; it files only after you've confirmed with them what will be sent.
Never say either was sent unless `status` comes back `filed`.
