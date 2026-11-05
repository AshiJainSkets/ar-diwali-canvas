"""SVG motif library for the sample Diwali gallery (procedural, original artwork).

Every function returns an SVG fragment string. Coordinates are in the painting's
1600×1200 viewBox. All randomness goes through a seeded `random.Random`.
"""
import math, os

FONT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'public', 'fonts'))
W, H = 1600, 1200

# ---- animation anchors -------------------------------------------------------------
# Motifs record what they draw (flames, lanterns, fireworks, stars...) so every painting gets an
# animation built from its exact contents. Callers that wrap motifs in SVG transforms pause
# recording with `with no_anchors():` and add their own anchors.
ANCHORS = []
_REC = [True]


def anchor(*a):
    if _REC[0]:
        ANCHORS.append(a)


class no_anchors:
    def __enter__(self): self.prev = _REC[0]; _REC[0] = False
    def __exit__(self, *e): _REC[0] = self.prev


def reset_anchors():
    ANCHORS.clear(); _REC[0] = True


def f(v):
    return f'{v:.1f}'


def defs(extra=''):
    deva = f'file://{FONT_DIR}/noto-serif-devanagari-devanagari-700-normal.woff2'
    corm = f'file://{FONT_DIR}/cormorant-garamond-latin-600-italic.woff2'
    return f'''<defs>
<style>
@font-face {{ font-family: 'Deva'; src: url('{deva}'); font-weight: 700; }}
@font-face {{ font-family: 'Corm'; src: url('{corm}'); font-style: italic; }}
</style>
<radialGradient id="flame" cx="50%" cy="70%" r="60%"><stop offset="0" stop-color="#fffef2"/><stop offset="0.35" stop-color="#fff2a8"/><stop offset="0.7" stop-color="#ffb627"/><stop offset="1" stop-color="#ff6a00"/></radialGradient>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffd27a" stop-opacity="0.85"/><stop offset="0.35" stop-color="#ffab3d" stop-opacity="0.35"/><stop offset="1" stop-color="#ff7a00" stop-opacity="0"/></radialGradient>
<radialGradient id="glowSoft" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffe2a0" stop-opacity="0.5"/><stop offset="1" stop-color="#ff8c1a" stop-opacity="0"/></radialGradient>
<linearGradient id="clay" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c8643a"/><stop offset="0.6" stop-color="#9a3f1f"/><stop offset="1" stop-color="#5e2210"/></linearGradient>
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset="0.25" stop-color="#e9b949"/><stop offset="0.5" stop-color="#b8841f"/><stop offset="0.75" stop-color="#f4d27a"/><stop offset="1" stop-color="#8a5a12"/></linearGradient>
<linearGradient id="goldV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbe6a2"/><stop offset="0.5" stop-color="#d4a23a"/><stop offset="1" stop-color="#7d5110"/></linearGradient>
<linearGradient id="copper" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6e2d12"/><stop offset="0.35" stop-color="#d9824b"/><stop offset="0.55" stop-color="#f3b07a"/><stop offset="1" stop-color="#7a3414"/></linearGradient>
<radialGradient id="petalPink" cx="50%" cy="90%" r="90%"><stop offset="0" stop-color="#fff4f6"/><stop offset="0.55" stop-color="#f7a8c0"/><stop offset="1" stop-color="#d2477a"/></radialGradient>
<radialGradient id="petalWhite" cx="50%" cy="90%" r="90%"><stop offset="0" stop-color="#ffffff"/><stop offset="0.6" stop-color="#fbe9ef"/><stop offset="1" stop-color="#e8a3bd"/></radialGradient>
<filter id="blur2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2"/></filter>
<filter id="blur6" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="blur20" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="20"/></filter>
<filter id="blur60" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>
<filter id="mottle" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.004 0.006" numOctaves="4" seed="3"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.55 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
<filter id="goldleaf" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="9" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0.98  0 0 0 0 0.80  0 0 0 0 0.38  0 0 0 1.6 -0.55" result="g"/><feComposite in="g" in2="SourceGraphic" operator="in"/></filter>
{extra}
</defs>'''


def rect_bg(fill):
    return f'<rect width="{W}" height="{H}" fill="{fill}"/>'


def lin_bg(stops, x1=0, y1=0, x2=0, y2=1, gid='bg'):
    s = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<defs><linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient></defs><rect width="{W}" height="{H}" fill="url(#{gid})"/>'


def rad_bg(stops, cx=0.5, cy=0.5, r=0.75, gid='rbg'):
    s = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<defs><radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient></defs><rect width="{W}" height="{H}" fill="url(#{gid})"/>'


def mottle(opacity=0.35, color='#000'):
    return f'<rect width="{W}" height="{H}" fill="{color}" opacity="{opacity}" filter="url(#mottle)"/>'


def glow(x, y, r, opacity=1.0, grad='glow'):
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="url(#{grad})" opacity="{opacity}"/>'


def flame(x, y, h, lean=0.0):
    anchor('flame', x, y - h * 0.45, h)
    w = h * 0.38
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({lean})">'
            f'<path d="M0 0 C{f(-w)} {f(-h*0.25)} {f(-w*0.35)} {f(-h*0.7)} 0 {f(-h)} C{f(w*0.35)} {f(-h*0.7)} {f(w)} {f(-h*0.25)} 0 0Z" fill="url(#flame)"/>'
            f'<path d="M0 {f(-h*0.05)} C{f(-w*0.35)} {f(-h*0.25)} {f(-w*0.15)} {f(-h*0.5)} 0 {f(-h*0.62)} C{f(w*0.15)} {f(-h*0.5)} {f(w*0.35)} {f(-h*0.25)} 0 {f(-h*0.05)}Z" fill="#fffef6" opacity="0.85"/>'
            '</g>')


