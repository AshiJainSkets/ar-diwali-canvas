// Physically-motivated "painted canvas" material.
//
// Goal: the painting must read as pigment on a stretched canvas under the room's light,
// not as a glowing screen. Ingredients:
//   • albedo texture (painting colours, sRGB) × measured room illumination field (3×3 grid,
//     estimated from how the camera sees the known tracking print — see LightEstimator)
//   • impasto relief from a per-painting height map (brush-stroke ridges) → normal → shading
//   • procedural canvas weave (over/under threads), anti-aliased by screen-space footprint
//   • faint varnish specular that moves with the viewing angle
//   • soft inner shadow where the stretcher frame meets the surface
//   • camera-matched softness (mip bias) and sensor grain so it doesn't look "too clean"
//   • painterly reveal transition between two paintings (noise-driven brush wipe)
//   • LIVING CANVAS: per-painting effect maps animate the painting's own pixels — flames
//     flicker, bulbs blink, stars twinkle, leaves/garlands sway, water ripples, lanterns swing,
//     painted chakras rotate. All effects scale with uAnim (0→1), so the first animated frame
//     is pixel-identical to the static painting and stopping returns to it exactly.
import * as THREE from 'three';

const vert = /* glsl */ `
  // The quad is placed directly in clip space by a homography (uv → NDC, homogeneous):
  // exact perspective mapping onto the physical canvas, independent of camera intrinsics.
  uniform mat3 uH;
  uniform vec3 uViewDir;   // object-space direction to the camera (from the tracked pose)
  varying vec2 vUv;
  varying vec3 vViewDirObj;
  void main() {
    vUv = uv;
    // view vector varies slightly across the surface so the varnish glint moves with the phone
    vViewDirObj = normalize(uViewDir + vec3((0.5 - uv) * vec2(1.0, 0.75), 0.0));
    vec3 h = uH * vec3(uv, 1.0);
    gl_Position = vec4(h.x, h.y, 0.0, h.z);
  }
`;

