"""Premium rangoli collection (replaces the old basic rangolis).

Two families, each design drawn on the 1600×1200 canvas:
  • Powder rangolis   — intricate symmetric designs (mandala, lotus, peacock, diya, geometric)
                        rendered as vector art, then given a coloured-powder finish (grainy fill,
                        irregular powder edges, chalk-white outlines, slight relief) on a stone floor.
  • Flower rangolis   — arrangements built from thousands of individually shaded petals and flower
                        heads (marigold, rose, jasmine, lotus, mixed) with real cast shadows on a
                        polished floor, like a photograph of a petal rangoli.

Every design function returns (svg_body, anchors) — anchors drive its "Bring to Life" animation.
"""
import math, random

W, H = 1600, 1200
CX, CY = 800, 600
TAU = math.tau
DENSITY = 2.3  # flower rangolis are packed so the floor barely shows through


def f(v):
    return f'{v:.1f}'


def pol(cx, cy, r, a):
    return cx + math.cos(a) * r, cy + math.sin(a) * r


def path_petal(r0, r1, width, a, cx=CX, cy=CY, bulge=0.5, tip=0.0):
    """Petal from radius r0 to r1 along angle a (radians), half-width `width` at bulge point."""
    rm = r0 + (r1 - r0) * bulge
    p0 = pol(cx, cy, r0, a)
    p1 = pol(cx, cy, r1, a)
    ca, sa = math.cos(a), math.sin(a)
    nx, ny = -sa, ca
    m = pol(cx, cy, rm, a)
    c1 = (m[0] + nx * width, m[1] + ny * width)
    c2 = (m[0] - nx * width, m[1] - ny * width)
    t = pol(cx, cy, r1 + tip, a)
    return (f'M{f(p0[0])} {f(p0[1])} Q{f(c1[0])} {f(c1[1])} {f(t[0])} {f(t[1])} '
            f'Q{f(c2[0])} {f(c2[1])} {f(p0[0])} {f(p0[1])}Z')


# =========================================================================================
# POWDER RANGOLIS
# =========================================================================================
POWDER_DEFS = '''<defs>
<filter id="powder" x="-5%" y="-5%" width="110%" height="110%">
  <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="floorTex" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.012 0.018" numOctaves="5" seed="11"/>
  <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.55 0"/>
  <feComposite in2="SourceGraphic" operator="in"/>
</filter>
<radialGradient id="vign" cx="50%" cy="50%" r="70%"><stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.55"/></radialGradient>
<radialGradient id="flameG" cx="50%" cy="70%" r="60%"><stop offset="0" stop-color="#fffef2"/><stop offset="0.4" stop-color="#ffe27a"/><stop offset="0.8" stop-color="#ffa21f"/><stop offset="1" stop-color="#ff6a00"/></radialGradient>
<radialGradient id="glowG" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffd27a" stop-opacity="0.75"/><stop offset="0.4" stop-color="#ffab3d" stop-opacity="0.25"/><stop offset="1" stop-color="#ff7a00" stop-opacity="0"/></radialGradient>
<linearGradient id="clayG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c8643a"/><stop offset="0.6" stop-color="#9a3f1f"/><stop offset="1" stop-color="#5e2210"/></linearGradient>
</defs>'''

WHITE = '#fbf6ea'


def floor(base='#2b2a30', tex=0.55):
    return (f'<rect width="{W}" height="{H}" fill="{base}"/>'
            f'<rect width="{W}" height="{H}" fill="#000" opacity="{tex}" filter="url(#floorTex)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#vign)"/>')


def ring_petals(n, r0, r1, width, fill, outline=WHITE, ow=2.5, rot=0.0, bulge=0.5, cx=CX, cy=CY):
    return ''.join(f'<path d="{path_petal(r0, r1, width, rot + i * TAU / n, cx, cy, bulge)}" fill="{fill}" stroke="{outline}" stroke-width="{ow}"/>' for i in range(n))


def ring_dots(n, r, rad, fill=WHITE, rot=0.0, cx=CX, cy=CY):
    return ''.join(f'<circle cx="{f(pol(cx, cy, r, rot + i * TAU / n)[0])}" cy="{f(pol(cx, cy, r, rot + i * TAU / n)[1])}" r="{f(rad)}" fill="{fill}"/>' for i in range(n))


def circle(r, fill='none', stroke=WHITE, sw=3, cx=CX, cy=CY):
    return f'<circle cx="{cx}" cy="{cy}" r="{f(r)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def scallop_ring(n, r, depth, fill, stroke=WHITE, sw=3, cx=CX, cy=CY, rot=0.0):
    pts = []
    for i in range(n):
        a0 = rot + i * TAU / n
        a1 = rot + (i + 1) * TAU / n
        am = (a0 + a1) / 2
        p0 = pol(cx, cy, r, a0); pm = pol(cx, cy, r + depth * 2, am); p1 = pol(cx, cy, r, a1)
        if i == 0:
            pts.append(f'M{f(p0[0])} {f(p0[1])}')
        pts.append(f'Q{f(pm[0])} {f(pm[1])} {f(p1[0])} {f(p1[1])}')
    return f'<path d="{" ".join(pts)}Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def star_poly(n, r_out, r_in, fill, stroke=WHITE, sw=3, rot=-math.pi / 2, cx=CX, cy=CY):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        x, y = pol(cx, cy, r, rot + i * math.pi / n)
        pts.append(f'{f(x)},{f(y)}')
    return f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def paisley_at(x, y, s, ang, fill, inner, stroke=WHITE):
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({ang:.1f}) scale({f(s)})">'
            f'<path d="M0 1 C-1 0.95 -1.05 -0.25 -0.25 -0.65 C0.35 -0.95 0.95 -0.7 0.85 -0.15 C0.75 0.25 0.35 0.3 0.4 -0.05 C0.85 0.6 0.6 1.0 0 1Z" fill="{fill}" stroke="{stroke}" stroke-width="{2.4 / s:.3f}"/>'
            f'<path d="M0 0.72 C-0.62 0.66 -0.66 -0.06 -0.14 -0.34" stroke="{inner}" stroke-width="{3 / s:.3f}" fill="none"/>'
            f'<circle cx="-0.18" cy="0.2" r="0.16" fill="{inner}"/></g>')


