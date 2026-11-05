"""Build each painting's prepared "Bring to Life" animation assets.

Input: a list of anchors in painting pixel space (1600×1200, y down) describing what is actually
in that painting, plus "protect" rectangles (faces / deities) that must never move or glow.
Output (in the painting's folder):
  fx.png      800×600  R = emitter strength, G = phase, B = kind (flame / bulb / star / glow)
  motion.png  400×300  R = foliage & garland sway, G = water ripple, B = lantern swing (0 pivot→1 tip)
  anim.json   3D effects that emerge from the canvas (fireworks, sparklers, birds, petals, embers,
              divine dust) and rotating halos — all in painting uv (u→right, v→down)

Anchor kinds (tuples):
  ('flame', x, y, h)                 diya / lamp flame centred at x,y, flame height h
  ('bulb', x, y, r, phase)           decorative light; phase 0..1 (chase order along a string)
  ('star', x, y, r)                  twinkle
  ('glow', x, y, r)                  slow divine/ambient breathing light
  ('firework', x, y, r, color)       bursts that fly out of the canvas
  ('sway', x0, y0, x1, y1)           leaves / garlands / fabric gently moving
  ('water', x0, y0, x1, y1)          ripple
  ('swing', x, y_pivot, w, h)        hanging lantern pendulum (pivot at top centre)
  ('halo', cx, cy, r0, r1, speed)    rotate the painted ring between radii (px) at speed rad/s
  ('birds', cx, cy, w, h)            tree: birds fly out of it
  ('petals', cx, cy, r, [colors])    flowers: petals float out of the canvas
  ('dust', cx, cy, r, color)         golden particles rising / drifting outward
  ('sparkler', cx, cy, r)            fuljhadi: circular trail + sparks
  ('ember', x, y)                    sparks rising from a flame (also derived from flames)
"""
import json, os, random
import numpy as np, cv2

W, H = 1600, 1200
KIND = {'flame': 0.15, 'bulb': 0.45, 'star': 0.70, 'glow': 0.92}


def _blob(strength, phase, kind, cx, cy, rx, ry, val, ph, scale):
    """Accumulate a soft elliptical emitter into the maps (max-composited)."""
    h, w = strength.shape
    x0, x1 = int(max(0, (cx - 2.2 * rx) * scale)), int(min(w, (cx + 2.2 * rx) * scale + 1))
    y0, y1 = int(max(0, (cy - 2.2 * ry) * scale)), int(min(h, (cy + 2.2 * ry) * scale + 1))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d2 = ((xx / scale - cx) / max(rx, 1e-3)) ** 2 + ((yy / scale - cy) / max(ry, 1e-3)) ** 2
    s = np.exp(-d2 * 1.6) * val
    sub = strength[y0:y1, x0:x1]
    m = s > sub
    sub[m] = s[m]
    phase[y0:y1, x0:x1][m] = ph
    kind[y0:y1, x0:x1][m] = KIND_VAL
    # (KIND_VAL injected by caller via global for speed)


