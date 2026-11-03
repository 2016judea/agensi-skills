#!/usr/bin/env python3
"""Read Safari history (History.db) and bookmarks (Bookmarks.plist). Read-only, on-device.

Usage:
  safari.py history [--since D] [--until D] [--domain X] [--search TEXT] [--limit 100]
  safari.py top [--since D] [--limit 25]           most-visited domains
  safari.py bookmarks [--search TEXT] [--folder X]
  safari.py reading-list
Dates are YYYY-MM-DD.
"""
import argparse, os, plistlib, sqlite3, sys
from datetime import datetime
from urllib.parse import urlparse

SAFARI = os.path.expanduser("~/Library/Safari")
APPLE = 978307200


def history_db():
    p = os.path.join(SAFARI, "History.db")
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        c.execute("SELECT 1 FROM history_visits LIMIT 1")
        return c
    except sqlite3.Error as e:
        sys.exit(f"Cannot open History.db ({e}). Grant Full Disk Access to your terminal (see SKILL.md).")


def apple(day):
    return datetime.strptime(day, "%Y-%m-%d").timestamp() - APPLE


def where(a):
    w, args = ["v.load_successful = 1", "v.redirect_destination IS NULL"], []  # skip redirect hops
    if getattr(a, "since", None):
        w.append("v.visit_time >= ?"); args.append(apple(a.since))
    if getattr(a, "until", None):
        w.append("v.visit_time < ?"); args.append(apple(a.until) + 86400)
    if getattr(a, "domain", None):
        w.append("i.url LIKE ?"); args.append(f"%://%{a.domain}%")
    if getattr(a, "search", None):
        w.append("(i.url LIKE ? OR v.title LIKE ?)"); args += [f"%{a.search}%"] * 2
    return " AND ".join(w), args


def history(a):
    c = history_db()
    w, args = where(a)
    rows = c.execute(f"""SELECT v.visit_time, v.title, i.url FROM history_visits v
        JOIN history_items i ON i.id = v.history_item WHERE {w} ORDER BY v.visit_time DESC LIMIT ?""", args + [a.limit]).fetchall()
    for t, title, url in rows:
        print(f"{datetime.fromtimestamp(t + APPLE):%Y-%m-%d %H:%M}  {(title or '')[:60]:60}  {url}")
    print(f"-- {len(rows)} visit(s)", file=sys.stderr)


def top(a):
    c = history_db()
    w, args = where(a)
    counts = {}
    for (url,) in c.execute(f"SELECT i.url FROM history_visits v JOIN history_items i ON i.id=v.history_item WHERE {w}", args):
        host = urlparse(url).netloc.removeprefix("www.")
        counts[host] = counts.get(host, 0) + 1
    for host, n in sorted(counts.items(), key=lambda x: -x[1])[:a.limit]:
        print(f"{n:>6}  {host}")


NICE = {"BookmarksBar": "Favorites", "BookmarksMenu": "Bookmarks Menu"}


def walk(node, path, out):
    t = node.get("WebBookmarkType")
    if t == "WebBookmarkTypeLeaf":
        out.append((path, node.get("URIDictionary", {}).get("title") or node.get("Title") or "", node.get("URLString", ""), node))
    for ch in node.get("Children", []) or []:
        name = ch.get("Title") or ""
        walk(ch, path + [NICE.get(name, name)] if ch.get("WebBookmarkType") == "WebBookmarkTypeList" else path, out)


def bookmarks():
    p = os.path.join(SAFARI, "Bookmarks.plist")
    try:
        # Binary plist with date/data values: `plutil -convert json` refuses it, plistlib reads it.
        root = plistlib.load(open(p, "rb"))
    except PermissionError:
        sys.exit("Cannot read Bookmarks.plist. Grant Full Disk Access to your terminal (see SKILL.md).")
    out = []
    walk(root, [], out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["history", "top", "bookmarks", "reading-list"])
    ap.add_argument("--since"); ap.add_argument("--until"); ap.add_argument("--domain")
    ap.add_argument("--search"); ap.add_argument("--folder"); ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.cmd == "history":
        a.limit = a.limit or 100; return history(a)
    if a.cmd == "top":
        a.limit = a.limit or 25; return top(a)
    rows = bookmarks()
    if a.cmd == "reading-list":
        rows = [r for r in rows if r[0][:1] == ["com.apple.ReadingList"]]
        for path, title, url, node in rows:
            added = node.get("ReadingList", {}).get("DateAdded")
            print(f"{added:%Y-%m-%d}  {title[:60]:60}  {url}" if added else f"{'':10}  {title[:60]:60}  {url}")
    else:
        rows = [r for r in rows if r[0][:1] != ["com.apple.ReadingList"]]
        if a.folder:
            rows = [r for r in rows if any(a.folder.lower() in f.lower() for f in r[0])]
        if a.search:
            s = a.search.lower()
            rows = [r for r in rows if s in r[1].lower() or s in r[2].lower()]
        for path, title, url, node in rows:
            folder = "/".join(path)
            print(f"{folder[:30]:30}  {title[:50]:50}  {url}")
    print(f"-- {len(rows)} item(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
