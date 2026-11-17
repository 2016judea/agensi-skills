---
name: tool-launch
description: >-
  Take a small software tool from idea to live and found in one session: a premise
  check with numbers, the wedge taken from competitor complaints, a trademark-safe
  domain, the build brief, SEO for a brand-new domain (IndexNow + Search Console), one
  MCP server listed in every assistant directory that takes it (ChatGPT, Claude, Grok,
  the MCP registry and others), outreach to super users, an honest feature board, and
  launch posts. Use when asked to "build a tool for <people> and sell it", "ride the
  <event> wave", "make it show up when people search", "ChatGPT and Grok plugin", "list
  it everywhere", "get it in front of people", "prepare for distribution", "launch it",
  or when a hype moment (a game launch, a product release) sets a deadline.
compatibility: >-
  Any agent that can run shell commands and drive a browser. Network access: IndexNow
  (api.indexnow.org) to ping search engines, the Vercel REST API (api.vercel.com) for
  domain price checks if you use Vercel, the official MCP Registry
  (registry.modelcontextprotocol.io), and the directory and platform sites you submit
  to through your own browser session (search.google.com, glama.ai, mcp.so,
  platform.openai.com, claude.ai, x.ai). Every call uses your own accounts.
allowed-tools: Bash Read Write
metadata:
  network-hosts: "api.indexnow.org api.vercel.com registry.modelcontextprotocol.io search.google.com glama.ai mcp.so platform.openai.com claude.ai x.ai"
---

# Tool launch: idea to live and found, in one session

**Done** means the tool is live on its own domain with analytics, Google and Bing know every
page, the MCP server is submitted to every assistant directory that takes it, the people who
stand in front of many buyers have each been contacted, and launch posts are up.

Every step below was run once for real (one launch: a stream-clipping tool built in an evening,
three days before a major game release). Treat the platform facts as dated, and re-check them.
Whether anyone uses the tool is unknown until visits and replies come in. Never predict
adoption in either direction; ship and measure.

## Order, and why this order

1. **Premise check, with numbers, before anything is named** (see
   `check-the-premise-not-adoption`). Find where the money actually flows, and say it plainly
   when the premise is off. *Why:* the launch premise was "the only money is in YouTube
   payouts", and it was backwards. Gaming Shorts pay about $0.01–0.10 per 1,000 views. The money
   was in brand clipping-campaign budgets, median about $1 per 1,000 views. That one fact set
   the pricing and the outreach target.
2. **The wedge comes from competitor complaints, not taste.** Mine about a dozen relevant
   subreddits (`reddit-mining`), running **one background process per subreddit** (a single
   combined run stalled on one huge sub and hit connection resets). Rank the complaints. The top
   one becomes the headline. *Why:* the top complaint, "these tools were built for podcasts, not
   gameplay", became the approved headline almost word for word.
3. **Check what's already free** (`github-scout`). If open source already does the core, wire it
   in and compete on the step nobody does. *Why:* VOD-to-clips already had three open repos with
   3k–6.5k stars each. The open space was *which campaign pays* and *live* moments.
4. **Write DATA_MODEL.md first, then hand the build to an agent** with a brief that holds every
   decision already made. *Why:* the brief is that agent's only context. A brief that carried the
   pricing, the trademark guard, the deadline, analytics and the gates shipped in one pass.
5. **Distribution runs in parallel with the build**, as below. Outreach goes out the moment the
   page works, not after a polish pass.

## Rules (each one cost something to learn)

- **The domain never carries someone else's mark, even one that sounds like a common word.**
  *Why:* a proposed name used a game publisher's studio name. A WIPO decision (D2021-1025)
  treats that word alone as the publisher's mark, and a disputed domain takes all of its search
  ranking with it. Use the mark descriptively in page titles, and say "not affiliated" in the
  footer. Check availability with `whois`. Check price with your registrar (on Vercel,
  `GET /v1/registrar/domains/<domain>/price`; see `vercel-api`). Buying the domain is the
  owner's money decision.
- **Price on the unit the buyer earns on.** *Why:* clippers earn per clip, and the top pricing
  complaint was per-minute billing. If the pricing *is* the difference, it goes in the headline.
- **Respect robots.txt even when other scrapers don't.** *Why:* the marketplace disallowed
  `/api/`, but its allowed discovery page carried every field in its Next.js flight payload
  (`self.__next_f`). Look at the allowed pages before you treat a block as a judgment call.
- **A new domain can't win the head term in days. Win fresh long tail instead.** Build a page
  per entity (each campaign, each streamer), a "rates today" page with a visible timestamp, and
  honest guides. Then:
  - Ping **IndexNow on every update**. Bing reads it, and Bing feeds ChatGPT search.
  - Set up Search Console (`search-console-setup`). The owner creates the property and pastes
    the TXT string, you write the DNS record, the owner clicks Verify, and then you submit
    `sitemap.xml`.
  - Allow OAI-SearchBot, GPTBot and xAI's crawlers in robots.txt.
