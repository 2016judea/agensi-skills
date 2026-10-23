---
name: claude-usage-mining
description: Read your own Claude Code state on this machine — session transcripts, what's running right now, which skills you actually invoke, how much you use it. Use when you ask "how much am I using Claude", "analyse my usage", "what sessions do I have running", "what am I actually using skills for", "mine my transcripts", "which of my skills are dead", "am I using subagents", or when building any tool that reads the local Claude corpus. This is the TOOL skill for that corpus — the file layout, the entry types, the fields that lie, and the retention sweep that deletes it.
---

# Reading Claude Code's own local state

Everything Claude Code knows about how you work is on this machine in
plain JSONL. This skill is the map, and the list of things that silently lie.

## THE FIRST RULE: check retention before promising a longitudinal read

`cleanupPeriodDays` defaults to **30** when unset, and a sweep runs at startup.

    python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.claude/settings.json'))).get('cleanupPeriodDays','UNSET -> 30'))"

**Why this is rule one:** with the default, anything older than a month is
already permanently deleted, and you usually discover it only when someone asks
for "a year of usage." If history matters, set `cleanupPeriodDays` high (e.g.
36500) and keep an rsync mirror (e.g. `~/.claude-archive/transcripts/`). Never
assume local history predates the day retention was raised.

## Where things are

    ~/.claude/projects/<slug>/<uuid>.jsonl                MAIN sessions
    ~/.claude/projects/<slug>/<uuid>/subagents/*.jsonl    SUBAGENT transcripts
    ~/.claude/projects/<slug>/<uuid>/tool-results/        large tool payloads
    ~/.claude-archive/transcripts/                        the mirror (never swept)
    ~/.claude/settings.json                               permissions, hooks, env
    ~/.claude.json                                        account, machine, caches

`<slug>` is the cwd with `/` → `-`, e.g. `-home-you-code-myrepo`.

**TRAP 1 — subagent transcripts are not sessions.** A naive
`glob("**/*.jsonl")` counts them as sessions and inflates everything. It made a
concurrency figure read **21 when the truth was 5**. Main sessions are
`*/*.jsonl` (one level); subagents are `*/*/subagents/*.jsonl`.

## What is running right now

    ~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude agents --json

**TRAP 2 — `claude` may not be on PATH.** The VS Code extension ships
its own binary and does not link it. Glob the extensions dir and take the last
match — the version drifts, sometimes mid-session.

**TRAP 3 — that call returns liveness ONLY**: `pid`, `cwd`, `kind`,
`startedAt`, `sessionId`, `name`. **No status.** Working / blocked / idle must be
derived yourself. Cost ~0.19s, cheap enough to poll.

## Who owns this uncommitted file?

The question that comes up when several sessions share a repo and one leaves a
dirty file (or a red test) behind. **Do not broadcast asking — read it.**
Messaging other sessions rarely finds the owner; the transcripts answer it in
two commands.

1. `agents --json` → `sessionId` per live pid (the traps above apply).
2. `sessionId` maps straight to `~/.claude/projects/<slug>/<sessionId>.jsonl`.
3. Scan each live session's transcript for `tool_use` blocks where
   `name in {Edit, Write, MultiEdit, NotebookEdit}` and `input.file_path`
   contains the file. Record `timestamp`.
4. **Confirm against the filesystem:** the last write's timestamp must match the
   file's `mtime`. Transcripts are **UTC**, `stat` is local — a 5-hour gap in
   summer is CDT, not a mismatch. A to-the-second match after that offset is
   proof; anything looser is a guess.

Read the winning `Edit`'s `old_string`/`new_string` to confirm *what* the change
is before acting on the attribution — and to quote it back, which is what makes
the claim checkable by the session you're accusing.

**Absence is evidence too.** "No live session has a write to this path" cleared
two sessions that had each asserted innocence, and pointed at the fourth.