def clay_diya(x, y, s, anchors):
    """Clay diya on the floor with a live flame (records its flame anchor)."""
    fy = y - s * 0.1
    anchors.append(('flame', x + s * 1.18, fy - s * 0.52, s * 1.15))
    return (f'<circle cx="{f(x + s * 0.9)}" cy="{f(fy - s * 0.4)}" r="{f(s * 3.6)}" fill="url(#glowG)"/>'
            f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">'
            f'<ellipse cx="0" cy="0.62" rx="1.15" ry="0.22" fill="#000" opacity="0.45"/>'
            f'<path d="M-1 0 C-0.95 0.55 -0.45 0.78 0 0.78 C0.5 0.78 0.85 0.5 1.0 0.12 L1.32 -0.12 C1.05 -0.08 0.95 -0.04 0.92 -0.04 C0.4 0.12 -0.4 0.12 -1 0Z" fill="url(#clayG)"/>'
            f'<path d="M-0.92 0.16 C-0.4 0.34 0.45 0.34 0.94 0.12" stroke="#f5c542" stroke-width="0.08" fill="none"/>'
            f'<ellipse cx="-0.04" cy="0" rx="0.96" ry="0.13" fill="#3a1608"/><ellipse cx="-0.04" cy="0.02" rx="0.8" ry="0.08" fill="#c9861f"/>'
            f'</g>'
            f'<g transform="translate({f(x + s * 1.18)} {f(fy)})"><path d="M0 0 C{f(-s*0.44)} {f(-s*0.29)} {f(-s*0.15)} {f(-s*0.8)} 0 {f(-s*1.15)} C{f(s*0.15)} {f(-s*0.8)} {f(s*0.44)} {f(-s*0.29)} 0 0Z" fill="url(#flameG)"/></g>')


def mandala_royal(rng):
    a = []
    P = dict(red='#b3122e', blue='#173f9e', mag='#c2187a', gold='#f2b705', orange='#ef6c00', purple='#5e2a8c', green='#0f7a4b')
    o = [floor('#24232a')]
    g = []
    g.append(circle(505, P['blue'], WHITE, 4))
    g.append(scallop_ring(48, 505, 9, P['blue']))
    g.append(ring_dots(96, 532, 4.5))
    g.append(ring_petals(24, 395, 500, 34, P['mag'], rot=TAU / 48))
    g.append(ring_petals(24, 410, 485, 16, P['gold'], ow=0, rot=TAU / 48))
    g.append(ring_petals(24, 395, 470, 30, P['red']))
    g.append(ring_petals(24, 408, 455, 13, P['orange'], ow=0))
    g.append(circle(395, P['purple'], WHITE, 4))
    for i in range(16):
        ang = i * TAU / 16
        x, y = pol(CX, CY, 350, ang)
        g.append(paisley_at(x, y, 34, math.degrees(ang) + 90, P['gold'], P['red']))
    g.append(ring_dots(64, 385, 3.6, P['gold']))
    g.append(circle(305, P['green'], WHITE, 4))
    g.append(star_poly(16, 300, 230, P['red']))
    g.append(star_poly(16, 270, 225, P['gold'], sw=0))
    g.append(circle(225, P['blue'], WHITE, 4))
    g.append(ring_petals(16, 120, 222, 40, P['mag']))
    g.append(ring_petals(16, 132, 205, 18, '#ff9ecb', ow=0))
    g.append(ring_petals(16, 120, 200, 32, P['orange'], rot=TAU / 32))
    g.append(ring_dots(48, 228, 4))
    g.append(circle(120, P['gold'], WHITE, 4))
    g.append(ring_petals(12, 40, 118, 26, P['red']))
    g.append(ring_petals(12, 50, 104, 11, P['orange'], ow=0))
    g.append(circle(42, P['blue'], WHITE, 4))
    g.append(ring_petals(8, 8, 40, 11, P['gold'], ow=1.5))
    g.append(circle(9, WHITE, 'none', 0))
    o.append(f'<g filter="url(#powder)">{"".join(g)}</g>')
    # corner ornaments and diyas
    for cx, cy in ((120, 120), (1480, 120), (120, 1080), (1480, 1080)):
        o.append(f'<g filter="url(#powder)">{ring_petals(8, 18, 82, 22, P["mag"], cx=cx, cy=cy)}{ring_petals(8, 18, 70, 10, P["gold"], ow=0, cx=cx, cy=cy)}{circle(22, P["gold"], WHITE, 3, cx, cy)}{ring_dots(16, 98, 4, cx=cx, cy=cy)}</g>')
    for i in range(8):
        x, y = pol(CX, CY, 575, i * TAU / 8 + TAU / 16)
        o.append(clay_diya(x - 20, y + 10, 26, a))
    a += [('sparkle_ring', CX, CY, 520, 70)]
    return ''.join(o), a


