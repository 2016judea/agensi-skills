#!/usr/bin/env python3
"""Count what a reddit_pull.py corpus says. Every number in a report comes from here.

The model reads the corpus and proposes themes, tools or phrases; this script does
the counting, so no figure in the output is an estimate. Every quote it prints is a
short verbatim span with the permalink it came from.

Input: one or more JSON files written by reddit_pull.py, in any of its three shapes
(a list of posts with optional top_comments, a list of bulk comments, or one
--thread object). Mixed files are fine; documents are de-duplicated by permalink.

Subcommands (all print Markdown; add --json for machine output):
  summary   corpus size: documents, threads, authors, subreddits, date range
  phrases   recurring 2-4 word phrases, ranked by distinct authors
  themes    count a themes file (name -> regex list): threads, authors, dates, quotes
  asks      "is there a tool / looking for / what do you use" posts about a topic, by month
  tools     tool/brand x mentions, praise vs complaint sentences, switches from/to
  digest    one thread (or a window of posts) as ranked answers, pushback, numeric claims

No network. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict

BOTS = {"AutoModerator", "[deleted]", None, ""}
DEAD = {"[deleted]", "[removed]", ""}

STOP = set("""a about above after again against all am an and any are aren't as at be because been
before being below between both but by can can't cannot could couldn't did didn't do does doesn't
doing don't down during each few for from further had hadn't has hasn't have haven't having he he'd
he'll he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in into is
isn't it it's its itself let's me more most mustn't my myself no nor not of off on once only or other
ought our ours ourselves out over own same shan't she she'd she'll she's should shouldn't so some such
than that that's the their theirs them themselves then there there's these they they'd they'll
they're they've this those through to too under until up very was wasn't we we'd we'll we're we've
were weren't what what's when when's where where's which while who who's whom why why's with won't
would wouldn't you you'd you'll you're you've your yours yourself yourselves just also get got like
really one even would much lot lots thing things going go know think want make made way still well
back now im ive dont didnt doesnt cant thats youre theyre it's isnt wasnt 's s t re ve ll d m
will need use used using us any anyone someone something anything every everything etc yes yeah ok
okay thanks thank please hi hey""".split())

PRESETS = {
    # Words people use when something hurts. A sentence must contain one to count.
    "pain": r"frustrat|\bhate\b|nightmare|struggl|annoy|pain in|headache|waste of time|"
            r"biggest (problem|challenge|issue)|hardest part|worst part|(issue|problem|trouble) with|"
            r"can't stand|tired of|sick of|drives me (crazy|nuts)|takes forever|"
            r"\bkeeps? (getting|happening)\b|struggling|overwhelm|stress(ed|ful)|burn(ed|t)? out|"
            r"losing (money|customers|time)|\bugh\b|why is it so|so hard to|impossible to",
    # Asking for something to exist.
    "ask": r"is there (a|an|any) |are there any |does (anyone|anybody) know (of )?(a|an|any)|"
           r"looking for (a|an|some)? ?(tool|app|software|service|platform|program|solution|system|way)|"
           r"what do (you|y'all|you guys|people) use|what (tool|app|software|program|system)s? do you|"
           r"(any|recommend(ation)?s?) (good |decent )?(tool|app|software|service|platform)s? for|"
           r"\balternative(s)? (to|for)\b|wish (there was|there were|i had) |\bneed a way to\b|"
           r"how do (you|y'all) (handle|manage|track|deal with)|anyone (use|using|tried)",
    # Wanting.
    "desire": r"\bi wish\b|\bif only\b|i just want|\bneed a way\b|would pay for|would love (a|an|to (have|get|find|see (a|an|something)))\b|"
              r"is there a way to|why can't (i|we|it)|should be able to",
    "praise": r"(?<!would )(?<!'d )\blove(s|d)?\b(?! to (hear|know|see))(?! of god)|\bgreat\b|amazing|awesome|\bsolid\b|recommend|\bbest\b|excellent|"
              r"\beasy\b|game ?changer|life ?saver|happy with|works (well|great)|worth (it|every)|"
              r"reliable|fantastic|helpful|intuitive|no complaints|can't beat",
    "complaint": r"\bhate\b|terrible|awful|\bworst\b|garbage|nightmare|\bsucks?\b|buggy|"
                 r"expensive|overpriced|\bslow\b|clunky|frustrat|annoying|broken|useless|"
                 r"disappoint|\bscam\b|crash|price (increase|hike)|raised (their |the )?prices?|"
                 r"nickel.and.dim|\bavoid\b|regret|headache|customer (service|support) (is|was) "
                 r"(terrible|awful|bad|non.?existent)|steer clear|\bmeh\b|outdated",
}

HURT = re.compile(PRESETS["pain"] + "|" + PRESETS["complaint"], re.I)

# Vendor posts and market research dressed as questions. Owner subs are full of them
# (MEASURED 2026-11-03: the top "pain" phrase in a year of r/restaurateur was
# "restaurant owners", from posts like "I built a tool that tells restaurant owners...").
# Counting them as customer pain counts the sellers, not the buyers.
PITCH = re.compile(
    r"\b(i|we) (just )?(built|made|created|launched|developed)\b|\b(i'm|i am|we're|we are) "
    r"(building|developing|launching|creating|working on (a|an|my|our) (app|tool|platform|product|startup))|"
    r"free (early )?access|\bwaitlist\b|beta tester|\bwould you (use|pay|try|be interested)\b|"
    r"\bdm me\b|\bour (app|platform|tool|software|product|startup|agency)\b|\bsign up\b|"
    r"\b(quick|short) (survey|question for)\b|market research|\bfounder\b|"
    r"\bhow much would you pay\b|\bpain points?\b|looking for (beta|testers|feedback on (my|our|a))|"
    r"\b(i'm|i am) (trying to understand|researching|curious how) (how|where|what|whether)\b|"
    r"\bwould love to hear (about|how|from) (the|your|you|other)\b|"
    r"\bresearching how\b|\bsmall startup\b",
    re.I)
DROPPED = {"posts": 0, "comments": 0, "unreadable": 0}

SWITCH = re.compile(
    r"\b(switch(?:ed|ing)?|mov(?:ed|ing)|migrat(?:ed|ing)|went|chang(?:ed|ing)|transition(?:ed|ing)?|"
    r"jump(?:ed|ing)? ship|left|ditch(?:ed|ing)?|dump(?:ed|ing)?|replac(?:ed|ing)|drop(?:ped|ping)|"
    r"cancel(?:l?ed|l?ing)?|stopp?(?:ed|ing) using|got rid of|gave up on)\b", re.I)

PUSHBACK = re.compile(
    r"^(no[,.! ]|nope|nah|disagree|i disagree|hard disagree|not true|that's not|thats not|"
    r"actually[, ]|wrong|incorrect|i'd push back|respectfully|not really|eh[,. ]|"
    r"this is (bad|terrible|wrong) advice|bad advice|don't do this|do not do this)", re.I)

DECISION = re.compile(
    r"\b(update|edit)\s*[:\-]|\bended up\b|\bwe went with\b|\bi went with\b|\bdecided\b|"
    r"\bwent ahead\b|\bfinal(ly)? (chose|picked|went)\b|\bin the end\b|\bturns out\b", re.I)

NUMERIC = re.compile(r"\$\s?\d|\d\s?%|\b\d[\d,.]*\s?(k|m|hrs?|hours?|days?|weeks?|months?|"
                     r"years?|per|/mo|/hr|/month|/year|x)\b", re.I)


# ---------------------------------------------------------------- loading

def _doc(thread, kind, author, created, text, permalink, sub, score, title="", extra=None):
    d = {"thread": thread, "kind": kind, "author": author, "created": created or "",
         "text": text or "", "permalink": permalink, "sub": sub, "score": score or 0,
         "title": title}
    if extra:
        d.update(extra)
    return d


def load(paths: list[str]) -> list[dict]:
    docs, seen = [], set()

    def add(d):
        if d["permalink"] in seen:
            return
        if d["author"] in ("AutoModerator",) or d["text"].strip() in DEAD:
            DROPPED["unreadable"] += 1
            seen.add(d["permalink"])
            return
        seen.add(d["permalink"])
        docs.append(d)

    for p in paths:
        data = json.load(open(p))
        rows = [data] if isinstance(data, dict) else data
        for r in rows:
            if "body" in r and "title" not in r:          # bulk comment
                tid = (r.get("link_id") or "").removeprefix("t3_")
                add(_doc(tid, "comment", r.get("author"), r.get("created"), r.get("body"),
                         r.get("permalink") or f"https://reddit.com/comments/{tid}/_/{r.get('id')}",
                         r.get("subreddit"), r.get("score")))
                continue
            tid = r.get("id") or r.get("permalink", "").rstrip("/").rsplit("/", 1)[-1]
            title = r.get("title") or ""
            body = r.get("selftext") or ""
            add(_doc(tid, "post", r.get("author"), r.get("created"),
                     (f"{title}{'' if title[-1:] in '.?!' else '.'} {body}"
                      if body not in DEAD else title),
                     r.get("permalink"), r.get("subreddit"), r.get("score"), title,
                     {"num_comments": r.get("num_comments")}))
            for c in (r.get("top_comments") or []) + (r.get("comments") or []):
                add(_doc(tid, "comment", c.get("author"), c.get("created"), c.get("body"),
                         c.get("permalink") or f"{r.get('permalink')}/_/{c.get('id')}",
                         r.get("subreddit"), c.get("score"), title,
                         {"id": c.get("id"), "parent_id": c.get("parent_id"),
                          "depth": c.get("depth")}))
    return docs


def clean(text: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text or "")   # markdown links -> text
    text = re.sub(r"https?://\S+", "", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"\\([~*_#>\[\]()-])", r"\1", text)                # markdown escapes
    return re.sub(r"[*_`#>]{1,3}", "", text).replace("&amp;", "&").replace("|", "/")


def sentences(text: str) -> list[str]:
    text = clean(text)
    parts = re.split(r"(?<=[.!?])\s+|\n+|(?<=\.)(?=[A-Z])", text)
    return [s.strip(" *>#-") for s in parts if len(s.strip()) > 3]


def snippet(sentence: str, m: re.Match | None = None, words: int = 25) -> str:
    """A short verbatim span: the whole sentence if short, else a window on the match."""
    if m is not None:          # keep the match position valid after cleaning
        m = re.search(re.escape(m.group(0)), clean(sentence), re.I)
    sentence = clean(sentence)
    w = sentence.split()
    if len(w) <= words:
        return sentence
    if m is None:
        return " ".join(w[:words]) + " …"
    at = len(sentence[:m.start()].split())
    lo = max(0, min(at - words // 3, len(w) - words))
    return ("… " if lo else "") + " ".join(w[lo:lo + words]) + (" …" if lo + words < len(w) else "")


def authors(ds) -> int:
    return len({d["author"] for d in ds if d["author"] not in BOTS})


def span(ds) -> tuple[str, str, int]:
    dates = sorted(d["created"] for d in ds if d["created"])
    if not dates:
        return "", "", 0
    return dates[0], dates[-1], len({x[:7] for x in dates})


def drop_pitches(docs: list[dict]) -> list[dict]:
    """Remove pitch posts, and the pitcher's own comments in those threads."""
    bad = {(d["thread"], d["author"]) for d in docs
           if d["kind"] == "post" and PITCH.search(d["text"])}
    keep = []
    for d in docs:
        if (d["thread"], d["author"]) in bad:
            DROPPED["posts" if d["kind"] == "post" else "comments"] += 1
        else:
            keep.append(d)
    return keep


