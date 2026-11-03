---
name: engagement-outreach
description: Take a paid offer to a named person at a buying organisation with a first-touch message whose opener is an ANOMALY — a fact you found by joining their own public record against a second layer, which they can verify but could not have seen — rather than a mirror of what they already know. Covers computing the anomaly, the join traps that ship false sentences, verifying the person off their own site, a two-name subject and an under-80-word body, reading your own drafts for four silent defects, freezing a campaign once sent, and sending from a ledger instead of a folder. Use for "who should we pitch", "write the first emails", "send the next batch", or "did anyone reply". A human presses send.
---

# Engagement outreach (the anomaly opener)

**Goal:** a named person at a buying organisation replies. A written "no thanks" counts: it
closes the row. **You draft; a human sends.** Draft, verify the recipient, put it in a file, say
it's a draft, stop.

## Step 0: the opener must be an ANOMALY, not a MIRROR. This is the whole skill.

A fact the recipient already knows about their own business sells nothing, however well measured.
"You wrote 25 SBA loans over $250k last year" is true, specific, checkable, and a **mirror**: they
wrote them. Most people don't see the problem a tool solves; half of selling is showing them a
problem they didn't know they had.

**So: join the prospect's own public record against a second layer, and lead with what the join
found.** They can verify every row, and they could not have seen it. It is also the offer
demonstrating itself for free before anyone is asked for money. The list is rarely the problem;
the opener usually is.

Example shape: lender loan records (borrower parcel) x the state's contamination-site register ->
"N of your loans over $250k landed on parcels the state holds a cleanup file on."

## Step 1: pick the offer by its existing line item

For each offer, ask whether the buyer already pays for this kind of thing (a purchase order you are
bidding on) or would need a new budget. Lead with the one that has a line item.

## Step 2: compute the anomaly, and respect the join's traps

Every join has traps that ship a false sentence. Find yours before drafting. Typical ones:

- **Composite keys.** Parcel ids are not unique across counties; joining on id alone invents hits.
- **Whose address is it?** A loan file may carry the borrower's address, not the project site. Then
  the true sentence is "landed on a parcel the state holds a file on", never "your collateral is
  contaminated". Put the caveat in the **body**, in a plain sentence.
- **Absence is not absence.** No row in a register means nobody opened a file, not that the site is
  clean. Say so, and never let a register search be mistaken for a professional assessment.

A message that volunteers its limits is the one a professional trusts.

### No join available? One checkable fact (the fallback ladder)

For a small business where a two-layer join isn't possible, open with **one** true, checkable fact
about them, strongest first:
1. **A structural gap**: their listing shows no hours, or the website it links 404s.
2. **A mismatch**: website hours vs directory hours.
3. **One dated review, quoted as one review** (not a trend).
4. **A real multi-review pattern**, only after reading every review in full (directory APIs often
   return 5 reviews, truncated; a snippet that might continue is not evidence).
No pitch and no link in this first message; a soft question; send the gentler facts first.
Validate any social handle live (right business? posted recently?) before using it.

## Step 3: verify the person off THEIR OWN site

Read name and title from the organisation's team or staff page and cite it in the draft header. **A
generic inbox is not a missing contact**: use an `Attn:` line over the org address. Never take an
address from a contact-data aggregator: a wrong one is a fabricated citation that burns the org.
Many orgs publish named staff and zero emails, or route every "email me" to a form. Normal; don't
guess. Your own crawler can hide a real address (ROT13 is a common anti-scraper trick); decode before
believing a mismatch.

## Step 4: subject and body

- **Subject: `<you> / <their company>`.** Two names and a slash. No verb, no pitch. A descriptive
  subject tells them what you want and lets them decline unopened. Trim legal suffixes and un-shout
  ALL CAPS; nothing cleverer, because a mangled name in the only line that gets read is fatal.
  (Exception: a records request keeps its statute in the subject, because a records officer routes
  on it.)
- **Body under ~80 words, one ask.** The anomaly is the body; no preamble.
- **First batch: no price.** The reply that teaches you most is someone asking what it costs.
- **One link, to a page per recipient** that repeats the email's sentence over a button handing
  over the evidence. A link to your generic homepage loses the sentence that earned the click.

## Step 5: before sending

- `dig +short MX <domain>` for every recipient domain.
- Send plain text.
- **Instrument first**: fire a tagged link yourself and read it back out of your analytics *before*
  the batch. An unmeasured batch teaches nothing (one team sent 1,400 cold emails and captured no
  reply, bounce or outcome).
- Sample size: cold-email reply rates are low, so a batch must be large enough that silence is a
  finding rather than noise. Log each reply's **kind** (price question, interested, no thanks,
  bounce): "any reply" lumps opposite findings together.

## Step 6: read your own output before anyone else does

Four defects that pass a green test suite:

- **A class-level number is a mail merge wearing a number.** If every HVAC firm gets the same city
  permit count, it's about the city, not them. Pair it with a figure that's theirs to make a ratio.
- **A NULL is a true finding and a terrible opener.** "We looked and found nothing" as a first line.
  Make "no anomaly -> don't send" a code rule.
- **A verified address can be the wrong room.** `investorrelations@` will never reach a credit
  officer. Keep a wrong-desk list.
- **A 200 doesn't mean the page delivers the promise.** Read the button URL out of the *shipped* page,
  follow it, and compare the label to what comes back.

## Step 7: a campaign is frozen once it's out

- Tokens or per-recipient URLs that include a build date rotate on rebuild and orphan sent links. Pin
  the day per batch.
- Windowed figures drift (471 becomes 470 overnight). **Don't rebuild a batch after it's sent**: a page
  that contradicts a sent email by one digit destroys the checkability the opener depends on.

## Step 8: sending infrastructure

- Don't blast from a person's mailbox: providers block the whole mailbox (replies included) after a
  few dozen cold sends in a day. Use a transactional sender with From/Reply-To set to the human's
  address.
- **Turn click tracking off.** It rewrites links into redirectors (destroys your tokens and looks like
  phishing).
- **A one-line opt-out** in the signature, and a real postal address where the law requires one.
- A separate sending subdomain protects your main domain's reputation.

## Step 9: the ledger decides who is written to, never the folder

When a rebuild drops a prospect (a duplicate, a placeholder mailbox), its draft file can stay on disk;
a loop over `drafts/*` then mails people you meant to drop, some for the third time. **Iterate the
ledger, not the directory**, refuse any recipient with no ledger row or already sent, and **when a
guard drops a record, delete the artefact the record was for.**

## Step 10: record and chase

Rename the draft `..._SENT`, with date, sender, recipient, provider message id, subject and any
difference between drafted and sent text. Put the chase (about two weeks) in your task tracker with
what silence should and shouldn't be read as.

## Honesty

This records a method that ran, not one proven to convert. Measure your own reply rate by kind before
scaling.
