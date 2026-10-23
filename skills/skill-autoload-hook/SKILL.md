---
name: skill-autoload-hook
description: A Claude Code UserPromptSubmit hook that injects a chosen skill's SKILL.md into context whenever your prompt matches a keyword pattern — once per session, then just a one-line pointer — so a must-follow skill (e.g. your outreach rules whenever you mention sending email) is loaded before the model starts reasoning. Use when you say "always load skill X when I talk about Y", "make sure the agent reads my rules before it emails anyone", or a skill keeps being skipped.
---

# skill-autoload-hook (UserPromptSubmit hook)

Skills load when the model decides to load them, which means a rule-heavy skill can be
skipped exactly when it matters. A `UserPromptSubmit` hook's stdout is added to the context,
so this hook prints the skill itself when the prompt matches a trigger pattern.

## Install

1. Copy `hooks/skill_autoload.py` to `~/.claude/hooks/skill_autoload.py`.
2. Add to `~/.claude/settings.json` (one entry per skill you want auto-loaded):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command",
                     "command": "AUTOLOAD_SKILL=my-outreach-rules python3 ~/.claude/hooks/skill_autoload.py 2>/dev/null || true",
                     "timeout": 10 } ] }
    ]
  }
}
```

- `AUTOLOAD_SKILL`: the folder name under `~/.claude/skills/`.
- `AUTOLOAD_PATTERN` (optional): a case-insensitive regex. The default matches sending and
  outreach words (send, email, outreach, reach out, pitch, campaign, follow-up, DM...).

## Behaviour

- **Once per session.** A large skill re-injected on every matching turn burns context fast
  (background-agent notifications mention "sent" and "email" constantly). After the first
  injection it prints a one-line pointer instead. The per-session marker lives in the temp
  directory and is invalidated when the SKILL.md changes.
- Ignores background task notifications (`<task-notification>`, `[SYSTEM NOTIFICATION`).
- Fails open: if the skill file is missing or the input is unreadable, it prints nothing.

Test: `echo '{"prompt":"email the vendor","session_id":"t"}' | AUTOLOAD_SKILL=<name> python3 ~/.claude/hooks/skill_autoload.py | head`
