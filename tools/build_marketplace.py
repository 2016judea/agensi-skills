#!/usr/bin/env python3
"""Write .claude-plugin/marketplace.json so skills/ installs as Claude Code plugins.

  build_marketplace.py            the LOCAL marketplace (this repo): leaves out any skill whose original
                                  still lives in ~/.claude/skills, so the harness never loads two copies
  build_marketplace.py --public   the full set, for the public mirror

Grouping comes from tools/themes.json. Unplaced skills land in the default plugin and are printed.
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(ROOT, "tools"))
public = "--public" in sys.argv
themes = json.load(open(os.path.join(ROOT, "tools/themes.json")))

# skills whose working original is still installed globally (by name, or by the ledger's source path)
src = {}
for l in open(os.path.join(ROOT, "ledger.tsv")):
    r = l.rstrip("\n").split("\t")
    if len(r) > 1 and r[0] != "name":
        src.setdefault(r[0], r[1])
glob = set(os.listdir(os.path.join(HOME, ".claude/skills")))
def has_original(n):
    if n in glob:
        return True
    s = src.get(n, "")
    return any(f"~/.claude/skills/{g}" in s.split() or f"~/.claude/skills/{g} " in s + " " for g in glob)

skills = sorted(n for n in os.listdir(os.path.join(ROOT, "skills"))
                if os.path.isfile(os.path.join(ROOT, "skills", n, "SKILL.md")))
groups, unplaced, dropped = {}, [], []
for n in skills:
    if not public and has_original(n):
        dropped.append(n)
        continue
    g = next((k for k, v in themes["plugins"].items()
              if n in v["names"] or any(n.startswith(p) for p in v["prefixes"])), None)
    if not g:
        g = themes["default"]
        unplaced.append(n)
    groups.setdefault(g, []).append(n)

desc = {k: v["description"] for k, v in themes["plugins"].items()}
desc[themes["default"]] = "General method skills: turning sessions into skills, falsifying a dataset's laws, reframing, divergent ideas, distribution, research-paper essays and more."
m = {
    "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
    "name": "brick-mortar-skills",
    "description": "Brick & Mortar's agent skills: small-business research, Reddit research, platform APIs, trading, personas, creative tools.",
    "owner": {"name": "Brick & Mortar"},
    "plugins": [{"name": g, "description": desc[g], "author": {"name": "Brick & Mortar"},
                 "source": "./skills", "strict": False, "skills": [f"./{n}" for n in sorted(ns)]}
                for g, ns in sorted(groups.items())],
}
os.makedirs(os.path.join(ROOT, ".claude-plugin"), exist_ok=True)
out = os.path.join(ROOT, ".claude-plugin/marketplace.json")
json.dump(m, open(out, "w"), indent=1)
for g, ns in sorted(groups.items()):
    print(f"{g:22s} {len(ns)}")
print(f"{sum(map(len, groups.values()))} skills in {len(groups)} plugins"
      + ("" if public else f"; {len(dropped)} left out (original still in ~/.claude/skills)"))
if unplaced:
    print("default plugin (place in tools/themes.json if wrong):", " ".join(unplaced))