def diya(x, y, s, body='clay', band='#f5c542', dots='#fff1c9', lit=True, glow_r=None, lean=0):
    """Clay oil lamp. (x,y) = centre of the rim, s = half-width."""
    fill = {'clay': 'url(#clay)', 'gold': 'url(#gold)', 'brass': 'url(#goldV)'}.get(body, body)
    out = []
    if lit:
        out.append(glow(x + s * 0.7, y - s * 0.55, glow_r or s * 3.2))
    out.append(f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">')
    # bowl with spout to the right
    out.append(f'<path d="M-1 0 C-0.95 0.55 -0.45 0.78 0 0.78 C0.5 0.78 0.85 0.5 1.0 0.12 L1.32 -0.12 C1.05 -0.08 0.95 -0.04 0.92 -0.04 C0.4 0.12 -0.4 0.12 -1 0Z" fill="{fill}"/>')
    out.append(f'<path d="M-0.92 0.16 C-0.4 0.34 0.45 0.34 0.94 0.12" stroke="{band}" stroke-width="0.09" fill="none"/>')
    for i in range(9):
        t = -0.78 + i * 0.19
        out.append(f'<circle cx="{f(t)}" cy="{f(0.42 + 0.05 * math.cos(t*1.6))}" r="0.035" fill="{dots}"/>')
    out.append('<ellipse cx="-0.04" cy="0.0" rx="0.96" ry="0.13" fill="#3a1608" opacity="0.85"/>')
    out.append('<ellipse cx="-0.04" cy="0.02" rx="0.8" ry="0.08" fill="#c9861f" opacity="0.8"/>')
    out.append('</g>')
    if lit:
        out.append(flame(x + s * 1.18, y - s * 0.1, s * 1.15, lean))
    return ''.join(out)


def lotus(x, y, s, grad='petalPink', leaf=True, rot=0):
    if s >= 60:
        anchor('petals', x, y - s * 0.55, s * 0.5, ['#f7a8c0', '#fbe9ef', '#d2477a'])
    out = [f'<g transform="translate({f(x)} {f(y)}) rotate({rot}) scale({f(s)})">']
    if leaf:
        out.append('<ellipse cx="0" cy="0.2" rx="1.55" ry="0.32" fill="#2f6b3a"/><ellipse cx="0" cy="0.16" rx="1.4" ry="0.24" fill="#4f8f4c"/>')
    petal = 'M0 0 C-0.32 -0.35 -0.28 -0.85 0 -1.15 C0.28 -0.85 0.32 -0.35 0 0Z'
    for a in (-75, 75, -55, 55):
        out.append(f'<path d="{petal}" transform="rotate({a}) scale(0.9)" fill="url(#{grad})" stroke="#b83c6a" stroke-width="0.012"/>')
    for a in (-30, 30, -12, 12, 0):
        out.append(f'<path d="{petal}" transform="rotate({a}) scale({1.05 if a == 0 else 1.0})" fill="url(#{grad})" stroke="#b83c6a" stroke-width="0.012"/>')
    out.append('</g>')
    return ''.join(out)


def marigold(x, y, r, rng, base='#f28c0f', hi='#ffc93c', dark='#c45a06'):
    out = [f'<g transform="translate({f(x)} {f(y)})">', f'<circle r="{f(r)}" fill="{dark}"/>']
    rings = 4
    for k in range(rings):
        rr = r * (1 - k / (rings + 0.6))
        n = max(7, int(18 * rr / r))
        col = [base, hi, base, hi][k % 4] if k else base
        for i in range(n):
            a = (i + rng.random() * 0.5) / n * 360 + k * 13
            out.append(f'<ellipse cx="0" cy="{f(-rr*0.62)}" rx="{f(rr*0.2)}" ry="{f(rr*0.42)}" fill="{col}" transform="rotate({a:.0f})" opacity="0.95"/>')
    out.append(f'<circle r="{f(r*0.18)}" fill="{dark}"/></g>')
    return ''.join(out)


def leaf(x, y, l, ang, col='#2f7a32', vein='#9fd17a'):
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({ang:.0f})"><path d="M0 0 C{f(l*0.3)} {f(-l*0.22)} {f(l*0.75)} {f(-l*0.18)} {f(l)} 0 C{f(l*0.75)} {f(l*0.18)} {f(l*0.3)} {f(l*0.22)} 0 0Z" fill="{col}"/>'
            f'<path d="M0 0 L{f(l*0.95)} 0" stroke="{vein}" stroke-width="{f(max(1,l*0.03))}"/></g>')


def garland(x0, y0, x1, y1, sag, r, rng, colors=(('#f28c0f', '#ffc93c', '#c45a06'), ('#ffd23a', '#fff07a', '#d99a06'))):
    out = []
    n = int(math.hypot(x1 - x0, y1 - y0) / (r * 1.55))
    for i in range(n + 1):
        t = i / max(1, n)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        if i % 3 == 1:
            out.append(leaf(x, y + r * 0.4, r * 1.4, 70 + rng.random() * 40))
        c = colors[i % len(colors)]
        out.append(marigold(x, y, r * (0.9 + rng.random() * 0.2), rng, *c))
        anchor('sway', x - r * 1.3, y - r * 1.3, x + r * 1.3, y + r * 1.8, 0.8)
        if i % 5 == 2:
            anchor('petals', x, y, r * 1.2, [c[0], c[1], '#ffe066'])
    return ''.join(out)


