#!/usr/bin/env python3
"""PreToolUse guard: cap sends from a Zoho Mail mailbox through the Zoho MCP.

Zoho blocks all outgoing mail for an account that sends in bursts (one block came
after ~50 sends in 45 minutes; the block notice was filed to Spam). A cap written
in a project note gets skipped by the next session that never loads it, so the cap
lives in a global hook, and it refuses the send instead of advising against it.

Counts every ZohoMail_sendEmail / ZohoMail_sendReplyEmail that is not a draft or
template. A scheduled send counts at its scheduled time. Ledger:
~/.claude/state/zoho_sends.jsonl (one {"t": epoch, "to", "subject"} per send).

Bulk sends belong on a bulk email provider, not the mailbox.
"""
import fcntl, json, os, sys, time
from datetime import datetime

CAPS = [  # (window seconds, max sends in any such window)
    (3600, 10),
    (86400, 25),
]
MIN_GAP = 90  # seconds between any two sends

LEDGER = os.environ.get("ZOHO_SEND_LEDGER") or os.path.expanduser("~/.claude/state/zoho_sends.jsonl")
TOOLS = ("ZohoMail_sendEmail", "ZohoMail_sendReplyEmail")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


def send_time(body):
    """Epoch the message will actually leave."""
    if not body.get("isSchedule"):
        return time.time()
    now = time.time()
    st = body.get("scheduleType")
    try:
        st = int(st)
    except (TypeError, ValueError):
        st = None
    if st in (1, 2, 3):
        return now + {1: 3600, 2: 7200, 3: 14400}[st]
    if st in (4, 5):  # next morning / afternoon, roughly
        d = datetime.fromtimestamp(now)
        h = 9 if st == 4 else 14
        return datetime(d.year, d.month, d.day, h).timestamp() + 86400
    raw = body.get("scheduleTime") or ""
    try:
        naive = datetime.strptime(raw, "%m/%d/%Y %H:%M:%S")
    except ValueError:
        return now
    tz = body.get("timeZone") or ""
    try:
        from zoneinfo import ZoneInfo
        return naive.replace(tzinfo=ZoneInfo(tz)).timestamp()
    except Exception:
        return naive.timestamp()  # fall back to this machine's local zone


def worst_window(times, t, w):
    """Max sends in any w-second window containing t, counting the new one."""
    near = sorted(x for x in times if t - w < x < t + w)
    best = 1
    for s in [x for x in near if x <= t] + [t]:
        best = max(best, 1 + sum(1 for x in near if s <= x < s + w))
    return best


def main():
    ev = json.load(sys.stdin)
    name = ev.get("tool_name", "")
    if not name.endswith(TOOLS):
        return
    body = (ev.get("tool_input") or {}).get("body") or {}
    if body.get("mode") in ("draft", "template"):
        return

    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        times = []
        for line in f:
            try:
                times.append(float(json.loads(line)["t"]))
            except Exception:
                pass
        t = send_time(body)
        for w, cap in CAPS:
            n = worst_window(times, t, w)
            if n > cap:
                label = "hour" if w == 3600 else "24 hours"
                deny(f"Zoho send cap: this would be send #{n} in a rolling {label} "
                     f"(cap {cap}). Zoho blocks accounts that send in bursts. "
                     f"Send batches through a bulk provider, or schedule this one later. "
                     f"Ledger: {LEDGER}")
        gap = min((abs(t - x) for x in times), default=MIN_GAP)
        if gap < MIN_GAP:
            deny(f"Zoho send cap: {int(gap)}s from the nearest other send; keep "
                 f"{MIN_GAP}s apart. Wait, or schedule it (isSchedule) later.")
        to = body.get("toAddress", "")
        f.write(json.dumps({"t": t, "logged": time.time(), "to": to,
                            "subject": body.get("subject", "")}) + "\n")


if __name__ == "__main__":
    main()
