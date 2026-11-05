"""Build fx.png / motion.png / anim.json for every painting and link them in catalog.json.

usage: python tools/paintings/build_animations.py [painting ids...]
"""
import json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import motifs
from compositions import PAINTINGS
from animations import EXTRAS
import fxmaps

OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'public', 'paintings'))


def build_procedural(pid, fn):
    motifs.reset_anchors()
    fn(random.Random(pid))                      # same seed as the render → identical positions
    anchors = list(motifs.ANCHORS)
    ex = EXTRAS.get(pid, {})
    anchors += ex.get('add', [])
    return fxmaps.build(os.path.join(OUT, pid), anchors, ex.get('protect', []), seed=sum(map(ord, pid)))


def link(catalog):
    for p in catalog['paintings']:
        d = os.path.join(OUT, p['id'])
        if os.path.exists(os.path.join(d, 'anim.json')):
            p['fx'] = f"/paintings/{p['id']}/fx.png"
            p['motion'] = f"/paintings/{p['id']}/motion.png"
            p['anim'] = f"/paintings/{p['id']}/anim.json"


if __name__ == '__main__':
    only = sys.argv[1:]
    for pid, cat, title, desc, med, fn in PAINTINGS:
        if only and pid not in only:
            continue
        a = build_procedural(pid, fn)
        print(pid, {k: len(v) for k, v in a.items() if isinstance(v, list)})
    cp = os.path.join(OUT, 'catalog.json')
    c = json.load(open(cp)); link(c); json.dump(c, open(cp, 'w'), indent=1, ensure_ascii=False)