def toran(y, rng, x0=0, x1=W, leaf_len=70):
    anchor('sway', x0, y, x1, y + leaf_len * 1.05, 0.9)
    out = [f'<rect x="{x0}" y="{y-14}" width="{x1-x0}" height="16" fill="#8b1e1e"/>']
    n = int((x1 - x0) / (leaf_len * 0.55))
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        out.append(leaf(x, y, leaf_len * (0.9 + rng.random() * 0.25), 90 + rng.uniform(-6, 6), col=['#2c6e2f', '#3f8a3a'][i % 2]))
    for i in range(0, n, 3):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        out.append(marigold(x, y + 4, 20, rng))
    return ''.join(out)


def rangoli(cx, cy, R, rng, pal, outline='#fff7e8', layers=None):
    """Radially-symmetric rangoli built from random ring types."""
    out = [f'<g transform="translate({f(cx)} {f(cy)})">']
    ring_types = layers or ['scallop', 'petals', 'dots', 'triangles', 'petals', 'leafring', 'star', 'center']
    radius = R
    k = 0
    for typ in ring_types:
        col = pal[k % len(pal)]
        col2 = pal[(k + 2) % len(pal)]
        k += 1
        n = rng.choice([8, 12, 16]) if radius > R * 0.35 else 8
        if typ == 'scallop':
            out.append(f'<circle r="{f(radius)}" fill="{col}"/>')
            for i in range(n * 2):
                a = math.radians(i * 360 / (n * 2))
                out.append(f'<circle cx="{f(math.cos(a)*radius)}" cy="{f(math.sin(a)*radius)}" r="{f(radius*math.pi/(n*2)*1.05)}" fill="{col}" stroke="{outline}" stroke-width="3"/>')
            out.append(f'<circle r="{f(radius*0.97)}" fill="{col}"/>')
            radius *= 0.86
        elif typ == 'petals':
            out.append(f'<circle r="{f(radius)}" fill="{col2}" opacity="0.0"/>')
            for i in range(n):
                out.append(f'<path d="M0 0 C{f(radius*0.22)} {f(-radius*0.4)} {f(radius*0.18)} {f(-radius*0.8)} 0 {f(-radius)} C{f(-radius*0.18)} {f(-radius*0.8)} {f(-radius*0.22)} {f(-radius*0.4)} 0 0Z" transform="rotate({i*360/n:.1f})" fill="{col}" stroke="{outline}" stroke-width="3"/>')
                out.append(f'<path d="M0 {f(-radius*0.25)} C{f(radius*0.1)} {f(-radius*0.45)} {f(radius*0.08)} {f(-radius*0.7)} 0 {f(-radius*0.82)} C{f(-radius*0.08)} {f(-radius*0.7)} {f(-radius*0.1)} {f(-radius*0.45)} 0 {f(-radius*0.25)}Z" transform="rotate({i*360/n:.1f})" fill="{col2}"/>')
            out.append(f'<circle r="{f(radius*0.42)}" fill="{pal[(k+1)%len(pal)]}" stroke="{outline}" stroke-width="3"/>')
            radius *= 0.42
        elif typ == 'dots':
            m = n * 3
            for i in range(m):
                a = math.radians(i * 360 / m)
                out.append(f'<circle cx="{f(math.cos(a)*radius*0.9)}" cy="{f(math.sin(a)*radius*0.9)}" r="{f(radius*0.045)}" fill="{outline}"/>')
            radius *= 0.84
        elif typ == 'triangles':
            out.append(f'<circle r="{f(radius)}" fill="{col}" stroke="{outline}" stroke-width="3"/>')
            for i in range(n):
                a = i * 360 / n
                out.append(f'<polygon points="0,{f(-radius)} {f(radius*0.2)},{f(-radius*0.72)} {f(-radius*0.2)},{f(-radius*0.72)}" transform="rotate({a:.1f})" fill="{col2}" stroke="{outline}" stroke-width="2"/>')
            radius *= 0.72
        elif typ == 'leafring':
            out.append(f'<circle r="{f(radius)}" fill="{col}" stroke="{outline}" stroke-width="3"/>')
            for i in range(n * 2):
                a = i * 360 / (n * 2)
                out.append(f'<ellipse cx="0" cy="{f(-radius*0.78)}" rx="{f(radius*0.07)}" ry="{f(radius*0.17)}" transform="rotate({a:.1f})" fill="{col2}" stroke="{outline}" stroke-width="1.5"/>')
            radius *= 0.58
        elif typ == 'star':
            pts = []
            for i in range(16):
                rr = radius if i % 2 == 0 else radius * 0.55
                a = math.radians(i * 360 / 16 - 90)
                pts.append(f'{f(math.cos(a)*rr)},{f(math.sin(a)*rr)}')
            out.append(f'<polygon points="{" ".join(pts)}" fill="{col}" stroke="{outline}" stroke-width="3"/>')
            radius *= 0.5
        elif typ == 'center':
            out.append(f'<circle r="{f(radius)}" fill="{col2}" stroke="{outline}" stroke-width="3"/>')
            for i in range(8):
                out.append(f'<ellipse cx="0" cy="{f(-radius*0.55)}" rx="{f(radius*0.2)}" ry="{f(radius*0.4)}" transform="rotate({i*45})" fill="{col}"/>')
            out.append(f'<circle r="{f(radius*0.25)}" fill="{outline}"/>')
    out.append('</g>')
    return ''.join(out)


