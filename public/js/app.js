// AR Diwali Canvas — app shell: welcome, gallery, AR screen, error handling.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};

const params = new URLSearchParams(location.search);
const pathMatch = location.pathname.match(/^\/c\/([^/?#]+)/);
const viaQR = !!pathMatch;
const canvasId = decodeURIComponent(pathMatch?.[1] || params.get('canvas') || 'demo');
const calibrate = params.get('calibrate') === '1';
const debug = params.get('debug') === '1';
let hd = params.get('hd') === '1';

const state = { canvas: null, catalog: null, paintings: [], selected: null, cat: 'all', session: null, returnTo: 'welcome' };

// ------------------------------------------------------------------ boot
boot().catch((e) => showMessage({ icon: 'alert', title: 'Something went wrong', text: esc(e.message || e), actions: [{ label: 'Reload', primary: true, onClick: () => location.reload() }] }));

async function boot() {
  const [canvasRes, catalogRes] = await Promise.all([
    fetch(`/api/canvas/${encodeURIComponent(canvasId)}`),
    fetch('/paintings/catalog.json', { cache: 'no-cache' }),
  ]);
  if (canvasRes.status === 404) {
    return showMessage({ icon: 'alert', title: 'Canvas not found', text: `There is no canvas with the ID <b>${esc(canvasId)}</b>. Check the QR code or ask the organiser.`, actions: [{ label: 'Open the demo', primary: true, onClick: () => (location.href = '/') }] });
  }
  if (!canvasRes.ok || !catalogRes.ok) throw new Error('Could not reach the server. Check your connection and try again.');
  state.canvas = await canvasRes.json();
  state.catalog = await catalogRes.json();
  const allowed = state.canvas.categories?.length ? new Set(state.canvas.categories) : null;
  state.paintings = state.catalog.paintings.filter((p) => !allowed || allowed.has(p.category) || p.id === state.canvas.paintingId);
  const want = params.get('painting') || (state.canvas.allowSwitch ? store.get(`ardc:${canvasId}:painting`) : null) || state.canvas.paintingId;
  state.selected = state.paintings.find((p) => p.id === want) || state.paintings.find((p) => p.id === state.canvas.paintingId) || state.paintings[0];

  renderWelcome();
  renderGallery();
  // Warm up the heavy AR bundle (three + MindAR + tfjs) while the user reads.
  const warm = () => import('./ar.js').catch(() => {});
  if ('requestIdleCallback' in window) requestIdleCallback(warm, { timeout: 2000 });
  else setTimeout(warm, 600);

  if (viaQR || params.get('autostart') === '1') startAR();
  else show('welcome');
}

// ------------------------------------------------------------------ screens
function show(id) {
  for (const s of document.querySelectorAll('.screen')) s.hidden = s.id !== id;
  const el = document.getElementById(id);
  el.classList.remove('fade-in'); void el.offsetWidth; el.classList.add('fade-in');
  if (id === 'welcome' || id === 'gallery') state.returnTo = id;
}

function renderWelcome() {
  const c = state.canvas;
  $('#hero-img').src = state.selected.preview;
  const feet = (cm) => { const f = cm / 30.48; return Math.abs(f - Math.round(f)) < 0.05 ? String(Math.round(f)) : f.toFixed(1); };
  $('#canvas-chip').innerHTML = `<span class="pill"><span class="dot"></span><b>${esc(c.name)}</b></span><span class="pill">${feet(c.widthCm)} × ${feet(c.heightCm)} ft canvas</span>`;
  $('#demo-note').hidden = c.id !== 'demo';
  $('#btn-gallery').hidden = !c.allowSwitch;
  $('#btn-start').onclick = () => startAR();
  $('#btn-gallery').onclick = () => show('gallery');
}

function catName(id) { return state.catalog.categories.find((c) => c.id === id)?.name || id; }

function renderGallery() {
  const cats = state.catalog.categories.filter((c) => state.paintings.some((p) => p.category === c.id));
  const catBtns = [{ id: 'all', name: 'All' }, ...cats];
  const nav = $('#cats');
  nav.innerHTML = catBtns.map((c) => `<button class="cat" data-cat="${c.id}" aria-pressed="${c.id === state.cat}">${esc(c.name)}</button>`).join('');
  nav.onclick = (e) => {
    const b = e.target.closest('.cat'); if (!b) return;
    state.cat = b.dataset.cat;
    renderGallery();
    $('#gallery').scrollTo({ top: 0, behavior: 'smooth' });
  };
  const grid = $('#grid');
  const list = state.cat === 'all' ? state.paintings : state.paintings.filter((p) => p.category === state.cat);
  let html = '', lastCat = null;
  for (const p of list) {
    if (state.cat === 'all' && p.category !== lastCat) {
      lastCat = p.category;
      const cat = state.catalog.categories.find((c) => c.id === p.category);
      html += `<div class="cat-head"><h3>${esc(cat?.name)}</h3><p>${esc(cat?.description)}</p></div>`;
    }
    html += cardHTML(p);
  }
  grid.innerHTML = html;
  grid.onclick = (e) => { const c = e.target.closest('.card'); if (c) openDetail(c.dataset.id, false); };
  updateDock();
  $('#gallery-back').onclick = () => show('welcome');
  $('#dock-start').onclick = () => startAR();
}

function cardHTML(p) {
  const sel = p.id === state.selected.id;
  return `<button class="card" role="option" data-id="${p.id}" aria-selected="${sel}">
    <div class="frame"><img loading="lazy" decoding="async" src="${p.thumb}" alt="${esc(p.title)}"></div>
    <span class="check"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3"><path d="m5 12 5 5L20 7"/></svg></span>
    <div class="meta"><div class="t">${esc(p.title)}</div><div class="m">${esc(p.medium)}</div></div>
  </button>`;
}

function updateDock() {
  $('#dock-img').src = state.selected.thumb;
  $('#dock-title').textContent = state.selected.title;
  $('#fab-img').src = state.selected.thumb;
  for (const c of document.querySelectorAll('.card')) c.setAttribute('aria-selected', String(c.dataset.id === state.selected.id));
}

function selectPainting(id) {
  const p = state.paintings.find((x) => x.id === id);
  if (!p) return;
  // a different painting starts static: "Bring to Life" switches off and must be tapped again
  if (state.animating && p.id !== state.selected?.id) {
    state.animating = false;
    if (state.session) state.session.setAnimating(false);
    setMagicButton(false);
  }
  state.selected = p;
  store.set(`ardc:${canvasId}:painting`, p.id);
  $('#hero-img').src = p.preview;
  updateDock();
  const img = new Image(); img.src = p.albedo; // prefetch
  if (state.session) state.session.setPainting(p).catch(() => toast('Could not load painting'));
}

// ------------------------------------------------------------------ sheets
function openSheet(id) {
  $('#backdrop').classList.add('open');
  $(id).classList.add('open');
  $('#backdrop').onclick = closeSheets;
}
function closeSheets() {
  $('#backdrop').classList.remove('open');
  for (const s of document.querySelectorAll('.sheet')) s.classList.remove('open');
}

function openDetail(id, inAR) {
  const p = state.paintings.find((x) => x.id === id);
  const isSel = p.id === state.selected.id;
  $('#detail').innerHTML = `
    <div class="frame"><img src="${p.preview}" alt="${esc(p.title)}"></div>
    <h3>${esc(p.title)}</h3>
    <div class="med">${esc(p.medium)} · ${esc(catName(p.category))}</div>
    <p>${esc(p.description)}</p>
    <div class="row">
      ${inAR ? '<button class="btn block" data-act="close">Close</button>' : `<button class="btn block" data-act="select">${isSel ? 'Selected ✓' : 'Select painting'}</button>
      <button class="btn primary block" data-act="ar">View in AR</button>`}
    </div>`;
  $('#detail').onclick = (e) => {
    const a = e.target.closest('[data-act]')?.dataset.act;
    if (a === 'select') { selectPainting(p.id); closeSheets(); }
    if (a === 'ar') { selectPainting(p.id); closeSheets(); startAR(); }
    if (a === 'close') closeSheets();
  };
  openSheet('#sheet-detail');
}

function openPicker() {
  const cats = state.catalog.categories.filter((c) => state.paintings.some((p) => p.category === c.id));
  let cur = state.selected.category;
  const render = () => {
    $('#picker-cats').innerHTML = cats.map((c) => `<button class="cat" data-cat="${c.id}" aria-pressed="${c.id === cur}">${esc(c.name)}</button>`).join('');
    $('#picker').innerHTML = state.paintings.filter((p) => p.category === cur).map(cardHTML).join('');
  };
  render();
  $('#picker-cats').onclick = (e) => { const b = e.target.closest('.cat'); if (b) { cur = b.dataset.cat; render(); $('#picker').scrollTo({ left: 0 }); } };
  $('#picker').onclick = (e) => {
    const c = e.target.closest('.card'); if (!c) return;
    selectPainting(c.dataset.id);
    closeSheets();
  };
  openSheet('#sheet-picker');
}

// ------------------------------------------------------------------ AR
let toastTimer;
function toast(text, ms = 2200) {
  const t = $('#toast');
  t.textContent = text; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), ms);
}
function setStatus(text, locked) {
  $('#status-text').textContent = text;
  $('#status').classList.toggle('locked', !!locked);
}
function setScanHint(title, text) {
  const box = $('#scan-text');
  const actions = box.querySelector('.hint-actions');
  box.innerHTML = `<b>${esc(title)}</b><span>${esc(text)}</span>`;
  if (actions) box.appendChild(actions);
}

async function startAR() {
  if (state.session) return;
  closeSheets();
  if (!state.canvas.targetUrl) {
    return showMessage({ icon: 'alert', title: 'Canvas not set up yet', text: 'This canvas has no tracking target yet. An administrator needs to generate its tracking print in the admin panel.', actions: backActions() });
  }
  if (isInAppBrowser()) toast('Tip: for best results open this page in Safari or Chrome', 4000);
  show('ar');
  $('#veil').classList.remove('hide');
  $('#veil-text').textContent = 'Opening camera…';
  $('#scan-guide').classList.remove('hide');
  $('#scan-text').hidden = false;
  setScanHint('Point your camera at the canvas', 'Fit the whole canvas in view so it fills most of the screen — about 2 m from a 4 ft canvas, closer for a smaller print or monitor.');
  setStatus('Starting…');
  $('#ar-pick').hidden = !state.canvas.allowSwitch;
  $('#ar-magic').hidden = true;
  $('#fab-img').src = state.selected.thumb;

  let ARSession, CameraError;
  try {
    ({ ARSession, CameraError } = await import('./ar.js'));
  } catch (e) {
    return showMessage({ icon: 'alert', title: 'Could not load AR', text: 'Your browser could not load the AR engine. Check your connection, or try an up-to-date Safari or Chrome.', actions: [{ label: 'Retry', primary: true, onClick: () => location.reload() }] });
  }
  const s = new ARSession({ container: $('#ar-stage'), canvas: { ...state.canvas, hd }, onState: onARState });
  state.session = s;
  window.__ar = s; // diagnostics
  try {
    await s.start(state.selected);
    wireARControls(s);
    if (calibrate) buildCalibration(s);
    if (debug) showDiagnostics(s);
  } catch (e) {
    s.stop();
    state.session = null;
    showCameraError(e, CameraError);
  }
}

let searchTimer;
function onARState(st, info) {
  switch (st) {
    case 'loading':
      $('#veil-text').textContent = 'Loading canvas tracking…';
      break;
    case 'scanning':
      $('#veil').classList.add('hide');
      $('#scan-guide').classList.remove('hide');
      $('#scan-text').hidden = false;
      setScanHint('Point your camera at the canvas', 'Fit the whole canvas in view so it fills most of the screen — about 2 m from a 4 ft canvas, closer for a smaller print or monitor.');
      setStatus('Looking for the canvas');
      break;
    case 'tracking':
      clearTimeout(searchTimer);
      $('#scan-guide').classList.add('hide');
      $('#scan-text').hidden = true;
      setStatus('Canvas locked', true);
      if (navigator.vibrate) navigator.vibrate(12);
      break;
    case 'searching':
      setStatus('Re-finding the canvas…');
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        if (state.session?.state !== 'searching') return;
        $('#scan-guide').classList.remove('hide');
        $('#scan-text').hidden = false;
        setScanHint('Lost sight of the canvas', 'Bring the frame back into view — the painting will snap back.');
      }, 1500);
      break;
    case 'hint':
      if (state.session?.state === 'tracking') break;
      if (info.dark) setScanHint('It’s quite dark here', 'Turn on a light near the canvas, or move closer.');
      else if (info.scanningMs > 12000) {
        setScanHint('Still looking…', 'Make sure the screen shows the tracking print (the patterned page with the QR code). Fit all four corners in view, hold steady, avoid glare.');
        addHintActions();
      } else setScanHint('Point your camera at the canvas', 'Hold the phone steady with the whole canvas in view.');
      break;
    case 'needs-restart':
      // camera changed resolution after start — restart the tracker with the real size
      if ((state.autoRestarts = (state.autoRestarts || 0) + 1) > 2) break; // never loop
      setTimeout(() => { const s = state.session; if (!s) return; s.stop(); state.session = null; startAR(); }, 50);
      break;
    case 'painting-ready':
      if (state.session?.state === 'tracking') toast(info.painting.title);
      break;
    case 'interrupted':
      showMessage({ icon: 'camera', title: 'Camera paused', text: 'The camera stopped while the page was in the background.', actions: [{ label: 'Resume AR', primary: true, onClick: () => { exitAR(); startAR(); } }, ...backActions()] });
      break;
  }
}

