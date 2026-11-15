"""Cave Mushroom, 32 px, facing right. Each frame is made of parts: stalk with a little face (and shade),
dome cap with glowing spots (2 phases), little feet, arms as thick lines and objects (spores, cloud).
In `failed` the cap wilts and tips over, the stalk shrinks and the spores escape.
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from math import sqrt

from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, stroke

PAL = {
    "K": "#241a2c", "C": "#efe3cf", "c": "#c2ae98", "U": "#7a4fb0", "u": "#4c2e78",
    "L": "#7ff5d6", "l": "#3fae9a", "E": "#a8e07a", "e": "#6aa848", "O": "#e0743a",
    "W": "#ffffff", "B": "#241a2c", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f",
}

SPORE = ["..K..", ".KLK.", "KLWLK", ".KLK.", "..K.."]
SPORE_S = [".K.", "KLK", ".K."]
CLOUD = [
    "....KKK.....",
    "..KKEEEKKK..",
    ".KEEELEEEEK.",
    "KEELEEEeEEEK",
    "KEEEEeELEEEK",
    "KeEEEEEEEeK.",
    ".KKeELEeKK..",
    "...KKKKK....",
]
PUFF = ["..KKK..", ".KEEEK.", "KEELEEK", "KEEEeEK", ".KEEEK.", "..KKK.."]
HAND = [".KKK.", "KCCCK", "KCCCK", ".KKK."]
# cap spots: (dx from the row center, row from the top, width, height, phase in which it lights up)
SPOTS = ((-4, 2, 2, 2, 0), (2, 1, 2, 1, 1), (4, 3, 2, 2, 0), (-1, 4, 1, 1, 1), (-7, 4, 1, 1, 1))


def frame(cx=15, base=30, h=9, lean=0, hat=9, hc=7, tilt=0, eyes="normal", shine=0, arms=(), por=(),
           behind=(), feet=(0, 0)):
    """One 32x32 frame and the anchor (corner of the add-on, 13 px to the left and 6 above the cap top).
    `hat`: half-width of the cap; `hc`: height; `tilt`: how far the cap top tips to the side."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    top = base - h
    stalk = set()
    for y in range(top, base):
        t = (y - top) / max(h - 1, 1)
        c = cx + round(lean * (1 - t))
        stalk |= {(x, y) for x in range(c - 5, c + 6)}
    for px, dx in ((cx - 4, feet[0]), (cx + 2, feet[1])):   # little feet
        stalk |= {(x, base) for x in range(px + dx, px + dx + 3)}
    ct = cx + lean
    ytop = top + 2 - hc
    cap = {}
    for r in range(hc):
        tt = (hc - 1 - r) / hc
        w = max(1, round(hat * sqrt(1 - tt * tt))) - (r == hc - 1)
        cc = ct + round(tilt * (hc - 1 - r) / max(hc - 1, 1))
        for x in range(cc - w, cc + w + 1):
            cap[(x, ytop + r)] = "u" if r == hc - 1 or x >= cc + w - 1 else "U"
        for dx, py, pw, ph, phase in SPOTS:
            if py <= r < py + ph:
                for x in range(cc + dx, cc + dx + pw):
                    if (x, ytop + r) in cap and cap[(x, ytop + r)] == "U" and abs(x - cc) < w:
                        cap[(x, ytop + r)] = "L" if phase == shine else "l"
    body = stalk | set(cap)
    for x, y in stalk:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = "c" if (x + 1, y) not in stalk or y >= base - 1 else "C"
    for (x, y), ch in cap.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = ch
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # face on the stalk, just below the cap
    fy = top + 2
    ex = ct - 3
    for x in (ex, ex + 5):
        if eyes == "closed":
            stamp(g, ["BB"], x, fy + 1)
        elif eyes == "happy":
            stamp(g, [".B.", "B.B"], x - (x > ex), fy)
        elif eyes == "x":
            stamp(g, ["B.B", ".B.", "B.B"], x - (x > ex), fy)
        else:
            stamp(g, ["WB", "BB"], x, fy)
            if eyes == "up":
                g[fy + 1][x] = g[fy + 1][x + 1] = "B"; g[fy][x] = "B"; g[fy][x + 1] = "W"
    if eyes not in ("closed", "x"):
        g[fy + 2][ex - 1] = g[fy + 2][ex + 7] = "P"
    my = fy + 3
    if eyes in ("sad", "x"):
        stamp(g, [".BB.", "B..B"], ex + 2, my)
    elif eyes == "angry":
        stamp(g, ["BBBB"], ex + 2, my)
    elif eyes != "closed":
        stamp(g, ["B..B", ".BB."], ex + 2, my)
    for a, b in arms:
        x, y = a
        while (x, y) in stalk:              # the arm leaves from the stalk's edge, without crossing the face
            x += 1 if x >= ct else -1
        stroke(g, (x, y), b, "C")
        stamp(g, HAND, b[0] - 2, b[1] - 1)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (ct + tilt - 13, ytop - 6)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, h=9 -> stalk from 21 to 29, cap from 16 to 22; stalk sides at cx-5 / cx+5 (cx=15: 10 and 20)
