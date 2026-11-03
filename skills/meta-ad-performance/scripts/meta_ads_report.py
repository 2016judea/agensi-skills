#!/usr/bin/env python3
"""Meta ad performance in one run: per-ad spend/CTR/CPC, audience breakdown, Pixel event funnel,
and (optionally) Stripe purchases at one price.

Env:
  META_ACCESS_TOKEN   (required) a token with ads_read
  META_AD_ACCOUNT_ID  (required) act_...
  META_CAMPAIGN_IDS   comma-separated campaign ids for the breakdowns (optional)
  META_PIXEL_ID       for the Pixel funnel (optional)
  LAUNCH_DATE         YYYY-MM-DD, start of the Pixel window (default: 7 days ago)
  STRIPE_SECRET_KEY + STRIPE_PRICE_CENTS   count paid charges at that amount since LAUNCH_DATE (optional)
"""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

V = "v21.0"
TOKEN = os.environ["META_ACCESS_TOKEN"]
ACCOUNT = os.environ["META_AD_ACCOUNT_ID"]
CAMPAIGNS = [c for c in os.environ.get("META_CAMPAIGN_IDS", "").split(",") if c]
PIXEL = os.environ.get("META_PIXEL_ID")
LAUNCH = os.environ.get("LAUNCH_DATE") or (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def meta(path, **params):
    params["access_token"] = TOKEN
    return get(f"https://graph.facebook.com/{V}/{path}?" + urllib.parse.urlencode(params))

for label, preset in [("TODAY", "today"), ("LAST 7 DAYS", "last_7d")]:
    data = meta(f"{ACCOUNT}/ads", fields=f"name,status,insights.date_preset({preset}){{spend,clicks,impressions,cpc,ctr,frequency}}", limit=100)
    rows = [(a["name"], a.get("insights", {}).get("data", [{}])[0]) for a in data.get("data", []) if a.get("status") == "ACTIVE"]
    rows = [(n, i) for n, i in rows if i and float(i.get("impressions", 0)) > 0]
    print(f"\n=== {label} ===")
    for n, i in rows:
        print(f"  {n}\n    ${float(i.get('spend', 0)):.2f} | {i.get('impressions')} impr | {i.get('clicks')} clicks | "
              f"{float(i.get('ctr', 0)):.2f}% CTR | ${float(i.get('cpc', 0) or 0):.2f} CPC | freq {float(i.get('frequency', 0) or 0):.2f}")
    if not rows: print("  no active ad delivery")

for cid in CAMPAIGNS:
    for bd in ("age,gender", "device_platform"):
        rows = meta(f"{cid}/insights", fields="impressions,clicks,ctr", breakdowns=bd, date_preset="last_7d").get("data", [])
        print(f"\n=== {cid} by {bd} (last 7d) ===")
        for r in sorted(rows, key=lambda x: int(x.get("clicks", 0)), reverse=True):
            if int(r.get("impressions", 0)) < 5: continue
            key = " ".join(r.get(k, "") for k in bd.split(","))
            print(f"  {key:22s} {r['impressions']:>6} impr {r['clicks']:>4} clicks {float(r['ctr']):.2f}% CTR")

if PIXEL:
    totals = {}
    for hour in meta(f"{PIXEL}/stats", start_time=LAUNCH, aggregation="event", limit=500).get("data", []):
        for e in hour.get("data", []):
            totals[e["value"]] = totals.get(e["value"], 0) + e["count"]
    print(f"\n=== PIXEL EVENTS since {LAUNCH} ===")
    for k, v in sorted(totals.items(), key=lambda x: -x[1]): print(f"  {k}: {v}")

if os.environ.get("STRIPE_SECRET_KEY") and os.environ.get("STRIPE_PRICE_CENTS"):
    since = int(datetime.strptime(LAUNCH, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    amt = int(os.environ["STRIPE_PRICE_CENTS"]); n = 0; after = None
    while True:
        q = {"limit": 100, "created[gte]": since}
        if after: q["starting_after"] = after
        page = get("https://api.stripe.com/v1/charges?" + urllib.parse.urlencode(q),
                   {"Authorization": f"Bearer {os.environ['STRIPE_SECRET_KEY']}"})
        n += sum(1 for c in page["data"] if c["paid"] and not c.get("refunded") and c["amount"] == amt)
        if not page.get("has_more"): break
        after = page["data"][-1]["id"]
    print(f"\n=== STRIPE paid charges at {amt/100:.2f} since {LAUNCH}: {n} ===")
