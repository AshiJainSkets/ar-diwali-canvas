"""Import paintings that come with their own animated version (GIF) for "Bring to Life".

For each painting:
  • the still image is fitted to the 4 × 3 ft canvas exactly like import_painting.py (whole artwork
    kept, festive mat around it) → albedo / height / preview / thumb;
  • the GIF becomes `animated.mp4`, laid out on the same canvas. Only what actually moves in the GIF
    (lights, flames, fireworks, sparklers) is taken from it: every video frame is
        still + (gif_frame − gif_frame_0)
    so frame 0 is pixel-identical to the static painting (no jump when it starts or stops), and
    everything that does not move — faces, people, clothing — stays the original still image;
  • frames are cross-blended from the GIF's 6.25 fps to 25 fps so the motion is smooth, and the loop
    wraps seamlessly;
  • a painting without a GIF gets the standard procedural animation (imported.py plan).

usage: python tools/paintings/import_animated.py
"""
import json, os, subprocess, sys, tempfile, shutil
import numpy as np, cv2
from PIL import Image, ImageSequence

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from import_painting import fit_to_canvas, OUT  # noqa: E402
from paintify import bake_preview               # noqa: E402
import fxmaps                                    # noqa: E402

SRC = os.path.join(HERE, 'source-animated')
W, H = 1600, 1200
VW, VH, FPS, SUB = 1280, 960, 25, 4   # video size, output fps, blended sub-frames per GIF frame

# (id, source name, title, description, trim white paper border)
ITEMS = [
    ('trad-ganesh-puja', 'ganesh-puja', 'Family Ganesh Puja at Home',
     'A family prays before Lord Ganesha among glowing diyas, marigolds and a festive rangoli.', True),
    ('trad-kids-rangoli', 'kids-rangoli', 'Rangoli & Fuljhadi on the Doorstep',
     'A girl lights diyas around a rangoli while her brother twirls a fuljhadi under fireworks.', True),
    ('trad-family-home', 'family-home', 'Festival of Lights at Home',
     'Family and neighbours gather at a home strung with lights as fireworks bloom overhead.', False),
    ('trad-lighting-diyas', 'lighting-diyas', 'Lighting the Evening Diyas',
     'A mother and her daughters light diyas on the terrace at dusk.', False),
    ('trad-glowing-diya', 'glowing-diya', 'The Radiant Diya',
     'A single clay diya glowing against a sky of festive colour.', False),
    ('trad-diyas-by-pond', 'diyas-pond', 'Diyas by the Pond',
     'A family arranges a platter of diyas and flowers beside a lamp-lit pond.', False),
]
MEDIUM = 'Animated painting'


def rgb2bgr(a):
    return np.ascontiguousarray(a[..., ::-1])


def trim_box(img, thr=236):
    """Bounding box of the painting inside a white paper border (RGB array)."""
    nonwhite = (img.min(axis=2) < thr)
    rows, cols = np.where(nonwhite.mean(axis=1) > 0.5)[0], np.where(nonwhite.mean(axis=0) > 0.5)[0]
    y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    inset = 3  # drop the soft paper edge
    return x0 + inset, y0 + inset, x1 - inset, y1 - inset


def art_rect(w, h, margin=46):
    """Where fit_to_canvas('contain') places the artwork (must match import_painting.fit_to_canvas)."""
    s2 = min((W - 2 * margin) / w, (H - 2 * margin) / h)
    fw, fh = int(w * s2), int(h * s2)
    return (W - fw) // 2, (H - fh) // 2, fw, fh, s2


