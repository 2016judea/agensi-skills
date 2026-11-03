---
name: review-intelligence
description: Read a business's public reviews for real signal instead of a star average — a complaint taxonomy with counted rates, recurring themes with verbatim quotes, whether it's getting better or worse, what customers name as the reason they come, and red flags a buyer should verify. Use when an owner asks "what are people actually complaining about", "are we slipping", or a buyer asks "is that 4.6 hiding something". Any US business, via the free Brick & Mortar MCP server's review_intelligence tool.
---

# Review intelligence

**In the owner's words:** "Our rating looks fine but something's off." · "What do people keep
complaining about?" · "Did the reviews change after the new owners took over?"

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

`review_intelligence` — required `business_name` and `city_metro` (disambiguates same-named
businesses); optional `category` (sets expectations for normal review volume).

## What comes back, and the one way to get it wrong

This tool **fetches no data**. It returns a research framework with these keys:
`framework` (the method, named), `research_procedure` (numbered steps), `output_schema` (the
shape of the finished deliverable), `quality_rubric` (`good_looks_like`, `common_failure_modes`)
and `caveats`. **You execute the procedure with your own web search, then write the deliverable
in the `output_schema` shape and check it against the rubric.** Handing the framework back to
the user as though it were the finding is the failure this skill exists to prevent.

The method is **review stratigraphy**: read the corpus in independent layers — classification,
pattern, trajectory, differentiation, risk — before drawing any conclusion. Key moves in the
procedure:

- Sample on purpose: the most recent reviews **and** a comparable sample from 12–24 months back.
- Tag every discrete complaint into a fixed taxonomy and **count** it ("9 of 41 sampled mention
  wait time") — never "several".
- A complaint becomes a named theme only when **3+ independent reviewers** raise it.
- Split recent vs. older windows and re-tally each; bucket ratings by quarter to spot a cliff.
- Check for authenticity anomalies (spikes of short, uniform reviews) — a flagged suspicion,
  never a confirmed finding.
- Mine 4–5 star reviews for **named** praise (a dish, a staff first name, a policy).
- Buyer pass: "new owners", "not the same since", health and safety mentions.

Close with a trajectory verdict: improving, stable, declining, or insufficient data.

## Rules

- **Compare complaint rates, not counts** — a busier business has more of everything.
- Under ~25 reviews, or ~10 in either window, say the sample can't support a trend.
- Review count and velocity are not foot traffic or revenue.
- An owner reply shows attention, not that the problem was fixed.

## Finish

- Check the draft against `quality_rubric.common_failure_modes` before answering.
- State the `caveats` that applied. What public signal cannot show is part of the answer.
- Date-stamp anything that moves (ratings, review counts, prices, multiples).
- For a client-ready document, pass your finished write-up(s) to `compose_report`
  (`business_name`, `audience`: owner | broker | buyer | investor | general,
  `completed_analyses: [{tool, summary}]`). It returns the section order (verdict first), a
  contradiction ledger across analyses, and citation rules; you write the report. Pass your
  **finished** analysis as `summary`, never the raw framework.
