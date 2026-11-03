#!/usr/bin/env python3
"""What needs re-publishing. Three lists:

  drifted  a listed skill whose original's SKILL.md changed since the baseline
  retired  a listed skill whose original no longer exists (the public copy stays; nothing to sync)
  new      a skill in ~/.claude/skills that the ledger has never decided on (list or skip)

Baseline = tools/drift_baseline.json, sha256 of each original SKILL.md as of the last publish.

Usage: drift.py                    print the lists, exit 1 if drifted or new is non-empty
       drift.py --pending          also add one item to ~/.claude/pending.json (once per day)
       drift.py --mark <skill>...  record the current originals as published (after update_skill)
       drift.py --mark-all         same, for every listed skill (first run only)
"""
import hashlib, json, os, re, sys, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
GLOBAL = os.path.join(HOME, ".claude/skills")
BASE = os.path.join(ROOT, "tools/drift_baseline.json")


def original(name, src):
    """The original SKILL.md for a listed skill, or None if it is gone. The ledger's source column is loose
    (a skill dir, a repo root, a hook file), so try the specific paths first."""
    for p in re.findall(r"~/[^\s\]\)+,`]+", src):
        p = os.path.expanduser(p).rstrip("/")
        stem = os.path.basename(p)
        for c in (p, os.path.join(p, "SKILL.md"), os.path.join(p, "skills", name, "SKILL.md"),
                  os.path.join(p, ".claude/skills", name, "SKILL.md"), os.path.join(p, stem, "SKILL.md")):
            if os.path.isfile(c):
                return c
    return None


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


rows = {}
for l in open(os.path.join(ROOT, "ledger.tsv")):
    r = l.rstrip("\n").split("\t")
    if r and r[0] and r[0] != "name":
        rows.setdefault(r[0], r + [""] * (5 - len(r)))
listed = {n: r[1] for n, r in rows.items() if r[2] == "list" and os.path.isdir(os.path.join(ROOT, "skills", n))}
base = json.load(open(BASE)) if os.path.exists(BASE) else {}

if "--mark" in sys.argv or "--mark-all" in sys.argv:
    names = listed if "--mark-all" in sys.argv else sys.argv[sys.argv.index("--mark") + 1:]
    for n in names:
        o = original(n, listed.get(n, ""))
        if o:
            base[n] = {"original": o.replace(HOME, "~"), "sha256": sha(o)}
    json.dump(base, open(BASE, "w"), indent=1, sort_keys=True)
    print(len(base), "in baseline")
    sys.exit(0)

drifted, retired = [], []
for n, src in sorted(listed.items()):
    o = original(n, src)
    if not o:
        retired.append(n)
    elif n in base and base[n]["sha256"] != sha(o):
        drifted.append((n, o.replace(HOME, "~")))
sources = " ".join(r[1] for r in rows.values())
new = sorted(n for n in os.listdir(GLOBAL)
             if os.path.isfile(os.path.join(GLOBAL, n, "SKILL.md")) and n not in rows and n != "synced"
             and f"skills/{n}" not in sources)  # listed under another name, e.g. browser-as-aidan -> browser-as-you

for n, o in drifted:
    print(f"drifted  {n:28s} {o}")
for n in new:
    print(f"new      {n}")
print(f"({len(retired)} listed skills have no live original; their public copy is the only copy)")

if "--pending" in sys.argv and (drifted or new):
    pf = os.path.join(HOME, ".claude/pending.json")
    items = json.load(open(pf))
    today = datetime.date.today().isoformat()
    iid = f"skill-drift-{today}"
    if not any(i.get("id") == iid for i in items):
        items.append({"id": iid, "due": today, "project": "agensi-skills",
                      "what": f"Skills to re-publish: {len(drifted)} drifted, {len(new)} never decided",
                      "how": "cd ~/Desktop/agensi-skills && python3 tools/drift.py; follow the skill-publishing "
                             "skill (re-scrub drifted copies, update_skill, drift.py --mark; list or skip new ones), "
                             "then python3 tools/build_marketplace.py, commit, push."})
        json.dump(items, open(pf, "w"), indent=1)
sys.exit(1 if drifted or new else 0)
