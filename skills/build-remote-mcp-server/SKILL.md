---
name: build-remote-mcp-server
description: >-
  Build and deploy a remote MCP (Model Context Protocol) server on
  Cloudflare Workers — TypeScript, Streamable HTTP, zero/near-zero infra
  cost. Use when you want to build a new MCP server, expose a set of
  tools to Claude/ChatGPT via MCP, or ask to "make this an MCP server" /
  "deploy an MCP server" / "submit to the Connectors Directory".
---

# Build a remote MCP server

Proven end-to-end on a production MCP server deployed to Cloudflare Workers
(mid-2026). The gotchas section below is the highest-value part — most of
them cost real debugging time the first time and are completely non-obvious
from the docs alone.

## Stack (verify before trusting this — see gotcha #1)

- **TypeScript**, `@modelcontextprotocol/server` v2 (`McpServer` class,
  `registerTool`) — the official SDK.
- **`agents`** package (Cloudflare), specifically its **stateless**
  `createMcpHandler` export (`agents/mcp/server`) — mounts as a plain
  Workers `fetch` handler at `/mcp`. **Not** the older `McpAgent` class,
  which is Durable-Object-backed and only worth it for genuinely stateful
  servers (persistent per-session memory, multiplayer). A server whose
  tools are pure functions of their input doesn't need it.
- **Zod v4** for input/output schemas.
- **Workers KV** (free tier) if you need any kind of usage tracking —
  no Durable Objects, no database, no external API calls from the server.

## Gotchas (read this before writing code)

1. **This ecosystem moves fast — verify package names/APIs against live
   npm/unpkg data, not memory.** The MCP TypeScript SDK had a full v1→v2
   split in July 2026: the old monolithic `@modelcontextprotocol/sdk`
   became `@modelcontextprotocol/server` + `@modelcontextprotocol/client` +
   `@modelcontextprotocol/core`. Training data before that split will
   confidently suggest the wrong package name. Before committing to an
   architecture: `curl https://registry.npmjs.org/<pkg>` for real
   dist-tags, and read the actual installed `node_modules/**/*.d.ts` (or
   `unpkg.com/<pkg>@<version>/dist/*.d.ts`) rather than guessing method
   signatures. A "the package name doesn't match what I remember" moment is
   a signal to verify, not to override the tool with your prior.

