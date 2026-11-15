"""Built-in Slime, 32 px. Each frame is made of parts: body (parametric dome with outline, shade and shine),
face (eyes, mouth, cheeks) and overlays (droplet, little arm, "z", "?", puddle).
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, mirror, stamp

PAL = {
    "K": "#1b1b2f", "G": "#57d36b", "L": "#b4f5a8", "D": "#2f9a4a",
    "W": "#ffffff", "B": "#1b1b2f", "P": "#ff8fb1", "R": "#c8304a",
    "S": "#d7dde9", "s": "#8a94a8", "Y": "#ffd23f", "y": "#c99a00", "T": "#8fd8ff",
}

# ---- face parts (left eye; the right one is the mirror, except where the shine must stay on the same side)
EYE = ["WB", "BB", "BB", "BB"]
EYE_CLOSED = ["...", "...", "BBB"]
EYE_HAPPY = [".B.", "B.B"]
EYE_X = ["B.B", ".B.", "B.B"]
EYE_UP = ["WB", "BB", ".."]
BROW_ANGRY = ["BB..", "..BB"]          # left: slopes down inward
BROW_SAD = ["..BB", "BB.."]         # left: slopes down outward
MOUTH = {
    "sorriso": ["B..B", ".BB."],
    "aberta": ["BBBBB", "BRRRB", "BRPRB", ".BBB."],
    "dentes": ["BBBBB", "BWBWB", ".BBB."],
    "o": [".B.", "B.B", ".B."],
    "triste": [".BB.", "B..B"],
    "reta": ["BBB"],
}

DROP = [".K.", "KGK", "KDK", ".K."]
DROP_S = ["K", "K"]
# little goo arm (root at the bottom left): down, horizontal, diagonal, up = the wave arc
ARM_DOWN = ["KKK......", "KGGKK....", "KGGGGKK..", ".KKGGGGK.", "...KKGGLK", ".....KKK."]
ARM_HOR = ["......KKK.", "KKKKKKGGLK", "KGGGGGGGGK", "KGGGGGGGDK", "KKKKKKKKK."]
ARM_DIAG = [".....KKK", "....KGLK", "...KGGGK", "..KGGGK.", ".KGGGK..", "KGGGK...", "KGGK....", "KKK....."]
ARM_UP = [".KKK.", "KGLGK", "KGGGK", "KGGGK", "KGGK.", "KGGK.", "KGGK.", "KKK.."]




def _body(w, h, cx, base, lean):
    """Dome: wide at the bottom, round at the top; `lean` shifts the top (lean forward or tilt)."""
    pts = set()
    for y in range(base - h + 1, base + 1):
        u = (base - y) / h                      # 0 at the base, ~1 at the top
        half = w / 2 * (1 - u ** 2.4) ** 0.5
        c = cx + lean * u
        for x in range(round(c - half), round(c + half)):
            if 0 < x < N - 1:
                pts.add((x, y))
    return pts


def frame(w, h, cx=16, base=30, lean=0, eyes="normal", look=0, mouth="sorriso", cheek=True, por=()):
    """One 32x32 frame and the anchor (top of the body) for the stage's add-on."""
    g = [["."] * N for _ in range(N)]
    pts = _body(w, h, cx, base, lean)
    top = min(y for _, y in pts)
    xs_top = sorted(x for x, y in pts if y == top)
    for x, y in pts:
        dir_ = (x + 1, y) not in pts or (x + 2, y) not in pts
        g[y][x] = "D" if (y >= base - 1 or dir_) else "G"
    for x, y in pts:                              # 4-neighbor outline
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in pts and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # shine at the top left
    bx, by = round(cx + lean * 0.75 - w * 0.28), top + max(1, h // 6)
    for x, y in ((bx, by), (bx + 1, by), (bx, by + 1), (bx + 2, by - 1)):
        if (x, y) in pts and g[y][x] == "G":
            g[y][x] = "L"
    # face
    ey = top + max(1, int(h * 0.38))
    fx = round(cx + lean * (base - ey) / h) + look
    lx, rx = fx - 5, fx + 3
    if eyes == "fechado":
        stamp(g, EYE_CLOSED, lx - 1, ey); stamp(g, EYE_CLOSED, rx, ey)
    elif eyes == "feliz":
        stamp(g, EYE_HAPPY, lx - 1, ey + 1); stamp(g, EYE_HAPPY, rx, ey + 1)
    elif eyes == "x":
        stamp(g, EYE_X, lx - 1, ey); stamp(g, EYE_X, rx, ey)
    elif eyes == "cima":
        stamp(g, EYE_UP, lx, ey - 1); stamp(g, EYE_UP, rx, ey - 1)
    else:
        stamp(g, EYE, lx, ey); stamp(g, EYE, rx, ey)
        if eyes == "bravo":
            stamp(g, BROW_ANGRY, lx - 2, ey - 3); stamp(g, mirror(BROW_ANGRY), rx, ey - 3)
        elif eyes == "triste":
            stamp(g, BROW_SAD, lx - 2, ey - 3); stamp(g, mirror(BROW_SAD), rx, ey - 3)
    if mouth:
        b = MOUTH[mouth]
        stamp(g, b, fx - len(b[0]) // 2, ey + 5)
    if cheek and eyes in ("normal", "feliz", "fechado"):
        for x in (lx - 3, lx - 2, rx + 3, rx + 4):
            if (x, ey + 4) in pts:
                g[ey + 4][x] = "P"
    for s, x, y in por:
        stamp(g, s, x, y)
    cxt = (xs_top[0] + xs_top[-1]) // 2
    return ["".join(l) for l in g], (cxt - 5, top - 4)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


_SPECS = {
    # breathes (stretches and squashes) and blinks on the 3rd frame
    "idle": [dict(w=24, h=18), dict(w=25, h=17), dict(w=25, h=17, eyes="fechado"), dict(w=23, h=19)],
    # stretches forward, eyes facing the way, a droplet left behind
    "run_r": [dict(w=24, h=16, cx=18, lean=4, look=2, por=((DROP, 2, 25),)),
              dict(w=23, h=18, cx=18, lean=3, look=2, por=((DROP, 0, 26), (DROP_S, 4, 29))),
              dict(w=25, h=15, cx=17, lean=5, look=3, por=((DROP_S, 2, 29),)),
              dict(w=24, h=17, cx=18, lean=4, look=2, por=((DROP, 3, 26),))],
    # little goo arm comes out on the right and waves
    "waving": [dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_DOWN, 22, 18),)),
               dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_HOR, 22, 16),)),
               dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_DIAG, 22, 11),)),
               dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_UP, 22, 9),))],
    # crouches, stretches in the air, high, falls, flattens on landing
    "jumping": [dict(w=28, h=12, eyes="fechado", mouth="reta"),
                dict(w=18, h=23, base=27, mouth="o"),
                dict(w=22, h=19, base=22, eyes="feliz", mouth="aberta"),
                dict(w=20, h=21, base=29, mouth="o"),
                dict(w=28, h=11, eyes="feliz")],
    # melts into a puddle; X eyes on the last one
    "failed": [dict(w=24, h=18, eyes="triste", mouth="triste", por=((TEAR, 9, 21),)),
               dict(w=26, h=14, eyes="triste", mouth="triste", por=((DROP, 1, 27), (DROP, 28, 27))),
               dict(w=28, h=10, eyes="triste", mouth="reta", por=((DROP_S, 0, 29), (DROP_S, 31, 29))),
               dict(w=30, h=7, eyes="fechado", mouth=None, cheek=False),
               dict(w=30, h=7, eyes="x", mouth=None)],
    # head tilts sideways, eyes closed, "z" rising
    "waiting": [dict(w=25, h=17, cx=14, lean=-2, eyes="fechado", mouth=None),
                dict(w=26, h=16, cx=14, lean=-4, eyes="fechado", mouth=None, por=((Z_S, 21, 7),)),
                dict(w=26, h=16, cx=14, lean=-4, eyes="fechado", mouth="o", por=((Z_S, 21, 7), (Z_L, 25, 1))),
                dict(w=25, h=17, cx=14, lean=-3, eyes="fechado", mouth=None, por=((Z_L, 25, 0),))],
    # lunges and bites: pulls back, charges with an open mouth, snaps its teeth
    "running": [dict(w=25, h=16, cx=15, lean=-3, eyes="bravo", mouth="reta"),
                dict(w=26, h=16, cx=16, lean=5, look=3, eyes="bravo", mouth="aberta"),
                dict(w=26, h=17, cx=16, lean=4, look=3, eyes="bravo", mouth="dentes"),
                dict(w=24, h=18, cx=15, lean=1, look=1, eyes="bravo", mouth="aberta")],
    # looks up and the "?" appears
    "review": [dict(w=24, h=18, cx=14, eyes="cima", mouth="reta"),
               dict(w=24, h=18, cx=14, eyes="cima", mouth="o", por=((QMARK_S, 24, 7),)),
               dict(w=23, h=19, cx=14, eyes="cima", mouth="o", por=((QMARK, 24, 3),)),
               dict(w=24, h=18, cx=14, eyes="cima", mouth="o", por=((QMARK, 24, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

BLINK = FRAMES["idle"][2]     # idle frame with the eyes closed

HELM = [
    "...KKKK...",
    "..KSSSSK..",
    ".KSSSSSsK.",
    "KSSRSSSSsK",
    "KKKKKKKKKK",
]
HERO_CROWN = [
    ".K...K...K.",
    "KYK.KYK.KYK",
    "KYYKYRYKYYK",
    "KYYYYYYYYYK",
    "KyyyyyyyyyK",
    ".KKKKKKKKK.",
]
STAGES = [
    {"title": "Gotinha", "floor": 1, "extra": None},
    {"title": "Slime", "floor": 4, "extra": HELM},
    {"title": "Rei Slime", "floor": 10, "extra": HERO_CROWN},
]
