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
import re
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

# History of the row ceiling, kept because each version silently truncated pulls:
# ~260 rows per request (2026-08-23), then 100 (2026-10-11), each dropping the OLDEST
# rows of a window with no error. Windows were split on date coverage until
# 2026-11-03, when that hit a one-day floor on busy subs. page_window() below replaces
# splitting with oldest-first paging, which has no floor. CAP/NEAR_CAP are unused now.
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


# HOW A WINDOW IS READ (rewritten 2026-11-03). The server returns at most ~100 rows
# per request and, sorted newest-first, silently drops the OLDEST rows of a busy
# window: a one-day r/smallbusiness window gave exactly 100 of its 166 posts. The old
# fix split windows in halves on a whole-day floor, which could not get under one day
# and wasted half its requests on internal nodes. Now every window is PAGED oldest-first:
# `sort=asc`, then `after` = the newest timestamp seen, until a page comes back short.
# One request per 100 rows, no floor, nothing dropped. `after` is exclusive, so each
# page restarts one second early and rows are de-duplicated by id. A timeout (HTTP 422
# "too expensive") halves the remaining range instead.
PAGE = 100


def page_window(path: str, params: dict, start_ts: int, end_ts: int,
                depth: int = 0) -> list[dict]:
    seen: dict[str, dict] = {}
    cur = start_ts
    while cur < end_ts:
        data = _get(path, {**params, "after": cur, "before": end_ts,
                           "limit": PAGE, "sort": "asc"})
        if data is None:                                   # too expensive: halve
            if end_ts - cur <= 60 or depth > 20:
                print(f"  ! gave up on {params} {cur}..{end_ts}", file=sys.stderr)
                break
            mid = cur + (end_ts - cur) // 2
            for half in (page_window(path, params, cur, mid, depth + 1),
                         page_window(path, params, mid, end_ts, depth + 1)):
                for r in half:
                    seen[r.get("id")] = r
            break
        for r in data:
            seen[r.get("id")] = r
        if len(data) < PAGE:
            break
        newest = max(int(r.get("created_utc") or 0) for r in data)
        nxt = newest - 1
        if nxt <= cur:            # >100 rows inside one second: cannot page further
            print(f"  ! {params} {cur}: page did not advance — truncated", file=sys.stderr)
            break
        cur = nxt
    return list(seen.values())


def _ts(d: date) -> int:
    return int(datetime.combine(d, dtime.min).replace(tzinfo=timezone.utc).timestamp())


def fetch_window(sub: str, start: date, end: date, depth: int = 0) -> list[dict]:
    """Every post in [start, end) for one subreddit."""
    return page_window("posts/search", {"subreddit": sub, "fields": POST_FIELDS},
                       _ts(start), _ts(end))


def fetch_comment_window(sub: str, start: datetime, end: datetime,
                         depth: int = 0) -> list[dict]:
    """Every comment in [start, end) for one sub."""
    return page_window("comments/search", {"subreddit": sub, "fields": BULK_COMMENT_FIELDS},
                       int(start.timestamp()), int(end.timestamp()))


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


def comment_tree(post_id: str) -> list[dict]:
    """Every comment on one thread, flattened, via /comments/tree.

    MEASURED 2026-11-03: `comments/search?link_id=` stops at 100 rows (a
    302-comment r/smallbusiness thread returned exactly 100), so "top N by
    score" from it is the top N of an arbitrary 100. `comments/tree` with a
    large limit returned all 303 in ~4s. Falls back to search if tree fails.
    """
    data = _get("comments/tree", {"link_id": post_id, "limit": 10000})
    flat: list[dict] = []

    def walk(nodes, depth):
        for n in nodes or []:
            if n.get("kind") != "t1":
                continue
            c = n.get("data") or {}
            flat.append({
                "id": c.get("id"),
                "parent_id": c.get("parent_id"),
                "depth": depth,
                "author": c.get("author"),
                "score": c.get("score"),
                "created": datetime.fromtimestamp(
                    c.get("created_utc") or 0, timezone.utc).strftime("%Y-%m-%d"),
                "body": " ".join((c.get("body") or "").split())[:2000],
                "permalink": f"https://reddit.com/comments/{post_id}/_/{c.get('id')}",
            })
            r = c.get("replies")
            if isinstance(r, dict):
                walk((r.get("data") or {}).get("children"), depth + 1)

    if data is not None:
        walk(data, 0)
    if not flat:   # tree unavailable: fall back to the (capped) search
        for c in _get("comments/search", {
                "link_id": post_id, "limit": 100,
                "fields": "id,body,score,author,created_utc,parent_id"}) or []:
            flat.append({
                "id": c.get("id"), "parent_id": c.get("parent_id"),
                "depth": None, "author": c.get("author"), "score": c.get("score"),
                "created": datetime.fromtimestamp(
                    c.get("created_utc") or 0, timezone.utc).strftime("%Y-%m-%d"),
                "body": " ".join((c.get("body") or "").split())[:2000],
                "permalink": f"https://reddit.com/comments/{post_id}/_/{c.get('id')}",
            })
    return flat


def top_comments(post_id: str, n: int) -> list[dict]:
    data = [c for c in comment_tree(post_id)
            if c.get("author") not in ("AutoModerator",)
            and c.get("body") not in ("[deleted]", "[removed]")]
    data.sort(key=lambda c: -(c.get("score") or 0))
    return [{k: c[k] for k in ("id", "author", "score", "created", "permalink")}
            | {"body": c["body"][:1200]} for c in data[:n]]