_SPECS = {
    # standing, spots blinking, little spores rising on both sides, little hands swaying
    "idle": [dict(shine=0, arms=(((20, 25), (24, 27)), ((10, 25), (6, 27))), por=((SPORE, 26, 18),)),
             dict(shine=1, arms=(((20, 25), (24, 26)), ((10, 25), (6, 28))), por=((SPORE, 27, 13),)),
             dict(shine=0, eyes="closed", arms=(((20, 25), (24, 27)), ((10, 25), (6, 27))),
                  por=((SPORE, 2, 17), (SPORE_S, 28, 9))),
             dict(shine=1, arms=(((20, 25), (24, 28)), ((10, 25), (6, 26))), por=((SPORE, 1, 12),))],
    # runs leaning, cap pulled back, spores left behind
    "run_r": [dict(lean=2, tilt=-2, feet=(-2, 2), arms=(((12, 25), (7, 28)),), por=((SPORE, 1, 20),)),
              dict(lean=3, base=29, tilt=-3, shine=1, arms=(((12, 24), (7, 23)),), por=((SPORE_S, 2, 17),)),
              dict(lean=2, tilt=-2, feet=(2, -2), arms=(((12, 25), (7, 27)),), por=((SPORE, 0, 19),)),
              dict(lean=3, base=29, tilt=-3, shine=1, arms=(((12, 24), (8, 21)),), por=((SPORE_S, 1, 15),))],
    # waves high with the right hand, the cap sways along
    "waving": [dict(eyes="happy", arms=(((20, 24), (28, 21)), ((10, 25), (6, 27)))),
               dict(eyes="happy", tilt=1, shine=1, arms=(((20, 24), (29, 16)), ((10, 25), (6, 27)))),
               dict(eyes="happy", tilt=2, arms=(((20, 24), (25, 14)), ((10, 25), (6, 27)))),
               dict(eyes="happy", tilt=1, shine=1, arms=(((20, 24), (29, 16)), ((10, 25), (6, 27))))],
    # crouches (cap flattens), jumps with arms up, falls, lands
    "jumping": [dict(h=7, hat=10, hc=6, eyes="closed", arms=(((20, 26), (24, 28)), ((10, 26), (6, 28)))),
                dict(base=27, hc=8, hat=8, arms=(((20, 22), (25, 18)), ((10, 22), (5, 18)))),
                dict(base=24, hc=8, hat=8, eyes="happy", shine=1,
                     arms=(((20, 19), (26, 14)), ((10, 19), (4, 14)))),
                dict(base=27, shine=1, arms=(((20, 22), (25, 24)), ((10, 22), (5, 24)))),
                dict(h=8, hat=10, hc=6, eyes="happy", arms=(((20, 26), (24, 28)), ((10, 26), (6, 28))))],
    # sad, the cap wilts and tips over, the stalk shrinks and the spores escape
    "failed": [dict(eyes="sad", arms=(((20, 25), (23, 29)), ((10, 25), (7, 29))), por=((TEAR, 11, 25),)),
               dict(eyes="sad", h=8, hc=6, hat=10, tilt=-2, shine=1,
                    arms=(((20, 26), (23, 29)), ((10, 26), (7, 29))), por=((SPORE, 25, 12),)),
               dict(cx=16, eyes="sad", h=8, hc=5, hat=10, tilt=-3, por=((TEAR, 11, 26), (SPORE, 24, 9),
                                                                      (SPORE, 3, 13))),
               dict(cx=17, eyes="x", h=7, hc=4, hat=10, tilt=-3, lean=-1, shine=1,
                    por=((SPORE_S, 25, 8), (SPORE, 4, 9), (SPORE, 26, 14))),
               dict(cx=18, eyes="x", h=7, hc=4, hat=11, tilt=-4, lean=-1, shine=2, por=((SPORE_S, 6, 6),))],
    # naps with the cap drooping forward, "z" rising
    "waiting": [dict(h=8, eyes="closed", tilt=2, shine=2),
                dict(h=8, eyes="closed", tilt=3, shine=2, por=((Z_S, 24, 6),)),
                dict(h=8, eyes="closed", tilt=3, shine=2, por=((Z_S, 23, 6), (Z_L, 26, 0))),
                dict(h=8, eyes="closed", tilt=2, shine=2, por=((Z_L, 26, 0),))],
    # attack: pulls the arm back, squeezes the cap and blows a spreading cloud of spores
    "running": [dict(cx=15, lean=-1, tilt=-1, hc=8, hat=8, eyes="angry", arms=(((8, 25), (3, 21)),)),
                dict(cx=14, lean=1, hc=5, hat=11, eyes="angry", shine=1, arms=(((19, 24), (24, 22)),),
                     por=((PUFF, 25, 22),)),
                dict(cx=14, lean=3, tilt=1, eyes="angry", arms=(((19, 24), (22, 24)),),
                     por=((CLOUD, 20, 18),)),
                dict(cx=14, lean=1, tilt=1, eyes="angry", shine=1, arms=(((19, 24), (23, 27)),),
                     por=((CLOUD, 19, 9), (SPORE, 25, 21), (SPORE_S, 28, 26), (SPORE_S, 22, 19)))],
    # hand on the chin, looking up, "?" appears
    "review": [dict(cx=13, eyes="up", arms=(((18, 27), (21, 25)),)),
               dict(cx=13, eyes="up", shine=1, arms=(((18, 27), (21, 25)),), por=((QMARK_S, 25, 4),)),
               dict(cx=13, eyes="up", arms=(((18, 27), (21, 25)),), por=((QMARK, 25, 2),)),
               dict(cx=13, eyes="normal", shine=1, arms=(((18, 27), (21, 25)),), por=((QMARK, 25, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)


def _extra(pieces, w=27, h=14):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


# glowing spores around the cap (the cap top sits on row 6, centered on column 13); the extra is 27
# columns wide, so the cap top (ct + tilt) stays between x=13 and x=18 in every frame for the spores to fit
_SHINE = ((SPORE, 2, 1), (SPORE, 22, 6), (SPORE, 0, 9))
SPORES = _extra(_SHINE)
# elder: little mushrooms sprouting from the cap top and two spores on the sides
MINI_S = [".KKK.", "KOLOK", "KKKKK", ".KCK.", ".KCK."]
MINI_L = ["..KKK..", ".KOOOK.", "KOLOOOK", "KKKKKKK", "..KCK..", "..KCK.."]
ELDER = _extra(((SPORE, 22, 6), (SPORE, 0, 9), (MINI_S, 7, 1), (MINI_L, 12, 0)))
STAGES = [
    {"title": "Sporeling", "floor": 1, "extra": None},
    {"title": "Cave Mushroom", "floor": 4, "extra": SPORES},
    {"title": "Mycelium Elder", "floor": 10, "extra": ELDER},
]