def lotus_rangoli(rng):
    a = []
    P = dict(pink='#e0457b', deep='#9c1452', light='#ffb3cf', green='#1c7a45', gold='#f2b705', blue='#1b3f8f', white=WHITE, orange='#ef6c00')
    o = [floor('#2a2520')]
    g = []
    # octagon frame with lattice
    oct_pts = ' '.join(f'{f(pol(CX, CY, 530, i * TAU / 8 + TAU / 16)[0])},{f(pol(CX, CY, 530, i * TAU / 8 + TAU / 16)[1])}' for i in range(8))
    g.append(f'<polygon points="{oct_pts}" fill="{P["blue"]}" stroke="{WHITE}" stroke-width="5"/>')
    oct2 = ' '.join(f'{f(pol(CX, CY, 488, i * TAU / 8 + TAU / 16)[0])},{f(pol(CX, CY, 488, i * TAU / 8 + TAU / 16)[1])}' for i in range(8))
    g.append(f'<polygon points="{oct2}" fill="#0f2a63" stroke="{P["gold"]}" stroke-width="4"/>')
    for i in range(8):  # small lotus buds at octagon corners
        x, y = pol(CX, CY, 455, i * TAU / 8 + TAU / 16)
        g.append(ring_petals(6, 6, 40, 16, P['pink'], cx=x, cy=y, ow=2))
        g.append(circle(9, P['gold'], WHITE, 2, x, y))
    for i in range(8):  # leaves between
        ang = i * TAU / 8
        g.append(f'<path d="{path_petal(300, 450, 34, ang)}" fill="{P["green"]}" stroke="{WHITE}" stroke-width="3"/>')
        g.append(f'<path d="{path_petal(312, 440, 4, ang)}" fill="#7bd38f"/>')
    g.append(circle(300, '#3d0a22', WHITE, 4))
    g.append(ring_dots(72, 288, 3.5, P['gold']))
    # layered lotus (back to front)
    for layer, (n, r0, r1, w, col, rot) in enumerate([
        (16, 70, 280, 58, P['deep'], TAU / 32), (16, 70, 255, 52, P['pink'], 0), (8, 60, 215, 60, P['light'], TAU / 16), (8, 50, 175, 46, P['pink'], 0)]):
        g.append(ring_petals(n, r0, r1, w, col, rot=rot, bulge=0.55))
        g.append(''.join(f'<path d="M{f(pol(CX, CY, r0 + 20, rot + i * TAU / n)[0])} {f(pol(CX, CY, r0 + 20, rot + i * TAU / n)[1])} L{f(pol(CX, CY, r1 - 22, rot + i * TAU / n)[0])} {f(pol(CX, CY, r1 - 22, rot + i * TAU / n)[1])}" stroke="{WHITE}" stroke-width="2" opacity="0.7"/>' for i in range(n)))
    g.append(circle(70, P['gold'], WHITE, 4))
    g.append(ring_dots(18, 50, 6, P['orange']))
    g.append(circle(28, P['orange'], WHITE, 3))
    o.append(f'<g filter="url(#powder)">{"".join(g)}</g>')
    for i in range(4):
        x, y = pol(CX, CY, 600, i * TAU / 4 + TAU / 8)
        o.append(clay_diya(x - 20, y + 8, 28, a))
    for x in (110, 1490):
        for y in (300, 900):
            o.append(f'<g filter="url(#powder)">{ring_petals(8, 10, 64, 22, P["pink"], cx=x, cy=y)}{circle(14, P["gold"], WHITE, 2, x, y)}</g>')
    a += [('sparkle_ring', CX, CY, 520, 60), ('petals', CX, CY - 60, 160, ['#f7a8c0', '#e0457b', '#ffd1e0'])]
    return ''.join(o), a


def peacock_motif(x, y, s, ang, P):
    """Stylised rangoli peacock (body + crest + fanned tail) facing outward along `ang`."""
    t = f'translate({f(x)} {f(y)}) rotate({math.degrees(ang) + 90:.1f}) scale({f(s)})'
    tail = []
    for i in range(9):
        aa = math.radians(-150 + i * 15)
        ex, ey = math.cos(aa) * 1.25, math.sin(aa) * 1.25 + 0.55
        tail.append(f'<path d="M0 0.6 Q{f(ex * 0.5)} {f(ey * 0.6)} {f(ex)} {f(ey)}" stroke="{P["green"]}" stroke-width="0.07" fill="none"/>')
        tail.append(f'<g transform="translate({f(ex)} {f(ey)}) rotate({math.degrees(aa) + 90:.0f})"><ellipse rx="0.17" ry="0.24" fill="{P["green"]}" stroke="{WHITE}" stroke-width="0.03"/><ellipse rx="0.11" ry="0.16" fill="{P["gold"]}"/><ellipse rx="0.065" ry="0.1" fill="{P["blue"]}"/></g>')
    body = (f'<path d="M-0.18 0.65 C-0.3 0.2 -0.1 -0.1 0.02 -0.35 C0.05 -0.6 0.0 -0.78 0.12 -0.88 C0.26 -0.95 0.36 -0.85 0.3 -0.72 L0.42 -0.68 L0.3 -0.64 C0.22 -0.45 0.3 -0.2 0.3 0.1 C0.32 0.45 0.15 0.68 -0.18 0.65Z" fill="{P["blue"]}" stroke="{WHITE}" stroke-width="0.035"/>'
            f'<circle cx="0.2" cy="-0.8" r="0.03" fill="{WHITE}"/>'
            + ''.join(f'<path d="M{0.12 + k * 0.05} -0.9 L{0.06 + k * 0.08} -1.06" stroke="{P["blue"]}" stroke-width="0.02"/><circle cx="{0.06 + k * 0.08}" cy="-1.08" r="0.028" fill="{P["gold"]}"/>' for k in range(3)))
    return f'<g transform="{t}">{"".join(tail)}{body}</g>'


