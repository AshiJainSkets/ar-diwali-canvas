"""Screenshot the main UI states (welcome, gallery, detail, AR locked, picker) for review."""
import sys, time
from playwright.sync_api import sync_playwright
base, vdir, out = sys.argv[1:4]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
        f'--use-file-for-fake-video-capture={vdir}/angled.y4m', '--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    errs = []
    ph = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ph.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.goto(base + '/'); pg.wait_for_timeout(1500); pg.screenshot(path=f'{out}/1_welcome.png')
    pg.click('#btn-gallery'); pg.wait_for_timeout(1200); pg.screenshot(path=f'{out}/2_gallery.png')
    pg.click('.cat[data-cat="rajasthani"]'); pg.wait_for_timeout(800)
    pg.click('.card[data-id="rajasthani-3"]'); pg.wait_for_timeout(900); pg.screenshot(path=f'{out}/3_detail.png')
    pg.click('[data-act="select"]'); pg.wait_for_timeout(500)
    ls = b.new_context(viewport={'width': 844, 'height': 390}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pa = ls.new_page(); pa.on('pageerror', lambda e: errs.append(str(e))); pa.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pa.goto(base + '/c/demo?painting=lakshmi-3'); pa.wait_for_timeout(600); pa.screenshot(path=f'{out}/4_ar_loading.png')
    t0 = time.time()
    while time.time() - t0 < 40 and pa.evaluate('window.__ar && window.__ar.state') != 'tracking': time.sleep(0.3)
    pa.wait_for_timeout(2600); pa.screenshot(path=f'{out}/5_ar_locked.png')
    pa.click('#ar-pick'); pa.wait_for_timeout(900); pa.screenshot(path=f'{out}/6_ar_picker.png')
    pa.click('#picker .card:nth-child(2)'); pa.wait_for_timeout(900); pa.screenshot(path=f'{out}/7_ar_switching.png')
    pa.wait_for_timeout(1800); pa.screenshot(path=f'{out}/8_ar_switched.png')
    pa.goto(base + '/c/demo?calibrate=1'); 
    t0 = time.time()
    while time.time() - t0 < 40 and pa.evaluate('window.__ar && window.__ar.state') != 'tracking': time.sleep(0.3)
    pa.wait_for_timeout(2500); pa.screenshot(path=f'{out}/9_ar_calibrate.png')
    pg.goto(base + '/c/nope'); pg.wait_for_timeout(1000); pg.screenshot(path=f'{out}/10_notfound.png')
    print('errors:', errs[:6])
    b.close()
