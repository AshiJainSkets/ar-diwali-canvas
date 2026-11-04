# AR Diwali Canvas

Web AR that makes a hand-painted Diwali artwork appear on a **physical 4 × 3 ft canvas**. Visitors scan a QR code, the page opens in the phone's browser (no app), and the painting locks onto the real canvas. It stays on the canvas, in correct perspective, as they move.

- **Viewer**: welcome screen → gallery of 30 paintings in 10 categories → live AR with painting switching, reset tracking and exit.
- **Admin** (`/admin`): create canvases, generate QR codes (PNG/SVG), download each canvas's tracking print, compile tracking targets in the browser, assign paintings or galleries, and calibrate alignment on a phone.
- **Stack**: Node/Express backend (JSON file store), plain ES-module frontend with no build step, three.js and MindAR (self-hosted under `public/vendor`).

---

## 1. How it works (and the one physical requirement)

**A blank canvas cannot be tracked.** Image trackers need visual texture, and a white canvas has none. A QR code on its own is too small and too repetitive to pin all four corners of a 4 ft frame without visible drift at the edges.

So each canvas gets a **tracking print**: a high-contrast, non-repeating Diwali line-art pattern with that canvas's QR code built in. It is generated as vector SVG at the exact physical size.

| Mode | What you physically install | Accuracy (automated test) |
|---|---|---|
| **Full-canvas print** (recommended) | Tracking print covers the whole 4×3 ft canvas face. The tracked rectangle *is* the canvas. | Corner error ≈ **0.3–0.4 %** of the canvas diagonal, frontal to 38° oblique |
| **Marker plaque** | A smaller plaque (default 30 × 22.5 cm) with QR + pattern at a measured spot inside the canvas. The rest stays blank. | ≈ **0.9–2 %** error with more jitter: corners are extrapolated about 4×. Use the calibration panel. |

Per-frame pipeline (`public/js/ar.js`):

1. **MindAR** finds and tracks the print (feature matching in WebGL, in a worker).
2. We tap the tracker's per-frame point correspondences and fit an **exact planar homography**, robust and outlier-rejecting (`homography.js`). MindAR's own 6-DoF pose assumes a fixed 45° camera FOV. On real phones that drifts at oblique angles: it measured 1.8 % error at 38° versus 0.3 % with the homography.
3. The 4 corners go through a **One-Euro filter**: low jitter when still, low lag when moving. A brief hold and fade covers short tracking dropouts. Re-acquisition snaps rather than glides.
4. The painting quad is mapped through that homography **straight into clip space**, so it is perspective-correct and pinned to the real corners at any angle or distance.

Realism (`paintingMaterial.js`, `lightEstimator.js`):

- **Real light estimation.** We know exactly what the print looks like, so comparing it with what the camera sees gives the room's light per region (3×3 grid). That includes brightness, colour cast and left/right falloff, which are applied to the painting.
- **Impasto relief** from a per-painting height map of brush strokes.
- **Procedural canvas weave**, anti-aliased by screen footprint.
- **Varnish glint** that moves with the phone.
- **Inner frame shadow** along the edges.
- **Camera-matched softness and sensor grain**, so the painting doesn't look "too clean" next to the video.
- **Painterly reveal** when the canvas is first found and when switching paintings.

---

## 2. Quick start (local)

Requirements: **Node 18.17+**. Python 3.10+ is only needed to rebuild the gallery or run the tests.

```bash
npm install
npm start
# → http://localhost:8080        viewer
# → http://localhost:8080/admin  admin (token is printed in the console and saved to data/.admin-token)
```

On first start a **demo canvas** (`/c/demo`) is created with a precompiled tracking target, so the experience works immediately.

Configuration goes in `.env` (copy `.env.example`). This works the same on Windows, macOS and Linux:

