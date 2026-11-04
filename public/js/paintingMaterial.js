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

  void main() {
    vec2 uv = vUv;
    // uv.y = 0 at bottom in three PlaneGeometry; textures are flipY'd so this is upright.

    // --- painterly reveal mask -------------------------------------------------
    float n = fbm(uv * vec2(6.0, 4.5)) * 0.55 + fbm(uv * vec2(40.0, 30.0)) * 0.2;
    float sweep = (uv.x * 0.6 + (1.0 - uv.y) * 0.25);
    float m = smoothstep(reveal * 1.6 - 0.35, reveal * 1.6 - 0.25, sweep * 0.55 + n * 0.75);
    float mixB = 1.0 - m;
    if (reveal >= 0.999) mixB = 1.0;
    if (reveal <= 0.001) mixB = 0.0;

    vec4 ca = texture2D(mapA, uv, mipBias);
    vec4 cb = texture2D(mapB, uv, mipBias);
    vec3 albedo = mix(ca.rgb, cb.rgb, mixB);
    vec3 nA = impastoNormal(heightA, uv, texelA);
    vec3 nB = impastoNormal(heightB, uv, texelB);
    vec3 N = normalize(mix(nA, nB, mixB));

    // --- canvas weave (plain weave, over/under) -------------------------------
    vec2 t = uv * sizeCm * threadsPerCm;
    vec2 fw = fwidth(t);
    float aa = 1.0 - smoothstep(0.25, 0.6, max(fw.x, fw.y)); // fade when threads < ~2px
    vec2 cell = floor(t);
    float parity = mod(cell.x + cell.y, 2.0);
    vec2 ft = fract(t);
    float hx = sin(ft.x * 3.14159), hy = sin(ft.y * 3.14159);
    float wv = mix(hy * (0.6 + 0.4 * hx), hx * (0.6 + 0.4 * hy), parity);
    // Thread slubs: tiny irregularity so the weave isn't a perfect grid.
    float slub = vnoise(t * 0.37) * 0.5 + 0.5;
    // Analytic weave gradient in uv space
    float gx = mix(hy * 0.4 * cos(ft.x * 3.14159) * 3.14159, cos(ft.x * 3.14159) * 3.14159 * (0.6 + 0.4 * hy), parity);
    float gy = mix(cos(ft.y * 3.14159) * 3.14159 * (0.6 + 0.4 * hx), hx * 0.4 * cos(ft.y * 3.14159) * 3.14159, parity);
    // Paint fills the weave where it's thick (impasto), so weave shows most in thin areas.
    float thick = mix(texture2D(heightA, uv).r, texture2D(heightB, uv).r, mixB);
    float weaveVis = weaveAmt * aa * (1.0 - 0.6 * smoothstep(0.55, 0.9, thick)) * (0.75 + 0.25 * slub);
    N = normalize(N + vec3(-gx, -gy, 0.0) * 0.12 * weaveVis);

    // --- lighting --------------------------------------------------------------
    vec3 L = normalize(lightDir);
    vec3 V = normalize(vViewDirObj);
    float ndl = dot(N, L), flat_ndl = L.z;
    float shade = 1.0 + 1.15 * (ndl - flat_ndl);              // relative: flat areas keep albedo
    shade *= 1.0 - 0.06 * weaveVis * (1.0 - wv);             // thread valleys catch less light
    vec3 H = normalize(L + V);
    float spec = pow(max(dot(N, H), 0.0), 38.0) * specAmt * (0.4 + 0.6 * thick);

    // Inner shadow along the frame / stretcher edge (~1.2 cm) + gentle edge falloff.
    vec2 dcm = min(uv, 1.0 - uv) * sizeCm;
    float edge = min(dcm.x, dcm.y);
    float ao = mix(0.72, 1.0, smoothstep(0.0, 1.4, edge)) * mix(0.94, 1.0, smoothstep(0.0, 9.0, edge));

    vec3 E = illumAt(uv);
    vec3 col = albedo * shade * ao * E + spec * E;

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
    },
  });
  return mat;
}

// ---------------------------------------------------------------------------------
// Texture loading with a small LRU so switching paintings is instant after first view.
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
  const p = Promise.all([
    loader.loadAsync(painting.albedo),
    loader.loadAsync(painting.height),
  ]).then(([albedo, height]) => {
    albedo.colorSpace = THREE.SRGBColorSpace;
    albedo.anisotropy = Math.min(8, maxAniso);
    albedo.generateMipmaps = true;
    albedo.minFilter = THREE.LinearMipmapLinearFilter;
    height.colorSpace = THREE.NoColorSpace;
    height.minFilter = THREE.LinearFilter;
    height.generateMipmaps = false;
    return { albedo, height, texel: new THREE.Vector2(1 / height.image.width, 1 / height.image.height) };
  });
  cache.set(key, p);
  if (cache.size > MAX_CACHE) {
    const [oldKey, oldP] = cache.entries().next().value;
    cache.delete(oldKey);
    oldP.then((t) => { t.albedo.dispose(); t.height.dispose(); }).catch(() => {});
  }
  p.catch(() => cache.delete(key));
  return p;
}
