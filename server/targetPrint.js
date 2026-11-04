// Generates the printable tracking target ("tracking print") for a canvas.
//
// Why this exists: a blank canvas has no visual features, so no image tracker can
// lock onto it. We print a high-contrast, non-repeating Diwali line-art pattern
// (with the canvas QR code embedded) at the exact physical size of the tracked
// region. MindAR is then compiled against this exact artwork, so the tracked
// rectangle == the printed rectangle == (in "full" mode) the canvas itself.
//
// The output is vector SVG (print-shop friendly at any size) and deterministic per
// canvas id (seeded RNG), so re-generating gives the identical print.

const QRCode = require('qrcode');

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

const INK = ['#3b0a14', '#5c1020', '#0d3532', '#1d1a3a', '#7a3d06'];

// Motifs drawn in a unit box centred at 0,0 (approx radius 1).
const MOTIFS = {
  diya: (c) => `<path d="M-1 -0.05 Q0 1.05 1 -0.05 Z" fill="${c}"/><path d="M0 -0.2 Q-0.38 -0.62 0 -1.15 Q0.38 -0.62 0 -0.2 Z" fill="${c}"/><circle cx="0" cy="0.32" r="0.16" fill="#f4e9d8"/>`,
  flower6: (c) => { let s = ''; for (let i = 0; i < 6; i++) s += `<ellipse cx="0" cy="-0.55" rx="0.24" ry="0.45" fill="${c}" transform="rotate(${i * 60})"/>`; return s + `<circle r="0.22" fill="#f4e9d8"/><circle r="0.1" fill="${c}"/>`; },
  flower8: (c) => { let s = ''; for (let i = 0; i < 8; i++) s += `<path d="M0 0 Q0.32 -0.5 0 -1 Q-0.32 -0.5 0 0Z" fill="none" stroke="${c}" stroke-width="0.13" transform="rotate(${i * 45})"/>`; return s + `<circle r="0.18" fill="${c}"/>`; },
  star: (c) => { const p = []; for (let i = 0; i < 10; i++) { const r = i % 2 ? 0.42 : 1; const a = (i * Math.PI) / 5 - Math.PI / 2; p.push(`${(r * Math.cos(a)).toFixed(3)},${(r * Math.sin(a)).toFixed(3)}`); } return `<polygon points="${p.join(' ')}" fill="${c}"/>`; },
  paisley: (c) => `<path d="M0.15 0.95 C-0.95 0.85 -0.9 -0.4 -0.1 -0.7 C0.5 -0.95 0.95 -0.6 0.75 -0.05 C0.6 0.35 0.2 0.3 0.25 0 " fill="none" stroke="${c}" stroke-width="0.16" stroke-linecap="round"/><circle cx="-0.25" cy="0.15" r="0.2" fill="${c}"/>`,
  rings: (c) => `<circle r="0.92" fill="none" stroke="${c}" stroke-width="0.14"/><circle r="0.55" fill="none" stroke="${c}" stroke-width="0.1" stroke-dasharray="0.18 0.12"/><circle r="0.22" fill="${c}"/>`,
  triangles: (c) => `<polygon points="0,-1 0.87,0.5 -0.87,0.5" fill="${c}"/><polygon points="0,0.55 0.42,-0.22 -0.42,-0.22" fill="#f4e9d8"/>`,
  crescent: (c) => `<path d="M0.3 -0.95 A1 1 0 1 0 0.3 0.95 A0.75 0.75 0 1 1 0.3 -0.95Z" fill="${c}"/><circle cx="0.55" cy="-0.1" r="0.16" fill="${c}"/>`,
  diamond: (c) => `<rect x="-0.7" y="-0.7" width="1.4" height="1.4" transform="rotate(45)" fill="none" stroke="${c}" stroke-width="0.16"/><rect x="-0.3" y="-0.3" width="0.6" height="0.6" fill="${c}"/>`,
  zigzag: (c) => `<polyline points="-1,0.5 -0.6,-0.5 -0.2,0.5 0.2,-0.5 0.6,0.5 1,-0.5" fill="none" stroke="${c}" stroke-width="0.18" stroke-linejoin="round"/>`,
  spiral: (c) => { const pts = []; for (let t = 0; t < 4.2 * Math.PI; t += 0.25) { const r = 0.08 + (t / (4.2 * Math.PI)) * 0.9; pts.push(`${(r * Math.cos(t)).toFixed(3)},${(r * Math.sin(t)).toFixed(3)}`); } return `<polyline points="${pts.join(' ')}" fill="none" stroke="${c}" stroke-width="0.12" stroke-linecap="round"/>`; },
  kalash: (c) => `<path d="M-0.55 -0.35 Q-1 0.4 -0.35 0.95 L0.35 0.95 Q1 0.4 0.55 -0.35 Z" fill="${c}"/><rect x="-0.45" y="-0.55" width="0.9" height="0.2" fill="${c}"/><circle cx="0" cy="-0.82" r="0.22" fill="${c}"/><path d="M-0.4 -0.6 L-0.9 -0.95 M0.4 -0.6 L0.9 -0.95" stroke="${c}" stroke-width="0.12"/>`,
};
const MOTIF_KEYS = Object.keys(MOTIFS);

