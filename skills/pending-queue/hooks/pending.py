#!/usr/bin/env python3
"""SessionStart hook: surface due follow-ups in-session instead of on a personal calendar.

Why: agent work items (chase a request, re-run a script, check a reply) clutter a
person's calendar, and a calendar row can't carry the steps. So work tracking lives
in ~/.claude/pending.json and arrives as context at session start.

Reads  ~/.claude/pending.json  (a JSON array; see the file's own _README entry)
       Override the path with CLAUDE_PENDING_FILE - used to test the rendering.
Writes JSON on stdout with hookSpecificOutput.additionalContext (into the model's
context) and systemMessage (one line the user sees).

Fails silent and open: any error prints nothing and exits 0. A hook that breaks a
session start is worse than a forgotten follow-up.
"""
import json, os, sys, datetime

TRACKER = os.environ.get("CLAUDE_PENDING_FILE") or os.path.expanduser("~/.claude/pending.json")
SOON_DAYS = 3          # items this close also surface
CAP = 12               # never flood a session start


def main() -> int:
    if not os.path.exists(TRACKER):
        return 0
    try:
        with open(TRACKER) as fh:
            raw = json.load(fh)
    except Exception:
        return 0
    if not isinstance(raw, list):
        return 0

    today = datetime.date.today()
    cwd = os.path.basename(os.getcwd())
    items = []
    for it in raw:
        if not isinstance(it, dict) or it.get("id", "").startswith("_"):
            continue
        if it.get("done"):
            continue
        try:
            due = datetime.date.fromisoformat(str(it["due"]))
        except Exception:
            continue
        delta = (due - today).days
        if delta > SOON_DAYS:
            continue
        items.append((delta, due, it))

    if not items:
        return 0
    items.sort(key=lambda t: t[0])

    # Anything scoped to another project is still shown, but after this one's.
    def rank(t):
        proj = (t[2].get("project") or "").lower()
        return (0 if proj in ("", cwd.lower()) else 1, t[0])
    items.sort(key=rank)

    shown, extra = items[:CAP], max(0, len(items) - CAP)
    lines = ["## Pending follow-ups (from ~/.claude/pending.json)", ""]
    overdue = 0
    for delta, due, it in shown:
        if delta < 0:
            when, overdue = f"OVERDUE by {-delta}d", overdue + 1
        elif delta == 0:
            when = "due TODAY"
        else:
            when = f"due in {delta}d"
        proj = it.get("project")
        tag = f" [{proj}]" if proj and proj.lower() != cwd.lower() else ""
        lines.append(f"- **{due} — {when}**{tag}: {it.get('what', '(no description)')}")
        if it.get("how"):
            lines.append(f"  - {it['how']}")
    if extra:
        lines.append(f"- ...and {extra} more in the tracker.")
    lines += [
        "",
        "These are the user's follow-ups, tracked in-session on purpose - they are "
        "deliberately NOT on their personal calendar. Raise them when relevant to "
        "what they are doing; do not derail them with them. Mark one done by setting `done: true` "
        "on its entry, and add new ones the same way.",
    ]

    n = len(shown) + extra
    msg = f"{n} pending follow-up{'s' if n != 1 else ''}"
    if overdue:
        msg += f", {overdue} overdue"
    print(json.dumps({
        "systemMessage": msg + " (see ~/.claude/pending.json)",
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        },
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
