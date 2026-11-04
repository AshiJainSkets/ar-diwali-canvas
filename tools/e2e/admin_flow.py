"""Admin E2E: sign in, create a marker-mode canvas, compile its target in-browser, verify via API."""
import sys, json, time, urllib.request
from playwright.sync_api import sync_playwright
base, token, out = sys.argv[1:4]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    pg = b.new_page(viewport={'width': 1200, 'height': 900})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(base + '/admin'); pg.fill('#token', token); pg.click('#login-btn'); pg.wait_for_selector('#list .cv')
    pg.fill('#form [name=name]', 'Lobby plaque canvas'); pg.fill('#form [name=id]', 'lobby-plaque')
    pg.select_option('#form [name=mode]', 'marker')
    pg.fill('#form [name=tW]', '30'); pg.fill('#form [name=tH]', '22.5'); pg.fill('#form [name=tX]', '86.9'); pg.fill('#form [name=tY]', '63.9')
    pg.click('#pick button[data-id="gold-1"]'); pg.click('#save-btn')
    pg.wait_for_selector('[data-id="lobby-plaque"]')
    pg.click('[data-id="lobby-plaque"] [data-a="compile"]')
    t0 = time.time()
    while time.time() - t0 < 120:
        txt = pg.inner_text('[data-id="lobby-plaque"] [data-msg]') if pg.query_selector('[data-id="lobby-plaque"] [data-msg]') else ''
        if 'Done' in txt or 'failed' in txt: break
        time.sleep(0.5)
    pg.wait_for_timeout(800)
    pg.screenshot(path=f'{out}/admin.png', full_page=True)
    print('msg:', txt, 'errors:', errs)
    b.close()
req = urllib.request.Request(base + '/api/admin/canvases/lobby-plaque', headers={'x-admin-token': token})
c = json.load(urllib.request.urlopen(req))
print('targetUrl', c['targetUrl'], 'stale', c['targetStale'], 'target', c['target'])
