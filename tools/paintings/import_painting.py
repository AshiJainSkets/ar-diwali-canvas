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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image'); ap.add_argument('--id', required=True); ap.add_argument('--category', required=True)
    ap.add_argument('--title', required=True); ap.add_argument('--description', default=''); ap.add_argument('--medium', default='Acrylic on canvas')
    ap.add_argument('--painterly', action='store_true', help='apply the brush-stroke filter (for flat digital art)')
    a = ap.parse_args()

    cat_path = os.path.join(OUT, 'catalog.json')
    catalog = json.load(open(cat_path))
    if a.category not in {c['id'] for c in catalog['categories']}:
        sys.exit(f'Unknown category {a.category!r}. Options: ' + ', '.join(c['id'] for c in catalog['categories']))

    img = cv2.imread(a.image, cv2.IMREAD_COLOR)
    if img is None: sys.exit('Could not read image')
    h, w = img.shape[:2]
    if w / h > 4 / 3: nw = int(h * 4 / 3); img = img[:, (w - nw) // 2:(w - nw) // 2 + nw]
    else: nh = int(w * 3 / 4); img = img[(h - nh) // 2:(h - nh) // 2 + nh]
    if img.shape[1] < 1200: print('warning: source is small (<1200 px wide); it may look soft on a 4 ft canvas')
    img = cv2.resize(img, (1600, 1200), interpolation=cv2.INTER_AREA if img.shape[1] > 1600 else cv2.INTER_CUBIC)
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
    json.dump(catalog, open(cat_path, 'w'), indent=1, ensure_ascii=False)
    print('added', a.id, '→', d)


if __name__ == '__main__':
    main()
