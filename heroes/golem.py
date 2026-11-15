"""Moss Golem, 32 px, facing right. A stocky little golem of grey stone, a rounded stone head
on a wide torso, yellow-green glowing eyes, moss patches on top of the head and on the
shoulders and a little pink flower sprouting on top. Thick stone arms with huge fists. The `running`
symbol is the stone punch: pulls the fist back, punches forward and the stone bursts into chips.
In `failed` he cracks into pebbles: the cracks spread, the front arm falls and he crumbles into a pile
of stones with the head on top.
The torso and head move together (only legs and arms change), so the add-ons' flower, nest and mushrooms
always stay in place. Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#141a14", "P": "#a39e93", "p": "#6e6a62", "l": "#cfc9bc", "k": "#3e3b36",
    "G": "#6cbf44", "g": "#3f8a2c", "E": "#e8ff8a", "R": "#ff7aa8", "r": "#c94a7a", "Y": "#ffd23f",
    "M": "#d8483a", "m": "#9a2c24", "W": "#ffffff", "D": "#9a6a3a", "d": "#634020", "B": "#bfe8ff",
    "T": "#8fd8ff", "Q": "#d8e0e8",
}

TRUNK = (5, 6, 7, 7, 7, 7, 6, 5)              # torso half-width per row (8 rows)
HEAD = (3, 4, 5, 5, 5, 5, 4)                 # head half-width per row (7 rows, above the torso)

FIST = [                                       # 7x7 stone fist
    ".KKKKK.",
    "KlPkPkK",
    "KPPkPkK",
    "KPPPPpK",
    "KPPPPpK",
    "KpPppkK",
    ".KKKKK.",
]
SPLINTERS = [                                      # the punch bursts: stone chips and dust
    "....K...K...",
    "...KlK.KPK..",
    "K..KPKKlK..K",
    "lK..KKKK..Kl",
    ".KK.KQQK.KK.",
    "..KKQWWQKK..",
    "KKPKQWWQKPKK",
    "..KKQQQQKK..",
    ".KK.KKKK.KK.",
    "pK.KPK.KlK.K",
    "K..KpK..KK..",
    "....K.......",
]
STREAK = ["QQQQ.", ".QQQQ", "QQQQ."]
PEBBLE = [".KK.", "KPlK", "KppK", ".KK."]
PEBBLE_S = ["KK", "Kp"]
LEAF = [".KK", "KGK", "Kg."]
MOUND = [                                       # pile of stones he crumbles into
    ".....KKK...KKKK.......",
    "...KKPlPK.KPPlPK.KKK..",
    "..KPPPPpKKPPPPpKKPlPK.",
    ".KPlPPpPKPPlPPPpKPPPpK",
    "KPPPpPPPKPPPPpPPKPpPPK",
    "KpPPPPpPPPPpPPPPPPPpPK",
    ".KKKKKKKKKKKKKKKKKKKK.",
]


def _arm(g, a, b, fist=True):
    """3 px stone arm from `a` (shoulder) to `b` (hand), with the huge fist at the tip."""
    px = {}
    for x, y in line(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1, 2):
                px[(x + dx, y + dy - 1)] = "p" if dy == 2 else "P"
    outline_cells(g, px)
    if fist:
        stamp(g, FIST, b[0] - 3, b[1] - 3)


def frame(cx=14, base=30, leg=3, seated=False, eye="n", feet=(0, 0), arms=(), por=(), crack=0, flor=True):
    """One 32x32 frame and the add-on anchor (8 to the left and 14 above the torso top).
    `leg`: leg height (0 = crouched); `seated`: crumbled on the ground, no legs;
    `arms`: ((shoulder), (hand)) with the back shoulder at (cx-6, t+1) and the front one at (cx+6, t+1);
    `crack`: 0 to 2, cracks in the stone; `flower`: False when the little flower fell off."""
    g = [["."] * N for _ in range(N)]
    t = (base - len(TRUNK) + 1) if seated else (base - leg - len(TRUNK))
    hx, h0 = cx + 1, t - len(HEAD)
    px = {}
    if not seated:
        for i, x0 in enumerate((cx - 5, cx + 2)):
            x = x0 + feet[i]
            for y in range(base - leg, base + 1):
                for x1 in range(x, x + 4):
                    px[(x1, y)] = "p" if i == 0 or x1 == x else "P"
    for r, w in enumerate(TRUNK):
        for x in range(cx - w, cx + w + 1):
            px[(x, t + r)] = "p" if x <= cx - w + 1 else "P"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "p" if x <= hx - w + 1 else "P"
    for x, y in ((cx + 2, t + 3), (cx + 4, t + 5), (cx - 2, t + 6), (hx + 3, h0 + 5)):   # light speckles
        px[(x, y)] = "l"
    for x in range(hx - 3, hx + 4):              # moss on top of the head
        px[(x, h0)] = "G"
        px[(x, h0 + 1)] = "G" if x % 3 else "g"
    for x in (hx - 5, hx + 5):
        px[(x, h0 + 2)] = "g"
    for x in list(range(cx - 5, cx - 1)) + list(range(cx + 3, cx + 6)):   # moss on the shoulders
        px[(x, t)] = "G"
        px[(x, t + 1)] = "g" if x % 2 else "G"
    if flor:                                      # little flower on top
        px[(hx + 1, h0 - 1)] = "g"
        for x, y in ((hx, h0 - 2), (hx + 2, h0 - 2), (hx + 1, h0 - 3)):
            px[(x, y)] = "R"
        px[(hx + 1, h0 - 2)] = "Y"
    outline_cells(g, px)
    # face: glowing eyes in a dark groove and the crack mouth
    ey = h0 + 3
    eyes = {"n": (["EE", "Ek"], ["EE", "Ek"]), "closed": (["..", "kk"], ["..", "kk"]),
             "happy": ([".E", "E."], [".E", "E."]), "x": (["k.k", ".k.", "k.k"], ["k.k", ".k.", "k.k"]),
             "angry": (["E.", "EE"], [".E", "EE"]), "up": (["Ek", "kk"], ["Ek", "kk"]),
             "sad": (["EE", "k."], ["EE", ".k"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 2 - (len(back[0]) > 2), ey - (len(back) > 2))
    stamp(g, front, hx + 2, ey - (len(front) > 2))
    for x in range(hx, hx + 3):
        g[h0 + 5][x] = "k"
    if eye == "sad":
        stamp(g, TEAR, hx - 2, ey + 2)
    if crack:                                     # cracks
        for x, y in ((cx - 1, t + 1), (cx, t + 2), (cx, t + 3), (cx + 1, t + 4), (cx + 1, t + 5), (cx + 2, t + 6)):
            g[y][x] = "K"
    if crack > 1:
        for x, y in ((hx - 1, h0 + 1), (hx - 1, h0 + 2), (hx - 2, h0 + 3), (cx - 4, t + 3), (cx - 3, t + 4),
                     (cx + 4, t + 2), (cx + 5, t + 3), (cx - 4, t + 5)):
            g[y][x] = "K"
    for a, b in arms:
        _arm(g, a, b)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 14)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, leg=3 -> torso 19-26 (cx=14), head 12-18 (hx=15), flower 9-11; shoulders at (8, 20) and (20, 20)
_FALLEN = (((8, 20), (5, 26)), ((20, 20), (23, 26)))      # arms hanging, fists on the ground from being so heavy
_SPECS = {
    # breathes slowly, blinks, a little moss leaf falls
    "idle": [dict(arms=_FALLEN),
             dict(arms=(((8, 20), (5, 25)), ((20, 20), (23, 25)))),
             dict(arms=_FALLEN, por=((LEAF, 26, 12),)),
             dict(eye="closed", arms=_FALLEN, por=((LEAF, 27, 17),)),
             dict(arms=(((8, 20), (5, 25)), ((20, 20), (23, 25))))],
    # walks heavily: legs alternating, arms swinging
    "run_r": [dict(feet=(-2, 2), arms=(((8, 20), (4, 25)), ((20, 20), (25, 23)))),
              dict(base=29, arms=(((8, 20), (5, 26)), ((20, 20), (23, 26)))),
              dict(feet=(2, -2), arms=(((8, 20), (6, 26)), ((20, 20), (22, 25)))),
              dict(base=29, arms=(((8, 20), (5, 26)), ((20, 20), (23, 26))))],
    # waves high with the front fist
    "waving": [dict(eye="happy", arms=(_FALLEN[0], ((20, 20), (26, 12)))),
               dict(eye="happy", arms=(_FALLEN[0], ((20, 20), (23, 9)))),
               dict(eye="happy", arms=(_FALLEN[0], ((20, 20), (27, 13))), por=((LEAF, 28, 4),)),
               dict(eye="happy", arms=(_FALLEN[0], ((20, 20), (23, 9))))],
    # crouches, jumps with fists up, comes down, lands
    "jumping": [dict(leg=0, eye="closed", arms=(((8, 23), (5, 28)), ((20, 23), (23, 28)))),
                dict(base=28, eye="up", arms=(((8, 18), (4, 15)), ((20, 18), (25, 12)))),
                dict(base=26, eye="happy", arms=(((8, 16), (4, 12)), ((20, 16), (26, 9)))),
                dict(base=28, arms=(((8, 18), (4, 19)), ((20, 18), (25, 18)))),
                dict(leg=0, eye="happy", arms=(((8, 23), (5, 28)), ((20, 23), (23, 28))))],
    # cracks into pebbles: cracks spread, the front arm falls, crumbles into a pile of stones
    "failed": [dict(eye="sad", crack=1, arms=_FALLEN, por=((PEBBLE_S, 26, 22),)),
               dict(eye="x", crack=2, arms=(_FALLEN[0],),
                    por=((FIST, 24, 25), (PEBBLE, 26, 15), (PEBBLE_S, 3, 17), (PEBBLE_S, 22, 10))),
               dict(eye="x", crack=2, seated=True, arms=(((8, 24), (5, 28)),),
                    por=((MOUND, 5, 25), (FIST, 25, 25), (PEBBLE, 1, 16), (PEBBLE, 27, 13))),
               dict(eye="x", crack=2, seated=True, flor=False, arms=(((8, 24), (5, 28)),),
                    por=((MOUND, 5, 25), (FIST, 25, 25), (PEBBLE_S, 1, 24), (PEBBLE, 27, 20))),
               dict(eye="x", crack=2, seated=True, flor=False, arms=(((8, 24), (5, 28)),),
                    por=((MOUND, 5, 25), (FIST, 25, 25), (PEBBLE, 27, 26)))],
    # naps standing, fists on the ground, "z" rising
    "waiting": [dict(eye="closed", arms=_FALLEN),
                dict(eye="closed", arms=_FALLEN, por=((Z_S, 23, 6),)),
                dict(eye="closed", arms=_FALLEN, por=((Z_S, 22, 7), (Z_L, 25, 0))),
                dict(eye="closed", arms=_FALLEN, por=((Z_L, 25, 0),))],
    # stone punch: pulls the fist back, punches forward, the stone bursts into chips
    "running": [dict(cx=11, eye="angry", arms=(((5, 20), (3, 25)), ((17, 20), (20, 9)))),
                dict(cx=11, eye="angry", arms=(((5, 20), (3, 25)), ((17, 20), (24, 20))),
                     por=((STREAK, 19, 14), (STREAK, 18, 24))),
                dict(cx=11, eye="angry", arms=(((5, 20), (3, 25)), ((17, 20), (22, 20))),
                     por=((SPLINTERS, 20, 12), (FIST, 19, 17))),
                dict(cx=11, eye="happy", arms=(((5, 20), (3, 25)), ((17, 20), (22, 22))),
                     por=((PEBBLE, 27, 12), (PEBBLE_S, 29, 24), (PEBBLE_S, 24, 9)))],
    # fist on the chin, "?" appears
    "review": [dict(eye="up", arms=(_FALLEN[0], ((20, 20), (21, 18)))),
               dict(eye="up", arms=(_FALLEN[0], ((20, 20), (21, 18))), por=((QMARK_S, 25, 3),)),
               dict(eye="up", arms=(_FALLEN[0], ((20, 20), (21, 18))), por=((QMARK, 25, 1),)),
               dict(eye="n", arms=(_FALLEN[0], ((20, 20), (21, 18))), por=((QMARK, 25, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# 18x14 grid attached 8 to the left and 14 above the torso top (head from row 7, center on column 9):
# big flower sprouting from the top; on the Elder, a nest with a little egg behind the flower and mushrooms on the nape
_FLOWER = [                                      # big 5-petal flower with a leaf on the stem
    "..KKK..",
    ".KRRRK.",
    "KRRYRRK",
    "KrRYRrK",
    ".KrRrK.",
    "KKKgKK.",
    "KGGgK..",
    ".KKgK..",
]
_NEST = [
    "...KKK...",
    "..KBBWK..",
    "KKKBBBKKK",
    "KdDdDdDdK",
    ".KDdDdDK.",
    "..KKKKK..",
]
_MUSHROOMS = [                                 # two red mushrooms with white spots
    ".KKK..",
    "KMWMK.",
    "KmMmKK",
    ".KQKMK",
    ".KQKmK",
    ".KKKQK",
    "...KKK",
]


def _extra(pieces, w=18, h=14):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


FLOWER = _extra(((_FLOWER, 8, 1),))
ELDER = _extra(((_NEST, 1, 4), (_MUSHROOMS, 0, 7), (_FLOWER, 8, 1)))
STAGES = [
    {"title": "Pebble", "floor": 1, "extra": None},
    {"title": "Moss Golem", "floor": 4, "extra": FLOWER},
    {"title": "Elder Golem", "floor": 10, "extra": ELDER},
]