const frag = /* glsl */ `
  precision highp float;
  uniform sampler2D mapA, heightA, mapB, heightB;
  uniform vec2 texelA, texelB;
  uniform float reveal;        // 0 = show A, 1 = show B
  uniform float opacity;
  uniform float aAlpha;        // 0 while slot A is empty (first reveal dissolves from the real print)
  uniform vec3 illum[9];       // 3×3 illumination gains (linear RGB)
  uniform vec3 lightDir;       // object space, z towards viewer
  uniform vec2 sizeCm;         // physical canvas size
  uniform float threadsPerCm;
  uniform float relief;
  uniform float weaveAmt;
  uniform float specAmt;
  uniform float mipBias;
  uniform float grainAmt;
  uniform float time;
  // ---- Living Canvas (animation) ----
  uniform float uAnim;          // 0 = static painting, 1 = fully alive (ramped → seamless start/stop)
  uniform float animTime;       // seconds since the animation was switched on
  uniform sampler2D fxMap;      // R emitter strength, G phase, B kind (flame/blink/twinkle/breath)
  uniform sampler2D motionMap;  // R foliage sway, G water ripple, B pendulum swing (0 pivot → 1 tip)
  uniform float hasFx;
  uniform vec4 halos[3];        // centre (uv), r0, r1 (fractions of canvas height) — rotating rings
  uniform float haloSpeed[3];   // rad/s
  uniform float canvasAspect;   // width / height
  uniform sampler2D videoMap;   // optional pre-rendered animated version (mp4); first frame == painting
  uniform float videoMix;
  varying vec2 vUv;
  varying vec3 vViewDirObj;

  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
  }
  float fbm(vec2 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p *= 2.03; a *= 0.5; } return s; }

  vec3 illumAt(vec2 uv) {
    // bilinear over cell centres at 1/6, 3/6, 5/6
    vec2 g = clamp(uv * 3.0 - 0.5, 0.0, 2.0);
    vec2 i = min(floor(g), vec2(1.0));
    vec2 f = g - i;
    int x = int(i.x), y = int(i.y);
    vec3 a = illum[y * 3 + x], b = illum[y * 3 + x + 1], c = illum[(y + 1) * 3 + x], d = illum[(y + 1) * 3 + x + 1];
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }

  vec3 impastoNormal(sampler2D h, vec2 uv, vec2 texel) {
    float l = texture2D(h, uv - vec2(texel.x, 0.0)).r;
    float r = texture2D(h, uv + vec2(texel.x, 0.0)).r;
    float d = texture2D(h, uv - vec2(0.0, texel.y)).r;
    float u = texture2D(h, uv + vec2(0.0, texel.y)).r;
    return normalize(vec3((l - r) * relief, (d - u) * relief, 1.0));
  }

  // Rotate the painting's own pixels inside an annulus (a painted chakra / halo turns in place).
  // Returns rotated uv in .xy and blend weight in .z (feathered annulus × animation intensity).
  vec3 haloWarp(vec2 uv) {
    for (int i = 0; i < 3; i++) {
      vec4 h = halos[i];
      if (h.w <= 0.0 || h.z < 0.0) continue;   // r0 < 0 marks a light-ray halo (see divineRays)
      vec2 d = (uv - h.xy) * vec2(canvasAspect, 1.0);
      float r = length(d);
      float w = smoothstep(h.z, h.z + 0.015, r) * (1.0 - smoothstep(h.w - 0.015, h.w, r));
      if (w <= 0.0) continue;
      float a = haloSpeed[i] * animTime;
      float c = cos(a), sn = sin(a);
      vec2 rd = vec2(c * d.x - sn * d.y, sn * d.x + c * d.y);
      return vec3(h.xy + rd / vec2(canvasAspect, 1.0), w * uAnim);
    }
    return vec3(uv, 0.0);
  }

  // Rotating divine light rays (additive), starting outside radius |r0| so they never cover the
  // deity; used where the painted ring itself is not symmetric enough to rotate.
  float divineRays(vec2 uv) {
    float acc = 0.0;
    for (int i = 0; i < 3; i++) {
      vec4 h = halos[i];
      if (h.w <= 0.0 || h.z >= 0.0) continue;
      vec2 d = (uv - h.xy) * vec2(canvasAspect, 1.0);
      float r = length(d);
      float r0 = -h.z;
      float band = smoothstep(r0, r0 + 0.05, r) * (1.0 - smoothstep(h.w * 0.7, h.w, r));
      float ang = atan(d.y, d.x);
      float rays = pow(abs(sin(ang * 12.0 + haloSpeed[i] * animTime)), 18.0) + 0.6 * pow(abs(sin(ang * 7.0 - haloSpeed[i] * 0.7 * animTime)), 24.0);
      acc += rays * band;
    }
    return acc;
  }

  void main() {
    // uv.y = 0 at bottom in three PlaneGeometry; textures are flipY'd so this is upright.
    vec2 uv = vUv;

    // --- Living Canvas: gently warp the painting's own pixels inside the motion masks.
    //     Masks never cover faces, so faces are never moved or distorted.
    vec3 mo = vec3(0.0); vec4 fx = vec4(0.0);
    if (uAnim > 0.001 && hasFx > 0.5) {
      mo = texture2D(motionMap, vUv).rgb;
      fx = texture2D(fxMap, vUv);
      float t = time;
      vec2 w = vec2(0.0);
      w.x += mo.r * (sin(t * 1.7 + vUv.y * 9.0 + vUv.x * 4.0) * 0.0022 + sin(t * 3.1 + vUv.x * 23.0) * 0.0008); // leaves / garlands
      w.y += mo.r * sin(t * 2.3 + vUv.x * 13.0) * 0.0009;
      w += mo.g * vec2(sin(t * 1.3 + vUv.y * 260.0) * 0.0016, sin(t * 2.0 + vUv.x * 90.0 + vUv.y * 140.0) * 0.0009); // water
      w.x += mo.b * sin(t * 1.6 + vUv.x * 6.0) * 0.006;                                                            // hanging lanterns
      float isFlame = fx.r * (1.0 - smoothstep(0.30, 0.34, fx.b));
      w.x += isFlame * sin(t * 11.0 + fx.g * 40.0 + vUv.y * 160.0) * 0.0016;                                       // flames dance
      w.y += isFlame * sin(t * 7.0 + fx.g * 23.0) * 0.0012;
      uv = vUv + w * uAnim;
    }
    vec3 hw = uAnim > 0.001 ? haloWarp(uv) : vec3(uv, 0.0);

    // --- painterly reveal mask -------------------------------------------------
    float n = fbm(vUv * vec2(6.0, 4.5)) * 0.55 + fbm(vUv * vec2(40.0, 30.0)) * 0.2;
    float sweep = (vUv.x * 0.6 + (1.0 - vUv.y) * 0.25);
    float m = smoothstep(reveal * 1.6 - 0.35, reveal * 1.6 - 0.25, sweep * 0.55 + n * 0.75);
    float mixB = 1.0 - m;
    if (reveal >= 0.999) mixB = 1.0;
    if (reveal <= 0.001) mixB = 0.0;

    vec4 ca = texture2D(mapA, vUv, mipBias);
    vec4 cb = texture2D(mapB, uv, mipBias);
    if (hw.z > 0.001) cb.rgb = mix(cb.rgb, texture2D(mapB, hw.xy, mipBias).rgb, hw.z);
    if (videoMix > 0.001) cb.rgb = mix(cb.rgb, texture2D(videoMap, vUv).rgb, videoMix);
    vec3 albedo = mix(ca.rgb, cb.rgb, mixB);
    vec3 nA = impastoNormal(heightA, vUv, texelA);
    vec3 nB = impastoNormal(heightB, vUv, texelB);
    vec3 N = normalize(mix(nA, nB, mixB));

    // --- canvas weave (plain weave, over/under) -------------------------------
    vec2 t = vUv * sizeCm * threadsPerCm;
    vec2 fw = fwidth(t);
    float aa = 1.0 - smoothstep(0.25, 0.6, max(fw.x, fw.y)); // fade when threads < ~2px
    vec2 cell = floor(t);
    float parity = mod(cell.x + cell.y, 2.0);
    vec2 ft = fract(t);
    float hx = sin(ft.x * 3.14159), hy = sin(ft.y * 3.14159);
    float wv = mix(hy * (0.6 + 0.4 * hx), hx * (0.6 + 0.4 * hy), parity);
    float slub = vnoise(t * 0.37) * 0.5 + 0.5;
    float gx = mix(hy * 0.4 * cos(ft.x * 3.14159) * 3.14159, cos(ft.x * 3.14159) * 3.14159 * (0.6 + 0.4 * hy), parity);
    float gy = mix(cos(ft.y * 3.14159) * 3.14159 * (0.6 + 0.4 * hx), hx * 0.4 * cos(ft.y * 3.14159) * 3.14159, parity);
    float thick = mix(texture2D(heightA, vUv).r, texture2D(heightB, vUv).r, mixB);
    float weaveVis = weaveAmt * aa * (1.0 - 0.6 * smoothstep(0.55, 0.9, thick)) * (0.75 + 0.25 * slub);
    N = normalize(N + vec3(-gx, -gy, 0.0) * 0.12 * weaveVis);

    // --- lighting --------------------------------------------------------------
    vec3 L = normalize(lightDir);
    vec3 V = normalize(vViewDirObj);
    float ndl = dot(N, L), flat_ndl = L.z;
    float shade = 1.0 + 1.15 * (ndl - flat_ndl);
    shade *= 1.0 - 0.06 * weaveVis * (1.0 - wv);
    vec3 H = normalize(L + V);
    float spec = pow(max(dot(N, H), 0.0), 38.0) * specAmt * (0.4 + 0.6 * thick);

    vec2 dcm = min(vUv, 1.0 - vUv) * sizeCm;
    float edge = min(dcm.x, dcm.y);
    float ao = mix(0.72, 1.0, smoothstep(0.0, 1.4, edge)) * mix(0.94, 1.0, smoothstep(0.0, 9.0, edge));

    vec3 E = illumAt(vUv);
    vec3 col = albedo * shade * ao * E + spec * E;

    // --- Living Canvas: light emitters (diya flames, bulbs, stars, divine glow) ---
    if (uAnim > 0.001 && hasFx > 0.5 && fx.r > 0.004 && videoMix < 0.5) {
      float tt = time, ph = fx.g * 6.2831;
      float k = fx.b;
      float e = fx.r * uAnim * mixB;
      if (k < 0.32) {               // flame: organic flicker + warm bloom
        float f = 0.86 + 0.14 * sin(tt * 9.0 + ph * 3.0) * sin(tt * 13.7 + ph) + 0.16 * (vnoise(vec2(tt * 6.0, ph * 9.0)) - 0.5);
        col *= mix(1.0, f, e);
        col += vec3(1.0, 0.62, 0.22) * e * (0.08 + 0.12 * f) * E;
      } else if (k < 0.58) {        // bulb: soft on/off chase along each light string
        float c = fract(tt * 0.5 + fx.g);
        float on = smoothstep(0.30, 0.42, c) * (1.0 - smoothstep(0.88, 1.0, c));
        col *= mix(1.0, mix(0.5, 1.12, on), e);
        col += vec3(1.0, 0.8, 0.45) * e * on * 0.14 * E;
      } else if (k < 0.82) {        // star / sparkle: sharp twinkle
        float tw = pow(max(0.0, sin(tt * 2.6 + ph * 7.0)), 10.0);
        col += vec3(1.0, 0.95, 0.85) * e * tw * 0.5;
      } else {                      // divine / ambient glow: slow breathing
        float b = 0.5 + 0.5 * sin(tt * 1.4 + ph);
        col += vec3(1.0, 0.82, 0.45) * e * (0.05 + 0.11 * b) * E;
      }
    }

    if (uAnim > 0.001) col += vec3(1.0, 0.8, 0.42) * divineRays(vUv) * 0.16 * uAnim * mixB * E;

    // Camera sensor grain (very low, temporally varying) so the overlay shares the feed's noise.
    float g = hash(gl_FragCoord.xy + fract(time * 13.7) * 91.0) - 0.5;
    col += g * grainAmt * (0.4 + col);

    gl_FragColor = vec4(max(col, 0.0), opacity * mix(aAlpha, 1.0, mixB));
    #include <colorspace_fragment>
  }
`;

