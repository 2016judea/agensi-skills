#!/usr/bin/env python
"""Mobile UI audit — the checks a phone visitor would fail on, run on real engines.

Born from a "mobile scroll is broken" report,
where every emulator scrolled cleanly and the real fault (an input under 16px that
makes iOS Safari zoom in and stay zoomed) was only visible as a *static property*
of the page. So this audit measures properties a device would act on, rather than
trusting that an emulated scroll "worked".

Engines: Playwright WebKit with the iPhone 13 profile (closest free thing to
Mobile Safari) and Chromium with the Pixel 5 profile. Needs
`pip install playwright && playwright install webkit chromium`.

Usage:
    audit.py URL [URL ...]            audit these pages
    audit.py --vercel                 every production alias on the Vercel team
    audit.py --vercel --crawl 4       plus up to 4 same-origin pages per site
    audit.py ... --json out.json      machine-readable rows as well as the table
    audit.py ... --shots DIR          top-of-page iPhone screenshots per URL

Exit status is 1 when any FAIL row exists, so a cron or a hook can gate on it.

Severity:
    FAIL  the visitor cannot do the thing: zoom trap, sideways overflow,
          document locked with content unreachable, page error, non-200.
    WARN  the visitor can do it but badly: tap targets under 24px, text under
          12px, a fixed layer covering >40% of the screen, scale caps in the
          viewport meta, header not back at y=0 after a scroll round-trip.
    INFO  measured but not judged: scroll model, document weight, inner scrollers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright  # noqa: E402

TEAM = os.environ.get("VERCEL_TEAM_ID", "")  # your Vercel team id; empty = personal account
DEVICES = {"iphone": ("webkit", "iPhone 13"), "android": ("chromium", "Pixel 5")}

PROBE = r"""() => {
  const d = document, h = d.documentElement, vw = innerWidth, vh = innerHeight;
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0'; };
  const tag = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '');
  const meta = (d.querySelector('meta[name=viewport]') || {}).content || null;

  // 1. iOS zoom trap: any text-entry control under 16px.
  const zoomTrap = [...d.querySelectorAll('input,textarea,select')]
    .filter(el => !['checkbox','radio','file','hidden','range','color','submit','button','image','reset'].includes(el.type) && vis(el))
    .map(el => ({ el: tag(el), fs: parseFloat(getComputedStyle(el).fontSize) }))
    .filter(x => x.fs < 16);

  // 2. Sideways overflow that nothing clips before the body.
  const clips = el => { for (let a = el.parentElement; a && a !== d.body; a = a.parentElement) {
    const s = getComputedStyle(a); if (s.overflowX !== 'visible' || (s.contain || '').includes('paint')) return true; } return false; };
  const leaks = [...d.querySelectorAll('body *')]
    .filter(el => { if (el.closest('svg') && el.tagName !== 'svg') return false; const r = el.getBoundingClientRect();
      return r.width > 0 && r.right > vw + 1 && !clips(el); })
    .slice(0, 6).map(el => tag(el) + ' right=' + Math.round(el.getBoundingClientRect().right));
  const docWider = h.scrollWidth > vw + 1;

  // 3. Scroll model.
  const ho = getComputedStyle(h).overflowY, bo = getComputedStyle(d.body).overflowY;
  const docLocked = ho === 'hidden' || (bo === 'hidden' && ho !== 'auto' && ho !== 'scroll');
  const scrollers = [...d.querySelectorAll('*')].filter(el => el !== d.body && el !== h && vis(el) && /(auto|scroll)/.test(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight + 2)
    .map(el => ({ el: tag(el), client: el.clientHeight, scroll: el.scrollHeight }));
  const docH = h.scrollHeight;
  const unreachable = docLocked && docH > vh + 2 && scrollers.length === 0;

  // 4. Fixed or sticky layers and how much of the screen they take.
  const layers = [...d.querySelectorAll('*')].filter(el => { const s = getComputedStyle(el); return (s.position === 'fixed' || s.position === 'sticky') && vis(el) && s.pointerEvents !== 'none'; })
    .map(el => { const r = el.getBoundingClientRect(); const w = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0)); const hh = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
      return { el: tag(el), pos: getComputedStyle(el).position, cover: Math.round(100 * w * hh / (vw * vh)) }; })
    .filter(l => l.cover >= 1).sort((a, b) => b.cover - a.cover).slice(0, 5);

  // 5. Tap targets under 24px (WCAG 2.5.8 minimum; Apple asks 44).
  const targets = [...d.querySelectorAll('a[href],button,input,select,textarea,[role=button],[onclick]')].filter(vis);
  const small = targets.filter(el => { const r = el.getBoundingClientRect(); return (r.width < 24 || r.height < 24) && r.width > 2 && r.height > 2; });  // 1x1 = skip-link / sr-only, deliberate
  const smallList = small.slice(0, 5).map(el => { const r = el.getBoundingClientRect(); return tag(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height); });

  // 6. Text under 12px, counted by element with its own text.
  const tiny = [...d.querySelectorAll('body *')].filter(el => vis(el) && el.childNodes.length && [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2) && parseFloat(getComputedStyle(el).fontSize) < 12);
  const tinyList = tiny.slice(0, 4).map(el => tag(el) + ' ' + getComputedStyle(el).fontSize);

  // 7. Header / first landmark position.
  const head = d.querySelector('header,nav,[role=banner]');
  const headTop = head ? Math.round(head.getBoundingClientRect().top) : null;

  // 8. Form fields : what a phone keyboard and autofill would see.
  //    `kind` is what the field asks for, read from type/name/id/placeholder/label; `type` is what it declares.
  const labelOf = el => { const l = (el.id && d.querySelector('label[for="' + CSS.escape(el.id) + '"]')) || el.closest('label'); return l ? l.textContent.trim().slice(0, 40) : ''; };
  const fields = [...d.querySelectorAll('input,textarea,select')]
    .filter(el => !['checkbox','radio','file','hidden','range','color','submit','button','image','reset'].includes(el.type) && vis(el))
    .map(el => { const hint = [el.type, el.name, el.id, el.placeholder, el.getAttribute('aria-label') || '', labelOf(el)].join(' ').toLowerCase();
      const kind = /e-?mail/.test(hint) ? 'email' : /phone|\btel\b|mobile|cell/.test(hint) ? 'tel' : /zip|postal/.test(hint) ? 'postal' : /address|street/.test(hint) ? 'address' : /card|cc-?num/.test(hint) ? 'card' : /name/.test(hint) ? 'name' : 'other';
      return { el: tag(el), type: el.type || el.tagName.toLowerCase(), name: el.name || '', kind, autocomplete: el.getAttribute('autocomplete'),
               inputmode: el.getAttribute('inputmode'), hint: (el.placeholder || labelOf(el) || el.name || '').slice(0, 40) }; });
  const wrongKeyboard = fields.filter(f => (f.kind === 'email' && f.type !== 'email' && f.inputmode !== 'email') || (f.kind === 'tel' && f.type !== 'tel' && f.inputmode !== 'tel' && f.inputmode !== 'numeric'))
    .filter(f => f.type === 'text' || f.type === 'textarea');
  const autofillOff = fields.filter(f => ['email','tel','name','address','postal','card'].includes(f.kind) && /^(off|nope|false|none)$/i.test(f.autocomplete || ''));

  // 9. Images that failed to load (complete, but no pixels).
  const brokenImgs = [...d.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth === 0 && (i.currentSrc || i.src) && !/^data:/.test(i.src) && i.loading !== 'lazy')
    .slice(0, 5).map(i => (i.currentSrc || i.src).slice(0, 160));

  // 10. Links on the money path: order / book / reserve / shop / gift / menu, by visible text or href.
  const MONEY_RE = /\b(order|book|reserv|appointment|schedule|shop|store|gift|menu|buy|checkout|cart)/i;
  const moneyLinks = [...d.querySelectorAll('a[href]')].filter(a => !/^(mailto|tel|sms|javascript):|^#/.test(a.getAttribute('href') || ''))
    .map(a => ({ text: (a.textContent || a.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40), href: a.href }))
    .filter(l => MONEY_RE.test(l.text) || /toasttab|order\.online|chownow|olo\.com|square\.site|clover|opentable|resy|tock|sevenrooms|vagaro|booksy|glossgenius|fresha|mindbody|schedulicity|styleseat|boulevard|joinblvd|acuity|calendly|setmore|giftup/i.test(l.href));
  const allLinks = [...new Set([...d.querySelectorAll('a[href]')].map(a => a.href).filter(h => /^https?:/.test(h)))];

  return { meta, vw, vh, docH, zoomTrap, leaks, docWider, docLocked, scrollers: scrollers.slice(0, 4), unreachable, layers,
           targets: targets.length, small: small.length, smallList, tiny: tiny.length, tinyList, headTop, headTag: head ? tag(head) : null,
           textLen: (d.body && d.body.innerText || '').trim().length, fields, wrongKeyboard, autofillOff, brokenImgs, moneyLinks: moneyLinks.slice(0, 12), allLinks: allLinks.slice(0, 80),
           weight: (performance.getEntriesByType('navigation')[0] || {}).transferSize || null, title: d.title };
}"""

# Reproduce sideways overflow rather than infer it: try to pan the page and read where it lands.
PAN = r"""async () => { window.scrollTo(400, 0); await new Promise(r => setTimeout(r, 150)); const x = Math.round(scrollX); window.scrollTo(0, 0); return x; }"""

ROUNDTRIP = r"""async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const head = document.querySelector('header,nav,[role=banner]');
  const sc = [...document.querySelectorAll('*')].find(el => el !== document.body && /(auto|scroll)/.test(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight + 2);
  window.scrollTo(0, 1e6); if (sc) sc.scrollTop = 1e6; await sleep(250);
  const atBottom = { y: Math.round(scrollY), inner: sc ? Math.round(sc.scrollTop) : null };
  window.scrollTo(0, 0); if (sc) sc.scrollTop = 0; await sleep(250);
  return { atBottom, backY: Math.round(scrollY), backInner: sc ? Math.round(sc.scrollTop) : null,
           headTop: head ? Math.round(head.getBoundingClientRect().top) : null };
}"""


def vercel_sites() -> list[str]:
    import urllib.request
    env = Path(os.environ.get("VERCEL_ENV_FILE", ".env")).expanduser()
    tok = os.environ.get("VERCEL_TOKEN")
    if not tok and env.exists():
        m = re.search(r"^VERCEL_TOKEN=(.+)$", env.read_text(), re.M)
        tok = m.group(1).strip().strip('"') if m else None
    if not tok:
        sys.exit("VERCEL_TOKEN not found (env var, ./.env, or VERCEL_ENV_FILE)")
    req = urllib.request.Request("https://api.vercel.com/v9/projects?limit=100" + (f"&teamId={TEAM}" if TEAM else ""), headers={"Authorization": f"Bearer {tok}"})
    data = json.load(urllib.request.urlopen(req))
    out = []
    for p in data.get("projects", []):
        prod = p.get("targets", {}).get("production") or {}
        aliases = prod.get("alias") or []
        # Prefer a custom domain, then the shortest <name>.vercel.app. The team-scoped
        # `-<team-slug>-projects` and `-git-` aliases sit behind Vercel SSO and audit
        # as a login page with a 200, so never pick them.
        aliases = [a for a in aliases if "-projects." not in a and "-git-" not in a]
        custom = [a for a in aliases if not a.endswith(".vercel.app") and not a.startswith("www.")]
        short = sorted((a for a in aliases if a.endswith(".vercel.app")), key=len)
        pick = (custom or short or [None])[0]
        if pick:
            out.append("https://" + pick + "/")
    return out


def crawl(page, base: str, limit: int) -> list[str]:
    """Same-origin pages: sitemap first, then links on the home page."""
    found: list[str] = []
    origin = urlparse(base).netloc
    try:
        r = page.request.get(urljoin(base, "/sitemap.xml"), timeout=8000)
        if r.ok:
            for loc in re.findall(r"<loc>([^<]+)</loc>", r.text()):
                if urlparse(loc).netloc == origin and loc.rstrip("/") != base.rstrip("/"):
                    found.append(loc)
    except Exception:
        pass
    if len(found) < limit:
        try:
            hrefs = page.evaluate("[...document.querySelectorAll('a[href]')].map(a => a.href)")
            for h in hrefs:
                u = urlparse(h)
                if u.netloc == origin and not u.fragment and h.rstrip("/") != base.rstrip("/") and h not in found and not re.search(r"\.(pdf|png|jpe?g|csv|json|zip|xml)$", u.path):
                    found.append(h)
        except Exception:
            pass
    seen, out = set(), []
    for u in found:
        k = u.rstrip("/")
        if k not in seen:
            seen.add(k); out.append(u)
    return out[:limit]


SKIP_LINK = re.compile(r"facebook\.com|instagram\.com|twitter\.com|x\.com/|tiktok\.com|linkedin\.com|youtube\.com|pinterest\.|yelp\.com|google\.[a-z.]+/maps|maps\.app\.goo|goo\.gl|tripadvisor|wa\.me|apple\.com/maps", re.I)


def check_links(page, hrefs: list[str]) -> list[dict]:
    """HTTP status of each link, GET with the page's own context, twice before calling it dead.

    Social and map hosts are skipped: they 4xx/999 to any script and the visitor sees them fine.
    A link is dead only when both tries answer >= 400 (a 403/429 from a bot wall is reported as
    `blocked`, never as dead, because the developer will open it in a browser and see it work).
    """
    out, seen = [], set()
    for h in hrefs:
        k = h.split("#")[0]
        if k in seen or SKIP_LINK.search(k) or not k.startswith("http"):
            continue
        seen.add(k)
        codes = []
        for _ in range(2):
            try:
                codes.append(page.request.get(k, timeout=12000, max_redirects=10).status)
            except Exception as e:
                codes.append(type(e).__name__)
            if codes[-1] == 200:
                break
        last = codes[-1]
        if isinstance(last, int) and last >= 400:
            out.append({"href": k, "codes": codes, "verdict": "blocked" if last in (401, 403, 429, 503, 999) else "dead"})
    return out


def money_hop(page_url: str, row: dict) -> str | None:
    """The first same-origin order/book/shop/menu page linked from this page, for a one-hop audit."""
    origin = urlparse(page_url).netloc.replace("www.", "")
    for l in row.get("moneyLinks") or []:
        u = urlparse(l["href"])
        if u.netloc.replace("www.", "") == origin and l["href"].split("#")[0].rstrip("/") != page_url.rstrip("/"):
            return l["href"].split("#")[0]
    return None


def audit_page(ctx, url: str, shots: Path | None, dev: str, links: bool = False) -> dict:
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)[:140]))
    page.on("console", lambda m: errors.append("console: " + m.text[:140]) if m.type == "error" else None)
    row: dict = {"url": url, "device": dev}
    t0 = time.time()
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=45000)
        row["status"] = resp.status if resp else None
    except Exception as e:
        try:
            resp = page.goto(url, wait_until="load", timeout=45000)
            row["status"] = resp.status if resp else None
            row["note"] = "networkidle never settled"
        except Exception as e2:
            row.update(status=None, error=str(e2)[:160], findings=[("FAIL", "did not load: " + str(e2)[:100])])
            page.close(); return row
    page.wait_for_timeout(700)
    row["load_s"] = round(time.time() - t0, 1)
    try:
        row.update(page.evaluate(PROBE))
        row["roundtrip"] = page.evaluate(ROUNDTRIP)
        row["panX"] = page.evaluate(PAN)
    except Exception as e:
        row["error"] = "probe: " + str(e)[:160]
    if links and row.get("moneyLinks") is not None:
        row["deadLinks"] = check_links(page, [l["href"] for l in row["moneyLinks"]] + row.get("allLinks", [])[:40])
    if shots and dev == "iphone":
        shots.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[:90] + ".png"
        try:
            page.screenshot(path=str(shots / name))
            row["shot"] = str(shots / name)
        except Exception:
            pass
    page.close()
    row["errors"] = [e for e in errors if "interactive-widget" not in e][:5]
    row["findings"] = judge(row)
    return row


def judge(r: dict) -> list[tuple[str, str]]:
    f: list[tuple[str, str]] = []
    if r.get("status") and r["status"] >= 400:
        f.append(("FAIL", f"HTTP {r['status']}"))
    if r.get("error"):
        f.append(("FAIL", r["error"]))
    if r.get("status") == 200 and r.get("textLen") is not None and r["textLen"] < 40:
        f.append(("FAIL", f"page renders blank on a phone: {r['textLen']} characters of visible text after load"))
    for z in r.get("zoomTrap", [])[:4]:
        f.append(("FAIL", f"iOS zoom trap: {z['el']} at {z['fs']}px (needs 16px on touch)"))
    if r.get("docWider") or r.get("leaks"):
        pan = r.get("panX")
        how = f" (page pans {pan}px sideways)" if pan else " (element leaks, but the page did not pan in this engine)"
        f.append(("FAIL" if pan else "WARN", "sideways overflow" + how + ": " + (", ".join(r.get("leaks") or ["document wider than viewport"]))))
    for w in r.get("wrongKeyboard", [])[:3]:
        f.append(("WARN", f"wrong phone keyboard: {w['kind']} field '{w['hint']}' ({w['el']}) is type={w['type']}, needs type={w['kind']}"))
    for w in r.get("autofillOff", [])[:3]:
        f.append(("WARN", f"autofill disabled: {w['kind']} field '{w['hint']}' ({w['el']}) has autocomplete={w['autocomplete']}"))
    for u in r.get("brokenImgs", [])[:3]:
        f.append(("WARN", f"broken image: {u}"))
    for l in r.get("deadLinks", []):
        if l["verdict"] == "dead":
            f.append(("FAIL", f"dead link: {l['href']} answers {l['codes'][-1]}"))
    if r.get("unreachable"):
        f.append(("FAIL", f"document locked (overflow hidden) with {r['docH']}px of content and no inner scroller"))
    # A cross-origin frame error is a third-party widget (Cloudflare Turnstile, a booking iframe), not the site's own JS.
    own = [e for e in r.get("errors", []) if e.startswith("pageerror") and not re.search(r"cross-origin|accessing a frame|challenges\.cloudflare|Script error", e)]
    if own:
        f.append(("FAIL", own[0]))
    meta = r.get("meta") or ""
    if not meta or "width=device-width" not in meta:
        f.append(("WARN", f"viewport meta: {meta or 'missing'}"))
    if "maximum-scale" in meta or "user-scalable=no" in meta:
        f.append(("WARN", "viewport meta caps zoom (Android honours it; pinch-zoom dies)"))
    for l in r.get("layers", []):
        if l["cover"] >= 40:
            f.append(("WARN", f"{l['pos']} layer {l['el']} covers {l['cover']}% of the screen"))
    rt = r.get("roundtrip") or {}
    if r.get("headTop") is not None and rt.get("headTop") is not None and rt["headTop"] < -2 and not r.get("docLocked"):
        f.append(("WARN", f"header at y={rt['headTop']} after scrolling down and back up"))
    if r.get("small", 0):
        f.append(("WARN", f"{r['small']} of {r['targets']} tap targets under 24px: {', '.join(r['smallList'])}"))
    if r.get("tiny", 0):
        f.append(("WARN", f"{r['tiny']} text elements under 12px: {', '.join(r['tinyList'])}"))
    if r.get("errors") and not own:
        f.append(("INFO", r["errors"][0]))
    f.append(("INFO", ("locked shell, scrollers: " + ", ".join(s["el"] for s in r["scrollers"])) if r.get("docLocked") else f"document scrolls, {r.get('docH')}px tall"))
    return f


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--vercel", action="store_true", help="audit every production alias on the Vercel team")
    ap.add_argument("--crawl", type=int, default=0, help="also audit up to N same-origin pages per site")
    ap.add_argument("--devices", default="iphone,android")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--shots", type=Path)
    ap.add_argument("--links", action="store_true", help="HTTP-check the money-path links and up to 40 others on each page")
    ap.add_argument("--hop", action="store_true", help="also audit the first same-origin order/book/shop/menu page one click deep")
    a = ap.parse_args()
    sites = list(a.urls)
    if a.vercel:
        sites += vercel_sites()
    if not sites:
        ap.error("give URLs or --vercel")
    rows: list[dict] = []
    with sync_playwright() as p:
        browsers = {}
        for dev in a.devices.split(","):
            engine, profile = DEVICES[dev]
            browsers[dev] = (getattr(p, engine).launch(), p.devices[profile])
        for site in sites:
            urls = [site]
            if a.crawl:
                b, prof = browsers[next(iter(browsers))]
                ctx = b.new_context(**prof); pg = ctx.new_page()
                try:
                    pg.goto(site, wait_until="load", timeout=30000); urls += crawl(pg, site, a.crawl)
                except Exception:
                    pass
                ctx.close()
            hopped = False
            while urls:
                url = urls.pop(0)
                for i, (dev, (b, prof)) in enumerate(browsers.items()):
                    ctx = b.new_context(**prof)
                    rows.append(audit_page(ctx, url, a.shots, dev, links=a.links and i == 0))
                    ctx.close()
                    rows[-1]["site"] = site
                    if a.hop and not hopped and i == 0:
                        nxt = money_hop(url, rows[-1])
                        if nxt:
                            urls.append(nxt); hopped = True; rows[-1]["hop"] = nxt
                    r = rows[-1]
                    if a.json:  # write as we go: a site that hangs must not take the finished rows with it
                        a.json.write_text(json.dumps(rows, indent=1))
                    worst = next((s for s in ("FAIL", "WARN") if any(x[0] == s for x in r["findings"])), "ok")
                    print(f"{worst:4} {dev:7} {url}", flush=True)
        for b, _ in browsers.values():
            b.close()
    if a.json:
        a.json.write_text(json.dumps(rows, indent=1))
    print("\n== findings (FAIL and WARN) ==")
    fails = 0
    for r in rows:
        items = [x for x in r["findings"] if x[0] != "INFO"]
        if not items:
            continue
        print(f"\n{r['url']}  [{r['device']}]")
        for sev, msg in items:
            print(f"  {sev}  {msg}")
            fails += sev == "FAIL"
    print(f"\n{len(rows)} page-device rows, {fails} FAIL findings")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
