#!/bin/zsh
# Publish skills/ to the PUBLIC repo github.com/2016judea/brick-mortar-skills, which skills.sh and SkillsMP
# index and which installs as a Claude Code plugin marketplace. Only gated, listed skills go out; the scrub
# tooling, ledger and submissions stay in this private repo. Run by sync_local.sh after each sync.
set -eu
cd ~/Desktop/agensi-skills
M=~/Desktop/brick-mortar-skills
for d in skills/*/; do tools/gate.sh "$d" >/dev/null || { echo "gate failed: $d — mirror not published"; exit 1; }; done
[ -d $M/.git ] || git clone -q https://github.com/2016judea/brick-mortar-skills.git $M
rsync -a --delete --exclude .git --exclude __pycache__ --exclude '*.pyc' skills/ $M/skills/
/usr/bin/python3 tools/build_marketplace.py --public >/dev/null
mkdir -p $M/.claude-plugin
cp .claude-plugin/marketplace.json $M/.claude-plugin/marketplace.json
/usr/bin/python3 tools/build_marketplace.py >/dev/null   # restore the local variant here
/usr/bin/python3 tools/mirror_readme.py > $M/README.md
cd $M
git add -A
git diff --cached --quiet || { git commit -q -m "Sync skills ($(ls skills | wc -l | tr -d ' ') skills)"; git push -q; echo "mirror pushed"; }
