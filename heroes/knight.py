"""Empty Knight, 32 px, facing right. An empty suit of armor: bucket helm with a dark visor slit and,
inside, a single little golden eye peeking from side to side. Breastplate with pauldrons, belt, greaves,
gauntlets as thick lines and the symbols: the sword and the shield with the golden cross. In `failed` the armor
collapses into pieces (sword and shield fall to the ground, the helm sinks into the pile) and the little eye runs away along the ground.
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, stroke

PAL = {
    "K": "#1c1424", "s": "#0d0812", "M": "#a4adbf", "m": "#646c80", "W": "#eef2f8", "S": "#dfe6f2",
    "Y": "#ffd23f", "y": "#8a6a20", "G": "#ffd23f", "g": "#b8860b", "D": "#5a3a24",
    "B": "#3d5a9e", "b": "#28396a", "R": "#c8334a", "r": "#7e1f33", "T": "#8fd8ff",
}

HH = 9                                          # helm height
HELM = (3, 4, 5, 5, 5, 5, 5, 5, 4)              # helm half-width per row

SHIELD = [
    "KKKKKKKK",
    "KMMMMMMK",
    "KBBGGBBK",
    "KBGGGGBK",
    "KBBGGBBK",
    "KBBGGBbK",
    ".KBGGbK.",
    ".KBBbbK.",
    "..KBbK..",
    "...KK...",
]
SHIELD_FLAT = [
    ".KKKKKKKKK.",
    "KMBBBGBBbbK",
    "KMBGGGGGbbK",
    "KMBBBGBBbK.",
    ".KKKKKKKK..",
]
# little eye that escaped the armor, with tiny legs (two steps)
EYE_TINY = [[".KKKK.", "KYYWYK", "KYYYYK", ".KKKK.", ".K..K."],
           [".KKKK.", "KYYWYK", "KYYYYK", ".KKKK.", "K....K"]]
SHINE = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
GASH = ["KKK.....", "WWWKK...", "KKWWWK..", "..KKWWK.", "....KWWK", ".....KWK", ".....KWK",
         "....KWK."]                                                   # white trail of the arc cut
HAND = [".KK.", "KMMK", "KmmK", ".KK."]


def sword(g, fist, tip):
    """Sword from the grip (brown handle and golden pommel) to the tip, with a golden crossguard."""
    (x0, y0), (x1, y1) = fist, tip
    dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
    stroke(g, (x0 + dx, y0 + dy), tip, "S")
    stroke(g, (x0 - dx, y0 - dy), (x0, y0), "D")
    gx, gy = x0 + 2 * dx, y0 + 2 * dy
    px, py = -dy, dx
    n = 1 if dx and dy else 2                     # shorter diagonal guard, so it does not become an X
    stroke(g, (gx - n * px, gy - n * py), (gx + n * px, gy + n * py), "G")
    stroke(g, (x0 + 3 * dx, y0 + 3 * dy), tip, "S")
    if 0 <= x1 < N and 0 <= y1 < N:
        g[y1][x1] = "W"
    px0, py0 = x0 - 2 * dx, y0 - 2 * dy
    if 0 <= px0 < N and 0 <= py0 < N:
        g[py0][px0] = "G"


def frame(cx=15, base=30, hr=7, leg=3, lean=0, falls=0, eye=0, arms=(), swords=(), por=(), behind=(),
           feet=(0, 0)):
    """One 32x32 frame and the add-on anchor (12 to the left and 8 above the helm top).
    `hr`: breastplate height; `leg`: greave height; `falls`: how far the helm sinks into the breastplate;
    `eye`: offset of the little eye in the slit (-2..2) or "fechado", "cima", "feliz", "bravo", "triste", "x", "fora"."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    cint = base - leg - hr
    ch = cx + lean
    top = cint - HH + falls
    chest = {}
    for r in range(hr):
        y = cint + r
        c = ch - round(lean * r / max(hr - 1, 1))
        m = 6 if r < 2 else (5 if r == hr - 1 else 4)
        for x in range(c - m, c + m + 1):
            if r == hr - 1 and hr > 2:
                color = "G" if x in (c, c + 1) else "D"            # belt with buckle
            elif x >= c + m - 1:
                color = "m"
            elif r == 1 and x in (c - 5, c + 5):
                color = "m"                                          # pauldron joint
            elif r in (2, 3) and x == c - 2:
                color = "W"
            else:
                color = "M"
            chest[(x, y)] = color
    leg_px = {}
    for px, dx in ((cx - 3, feet[0]), (cx + 1, feet[1])):
        for y in range(base - leg, base):
            leg_px[(px + dx, y)] = "M"
            leg_px[(px + dx + 1, y)] = "m"
        for x in range(px + dx - 1, px + dx + 2):
            leg_px[(x, base)] = "m"
    helm = {}
    for r, w in enumerate(HELM):
        for x in range(ch - w, ch + w + 1):
            if r == HH - 1 or x >= ch + w - 1 and r > 0:
                color = "m"
            elif r in (1, 2) and x == ch - 3:
                color = "W"
            else:
                color = "M"
            helm[(x, top + r)] = color
    body = {**leg_px, **chest, **helm}
    for (x, y), c in body.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # visor slit (3 dark rows) and the little eye inside
    for y in range(top + 3, top + 6):
        for x in range(ch - 3, ch + 5):
            g[y][x] = "s"
    for x in (ch - 1, ch + 2):                                     # rivets
        g[top + 7][x] = "K"
    ex, ey = ch, top + 4
    if isinstance(eye, int):
        stamp(g, ["YW", "YY"], ex + eye, ey)
    elif eye == "closed":
        stamp(g, ["yy"], ex, ey + 1)
    elif eye == "up":
        stamp(g, ["YW", "YY"], ex + 1, ey - 1)
    elif eye == "happy":
        stamp(g, [".Y.", "Y.Y"], ex, ey)
    elif eye == "angry":
        stamp(g, ["sYW", "YYY"], ex, ey)
    elif eye == "sad":
        stamp(g, ["Ys", "YY"], ex, ey + 1)
    elif eye == "x":
        stamp(g, ["Y.Y", ".Y.", "Y.Y"], ex, ey - 1)
    for a, b in arms:
        x, y = a
        while (x, y) in body:             # the arm leaves from the body's edge, without crossing the breastplate
            x += 1 if x >= ch else -1
        stroke(g, (x, y), b, "M")
        stamp(g, HAND, b[0] - 1, b[1] - 1)
    for fist, tip in swords:
        sword(g, fist, tip)
        stamp(g, HAND, fist[0] - 1, fist[1] - 1)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (ch - 12, top - 8)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, hr=7, leg=3 -> breastplate 20-26, greaves 27-29, feet 30, helm 11-19; shoulders at (cx±6, 21)
