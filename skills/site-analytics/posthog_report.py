#!/usr/bin/env python3
"""Who actually came, per site, from PostHog — your own traffic and test accounts filtered out.

    posthog_report.py [--days 7] [--host example.com]

Per host: unique persons, returning persons (seen on 2+ distinct days in the window),
pageviews, top paths, top referrers. One PostHog project can serve many sites;
they are told apart by $host (and a `site` super property). The project's
test_account_filters (e.g. an internal cohort, your IP, localhost, distinct_id 'internal-*')
are applied through HogQL's {filters} placeholder, and the snippet's ?me=1 opt-out means
your opted-out browsers never send at all.

Keys: POSTHOG_PERSONAL_API_KEY, POSTHOG_PROJECT_ID, POSTHOG_HOST in the environment or
./.env (override the path with POSTHOG_ENV_FILE).
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ENV = pathlib.Path(os.environ.get("POSTHOG_ENV_FILE", ".env")).expanduser()


def env():
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    for k in ("POSTHOG_PERSONAL_API_KEY", "POSTHOG_PROJECT_ID"):
        if not os.environ.get(k):
            sys.exit(f"missing {k} (expected in {ENV})")
    return os.environ.get("POSTHOG_HOST", "https://us.posthog.com").rstrip("/")


def hogql(host, q):
    body = {"query": {"kind": "HogQLQuery", "query": q, "filters": {"filterTestAccounts": True}}}
    req = urllib.request.Request(
        f"{host}/api/projects/{os.environ['POSTHOG_PROJECT_ID']}/query/",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ["POSTHOG_PERSONAL_API_KEY"],
                 "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120)).get("results", [])
    except urllib.error.HTTPError as e:
        sys.exit(f"PostHog {e.code}: {e.read().decode()[:400]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--host", help="only this $host")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    api = env()
    secs = int(a.days * 86400)
    w = (f"timestamp > now() - interval {secs} second AND properties.$host IS NOT NULL AND {{filters}}"
         + (f" AND properties.$host = '{a.host}'" if a.host else ""))

    totals = hogql(api, f"""
        SELECT host, uniq(pid), uniqIf(pid, days >= 2), sum(pv)
        FROM (SELECT properties.$host AS host, person_id AS pid,
                     uniq(toDate(timestamp)) AS days, countIf(event = '$pageview') AS pv
              FROM events WHERE {w} GROUP BY host, pid)
        GROUP BY host ORDER BY 2 DESC, 4 DESC LIMIT 100""")
    paths = hogql(api, f"""
        SELECT properties.$host, properties.$pathname, count(), uniq(person_id)
        FROM events WHERE {w} AND event = '$pageview'
        GROUP BY 1, 2 ORDER BY 1, 3 DESC LIMIT 1000""")
    refs = hogql(api, f"""
        SELECT properties.$host, properties.$referring_domain, uniq(person_id)
        FROM events WHERE {w} AND event = '$pageview'
          AND properties.$referring_domain NOT IN ('$direct', '')
          AND properties.$referring_domain != properties.$host
        GROUP BY 1, 2 ORDER BY 1, 3 DESC LIMIT 1000""")

    by_path, by_ref = {}, {}
    for h, p, n, u in paths:
        by_path.setdefault(h, []).append((p, n, u))
    for h, r, u in refs:
        by_ref.setdefault(h, []).append((r, u))

    span = f"{a.days:g} day{'s' if a.days != 1 else ''}"
    print(f"PostHog, last {span}, test accounts + internal filtered. persons / returning (2+ days) / pageviews")
    if not totals:
        print("  no events")
        return
    for h, persons, ret, pv in totals:
        print(f"\n{h}  {persons} persons / {ret} returning / {pv} pageviews")
        top = by_path.get(h, [])[: a.top]
        if top:
            print("  paths:     " + "; ".join(f"{p} {n}pv/{u}p" for p, n, u in top))
        rr = by_ref.get(h, [])[: a.top]
        if rr:
            print("  referrers: " + "; ".join(f"{r} {u}p" for r, u in rr))


if __name__ == "__main__":
    main()
