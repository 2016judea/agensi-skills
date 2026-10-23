#!/bin/zsh
# Real Mobile Safari probe on a HEADLESS iOS Simulator — the tier the emulators
# cannot reach. Proven on a site whose 12px address field zoomed iOS to scale
# 1.33 and stayed there after the keyboard closed; the fixed page focused at 1.00.
#
#   sim_probe.sh <url> <out_dir> [tap_x tap_y]     # tap coords in POINTS (iPhone 17: 402x874)
#
# Needs: Xcode 27 (App Store; ~3.7 GB on disk is complete), the iOS runtime
# (`xcodebuild -downloadPlatform iOS`, 8 GB, registers despite a manifest error),
# idb for taps (`brew trust facebook/fb && brew install idb-companion`, client
# `pip install fb-idb`). Xcode 27 from the App Store ships NO
# Simulator.app, so there is no window to click; simctl renders headless and idb
# injects touches. The software keyboard DOES appear headless, and the focus zoom
# runs with it.
#
# Reading the result: compare 2-after-tap.png with 1-load.png. Bigger type and a
# right edge off-screen is the iOS zoom trap. For a number, load a page that prints
# `visualViewport.scale` (see zoomtest.html in this directory) — scale 1.33 = a
# 12px field, 1.00 = clean.
set -euo pipefail
URL=$1; OUT=$2; TX=${3:-}; TY=${4:-}
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
IDB=${IDB:-idb}
mkdir -p "$OUT"
DEV=$(xcrun simctl list devices available | grep -E "iPhone 17 \(" | head -1 | sed -E 's/.*\(([0-9A-F-]{36})\).*/\1/')
[ -n "$DEV" ] || DEV=$(xcrun simctl list devices available | grep -i iphone | head -1 | sed -E 's/.*\(([0-9A-F-]{36})\).*/\1/')
[ -n "$DEV" ] || { echo "no iPhone simulator; run: xcodebuild -downloadPlatform iOS"; exit 2; }
xcrun simctl boot "$DEV" 2>/dev/null || true
xcrun simctl bootstatus "$DEV" -b >/dev/null
# First openurl after a boot times out while SpringBoard settles; the second works.
xcrun simctl openurl "$DEV" "$URL" 2>/dev/null || { sleep 8; xcrun simctl openurl "$DEV" "$URL"; }
sleep 9
xcrun simctl io "$DEV" screenshot "$OUT/1-load.png" >/dev/null 2>&1
echo "loaded: $OUT/1-load.png"
if [ -n "$TX" ]; then
  # The companion dies with the device; reconnect every run.
  "$IDB" disconnect "$DEV" >/dev/null 2>&1 || true
  "$IDB" connect "$DEV" >/dev/null
  "$IDB" ui tap "$TX" "$TY" --udid "$DEV"
  sleep 3
  xcrun simctl io "$DEV" screenshot "$OUT/2-after-tap.png" >/dev/null 2>&1
  echo "after tap: $OUT/2-after-tap.png"
  # The keyboard's Done tick sits at ~(361,512) pts on an iPhone 17 while the
  # keyboard is up. A page that stayed zoomed after this is the trap.
  "$IDB" ui tap 361 512 --udid "$DEV"
  sleep 3
  xcrun simctl io "$DEV" screenshot "$OUT/3-after-dismiss.png" >/dev/null 2>&1
  echo "after dismiss: $OUT/3-after-dismiss.png"
fi
# Field coordinates: measure with Playwright WebKit at viewport 402x874 —
# getBoundingClientRect() of the input is already in points, no status-bar offset
# needed on iOS 27 Safari (toolbar is at the bottom).
