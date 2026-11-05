// AR session: camera → MindAR image tracking → homography fit → smoothing → painted-canvas render.
//
// Pipeline per frame
//   1. MindAR detects / tracks the printed target (feature matching, runs in a worker + tfjs).
//   2. We tap the tracker's per-frame point correspondences (target px ↔ camera px) and fit an
//      exact planar homography (robust least squares). Fallback: MindAR's 6-DoF pose.
//   3. The 4 target corners (camera px) are One-Euro filtered → low jitter, low lag.
//   4. Painting quad = calibrated canvas rectangle mapped through that homography straight into
//      clip space → it hugs the physical canvas from any angle/distance.
import * as THREE from 'three';
import { MindARThree } from '/vendor/mindar/mindar-image-three.prod.js';
import { createPaintingMaterial, loadPaintingTextures } from './paintingMaterial.js';
import { LightEstimator } from './lightEstimator.js';
import { LivingFx } from './fxLayer.js';
import { fitHomographyRobust, homographyFrom4, apply, mul3, OneEuro } from './homography.js';

// mindar*: MindAR's internal pose filter (ms time base) — only used for the pose fallback.
// euro*: our corner filter (Hz, px/s). warmup/miss: frames before showing / hiding.
export const TRACKING_PRESETS = {
  stable: { mindarMinCF: 0.0005, mindarBeta: 0.01, euroMin: 0.45, euroBeta: 0.008, warmup: 6, miss: 10 },
  balanced: { mindarMinCF: 0.001, mindarBeta: 0.05, euroMin: 0.9, euroBeta: 0.02, warmup: 4, miss: 7 },
  responsive: { mindarMinCF: 0.001, mindarBeta: 1, euroMin: 1.8, euroBeta: 0.05, warmup: 3, miss: 5 },
};

export class CameraError extends Error {
  constructor(kind, detail) { super(kind); this.kind = kind; this.detail = detail; }
}

export async function openCamera({ hd = false } = {}) {
  if (!window.isSecureContext) throw new CameraError('insecure');
  if (!navigator.mediaDevices?.getUserMedia) throw new CameraError('unsupported');
  // Default = the camera's native default size (what MindAR is tuned for, ~640×480 on most phones).
  // HD mode asks for 1280×720: sharper at long distance, but heavier and less compatible.
  const tries = [
    hd
      ? { audio: false, video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } } }
      : { audio: false, video: { facingMode: { ideal: 'environment' } } },
    { audio: false, video: { facingMode: 'environment' } },
    { audio: false, video: true },
  ];
  let last;
  for (const c of tries) {
    try { return await navigator.mediaDevices.getUserMedia(c); } catch (e) {
      last = e;
      if (e.name === 'NotAllowedError' || e.name === 'SecurityError') break; // denied: don't re-prompt
    }
  }
  const map = { NotAllowedError: 'denied', SecurityError: 'denied', NotFoundError: 'nocamera', OverconstrainedError: 'nocamera', NotReadableError: 'busy', AbortError: 'busy' };
  throw new CameraError(map[last?.name] || 'unknown', last?.message);
}

// MindARThree that uses a stream we already opened (so we can report precise errors).
class StreamMindAR extends MindARThree {
  constructor(opts, stream) { super(opts); this._stream = stream; }
  _startVideo() {
    return new Promise((resolve, reject) => {
      const v = (this.video = document.createElement('video'));
      v.setAttribute('autoplay', ''); v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
      v.muted = true; v.playsInline = true;
      Object.assign(v.style, { position: 'absolute', top: '0px', left: '0px', zIndex: '-2' });
      this.container.appendChild(v);
      const done = () => { v.setAttribute('width', v.videoWidth); v.setAttribute('height', v.videoHeight); resolve(); };
      v.addEventListener('loadedmetadata', done, { once: true });
      v.srcObject = this._stream;
      v.play().catch(() => {});
      setTimeout(() => (v.videoWidth ? null : reject(new CameraError('busy'))), 8000);
    });
  }
}

