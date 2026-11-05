"""Assemble public/paintings/catalog.json from all sources and link animation assets.

Sources: procedural paintings (compositions.py), premium rangolis (rangoli_premium.py) and
imported artwork already in the catalog (Skets Studio, future AI paintings). Category order comes
from compositions.CATEGORIES. Paintings whose category no longer exists are dropped.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from compositions import PAINTINGS, CATEGORIES
from rangoli_premium import RANGOLIS

OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'public', 'paintings'))


def entry(pid, cat, title, desc, med):
    e = {'id': pid, 'category': cat, 'title': title, 'description': desc, 'medium': med}
    for k in ('albedo', 'height', 'preview', 'thumb'):
        e[k] = f'/paintings/{pid}/{k}.jpg'
    return e


def main():
    cp = os.path.join(OUT, 'catalog.json')
    old = json.load(open(cp)) if os.path.exists(cp) else {'paintings': []}
    generated = {p[0] for p in PAINTINGS} | {r[0] for r in RANGOLIS}
    cats = [c for c, _, _ in CATEGORIES]
    paintings = [entry(*p[:5]) for p in PAINTINGS + RANGOLIS if p[1] in cats]  # removed categories are dropped
    REPLACED = {'rangoli-1', 'rangoli-2', 'rangoli-3'}  # old basic rangolis, replaced by the premium set
    paintings += [p for p in old['paintings'] if p['id'] not in generated and p['id'] not in REPLACED
                  and p['category'] in cats and os.path.exists(os.path.join(OUT, p['id'], 'albedo.jpg'))]  # imported art
    for p in paintings:
        d = os.path.join(OUT, p['id'])
        if os.path.exists(os.path.join(d, 'anim.json')):
            p['fx'], p['motion'], p['anim'] = (f"/paintings/{p['id']}/{n}" for n in ('fx.png', 'motion.png', 'anim.json'))
        if os.path.exists(os.path.join(d, 'animated.mp4')):   # optional pre-rendered animated version
            p['video'] = f"/paintings/{p['id']}/animated.mp4"
    order = {c: i for i, c in enumerate(cats)}
    imported_order = {p['id']: i for i, p in enumerate(old['paintings'])}
    paintings.sort(key=lambda p: (order[p['category']], imported_order.get(p['id'], -1)))
    cat = {'version': 2, 'canvasAspect': '4:3',
           'categories': [{'id': c, 'name': n, 'description': d} for c, n, d in CATEGORIES],
           'paintings': paintings}
    json.dump(cat, open(cp, 'w'), indent=1, ensure_ascii=False)
    missing = [p['id'] for p in paintings if not os.path.exists(os.path.join(OUT, p['id'], 'albedo.jpg'))]
    noanim = [p['id'] for p in paintings if 'anim' not in p]
    print(f'{len(paintings)} paintings in {len(CATEGORIES)} categories; missing images: {missing}; without animation: {noanim}')


if __name__ == '__main__':
    main()