def peacock_rangoli(rng):
    a = []
    P = dict(blue='#123f9c', teal='#0f8a83', green='#1a8a4a', gold='#f2b705', mag='#b0176f', purple='#4b2382', red='#b3122e')
    o = [floor('#1f2328')]
    g = [circle(520, P['purple'], WHITE, 4), scallop_ring(40, 520, 10, P['purple']), ring_dots(80, 548, 4.5, P['gold'])]
    g.append(circle(470, '#1a1440', P['gold'], 4))
    for i in range(6):
        ang = i * TAU / 6 - math.pi / 2
        x, y = pol(CX, CY, 300, ang)
        g.append(peacock_motif(x, y, 120, ang, P))
    for i in range(6):
        ang = i * TAU / 6 - math.pi / 2 + TAU / 12
        x, y = pol(CX, CY, 380, ang)
        g.append(paisley_at(x, y, 40, math.degrees(ang) + 90, P['mag'], P['gold']))
    g.append(circle(165, P['teal'], WHITE, 4))
    g.append(ring_petals(12, 60, 160, 34, P['blue']))
    g.append(ring_petals(12, 70, 145, 14, P['gold'], ow=0))
    g.append(circle(62, P['mag'], WHITE, 4))
    g.append(star_poly(8, 58, 30, P['gold'], sw=2))
    g.append(circle(16, WHITE, 'none', 0))
    o.append(f'<g filter="url(#powder)">{"".join(g)}</g>')
    for i in range(6):
        x, y = pol(CX, CY, 600, i * TAU / 6 + TAU / 12)
        o.append(clay_diya(x - 18, y + 8, 24, a))
    a += [('sparkle_ring', CX, CY, 500, 70)]
    return ''.join(o), a


def diya_rangoli(rng):
    a = []
    P = dict(red='#a5122a', orange='#ef6c00', gold='#f2b705', mag='#c2187a', blue='#173f9e', green='#0f7a4b', purple='#5e2a8c')
    o = [floor('#2c2622')]
    g = [circle(510, P['red'], WHITE, 4), scallop_ring(36, 510, 11, P['red']), ring_dots(72, 540, 4.5, P['gold'])]
    for i in range(8):  # 8 rangoli diyas around (powder lamps with flames)
        ang = i * TAU / 8
        x, y = pol(CX, CY, 395, ang)
        rot = math.degrees(ang) + 90
        g.append(f'<g transform="translate({f(x)} {f(y)}) rotate({rot:.1f}) scale(70)">'
                 f'<path d="M-1 0 C-0.9 0.6 0.9 0.6 1 0 Q0 0.18 -1 0Z" fill="{P["orange"]}" stroke="{WHITE}" stroke-width="0.04"/>'
                 f'<path d="M-0.7 0.2 Q0 0.36 0.7 0.2" stroke="{P["gold"]}" stroke-width="0.07" fill="none"/>'
                 f'<path d="M0 -0.05 C-0.3 -0.35 -0.15 -0.7 0 -0.95 C0.15 -0.7 0.3 -0.35 0 -0.05Z" fill="{P["gold"]}" stroke="{WHITE}" stroke-width="0.03"/>'
                 f'<path d="M0 -0.15 C-0.12 -0.35 -0.06 -0.55 0 -0.68 C0.06 -0.55 0.12 -0.35 0 -0.15Z" fill="#fff4c2"/></g>')
        fx, fy = pol(CX, CY, 395 - 50, ang)
        a.append(('glow', fx, fy, 30))
    g.append(circle(300, P['blue'], WHITE, 4))
    g.append(star_poly(8, 295, 200, P['mag']))
    g.append(star_poly(8, 255, 190, P['purple'], sw=0, rot=-math.pi / 2 + math.pi / 8))
    g.append(circle(190, P['green'], WHITE, 4))
    g.append(ring_petals(16, 90, 186, 30, P['gold']))
    g.append(ring_petals(16, 100, 170, 12, P['orange'], ow=0))
    g.append(circle(92, P['red'], WHITE, 4))
    # central large powder diya
    g.append(f'<g transform="translate({CX} {CY + 20}) scale(70)">'
             f'<path d="M-1 0 C-0.9 0.6 0.9 0.6 1 0 Q0 0.18 -1 0Z" fill="{P["gold"]}" stroke="{WHITE}" stroke-width="0.04"/>'
             f'<path d="M0 -0.05 C-0.3 -0.35 -0.15 -0.75 0 -1.0 C0.15 -0.75 0.3 -0.35 0 -0.05Z" fill="{P["orange"]}" stroke="{WHITE}" stroke-width="0.03"/>'
             f'<path d="M0 -0.18 C-0.12 -0.38 -0.06 -0.6 0 -0.72 C0.06 -0.6 0.12 -0.38 0 -0.18Z" fill="#fff4c2"/></g>')
    o.append(f'<g filter="url(#powder)">{"".join(g)}</g>')
    a.append(('glow', CX, CY - 15, 45))
    for i in range(12):
        x, y = pol(CX, CY, 610, i * TAU / 12)
        if 80 < y < 1130:
            o.append(clay_diya(x - 16, y + 6, 20, a))
    a += [('sparkle_ring', CX, CY, 500, 60)]
    return ''.join(o), a