**TRAP 6 — `grep -l <name>` over the transcripts is not ownership.** Mentioning a
file (reading it, running it in Bash, being told about it) is not writing it. The
naive grep returned 36 of ~40 transcripts for one filename; filtering to *writer
tools with a matching `file_path`* returned one live session.

## Deriving state (the part that is actually hard)

**TRAP 4 — an unanswered `tool_use` at the tail is ambiguous.** It means
*"blocked on a permission prompt"* **or** *"mid-tool-call right now."* Reading
the tail alone gives false positives.
**Only a two-sample delta separates them:**

| State | Test |
|---|---|
| `working` | transcript grew between two polls, **or** frozen < ~20s |
| `blocked` | alive, frozen ≥ ~20s, **and** an unanswered `tool_use` |
| `yours` | alive, frozen, nothing unanswered — Claude finished its turn |
| `gone` | no live pid |

Pair `tool_use` ids against `tool_result.tool_use_id` to find unanswered calls.
**What it is blocked on lives in the tool input, not the prose** — an
`AskUserQuestion`'s `input.questions[0].question`, a `Bash`'s `input.command`.
The last assistant *text* is usually preamble.

## Entry types worth knowing

- `ai-title` → `{"aiTitle": "Review the landing page feedback"}`. Real human-readable
  session names, free. **Take the LAST one in the file** — it is re-emitted as a
  session drifts, and the first is often stale.
- `last-prompt` → marks a finished turn at the tail.
- `user` rows: skip `isMeta: true` and any with `toolUseResult` — those are hook
  noise and tool returns, not the human. Skip text starting with `<` or containing
  `system-reminder`.

## TRAP 5 — `cwd` lies about which repo you are working in

Sessions launched in one repo routinely write to another repo or to `~/.claude`. **Attribute to the git root most often
written to**, from `Edit`/`Write`/`NotebookEdit` `input.file_path`, walking up to
the nearest `.git`. Fall back to `cwd` only when there are no writes.

*Why it matters:* every per-repo number — usage, continuity, "what did I ship" —
is wrong if you key on `cwd`, and wrong in a way that looks plausible.

## Performance

The corpus is ~1 GB. **Read tails, not files.** Seek to the last ~512 KB, discard
the first partial line, parse the rest. Bounded and fast even on a 50 MB session.
Full scans are only acceptable for cached, once-per-session work (repo
attribution, `ai-title` lookup) — and those must be throttled if repeated.

## Counting skill usage, and finding dead skills

Count `tool_use` blocks where `name == "Skill"`, keyed on `input.skill`. Compare
against what exists:

- `~/.claude/skills/*/` (global)
- `<repo>/.claude/skills/*/` for each repo
- `~/.claude/plugins/cache/**/skills/*`
- **plus a hand-maintained allowlist of CLI-shipped built-ins** (`artifact-design`,
  `dataviz`, `claude-api`, `run`, `update-config`, `loop`, `schedule`,
  `code-review`, `simplify`, `security-review`, `init`, `keybindings-help`,
  `fewer-permission-prompts`, `artifact-diagramming`, `artifact-capabilities`) —
  without it the report cries wolf on every run and you learn to ignore it.
- Skip `superpowers:*` — plugin-resolved at runtime.

Dedupe by filename when scanning archive **and** live dirs, or every count doubles.

**What this typically finds: hundreds of invocations of skills that no longer
exist** — renamed or deleted skills still being called. That is not a *stale*
skill but a *silently missing* one. Worth surfacing unprompted whenever mining usage.

## Ask vs. decide yourself

- **Decide:** how to read, what to count, performance strategy.
- **Ask:** before deleting any skill a dead-skill report flags — some were folded
  into others deliberately. Retire aggressively, but the owner confirms the list.
  See `crystallize`.

## Forward references

- Building a local Mac surface over this data → `mac-menu-bar-app`
- Turning a session like this into skills → `crystallize`
