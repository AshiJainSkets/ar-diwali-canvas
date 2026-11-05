"""Animation definitions for imported artwork (Skets Studio paintings and future AI paintings).

For each painting:
  • lights & flames are detected automatically (bright, warm, small, locally-contrasting blobs);
    tall warm blobs become flickering flames, small ones become blinking bulbs whose phase runs
    along the image so light strings "chase";
  • the hand-checked plan below adds what detection can't know (fireworks, trees with birds,
    garlands that sway, petals, water) and PROTECTS every person: no effect is ever applied inside
    a protected rectangle, so faces, bodies and clothing never move, blink or glow.

usage: python tools/paintings/imported.py [ids...]   (writes fx.png / motion.png / anim.json)
"""
import os, sys, json
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fxmaps
from animations import sparkle

OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'public', 'paintings'))
MARIGOLD = ['#f28c0f', '#ffc93c', '#e8590c']

PLANS = {
    'skets-1': dict(
        add=[('firework', 580, 210, 150, '#ff6fd0'), ('firework', 1040, 175, 200, '#ffcf5a'), ('firework', 815, 330, 90, '#7ff0e0'),
             ('birds', 110, 870, 300, 260), ('birds', 560, 850, 320, 260), ('birds', 1080, 850, 320, 260), ('birds', 1470, 880, 280, 240)],
        protect=[]),
    'skets-2': dict(
        add=[('firework', 750, 65, 85, '#ffd27a'), ('firework', 905, 110, 50, '#ff7ab8'), ('firework', 830, 150, 38, '#ffcf5a'),
             ('sway', 0, 250, 560, 720, 0.7), ('sway', 1080, 250, 1600, 720, 0.7), ('sway', 550, 730, 760, 790, 0.6),
             ('petals', 250, 450, 130, MARIGOLD), ('petals', 1350, 430, 130, MARIGOLD)],
        protect=[(760, 420, 1150, 1200)]),
    'skets-3': dict(
        add=[('sway', 25, 140, 75, 390, 0.6), ('sway', 230, 150, 290, 390, 0.6), ('sway', 300, 140, 360, 400, 0.6), ('sway', 380, 150, 590, 370, 0.5),
             ('sway', 820, 220, 900, 370, 0.6), ('sway', 940, 220, 1060, 370, 0.6), ('sway', 1080, 240, 1160, 360, 0.6),
             ('petals', 1400, 1000, 110, ['#b5179e', '#f28c0f', '#ffc93c', '#2a9d8f'])] + sparkle(1400, 1000, 180, 70, 26, 33),
        protect=[(480, 50, 1010, 1200), (90, 280, 535, 470), (455, 290, 570, 410), (1015, 395, 1155, 505), (1150, 330, 1600, 405)]),
    'skets-4': dict(
        add=[('sway', 0, 400, 330, 540, 0.6), ('sway', 1270, 400, 1600, 540, 0.6),
             ('petals', 105, 1030, 90, MARIGOLD), ('petals', 1515, 1030, 90, MARIGOLD), ('dust', 800, 300, 330, '#ffd77a')],
        protect=[(0, 595, 1600, 1000), (680, 80, 930, 215)]),   # crowd + UDAAN logo
    'skets-5': dict(
        add=[('sway', 90, 180, 1520, 350, 0.55), ('sway', 0, 0, 110, 520, 0.6), ('sway', 1500, 0, 1600, 520, 0.6),
             ('petals', 300, 1020, 80, MARIGOLD), ('petals', 800, 1020, 80, MARIGOLD), ('petals', 1300, 1020, 80, MARIGOLD),
             ('water', 0, 1035, 1600, 1200)] + sparkle(800, 420, 700, 70, 40, 55, r=4),
        protect=[(0, 455, 1600, 985), (545, 345, 785, 470)]),   # people + UDAAN logo
    'skets-6': dict(
        add=[('sway', 165, 0, 285, 620, 0.6), ('sway', 1035, 0, 1100, 420, 0.6), ('petals', 110, 780, 90, MARIGOLD), ('petals', 1460, 830, 80, MARIGOLD)],
        protect=[(365, 375, 1405, 1200), (300, 40, 1000, 140)]),   # team + SKETStudio/AIA26 text
    # Traditional: no GIF supplied for this one, so it gets a hand-placed plan (the source is very
    # small, so automatic light detection is switched off — it mistakes the bright wall for lights).
    'trad-ganesh-puja': dict(
        detect=False,
        add=[('bulb', x, 228 - 30 * (1 - ((x - 390) / 120) ** 2), 5, i / 7) for i, x in enumerate(range(285, 500, 30))]
            + [('bulb', x, 296 + 10 * (1 - ((x - 715) / 75) ** 2), 4, i / 7) for i, x in enumerate(range(640, 800, 22))]
            + [('flame', 673, 775, 20), ('flame', 727, 840, 22), ('flame', 660, 893, 20),
               ('flame', 513, 965, 13), ('flame', 593, 978, 13),   # h < 14: no embers rising past Ganesha
               ('glow', 690, 870, 110),
               ('sway', 560, 100, 940, 290, 0.6), ('sway', 255, 190, 530, 430, 0.6), ('sway', 945, 160, 1090, 330, 0.4),
               ('petals', 985, 985, 80, MARIGOLD), ('petals', 450, 1030, 90, MARIGOLD)]
            + sparkle(780, 950, 90, 48, 18, 71, r=4),
        protect=[(285, 430, 625, 905), (855, 330, 1190, 955)]),   # Lord Ganesha + family
}


