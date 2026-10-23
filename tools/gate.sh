#!/bin/bash
# Final gate: zero hits or the folder does not list.
# Usage: tools/gate.sh skills/<name> [more...]
TERMS='aidan|jude|2016judea|randomaidan|/Users/|@gmail|@brickandmortar|brickandmortar|brick ?& ?mortar|readglean|glean|[a-z0-9]\.vercel\.app|612|acct_[0-9a-z]|5671348|linkedin\.com/in|substack\.com/@|\.substack\.com|joel|becky|mason|joeri|maverick|etrade account|e\*trade.*[0-9]{6}|team_[a-z0-9]{10}|phc_|posthog_key|ein |(^|[^a-z])llc([^a-z]|$)|zoho.*[0-9]{10}|aetas|okay-mom|bricks'
KEYS='sk-[A-Za-z0-9]{10}|sk_(live|test)_|pk_(live|test)_|rk_(live|test)_|xox[abp]-|ghp_[A-Za-z0-9]{10}|gho_|AKIA[0-9A-Z]{12}|AIza[0-9A-Za-z_-]{20}|[0-9a-f]{32,}|-----BEGIN'
rc=0
for d in "$@"; do
  [ -d "$d" ] || { echo "FAIL $d (missing)"; rc=1; continue; }
  h=$(grep -rniE "$TERMS" "$d"; grep -rnE "$KEYS" "$d"; python3 "$(dirname "$0")/entropy.py" "$d")
  name=$(basename "$d")
  allow=$(awk -F'\t' -v n="$name" '$1==n{print $2}' "$(dirname "$0")/allow.txt" | paste -sd'|' -)
  [ -n "$allow" ] && h=$(echo "$h" | grep -vE "$allow")
  h=$(echo "$h" | sed '/^$/d')
  bin=$(find "$d" -type f ! -name '*.md' ! -name '*.py' ! -name '*.sh' ! -name '*.js' ! -name '*.mjs' ! -name '*.ts' ! -name '*.txt' ! -name '*.json' ! -name '*.swift' ! -name '*.html' ! -name '*.css' ! -name '*.toml' ! -name '*.yaml' ! -name '*.yml')
  if [ -n "$h$bin" ]; then echo "FAIL $d"; echo "$h" | head -40; [ -n "$bin" ] && echo "non-text: $bin"; rc=1; else echo "PASS $d"; fi
done
exit $rc