def build(out_dir, anchors, protect=(), seed=0):
    global KIND_VAL
    rng = random.Random(seed)
    os.makedirs(out_dir, exist_ok=True)
    fs = 0.5  # fx map is half resolution (800×600)
    st = np.zeros((600, 800), np.float32); ph = np.zeros_like(st); kd = np.zeros_like(st)
    ms = 0.25  # motion map quarter resolution (400×300)
    mo = np.zeros((300, 400, 3), np.float32)
    anim = {'version': 1, 'fireworks': [], 'sparklers': [], 'birds': [], 'petals': [], 'embers': [], 'dust': [], 'halos': []}
    flames = []

    def emit(kind, cx, cy, rx, ry, val, phase):
        global KIND_VAL
        KIND_VAL = KIND[kind]
        _blob(st, ph, kd, cx, cy, rx, ry, val, phase, fs)

    def rect_soft(ch, x0, y0, x1, y1, val=1.0, feather=18):
        a = np.zeros((300, 400), np.float32)
        cv2.rectangle(a, (int(x0 * ms), int(y0 * ms)), (int(x1 * ms), int(y1 * ms)), 1.0, -1)
        a = cv2.GaussianBlur(a, (0, 0), max(1, feather * ms))
        mo[..., ch] = np.maximum(mo[..., ch], a * val)

    for a in anchors:
        k = a[0]
        if k == 'flame':
            _, x, y, h = a[:4]
            emit('flame', x, y, max(3, h * 0.42), max(4, h * 0.7), 1.0, rng.random())
            flames.append((x, y, h))
        elif k == 'bulb':
            _, x, y, r = a[:4]
            emit('bulb', x, y, max(3, r), max(3, r), 1.0, a[4] if len(a) > 4 else rng.random())
        elif k == 'star':
            _, x, y, r = a[:4]
            emit('star', x, y, max(2.5, r), max(2.5, r), 0.9, rng.random())
        elif k == 'glow':
            _, x, y, r = a[:4]
            emit('glow', x, y, r, r, 0.8, rng.random())
        elif k == 'firework':
            _, x, y, r = a[:4]
            color = a[4] if len(a) > 4 else '#ffcf5a'
            anim['fireworks'].append({'u': x / W, 'v': y / H, 'r': r / W, 'color': color, 'period': round(rng.uniform(2.6, 4.2), 2)})
            emit('star', x, y, r * 0.18, r * 0.18, 0.7, rng.random())
        elif k == 'sway':
            rect_soft(0, *a[1:5], val=a[5] if len(a) > 5 else 1.0)
        elif k == 'water':
            rect_soft(1, *a[1:5], val=1.0, feather=10)
        elif k == 'swing':
            _, x, yp, w, h = a[:5]
            g = np.zeros((300, 400), np.float32)
            x0, x1 = int((x - w / 2) * ms), int((x + w / 2) * ms)
            y0, y1 = int(yp * ms), int((yp + h) * ms)
            for yy in range(max(0, y0), min(300, y1)):
                g[yy, max(0, x0):min(400, x1)] = (yy - y0) / max(1, y1 - y0)
            g = cv2.GaussianBlur(g, (0, 0), 2)
            mo[..., 2] = np.maximum(mo[..., 2], g)
        elif k == 'halo':
            _, cx, cy, r0, r1 = a[:5]
            anim['halos'].append({'u': cx / W, 'v': cy / H, 'r0': r0 / H, 'r1': r1 / H, 'speed': a[5] if len(a) > 5 else 0.22})
        elif k == 'rays':   # rotating light rays behind a deity, from radius r0 outward
            _, cx, cy, r0, r1 = a[:5]
            anim['halos'].append({'u': cx / W, 'v': cy / H, 'r0': -r0 / H, 'r1': r1 / H, 'speed': a[5] if len(a) > 5 else 0.3})
        elif k == 'birds':
            _, cx, cy, w, h = a[:5]
            anim['birds'].append({'u': cx / W, 'v': cy / H, 'w': w / W, 'h': h / H, 'period': round(rng.uniform(2.8, 4.5), 2)})
            rect_soft(0, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, val=0.8, feather=30)
        elif k == 'petals':
            _, cx, cy, r = a[:4]
            anim['petals'].append({'u': cx / W, 'v': cy / H, 'r': r / H, 'colors': a[4] if len(a) > 4 else ['#f28c0f', '#ffc93c', '#d62828'], 'period': round(rng.uniform(1.4, 2.6), 2)})
        elif k == 'dust':
            _, cx, cy, r = a[:4]
            anim['dust'].append({'u': cx / W, 'v': cy / H, 'r': r / H, 'color': a[4] if len(a) > 4 else '#ffd77a', 'period': 0.18})
        elif k == 'sparkler':
            _, cx, cy, r = a[:4]
            anim['sparklers'].append({'u': cx / W, 'v': cy / H, 'r': r / W, 'squash': W / H, 'rps': 1.2, 'phase': rng.random()})
        elif k == 'ember':
            anim['embers'].append({'u': a[1] / W, 'v': a[2] / H, 'period': 0.7})

    # embers rise from the most prominent flames (cap for performance)
    for x, y, h in sorted(flames, key=lambda f: -f[2])[:10]:
        if h >= 14:
            anim['embers'].append({'u': x / W, 'v': (y - h * 0.5) / H, 'period': round(0.5 + 30 / h, 2)})

    # never touch faces / deities: zero every effect inside protected rectangles
    for (x0, y0, x1, y1) in protect:
        st[int(y0 * fs):int(y1 * fs), int(x0 * fs):int(x1 * fs)] = 0
        mo[int(y0 * ms):int(y1 * ms), int(x0 * ms):int(x1 * ms)] = 0
    anim['protect'] = [[x0 / W, y0 / H, x1 / W, y1 / H] for (x0, y0, x1, y1) in protect]
    # particle emitters must also start outside protected areas (never spawn on a person or deity)
    pr = anim['protect']
    def clear(e):
        return not any(x0 <= e['u'] <= x1 and y0 <= e['v'] <= y1 for (x0, y0, x1, y1) in pr)
    for k in ('fireworks', 'sparklers', 'birds', 'petals', 'embers'):
        anim[k] = [e for e in anim[k] if clear(e)]

    fx = np.dstack([np.clip(st, 0, 1) * 255, ph * 255, kd * 255]).astype(np.uint8)
    cv2.imwrite(os.path.join(out_dir, 'fx.png'), cv2.cvtColor(fx, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    cv2.imwrite(os.path.join(out_dir, 'motion.png'), cv2.cvtColor((np.clip(mo, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    anim = {k: v for k, v in anim.items() if v or k == 'version'}
    json.dump(anim, open(os.path.join(out_dir, 'anim.json'), 'w'), separators=(',', ':'))
    return anim


KIND_VAL = 0.0
