---
name: browser-as-you
description: Complete a sign-up, listing, claim or console task on a third-party site AS you, by driving Chrome on a copy of your own logged-in session — "create the account", "submit us to X", "claim that listing", "file the application", "take over a browser", "I don't have an account, can you do it". Use when a task is blocked on a web UI that has no API and no credential on disk. Covers the launch recipe that works (macOS, Chrome, puppeteer-core), the gates that stop it, reading a verification code out of your mail or Messages, and the failure where a green exit code hides a no-op.
compatibility: >-
  macOS with Google Chrome and Node (puppeteer-core); the OCR helper (inline below) needs swiftc
  (Xcode command-line tools). Network: only the sites you point the browser at, signed in as
  you. The recipes below name www.google.com (Maps lists), substack.com, news.ycombinator.com,
  x.com, whop.com and platform.openai.com.
metadata:
  network-hosts: "www.google.com substack.com news.ycombinator.com x.com whop.com platform.openai.com"
---

# Driving a browser as you

Most directory, registry and console work has no API. The task is not blocked on the
human; it is blocked on a logged-in browser. This is how to be one — for **your own
accounts only**.

**Don't hand back a checklist of URLs when this skill applies.** Go and do it, then report
what exists and what it cost.

---

## Step 1 — the launch recipe

Copy your cookies out, launch Chrome yourself, then attach. Launched by hand it carries no
automation flag and `navigator.webdriver` is false.

```bash
SP=$(mktemp -d)
mkdir -p "$SP/w/Default"
cp "$HOME/Library/Application Support/Google/Chrome/Default/Cookies" "$SP/w/Default/Cookies"
cp "$HOME/Library/Application Support/Google/Chrome/Local State"     "$SP/w/Local State"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --remote-debugging-port=9461 --user-data-dir="$SP/w" \
  --no-first-run --no-default-browser-check "<the page you want>" &
```

Then `puppeteer.connect({browserURL:"http://localhost:9461"})` (`npm i puppeteer-core`).
Your GitHub and Google sessions come with the cookies, so "Sign in with GitHub" often
completes with no typing.

**Headless is the default.** A visible window steals the user's screen while they work. A step
that only works in a window is a gate to report, not a reason to open one, unless the user has
said to take over their screen for this task.

**`--window-position=-4000,-4000` does not keep a window off screen on macOS.** It is ignored:
three windows opened at the top-left of the user's display, and one stayed there for about 15
minutes. If a site walls headless (some sign-up forms, Cloudflare Turnstile) and you've been told
to use a window, minimise it on the first CDP call: `Browser.getWindowForTarget`, then
`Browser.setWindowBounds {windowState:"minimized"}`. Screenshots still work minimised. To type,
call `Emulation.setFocusEmulationEnabled {enabled:true}`, focus the field in-page, then
`page.keyboard.type`. `elementHandle.click()` hangs on a minimised window; use `page.mouse.click`
at the box, or a DOM `.click()`.

**Land on the target URL at launch.** Navigating afterwards is where it hangs.

**For a brand-new account, use an EMPTY profile instead** (skip the cookie copy) so the new
account isn't tied to your other sessions.

**Delete the profile copy when done.** It holds live session cookies for every site you are
signed into. `rm -rf "$SP/w"`, every time, and kill the browser.

## Step 2 — the mechanics that cost the most cycles

1. **ONE script per Chrome launch.** The first `puppeteer.connect` works; a later one can
   hang on connect, `goto` or `evaluate`. Do the flow in one script, then `pkill -f
   "remote-debugging-port=<port>"` and relaunch on a NEW port for the next stage. Wrap every
   script in `setTimeout(()=>process.exit(1), N)` so a hang costs seconds. Pick an unusual
   port range so other tools' `pkill` patterns don't kill your browser.
2. **A scripted `.click()` is ignored by React-style forms.** Use a real
   `p.mouse.click(x, y)` at the element's bounding-box centre, after `scrollIntoView`. The
   default headless viewport is 800x600, so set a tall viewport first or the button is off
   screen. For a styled radio or checkbox, click its **`<label>`**, not the hidden input.
3. **Set values through the native setter**, not `el.value =`:
   `Object.getOwnPropertyDescriptor(el.constructor.prototype,"value").set.call(el,v)` then
   dispatch `input` and `change`. A plain assignment leaves the framework's state empty and
   the form submits blank.
4. **A one-time secret is often not in `innerText`.** Scrape `documentElement.innerHTML` and
   input `value`s on the same page load that created it (e.g. `/hf_[A-Za-z0-9]{20,}/` for a
   Hugging Face token).
