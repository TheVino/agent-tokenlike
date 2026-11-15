"""Scarecrow, 32 px, facing right. A little scarecrow with a burlap sack head (button eyes and stitched
mouth), a wide-brimmed straw hat with a red ribbon, a blue shirt full of patches, brown trousers and tufts of
straw coming out of the neck, sleeves, hem and feet. Standing he keeps his arms wide open (the scarecrow pose);
the `running` symbol is the scythe: winds up high, strikes and releases a half-moon cut with straw flying.
In `failed` he falls apart into straw: the straw escapes from the sleeves, the hat flies off and he sinks into a pile of straw.
The torso and head move together (only legs and arms change), so the add-ons' little crow on the shoulder and pumpkin
lantern always stay in place. Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#1a1410", "S": "#dcbc8c", "s": "#a9875a", "Y": "#f5d35e", "y": "#c3922c",
    "C": "#5b86d0", "c": "#3c5c9a", "R": "#d0473c", "G": "#6fb44c", "D": "#8a5a32", "d": "#5e3a20",
    "k": "#4a3628", "W": "#ffffff", "Q": "#d8e0e8", "q": "#8e9aa6", "O": "#f08a24", "o": "#b0541a",
    "L": "#ffe680", "A": "#ff9a3c", "T": "#8fd8ff", "V": "#6a5a86", "v": "#43385a",
}

SHIRT = (4, 4, 5, 5, 5, 6, 6, 6)              # shirt half-width per row (8 rows)

SCYTHE = [                                       # handle at the bottom left, curved blade over the top and forward
    "..KKKKK..",
    ".KQQWWWK.",
    "KQKKKKKWK",
    "KQK...KWK",
    "KQK...KWK",
    "KDK....K.",
    "KDK......",
    "KDK......",
    ".K.......",
]


def _rotate(s):
    """Rotates the sprite 90 degrees clockwise."""
    return ["".join(s[len(s) - 1 - r][c] for r in range(len(s))) for c in range(len(s[0]))]


SCYTHE_FRONT = _rotate(SCYTHE)                   # handle back, blade in front pointing down
CUT = [                                       # half-moon of the attack
    "...KKKK.....",
    "..KWWWWKK...",
    "...KKKWWWK..",
    "......KKWWK.",
    ".......KKWWK",
    "........KWWK",
    "........KWWK",
    ".......KKWWK",
    "......KKWWK.",
    "...KKKWWWK..",
    "..KWWWWKK...",
    "...KKKK.....",
]
STRAW = ["KKK...", "KYYKK.", ".KKYYK", "...KKK"]   # flying straw wisp
STRAW_V = ["KK.", "KYK", "KYK", ".KK"]
STREAK = ["QQQ.", ".QQQ", "QQQ."]
MOUND = [                                       # pile of straw he sinks into
    "....KK.K..KK.K....",
    "..KKYYKYKKYYKYKK..",
    ".KYYyYYYYYYyYYYYK.",
    "KYyYYYyYYyYYYYyYYK",
    "KYYYyYYYYYYYyYYYYK",
    ".KKKKKKKKKKKKKKKK.",
]
HAT = [                                      # fallen hat, on its side on the ground
    "....KKKKK....",
    "...KYYYYYK...",
    "..KYYYYYYYK..",
    "..KRRRRRRRK..",
    "KKYYYYYYYYYKK",
    "KYYyYYYYYyYYK",
    ".KKKKKKKKKKK.",
]
HAT_FLYING = [                               # hat spinning in the air
    "...KKKK...",
    "..KYYYYK..",
    ".KKRRRRKK.",
    "KYYYYYYYYK",
    ".KKyYYyKK.",
    "...KKKK...",
]
HAND = [".K.K.", "KYKYK", "KYYYK", "KYyYK", ".KKK."]   # straw tuft hand


def _arm(g, a, b, hand=True):
    """2 px shirt sleeve from `a` (shoulder) to `b` (hand), with the straw tuft at the tip."""
    px = {}
    for x, y in line(*a, *b):
        px[(x, y)] = px[(x, y + 1)] = "C"
    outline_cells(g, px)
    if hand:
        stamp(g, HAND, b[0] - 2, b[1] - 2)


def frame(cx=13, base=30, leg=3, seated=False, eye="n", feet=(0, 0), arms=(), scythe=None, por=(),
           hat=True):
    """One 32x32 frame and the add-on anchor (8 to the left and 12 above the shirt top).
    `leg`: leg height (0 = crouched); `seated`: sunk into the ground, no legs;
    `arms`: ((shoulder), (hand)) with the back shoulder at (cx-4, t+1) and the front one at (cx+4, t+1);
    `scythe`: (sprite, x, y) drawn over the hand; `hat`: False when the hat fell off the head."""
    g = [["."] * N for _ in range(N)]
    t = (base - len(SHIRT) + 1) if seated else (base - leg - len(SHIRT))
    hx, hy = cx + 1, t - 4
    px = {}
    if not seated:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + feet[i]
            for y in range(base - leg, base):
                px[(x, y)] = "D" if i else "d"
                px[(x + 1, y)] = "D" if i else "d"
            for x1 in range(x - 1, x + 3):          # straw foot
                px[(x1, base)] = "Y" if x1 % 2 else "y"
    for r, w in enumerate(SHIRT):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "c" if x <= cx - w + 1 else "C"
    for x in range(cx - 5, cx + 7, 2):               # straw sticking out of the hem
        px[(x, t + len(SHIRT))] = "Y"
    for x in range(hx - 4, hx + 5):
        for y in range(hy - 4, hy + 5):
            if (x - hx) ** 2 + (y - hy) ** 2 <= 21:
                px[(x, y)] = "s" if x <= hx - 3 else "S"
    for x in (hx - 2, hx, hx + 2):                   # neck straw
        px[(x, hy + 5)] = "Y"
    if hat:
        for x in range(hx - 7, hx + 7):              # brim
            px[(x, hy - 3)] = "Y"
        px[(hx - 8, hy - 2)] = px[(hx + 7, hy - 2)] = "y"
        for i, (a, b) in enumerate(((-4, 4), (-4, 3), (-3, 3), (-2, 2))):   # crown
            for x in range(hx + a, hx + b + 1):
                px[(x, hy - 4 - i)] = "R" if i == 0 else ("y" if x == hx + a else "Y")
    outline_cells(g, px)
    # patches and the waist cord
    stamp(g, ["RRR", "RkR", "RRR"], cx - 3, t + 2)
    stamp(g, ["GG", "GG"], cx + 3, t + 5)
    for x in range(cx - 5, cx + 6):
        if g[t + 4][x] in "Cc":
            g[t + 4][x] = "y"
    # face: button eyes and stitched mouth
    eyes = {"n": (["KK", "KW"], ["KK", "KW"]), "fechado": (["..", "kk"], ["..", "kk"]),
             "feliz": ([".k", "k."], [".k", "k."]), "x": (["K.K", ".K.", "K.K"], ["K.K", ".K.", "K.K"]),
             "bravo": (["K.", "KK"], [".K", "KK"]), "cima": (["KW", "KK"], ["KW", "KK"]),
             "triste": (["KK", "K."], ["KK", ".K"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 1 - (len(back[0]) > 2), hy - 1 - (len(back) > 2))
    stamp(g, front, hx + 2, hy - 1 - (len(front) > 2))
    g[hy + 2][hx] = g[hy + 2][hx + 3] = "k"       # little stitched smile
    g[hy + 3][hx + 1] = g[hy + 3][hx + 2] = "k"
    if eye == "triste":
        stamp(g, TEAR, hx - 1, hy + 1)
    for a, b in arms:
        _arm(g, a, b)
    if scythe:
        stamp(g, *scythe)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, leg=3 -> shirt 19-26 (cx=13), head 11-19 (hx=14), hat 7-12; shoulders at (9, 20) and (17, 20)
_OPEN = (((9, 20), (3, 20)), ((17, 20), (25, 20)))     # arms wide open, the scarecrow pose
_FALLEN = (((9, 20), (7, 26)), ((17, 20), (19, 26)))      # arms hanging
_SPECS = {
    # arms wide open; the hand straw sways, a wisp falls and he blinks
    "idle": [dict(arms=_OPEN),
             dict(arms=(((9, 20), (3, 21)), ((17, 20), (25, 19)))),
             dict(arms=_OPEN, por=((STRAW_V, 25, 23),)),
             dict(eye="fechado", arms=(((9, 20), (3, 19)), ((17, 20), (25, 21))), por=((STRAW_V, 26, 26),)),
             dict(arms=_OPEN)],
    # runs clumsily: legs alternating, arms swinging
    "run_r": [dict(feet=(-2, 2), arms=(((9, 20), (4, 23)), ((17, 20), (23, 17)))),
              dict(base=29, arms=(((9, 20), (5, 20)), ((17, 20), (23, 21)))),
              dict(feet=(2, -2), arms=(((9, 20), (4, 17)), ((17, 20), (22, 24)))),
              dict(base=29, arms=(((9, 20), (5, 20)), ((17, 20), (23, 21))))],
    # waves high with the front hand, straw flying from the hand
    "waving": [dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (24, 13)))),
               dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (21, 9)))),
               dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (26, 11))), por=((STRAW, 25, 3),)),
               dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (21, 9))))],
    # crouches, jumps with arms up, comes down, lands
    "jumping": [dict(leg=0, eye="fechado", arms=(((9, 23), (4, 26)), ((17, 23), (22, 26)))),
                dict(base=28, eye="cima", arms=(((9, 18), (4, 13)), ((17, 18), (23, 13)))),
                dict(base=26, eye="feliz", arms=(((9, 16), (3, 10)), ((17, 16), (24, 10)))),
                dict(base=28, arms=(((9, 18), (3, 18)), ((17, 18), (24, 18)))),
                dict(leg=0, eye="feliz", arms=(((9, 23), (4, 26)), ((17, 23), (22, 26))))],
    # the straw escapes from the sleeves, the hat flies off and he sinks into a pile of straw
    "failed": [dict(eye="triste", arms=_FALLEN, por=((STRAW_V, 5, 27), (STRAW_V, 20, 27))),
               dict(eye="x", hat=False, arms=(((9, 21), (5, 27)), ((17, 21), (21, 27))),
                    por=((HAT_FLYING, 18, 1), (STRAW, 1, 23), (STRAW, 23, 22))),
               dict(eye="x", seated=True, hat=False, arms=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MOUND, 5, 26), (HAT, 19, 3), (STRAW, 0, 14), (STRAW, 25, 13))),
               dict(eye="x", seated=True, hat=False, arms=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MOUND, 5, 26), (HAT, 19, 11), (STRAW_V, 2, 20))),
               dict(eye="x", seated=True, hat=False, arms=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MOUND, 5, 26), (HAT, 19, 25)))],
    # naps standing, arms hanging, "z" rising
    "waiting": [dict(eye="fechado", arms=_FALLEN),
                dict(eye="fechado", arms=_FALLEN, por=((Z_S, 23, 7),)),
                dict(eye="fechado", arms=_FALLEN, por=((Z_S, 22, 8), (Z_L, 25, 0))),
                dict(eye="fechado", arms=_FALLEN, por=((Z_L, 25, 0),))],
    # scythe: winds up high behind the head, strikes forward, a half-moon cut with straw flying
    "running": [dict(cx=11, eye="bravo", arms=(((7, 20), (3, 23)), ((15, 20), (19, 10))),
                     scythe=(SCYTHE, 18, 2)),
                dict(cx=11, eye="bravo", arms=(((7, 20), (3, 23)), ((15, 20), (22, 16))),
                     scythe=(_rotate(SCYTHE), 21, 10), por=((STREAK, 21, 4),)),
                dict(cx=11, eye="bravo", arms=(((7, 20), (3, 23)), ((15, 20), (21, 20))),
                     scythe=(SCYTHE_FRONT, 20, 19), por=((CUT, 20, 6), (STRAW, 25, 2))),
                dict(cx=11, eye="feliz", arms=(((7, 20), (3, 23)), ((15, 20), (20, 23))),
                     scythe=(SCYTHE_FRONT, 19, 22), por=((STRAW, 24, 8), (STRAW_V, 28, 14)))],
    # hand on the chin, "?" appears
    "review": [dict(eye="cima", arms=(_FALLEN[0], ((17, 20), (20, 17)))),
               dict(eye="cima", arms=(_FALLEN[0], ((17, 20), (20, 17))), por=((QMARK_S, 24, 3),)),
               dict(eye="cima", arms=(_FALLEN[0], ((17, 20), (20, 17))), por=((QMARK, 24, 1),)),
               dict(eye="n", arms=(_FALLEN[0], ((17, 20), (20, 17))), por=((QMARK, 24, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# 16x21 grid attached 8 to the left and 12 above the shirt top (shirt from row 12, center on column 8):
# little crow sitting on the back shoulder (rows 7-12) and a pumpkin lantern hanging from the back hip
_CROW = [                                     # little crow with dark feathers, orange beak touching the head
    "..KK..",
    ".KVVK.",
    "KVVWKK",
    "KvVVKA",
    "KvvVVK",
    ".KKKK.",
]
_LANTERN = [
    "...K...",
    "..KGK..",
    ".KKKKK.",
    "KOLOLOK",
    "KOOOOOK",
    "KoLLLoK",
    ".KKKKK.",
]


def _extra(pieces, w=16, h=21):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CROW = _extra(((_CROW, 0, 7),))
CROW_LANTERN = _extra(((_CROW, 0, 7), (_LANTERN, 0, 14)))
STAGES = [
    {"title": "Espantalhinho", "floor": 1, "extra": None},
    {"title": "Espantalho", "floor": 4, "extra": CROW},
    {"title": "Guardião da Lavoura", "floor": 10, "extra": CROW_LANTERN},
]
