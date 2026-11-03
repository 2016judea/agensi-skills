#!/bin/bash
# Copy the two Reddit scripts from the tool skill into every task skill in the series,
# so each Agensi listing installs standalone. Edit the copies in skills/reddit-mining/scripts
# only, then run this. Usage: tools/sync_reddit_series.sh
cd "$(dirname "$0")/.." || exit 1
for s in reddit-pain-points reddit-demand-check reddit-tool-stack reddit-competitor-chatter \
         reddit-customer-language reddit-thread-digest; do
  mkdir -p "skills/$s/scripts"
  cp skills/reddit-mining/scripts/reddit_pull.py skills/reddit-mining/scripts/reddit_tally.py "skills/$s/scripts/"
done
echo synced