def firework(x, y, r, color, rng, n=36, width=3):
    anchor('firework', x, y, r, color)
    out = [glow(x, y, r * 0.9, 0.5, 'glowSoft')]
    for i in range(n):
        a = i / n * 2 * math.pi + rng.random() * 0.1
        rr = r * (0.75 + rng.random() * 0.3)
        x2, y2 = x + math.cos(a) * rr, y + math.sin(a) * rr + rr * 0.08
        xm, ym = x + math.cos(a) * rr * 0.3, y + math.sin(a) * rr * 0.3
        out.append(f'<path d="M{f(xm)} {f(ym)} Q{f(x+math.cos(a)*rr*0.7)} {f(y+math.sin(a)*rr*0.7)} {f(x2)} {f(y2)}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none" opacity="0.85"/>')
        out.append(f'<circle cx="{f(x2)}" cy="{f(y2)}" r="{f(width*1.4)}" fill="#fff6d8"/>')
    out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r*0.06)}" fill="#fffbe6"/>')
    return ''.join(out)


def bokeh(rng, n, x0, y0, x1, y1, colors, rmin=6, rmax=30, op=(0.25, 0.7)):
    out = []
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(rmin, rmax)
        anchor('bulb', x, y, r, (x * 0.0137 + y * 0.0071) % 1.0)  # no rng call: keeps the painting identical
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{rng.choice(colors)}" opacity="{rng.uniform(*op):.2f}"/>')
    return ''.join(out)


def stars(rng, n, y1=600, color='#fff8e0'):
    out = []
    for _ in range(n):
        x, y, r, o = rng.uniform(0, W), rng.uniform(0, y1), rng.uniform(0.8, 2.6), rng.uniform(0.4, 1)
        if r > 1.6:
            anchor('star', x, y, r * 3.5)
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{color}" opacity="{o:.2f}"/>')
    return ''.join(out)


def lantern(x, y, s, color='#e0303a', color2='#ffb000', rng=None):
    """Akash kandil (star lantern) hanging from a string."""
    anchor('swing', x, 0, s * 2.6, y + s * 1.9)
    anchor('glow', x, y, s * 0.9)
    out = [f'<line x1="{f(x)}" y1="0" x2="{f(x)}" y2="{f(y - s)}" stroke="#2b1408" stroke-width="2"/>', glow(x, y, s * 2.6, 0.9)]
    out.append(f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">')
    pts = []
    for i in range(16):
        rr = 1.0 if i % 2 == 0 else 0.55
        a = math.radians(i * 22.5 - 90)
        pts.append(f'{f(math.cos(a)*rr)},{f(math.sin(a)*rr)}')
    out.append(f'<polygon points="{" ".join(pts)}" fill="{color}" stroke="{color2}" stroke-width="0.04"/>')
    out.append(f'<circle r="0.42" fill="{color2}"/><circle r="0.3" fill="#fff3c4"/>')
    for i in range(8):
        a = math.radians(i * 45 + 22.5)
        out.append(f'<line x1="0" y1="0" x2="{f(math.cos(a)*0.55)}" y2="{f(math.sin(a)*0.55)}" stroke="{color2}" stroke-width="0.03"/>')
    for i, dx in enumerate((-0.35, -0.12, 0.12, 0.35)):
        out.append(f'<path d="M{dx} 0.6 L{dx*1.1} {1.7 + 0.15 * (i % 2)}" stroke="{color2}" stroke-width="0.06"/>')
        out.append(f'<circle cx="{dx*1.1}" cy="{1.75 + 0.15 * (i % 2)}" r="0.07" fill="{color}"/>')
    out.append('</g>')
    return ''.join(out)


def sky_lantern(x, y, s):
    anchor('flame', x, y + s * 0.3, s * 1.6)
    return (glow(x, y, s * 3, 0.7) +
            f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})"><path d="M-0.6 -1 L0.6 -1 L0.8 1 L-0.8 1Z" fill="#ffb347"/><path d="M-0.45 -0.85 L0.45 -0.85 L0.6 0.9 L-0.6 0.9Z" fill="#ffe08a"/><ellipse cx="0" cy="1" rx="0.8" ry="0.12" fill="#ff8c1a"/></g>')


