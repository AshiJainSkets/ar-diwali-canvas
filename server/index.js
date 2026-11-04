// AR Diwali Canvas — backend
// Serves the web app, the canvas registry API, QR codes and tracking prints.
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const express = require('express');
const compression = require('compression');
const QRCode = require('qrcode');
const { customAlphabet } = require('nanoid');
const { Store } = require('./store');
const { buildTargetSVG } = require('./targetPrint');

const ROOT = path.join(__dirname, '..');

// Minimal .env loader (works the same on Windows, macOS, Linux). Real env vars win.
(function loadDotEnv() {
  const f = path.join(ROOT, '.env');
  if (!fs.existsSync(f)) return;
  for (const line of fs.readFileSync(f, 'utf8').split(/\r?\n/)) {
    const m = /^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/.exec(line);
    if (m && !line.trim().startsWith('#') && process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^['"]|['"]$/g, '');
  }
})();
if (process.argv.includes('--https')) process.env.HTTPS = '1';
const DATA_DIR = process.env.DATA_DIR || path.join(ROOT, 'data');
const PUBLIC_DIR = path.join(ROOT, 'public');
const PORT = +process.env.PORT || 8080;
const PUBLIC_BASE_URL = (process.env.PUBLIC_BASE_URL || '').replace(/\/+$/, '');
const store = new Store(DATA_DIR);
const newId = customAlphabet('abcdefghjkmnpqrstuvwxyz23456789', 8);
const ID_RE = /^[a-z0-9][a-z0-9-]{2,39}$/;

// ---- admin token -----------------------------------------------------------
let ADMIN_TOKEN = process.env.ADMIN_TOKEN;
if (!ADMIN_TOKEN) {
  const f = path.join(DATA_DIR, '.admin-token');
  ADMIN_TOKEN = fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim() : crypto.randomBytes(12).toString('hex');
  fs.writeFileSync(f, ADMIN_TOKEN);
  console.log(`[admin] ADMIN_TOKEN not set — using generated token: ${ADMIN_TOKEN}  (stored in data/.admin-token)`);
}
function requireAdmin(req, res, next) {
  const t = req.get('x-admin-token') || req.query.token || '';
  const a = Buffer.from(String(t)), b = Buffer.from(ADMIN_TOKEN);
  if (a.length === b.length && crypto.timingSafeEqual(a, b)) return next();
  res.status(401).json({ error: 'Admin token required' });
}

// ---- seed demo canvas ------------------------------------------------------
if (!store.get('demo')) {
  const seedMind = path.join(__dirname, 'seed', 'demo.mind');
  const seedMeta = path.join(__dirname, 'seed', 'demo.json');
  const meta = fs.existsSync(seedMeta) ? JSON.parse(fs.readFileSync(seedMeta, 'utf8')) : {};
  let targetFile = null;
  if (fs.existsSync(seedMind)) {
    targetFile = 'demo-1.mind';
    fs.copyFileSync(seedMind, path.join(DATA_DIR, 'targets', targetFile));
  }
  store.create('demo', {
    name: 'Demo canvas (4 × 3 ft)',
    paintingId: 'traditional-1',
    targetFile,
    targetVersion: targetFile ? 1 : 0,
    targetCompiledFor: meta.url || null,
  });
  console.log('[seed] created demo canvas');
}

// ---- helpers ----------------------------------------------------------------
function baseUrl(req) {
  if (PUBLIC_BASE_URL) return PUBLIC_BASE_URL;
  return `${req.protocol}://${req.get('host')}`;
}
const canvasUrl = (req, id) => `${baseUrl(req)}/c/${encodeURIComponent(id)}`;

function publicCanvas(req, c) {
  return {
    id: c.id,
    name: c.name,
    widthCm: c.widthCm,
    heightCm: c.heightCm,
    mode: c.mode,
    target: c.target,
    paintingId: c.paintingId,
    allowSwitch: c.allowSwitch,
    categories: c.categories,
    calibration: c.calibration,
    tracking: c.tracking,
    targetUrl: c.targetFile ? `/targets/${c.targetFile}?v=${c.targetVersion}` : null,
    url: canvasUrl(req, c.id),
  };
}
function adminCanvas(req, c) {
  const url = canvasUrl(req, c.id);
  return {
    ...publicCanvas(req, c),
    createdAt: c.createdAt,
    updatedAt: c.updatedAt,
    targetVersion: c.targetVersion,
    targetCompiledFor: c.targetCompiledFor || null,
    targetStale: !!c.targetFile && c.targetCompiledFor !== url,
  };
}
function loadCanvas(req, res, next) {
  const c = store.get(req.params.id);
  if (!c) return res.status(404).json({ error: 'Canvas not found' });
  req.canvas = c;
  next();
}

// ---- app ----------------------------------------------------------------------
const app = express();
app.set('trust proxy', true); // correct https/host behind Render/Railway/Nginx
app.disable('x-powered-by');
app.use(compression());
app.use(express.json({ limit: '200kb' }));
app.use((req, res, next) => {
  res.set('Permissions-Policy', 'camera=(self)');
  res.set('X-Content-Type-Options', 'nosniff');
  next();
});

// Static: long cache for immutable vendor/fonts/paintings, short for app code.
app.use('/vendor', express.static(path.join(PUBLIC_DIR, 'vendor'), { maxAge: '30d', immutable: true }));
app.use('/fonts', express.static(path.join(PUBLIC_DIR, 'fonts'), { maxAge: '30d', immutable: true }));
app.use('/paintings', express.static(path.join(PUBLIC_DIR, 'paintings'), { maxAge: '7d' }));
app.use('/targets', express.static(path.join(DATA_DIR, 'targets'), { maxAge: '7d' }));
app.use(express.static(PUBLIC_DIR, { maxAge: '5m', index: false }));

const sendIndex = (req, res) => res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
app.get('/', sendIndex);
app.get('/c/:id', sendIndex);
app.get('/admin', (req, res) => res.sendFile(path.join(PUBLIC_DIR, 'admin.html')));
app.get('/healthz', (req, res) => res.json({ ok: true }));
app.get('/favicon.ico', (req, res) => res.redirect(301, '/img/logo.svg'));

// ---- public API ---------------------------------------------------------------
app.get('/api/canvas/:id', loadCanvas, (req, res) => {
  res.set('Cache-Control', 'no-cache');
  res.json(publicCanvas(req, req.canvas));
});

app.get('/api/canvas/:id/qr.:ext(svg|png)', loadCanvas, async (req, res) => {
  const url = canvasUrl(req, req.canvas.id);
  const opts = { errorCorrectionLevel: 'Q', margin: 2, color: { dark: req.query.dark || '#14070aff', light: '#ffffffff' } };
  const dl = req.query.download ? `attachment; filename="ar-diwali-${req.canvas.id}-qr.${req.params.ext}"` : 'inline';
  res.set('Content-Disposition', dl);
  try {
    if (req.params.ext === 'svg') {
      res.type('image/svg+xml').send(await QRCode.toString(url, { ...opts, type: 'svg' }));
    } else {
      const width = Math.max(256, Math.min(4096, +req.query.size || 1024));
      res.type('png').send(await QRCode.toBuffer(url, { ...opts, width }));
    }
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Tracking print (vector). ?compile=1 returns the unitless variant used for compiling.
app.get('/api/canvas/:id/print.svg', loadCanvas, async (req, res) => {
  const c = req.canvas;
  const { svg } = await buildTargetSVG({
    canvasId: c.id,
    url: canvasUrl(req, c.id),
    widthCm: c.target.wCm,
    heightCm: c.target.hCm,
    label: c.id, // immutable, so renaming a canvas never invalidates its compiled target
    forCompile: !!req.query.compile,
  });
  if (req.query.download) res.set('Content-Disposition', `attachment; filename="ar-diwali-${c.id}-tracking-print-${c.target.wCm.toFixed(1)}x${c.target.hCm.toFixed(1)}cm.svg"`);
  res.set('Cache-Control', 'no-cache');
  res.type('image/svg+xml').send(svg);
});

// ---- admin API ----------------------------------------------------------------
const admin = express.Router();
admin.use(requireAdmin);
admin.get('/verify', (req, res) => res.json({ ok: true, baseUrl: baseUrl(req), publicBaseUrlSet: !!PUBLIC_BASE_URL }));
admin.get('/canvases', (req, res) => res.json(store.list().map((c) => adminCanvas(req, c))));
admin.post('/canvases', (req, res) => {
  const body = req.body || {};
  const id = body.id ? String(body.id).toLowerCase().trim() : newId();
  if (!ID_RE.test(id)) return res.status(400).json({ error: 'Canvas ID must be 3–40 chars: a–z, 0–9, hyphen' });
  if (store.get(id)) return res.status(409).json({ error: 'Canvas ID already exists' });
  const rec = store.create(id, pickEditable(body));
  res.status(201).json(adminCanvas(req, rec));
});
admin.get('/canvases/:id', loadCanvas, (req, res) => res.json(adminCanvas(req, req.canvas)));
admin.put('/canvases/:id', loadCanvas, (req, res) => res.json(adminCanvas(req, store.update(req.canvas.id, pickEditable(req.body || {})))));
admin.put('/canvases/:id/calibration', loadCanvas, (req, res) => {
  const b = req.body || {};
  const rec = store.update(req.canvas.id, { calibration: b.calibration || req.canvas.calibration, tracking: b.tracking || req.canvas.tracking });
  res.json(adminCanvas(req, rec));
});
admin.delete('/canvases/:id', loadCanvas, (req, res) => {
  store.remove(req.canvas.id);
  res.json({ ok: true });
});
// Upload a compiled MindAR target (.mind binary), produced in the admin page.
admin.post('/canvases/:id/target', loadCanvas, express.raw({ type: 'application/octet-stream', limit: '20mb' }), (req, res) => {
  if (!req.body || !req.body.length) return res.status(400).json({ error: 'Empty target file' });
  const c = req.canvas;
  const version = (c.targetVersion || 0) + 1;
  const file = `${c.id}-${version}.mind`;
  fs.writeFileSync(path.join(DATA_DIR, 'targets', file), req.body);
  if (c.targetFile && c.targetFile !== file) fs.rm(path.join(DATA_DIR, 'targets', c.targetFile), () => {});
  const rec = store.update(c.id, { targetFile: file, targetVersion: version, targetCompiledFor: String(req.query.url || canvasUrl(req, c.id)) });
  res.json(adminCanvas(req, rec));
});
app.use('/api/admin', admin);

function pickEditable(b) {
  const out = {};
  for (const k of ['name', 'widthCm', 'heightCm', 'mode', 'target', 'paintingId', 'allowSwitch', 'categories', 'calibration', 'tracking']) {
    if (k in b) out[k] = b[k];
  }
  return out;
}

app.use('/api', (req, res) => res.status(404).json({ error: 'Not found' }));
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Server error' });
});

// ---- start ----------------------------------------------------------------------
async function start() {
  if (process.env.HTTPS === '1') {
    // Self-signed HTTPS for LAN phone testing (camera requires a secure context).
    const https = require('https');
    const certDir = path.join(DATA_DIR, 'cert');
    fs.mkdirSync(certDir, { recursive: true });
    const keyF = path.join(certDir, 'key.pem'), certF = path.join(certDir, 'cert.pem');
    if (!fs.existsSync(keyF)) {
      const selfsigned = require('selfsigned');
      const pems = selfsigned.generate([{ name: 'commonName', value: 'ar-diwali-canvas.local' }], { days: 365, keySize: 2048 });
      fs.writeFileSync(keyF, pems.private);
      fs.writeFileSync(certF, pems.cert);
    }
    const port = +process.env.HTTPS_PORT || 8443;
    https.createServer({ key: fs.readFileSync(keyF), cert: fs.readFileSync(certF) }, app).listen(port, '0.0.0.0', () => {
      console.log(`AR Diwali Canvas (HTTPS, self-signed) on https://0.0.0.0:${port}`);
      printLanHints(port, 'https');
    });
  }
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`AR Diwali Canvas on http://localhost:${PORT}   admin: http://localhost:${PORT}/admin`);
    if (!PUBLIC_BASE_URL) console.log('[warn] PUBLIC_BASE_URL not set — QR codes will encode the host of whoever requests them.');
  });
}
function printLanHints(port, proto) {
  const nets = require('os').networkInterfaces();
  for (const list of Object.values(nets)) for (const n of list || []) if (n.family === 'IPv4' && !n.internal) console.log(`   phone on same Wi-Fi: ${proto}://${n.address}:${port}`);
}
if (require.main === module) start();
module.exports = { app };
