---
name: mac-screen-time
description: See how you actually spend time on your Mac: hours per app, per day, and per hour of the day, from the app-usage log behind Screen Time (knowledgeC.db), read-only. Use when asked "how much time did I spend in Slack this week", "what apps do I use most", "how many hours was I on the computer each day", or "when in the day do I work".
compatibility: macOS; reads local files only; needs Full Disk Access
---

# Mac Screen Time (local, read-only)

`scripts/screentime.py`, Python 3 stdlib only.

```bash
python3 scripts/screentime.py apps                      # last 7 days, top 20 apps
python3 scripts/screentime.py apps --since 2026-10-01 --until 2026-10-14
python3 scripts/screentime.py daily --days 28
python3 scripts/screentime.py app slack --days 14       # name or bundle id, per day
python3 scripts/screentime.py hours                     # hour-of-day profile
```

```
 13h 31m    66%  Web Browser
  6h 20m    31%  Code Editor
```

## Where the data is

`~/Library/Application Support/Knowledge/knowledgeC.db` (SQLite, WAL). Table `ZOBJECT`, rows with
`ZSTREAMNAME = '/app/usage'`: `ZVALUESTRING` is the bundle id in the foreground, `ZSTARTDATE` and
`ZENDDATE` are seconds since 2001-01-01. Bundle ids are turned into names by reading
`Contents/Info.plist` of each app in `/Applications`, `/System/Applications` and `~/Applications`.

## Traps

- **Only about four weeks are kept.** Older ranges return nothing, not an error.
- **This is foreground time on this Mac only.** iPhone and iPad usage synced to Screen Time is not
  in this table; it lives in Biome streams under `~/Library/Biome` in an undocumented format.
- Very short rows (1-2 s) are app switches; they add little but are real.
- Other streams in the same table (`/display/isBacklit`, `/notification/usage`, `/bluetooth/isConnected`)
  follow the same shape if you need screen-on time or notifications.

## Permission (TCC)

Full Disk Access for the app running the agent (System Settings > Privacy & Security > Full Disk
Access, then restart it). Screen Time itself does not need to be switched on for `/app/usage` to fill.

## Limits

Read-only, local only. Web-domain time is not recorded here.
