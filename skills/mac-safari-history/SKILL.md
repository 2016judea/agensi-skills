---
name: mac-safari-history
description: Search your Safari browsing history, bookmarks and Reading List on a Mac straight from the local History.db and Bookmarks.plist, read-only. Use when asked "what was that site I looked at Tuesday", "every page I visited on example.com last month", "which sites do I visit most", "find my bookmark for the recipe", or "what's in my Reading List".
compatibility: macOS; reads local files only; needs Full Disk Access
---

# Mac Safari history and bookmarks (local, read-only)

`scripts/safari.py`, Python 3 stdlib only.

```bash
python3 scripts/safari.py history --since 2026-10-01 --until 2026-10-07
python3 scripts/safari.py history --domain example.com --limit 300
python3 scripts/safari.py history --search "sourdough"     # url or page title
python3 scripts/safari.py top --since 2026-10-01           # most-visited domains
python3 scripts/safari.py bookmarks --search recipe
python3 scripts/safari.py bookmarks --folder Favorites
python3 scripts/safari.py reading-list
```

## Where the data is

- `~/Library/Safari/History.db` (SQLite): `history_items(id, url, visit_count)` and
  `history_visits(history_item, visit_time, title, load_successful, redirect_destination)`.
  `visit_time` is seconds since 2001-01-01. One item, many visits.
- `~/Library/Safari/Bookmarks.plist`: a tree of `WebBookmarkTypeList` folders and
  `WebBookmarkTypeLeaf` bookmarks. Top level: `BookmarksBar` (shown as Favorites), `BookmarksMenu`,
  `com.apple.ReadingList` (each item has `ReadingList.DateAdded`).

## Traps

- **`plutil -convert json` fails on Bookmarks.plist** ("Invalid object in plist for JSON format")
  because it holds dates and data. Read it with Python's `plistlib` or `plutil -convert xml1`.
- **Redirect hops are visits.** Skip rows with `redirect_destination` set, and failed loads, or a
  single click counts two or three times.
- **The title lives on the visit**, not the item.
- **History.db only holds this Mac's visits** plus what iCloud synced from other devices; Safari
  trims history by the "Remove history items" setting (default one year).
- Private-browsing windows write nothing.

## Permission (TCC)

`~/Library/Safari` needs Full Disk Access for the app running the agent (System Settings > Privacy &
Security > Full Disk Access, then restart it). Without it: `Operation not permitted`.

## Limits

Read-only. For Chrome, read `~/Library/Application Support/Google/Chrome/Default/History` (SQLite,
copy it first: Chrome holds a lock) or use a Chrome bookmarks skill.
