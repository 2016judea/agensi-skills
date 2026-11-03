---
name: tool-skill-template
description: Template for a TOOL skill — one per API, CLI or service your agent keeps fighting. Copy this folder to ~/.claude/skills/<tool-name>/, rename, and fill it from a session where the tool actually bit you. Use when you say "make a skill for <tool>", "the <API> keeps breaking", "write down how <service> works", or when crystallize says a lesson belongs in a tool skill.
---

# <Tool name>

<!-- One line: what this tool is for, in the words you'd type. Task skills point
here instead of restating any of this: every tool gets its own skill, and task skills compose them. -->

## Credentials and where they live

<!-- The env var name and the FILE it is read from, never the value.
     Example: `API_TOKEN` in `./.env`. Every call needs `team=<id>` or it sees nothing. -->

## The calls that work

<!-- The 3–6 calls you actually use, copy-pasteable. Only ones you ran.
     Each with what it returns and the one field that matters. -->

    GET https://api.example.com/v1/things?team=<id>

## The fields that lie

<!-- The highest-value section. Every entry: what it says, what is true, the date
     you found out, and the tell that spots it. A green status over nothing, a
     200 that is a login page, a count that silently caps. -->

- **<field or status>** says X; really Y. Found <YYYY-MM-DD> when <what broke>.
  Tell: <the one check that catches it>.

## Limits

<!-- Rate limits, quotas, reset times, size caps — with the error code you saw. -->

## Rules (only where a mistake is expensive)

<!-- Rule density follows risk: the costlier the mistake, the more specific the rule. Every rule carries its why:
     **Never X.** Why: on <date>, X did <cost>. -->

## What this skill does not own

<!-- Forward-reference the neighbours instead of restating them. One line each:
     Visit counts → `site-analytics`. Phone QA → `mobile-ui-audit`. -->

---

## How to fill this (delete this section once filled)

1. Fill it from a session where the tool actually bit you, not from its docs. A tool skill
   written ahead of the work is a guess; the value is in what the docs don't say.
2. "The fields that lie" is the section that pays for the skill. If you have nothing for it yet,
   the skill may not be needed yet.
3. Keep it short. Every line should narrow what the next agent could get wrong.
4. Date each trap. A trap with no date can't be re-checked when the API changes.