def inside(x, y, rects, pad=6):
    return any(x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad for (x0, y0, x1, y1) in rects)


def detect_lights(img, protect, max_n=420):
    """Find decorative lights and flames: bright, warm-white, small and brighter than surroundings.

    Saturated orange (marigolds, saris) is excluded — only light sources qualify. Shape decides
    behaviour: compact teardrops flicker like flames, small round points blink like bulbs, and tall
    thin strips (lit louvres, windows) breathe softly instead of flickering.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    Hh, S, V = hsv[..., 0].astype(np.int32), hsv[..., 1].astype(np.int32), hsv[..., 2].astype(np.float32)
    local = V - cv2.GaussianBlur(V, (0, 0), 7)
    warm = ((Hh >= 4) & (Hh <= 40)) | (S < 60)
    mask = ((V > 212) & (local > 26) & warm & (S < 165)).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(mask, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 3 or area > 900 or w > 70 or h > 120:
            continue
        cx, cy = cent[i]
        if inside(cx, cy, protect):
            continue
        if h > 2.6 * w and h > 14:
            out.append(('glow', cx, cy, max(8.0, h * 0.6)))
        elif area >= 18 and 1.1 * w <= h <= 2.6 * w:
            out.append(('flame', cx, cy, max(10.0, h * 1.6)))
        else:
            out.append(('bulb', cx, cy, max(3.0, np.sqrt(area) * 0.9), ((cx / 1600) * 2.0 + cy / 1200) % 1.0))
    out.sort(key=lambda a: -a[3])
    return out[:max_n]


def build(pid):
    d = os.path.join(OUT, pid)
    if os.path.exists(os.path.join(d, 'animated.mp4')):   # its own GIF animation is used instead
        return [], fxmaps.build(d, [], (), seed=0)
    img = cv2.imread(os.path.join(d, 'albedo.jpg'))
    plan = PLANS.get(pid, dict(add=[], protect=[]))
    if plan.get('faces', True):  # also auto-protect any detected face (expanded) — belt and braces
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cc = cv2.CascadeClassifier(os.path.join(getattr(cv2, 'data', None) and cv2.data.haarcascades or '', 'haarcascade_frontalface_default.xml'))
        faces = [] if cc.empty() else cc.detectMultiScale(g, 1.1, 5, minSize=(18, 18))  # optional; manual rects always apply
        for (x, y, w, h) in faces:
            plan['protect'] = list(plan['protect']) + [(x - w * 0.4, y - h * 0.5, x + w * 1.4, y + h * 1.6)]
    lights = detect_lights(img, plan['protect']) if plan.get('detect', True) else []
    anchors = lights + plan['add']
    anim = fxmaps.build(d, anchors, plan['protect'], seed=sum(map(ord, pid)))
    return lights, anim


if __name__ == '__main__':
    ids = sys.argv[1:] or list(PLANS)
    for pid in ids:
        lights, anim = build(pid)
        kinds = {}
        for a in lights:
            kinds[a[0]] = kinds.get(a[0], 0) + 1
        print(pid, 'detected', kinds, {k: len(v) for k, v in anim.items() if isinstance(v, list)})