5. **Screenshot when a submit silently fails.** A native `type=url` tooltip ("Please enter a
   URL") is invisible to every text check. A bare domain needs the scheme.
6. **Fresh sign-ins get bounced to an upsell** (`/trial`, `/pricing`). Don't follow it; go
   straight back to the target path.
7. **OAuth for a CLI/agent client** (an MCP server with dynamic client registration): register
   a client with a `http://localhost:<port>/callback` redirect, build the PKCE authorize URL,
   launch the logged-in browser ON that URL, click Allow, and run a one-request local HTTP
   server to catch the `code`. Then exchange it at the token endpoint and store the token
   `chmod 600` outside any repo.

## Step 3 — the gates, and they are the whole exception list

A gate stops that branch, never the whole task.

- **A CAPTCHA is where automation stops.** Fill everything, bring the window to the front,
  and tell the human the one click. Everything after it is automatable again.
- **A passkey challenge is the same gate.** Sites like Google re-challenge a copied session
  after it has been used once, so do every step for that site in the FIRST launch.
- **An invisible reCAPTCHA on a login is the same gate, and it looks like a hang.** An
  email-and-password login that sits on "Logging in..." forever behind a reCAPTCHA frame will
  not finish. A password reset usually does work headless (request it, read the link from your
  mail, set the password, store it in Keychain), but the login after it still waits. The human
  logs in once in their own Chrome; a fresh cookie copy then lands signed in, and an API token
  can be read off the settings page.
- **Copied SSO can be dead.** Google's account chooser may show "Signed out", and GitHub's
  `user_session` cookie may have expired that day. Check `expires_utc` on
  `github.com|user_session` in the copied Cookies file before relying on "Sign in with GitHub".
- **Money.** Surface the price; never pay without an explicit go.
- **An OAuth consent screen is the human's to grant, and scopes are not equal.** Read the
  scope list out in the report and say where it is revocable (e.g.
  `github.com/settings/applications`).
- **Anything that messages a stranger.** Draft it; a human presses send.
- **Never use this on someone else's account**, and respect each site's terms on automation.

## Step 4 — a verification code is not a gate

Sign-ups often mail a 6-digit code or a magic link. **Read it** from your mail (Gmail or
Zoho MCP, or IMAP). An OTP widget is usually six `input[inputmode=numeric]` boxes:
`.focus()` the first and send `keyboard.press("Digit<n>")` per character. Setting `.value`
and `type()` per box both fail.

**An SMS code is readable too, if your texts sync to the Mac.** Query
`~/Library/Messages/chat.db` for rows in the last few minutes — on current macOS the `text`
column is NULL and the body lives in the `attributedBody` blob, so pull
`hex(attributedBody)`, `xxd -r -p | strings`, and grep the digits. A poll that filters on
`text LIKE '%code%'` waits forever. (Needs Full Disk Access for the terminal.)

**An emailed confirmation link must be opened in the browser holding the session** — launch
Chrome with the same `--user-data-dir` on the link. `curl` returns 200 and confirms nothing.

## Step 5 — verify against the world, never the exit code

**A zero exit from an uploader or a form is not proof anything happened.** An upload can exit
0 having uploaded only metadata, because a `.gitignore` inside the folder was honoured.
Read the state back off the service's own API and compare it to what you sent: file counts,
row counts, the field you changed.

Then **record it**: what exists now, under which account, which scopes were granted, where
the credential is stored, and what is left for the human. An account created and never
written down is a credential nobody can find later.

## Substack notes

- **Never publish on your Substack unless you asked for that specific post.** A third-party
  ownership check that wants a verification post is the owner's to do by hand.
- **Publishing needs a FRESH sign-in.** Copied cookies read and write drafts, but `POST
  /api/v1/drafts/{id}/publish` returns 403 `reauthentication_required`. Use a clean profile:
  enter your email on `substack.com/sign-in`, open the emailed "Confirm your email" link in
  that browser; that session publishes. `{send:false}` publishes web-only (no subscriber
  email); `PUT /api/v1/drafts/{id} {post_date}` after publish backdates. Pace calls ~3s and
  retry 429s after 20s.
- **Check a publication name first:** `curl -s -o /dev/null -w '%{http_code}'
  https://<sub>.substack.com/` — 404 means free.
- Tune a publication through internal endpoints with in-page `fetch`: `PUT
  /api/v1/publication` (name, hero_text, email_from_name, welcome email), `PUT
  /api/v1/publication/publication_tags {tag_ids}` (ids from `GET
  substack.com/api/v1/categories`), `PUT /api/v1/publication_settings`.
- **A toggle click FLIPS it: read `aria-checked` first.**
- **Notes can't be automated**: the Notes endpoint returns a Cloudflare 403 to headless
  Chrome even after a fresh login. Post Notes by hand.

## Driving the Chrome you already have open

When the user says "take over, I already have Chrome open", use their window rather than a copy.
Passkey-guarded sessions (the OpenAI platform, for one) only work there.

- **AppleScript `execute javascript` is unreliable here.** It needs View > Developer > Allow
  JavaScript from Apple Events, and even with that on, `tell application "Google Chrome"` can
  attach to another process's headless Chrome instead of the user's window. Check `ps` first.
- **Plain GUI driving works.** `screencapture -x`, then read the PNG. `cliclick c:x,y` clicks in
  points, and the screenshot is retina pixels, so scale by (screen width in points) / (image
  width). System Events `keystroke` sends keys. `pbcopy` + Cmd+V pastes text fast, newlines
  included. Page Down (key code 121) after clicking blank space scrolls a panel. A panel's own
  copy button + `pbpaste` reads a token with no OCR mistakes.
- **Navigate with Cmd+L, paste, Return.** `set URL of active tab of front window` can hit another
  session's Chrome, because `front window` isn't always the user's.
- **Find click targets by OCR, not by eye.** Save the helper below as `ocr.swift`, build it
  with `swiftc -O ocr.swift -o ocr`, then `screencapture`, `sips -Z <width in points>`, and
  `./ocr shot.png` prints `text|x|y` per text block. Wait about 4 s after navigating before you
  OCR, or labels are missing.

  ```swift
  import Vision
  import AppKit
  // usage: ocr <png> ; prints "text|x|y" in image-point coords (top-left origin), x,y = center
  let url = URL(fileURLWithPath: CommandLine.arguments[1])
  let img = NSImage(contentsOf: url)!
  var rect = CGRect(origin: .zero, size: img.size)
  let cg = img.cgImage(forProposedRect: &rect, context: nil, hints: nil)!
  let W = CGFloat(cg.width), H = CGFloat(cg.height)
  let req = VNRecognizeTextRequest()
  req.recognitionLevel = .accurate
  try! VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
  for o in req.results ?? [] {
    guard let t = o.topCandidates(1).first else { continue }
    let b = o.boundingBox
    let x = (b.midX * W), y = ((1 - b.midY) * H)
    print("\(t.string)|\(Int(x))|\(Int(y))")
  }
  ```
- **File pickers:** click the upload button, then Cmd+Shift+G, the path, Return, Return. Cmd+Shift+G
  before the picker is open opens Chrome's find bar instead.
- **A demo video** is `screencapture -v -V <secs> -R<window rect>` running in the background
  while a script drives the page. In ChatGPT, attach a developer plugin by typing `@<App name>`
  and Return; without that it answers from web search.

## Google Maps saved lists: never with copied cookies

- **Copied cookies read Maps but can't write it, and trying signs your real Chrome out of
  Google.** "Create list" returned "Failed to create list", the next action bounced to the
  account chooser, and the user's own Maps then showed "Sign in". It happened twice; a fresh
  cookie copy and a normal user agent didn't help. Drive the user's own window (with their OK,
  since it takes over the screen). Signing back in needs their passkey.
- **Reading a whole list:** open it (its id is the `!2s<id>` part of the URL), open DevTools
  (Cmd+Opt+J), and paste
  `fetch('/maps/preview/entitylist/getlist?authuser=0&hl=en&gl=us&pb=!1m4!1s<id>!2e1!3m1!1e1!2e2!3e2!4i500!16b1')`,
  then `copy()` the text and `pbpaste`. Entries are at
  `d[0][8]`: `e[2]` name, `e[1][2]` address, `e[1][5][2:4]` lat/lng, and `e[1][6]` the two
  signed-int64 halves of the feature id. The second half, read unsigned, is the `?cid=`.
- **Moving a place between lists:** open `maps.google.com/?cid=N`, click Save, then the target
  list. Click Save again, then the source list to uncheck it. Checked lists sort to the top of
  the menu, so find each list by its text every time, never by position. The Save icon sits
  about 45 pt above its "Save"/"Saved" label in an OCR read.

## Launch-night sign-ups and posts (2026-11)

- **X:** automated **email** signup is refused ("Please try using a different method").
  "Continue with Google" in the user's own Chrome works; they approve the passkey, fill in the
  birthday and pick the handle. Skip X's passkey offer. Brand accounts only, never a pseudonym
  persona.
- **Hacker News:** signup has a reCAPTCHA, so automation stops there. A low-karma account's
  submission can be killed on submit; see `distribution-channel`.
- **Whop:** no password; you sign in with an emailed code (read it from your mail). A store's
  "Contact support" messages its admin team with no purchase.
- **OpenAI platform:** a Google + passkey sign-in can't be copied to another browser. Work in a
  new tab of the user's own Chrome. Plugin submission is ZIP upload only; see `tool-launch`.
- **Reddit:** a copied session can be stale; check before assuming you're signed in.
- **Credentials** for anything new go in `~/.config/<project>/accounts.txt` (chmod 600), never in
  a repo.
