// Living Canvas — 3D foreground effects that emerge from the physical canvas.
//
// Everything here lives in the tracked canvas's own 3D space (MindAR anchor: 1 unit = width of
// the tracked print, z = 0 on the canvas surface, +z towards the viewer). Particles are born at
// exact positions in the painting (fireworks centres, diya flames, sparklers, trees, flowers,
// deities) and travel outward along +z, so with perspective they visibly leave the canvas and
// come into the room. Travel distance is capped (≈ 0.45 canvas widths) and everything fades out
// before reaching the phone, so effects never cover the viewer or drift away from the artwork.
import * as THREE from 'three';

const MAX_GLOW = 2600;   // additive particles (sparks, trails, embers, dust, flashes)
const MAX_PETAL = 160;   // alpha-blended petals
const MAX_BIRDS = 10;
const rand = (a, b) => a + Math.random() * (b - a);

function makeParticles(max, additive) {
  const g = new THREE.BufferGeometry();
  const pos = new Float32Array(max * 3), col = new Float32Array(max * 3), size = new Float32Array(max), alpha = new Float32Array(max), rot = new Float32Array(max), shape = new Float32Array(max);
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setAttribute('size', new THREE.BufferAttribute(size, 1));
  g.setAttribute('alpha', new THREE.BufferAttribute(alpha, 1));
  g.setAttribute('rot', new THREE.BufferAttribute(rot, 1));
  g.setAttribute('shape', new THREE.BufferAttribute(shape, 1));
  const m = new THREE.ShaderMaterial({
    transparent: true, depthTest: false, depthWrite: false,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    uniforms: { uScale: { value: 400 }, uFade: { value: 1 }, uSizeMul: { value: additive ? 3.2 : 1.6 } },
    vertexShader: /* glsl */ `
      attribute float size; attribute float alpha; attribute float rot; attribute float shape;
      attribute vec3 color;
      uniform float uScale; uniform float uSizeMul;
      varying vec3 vCol; varying float vA; varying float vRot; varying float vShape;
      void main() {
        vCol = color; vA = alpha; vRot = rot; vShape = shape;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = clamp(size * uSizeMul * uScale / max(0.05, -mv.z), 1.0, 128.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform float uFade;
      varying vec3 vCol; varying float vA; varying float vRot; varying float vShape;
      void main() {
        vec2 p = gl_PointCoord - 0.5;
        float a;
        if (vShape < 0.5) {                       // soft glowing spark
          float d = length(p) * 2.0;
          a = exp(-d * d * 4.0) + 0.35 * exp(-d * d * 40.0);
        } else {                                  // petal: rotated teardrop with soft edge + vein shading
          float c = cos(vRot), s = sin(vRot);
          vec2 q = vec2(c * p.x - s * p.y, s * p.x + c * p.y);
          q.y += 0.08;
          float e = length(vec2(q.x * 2.2 * (1.0 + q.y), q.y * 1.15));
          a = 1.0 - smoothstep(0.42, 0.5, e);
          float shade = 0.75 + 0.35 * (0.5 - q.y) - 0.15 * abs(q.x) * 3.0;
          gl_FragColor = vec4(vCol * shade, a * vA * uFade);
          return;
        }
        gl_FragColor = vec4(vCol * a * vA * uFade, a * vA * uFade);
      }`,
  });
  const pts = new THREE.Points(g, m);
  pts.frustumCulled = false;
  pts.renderOrder = 5;
  return { pts, pos, col, size, alpha, rot, shape, g, m, max, live: [] };
}

