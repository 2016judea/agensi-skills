#!/bin/zsh
# Run a JS file inside Chrome's chrome://bookmarks tab and print window.__r.
# The JS must set window.__r (string) when done; see ../SKILL.md.
# usage: run_in_bookmarks.sh file.js [wait_seconds]
set -e
JS="$1"; WAIT="${2:-6}"
if pgrep -f -- "--headless" >/dev/null; then
  echo "A headless Chrome is running; AppleScript may target it instead of your Chrome. Kill yours by its port first." >&2
  exit 2
fi
osascript -e "set js to read POSIX file \"$JS\" as «class utf8»" -e "tell application \"Google Chrome\"
set bt to missing value
repeat with w in windows
repeat with t in tabs of w
if URL of t starts with \"chrome://bookmarks\" then set bt to t
end repeat
end repeat
if bt is missing value then set bt to make new tab at end of tabs of front window with properties {URL:\"chrome://bookmarks\"}
delay 2
execute bt javascript \"window.__r=null\"
execute bt javascript js
delay $WAIT
execute bt javascript \"window.__r\"
end tell"