export class ARSession {
  /**
   * @param {object} o
   * @param {HTMLElement} o.container  full-screen element
   * @param {object} o.canvas          canvas config from /api/canvas/:id
   * @param {(s:string, info?:object)=>void} o.onState
   */
  constructor({ container, canvas, onState = () => {} }) {
    this.container = container;
    this.cfg = structuredClone(canvas);
    this.onState = onState;
    this.state = 'idle';
    this.preset = TRACKING_PRESETS[this.cfg.tracking] || TRACKING_PRESETS.balanced;
    this.light = new LightEstimator();
    this.euro = new OneEuro(this.preset.euroMin, this.preset.euroBeta);
    this.targetSeen = false;
    this.lostAt = -1e9;
    this.opacity = 0;
    this.reveal = { from: 0, to: 0, t0: 0, dur: 1 };
    this.currentPaintingId = null;
    this.meas = null;          // latest homography measurement {H, t, n, rms}
    this.Hs = null;            // smoothed target→video homography
    this.stats = { hFrames: 0, poseFrames: 0, lastRms: 0, lastInliers: 0 };
    this._v3 = new THREE.Vector3();
    this._m4 = new THREE.Matrix4();
  }

  _setState(s, info) { if (s !== this.state) { this.state = s; this.onState(s, info); } }

