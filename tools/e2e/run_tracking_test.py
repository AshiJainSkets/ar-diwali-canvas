"""Automated AR alignment test.

Feeds a synthetic camera video (known geometry) into headless Chromium as the webcam,
runs the real tracker + renderer via /dev/harness.html, and measures the distance between
the rendered painting corners and the true canvas corners.

usage: python run_tracking_test.py <base_url> <video_dir> <scenario> [screenshot.png] [canvas_id]
"""
import sys, json, time, math
from playwright.sync_api import sync_playwright

base, vdir, name = sys.argv[1:4]
shot = sys.argv[4] if len(sys.argv) > 4 else None
canvas_id = sys.argv[5] if len(sys.argv) > 5 else 'demo'
gt = json.load(open(f'{vdir}/{name}.json'))
VW_, VH_ = 390, 844  # portrait phone-ish viewport (iPhone 14)
VIEW = (844, 390) if name != 'portrait' else (VW_, VH_)  # landscape: canvas is landscape

with sync_playwright() as p:
    b = p.chromium.launch(args=[
        '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
        f'--use-file-for-fake-video-capture={vdir}/{name}.y4m',
        '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist'])
    ctx = b.new_context(viewport={'width': VIEW[0], 'height': VIEW[1]}, device_scale_factor=1)
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.goto(f'{base}/dev/harness.html?auto=1&canvas={canvas_id}')
    t0 = time.time()
    found_at = None
    samples = []
    while time.time() - t0 < (70 if name == 'moving' else 45):
        st = pg.evaluate('window.__ar && window.__ar.state')
        if pg.evaluate('window.__err || null'):
            print('ERROR', pg.evaluate('window.__err')); break
        if st == 'tracking' and found_at is None:
            found_at = time.time() - t0
        if found_at is not None:
            r = pg.evaluate('''() => { const s = window.__ar, v = s.video, st = v.style;
                return { c: s.paintingCornersOnScreen(), op: s.opacity, tracking: s.state === 'tracking',
                  left: parseFloat(st.left), top: parseFloat(st.top), w: parseFloat(st.width), h: parseFloat(st.height),
                  vw: v.videoWidth, vh: v.videoHeight, illum: s.light.gains[4], illumL: s.light.gains[3], illumR: s.light.gains[5], stats: s.stats } }''')
            samples.append(r)
            if name != 'moving' and len(samples) >= 25: break
        time.sleep(0.25)
    if shot:
        pg.screenshot(path=shot)
    states = pg.evaluate('window.__states || []')
    b.close()

print(f'scenario={name} first_lock={found_at and round(found_at,1)}s states={states[:8]} errors={errs[:3]}')
if not samples:
    print('NO LOCK'); sys.exit(1)

def to_screen(r, pt):
    return (r['left'] + pt[0] / r['vw'] * r['w'], r['top'] + pt[1] / r['vh'] * r['h'])

if name != 'moving':
    good = [s for s in samples[5:] if s['c'] and s['tracking']]
    exp = [to_screen(good[0], pt) for pt in gt['corners'][0]]
    # canvas diagonal on screen for relative error
    diag = math.dist(exp[0], exp[2])
    errs_px = []
    for s in good:
        e = [math.dist((c['x'], c['y']), x) for c, x in zip(s['c'], exp)]
        errs_px.append(e)
    mean = sum(sum(e) / 4 for e in errs_px) / len(errs_px)
    worst = max(max(e) for e in errs_px)
    # jitter: std of corner positions over time
    import statistics as stt
    jit = max(stt.pstdev([s['c'][k]['x'] for s in good]) + stt.pstdev([s['c'][k]['y'] for s in good]) for k in range(4))
    print(f'corner error mean={mean:.1f}px worst={worst:.1f}px ({100*mean/diag:.2f}% of canvas diagonal {diag:.0f}px)  jitter={jit:.2f}px  samples={len(good)}')
    print('stats', good[-1]['stats']); print('illum centre', [round(x, 2) for x in good[-1]['illum']], 'left', [round(x, 2) for x in good[-1]['illumL']], 'right', [round(x, 2) for x in good[-1]['illumR']])
else:
    locked = sum(1 for s in samples if s['tracking'])
    print(f'moving: tracked {locked}/{len(samples)} samples ({100*locked/len(samples):.0f}%)')
