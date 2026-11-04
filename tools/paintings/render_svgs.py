"""Render all compositions to raw PNG (before the painterly pass)."""
import random, sys, os
from compositions import PAINTINGS
from motifs import defs, W, H
from playwright.sync_api import sync_playwright
out = sys.argv[1]; only = sys.argv[2:] 
os.makedirs(out, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': W, 'height': H})
    for pid, cat, title, desc, med, fn in PAINTINGS:
        if only and pid not in only: continue
        rng = random.Random(pid)
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{defs()}{fn(rng)}</svg>'
        path = os.path.join(out, pid + '.svg'); open(path, 'w').write(svg)
        pg.goto('file://' + path); pg.wait_for_timeout(250)
        pg.screenshot(path=os.path.join(out, pid + '.png'))
        print(pid, len(svg) // 1024, 'KB svg')
    b.close()
