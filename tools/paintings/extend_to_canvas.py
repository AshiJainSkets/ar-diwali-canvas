"""Content-aware extension of a photo/painting to the 4:3 canvas without touching people.

Technique: seam insertion (Avidan & Shamir, "Seam Carving"). Low-detail paths through the
background (sky, ceiling, carpet, walls) are found and duplicated until the image reaches 4:3.
Protected rectangles (faces, bodies, logos, text) get infinite cost, so no seam ever passes
through them: those pixels are copied unchanged, only shifted. Nothing is "generated" or redrawn.

usage (library): extend(img_bgr, protect=[(x0,y0,x1,y1), ...], crop=(x0,y0,x1,y1)|None) -> 1600×1200
"""
import numpy as np, cv2

BIG = 1e6


def _energy(img, protect_mask):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
    hard = protect_mask >= 1
    return e + hard * BIG + (~hard) * protect_mask * 400.0


def _find_seam(energy):
    h, w = energy.shape
    M = energy.astype(np.float64).copy()
    back = np.zeros((h, w), np.int32)
    idx = np.arange(w)
    for i in range(1, h):
        prev = M[i - 1]
        left = np.r_[np.inf, prev[:-1]]
        right = np.r_[prev[1:], np.inf]
        stack = np.vstack([left, prev, right])
        k = np.argmin(stack, axis=0)
        back[i] = idx + k - 1
        M[i] += stack[k, idx]
    seam = np.zeros(h, np.int32)
    seam[-1] = int(np.argmin(M[-1]))
    for i in range(h - 1, 0, -1):
        seam[i - 1] = back[i, seam[i]]
    return seam


def extend(img, protect=(), crop=None, work_width=900):
    """Return the image extended (never cropped beyond `crop`) to exactly 4:3, 1600×1200."""
    if crop:
        x0, y0, x1, y1 = crop
        img = img[y0:y1, x0:x1]
        protect = [(r[0] - x0, r[1] - y0, r[2] - x0, r[3] - y0, *r[4:]) for r in protect]
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.float32)
    for r in protect:  # (x0, y0, x1, y1[, weight]) — weight < 1 only discourages seams there
        a, b, c, d = r[:4]
        wgt = r[4] if len(r) > 4 else 1.0
        sl = (slice(max(0, b), min(h, d)), slice(max(0, a), min(w, c)))
        mask[sl] = np.maximum(mask[sl], wgt)
    # Seams are searched on a reduced copy for speed. Each pixel carries its exact source (x, y)
    # through the growth; the result is then sampled from the full-resolution original.
    s = min(1.0, work_width / w)
    small = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else img
    smask = cv2.resize(mask, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST) if s < 1 else mask
    sh, sw = small.shape[:2]
    if sw / sh < 4 / 3:
        add_w, add_h = int(round(sh * 4 / 3)) - sw, 0
    else:
        add_w, add_h = 0, int(round(sw * 3 / 4)) - sh
    ys, xs = np.mgrid[0:sh, 0:sw].astype(np.float32)
    packed = np.dstack([small.astype(np.float32), (xs + 0.5) / s - 0.5, (ys + 0.5) / s - 0.5])
    grown = _grow_packed(packed, smask.copy(), add_w, add_h)
    gx = cv2.resize(grown[..., 3], (1600, 1200), interpolation=cv2.INTER_LINEAR)
    gy = cv2.resize(grown[..., 4], (1600, 1200), interpolation=cv2.INTER_LINEAR)
    return cv2.remap(img, gx, gy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def _grow_packed(packed, mask, add_w, add_h, step=0.25):
    def insert(p, m, n):
        h, w = m.shape
        work = p.copy(); wm = m.copy()
        orig = np.tile(np.arange(w), (h, 1))
        seams = []
        for _ in range(n):
            s = _find_seam(_energy(np.clip(work[..., :3], 0, 255).astype(np.uint8), wm))
            rows = np.arange(h)
            seams.append(orig[rows, s].copy())
            keep = np.ones(wm.shape, bool); keep[rows, s] = False
            cw = wm.shape[1] - 1
            work = work[keep].reshape(h, cw, p.shape[2]); wm = wm[keep].reshape(h, cw); orig = orig[keep].reshape(h, cw)
        cols = np.array(seams).T
        out = np.zeros((h, w + n, p.shape[2]), np.float32); om = np.zeros((h, w + n), np.float32)
        for r in range(h):
            dup = np.bincount(cols[r], minlength=w)
            reps = 1 + dup
            src = p[r]; nxt = np.vstack([src[1:], src[-1:]])
            o = np.repeat(src, reps, axis=0)
            pos = np.cumsum(reps) - 1
            for c in np.nonzero(dup)[0]:
                for j in range(dup[c]):
                    t = (j + 1) / (dup[c] + 1)
                    o[pos[c] - dup[c] + 1 + j] = src[c] * (1 - t) + nxt[c] * t
            out[r] = o; om[r] = np.repeat(m[r], reps)
        return out, om
    p, m = packed, mask
    while add_w > 0:
        n = min(add_w, max(1, int(p.shape[1] * step)))
        p, m = insert(p, m, n); add_w -= n
    while add_h > 0:
        n = min(add_h, max(1, int(p.shape[0] * step)))
        tp, tm = insert(np.ascontiguousarray(p.transpose(1, 0, 2)), np.ascontiguousarray(m.T), n)
        p, m = np.ascontiguousarray(tp.transpose(1, 0, 2)), np.ascontiguousarray(tm.T); add_h -= n
    return p
