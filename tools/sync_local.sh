#!/bin/zsh
# Keep the local harness on the current skill set. Run daily by launchd (local.brick-mortar-skills-sync)
# and by hand after any publish: rebuild the marketplace, refresh it, install new plugins, update the rest,
# then queue a pending item if any original drifted or a new global skill was never decided.
set -u
cd ~/Desktop/agensi-skills || exit 1
CLAUDE=${CLAUDE:-$(command -v claude || echo ~/.local/bin/claude)}
/usr/bin/python3 tools/build_marketplace.py >/dev/null
"$CLAUDE" plugin marketplace update brick-mortar-skills >/dev/null 2>&1
installed=$("$CLAUDE" plugin list 2>/dev/null)
for p in $(/usr/bin/python3 -c "import json;print(' '.join(p['name'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins']))"); do
  if print -r -- "$installed" | grep -q "$p@brick-mortar-skills"; then
    "$CLAUDE" plugin update "$p@brick-mortar-skills" >/dev/null 2>&1
  else
    "$CLAUDE" plugin install "$p@brick-mortar-skills" >/dev/null 2>&1 && echo "installed $p"
  fi
done
/usr/bin/python3 tools/drift.py --pending >/dev/null
exit 0
