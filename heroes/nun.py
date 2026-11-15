"""Ash Nun, 32 px, facing right. A short little nun in an ash-grey habit (the color of fireplace
ash), a dark rounded veil falling down the back and a white coif framing the round face. The symbol is the
little bone rosary (bone beads with a tiny skull at the end): it sways in idle and becomes a whip in `running` (the
little skull cracks on the enemy in a burst of embers). In `failed` she crumbles into ash: the habit crumbles and
what is left is a little ash mound with embers, the veil fallen on top and the rosary beside it.
The torso and head move together (only feet and arms change), so the add-ons' cord and long veil always
stay in place. Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#16121c", "H": "#aaa3b0", "h": "#7d7688", "V": "#6d6580", "v": "#4c455c", "C": "#efebf2",
    "F": "#f6dccb", "f": "#d8b3a0", "P": "#ff8fae", "L": "#bfe8ff", "d": "#3a3340", "k": "#3a2e3e",
    "W": "#efe6cf", "w": "#c7b993", "Q": "#c3bdc6", "q": "#8d8794", "O": "#ff8a3d", "o": "#c2421e",
    "Y": "#ffd23f", "T": "#8fd8ff", "D": "#8a5a32",
}

HABIT = (3, 4, 4, 5, 5, 6, 6, 7, 7, 7)       # habit half-width per row (10 rows, down to the ground)

SKULL = [".KKKK.", "KWWWWK", "KOWWOK", "KWWWWK", ".KwwK.", "..KK.."]   # little skull with ember eyes
EMBER = [                                       # the little skull cracks: burst of embers
    "...K...K....",
    "..KOK.KYK...",
    "K.KOOKKYOK.K",
    "OKKOYYOYOKKO",
    ".KOYYWYYOOK.",
    "..KOYWWYOK..",
    ".KOOYYYYOOK.",
    "OKKOOYOOOKKO",
    "K.KOoKKOoK.K",
    "..KoK..KoK..",
    "...K....K...",
]
FLICKER = [".K.", "KOK", ".K."]
FLICKER_Y = [".K.", "KYK", ".K."]
STREAK = ["QQQ.", ".QQQ", "QQQ."]
SMOKE = [
    "..KKK...",
    ".KQQQK..",
    "KQqQQQK.",
    "KQQQqQK.",
    ".KKQQQK.",
    "...KKK..",
]
SMOKE_S = [".KK.", "KQQK", "KqQK", ".KK."]
GREY = ["Q.", ".q"]                             # falling ash flakes


def _arm(g, a, b, hand=True):
    """Wide habit sleeve from `a` (shoulder) to `b` (hand), with the little skin-colored hand at the tip."""
    px = {}
    for x, y in line(*a, *b):
        px[(x, y)] = px[(x, y + 1)] = "h"
    outline_cells(g, px)
    if hand:
        stamp(g, [".KK.", "KFFK", "KFfK", ".KK."], b[0] - 1, b[1] - 1)


def _rosary(g, hand, tip):
    """Little bone rosary: bone beads from the hand to the tip, with the tiny skull hanging from it."""
    px = {}
    for i, (x, y) in enumerate(line(*hand, *tip)[1:]):    # 2 px beads, alternating light and dark bone
        px[(x, y)] = "W" if i % 3 == 0 else "w"
        if i % 3 == 0:                            # 2x2 bone bead, thin cord between them
            px[(x + 1, y)] = px[(x, y + 1)] = px[(x + 1, y + 1)] = "W"
    outline_cells(g, px)
    stamp(g, SKULL, tip[0] - 2, tip[1])


def _mound(g, cx, base, phase):
    """Little ash mound with embers and the veil fallen on top (phase 1 = still crumbling, 2 = only the mound)."""
    px = {}
    # mounds of different sizes (center x, center y, radius x, radius y) added up: irregular top outline
    for mx, my, rx, ry in ((cx - 6, base, 4, 3), (cx, base - 1, 5, 3), (cx + 6, base - 1, 4, 5),
                           (cx + 10, base + 1, 2, 2), (cx - 10, base + 1, 1, 1)):
        for x in range(mx - rx, mx + rx + 1):
            for y in range(my - ry, min(my + ry, base) + 1):
                if (x - mx) ** 2 / (rx + 0.5) ** 2 + (y - my) ** 2 / (ry + 0.5) ** 2 <= 1:
                    px[(x, y)] = "q" if (3 * x + 7 * y) % 11 < 2 else "Q"
    for x, y in ((cx - 12, base), (cx + 13, base), (cx + 3, base - 6)):   # loose crumbs
        px[(x, y)] = "Q"
    hx, hy = cx - 1, base - 5                    # the veil fallen and crumpled on top of the little mound, slipping to the right
    for x in range(hx - 6, hx + 7):
        for y in range(hy - 4, hy + 3):
            if (x - hx) ** 2 / 26 + (y - hy - 1 - (x - hx) // 3) ** 2 / 9 <= 1:
                px[(x, y)] = "v" if x <= hx - 3 else "V"
    for x in range(hx - 1, hx + 6):              # little tip of the coif showing under the veil
        px[(x, hy + 3)] = "C"
    outline_cells(g, px)
    embers = [(cx - 5, base - 1), (cx + 4, base - 2), (cx - 1, base)] if phase == 2 else [(cx + 3, base - 1)]
    for x, y in embers:
        g[y][x] = "O"
        g[y - 1][x] = "o"


def frame(cx=13, base=30, leg=1, eye="n", feet=(0, 0), arms=(), rosary=None, por=(), mound=0, crumbles=False):
    """One 32x32 frame and the add-on anchor (8 to the left and 12 above the habit top).
    `arms`: ((shoulder), (hand)) with the back shoulder at (cx-4, t+1) and the front one at (cx+4, t+1);
    `rosary`: ((hand), (tip)) drawn over the hand; `mound`: 1 or 2 = became a little ash mound."""
    g = [["."] * N for _ in range(N)]
    if mound:
        _mound(g, cx, base, mound)
        for s, x, y in por:
            stamp(g, s, x, y)
        return ["".join(l) for l in g], (cx - 8, base - 16)
    t = base - leg - len(HABIT)
    hx, hy = cx + 1, t - 5
    px = {}
    for i, x0 in enumerate((cx - 3, cx + 1)):     # little shoes showing under the habit
        x = x0 + feet[i]
        for y in range(base - leg, base + 1):
            for x1 in range(x, x + 3):
                px[(x1, y)] = "d"
    for r, w in enumerate(HABIT):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "h" if x <= cx - w + 1 else "H"
        if crumbles and r >= 6:                   # the habit's hem turns to ash
            for x in range(cx - w, cx + w + 1):
                px[(x, y)] = "q" if (x + y) % 3 else "Q"
    for y in range(hy, t + 4):                    # the veil falls down the back to the shoulders
        for x in range(hx - 6, hx - 1):
            px[(x, y)] = "v" if x <= hx - 4 else "V"
    for x in range(hx - 5, hx + 6):
        for y in range(hy - 5, hy + 6):
            d = (x - hx) ** 2 + (y - hy) ** 2
            if d <= 27:
                px[(x, y)] = "v" if x <= hx - 3 else "V"
            fd = (x - hx - 1) ** 2 + (y - hy - 1) ** 2
            if fd <= 15 and d <= 27:
                px[(x, y)] = "F" if fd <= 7 else "C"
    outline_cells(g, px)
    # face: two little eyes, cheek and small mouth
    eyes = {"n": (["K", "K"], ["K", "L"]), "closed": (["k"], ["k"]), "happy": ([".", "K"], [".", "K"]),
             "x": (["K.K", ".K.", "K.K"], None), "angry": (["K", "K"], ["K", "K"]), "up": (["K"], ["L"]),
             "sad": (["K", "K"], ["K", "K"])}[eye]
    ex, ey = hx, hy
    if eye == "x":                               # ">" and "<" little eyes
        stamp(g, ["K.", ".K", "K."], ex - 1, ey - 1)
        stamp(g, [".K", "K.", ".K"], ex + 2, ey - 1)
    else:
        stamp(g, eyes[0], ex, ey)
        stamp(g, eyes[1], ex + 2, ey)
    if eye == "happy":
        g[ey][ex - 1] = g[ey][ex + 1] = g[ey][ex + 3] = "F"
        g[ey][ex], g[ey][ex + 2] = "K", "K"
        g[ey + 1][ex], g[ey + 1][ex + 2] = "F", "F"
    if eye == "angry":
        g[ey - 1][ex] = g[ey - 1][ex + 2] = "K"
    if eye == "up":
        g[ey - 1][ex] = g[ey - 1][ex + 2] = "K"
    g[hy + 2][hx + 3] = "P"                       # cheek
    g[hy + 3][hx + 1] = "f" if eye not in ("x", "sad") else "K"
    if eye == "sad":
        stamp(g, TEAR, hx - 1, hy + 2)
    for a, b in arms:
        _arm(g, a, b)
    if rosary:
        _rosary(g, *rosary)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, leg=1 -> habit 19-28 (cx=13), head 9-19 (hx=14, hy=14); shoulders at (9, 20) and (17, 20)
_T = ((9, 20), (6, 25))                         # back arm loose at the side
_F = ((17, 20), (20, 22))                       # front arm holding the rosary
_SPECS = {
    # standing with the rosary hanging from the front hand; it sways from side to side and she blinks
    "idle": [dict(arms=(_T, _F), rosary=((20, 22), (21, 27))),
             dict(arms=(_T, _F), rosary=((20, 22), (24, 26))),
             dict(arms=(_T, _F), rosary=((20, 22), (26, 25))),
             dict(eye="closed", arms=(_T, _F), rosary=((20, 22), (24, 26))),
             dict(arms=(_T, _F), rosary=((20, 22), (21, 27)))],
    # trotting with the little shoes alternating and the rosary swinging back
    "run_r": [dict(feet=(-2, 2), arms=(((9, 20), (5, 23)), ((17, 20), (21, 21))), rosary=((21, 21), (18, 26))),
              dict(base=29, arms=(((9, 20), (6, 22)), ((17, 20), (21, 22))), rosary=((21, 22), (20, 26))),
              dict(feet=(2, -2), arms=(((9, 20), (5, 23)), ((17, 20), (21, 21))), rosary=((21, 21), (18, 26))),
              dict(base=29, arms=(((9, 20), (6, 22)), ((17, 20), (21, 22))), rosary=((21, 22), (20, 26)))],
    # waves high with the front hand; the rosary spins hanging from the wrist
    "waving": [dict(eye="happy", arms=(_T, ((17, 20), (23, 14))), rosary=((23, 14), (26, 18))),
               dict(eye="happy", arms=(_T, ((17, 20), (21, 10))), rosary=((21, 10), (25, 13))),
               dict(eye="happy", arms=(_T, ((17, 20), (26, 12))), rosary=((26, 12), (27, 17))),
               dict(eye="happy", arms=(_T, ((17, 20), (21, 10))), rosary=((21, 10), (25, 13)))],
    # crouches, jumps with the rosary raised, comes down, lands
    "jumping": [dict(leg=0, eye="closed", arms=(((9, 21), (5, 25)), ((17, 21), (21, 24))),
                     rosary=((21, 24), (23, 27))),
                dict(base=28, eye="up", arms=(((9, 18), (5, 14)), ((17, 18), (22, 12))),
                     rosary=((22, 12), (25, 16))),
                dict(base=26, eye="happy", arms=(((9, 16), (4, 11)), ((17, 16), (23, 9))),
                     rosary=((23, 9), (26, 13))),
                dict(base=28, arms=(((9, 18), (5, 21)), ((17, 18), (22, 16))), rosary=((22, 16), (24, 21))),
                dict(leg=0, eye="happy", arms=(((9, 21), (5, 25)), ((17, 21), (21, 24))),
                     rosary=((21, 24), (23, 27)))],
    # crumbles into ash: cries, the habit crumbles, becomes a little ash mound with the veil on top and the rosary beside it
    "failed": [dict(eye="sad", arms=(_T, _F), rosary=((20, 22), (21, 27))),
               dict(eye="x", crumbles=True, arms=(((9, 20), (5, 24)), ((17, 20), (22, 24))),
                    rosary=((22, 24), (25, 27)), por=((GREY, 4, 27), (GREY, 24, 29), (GREY, 7, 30))),
               dict(mound=1, por=((SKULL, 24, 25), (SMOKE, 18, 10), (GREY, 6, 19))),
               dict(mound=2, por=((SKULL, 24, 25), (SMOKE_S, 21, 9), (SMOKE, 18, 4))),
               dict(mound=2, por=((SKULL, 24, 25), (SMOKE_S, 22, 2)))],
    # naps with the head down, rosary hanging, "z" rising
    "waiting": [dict(leg=0, eye="closed", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29))),
                dict(leg=0, eye="closed", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29)), por=((Z_S, 24, 7),)),
                dict(leg=0, eye="closed", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29)), por=((Z_S, 23, 8), (Z_L, 25, 0))),
                dict(leg=0, eye="closed", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29)), por=((Z_L, 25, 0),))],
    # whip: raises the rosary back up high, swings it forward (streaks), the little skull cracks into embers
    "running": [dict(cx=11, eye="angry", arms=(((7, 20), (4, 25)), ((15, 20), (19, 7))),
                     rosary=((19, 7), (9, 1))),
                dict(cx=11, eye="angry", arms=(((7, 20), (4, 25)), ((15, 20), (21, 17))),
                     rosary=((21, 17), (27, 12)), por=((STREAK, 21, 5),)),
                dict(cx=11, eye="angry", arms=(((7, 20), (4, 25)), ((15, 20), (22, 19))),
                     rosary=((21, 18), (27, 15)), por=((EMBER, 19, 3),)),
                dict(cx=11, eye="happy", arms=(((7, 20), (4, 25)), ((15, 20), (20, 22))),
                     rosary=((20, 22), (22, 27)), por=((FLICKER, 25, 9), (FLICKER_Y, 28, 14), (FLICKER, 23, 4)))],
    # hand on the chin, looking up, "?" appears; the rosary hanging from the other hand
    "review": [dict(eye="up", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (4, 28))),
               dict(eye="up", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (4, 28)),
                    por=((QMARK_S, 24, 4),)),
               dict(eye="up", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (5, 28)),
                    por=((QMARK, 24, 2),)),
               dict(eye="n", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (4, 28)),
                    por=((QMARK, 24, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# 17x18 grid attached 8 to the left and 12 above the habit top (habit from row 12, center on column 8;
# head centered at (9, 7), top of the veil on row 2): charcoal cord at the waist with ember knots; lit embers
# sprinkled on the veil, from the top down to the hem on the back (on the `failed` ash mound they rise loose as
# sparks, and the cord lies fallen in the ash)
_CORD = [
    "KKKKKKKKKKK",
    "dQdOdQdQdOd",
    "KKKKKKKKKKK",
]
_EMBER_S = ["YO", "Oo"]


def _extra(pieces, w=17, h=18):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != "." and 0 <= y + dy < h and 0 <= x + dx < w:
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CORD = _extra(((_CORD, 3, 15),))
CORD_EMBERS = _extra(((_EMBER_S, 7, 3), (_EMBER_S, 4, 6), (_EMBER_S, 4, 11), (["Y"], 6, 9), (["O"], 11, 1),
                        (["Y"], 3, 0), (_CORD, 3, 15)))
STAGES = [
    {"title": "Ash Novice", "floor": 1, "extra": None},
    {"title": "Ash Nun", "floor": 4, "extra": CORD},
    {"title": "Ash Abbess", "floor": 10, "extra": CORD_EMBERS},
]