def kalash(x, y, s, body='url(#copper)'):
    out = [f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">']
    for i, a in enumerate(range(-70, 80, 20)):
        out.append(f'<path d="M0 -0.95 C0.15 -1.2 0.35 -1.45 0.08 -1.95 C-0.12 -1.45 -0.1 -1.2 0 -0.95Z" transform="rotate({a} 0 -0.95)" fill="{["#2e6b2e","#3d8a3a"][i%2]}"/>')
    out.append('<ellipse cx="0" cy="-1.18" rx="0.36" ry="0.42" fill="#7a4a1d"/><ellipse cx="0" cy="-1.3" rx="0.22" ry="0.2" fill="#a06a2f" opacity="0.7"/>')
    out.append('<path d="M-0.34 -1.05 Q0 -1.2 0.34 -1.05 L0.3 -0.9 Q0 -1.0 -0.3 -0.9Z" fill="#c4282d"/>')
    out.append(f'<path d="M-0.42 -0.95 L0.42 -0.95 L0.36 -0.72 C0.95 -0.45 1.0 0.45 0.55 0.8 L-0.55 0.8 C-1.0 0.45 -0.95 -0.45 -0.36 -0.72Z" fill="{body}"/>')
    out.append('<path d="M-0.86 -0.1 Q0 0.1 0.86 -0.1" stroke="#c4282d" stroke-width="0.07" fill="none"/>')
    out.append('<path d="M-0.86 0.06 Q0 0.26 0.86 0.06" stroke="#f1c34b" stroke-width="0.04" fill="none"/>')
    for i in range(7):
        t = -0.6 + i * 0.2
        out.append(f'<circle cx="{f(t)}" cy="{f(-0.32 + 0.04*abs(t))}" r="0.05" fill="#c4282d"/>')
    out.append('<ellipse cx="0" cy="0.82" rx="0.6" ry="0.08" fill="#4a1d0a"/></g>')
    return ''.join(out)


def coins(x, y, s, rng, n=14, spread=1.0):
    out = []
    for i in range(n):
        cx = x + rng.gauss(0, s * 1.6 * spread)
        cy = y + rng.gauss(0, s * 0.35 * spread)
        r = s * rng.uniform(0.45, 0.6)
        tilt = rng.uniform(0.35, 0.7)
        if i % 3 == 0:
            anchor('star', cx, cy - r * 0.2, r * 0.7)
        out.append(f'<g transform="translate({f(cx)} {f(cy)}) rotate({rng.uniform(-20,20):.0f})"><ellipse rx="{f(r)}" ry="{f(r*tilt)}" fill="#8a5a12"/><ellipse rx="{f(r*0.95)}" ry="{f(r*tilt*0.9)}" cy="{f(-r*0.06)}" fill="url(#gold)"/><ellipse rx="{f(r*0.6)}" ry="{f(r*tilt*0.55)}" cy="{f(-r*0.06)}" fill="none" stroke="#9b6a14" stroke-width="{f(r*0.06)}"/></g>')
    return ''.join(out)


def footprint(x, y, s, ang=0, color='#c4142b', deco='#fff1d6'):
    out = [f'<g transform="translate({f(x)} {f(y)}) rotate({ang}) scale({f(s)})">']
    out.append(f'<path d="M0 -0.55 C0.42 -0.6 0.5 -0.1 0.38 0.35 C0.3 0.75 0.28 0.95 0 1.0 C-0.3 0.95 -0.3 0.6 -0.33 0.3 C-0.4 -0.15 -0.35 -0.52 0 -0.55Z" fill="{color}"/>')
    for i, (tx, ty, tr) in enumerate([(-0.18, -0.66, 0.15), (0.06, -0.73, 0.11), (0.23, -0.68, 0.095), (0.35, -0.58, 0.08), (0.42, -0.45, 0.065)]):
        out.append(f'<circle cx="{tx}" cy="{ty}" r="{tr}" fill="{color}"/>')
    out.append(f'<circle cx="0" cy="0.15" r="0.12" fill="none" stroke="{deco}" stroke-width="0.04"/><circle cx="0" cy="0.15" r="0.04" fill="{deco}"/>')
    for a in range(0, 360, 45):
        out.append(f'<ellipse cx="0" cy="-0.06" rx="0.025" ry="0.06" transform="rotate({a} 0 0.15)" fill="{deco}"/>')
    out.append('</g>')
    return ''.join(out)


def om(x, y, size, fill='url(#gold)', opacity=1):
    anchor('glow', x, y, size * 0.5)
    return f'<text x="{f(x)}" y="{f(y)}" font-family="Deva" font-weight="700" font-size="{f(size)}" text-anchor="middle" dominant-baseline="central" fill="{fill}" opacity="{opacity}">ॐ</text>'


def deva_text(x, y, txt, size, fill='#ffd36b', opacity=1):
    return f'<text x="{f(x)}" y="{f(y)}" font-family="Deva" font-weight="700" font-size="{f(size)}" text-anchor="middle" fill="{fill}" opacity="{opacity}">{txt}</text>'


def ganesha(x, y, s, line='url(#gold)', fill='none', accent='#c4142b', sw=0.035):
    """Minimal line-art Ganesha (crown, ears, eyes, trunk curling right, belly)."""
    st = f'stroke="{line}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
    o = [f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})" fill="{fill}">']
    # crown
    o.append(f'<path d="M-0.42 -0.62 C-0.42 -0.95 -0.15 -1.1 0 -1.45 C0.15 -1.1 0.42 -0.95 0.42 -0.62Z" {st}/>')
    o.append(f'<path d="M-0.42 -0.62 Q0 -0.7 0.42 -0.62" {st}/><path d="M-0.3 -0.82 Q0 -0.9 0.3 -0.82" {st}/>')
    o.append(f'<circle cx="0" cy="-1.0" r="0.07" fill="{accent}"/>')
    # head
    o.append(f'<path d="M-0.42 -0.62 C-0.5 -0.35 -0.45 -0.1 -0.28 0.05 M0.42 -0.62 C0.5 -0.35 0.45 -0.1 0.28 0.05" {st}/>')
    # ears (large fans with scalloped edge)
    for sgn in (-1, 1):
        o.append(f'<path d="M{0.43*sgn} -0.55 C{0.95*sgn} -0.85 {1.25*sgn} -0.45 {1.15*sgn} -0.05 C{1.12*sgn} 0.3 {0.85*sgn} 0.45 {0.55*sgn} 0.25 C{0.5*sgn} 0.18 {0.46*sgn} 0.1 {0.4*sgn} 0.02" {st}/>')
        o.append(f'<path d="M{0.62*sgn} -0.45 C{0.95*sgn} -0.55 {1.02*sgn} -0.2 {0.95*sgn} 0.05" {st} opacity="0.7"/>')
    # eyes + tilak
    for sgn in (-1, 1):
        o.append(f'<path d="M{0.12*sgn} -0.38 Q{0.22*sgn} -0.45 {0.32*sgn} -0.38 Q{0.22*sgn} -0.33 {0.12*sgn} -0.38Z" {st}/>')
    o.append(f'<path d="M-0.08 -0.6 Q0 -0.45 0.08 -0.6" stroke="{accent}" stroke-width="{sw*1.2}" fill="none"/><circle cx="0" cy="-0.47" r="0.035" fill="{accent}"/>')
    # trunk: two parallel curves curling to the right
    o.append(f'<path d="M-0.12 -0.28 C-0.16 0.1 -0.2 0.4 -0.05 0.62 C0.1 0.85 0.42 0.8 0.42 0.58 C0.42 0.44 0.28 0.42 0.24 0.52" {st}/>')
    o.append(f'<path d="M0.12 -0.28 C0.1 0.05 0.06 0.32 0.16 0.48" {st}/>')
    # tusk
    o.append(f'<path d="M-0.26 0.02 C-0.36 0.12 -0.4 0.22 -0.36 0.3" {st}/>')
    # belly + modak hand hint
    o.append(f'<path d="M-0.55 0.35 C-0.95 0.7 -0.85 1.35 -0.2 1.42 C0.45 1.48 0.95 1.2 0.75 0.6" {st}/>')
    o.append(f'<path d="M-0.2 1.42 Q0 1.25 0.2 1.42" {st} opacity="0.7"/>')
    o.append(f'<circle cx="0.62" cy="0.62" r="0.13" fill="none" {st}/><path d="M0.55 0.55 L0.62 0.5 L0.69 0.55" {st}/>')
    o.append('</g>')
    return ''.join(o)


