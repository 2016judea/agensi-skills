---
name: clover-api
description: Read a Clover (Fiserv) merchant's register through OAuth v2 — payments, orders, shifts and tips — and get a third-party app listed and billed on the Clover App Market. Use for "connect their Clover", "pull daily sales from Clover", "list on the Clover App Market", "does Clover bill app subscriptions", "Clover sandbox", "Clover developer account", "Clover refresh token", "seed the Clover sandbox". Carries the facts that cost a cycle: single-use refresh tokens, 30-minute sandbox tokens, the 90-day filter cap, the region trap at signup, and the order of the approval gates.
---

# Clover API

## The one fact: Clover bills the merchant, and the market is open

**Clover App Market is self-serve and open to new developers** (read 2026-11; contrast
Square, which paused new marketplace onboarding in 2026-10). Every app carries a
subscription, free or paid; Clover charges the merchant on the 1st of each month, prorated
daily, and pays the developer's share into a bank account in the third week of the following
month. The developer keeps **70%** (30% transaction fee, Clover App Market Developer Terms
§9.2). Free trials 14–90 days. No active-merchant minimum before listing. The merchant's
billing state is readable: `GET /v3/apps/{appId}/merchants/{mId}/billing_info` → `status`
(ACTIVE/LAPSED/INACTIVE/SUPPRESSED), `isInTrial`, `appSubscription`.

What a listing needs: a **verified production developer account** (legal name, DOB, home
address, EIN if registering as a business, OFAC check; identity only, no fee) and an approved
app (functional review with a walkthrough **video**, legal review of a privacy policy + TOS
URL, listing review of icon / screenshots / 3–5 merchant benefits, support email + site +
phone). Paid tiers need a bank account on the developer account first. A stuck review is
chased through Clover developer relations with the App ID.

**Plan for months, not days.** Developers on r/CloverPOS (mid-2026) reported 2–7 months
"Under review" after a submission freeze. Submit the day the account is approved and never
promise a merchant a date.

## Order of the gates

Submit App refuses with "you must be an approved developer" while Developer Info reads
VERIFYING ACCOUNT. The bank/payout section does not appear until the account is verified,
and paid pricing tiers need the bank. Production "Create new app" can be inert (no dialog)
while the account is verifying. So: **verify → bank → paid tier → create production app →
Submit.** The checklist's last item, "Explain your Request for Merchant Permissions", wants
one reason per READ permission (App Settings → Requested Permissions). Request only what the
code calls.

## Hosts

| | Sandbox | Production (North America) |
|---|---|---|
| OAuth authorize | `https://sandbox.dev.clover.com/oauth/v2/authorize` | `https://www.clover.com/oauth/v2/authorize` |
| token / refresh | `https://apisandbox.dev.clover.com/oauth/v2/{token,refresh}` | `https://api.clover.com/oauth/v2/{token,refresh}` |
| REST | `https://apisandbox.dev.clover.com/v3/…` | `https://api.clover.com/v3/…` |

Sandbox app ids work only against sandbox hosts; a production app is a **separate app**
created with the Sandbox toggle off, with its own id and secret.

## OAuth v2 (expiring tokens, code flow)

Authorize URL: `client_id`, `response_type=code`, `redirect_uri`, `state`. **`redirect_uri`
must be a subpath of the app's registered Site URL** (same scheme and host). Clover redirects
with `code` and `merchant_id`. When a merchant opens the app from the App Market or their
dashboard, Clover sends them to the Site URL / Alternate Launch Path with `merchant_id` (and
`employee_id`); the app must start the authorize flow itself.

