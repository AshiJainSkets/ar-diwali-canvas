// Headless compile of a canvas tracking target (same code path as the admin page).
// Usage: node tools/compile-target.mjs <baseUrl> <canvasId> <adminToken> [--seed]
//   --seed  also writes server/seed/demo.mind + demo.json (ships the precompiled demo)
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright'); // devDependency: npm i -D playwright && npx playwright install chromium
import fs from 'node:fs';
import path from 'node:path';

const [base = 'http://localhost:8080', id = 'demo', token = '', ...flags] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage();
page.on('console', (m) => { if (/error/i.test(m.type())) console.log('[page]', m.text()); });
await page.goto(`${base}/admin`, { waitUntil: 'domcontentloaded' });
const t0 = Date.now();
const out = await page.evaluate(async (id) => {
  const { compileCanvasTarget } = await import('/js/targetCompiler.js');
  let last = 0;
  const { buffer } = await compileCanvasTarget(id, (p) => { if (p - last > 10) { last = p; console.log('progress ' + p.toFixed(0)); } });
  return Array.from(buffer);
}, id);
const buf = Buffer.from(out);
console.log(`compiled ${id}: ${buf.length} bytes in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
const canvasRes = await page.evaluate(async (id) => (await fetch(`/api/canvas/${id}`)).json(), id);
if (token) {
  const r = await fetch(`${base}/api/admin/canvases/${id}/target?url=${encodeURIComponent(canvasRes.url)}`, {
    method: 'POST', headers: { 'x-admin-token': token, 'content-type': 'application/octet-stream' }, body: buf,
  });
  console.log('upload:', r.status, (await r.json()).targetUrl);
}
if (flags.includes('--seed')) {
  const dir = path.join(path.dirname(new URL(import.meta.url).pathname), '..', 'server', 'seed');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'demo.mind'), buf);
  fs.writeFileSync(path.join(dir, 'demo.json'), JSON.stringify({ url: canvasRes.url }, null, 2));
  console.log('seed written');
}
await browser.close();