def elephant(x, y, s, body='#5b6b8c', cloth='#c4142b', trim='#f1c34b', facing=1):
    """Decorated side-view elephant (Rajasthani style). (x,y) = ground under the body centre."""
    o = [f'<g transform="translate({f(x)} {f(y)}) scale({f(s*facing)} {f(s)})">']
    # legs
    for lx in (-0.75, -0.42, 0.35, 0.68):
        o.append(f'<path d="M{lx-0.14} -0.55 L{lx-0.15} -0.02 Q{lx} 0.04 {lx+0.15} -0.02 L{lx+0.14} -0.55Z" fill="{body}"/>')
        o.append(f'<rect x="{lx-0.16}" y="-0.16" width="0.32" height="0.06" fill="{trim}"/>')
    # body
    o.append(f'<path d="M-1.05 -0.75 C-1.1 -1.25 -0.6 -1.45 -0.05 -1.42 C0.5 -1.4 0.85 -1.3 0.98 -1.0 L1.0 -0.55 C0.6 -0.42 -0.7 -0.42 -1.0 -0.55Z" fill="{body}"/>')
    # tail
    o.append(f'<path d="M-1.04 -0.95 C-1.18 -0.8 -1.18 -0.6 -1.12 -0.45" stroke="{body}" stroke-width="0.05" fill="none"/>')
    # head + trunk (raised)
    o.append(f'<path d="M0.75 -1.25 C0.9 -1.65 1.45 -1.7 1.58 -1.3 C1.68 -1.0 1.62 -0.75 1.58 -0.5 C1.56 -0.3 1.62 -0.15 1.78 -0.12 C1.9 -0.1 1.95 -0.22 1.92 -0.3 L1.98 -0.32 C2.02 -0.1 1.9 0.02 1.74 0.0 C1.48 -0.04 1.42 -0.3 1.42 -0.55 C1.4 -0.75 1.25 -0.85 1.0 -0.82Z" fill="{body}"/>')
    # ear
    o.append(f'<path d="M0.95 -1.35 C0.7 -1.35 0.6 -1.0 0.72 -0.78 C0.85 -0.62 1.12 -0.75 1.15 -1.0Z" fill="{body}" stroke="#2c3550" stroke-width="0.02"/>')
    o.append(f'<path d="M0.95 -1.35 C0.7 -1.35 0.6 -1.0 0.72 -0.78" stroke="{trim}" stroke-width="0.03" fill="none"/>')
    # eye + tusk
    o.append('<circle cx="1.3" cy="-1.25" r="0.035" fill="#120d0a"/>')
    o.append('<path d="M1.42 -0.68 C1.6 -0.62 1.72 -0.7 1.78 -0.82" stroke="#fff6e0" stroke-width="0.06" stroke-linecap="round" fill="none"/>')
    # head ornament (forehead patterns)
    o.append(f'<path d="M1.25 -1.55 C1.45 -1.5 1.55 -1.25 1.52 -1.0" stroke="{trim}" stroke-width="0.04" fill="none"/>')
    for i in range(5):
        o.append(f'<circle cx="{1.55 - i*0.005}" cy="{-1.0 + i*0.12}" r="0.03" fill="{trim}"/>')
    # caparison (jhool)
    o.append(f'<path d="M-0.55 -1.36 C-0.1 -1.48 0.4 -1.44 0.62 -1.32 L0.6 -0.66 L-0.55 -0.66Z" fill="{cloth}"/>')
    o.append(f'<path d="M-0.55 -0.66 L0.6 -0.66" stroke="{trim}" stroke-width="0.06"/>')
    for i in range(12):
        tx = -0.52 + i * 0.1
        o.append(f'<path d="M{tx} -0.66 L{tx+0.05} -0.56 L{tx+0.1} -0.66Z" fill="{trim}"/>')
    o.append(f'<rect x="-0.4" y="-1.25" width="0.85" height="0.45" fill="none" stroke="{trim}" stroke-width="0.03"/>')
    o.append(f'<circle cx="0.02" cy="-1.03" r="0.13" fill="none" stroke="{trim}" stroke-width="0.03"/><circle cx="0.02" cy="-1.03" r="0.05" fill="{trim}"/>')
    # howdah/canopy hint
    o.append(f'<path d="M-0.35 -1.42 L-0.3 -1.75 Q0.05 -2.05 0.4 -1.75 L0.45 -1.42Z" fill="{trim}" opacity="0.9"/><path d="M0.05 -2.0 L0.05 -2.18" stroke="{trim}" stroke-width="0.04"/>')
    o.append('</g>')
    return ''.join(o)


