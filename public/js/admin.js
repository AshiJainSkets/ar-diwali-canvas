// Admin: manage canvases, QR codes, tracking prints and compiled targets.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const TOKEN_KEY = 'ardc-admin-token';
let token = (() => { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } })();
let catalog, canvases = [], editing = null, pickedPainting = 'traditional-1', info = {};

async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { 'x-admin-token': token, ...(opts.body && !(opts.body instanceof Uint8Array) ? { 'content-type': 'application/json' } : {}), ...(opts.headers || {}) } });
  if (r.status === 401) { showLogin('Token rejected.'); throw new Error('unauthorised'); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

function showLogin(err = '') {
  $('#login').hidden = false; $('#main').hidden = true; $('#logout').hidden = true;
  $('#login-err').textContent = err;
}
$('#login-btn').onclick = async () => {
  token = $('#token').value.trim();
  try { await init(); try { localStorage.setItem(TOKEN_KEY, token); } catch {} } catch {}
};
$('#token').addEventListener('keydown', (e) => e.key === 'Enter' && $('#login-btn').click());
$('#logout').onclick = () => { try { localStorage.removeItem(TOKEN_KEY); } catch {} token = ''; showLogin(); };

async function init() {
  info = await api('/api/admin/verify');
  $('#login').hidden = true; $('#main').hidden = false; $('#logout').hidden = false;
  catalog = catalog || (await (await fetch('/paintings/catalog.json')).json());
  baseWarning();
  buildForm();
  await refresh();
}

function baseWarning() {
  const w = $('#base-warn');
  const local = /localhost|127\.0\.0\.1|0\.0\.0\.0|^https?:\/\/(10|192\.168|172\.(1[6-9]|2\d|3[01]))\./.test(info.baseUrl);
  const insecure = info.baseUrl.startsWith('http://');
  if (!local && !insecure && info.publicBaseUrlSet) { w.hidden = true; return; }
  w.hidden = false;
  w.innerHTML = `<b>QR codes currently point to <code>${esc(info.baseUrl)}</code>.</b><br>
    ${insecure ? 'Phones only allow the camera on <b>https</b>. ' : ''}${local ? 'This address only works on your own network. ' : ''}
    Before printing, deploy the server on a public HTTPS domain and set <code>PUBLIC_BASE_URL</code> (e.g. <code>https://diwali.example.com</code>), then regenerate each canvas's tracking target.`;
}

// ------------------------------------------------------------------ form
function buildForm() {
  const f = $('#form');
  $('#pick').innerHTML = catalog.paintings.map((p) => `<button type="button" data-id="${p.id}" aria-pressed="${p.id === pickedPainting}"><img src="${p.thumb}" alt="" loading="lazy"><span>${esc(p.title)}</span></button>`).join('');
  $('#pick').onclick = (e) => { const b = e.target.closest('button'); if (!b) return; pickedPainting = b.dataset.id; [...$('#pick').children].forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.id === pickedPainting))); };
  $('#cat-checks').innerHTML = catalog.categories.map((c) => `<label><input type="checkbox" value="${c.id}">${esc(c.name)}</label>`).join('');
  const sync = () => {
    f.querySelector('[data-custom]').hidden = f.elements.size.value !== 'custom';
    const marker = f.elements.mode.value === 'marker';
    f.querySelectorAll('[data-marker]').forEach((el) => (el.hidden = !marker));
    f.querySelector('[data-mode-help]').textContent = marker
      ? 'Prints a smaller plaque (with QR) placed inside the canvas. Canvas stays mostly blank; edge accuracy is lower.'
      : 'Prints a pattern covering the whole canvas. Most accurate: the painting corners lock to the real corners.';
  };
  f.elements.size.onchange = f.elements.mode.onchange = sync;
  sync();
  f.onsubmit = async (e) => {
    e.preventDefault();
    const [w, h] = f.elements.size.value === 'custom' ? [+f.elements.widthCm.value, +f.elements.heightCm.value] : f.elements.size.value.split('x').map(Number);
    const body = {
      name: f.elements.name.value.trim(), widthCm: w, heightCm: h, mode: f.elements.mode.value,
      target: { wCm: +f.elements.tW.value, hCm: +f.elements.tH.value, xCm: +f.elements.tX.value, yCm: +f.elements.tY.value },
      tracking: f.elements.tracking.value, allowSwitch: f.elements.allowSwitch.value === 'true', paintingId: pickedPainting,
      categories: [...$('#cat-checks').querySelectorAll('input:checked')].map((i) => i.value),
    };
    try {
      if (editing) await api(`/api/admin/canvases/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      else await api('/api/admin/canvases', { method: 'POST', body: JSON.stringify({ ...body, id: f.elements.id.value.trim() || undefined }) });
      resetForm();
      await refresh();
    } catch (err) { alert(err.message); }
  };
  $('#cancel-edit').onclick = resetForm;
}

function resetForm() {
  editing = null;
  const f = $('#form'); f.reset(); f.elements.id.disabled = false;
  $('#form-title').textContent = 'New canvas'; $('#save-btn').textContent = 'Create canvas'; $('#cancel-edit').hidden = true;
  $('#cat-checks').querySelectorAll('input').forEach((i) => (i.checked = false));
  f.elements.size.dispatchEvent(new Event('change'));
}

function editCanvas(c) {
  editing = c.id;
  const f = $('#form');
  f.elements.name.value = c.name; f.elements.id.value = c.id; f.elements.id.disabled = true;
  const preset = [...f.elements.size.options].find((o) => o.value === `${c.widthCm}x${c.heightCm}`);
  f.elements.size.value = preset ? preset.value : 'custom';
  f.elements.widthCm.value = c.widthCm; f.elements.heightCm.value = c.heightCm;
  f.elements.mode.value = c.mode; f.elements.tracking.value = c.tracking; f.elements.allowSwitch.value = String(c.allowSwitch);
  f.elements.tW.value = c.target.wCm; f.elements.tH.value = c.target.hCm; f.elements.tX.value = c.target.xCm; f.elements.tY.value = c.target.yCm;
  pickedPainting = c.paintingId;
  [...$('#pick').children].forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.id === pickedPainting)));
  $('#cat-checks').querySelectorAll('input').forEach((i) => (i.checked = c.categories.includes(i.value)));
  f.elements.size.dispatchEvent(new Event('change'));
  $('#form-title').textContent = `Edit “${c.name}”`; $('#save-btn').textContent = 'Save changes'; $('#cancel-edit').hidden = false;
  window.scrollTo({ top: $('#form').offsetTop - 80, behavior: 'smooth' });
}

// ------------------------------------------------------------------ list
async function refresh() {
  canvases = await api('/api/admin/canvases');
  const list = $('#list');
  if (!canvases.length) { list.innerHTML = '<p class="muted">No canvases yet.</p>'; return; }
  list.innerHTML = canvases.map((c) => {
    const p = catalog.paintings.find((x) => x.id === c.paintingId);
    const target = !c.targetUrl ? '<span class="badge bad">Tracking target not generated</span>'
      : c.targetStale ? '<span class="badge warn">QR URL changed — regenerate target & reprint</span>'
        : `<span class="badge ok">Tracking target v${c.targetVersion} ready</span>`;
    const size = `${c.widthCm.toFixed(1)} × ${c.heightCm.toFixed(1)} cm`;
    const printSize = `${c.target.wCm.toFixed(1)} × ${c.target.hCm.toFixed(1)} cm`;
    const v = encodeURIComponent(c.updatedAt);
    return `<article class="panel cv" data-id="${c.id}" style="margin:0">
      <div class="qr"><img src="/api/canvas/${c.id}/qr.svg?v=${v}" alt="QR code for ${esc(c.name)}"></div>
      <div>
        <h3>${esc(c.name)}</h3>
        <div class="sub">ID <b>${esc(c.id)}</b> · <a href="${esc(c.url)}" target="_blank">${esc(c.url)}</a></div>
        <div class="badges">
          ${target}
          <span class="badge">${c.mode === 'full' ? 'Full-canvas print' : 'Marker plaque'}</span>
          <span class="badge">Canvas ${size}</span>
          <span class="badge">Print ${printSize}</span>
          <span class="badge">Painting: ${esc(p?.title || c.paintingId)}</span>
          <span class="badge">${c.allowSwitch ? (c.categories.length ? c.categories.length + ' categories' : 'All categories') : 'Fixed painting'}</span>
        </div>
        <div class="btns">
          <button class="btn small primary" data-a="compile">${c.targetUrl ? 'Regenerate' : 'Generate'} tracking target</button>
          <a class="btn small" href="/api/canvas/${c.id}/print.svg?download=1">Tracking print (SVG)</a>
          <a class="btn small" href="/api/canvas/${c.id}/qr.png?size=2048&download=1">QR PNG</a>
          <a class="btn small" href="/api/canvas/${c.id}/qr.svg?download=1">QR SVG</a>
          <a class="btn small" href="/c/${c.id}" target="_blank">Open AR</a>
          <a class="btn small" href="/c/${c.id}?calibrate=1" target="_blank">Calibrate</a>
          <button class="btn small" data-a="copy">Copy link</button>
          <button class="btn small" data-a="edit">Edit</button>
          ${c.id === 'demo' ? '' : '<button class="btn small" data-a="delete" style="color:var(--danger)">Delete</button>'}
        </div>
        <div class="prog" hidden><i></i></div>
        <div class="note" data-msg></div>
      </div>
    </article>`;
  }).join('');
  list.onclick = onListClick;
}

async function onListClick(e) {
  const btn = e.target.closest('[data-a]'); if (!btn) return;
  const card = btn.closest('[data-id]'); const c = canvases.find((x) => x.id === card.dataset.id);
  const msg = card.querySelector('[data-msg]');
  if (btn.dataset.a === 'edit') editCanvas(c);
  if (btn.dataset.a === 'copy') { await navigator.clipboard?.writeText(c.url); msg.textContent = 'Link copied.'; }
  if (btn.dataset.a === 'delete') {
    if (!confirm(`Delete canvas “${c.name}”? Its QR code will stop working.`)) return;
    await api(`/api/admin/canvases/${c.id}`, { method: 'DELETE' }); await refresh();
  }
  if (btn.dataset.a === 'compile') {
    const bar = card.querySelector('.prog'); bar.hidden = false;
    btn.disabled = true; msg.textContent = 'Loading compiler…';
    try {
      const { compileCanvasTarget } = await import('/js/targetCompiler.js');
      const t0 = performance.now();
      const { buffer } = await compileCanvasTarget(c.id, (p) => { bar.firstElementChild.style.width = p + '%'; msg.textContent = `Analysing print features… ${p.toFixed(0)} %`; });
      msg.textContent = 'Uploading…';
      await api(`/api/admin/canvases/${c.id}/target?url=${encodeURIComponent(c.url)}`, { method: 'POST', body: buffer, headers: { 'content-type': 'application/octet-stream' } });
      msg.textContent = `Done in ${((performance.now() - t0) / 1000).toFixed(0)} s. Download the tracking print and print it at 100 %.`;
      await refresh();
    } catch (err) {
      msg.textContent = 'Compile failed: ' + err.message; btn.disabled = false;
    }
  }
}

if (token) init().catch(() => {}); else showLogin();
