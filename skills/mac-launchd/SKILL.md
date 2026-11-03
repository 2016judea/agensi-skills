---
name: mac-launchd
description: Schedule a script on a Mac with launchd — a LaunchAgent that runs every morning, every hour, at login or on a file change — and debug the one that silently never ran. Use when you say "run this every day at 7", "cron on my mac", "make it start at login", "my launch agent isn't running", "launchctl load doesn't work", "Bootstrap failed: 5", "why does my job say command not found". Covers the plist template, StartCalendarInterval vs StartInterval, bootstrap/bootout/kickstart, reading last exit code, and the PATH, sleep and permission traps.
compatibility: >-
  macOS (tested on macOS 26, Apple silicon). Built-in tools only: launchctl, plutil. No network. Per-user agents need no sudo.
metadata:
  grounded: "2026-11-03 — template bootstrapped, kicked, inspected and booted out live on macOS 26.6"
---

# launchd, the Mac's scheduler

Use a **LaunchAgent** in `~/Library/LaunchAgents/` (runs as you, in your login session, no
sudo). LaunchDaemons in `/Library/LaunchDaemons/` run as root and need an admin; you
almost never want one. Cron still exists but runs without your session's permissions and
is deprecated; don't.

## Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>local.example.morning-job</string>
  <key>ProgramArguments</key><array>
    <string>/bin/zsh</string><string>-lc</string>
    <string>exec "$HOME/bin/morning-job.sh"</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/morning-job.out.log</string>
  <key>StandardErrorPath</key><string>/tmp/morning-job.err.log</string>
</dict></plist>
```

- File name must equal `Label` + `.plist`.
- Paths in the plist are literal: **no `~`, no `$HOME`** outside a shell string. Write the
  absolute path, or do as above and let `zsh -c` expand `$HOME`.
- Schedules: `StartCalendarInterval` (wall clock; an array of dicts for several times;
  omitted keys are wildcards, so `{Minute:0}` is hourly), `StartInterval` (every N
  seconds), `RunAtLoad` (at login / on bootstrap), `WatchPaths` (when a file changes),
  `KeepAlive` (restart if it exits; for daemons, not jobs).
- `plutil -lint file.plist` before loading. A malformed plist fails with an unhelpful error.

## Load, run, inspect, unload

```bash
U=gui/$(id -u); L=local.example.morning-job; P=~/Library/LaunchAgents/$L.plist
plutil -lint "$P"
launchctl bootstrap $U "$P"           # load (replaces the deprecated `launchctl load`)
launchctl kickstart -p $U/$L          # run it NOW, prints the pid — test before waiting for 7am
launchctl print $U/$L | grep -E 'state|runs|last exit code|path'
launchctl bootout $U/$L               # unload (replaces `launchctl unload`)
```

After editing the plist you must `bootout` then `bootstrap` again; launchd caches it.

`launchctl list | grep <label>` gives `PID  LastExitStatus  Label`; a `-` PID means not
running right now, which is normal for a scheduled job.

## Error strings, decoded

| You see | It means |
|---|---|
| `Bootstrap failed: 5: Input/output error` | Usually **already loaded**. `bootout` first. (Verified: a second bootstrap of a loaded agent gives exactly this.) Otherwise a bad plist: lint it. |
| `Bad request.` from `launchctl print` | The label is not loaded. |
| `last exit code = 127` | Command not found: the PATH trap below. |
| `last exit code = 126` | Script not executable: `chmod +x`. |
| `runs = 0` after the scheduled time | The Mac was asleep or the job is not loaded; see below. |

## Why a job silently doesn't run

1. **PATH is not your shell's.** A job's PATH is `/usr/bin:/bin:/usr/sbin:/sbin` (verified:
   `which brew` failed inside a job on a machine where it works in Terminal). Homebrew,
   pyenv, nvm, `~/.local/bin` are all invisible. Set `EnvironmentVariables` > `PATH`, or use
   absolute paths to every tool.
2. **No shell profile.** `.zshrc` exports (API keys, aliases) are absent. Source a small env
   file explicitly in the script, or read secrets from the keychain (`mac-keychain` skill).
3. **The Mac was asleep.** A `StartCalendarInterval` missed during sleep runs once on wake;
   missed during shutdown, never. `StartInterval` timers don't advance while asleep. If it
   must run on time, schedule a wake (`sudo pmset repeat wake ...`, needs an admin) or keep
   the machine up with `caffeinate` (`mac-system-health` skill).
4. **Privacy (TCC).** A job that reads Desktop, Documents, Mail, Messages or Photos runs
   with the permissions of the *binary launchd starts*, not of your Terminal. If
   `/bin/zsh` (or the python/node binary) has no Full Disk Access, the job gets
   `Operation not permitted` and your log shows it while the same script works
   interactively. Grant FDA to the exact binary in the plist, or keep the job's files
   outside protected folders. Test from inside the job: `ls ~/Library/Messages` in the
   script, read the log. See `mac-permissions`.
5. **It ran, the output went nowhere.** Without `StandardOutPath`/`StandardErrorPath` you
   will never see the error. (launchd creates a missing log directory itself; verified.)

## Removing a job

```bash
launchctl bootout gui/$(id -u)/local.example.morning-job
rm ~/Library/LaunchAgents/local.example.morning-job.plist
```

Related: `mac-menu-bar-app` (a launchd agent that ships with a real app), `overnight-job`
(running unattended work), `mac-system-health` (sleep and power assertions).