| Variable | Purpose |
|---|---|
| `PUBLIC_BASE_URL` | Public **https** origin encoded in QR codes, e.g. `https://diwali.example.com`. **Required in production.** |
| `ADMIN_TOKEN` | Admin password. If unset, one is generated into `data/.admin-token`. |
| `PORT` | HTTP port (default 8080). |
| `DATA_DIR` | Where `canvases.json` and compiled targets live. Use a persistent volume in production. |
| `HTTPS=1` / `npm run dev` | Also start a self-signed HTTPS server on `HTTPS_PORT` (8443), for LAN phone testing. |

---

## 3. Testing on a phone

Browsers only allow the camera on **https** (or `localhost`). Pick one:

**A. Tunnel (recommended, works on iOS and Android).** Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) or ngrok, then:

```bash
npm start
cloudflared tunnel --url http://localhost:8080      # prints https://<random>.trycloudflare.com
```

Set `PUBLIC_BASE_URL` to that https URL in `.env` and restart. In `/admin`, click **Regenerate tracking target** for each canvas, so the printed QR matches the URL.

**B. Same Wi-Fi with self-signed HTTPS.** Run `npm run dev` and open `https://<your-LAN-IP>:8443` on the phone, then accept the certificate warning. Android Chrome works. iOS Safari usually works after "visit this website", but a tunnel is more reliable there.

**Test without the physical canvas.** Open `/api/canvas/demo/print.svg` full-screen on a laptop or monitor (or print it on A3/A4). Then on the phone open `/c/demo` and point it at the screen. Moving the phone around should keep the painting locked to the screen edges.

Supported: iOS Safari 15+, Android Chrome 90+, and recent Samsung Internet and Firefox Android. In-app browsers (Instagram, Facebook) often block the camera; the app detects this and tells users to open the page in Safari or Chrome.

---

## 4. Installing a real canvas (end-to-end)

1. **Create the canvas** in `/admin`: name, ID (this goes into the QR URL), size (default 4 × 3 ft), mode, default painting, and which categories visitors may browse (none ticked means all).
2. **Generate tracking target.** This compiles the print into a MindAR `.mind` file in your browser in about 10–60 s, then uploads it.
3. **Download the tracking print (SVG)** and send it to a print shop:
   - Print at **100 % scale**, exactly the listed size (121.9 × 91.4 cm for 4 × 3 ft), edge to edge.
   - Use **matte** canvas or matte vinyl. Glossy lamination causes glare, and glare breaks tracking.
   - For a gallery-wrapped canvas, ask the printer to add **mirrored edge bleed** for the wrap. The SVG artwork must land exactly on the *front face*.
   - Many shops prefer PDF. Open the SVG in Inkscape or Illustrator and export a PDF at the same size, without rescaling.
4. **Mount it**: stretch onto the frame (full mode), or fix the plaque at the measured position (marker mode).
5. **Light it evenly.** No hard spotlight hotspots on the surface.
6. **Calibrate.** In `/admin` click **Calibrate**, which opens `/c/<id>?calibrate=1` (do this on a phone). When the canvas locks:
   - The **cyan dashed** outline shows the tracked print. The **gold** outline shows the painting edge.
   - Turn on **Peek** (semi-transparent painting) and nudge **Shift / Scale / Rotate** until the gold edge sits on the real canvas edge.
   - Pick a **Tracking** feel: *stable* (least jitter), *balanced*, or *responsive* (least lag).
   - **Save**. You need the admin token once; it is then remembered on that phone.
7. **Verify.** Scan the printed QR with the phone camera, then walk left, right, closer and farther. The painting should stay inside the frame.

The QR always opens the same canvas. To change what that canvas shows, edit its painting or gallery in `/admin`. **You never need to reprint.**

You only need to regenerate the target and reprint if you change the canvas size, the mode or the marker size. The admin page flags when that happens. It also flags when `PUBLIC_BASE_URL` changed since the print was made.

---

## 5. Production deployment

Any Node host with HTTPS and a **persistent disk** for `DATA_DIR` will work.

**Docker:**

