"""Per-painting "Bring to Life" animation definitions.

Procedural paintings: anchors are recorded automatically while the painting is drawn (motifs.py),
then enriched here with what only the composition knows (water areas, rotating halos, divine
light, rangoli sparkle...). Imported artwork (Skets Studio, future AI paintings) is defined by
hand-checked anchors + automatic light detection — see `imported.py`.

Every painting gets its own animation built from its actual contents. Protected rectangles
(faces, deity figures) are excluded from every pixel effect.
"""
import math, random

W, H = 1600, 1200


def sparkle(cx, cy, rx, ry, n, seed, r=6):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a, d = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        out.append(('star', cx + math.cos(a) * rx * d, cy + math.sin(a) * ry * d, r * rng.uniform(0.7, 1.3)))
    return out


GOLD = '#ffd77a'
EXTRAS = {
    'traditional-1': dict(add=sparkle(800, 1110, 230, 74, 40, 1)),
    'traditional-2': dict(add=sparkle(800, 1060, 340, 122, 50, 2) + [('glow', 800, 560, 260)]),
    'traditional-3': dict(add=[]),
    'lakshmi-1': dict(add=[('water', 0, 830, 1600, 1200), ('glow', 800, 520, 300), ('dust', 800, 640, 330, GOLD), ('dust', 800, 260, 420, '#ffe6a0')]),
    'lakshmi-2': dict(add=[('glow', 800, 450, 210), ('dust', 800, 470, 230, GOLD)]),
    'lakshmi-3': dict(add=[('water', 0, 885, 1600, 1200), ('glow', 800, 470, 230), ('dust', 800, 470, 300, GOLD)]),
    'ganesha-1': dict(add=[('rays', 800, 600, 455, 760, 0.35), ('dust', 800, 600, 470, GOLD)], protect=[(455, 212, 1145, 1020)]),
    'ganesha-2': dict(add=[('halo', 800, 600, 297, 338, 0.18), ('rays', 800, 600, 350, 760, 0.3), ('dust', 800, 600, 360, GOLD)]),
    'ganesha-3': dict(add=[('dust', 800, 600, 420, GOLD), ('glow', 800, 560, 300)], protect=[(515, 185, 1085, 940)]),
    'diya-1': dict(add=[('petals', 800, 1010, 300, ['#f28c0f', '#ffc93c', '#d62828'])]),
    'diya-2': dict(add=[('water', 0, 425, 1600, 1200)]),
    'diya-3': dict(add=[('petals', 800, 1050, 320, ['#c1121f', '#e63946', '#f28c0f']), ('glow', 760, 600, 380)]),
    'heritage-1': dict(add=[('water', 0, 780, 1600, 1200)]),
    'heritage-2': dict(add=sparkle(800, 1060, 330, 110, 40, 3) + [('glow', 800, 820, 120)]),
    'heritage-3': dict(add=[]),
    'rajasthani-1': dict(add=[]),
    'rajasthani-2': dict(add=[('glow', 90 + i * 300 + 105, 560 + row * 520 - 130, 95) for row in range(2) for i in range(5)]),
    'rajasthani-3': dict(add=[]),
}
