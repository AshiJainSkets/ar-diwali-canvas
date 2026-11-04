"""30 original Diwali compositions across 10 categories (procedural SVG).

Each entry: (id, category, title, description, medium, fn(rng) -> svg body)
"""
import math
from motifs import *  # noqa

CATEGORIES = [
    ('skets', 'Skets Studio', 'Our studio, our people, our Diwali.'),
    ('traditional', 'Traditional Diwali Celebration', 'Homes, lamps and fireworks on the night of Amavasya.'),
    ('rangoli', 'Diwali Rangoli Art', 'Radiant floor art of petals, powders and dots.'),
    ('lakshmi', 'Goddess Lakshmi Inspired', 'Lotus, gold and footsteps of prosperity.'),
    ('ganesha', 'Lord Ganesha Artwork', 'Vighnaharta, remover of obstacles, in line and light.'),
    ('diya', 'Diya & Floral Decorations', 'Clay lamps, marigolds and flowing petals.'),
    ('heritage', 'Indian Heritage Diwali', 'Ghats, temples and forts aglow.'),
    ('rajasthani', 'Royal Rajasthani Diwali', 'Palaces, jharokhas and caparisoned elephants.'),
    ('abstract', 'Modern Abstract Diwali', 'Contemporary colour fields and geometry of flame.'),
    ('folk', 'Traditional Indian Folk Art', 'Warli, Madhubani and Gond interpretations.'),
    ('gold', 'Luxury Gold Diwali', 'Gilded mandalas, emerald and gold leaf.'),
]
PAL_FESTIVE = ['#e63946', '#f4a261', '#ffd166', '#2a9d8f', '#7b2cbf', '#ef476f']


def warm_ground(y, color='#2b1206'):
    return f'<rect x="0" y="{y}" width="{W}" height="{H-y}" fill="{color}"/>'


# ---------------------------------------------------------------- traditional
def traditional_1(r):
    o = [lin_bg([(0, '#0b0a2e'), (0.55, '#3b1250'), (1, '#7a2d3a')])]
    o.append(stars(r, 160, 650))
    o.append(firework(330, 260, 190, '#ffcf5a', r))
    o.append(firework(1180, 200, 160, '#ff6fa8', r))
    o.append(firework(820, 420, 120, '#7ff0ff', r, n=28))
    o.append(glow(800, 1000, 900, 0.35, 'glowSoft'))
    o.append(haveli(150, 1020, 1300, 420, r))
    for x in (110, 1490):
        o.append(lantern(x, 360, 46, '#e23d3d', '#ffc23d'))
    o.append(warm_ground(1020, '#3a1608'))
    o.append(f'<g transform="translate(800 1110) scale(1 0.32)">{rangoli(0, 0, 230, r, PAL_FESTIVE)}</g>')
    for i in range(10):
        a = i / 10 * 2 * math.pi
        o.append(diya(800 + math.cos(a) * 300, 1112 + math.sin(a) * 80, 16, glow_r=60))
    o.append(mottle(0.25))
    return ''.join(o)


def traditional_2(r):
    o = [lin_bg([(0, '#5a1a12'), (1, '#2a0b07')])]
    o.append(glow(800, 700, 760, 0.6, 'glowSoft'))
    # doorway
    o.append(f'<rect x="460" y="120" width="680" height="820" rx="10" fill="#1a0705"/>')
    o.append('<defs><linearGradient id="inside" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffcf7a"/><stop offset="1" stop-color="#c8641e"/></linearGradient></defs>')
    o.append(cusped_arch(500, 940, 600, 780, 'url(#inside)'))
    o.append(lantern(800, 470, 50, '#c4142b', '#ffd166'))
    for dx, sk in ((500, 1), (1100, -1)):
        o.append(f'<path d="M{dx} 940 L{dx} 330 L{dx+sk*120} 300 L{dx+sk*120} 960Z" fill="#4a1f0c" stroke="#c8963c" stroke-width="5"/>')
        for k in range(5):
            for j in range(2):
                o.append(f'<circle cx="{dx+sk*(35+j*50)}" cy="{400+k*120+j*-6}" r="7" fill="#e8b54a"/>')
    o.append(f'<path d="M520 940 L520 330 M1080 940 L1080 330" stroke="#c8963c" stroke-width="10"/>')
    o.append(f'<rect x="430" y="100" width="740" height="40" fill="#8a4b1c"/>')
    o.append(toran(150, r, 430, 1170, 80))
    o.append(garland(430, 150, 800, 150, 130, 24, r))
    o.append(garland(800, 150, 1170, 150, 130, 24, r))
    o.append(warm_ground(940, '#6b2f1a'))
    o.append(f'<g transform="translate(800 1060) scale(1 0.36)">{rangoli(0, 0, 340, r, ["#d62828", "#f77f00", "#fcbf49", "#2a9d8f", "#9b5de5"])}</g>')
    for i in range(7):
        x = 330 + i * 157
        o.append(diya(x, 990 + (abs(i - 3) * 6), 30))
    o.append(mottle(0.3))
    return ''.join(o)