def corpus_line(docs) -> str:
    a, b, _ = span(docs)
    subs = sorted({d["sub"] for d in docs if d["sub"]})
    posts = sum(d["kind"] == "post" for d in docs)
    return (f"Corpus: {len(docs):,} documents ({posts:,} posts, {len(docs) - posts:,} comments) "
            f"in {len({d['thread'] for d in docs}):,} threads by {authors(docs):,} authors, "
            f"r/{', r/'.join(subs) if subs else '?'}, {a} to {b}."
            + (f" Dropped as vendor pitches / market research: {DROPPED['posts']:,} posts "
               f"(+{DROPPED['comments']:,} of the pitcher's own comments); --keep-pitches keeps them."
               if DROPPED["posts"] else ""))


def compile_any(pats: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in pats), re.I)


def near_filter(args) -> re.Pattern | None:
    pats = list(args.near or [])
    for name in args.near_preset or []:
        pats.append(PRESETS[name])
    return compile_any(pats) if pats else None


# ---------------------------------------------------------------- summary

def cmd_summary(args, docs):
    out = {"documents": len(docs), "threads": len({d["thread"] for d in docs}),
           "authors": authors(docs), "first": span(docs)[0], "last": span(docs)[1],
           "by_sub": Counter(d["sub"] for d in docs)}
    if args.json:
        return print(json.dumps(out, indent=1))
    print(corpus_line(docs))
    for s, n in out["by_sub"].most_common():
        print(f"- r/{s}: {n:,} documents")


