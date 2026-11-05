// Planar homography utilities.
//
// Why: MindAR estimates a 6-DoF pose with a *fixed, assumed* camera FOV (45° vertical).
// Real phone cameras differ, so at oblique angles a pose-based overlay drifts off the
// physical edges by a few percent. The painting lives on a plane, so we instead fit the
// exact 8-DoF perspective map (homography) from target-image points to camera pixels using
// the tracker's own per-frame correspondences, and render with it. This is independent of
// camera intrinsics and pins the painting to the real canvas corners.

/** Solve Ax=b (n×n) by Gaussian elimination with partial pivoting. Returns null if singular. */
function solve(A, b) {
  const n = b.length;
  const M = A.map((r, i) => [...r, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-12) return null;
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = c + 1; r < n; r++) {
      const f = M[r][c] / M[c][c];
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) {
    let s = M[r][n];
    for (let k = r + 1; k < n; k++) s -= M[r][k] * x[k];
    x[r] = s / M[r][r];
  }
  return x;
}

function normalizer(pts) {
  let mx = 0, my = 0;
  for (const p of pts) { mx += p.x; my += p.y; }
  mx /= pts.length; my /= pts.length;
  let d = 0;
  for (const p of pts) d += Math.hypot(p.x - mx, p.y - my);
  const s = Math.SQRT2 / Math.max(1e-9, d / pts.length);
  return { T: [s, 0, -s * mx, 0, s, -s * my, 0, 0, 1], f: (p) => ({ x: s * (p.x - mx), y: s * (p.y - my) }) };
}

/** Least-squares homography src→dst (h33 = 1), Hartley-normalised. Row-major 3×3 array. */
export function fitHomography(src, dst) {
  const n = src.length;
  if (n < 4) return null;
  const ns = normalizer(src), nd = normalizer(dst);
  const ATA = Array.from({ length: 8 }, () => new Array(8).fill(0));
  const ATb = new Array(8).fill(0);
  const acc = (row, b) => {
    for (let i = 0; i < 8; i++) { if (!row[i]) continue; ATb[i] += row[i] * b; for (let j = 0; j < 8; j++) ATA[i][j] += row[i] * row[j]; }
  };
  for (let i = 0; i < n; i++) {
    const s = ns.f(src[i]), d = nd.f(dst[i]);
    acc([s.x, s.y, 1, 0, 0, 0, -d.x * s.x, -d.x * s.y], d.x);
    acc([0, 0, 0, s.x, s.y, 1, -d.y * s.x, -d.y * s.y], d.y);
  }
  const h = solve(ATA, ATb);
  if (!h) return null;
  const Hn = [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
  // denormalise: H = Td^-1 · Hn · Ts
  const Td = nd.T, sd = Td[0];
  const TdInv = [1 / sd, 0, -Td[2] / sd, 0, 1 / sd, -Td[5] / sd, 0, 0, 1];
  const H = mul3(TdInv, mul3(Hn, ns.T));
  return scale3(H, 1 / H[8]);
}

/** Fit with one round of outlier rejection. Returns {H, inliers, rms} or null. */
export function fitHomographyRobust(src, dst, { minInliers = 8, thresholdPx = 3 } = {}) {
  let H = fitHomography(src, dst);
  if (!H) return null;
  for (let round = 0; round < 2; round++) {
    const res = src.map((p, i) => dist(apply(H, p), dst[i]));
    const sorted = [...res].sort((a, b) => a - b);
    const med = sorted[sorted.length >> 1] || 0;
    const th = Math.max(thresholdPx, 2.5 * med);
    const keep = res.map((r) => r <= th);
    const s2 = src.filter((_, i) => keep[i]), d2 = dst.filter((_, i) => keep[i]);
    if (s2.length < minInliers) return null;
    const H2 = fitHomography(s2, d2);
    if (!H2) return null;
    H = H2;
    if (s2.length === src.length) break;
  }
  const res = src.map((p, i) => dist(apply(H, p), dst[i]));
  const inl = res.filter((r) => r <= thresholdPx * 2);
  const rms = Math.sqrt(inl.reduce((a, r) => a + r * r, 0) / Math.max(1, inl.length));
  return { H, inliers: inl.length, rms };
}

/** Exact homography mapping 4 src points to 4 dst points. */
export const homographyFrom4 = (src, dst) => fitHomography(src, dst);

export function apply(H, p) {
  const w = H[6] * p.x + H[7] * p.y + H[8];
  return { x: (H[0] * p.x + H[1] * p.y + H[2]) / w, y: (H[3] * p.x + H[4] * p.y + H[5]) / w, w };
}
export function mul3(a, b) {
  const o = new Array(9);
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) o[r * 3 + c] = a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c];
  return o;
}
const scale3 = (m, s) => m.map((v) => v * s);
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

