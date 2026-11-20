---
name: museum-open-access
description: Pull real public-domain artworks from museum open-access APIs (Art Institute of Chicago, Cleveland Museum of Art) for plates, covers, an artist in residence, or any page that needs credited public-domain art. Use when a task says "find public-domain works by <artist>", "artist in residence", "plates for the issue", "museum images", "CC0 art", "is this really by <artist>", or when a page using AIC/Cleveland images shows no art, CORS errors, or "0 plates". Carries the attribution trap (a work filed under an artist that isn't theirs) and the headless-browser trap that fakes a CORS failure.
compatibility: Network access to api.artic.edu, www.artic.edu, openaccess-api.clevelandart.org, www.clevelandart.org
metadata:
  network-hosts: "api.artic.edu www.artic.edu openaccess-api.clevelandart.org www.clevelandart.org"
---

# Museum open-access art

Everything below was measured against the live APIs on 2026-11-20, while building a print-magazine tool
that sets one artist's real public-domain works as its plates.

## Rules

1. **Public domain means the museum's flag, nothing else.** AIC: `is_public_domain: true`.
   Cleveland: `share_license_status === "CC0"`. Re-check at the moment of use, not only at search.
   *Why:* a death date or a "looks old" guess is how a copyrighted work ends up printed and sold.
2. **Attribution comes from the full display string, never the linked name.** AIC's `artist_title`
   is the linked agent. It read "Thomas Bewick" for aic:83463, while `artist_display` read
   "Possibly after Thomas Bewick … or Frederick Wilton Litchfield Stockdale". That work nearly became the
   cover of an issue whose back cover credits Bewick as the artist.
   - Reject a work whose `artist_display` contains after, possibly, probably, attributed,
     follower/circle/school/workshop/studio of, copy, manner, style, pupil, or offers two artists
     joined by "or".
   - Cleveland: every creator's `qualifier` must be empty, with exactly one creator in the
     `artist` role.
   - The same check is why Audubon returns nothing: the museums' Birds of America plates are
     Havell *after* Audubon.
3. **Dedupe on the museum id, never on the title.** Bewick has many works called "Vignette";
   merging by title cut him from 44 works to 26.
4. **Credit every work:** title, date, museum, licence. One work per slot per issue
   (no repeats).

## Images

- **AIC IIIF:** `https://www.artic.edu/iiif/2/<image_id>/full/<size>/0/default.jpg`, with
  `Access-Control-Allow-Origin: *`.
  - These size forms work: `843,`, `1686,` and `!3000,3000`.
  - These answer 403 with **no CORS header**: `!1200,1200`, `!2000,2000`, `3600,` and `full`. The
    browser reports that as a CORS failure.
  - Use `1686,` for previews and `!3000,3000` for print (measured 2026-11-20, `_art.js` header).
- **Cleveland's CDN sends no CORS header,** so the browser can't read its pixels. Proxy them
  through a route of your own. Vercel caps a response at 4.5 MB, so skip print files
  bigger than that. This is the one per-view cost.
- **Print sharpness:** full-bleed ppi = long-side px ÷ 11.25 in (letter plus bleed). 200+ prints
  sharp. Never set a plate larger than its pixels support.
- **White-on-black stencils need line work** (etching, engraving, woodcut, pen, pencil). Tonal
  media (lithograph, charcoal, wash, watercolour, photograph) render as a black slab. Redon did
  exactly that on the first test issue.

## QA trap: headless Chrome gets no art

AIC's image CDN refuses the **HeadlessChrome user agent**. Playwright with its default UA showed 18
CORS errors and "0 works". The same page with a normal Chrome UA loaded every plate (2026-11-20).
curl gets 200 as well. So in any headless QA, set:

    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

before reporting a missing-image bug. Real visitors aren't affected.

## Related

`build-remote-mcp-server`.
