#!/usr/bin/env python3
"""Read this Mac's app-usage history (the data behind Screen Time) from knowledgeC.db. Read-only.

Usage:
  screentime.py apps [--since D] [--until D] [--days 7] [--limit 20]   time in front of each app
  screentime.py daily [--days 14]                                       total foreground time per day
  screentime.py app <name-or-bundle-id> [--days 14]                     one app, per day
  screentime.py hours [--days 7]                                        when in the day you use the Mac
Dates are YYYY-MM-DD. macOS keeps roughly the last four weeks.
"""
import argparse, glob, os, plistlib, sqlite3, sys
from datetime import datetime, timedelta

DB = os.path.expanduser("~/Library/Application Support/Knowledge/knowledgeC.db")
APPLE = 978307200


def conn():
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        c.execute("SELECT 1 FROM ZOBJECT LIMIT 1")
        return c
    except sqlite3.Error as e:
        sys.exit(f"Cannot open knowledgeC.db ({e}). Grant Full Disk Access to your terminal (see SKILL.md).")


_NAMES = None
def app_name(bundle):
    """Bundle id -> display name, from the Info.plist of every installed app."""
    global _NAMES
    if _NAMES is None:
        _NAMES = {}
        for root in ("/Applications", "/System/Applications", "/System/Applications/Utilities",
                     os.path.expanduser("~/Applications"), "/Applications/Utilities"):
            for app in glob.glob(os.path.join(root, "*.app")):
                try:
                    info = plistlib.load(open(os.path.join(app, "Contents", "Info.plist"), "rb"))
                    _NAMES[info.get("CFBundleIdentifier", "")] = info.get("CFBundleDisplayName") or info.get("CFBundleName") or os.path.basename(app)[:-4]
                except Exception:
                    pass
    return _NAMES.get(bundle) or bundle


def hm(sec):
    h, m = divmod(int(sec) // 60, 60)
    return f"{h:>3}h {m:02}m"


def rows(c, since, until, bundle=None):
    q = """SELECT ZVALUESTRING, ZSTARTDATE, ZENDDATE FROM ZOBJECT
           WHERE ZSTREAMNAME = '/app/usage' AND ZSTARTDATE >= ? AND ZSTARTDATE < ?"""
    args = [since.timestamp() - APPLE, until.timestamp() - APPLE]
    if bundle:
        q += " AND ZVALUESTRING = ?"; args.append(bundle)
    return [(b, datetime.fromtimestamp(s + APPLE), max(0, e - s)) for b, s, e in c.execute(q, args) if b]


def window(a):
    until = datetime.strptime(a.until, "%Y-%m-%d") + timedelta(days=1) if a.until else datetime.now()
    since = datetime.strptime(a.since, "%Y-%m-%d") if a.since else (until - timedelta(days=a.days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return since, until


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["apps", "daily", "app", "hours"])
    ap.add_argument("q", nargs="?")
    ap.add_argument("--since"); ap.add_argument("--until"); ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    a.days = a.days or (14 if a.cmd in ("daily", "app") else 7)
    c = conn()
    since, until = window(a)
    if a.cmd == "app":
        if not a.q:
            ap.error("app needs a name or bundle id")
        all_ids = {b for (b,) in c.execute("SELECT DISTINCT ZVALUESTRING FROM ZOBJECT WHERE ZSTREAMNAME='/app/usage'") if b}
        hits = [b for b in all_ids if a.q.lower() in b.lower() or a.q.lower() in app_name(b).lower()]
        if not hits:
            sys.exit(f"No usage recorded for {a.q!r}. Try `screentime.py apps --days 28`.")
        per = {}
        for b in hits:
            for _, s, d in rows(c, since, until, b):
                per[s.date()] = per.get(s.date(), 0) + d
        print(", ".join(app_name(b) for b in hits))
        for day in sorted(per):
            print(f"{day:%a %Y-%m-%d}  {hm(per[day])}")
        return
    data = rows(c, since, until)
    print(f"{since:%Y-%m-%d} to {until:%Y-%m-%d %H:%M}", file=sys.stderr)
    if a.cmd == "apps":
        tot = {}
        for b, _, d in data:
            tot[b] = tot.get(b, 0) + d
        grand = sum(tot.values()) or 1
        for b, sec in sorted(tot.items(), key=lambda x: -x[1])[:a.limit]:
            print(f"{hm(sec)}  {100 * sec / grand:4.0f}%  {app_name(b)}")
        print(f"{hm(grand)}  total", file=sys.stderr)
    elif a.cmd == "daily":
        per = {}
        for _, s, d in data:
            per[s.date()] = per.get(s.date(), 0) + d
        for day in sorted(per):
            print(f"{day:%a %Y-%m-%d}  {hm(per[day])}  " + "#" * int(per[day] / 1800))
    else:
        per = [0] * 24
        for _, s, d in data:
            per[s.hour] += d
        for h, sec in enumerate(per):
            print(f"{h:02}:00  {hm(sec)}  " + "#" * int(sec / 900))


if __name__ == "__main__":
    main()