# ---------------------------------------------------------------- phrases

def grams(tokens, n):
    for i in range(len(tokens) - n + 1):
        g = tokens[i:i + n]
        if g[0] in STOP or g[-1] in STOP or all(t in STOP for t in g):
            continue
        if any(t.isdigit() for t in (g[0], g[-1])):
            continue
        yield " ".join(g)


def cmd_phrases(args, docs):
    near = near_filter(args)
    about = compile_any(args.about) if args.about else None
    excl = {e.lower() for e in args.exclude or []}
    hits: dict[str, list] = defaultdict(list)
    for d in docs:
        for s in sentences(d["text"]):
            if near and not near.search(s):
                continue
            if about and not about.search(s):
                continue
            toks = re.findall(r"[a-z0-9][a-z0-9'$%]*", s.lower())
            got = set()
            for n in range(args.min_n, args.max_n + 1):
                got.update(grams(toks, n))
            for g in got:
                if g not in excl and not any(e in g for e in excl):
                    hits[g].append((d, s))
    rows = []
    for g, occ in hits.items():
        ds = {o[0]["permalink"]: o[0] for o in occ}.values()
        th = len({d["thread"] for d in ds})
        if th < args.min_threads:
            continue
        rows.append((g, th, authors(ds), occ))
    # drop a phrase when a longer phrase containing it has the same thread count
    rows.sort(key=lambda r: (-r[2], -r[1], -len(r[0])))
    keep = []
    for r in rows:
        if any(r[0] in k[0] and r[0] != k[0] and k[1] >= r[1] for k in keep):
            continue
        keep.append(r)
    keep = keep[:args.top]
    if args.json:
        return print(json.dumps([{"phrase": g, "threads": t, "authors": a,
                                  "quotes": quotes(occ, args.quotes, g)} for g, t, a, occ in keep],
                                indent=1))
    print(corpus_line(docs))
    filt = []
    if near:
        filt.append("sentences matching " + ", ".join((args.near_preset or []) + (args.near or [])))
    if about:
        filt.append("sentences mentioning " + ", ".join(args.about))
    if filt:
        print("Counted within: " + "; ".join(filt) + ".")
    print()
    print("| # | phrase | threads | authors | example |")
    print("|---|---|---|---|---|")
    for i, (g, t, a, occ) in enumerate(keep, 1):
        q = quotes(occ, 1, g)
        ex = f"\"{q[0]['quote']}\" ([link]({q[0]['permalink']}))" if q else ""
        print(f"| {i} | {g} | {t} | {a} | {ex} |")
    if args.quotes > 1:
        print()
        for g, t, a, occ in keep[:args.quote_rows]:
            print(f"**{g}** ({t} threads, {a} authors)")
            for q in quotes(occ, args.quotes, g):
                print(f"- \"{q['quote']}\" ({q['created']}, {q['permalink']})")
            print()