def geometric_rangoli(rng):
    a = []
    P = dict(red='#b3122e', blue='#173f9e', gold='#f2b705', mag='#c2187a', green='#0f7a4b', white=WHITE, orange='#ef6c00', purple='#5e2a8c')
    o = [floor('#26252b')]
    g = []
    # square-in-square interlace (classic 8-point star geometry) with petal infills
    for k, (r, col) in enumerate([(520, P['blue']), (470, P['red']), (410, P['purple']), (350, P['green'])]):
        for rot in (0, math.pi / 4):
            pts = ' '.join(f'{f(pol(CX, CY, r, rot + i * math.pi / 2 + math.pi / 4)[0])},{f(pol(CX, CY, r, rot + i * math.pi / 2 + math.pi / 4)[1])}' for i in range(4))
            g.append(f'<polygon points="{pts}" fill="{col}" stroke="{WHITE}" stroke-width="4" opacity="0.96"/>')
    for i in range(8):
        ang = i * TAU / 8
        g.append(f'<path d="{path_petal(270, 420, 30, ang)}" fill="{P["gold"]}" stroke="{WHITE}" stroke-width="3"/>')
        g.append(f'<path d="{path_petal(290, 400, 12, ang)}" fill="{P["orange"]}"/>')
        x, y = pol(CX, CY, 440, ang + TAU / 16)
        g.append(ring_petals(6, 6, 34, 12, P['mag'], cx=x, cy=y, ow=2))
    g.append(circle(270, '#13183a', WHITE, 4))
    g.append(ring_dots(56, 255, 4, P['gold']))
    g.append(star_poly(12, 238, 170, P['red']))
    g.append(star_poly(12, 200, 160, P['mag'], sw=0, rot=-math.pi / 2 + math.pi / 12))
    g.append(circle(160, P['blue'], WHITE, 4))
    for i in range(12):  # lattice of crossing arcs (kolam feel)
        ang = i * TAU / 12
        x, y = pol(CX, CY, 110, ang)
        g.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="56" fill="none" stroke="{P["gold"]}" stroke-width="3"/>')
    g.append(ring_petals(12, 20, 92, 18, P['orange'], ow=2))
    g.append(circle(24, P['gold'], WHITE, 3))
    o.append(f'<g filter="url(#powder)">{"".join(g)}</g>')
    for x, y in ((140, 140), (1460, 140), (140, 1060), (1460, 1060)):
        o.append(clay_diya(x - 18, y + 8, 26, a))
    a += [('sparkle_ring', CX, CY, 520, 70)]
    return ''.join(o), a


# =========================================================================================
# FLOWER-PETAL RANGOLIS (photographic style)
# =========================================================================================
FLOWER_DEFS = '''<defs>
<filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="2.5" dy="4" stdDeviation="2.6" flood-color="#000" flood-opacity="0.45"/></filter>
<filter id="shadowSm" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="1.2" dy="2" stdDeviation="1.2" flood-color="#000" flood-opacity="0.4"/></filter>
<filter id="marble" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.004 0.012" numOctaves="6" seed="21" result="t"/>
  <feColorMatrix in="t" values="0 0 0 0 0.35  0 0 0 0 0.33  0 0 0 0 0.32  0 0 0 1.1 -0.35"/>
  <feComposite in2="SourceGraphic" operator="in"/>
</filter>
<radialGradient id="vign2" cx="50%" cy="48%" r="72%"><stop offset="0.5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.6"/></radialGradient>
<radialGradient id="roseG" cx="50%" cy="65%" r="70%"><stop offset="0" stop-color="#ff5a6e"/><stop offset="0.6" stop-color="#c8102e"/><stop offset="1" stop-color="#6e0717"/></radialGradient>
<radialGradient id="roseP" cx="50%" cy="65%" r="70%"><stop offset="0" stop-color="#ffd0dc"/><stop offset="0.6" stop-color="#f27a9a"/><stop offset="1" stop-color="#b8325a"/></radialGradient>
<radialGradient id="marO" cx="50%" cy="80%" r="80%"><stop offset="0" stop-color="#ffb347"/><stop offset="0.7" stop-color="#f07b0f"/><stop offset="1" stop-color="#b44a05"/></radialGradient>
<radialGradient id="marY" cx="50%" cy="80%" r="80%"><stop offset="0" stop-color="#fff07a"/><stop offset="0.7" stop-color="#ffc21a"/><stop offset="1" stop-color="#c98a04"/></radialGradient>
<radialGradient id="jas" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="#ffffff"/><stop offset="0.7" stop-color="#f4f1e6"/><stop offset="1" stop-color="#cfc8b4"/></radialGradient>
<radialGradient id="lotusP" cx="50%" cy="85%" r="90%"><stop offset="0" stop-color="#fff6f8"/><stop offset="0.55" stop-color="#f6a3bf"/><stop offset="1" stop-color="#c93d74"/></radialGradient>
<radialGradient id="purpleP" cx="50%" cy="70%" r="75%"><stop offset="0" stop-color="#e0b8ff"/><stop offset="0.6" stop-color="#8e44c9"/><stop offset="1" stop-color="#4a1b78"/></radialGradient>
<radialGradient id="ball" cx="38%" cy="32%" r="70%"><stop offset="0" stop-color="#fff" stop-opacity="0.35"/><stop offset="0.5" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.3"/></radialGradient>
<linearGradient id="leafG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2e7d32"/><stop offset="0.5" stop-color="#4caf50"/><stop offset="1" stop-color="#1b5e20"/></linearGradient>
<radialGradient id="glowG" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffd27a" stop-opacity="0.75"/><stop offset="0.4" stop-color="#ffab3d" stop-opacity="0.25"/><stop offset="1" stop-color="#ff7a00" stop-opacity="0"/></radialGradient>
<radialGradient id="flameG" cx="50%" cy="70%" r="60%"><stop offset="0" stop-color="#fffef2"/><stop offset="0.4" stop-color="#ffe27a"/><stop offset="0.8" stop-color="#ffa21f"/><stop offset="1" stop-color="#ff6a00"/></radialGradient>
<linearGradient id="clayG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c8643a"/><stop offset="0.6" stop-color="#9a3f1f"/><stop offset="1" stop-color="#5e2210"/></linearGradient>
</defs>'''


