---
name: search-console-setup
description: >
  Make a domain findable and verified in Google — verify it in Google Search Console,
  submit the sitemap, and give the site entity markup that resolves to one business.
  Use when you say "verify my domain in Search Console", "submit the sitemap", "why
  isn't my site showing up on Google", "set up SEO for <domain>", "anything I should
  do with my SEO", "I registered an LLC / got an EIN", "add structured data / schema",
  or ask about the Google Business Profile name. Includes writing the DNS TXT record
  over the Vercel API.
---

# Standing up a domain's search presence

The whole job, in order. Steps 1-3 run headless; step 2's property creation is one
browser click only the domain owner can make; step 5 is the owner's call.

**Done looks like:** the domain is a verified Domain property in Search Console, the
sitemap is submitted once and reports the right page count, and the site serves exactly
one `Organization` node that agrees with the Google Business Profile.

---

## Rule 0 — an EIN does nothing for SEO

Google cannot read IRS records. **Never put the EIN on the site or in markup.** What
business registration actually buys is *entity consolidation*: a legal name a third
party can verify, which is what lets `legalName` do its job in rule 2.

**Why this is rule 0:** the question arrives as "I registered the business, what about
SEO?" and the tempting answer is a list of SEO tips. The real answer is narrower:
registration is an identity fact, so the work is identity work.

---

## Step 1 — find out if it's even verified

Do this before anything else. "It's probably verified, I just need to submit a sitemap"
is often wrong, and it inverts the task.

```bash
D=example.com
dig +short TXT $D @8.8.8.8 | grep google-site-verification   # DNS method
curl -s https://$D/ | grep -i google-site-verification       # meta-tag method
```

Also check whether Google Analytics or Tag Manager is on the page — either can carry
verification instead. All four negative -> **not verified, no property exists**, and
there is nothing to submit a sitemap to yet.

## Step 2 — the owner creates the property, you write the DNS record

**Domain property, not URL-prefix.** It covers every subdomain and both protocols. Its
only cost is that it's DNS-verify-only, which is free when you can write DNS.

The owner pastes back a string like `google-site-verification=Dm4-...`. Then:

### Writing a TXT record on Vercel DNS

If the domain sits on Vercel's nameservers, records are writable over the REST API with
a `VERCEL_TOKEN` — no CLI.

```python
import json, os, urllib.request
tok  = os.environ['VERCEL_TOKEN']
TEAM = os.environ.get('VERCEL_TEAM_ID', '')     # required if the domain is under a team
body = json.dumps({'name': '', 'type': 'TXT',   # '' == apex, NOT '@'
                   'value': 'google-site-verification=...',
                   'ttl': 60}).encode()
q = f'?teamId={TEAM}' if TEAM else ''
req = urllib.request.Request(
    f'https://api.vercel.com/v2/domains/{DOMAIN}/records{q}',
    data=body, method='POST',
    headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
print(json.load(urllib.request.urlopen(req)))    # -> {'uid': 'rec_...'}
```

Listing is `GET /v4/domains/{domain}/records?limit=100&teamId=...`.

Three things that cost time:

- **Omitting `teamId` returns a bare 403**, not a helpful error, when the domain lives
  under a team. Recover the id with `GET /v2/teams`.
- **The apex name is `''`, not `'@'`.** Vercel returns apex records with an empty `name`;
  sending `'@'` creates a literal `@` subdomain.
- **Set `ttl: 60`.** Google's checker runs the moment the owner clicks Verify, and a
  default TTL can leave a cached negative answer in front of it.

**Add the record; never edit an existing TXT to hold it.** Multiple TXT records coexist
at the apex by design. Merging a verification string into the SPF record breaks mail
authentication — and the apex often carries SPF for your mail provider and any bulk
sender.

Confirm on two independent resolvers before telling the owner to click Verify:

```bash
for r in 8.8.8.8 1.1.1.1; do dig +short TXT $D @$r; done
```

## Step 3 — deploy, THEN submit

**The sitemap must be live and correct before it is submitted.** Submitting hands Google
whatever the deployed file says; the local one is irrelevant. Unpushed commits are the
usual reason the live sitemap is stale.