/**
 * @param {object} o
 * @param {string} o.canvasId
 * @param {string} o.url             URL encoded in the QR code
 * @param {number} o.widthCm         physical width of the tracked print
 * @param {number} o.heightCm        physical height of the tracked print
 * @param {string} [o.label]         human label printed under the QR
 * @param {boolean}[o.forCompile]    omit crop marks / footer text that is outside the trim
 */
async function buildTargetSVG({ canvasId, url, widthCm, heightCm, label = '', forCompile = false }) {
  const W = 1200; // internal units across the print width
  const H = Math.round((W * heightCm) / widthCm);
  const rnd = mulberry32(hashString('ardiwali:' + canvasId));
  const R = (a, b) => a + (b - a) * rnd();
  const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
  const isMarker = widthCm < 80; // small plaque vs full canvas

  const out = [];
  out.push(`<rect width="${W}" height="${H}" fill="#f4e9d8"/>`);

  // Background texture: random fine hatching patches (adds trackable corners everywhere).
  for (let i = 0; i < (isMarker ? 90 : 260); i++) {
    const x = R(0, W), y = R(0, H), len = R(8, 26), ang = R(0, 180);
    const n = 2 + Math.floor(R(0, 4));
    let s = '';
    for (let k = 0; k < n; k++) s += `<line x1="${-len}" y1="${k * 5}" x2="${len}" y2="${k * 5}"/>`;
    out.push(`<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${ang.toFixed(0)})" stroke="${pick(INK)}" stroke-width="2" opacity="0.55">${s}</g>`);
  }

  // Main motif field on a jittered grid.
  const cols = isMarker ? 8 : 13;
  const cell = W / cols;
  const rows = Math.ceil(H / cell);
  const qrSize = isMarker ? H * 0.52 : H * 0.27;
  const qrPanel = { w: qrSize + (isMarker ? 70 : 70), h: qrSize + (isMarker ? 100 : 110) };
  const qrBox = isMarker
    ? { x: W - qrPanel.w - 30, y: (H - qrPanel.h) / 2 }
    : { x: (W - qrPanel.w) / 2, y: (H - qrPanel.h) / 2 };
  const insideQR = (x, y, pad) => x > qrBox.x - pad && x < qrBox.x + qrPanel.w + pad && y > qrBox.y - pad && y < qrBox.y + qrPanel.h + pad;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cx = (c + 0.5) * cell + R(-0.22, 0.22) * cell;
      const cy = (r + 0.5) * cell + R(-0.22, 0.22) * cell;
      if (insideQR(cx, cy, cell * 0.35)) continue;
      const key = pick(MOTIF_KEYS);
      const s = cell * R(0.28, 0.46);
      const col = pick(INK);
      out.push(`<g transform="translate(${cx.toFixed(1)} ${cy.toFixed(1)}) rotate(${R(0, 360).toFixed(0)}) scale(${s.toFixed(1)})">${MOTIFS[key](col)}</g>`);
      // satellite dots
      const nd = Math.floor(R(1, 4));
      for (let d = 0; d < nd; d++) {
        const dx = cx + R(-0.5, 0.5) * cell, dy = cy + R(-0.5, 0.5) * cell;
        if (insideQR(dx, dy, 10)) continue;
        out.push(`<circle cx="${dx.toFixed(1)}" cy="${dy.toFixed(1)}" r="${R(2.5, 6).toFixed(1)}" fill="${pick(INK)}"/>`);
      }
    }
  }

  // Bold asymmetric border band: strong features right at the edges/corners,
  // which is where alignment error would otherwise be most visible.
  const bw = isMarker ? 26 : 22;
  out.push(`<rect x="${bw / 2}" y="${bw / 2}" width="${W - bw}" height="${H - bw}" fill="none" stroke="#3b0a14" stroke-width="${bw}"/>`);
  let pos = 0, k = 0;
  const perim = 2 * (W + H);
  while (pos < perim) {
    const len = R(14, 46);
    if (k++ % 2 === 0) {
      const p0 = pos, p1 = Math.min(pos + len, perim);
      const pt = (p) => (p < W ? [p, bw / 2] : p < W + H ? [W - bw / 2, p - W] : p < 2 * W + H ? [W - (p - W - H), H - bw / 2] : [bw / 2, H - (p - 2 * W - H)]);
      const [x0, y0] = pt(p0), [x1, y1] = pt(p1);
      out.push(`<line x1="${x0.toFixed(1)}" y1="${y0.toFixed(1)}" x2="${x1.toFixed(1)}" y2="${y1.toFixed(1)}" stroke="${pick(['#f4e9d8', '#c9a227', '#e8b04a'])}" stroke-width="${(bw * 0.38).toFixed(1)}"/>`);
    }
    pos += len;
  }
  // Unique corner glyphs (each corner different => no rotational ambiguity).
  const cornerKeys = ['star', 'diya', 'flower6', 'kalash'];
  [[bw * 2.4, bw * 2.4], [W - bw * 2.4, bw * 2.4], [W - bw * 2.4, H - bw * 2.4], [bw * 2.4, H - bw * 2.4]].forEach(([x, y], i) => {
    out.push(`<circle cx="${x}" cy="${y}" r="${bw * 1.5}" fill="#3b0a14"/><g transform="translate(${x} ${y}) scale(${bw * 1.05})">${MOTIFS[cornerKeys[i]]('#f4e9d8')}</g>`);
  });

  // QR panel
  const qr = QRCode.create(url, { errorCorrectionLevel: 'Q' });
  const n = qr.modules.size;
  const quiet = 2;
  const mod = qrSize / (n + quiet * 2);
  let qrPath = '';
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (qr.modules.get(x, y)) qrPath += `M${((x + quiet) * mod).toFixed(2)} ${((y + quiet) * mod).toFixed(2)}h${mod.toFixed(2)}v${mod.toFixed(2)}h-${mod.toFixed(2)}z`;
  const qx = qrBox.x + (qrPanel.w - qrSize) / 2;
  const qy = qrBox.y + 26;
  out.push(`<rect x="${qrBox.x}" y="${qrBox.y}" width="${qrPanel.w}" height="${qrPanel.h}" rx="18" fill="#3b0a14"/>`);
  out.push(`<rect x="${qx - 6}" y="${qy - 6}" width="${qrSize + 12}" height="${qrSize + 12}" rx="10" fill="#ffffff"/>`);
  out.push(`<path transform="translate(${qx} ${qy})" d="${qrPath}" fill="#14070a"/>`);
  const ty = qy + qrSize + (isMarker ? 34 : 40);
  const fs = isMarker ? 24 : 26;
  out.push(`<text x="${qrBox.x + qrPanel.w / 2}" y="${ty}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="${fs}" font-weight="700" fill="#f2cf73" letter-spacing="2">SCAN TO REVEAL</text>`);
  out.push(`<text x="${qrBox.x + qrPanel.w / 2}" y="${ty + fs * 1.15}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="${fs * 0.55}" fill="#f4e9d8" letter-spacing="1.5">AR DIWALI CANVAS · ${escapeXml(label || canvasId).toUpperCase()}</text>`);

  const body = out.join('\n');
  const physical = forCompile ? '' : ` width="${widthCm}cm" height="${heightCm}cm"`;
  return {
    svg: `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg"${physical} viewBox="0 0 ${W} ${H}" shape-rendering="geometricPrecision">\n<!-- AR Diwali Canvas tracking print · canvas=${escapeXml(canvasId)} · ${widthCm} x ${heightCm} cm · print at 100% scale, edge to edge, no margins -->\n${body}\n</svg>`,
    viewW: W,
    viewH: H,
  };
}

function escapeXml(s) {
  return String(s).replace(/[<>&'"]/g, (ch) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[ch]));
}

module.exports = { buildTargetSVG };
