import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("tkinter", __import__("types").ModuleType("tkinter"))
import tokenlike as tp
import art
import visual as V

SLIME_16_PAL = {
    "K": "#1b1b2f", "G": "#57d36b", "L": "#b4f5a8", "D": "#2f9a4a",
    "W": "#ffffff", "B": "#1b1b2f", "P": "#ff8fb1",
    "S": "#d7dde9", "s": "#8a94a8", "R": "#e2384d", "Y": "#ffd23f", "y": "#c99a00",
    "T": "#8fd8ff",   # tear, thought drops and the sleep "z"
}
SLIME_16 = [
    "................",
    "................",
    "................",
    "......KKKK......",
    "....KKLLGGKK....",
    "...KLLGGGGGGK...",
    "..KLGGGGGGGGGK..",
    "..KLGGGGGGGGGK..",
    ".KGGGWWGGWWGGGK.",
    ".KGGGWBGGWBGGGK.",
    ".KGPPGGGGGGPPGK.",
    ".KGGGGGKKGGGGGK.",
    ".KGGGGGGGGGGGGK.",
    ".KDGGGGGGGGGGDK.",
    "..KDDDDDDDDDDK..",
    "...KKKKKKKKKK...",
]
slime = V.grid_to_map(SLIME_16, SLIME_16_PAL)
assert V.bbox(slime) == (1, 3, 15, 16), V.bbox(slime)
assert V.grid_to_map(["A.", ".B"], {"A": "#111111"}) == {(0, 0): "#111111"}  # skips '.' and letters without a color

# any map (community PNG): 6x10 rectangle with a dark border and arbitrary colors
other = {(x, y): ("#1b1b2f" if x in (0, 5) or y in (0, 9) else ("#c0ffee" if (x + y) % 2 else "#ba5e11"))
         for x in range(6) for y in range(10)}

for pm in (slime, other):
    pm_original = dict(pm)
    x0, y0, x1, y1 = V.bbox(pm)
    e = V.thorns(pm, "#e2384d"); assert V.bbox(e)[1] < y0 and len(e) > len(pm)
    g = V.drops(pm, "#4fbf5a"); assert V.bbox(g)[3] > y1
    c = V.contour(pm, "#ffd23f"); assert all(p in c for p in pm) and len(c) > len(pm)
    assert all(c[p] == "#ffd23f" for p in c if p not in pm)
    t = V.tint(pm, "#9b6ad6", 0.5); assert t.keys() == pm.keys()
    assert all(t[p] == pm[p] for p in pm if pm[p] == "#1b1b2f")      # dark outline intact
    assert any(t[p] != pm[p] for p in pm)
    assert V.thorns(pm, "#e2384d", 2) != e                          # a higher level reinforces it
    assert V.drops(pm, "#4fbf5a", 2) != g
    assert pm == pm_original                                          # the input does not change

# objects at the same anchor do not fully overlap
art_obj = V.grid_to_map(art.ITEM_ART["horns"], art.PAL)
a = V.place_object(slime, art_obj, "top", 0); b = V.place_object(a, art_obj, "top", 1)
assert V.bbox(b)[1] < V.bbox(a)[1]
# glow: pixels next to the object in the rarity color
gl = V.place_object(slime, art_obj, "right", 0, glow="#6fd6ff"); assert "#6fd6ff" in gl.values()
# sticker in the center of the map
ad = V.sticker(slime, {(0, 0): "#ff00ff"}, (0.5, 0.5)); assert "#ff00ff" in ad.values()
# every anchor changes the map
for anc in ("top", "left", "right", "front", "base", "float"):
    for o in (0, 5):
        assert V.place_object(slime, art_obj, anc, o) != slime, anc
# order 1 does not fully hide the order 0 object
for anc in ("top", "left", "right", "front", "base", "float"):
    o0 = V.place_object(slime, art_obj, anc, 0); o1 = V.place_object(o0, art_obj, anc, 1)
    assert o1 != o0 and V.place_object(slime, art_obj, anc, 1) != o0, anc
    n0 = {p for p in o0 if o0[p] != slime.get(p)}; n1 = {p for p in o1 if o1[p] != o0.get(p)}
    assert n1 and n1 != n0, anc
