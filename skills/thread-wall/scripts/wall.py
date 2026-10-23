#!/usr/bin/env python3
"""Collapse an iMessage thread into a wall of text.

Usage:
    wall.py +15555550123 [YYYY-MM-DD | today | all] [limit]

Prints speaker turns separated by blank lines. No names, no timestamps,
no tapbacks. Consecutive messages from the same person join into one
paragraph, because that is how a person actually talks -- the bubble
breaks are typing artifacts, not sentence boundaries.

Reads through read_messages.py (beside this file) so the attributedBody
decoding lives in exactly one place.
"""
import datetime as dt
import re
import subprocess
import sys

import os
READER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "read_messages.py")
LINE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}\] (ME|THEM)\s*: ?(.*)$")

# Tapbacks requote the other person's message verbatim. Left in, they
# duplicate half the thread and read as if someone said it twice.
TAPBACK = re.compile(
    r"^\.?(Loved|Liked|Disliked|Laughed at|Emphasized|Questioned|Reacted)\b"
)


def turns(number, limit):
    out = subprocess.run(
        ["python3", READER, number, str(limit)],
        capture_output=True, text=True, check=True,
    ).stdout

    msgs = []
    for raw in out.splitlines():
        m = LINE.match(raw)
        if m:
            msgs.append([m.group(1), m.group(2), m.group(3)])
        elif msgs:
            # continuation of a multi-line message body
            msgs[-1][2] += " " + raw
    return msgs


def main():
    number = sys.argv[1]
    day = sys.argv[2] if len(sys.argv) > 2 else "today"
    limit = sys.argv[3] if len(sys.argv) > 3 else 200
    if day == "today":
        day = dt.date.today().isoformat()

    kept = []
    for date, who, text in turns(number, limit):
        if day != "all" and date != day:
            continue
        text = text.strip()
        if not text or TAPBACK.match(text):
            continue
        if text in ("+￼", "-￼"):  # bare attachment, no caption
            continue
        text = text.replace("+￼", "").replace("-￼", "").strip()
        if kept and kept[-1][0] == who:
            kept[-1][1] += " " + text
        else:
            kept.append([who, text])

    print("\n\n".join(t[1].strip() for t in kept))


if __name__ == "__main__":
    main()
