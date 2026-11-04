"""Add your own artwork (a real scanned/photographed painting or licensed image) to the gallery.

usage:
  python tools/paintings/import_painting.py path/to/art.jpg --id my-diwali-1 --category gold \
      --title "Lakshmi Puja" --description "Commissioned acrylic, 2026" --medium "Acrylic on canvas" [--painterly]

What it does
  • centre-crops to 4:3 landscape and resizes to 1600×1200 (albedo.jpg)
  • derives an impasto height map from the image's fine detail (or from brush strokes with --painterly)
  • bakes preview.jpg / thumb.jpg with canvas lighting
  • appends / replaces the entry in public/paintings/catalog.json
Use a high-resolution, evenly lit, glare-free photo or scan for real paintings.
"""
import argparse, json, os, sys
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paintify import bake_preview, paintify  # noqa: E402

OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'public', 'paintings'))


def fit_to_canvas(img, mode='auto'):
    """Return a 1600×1200 (4:3) image. 'contain' keeps the whole artwork (no one is cropped out)
    and fills the remaining canvas with a blurred, darkened extension of the same image, a soft
    drop shadow and a thin gold frame line, so it reads as a deliberate mat, not empty bars."""
    W, H = 1600, 1200
    h, w = img.shape[:2]
    ar = w / h
    if mode == 'auto':
        mode = 'cover' if abs(ar / (4 / 3) - 1) < 0.06 else 'contain'
    if mode == 'cover':
        if ar > 4 / 3: nw = int(h * 4 / 3); img = img[:, (w - nw) // 2:(w - nw) // 2 + nw]
        else: nh = int(w * 3 / 4); img = img[(h - nh) // 2:(h - nh) // 2 + nh]
        if img.shape[1] < 1200: print('warning: source is small (<1200 px wide); it may look soft on a 4 ft canvas')
        return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA if img.shape[1] > W else cv2.INTER_CUBIC)
    # --- contain on a festive mat ---
    s = max(W / w, H / h)
    bg = cv2.resize(img, (int(w * s) + 2, int(h * s) + 2), interpolation=cv2.INTER_AREA)
    y0, x0 = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2
    bg = bg[y0:y0 + H, x0:x0 + W].astype(np.float32)
    bg = cv2.GaussianBlur(bg, (0, 0), 45) * 0.42 * np.array([0.85, 0.95, 1.12], np.float32)  # darker, warmer (BGR)
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    bg *= np.clip(vig, 0.4, 1)[..., None]
    rng = np.random.default_rng(7)                      # a few warm bokeh lights on the mat
    glow = np.zeros((H, W), np.float32)
    for _ in range(40):
        cv2.circle(glow, (int(rng.uniform(0, W)), int(rng.uniform(0, H))), int(rng.uniform(4, 16)), float(rng.uniform(0.3, 1)), -1)
    glow = cv2.GaussianBlur(glow, (0, 0), 6)
    bg += glow[..., None] * np.array([60, 150, 255], np.float32) * 0.35
    margin = 46
    s2 = min((W - 2 * margin) / w, (H - 2 * margin) / h)
    fw, fh = int(w * s2), int(h * s2)
    fx, fy = (W - fw) // 2, (H - fh) // 2
    shadow = np.zeros((H, W), np.float32)
    cv2.rectangle(shadow, (fx + 6, fy + 12), (fx + fw + 6, fy + fh + 12), 1.0, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 18)
    bg *= (1 - 0.6 * shadow)[..., None]
    pad = 7                                             # gold frame line
    cv2.rectangle(bg, (fx - pad, fy - pad), (fx + fw + pad - 1, fy + fh + pad - 1), (74, 162, 214), -1)
    cv2.rectangle(bg, (fx - 3, fy - 3), (fx + fw + 2, fy + fh + 2), (40, 90, 130), -1)
    art = cv2.resize(img, (fw, fh), interpolation=cv2.INTER_AREA if s2 < 1 else cv2.INTER_CUBIC)
    bg[fy:fy + fh, fx:fx + fw] = art
    return np.clip(bg, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image'); ap.add_argument('--id', required=True); ap.add_argument('--category', required=True)
    ap.add_argument('--title', required=True); ap.add_argument('--description', default=''); ap.add_argument('--medium', default='Acrylic on canvas')
    ap.add_argument('--painterly', action='store_true', help='apply the brush-stroke filter (for flat digital art)')
    ap.add_argument('--fit', choices=['auto', 'cover', 'contain'], default='auto',
                    help='cover = crop to 4:3; contain = keep the whole image on a festive mat; auto = cover only if already ~4:3')
    a = ap.parse_args()

    cat_path = os.path.join(OUT, 'catalog.json')
    catalog = json.load(open(cat_path))
    if a.category not in {c['id'] for c in catalog['categories']}:
        sys.exit(f'Unknown category {a.category!r}. Options: ' + ', '.join(c['id'] for c in catalog['categories']))

    img = cv2.imread(a.image, cv2.IMREAD_COLOR)
    if img is None: sys.exit('Could not read image')
    img = fit_to_canvas(img, a.fit)
    d = os.path.join(OUT, a.id); os.makedirs(d, exist_ok=True)

    if a.painterly:
        tmp = os.path.join(d, '_src.png'); cv2.imwrite(tmp, img)
        paintify(tmp, d, seed=sum(map(ord, a.id))); os.remove(tmp)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        detail = gray - cv2.GaussianBlur(gray, (0, 0), 3)
        height = 0.5 + 2.2 * detail + 0.25 * (cv2.GaussianBlur(gray, (0, 0), 8) - 0.5)
        height = np.clip(cv2.GaussianBlur(height, (0, 0), 0.8), 0, 1)
        cv2.imwrite(os.path.join(d, 'albedo.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 88, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
        cv2.imwrite(os.path.join(d, 'height.jpg'), cv2.resize((height * 255).astype(np.uint8), (800, 600), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
        prev = bake_preview(img.astype(np.float32), height, 1200)
        cv2.imwrite(os.path.join(d, 'preview.jpg'), prev, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
        cv2.imwrite(os.path.join(d, 'thumb.jpg'), cv2.resize(prev, (480, 360), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])

    entry = {'id': a.id, 'category': a.category, 'title': a.title, 'description': a.description, 'medium': a.medium,
             'albedo': f'/paintings/{a.id}/albedo.jpg', 'height': f'/paintings/{a.id}/height.jpg',
             'preview': f'/paintings/{a.id}/preview.jpg', 'thumb': f'/paintings/{a.id}/thumb.jpg'}
    catalog['paintings'] = [p for p in catalog['paintings'] if p['id'] != a.id] + [entry]
    order = {c['id']: i for i, c in enumerate(catalog['categories'])}
    catalog['paintings'].sort(key=lambda p: order.get(p['category'], 99))  # stable: keeps order within a category
    json.dump(catalog, open(cat_path, 'w'), indent=1, ensure_ascii=False)
    print('added', a.id, '→', d)


if __name__ == '__main__':
    main()