- **One MCP server is many channels.** List the same `/mcp` endpoint in each directory below.
  Keep one listing kit in the repo (name, one-liner, description, URLs, tool annotations, test
  cases, starter prompts) and copy from it on every form. The facts as of 2026-11:

  | Directory | What it takes, and what bit |
  |---|---|
  | Official MCP Registry | `server.json` + `mcp-publisher`. A namespace on your own domain authenticates by DNS. The description is capped at 100 characters (422 above it). Listed the same day. |
  | Glama | Picks up the registry entry. Claim it, and keep the health check passing. |
  | Claude Connectors Directory | Add the server to your own account as a custom connector first, then file. "Read only" is refused if any tool has `readOnlyHint: false`. Wrapping third-party APIs "typically blocks listing": say plainly in the reviewer notes what you read and from where. Review can take weeks. |
  | ChatGPT plugin directory | **ZIP upload only** (the "create with MCP" path is gone). Short description max 30 characters. No pricing words such as "Free" in the description. Support must be a URL, not an email. Domain check: serve the token at `/.well-known/openai-apps-challenge`, and leave it up because it is re-checked. **Approval does not publish**: the owner clicks Publish afterwards. **Developer mode works on the Free plan**, so you don't need a paid plan to record the demo. |
  | xAI connector marketplace (Grok) | A web form, and the reply comes by email. |
  | mcp.so | A free submission queue. |
  | Smithery, PulseMCP, mcptop | Smithery closed to submissions on 2026-10-31. PulseMCP paused submissions and picks up registry entries when it reopens. mcptop mirrors the other directories and has no form. |

  The OpenAI platform sign-in (Google + passkey) can't be carried into a copied browser
  profile. Work in a new tab of the owner's own Chrome (see `browser-as-you`). Every directory is
  for being found, not for getting paid. Payment happens on your own site.
- **GitHub trending as a channel needs about 1,500+ stars in a week** on the global weekly list.
  What trends is agent-native framing: "built for agents", an MCP server, a CLI, a Claude Code
  skill. The README opens with the live link.
- **Outreach goes to super users, not end users** (`distribution-channel`, the super-user
  section). On a marketplace, the people who stand in front of many buyers are the listing
  owners. One campaign owner alone fronted more than 7,000 clippers.
  - Open on their own listing (title, rate, count), refreshed from live data minutes before
    sending.
  - Link to `/for/<readable-slug>`, not a random ID. In email, send HTML with the link text set
    to the bare domain. On platforms that show raw links, the readable slug is what keeps it
    from looking like tracking.
  - Verify every contact route on the owner's own page. Never pattern-guess an address.
  - Keep names and emails out of a public repo (gitignore `outreach/`).
  - A human approves and sends.
- **Seed feature boards honestly.** Label seeded ideas "Suggested by <brand>", start every vote
  at 0, and allow one vote per browser with no login. *Why:* fake votes are a fabricated record,
  and the first person who notices kills the community the board exists to build.

## Launch posts: what each platform actually did (2026-11)

| Platform | Result | Next time |
|---|---|---|
| A niche subreddit | Its sidebar rules banned the exact topic; the post was written, then dropped | Read the sidebar rules before drafting |
| Show HN | Posted from a 1-karma account, **[flagged] and dead within a minute** | Post from an account with history, or email the mods (hn@ycombinator.com) first. Never repost a dead item. HN's API hides a dead item's text, so an empty `text` doesn't mean the body failed to post |
| X | Automated email signup refused ("Please try using a different method"); "Continue with Google" in the owner's own Chrome, with their passkey, worked | A brand account under a handle the owner picks, never a pseudonym persona. Render the avatar from the logo SVG (`inkscape … -w 800`) |
| Whop | Account by emailed code, no password. A store's "Contact support" reaches its admin team with no purchase | Use it as the contact route for store owners |

Account creation and posting mechanics live in `browser-as-you`. Do the browser work yourself;
hand the human only the passkey, the CAPTCHA tick and the Publish button.

## Mail

Respect your mailbox's send cap (see `zoho-send-cap`): read the send log before promising a send
time. If the cap is full, a second mailbox works, but replies land there, so say where to look.

## What's the owner's vs. yours

**The owner's:** whether to build, the domain purchase, any copy they write themselves, when to
send (default: as soon as it's ready), the handle, Publish buttons, and anything that needs their
passkey or phone.
**Yours:** the pricing model, the trademark guard, which buyers to reach and how, the premise
numbers, the directory submissions, the posts themselves once the owner has approved the copy, and every
fix along the way.