Token: `POST /oauth/v2/token` JSON `{client_id, client_secret, code}` →
`{access_token, access_token_expiration, refresh_token, refresh_token_expiration}` (Unix
seconds; don't hard-code lifetimes). **Refresh tokens are single-use**: `POST
/oauth/v2/refresh` `{client_id, refresh_token}` returns a new pair and kills the old refresh
token, so persist the new pair before anything else runs. If the new pair is lost, the
previous refresh token is a recovery token at `/oauth/v2/recovery` (needs `client_secret`).

- **Sandbox access tokens live ~30 minutes**; refresh tokens 365 days. Any job that runs less
  often than that must refresh first.
- Permissions are set on the app (Merchant / Orders / Payments / Employees read…); changing
  them after install needs the merchant to uninstall + reinstall.

## Reading the register

- `GET /v3/merchants/{mId}?expand=address,owner` → `name`, `address{…}`, `owner{email}`.
  One merchant id is one location.
- `GET /v3/merchants/{mId}/payments?filter=createdTime>={ms}&filter=createdTime<{ms}&limit=1000&offset=N`
  → `elements[]` of `{amount (cents), tipAmount, taxAmount, result, createdTime (ms),
  order{id}, tender{id}}`. Count only `result == "SUCCESS"`. **Time filters are capped at 90
  days per call**; `limit` default 100, max 1000, page with `offset`. Add
  `expand=tender,order,employee,refunds,serviceCharge` for the server (`order.employee.id`),
  `serviceCharge.amount`, `refunds.elements[].tipAmount`, `tender.labelKey`.
- `GET /v3/merchants/{mId}/orders?filter=clientCreatedTime>=…&expand=lineItems` for what sold.
- `GET /v3/merchants/{mId}/shifts?filter=in_time>=…&expand=employee` → `inTime`, `outTime`,
  `overrideInTime/OutTime`, `cashTipsCollected` (declared at clock-out).
- **The employee object carries no wage**, and Clover holds no reliable exempt status or
  workweek start: a payroll-type app must ask the merchant for them.
- Timestamps are milliseconds; bucket by the merchant's local day. The time zone is on
  `/v3/merchants/{mId}/properties` → `timezone`, not on the merchant object.

## Seeding the sandbox

REST refuses native card payments ("use an external tender type"); creating or enabling a
tender needs MERCHANT_W. The sandbox's enabled **Check** tender accepts payments with tips.
Merchant-dashboard API tokens need 2FA on the merchant login, so seed with the app's own
token after temporarily adding WRITE permissions, then drop them and uninstall/reinstall
(My Apps → More Actions → Uninstall app).

Test merchant: Global Dashboard → Test Merchants → **Launch Dashboard** (an icon with an
aria-label, no text) opens the sandbox dashboard signed in as the merchant. Hitting the app's
launch URL from there lands on the sandbox App Market listing: Connect → modal → the modal's
own Connect → "Success!" → **Open the app**. The install itself never redirects to
`redirect_uri`; "Open the app" does.

## Driving the developer console (no API for it)

If you automate the console in a browser, run it **headless with its own profile**; a visible
window pops tabs ("Open the app") in front of whoever is at the machine.

- **Signup region trap.** The region picker on "finish setting up" is an animated checkbox
  list; a click while it animates lands on the next option. An account created in Latin
  America has no app billing. Fix: Region icon (top-right) → Add region → North America.
  Check the URL contains `/NA/` before creating anything.
- Signup passwords reject any character repeated 3× in a row. A bare "Error / Error" dialog
  can appear even though the account WAS created; reload before resubmitting.
- Login is Ping Federate: `#username`, `#password`, then the `#signOnButton` **anchor**; set
  fields through the native value setter (typing onto a prefilled field doubles it). MFA is an
  authenticator app only; the pairing page carries an `otpauth://totp/…?secret=` URI in its
  HTML, so `pyotp.TOTP(secret).now()` produces codes. Ping cookies are session-scoped: a
  browser restart means logging in again.
- App Settings / Developer Settings panes live in an **iframe**: the outer page's `innerText`
  is blank, so work in `page.frames()` and use element-handle `.click()`. Pencil icons are
  `<i>edit</i>`. Field ids regenerate per render; find inputs by placeholder/label each time.
- **MUI selects (Country, State) take a click, then an `[role=option]` click; typing does
  nothing.** State reads `-` until Country is picked. The Website field prefixes `https://`.
- Sandbox "Create new app" offers only Payment / Private apps; an **App Market app exists only
  with the Sandbox toggle off**. A Private + Web app is fine for sandbox OAuth testing.
- The Requested Permissions dialog has dropped a row on the first Save; re-open, re-tick, save,
  and read the summary line back.
- Market Listing images: the crop pop-up's Submit is **disabled until you click its "Crop
  Image" bar**. A real mouse click on UPLOAD IMAGE opens a native chooser
  (`page.waitForFileChooser()`); screenshots multi-select from the dialog's centre button.
  `offsetParent !== null` is not visibility here (closed MUI dialogs still report visible
  buttons); trust a screenshot.
- Textareas clear with `ta.select()` + Backspace, then `keyboard.sendCharacter(text)`.
- A second `puppeteer.connect` to the same Chrome can hang; relaunch on a new port with the
  same `--user-data-dir`. Long sessions that stall on `Runtime.callFunctionOn` recover with
  `--disable-backgrounding-occluded-windows --disable-renderer-backgrounding
  --disable-background-timer-throttling`.
- Production developer verification (Developer Settings → Developer Info): Account Details
  (tax country, EIN as 9 digits, legal name, address), Identity (name, **DOB YYYY-MM-DD**,
  home address, phone, email), Contact Info, then "Verify Your Account". No document upload
  for a US developer.

Keep app ids, secrets, TOTP seeds and login passwords in a gitignored `.env`, never in a skill.

## Related

`square-api` for the other big register (same shape, different billing); `browser-as-you`
for driving consoles that have no API.