function setMagicButton(on) {
  const b = $('#ar-magic');
  b.setAttribute('aria-pressed', String(!!on));
  b.querySelector('.magic-label').textContent = on ? 'Pause ❚❚' : 'Bring to Life ✨';
  b.title = on ? 'Pause the animation' : 'Bring the painting to life';
}

function wireARControls(s) {
  const magic = $('#ar-magic');
  magic.hidden = false;
  setMagicButton(state.animating);
  if (state.animating) s.setAnimating(true);       // keep "alive" mode when AR restarts
  magic.onclick = () => {
    state.animating = !state.animating;
    s.setAnimating(state.animating);
    setMagicButton(state.animating);
    if (state.animating && s.state !== 'tracking') toast('Point at the canvas to see it come alive ✨');
  };
  $('#ar-exit').onclick = exitAR;
  $('#ar-reset').onclick = () => { s.resetTracking(); toast('Tracking reset — point at the canvas'); };
  $('#ar-pick').onclick = openPicker;
  $('#ar-info').onclick = () => openDetail(state.selected.id, true);
}

function exitAR() {
  closeSheets();
  clearTimeout(searchTimer);
  state.session?.stop();
  state.session = null;
  $('#calib').hidden = true;
  show(state.returnTo);
}
window.addEventListener('pagehide', () => state.session?.stop());

