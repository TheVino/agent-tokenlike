"""Messenger Crow, 32 px, facing right. A round little crow with slate feathers, amber beak, bright white
eye, fan tail and big wings with light tips. The symbol is the sealed letter (cream envelope with a red
seal), which it carries in its beak: it sways in idle and becomes a weapon in the `running` double peck. In `failed` it takes the
hit, the letter slips from the beak and flies away while the crow collapses with open wings, a loose feather in the air.
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, mirror, trait

PAL = {
    "K": "#0d0a12", "B": "#3d3858", "b": "#29253c", "P": "#5e5882", "A": "#4b4574", "a": "#9a94c8",
    "W": "#f4f6fb", "Y": "#f0b030", "y": "#a8701c", "L": "#e0913a", "C": "#f4ead2", "c": "#c9b994",
    "R": "#c8334a", "r": "#7e1f33", "D": "#7a4a28", "d": "#4e2e16", "H": "#5a2a6e", "h": "#3a1a48",
    "G": "#ffd23f", "g": "#b8860b", "T": "#8fd8ff", "N": "#7f92d6",
}

BODY = (3, 5, 6, 7, 7, 7, 7, 7, 6, 6, 5, 3)           # body half-width per row (12 rows)
BODY_LOW = (4, 6, 7, 7, 7, 7, 6, 5, 3)              # crouched body (9 rows)
BODY_FLAT = (5, 7, 8, 8, 8, 7, 5)                    # collapsed body (7 rows)
HEAD = (2, 4, 5, 5, 5, 5, 5, 4, 3)                   # head half-width (9 rows)

CARD = [
    "KKKKKKKKK",
    "KCcCCCcCK",
    "KCCcRRCCK",
    "KCCCrRCCK",
    "KKKKKKKKK",
]
CARD_STANDING = [                                         # the rotated letter (flying in failed)
    "KKKKK",
    "KCCCK",
    "KcCCK",
    "KCcCK",
    "KCRrK",
    "KCRRK",
    "KCcCK",
    "KcCCK",
    "KKKKK",
]
# raised wing (tips up), the base touches the back
WING_UP = [
    "K.K.K.....",
    "KaKaKK....",
    "KaKaKaK...",
    "KaAaAaAK..",
    "KAAAAAAaK.",
    ".KAAAAAAAK",
    "..KAAAAAAK",
    "...KAAAAK.",
    "....KKKK..",
]
WING_DOWN = WING_UP[::-1]                              # pushing the air down
WING_WAVE = mirror(WING_UP)                           # tips forward (waving)
WING_FRONT = [                                          # stretched forward, tips to the right
    ".KKKKKKKKK...",
    "KAAAAAAAAAKK.",
    "KAAAAAAaaaaaK",
    ".KAAAAaKaKaKK",
    "..KKKKK.K.K..",
]
WING_CLOSED = [
    "..KKKKKK.",
    ".KAAAAAAK",
    "KAaAAAAAK",
    "KAAaAAAK.",
    ".KAAaAK..",
    "..KaAK...",
    "...KK....",
]
WING_DROOP = [                                           # wing dropped on the ground
    ".KKKKKKK..",
    "KAAAAAAAKK",
    "KaAaAaAaAK",
    ".KaKaKaKK.",
    "..K.K.K...",
]
SHINE = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
SHINE_S = [".K.", "KWK", ".K."]
FEATHER = ["...KK", "..KaK", ".KaAK", "KaAK.", "KKK.."]
WIND = ["KKKK...", "..KKKK.", "....KKK"]                # little wind streaks of the wing strike


def frame(cx=12, base=30, leg=3, body=BODY, eye="n", beak="f", card="bico", cdy=0, wing=(WING_CLOSED, -5, -2),
           feet=(0, 0), por=(), behind=()):
    """One 32x32 frame and the add-on anchor (10 to the left and 5 above the head top).
    `wing`: (sprite, dx, dy) relative to the body center; `card`: "bico" (held in the beak, `cdy` sways),
    None or an absolute (sprite, x, y)."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    backdrop = base - leg - 1
    bt = backdrop - len(body) + 1
    htop, hx = bt - 6, cx + 3
    for i, px in enumerate((cx - 2, cx + 2)):          # little legs with toes
        if leg:
            x = px + feet[i]
            trait(g, (x, backdrop), (x, base - 1), "L")
            trait(g, (x - 1, base), (x + 1, base), "L")
    px = {}
    for r, w in enumerate(body):
        y = bt + r
        for x in range(cx - w, cx + w + 1):
            front = x > cx and r > len(body) // 3
            px[(x, y)] = "P" if front else ("b" if x <= cx - w + 1 else "B")
    tail_tip = ((-11, -6), (-12, -6), (-12, -7), (-11, -9))  # tail fan, backward and downward
    for i, (a, b) in enumerate(tail_tip):
        for x in range(cx + a, cx + b + 1):
            px[(x, bt + 5 + i)] = "B" if (x + i) % 3 == 0 else "b"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, htop + r)] = "P" if r == 1 and x < hx + 2 else "B"
    if beak == "f":
        parts = ((4, 4, 8, "Y"), (5, 4, 9, "Y"), (6, 4, 7, "y"))
    else:                                               # open: a dark gap between the two halves
        parts = ((3, 4, 8, "Y"), (4, 4, 9, "Y"), (6, 4, 8, "y"))
    for r, a, b, color in parts:
        for x in range(hx + a, hx + b + 1):
            px[(x, htop + r)] = color
    for (x, y), c in list(px.items()):                  # bluish shine at the top of the feathers (contrast on a dark background)
        if c in "BbP" and (x, y - 1) not in px:
            px[(x, y)] = "N"
    outline_cells(g, px)
    if beak != "f":
        for x in range(hx + 5, hx + 9):
            g[htop + 5][x] = "K"
    ex, ey = hx + 1, htop + 3
    eyes = {"n": ["WK", "WW"], "baixo": ["WW", "WK"], "fechado": ["..", "aa"], "feliz": [".W.", "W.W"],
             "x": ["W.W", ".W.", "W.W"], "triste": ["a..", "WW.", "WK."], "bravo": ["aa.", ".aa", ".WK"]}[eye]
    stamp(g, eyes, ex - (eye in ("triste", "bravo", "x")), ey - (eye in ("triste", "bravo", "x")))
    if eye == "triste":
        stamp(g, TEAR, ex, ey + 2)
    if wing:
        s, dx, dy = wing
        stamp(g, s, cx + dx, bt + 5 + dy)
    if card == "bico":
        stamp(g, CARD, hx + 7, htop + 4 + cdy)
    elif card:
        stamp(g, *card)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (hx - 10, htop - 5)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, leg=3 -> body 15-26 (center x=12), head 9-17 (center x=15), beak up to x=24, letter at 22-30