def quotes(occ, k, pattern=None, prefer=None):
    """Up to k quotes from distinct threads and documents: sentences matching `prefer`
    first, then short ones (a quote should stand alone), then highest score."""
    rx = re.compile(re.escape(pattern), re.I) if isinstance(pattern, str) else pattern
    out, used = [], set()
    key = lambda o: (not (prefer and prefer.search(o[1])), len(o[1].split()) > 30,
                     -(o[0]["score"] or 0))
    for d, s in sorted(occ, key=key):
        if d["thread"] in used:
            continue
        used.add(d["thread"])
        m = rx.search(s) if rx else None
        out.append({"quote": snippet(s, m).replace("|", "/"), "permalink": d["permalink"],
                    "created": d["created"], "score": d["score"]})
        if len(out) >= k:
            break
    return out


# ---------------------------------------------------------------- themes

def cmd_themes(args, docs):
    spec = json.load(open(args.themes))
    about = compile_any(args.about) if args.about else None
    near = near_filter(args)
    rows, matched_docs = [], set()
    pool = []
    for d in docs:
        for s in sentences(d["text"]):
            if about and not about.search(s):
                continue
            if near and not near.search(s):
                continue
            pool.append((d, s))
    pool_docs = {d["permalink"] for d, _ in pool}
    for name, pats in spec.items():
        rx = compile_any(pats if isinstance(pats, list) else [pats])
        occ = [(d, s) for d, s in pool if rx.search(s)]
        ds = list({d["permalink"]: d for d, _ in occ}.values())
        matched_docs.update(d["permalink"] for d in ds)
        a, b, months = span(ds)
        sore = {d["thread"] for d, s in occ if HURT.search(s)}
        rows.append({"theme": name, "threads": len({d["thread"] for d in ds}),
                     "complaint_threads": len(sore),
                     "authors": authors(ds), "mentions": len(ds), "first": a, "last": b,
                     "months": months, "quotes": quotes(occ, args.quotes, rx, HURT)})
    rows.sort(key=lambda r: (-r["threads"], -r["authors"]))
    if args.show_unmatched:
        rxs = [compile_any(p if isinstance(p, list) else [p]) for p in spec.values()]
        miss = [(d, s) for d, s in pool if not any(r.search(s) for r in rxs)]
        miss.sort(key=lambda o: -(o[0]["score"] or 0))
        print(f"{len(miss):,} in-scope sentences matched no theme. Highest-scored:")
        for d, s in miss[:args.show_unmatched]:
            print(f"- \"{snippet(s)}\" ({d['permalink']})")
        return
    if args.json:
        return print(json.dumps(rows, indent=1))
    print(corpus_line(docs))
    scope = []
    if about:
        scope.append("sentences mentioning " + ", ".join(args.about))
    if near:
        scope.append("sentences matching " + ", ".join((args.near_preset or []) + (args.near or [])))
    print(f"In scope: {len(pool_docs):,} documents"
          + (f" ({'; '.join(scope)})" if scope else "") + f". Matched at least one theme: "
          f"{len(matched_docs):,}. Matched none: {len(pool_docs - matched_docs):,}.")
    print()
    print("| # | theme | threads | in a complaint sentence | authors | mentions | first | last | months active |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        print(f"| {i} | {r['theme']} | {r['threads']} | {r['complaint_threads']} | {r['authors']} | {r['mentions']} | "
              f"{r['first']} | {r['last']} | {r['months']} |")
    print()
    for r in rows:
        if not r["quotes"]:
            continue
        print(f"**{r['theme']}**")
        for q in r["quotes"]:
            print(f"- \"{q['quote']}\" ({q['created']}, {q['permalink']})")
        print()


