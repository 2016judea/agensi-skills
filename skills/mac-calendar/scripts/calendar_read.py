#!/usr/bin/env python3
"""Read Calendar.app events straight from the local Calendar.sqlitedb. Read-only, on-device.

Usage:
  calendar_read.py calendars                               every calendar, its account, event count
  calendar_read.py events [--since D] [--until D] [--days N] [--calendar NAME] [--search TEXT] [--detail]
  calendar_read.py search <text> [--detail]                all-time search: title, location, notes
  calendar_read.py today | week
Defaults: events = today through 7 days out. Recurring events are expanded. Dates are YYYY-MM-DD.
"""
import argparse, os, sqlite3, sys
from datetime import datetime, timedelta, timezone

DB = os.path.expanduser("~/Library/Group Containers/group.com.apple.calendar/Calendar.sqlitedb")
APPLE = 978307200
EVENT = 2  # CalendarItem.entity_type: 2 = event (reminders live in the Reminders store now)


def conn():
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        c.execute("SELECT 1 FROM CalendarItem LIMIT 1")
        return c
    except sqlite3.Error as e:
        sys.exit(f"Cannot open Calendar.sqlitedb ({e}). Grant Full Disk Access to your terminal (see SKILL.md).")


def to_apple(day):
    return datetime.strptime(day, "%Y-%m-%d").timestamp() - APPLE


def when(start, end, all_day, floating=False):
    if all_day:  # all-day events show the date only
        # master rows store all-day dates as UTC midnight ("_float" tz); OccurrenceCache uses local midnight
        s = datetime.fromtimestamp(start + APPLE, timezone.utc) if floating else datetime.fromtimestamp(start + APPLE)
        days = round(((end or start) - start) / 86400) if end else 1
        return f"{s:%a %Y-%m-%d}  all day" + (f" ({days} days)" if days > 1 else "")
    s = datetime.fromtimestamp(start + APPLE)
    e = datetime.fromtimestamp(end + APPLE) if end else None
    return f"{s:%a %Y-%m-%d %H:%M}-{e:%H:%M}" if e and e.date() == s.date() else f"{s:%a %Y-%m-%d %H:%M}" + (f" to {e:%Y-%m-%d %H:%M}" if e else "")


SEL = """SELECT i.ROWID, i.summary, cal.title, i.all_day, l.title, l.address, i.description, i.url,
                i.conference_url, i.has_attendees, i.status"""
JOIN = """FROM CalendarItem i JOIN Calendar cal ON cal.ROWID=i.calendar_id
          LEFT JOIN Location l ON l.ROWID=i.location_id"""


def attendees(c, eid):
    return [(n or e or p or "?", st) for n, e, p, st in c.execute(
        """SELECT COALESCE(id.display_name, ''), p.email, p.phone_number, p.status FROM Participant p
           LEFT JOIN Identity id ON id.ROWID=p.identity_id WHERE p.owner_id=? AND p.entity_type=7""", (eid,))]


def show(c, rows, detail):
    STATUS = {0: "", 1: "", 2: "tentative", 3: "CANCELLED"}
    for row in rows:
        start, end, r = row[:3]
        floating = len(row) > 3
        eid, title, cal, allday, lt, la, desc, url, conf, has_att, st = r
        loc = " | ".join(x for x in dict.fromkeys((lt, la)) if x)
        flag = STATUS.get(st, "")
        print(f"{when(start, end, allday, floating):34} {title or '(no title)'}  [{cal}]" + (f"  {flag}" if flag else ""))
        if detail:
            if loc: print(f"{'':36}where: {loc}")
            if conf: print(f"{'':36}call:  {conf}")
            if url: print(f"{'':36}url:   {url}")
            if has_att:
                for n, s in attendees(c, eid):
                    print(f"{'':36}with:  {n}")
            if desc: print(f"{'':36}notes: " + " ".join(desc.split())[:300])
    print(f"-- {len(rows)} event(s)", file=sys.stderr)


def events(c, since, until, calendar=None, search=None):
    lo, hi = to_apple(since), to_apple(until) + 86400
    extra, args = "", []
    if calendar:
        extra += " AND cal.title LIKE ?"; args.append(f"%{calendar}%")
    if search:
        extra += " AND (i.summary LIKE ? OR l.title LIKE ? OR i.description LIKE ?)"; args += [f"%{search}%"] * 3
    out, seen = [], set()
    # OccurrenceCache holds every occurrence (recurrences expanded) in a rolling window, about
    # one year back to a few years ahead. Outside it, fall back to the master rows below.
    for r in c.execute(f"""SELECT COALESCE(o.occurrence_start_date, o.occurrence_date), o.occurrence_end_date, {SEL[7:]}
            {JOIN} JOIN OccurrenceCache o ON o.event_id=i.ROWID
            WHERE i.entity_type={EVENT} AND COALESCE(o.occurrence_start_date, o.occurrence_date) < ?
              AND COALESCE(o.occurrence_end_date, o.occurrence_date) >= ? {extra}""", [hi, lo] + args):
        key = (r[2], int(r[0]))
        if key not in seen:
            seen.add(key); out.append((r[0], r[1], r[2:]))
    cached = {k[0] for k in seen}
    for r in c.execute(f"""SELECT i.start_date, i.end_date, {SEL[7:]} {JOIN}
            WHERE i.entity_type={EVENT} AND i.start_date < ? AND i.end_date >= ? {extra}""", [hi, lo] + args):
        if r[2] not in cached:
            out.append((r[0], r[1], r[2:], "master"))
    return sorted(out, key=lambda x: x[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["calendars", "events", "search", "today", "week"])
    ap.add_argument("q", nargs="?")
    ap.add_argument("--since"); ap.add_argument("--until"); ap.add_argument("--days", type=int)
    ap.add_argument("--calendar"); ap.add_argument("--search"); ap.add_argument("--detail", action="store_true")
    a = ap.parse_args()
    c = conn()
    today = datetime.now().strftime("%Y-%m-%d")
    if a.cmd == "calendars":
        for t, store, n in c.execute(f"""SELECT cal.title, s.name, count(i.ROWID) FROM Calendar cal
                JOIN Store s ON s.ROWID=cal.store_id LEFT JOIN CalendarItem i ON i.calendar_id=cal.ROWID
                AND i.entity_type={EVENT} GROUP BY cal.ROWID ORDER BY s.name, cal.title"""):
            print(f"{n:>6}  {store:22} {t}")
        return
    if a.cmd == "search":
        rows = [(r[0], r[1], r[2:], "master") for r in c.execute(f"""SELECT i.start_date, i.end_date, {SEL[7:]} {JOIN}
                WHERE i.entity_type={EVENT} AND (i.summary LIKE ? OR l.title LIKE ? OR l.address LIKE ? OR i.description LIKE ?)
                ORDER BY i.start_date""", [f"%{a.q}%"] * 4)]
        print("(recurring events show their first occurrence)", file=sys.stderr)
        return show(c, rows, a.detail)
    since = a.since or today
    days = 0 if a.cmd == "today" else 6 if a.cmd == "week" else (a.days if a.days is not None else 7)
    until = a.until or (datetime.strptime(since, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
    show(c, events(c, since, until, a.calendar, a.search), a.detail)


if __name__ == "__main__":
    main()