// Rotating the phone swaps the camera frame's axes; the tracker must restart for the new
// orientation (MindAR's camera model is fixed at start). Keep the chosen painting.
let lastPortrait = innerHeight > innerWidth, rotTimer;
window.addEventListener('resize', () => {
  clearTimeout(rotTimer);
  rotTimer = setTimeout(() => {
    const portrait = innerHeight > innerWidth;
    if (portrait === lastPortrait) return;
    lastPortrait = portrait;
    const s = state.session;
    if (!s || ['starting', 'loading', 'stopped'].includes(s.state)) return;
    s.stop(); state.session = null;
    startAR();
  }, 450);
});

function backActions() {
  return [{ label: 'Back', onClick: () => { exitAR(); show(state.returnTo); } }];
}

function isInAppBrowser() { return /FBAN|FBAV|Instagram|Line\/|; wv\)|Snapchat|LinkedInApp/i.test(navigator.userAgent); }
const isIOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

function showCameraError(e, CameraError) {
  const kind = e instanceof CameraError ? e.kind : 'unknown';
  const retry = { label: 'Try again', primary: true, onClick: () => { show(state.returnTo); startAR(); } };
  const M = {
    denied: {
      icon: 'camera', title: 'Camera access is off',
      text: `AR needs your camera to see the canvas. Nothing is recorded or uploaded.${isIOS()
        ? '<ol><li>Tap <b>aA</b> in Safari’s address bar → <b>Website Settings</b></li><li>Set <b>Camera</b> to <b>Allow</b></li><li>Come back and tap <b>Try again</b></li></ol>'
        : '<ol><li>Tap the <b>lock / settings icon</b> next to the address</li><li>Open <b>Permissions</b> → <b>Camera</b> → <b>Allow</b></li><li>Come back and tap <b>Try again</b></li></ol>'}`,
    },
    nocamera: { icon: 'camera', title: 'No camera found', text: 'We couldn’t find a rear camera on this device. Try a phone or tablet.' },
    busy: { icon: 'camera', title: 'Camera is busy', text: 'Another app or tab is using the camera. Close it and try again.' },
    insecure: { icon: 'alert', title: 'Secure connection required', text: 'Browsers only allow the camera on <b>https://</b> pages. Open this experience through its https link.' },
    unsupported: { icon: 'alert', title: 'Browser not supported', text: isInAppBrowser() ? 'This in-app browser blocks the camera. Tap ••• and choose <b>Open in Safari / Chrome</b>.' : 'Please use a recent version of Safari (iOS 15+) or Chrome (Android 9+).' },
    notarget: { icon: 'alert', title: 'Canvas not set up yet', text: 'This canvas has no tracking target. Ask the administrator to compile it in the admin panel.' },
    tracker: { icon: 'alert', title: 'AR could not start', text: 'Your device’s graphics (WebGL) could not start the tracker. Close other tabs and try again, or try another browser.' },
    unknown: { icon: 'alert', title: 'AR could not start', text: esc(e?.detail || e?.message || 'Unknown error.') },
  };
  const m = M[kind] || M.unknown;
  showMessage({ ...m, actions: kind === 'notarget' || kind === 'nocamera' ? backActions() : [retry, ...backActions()] });
}