# ---------------------------------------------------------------- asks

def cmd_asks(args, docs):
    topic = compile_any(args.topic)
    ask = compile_any([PRESETS["ask"]] + (args.ask or []))
    posts = [d for d in docs if d["kind"] == "post"]
    hits = []
    topic_posts = 0
    for d in posts:
        ss = [d["title"]] + sentences(d["text"])
        if not any(topic.search(s) for s in ss):
            continue
        topic_posts += 1
        for s in ss:
            if topic.search(s) and ask.search(s):
                hits.append((d, s))
                break
        else:
            # title asks + topic anywhere in the post also counts
            if ask.search(d["title"]):
                hits.append((d, d["title"]))
    stats = None
    for f in args.stats or []:
        one = json.load(open(f))
        if stats is None:
            stats = {"after": one["after"], "before": one["before"], "scanned": {}}
        stats["after"] = min(stats["after"], one["after"])
        stats["before"] = max(stats["before"], one["before"])
        stats["scanned"].update(one["scanned"])
    scanned = Counter()
    if stats:
        for sub, months in stats["scanned"].items():
            for m, n in months.items():
                scanned[m] += n
    by_month = Counter(d["created"][:7] for d, _ in hits)
    months = sorted(set(scanned) | set(by_month)) if stats else sorted(by_month)
    out = {"asks": len(hits), "ask_authors": authors([d for d, _ in hits]),
           "topic_posts": topic_posts, "posts_scanned": sum(scanned.values()) if stats else None,
           "by_month": [{"month": m, "scanned": scanned.get(m), "asks": by_month.get(m, 0)}
                        for m in months],
           "threads": [{"created": d["created"], "sub": d["sub"], "title": d["title"],
                        "score": d["score"], "comments": d.get("num_comments"),
                        "permalink": d["permalink"], "ask": snippet(s, ask.search(s))}
                       for d, s in sorted(hits, key=lambda h: h[0]["created"], reverse=True)]}
    if args.json:
        return print(json.dumps(out, indent=1))
    window = f"{stats['after']} to {stats['before']}" if stats else f"{span(docs)[0]} to {span(docs)[1]}"
    subs = ", ".join(f"r/{s}" for s in (stats["scanned"] if stats else {d['sub'] for d in docs}))
    denom = f"{out['posts_scanned']:,} posts scanned" if stats else "posts in the pull (no --stats denominator)"
    print(f"Window: {window}. Subreddits: {subs}. {denom}.")
    print(f"Posts mentioning the topic ({', '.join(args.topic)}): {topic_posts:,}.")
    print(f"Posts asking for it: **{len(hits)}** by {out['ask_authors']} distinct authors.")
    if not hits:
        print("\nNULL RESULT: no post in this window both names the topic and asks for a tool, "
              "app, service or way to do it. This is the archive's coverage of these subreddits "
              "only; it is not proof nobody wants it.")
    print()
    print("| month | posts scanned | asks | asks per 1,000 posts |")
    print("|---|---|---|---|")
    for r in out["by_month"]:
        rate = (f"{1000 * r['asks'] / r['scanned']:.1f}" if r["scanned"] else "")
        print(f"| {r['month']} | {r['scanned'] if r['scanned'] is not None else ''} | "
              f"{r['asks']} | {rate} |")
    if hits:
        print()
        print("| date | sub | ask (verbatim) | score | comments | link |")
        print("|---|---|---|---|---|---|")
        for t in out["threads"][:args.list]:
            print(f"| {t['created']} | r/{t['sub']} | \"{t['ask'].replace('|', '/')}\" | "
                  f"{t['score']} | {t['comments']} | {t['permalink']} |")
        if len(out["threads"]) > args.list:
            print(f"\n({len(out['threads']) - args.list} more; raise --list to see them)")