def peacock(x, y, s, rng, fan=True):
    if fan:
        anchor('sway', x - s * 2.0, y - s * 2.0, x + s * 2.0, y - s * 0.6, 0.5)
    o = [f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">']
    if fan:
        for i in range(23):
            a = math.radians(-160 + i * (140 / 22))
            L = 1.9 + rng.uniform(-0.1, 0.1)
            ex, ey = math.cos(a) * L, math.sin(a) * L
            o.append(f'<path d="M0 0 Q{f(ex*0.5)} {f(ey*0.5 - 0.05)} {f(ex)} {f(ey)}" stroke="#2f7d4f" stroke-width="0.05" fill="none"/>')
            anchor('star', x + ex * s, y + ey * s, s * 0.09)
            o.append(f'<g transform="translate({f(ex)} {f(ey)}) rotate({math.degrees(a)+90:.0f})"><ellipse rx="0.2" ry="0.28" fill="#1f8a5b"/><ellipse rx="0.14" ry="0.2" fill="#d8b23a"/><ellipse rx="0.09" ry="0.13" fill="#1a5fa8"/><ellipse rx="0.045" ry="0.07" fill="#0b1f4a"/></g>')
    # body
    o.append('<path d="M-0.3 0.15 C-0.4 -0.3 -0.1 -0.6 0.05 -0.75 C0.1 -1.0 0.05 -1.2 0.15 -1.35 C0.3 -1.45 0.42 -1.35 0.38 -1.2 L0.5 -1.15 L0.38 -1.1 C0.3 -0.9 0.38 -0.6 0.4 -0.3 C0.45 0.0 0.2 0.25 -0.3 0.15Z" fill="#1959b5"/>')
    o.append('<path d="M0.05 -0.75 C0.0 -0.45 0.05 -0.2 0.2 0.05" stroke="#2ec4b6" stroke-width="0.05" fill="none"/>')
    o.append('<circle cx="0.27" cy="-1.27" r="0.03" fill="#fff"/>')
    for i in range(3):
        o.append(f'<path d="M{0.18 + i*0.06} -1.38 L{0.12 + i*0.09} -1.58" stroke="#1959b5" stroke-width="0.02"/><circle cx="{0.12 + i*0.09}" cy="-1.6" r="0.035" fill="#2ec4b6"/>')
    o.append('<path d="M-0.15 0.1 L-0.2 0.45 M0.12 0.12 L0.12 0.45" stroke="#6b4a1d" stroke-width="0.04"/>')
    o.append('</g>')
    return ''.join(o)


def cusped_arch(x, y, w, h, fill, stroke='none', sw=0):
    """Rajasthani multi-foil (cusped) arch opening. (x,y)=bottom-left."""
    r = w / 2
    lobes = 7
    pts = [f'M{f(x)} {f(y)} L{f(x)} {f(y - h + r)}']
    for i in range(lobes):
        a0 = math.pi + i * math.pi / lobes
        a1 = math.pi + (i + 1) * math.pi / lobes
        ex, ey = x + r + r * math.cos(a1), y - h + r + r * math.sin(a1) * 1.15
        pts.append(f'A{f(r/lobes*1.25)} {f(r/lobes*1.25)} 0 0 1 {f(ex)} {f(ey)}')
    pts.append(f'L{f(x + w)} {f(y)} Z')
    return f'<path d="{" ".join(pts)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def warli_figure(x, y, s, ang=0, color='#f6efe2', arms='up'):
    o = [f'<g transform="translate({f(x)} {f(y)}) rotate({ang:.0f}) scale({f(s)})" fill="{color}" stroke="{color}" stroke-linecap="round">']
    o.append('<circle cx="0" cy="-1.55" r="0.28"/>')
    o.append('<polygon points="-0.42,-1.2 0.42,-1.2 0,-0.5" /><polygon points="0,-0.5 -0.42,0.15 0.42,0.15"/>')
    if arms == 'up':
        o.append('<path d="M-0.35 -1.12 L-0.75 -0.7 L-1.0 -1.2 M0.35 -1.12 L0.75 -0.7 L1.0 -1.2" stroke-width="0.1" fill="none"/>')
    else:
        o.append('<path d="M-0.35 -1.12 L-0.8 -0.9 L-1.05 -0.55 M0.35 -1.12 L0.8 -0.9 L1.05 -0.55" stroke-width="0.1" fill="none"/>')
    o.append('<path d="M-0.2 0.15 L-0.42 0.95 L-0.62 1.05 M0.2 0.15 L0.42 0.95 L0.62 1.05" stroke-width="0.1" fill="none"/>')
    o.append('</g>')
    return ''.join(o)


def mandala_lines(cx, cy, R, rng, color='url(#gold)', sw=3, rings=7):
    anchor('mandala', cx, cy, R)
    o = [f'<g transform="translate({f(cx)} {f(cy)})" fill="none" stroke="{color}" stroke-width="{sw}">']
    r = R
    for k in range(rings):
        n = rng.choice([12, 16, 24, 32])
        kind = k % 4
        o.append(f'<circle r="{f(r)}"/>')
        if kind == 0:
            for i in range(n):
                o.append(f'<path d="M0 {f(-r)} C{f(r*0.12)} {f(-r*0.92)} {f(r*0.1)} {f(-r*0.84)} 0 {f(-r*0.8)} C{f(-r*0.1)} {f(-r*0.84)} {f(-r*0.12)} {f(-r*0.92)} 0 {f(-r)}" transform="rotate({i*360/n:.1f})"/>')
            r *= 0.8
        elif kind == 1:
            for i in range(n):
                a = math.radians(i * 360 / n)
                o.append(f'<circle cx="{f(math.cos(a)*r*0.92)}" cy="{f(math.sin(a)*r*0.92)}" r="{f(r*0.05)}"/>')
            r *= 0.85
        elif kind == 2:
            for i in range(n):
                o.append(f'<path d="M0 {f(-r)} L{f(r*0.08)} {f(-r*0.82)} L0 {f(-r*0.7)} L{f(-r*0.08)} {f(-r*0.82)}Z" transform="rotate({i*360/n:.1f})"/>')
            r *= 0.7
        else:
            for i in range(n):
                o.append(f'<path d="M0 0 L0 {f(-r)}" transform="rotate({i*360/n:.1f})" opacity="0.5"/>')
            o.append(f'<circle r="{f(r*0.8)}"/>')
            r *= 0.72
    o.append('</g>')
    return ''.join(o)


def haveli(x0, y_ground, w, h, rng, wall='#2a1630', window='#ffb84d', diya_row=True):
    """Silhouetted house/haveli with glowing jharokha windows and diyas on the ledges."""
    o = [f'<rect x="{f(x0)}" y="{f(y_ground-h)}" width="{f(w)}" height="{f(h)}" fill="{wall}"/>']
    # parapet + domes
    o.append(f'<rect x="{f(x0-10)}" y="{f(y_ground-h-18)}" width="{f(w+20)}" height="22" fill="{wall}"/>')
    for i in range(int(w // 120)):
        cx = x0 + 60 + i * 120
        o.append(f'<path d="M{f(cx-34)} {f(y_ground-h-18)} Q{f(cx)} {f(y_ground-h-95)} {f(cx+34)} {f(y_ground-h-18)}Z" fill="{wall}"/><path d="M{f(cx)} {f(y_ground-h-80)} L{f(cx)} {f(y_ground-h-102)}" stroke="{wall}" stroke-width="4"/>')
    floors = max(1, int(h // 170))
    for fl in range(floors):
        yb = y_ground - 30 - fl * 170
        n = max(1, int(w // 110))
        for i in range(n):
            cx = x0 + (i + 0.5) * w / n
            o.append(glow(cx, yb - 55, 70, 0.35, 'glowSoft'))
            anchor('glow', cx, yb - 50, 30)
            o.append(cusped_arch(cx - 26, yb, 52, 100, window))
            o.append(cusped_arch(cx - 26, yb, 52, 100, 'none', '#5c2a14', 3))
        if diya_row:
            for i in range(int(w // 46)):
                dx = x0 + 23 + i * 46
                o.append(diya(dx, yb + 8, 11, glow_r=34))
    return ''.join(o)


def temple(x, y_ground, s, color='#1d1030'):
    """Nagara-style shikhara temple silhouette."""
    o = [f'<g transform="translate({f(x)} {f(y_ground)}) scale({f(s)})" fill="{color}">']
    o.append('<rect x="-1.2" y="-0.9" width="2.4" height="0.9"/>')
    o.append('<rect x="-1.4" y="-0.15" width="2.8" height="0.15"/>')
    o.append('<path d="M-0.75 -0.9 C-0.75 -2.0 -0.35 -2.9 0 -3.2 C0.35 -2.9 0.75 -2.0 0.75 -0.9Z"/>')
    o.append('<ellipse cx="0" cy="-3.22" rx="0.22" ry="0.09"/><path d="M0 -3.3 L0 -3.75 L0.3 -3.62 L0 -3.5" />')
    o.append('<path d="M-1.2 -0.9 C-1.2 -1.4 -1.0 -1.75 -0.8 -1.9 C-0.75 -1.4 -0.75 -1.1 -0.75 -0.9Z M1.2 -0.9 C1.2 -1.4 1.0 -1.75 0.8 -1.9 C0.75 -1.4 0.75 -1.1 0.75 -0.9Z"/>')
    o.append('</g>')
    return ''.join(o)


def paisley(x, y, s, ang, fill, inner='#fff4dc'):
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({ang:.0f}) scale({f(s)})">'
            f'<path d="M0 1 C-1 0.95 -1.05 -0.25 -0.25 -0.65 C0.35 -0.95 0.95 -0.7 0.85 -0.15 C0.75 0.25 0.35 0.3 0.4 -0.05 C0.85 0.6 0.6 1.0 0 1Z" fill="{fill}"/>'
            f'<path d="M0 0.75 C-0.65 0.7 -0.7 -0.1 -0.15 -0.38" stroke="{inner}" stroke-width="0.06" fill="none"/>'
            f'<circle cx="-0.2" cy="0.2" r="0.16" fill="{inner}"/></g>')
