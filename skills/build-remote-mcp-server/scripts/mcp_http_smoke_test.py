#!/usr/bin/env python3
"""Smoke-test a Streamable HTTP MCP server: tools/list + tools/call per tool.

Usage:
    python3 mcp_http_smoke_test.py <base_url> [calls.json]

<base_url>   e.g. http://localhost:8787/mcp or https://your-worker.workers.dev/mcp
calls.json   optional — a JSON array of [tool_name, arguments_dict] pairs to
             test with tools/call. Without it, only tools/list runs.

Handles the two things that are easy to get wrong when scripting this by
hand: parsing the SSE "data: {...}" frame (not plain JSON — Streamable HTTP
wraps every response in an SSE event), and reading structuredContent/isError
instead of assuming the raw text content is the whole story.
"""
import json
import re
import sys
import urllib.request


def call(url: str, method: str, params: dict, req_id: int) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
            # Cloudflare's bot protection blocks the default "Python-urllib/x.y"
            # User-Agent with a 403 even when everything else about the request
            # is correct — curl's default UA sails through. See this skill's
            # gotcha #9.
            "user-agent": "mcp-http-smoke-test/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode()
    m = re.search(r"^data: (.+)$", raw, re.MULTILINE)
    if not m:
        raise RuntimeError(f"no SSE data frame in response: {raw[:300]!r}")
    return json.loads(m.group(1))


def main() -> None:
    base_url = sys.argv[1]
    calls_file = sys.argv[2] if len(sys.argv) > 2 else None

    d = call(base_url, "tools/list", {}, 1)
    if "error" in d:
        print(f"tools/list JSONRPC ERROR: {d['error']}")
        sys.exit(1)
    tools = d["result"]["tools"]
    print(f"tools/list: {len(tools)} tools")
    for t in tools:
        ro = t.get("annotations", {}).get("readOnlyHint")
        has_out = "outputSchema" in t
        print(f"  - {t['name']:30s} readOnlyHint={ro} outputSchema={has_out}")

    if not calls_file:
        return

    with open(calls_file) as f:
        test_calls = json.load(f)

    print()
    for i, (name, args) in enumerate(test_calls, start=2):
        d = call(base_url, "tools/call", {"name": name, "arguments": args}, i)
        if "error" in d:
            print(f"{name}: JSONRPC ERROR {d['error']}")
            continue
        r = d["result"]
        is_err = r.get("isError")
        has_structured = "structuredContent" in r
        print(f"{name}: isError={is_err} structuredContent={has_structured}")


if __name__ == "__main__":
    main()