const ICONS = {
  camera: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="4"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5M12 18v.5"/></svg>',
};
function showMessage({ icon = 'alert', title, text, actions = [] }) {
  const box = $('#message-box');
  box.innerHTML = `<div class="ic-big">${ICONS[icon] || ''}</div><h2>${esc(title)}</h2><div>${text}</div><div class="actions"></div>`;
  const wrap = box.querySelector('.actions');
  for (const a of actions) {
    const b = document.createElement('button');
    b.className = `btn block${a.primary ? ' primary' : ''}`;
    b.textContent = a.label;
    b.onclick = a.onClick;
    wrap.appendChild(b);
  }
  if (state.session) { state.session.stop(); state.session = null; }
  show('message');
}

function addHintActions() {
  const box = $('#scan-text');
  if (box.querySelector('.hint-actions')) return;
  const row = document.createElement('div');
  row.className = 'hint-actions';
  row.style.cssText = 'display:flex;gap:8px;justify-content:center;margin-top:10px;flex-wrap:wrap';
  row.innerHTML = `<button class="btn small" data-h="diag">Show diagnostics</button><button class="btn small" data-h="cam">${hd ? 'Use standard camera' : 'Try HD camera'}</button>`;
  row.onclick = (e) => {
    const h = e.target.dataset.h;
    if (h === 'diag' && state.session) showDiagnostics(state.session);
    if (h === 'cam') { hd = !hd; const s = state.session; if (s) { s.stop(); state.session = null; } startAR(); }
  };
  box.appendChild(row);
}

