---
name: mac-keychain
description: Keep API keys and tokens in the macOS login keychain instead of .env files, and read them into scripts without ever printing them — store, read, update, delete with the `security` CLI. Use when you say "where should I put this API key", "stop putting secrets in .env", "store this token in my keychain", "read the key from keychain in my script", "my launch agent can't find the API key", "security: item could not be found". Covers the exact commands, exit codes, never-echo patterns, launchd use, and the ACL prompt.
compatibility: >-
  macOS (tested on macOS 26, Apple silicon). Built-in tool only: security. No network.
metadata:
  grounded: "2026-11-03 — a throwaway item added, read by length, duplicated and deleted live on macOS 26.6"
---

# Secrets in the macOS keychain

A `.env` file is plaintext on disk, ends up in backups, gets committed by accident and is
readable by every process you run. The login keychain is encrypted, unlocked with your
login, and per-item access-controlled. For your own scripts it is the better home.

## The commands

Use one **service** name per secret, namespaced (`local.myproject.openai`), and your user
as the account.

```bash
# store (or update: -U overwrites an existing item instead of failing)
security add-generic-password -a "$USER" -s local.myproject.api -U -w
#   ^ with -w LAST and no value, it prompts for the secret (needs a TTY), so it never
#     lands in shell history or `ps`.

# read into a variable, never to the terminal
API_KEY=$(security find-generic-password -a "$USER" -s local.myproject.api -w) || exit 1
export API_KEY

# check it exists without revealing it
security find-generic-password -s local.myproject.api >/dev/null 2>&1 && echo present
echo "${#API_KEY} chars"            # length is a safe confirmation; the value is not

# delete
security delete-generic-password -a "$USER" -s local.myproject.api
```

Exit codes (verified): `0` found; **`44`** not found (`The specified item could not be
found in the keychain.`); **`45`** add without `-U` when the item already exists
(`already exists in the keychain`).

## Never print the secret

- `-w` prints only the password. **Without `-w`, the attribute dump does not include the
  password** but does show service, account and dates; that is safe to show.
- `-g` prints the password to stderr (verified). Don't use it.
- Never `echo $API_KEY`, never `set -x` in a script that reads one, never paste a value
  into a log, commit, issue or chat. To prove a read worked, print the length.
- Passing a value inline (`-w 'abc123'`) puts it in shell history and in `ps` output for
  the life of the process. If the value comes from another program, pipe it through a
  variable in a script that is not logged, and clear the variable after.

## Use it from a script, an app or a launch agent

```bash
#!/bin/zsh
set -euo pipefail
TOKEN=$(security find-generic-password -a "$USER" -s local.myproject.api -w)
curl -sS -H "Authorization: Bearer $TOKEN" https://api.example.com/v1/me >/dev/null
```

```python
import getpass, subprocess
key = subprocess.run(["security", "find-generic-password", "-a", getpass.getuser(),
                      "-s", "local.myproject.api", "-w"],
                     capture_output=True, text=True, check=True).stdout.strip()
```

This is the fix for "my LaunchAgent can't see the API key": jobs don't load `.zshrc`
(`mac-launchd` skill), but they run in your login session, where the login keychain is
unlocked, so the same `security` call works.

## Traps

- **The ACL prompt.** An item created by `security` lists `security` as trusted, so
  `security find-generic-password` reads it with no dialog (verified). An item created by
  another app (a browser, Keychain Access) may pop **"security wants to use your
  confidential information"** and block until a human clicks. In unattended runs, create
  the items you read with `security` itself, and wrap reads:
  `perl -e 'alarm 10; exec @ARGV' security find-generic-password ...` (exit 142 = timed out).
- **No GUI session, locked keychain.** Over SSH, or before anyone logs in, the login
  keychain is locked and reads fail. That is the design; don't unlock it with a password
  in a script.
- **iCloud Keychain / passwords app items** are a different store (data-protection
  keychain) and generally aren't visible to `security`. Store script secrets with
  `security`, not through the Passwords app.
- `security list-keychains` should show your `login.keychain-db`. If a read fails with
  44 and you're sure it exists, check you used the same `-s` and `-a` you stored with:
  both are part of the lookup.

## Moving off a `.env`

For each line: `security add-generic-password -a "$USER" -s local.<project>.<name> -U -w`
(type the value at the prompt), replace the `.env` read with the `security` call, run the
script once, then delete the `.env` line. Deleting the user's `.env` file is their call.
