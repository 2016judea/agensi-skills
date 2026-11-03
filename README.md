# agensi-skills

Scrubbed, public-safe copies of our Claude Code skills and hooks, listed free on
[Agensi](https://agensi.io/creators/brick-mortar). Private repo: it holds the scrub tooling and
the decision ledger, not the originals (those stay where they live and were never edited).

- `skills/<name>/` — one folder per listing: `SKILL.md` plus scripts and small reference files.
  No data, corpora, images or personal details.
- `LEDGER.md` — every skill and hook: listed or skipped, the Agensi URL, what was scrubbed, why
  anything was skipped. Regenerate with `python3 tools/build_ledger.py`.
- `tools/gate.sh` — the final per-listing gate: personal identifiers, other people's names,
  business ids, key shapes and high-entropy strings. Zero hits or it doesn't list.
  `tools/allow.txt` holds the reviewed false positives.
- `tools/submit.py` — gate, preview, confirm via the Agensi MCP (`tools/agensi.py`, OAuth token kept
  outside the repo in `~/.config/agensi/`). Logs to `submissions.jsonl`.

- `tools/usage.py` — daily snapshot of external uses per listing into `usage/`, the data a price waits on.
  Every listing starts free; Aidan reads the usage when he checks in and decides on any price.

Scrub rules: no personal identifiers, no other real people, no private life or money, no secrets,
no data files or copyrighted corpora; generalise rather than gut; skip what doesn't survive.