# ---------------------------------------------------------------- tools

def tool_patterns(spec: dict) -> dict[str, re.Pattern]:
    return {name: re.compile(r"(?<![\w.])(?:" + "|".join(
        a if a.startswith("(?") else re.escape(a) for a in aliases) + r")(?![\w])", re.I)
        for name, aliases in spec.items()}


def cmd_discover(args, docs):
    """Candidate product/brand names: capitalised or CamelCase tokens used mid-sentence."""
    seen: dict[str, set] = defaultdict(set)
    common = STOP | set("""i the a reddit edit update tldr tl dr op lol imo imho usa us uk ca
    monday tuesday wednesday thursday friday saturday sunday january february march april may june
    july august september october november december google""".split())
    for d in docs:
        for s in sentences(d["text"]):
            toks = re.findall(r"[A-Za-z][\w.+&-]*[\w+]|[A-Za-z]", s)
            for t in toks[1:]:
                if t.lower() in common or len(t) < 2:
                    continue
                camel = re.search(r"[a-z][A-Z]", t)
                if (t[0].isupper() and not t.isupper()) or camel or (t.isupper() and 2 < len(t) <= 6):
                    seen[t].add(d["author"])
    rows = sorted(((t, len(a - BOTS)) for t, a in seen.items()), key=lambda r: -r[1])
    rows = [r for r in rows if r[1] >= args.min_authors][:args.top]
    print("Candidate names (mid-sentence capitalised tokens) by distinct authors. Curate into a")
    print("tools file: merge aliases, drop ordinary words. These are NOT counts to report.\n")
    print(", ".join(f"{t} ({n})" for t, n in rows))


NEG = re.compile(r"\b(not|no|never|nothing|hardly|isn't|wasn't|aren't|don't|didn't|doesn't|"
                 r"won't|can't|couldn't|without)\b[\w' ]{0,25}$", re.I)


def positive(rx, s):
    """A praise word that isn't negated a few words before ("didn't find anything helpful")."""
    return any(not NEG.search(s[:m.start()]) for m in rx.finditer(s))


def cmd_tools(args, docs):
    if args.discover:
        return cmd_discover(args, docs)
    spec = json.load(open(args.tools))
    pats = tool_patterns(spec)
    praise, complaint = re.compile(PRESETS["praise"], re.I), re.compile(PRESETS["complaint"], re.I)
    stats = {n: {"docs": {}, "praise": [], "complaint": [], "to": [], "away": []} for n in spec}
    edges: dict[tuple, list] = defaultdict(list)
    for d in docs:
        for s in sentences(d["text"]):
            found = {n: p.search(s) for n, p in pats.items()}
            found = {n: m for n, m in found.items() if m}
            if not found:
                continue
            for n, m in found.items():
                st = stats[n]
                st["docs"][d["permalink"]] = d
                # judge only the words near the mention: a long list sentence
                # ("we work on Lennox, York, Carrier ... best part is") says nothing
                # about each brand in it
                near = s[max(0, m.start() - 45):m.end() + 45]
                good = positive(praise, near)
                if good and not complaint.search(near):
                    st["praise"].append((d, s))
                elif complaint.search(near) and not good:
                    st["complaint"].append((d, s))
            sw = SWITCH.search(s)
            if not sw:
                continue
            src, dst = set(), set()
            for n, m in found.items():
                before = s[:m.start()].lower()
                tail = before[-24:]
                if re.search(r"\b(from|off( of)?|left|ditch\w*|dump\w*|cancel\w*|replac\w*|"
                             r"drop\w*|using|rid of|up on|away from)\s+(\w+\s+)?$", tail):
                    src.add(n)
                elif re.search(r"\b(to|for|with|onto|into|over to|went)\s+(\w+\s+)?$", tail):
                    dst.add(n)
            if src or dst:
                for n in src:
                    stats[n]["away"].append((d, s))
                for n in dst:
                    stats[n]["to"].append((d, s))
                for a in src or {"?"}:
                    for b in dst or {"?"}:
                        if a != b:
                            edges[(a, b)].append((d, s))
    rows = []
    for n, st in stats.items():
        ds = list(st["docs"].values())
        uniq = lambda occ: len({x[0]["permalink"] for x in occ})
        rows.append({"tool": n, "threads": len({d["thread"] for d in ds}), "authors": authors(ds),
                     "mentions": len(ds), "praise": uniq(st["praise"]),
                     "complaint": uniq(st["complaint"]), "switched_to": uniq(st["to"]),
                     "switched_away": uniq(st["away"]),
                     "example": (sorted(ds, key=lambda d: -d["score"])[0]["permalink"] if ds else ""),
                     "praise_quotes": quotes(st["praise"], args.quotes, pats[n]),
                     "complaint_quotes": quotes(st["complaint"], args.quotes, pats[n])})
    rows.sort(key=lambda r: (-r["authors"], -r["threads"]))
    erows = sorted(({"from": a, "to": b, "count": len({x[0]['permalink'] for x in occ}),
                     "quotes": quotes(occ, args.quotes, None)} for (a, b), occ in edges.items()),
                   key=lambda e: -e["count"])
    if args.json:
        return print(json.dumps({"tools": rows, "switches": erows}, indent=1))
    print(corpus_line(docs))
    print("Praise / complaint = documents where a praise (or complaint) word sits within ~45 characters")
    print("of the tool name, not both. Switches = a switch verb in the same sentence, direction read from")
    print("'from X' / 'to X'. '?' = the other side was not a tool in the list.\n")
    print("| # | tool | threads | authors | praise | complaint | switched to | switched away | top thread |")
    print("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        print(f"| {i} | {r['tool']} | {r['threads']} | {r['authors']} | {r['praise']} | "
              f"{r['complaint']} | {r['switched_to']} | {r['switched_away']} | {r['example']} |")
    if erows:
        print("\n| from | to | documents | example |")
        print("|---|---|---|---|")
        for e in erows[:args.top]:
            q = e["quotes"][0]
            print(f"| {e['from']} | {e['to']} | {e['count']} | \"{q['quote']}\" ({q['permalink']}) |")
    if args.quotes:
        print()
        for r in rows[:args.quote_rows]:
            if not (r["praise_quotes"] or r["complaint_quotes"]):
                continue
            print(f"**{r['tool']}**")
            for q in r["praise_quotes"]:
                print(f"- praise: \"{q['quote']}\" ({q['permalink']})")
            for q in r["complaint_quotes"]:
                print(f"- complaint: \"{q['quote']}\" ({q['permalink']})")
            print()


