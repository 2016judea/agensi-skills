#!/usr/bin/env python3
"""UserPromptSubmit hook: when the prompt matches a keyword pattern, print a chosen
skill's SKILL.md so it is in context before any reasoning starts. stdout of a
UserPromptSubmit hook is added as context.

Configure with env vars (or edit the defaults below):
  AUTOLOAD_SKILL    skill folder name under ~/.claude/skills   (default: distribution-channel)
  AUTOLOAD_PATTERN  case-insensitive regex that triggers it    (default: sending/outreach words)

Once per session: a big skill re-injected on every matching turn (background-agent
notifications mention "sent" and "email" constantly) burns context fast. Context
persists within a session, so after the first injection a one-line pointer is enough."""
import json, os, re, sys, pathlib, tempfile
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
prompt = data.get("prompt", "")
# Background-task notifications are not the user asking for anything.
if "<task-notification>" in prompt or "[SYSTEM NOTIFICATION" in prompt:
    sys.exit(0)
PAT = re.compile(os.environ.get("AUTOLOAD_PATTERN") or r"\b(send|sent|sending|email|e-mail|inmail|linkedin|outreach|reach out|cold|pitch|mailer|message (him|her|them)|dm|campaign|prospect|distribution|follow[- ]?up)\b", re.I)
if not PAT.search(prompt):
    sys.exit(0)
NAME = os.environ.get("AUTOLOAD_SKILL", "distribution-channel")
skill = pathlib.Path.home() / ".claude/skills" / NAME / "SKILL.md"
if not skill.exists():
    sys.exit(0)
sid = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id", "")))
marker = pathlib.Path(tempfile.gettempdir()) / f"skill_autoload_{NAME}_{sid}" if sid else None
if marker and marker.exists() and marker.stat().st_mtime >= skill.stat().st_mtime:
    print(f"{NAME} skill already loaded earlier this session; reread {skill} only if it has left context.")
    sys.exit(0)
print(f"<{NAME}-skill note='auto-loaded once per session by skill_autoload.py because the prompt matched its trigger pattern'>")
print(skill.read_text())
print(f"</{NAME}-skill>")
if marker:
    marker.touch()
