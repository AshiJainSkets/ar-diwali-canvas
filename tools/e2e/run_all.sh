#!/usr/bin/env bash
# Full automated check: synthetic camera videos → real tracker in headless Chromium → alignment metrics.
# Requires: server running on $BASE (default http://localhost:8080), python3 + playwright + opencv-python.
set -euo pipefail
BASE=${BASE:-http://localhost:8080}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$HERE/videos}
mkdir -p "$OUT"
curl -sf "$BASE/api/canvas/demo/print.svg?compile=1" > "$OUT/demo_print.svg"
python3 - "$OUT" <<'PY'
import sys
from playwright.sync_api import sync_playwright
o=sys.argv[1]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':2400,'height':1800})
    pg.goto('file://'+o+'/demo_print.svg'); pg.wait_for_timeout(300); pg.screenshot(path=o+'/demo_print.png'); b.close()
PY
for s in frontal angled close moving; do python3 "$HERE/make_video.py" "$OUT/demo_print.png" "$OUT" "$s"; done
for s in frontal angled close moving; do python3 "$HERE/run_tracking_test.py" "$BASE" "$OUT" "$s" "$OUT/shot_$s.png"; done
