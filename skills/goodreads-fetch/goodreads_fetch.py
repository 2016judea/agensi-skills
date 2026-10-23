#!/usr/bin/env python3
"""Pull a Goodreads "read" shelf via the PUBLIC RSS feed — no login required.

Goodreads blocks unauthenticated HTML scraping of review lists (it redirects to
sign-in), but the per-shelf RSS feed is public and carries the real read dates.

    https://www.goodreads.com/review/list_rss/<USER_ID>?shelf=read

Usage:
    python3 goodreads_fetch.py --user-id <your numeric Goodreads id> [--out goodreads_reads.json]

Writes a JSON list of {title, author, read_date, read_year, date_added, rating,
review}. Only books with a real user_read_at date are counted toward the
per-year arc; the rest are undated shelf backlog (reported separately).

Also carries user_date_created — when the review record was first created. That
field survives bulk re-shelving (which rewrites user_date_added) and is the only
signal that can localise a year-only read-date; see estimate_dates() below.
"""
import argparse
import html
import json
import re
import sys
import urllib.request
from collections import Counter
from email.utils import parsedate_to_datetime

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")


def _year(s: str):
    m = re.search(r"\b(20\d\d)\b", s or "")
    return int(m.group(1)) if m else None


def _tag(block: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", block, re.S)
    if not m:
        m = re.search(rf"<{tag}><!\[CDATA\[(.*?)\]\]></{tag}>", block, re.S)
    if not m:
        return ""
    val = re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1)).strip()
    return html.unescape(val)


def fetch(user_id: str, max_pages: int = 100, shelf: str = "read"):
    # Paging rule (audited 2026-10-18, 485 of 485 books on the shelf): advance one
    # page at a time and stop ONLY on an empty page. Goodreads honours
    # per_page=100 today, but a page shorter than the limit is not proof it was
    # the last one — the Substack archive API caps below its limit and that
    # exact "len(page) < limit" stop silently dropped half a corpus. max_pages
    # is a runaway guard (10,000 books), not a size assumption.
    base = (f"https://www.goodreads.com/review/list_rss/{user_id}"
            f"?shelf={shelf}&sort=date_read&order=d&per_page=100&page=")
    items, seen = [], set()
    for page in range(1, max_pages + 1):
        req = urllib.request.Request(base + str(page), headers={"User-Agent": UA})
        xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        blocks = re.findall(r"<item>(.*?)</item>", xml, re.S)
        blocks = [b for b in blocks if _tag(b, "guid") not in seen]
        if not blocks:
            break
        seen.update(_tag(b, "guid") for b in blocks)
        for b in blocks:
            read = _tag(b, "user_read_at")
            added = _tag(b, "user_date_added")
            pub = _tag(b, "book_published")
            pages = _tag(b, "num_pages")
            rating = _tag(b, "user_rating")
            items.append({
                "title": re.sub(r"\s*\(.*?\)\s*$", "", _tag(b, "title")).strip(),
                "author": _tag(b, "author_name").strip(),
                "read_date": read,
                "read_year": _year(read),
                "date_added": added,
                "date_created": _tag(b, "user_date_created"),
                "shelves": _tag(b, "user_shelves"),
                "published": int(pub) if pub.lstrip("-").isdigit() else None,
                "pages": int(pages) if pages.isdigit() else None,
                "rating": int(rating) if rating.isdigit() and rating != "0" else None,
                "review": _tag(b, "user_review").strip(),
            })
    return items


# --- read-date estimation -------------------------------------------------
# Goodreads writes 1 Jan when you give it a year with no month, so a chunk of a
# shelf carries a stamp that is a year-guess, not a date. user_date_created can
# localise most of them.
#
# Validated on a ~230-book shelf whose books carry BOTH a real read-date and a
# small-cluster creation date: date_created preceded the read-date 99% of the
# time, so it is a hard floor.
#
# The filter that matters is BULK_DAY. Records created en masse are shelving
# events, not reading events (e.g. ~100 back-catalog books added in one day) and
# sit years off the true read-date. date_created is the ceiling of what Goodreads
# holds: per-review Started/Finished timelines are usually empty, the updates_rss
# feed holds only the last 10 items, and the v1 API is dead (401 since 2020).
#
# Accuracy degrades monotonically with cluster size — share of real-dated books
# whose date_created lands in a plausible reading window (180d before -> 7d after):
#   cluster 1-3: 73% | 4-5: 50% | 6-9: 33% | 10+: 10%
BULK_DAY = 6  # creation-day clusters this size or larger are back-shelving

# Read-stamps whose YEAR you know is wrong too (e.g. a whole childhood series
# under one blanket stamp). Keyed by stamp date ("YYYY-MM-DD"); those books go to
# the undated group. The original stamp is kept in read_date_raw.
UNTRUSTED_STAMPS = set()


def _placeholder(dt, same_day_n):
    """A year-guess Goodreads rendered as an early-January date."""
    return dt.month == 1 and (dt.day == 1 or (dt.day <= 7 and same_day_n >= 4))


def estimate_dates(items):
    """Annotate each item with date_precision, and read_date_est where recoverable.

    date_precision: "day"   — a real read-date the reader entered
                    "month" — year-guess localised via date_created (read_date_est)
                    "year"  — year-guess, nothing to localise it with
                    None    — no read-date at all
    """
    def _day(s):
        try:
            return parsedate_to_datetime(s).date()
        except (TypeError, ValueError):
            return None

    created_n = Counter(_day(i.get("date_created")) for i in items)
    read_n = Counter(_day(i.get("read_date")) for i in items)

    n_month = n_year = n_void = 0
    for i in items:
        i["read_date_est"] = None
        rd = _day(i.get("read_date"))
        if rd is not None and rd.isoformat() in UNTRUSTED_STAMPS:
            i["read_date_raw"] = i["read_date"]
            i["read_date"] = ""
            i["read_year"] = None
            i["date_precision"] = None
            n_void += 1
            continue
        if rd is None:
            i["date_precision"] = None
            continue
        if not _placeholder(rd, read_n[rd]):
            i["date_precision"] = "day"
            continue
        cd = _day(i.get("date_created"))
        # Only trust a creation date that is solitary-ish AND lands in the year
        # the stamp claims — otherwise it is a shelving artifact, or predates
        # the reading entirely (a to-read add), and the year is all we know.
        if cd and created_n[cd] < BULK_DAY and cd.year == rd.year:
            i["read_date_est"] = i["date_created"]
            i["date_precision"] = "month"
            n_month += 1
        else:
            i["date_precision"] = "year"
            n_year += 1
    return n_month, n_year, n_void


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True, help="numeric id from your profile URL: goodreads.com/user/show/<ID>-name")
    ap.add_argument("--out", default="goodreads_reads.json")
    ap.add_argument("--shelf", default="read",
                    help="Goodreads shelf name, e.g. read | to-read | currently-reading")
    args = ap.parse_args()

    items = fetch(args.user_id, shelf=args.shelf)
    n_month, n_year, n_void = estimate_dates(items)
    dated = [i for i in items if i["read_year"]]
    with open(args.out, "w") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    by_year = Counter(i["read_year"] for i in dated)
    print(f"Wrote {len(items)} shelf items ({len(dated)} with real read-dates) -> {args.out}")
    for y in sorted(by_year):
        print(f"  {y}: {by_year[y]}")
    print(f"  undated backlog: {len(items) - len(dated)}")
    print(f"  year-guess stamps: {n_month} localised to a month, {n_year} left year-only")
    print(f"  untrusted stamps voided to undated: {n_void}")


if __name__ == "__main__":
    main()