  async start(painting) {
    this._setState('starting');
    if (!this.cfg.targetUrl) throw new CameraError('notarget');
    this.stream = await openCamera({ hd: !!this.cfg.hd });
    this._setState('loading');

    this.mindar = new StreamMindAR({
      container: this.container,
      imageTargetSrc: this.cfg.targetUrl,
      maxTrack: 1,
      uiLoading: 'no', uiScanning: 'no', uiError: 'no',
      filterMinCF: this.preset.mindarMinCF,
      filterBeta: this.preset.mindarBeta,
      warmupTolerance: this.preset.warmup,
      missTolerance: this.preset.miss,
    }, this.stream);
    const { renderer, scene, camera } = this.mindar;
    this.renderer = renderer; this.scene = scene; this.camera = camera;
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    if (this.mindar.cssRenderer) this.mindar.cssRenderer.domElement.style.pointerEvents = 'none';

    this.anchor = this.mindar.addAnchor(0);
    this.anchor.onTargetFound = () => this._found();
    this.anchor.onTargetLost = () => this._lost();

    this.material = createPaintingMaterial({ widthCm: this.cfg.widthCm, heightCm: this.cfg.heightCm });
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), this.material);
    this.mesh.frustumCulled = false;
    scene.add(this.mesh);
    this.fx = new LivingFx(scene);   // 3D effects that emerge from the canvas (Bring to Life)
    this.animOn = false;

    // 2D overlay for calibration guides
    this.guideCanvas = document.createElement('canvas');
    Object.assign(this.guideCanvas.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', pointerEvents: 'none', display: 'none' });
    this.container.appendChild(this.guideCanvas);

    const lightInit = this.light.init(`/api/canvas/${encodeURIComponent(this.cfg.id)}/print.svg?compile=1`, { uniform: this.cfg.mode === 'marker' });
    const first = painting ? this.setPainting(painting) : Promise.resolve();

    try {
      await this.mindar.start();
    } catch (e) {
      throw e instanceof CameraError ? e : new CameraError('tracker', e?.message || String(e));
    }
    this.video = this.mindar.video;
    const ctl = this.mindar.controller;
    const [tw, th] = ctl.markerDimensions[0];
    this.targetPx = { w: tw, h: th, corners: [{ x: 0, y: 0 }, { x: tw, y: 0 }, { x: tw, y: th }, { x: 0, y: th }] };
    this._tapTracker(ctl);
    this._tapDiagnostics(ctl);
    // Some phones (notably iOS) report the camera size at start, then change it once the stream
    // settles (e.g. portrait swap). MindAR draws frames using the size it saw at start, so a silent
    // change squashes every frame and the canvas is never found. Watch for it and adapt / restart.
    this._onVideoResize = () => {
      const v = this.video; if (!v || !v.videoWidth) return;
      this.diag.videoResizes++;
      v.setAttribute('width', v.videoWidth); v.setAttribute('height', v.videoHeight);
      const same = v.videoWidth === ctl.inputWidth && v.videoHeight === ctl.inputHeight;
      const swapped = v.videoWidth === ctl.inputHeight && v.videoHeight === ctl.inputWidth;
      if (same || swapped) { try { this.mindar.resize(); } catch {} }
      else this._setState('needs-restart');
    };
    this.video.addEventListener('resize', this._onVideoResize);
    await Promise.all([lightInit, first.catch(() => {})]);
    this._last = performance.now();
    renderer.setAnimationLoop(() => this._frame());
    this._setState('scanning');
    this._scanStart = performance.now();

    this._onVis = () => {
      if (document.visibilityState !== 'visible') return;
      const track = this.stream?.getVideoTracks()[0];
      if (!track || track.readyState === 'ended') this._setState('interrupted');
      else this.video?.play().catch(() => {});
    };
    document.addEventListener('visibilitychange', this._onVis);
  }

  /** Capture MindAR's per-frame tracking correspondences and fit a homography from them. */
  _tapTracker(ctl) {
    const tracker = ctl.tracker;
    if (!tracker || typeof tracker.track !== 'function') return;
    const orig = tracker.track.bind(tracker);
    tracker.track = (...args) => {
      const r = orig(...args);
      try {
        const n = r.worldCoords.length;
        const rotated = this.video && (this.video.videoWidth !== ctl.inputWidth);
        if (n >= 8 && !rotated) {
          const fit = fitHomographyRobust(r.worldCoords, r.screenCoords, { minInliers: 8, thresholdPx: 3 });
          if (fit && fit.rms < 4) this.meas = { H: fit.H, t: performance.now(), n: fit.inliers, rms: fit.rms };
          if (fit) { this.stats.lastRms = fit.rms; this.stats.lastInliers = fit.inliers; }
        }
      } catch (e) { /* never break tracking */ }
      return r;
    };
  }

  /** Lightweight counters for the on-screen diagnostics panel (?debug=1). */
  _tapDiagnostics(ctl) {
    const d = (this.diag = { frames: 0, detects: 0, lastFeatures: 0, maxFeatures: 0, matchCalls: 0, matches: 0, videoResizes: 0 });
    try {
      const cd = ctl.cropDetector;
      if (cd?.detectMoving) {
        const o = cd.detectMoving.bind(cd);
        cd.detectMoving = (...a) => { const r = o(...a); d.detects++; d.lastFeatures = r?.featurePoints?.length || 0; d.maxFeatures = Math.max(d.maxFeatures, d.lastFeatures); return r; };
      }
      if (ctl._workerMatch) {
        const o = ctl._workerMatch.bind(ctl);
        ctl._workerMatch = async (...a) => { const r = await o(...a); d.matchCalls++; if (r && r.targetIndex !== -1 && r.targetIndex != null) d.matches++; return r; };
      }
      const ou = ctl.onUpdate;
      ctl.onUpdate = (u) => { if (u?.type === 'processDone') d.frames++; if (ou) ou(u); };
    } catch (e) { /* diagnostics must never break tracking */ }
  }

  /** Snapshot of diagnostics for display / support. */
  diagnostics() {
    const ctl = this.mindar?.controller, v = this.video;
    let gpu = '';
    try { const gl = this.renderer.getContext(); const ext = gl.getExtension('WEBGL_debug_renderer_info'); gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); } catch {}
    let backend = '';
    try { backend = window.MINDAR?.IMAGE?.tf?.getBackend?.() || ''; } catch {}
    return {
      state: this.state,
      video: v ? `${v.videoWidth}×${v.videoHeight} (attr ${v.getAttribute('width')}×${v.getAttribute('height')}, ready ${v.readyState}, ${v.paused ? 'paused' : 'playing'})` : '-',
      trackerInput: ctl ? `${ctl.inputWidth}×${ctl.inputHeight}` : '-',
      target: this.targetPx ? `${this.targetPx.w}×${this.targetPx.h}` : '-',
      backend, gpu,
      ...this.diag,
      homography: `${this.stats.hFrames} h / ${this.stats.poseFrames} pose, rms ${this.stats.lastRms.toFixed(2)}`,
      ua: navigator.userAgent,
    };
  }
  /** The exact greyscale frame the tracker analyses (to spot black / squashed frames). */
  trackerInputCanvas() { return this.mindar?.controller?.inputLoader?.context?.canvas || null; }

  // ---- geometry ---------------------------------------------------------------
  setCalibration(cal) { this.cfg.calibration = { ...this.cfg.calibration, ...cal }; }
  setTracking(name) {
    this.cfg.tracking = name;
    this.preset = TRACKING_PRESETS[name] || TRACKING_PRESETS.balanced;
    this.euro.minCutoff = this.preset.euroMin; this.euro.beta = this.preset.euroBeta;
    const ctl = this.mindar?.controller;
    if (ctl) {
      ctl.filterMinCF = this.preset.mindarMinCF; ctl.filterBeta = this.preset.mindarBeta;
      ctl.warmupTolerance = this.preset.warmup; ctl.missTolerance = this.preset.miss;
      for (const s of ctl.trackingStates || []) { s.filter.minCutOff = this.preset.mindarMinCF; s.filter.beta = this.preset.mindarBeta; }
    }
  }
  setGuides(on) { this.showGuides = on; this.guideCanvas.style.display = on ? 'block' : 'none'; }
  setPeek(on) { this.peek = on; }

  /** Painting uv (u→right, v→up) → target image px, including canvas layout + calibration. */
  _layoutMatrix() {
    const c = this.cfg, t = c.target, cal = c.calibration || { dxCm: 0, dyCm: 0, scale: 1, rotDeg: 0 };
    const W = c.widthCm, H = c.heightCm;
    // uv → canvas cm (y down)
    const U = [W, 0, 0, 0, -H, H, 0, 0, 1];
    // calibration about canvas centre: translate(-c) → scale → rotate → translate(c + d)
    const a = (cal.rotDeg * Math.PI) / 180, cs = Math.cos(a) * cal.scale, sn = Math.sin(a) * cal.scale;
    const cx = W / 2, cy = H / 2;
    const C = [cs, -sn, cx + cal.dxCm - cs * cx + sn * cy, sn, cs, cy + cal.dyCm - sn * cx - cs * cy, 0, 0, 1];
    // canvas cm → target px
    const sx = this.targetPx.w / t.wCm, sy = this.targetPx.h / t.hCm;
    const T = [sx, 0, -t.xCm * sx, 0, sy, -t.yCm * sy, 0, 0, 1];
    return mul3(T, mul3(C, U));
  }
  /** camera video px → NDC (accounts for MindAR's cover-fit video placement). */
  _videoToNdc() {
    const st = this.video.style, cw = this.container.clientWidth, ch = this.container.clientHeight;
    const left = parseFloat(st.left) || 0, top = parseFloat(st.top) || 0;
    const dw = parseFloat(st.width) || cw, dh = parseFloat(st.height) || ch;
    const kx = dw / this.video.videoWidth, ky = dh / this.video.videoHeight;
    return [(2 * kx) / cw, 0, (2 * left) / cw - 1, 0, (-2 * ky) / ch, 1 - (2 * top) / ch, 0, 0, 1];
  }
  _poseCornersVideo() {
    // Fallback: project target corners with MindAR's pose (anchor units: 1 = target width).
    const ar = this.targetPx.h / this.targetPx.w;
    const st = this.video.style, cw = this.container.clientWidth, ch = this.container.clientHeight;
    const left = parseFloat(st.left) || 0, top = parseFloat(st.top) || 0;
    const dw = parseFloat(st.width) || cw, dh = parseFloat(st.height) || ch;
    return [[-0.5, ar / 2], [0.5, ar / 2], [0.5, -ar / 2], [-0.5, -ar / 2]].map(([x, y]) => {
      const v = this._v3.set(x, y, 0).applyMatrix4(this.anchor.group.matrix).project(this.camera);
      const sx = ((v.x + 1) / 2) * cw, sy = ((1 - v.y) / 2) * ch;
      return { x: ((sx - left) / dw) * this.video.videoWidth, y: ((sy - top) / dh) * this.video.videoHeight };
    });
  }

  // ---- paintings --------------------------------------------------------------
  async setPainting(painting) {
    if (painting.id === this.currentPaintingId) return;
    const reqId = (this._paintReq = (this._paintReq || 0) + 1);
    this.onState('painting-loading', { painting });
    const tex = await loadPaintingTextures(painting, this.renderer);
    if (reqId !== this._paintReq) return; // superseded by a newer selection
    const u = this.material.uniforms;
    if (u.reveal.value > 0.5) { // current painting (in B) moves to A, new one goes to B
      u.mapA.value = u.mapB.value; u.heightA.value = u.heightB.value; u.texelA.value.copy(u.texelB.value); u.aAlpha.value = 1;
    }
    u.mapB.value = tex.albedo; u.heightB.value = tex.height; u.texelB.value.copy(tex.texel);
    u.reveal.value = 0;
    this._applyAnimation(painting, tex);
    const firstEver = !this.currentPaintingId;
    this.reveal = { from: 0, to: 1, t0: performance.now(), dur: firstEver ? 1800 : 1400, waitForLock: firstEver };
    this.currentPaintingId = painting.id;
    this.onState('painting-ready', { painting });
  }

  // ---- Living Canvas ("Bring to Life") ----------------------------------------------
  /** Wire the painting's prepared animation assets (loaded with the painting, so no delay). */
  _applyAnimation(painting, tex) {
    const u = this.material.uniforms;
    const black = this.material.userData.black;
    u.fxMap.value = tex.fx || black;
    u.motionMap.value = tex.motion || black;
    u.hasFx.value = tex.fx ? 1 : 0;
    const halos = (tex.anim && tex.anim.halos) || [];
    for (let i = 0; i < 3; i++) {
      const h = halos[i];
      u.halos.value[i].set(h ? h.u : 0, h ? 1 - h.v : 0, h ? h.r0 : 0, h ? h.r1 : 0);
      u.haloSpeed.value[i] = h ? (h.speed ?? 0.25) : 0;
    }
    this.currentAnim = tex.anim || null;
    this.fx.setManifest(this.currentAnim, (uu, vv) => this._uvToCanvas3D(uu, vv));
    this._setupVideo(painting);
  }
  hasAnimation() { return !!this.currentAnim || this.material.uniforms.hasFx.value > 0; }

  /** Optional pre-rendered animated version (e.g. image-to-video clip). Its first frame must be
   *  the painting; it is cross-faded in only once it is actually playing (no loading flash). */
  _setupVideo(painting) {
    if (this.videoEl) { this.videoEl.pause(); this.videoEl.removeAttribute('src'); this.videoEl.load(); this.videoEl.remove(); this.videoEl = null; }
    if (this.videoTex) { this.videoTex.dispose(); this.videoTex = null; }
    this.material.uniforms.videoMix.value = 0;
    this.videoReady = false;
    if (!painting.video) return;
    const v = document.createElement('video');
    Object.assign(v, { muted: true, loop: true, playsInline: true, preload: 'auto', crossOrigin: 'anonymous' });
    v.setAttribute('playsinline', ''); v.setAttribute('muted', '');
    // kept in the page (invisible) so every mobile browser decodes it for the texture
    v.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;pointer-events:none;z-index:-1';
    v.src = painting.video;
    v.addEventListener('playing', () => { this.videoReady = true; }, { once: false });
    this.videoEl = v;
    document.body.appendChild(v);
    this.videoTex = new THREE.VideoTexture(v);
    this.videoTex.colorSpace = THREE.NoColorSpace;   // decoded sRGB→linear in the shader (see paintingMaterial)
    this.material.uniforms.videoMap.value = this.videoTex;
    // warm up: download + start the decoder now, so "Bring to Life" starts instantly; rest on frame 0
    v.play().then(() => { if (this.videoEl === v && !this.animOn) { v.pause(); v.currentTime = 0; } }).catch(() => {});
  }

  setAnimating(on) {
    this.animOn = !!on;
    if (this.videoEl) {
      if (on) { this.videoEl.currentTime = 0; this.videoEl.play().catch(() => {}); }
    }
    this.onState(on ? 'anim-on' : 'anim-off');
  }

  /** Painting uv (u→right, v→down, 0..1) → 3D point in MindAR anchor space (z = 0 on canvas). */
  _uvToCanvas3D(uu, vv) {
    const L = this._layoutMatrix();
    const p = apply(L, { x: uu, y: 1 - vv });
    const tw = this.targetPx.w, th = this.targetPx.h;
    return new THREE.Vector3(p.x / tw - 0.5, (0.5 - p.y / th) * (th / tw), 0);
  }

  // ---- tracking events ------------------------------------------------------------
  _found() {
    const now = performance.now();
    if (!this.Hs || now - this.lostAt > 1200) this.euro.reset(); // re-acquire: jump, don't glide
    this.targetSeen = true;
    if (this.reveal.waitForLock) { this.reveal.waitForLock = false; this.reveal.t0 = now; }
    this._setState('tracking');
  }
  _lost() {
    this.targetSeen = false;
    this.lostAt = performance.now();
    this._scanStart = this.lostAt;
    this._setState('searching');
  }

  resetTracking() {
    const ctl = this.mindar?.controller;
    if (!ctl) return;
    ctl.stopProcessVideo();
    this.targetSeen = false;
    this.Hs = null; this.meas = null; this.euro.reset();
    this.opacity = 0;
    this._setState('scanning');
    this._scanStart = performance.now();
    setTimeout(() => ctl.processVideo(this.video), 150);
  }

  // ---- per-frame ----------------------------------------------------------------
  _frame() {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this._last) / 1000);
    this._last = now;
    const u = this.material.uniforms;

    // 1) target corners in camera px: homography measurement (preferred) or pose fallback
    if (this.targetSeen) {
      let raw = null;
      const pose = this._poseCornersVideo();
      if (this.meas && now - this.meas.t < 300) {
        raw = this.targetPx.corners.map((p) => apply(this.meas.H, p));
        // sanity check against the pose; reject a wild fit
        const diag = Math.hypot(pose[2].x - pose[0].x, pose[2].y - pose[0].y);
        const dev = Math.max(...raw.map((p, i) => Math.hypot(p.x - pose[i].x, p.y - pose[i].y)));
        if (!(dev < 0.3 * diag) || raw.some((p) => p.w <= 0)) raw = null;
      }
      if (raw) this.stats.hFrames++; else this.stats.poseFrames++;
      raw = raw || pose;
      const f = this.euro.filter(raw.flatMap((p) => [p.x, p.y]), now / 1000);
      const sm = [0, 1, 2, 3].map((i) => ({ x: f[2 * i], y: f[2 * i + 1] }));
      this.Hs = homographyFrom4(this.targetPx.corners, sm) || this.Hs;
      this.smoothCorners = sm;
    }

    // 2) compose uv → NDC and upload
    let drawable = false;
    if (this.Hs) {
      const M = mul3(this._videoToNdc(), mul3(this.Hs, this._layoutMatrix()));
      // all 4 painting corners must be in front of the camera (w > 0)
      drawable = [[0, 0], [1, 0], [1, 1], [0, 1]].every(([x, y]) => M[6] * x + M[7] * y + M[8] > 0);
      if (drawable) u.uH.value.set(...M);
      this._M = M;
      // view direction for the varnish highlight, from the pose
      this._m4.copy(this.anchor.group.matrix).invert();
      const cam = this._v3.set(0, 0, 0).applyMatrix4(this._m4);
      if (Number.isFinite(cam.x) && cam.lengthSq() > 0) u.uViewDir.value.copy(cam).normalize();
    }

    // 3) visibility: fade in on lock; hold briefly then fade out on loss
    const want = this.targetSeen || now - this.lostAt < 300 ? 1 : 0;
    this.opacity += (want - this.opacity) * Math.min(1, dt * (want ? 5.5 : 3.5));
    if (!want && this.opacity < 0.005) this.opacity = 0;
    u.opacity.value = this.opacity * (this.peek ? 0.45 : 1);
    this.mesh.visible = drawable && this.opacity > 0.001;

    // 4) painterly reveal
    const r = this.reveal;
    if (!r.waitForLock) u.reveal.value = r.from + (r.to - r.from) * easeInOut(Math.min(1, (now - r.t0) / r.dur));

    // 5) light estimation (≈5 Hz while locked) + low-light hints while searching
    if (this.targetSeen && this.Hs) {
      const tp = this.targetPx;
      if (this.light.update(this.video, (uu, vv) => apply(this.Hs, { x: uu * tp.w, y: vv * tp.h }), now)) {
        for (let i = 0; i < 9; i++) u.illum.value[i].fromArray(this.light.gains[i]);
        this.light.lightDirection(u.lightDir.value);
      }
    } else if (now - (this._lumT || 0) > 1000) {
      this._lumT = now;
      this.light.update(this.video, null, now);
      const scanning = now - (this._scanStart || now);
      if (scanning > 6000) this.onState('hint', { dark: this.light.globalLuma < 0.035, scanningMs: scanning });
    }

    u.time.value = now / 1000;

    // 6) Living Canvas: ramp animation in/out (seamless — 0 is exactly the static painting)
    const target = this.animOn ? 1 : 0;
    u.uAnim.value += (target - u.uAnim.value) * Math.min(1, dt * 3.2);
    if (Math.abs(u.uAnim.value - target) < 0.002) u.uAnim.value = target;
    if (u.uAnim.value > 0) u.animTime.value += dt; else u.animTime.value = 0;
    if (this.videoEl) {
      const want = this.animOn && this.videoReady ? 1 : 0;
      u.videoMix.value += (want - u.videoMix.value) * Math.min(1, dt * 6);
      if (!this.animOn && u.videoMix.value < 0.01 && !this.videoEl.paused) this.videoEl.pause();
    }
    if (this.targetSeen) this._lastPose = (this._lastPose || new THREE.Matrix4()).copy(this.anchor.group.matrix);
    if (this.fx && this.targetPx) {
      this.fx.update(dt, this._lastPose || null, this.animOn, this.mesh.visible && this.opacity > 0.3 && !!this._lastPose, this.camera, this.container.clientHeight);
    }
    this.renderer.render(this.scene, this.camera);
    if (this.showGuides) this._drawGuides();
  }

  _drawGuides() {
    const g = this.guideCanvas, dpr = Math.min(2, window.devicePixelRatio || 1);
    const cw = this.container.clientWidth, ch = this.container.clientHeight;
    if (g.width !== cw * dpr) { g.width = cw * dpr; g.height = ch * dpr; }
    const ctx = g.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cw, ch);
    if (!this.Hs || !this.mesh.visible) return;
    const V = this._videoToNdc();
    const toScr = (p) => ({ x: ((p.x + 1) / 2) * cw, y: ((1 - p.y) / 2) * ch });
    const quad = (pts, color, dash) => {
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.setLineDash(dash || []);
      ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.closePath(); ctx.stroke();
    };
    quad(this.targetPx.corners.map((p) => toScr(apply(mul3(V, this.Hs), p))), '#38e1ff', [6, 5]);
    quad(this.paintingCornersOnScreen(), '#ffc94d');
  }

  /** Screen-space corners of the rendered painting: TL, TR, BR, BL (tests / guides). */
  paintingCornersOnScreen() {
    if (!this._M) return null;
    const cw = this.container.clientWidth, ch = this.container.clientHeight;
    return [[0, 1], [1, 1], [1, 0], [0, 0]].map(([x, y]) => {
      const p = apply(this._M, { x, y });
      return { x: ((p.x + 1) / 2) * cw, y: ((1 - p.y) / 2) * ch };
    });
  }

  stop() {
    document.removeEventListener('visibilitychange', this._onVis);
    try { this.video?.removeEventListener('resize', this._onVideoResize); } catch {}
    try { this.renderer?.setAnimationLoop(null); } catch {}
    try { this.mindar?.controller?.stopProcessVideo(); } catch {}
    try { this.stream?.getTracks().forEach((t) => t.stop()); } catch {}
    try { this.mindar?.video?.remove(); if (this.mindar) this.mindar.video = null; } catch {}
    try {
      this.material?.dispose(); this.mesh?.geometry.dispose(); this.fx?.dispose();
      if (this.videoEl) { this.videoEl.pause(); this.videoEl.remove(); this.videoEl = null; }
      this.renderer?.dispose();
      this.renderer?.domElement.remove();
      this.mindar?.cssRenderer?.domElement.remove();
      this.guideCanvas?.remove();
    } catch {}
    this._setState('stopped');
  }
}
const easeInOut = (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);