# compose + crop: the max box is respected with many objects
looks = [({"type": "obj", "anchor": "top", "art": "horns"}, None)] * 12
pm2 = V.crop(V.compose(slime, looks, {"horns": art_obj}), V.LOOK_BOX)
bx0, by0, bx1, by1 = V.bbox(pm2)
assert bx0 >= V.LOOK_BOX[0] and by0 >= V.LOOK_BOX[1] and bx1 <= V.LOOK_BOX[2] and by1 <= V.LOOK_BOX[3]
assert V.compose(slime, [], {}) == slime
# compose of mutations
mut = V.compose(slime, [({"type": "thorns", "color": "#e2384d"}, None),
                        ({"type": "tint", "color": "#9b6ad6", "amount": 0.3}, None)], {})
assert V.bbox(mut)[1] < V.bbox(slime)[1]
for kind, fn in (("thorns", V.thorns), ("drops", V.drops)):
    lk = ({"type": kind, "color": "#e2384d"}, None)
    assert V.compose(slime, [lk] * 2, {}) == fn(slime, "#e2384d", 2), kind
# all items of dungeon.ITEMS together: the newest at each anchor shows whole inside LOOK_BOX
import dungeon as M
arts = {k: V.grid_to_map(g, art.PAL) for k, g in art.ITEM_ART.items()}
all_ = [(it["look"], None) for it in M.ITEMS.values()]
full = V.compose(slime, all_, arts)
inside = lambda p: V.LOOK_BOX[0] <= p[0] < V.LOOK_BOX[2] and V.LOOK_BOX[1] <= p[1] < V.LOOK_BOX[3]
for anc in {l["anchor"] for l, _ in all_ if l["type"] == "obj"}:
    i = max(j for j, (l, _) in enumerate(all_) if l.get("anchor") == anc)
    no_elem = V.compose(slime, all_[:i] + all_[i + 1:], arts)
    new = {p for p in full if full[p] != no_elem.get(p)}
    assert new and all(inside(p) for p in new), (anc, all_[i][0]["art"], [p for p in new if not inside(p)])
# beyond capacity, the oldest at the anchor disappears (12 hats: only the last ones fit)
hat = ({"type": "obj", "anchor": "top", "art": "hat"}, None)
candle = ({"type": "obj", "anchor": "top", "art": "candle"}, None)
assert V.compose(slime, [candle] + [hat] * 12, arts) == V.compose(slime, [hat] * 12, arts)
assert V.compose(slime, [candle], arts) != slime                        # alone it shows
# few items: nothing changes (two at one anchor that fit both stay)
dagger = ({"type": "obj", "anchor": "right", "art": "dagger"}, None)
bx = V.bbox(slime)
assert V.compose(slime, [dagger] * 2, arts) == V._place(V._place(slime, arts["dagger"], bx, "right", 0, None),
                                                         arts["dagger"], bx, "right", 1, None)
# animated elemental looks: 3 different frames, body preserved (frost recolors the border), pure
for fn in (V.flames, V.sparks, V.poison_drops, V.frost):
    for pm in (slime, other):
        copy = dict(pm)
        frames = [fn(pm, 1, f) for f in range(V.PHASES)]
        assert len({tuple(sorted(f.items())) for f in frames}) == V.PHASES, fn.__name__
        assert all(set(pm) <= set(f) or fn is V.frost for f in frames), fn.__name__
        assert pm == copy, fn.__name__
        assert fn(pm, 2, 0) != fn(pm, 1, 0), fn.__name__
lk = [({"type": "flames"}, None)]
assert V.has_anim(lk) and not V.has_anim([({"type": "obj", "anchor": "top", "art": "horns"}, None)])
c0, c1 = V.crop(V.compose(slime, lk, {}, phase=0), V.LOOK_BOX), V.crop(V.compose(slime, lk, {}, phase=1), V.LOOK_BOX)
assert c0 != c1 and V.compose(slime, [], {}, phase=2) == slime
# objects do not depend on the phase (fixed anchor box)
_arts = {k: V.grid_to_map(g, art.PAL) for k, g in art.ITEM_ART.items()}
_lk = [({"type": "flames"}, None), ({"type": "poison_drops"}, None),
       ({"type": "obj", "anchor": "top", "art": "hat"}, None), ({"type": "obj", "anchor": "base", "art": "dagger"}, None)]
_obj = [l for l in _lk if l[0]["type"] == "obj"]
_without = V.compose(slime, _obj, _arts)
for f in range(V.PHASES):
    _c = V.compose(slime, _lk, _arts, phase=f)
    assert all(_c.get(p) == c for p, c in _without.items() if p not in slime), f   # objects on the same pixels and colors
