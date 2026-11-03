#!/usr/bin/env python3
"""
One-time Dropbox OAuth flow to get a refresh token.
After running this, token refresh is fully automatic — no more expired tokens.

Usage (from the directory holding your .env):
    python3 dropbox_auth.py
    ENV_FILE=/path/to/.env python3 dropbox_auth.py
"""
import json
import os
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ENV_FILE = Path(os.environ.get("ENV_FILE", ".env")).resolve()  # the .env in the current directory by default


def _load_env():
    if not ENV_FILE.exists():
        ENV_FILE.write_text("")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _update_env(key: str, value: str):
    lines = ENV_FILE.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"  → {key} saved to .env")


def main():
    _load_env()
    app_key    = os.environ.get("DROPBOX_APP_KEY", "")
    app_secret = os.environ.get("DROPBOX_APP_SECRET", "")

    if not app_key or not app_secret:
        print("ERROR: Add DROPBOX_APP_KEY and DROPBOX_APP_SECRET to .env first.")
        print("  Get them from: https://www.dropbox.com/developers/apps")
        return

    # Step 1 — build authorization URL
    auth_url = (
        "https://www.dropbox.com/oauth2/authorize?"
        + urllib.parse.urlencode({
            "client_id":     app_key,
            "response_type": "code",
            "token_access_type": "offline",  # gives us a refresh token
        })
    )

    print("Opening Dropbox authorization page in your browser...")
    print(f"\n{auth_url}\n")
    webbrowser.open(auth_url)

    code = input("Paste the authorization code from Dropbox here: ").strip()
    if not code:
        print("No code entered. Aborting.")
        return

    # Step 2 — exchange code for refresh token + access token
    data = urllib.parse.urlencode({
        "code":         code,
        "grant_type":   "authorization_code",
        "client_id":    app_key,
        "client_secret": app_secret,
    }).encode()

    req = urllib.request.Request(
        "https://api.dropbox.com/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())

    refresh_token = resp.get("refresh_token", "")
    access_token  = resp.get("access_token", "")

    if not refresh_token:
        print(f"ERROR: No refresh token in response: {resp}")
        return

    print("\n✓ Got refresh token. Saving to .env...")
    _update_env("DROPBOX", access_token)
    _update_env("DROPBOX_REFRESH_TOKEN", refresh_token)
    print("\nDone. Tokens are saved. You won't need to do this again.")


if __name__ == "__main__":
    main()