_SPECS = {
    # standing with the letter in the beak, which sways; blinks once
    "idle": [dict(), dict(cdy=1), dict(cdy=1, eye="fechado"), dict(), dict(cdy=-1)],
    # trotting on its little legs, wings half open flapping, letter firm in the beak
    "run_r": [dict(feet=(-2, 2), wing=(WING_CLOSED, -6, -3)),
              dict(base=29, leg=2, wing=(WING_UP, -11, -10)),
              dict(feet=(2, -2), wing=(WING_CLOSED, -6, -3)),
              dict(base=29, leg=2, wing=(WING_UP, -11, -10))],
    # waves the raised wing from side to side, happy eye
    "waving": [dict(eye="feliz", wing=(WING_UP, -11, -12)),
               dict(eye="feliz", wing=(WING_WAVE, -9, -13)),
               dict(eye="feliz", wing=(WING_UP, -11, -12)),
               dict(eye="feliz", wing=(WING_WAVE, -9, -13))],
    # crouches, pushes the air with the wings, rises with open wings, comes down and lands
    "jumping": [dict(leg=1, body=BODY_LOW, eye="fechado", wing=(WING_CLOSED, -5, -3)),
                dict(base=28, wing=(WING_DOWN, -7, -1)),
                dict(base=26, eye="feliz", wing=(WING_UP, -11, -12)),
                dict(base=27, wing=(WING_UP, -11, -11)),
                dict(leg=1, body=BODY_LOW, eye="feliz", wing=(WING_CLOSED, -5, -3))],
    # takes the hit, drops the letter (which flies away) and collapses on the ground with open wings
    "failed": [dict(eye="triste", beak="a", card=(CARD, 22, 16)),
               dict(eye="x", beak="a", leg=2, body=BODY_LOW, wing=(WING_UP, -11, -10),
                    card=(CARD_STANDING, 25, 6), por=((FEATHER, 25, 20),)),
               dict(eye="x", beak="a", leg=0, body=BODY_FLAT, wing=(WING_DROOP, -12, 1),
                    card=(CARD, 22, 1), por=((FEATHER, 24, 15),)),
               dict(eye="x", leg=0, body=BODY_FLAT, wing=(WING_DROOP, -12, 1),
                    card=(CARD_STANDING, 26, 0), por=((FEATHER, 23, 22),)),
               dict(eye="x", leg=0, body=BODY_FLAT, wing=(WING_DROOP, -12, 1),
                    card=None, por=((FEATHER, 25, 25),))],
    # naps sitting, head low, letter on the ground beside it, "z" rising
    "waiting": [dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26)),
                dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26), por=((Z_S, 25, 7),)),
                dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26),
                     por=((Z_S, 24, 8), (Z_L, 26, 0))),
                dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26), por=((Z_L, 26, 0),))],
    # double peck: winds back, pecks with the letter (shine), pecks again with a wing strike, returns
    "running": [dict(cx=11, eye="bravo", wing=(WING_UP, -11, -12)),
                dict(cx=13, eye="bravo", wing=(WING_DOWN, -8, -1), cdy=-1, por=((SHINE, 25, 5),)),
                dict(cx=13, eye="bravo", wing=(WING_FRONT, 0, 3), cdy=1,
                     por=((SHINE, 25, 12), (SHINE_S, 29, 7), (WIND, 24, 27))),
                dict(cx=12, eye="bravo", wing=(WING_CLOSED, -5, -2))],
    # reads the letter held at the wing tip, eye down; "?" appears
    "review": [dict(eye="baixo", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3)),
               dict(eye="baixo", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3), por=((QMARK_S, 25, 3),)),
               dict(eye="n", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3), por=((QMARK, 25, 1),)),
               dict(eye="baixo", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3), por=((QMARK, 25, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# 16x20 grid attached 10 to the left and 5 above the head top (head on rows 5-13, center on column 10;
# body from row 11, center on column 7): letter bag on the chest with a strap around the neck; purple herald
# hood with a golden plume
_BAG = [
    "K.......",
    "dK......",
    ".dK.KKK.",
    "..dKCCK.",
    "..KKKKKKK",
    "..KDDDDDK",
    "..KdddddK",
    "..KDDGDDK",
    "..KDDDDDK",
    "...KKKKK.",
]
_HOOD = [
    "...KK...........",
    "..KGGK..........",
    "..KGgGK.........",
    "...KGgGKKKK.....",
    "....KHHHHHHKK...",
    "...KHHHHHHHHHK..",
    "..KHhHHHHHHHHHK.",
    "..KHhHHHHKKKKKK.",
    "..KHHhHHK.......",
    "..KHHhHK........",
    "...KKKK.........",
]


def _extra(pieces, w=16, h=20):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BAG = _extra(((_BAG, 6, 10),))
BAG_HOOD = _extra(((_BAG, 6, 10), (_HOOD, 0, 0)))
STAGES = [
    {"title": "Filhote de Corvo", "floor": 1, "extra": None},
    {"title": "Corvo Mensageiro", "floor": 4, "extra": BAG},
    {"title": "Corvo Arauto", "floor": 10, "extra": BAG_HOOD},
]
