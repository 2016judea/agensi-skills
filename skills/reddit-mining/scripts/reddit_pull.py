#!/usr/bin/env python3
"""Pull real Reddit threads + comments via the Arctic Shift archive.

Replaces the PullPush transport, which as of 2026-08-16 returns HTTP 429 with
  {"error": "Rate limit exceeded. This website does not provide free scraping
   resources for agents..."}
to every unauthenticated request. That is a policy block, not a throttle — no
backoff clears it.

Arctic Shift works, with one hard constraint that dictates this design:
its server-side keyword search (`query`/`selftext`/`body`) TIMES OUT even on a
one-month window of a mid-size subreddit, while a date-windowed *listing*
returns 1000 posts in ~6s. So we never ask the server to search. We bulk-read
date windows and filter locally. Slower to describe, far faster in practice,
and it returns a real corpus rather than a search index's guess at relevance.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime

API = "https://arctic-shift.photon-reddit.com/api"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Arctic Shift's real per-request ceiling is ~260 rows, NOT the 1000 the docs
# imply, and `limit` itself is rejected above 100 ("'limit' must be between 1
# and 100"), so `limit=auto` is the only way to get more than 100 at a time.
# MEASURED 2026-08-23: one 90-day r/AnalogCommunity request returned 258 posts
# spanning only its LAST FOUR DAYS. The other 86 days were dropped in silence.
# A count-only cap check at 1000 therefore never fires, and the run reads as
# complete coverage while holding ~4% of the period, biased to the window's end.
#
# So truncation is detected by DATE COVERAGE, not by row count: if the oldest
# row we got back is newer than the window's start, the server didn't reach the
# beginning and the window must be split. NEAR_CAP only guards against splitting
# a quiet sub that genuinely has no posts early in its window.
# MEASURED 2026-10-11: `limit=auto` on posts/search now returns at most 100
# rows (r/Minneapolis, 40-day window: exactly 100). With NEAR_CAP at 200 the
# split never fired and every 90-day window silently kept only its newest 100
# posts (600 posts "scanned" for 16 months of r/Minneapolis). NEAR_CAP must sit
# BELOW whatever `auto` currently returns; 90 is safe for 100 and for 260.
CAP = 1000
NEAR_CAP = 90

POST_FIELDS = "id,title,selftext,score,num_comments,created_utc,subreddit,author"
COMMENT_FIELDS = "body,score,author,created_utc"
# Bulk comment pulls need `id` so overlapping windows can be de-duplicated.
BULK_COMMENT_FIELDS = "id,body,score,author,created_utc,link_id"


def _get(path: str, params: dict, tries: int = 3) -> list[dict] | None:
    """Return data list, or None if the query was too expensive / errored.

    Arctic Shift reports "query too expensive" as **HTTP 422 with the message
    in the JSON body** — which urllib raises as an exception. Read the body on
    every error status; a handler that only logs e.code turns a splittable
    timeout into an opaque retry loop. (That bug cost a full debug cycle here,
    and is the same mistake that hid PullPush's real shutdown message.)
    """
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode())
            except Exception:
                print(f"  ! HTTP {e.code} (unparseable body)", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
                continue
        except Exception as e:  # network blip, malformed JSON
            print(f"  ! {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            time.sleep(3 * (attempt + 1))
            continue

        if payload.get("data") is not None:
            return payload["data"]
        err = payload.get("error", "")
        if "imeout" in err:
            return None          # caller halves the window and retries
        print(f"  ! api error: {err}", file=sys.stderr, flush=True)
        return None
    return None


def fetch_window(sub: str, start: date, end: date, depth: int = 0) -> list[dict]:
    """Pull every post in [start, end) for one subreddit, splitting on cap."""
    data = _get("posts/search", {
        "subreddit": sub,
        "after": start.isoformat(),
        "before": end.isoformat(),
        "limit": "auto",
        "fields": POST_FIELDS,
    })

    span = (end - start).days
    if data is None:                       # timeout — halve and retry
        if span <= 1 or depth > 8:
            print(f"  ! gave up on r/{sub} {start}..{end}", file=sys.stderr)
            return []
        mid = start + timedelta(days=span // 2)
        return (fetch_window(sub, start, mid, depth + 1)
                + fetch_window(sub, mid, end, depth + 1))

    # Did the response actually reach the start of the window?
    start_ts = datetime.combine(start, dtime.min).replace(
        tzinfo=timezone.utc).timestamp()
    oldest = min((p.get("created_utc") or 0) for p in data) if data else start_ts
    short = len(data) >= NEAR_CAP and oldest > start_ts + 3600

    if (len(data) >= CAP or short) and span > 1 and depth <= 8:
        # Truncated. Split rather than silently dropping the remainder.
        mid = start + timedelta(days=span // 2)
        return (fetch_window(sub, start, mid, depth + 1)
                + fetch_window(sub, mid, end, depth + 1))

    if len(data) >= CAP or short:
        print(f"  ! r/{sub} {start}..{end} returned {len(data)} rows starting "
              f"only at {datetime.utcfromtimestamp(oldest):%Y-%m-%d} and cannot "
              f"be split further — results truncated", file=sys.stderr)
    return data


# The comments endpoint truncates HARDER than posts, and sub-day windows are
# mandatory. Measured 2026-08-23 on r/physicaltherapy:
#   8 days  -> 113 rows, oldest only in the LAST day of the window
#   1 day   -> 100 rows, spanning only 14:08-23:47 (the last 10 hours)
#   2 x 12h -> 70 + 112 = 182 rows for that same day
# `limit=auto` reaches ~260 on posts/search but only ~100 here, and it drops the
# OLDEST rows, so a naive day-by-day loop silently undercounts by ~45% per day
# and a month-window loop undercounts ~6x. fetch_window() cannot be reused: it
# splits on whole days and bottoms out at span<=1, which is above the depth at
# which comments still truncate. Hence a parallel walker in SECONDS.
# NEAR_CAP matters as much here as it does for posts: without it, a window that
# genuinely holds one comment at 10:12 looks "truncated" because the oldest row
# is newer than the window start, and the walker splits to the floor on every
# sparse window. Measured cap on this endpoint is ~100-113 rows.
FLOOR_SECONDS = 900
NEAR_CAP_COMMENTS = 90


def fetch_comment_window(sub: str, start: datetime, end: datetime,
                         depth: int = 0) -> list[dict]:
    """Every comment in [start, end) for one sub, splitting on date coverage."""
    data = _get("comments/search", {
        "subreddit": sub,
        "after": start.isoformat().replace("+00:00", ""),
        "before": end.isoformat().replace("+00:00", ""),
        "limit": "auto",
        "fields": BULK_COMMENT_FIELDS,
    })

    span = (end - start).total_seconds()
    if data is None:                       # timeout — halve and retry
        if span <= FLOOR_SECONDS or depth > 24:
            print(f"  ! gave up on r/{sub} {start}..{end}", file=sys.stderr)
            return []
        mid = start + timedelta(seconds=span / 2)
        return (fetch_comment_window(sub, start, mid, depth + 1)
                + fetch_comment_window(sub, mid, end, depth + 1))

    if not data:
        return []

    # Truncated if the oldest row we got is newer than the window's start.
    oldest = min(c.get("created_utc") or 0 for c in data)
    short = (len(data) >= NEAR_CAP_COMMENTS
             and oldest > start.timestamp() + 60)

    if short and span > FLOOR_SECONDS and depth <= 24:
        mid = start + timedelta(seconds=span / 2)
        return (fetch_comment_window(sub, start, mid, depth + 1)
                + fetch_comment_window(sub, mid, end, depth + 1))

    if short:
        print(f"  ! r/{sub} {start:%Y-%m-%d %H:%M}..{end:%H:%M} returned "
              f"{len(data)} rows starting only at "
              f"{datetime.fromtimestamp(oldest, timezone.utc):%Y-%m-%d %H:%M} "
              f"and cannot be split further — truncated", file=sys.stderr)
    return data


def fetch_comments(sub: str, start: date, end: date) -> list[dict]:
    """Bulk-pull a sub's comments across [start, end), de-duplicated by id."""
    s = datetime.combine(start, dtime.min).replace(tzinfo=timezone.utc)
    e = datetime.combine(end, dtime.min).replace(tzinfo=timezone.utc)
    seen: dict[str, dict] = {}
    day = s
    while day < e:
        nxt = min(day + timedelta(days=1), e)
        got = fetch_comment_window(sub, day, nxt)
        for c in got:
            if c.get("id"):
                seen[c["id"]] = c
        print(f"  {day:%Y-%m-%d}  +{len(got):<5} total {len(seen):,}",
              file=sys.stderr, flush=True)
        day = nxt
    return list(seen.values())


def matches(post: dict, terms: list[str]) -> bool:
    if not terms:
        return True
    hay = ((post.get("title") or "") + " " + (post.get("selftext") or "")).lower()
    return any(t in hay for t in terms)


def top_comments(post_id: str, n: int) -> list[dict]:
    data = _get("comments/search", {
        "link_id": post_id, "limit": max(n * 4, 25), "fields": COMMENT_FIELDS,
    }) or []
    data.sort(key=lambda c: -(c.get("score") or 0))
    return [{"score": c.get("score"),
             "body": " ".join((c.get("body") or "").split())[:1200]}
            for c in data[:n]]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Mine real Reddit threads via the Arctic Shift archive.")
    ap.add_argument("--subreddits", nargs="+", required=True)
    ap.add_argument("--queries", nargs="*", default=[],
                    help="keywords, matched LOCALLY against title+selftext "
                         "(any match, case-insensitive). Omit to keep all.")
    ap.add_argument("--after", default=None, help="YYYY-MM-DD (default: 3y ago)")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--top", type=int, default=40,
                    help="keep this many top-scoring matches per subreddit")
    ap.add_argument("--comments", type=int, nargs="?", const=5, default=0,
                    help="fetch N top comments for each kept thread")
    ap.add_argument("--bulk-comments", action="store_true",
                    help="pull EVERY comment in the date range instead of "
                         "posts (sub-day windowing; use for prevalence counts)")
    args = ap.parse_args()

    end = (datetime.strptime(args.before, "%Y-%m-%d").date()
           if args.before else date.today())
    start = (datetime.strptime(args.after, "%Y-%m-%d").date()
             if args.after else end - timedelta(days=365 * 3))
    terms = [q.lower() for q in args.queries]

    if args.bulk_comments:
        # Prevalence work needs the whole comment corpus, not top-N per post.
        allc: list[dict] = []
        for sub in args.subreddits:
            print(f"r/{sub} comments {start}..{end}", file=sys.stderr)
            got = fetch_comments(sub, start, end)
            for c in got:
                c["subreddit"] = sub
            print(f"r/{sub}: {len(got):,} comments", file=sys.stderr, flush=True)
            allc.extend(got)
        if terms:
            allc = [c for c in allc
                    if any(t in (c.get("body") or "").lower() for t in terms)]
            print(f"filtered to {len(allc):,} matching", file=sys.stderr)
        json.dump(allc, sys.stdout)
        print(f"\nWROTE {len(allc):,} comments", file=sys.stderr)
        return

    out: list[dict] = []
    for sub in args.subreddits:
        scanned, kept = 0, []
        cur = start
        while cur < end:
            nxt = min(cur + timedelta(days=args.window_days), end)
            posts = fetch_window(sub, cur, nxt)
            scanned += len(posts)
            kept.extend(p for p in posts if matches(p, terms))
            print(f"  r/{sub} {cur}..{nxt}: {len(posts)} scanned, "
                  f"{len(kept)} kept so far", file=sys.stderr, flush=True)
            cur = nxt

        kept.sort(key=lambda p: -(p.get("score") or 0))
        kept = kept[:args.top]
        print(f"r/{sub}: {scanned} posts scanned, {len(kept)} kept",
              file=sys.stderr, flush=True)

        for p in kept:
            rec = {
                "subreddit": p.get("subreddit"),
                "title": p.get("title"),
                "selftext": (p.get("selftext") or "")[:2500],
                "score": p.get("score"),
                "num_comments": p.get("num_comments"),
                "created": datetime.utcfromtimestamp(
                    p.get("created_utc", 0)).strftime("%Y-%m-%d"),
                "permalink": f"https://reddit.com/comments/{p.get('id')}",
                "author": p.get("author"),
            }
            if args.comments:
                rec["top_comments"] = top_comments(p["id"], args.comments)
            out.append(rec)

    json.dump(out, sys.stdout, indent=1)
    print(f"\nWROTE {len(out)} threads", file=sys.stderr)


if __name__ == "__main__":
    main()
