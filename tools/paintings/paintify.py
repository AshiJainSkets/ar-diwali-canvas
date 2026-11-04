"""Painterly pass: turns a clean vector render into a brush-stroke painting.

Outputs per painting (in public/paintings/<id>/):
  albedo.jpg   1600×1200  paint colour (what the AR shader lights)
  height.jpg    800×600   impasto height (stroke ridges + bristles) → normals in the shader
  preview.jpg  1200×900   gallery preview with baked canvas lighting
  thumb.jpg     480×360   gallery card

Method: layered brush strokes (Hertzmann-style, coarse → fine, only where the canvas still
differs from the reference) oriented along the image's structure-tensor flow, with per-stroke
colour jitter; bristle streaks are noise smeared along the flow; heights are accumulated per stroke.
"""
import sys, os, math
import numpy as np, cv2

def orientation_field(gray):
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), 6)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), 6)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), 6)
    # direction of least change (along edges)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    coherence = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    return theta.astype(np.float32), coherence.astype(np.float32)


def paint_layer(canvas, height, ref, theta, coh, radius, spacing, threshold, rng, length_mul, height_amt):
    Hh, Ww = ref.shape[:2]
    diff = np.abs(canvas - ref).mean(axis=2)
    ys, xs = np.mgrid[spacing // 2:Hh:spacing, spacing // 2:Ww:spacing]
    ys = (ys + rng.integers(-spacing // 2, spacing // 2 + 1, ys.shape)).clip(0, Hh - 1).ravel()
    xs = (xs + rng.integers(-spacing // 2, spacing // 2 + 1, xs.shape)).clip(0, Ww - 1).ravel()
    if threshold > 0:
        err = cv2.blur(diff, (spacing, spacing))
        keep = err[ys, xs] > threshold
        ys, xs = ys[keep], xs[keep]
    order = rng.permutation(len(xs))
    th = int(max(1, round(radius * 2)))
    jit = rng.normal(1.0, 0.035, (len(xs), 1)).astype(np.float32)
    hval = rng.uniform(0.35, 1.0, len(xs)) * height_amt
    for k in order:
        x, y = int(xs[k]), int(ys[k])
        col = ref[y, x] * jit[k]
        a = float(theta[y, x])
        L = radius * length_mul * (0.6 + 0.8 * min(1.0, float(coh[y, x]) * 2))
        # two-segment curved stroke following the flow field
        dx, dy = math.cos(a), math.sin(a)
        x0, y0 = x - dx * L / 2, y - dy * L / 2
        mx, my = int(min(Ww - 1, max(0, x))), int(min(Hh - 1, max(0, y)))
        x1, y1 = x + dx * L / 2, y + dy * L / 2
        xe, ye = int(min(Ww - 1, max(0, x1))), int(min(Hh - 1, max(0, y1)))
        a2 = float(theta[ye, xe])
        if math.cos(a2 - a) < 0: a2 += math.pi
        x2, y2 = x1 + math.cos(a2) * L * 0.35, y1 + math.sin(a2) * L * 0.35
        pts = np.array([[x0, y0], [x1, y1], [x2, y2]], np.int32)
        c = (float(col[0]), float(col[1]), float(col[2]))
        cv2.polylines(canvas, [pts], False, c, th, cv2.LINE_AA)
        hv = float(hval[k])
        cv2.polylines(height, [pts], False, hv, th, cv2.LINE_AA)
        if th >= 3:
            cv2.polylines(height, [pts], False, min(1.0, hv + 0.18), max(1, th // 3), cv2.LINE_AA)


def bristles(theta, shape, rng, amount):
    noise = rng.normal(0, 1, shape).astype(np.float32)
    out = np.zeros(shape, np.float32)
    bins = 12
    idx = ((theta % np.pi) / np.pi * bins).astype(np.int32) % bins
    for b in range(bins):
        a = (b + 0.5) / bins * np.pi
        k = np.zeros((15, 15), np.float32)
        cv2.line(k, (int(7 - 7 * math.cos(a)), int(7 - 7 * math.sin(a))), (int(7 + 7 * math.cos(a)), int(7 + 7 * math.sin(a))), 1.0, 1)
        k /= k.sum()
        f = cv2.filter2D(noise, -1, k)
        out[idx == b] = f[idx == b]
    out /= (out.std() + 1e-6)
    return out * amount


def weave(shape, period=7.0):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    tx, ty = xx / period, yy / period
    par = (np.floor(tx) + np.floor(ty)) % 2
    hx, hy = np.sin(np.pi * (tx % 1)), np.sin(np.pi * (ty % 1))
    return np.where(par > 0, hx * (0.6 + 0.4 * hy), hy * (0.6 + 0.4 * hx)).astype(np.float32)


def bake_preview(albedo, height, out_w):
    """Gallery preview: albedo lit by a soft top-left light over impasto + canvas weave."""
    h = cv2.GaussianBlur(height, (0, 0), 0.8)
    hw = weave(h.shape) * 0.14
    thick = cv2.GaussianBlur(height, (0, 0), 2)
    htot = h * 1.0 + hw * (1 - 0.6 * np.clip((thick - 0.55) / 0.35, 0, 1))
    gx = cv2.Sobel(htot, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(htot, cv2.CV_32F, 0, 1, ksize=3)
    n = np.dstack([-gx * 1.6, -gy * 1.6, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = np.array([-0.4, -0.5, 1.0]); L /= np.linalg.norm(L)  # light from top-left (image y down)
    ndl = (n @ L)
    shade = 1 + 0.75 * (ndl - L[2])
    Hv = L + np.array([0, 0, 1.0]); Hv /= np.linalg.norm(Hv)
    spec = np.clip(n @ Hv, 0, 1) ** 40 * 0.07 * (0.4 + 0.6 * thick)
    lin = (albedo / 255.0) ** 2.2
    lit = lin * shade[..., None] + spec[..., None]
    # inner frame shadow
    hh, ww = lit.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww]
    d = np.minimum(np.minimum(xx, ww - 1 - xx), np.minimum(yy, hh - 1 - yy)).astype(np.float32)
    lit *= (0.8 + 0.2 * np.clip(d / 18, 0, 1))[..., None]
    out = np.clip(lit, 0, 1) ** (1 / 2.2) * 255
    return cv2.resize(out.astype(np.uint8), (out_w, out_w * 3 // 4), interpolation=cv2.INTER_AREA)


def paintify(src_png, out_dir, seed=0):
    rng = np.random.default_rng(seed)
    ref = cv2.imread(src_png, cv2.IMREAD_COLOR).astype(np.float32)
    ref = cv2.resize(ref, (1600, 1200), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) / 255.0
    theta, coh = orientation_field(gray)
    # break up perfectly concentric strokes in smooth gradients with a low-frequency wobble
    wob = cv2.resize(cv2.GaussianBlur(rng.normal(0, 1, (30, 40)).astype(np.float32), (0, 0), 1.5), (1600, 1200), interpolation=cv2.INTER_CUBIC)
    theta = theta + (wob / (wob.std() + 1e-6)) * 0.45 * (1.2 - np.clip(coh, 0, 1))
    canvas = cv2.GaussianBlur(ref, (0, 0), 10)
    height = np.full(gray.shape, 0.25, np.float32)
    refs = {r: cv2.GaussianBlur(ref, (0, 0), max(0.6, r * 0.55)) for r in (10, 5, 2.4, 1.4)}
    paint_layer(canvas, height, refs[10], theta, coh, 10, 9, 0, rng, 4.0, 0.75)
    paint_layer(canvas, height, refs[5], theta, coh, 5, 5, 6.0, rng, 3.4, 0.9)
    paint_layer(canvas, height, refs[2.4], theta, coh, 2.4, 3, 6.0, rng, 3.0, 1.0)
    paint_layer(canvas, height, refs[1.4], theta, coh, 1.4, 2, 9.0, rng, 2.6, 0.9)
    # keep crisp detail (fine line work, lettering) from the reference
    detail = np.abs(ref - cv2.GaussianBlur(ref, (0, 0), 2)).mean(axis=2)
    m = np.clip(detail / 40.0, 0, 1)[..., None] * 0.55 + 0.12
    albedo = canvas * (1 - m) + ref * m
    br = bristles(theta, gray.shape, rng, 1.0)
    albedo *= (1 + 0.03 * br)[..., None]
    # gentle pigment variation (low frequency)
    lf = cv2.GaussianBlur(rng.normal(0, 1, (75, 100)).astype(np.float32), (0, 0), 3)
    lf = cv2.resize(lf / (lf.std() + 1e-6), (1600, 1200), interpolation=cv2.INTER_CUBIC)
    albedo *= (1 + 0.025 * lf)[..., None]
    albedo = np.clip(albedo, 0, 255).astype(np.uint8)
    height = cv2.GaussianBlur(height, (0, 0), 1.4) + 0.05 * br
    height = (height - height.min()) / (height.max() - height.min() + 1e-6)

    os.makedirs(out_dir, exist_ok=True)
    cv2.imwrite(os.path.join(out_dir, 'albedo.jpg'), albedo, [cv2.IMWRITE_JPEG_QUALITY, 86, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    h8 = cv2.resize((height * 255).astype(np.uint8), (800, 600), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(out_dir, 'height.jpg'), h8, [cv2.IMWRITE_JPEG_QUALITY, 88])
    prev = bake_preview(albedo.astype(np.float32), height, 1200)
    cv2.imwrite(os.path.join(out_dir, 'preview.jpg'), prev, [cv2.IMWRITE_JPEG_QUALITY, 84, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    cv2.imwrite(os.path.join(out_dir, 'thumb.jpg'), cv2.resize(prev, (480, 360), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == '__main__':
    import time
    src, out = sys.argv[1], sys.argv[2]
    t = time.time()
    paintify(src, out, seed=abs(hash(os.path.basename(src))) % 2**31)
    print(os.path.basename(src), f'{time.time()-t:.1f}s')
