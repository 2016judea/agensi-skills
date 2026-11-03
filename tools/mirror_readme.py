#!/usr/bin/env python3
"""README for the public mirror, generated from .claude-plugin/marketplace.json (public variant) and each SKILL.md."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = json.load(open(os.path.join(ROOT, ".claude-plugin/marketplace.json")))


def desc(n):
    t = open(os.path.join(ROOT, "skills", n, "SKILL.md")).read()
    fm = t.split("---")[1] if t.startswith("---") else ""
    d = re.search(r"^description:\s*(>-?\s*\n)?(.*?)(?=^\S|\Z)", fm, re.S | re.M)
    s = " ".join((d.group(2) if d else "").split()).strip("'\"")
    s = re.split(r"(?<=[.!?])\s", s)[0]
    return s[:160] + ("…" if len(s) > 160 else "")


total = sum(len(p["skills"]) for p in m["plugins"])
out = [f"# Brick & Mortar skills", "",
       f"{total} free agent skills (SKILL.md) for Claude Code and any agent that reads the "
       "[Agent Skills](https://agentskills.io/specification) format: small-business research, Reddit research, "
       "your Mac's own data and OS, platform APIs, trading, personas, creative tools.", "",
       "## Install", "",
       "Claude Code, as plugins:", "", "```",
       "/plugin marketplace add 2016judea/brick-mortar-skills",
       "/plugin install bm-mac@brick-mortar-skills      # or any plugin below", "```", "",
       "Any agent, one skill at a time ([skills.sh](https://skills.sh)):", "", "```",
       "npx skills add 2016judea/brick-mortar-skills --skill reddit-pain-points", "```", "",
       "Also listed free on [Agensi](https://agensi.io/creators/brick-mortar).", ""]
for p in m["plugins"]:
    out += [f"## {p['name']} ({len(p['skills'])})", "", p["description"], ""]
    for s in p["skills"]:
        n = s.strip("./")
        out.append(f"- [`{n}`](skills/{n}/SKILL.md) — {desc(n)}")
    out.append("")
out += ["## License", "",
        "MIT, unless a skill's own frontmatter names another license. Scripts that call an outside API or read "
        "public data run on your machine with your own credentials; the terms of those services govern what you pull.", ""]
print("\n".join(out))