function birdTexture() {
  // 4-frame wing-flap flipbook, painted dark like the artwork's silhouettes.
  const c = document.createElement('canvas'); c.width = 256; c.height = 64;
  const x = c.getContext('2d');
  const wing = [-0.9, -0.35, 0.25, -0.35];
  wing.forEach((w, i) => {
    const ox = i * 64 + 32, oy = 36;
    x.fillStyle = '#2a1a14'; x.strokeStyle = '#2a1a14'; x.lineWidth = 3; x.lineCap = 'round';
    x.beginPath(); x.ellipse(ox, oy, 7, 4, 0, 0, Math.PI * 2); x.fill();          // body
    x.beginPath(); x.arc(ox + 7, oy - 2, 3, 0, Math.PI * 2); x.fill();             // head
    x.beginPath(); x.moveTo(ox + 10, oy - 2); x.lineTo(ox + 14, oy - 1); x.stroke(); // beak
    x.beginPath(); x.moveTo(ox - 7, oy); x.lineTo(ox - 13, oy + 3); x.stroke();     // tail
    for (const s of [-1, 1]) {                                                       // wings
      x.beginPath(); x.moveTo(ox - 2, oy - 2);
      x.quadraticCurveTo(ox - 2 + s * 4, oy - 2 + w * 22 * 0.6, ox - 10 + s * 3, oy - 2 + w * 22);
      x.quadraticCurveTo(ox + 2, oy - 2 + w * 10, ox + 3, oy - 2);
      x.fill();
    }
  });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export class LivingFx {
  constructor(scene) {
    this.group = new THREE.Group();
    this.group.matrixAutoUpdate = false;
    this.group.visible = false;
    scene.add(this.group);
    this.glow = makeParticles(MAX_GLOW, true);
    this.petal = makeParticles(MAX_PETAL, false);
    this.group.add(this.glow.pts, this.petal.pts);
    this.birdTex = birdTexture();
    this.birds = [];
    for (let i = 0; i < MAX_BIRDS; i++) {
      const mat = new THREE.ShaderMaterial({
        transparent: true, depthTest: false, depthWrite: false,
        uniforms: { map: { value: this.birdTex }, frame: { value: 0 }, alpha: { value: 0 }, flip: { value: 1 } },
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
        fragmentShader: 'uniform sampler2D map; uniform float frame; uniform float alpha; uniform float flip; varying vec2 vUv; void main(){ vec2 uv = vec2((flip > 0.0 ? vUv.x : 1.0 - vUv.x) * 0.25 + floor(frame) * 0.25, vUv.y); vec4 c = texture2D(map, uv); gl_FragColor = vec4(c.rgb, c.a * alpha); }',
      });
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 0.25), mat);
      m.frustumCulled = false; m.renderOrder = 6; m.visible = false;
      this.group.add(m);
      this.birds.push({ mesh: m, alive: false });
    }
    this.manifest = null;
    this.intensity = 0;
    this.timers = new Map();
    this.t = 0;
  }

  /** @param anim manifest (uv in image space: u→right, v→down) @param uvToCanvas3D(u,v)→Vector3 */
  setManifest(anim, uvToCanvas3D) {
    this.manifest = anim || null;
    this.uvTo = uvToCanvas3D;
    this.timers.clear();
  }

  // ---- particle helpers ---------------------------------------------------------
  _spawn(sys, p) {
    if (sys.live.length >= sys.max) return null;
    sys.live.push(p);
    return p;
  }

  _burst(fw) {
    const c = this.uvTo(fw.u, fw.v);
    const base = new THREE.Color(fw.color || '#ffcf5a');
    const alt = new THREE.Color(fw.color2 || '#fff4d6');
    const n = Math.round(70 + 50 * (fw.r || 0.1) / 0.1);
    const speed = (fw.r || 0.1) * 2.6;
    const ring = Math.random() < 0.35; // some bursts are flat rings, some full spheres (variety)
    for (let i = 0; i < n; i++) {
      let dx, dy, dz;
      if (ring) { const a = (i / n) * Math.PI * 2; dx = Math.cos(a); dy = Math.sin(a); dz = rand(0.2, 0.9); }
      else { do { dx = rand(-1, 1); dy = rand(-1, 1); dz = rand(-0.2, 1); } while (dx * dx + dy * dy + dz * dz > 1); }
      const l = Math.hypot(dx, dy, dz) || 1;
      const s = speed * rand(0.75, 1.05);
      this._spawn(this.glow, {
        x: c.x, y: c.y, z: c.z + 0.002, vx: dx / l * s, vy: dy / l * s, vz: Math.abs(dz / l) * s * 1.15,
        life: rand(1.4, 2.1), age: 0, size: rand(0.006, 0.01), col: (Math.random() < 0.8 ? base : alt).clone(),
        drag: 1.15, g: -0.14, trail: true, kind: 'spark',
      });
    }
    this._spawn(this.glow, { x: c.x, y: c.y, z: c.z + 0.003, vx: 0, vy: 0, vz: 0, life: 0.35, age: 0, size: (fw.r || 0.1) * 0.9, col: base.clone().lerp(new THREE.Color('#fff'), 0.6), drag: 0, g: 0, kind: 'flash' });
  }

  _sparkler(sp, dt) {
    const turn = (this.t * (sp.rps || 1.3) + (sp.phase || 0)) * Math.PI * 2;
    const r = sp.r || 0.03;
    const u = sp.u + Math.cos(turn) * r, v = sp.v + Math.sin(turn) * r * (sp.squash || 1);
    const p = this.uvTo(u, v);
    // persistent circular light trail
    this._spawn(this.glow, { x: p.x, y: p.y, z: p.z + 0.004, vx: 0, vy: 0, vz: 0.01, life: 0.55, age: 0, size: 0.009, col: new THREE.Color('#ffe9b0'), drag: 0, g: 0, kind: 'trail' });
    const n = Math.round(260 * dt);
    for (let i = 0; i < n; i++) {
      const a = rand(0, Math.PI * 2), s = rand(0.12, 0.38);
      this._spawn(this.glow, { x: p.x, y: p.y, z: p.z + 0.004, vx: Math.cos(a) * s, vy: Math.sin(a) * s, vz: rand(0.05, 0.45), life: rand(0.18, 0.42), age: 0, size: rand(0.003, 0.006), col: new THREE.Color(Math.random() < 0.7 ? '#fff1c2' : '#ffb347'), drag: 2.5, g: -0.4, kind: 'spark' });
    }
  }

  _ember(f) {
    const p = this.uvTo(f.u + rand(-0.004, 0.004), f.v - 0.01);
    this._spawn(this.glow, { x: p.x, y: p.y, z: p.z + 0.002, vx: rand(-0.008, 0.008), vy: rand(0.03, 0.06), vz: rand(0.0, 0.06), life: rand(1.4, 2.6), age: 0, size: rand(0.003, 0.0055), col: new THREE.Color(Math.random() < 0.6 ? '#ffc35a' : '#ff8a2a'), drag: 0.3, g: 0.0, wobble: rand(0, 6), kind: 'ember' });
  }

  _dust(d) {
    const a = rand(0, Math.PI * 2), rr = (0.55 + 0.45 * Math.sqrt(Math.random())) * (d.r || 0.15); // ring: keeps clear of central figures
    const p = this.uvTo(d.u + Math.cos(a) * rr * 0.75, d.v + Math.sin(a) * rr);
    this._spawn(this.glow, { x: p.x, y: p.y, z: p.z + 0.003, vx: rand(-0.01, 0.01), vy: rand(0.008, 0.03), vz: rand(0.01, 0.09), life: rand(2.2, 3.6), age: 0, size: rand(0.003, 0.007), col: new THREE.Color(d.color || '#ffd77a'), drag: 0.2, g: 0, wobble: rand(0, 6), kind: 'dust' });
  }

  _petal(fl) {
    const a = rand(0, Math.PI * 2), rr = Math.sqrt(Math.random()) * (fl.r || 0.05);
    const p = this.uvTo(fl.u + Math.cos(a) * rr * 0.75, fl.v + Math.sin(a) * rr);
    const cols = fl.colors || ['#f28c0f', '#ffc93c', '#d62828'];
    this._spawn(this.petal, { x: p.x, y: p.y, z: p.z + 0.004, vx: rand(-0.025, 0.025), vy: rand(-0.005, 0.02), vz: rand(0.05, 0.11), life: rand(3.5, 5), age: 0, size: rand(0.014, 0.022), col: new THREE.Color(cols[Math.floor(Math.random() * cols.length)]), drag: 0.15, g: -0.012, rot: rand(0, 6.28), vr: rand(-2, 2), wobble: rand(0, 6), kind: 'petal' });
  }

  _bird(tree) {
    const b = this.birds.find((x) => !x.alive);
    if (!b) return;
    const p = this.uvTo(tree.u + rand(-tree.w / 2, tree.w / 2) * 0.6, tree.v + rand(-tree.h / 2, tree.h / 2) * 0.5);
    const dir = Math.random() < 0.5 ? -1 : 1;
    Object.assign(b, {
      alive: true, age: 0, life: rand(3.2, 4.4), x: p.x, y: p.y, z: p.z + 0.004,
      vx: dir * rand(0.06, 0.14), vy: rand(0.03, 0.08), vz: rand(0.07, 0.13), curve: rand(-0.6, 0.6), flapRate: rand(9, 13), dir,
      scale: rand(0.06, 0.08),
    });
    b.mesh.visible = true;
    b.mesh.material.uniforms.flip.value = dir;
  }

  _every(key, period, fn) {
    if (!this.timers.has(key)) this.timers.set(key, this.t + rand(0.05, 0.5) * period); // first one comes quickly
    if (this.t >= this.timers.get(key)) { fn(); this.timers.set(key, this.t + period * rand(0.7, 1.3)); }
  }

  /** @param poseMatrix canvas→camera-space matrix (MindAR anchor) @param on animation requested */
  update(dt, poseMatrix, on, visible, camera, viewportH) {
    this.t += dt;
    this.intensity += ((on ? 1 : 0) - this.intensity) * Math.min(1, dt * 4);
    const m = this.manifest;
    if (poseMatrix) { this.group.matrix.copy(poseMatrix); this.group.matrixWorldNeedsUpdate = true; }
    // point sizes are in canvas units; the anchor matrix scales canvas units into camera units
    const modelScale = new THREE.Vector3().setFromMatrixScale(this.group.matrix).x || 1;
    const scale = viewportH * 0.5 * camera.projectionMatrix.elements[5] * modelScale;
    this.glow.m.uniforms.uScale.value = scale;
    this.petal.m.uniforms.uScale.value = scale;
    const fade = visible ? 1 : 0;
    this.glow.m.uniforms.uFade.value = fade;
    this.petal.m.uniforms.uFade.value = fade;

    if (on && m && visible && this.uvTo) {
      (m.fireworks || []).forEach((fw, i) => this._every('fw' + i, fw.period || 3.2, () => this._burst(fw)));
      (m.sparklers || []).forEach((sp) => this._sparkler(sp, dt));
      (m.embers || []).forEach((f, i) => this._every('em' + i, f.period || 0.55, () => this._ember(f)));
      (m.dust || []).forEach((d, i) => this._every('du' + i, d.period || 0.12, () => this._dust(d)));
      (m.petals || []).forEach((fl, i) => this._every('pe' + i, fl.period || 1.1, () => this._petal(fl)));
      (m.birds || []).forEach((tr, i) => this._every('bi' + i, tr.period || 3.5, () => this._bird(tr)));
    }

    // integrate particles
    for (const sys of [this.glow, this.petal]) {
      const keep = [];
      for (const p of sys.live) {
        p.age += dt;
        if (p.age >= p.life) continue;
        const dr = Math.exp(-(p.drag || 0) * dt);
        p.vx *= dr; p.vy *= dr; p.vz *= dr;
        p.vy += (p.g || 0) * dt;
        if (p.wobble !== undefined) p.vx += Math.sin(this.t * 2.2 + p.wobble) * 0.015 * dt;
        p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
        if (p.vr) p.rot += p.vr * dt;
        if (p.z > 0.5) continue; // never come closer than ~half a canvas width
        if (p.trail && Math.random() < 0.55) {
          this._spawn(this.glow, { x: p.x, y: p.y, z: p.z, vx: 0, vy: 0, vz: 0, life: 0.38, age: 0, size: p.size * 0.6, col: p.col.clone().multiplyScalar(0.6), drag: 0, g: 0, kind: 'trail' });
        }
        keep.push(p);
      }
      sys.live = keep;
      const n = Math.min(sys.max, keep.length);
      for (let i = 0; i < n; i++) {
        const p = keep[i];
        const k = p.age / p.life;
        let a;
        if (p.kind === 'flash') a = (1 - k) * (1 - k);
        else if (p.kind === 'spark') a = k < 0.7 ? 1 : 1 - (k - 0.7) / 0.3;
        else if (p.kind === 'petal') a = Math.min(1, p.age * 3) * (k < 0.75 ? 1 : 1 - (k - 0.75) / 0.25);
        else a = Math.sin(Math.PI * k);
        a *= Math.max(0, 1 - Math.max(0, p.z - 0.32) / 0.18); // fade as it nears the viewer
        sys.pos[i * 3] = p.x; sys.pos[i * 3 + 1] = p.y; sys.pos[i * 3 + 2] = p.z;
        sys.col[i * 3] = p.col.r; sys.col[i * 3 + 1] = p.col.g; sys.col[i * 3 + 2] = p.col.b;
        sys.size[i] = p.size * (p.kind === 'spark' && Math.random() < 0.12 ? 1.8 : 1); // glitter
        sys.alpha[i] = a;
        sys.rot[i] = p.rot || 0;
        sys.shape[i] = p.kind === 'petal' ? 1 : 0;
      }
      sys.g.setDrawRange(0, n);
      for (const k of ['position', 'color', 'size', 'alpha', 'rot', 'shape']) sys.g.attributes[k].needsUpdate = true;
    }

    // birds
    for (const b of this.birds) {
      if (!b.alive) continue;
      b.age += dt;
      if (b.age >= b.life) { b.alive = false; b.mesh.visible = false; continue; }
      const k = b.age / b.life;
      b.vx += b.curve * 0.05 * dt; b.vy += 0.02 * dt;
      b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
      b.mesh.position.set(b.x, b.y, Math.min(b.z, 0.48));
      b.mesh.scale.setScalar(b.scale);
      b.mesh.material.uniforms.frame.value = (b.age * b.flapRate) % 4;
      b.mesh.material.uniforms.alpha.value = Math.min(1, b.age * 4) * (k < 0.8 ? 1 : 1 - (k - 0.8) / 0.2) * fade;
      b.mesh.visible = visible;
    }
    this.group.visible = visible;
  }

  activeCount() { return this.glow.live.length + this.petal.live.length + this.birds.filter((b) => b.alive).length; }

  dispose() {
    this.glow.g.dispose(); this.glow.m.dispose(); this.petal.g.dispose(); this.petal.m.dispose();
    this.birdTex.dispose();
    for (const b of this.birds) { b.mesh.geometry.dispose(); b.mesh.material.dispose(); }
    this.group.removeFromParent();
  }
}
