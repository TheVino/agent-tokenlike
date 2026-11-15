"""Ghost, 32 px. Each frame is made of parts: sheet (dome with a wavy hem, outline, shade and shine),
face (eyes, mouth, cheeks) and overlays (little sheet hand, trail, "z", "?", holes, fading).
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
import math
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, EXCLAM, TEAR, mirror, stamp

PAL = {
    "K": "#2a2140", "G": "#f2f0ff", "D": "#c6c0e8", "L": "#ffffff", "B": "#2a2140", "W": "#ffffff",
    "P": "#ff9ec4", "R": "#c8304a", "H": "#7b5cc9", "h": "#4f3a8f", "Y": "#ffd23f", "y": "#c99a00",
    "T": "#8fd8ff", "S": "#d7dde9", "s": "#8a94a8",
}

EYE = [".BB.", "BWBB", "BBBB", "BBBB", ".BB."]
EYE_CLOSED = ["....", "B..B", ".BB."]       # half-moon facing down (sleep)
EYE_HAPPY = [".BB.", "B..B"]
EYE_X = ["B..B", ".BB.", ".BB.", "B..B"]
EYE_UP = [".BB.", "BWBB", "BBBB", "...."]
BROW_ANGRY = ["BB...", "..BBB"]
BROW_SAD = ["...BB", "BBB.."]
MOUTH = {
    "smile": ["B...B", ".BBB."],
    "boo": [".BBB.", "BRRRB", "BRRRB", "BRPRB", ".BBB."],
    "boo_l": [".BBBB.", "BRRRRB", "BRRRRB", "BRRRRB", "BRPPRB", ".BBBB."],
    "o": [".B.", "B.B", ".B."],
    "sad": [".BBB.", "B...B"],
    "straight": ["BBB"],
    "crooked": ["BB..", "..BB"],
}

# little sheet hand (root on the left, attached to the body): low, straight, high, waving up high
HAND_LOW = ["KK.......", "GGKK.....", "GGGGKK...", "KGGGGGKK.", ".KKGGGGLK", "...KKGGGK", ".....KKK."]
HAND_STRAIGHT = ["......KKK.", "KKKKKKGGLK", "GGGGGGGGGK", "GGGGGGGGDK", "KKKKKKKKK."]
HAND_HIGH = [".....KKK", "....KGLK", "...KGGGK", "..KGGGK.", ".KGGGK..", "KGGGK...", "GGGK....", "KKK....."]
HAND_UP = [".KKK.", "KGLGK", "KGGGK", "KGGGK", "KGGK.", "KGGK.", "KGGK.", "GGGK.", "KKK.."]
# scratching its head: arm bent over the top (root at the bottom right)
ITCH_A = ["..KKKK..", ".KGGLGK.", "KGGGGGGK", "KGKKKGGK", "KK..KGGK", "....KGGK", "....KGGK", "....GGGK", "....KKK."]
ITCH_B = [".KKKK...", "KGLGGK..", "KGGGGGK.", ".KKKGGGK", "....KGGK", "....KGGK", "....KGGK", "....GGGK", "....KKK."]
TRAIL_1 = ["KKKKKK", "DDDDDK", "KKKKKK"]
TRAIL_2 = ["KKK", "DDK", "KKK"]




def _bedsheet(w, h, cx, base, lean, phase):
    """Dome on top, straight sides and a hem with 3 points waving (`phase`); `lean` shifts the top."""
    pts = set()
    r = w / 2
    top = base - h + 1
    for y in range(top, base + 1):
        u = (base - y) / h
        d = y - top
        half = r if d >= r else (r * r - (r - d - 0.5) ** 2) ** 0.5
        c = cx + lean * u
        for x in range(round(c - half), round(c + half)):
            wave = 1.6 + 1.6 * math.sin(2 * math.pi * (x - c) / (w / 3) + phase)
            if 0 < x < N - 1 and y <= base - round(wave):
                pts.add((x, y))
    return pts


def frame(w=20, h=24, cx=16, base=30, lean=0, phase=0.0, eyes="normal", look=0, mouth="smile",
           cheek=True, por=(), holes=(), some=0):
    """One 32x32 frame and the anchor (top of the head) for the stage's add-on."""
    g = [["."] * N for _ in range(N)]
    pts = _bedsheet(w, h, cx, base, lean, phase)
    for bx, by, br in holes:
        pts -= {(x, y) for x, y in pts if (x - bx) ** 2 + (y - by) ** 2 <= br * br}
    top = min(y for _, y in pts)
    xs_top = sorted(x for x, y in pts if y == top)
    for x, y in pts:
        dir_ = (x + 1, y) not in pts or (x + 2, y) not in pts
        low = (x, y + 1) not in pts or (x, y + 2) not in pts
        g[y][x] = "D" if (dir_ or low) else "G"
    for x, y in pts:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in pts and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # shine at the top left
    bx, by = round(cx + lean * 0.8 - w * 0.25), top + 2
    for x, y in ((bx, by), (bx + 1, by - 1), (bx, by + 1), (bx, by + 2)):
        if (x, y) in pts and g[y][x] == "G":
            g[y][x] = "L"
    if some:   # fading (before the face, which stays sharp): checkerboard from the bottom up (1/4, 1/2); fade >= 3 leaves the end sparse (1 in 4)
        corte = base - h * min(some, 2) // 4
        for y in range(N):
            for x in range(N):
                if g[y][x] != "." and y > corte and ((x + y) % 2 or (some >= 3 and y > corte + 4 and y % 2)):
                    g[y][x] = "."
    ey = top + max(3, int(h * 0.27))
    fx = round(cx + lean * (base - ey) / h) + look
    lx, rx = fx - 6, fx + 2
    if eyes == "closed":
        stamp(g, EYE_CLOSED, lx, ey); stamp(g, EYE_CLOSED, rx, ey)
    elif eyes == "happy":
        stamp(g, EYE_HAPPY, lx, ey + 1); stamp(g, EYE_HAPPY, rx, ey + 1)
    elif eyes == "x":
        stamp(g, EYE_X, lx, ey); stamp(g, EYE_X, rx, ey)
    elif eyes == "up":
        stamp(g, EYE_UP, lx, ey - 1); stamp(g, EYE_UP, rx, ey - 1)
    else:
        stamp(g, EYE, lx, ey); stamp(g, EYE, rx, ey)
        if eyes == "angry":
            stamp(g, BROW_ANGRY, lx - 1, ey - 2); stamp(g, mirror(BROW_ANGRY), rx, ey - 2)
        elif eyes == "sad":
            stamp(g, BROW_SAD, lx - 1, ey - 2); stamp(g, mirror(BROW_SAD), rx, ey - 2)
    if mouth:
        b = MOUTH[mouth]
        stamp(g, b, fx - len(b[0]) // 2, ey + 6)
    if cheek and eyes in ("normal", "happy", "closed"):
        for x in (lx - 2, lx - 1, rx + 4, rx + 5):
            if (x, ey + 5) in pts:
                g[ey + 5][x] = "P"
    for s, x, y in por:
        stamp(g, s, x, y)
    cxt = (xs_top[0] + xs_top[-1]) // 2
    return ["".join(l) for l in g], (cxt - 7, ey - 11)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


_F = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
_SPECS = {
    # floats slowly, hem waving; blinks on the 3rd frame
    "idle": [dict(base=30, phase=_F[0]), dict(base=29, phase=_F[1]),
             dict(base=29, phase=_F[2], eyes="closed"), dict(base=30, phase=_F[3])],
    # leans forward, looking ahead, a sheet trail left behind
    "run_r": [dict(cx=18, lean=4, look=2, phase=_F[0], por=((TRAIL_1, 2, 22), (TRAIL_2, 0, 26))),
              dict(cx=18, lean=5, look=2, base=29, phase=_F[1], por=((TRAIL_1, 1, 20), (TRAIL_2, 3, 26))),
              dict(cx=18, lean=4, look=2, phase=_F[2], por=((TRAIL_2, 2, 21), (TRAIL_1, 0, 25))),
              dict(cx=18, lean=5, look=2, base=29, phase=_F[3], por=((TRAIL_1, 2, 24), (TRAIL_2, 1, 19)))],
    # little sheet hand comes out on the right and waves
    "waving": [dict(cx=13, eyes="happy", mouth="boo", phase=_F[0], por=((HAND_LOW, 22, 17),)),
               dict(cx=13, eyes="happy", mouth="boo", phase=_F[1], por=((HAND_STRAIGHT, 22, 14),)),
               dict(cx=13, eyes="happy", mouth="boo", phase=_F[2], por=((HAND_HIGH, 22, 8),)),
               dict(cx=13, eyes="happy", mouth="boo", phase=_F[3], por=((HAND_UP, 22, 6),))],
    # shrinks, shoots up, opens its arms at the top, comes down, lands
    "jumping": [dict(w=24, h=22, eyes="closed", mouth="straight"),
                dict(w=16, h=24, base=30, mouth="o", phase=_F[1]),
                dict(w=20, h=21, base=27, eyes="happy", mouth="boo", phase=_F[2]),
                dict(w=18, h=22, base=29, mouth="o", phase=_F[3]),
                dict(w=23, h=20, eyes="happy")],
    # sad, holes open in the sheet and it slowly fades away
    "failed": [dict(eyes="sad", mouth="sad", por=((TEAR, 10, 17),)),
               dict(eyes="sad", mouth="sad", phase=_F[1], holes=((12, 27, 1.5), (21, 24, 1.2))),
               dict(eyes="sad", mouth="straight", phase=_F[2], holes=((12, 27, 2), (21, 24, 1.8), (16, 20, 1)), some=1),
               dict(eyes="closed", mouth=None, cheek=False, phase=_F[3],
                    holes=((12, 27, 2.5), (21, 24, 2.2), (16, 20, 1.5)), some=2),
               dict(eyes="x", mouth=None, cheek=False, base=30, holes=((21, 22, 2),), some=3)],
    # naps floating sideways, "z" rising
    "waiting": [dict(cx=14, lean=-2, eyes="closed", mouth=None, base=30),
                dict(cx=14, lean=-3, eyes="closed", mouth=None, base=29, phase=_F[1], por=((Z_S, 22, 6),)),
                dict(cx=14, lean=-3, eyes="closed", mouth="o", base=29, phase=_F[2], por=((Z_S, 22, 6), (Z_L, 26, 0))),
                dict(cx=14, lean=-2, eyes="closed", mouth=None, base=29, phase=_F[3], por=((Z_L, 26, 0),))],
    # pulls back and charges with an open mouth: "Boo!"
    "running": [dict(cx=14, lean=-3, eyes="angry", mouth="straight"),
                dict(cx=17, lean=5, look=1, eyes="angry", mouth="boo", phase=_F[1], por=((TRAIL_2, 3, 22),)),
                dict(cx=18, lean=6, look=1, w=21, eyes="angry", mouth="boo_l", phase=_F[2],
                     por=((TRAIL_1, 1, 20), (EXCLAM, 28, 2))),
                dict(cx=16, lean=3, look=2, eyes="angry", mouth="boo", phase=_F[3], por=((EXCLAM, 28, 3),))],
    # scratches its head and the "?" appears
    "review": [dict(cx=14, eyes="up", mouth="crooked"),
               dict(cx=14, eyes="up", mouth="crooked", phase=_F[1], por=((ITCH_A, 17, 4), (QMARK_S, 26, 4))),
               dict(cx=14, eyes="up", mouth="o", phase=_F[2], por=((ITCH_B, 17, 4), (QMARK, 25, 0))),
               dict(cx=14, eyes="up", mouth="o", phase=_F[3], por=((ITCH_A, 17, 4), (QMARK, 25, 0)))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# hat: 5 cone rows above the head + brim (anchor = eyes - 11; on the tall sheet the brim sits on the top)
HAT = [
    ".........KK...",
    ".......KKHK...",
    ".....KKHHYK...",
    "....KHHYHHHK..",
    "...KHHhhhhHHK.",
    ".KKhhhhhhhhhhK",
    "KhhhhhhhhhhhhK",
    ".KKKKKKKKKKKK.",
]
# little chain on the neck, just below the widest mouth ("boo"), on the same anchor
CHAIN = ["." * 14] * 22 + [
    "KsKsKsKsKsKsKs",
    "......KK......",
    ".....KYYK.....",
    "......KK......",
]
MAGE = [HAT[i] if i < len(HAT) else CHAIN[i] for i in range(len(CHAIN))]
STAGES = [
    {"title": "Little Ghost", "floor": 1, "extra": None},
    {"title": "Ghost", "floor": 4, "extra": CHAIN},
    {"title": "Ghost Mage", "floor": 10, "extra": MAGE},
]