```bash
docker build -t ar-diwali-canvas .
docker run -d -p 8080:8080 -v ardc-data:/data \
  -e PUBLIC_BASE_URL=https://diwali.example.com -e ADMIN_TOKEN='long-random-secret' ar-diwali-canvas
```

Put it behind a TLS reverse proxy: Caddy (automatic HTTPS), Nginx with Let's Encrypt, or Cloudflare. The app sets `trust proxy`, so the forwarded https host is respected.

**Render / Railway / Fly.io:** create a Node web service with start command `npm start`. Attach a persistent volume and set `DATA_DIR` to its mount path, then set `PUBLIC_BASE_URL` and `ADMIN_TOKEN`.

**Checklist before printing QR codes:**

- `PUBLIC_BASE_URL` is your final https domain. QR codes encode it permanently.
- Each canvas shows "Tracking target vN ready" with no stale warning.
- `ADMIN_TOKEN` is long and secret.

Caching: vendor libraries and fonts are cached for 30 days, paintings for 7 days, and responses are gzip-compressed. First AR load is about 0.4 MB gzipped for MindAR and tfjs, about 0.2 MB for three.js, about 0.9 MB for the tracking target, and about 0.4 MB per painting. The heavy AR bundle is prefetched while the welcome screen is shown.

---

## 6. Gallery: sample art and adding your own

The 30 sample paintings are **original, procedurally generated** compositions (`tools/paintings/compositions.py`), turned into oil or acrylic-looking paintings by a brush-stroke filter (`paintify.py`). Each painting has:

- `albedo.jpg` (1600×1200) and `height.jpg` (800×600, impasto) — used in AR
- `preview.jpg` and `thumb.jpg` — gallery images with canvas lighting baked in

Deities are shown through respectful line-art or symbols (lotus, footsteps, Om, gaja-abhishek), not detailed figurative portraits. **For a commercial installation, replace or extend them with commissioned or licensed artwork:**

```bash
pip install opencv-python numpy
python tools/paintings/import_painting.py my-scan.jpg --id lakshmi-puja --category lakshmi \
  --title "Lakshmi Puja" --medium "Acrylic on canvas" --description "Commissioned, 2026"
# add --painterly for flat digital art you want turned into brush strokes
```

The script crops the image to 4:3, builds the height map and previews, and updates `public/paintings/catalog.json`. For best results use a scan or photo of at least 3000 px, evenly lit and without glare. To regenerate the sample set: `npm run gallery:build` (needs `pip install playwright opencv-python numpy` and `playwright install chromium`).

---

## 7. Verification

`tools/e2e/` contains an automated test that needs no phone. It renders the real tracking print onto a wall in a synthetic camera video with known geometry, framing, lighting gradient, colour cast, blur and sensor noise. That video is fed to headless Chromium as the webcam. The real app then runs: tracker, homography, smoothing and renderer. Finally the test measures the rendered painting corners against the true canvas corners.

```bash
npm i -D playwright && npx playwright install chromium && pip install playwright opencv-python numpy
npm start   # in another terminal
npm run test:e2e   # bash (macOS/Linux/WSL/Git Bash)
```

Results from the build (960×540 video, headless software WebGL):

| Scenario | First lock | Mean corner error | Worst | Jitter (σ) |
|---|---|---|---|---|
| Frontal, 2.5 m | 2.5 s | 1.7 px (0.40 %) | 2.0 px | 0.0 px |
| 38° yaw, −12° pitch, 2.2 m | 2.5 s | 1.2 px (0.31 %) | 2.5 px | 0.5 px |
| Close, 1.35 m, −22° | 2.6 s | 2.4 px (0.32 %) | 4.7 px | 1.3 px |
| Moving orbit ±32°, 3.0 → 1.7 m | — | locked 100 % of samples | — | — |
| Marker plaque, frontal | 2.6 s | 8.4 px (1.97 %) | 18.8 px | 0.1 px |
| Marker plaque, 38° | 2.5 s | 3.6 px (0.88 %) | 10.0 px | 3.9 px |