```bash
curl -s https://$D/sitemap.xml | grep -c "<loc>"   # what Google will actually get
git log --oneline origin/main..HEAD                 # anything undeployed?
```

Then submit `https://$D/sitemap.xml` in Sitemaps.

**Submit once. Never build automation for this.** Google recrawls a known sitemap on its
own; resubmitting after a content change does nothing. See rule 6.

## Step 4 — Google Business Profile

Covered by rules 2 and 3 below.

## Step 5 — the off-site directories are optional

Apple Business Connect, Bing Places, a free D&B DUNS number. Offer them once, ranked,
then drop it. If the owner skips them, don't re-pitch.

---

## The rules, and why each exists

**1. Exactly one `Organization` node per site.**
Two nodes claiming the same name with different `logo` or `url` is precisely the entity
split the markup exists to prevent. It happens easily when two edits (or two agents)
each add a block. **Always count after editing:**

```bash
python3 -c "
import re,json
h=open('index.html').read()
b=re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>',h,re.S)
print('blocks:',len(b))          # must be 1
[json.loads(x) for x in b]       # must parse
"
```

**2. `legalName` carries the LLC. The GBP name never does.**
Google's GBP naming rules only allow the name as it appears on real-world signage;
appending "LLC" risks suspension. So the profile and the state filing are *supposed* to
differ, and `legalName` reconciles them. What must be consistent across citations is the
**brand** string, not the legal one.

```jsonc
"name":          "Acme & Co",            // brand — matches GBP exactly
"legalName":     "Acme and Co LLC",      // the filing
"alternateName": ["Acme and Co", "Acme"] // real search variants
```

Include the spelled-out variant when the domain spells it out (people type both "&" and
"and").

**3. Service-area business => no `streetAddress` anywhere.**
If the GBP hides the address but the site publishes one, the two disagree about whether
customers can visit. Locality-only `PostalAddress` plus `areaServed`. Cap the GBP service
area at the metro or state even for a nationally-served product — Google limits it to
~20 regions and an over-broad area dilutes local relevance.

**4. `sameAs` is the field that earns its keep.**
It ties the domain to the GBP and the social accounts, which is how crawlers *and answer
engines* resolve one entity instead of several unrelated mentions. The GBP link form is
`https://www.google.com/maps/place/?q=place_id:<PLACE_ID>`.

**5. Never put developer notes in a schema field.**
`comment` is a real schema.org property, so an internal note there gets published as
structured data. Notes go in an HTML comment above the `<script>`.

**6. The Search Console API cannot be driven by an API key.**
It needs OAuth2 with the `webmasters` scope — a browser consent flow — and property
creation can't be automated at all (`sites.add` still requires interactive verification).
Combined with "submit once", the 3-minute manual path beats any automation. The old
unauthenticated `google.com/ping?sitemap=` endpoint was retired by Google.

---

## Also worth running: how much is actually crawlable

Strip scripts and tags from the *served* HTML and count words — it reveals JS-painted
pages that Google can reach but can't read.

```bash
for u in "" "about/" "pricing/"; do
  n=$(curl -s "https://$D/$u" | python3 -c "
import sys,re,html
h=re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>',' ',sys.stdin.read())
print(len([w for w in html.unescape(re.sub(r'(?s)<[^>]+>',' ',h)).split() if len(w)>1]))")
  printf '%-16s %5s words\n' "/$u" "$n"
done
```

A chat-style app page that paints everything with JavaScript can serve ~80 words, in
which case the structured data is the *only* substantive description a crawler gets.

**How to report this:** brand searches will resolve (entity markup + `sameAs` do that
job) but descriptive queries won't rank, because there's no text to match. Say that
plainly and stop — it's a content decision, not a technical defect.

---

## Decide vs. ask

**Decide yourself:** schema shape and fields, TTL, Domain-vs-URL-prefix property, which
validation to run, whether to dedupe markup.

**Ask the owner, always:**
- **Publish the address or hide it.** Privacy, and often a home address.
- **Which off-site directories are worth their time.**
- **The exact registered legal name**, character-for-character. Never infer it from the
  brand ("&" vs "and" is a common mismatch).
