"""Alchemist, 32 px, facing right. An apprentice in a teal tunic with a wide-brimmed leather hat,
copper hair and a golden monocle on a chain over the front eye. The symbol is the glass flask with
green liquid: it bubbles in idle and becomes a grenade in `running` (throw and green burst). In `failed` the flask cracks
in her hand, gives off smoke and she sits on the ground dizzy, with shards and a green puddle beside her.
The torso, head and hat move together (only legs and arms change), so the add-on's belt and goggles
always stay in place. Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#1a1422", "R": "#3f9a84", "r": "#2a6658", "E": "#9fe8c8", "F": "#f6d7c3", "f": "#d8a98e",
    "O": "#e0782e", "o": "#a8501e", "D": "#9a6236", "d": "#5e3a20", "B": "#c8334a",
    "G": "#ffd23f", "g": "#b8860b", "L": "#bfe8ff", "W": "#ffffff", "S": "#d8e6f0",
    "V": "#a6f06b", "v": "#4c9a3a", "P": "#ff6fae", "A": "#ffa94d", "Q": "#b8c4bc", "q": "#7d8a84",
    "k": "#3a2e3e", "T": "#8fd8ff", "Y": "#ffd23f",
}

TUNIC = (4, 4, 5, 5, 5, 6, 6, 7, 7)          # tunic half-width per row (9 rows)

FLASK = [
    ".KKKKK.",
    "..KSK..",
    "..KSK..",
    ".KSSSK.",
    "KVVVVWK",
    "KVvVVVK",
    "KvVVVvK",
    ".KKKKK.",
]
FLASK_CRACKED = [
    ".KKKKK.",
    "..KSK..",
    "..KKK..",
    ".KSKSK.",
    "KVKVKWK",
    "KVvKVVK",
    "KvVVKvK",
    ".KKKKK.",
]
FLASK_FLAT = [                               # rotated, flying sideways
    ".KKKK...",
    "KVVvVK..",
    "KVVVVSKK",
    "KvVVVSSK",
    "KVVvVSKK",
    ".KKKK...",
]
BUBBLE = [".K.", "KVK", ".K."]
BUBBLE_L = [".KK.", "KVWK", "KVVK", ".KK."]
BURST = [                                       # the flask bursts green on the enemy
    "...K....K...",
    "..KVK..KVK..",
    "K.KVVKKVVK.K",
    "VKKVVVVVVKKV",
    ".KVVWVVWVVK.",
    "..KVVWWVVK..",
    ".KVVWVVWVVK.",
    "VKKVVVVVVKKV",
    "K.KVVKKVVK.K",
    "..KVK..KVK..",
    "...K....K...",
]
STREAK = ["QQQ.", ".QQQ", "QQQ."]      # little motion streaks of the throw
SMOKE = [
    "...KKK....",
    "..KQQQK.K.",
    ".KQQqQQKQK",
    "KQQQQQqQQK",
    "KQqQQQQQK.",
    ".KKQQqQQK.",
    "...KKKKK..",
]
SMOKE_S = [".KK.", "KQQK", "KqQK", ".KK."]
SHARDS = [                                         # broken flask: fallen neck, shards and a green puddle
    "..KK.....K.",
    ".KSSK...KSK",
    "KSSK.K..KSK",
    ".KK.KSK.KK.",
    "KKKKKKKKKKK",
    "KVVvVVVVvVK",
    ".KKKKKKKKK.",
]
SHINE = ["..K..", ".KWK.", "KWLWK", ".KWK.", "..K.."]
BOOT = ["KKKK.", "KddKK", "KdddK", "KKKKK"]


def _arm(g, a, b, hand=True):
    """Thick tunic sleeve from `a` (shoulder) to `b` (hand), with the skin-colored hand at the tip."""
    px = {}
    for x, y in line(*a, *b):                   # 2 px thick sleeve
        px[(x, y)] = px[(x, y + 1)] = "R"
    outline_cells(g, px)
    if hand:
        stamp(g, [".KK.", "KFFK", "KFfK", ".KK."], b[0] - 1, b[1] - 1)


def frame(cx=13, base=30, leg=2, sitting=False, eye="n", feet=(0, 0), arms=(), flask=None, por=(),
           behind=()):
    """One 32x32 frame and the add-on anchor (7 to the left and 12 above the tunic top).
    `leg`: leg height (0 = crouched); `sitting`: legs stretched forward, tunic on the ground;
    `arms`: ((shoulder), (hand)) with the back shoulder at (cx-4, t+1) and the front one at (cx+4, t+1);
    `flask`: (sprite, x, y) drawn over the hand."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    t = (base - len(TUNIC) + 1) if sitting else (base - leg - len(TUNIC))
    hx, hy = cx + 1, t - 4
    px = {}
    if sitting:
        stamp(g, BOOT, cx + 5, base - 3)
    else:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + feet[i]
            for y in range(base - leg, base):
                px[(x, y)] = "k"
                px[(x + 1, y)] = "k"
            for x1 in range(x - 1, x + 3):
                px[(x1, base)] = "d"
    for r, w in enumerate(TUNIC):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "r" if x <= cx - w + 1 else ("E" if x == cx + 1 and r > 1 else "R")
    for x in range(hx - 4, hx + 5):
        for y in range(hy - 4, hy + 5):
            if (x - hx) ** 2 + (y - hy) ** 2 <= 21:
                hair = x <= hx - 2 or y <= hy - 3
                px[(x, y)] = ("o" if x <= hx - 4 else "O") if hair else "F"
    for x in range(hx - 7, hx + 7):               # hat brim
        px[(x, hy - 3)] = "D"
    for i, (a, b) in enumerate(((-4, 4), (-4, 3), (-4, 2), (-4, 1), (-5, -1))):   # crown, tipping backward
        for x in range(hx + a, hx + b + 1):
            px[(x, hy - 4 - i)] = "B" if i == 0 else ("d" if x == hx + a else "D")
    outline_cells(g, px)
    for x in range(hx - 7, hx + 7):
        g[hy - 2][x] = "K" if x in (hx - 7, hx + 6) or not (hx - 4 <= x <= hx + 4) else g[hy - 2][x]
    # face: back eye free, front eye inside the golden monocle with a chain
    ox, oy = hx + 2, hy
    stamp(g, [".GG.", "G..G", "G..G", ".GG."], ox - 1, oy - 1)
    eyes = {"n": (["K", "K"], ["KL", "KL"]), "fechado": (["..", "kk"], ["kk", "LL"]),
             "feliz": ([".K", "K."], ["KK", "LL"]), "x": (["K.K", ".K.", "K.K"], ["KK", "KK"]),
             "bravo": (["K.", ".K"], ["KK", "KL"]), "cima": (["K", "F"], ["KL", "LL"]),
             "triste": (["K.", "KK"], ["LL", "KK"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 1 - (len(back[0]) > 2), hy - (len(back) > 2))
    stamp(g, front, ox, oy)
    g[oy + 3][ox - 1] = "g"
    g[oy + 4][ox - 2] = "g"
    g[hy + 2][hx - 2] = "P"                       # cheek
    g[hy + 3][hx + 1] = "f" if eye not in ("x", "triste") else "K"
    if eye == "triste":
        stamp(g, TEAR, hx - 1, hy + 2)
    for a, b in arms:
        _arm(g, a, b)
    if flask:
        stamp(g, *flask)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 7, t - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, leg=2 -> tunic 19-27 (cx=13), head 11-19 (hx=14), hat 6-12; shoulders at (9, 20) and (17, 20)
_T = ((9, 20), (6, 25))                        # back arm loose at the side
_SEG = ((17, 20), (21, 22))                    # front arm holding the flask
_F = (FLASK, 18, 14)
_SPECS = {
    # standing with the flask in hand; the liquid bubbles (bubbles rise and pop) and she blinks
    "idle": [dict(arms=(_T, _SEG), flask=_F),
             dict(arms=(_T, _SEG), flask=_F, por=((BUBBLE, 20, 11),)),
             dict(arms=(_T, _SEG), flask=_F, por=((BUBBLE, 19, 9), (BUBBLE_L, 21, 6))),
             dict(eye="fechado", arms=(_T, _SEG), flask=_F, por=((BUBBLE_L, 20, 4),)),
             dict(arms=(_T, _SEG), flask=_F, por=((BUBBLE, 22, 3),))],
    # runs with the legs alternating, flask in front and the back arm swinging
    "run_r": [dict(feet=(-2, 2), arms=(((9, 20), (5, 23)), ((17, 20), (22, 21))), flask=(FLASK, 19, 13)),
              dict(base=29, feet=(0, 0), arms=(((9, 20), (6, 21)), ((17, 20), (22, 22))),
                   flask=(FLASK, 19, 14)),
              dict(feet=(2, -2), arms=(((9, 20), (5, 23)), ((17, 20), (22, 21))), flask=(FLASK, 19, 13)),
              dict(base=29, feet=(0, 0), arms=(((9, 20), (6, 21)), ((17, 20), (22, 22))),
                   flask=(FLASK, 19, 14))],
    # waves high with the front hand; the flask stays in the other hand, at the side
    "waving": [dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (24, 15))), flask=(FLASK, 2, 16)),
               dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (23, 11))), flask=(FLASK, 2, 16)),
               dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (27, 13))), flask=(FLASK, 2, 16)),
               dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (23, 11))), flask=(FLASK, 2, 16))],
    # crouches, jumps with the flask raised, comes down, lands
    "jumping": [dict(leg=0, eye="fechado", arms=(((9, 22), (5, 26)), ((17, 22), (22, 25))),
                     flask=(FLASK, 19, 17)),
                dict(base=28, eye="cima", arms=(((9, 18), (5, 14)), ((17, 18), (22, 12))),
                     flask=(FLASK, 19, 4)),
                dict(base=26, eye="feliz", arms=(((9, 16), (4, 12)), ((17, 16), (23, 10))),
                     flask=(FLASK, 20, 2)),
                dict(base=28, arms=(((9, 18), (5, 21)), ((17, 18), (22, 16))), flask=(FLASK, 19, 8)),
                dict(leg=0, eye="feliz", arms=(((9, 22), (5, 26)), ((17, 22), (22, 25))),
                     flask=(FLASK, 19, 17))],
    # the flask cracks in her hand and gives off smoke; she sits on the ground dizzy, with shards and a green puddle beside her
    "failed": [dict(eye="triste", arms=(_T, _SEG), flask=(FLASK_CRACKED, 18, 14)),
               dict(eye="x", arms=(_T, ((17, 20), (21, 23))), flask=(FLASK_CRACKED, 18, 15),
                    por=((SMOKE, 20, 4),)),
               dict(eye="x", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((SHARDS, 21, 24), (SMOKE, 21, 3))),
               dict(eye="x", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((SHARDS, 21, 24), (SMOKE_S, 24, 2), (SMOKE, 21, 7))),
               dict(eye="x", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((SHARDS, 21, 24), (SMOKE_S, 26, 1)))],
    # naps sitting on the ground, flask beside her, "z" rising
    "waiting": [dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22)),
                dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22), por=((Z_S, 25, 8),)),
                dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22), por=((Z_S, 24, 9), (Z_L, 26, 1))),
                dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22), por=((Z_L, 26, 1),))],
    # throw: winds the flask back up high, throws it (streaks), the flask flies and bursts green on the enemy
    "running": [dict(cx=12, eye="bravo", arms=(((8, 20), (3, 12)), ((16, 20), (20, 23))),
                     flask=(FLASK, 0, 4)),
                dict(cx=12, eye="bravo", arms=(((8, 20), (5, 24)), ((16, 20), (24, 17))),
                     flask=(FLASK_FLAT, 23, 10), por=((STREAK, 20, 9),)),
                dict(cx=12, eye="bravo", arms=(((8, 20), (5, 24)), ((16, 20), (22, 22))),
                     flask=(FLASK_FLAT, 24, 7), por=((STREAK, 21, 8),)),
                dict(cx=12, eye="feliz", arms=(((8, 20), (5, 24)), ((16, 20), (22, 22))),
                     por=((BURST, 20, 5),))],
    # hand on the chin, eye to the side through the monocle (which shines), "?" appears
    "review": [dict(eye="cima", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18)),
               dict(eye="cima", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18),
                    por=((QMARK_S, 25, 4),)),
               dict(eye="cima", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18),
                    por=((QMARK, 25, 2), (SHINE, 18, 7))),
               dict(eye="n", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18),
                    por=((QMARK, 25, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# 15x21 grid attached 7 to the left and 12 above the tunic top (tunic from row 12, center on column 7;
# hat band on row 4, head centered on column 8): leather belt with three colored flasks at the waist;
# double-lens brass-rimmed goggles on the hat band, inside the crown (rows 2-5, columns 5-11)
_BELT = [
    "KddddKGKddddK",
    ".KdK...KdKKdK",
    ".KAK...KVKKPK",
    ".KAK...KVKKPK",
    ".KKK...KKKKKK",
]
_GOGGLES = [                                       # brass rim, no dark outline, to stand out on the hat
    ".gg.gg.",                                    # 7 wide: fits inside the crown without eating its outline
    "gLWgLWg",
    "gLLgLLg",
    ".gg.gg.",
]


def _extra(pieces, w=15, h=21):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BELT = _extra(((_BELT, 1, 15),))
BELT_GOGGLES = _extra(((_BELT, 1, 15), (_GOGGLES, 5, 2)))
STAGES = [
    {"title": "Aprendiz de Alquimia", "floor": 1, "extra": None},
    {"title": "Alquimista", "floor": 4, "extra": BELT},
    {"title": "Mestre Alquimista", "floor": 10, "extra": BELT_GOGGLES},
]
