// Tiny JSON-file store for canvas records. Atomic writes (tmp + rename) so a crash
// mid-write never corrupts the file. Swap for a DB later without touching routes.
const fs = require('fs');
const path = require('path');

const FT_CM = 30.48;

const DEFAULT_CANVAS = {
  name: 'Untitled canvas',
  widthCm: 4 * FT_CM, // 121.92 — physical canvas, landscape
  heightCm: 3 * FT_CM, // 91.44
  // 'full'   = tracking print covers the whole canvas (recommended, most precise)
  // 'marker' = a smaller printed plaque inside the canvas, at target.{xCm,yCm}
  mode: 'full',
  target: { xCm: 0, yCm: 0, wCm: 4 * FT_CM, hCm: 3 * FT_CM },
  // What the viewer sees
  paintingId: 'traditional-1',
  allowSwitch: true,
  categories: [], // [] = all categories available in the in-AR picker
  // Fine alignment correction, saved from the in-AR calibration panel.
  // dx/dy in cm (+x right, +y down), scale multiplier, rotation in degrees.
  calibration: { dxCm: 0, dyCm: 0, scale: 1, rotDeg: 0 },
  tracking: 'balanced', // 'stable' | 'balanced' | 'responsive'
  targetFile: null, // compiled MindAR .mind file name in data/targets
  targetVersion: 0,
};

class Store {
  constructor(dir) {
    this.dir = dir;
    this.file = path.join(dir, 'canvases.json');
    fs.mkdirSync(path.join(dir, 'targets'), { recursive: true });
    this.data = fs.existsSync(this.file) ? JSON.parse(fs.readFileSync(this.file, 'utf8')) : { canvases: {} };
  }
  save() {
    const tmp = this.file + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(this.data, null, 2));
    fs.renameSync(tmp, this.file);
  }
  list() {
    return Object.values(this.data.canvases).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }
  get(id) {
    return this.data.canvases[id] || null;
  }
  create(id, fields) {
    if (this.data.canvases[id]) throw new Error('Canvas id already exists');
    const now = new Date().toISOString();
    const rec = normalise({ ...structuredClone(DEFAULT_CANVAS), ...fields, id, createdAt: now, updatedAt: now });
    this.data.canvases[id] = rec;
    this.save();
    return rec;
  }
  update(id, fields) {
    const cur = this.get(id);
    if (!cur) return null;
    const next = normalise({ ...cur, ...fields, id, createdAt: cur.createdAt, updatedAt: new Date().toISOString() });
    // A geometry change invalidates the compiled target (the print changes).
    const geomChanged = ['mode', 'widthCm', 'heightCm'].some((k) => next[k] !== cur[k]) ||
      ['wCm', 'hCm'].some((k) => next.target[k] !== cur.target[k]);
    if (geomChanged && !('targetFile' in fields)) next.targetFile = null;
    this.data.canvases[id] = next;
    this.save();
    return next;
  }
  remove(id) {
    const cur = this.get(id);
    if (!cur) return false;
    delete this.data.canvases[id];
    this.save();
    if (cur.targetFile) fs.rm(path.join(this.dir, 'targets', cur.targetFile), () => {});
    return true;
  }
}

const num = (v, d) => (Number.isFinite(+v) ? +v : d);

function normalise(c) {
  c.widthCm = Math.max(10, num(c.widthCm, DEFAULT_CANVAS.widthCm));
  c.heightCm = Math.max(10, num(c.heightCm, DEFAULT_CANVAS.heightCm));
  c.mode = c.mode === 'marker' ? 'marker' : 'full';
  const t = c.target || {};
  if (c.mode === 'full') {
    c.target = { xCm: 0, yCm: 0, wCm: c.widthCm, hCm: c.heightCm };
  } else {
    const w = Math.min(c.widthCm, Math.max(10, num(t.wCm, 30)));
    const h = Math.min(c.heightCm, Math.max(7.5, num(t.hCm, (w * 3) / 4)));
    c.target = {
      wCm: w,
      hCm: h,
      xCm: Math.min(c.widthCm - w, Math.max(0, num(t.xCm, c.widthCm - w - 5))),
      yCm: Math.min(c.heightCm - h, Math.max(0, num(t.yCm, c.heightCm - h - 5))),
    };
  }
  const cal = c.calibration || {};
  c.calibration = {
    dxCm: Math.max(-30, Math.min(30, num(cal.dxCm, 0))),
    dyCm: Math.max(-30, Math.min(30, num(cal.dyCm, 0))),
    scale: Math.max(0.8, Math.min(1.2, num(cal.scale, 1))),
    rotDeg: Math.max(-10, Math.min(10, num(cal.rotDeg, 0))),
  };
  c.tracking = ['stable', 'balanced', 'responsive'].includes(c.tracking) ? c.tracking : 'balanced';
  c.allowSwitch = c.allowSwitch !== false;
  c.categories = Array.isArray(c.categories) ? c.categories.filter((x) => typeof x === 'string') : [];
  c.name = String(c.name || 'Untitled canvas').slice(0, 80);
  c.paintingId = String(c.paintingId || DEFAULT_CANVAS.paintingId);
  c.targetVersion = num(c.targetVersion, 0);
  return c;
}

module.exports = { Store, DEFAULT_CANVAS };
