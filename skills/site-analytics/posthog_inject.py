#!/usr/bin/env python3
"""Put the shared PostHog snippet into HTML files (or print it for a generator).

    posthog_inject.py --site <repo> file.html [...]   # insert before </head>, or replace an existing block
    posthog_inject.py --site <repo> --print [--fstring]  # emit the block; --fstring doubles braces

Idempotent: the block is delimited by <!-- site-posthog:begin ... --> / <!-- site-posthog:end -->.
Source of truth for the block: posthog_snippet.html next to this file.
"""
import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
BLOCK_RE = re.compile(r"<!-- site-posthog:begin.*?<!-- site-posthog:end -->\n?", re.S)


def block(site: str) -> str:
    return (HERE / "posthog_snippet.html").read_text().replace("__SITE__", site)


def inject(text: str, snippet: str) -> str:
    if BLOCK_RE.search(text):
        return BLOCK_RE.sub(lambda _: snippet, text, count=1)
    i = text.lower().find("</head>")
    if i < 0:
        raise ValueError("no </head>")
    return text[:i] + snippet + text[i:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--fstring", action="store_true")
    ap.add_argument("files", nargs="*")
    a = ap.parse_args()
    snip = block(a.site)
    if a.print:
        sys.stdout.write(snip.replace("{", "{{").replace("}", "}}") if a.fstring else snip)
        return 0
    rc = 0
    for f in a.files:
        p = pathlib.Path(f)
        try:
            new = inject(p.read_text(), snip)
        except ValueError as e:
            print(f"skip {f}: {e}", file=sys.stderr)
            rc = 1
            continue
        p.write_text(new)
        print(f"ok {f}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
