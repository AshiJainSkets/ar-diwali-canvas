"""Render the premium rangoli collection + its animation assets into public/paintings.

usage: python tools/paintings/build_rangolis.py [ids...]
"""
import os, sys, random, tempfile
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rangoli_premium import RANGOLIS, POWDER_DEFS, FLOWER_DEFS, W, H
from paintify import bake_preview
from animations import sparkle
import fxmaps
from playwright.sync_api import sync_playwright

OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'public', 'paintings'))


def powder_finish(img, rng):
    """Coloured-powder look: fine granular texture + slight colour jitter where the powder is."""
    f = img.astype(np.float32)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    powder = ((hsv[..., 1] > 70) | (hsv[..., 2] > 225)).astype(np.float32)
    powder = cv2.GaussianBlur(powder.astype(np.float32), (0, 0), 1.2)
    grain = rng.normal(0, 1, img.shape[:2]).astype(np.float32)
    grain = cv2.GaussianBlur(grain, (0, 0), 0.7)
    grain /= grain.std() + 1e-6
    f *= (1 + 0.075 * grain * powder)[..., None]
    speck = (rng.random(img.shape[:2]) > 0.996).astype(np.float32) * powder  # bright granules
    f += speck[..., None] * 60
    return np.clip(f, 0, 255).astype(np.uint8), powder


def save(pid, img, height):
    d = os.path.join(OUT, pid); os.makedirs(d, exist_ok=True)
    cv2.imwrite(os.path.join(d, 'albedo.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 88, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    cv2.imwrite(os.path.join(d, 'height.jpg'), cv2.resize((np.clip(height, 0, 1) * 255).astype(np.uint8), (800, 600), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    prev = bake_preview(img.astype(np.float32), height, 1200)
    cv2.imwrite(os.path.join(d, 'preview.jpg'), prev, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    cv2.imwrite(os.path.join(d, 'thumb.jpg'), cv2.resize(prev, (480, 360), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])


def main(only):
    tmp = tempfile.mkdtemp(prefix='rangoli-')
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': W, 'height': H})
        for pid, cat, title, desc, med, fn, fam in RANGOLIS:
            if only and pid not in only: continue
            rng = random.Random(pid)
            body, anchors = fn(rng)
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{POWDER_DEFS if fam == "powder" else FLOWER_DEFS}{body}</svg>'
            sp = os.path.join(tmp, pid + '.svg'); open(sp, 'w').write(svg)
            pg.goto('file://' + sp); pg.wait_for_timeout(400)
            png = os.path.join(tmp, pid + '.png'); pg.screenshot(path=png)
            img = cv2.imread(png)
            nrng = np.random.default_rng(sum(map(ord, pid)))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
            if fam == 'powder':
                img, powder = powder_finish(img, nrng)
                height = 0.35 + 0.35 * cv2.GaussianBlur(powder, (0, 0), 2.5) + 0.15 * (gray - cv2.GaussianBlur(gray, (0, 0), 2))
            else:
                height = 0.45 + 1.6 * (gray - cv2.GaussianBlur(gray, (0, 0), 3)) + 0.2 * (cv2.GaussianBlur(gray, (0, 0), 6) - 0.5)
            save(pid, img, cv2.GaussianBlur(height, (0, 0), 0.8))
            # animation: sparkle across the rangoli, diya flames, floating petals
            anim_anchors = []
            for a in anchors:
                if a[0] == 'sparkle_ring':
                    _, cx, cy, r, n = a
                    anim_anchors += sparkle(cx, cy, r, r, n, sum(map(ord, pid)), r=5)
                else:
                    anim_anchors.append(a)
            fxmaps.build(os.path.join(OUT, pid), anim_anchors, [], seed=sum(map(ord, pid)))
            print('built', pid)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:])
