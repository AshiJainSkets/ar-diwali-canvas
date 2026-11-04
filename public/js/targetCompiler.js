// Compiles a canvas's tracking print into a MindAR .mind target, in the browser.
// Used by the admin page (and by tools/compile-demo-target.mjs via headless Chromium).
import { Compiler } from '/vendor/mindar/mindar-image.prod.js';

export const COMPILE_WIDTH = 1200; // px — enough detail for 4×3 ft prints, compiles in ~30–90 s

export async function rasterizeSVG(svgText, width = COMPILE_WIDTH) {
  const blob = new Blob([svgText], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  try {
    const img = new Image();
    img.decoding = 'sync';
    await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error('Could not rasterize print SVG')); img.src = url; });
    const vb = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(svgText);
    const aspect = vb ? +vb[2] / +vb[1] : img.naturalHeight / img.naturalWidth;
    const c = document.createElement('canvas');
    c.width = width;
    c.height = Math.round(width * aspect);
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0, c.width, c.height);
    return c;
  } finally {
    URL.revokeObjectURL(url);
  }
}

/** @returns {Promise<{buffer: Uint8Array, preview: HTMLCanvasElement}>} */
export async function compileCanvasTarget(canvasId, onProgress = () => {}) {
  const res = await fetch(`/api/canvas/${encodeURIComponent(canvasId)}/print.svg?compile=1&t=${Date.now()}`);
  if (!res.ok) throw new Error('Could not load tracking print');
  const svg = await res.text();
  const raster = await rasterizeSVG(svg);
  const compiler = new Compiler();
  await compiler.compileImageTargets([raster], (p) => onProgress(Math.min(100, p)));
  const buffer = compiler.exportData();
  return { buffer, preview: raster };
}
