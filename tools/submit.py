#!/usr/bin/env python3
"""Submit scrubbed skills to Agensi as FREE listings. Gate first, then preview, then confirm.
Usage: submit.py <skill> [<skill> ...]   (records results in submissions.jsonl)"""
import json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import agensi
from listings import L
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "submissions.jsonl")

def frontmatter(md):
    m = re.match(r"---\n(.*?)\n---\n", md, re.S)
    fm = m.group(1)
    d = re.search(r"^description:\s*(>-?|\|)?\s*\n?(.*?)(?=^\w[\w-]*:|\Z)", fm, re.S | re.M).group(2)
    return " ".join(d.split())

def summary(desc):
    s = re.split(r"(?<=[.!?])\s", desc)[0]
    return s if len(s) <= 200 else s[:197].rsplit(" ", 1)[0] + "..."

def submitted():
    out = {}
    if os.path.exists(LOG):
        for line in open(LOG):
            r = json.loads(line); out[r["skill"]] = r
    return out

def main():
    done = submitted()
    for skill in sys.argv[1:]:
        if done.get(skill, {}).get("status") == "submitted":
            print("skip (already submitted)", skill); continue
        d = os.path.join(ROOT, "skills", skill)
        g = subprocess.run([os.path.join(ROOT, "tools/gate.sh"), d], capture_output=True, text=True)
        if g.returncode != 0:
            print("GATE FAIL", skill, g.stdout[:300]); continue
        files = []
        for base, _, fs in os.walk(d):
            for f in sorted(fs):
                p = os.path.join(base, f)
                files.append({"path": os.path.relpath(p, d), "content": open(p, encoding="utf-8").read()})
        desc = frontmatter(open(os.path.join(d, "SKILL.md")).read())
        name, tags = L[skill]
        args = {"files": files, "name": name, "summary": summary(desc), "description": desc,
                "pricing_type": "free", "tags": tags,
                "compatibility_note": "Written for Claude Code; works with any agent that reads SKILL.md.",
                "version": "1.0"}
        prev = agensi.call("submit_skill", args)
        if not isinstance(prev, dict) or "draft_id" not in prev:
            rec = {"skill": skill, "status": "preview_failed", "detail": str(prev)[:500], "t": time.time()}
        else:
            conf = agensi.call("submit_skill", {"draft_id": prev["draft_id"], "confirm": True})
            ok = isinstance(conf, dict) and conf.get("status") not in ("error",) and "error" not in conf
            rec = {"skill": skill, "status": "submitted" if ok else "confirm_failed", "draft_id": prev["draft_id"],
                   "detail": conf if isinstance(conf, dict) else str(conf)[:500], "t": time.time()}
        open(LOG, "a").write(json.dumps(rec) + "\n")
        print(rec["status"], skill, json.dumps(rec.get("detail"))[:200])
        time.sleep(4)

if __name__ == "__main__":
    main()