/** One-Euro filter over a vector (time in seconds). */
export class OneEuro {
  constructor(minCutoff = 1, beta = 0.02, dCutoff = 1) { Object.assign(this, { minCutoff, beta, dCutoff }); this.x = null; }
  reset() { this.x = null; }
  static alpha(dt, cutoff) { const r = 2 * Math.PI * cutoff * dt; return r / (r + 1); }
  filter(v, t) {
    if (!this.x || t <= this.t) { this.x = v.slice(); this.dx = v.map(() => 0); this.t = t; return this.x; }
    const dt = Math.min(0.25, t - this.t); this.t = t;
    const ad = OneEuro.alpha(dt, this.dCutoff);
    // speed is shared across the vector (corners move together) so the filter opens uniformly
    let speed = 0;
    for (let i = 0; i < v.length; i++) {
      const d = (v[i] - this.x[i]) / dt;
      this.dx[i] = ad * d + (1 - ad) * this.dx[i];
      speed = Math.max(speed, Math.abs(this.dx[i]));
    }
    const a = OneEuro.alpha(dt, this.minCutoff + this.beta * speed);
    for (let i = 0; i < v.length; i++) this.x[i] = a * v[i] + (1 - a) * this.x[i];
    return this.x;
  }
}

/**
 * Corner stabiliser: keeps the painting still on a still canvas, follows it quickly when it moves.
 *
 * Why: per-frame tracking measurements are noisy (single-frame spikes of several % of the canvas,
 * even with the phone held still). A One-Euro filter reads that noise as speed and opens up, so the
 * painting shivers. Here:
 *   1. a running median over the last few *new* measurements removes one-frame spikes;
 *   2. while the measured corners stay within a small dead zone of the shown position (relative to
 *      the canvas size), the painting is held almost locked (very slow drift correction);
 *   3. beyond the dead zone (real hand / phone movement) it switches smoothly to fast following,
 *      and settles back onto the measurement before locking again (hysteresis).
 */
export class CornerStabilizer {
  constructor(opts = {}) { this.configure(opts); this.reset(); }
  configure({ deadzone = 0.01, still = 0.25, move = 9, window = 3 } = {}) {
    Object.assign(this, { deadzone, still, move, window });
  }
  reset() { this.win = []; this.target = null; this.x = null; this.t = 0; this.moving = false; this.last = null; }
  /** Add a new measurement (8 numbers: x0,y0,…,x3,y3). Identical repeats are ignored. */
  push(v) {
    if (this.last && v.every((a, i) => Math.abs(a - this.last[i]) < 1e-6)) return;
    this.last = v.slice();
    this.win.push(v.slice());
    if (this.win.length > this.window) this.win.shift();
    this.target = v.map((_, i) => median(this.win.map((w) => w[i])));
  }
  /** Advance the shown corners towards the measurement; call every rendered frame. */
  update(t) {
    if (!this.target) return this.x;
    if (!this.x) { this.x = this.target.slice(); this.t = t; return this.x; }
    const dt = Math.min(0.25, Math.max(0.001, t - this.t)); this.t = t;
    const diag = Math.hypot(this.x[4] - this.x[0], this.x[5] - this.x[1]) || 1;
    let dev = 0;
    for (let i = 0; i < 8; i += 2) dev = Math.max(dev, Math.hypot(this.target[i] - this.x[i], this.target[i + 1] - this.x[i + 1]));
    const r = dev / diag;
    const dz = this.moving ? this.deadzone * 0.35 : this.deadzone;   // hysteresis: settle, then lock
    const k = Math.min(1, Math.max(0, (r - dz) / (this.deadzone * 3)));
    this.moving = k > 0.15 || (this.moving && r > dz);
    const cutoff = this.still + (this.move - this.still) * Math.sqrt(k);
    const a = OneEuro.alpha(dt, cutoff);
    for (let i = 0; i < 8; i++) this.x[i] += a * (this.target[i] - this.x[i]);
    return this.x;
  }
}

function median(a) {
  const s = a.slice().sort((p, q) => p - q), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
