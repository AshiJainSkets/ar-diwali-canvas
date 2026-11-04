"""Build the sample gallery: SVG compositions → raster → painterly pass → catalog.json.

usage: python tools/paintings/build_gallery.py            (all)
       python tools/paintings/build_gallery.py diya-1 ... (subset)
Requires: python playwright (chromium), opencv-python, numpy.
"""
import os, sys, json, subprocess, tempfile
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compositions import PAINTINGS, CATEGORIES  # noqa: E402
from paintify import paintify  # noqa: E402

OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'public', 'paintings'))


def job(pid, raw_dir):
    paintify(os.path.join(raw_dir, pid + '.png'), os.path.join(OUT, pid), seed=sum(map(ord, pid)))
    return pid


def main():
    only = sys.argv[1:]
    raw = tempfile.mkdtemp(prefix='ardc-raw-')
    subprocess.run([sys.executable, os.path.join(HERE, 'render_svgs.py'), raw, *only], check=True)
    ids = [p[0] for p in PAINTINGS if not only or p[0] in only]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2))) as ex:
        for pid in ex.map(job, ids, [raw] * len(ids)):
            print('painted', pid)
    catalog = {
        'version': 1,
        'canvasAspect': '4:3',
        'categories': [{'id': c, 'name': n, 'description': d} for c, n, d in CATEGORIES],
        'paintings': [{
            'id': pid, 'category': cat, 'title': title, 'description': desc, 'medium': med,
            'albedo': f'/paintings/{pid}/albedo.jpg', 'height': f'/paintings/{pid}/height.jpg',
            'preview': f'/paintings/{pid}/preview.jpg', 'thumb': f'/paintings/{pid}/thumb.jpg',
        } for pid, cat, title, desc, med, _ in PAINTINGS],
    }
    with open(os.path.join(OUT, 'catalog.json'), 'w') as fh:
        json.dump(catalog, fh, indent=1, ensure_ascii=False)
    print('catalog written:', len(catalog['paintings']), 'paintings')


if __name__ == '__main__':
    main()