// ------------------------------------------------------------------ diagnostics (?debug=1 or from the hint)
let diagTimer;
function showDiagnostics(s) {
  const panel = $('#calib');
  panel.hidden = false;
  panel.innerHTML = `<h4>Tracking diagnostics</h4>
    <canvas id="diag-view" style="width:100%;border-radius:8px;background:#000;display:block;margin-bottom:8px"></canvas>
    <pre id="diag-text" style="white-space:pre-wrap;font-size:11px;line-height:1.35;margin:0;color:#e7d9cb"></pre>
    <div class="row"><button class="btn small" data-d="copy">Copy</button><button class="btn small" data-d="close">Close</button></div>
    <p style="color:var(--muted);margin:8px 0 0">The picture above is exactly what the tracker sees. Take a screenshot of this panel if the canvas isn’t found.</p>`;
  let lastFrames = 0, lastT = performance.now();
  const tick = () => {
    if (!state.session || panel.hidden) return clearInterval(diagTimer);
    const d = s.diagnostics();
    const now = performance.now();
    const fps = ((d.frames - lastFrames) * 1000) / (now - lastT);
    lastFrames = d.frames; lastT = now;
    $('#diag-text').textContent =
      `state: ${d.state}   tracker fps: ${fps.toFixed(1)}\nvideo: ${d.video}\ntracker input: ${d.trackerInput}  target: ${d.target}\n` +
      `features: ${d.lastFeatures} (max ${d.maxFeatures})  detections: ${d.detects}\nmatch tries: ${d.matchCalls}  matches: ${d.matches}  resizes: ${d.videoResizes}\n` +
      `${d.homography}\nbackend: ${d.backend}  gpu: ${d.gpu}\n${hd ? 'camera: HD\n' : 'camera: standard\n'}${d.ua}`;
    const src = s.trackerInputCanvas(), view = $('#diag-view');
    if (src && src.width) {
      const w = 240, h = Math.round((w * src.height) / src.width);
      if (view.width !== w || view.height !== h) { view.width = w; view.height = h; }
      try { view.getContext('2d').drawImage(src, 0, 0, w, h); } catch {}
    }
  };
  clearInterval(diagTimer);
  diagTimer = setInterval(tick, 700);
  tick();
  panel.onclick = (e) => {
    const a = e.target.dataset.d;
    if (a === 'close') { panel.hidden = true; clearInterval(diagTimer); }
    if (a === 'copy') navigator.clipboard?.writeText($('#diag-text').textContent).then(() => toast('Diagnostics copied'));
  };
}