_E = ((9, 22), (6, 25))                 # back arm holding the shield at the side
_SPECS = {
    # standing with the sword stuck in the ground; the little eye peeks through the visor from side to side and blinks
    "idle": [dict(eye=0, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye=2, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye=2, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye=-2, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye="closed", arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),))],
    # runs leaning, sword pointed forward, shield on the back swinging
    "run_r": [dict(lean=2, eye=2, feet=(-2, 2), arms=(((11, 22), (6, 25)), ((22, 22), (24, 23))),
                   swords=(((24, 23), (31, 17)),), por=((SHIELD, 0, 20),)),
              dict(lean=3, base=29, eye=2, arms=(((12, 21), (7, 23)), ((23, 21), (25, 22))),
                   swords=(((25, 22), (31, 15)),), por=((SHIELD, 1, 17),)),
              dict(lean=2, eye=2, feet=(2, -2), arms=(((11, 22), (6, 25)), ((22, 22), (24, 23))),
                   swords=(((24, 23), (31, 17)),), por=((SHIELD, 0, 21),)),
              dict(lean=3, base=29, eye=2, arms=(((12, 21), (7, 23)), ((23, 21), (25, 22))),
                   swords=(((25, 22), (31, 15)),), por=((SHIELD, 1, 18),))],
    # waves high with the gauntlet; the shield stays on the other arm
    "waving": [dict(eye="happy", arms=(_E, ((21, 22), (26, 17))), por=((SHIELD, 1, 21),)),
               dict(eye="happy", arms=(_E, ((21, 22), (27, 13))), por=((SHIELD, 1, 21),)),
               dict(eye="happy", arms=(_E, ((21, 22), (29, 15))), por=((SHIELD, 1, 21),)),
               dict(eye="happy", arms=(_E, ((21, 22), (27, 13))), por=((SHIELD, 1, 21),))],
    # crouches (armor shrinks), jumps with the sword up high, falls, lands
    "jumping": [dict(hr=6, leg=2, eye="closed", arms=(((9, 24), (5, 28)),), swords=(((24, 26), (30, 29)),)),
                dict(base=28, eye="up", arms=(((9, 20), (5, 15)),), swords=(((25, 15), (29, 6)),)),
                dict(base=27, eye="happy", arms=(((9, 19), (4, 13)),), swords=(((25, 13), (28, 3)),)),
                dict(base=28, eye=0, arms=(((9, 20), (5, 23)),), swords=(((25, 22), (30, 17)),)),
                dict(hr=6, eye="happy", arms=(((9, 23), (5, 27)),), swords=(((24, 25), (30, 28)),))],
    # collapses: the sword falls, the armor sinks piece by piece, the helm drops on the pile and the little eye runs away
    "failed": [dict(eye="sad", arms=(_E, ((21, 22), (23, 27))), por=((SHIELD, 1, 21), (TEAR, 16, 17))),
               dict(eye="sad", hr=6, leg=2, arms=(((9, 22), (7, 28)), ((21, 22), (23, 28))),
                    swords=(((20, 29), (31, 29)),), por=((SHIELD, 0, 21),)),
               dict(eye="x", hr=5, leg=1, falls=1, arms=(((9, 25), (6, 29)), ((21, 25), (24, 29))),
                    swords=(((20, 29), (31, 29)),), por=((SHIELD_FLAT, 0, 26),)),
               dict(eye="out", hr=3, leg=1, falls=2, swords=(((20, 29), (31, 29)),),
                    por=((SHIELD_FLAT, 0, 26), (EYE_TINY[0], 24, 22))),
               dict(eye="out", hr=3, leg=0, falls=3, swords=(((20, 29), (31, 29)),),
                    por=((SHIELD_FLAT, 0, 26), (EYE_TINY[1], 26, 22)))],
    # naps leaning on the stuck sword, the little eye dimmed, "z" rising
    "waiting": [dict(hr=6, falls=1, eye="closed", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22),)),
                dict(hr=6, falls=1, eye="closed", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22), (Z_S, 25, 8))),
                dict(hr=6, falls=1, eye="closed", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22), (Z_S, 24, 8), (Z_L, 26, 1))),
                dict(hr=6, falls=1, eye="closed", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22), (Z_L, 26, 1)))],
    # attack: raises the sword, cuts down (white trail), pushes the shield (thud), thrusts with a shine
    "running": [dict(cx=14, eye="angry", arms=(((8, 22), (5, 25)),), swords=(((23, 14), (29, 3)),),
                     por=((SHIELD, 0, 21),)),
                dict(cx=14, lean=1, eye="angry", arms=(((9, 22), (6, 25)),), swords=(((24, 21), (31, 28)),),
                     por=((SHIELD, 1, 21), (GASH, 23, 8))),
                dict(cx=14, lean=2, eye="angry", arms=(((22, 22), (25, 21)),),
                     swords=(((10, 25), (6, 30)),), por=((SHIELD, 23, 16), (SHINE, 25, 7))),
                dict(cx=14, lean=2, eye="angry", arms=(((10, 22), (7, 25)),), swords=(((24, 21), (31, 21)),),
                     por=((SHIELD, 1, 20), (SHINE, 25, 13)))],
    # gauntlet on the helm's chin, little eye looking up, "?" appears
    "review": [dict(eye="up", arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21),)),
               dict(eye="up", arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21), (QMARK_S, 25, 4))),
               dict(eye="up", arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21), (QMARK, 25, 2))),
               dict(eye=2, arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21), (QMARK, 25, 2)))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# 17x10 grid attached 12 to the left and 8 above the helm top (helm top on row 8, center on column 12):
# red plume on top of the helm, falling backward; the blue banner with a golden cross sticks out of the back
_PLUME = [
    "....KKKK.",
    "..KKRRRRK",
    ".KRRRRrRK",
    "KRRrrKKRK",
    "KRrK.KGGK",
    ".KK..KGK.",
]
_BANNER = [
    ".....KGK",
    "KKKKKKDK",
    "KBBGBKDK",
    "KBGGGKDK",
    "KBBGBKDK",
    "KBBGBKDK",
    ".KBbKKDK",
    "..KK.KDK",
    ".....KDK",
    ".....KDK",
]


def _extra(pieces, w=17, h=10):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


PLUME = _extra(((_PLUME, 7, 2),))
PLUME_BANNER = _extra(((_BANNER, 0, 0), (_PLUME, 7, 2)))
STAGES = [
    {"title": "Empty Armor", "floor": 1, "extra": None},
    {"title": "Empty Knight", "floor": 4, "extra": PLUME},
    {"title": "Empty Paladin", "floor": 10, "extra": PLUME_BANNER},
]