# ---------------------------------------------------------------- digest

def cmd_digest(args, docs):
    posts = [d for d in docs if d["kind"] == "post"]
    comments = [d for d in docs if d["kind"] == "comment"]
    if len(posts) == 1 and comments and comments[0].get("parent_id") is not None:
        return digest_thread(args, posts[0], comments)
    return digest_window(args, posts, comments)


def digest_thread(args, post, comments):
    kids = defaultdict(list)
    for c in comments:
        kids[(c.get("parent_id") or "").split("_")[-1]].append(c)

    def subtree(c):
        return 1 + sum(subtree(k) for k in kids.get(c["id"], []))

    top = [c for c in comments if (c.get("parent_id") or "").startswith("t3_")]
    top.sort(key=lambda c: -(c["score"] or 0))
    op = post["author"]
    print(f"# {post['title']}")
    print(f"r/{post['sub']}, {post['created']}, score {post['score']}, {post['permalink']}")
    print(f"Readable comments: {len(comments)} of {len(comments) + DROPPED['unreadable']} archived "
          f"(rest removed, deleted or bot; post reports {post.get('num_comments')}); "
          f"distinct commenters: {authors(comments)}; top-level answers: {len(top)}.\n")
    print(f"**Question (verbatim, opening):** \"{snippet(post['text'], None, 60)}\"\n")
    print("## Top answers by score\n")
    print("| # | score | replies under it | answer (opening, verbatim) | link |")
    print("|---|---|---|---|---|")
    for i, c in enumerate(top[:args.top], 1):
        print(f"| {i} | {c['score']} | {subtree(c) - 1} | \"{snippet(c['text'], None, 30).replace('|', '/')}\" "
              f"| {c['permalink']} |")
    byid = {c["id"]: c for c in comments}
    push = [c for c in comments if PUSHBACK.search(c["text"])
            and (c.get("parent_id") or "").startswith("t1_")]
    push.sort(key=lambda c: -(c["score"] or 0))
    print(f"\n## Pushback: {len(push)} replies open by disagreeing\n")
    for c in push[:args.top]:
        par = byid.get(c["parent_id"].split("_")[-1])
        pq = snippet(par["text"], None, 18) if par else "?"
        print(f"- \"{snippet(c['text'], None, 25)}\" (score {c['score']}, {c['permalink']}) "
              f"replying to \"{pq}\"")
    opc = [c for c in comments if c["author"] == op and op not in BOTS]
    dec = [(c, s) for c in [post] + opc for s in sentences(c["text"]) if DECISION.search(s)]
    print(f"\n## What the original poster said or decided: {len(opc)} OP comments, "
          f"{len(dec)} decision/update sentences\n")
    for c, s in dec[:args.top]:
        print(f"- \"{snippet(s, DECISION.search(s))}\" ({c['permalink']})")
    num = [(c, s) for c in comments for s in sentences(c["text"]) if NUMERIC.search(s)]
    num.sort(key=lambda x: -(x[0]["score"] or 0))
    print(f"\n## Claims with a number: {len(num)} sentences (top by score)\n")
    for c, s in num[:args.top]:
        print(f"- \"{snippet(s, NUMERIC.search(s))}\" (score {c['score']}, {c['permalink']})")