# drops fall 1 px per phase: frame 1 is frame 0 shifted (except the return to the top)
_g = [{p for p in V.poison_drops(slime, 1, f) if p not in slime} for f in range(3)]
assert _g[0] != _g[1] != _g[2] and any((x, y + 1) in _g[1] for x, y in _g[0])
# R11: an elemental item without an animated look still shows the element (derived look, once per element)
import dungeon as M
_run = M.new_run("slime", {}, 1)
_run["items"] = [{"key": "torch", "rar": "common"}]
_pl = tp.pet_looks(_run)
assert [l["type"] for l, _ in _pl].count("flames") == 1
assert len({tuple(sorted(V.compose(slime, _pl, _arts, phase=f).items())) for f in range(V.PHASES)}) == V.PHASES
_run["items"] = [{"key": "ember", "rar": "common"}, {"key": "torch", "rar": "common"}]
assert [l["type"] for l, _ in tp.pet_looks(_run)].count("flames") == 1        # ember already has flames: does not double
_run["items"] = [{"key": "ember", "rar": "common"}, {"key": "singed_fur", "rar": "rare"}]
assert [l["type"] for l, _ in tp.pet_looks(_run)].count("flames") == 2        # explicit ones keep the level
_run["items"] = []
assert tp.pet_looks(_run) == []
# scale k: k=1 the same; 48x48 body with k=3 -> object 3x wider, same support between phases
assert V.look_box(1) == V.LOOK_BOX and V.look_box(3) == (-24, -30, 72, 60)
_top = [({"type": "obj", "anchor": "top", "art": "hat"}, None)]
assert V.compose(slime, _top, _arts, k=1) == V.compose(slime, _top, _arts)
_big = {(x, y): "#aa5522" for x in range(48) for y in range(48)}
def _width(m, b):
    x0, _, x1, _ = V.bbox({p: c for p, c in m.items() if p not in b}); return x1 - x0
_w1 = _width(V.compose(slime, _top, _arts), slime)
_w3 = _width(V.compose(_big, _top, _arts, k=3), _big)
assert _w3 == 3 * _w1, (_w1, _w3)
_cen = lambda m, b: (lambda bb: (bb[0] + bb[2]) / 2)(V.bbox({p: c for p, c in m.items() if p not in b}))
assert _cen(V.compose(_big, _top, _arts, k=3), _big) == 24 and _cen(V.compose(slime, _top, _arts), slime) == 8
_lk3 = _top + [({"type": "flames"}, None)]
_s3 = [V.compose(_big, _lk3, _arts, f, 3) for f in range(V.PHASES)]
assert all(all(m.get(p) == c for p, c in V.compose(_big, _top, _arts, k=3).items() if p not in _big) for m in _s3)
# object glow scales with k: 3 px ring at k=3, 1 px at k=1
_gl = "#ffd700"
for _k, _b in ((1, slime), (3, _big)):
    _o = {p: c for p, c in V.compose(_b, _top, _arts, k=_k).items() if p not in _b}
    _m2 = V.compose(_b, [(_top[0][0], _gl)], _arts, k=_k)
    _ring = {p for p, c in _m2.items() if c == _gl}
    _a = V.bbox({p for p in _o}); _a2 = V.bbox(_ring)
    assert _a2[1] == _a[1] - _k and _a2[0] == _a[0] - _k, (_k, _a, _a2)
# float: the glow k must not be overridden by the position (order>=4 at k=1; order 0 at k=3)
for _k, _b, _ord in ((1, slime, 4), (3, _big, 0)):
    _art = V.scale(_arts["hat"], _k)
    _without = V._place(dict(_b), _art, V.bbox(_b), "float", _ord, None, _k)
    _com = V._place(dict(_b), _art, V.bbox(_b), "float", _ord, _gl, _k)
    _nov = {p for p in _com if p not in _without}
    _ba, _bn = V.bbox({p for p in _without if p not in _b}), V.bbox(_nov)
    assert _bn[0] == _ba[0] - _k and _bn[3] == _ba[3] + _k, (_k, _ord, _ba, _bn)
print("ok: visual")

# hole inside the silhouette (the ghost's fading checkerboard) is not painted by outline/sparks/frost
ring = {(x, y): "#ffffff" for x in range(5) for y in range(5) if (x, y) != (2, 2)}
assert (2, 2) not in V.contour(ring, "#ff0000")
assert all((2, 2) not in V.sparks(ring, 4, f) for f in range(3))
assert all(V.frost(ring, 3, f)[(2, 1)] == "#ffffff" for f in range(3))
assert (-1, 0) in V.contour(ring, "#ff0000")              # the outside stays the same
print("ok: inner hole")