export function createPaintingMaterial({ widthCm, heightCm }) {
  const blank = new THREE.DataTexture(new Uint8Array([128, 128, 128, 255]), 1, 1);
  blank.needsUpdate = true;
  const black = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
  black.needsUpdate = true;
  const illum = Array.from({ length: 9 }, () => new THREE.Vector3(1, 1, 1));
  const mat = new THREE.ShaderMaterial({
    vertexShader: vert,
    fragmentShader: frag,
    transparent: true,
    depthWrite: false,
    depthTest: false,
    extensions: { derivatives: true },
    uniforms: {
      uH: { value: new THREE.Matrix3() },
      uViewDir: { value: new THREE.Vector3(0, 0, 1) },
      mapA: { value: blank }, heightA: { value: blank }, texelA: { value: new THREE.Vector2(1 / 800, 1 / 600) },
      mapB: { value: blank }, heightB: { value: blank }, texelB: { value: new THREE.Vector2(1 / 800, 1 / 600) },
      reveal: { value: 0 },
      opacity: { value: 0 },
      aAlpha: { value: 0 },
      illum: { value: illum },
      lightDir: { value: new THREE.Vector3(-0.35, 0.45, 1).normalize() },
      sizeCm: { value: new THREE.Vector2(widthCm, heightCm) },
      threadsPerCm: { value: 5.5 },
      relief: { value: 2.4 },
      weaveAmt: { value: 1.0 },
      specAmt: { value: 0.07 },
      mipBias: { value: 0.35 },
      grainAmt: { value: 0.022 },
      time: { value: 0 },
      uAnim: { value: 0 }, animTime: { value: 0 },
      fxMap: { value: black }, motionMap: { value: black }, hasFx: { value: 0 },
      halos: { value: [new THREE.Vector4(), new THREE.Vector4(), new THREE.Vector4()] },
      haloSpeed: { value: [0, 0, 0] },
      canvasAspect: { value: widthCm / heightCm },
      videoMap: { value: blank }, videoMix: { value: 0 },
    },
  });
  mat.userData.black = black;
  return mat;
}