// ------------------------------------------------------------------ calibration (admin, ?calibrate=1)
function buildCalibration(s) {
  const panel = $('#calib');
  const cal = { ...state.canvas.calibration };
  panel.hidden = false;
  const rows = [
    ['dxCm', 'Shift X', -15, 15, 0.1, 'cm'], ['dyCm', 'Shift Y', -15, 15, 0.1, 'cm'],
    ['scale', 'Scale', 0.9, 1.1, 0.001, '×'], ['rotDeg', 'Rotate', -5, 5, 0.05, '°'],
  ];
  panel.innerHTML = `<h4>Alignment calibration</h4>
    ${rows.map(([k, l, mn, mx, st]) => `<label>${l}<input type="range" data-k="${k}" min="${mn}" max="${mx}" step="${st}" value="${cal[k]}"><output data-o="${k}"></output></label>`).join('')}
    <label>Tracking<select data-k="tracking" style="grid-column: span 2">${['stable', 'balanced', 'responsive'].map((t) => `<option ${t === state.canvas.tracking ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
    <div class="row">
      <button class="btn small" data-a="guides">Guides: on</button>
      <button class="btn small" data-a="peek">Peek: off</button>
      <button class="btn small" data-a="zero">Reset</button>
      <button class="btn small primary" data-a="save">Save</button>
    </div>
    <p style="color:var(--muted);margin:8px 0 0">Cyan dashed = tracked print · Gold = painting edge. Use <b>Peek</b> to see the real frame through the painting, then nudge until the gold edge sits on the canvas edge.</p>`;
  const fmt = () => rows.forEach(([k, , , , , u]) => { panel.querySelector(`[data-o="${k}"]`).textContent = (+cal[k]).toFixed(k === 'scale' ? 3 : 1) + u; });
  fmt();
  s.setGuides(true);
  let guides = true, peek = false;
  panel.oninput = (e) => {
    const k = e.target.dataset.k; if (!k) return;
    if (k === 'tracking') { s.setTracking(e.target.value); state.canvas.tracking = e.target.value; return; }
    cal[k] = +e.target.value; s.setCalibration(cal); fmt();
  };
  panel.onclick = async (e) => {
    const a = e.target.dataset.a; if (!a) return;
    if (a === 'guides') { guides = !guides; s.setGuides(guides); e.target.textContent = `Guides: ${guides ? 'on' : 'off'}`; }
    if (a === 'peek') { peek = !peek; s.setPeek(peek); e.target.textContent = `Peek: ${peek ? 'on' : 'off'}`; }
    if (a === 'zero') { Object.assign(cal, { dxCm: 0, dyCm: 0, scale: 1, rotDeg: 0 }); panel.querySelectorAll('input[type=range]').forEach((i) => (i.value = cal[i.dataset.k])); s.setCalibration(cal); fmt(); }
    if (a === 'save') {
      let token = store.get('ardc-admin-token');
      if (!token) { token = prompt('Admin token'); if (!token) return; }
      const r = await fetch(`/api/admin/canvases/${encodeURIComponent(canvasId)}/calibration`, {
        method: 'PUT', headers: { 'content-type': 'application/json', 'x-admin-token': token },
        body: JSON.stringify({ calibration: cal, tracking: state.canvas.tracking }),
      });
      if (r.ok) { store.set('ardc-admin-token', token); state.canvas.calibration = { ...cal }; toast('Calibration saved'); }
      else toast(r.status === 401 ? 'Wrong admin token' : 'Save failed');
    }
  };
}
