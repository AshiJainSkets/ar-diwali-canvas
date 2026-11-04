// Real-world light estimation from the known tracking print.
//
// We know exactly what the printed target looks like (its SVG). The camera sees that
// same print under the room's light, through the phone's exposure + white balance.
// Comparing observed vs. known colour at the same target positions gives a per-region
// gain (linear RGB) that we apply to the painting's albedo. Result: the painting gets the
// same brightness, colour cast and left/right light falloff as the physical canvas.
const GRID = 3;          // 3×3 illumination cells
const SAMPLES = 10;      // 10×10 candidate samples per cell (only paper-white ones are used)
const VIDEO_W = 192;     // downscaled camera frame used for sampling
const PRINT_W = 120;     // downscaled print raster (comparable blur to a distant canvas)

const toLin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
const LUT = new Float32Array(256).map((_, i) => toLin(i));

export class LightEstimator {
  constructor() {
    this.ready = false;
    this.gains = Array.from({ length: GRID * GRID }, () => [1, 1, 1]);
    this.globalLuma = 0.5;
    this.vCanvas = document.createElement('canvas');
    this.vCtx = this.vCanvas.getContext('2d', { willReadFrequently: true });
    this.last = 0;
    this.uniform = false;
  }

  async init(printSvgUrl, { uniform = false } = {}) {
    this.uniform = uniform;
    try {
      const svg = await (await fetch(printSvgUrl)).text();
      const vb = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(svg);
      const aspect = vb ? +vb[2] / +vb[1] : 0.75;
      const img = new Image();
      const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
      await new Promise((r, j) => { img.onload = r; img.onerror = j; img.src = url; });
      // Rasterize big then downscale in steps (proper area averaging).
      let w = 960, h = Math.round(960 * aspect);
      let c = document.createElement('canvas'); c.width = w; c.height = h;
      c.getContext('2d').drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      while (w > PRINT_W * 2) {
        const n = document.createElement('canvas'); n.width = Math.round(w / 2); n.height = Math.round(h / 2);
        n.getContext('2d').drawImage(c, 0, 0, n.width, n.height);
        c = n; w = n.width; h = n.height;
      }
      const f = document.createElement('canvas'); f.width = PRINT_W; f.height = Math.round(PRINT_W * aspect);
      f.getContext('2d').drawImage(c, 0, 0, f.width, f.height);
      this.pw = f.width; this.ph = f.height;
      this.print = f.getContext('2d').getImageData(0, 0, f.width, f.height).data;
      this.ready = true;
    } catch (e) {
      console.warn('[light] print raster unavailable, light estimation disabled', e);
    }
  }

  /**
   * @param {HTMLVideoElement} video
   * @param {(u:number,v:number)=>({x:number,y:number}|null)} projectToVideo  target uv (v down) → video px
   * @param {number} now ms
   * @returns {boolean} true when gains were updated
   */
  update(video, projectToVideo, now) {
    if (now - this.last < 180 || !video || !video.videoWidth) return false;
    this.last = now;
    const vw = VIDEO_W, vh = Math.round((VIDEO_W * video.videoHeight) / video.videoWidth);
    if (this.vCanvas.width !== vw || this.vCanvas.height !== vh) { this.vCanvas.width = vw; this.vCanvas.height = vh; }
    this.vCtx.drawImage(video, 0, 0, vw, vh);
    const vd = this.vCtx.getImageData(0, 0, vw, vh).data;
    const sx = vw / video.videoWidth, sy = vh / video.videoHeight;

    // global luminance (for "too dark" hints), cheap stride sampling
    let lum = 0, cnt = 0;
    for (let i = 0; i < vd.length; i += 4 * 37) { lum += 0.2126 * LUT[vd[i]] + 0.7152 * LUT[vd[i + 1]] + 0.0722 * LUT[vd[i + 2]]; cnt++; }
    this.globalLuma = lum / cnt;

    if (!this.ready || !projectToVideo) return false;

    const obs = new Float64Array(GRID * GRID * 3), ref = new Float64Array(GRID * GRID * 3), n = new Uint16Array(GRID * GRID);
    for (let gy = 0; gy < GRID; gy++) for (let gx = 0; gx < GRID; gx++) {
      const ci = gy * GRID + gx;
      for (let j = 0; j < SAMPLES; j++) for (let i = 0; i < SAMPLES; i++) {
        const u = (gx + (i + 0.5) / SAMPLES) / GRID, v = (gy + (j + 0.5) / SAMPLES) / GRID;
        const p = projectToVideo(u, v);
        if (!p) continue;
        const x = Math.round(p.x * sx), y = Math.round(p.y * sy);
        if (x < 1 || y < 1 || x >= vw - 1 || y >= vh - 1) continue;
        const k = (y * vw + x) * 4;
        const px = Math.min(this.pw - 1, Math.round(u * (this.pw - 1))), py = Math.min(this.ph - 1, Math.round(v * (this.ph - 1)));
        const q = (py * this.pw + px) * 4;
        // Only measure where the print is bare paper: ink edges are sensitive to blur and
        // misregistration, paper white is a clean "grey card" for the room light.
        if (LUT[this.print[q]] * 0.2126 + LUT[this.print[q + 1]] * 0.7152 + LUT[this.print[q + 2]] * 0.0722 < 0.62) continue;
        for (let ch = 0; ch < 3; ch++) { obs[ci * 3 + ch] += LUT[vd[k + ch]]; ref[ci * 3 + ch] += LUT[this.print[q + ch]]; }
        n[ci]++;
      }
    }
    // global fallback for cells that are off-screen
    let go = [0, 0, 0], gr = [0, 0, 0], gn = 0;
    for (let c = 0; c < GRID * GRID; c++) if (n[c] > 6) { for (let ch = 0; ch < 3; ch++) { go[ch] += obs[c * 3 + ch]; gr[ch] += ref[c * 3 + ch]; } gn += n[c]; }
    if (gn < 20) return false;
    const gGain = go.map((o, ch) => clampGain(o / Math.max(1e-4, gr[ch])));
    const k = 0.22; // temporal smoothing (per update, ~5 Hz)
    for (let c = 0; c < GRID * GRID; c++) {
      for (let ch = 0; ch < 3; ch++) {
        let g = this.uniform || n[c] <= 6 ? gGain[ch] : clampGain(obs[c * 3 + ch] / Math.max(1e-4, ref[c * 3 + ch]));
        // keep regions coherent: pull cell gains towards global (limits occluder influence)
        g = 0.65 * g + 0.35 * gGain[ch];
        this.gains[c][ch] += (g - this.gains[c][ch]) * k;
      }
    }
    return true;
  }

  /** Dominant light direction (object space) from the illumination gradient. */
  lightDirection(out) {
    const L = (c) => this.gains[c][0] * 0.2126 + this.gains[c][1] * 0.7152 + this.gains[c][2] * 0.0722;
    const left = L(0) + L(3) + L(6), right = L(2) + L(5) + L(8), top = L(0) + L(1) + L(2), bottom = L(6) + L(7) + L(8);
    const tot = Math.max(1e-3, left + right);
    const gx = (right - left) / tot, gy = (top - bottom) / Math.max(1e-3, top + bottom);
    out.set(clamp(gx * 3, -0.8, 0.8) || -0.3, clamp(gy * 3, -0.8, 0.8) || 0.45, 1).normalize();
    return out;
  }
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const clampGain = (g) => clamp(g, 0.12, 1.8);