// ---------------------------------------------------------------------------------
// Texture loading with a small LRU so switching paintings is instant after first view.
// Each painting's animation assets (fx map, motion map, animation manifest) are loaded together
// with the painting, so "Bring to Life" starts instantly — nothing is generated on click.
const loader = new THREE.TextureLoader();
const cache = new Map();
const MAX_CACHE = 6;

export function loadPaintingTextures(painting, renderer) {
  const key = painting.id;
  if (cache.has(key)) {
    const v = cache.get(key);
    cache.delete(key); cache.set(key, v); // refresh LRU
    return v;
  }
  const maxAniso = renderer ? renderer.capabilities.getMaxAnisotropy() : 1;
  const optional = (url) => (url ? loader.loadAsync(url).catch(() => null) : Promise.resolve(null));
  const p = Promise.all([
    loader.loadAsync(painting.albedo),
    loader.loadAsync(painting.height),
    optional(painting.fx),
    optional(painting.motion),
    painting.anim ? fetch(painting.anim).then((r) => (r.ok ? r.json() : null)).catch(() => null) : Promise.resolve(null),
  ]).then(([albedo, height, fx, motion, anim]) => {
    albedo.colorSpace = THREE.SRGBColorSpace;
    albedo.anisotropy = Math.min(8, maxAniso);
    albedo.generateMipmaps = true;
    albedo.minFilter = THREE.LinearMipmapLinearFilter;
    height.colorSpace = THREE.NoColorSpace;
    height.minFilter = THREE.LinearFilter;
    height.generateMipmaps = false;
    for (const t of [fx, motion]) {
      if (!t) continue;
      t.colorSpace = THREE.NoColorSpace; t.generateMipmaps = false;
      t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter;
    }
    return { albedo, height, fx, motion, anim, texel: new THREE.Vector2(1 / height.image.width, 1 / height.image.height) };
  });
  cache.set(key, p);
  if (cache.size > MAX_CACHE) {
    const [oldKey, oldP] = cache.entries().next().value;
    cache.delete(oldKey);
    oldP.then((t) => { for (const k of ['albedo', 'height', 'fx', 'motion']) t[k]?.dispose(); }).catch(() => {});
  }
  p.catch(() => cache.delete(key));
  return p;
}
