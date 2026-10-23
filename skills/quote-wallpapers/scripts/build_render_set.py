#!/usr/bin/env python3
"""
Turn a raw quotes JSON into a render-ready set for the wallpaper compositor.
  input : [{"quote","author","book"}, ...]   (e.g. exported from a Notion database or Kindle highlights)
  output: [{"quote","author","book","display","excerpted"}, ...]
- filters slur/explicit quotes out of the wallpaper set (they stay in the DB)
- excerpts long quotes (>~210 chars) down to a punchy 1–2 sentence core
Usage: python3 build_render_set.py quotes.json render_set.json
"""
import os
import json, re, sys

# Words that keep a quote OFF the lock screen (it stays in your source list). One per line in
# blocklist.txt beside this script; add slurs and explicit terms you don't want on a phone.
_BL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blocklist.txt")
_WORDS = [w.strip() for w in open(_BL)] if os.path.exists(_BL) else []
BLOCK = re.compile(r'\b(' + '|'.join(map(re.escape, [w for w in _WORDS if w])) + r')\b', re.I) if _WORDS else re.compile(r'(?!x)x')

KEY = set("love death world time god beauty loss dream dreams soul fear life alone night stars star "
          "sea light dark heart wonder silence men man cannot never forever memory blood snow fire "
          "mountains rain".split())

def excerpt(t, target=330):
    """Keep whole if it fits; else keep the ENDING (the payoff usually lands last),
    cutting at a natural break in the ORIGINAL string so punctuation stays intact."""
    t = t.strip()
    if len(t) <= target: return t, False
    # positions just after a sentence end / em-dash / semicolon / ellipsis + following space
    breaks = [m.end() for m in re.finditer(r'[.!?;—–…]+["”’)\]]?\s+', t)]
    cut = next((b for b in breaks if len(t) - b <= target), None)   # earliest = longest valid tail
    if cut is None:
        frag = t[-target:]
        frag = frag.split(' ', 1)[1] if ' ' in frag else frag
        return "… " + frag.lstrip(" .·—–…\"'").rstrip(), True
    tail = t[cut:].lstrip(" .·—–…").rstrip()   # keep the closing punctuation!
    return "… " + tail, True

def build(quotes):
    out = []
    for q in quotes:
        txt = re.sub(r'<br/?>', ' ', q['quote'])
        txt = re.sub(r'\\([\[\]*_])', r'\1', txt)      # unescape markdown
        txt = txt.replace('*', '')                      # stray bold/italic marks
        txt = re.sub(r'\s*-{2,}\s*[A-Z]*\s*', ' ', txt) # --- separators / leaked markers
        txt = re.sub(r'\s+', ' ', txt).strip()
        if BLOCK.search(txt): continue
        disp, cut = excerpt(txt)
        out.append({"quote": txt, "author": q.get('author'), "book": q.get('book'),
                    "display": disp, "excerpted": cut})
    return out

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    rs = build(data)
    json.dump(rs, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
    print(f"{len(data)} quotes -> {len(rs)} cards ({sum(1 for r in rs if r['excerpted'])} excerpted, "
          f"{len(data)-len(rs)} filtered)")