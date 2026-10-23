# Findings: symptom → true cause → the fix to recommend

Back-referenced from `SKILL.md`, rule 2. Each row says what the visitor experiences, then the cause a developer will confirm, then the fix. Use only the rows the audit actually showed on that site, and add a row the first time a new kind of bug turns up.

| What the visitor hits | True cause (how to confirm) | Recommend to your developer that they… |
|---|---|---|
| The address or card doesn't auto-fill at checkout (never the only finding; see SKILL rule 3) | The inputs are missing `autocomplete` tokens (`street-address`, `postal-code`, `email`, `tel`, `cc-number`), or the `name`/`id` values are random. Confirm by reading the form's DOM. | add the standard `autocomplete` attributes to each checkout field |
| Tapping a box zooms the page, then scrolling "breaks" and the menu can't be reached | An `input`, `select` or `textarea` is smaller than 16px on iOS. The audit marks it as a FAIL, an iOS zoom trap. | set form fields to at least 16px on phones (see `mobile-ui-audit` for the fix by stack) |
| The page slides sideways on a phone | Something is wider than the viewport and no parent element clips it. The audit marks it as sideways overflow. | constrain that element's width (name the element from the audit JSON) |
| Can't scroll down to the menu or the order button | The document is locked (`overflow:hidden` on html/body, often left behind by a popup) and nothing inside it scrolls. | remove the scroll lock, or release it when the popup closes |
| A popup or banner covers most of the screen and won't close | A fixed layer covers 40% or more of the screen with no reachable close button. Confirm it in the screenshot. | make the overlay closable on mobile, or smaller |
| A link on the order/menu path is dead | The link returns HTTP 400 or higher. Quote the URL. | fix or remove the broken link to <url> |
| The whole site shows up shrunk to a tiny desktop page on a phone, so you have to pinch to read anything | The page has no `<meta name="viewport" content="width=device-width, initial-scale=1">`, so phones render it at 980px wide and shrink it. Confirm with view-source. Audit: WARN `viewport meta: missing`. | add the viewport meta tag (and check the layout once it's on) |
| A picture on the page shows as a broken image | The image URL answers an error, so the `<img>` loads no pixels (`naturalWidth` 0). Quote the URL. | re-upload or re-link the image at <url> |
| The order / book / gift card button goes to an error page | That link answers HTTP 404 (or 410/500) twice. Quote the button text and the URL. | point the <button text> button at the live ordering page |
| The site errors out or is blank on a phone | A page error or JS exception shows up in the audit console. | look at the JavaScript error on <page> (quote the message) |

Never write a cause that isn't in this table, or that you didn't confirm in the DOM. If you haven't confirmed the cause, write only the symptom and "Recommend to your developer that they take a look."

These two are deliberately not on the list: small tap targets and a pinch-zoom cap. They're real, but they aren't big (SKILL rule 3). A visitor never notices them as broken.