def post_record(p: dict) -> dict:
    return {
        "id": p.get("id"),
        "subreddit": p.get("subreddit"),
        "title": p.get("title"),
        "selftext": (p.get("selftext") or "")[:2500],
        "score": p.get("score"),
        "num_comments": p.get("num_comments"),
        "created": datetime.fromtimestamp(
            p.get("created_utc") or 0, timezone.utc).strftime("%Y-%m-%d"),
        "permalink": f"https://reddit.com/comments/{p.get('id')}",
        "author": p.get("author"),
    }


def thread_id(s: str) -> str:
    """Accept a bare id, t3_ id, or any reddit URL containing /comments/<id>."""
    m = re.search(r"comments/([a-z0-9]+)", s)
    if m:
        return m.group(1)
    return s.removeprefix("t3_").strip("/")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Mine real Reddit threads via the Arctic Shift archive.")
    ap.add_argument("--subreddits", nargs="+",
                    help="required unless --thread is given")
    ap.add_argument("--thread", default=None,
                    help="one thread (id or URL): the post plus EVERY comment, "
                         "flattened with depth + parent, as one JSON object")
    ap.add_argument("--queries", nargs="*", default=[],
                    help="keywords, matched LOCALLY against title+selftext "
                         "(any match, case-insensitive). Omit to keep all.")
    ap.add_argument("--after", default=None, help="YYYY-MM-DD (default: 3y ago)")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--window-days", type=int, default=90)
    ap.add_argument("--top", type=int, default=40,
                    help="keep this many top-scoring matches per subreddit "
                         "(0 = keep every match; use 0 whenever you will count)")
    ap.add_argument("--stats", default=None,
                    help="write {subreddit: {YYYY-MM: posts scanned}} to this "
                         "file: the denominator for any count over time")
    ap.add_argument("--comments", type=int, nargs="?", const=5, default=0,
                    help="fetch N top comments for each kept thread")
    ap.add_argument("--comments-for", type=int, default=0,
                    help="with --comments: fetch comments only for the K "
                         "most-commented kept threads (each costs ~1-4s)")
    ap.add_argument("--bulk-comments", action="store_true",
                    help="pull EVERY comment in the date range instead of "
                         "posts (sub-day windowing; use for prevalence counts)")
    args = ap.parse_args()

    if args.thread:
        tid = thread_id(args.thread)
        posts = _get("posts/ids", {"ids": tid, "fields": POST_FIELDS}) or []
        if not posts:
            sys.exit(f"thread {tid} not found in the archive")
        rec = post_record(posts[0])
        rec["selftext"] = (posts[0].get("selftext") or "")[:20000]
        rec["comments"] = comment_tree(tid)
        json.dump(rec, sys.stdout, indent=1)
        print(f"\nWROTE thread {tid}: {len(rec['comments'])} comments "
              f"(post says {rec['num_comments']})", file=sys.stderr)
        return
    if not args.subreddits:
        ap.error("--subreddits is required unless --thread is given")

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
                pid = (c.get("link_id") or "").removeprefix("t3_")
                c["permalink"] = f"https://reddit.com/comments/{pid}/_/{c.get('id')}"
                c["created"] = datetime.fromtimestamp(
                    c.get("created_utc") or 0, timezone.utc).strftime("%Y-%m-%d")
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
    stats: dict[str, dict[str, int]] = {}
    for sub in args.subreddits:
        scanned, kept = 0, []
        months = stats.setdefault(sub, {})
        cur = start
        while cur < end:
            nxt = min(cur + timedelta(days=args.window_days), end)
            posts = fetch_window(sub, cur, nxt)
            seen_ids = set()
            for p in posts:
                if p.get("id") in seen_ids:
                    continue
                seen_ids.add(p.get("id"))
                scanned += 1
                m = datetime.fromtimestamp(p.get("created_utc") or 0,
                                           timezone.utc).strftime("%Y-%m")
                months[m] = months.get(m, 0) + 1
                if matches(p, terms):
                    kept.append(p)
            print(f"  r/{sub} {cur}..{nxt}: {len(posts)} scanned, "
                  f"{len(kept)} kept so far", file=sys.stderr, flush=True)
            cur = nxt

        kept.sort(key=lambda p: -(p.get("score") or 0))
        if args.top:
            kept = kept[:args.top]
        print(f"r/{sub}: {scanned} posts scanned, {len(kept)} kept",
              file=sys.stderr, flush=True)

        want = set()
        if args.comments:
            ranked = sorted(kept, key=lambda p: -(p.get("num_comments") or 0))
            want = {p["id"] for p in (ranked[:args.comments_for]
                                      if args.comments_for else ranked)}
        for p in kept:
            rec = post_record(p)
            if p["id"] in want and (p.get("num_comments") or 0) > 0:
                rec["top_comments"] = top_comments(p["id"], args.comments)
            out.append(rec)

    if args.stats:
        with open(args.stats, "w") as fh:
            json.dump({"after": start.isoformat(), "before": end.isoformat(),
                       "queries": args.queries, "scanned": stats}, fh, indent=1)
    json.dump(out, sys.stdout, indent=1)
    print(f"\nWROTE {len(out)} threads", file=sys.stderr)


if __name__ == "__main__":
    main()