2. **Every `registerTool()` call with an `outputSchema` means the SDK
   validates `structuredContent` on EVERY result — including your own
   middleware's short-circuits.** If you wrap tools in an auth/rate-limit/
   policy middleware and it returns early (a denial, a friendly "you've hit
   your limit" message) without `structuredContent` matching the declared
   schema, the SDK itself rejects it and silently wraps it as
   `isError: true` — turning a clean, intentional denial into what looks
   like a broken tool call. Fix: give denial responses a real
   `structuredContent` conforming to the same schema (add an optional
   field like `notice` to carry the denial payload) rather than a
   differently-shaped ad hoc object. **This is easy to ship without
   noticing** — it only shows up when you actually exercise the denial
   path, which is usually dormant/untested code.

3. **A no-auth server should NOT serve OAuth Protected Resource Metadata
   or a 401 challenge at all.** Per the MCP spec, authorization is
   OPTIONAL — the compliant move for "no auth required" is to skip the
   OAuth dance entirely (no PRM doc, no `WWW-Authenticate` header on
   `/mcp`). Serving a PRM for a resource that isn't actually protected is
   the non-compliant move, not the safe default. Write the OAuth discovery
   handlers as real, ready, **unmounted** code for later (so adding auth
   is additive) rather than stubbing a fake 401 today.

4. **Tool handlers get the raw request via `ctx.http.req`** (a real
   `globalThis.Request`) and, once auth exists, validated auth info via
   `ctx.http.authInfo` — both on the `ServerContext` second argument every
   tool callback receives. That's the seam for identity resolution
   middleware (e.g. hash the caller's IP today, swap to `authInfo`'s
   subject later with zero other changes).

5. **Cloudflare account bootstrap:** a brand-new account has no
   `workers.dev` subdomain registered. `wrangler deploy` will report
   success and print a URL that **doesn't resolve** until one exists — no
   `wrangler` CLI command registers it; `wrangler deploy` auto-registers
   one on first deploy (derived oddly — it used the local package/repo
   name once, not a chosen name) with a warning, or call the Cloudflare API
   directly: `GET`/`PUT
   https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/subdomain`.
   DNS can take a few minutes to propagate after that; the SSL cert for the
   new hostname can lag a bit longer.

6. **`wrangler kv namespace create <BINDING_NAME>`** is the current
   syntax (not the legacy `wrangler kv:namespace create`). Run it once,
   copy the real `id` from its output into `wrangler.jsonc`'s
   `kv_namespaces` — don't leave a placeholder id and expect `wrangler dev`
   to fail loudly; Miniflare's local KV simulation works fine even with a
   fake id, so a bad id only breaks the **real** deploy, silently, unless
   you test against production too.

7. **If the repo also deploys to Vercel from git, the commit author email must be
   one Vercel recognises on the project.** A commit authored with a different
   address can be silently skipped: the push succeeds, GitHub shows the commit, and
   production keeps serving the previous build with no error anywhere you would look.
   Don't pass `-c user.email=` inline; set the repo's git identity once to the
   authorised address and check the deployment went READY after every push.

8. **Sandbox-specific TLS trap:** this environment's `curl` (LibreSSL
   3.3.6-based build) can silently fail TLS 1.3 negotiation against
   Cloudflare's edge with a generic `SSL routines:ST_CONNECT:sslv3 alert
   handshake failure` — which looks *exactly* like "the SSL cert isn't
   provisioned yet for a freshly-registered `workers.dev` subdomain" (a
   real, separate, also-possible cause). Before concluding a fresh
   Cloudflare deploy is broken: retry with `curl --tlsv1.2 --tls-max 1.2`.
   If that succeeds, it was never a deploy problem — it's this sandbox's
   client TLS stack, every time.

9. **Cloudflare's bot protection blocks Python's default `urllib`
   User-Agent (`Python-urllib/x.y`) with a plain 403** — even when the
   request is otherwise perfectly correct (right headers, right body,
   right method). `curl`'s default User-Agent sails through untouched. If
   a hand-rolled Python test script against a live Cloudflare Workers
   deploy gets 403s while the equivalent `curl` command gets 200, this is
   almost certainly why — set a custom `User-Agent` header. (Already fixed
   in `scripts/mcp_http_smoke_test.py` in this skill.)

## Testing before and after deploy

- **Local:** `wrangler dev` (Miniflare's local KV works with a placeholder
  namespace id — no Cloudflare account needed for this step).
- **Real MCP client, not just curl:** `npx @modelcontextprotocol/inspector
  --cli --server-url <url>/mcp --transport http --method tools/list
  --format json` (and `--method tools/call --tool-name <name>
  --tool-args-json '{...}'`). This drives the actual reference client
  implementation — worth using over hand-rolled curl+JSON-RPC parsing,
  which is easy to get subtly wrong (see below).
- **Scripted smoke test:** `scripts/mcp_http_smoke_test.py <url>
  [calls.json]` in this skill — handles the SSE `data: {...}` frame
  parsing correctly (Streamable HTTP wraps every response in an SSE
  event, which trips up a naive `json.loads(response.text)`) and checks
  `isError`/`structuredContent` rather than assuming success.
- **Exercise the dormant paths too**, not just the happy path — that's
  where gotcha #2 was actually caught. If there's a rate-limit/auth/policy
  seam that isn't active by default, flip it on locally and call a tool
  past the limit before calling the build done.

## Directory Connectors submission

If targeting Anthropic's Connectors Directory: every tool needs a `title`
and `annotations` (`readOnlyHint: true` for anything that doesn't mutate
state), 2-3 few-shot example invocations in the description, a public
`/privacy` page, and HTTPS. Keep a `SUBMISSION.md` in the repo with a
requirements-to-implementation checklist and ready submission-form copy
(server name, tagline, use-case description, example prompts) so the form
is a paste, not a writing session. OpenAI's Apps/plugin submission is a **separate path** with
its own (and possibly-changed-by-now) requirements — don't assume parity,
verify current docs at submission time.

## Related

`sms-native-product` — the other way to give a product a native surface
instead of a website: text messages. Same instinct (meet people where they
already are, install nothing), different channel, and a much harder gate —
US carriers must approve the traffic before it can send at all.
