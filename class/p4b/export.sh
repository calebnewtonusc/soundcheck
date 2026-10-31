#!/bin/bash
# Build SoundCheck-P4b.pdf from screenshots of the live site, one per slide, so the
# PDF is pixel-for-pixel what the browser shows. Chrome's print path turned
# the saber's blurred glow into solid blocks (2026-09-29), and screenshots
# don't have that problem.
#
# Six renders at a time. All seventeen at once starved each other.
set -uo pipefail
cd "$(dirname "$0")"
export C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
export URL="${1:-http://localhost:4519/index.html}"
export OUT; OUT=$(mktemp -d)
N=$(grep -c '<section class="slide' index.html)

shot() {
  local i=$1 f
  f="$OUT/slide-$(printf %02d "$i").png"
  # Headless Chrome writes the PNG in about a second and then sits for 40s
  # before exiting (measured 2026-09-29), so wait for the file, not the process.
  "$C" --headless=new --user-data-dir="$OUT/p$i" \
    --disable-gpu --no-first-run --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1456,819 --virtual-time-budget=3000 \
    --screenshot="$f" "$URL?slide=$i&v=$RANDOM" >/dev/null 2>&1 &
  local pid=$! t=0
  while [ ! -s "$f" ] && [ $t -lt 200 ]; do sleep 0.1; t=$((t+1)); done
  sleep 0.3; kill $pid 2>/dev/null; wait $pid 2>/dev/null
  [ -s "$f" ] || echo "FAIL slide $i" >&2
}
export -f shot
seq 1 "$N" | xargs -P 3 -I{} bash -c 'shot {}'

got=$(ls "$OUT"/slide-*.png 2>/dev/null | wc -l | tr -d ' ')
[ "$got" = "$N" ] || { echo "only $got of $N slides rendered" >&2; exit 1; }

# Wrap the PNGs in a page that prints one image per 1456x819 page. Printing
# an image adds nothing and changes nothing, unlike printing the live CSS.
{
  echo '<!doctype html><html><head><style>@page{size:1456px 819px;margin:0}'
  echo 'body{margin:0}img{display:block;width:1456px;height:819px;break-after:page}</style></head><body>'
  for f in "$OUT"/slide-*.png; do echo "<img src=\"file://$f\">"; done
  echo '</body></html>'
} > "$OUT/pages.html"
"$C" --headless=new --user-data-dir="$OUT/print" \
  --disable-gpu --no-first-run --no-pdf-header-footer --allow-file-access-from-files \
  --print-to-pdf="$PWD/SoundCheck-P4b.pdf" "file://$OUT/pages.html" >/dev/null 2>&1 &
pp=$!; t=0
while [ ! -s SoundCheck-P4b.pdf ] && [ $t -lt 600 ]; do sleep 0.1; t=$((t+1)); done
sleep 1; kill $pp 2>/dev/null
echo "$N slides -> SoundCheck-P4b.pdf"