def save_static(d, img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    detail = gray - cv2.GaussianBlur(gray, (0, 0), 3)
    height = 0.5 + 2.2 * detail + 0.25 * (cv2.GaussianBlur(gray, (0, 0), 8) - 0.5)
    height = np.clip(cv2.GaussianBlur(height, (0, 0), 0.8), 0, 1)
    cv2.imwrite(os.path.join(d, 'albedo.jpg'), img, [cv2.IMWRITE_JPEG_QUALITY, 90, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    cv2.imwrite(os.path.join(d, 'height.jpg'), cv2.resize((height * 255).astype(np.uint8), (800, 600), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
    prev = bake_preview(img.astype(np.float32), height, 1200)
    cv2.imwrite(os.path.join(d, 'preview.jpg'), prev, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    cv2.imwrite(os.path.join(d, 'thumb.jpg'), cv2.resize(prev, (480, 360), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])


def build_video(d, still_rgb, gif_path, box, canvas_bgr):
    frames = [np.asarray(f.convert('RGB')).astype(np.float32) for f in ImageSequence.Iterator(Image.open(gif_path))]
    if box:
        x0, y0, x1, y1 = box
        frames = [f[y0:y1, x0:x1] for f in frames]
    assert frames[0].shape == still_rgb.shape, (frames[0].shape, still_rgb.shape)
    P = still_rgb.astype(np.float32)
    F0 = frames[0]
    # motion mask: only pixels the GIF actually animates (soft edge, kills dithering residue)
    var = np.max([np.abs(f - F0).max(axis=2) for f in frames], axis=0)
    m = (var > 6).astype(np.float32)
    m = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 2)[..., None]
    h, w = P.shape[:2]
    fx, fy, fw, fh, s2 = art_rect(w, h)
    layers = [np.clip(P + m * (f - F0), 0, 255) for f in frames]
    tmp = tempfile.mkdtemp()
    try:
        n = 0
        L = len(layers)
        for i in range(L):
            a, b = layers[i], layers[(i + 1) % L]   # wraps: seamless loop
            for k in range(SUB):
                t = k / SUB
                fr = a * (1 - t) + b * t
                art = cv2.resize(rgb2bgr(fr), (fw, fh), interpolation=cv2.INTER_CUBIC)
                c = canvas_bgr.copy()
                c[fy:fy + fh, fx:fx + fw] = np.clip(art, 0, 255).astype(np.uint8)
                cv2.imwrite(os.path.join(tmp, f'{n:04d}.png'), cv2.resize(c, (VW, VH), interpolation=cv2.INTER_AREA))
                n += 1
        out = os.path.join(d, 'animated.mp4')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%04d.png'),
                        '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                        '-c:v', 'libx264', '-profile:v', 'main', '-preset', 'slow', '-crf', '21', '-g', str(FPS),
                        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                        '-movflags', '+faststart', '-an', out], check=True)
        return n, os.path.getsize(out), float((m > 0.5).mean())
    finally:
        shutil.rmtree(tmp)


def main(only=None):
    import imported
    cat_path = os.path.join(OUT, 'catalog.json')
    catalog = json.load(open(cat_path))
    for pid, name, title, desc, trim in ITEMS:
        if only and pid not in only:
            continue
        d = os.path.join(OUT, pid); os.makedirs(d, exist_ok=True)
        still = np.asarray(Image.open(os.path.join(SRC, name + '.png')).convert('RGB'))
        box = trim_box(still) if trim else None
        if box:
            x0, y0, x1, y1 = box; still = still[y0:y1, x0:x1]
        canvas = fit_to_canvas(rgb2bgr(still), 'contain')
        save_static(d, canvas)
        gif = os.path.join(SRC, name + '.gif')
        if os.path.exists(gif):
            n, size, moving = build_video(d, still, gif, box, canvas)
            fxmaps.build(d, [], (), seed=0)   # no extra procedural effects: the painting's own animation plays
            print(f'{pid}: video {n} frames, {size/1e6:.2f} MB, animated area {moving*100:.1f}% of artwork')
        else:
            if os.path.exists(os.path.join(d, 'animated.mp4')): os.remove(os.path.join(d, 'animated.mp4'))
            lights, anim = imported.build(pid)
            print(f'{pid}: procedural animation, {len(lights)} lights,', {k: len(v) for k, v in anim.items() if isinstance(v, list)})
        entry = {'id': pid, 'category': 'traditional', 'title': title, 'description': desc, 'medium': MEDIUM,
                 **{k: f'/paintings/{pid}/{k}.jpg' for k in ('albedo', 'height', 'preview', 'thumb')}}
        ids = [p['id'] for p in catalog['paintings']]
        if pid in ids: catalog['paintings'][ids.index(pid)] = entry
        else: catalog['paintings'].append(entry)
    json.dump(catalog, open(cat_path, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