def stone_floor(base='#d9d2c5', tiles=True):
    o = [f'<rect width="{W}" height="{H}" fill="{base}"/>', f'<rect width="{W}" height="{H}" fill="#fff" filter="url(#marble)" opacity="0.9"/>']
    if tiles:
        for x in range(0, W + 1, 400):
            o.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#8d8577" stroke-width="2" opacity="0.5"/>')
        for y in range(0, H + 1, 400):
            o.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#8d8577" stroke-width="2" opacity="0.5"/>')
    o.append(f'<rect width="{W}" height="{H}" fill="url(#vign2)"/>')
    return ''.join(o)


def rose_petal(x, y, s, ang, grad='roseG'):
    return (f'<path transform="translate({f(x)} {f(y)}) rotate({ang:.0f}) scale({f(s)})" '
            f'd="M0 1 C-0.9 0.6 -1.05 -0.35 -0.45 -0.9 C-0.2 -1.05 0 -0.8 0 -0.8 C0 -0.8 0.2 -1.05 0.45 -0.9 C1.05 -0.35 0.9 0.6 0 1Z" fill="url(#{grad})"/>')


def jasmine(x, y, s, ang):
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({ang:.0f}) scale({f(s)})">'
            + ''.join(f'<ellipse cx="0" cy="-0.55" rx="0.32" ry="0.55" fill="url(#jas)" transform="rotate({k * 72})"/>' for k in range(5))
            + '<circle r="0.18" fill="#f2d25a"/></g>')


def jasmine_bud(x, y, s, ang):
    return f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(s * 0.32)}" ry="{f(s)}" fill="url(#jas)" transform="rotate({ang:.0f} {f(x)} {f(y)})"/>'


def marigold_head(x, y, r, rng, grad='marO'):
    """Ruffled marigold (genda) head: dense layered petals, darker core, spherical highlight."""
    dark = '#a8420a' if grad == 'marO' else '#b77d05'
    o = [f'<g filter="url(#shadowSm)"><circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 1.02)}" fill="{dark}"/>']
    for k in range(6):
        rr = r * (1 - k * 0.15)
        n = 12 + int(26 * rr / r)
        for i in range(n):
            a = (i + rng.random() * 0.8) / n * TAU + k * 0.5
            px, py = pol(x, y, rr * 0.62, a)
            sz = rng.uniform(0.8, 1.2)
            o.append(f'<ellipse cx="{f(px)}" cy="{f(py)}" rx="{f(rr * 0.2 * sz)}" ry="{f(rr * 0.4 * sz)}" fill="url(#{grad})" '
                     f'transform="rotate({math.degrees(a) + 90 + rng.uniform(-25, 25):.0f} {f(px)} {f(py)})" opacity="{rng.uniform(0.85, 1):.2f}"/>')
    o.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="url(#ball)"/>')
    o.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 0.13)}" fill="#6b3002"/></g>')
    return ''.join(o)


def leaf(x, y, l, ang):
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({ang:.0f})" filter="url(#shadowSm)"><path d="M0 0 C{f(l*0.3)} {f(-l*0.24)} {f(l*0.75)} {f(-l*0.2)} {f(l)} 0 C{f(l*0.75)} {f(l*0.2)} {f(l*0.3)} {f(l*0.24)} 0 0Z" fill="url(#leafG)"/>'
            f'<path d="M0 0 L{f(l*0.95)} 0" stroke="#a5d6a7" stroke-width="{f(max(1, l * 0.03))}"/></g>')


def fill_ring(r0, r1, density, draw, rng, a0=0.0, a1=TAU, cx=CX, cy=CY):
    """Scatter flower items to densely fill an annular sector."""
    out = []
    area = 0.5 * (a1 - a0) * (r1 * r1 - r0 * r0)
    n = int(area * density / 1000 * DENSITY)
    for _ in range(n):
        r = math.sqrt(rng.uniform(r0 * r0, r1 * r1))
        a = rng.uniform(a0, a1)
        x, y = pol(cx, cy, r, a)
        out.append(draw(x, y, a))
    return ''.join(out)


