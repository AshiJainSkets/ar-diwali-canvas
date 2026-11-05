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




# ---------------------------------------------------------------------------------------------
# GIFs made from a painting that is already in the app (e.g. Skets Studio). The GIF was generated
# from the app's own canvas image, so it is registered to it (sub-pixel offset measured once).
# People are protected:
#   • the main person is cut out precisely (`<id>-person.png`, GrabCut + head region, checked by eye)
#     and is ALWAYS the original painting — nothing from the GIF is used on them (the Skets 2 GIF,
#     for example, adds lights onto the saree that are not in the painting; those are rejected);
#   • inside the other protected rectangles (small background figures) the GIF is used only where
#     the original painting already has a light (string lights / diyas passing behind someone).
EXISTING = {
    # id: (gif, gif→canvas offset in GIF px (dx, dy) measured by phase correlation)
    'skets-2': ('skets-2.gif', (-0.51, 0.01)),
    'skets-3': ('skets-3.gif', (-0.50, 0.01)),
}


def light_mask(bgr):
    """Pixels of the ORIGINAL painting that are light sources: very bright, warm or white, small,
    strongly brighter than their surroundings (fabric folds and highlights are large / low contrast)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    Hh, S, V = hsv[..., 0].astype(np.int32), hsv[..., 1].astype(np.int32), hsv[..., 2].astype(np.float32)
    local = V - cv2.GaussianBlur(V, (0, 0), 6)
    m = ((V > 235) & (local > 30) & (((Hh >= 4) & (Hh <= 40)) | (S < 60))).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    small = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] <= 150 and st[i, 2] <= 30 and st[i, 3] <= 30:
            small[lab == i] = 1
    small = cv2.dilate(small, np.ones((7, 7), np.uint8))
    return cv2.GaussianBlur(small.astype(np.float32), (0, 0), 2)


def attach_gif(pid):
    import imported
    gif, (dx, dy) = EXISTING[pid]
    d = os.path.join(OUT, pid)
    albedo = cv2.imread(os.path.join(d, 'albedo.jpg')).astype(np.float32)          # 1600×1200 BGR
    frames = [np.asarray(f.convert('RGB'))[..., ::-1].astype(np.float32) for f in ImageSequence.Iterator(Image.open(os.path.join(SRC, gif)))]
    gh, gw = frames[0].shape[:2]
    F0 = frames[0]
    # real motion only (GIF re-dithering flickers everywhere; blur before measuring)
    B0 = cv2.GaussianBlur(F0, (0, 0), 1.2)
    var = np.max([np.abs(cv2.GaussianBlur(f, (0, 0), 1.2) - B0).max(axis=2) for f in frames], axis=0)
    mot = cv2.GaussianBlur(cv2.dilate((var > 10).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.0)[..., None]
    s = W / gw
    M = np.float32([[s, 0, (0.5 + dx) * s - 0.5], [0, H / gh, (0.5 + dy) * (H / gh) - 0.5]])
    up = lambda a: cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    # protection multiplier on the canvas
    person = (cv2.imread(os.path.join(SRC, f'{pid}-person.png'), cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
    person = cv2.GaussianBlur(cv2.dilate(person, np.ones((17, 17), np.uint8)).astype(np.float32), (0, 0), 4)
    P = np.zeros((H, W), np.float32)
    for (x0, y0, x1, y1) in imported.PLANS[pid]['protect']:
        cv2.rectangle(P, (int(x0), int(y0)), (int(x1), int(y1)), 1.0, -1)
    P = cv2.GaussianBlur(P, (0, 0), 6)
    allow = light_mask(albedo.astype(np.uint8))
    mult = ((1 - P) + P * allow) * (1 - np.clip(person * 1.15, 0, 1))
    mult = mult[..., None]
    tmp = tempfile.mkdtemp()
    try:
        n, L = 0, len(frames)
        deltas = [up((f - F0) * mot) * mult for f in frames]
        for i in range(L):
            a, b = deltas[i], deltas[(i + 1) % L]
            for k in range(SUB):
                t = k / SUB
                fr = np.clip(albedo + a * (1 - t) + b * t, 0, 255).astype(np.uint8)
                cv2.imwrite(os.path.join(tmp, f'{n:04d}.png'), cv2.resize(fr, (VW, VH), interpolation=cv2.INTER_AREA))
                n += 1
        out = os.path.join(d, 'animated.mp4')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%04d.png'),
                        '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                        '-c:v', 'libx264', '-profile:v', 'main', '-preset', 'slow', '-crf', '21', '-g', str(FPS),
                        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                        '-movflags', '+faststart', '-an', out], check=True)
    finally:
        shutil.rmtree(tmp)
    fxmaps.build(d, [], (), seed=0)   # the painting's own GIF animation replaces the procedural effects
    print(f'{pid}: GIF video {n} frames, {os.path.getsize(out)/1e6:.2f} MB')
    return mult[..., 0]


if __name__ == '__main__':
    args = set(sys.argv[1:])
    for pid in [p for p in EXISTING if not args or p in args]:
        attach_gif(pid)
    rest = {i[0] for i in ITEMS} & args if args else None
    if not args or rest:
        main(rest)
