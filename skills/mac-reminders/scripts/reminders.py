#!/usr/bin/env python3
"""Read Apple Reminders from the local Core Data stores. Read-only, on-device.

Usage:
  reminders.py lists                                   every list with open / done counts
  reminders.py open [--list NAME] [--due-before D]     incomplete reminders, soonest due first
  reminders.py done [--list NAME] [--since D]          completed reminders, newest first
  reminders.py search <text> [--all]                   title + notes; --all includes completed
  --store FILE  read one specific Data-*.sqlite instead of all of them
Dates are YYYY-MM-DD.
"""
import argparse, glob, os, sqlite3, sys
from datetime import datetime

STORES = os.path.expanduser("~/Library/Group Containers/group.com.apple.reminders/Container_v1/Stores")
APPLE = 978307200


def stores(one=None):
    paths = [one] if one else sorted(glob.glob(os.path.join(STORES, "Data-*.sqlite")))
    if not paths:
        sys.exit("No Reminders store found. Grant Full Disk Access to your terminal (see SKILL.md), "
                 "and open Reminders.app once so it creates its stores.")
    for p in paths:
        try:
            c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            c.execute("SELECT 1 FROM ZREMCDREMINDER LIMIT 1")
            yield c
        except sqlite3.Error as e:
            print(f"warn: {os.path.basename(p)}: {e}", file=sys.stderr)


def d(v, fmt="%Y-%m-%d %H:%M"):
    return datetime.fromtimestamp(v + APPLE).strftime(fmt) if v else ""


def apple(day):
    return datetime.strptime(day, "%Y-%m-%d").timestamp() - APPLE


SQL = """SELECT r.ZTITLE, r.ZNOTES, r.ZDUEDATE, r.ZALLDAY, r.ZCOMPLETED, r.ZCOMPLETIONDATE, r.ZFLAGGED,
                r.ZPRIORITY, l.ZNAME, r.ZPARENTREMINDER, r.ZCREATIONDATE
         FROM ZREMCDREMINDER r LEFT JOIN ZREMCDBASELIST l ON l.Z_PK = r.ZLIST
         WHERE r.ZMARKEDFORDELETION = 0 AND r.ZTITLE IS NOT NULL"""
PRI = {1: "!!!", 5: "!!", 9: "!"}  # Apple: 1 high, 5 medium, 9 low, 0 none


def collect(store, extra="", args=()):
    rows = []
    for c in stores(store):
        rows += c.execute(SQL + extra, args).fetchall()
    return rows


def show(rows):
    for t, notes, due, allday, done, doneat, flag, pri, lst, parent, created in rows:
        box = "[x]" if done else "[ ]"
        when = (f"due {d(due, '%Y-%m-%d' if allday else '%Y-%m-%d %H:%M')}" if due else "") + (f" done {d(doneat, '%Y-%m-%d')}" if done and doneat else "")
        marks = (" *flagged*" if flag else "") + (f" {PRI[pri]}" if pri in PRI else "")
        print(f"{box} {'  ' if parent else ''}{t}{marks}  [{lst or '?'}]  {when}".rstrip())
        if notes:
            print(f"      {' '.join(notes.split())[:200]}")
    print(f"-- {len(rows)} reminder(s)", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["lists", "open", "done", "search"])
    ap.add_argument("q", nargs="?")
    ap.add_argument("--list"); ap.add_argument("--due-before"); ap.add_argument("--since")
    ap.add_argument("--all", action="store_true"); ap.add_argument("--store")
    a = ap.parse_args()
    if a.cmd == "lists":
        n = 0
        for c in stores(a.store):
            for name, op, dn in c.execute("""SELECT l.ZNAME, sum(r.ZCOMPLETED=0), sum(r.ZCOMPLETED=1)
                    FROM ZREMCDBASELIST l LEFT JOIN ZREMCDREMINDER r ON r.ZLIST=l.Z_PK AND r.ZMARKEDFORDELETION=0
                    WHERE l.ZMARKEDFORDELETION=0 AND l.ZNAME IS NOT NULL GROUP BY l.Z_PK ORDER BY l.ZNAME"""):
                print(f"{op or 0:>5} open {dn or 0:>5} done  {name}"); n += 1
        print(f"-- {n} list(s)", file=sys.stderr)
        return
    extra, args = "", []
    if a.list:
        extra += " AND l.ZNAME LIKE ?"; args.append(f"%{a.list}%")
    if a.cmd == "open":
        extra += " AND r.ZCOMPLETED = 0"
        if a.due_before:
            extra += " AND r.ZDUEDATE < ?"; args.append(apple(a.due_before) + 86400)
        rows = sorted(collect(a.store, extra, args), key=lambda r: (r[2] is None, r[2] or 0))
    elif a.cmd == "done":
        extra += " AND r.ZCOMPLETED = 1"
        if a.since:
            extra += " AND r.ZCOMPLETIONDATE >= ?"; args.append(apple(a.since))
        rows = sorted(collect(a.store, extra, args), key=lambda r: -(r[5] or 0))
    else:
        if not a.q:
            ap.error("search needs text")
        extra += " AND (r.ZTITLE LIKE ? OR r.ZNOTES LIKE ?)"; args += [f"%{a.q}%"] * 2
        if not a.all:
            extra += " AND r.ZCOMPLETED = 0"
        rows = sorted(collect(a.store, extra, args), key=lambda r: -(r[10] or 0))
    show(rows)


if __name__ == "__main__":
    main()
