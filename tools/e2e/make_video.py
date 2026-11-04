"""Synthesise a phone-camera video of the physical canvas (tracking print in a frame, on a wall)
with known ground-truth geometry, for automated tracking/alignment tests.

usage: python make_video.py print.png out_dir scenario
writes out_dir/<scenario>.y4m and out_dir/<scenario>.json (per-frame canvas corners in video px)
"""
import sys, json, math
import numpy as np, cv2

W, H = 960, 540
HFOV = 62.0
fx = (W / 2) / math.tan(math.radians(HFOV / 2))
K = np.array([[fx, 0, W / 2], [0, fx, H / 2], [0, 0, 1.0]])
CW, CH = 121.92, 91.44           # canvas cm
FRAME = 5.0                      # frame moulding width cm

def rot(yaw, pitch, roll):
    y, p, r = map(math.radians, (yaw, pitch, roll))
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return Rz @ Rx @ Ry

def homography(yaw, pitch, roll, dist, ox=0, oy=0):
    # plane coords (cm) X right, Y down, centred on canvas; camera looks at the canvas centre
    R = rot(yaw, pitch, roll)
    t = np.array([ox, oy, dist])
    Hm = K @ np.column_stack([R[:, 0], R[:, 1], t])
    return Hm

def project(Hm, pts):
    p = np.column_stack([pts, np.ones(len(pts))]) @ Hm.T
    return p[:, :2] / p[:, 2:3]

def scenario(name, n):
    for i in range(n):
        s = i / max(1, n - 1)
        if name.startswith('frontal'):   yield dict(yaw=0, pitch=0, roll=0, dist=250)
        elif name.startswith('angled'):  yield dict(yaw=38, pitch=-12, roll=4, dist=220)
        elif name == 'close':   yield dict(yaw=-22, pitch=8, roll=-3, dist=135, ox=10, oy=-6)
        elif name == 'moving':
            yield dict(yaw=-32 + 64 * (0.5 - 0.5 * math.cos(math.pi * s)), pitch=6 * math.sin(2 * math.pi * s),
                       roll=3 * math.sin(4 * math.pi * s), dist=300 - 130 * s, ox=8 * math.sin(3 * s), oy=0)

def main():
    print_png, out_dir, name = sys.argv[1:4]
    n = 150 if name == 'moving' else 12
    art = cv2.imread(print_png)
    if len(sys.argv) > 4:  # marker mode: blank canvas with the plaque at x,y,w,h (cm)
        mx, my, mw, mh = map(float, sys.argv[4:8])
        ppc = 20.0
        blank = np.full((int(CH * ppc), int(CW * ppc), 3), (236, 240, 242), np.uint8)
        blank = (blank + np.random.default_rng(3).normal(0, 2.5, blank.shape)).clip(0, 255).astype(np.uint8)
        plaque = cv2.resize(art, (int(mw * ppc), int(mh * ppc)), interpolation=cv2.INTER_AREA)
        blank[int(my * ppc):int(my * ppc) + plaque.shape[0], int(mx * ppc):int(mx * ppc) + plaque.shape[1]] = plaque
        art = blank
        name = name + '_marker'
    ah, aw = art.shape[:2]
    # canvas texture (print) with a dark wooden frame around it
    px_per_cm = aw / CW
    fpx = int(FRAME * px_per_cm)
    framed = cv2.copyMakeBorder(art, fpx, fpx, fpx, fpx, cv2.BORDER_CONSTANT, value=(30, 45, 70))
    grain = (np.random.default_rng(1).random(framed.shape[:2]) * 18).astype(np.float32)
    mask = np.zeros(framed.shape[:2], np.uint8); mask[:fpx, :] = mask[-fpx:, :] = 1; mask[:, :fpx] = mask[:, -fpx:] = 1
    framed = framed.astype(np.float32); framed[mask == 1] += grain[mask == 1][:, None]
    framed = np.clip(framed, 0, 255).astype(np.uint8)
    # wall
    rng = np.random.default_rng(7)
    wall = np.full((H, W, 3), (178, 196, 214), np.float32)
    wall += cv2.GaussianBlur(rng.normal(0, 12, (H, W, 1)).astype(np.float32), (0, 0), 6)[..., None]
    # source px -> plane cm (origin at canvas centre)
    S = np.array([[1 / px_per_cm, 0, -(CW / 2 + FRAME)], [0, 1 / px_per_cm, -(CH / 2 + FRAME)], [0, 0, 1]])
    y4m = open(f'{out_dir}/{name}.y4m', 'wb')
    y4m.write(f'YUV4MPEG2 W{W} H{H} F30:1 Ip A1:1 C420jpeg\n'.encode())
    gt = []
    corners_cm = np.array([[-CW / 2, -CH / 2], [CW / 2, -CH / 2], [CW / 2, CH / 2], [-CW / 2, CH / 2]])
    for i, p in enumerate(scenario(name, n)):
        Hm = homography(p['yaw'], p['pitch'], p['roll'], p['dist'], p.get('ox', 0), p.get('oy', 0))
        img = wall.copy()
        warped = cv2.warpPerspective(framed, Hm @ S, (W, H), flags=cv2.INTER_AREA)
        m = cv2.warpPerspective(np.ones(framed.shape[:2], np.float32), Hm @ S, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        # soft shadow of the frame on the wall
        sh = cv2.GaussianBlur(m, (0, 0), 9); sh = np.roll(sh, (6, 4), (0, 1))[..., None] if sh.ndim == 2 else np.roll(sh, (6, 4), (0, 1))
        img *= (1 - 0.35 * sh.reshape(H, W, 1))
        img = img * (1 - m) + warped.astype(np.float32) * m
        # room light: left brighter + warm cast, then camera blur + sensor noise
        grad = np.linspace(1.12, 0.78, W, dtype=np.float32)[None, :, None]
        img = img * grad * np.array([0.86, 0.98, 1.06], np.float32)  # BGR: warm
        img = cv2.GaussianBlur(img, (0, 0), 0.8)
        img += rng.normal(0, 3.0, img.shape).astype(np.float32)
        img = np.clip(img, 0, 255).astype(np.uint8)
        yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV_I420)
        y4m.write(b'FRAME\n'); y4m.write(yuv.tobytes())
        gt.append(project(Hm, corners_cm).tolist())
        if i == 0: cv2.imwrite(f'{out_dir}/{name}_f0.jpg', img)
    y4m.close()
    json.dump({'W': W, 'H': H, 'corners': gt}, open(f'{out_dir}/{name}.json', 'w'))
    print(name, n, 'frames')

main()