def digest_window(args, posts, comments):
    docs = posts + comments
    print(corpus_line(docs) + "\n")
    print("## Threads that drew the most discussion\n")
    print("| # | date | score | comments | title | link |")
    print("|---|---|---|---|---|---|")
    ranked = sorted(posts, key=lambda d: -((d.get("num_comments") or 0) + (d["score"] or 0)))
    for i, d in enumerate(ranked[:args.top], 1):
        print(f"| {i} | {d['created']} | {d['score']} | {d.get('num_comments')} | "
              f"{d['title'].replace('|', '/')} | {d['permalink']} |")
    by_thread = defaultdict(list)
    for c in comments:
        by_thread[c["thread"]].append(c)
    print("\n## Highest-scored answer in each of those threads\n")
    for d in ranked[:args.top]:
        cs = sorted(by_thread.get(d["thread"], []), key=lambda c: -(c["score"] or 0))
        if cs:
            print(f"- {d['title'][:80]}: \"{snippet(cs[0]['text'], None, 25)}\" "
                  f"(score {cs[0]['score']}, {cs[0]['permalink']})")
    push = [c for c in comments if PUSHBACK.search(c["text"])]
    print(f"\nComments opening with disagreement: {len(push)} of {len(comments)}.")
    num = [(c, s) for c in docs for s in sentences(c["text"]) if NUMERIC.search(s)]
    num.sort(key=lambda x: -(x[0]["score"] or 0))
    print(f"\n## Claims with a number (top {min(args.top, len(num))} of {len(num)} by score)\n")
    for c, s in num[:args.top]:
        print(f"- \"{snippet(s, NUMERIC.search(s))}\" (score {c['score']}, {c['permalink']})")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("files", nargs="+", help="reddit_pull.py JSON output(s)")
        p.add_argument("--json", action="store_true")
        p.add_argument("--top", type=int, default=25)
        p.add_argument("--quotes", type=int, default=2)
        p.add_argument("--quote-rows", type=int, default=10)
        p.add_argument("--near", nargs="*", help="regex: only count sentences matching one")
        p.add_argument("--near-preset", nargs="*", choices=sorted(PRESETS))
        p.add_argument("--about", nargs="*", help="regex: only count sentences mentioning one")
        p.add_argument("--keep-pitches", action="store_true",
                       help="keep vendor/market-research posts (dropped by default)")
        return p

    common(sub.add_parser("summary"))
    p = common(sub.add_parser("phrases"))
    p.add_argument("--min-n", type=int, default=2)
    p.add_argument("--max-n", type=int, default=4)
    p.add_argument("--min-threads", type=int, default=3)
    p.add_argument("--exclude", nargs="*", help="drop phrases containing these")
    p = common(sub.add_parser("themes"))
    p.add_argument("--themes", required=True, help='JSON: {"theme": ["regex", ...]}')
    p.add_argument("--show-unmatched", type=int, default=0,
                   help="print N in-scope sentences no theme caught (to refine the file)")
    p = common(sub.add_parser("asks"))
    p.add_argument("--topic", nargs="+", required=True, help="regex for the thing asked about")
    p.add_argument("--ask", nargs="*", help="extra ask regexes, added to the built-in set")
    p.add_argument("--stats", nargs="*",
                   help="--stats file(s) from reddit_pull.py (the denominator)")
    p.add_argument("--list", type=int, default=30)
    p = common(sub.add_parser("tools"))
    p.add_argument("--tools", help='JSON: {"Tool": ["alias", ...]}')
    p.add_argument("--discover", action="store_true", help="print candidate names to curate")
    p.add_argument("--min-authors", type=int, default=3)
    common(sub.add_parser("digest"))
    args = ap.parse_args()
    if args.cmd == "tools" and not (args.tools or args.discover):
        ap.error("tools needs --tools FILE or --discover")
    docs = load(args.files)
    if args.cmd != "digest" and not args.keep_pitches:
        docs = drop_pitches(docs)
    if not docs:
        sys.exit("no documents in input")
    {"summary": cmd_summary, "phrases": cmd_phrases, "themes": cmd_themes, "asks": cmd_asks,
     "tools": cmd_tools, "digest": cmd_digest}[args.cmd](args, docs)


if __name__ == "__main__":
    main()