Also verified in a browser:

- Welcome, gallery, filters, detail sheet, AR, painting switch, calibration panel, unknown-canvas error.
- Admin sign-in, canvas creation, in-browser target compile and upload.
- QR PNG/SVG and print downloads, HTTPS mode, auth errors.

**Not verified here:** real phones and a real printed canvas. The synthetic test is a strong proxy, but do the on-site calibration (section 4, step 6) and a walk-around check before opening to visitors.

`/dev/harness.html?canvas=<id>&guides=1` is a bare diagnostics page showing tracking state, video resolution and the light-estimation gains.

---

## 8. Known limitations

- **Occlusion**: a person standing in front of the canvas gets painted over. Web AR has no reliable person segmentation on all phones.
- **Distance and angle** (estimate, not yet measured on real phones): expect reliable tracking from about 0.8 m to 4 m and up to about 50–60° off-axis. Beyond that the print is too small or too foreshortened in the image. The synthetic tests cover 1.35–3 m and up to 38°.
- **Lighting**: very dark rooms, strong glare or coloured stage lighting reduce tracking. The app detects low light and tells the user.
- **Light estimation** is a per-region gain on the paper-white parts of the print. It matches overall exposure, colour cast and gradients, not sharp cast shadows.
- **Marker mode** extrapolates far beyond the plaque, so small tracking noise grows about 4× at the far corners. Prefer full-canvas mode, or use a larger plaque (≥ 45 cm wide) placed centrally.
- MindAR is used unmodified from npm (1.2.5, MIT). The homography tap relies on its internal `tracker.track()` method. If you upgrade MindAR, re-run the E2E test; if that hook is missing, the app falls back to MindAR's pose automatically.

---

## 9. Project map

```
server/
  index.js          Express app: pages, public API, admin API, QR, prints, HTTPS option, .env loader
  store.js          JSON-file canvas registry (atomic writes)
  targetPrint.js    Deterministic tracking-print SVG generator (pattern + QR)
  seed/             Precompiled demo target
public/
  index.html        Viewer shell (welcome · gallery · AR · messages)
  admin.html        Admin UI
  js/app.js         Viewer UI logic, error handling, calibration panel
  js/ar.js          AR session: camera, MindAR, homography, smoothing, render loop
  js/homography.js  Robust homography fit + One-Euro filter
  js/paintingMaterial.js  Painted-canvas shader + texture cache
  js/lightEstimator.js    Room-light estimation from the known print
  js/targetCompiler.js    In-browser .mind compiler (admin + CLI)
  js/admin.js       Admin logic
  paintings/        catalog.json + 30 paintings
  vendor/           three.js r160, MindAR 1.2.5 (self-hosted)
tools/
  compile-target.mjs        Headless target compile (CI / seeding)
  paintings/                Gallery generator, painterly filter, importer
  e2e/                      Synthetic-camera tracking tests, UI and admin flows
```

## API (summary)

| Method | Path | Auth | |
|---|---|---|---|
| GET | `/c/:id` | – | Viewer for a canvas (what the QR opens) |
| GET | `/api/canvas/:id` | – | Public canvas config |
| GET | `/api/canvas/:id/qr.png?size=2048&download=1` | – | QR PNG |
| GET | `/api/canvas/:id/qr.svg` | – | QR SVG |
| GET | `/api/canvas/:id/print.svg?download=1` | – | Tracking print at physical size |
| GET/POST | `/api/admin/canvases` | token | List / create |
| PUT/DELETE | `/api/admin/canvases/:id` | token | Update / delete |
| PUT | `/api/admin/canvases/:id/calibration` | token | Save calibration and tracking preset |
| POST | `/api/admin/canvases/:id/target` | token | Upload compiled `.mind` |

The admin token goes in the `x-admin-token` header.

Third-party: three.js (MIT), MindAR (MIT), Cormorant Garamond, Manrope and Noto Serif Devanagari fonts (SIL OFL 1.1).
