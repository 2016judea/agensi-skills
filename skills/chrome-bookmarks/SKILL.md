---
name: chrome-bookmarks
description: Read, add, move or reorganize Chrome bookmarks on macOS from an agent — "organize my bookmarks", "put these in a folder", "bookmark these", "move X under Y", "sort my bookmarks bar", "add a bookmark for each". The tool skill: why editing the Bookmarks JSON file gets undone by Chrome Sync, and the chrome.bookmarks-via-AppleScript route that sticks.
---

# Chrome bookmarks (macOS)

The default profile is `~/Library/Application Support/Google/Chrome/Default`. Assume bookmark
**Sync is on** unless you have checked.

## Rule 1: never edit the `Bookmarks` file to move things

**Why:** with Chrome quit, the JSON edited and `checksum` removed, a relaunch kept the *new*
nodes but every *existing* node that had been moved snapped back to its old position from the
Sync server, and new folders landed at the end. Reading the file is fine and is the fastest way
to inspect the tree; writing it is not.

## The route that works: `chrome.bookmarks` inside `chrome://bookmarks`

The bookmarks manager WebUI exposes `chrome.bookmarks` (getTree, getChildren, create, move,
remove, getSubTree). Drive it with AppleScript `execute … javascript`:

```bash
scripts/run_in_bookmarks.sh my.js 6     # run my.js in the chrome://bookmarks tab, wait 6 s, print window.__r
```

The JS must be an async IIFE that writes its result to `window.__r`: `execute` returns before
promises settle, so the runner waits and then reads `__r`. Wrap the body in
`.catch(e=>window.__r='ERR '+e.stack)`.

```js
(async()=>{
  const C = chrome.bookmarks;
  const P = fn => (...a) => new Promise((res, rej) =>
    C[fn](...a, r => chrome.runtime && chrome.runtime.lastError ? rej(chrome.runtime.lastError) : res(r)));
  const g = P('getChildren'), create = P('create'), move = P('move');
  // find-or-create a folder (idempotent)
  const folder = async (parent, title) =>
    (await g(parent)).find(n => !n.url && n.title === title) || create({parentId: parent, title});
  // add a link only if the folder doesn't already hold that URL (idempotent)
  const add = async (parent, title, url) => {
    if (!(await g(parent)).find(n => n.url === url)) await create({parentId: parent, title, url});
  };
  const bar = '1';                       // bookmarks bar; '2' = Other bookmarks
  const f = await folder(bar, 'Reading');
  await add(f.id, 'Example', 'https://example.com/');
  window.__r = JSON.stringify((await g(f.id)).map(n => n.title));
})().catch(e => window.__r = 'ERR ' + e.stack);
```

- **Prerequisite:** "Allow JavaScript from Apple Events" (View → Developer) must be on.
  Clicking the menu item through System Events did not flip it. What works: quit Chrome, set
  `"browser": {"allow_javascript_apple_events": true}` in `Default/Preferences`, relaunch.
- **Find the tab by URL**, not "active tab" — the user may switch tabs mid-run. The runner does.
- **Kill any headless Chrome you launched first** (by its own `--remote-debugging-port`, never a
  blanket pkill). With a headless instance alive, AppleScript can talk to *it*, and
  `getChildren('1')` returns an empty bar — it looks as if the bookmarks are gone. They are not.
  The runner refuses to run while a `--headless` process exists.
- Make every add idempotent: re-runs happen.
- Confirm by re-reading the `Bookmarks` file after the run.

## Quit and relaunch without losing tabs

Needed only for the Preferences toggle: `osascript -e 'tell application "Google Chrome" to quit'`,
then TERM any leftover `--no-startup-window` process (Chrome running in the background, holding
the profile). Leave alone any process started with its own `--user-data-dir`. Relaunch with
`open -a "Google Chrome" --args --restore-last-session`.
