---
name: test-it
description: Functionally verify that a shipped change actually works — not just that it deployed. Use automatically, without being asked, whenever a change has runtime behavior (a tracking event, form handler, API wiring, redirect, webhook, script flag) rather than only visual/copy changes. Complements visual QA and content QA: this is the third leg, does the code path actually execute correctly when triggered.
---

# Test It

"Committed and pushed" is not "works." A change can be on `main`, deployed,
and still be dead code — a typo'd event name, a handler wired to the wrong
element, a flag that's silently ignored. Prove the behavior, don't infer it
from reading the diff.

**Do this proactively, on every change with runtime behavior, without being
asked.** "Did you actually test it" should never be a question the user has to
remember to ask.

## When to use

Any shipped change where something *executes* at runtime — not pure
copy/CSS:

- A new or edited analytics/tracking event (PostHog, Pixel, GA)
- A form handler, API call, or webhook
- A redirect (Stripe success URL, QR code target)
- A script flag or CLI argument that changes behavior
- Anything with a success/failure branch (try/catch, `if (res.ok)`)

Not this skill: pure visual changes (-> a phone-width visual audit such as
`mobile-ui-audit`), content quality, or writing voice. Those check different
things: a page can pass a visual audit and still have a broken submit handler
underneath it.

## The three separate claims — verify each one, don't conflate them

1. **Committed** — `git log` shows the commit locally.
2. **Pushed** — local HEAD matches `origin/<branch>` (`git fetch` then
   compare, don't assume `git push` succeeded from its exit code alone).
3. **Deployed and live** — the actual behavior in question is present on the
   real URL, not just "Vercel probably built it." Fastest check: `curl` the
   live page for a string unique to the new code
   (`curl -s <url> | grep "your_new_event_name"`).

None of these three prove the code *works* — only that it *shipped*. That's
the next step.

## The functional test — exercise the real code path, mock the side effect

Load the **live** page in the puppeteer MCP and drive the real DOM/JS path
end to end, but intercept whatever call would create a real-world side
effect (a lead in your CRM, a Stripe charge, an email, a Slack message) so the
test doesn't pollute production data. The logic under test still runs for
real — only the network call at the boundary is mocked.

Pattern (adapt the intercepted call and the triggering DOM actions to the
feature under test):

```js
mcp__puppeteer__puppeteer_navigate({ url: "https://the-live-url/..." });

mcp__puppeteer__puppeteer_evaluate({ script: `
(async () => {
  // 1. Wait for any async-loaded dependency (e.g. posthog) to be ready.
  const waitFor = (fn, timeout=5000) => new Promise((resolve, reject) => {
    const start = Date.now();
    const iv = setInterval(() => {
      if (fn()) { clearInterval(iv); resolve(true); }
      else if (Date.now() - start > timeout) { clearInterval(iv); reject(new Error('timeout')); }
    }, 100);
  });
  await waitFor(() => window.posthog && typeof posthog.capture === 'function');

  // 2. Record calls to the thing you're verifying fires, without blocking it.
  const captured = [];
  const origCapture = posthog.capture.bind(posthog);
  posthog.capture = function (name, props) { captured.push({name, props}); return origCapture(name, props); };

  // 3. Intercept the side-effecting network call so nothing real happens.
  const origFetch = window.fetch;
  let fetchCalledWith = null;
  window.fetch = function (url, opts) {
    fetchCalledWith = { url, body: opts && opts.body };
    return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }));
  };

  // 4. Drive the REAL user path through the REAL handler — fill fields,
  //    dispatch real events, don't call internal functions directly.
  document.querySelector('input[name="interest"]').checked = true;
  document.querySelector('input[name="interest"]').dispatchEvent(new Event('change', { bubbles: true }));
  document.getElementById('nameInput').value = 'QA Test — not a real lead';
  document.getElementById('intakeForm').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  await new Promise(r => setTimeout(r, 400));

  window.fetch = origFetch;
  posthog.capture = origCapture;

  return { fetchIntercepted: !!fetchCalledWith, fetchUrl: fetchCalledWith && fetchCalledWith.url, captured };
})()
`});
```

Read the result for the *specific claim*, not just "no errors": did the
right event fire, with the right payload, gated behind the right condition
(only on success, not on click)? A test that only checks "no JS exception"
would have passed even if the event never fired.

## Non-browser equivalents

The same principle applies off the web — exercise the real code path,
intercept only the side-effecting boundary:

- **Python scripts with an external API call** (Stripe, a CRM, an email
  service, file storage): run with the real function but monkeypatch the client/`requests`
  call, or use the script's own `--dry-run` flag if it has one — don't just
  read the function and assert it "looks right."
- **Redirect/URL correctness** (payment-link success URLs, QR targets): actually request the URL and check the response, don't
  compare strings in config.
- **CLI flags**: run the command with the flag and diff real output against
  the no-flag baseline, not just grep the argparse definition.

## Gotchas

- **Never let the intercepted test create a real side effect.** A skipped
  mock means a fake lead in the sales pipeline, a real (if $0) Stripe
  event, or a real email/Slack message someone downstream will act on.
  Always mock `fetch`/the client call before triggering the real action.
- **Test the live URL, not just the local file**, when the deploy step
  matters (this is what actually separates this from `mobile-qa`, which is
  fine to iterate against `file://` locally). A local-only pass can hide a
  deploy that never went out or a CDN cache serving stale JS.
- **Restore the monkeypatches** (`window.fetch = origFetch`, etc.) at the
  end of the eval — the puppeteer session can persist across calls in the
  same conversation.
- **Report what you actually verified, not what you assume.** "Committed
  and pushed" and "confirmed working on the live URL" are different
  sentences — say which one you did.

## Worked example

A landing page shipped a `get_started_submitted` analytics event that should fire only after
the lead form's POST returns success. Verified live: navigated to the production page, mocked
`fetch` to return a fake 200 without hitting the real endpoint (so no fake lead landed in the
real CRM), drove the actual form fill + native `submit` event, and confirmed the event fired
with the right `interest` payload, and did *not* fire on the earlier click or on page load.
