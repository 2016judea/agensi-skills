#!/bin/bash
# Print an annotated-play HTML file (from render_annotated_play.py) to PDF via
# headless Chrome. No installs needed (weasyprint/wkhtmltopdf/pandoc aren't
# required). --no-pdf-header-footer is REQUIRED or Chrome stamps a date/URL/
# page-number header+footer on every page.
#
# Usage: ./print_pdf.sh input.html output.pdf
set -e
IN="$1"
OUT="$2"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -x "$CHROME" ]; then
  echo "Google Chrome not found at $CHROME -- edit this script's CHROME path." >&2
  exit 1
fi
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")"
echo "wrote $OUT"