def traditional_3(r):
    o = [lin_bg([(0, '#060a24'), (0.6, '#1b1d4f'), (1, '#4c2557')])]
    o.append(stars(r, 220, 800))
    o.append(firework(1250, 280, 150, '#ffd166', r))
    o.append(firework(260, 180, 110, '#ef476f', r, n=30))
    for _ in range(26):
        x, y = r.uniform(60, 1540), r.uniform(80, 700)
        o.append(sky_lantern(x, y, r.uniform(9, 24)))
    # rooftops
    x = -20
    while x < W:
        w = r.uniform(140, 260); h = r.uniform(170, 330)
        o.append(f'<rect x="{x:.0f}" y="{1200-h:.0f}" width="{w:.0f}" height="{h:.0f}" fill="#120b1f"/>')
        o.append(f'<polygon points="{x-10:.0f},{1200-h:.0f} {x+w/2:.0f},{1200-h-70:.0f} {x+w+10:.0f},{1200-h:.0f}" fill="#120b1f"/>')
        for k in range(int(w // 60)):
            o.append(glow(x + 40 + k * 60, 1200 - h + 70, 40, 0.5, 'glowSoft'))
            o.append(f'<rect x="{x+28+k*60:.0f}" y="{1200-h+50:.0f}" width="24" height="36" fill="#ffb84d"/>')
        for k in range(int(w // 36)):
            o.append(diya(x + 18 + k * 36, 1200 - h - 2, 8, glow_r=26))
        x += w + r.uniform(-10, 20)
    o.append(mottle(0.25))
    return ''.join(o)


# ---------------------------------------------------------------- rangoli
def rangoli_1(r):
    o = [rad_bg([(0, '#a4552c'), (1, '#4a1a0c')])]
    o.append(mottle(0.35))
    o.append(rangoli(800, 600, 470, r, ['#e63946', '#ffb703', '#219ebc', '#fb8500', '#8338ec', '#06d6a0']))
    for cx, cy in ((170, 170), (1430, 170), (170, 1030), (1430, 1030)):
        o.append(rangoli(cx, cy, 130, r, ['#ffb703', '#e63946', '#06d6a0', '#8338ec'], layers=['petals', 'dots', 'center']))
    for i in range(16):
        a = i / 16 * 2 * math.pi
        o.append(diya(800 + math.cos(a) * 545 - 15, 600 + math.sin(a) * 545 * 0.98 + 10, 20, glow_r=60))
    o.append(bokeh(r, 120, 0, 0, W, H, ['#ffd166', '#ef476f', '#fff1e0'], 2, 6, (0.5, 0.9)))
    return ''.join(o)


def rangoli_2(r):
    o = [rect_bg('#141018'), mottle(0.5, '#3a2b3a')]
    o.append(rangoli(800, 600, 400, r, ['#ff006e', '#ffbe0b', '#3a86ff', '#fb5607', '#8338ec']))
    o.append(peacock(330, 860, 150, r))
    o.append(f'<g transform="translate(1270 860) scale(-1 1)">{peacock(0, 0, 150, r)}</g>')
    for _ in range(140):
        x, y = r.uniform(0, W), r.uniform(0, H)
        if math.hypot(x - 800, y - 600) < 430:
            continue
        o.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="9" ry="16" transform="rotate({r.uniform(0,360):.0f} {x:.0f} {y:.0f})" fill="{r.choice(["#ff006e","#ffbe0b","#fb5607","#ffffff"])}" opacity="0.85"/>')
    for i in range(12):
        a = i / 12 * 2 * math.pi
        o.append(diya(800 + math.cos(a) * 470 - 14, 600 + math.sin(a) * 470 + 8, 19, glow_r=55))
    return ''.join(o)


def rangoli_3(r):
    o = [rect_bg('#f3e6cf'), mottle(0.2, '#7a4b1e')]
    o.append(rangoli(470, 560, 380, r, ['#0b6e4f', '#f2a541', '#c1121f', '#003049', '#e9c46a']))
    o.append(rangoli(1170, 420, 300, r, ['#c1121f', '#f77f00', '#003049', '#fcbf49']))
    o.append(rangoli(1180, 960, 200, r, ['#7b2cbf', '#f72585', '#4cc9f0', '#ffd166'], layers=['scallop', 'petals', 'dots', 'center']))
    # dotted kolam border
    for i in range(0, W, 40):
        for y in (40, H - 40):
            o.append(f'<circle cx="{i+20}" cy="{y}" r="5" fill="#7a1d1d"/>')
            o.append(f'<path d="M{i} {y} Q{i+20} {y-22} {i+40} {y}" stroke="#c1121f" stroke-width="3" fill="none"/>')
    for x in (300, 620, 980, 1380):
        o.append(diya(x, 1080, 24))
    return ''.join(o)


# ---------------------------------------------------------------- lakshmi
def lakshmi_1(r):
    o = [lin_bg([(0, '#3d0a3a'), (0.5, '#7a1f4f'), (1, '#e0893a')])]
    o.append(glow(800, 520, 700, 0.9, 'glowSoft'))
    for i in range(36):
        a = math.radians(i * 10)
        o.append(f'<path d="M800 520 L{800+math.cos(a)*900:.0f} {520+math.sin(a)*900:.0f}" stroke="#ffd98a" stroke-width="{6 if i%2 else 2}" opacity="0.18"/>')
    o.append(f'<rect x="0" y="820" width="{W}" height="380" fill="#21305e" opacity="0.9"/>')
    for i in range(40):
        y = 830 + i * 9
        o.append(f'<path d="M0 {y} Q400 {y-6} 800 {y} T1600 {y}" stroke="#7aa0d8" stroke-width="2" opacity="{0.15 + 0.2*r.random():.2f}" fill="none"/>')
    o.append(lotus(800, 800, 260, 'petalPink'))
    o.append(f'<g opacity="0.35" transform="translate(0 1640) scale(1 -1)">{lotus(800, 800, 260, "petalPink", leaf=False)}</g>')
    for x, s in ((330, 110), (1270, 110), (130, 70), (1470, 70)):
        o.append(lotus(x, 900, s, 'petalWhite'))
    for _ in range(26):
        o.append(coins(r.uniform(150, 1450), r.uniform(-20, 520), 16, r, n=1))
    o.append(coins(800, 1000, 28, r, n=18, spread=1.8))
    return ''.join(o)


def lakshmi_2(r):
    o = [lin_bg([(0, '#4d1414'), (1, '#1f0606')])]
    o.append(f'<path d="M0 760 L1600 760 L1600 1200 L0 1200Z" fill="#7c3a1f"/>')
    o.append(mottle(0.35))
    o.append(f'<rect x="560" y="80" width="480" height="680" fill="#120403"/>')
    o.append(glow(800, 420, 420, 0.8, 'glowSoft'))
    o.append(cusped_arch(600, 760, 400, 640, '#ffcf7a'))
    o.append(toran(110, r, 540, 1060, 60))
    o.append(kalash(470, 740, 110))
    o.append(kalash(1130, 740, 110))
    # footsteps walking in
    steps = [(720, 1150, -4), (880, 1080, 6), (735, 1005, -4), (860, 945, 6), (750, 885, -4), (845, 835, 6)]
    for i, (x, y, a) in enumerate(steps):
        s = 46 - i * 4
        o.append(footprint(x, y, s, a))
    for i in range(9):
        t = i / 8
        o.append(diya(300 - t * 120, 800 + t * 360, 18 + t * 10))
        o.append(diya(1300 + t * 120, 800 + t * 360, 18 + t * 10))
    for _ in range(80):
        o.append(f'<circle cx="{r.uniform(0,W):.0f}" cy="{r.uniform(780,H):.0f}" r="{r.uniform(3,7):.1f}" fill="{r.choice(["#ffffff","#ffd166","#e63946"])}" opacity="0.8"/>')
    return ''.join(o)


def lakshmi_3(r):
    o = [lin_bg([(0, '#f7d9a0'), (0.6, '#e7a75b'), (1, '#9a4d22')])]
    o.append(glow(800, 470, 520, 1.0))
    for i in range(48):
        a = math.radians(i * 7.5)
        o.append(f'<path d="M800 470 L{800+math.cos(a)*330:.0f} {470+math.sin(a)*330:.0f}" stroke="#fff2c2" stroke-width="3" opacity="0.5"/>')
    o.append(f'<circle cx="800" cy="470" r="240" fill="none" stroke="url(#gold)" stroke-width="16"/>')
    o.append(f'<rect x="0" y="880" width="{W}" height="320" fill="#2f6f73"/>')
    o.append(lotus(800, 860, 230, 'petalPink'))
    o.append(elephant(350, 900, 165, body='#e9e4dc', cloth='#b5172f', trim='#f1c34b'))
    o.append(elephant(1250, 900, 165, body='#e9e4dc', cloth='#b5172f', trim='#f1c34b', facing=-1))
    for sgn in (-1, 1):
        x0 = 800 + sgn * 480
        for k in range(5):
            o.append(f'<path d="M{x0} 590 Q{800+sgn*260} {360-k*20} {800+sgn*(90+k*18)} {470+k*10}" stroke="#bfe9ff" stroke-width="{7-k}" fill="none" opacity="0.75"/>')
    for i in range(12):
        o.append(lotus(80 + i * 130, 1040 + (i % 2) * 70, 34, 'petalWhite' if i % 2 else 'petalPink'))
    o.append(coins(800, 1120, 24, r, n=12, spread=2.4))
    return ''.join(o)


# ---------------------------------------------------------------- ganesha
def ganesha_1(r):
    o = [rad_bg([(0, '#b3202e'), (0.7, '#6a0d1a'), (1, '#33040b')])]
    o.append(mandala_lines(800, 560, 520, r, color='#f2c14e', sw=2, rings=8).replace('<g ', '<g opacity="0.35" ', 1))
    o.append(glow(800, 560, 420, 0.5, 'glowSoft'))
    o.append(ganesha(800, 600, 270, line='url(#gold)', sw=0.04))
    for i in range(11):
        o.append(diya(140 + i * 132, 1110, 26))
    o.append(garland(0, 40, 800, 40, 160, 26, r))
    o.append(garland(800, 40, 1600, 40, 160, 26, r))
    return ''.join(o)


def ganesha_2(r):
    o = [rad_bg([(0, '#ffb347'), (0.45, '#d4581f'), (1, '#5a1208')])]
    for i in range(60):
        a = math.radians(i * 6)
        o.append(f'<path d="M800 600 L{800+math.cos(a)*1100:.0f} {600+math.sin(a)*1100:.0f}" stroke="#ffe7b0" stroke-width="{10 if i%3==0 else 3}" opacity="0.16"/>')
    o.append(f'<circle cx="800" cy="600" r="330" fill="#7a1408" opacity="0.55"/>')
    o.append(f'<circle cx="800" cy="600" r="330" fill="none" stroke="url(#gold)" stroke-width="14"/>')
    o.append(rangoli(800, 600, 300, r, ['#8c1c13', '#bf4342', '#e7d7c1', '#a78a7f'], layers=['scallop', 'dots']).replace('<g ', '<g opacity="0.55" ', 1))
    o.append(om(800, 585, 420))
    o.append(deva_text(800, 1060, 'ॐ श्री गणेशाय नमः', 74, '#ffe2a0'))
    o.append(garland(0, 30, 520, 60, 210, 30, r))
    o.append(garland(1080, 60, 1600, 30, 210, 30, r))
    for x in (230, 1370):
        o.append(diya(x, 900, 46))
    return ''.join(o)


def ganesha_3(r):
    o = [lin_bg([(0, '#0b2a3c'), (1, '#04131c')])]
    o.append(glow(800, 560, 520, 0.55, 'glowSoft'))
    o.append(lotus(800, 1000, 230, 'petalPink'))
    o.append(ganesha(800, 560, 250, line='#fff3dc', sw=0.038, accent='#ff6b6b'))
    for i in range(18):
        a = math.pi + i / 17 * math.pi
        x, y = 800 + math.cos(a) * 590, 620 + math.sin(a) * 500
        o.append(marigold(x, y, 26, r) if i % 2 else diya(x - 10, y + 6, 22, glow_r=70))
    o.append(bokeh(r, 70, 0, 0, W, H, ['#ffd166', '#ffffff'], 2, 5, (0.4, 0.9)))
    return ''.join(o)


# ---------------------------------------------------------------- diya
def diya_1(r):
    o = [lin_bg([(0, '#2b0d0a'), (1, '#120403')])]
    o.append(bokeh(r, 70, 0, 0, W, 760, ['#ffb347', '#ff7b39', '#ffd36b', '#f25c54'], 20, 70, (0.12, 0.4)))
    o.append(f'<g filter="url(#blur6)">{bokeh(r, 30, 0, 0, W, 700, ["#ffd36b", "#fff1c9"], 8, 26, (0.3, 0.6))}</g>')
    o.append(f'<rect x="0" y="830" width="{W}" height="370" fill="#4a2414"/><rect x="0" y="830" width="{W}" height="16" fill="#8a5432"/>')
    for i in range(9):
        o.append(diya(110 + i * 172, 820, 58 + (8 if i == 4 else 0)))
    for _ in range(110):
        x, y = r.uniform(0, W), r.uniform(860, 1180)
        o.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="10" ry="16" transform="rotate({r.uniform(0,360):.0f} {x:.0f} {y:.0f})" fill="{r.choice(["#f28c0f","#ffc93c","#d62828","#ffe066"])}"/>')
    return ''.join(o)


def diya_2(r):
    o = [lin_bg([(0, '#0a1630'), (0.45, '#1b2b5a'), (1, '#06101f')])]
    o.append(stars(r, 80, 380))
    o.append(f'<rect x="0" y="420" width="{W}" height="780" fill="#0b2140"/>')
    for i in range(70):
        y = 430 + i * 11
        o.append(f'<path d="M0 {y} Q400 {y-5} 800 {y} T1600 {y}" stroke="#4d79b8" stroke-width="2" opacity="{0.08 + 0.12*r.random():.2f}" fill="none"/>')
    spots = [(r.uniform(80, 1520), r.uniform(500, 1150)) for _ in range(16)]
    for x, y in sorted(spots, key=lambda p: p[1]):
        s = 18 + (y - 480) / 700 * 34
        o.append(f'<rect x="{x+s*0.9:.0f}" y="{y:.0f}" width="{s*0.35:.0f}" height="{s*5:.0f}" fill="#ffb347" opacity="0.25" filter="url(#blur6)"/>')
        o.append(diya(x, y, s, glow_r=s * 4))
    for _ in range(9):
        x, y = r.uniform(80, 1520), r.uniform(560, 1150)
        o.append(lotus(x, y, 22 + (y - 480) / 700 * 34, r.choice(['petalPink', 'petalWhite'])))
    for _ in range(90):
        x, y = r.uniform(0, W), r.uniform(500, H)
        o.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="7" ry="4" fill="{r.choice(["#f28c0f","#ffc93c","#e63946"])}" opacity="0.8"/>')
    return ''.join(o)


def diya_3(r):
    o = [rad_bg([(0, '#7a2a10'), (1, '#1c0703')])]
    o.append(glow(800, 560, 640))
    o.append(garland(-40, 120, 820, 120, 330, 38, r))
    o.append(garland(780, 120, 1640, 120, 330, 38, r))
    for x in (60, 1540):
        for k in range(8):
            o.append(marigold(x, 160 + k * 80, 34, r, *(('#ffd23a', '#fff07a', '#d99a06') if k % 2 else ('#f28c0f', '#ffc93c', '#c45a06'))))
    o.append(diya(760, 760, 230, body='brass', band='#c4142b', dots='#7a1d1d', glow_r=760))
    for _ in range(160):
        x, y = r.uniform(80, 1520), r.uniform(900, 1180)
        o.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="11" ry="18" transform="rotate({r.uniform(0,360):.0f} {x:.0f} {y:.0f})" fill="{r.choice(["#c1121f","#e63946","#f28c0f","#ffc93c"])}"/>')
    return ''.join(o)


# ---------------------------------------------------------------- heritage
def heritage_1(r):
    o = [lin_bg([(0, '#1d1240'), (0.45, '#82325a'), (0.62, '#f08a4b'), (0.63, '#1a2238'), (1, '#0b1020')])]
    o.append(stars(r, 70, 300))
    o.append(firework(1300, 190, 120, '#ffd166', r))
    for x, s in ((260, 70), (560, 95), (900, 80), (1250, 105)):
        o.append(temple(x, 640, s, '#1a0f2a'))
    for k in range(6):
        y = 640 + k * 20
        o.append(f'<rect x="0" y="{y}" width="{W}" height="20" fill="{["#2a1d33","#33243d"][k%2]}"/>')
        for i in range(int(W // 70)):
            o.append(diya(35 + i * 70 + (k % 2) * 35, y + 6, 6, glow_r=20))
    for _ in range(170):
        x, y = r.uniform(0, W), r.uniform(790, 1190)
        s = 4 + (y - 760) / 440 * 14
        o.append(f'<rect x="{x+s*0.9:.0f}" y="{y:.0f}" width="{max(2, s*0.4):.0f}" height="{s*5:.0f}" fill="#ffb347" opacity="0.3" filter="url(#blur2)"/>')
        o.append(diya(x, y, s, glow_r=s * 3.5))
    return ''.join(o)


def heritage_2(r):
    o = [lin_bg([(0, '#160c2b'), (0.7, '#4a1d3f'), (1, '#2b0f12')])]
    o.append(stars(r, 120, 500))
    o.append(glow(800, 620, 620, 0.55, 'glowSoft'))
    o.append(temple(800, 900, 210, '#241238'))
    o.append(f'<rect x="700" y="760" width="200" height="140" fill="#ffb84d"/>')
    o.append(cusped_arch(720, 900, 160, 150, '#ffd98f'))
    for x in (330, 1270):  # deepstambh lamp towers
        o.append(f'<path d="M{x-40} 920 L{x-22} 360 L{x+22} 360 L{x+40} 920Z" fill="#3a2246"/>')
        for k in range(10):
            y = 900 - k * 56
            w = 54 - k * 2.6
            o.append(f'<rect x="{x-w}" y="{y}" width="{2*w}" height="8" fill="#5a3466"/>')
            for d in (-w + 6, 0, w - 6):
                o.append(diya(x + d - 4, y - 2, 8, glow_r=30))
        o.append(diya(x - 6, 350, 16))
    o.append(warm_ground(920, '#3d1d13'))
    o.append(f'<g transform="translate(800 1060) scale(1 0.33)">{rangoli(0, 0, 330, r, ["#e63946", "#ffb703", "#06d6a0", "#8338ec", "#fb8500"])}</g>')
    return ''.join(o)


def heritage_3(r):
    o = [lin_bg([(0, '#0d1033'), (0.6, '#40265e'), (1, '#c4573a')])]
    o.append(stars(r, 100, 500))
    o.append(firework(400, 230, 170, '#ffd166', r))
    o.append(firework(1150, 300, 200, '#ff6fa8', r))
    o.append(firework(820, 140, 100, '#9bf6ff', r, n=26))
    o.append(f'<path d="M0 1200 L0 900 Q400 760 800 800 Q1200 840 1600 760 L1600 1200Z" fill="#1c0f22"/>')
    # fort wall with crenellations
    o.append(f'<path d="M180 820 L1450 780 L1450 640 L180 690Z" fill="#2e1a33"/>')
    for i in range(30):
        x = 180 + i * 43
        y = 690 - i * 1.6
        o.append(f'<rect x="{x}" y="{y-24:.0f}" width="26" height="26" fill="#2e1a33"/>')
        o.append(diya(x + 10, y - 26, 7, glow_r=26))
    for x in (180, 600, 1020, 1450):
        y = 690 - (x - 180) / 1270 * 50
        o.append(f'<rect x="{x-45}" y="{y-180:.0f}" width="90" height="190" fill="#251329"/><path d="M{x-55} {y-180:.0f} Q{x} {y-280:.0f} {x+55} {y-180:.0f}Z" fill="#251329"/>')
        o.append(cusped_arch(x - 16, y - 90, 32, 60, '#ffb84d'))
    return ''.join(o)


# ---------------------------------------------------------------- rajasthani
def rajasthani_1(r):
    o = [lin_bg([(0, '#f3a6a0'), (0.55, '#e57a6b'), (1, '#b84a3c')])]
    o.append(f'<rect x="0" y="140" width="{W}" height="680" fill="#d8665a"/>')
    for i in range(7):
        x = 40 + i * 225
        o.append(cusped_arch(x, 760, 170, 520, '#8f2f2f'))
        o.append(cusped_arch(x + 18, 760, 134, 470, '#f6c36b'))
        o.append(f'<rect x="{x}" y="760" width="170" height="16" fill="#f3e0c0"/>')
        o.append(diya(x + 70, 755, 18))
    o.append(f'<rect x="0" y="120" width="{W}" height="30" fill="#f3e0c0"/>')
    o.append(garland(0, 160, 800, 160, 120, 22, r))
    o.append(garland(800, 160, 1600, 160, 120, 22, r))
    o.append(f'<rect x="0" y="780" width="{W}" height="420" fill="#c98a4b"/>')
    o.append(mottle(0.2))
    o.append(elephant(470, 1110, 190, body='#6f7b9e', cloth='#1f4e8c', trim='#f1c34b'))
    o.append(elephant(1180, 1110, 190, body='#7d7f98', cloth='#b5172f', trim='#f1c34b', facing=-1))
    return ''.join(o)


def rajasthani_2(r):
    o = [rect_bg('#e8a07a'), mottle(0.3, '#7a2d18')]
    for row in range(2):
        for i in range(5):
            x = 90 + i * 300
            yb = 560 + row * 520
            o.append(f'<rect x="{x-20}" y="{yb-440}" width="250" height="470" fill="#d47c58"/>')
            o.append(cusped_arch(x, yb, 210, 400, '#5a1d17'))
            o.append(glow(x + 105, yb - 130, 170, 0.8))
            o.append(cusped_arch(x + 22, yb, 166, 350, '#ffcd73'))
            o.append(f'<path d="M{x-24} {yb-450} Q{x+105} {yb-520} {x+234} {yb-450}Z" fill="#b65a3d"/>')
            o.append(diya(x + 92, yb - 10, 30))
            o.append(f'<rect x="{x-30}" y="{yb}" width="270" height="22" fill="#f6d7b0"/>')
    o.append(peacock(1350, 1140, 120, r, fan=False))
    return ''.join(o)


def rajasthani_3(r):
    o = [lin_bg([(0, '#0b1446'), (0.7, '#2c2b6e'), (1, '#4b2a56')])]
    o.append(stars(r, 150, 560))
    for x, s in ((200, 1.0), (500, 1.3), (1100, 1.3), (1400, 1.0)):
        o.append(f'<g transform="translate({x} 700) scale({s})" fill="#191338"><rect x="-70" y="-60" width="140" height="300"/><path d="M-90 -60 Q0 -190 90 -60Z"/><rect x="-6" y="-200" width="12" height="40"/></g>')
        o.append(lantern(x, 440 - s * 60, 30 * s, '#ff5d73', '#ffd166'))
    o.append(f'<rect x="0" y="900" width="{W}" height="300" fill="#191338"/>')
    for i in range(int(W // 40)):
        o.append(diya(20 + i * 40, 902, 9, glow_r=30))
    o.append(peacock(800, 960, 260, r))
    return ''.join(o)


# ---------------------------------------------------------------- abstract
def abstract_1(r):
    o = [rect_bg('#1d1a4a')]
    shapes = [(420, 520, 430, '#ff7b00'), (1140, 420, 360, '#d81159'), (900, 880, 300, '#ffbc42'), (260, 980, 220, '#218380'), (1420, 950, 260, '#8f2d56')]
    for x, y, rr, c in shapes:
        o.append(f'<circle cx="{x}" cy="{y}" r="{rr}" fill="{c}" opacity="0.88"/>')
    o.append(f'<g style="mix-blend-mode:screen">' + ''.join(f'<circle cx="{x+40}" cy="{y-30}" r="{rr*0.6}" fill="none" stroke="#ffe29a" stroke-width="6" opacity="0.6"/>' for x, y, rr, _ in shapes) + '</g>')
    # geometric diya
    o.append('<path d="M560 760 A240 240 0 0 0 1040 760Z" fill="#fef3c7"/>')
    o.append('<path d="M800 760 C700 620 760 470 800 360 C840 470 900 620 800 760Z" fill="#ffbc42"/><path d="M800 740 C750 650 780 560 800 500 C820 560 850 650 800 740Z" fill="#fff8e1"/>')
    for k in range(9):
        o.append(f'<path d="M{100+k*170} 0 L{40+k*170} 1200" stroke="#ffffff" stroke-width="2" opacity="0.06"/>')
    o.append(f'<rect width="{W}" height="{H}" fill="#e9b949" filter="url(#goldleaf)" opacity="0.18"/>')
    return ''.join(o)


def abstract_2(r):
    o = [rect_bg('#f6efe6')]
    o.append('<defs><filter id="brushy" x="-20%" y="-20%" width="140%" height="140%"><feTurbulence type="fractalNoise" baseFrequency="0.02 0.4" numOctaves="2" seed="5"/><feDisplacementMap in="SourceGraphic" scale="40"/></filter></defs>')
    cols = ['#ff5400', '#ff0054', '#ffbd00', '#00a6a6', '#390099', '#9e0059']
    for i in range(14):
        y = r.uniform(80, 1120); c = r.choice(cols)
        o.append(f'<path d="M{r.uniform(-200,300):.0f} {y:.0f} C{r.uniform(300,700):.0f} {y+r.uniform(-260,260):.0f} {r.uniform(900,1300):.0f} {y+r.uniform(-260,260):.0f} {r.uniform(1300,1800):.0f} {y+r.uniform(-120,120):.0f}" stroke="{c}" stroke-width="{r.uniform(40,150):.0f}" stroke-linecap="round" fill="none" opacity="0.82" filter="url(#brushy)"/>')
    for _ in range(26):
        x, y = r.uniform(100, 1500), r.uniform(100, 1100)
        rr = r.uniform(20, 60)
        o.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="url(#gold)"/><circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="#fff3c4" filter="url(#goldleaf)" opacity="0.6"/>')
    o.append(bokeh(r, 160, 0, 0, W, H, ['#ffffff'], 2, 5, (0.6, 1)))
    for x in (520, 800, 1080):
        o.append(diya(x, 1020, 48, body='#1b1b3a', band='#ffbd00'))
    return ''.join(o)


def abstract_3(r):
    o = [rad_bg([(0, '#2d0f3d'), (1, '#05020a')], 0.5, 0.6, 0.8)]
    o.append(f'<g filter="url(#blur20)">{bokeh(r, 40, 0, 0, W, H, ["#ff9e00", "#ff4d6d", "#ffd60a", "#c77dff"], 40, 110, (0.25, 0.55))}</g>')
    o.append(f'<g filter="url(#blur6)">{bokeh(r, 70, 0, 0, W, H, ["#ffd60a", "#ffb703", "#fff1c9"], 10, 34, (0.4, 0.8))}</g>')
    o.append(bokeh(r, 220, 0, 0, W, H, ['#fff8e1', '#ffd166'], 1.5, 4, (0.6, 1)))
    # minimal line diya
    o.append('<path d="M560 820 Q800 1030 1040 820" stroke="#ffd166" stroke-width="10" fill="none" stroke-linecap="round"/>')
    o.append('<path d="M540 820 L1060 820" stroke="#ffd166" stroke-width="6" stroke-linecap="round"/>')
    o.append(flame(800, 800, 300))
    o.append(glow(800, 650, 420, 0.9))
    return ''.join(o)


# ---------------------------------------------------------------- folk
def folk_1(r):
    o = [rect_bg('#8b3a1a'), mottle(0.35, '#3a1206')]
    ink = '#f6efe2'
    # sun & houses & trees (Warli vocabulary)
    o.append(f'<circle cx="1380" cy="170" r="70" fill="none" stroke="{ink}" stroke-width="6"/>')
    for i in range(16):
        a = math.radians(i * 22.5)
        o.append(f'<path d="M{1380+math.cos(a)*85:.0f} {170+math.sin(a)*85:.0f} L{1380+math.cos(a)*115:.0f} {170+math.sin(a)*115:.0f}" stroke="{ink}" stroke-width="5"/>')
    for x in (150, 300):
        o.append(f'<path d="M{x-70} 330 L{x} 250 L{x+70} 330 L{x+55} 330 L{x+55} 420 L{x-55} 420 L{x-55} 330Z" fill="none" stroke="{ink}" stroke-width="5"/><rect x="{x-14}" y="370" width="28" height="50" fill="{ink}"/>')
    for x in (1240, 1500):
        o.append(f'<path d="M{x} 1120 L{x} 860" stroke="{ink}" stroke-width="7"/>')
        for k in range(9):
            o.append(f'<path d="M{x} {880+k*24} L{x+(1 if k%2 else -1)*60} {850+k*24}" stroke="{ink}" stroke-width="4"/>')
    # concentric tarpa dance circles around the diya
    for ring, (R, n) in enumerate(((210, 12), (330, 18), (450, 24))):
        for i in range(n):
            a = i / n * 2 * math.pi
            x, y = 800 + math.cos(a) * R, 640 + math.sin(a) * R * 0.92
            o.append(warli_figure(x, y, 22 - ring * 1.5, math.degrees(a) + 90, ink, 'up' if (i + ring) % 2 else 'side'))
    o.append(diya(770, 650, 70, body='#3b1608', band=ink, dots=ink, glow_r=260))
    for i in range(0, W, 30):
        o.append(f'<path d="M{i} 1170 L{i+15} 1150 L{i+30} 1170" stroke="{ink}" stroke-width="3" fill="none"/>')
        o.append(f'<path d="M{i} 30 L{i+15} 50 L{i+30} 30" stroke="{ink}" stroke-width="3" fill="none"/>')
    return ''.join(o)


def madhubani_border(width=60, c1='#111', c2='#d62828', c3='#ffd166'):
    o = [f'<rect x="{width/2}" y="{width/2}" width="{W-width}" height="{H-width}" fill="none" stroke="{c2}" stroke-width="{width}"/>']
    o.append(f'<rect x="8" y="8" width="{W-16}" height="{H-16}" fill="none" stroke="{c1}" stroke-width="6"/><rect x="{width-6}" y="{width-6}" width="{W-2*width+12}" height="{H-2*width+12}" fill="none" stroke="{c1}" stroke-width="6"/>')
    for i in range(0, W, 40):
        for y in (width / 2, H - width / 2):
            o.append(f'<path d="M{i} {y} q10 -14 20 0 q10 14 20 0" stroke="{c3}" stroke-width="5" fill="none"/>')
    for j in range(0, H, 40):
        for x in (width / 2, W - width / 2):
            o.append(f'<path d="M{x} {j} q-14 10 0 20 q14 10 0 20" stroke="{c3}" stroke-width="5" fill="none"/>')
    return ''.join(o)


def fish(x, y, s, ang, body='#2a9d8f', ink='#111'):
    o = [f'<g transform="translate({f(x)} {f(y)}) rotate({ang}) scale({f(s)})">']
    o.append(f'<path d="M-1 0 C-0.5 -0.55 0.5 -0.55 0.9 0 C0.5 0.55 -0.5 0.55 -1 0Z" fill="{body}" stroke="{ink}" stroke-width="0.06"/>')
    o.append(f'<path d="M0.85 0 L1.35 -0.35 L1.3 0 L1.35 0.35Z" fill="{body}" stroke="{ink}" stroke-width="0.06"/>')
    for i in range(6):
        o.append(f'<path d="M{-0.3+i*0.18} -0.3 Q{-0.2+i*0.18} 0 {-0.3+i*0.18} 0.3" stroke="{ink}" stroke-width="0.035" fill="none"/>')
    o.append(f'<circle cx="-0.65" cy="-0.08" r="0.11" fill="#fff" stroke="{ink}" stroke-width="0.04"/><circle cx="-0.65" cy="-0.08" r="0.05" fill="{ink}"/></g>')
    return ''.join(o)


def folk_2(r):
    o = [rect_bg('#f7e7c4'), mottle(0.12, '#8a5a12')]
    o.append(madhubani_border())
    # central diya with hatched bowl, flanked by fish & peacocks
    o.append(f'<g stroke="#111" stroke-width="6">')
    o.append('<path d="M480 760 C520 960 1080 960 1120 760 Q800 820 480 760Z" fill="#d62828"/>')
    o.append('</g>')
    for i in range(14):
        x = 540 + i * 38
        o.append(f'<path d="M{x} 800 L{x+14} 900" stroke="#111" stroke-width="4"/>')
    o.append('<path d="M480 760 Q800 820 1120 760" stroke="#ffd166" stroke-width="14" fill="none"/>')
    o.append('<path d="M800 740 C640 540 760 330 800 230 C840 330 960 540 800 740Z" fill="#ffd166" stroke="#111" stroke-width="7"/>')
    o.append('<path d="M800 700 C730 560 780 430 800 360 C820 430 870 560 800 700Z" fill="#f77f00" stroke="#111" stroke-width="5"/>')
    for k in range(5):
        o.append(f'<path d="M800 {690-k*60} m-{40-k*6} 0 q{40-k*6} -30 {2*(40-k*6)} 0" stroke="#111" stroke-width="3" fill="none"/>')
    o.append(fish(320, 400, 120, -20, '#2a9d8f'))
    o.append(fish(1280, 400, 120, 200, '#e76f51'))
    o.append(fish(320, 860, 100, 20, '#e9c46a'))
    o.append(fish(1280, 860, 100, 160, '#2a9d8f'))
    for x in (230, 1370):
        for k in range(5):
            o.append(f'<circle cx="{x}" cy="{240+k*170}" r="26" fill="#d62828" stroke="#111" stroke-width="5"/><circle cx="{x}" cy="{240+k*170}" r="9" fill="#ffd166"/>')
    for k in range(9):
        a = math.radians(-160 + k * 17.5)
        o.append(f'<ellipse cx="{800+math.cos(a)*330:.0f}" cy="{560+math.sin(a)*330:.0f}" rx="30" ry="58" transform="rotate({math.degrees(a)+90:.0f} {800+math.cos(a)*330:.0f} {560+math.sin(a)*330:.0f})" fill="{["#2a9d8f","#e76f51","#e9c46a"][k%3]}" stroke="#111" stroke-width="5"/>')
    return ''.join(o)


def folk_3(r):
    o = [rect_bg('#101524')]
    # Gond tree: trunk + dot/line filled leaves
    o.append('<path d="M760 1200 C770 1000 740 860 700 760 L760 760 C790 860 820 1000 840 1200Z" fill="#c1440e"/>')
    for k in range(40):
        y = 1180 - k * 11
        o.append(f'<path d="M{770+k*0.3:.0f} {y} L{820-k*0.6:.0f} {y}" stroke="#ffd166" stroke-width="2"/>')
    branches = []
    for i in range(9):
        a = math.radians(-170 + i * 20)
        branches.append((730 + math.cos(a) * 520, 700 + math.sin(a) * 520 * 0.9))
    for bx, by in branches:
        o.append(f'<path d="M730 760 Q{(730+bx)/2:.0f} {by+120:.0f} {bx:.0f} {by:.0f}" stroke="#c1440e" stroke-width="18" fill="none"/>')
    cols = ['#2ec4b6', '#ff9f1c', '#e71d36', '#a3d977', '#f9c80e']
    for _ in range(46):
        x, y = r.uniform(170, 1330), r.uniform(120, 760)
        if math.hypot((x - 730) / 1.1, y - 650) > 600:
            continue
        L = r.uniform(70, 120); a = r.uniform(0, 360); c = r.choice(cols)
        o.append(f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M0 0 C{L*0.3:.0f} {-L*0.3:.0f} {L*0.8:.0f} {-L*0.25:.0f} {L:.0f} 0 C{L*0.8:.0f} {L*0.25:.0f} {L*0.3:.0f} {L*0.3:.0f} 0 0Z" fill="{c}"/>')
        for d in range(8):
            o.append(f'<circle cx="{L*(0.15+d*0.1):.0f}" cy="{(r.random()-0.5)*L*0.2:.0f}" r="2.6" fill="#101524"/>')
        o.append('</g>')
    for bx, by in branches[1:-1:2]:
        o.append(f'<line x1="{bx:.0f}" y1="{by:.0f}" x2="{bx:.0f}" y2="{by+60:.0f}" stroke="#ffd166" stroke-width="2"/>')
        o.append(diya(bx - 10, by + 80, 20, glow_r=80))
    for x, y, c in ((380, 380, '#2ec4b6'), (1100, 330, '#ff9f1c')):
        o.append(f'<g transform="translate({x} {y})"><path d="M-50 0 C-40 -40 30 -45 50 -10 L80 -20 L58 0 C40 40 -30 40 -50 0Z" fill="{c}"/><circle cx="30" cy="-15" r="6" fill="#101524"/>' + ''.join(f'<path d="M{-30+k*12} -20 L{-30+k*12} 20" stroke="#101524" stroke-width="3"/>' for k in range(5)) + '</g>')
    o.append(stars(r, 60, 1200, '#ffd166'))
    return ''.join(o)


# ---------------------------------------------------------------- gold
def gold_1(r):
    o = [rad_bg([(0, '#1b1611'), (1, '#050403')])]
    o.append(glow(800, 600, 600, 0.35, 'glowSoft'))
    o.append(mandala_lines(800, 600, 540, r, color='url(#gold)', sw=4, rings=9))
    o.append(f'<circle cx="800" cy="600" r="120" fill="url(#gold)"/>')
    o.append(f'<circle cx="800" cy="600" r="120" fill="#fff3c4" filter="url(#goldleaf)" opacity="0.55"/>')
    for _ in range(14):
        x, y = r.choice([r.uniform(0, 300), r.uniform(1300, 1600)]), r.uniform(0, H)
        rr = r.uniform(30, 110)
        o.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="url(#gold)" opacity="0.85"/><circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="#fff3c4" filter="url(#goldleaf)" opacity="0.6"/>')
    return ''.join(o)


def gold_2(r):
    o = [rad_bg([(0, '#0f5a46'), (1, '#032019')])]
    o.append(mottle(0.4))
    for i in range(0, W, 110):
        for y in (70, H - 70):
            o.append(paisley(i + 55, y, 40, 90 if y < 600 else -90, 'url(#gold)', '#0f5a46'))
    o.append(f'<rect x="70" y="140" width="{W-140}" height="{H-280}" fill="none" stroke="url(#gold)" stroke-width="5"/>')
    o.append(f'<rect x="90" y="160" width="{W-180}" height="{H-320}" fill="none" stroke="url(#gold)" stroke-width="2"/>')
    o.append(mandala_lines(800, 560, 300, r, color='url(#gold)', sw=2.5, rings=6).replace('<g ', '<g opacity="0.5" ', 1))
    for i in range(5):
        x = 330 + i * 235
        o.append(diya(x - 20, 860 + abs(i - 2) * 18, 70 - abs(i - 2) * 8, body='gold', band='#0f5a46', dots='#0f5a46'))
    return ''.join(o)


def gold_3(r):
    o = [lin_bg([(0, '#3a0610'), (1, '#0e0104')])]
    o.append(f'<rect width="{W}" height="{H}" fill="#e9b949" filter="url(#goldleaf)" opacity="0.1"/>')
    o.append(glow(800, 560, 560, 0.5, 'glowSoft'))
    o.append(om(800, 300, 200, 'url(#gold)', 0.9))
    o.append(f'<defs><radialGradient id="petalGold" cx="50%" cy="90%" r="90%"><stop offset="0" stop-color="#fff6cf"/><stop offset="0.5" stop-color="#e3b14a"/><stop offset="1" stop-color="#7d5110"/></radialGradient></defs>')
    o.append(lotus(800, 860, 300, 'petalGold', leaf=False))
    o.append(coins(800, 990, 30, r, n=22, spread=2.2))
    for x in (260, 1340):
        o.append(diya(x, 980, 60, body='gold', band='#3a0610', dots='#3a0610'))
    return ''.join(o)


PAINTINGS = [
    ('traditional-1', 'traditional', 'Festival of Lights at the Haveli', 'A haveli lined with diyas under a sky of fireworks.', 'Acrylic on canvas', traditional_1),
    ('traditional-2', 'traditional', 'Diyas on the Doorstep', 'A garlanded doorway welcoming the goddess with rangoli and lamps.', 'Oil on canvas', traditional_2),
    ('traditional-3', 'traditional', 'Lanterns over the Rooftops', 'Sky lanterns drift over a sleeping town ringed with light.', 'Acrylic on canvas', traditional_3),
    ('rangoli-1', 'rangoli', 'Lotus Mandala Rangoli', 'A sixteen-lamp rangoli on a terracotta courtyard.', 'Textured acrylic', rangoli_1),
    ('rangoli-2', 'rangoli', 'Peacock Rangoli', 'Peacocks guard a jewel-toned rangoli strewn with petals.', 'Acrylic on canvas', rangoli_2),
    ('rangoli-3', 'rangoli', 'Kolam Garden', 'Interlacing rangolis framed by a dotted kolam border.', 'Gouache-style acrylic', rangoli_3),
    ('lakshmi-1', 'lakshmi', "Lakshmi's Lotus", 'A radiant lotus rises as gold coins fall like blessings.', 'Oil on canvas', lakshmi_1),
    ('lakshmi-2', 'lakshmi', 'Footsteps of Prosperity', 'Alta-red footsteps lead through a lamp-lit doorway.', 'Acrylic on canvas', lakshmi_2),
    ('lakshmi-3', 'lakshmi', 'Gaja Lakshmi Abhishek', 'Royal elephants bathe the sacred lotus in light.', 'Oil on canvas', lakshmi_3),
    ('ganesha-1', 'ganesha', 'Golden Vighnaharta', 'A gilded line portrait of Ganesha within a mandala halo.', 'Gold leaf & acrylic', ganesha_1),
    ('ganesha-2', 'ganesha', 'Om Shri Ganeshaya Namah', 'A sunburst Om framed by marigold torans.', 'Acrylic on canvas', ganesha_2),
    ('ganesha-3', 'ganesha', 'Lamps for Ganapati', 'Ganesha on a lotus, encircled by diyas and marigolds.', 'Oil on canvas', ganesha_3),
    ('diya-1', 'diya', 'Row of Light', 'Nine clay diyas on a ledge strewn with marigold petals.', 'Oil on canvas', diya_1),
    ('diya-2', 'diya', 'Floating Diyas', 'Lamps and lotuses drifting on a twilight river.', 'Acrylic on canvas', diya_2),
    ('diya-3', 'diya', 'Marigold & Flame', 'A brass diya crowned by heavy marigold garlands.', 'Impasto oil', diya_3),
    ('heritage-1', 'heritage', 'Ghats of Light', 'Temple ghats and a river carrying a thousand lamps.', 'Oil on canvas', heritage_1),
    ('heritage-2', 'heritage', 'Temple Courtyard Deepstambh', 'Twin lamp towers blaze before a shikhara temple.', 'Acrylic on canvas', heritage_2),
    ('heritage-3', 'heritage', 'Fort at Dusk', 'Fireworks bloom over the ramparts of a hill fort.', 'Acrylic on canvas', heritage_3),
    ('rajasthani-1', 'rajasthani', 'Royal Elephant Procession', 'Caparisoned elephants before pink-city arches.', 'Gouache-style acrylic', rajasthani_1),
    ('rajasthani-2', 'rajasthani', 'Jharokha Lights', 'Sandstone jharokhas, each holding a single flame.', 'Textured acrylic', rajasthani_2),
    ('rajasthani-3', 'rajasthani', 'Peacock Palace Night', 'A peacock dances beneath chhatris and star lanterns.', 'Oil on canvas', rajasthani_3),
    ('abstract-1', 'abstract', 'Flame Geometry', 'Overlapping orbs resolve into an abstract diya.', 'Acrylic & gold leaf', abstract_1),
    ('abstract-2', 'abstract', 'Celebration in Colour', 'Gestural sweeps of festival colour and gilt.', 'Mixed media', abstract_2),
    ('abstract-3', 'abstract', 'Night of a Thousand Lights', 'A single line-drawn diya in a field of bokeh.', 'Oil on canvas', abstract_3),
    ('folk-1', 'folk', 'Warli Diwali Dance', 'Warli figures dance the tarpa around a central lamp.', 'Rice paste on earth-red (acrylic)', folk_1),
    ('folk-2', 'folk', 'Madhubani Deep', 'A Madhubani-style lamp with fish, petals and bold borders.', 'Acrylic on canvas', folk_2),
    ('folk-3', 'folk', 'Gond Tree of Light', 'A Gond-style tree bearing diyas as fruit.', 'Acrylic on canvas', folk_3),
    ('gold-1', 'gold', 'Golden Mandala', 'An intricate gold mandala on midnight black.', 'Gold leaf on canvas', gold_1),
    ('gold-2', 'gold', 'Emerald & Gold Diyas', 'Gilded diyas on emerald with a paisley border.', 'Gold leaf & acrylic', gold_2),
    ('gold-3', 'gold', 'Gilded Lotus', 'A gold-leaf lotus and Om over crimson-black.', 'Gold leaf & oil', gold_3),
]