def flower_marigold(rng):
    a = []
    o = [stone_floor('#d8cfbf')]
    g = []
    g.append(fill_ring(470, 540, 0.55, lambda x, y, an: marigold_head(x, y, rng.uniform(19, 23), rng, 'marO' if rng.random() < 0.6 else 'marY'), rng))
    g.append(fill_ring(430, 468, 4.5, lambda x, y, an: rose_petal(x, y, rng.uniform(9, 12), math.degrees(an) + rng.uniform(-60, 60)), rng))
    for i in range(16):  # alternating sectors: rose / jasmine / yellow marigold petals
        a0, a1 = i * TAU / 16, (i + 1) * TAU / 16
        if i % 2 == 0:
            g.append(fill_ring(250, 428, 3.2, lambda x, y, an: rose_petal(x, y, rng.uniform(10, 13), rng.uniform(0, 360)), rng, a0, a1))
        else:
            g.append(fill_ring(250, 428, 2.8, lambda x, y, an: f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rng.uniform(5,7))}" ry="{f(rng.uniform(9,12))}" fill="url(#marY)" transform="rotate({rng.uniform(0,360):.0f} {f(x)} {f(y)})"/>', rng, a0, a1))
    for i in range(16):  # jasmine dividers
        ang = i * TAU / 16
        for r in range(255, 430, 16):
            x, y = pol(CX, CY, r, ang)
            g.append(jasmine_bud(x, y, 8, math.degrees(ang) + 90))
    g.append(fill_ring(200, 248, 1.0, lambda x, y, an: marigold_head(x, y, rng.uniform(15, 18), rng, 'marY'), rng))
    g.append(fill_ring(110, 198, 3.0, lambda x, y, an: rose_petal(x, y, rng.uniform(9, 12), rng.uniform(0, 360), 'roseP'), rng))
    for i in range(8):
        g.append(leaf(*pol(CX, CY, 110, i * TAU / 8 + TAU / 16), 80, math.degrees(i * TAU / 8 + TAU / 16)))
    g.append(fill_ring(0, 105, 0.9, lambda x, y, an: jasmine(x, y, rng.uniform(13, 16), rng.uniform(0, 72)), rng))
    o.append(f'<g filter="url(#shadow)">{"".join(g)}</g>')
    for i in range(8):
        x, y = pol(CX, CY, 590, i * TAU / 8 + TAU / 16)
        o.append(petal_diya(x - 18, y + 6, 24, a))
    a += [('sparkle_ring', CX, CY, 520, 40), ('petals', CX, CY, 420, ['#f07b0f', '#ffc21a', '#c8102e'])]
    return ''.join(o), a


def flower_rose_lotus(rng):
    a = []
    o = [stone_floor('#cfc6b6')]
    g = []
    g.append(fill_ring(500, 545, 0.9, lambda x, y, an: leaf(x, y, rng.uniform(46, 58), math.degrees(an) + rng.uniform(-30, 30)), rng))
    g.append(fill_ring(440, 498, 0.55, lambda x, y, an: marigold_head(x, y, rng.uniform(17, 20), rng, 'marY'), rng))
    g.append(fill_ring(330, 438, 3.6, lambda x, y, an: rose_petal(x, y, rng.uniform(10, 13), rng.uniform(0, 360)), rng))
    # lotus made of real lotus petals (layers), white jasmine outlining each petal
    for n, r0, r1, w, rot in ((12, 60, 330, 62, 0.0), (12, 60, 280, 56, TAU / 24), (8, 50, 210, 52, 0.0)):
        for i in range(n):
            ang = rot + i * TAU / n
            g.append(f'<path d="{path_petal(r0, r1, w, ang, bulge=0.55)}" fill="url(#lotusP)" filter="url(#shadowSm)"/>')
            for t in range(10):
                tt = t / 9
                for side in (-1, 1):
                    rr = r0 + 30 + (r1 - r0 - 50) * tt
                    ww = w * math.sin(math.pi * min(1, tt * 1.1)) * 0.82 * side
                    x, y = pol(CX, CY, rr, ang)
                    x += -math.sin(ang) * ww; y += math.cos(ang) * ww
                    g.append(jasmine_bud(x, y, 6, math.degrees(ang)))
    g.append(fill_ring(0, 58, 1.2, lambda x, y, an: marigold_head(x, y, rng.uniform(14, 17), rng, 'marO'), rng))
    o.append(f'<g filter="url(#shadow)">{"".join(g)}</g>')
    for x, y in ((150, 150), (1450, 150), (150, 1050), (1450, 1050)):
        o.append(petal_diya(x - 18, y + 6, 26, a))
    a += [('sparkle_ring', CX, CY, 500, 40), ('petals', CX, CY, 380, ['#c8102e', '#f6a3bf', '#ffffff'])]
    return ''.join(o), a


def flower_mixed(rng):
    a = []
    o = [stone_floor('#d4ccbe')]
    g = []
    grads = ['roseG', 'purpleP', 'marY', 'roseP', 'marO', 'jas']
    g.append(fill_ring(500, 545, 0.55, lambda x, y, an: marigold_head(x, y, rng.uniform(17, 20), rng, 'marO'), rng))
    for i in range(12):
        a0, a1 = i * TAU / 12, (i + 1) * TAU / 12
        gr = grads[i % len(grads)]
        g.append(fill_ring(300, 495, 2.8, lambda x, y, an, gr=gr: rose_petal(x, y, rng.uniform(10, 13), rng.uniform(0, 360), gr) if gr in ('roseG', 'roseP', 'purpleP') else f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rng.uniform(5,7))}" ry="{f(rng.uniform(9,12))}" fill="url(#{gr})" transform="rotate({rng.uniform(0,360):.0f} {f(x)} {f(y)})"/>', rng, a0, a1))
        for r in range(305, 495, 15):  # leaf-green divider lines
            x, y = pol(CX, CY, r, a0)
            g.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="4" ry="9" fill="url(#leafG)" transform="rotate({math.degrees(a0) + 90:.0f} {f(x)} {f(y)})"/>')
    g.append(fill_ring(250, 298, 0.5, lambda x, y, an: marigold_head(x, y, rng.uniform(15, 17), rng, 'marY'), rng))
    g.append(fill_ring(120, 248, 3.0, lambda x, y, an: rose_petal(x, y, rng.uniform(9, 12), rng.uniform(0, 360), 'purpleP'), rng))
    for i in range(12):
        g.append(jasmine(*pol(CX, CY, 185, i * TAU / 12), 18, rng.uniform(0, 72)))
    g.append(fill_ring(0, 118, 2.6, lambda x, y, an: rose_petal(x, y, rng.uniform(10, 13), rng.uniform(0, 360)), rng))
    g.append(marigold_head(CX, CY, 40, rng, 'marO'))
    o.append(f'<g filter="url(#shadow)">{"".join(g)}</g>')
    for i in range(12):
        x, y = pol(CX, CY, 600, i * TAU / 12)
        if 80 < y < 1130:
            o.append(petal_diya(x - 16, y + 6, 20, a))
    a += [('sparkle_ring', CX, CY, 520, 40), ('petals', CX, CY, 420, ['#c8102e', '#8e44c9', '#ffc21a', '#ffffff'])]
    return ''.join(o), a


def flower_jasmine_marigold(rng):
    """Concentric jasmine & marigold rangoli with a lotus centre and diya ring."""
    a = []
    o = [stone_floor('#3a332d', tiles=False)]  # dark slate floor, evening
    g = []
    g.append(fill_ring(505, 540, 1.6, lambda x, y, an: jasmine(x, y, rng.uniform(11, 14), rng.uniform(0, 72)), rng))
    for i in range(24):
        ang = i * TAU / 24
        g.append(marigold_head(*pol(CX, CY, 470, ang), 26, rng, 'marO' if i % 2 else 'marY'))
    g.append(fill_ring(330, 440, 3.4, lambda x, y, an: rose_petal(x, y, rng.uniform(10, 13), rng.uniform(0, 360)), rng))
    for i in range(12):
        ang = i * TAU / 12
        g.append(f'<path d="{path_petal(180, 330, 50, ang)}" fill="#f6eedc" filter="url(#shadowSm)"/>')
        g.append(fill_ring(190, 320, 1.4, lambda x, y, an: jasmine_bud(x, y, 7, rng.uniform(0, 180)), rng, ang - 0.12, ang + 0.12))
    g.append(fill_ring(110, 180, 1.3, lambda x, y, an: marigold_head(x, y, rng.uniform(15, 18), rng, 'marO'), rng))
    for n, r1, w in ((10, 108, 34), (6, 80, 30)):
        for i in range(n):
            g.append(f'<path d="{path_petal(10, r1, w, i * TAU / n)}" fill="url(#lotusP)" filter="url(#shadowSm)"/>')
    g.append(f'<circle cx="{CX}" cy="{CY}" r="16" fill="#ffc21a"/>')
    o.append(f'<g filter="url(#shadow)">{"".join(g)}</g>')
    for i in range(10):
        x, y = pol(CX, CY, 600, i * TAU / 10 + TAU / 20)
        if 80 < y < 1130:
            o.append(petal_diya(x - 18, y + 6, 24, a))
    a += [('sparkle_ring', CX, CY, 500, 45), ('petals', CX, CY, 420, ['#f07b0f', '#ffc21a', '#ffffff'])]
    return ''.join(o), a


def petal_diya(x, y, s, anchors):
    fy = y - s * 0.1
    anchors.append(('flame', x + s * 1.18, fy - s * 0.52, s * 1.15))
    return (f'<circle cx="{f(x + s * 0.9)}" cy="{f(fy - s * 0.4)}" r="{f(s * 3.4)}" fill="url(#glowG)"/>'
            f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})" filter="url(#shadowSm)">'
            f'<path d="M-1 0 C-0.95 0.55 -0.45 0.78 0 0.78 C0.5 0.78 0.85 0.5 1.0 0.12 L1.32 -0.12 C1.05 -0.08 0.95 -0.04 0.92 -0.04 C0.4 0.12 -0.4 0.12 -1 0Z" fill="url(#clayG)"/>'
            f'<ellipse cx="-0.04" cy="0" rx="0.96" ry="0.13" fill="#3a1608"/><ellipse cx="-0.04" cy="0.02" rx="0.8" ry="0.08" fill="#c9861f"/></g>'
            f'<g transform="translate({f(x + s * 1.18)} {f(fy)})"><path d="M0 0 C{f(-s*0.44)} {f(-s*0.29)} {f(-s*0.15)} {f(-s*0.8)} 0 {f(-s*1.15)} C{f(s*0.15)} {f(-s*0.8)} {f(s*0.44)} {f(-s*0.29)} 0 0Z" fill="url(#flameG)"/></g>')


# id, category, title, description, medium, fn, family
RANGOLIS = [
    ('rangoli-mandala', 'rangoli', 'Royal Mandala Rangoli', 'A sixteen-fold mandala in ruby, royal blue and gold powder.', 'Coloured rangoli powder', mandala_royal, 'powder'),
    ('rangoli-lotus', 'rangoli', 'Lotus Blossom Rangoli', 'A layered lotus within a jewelled octagon.', 'Coloured rangoli powder', lotus_rangoli, 'powder'),
    ('rangoli-peacock', 'rangoli', 'Mayur Peacock Rangoli', 'Six peacocks fan their tails around a lotus medallion.', 'Coloured rangoli powder', peacock_rangoli, 'powder'),
    ('rangoli-diya', 'rangoli', 'Deepam Rangoli', 'Eight powder diyas circle a glowing central lamp.', 'Coloured rangoli powder', diya_rangoli, 'powder'),
    ('rangoli-geometric', 'rangoli', 'Ashtakona Geometric Rangoli', 'Interlaced eight-point star geometry with kolam arcs.', 'Coloured rangoli powder', geometric_rangoli, 'powder'),
    ('flower-marigold', 'flower-rangoli', 'Marigold & Rose Mandala', 'Marigold heads, rose petals and jasmine buds on marble.', 'Fresh flower petals', flower_marigold, 'flower'),
    ('flower-lotus', 'flower-rangoli', 'Rose Lotus with Jasmine', 'A lotus of real lotus petals outlined in jasmine on a bed of roses.', 'Fresh flower petals', flower_rose_lotus, 'flower'),
    ('flower-mixed', 'flower-rangoli', 'Festival Petal Medallion', 'Twelve colour sectors of mixed petals with a marigold heart.', 'Fresh flower petals', flower_mixed, 'flower'),
    ('flower-jasmine', 'flower-rangoli', 'Jasmine Moon Rangoli', 'Jasmine and marigold rings around a lotus, lit by diyas.', 'Fresh flower petals', flower_jasmine_marigold, 'flower'),
]
