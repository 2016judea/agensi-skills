"""
List or set Vercel project environment variables via the Vercel REST API.

No `vercel` CLI required. Requires VERCEL_TOKEN in the environment (Account
Settings -> Tokens on vercel.com). For a team project also set VERCEL_TEAM_ID
(team_...), or the project search only sees your personal scope.

Usage:
    export VERCEL_TOKEN=...   # and VERCEL_TEAM_ID=team_... for a team project

    # List var names + targets for a project (never prints values)
    python3 vercel_env.py list --project my-site

    # Create or update one or more vars (upsert — safe to re-run)
    python3 vercel_env.py set SOME_API_KEY=abc123 \\
        --project my-site --target production,preview

    # Pull a value straight out of .env instead of typing it twice
    python3 vercel_env.py set-from-env GEMINI_API_KEY \\
        --project my-site
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.vercel.com"


def _request(method: str, path: str, token: str, params: dict | None = None, body: dict | None = None) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items() if v)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        raise RuntimeError(f"Vercel API {method} {path} -> {e.code}: {detail}") from None


def find_project(name: str, token: str) -> tuple[str, str | None]:
    """Returns (project_id, team_id_or_None)."""
    team = os.environ.get("VERCEL_TEAM_ID")
    data = _request("GET", "/v9/projects", token, params={"search": name, "limit": 20, "teamId": team})
    for p in data.get("projects", []):
        if p.get("name") == name:
            return p["id"], p.get("accountId")
    raise RuntimeError(f"No Vercel project named {name!r} found for this token.")


def list_env(project: str, token: str) -> None:
    project_id, team_id = find_project(project, token)
    params = {"teamId": team_id} if team_id else {}
    data = _request("GET", f"/v9/projects/{project_id}/env", token, params=params)
    for e in sorted(data.get("envs", []), key=lambda e: e.get("key", "")):
        print(f"{e['key']}\t{','.join(e.get('target', []))}")


def set_env(project: str, token: str, pairs: dict[str, str], targets: list[str]) -> None:
    project_id, team_id = find_project(project, token)
    params = {"teamId": team_id, "upsert": "true"} if team_id else {"upsert": "true"}
    payload = [
        {"key": k, "value": v, "type": "encrypted", "target": targets}
        for k, v in pairs.items()
    ]
    result = _request("POST", f"/v10/projects/{project_id}/env", token, params=params, body=payload)
    for c in result.get("created", []):
        print(f"set: {c['key']} -> {','.join(c.get('target', []))}")
    for f in result.get("failed", []):
        print(f"FAILED: {f}", file=sys.stderr)


def main() -> None:
    # Shared so --project/--target work whether typed before or after the
    # subcommand (argparse subparsers don't inherit parent-only options).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=os.environ.get("VERCEL_PROJECT"), help="Vercel project name (or set VERCEL_PROJECT)")
    common.add_argument("--target", default="production,preview", help="Comma-separated: production,preview,development")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, parents=[common])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List env var names + targets (never prints values)", parents=[common])

    set_parser = sub.add_parser("set", help="Create or update one or more KEY=VALUE pairs", parents=[common])
    set_parser.add_argument("pairs", nargs="+", help="KEY=VALUE pairs")

    set_from_env_parser = sub.add_parser("set-from-env", help="Copy KEY's value from the local .env into Vercel", parents=[common])
    set_from_env_parser.add_argument("keys", nargs="+", help="Env var names to copy from .env")

    args = parser.parse_args()
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        print("VERCEL_TOKEN not set — export VERCEL_TOKEN=...   # and VERCEL_TEAM_ID=team_... for a team project first.", file=sys.stderr)
        sys.exit(1)

    if not args.project:
        print("Pass --project <name> (or set VERCEL_PROJECT).", file=sys.stderr)
        sys.exit(1)
    targets = [t.strip() for t in args.target.split(",") if t.strip()]

    if args.command == "list":
        list_env(args.project, token)
    elif args.command == "set":
        pairs = dict(p.split("=", 1) for p in args.pairs)
        set_env(args.project, token, pairs, targets)
    elif args.command == "set-from-env":
        pairs = {}
        for key in args.keys:
            value = os.environ.get(key)
            if not value:
                print(f"{key} not found in the current environment — export .env first.", file=sys.stderr)
                sys.exit(1)
            pairs[key] = value
        set_env(args.project, token, pairs, targets)


if __name__ == "__main__":
    main()
