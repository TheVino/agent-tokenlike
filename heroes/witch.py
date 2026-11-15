"""Swamp Witch, 32 px, facing right. Each frame is made of parts: purple bell dress, light green head
with a pointy nose and moss hair behind, crooked pointed hat (follows the body's lean), little boots, arms as
thick lines and the wooden ladle with swamp broth. In `failed` she melts into a green puddle and only the hat is left.
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, line

PAL = {
    "K": "#1c1a2a", "R": "#5f3f86", "r": "#3f2a5e", "G": "#b3dc8e", "g": "#7fae66", "L": "#3d6e45",
    "H": "#33402f", "h": "#232c21", "U": "#b06ad8", "N": "#8a5a36", "V": "#a6e86b", "v": "#4c8a3a",
    "W": "#ffffff", "B": "#1c1a2a", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f", "k": "#2c2440",
    "O": "#ff8a3d", "S": "#7d7790",
}

BUBBLE = [".KK.", "KVVK", "KvVK", ".KK."]
BUBBLE_S = ["KK", "KK"]
DROP = [".KKK.", "KVVVK", "KVWVK", "KvVVK", ".KKK."]
# broth flying with green fire (the stroke is burn)
SPELL = ["...KK.KK..", "..KVKKYK..", ".KVVVKYOK.", "KVVWVVKOK.", "KVVVVvVVK.", "KvVVVVVvK.", ".KVvVVVK..", "..KKKKK..."]
SPLASH = ["..KK...KK.", ".KYOK.KVK.", "KVYOVKKVVK", "KVVVVVVvK.", ".KVvVVVVVK", "KVVVYVvVK.", ".KKVVOVKK.", "...KKKKK.."]
HAND = ["KKK", "KGK", "KKK"]


def _trait(g, a, b, color, thick=1):
    pts = line(*a, *b)
    r = range(-thick, thick + 1)
    for x, y in pts:
        for dx in r:
            for dy in r:
                if 0 <= x + dx < N and 0 <= y + dy < N:
                    g[y + dy][x + dx] = "K"
    for x, y in pts:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = color


def _shell(g, hand, tip, full=True):
    """Wooden handle from the hand to the tip and the ladle (3x3, with broth) at the tip."""
    _trait(g, hand, tip, "N")
    px, py = tip
    stamp(g, [".KKK.", "KVVVK" if full else "KNNNK", "KvVvK" if full else "KNNNK", ".KKK."], px - 2, py - 2)


def _hat(g, bx, by, crooked=0):
    """Witch hat with the brim at (bx, by) and the tip bent backward; `crooked` pushes the tip (follows the body)."""
    px = {}
    for x in range(bx - 8, bx + 9):          # brim
        px[(x, by)] = "H"
        if abs(x - bx) < 8:
            px[(x, by + 1)] = "h"
    for i in range(1, 10):                   # crown: narrows and bends backward
        half = max(0, round(4.5 - i * 0.5))
        c = bx - round(i * i / 14) + round(crooked * i / 9)
        for x in range(c - half, c + half + 1):
            px[(x, by - i)] = "h" if x == c - half and half else "H"
    tip = bx - round(81 / 14) + crooked
    px[(tip - 1, by - 9)] = px[(tip - 2, by - 8)] = "H"   # drooping tip
    for x in range(bx - 4, bx + 5):          # purple ribbon
        px[(x, by - 1)] = "U"
    for (x, y) in px:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in px and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for (x, y), c in px.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c
    g[by - 1][bx + 2] = "Y"                  # buckle


def _face(g, hx, hy, eyes):
    """Plain face: two eyes (2x2 blocks, or line/arc) and a small mouth; no loose shine or cheeks."""
    ex, ey = hx + 1, hy - 1
    for x in (ex - 2, ex + 2):
        if eyes == "closed":
            stamp(g, ["BB"], x, ey + 1)
        elif eyes == "happy":
            stamp(g, [".B.", "B.B"], x - (x > ex), ey)
        elif eyes == "x":
            stamp(g, ["B.B", ".B.", "B.B"], x - (x > ex), ey - 1)
        else:
            stamp(g, ["BB", "BB"], x, ey - (eyes == "up"))
            if eyes == "angry":
                stamp(g, ["BB."] if x < ex else [".BB"], x - (x < ex), ey - 2)
            if eyes == "sad":
                stamp(g, [".BB"] if x < ex else ["BB."], x - (x < ex), ey - 2)
    mouth = {"happy": ["B..B", ".BB."], "sad": [".BB.", "B..B"], "angry": [".BB.", "B..B"]}.get(eyes, [".BB."])
    stamp(g, mouth, ex - 1, ey + 3)


def _puddle(g, cx, y, half, eyes=False):
    """Swamp puddle: shallow green ellipse with bubbles; `eyes` draws two sad little eyes on it."""
    px = set()
    for dy, f in ((0, 0.6), (1, 1.0), (2, 0.85)):
        w = round(half * f)
        px |= {(x, y + dy) for x in range(cx - w, cx + w + 1)}
    for x, yy in px:
        for nx, ny in ((x + 1, yy), (x - 1, yy), (x, yy + 1), (x, yy - 1)):
            if (nx, ny) not in px and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for x, yy in px:
        if 0 <= x < N and 0 <= yy < N:
            g[yy][x] = "v" if yy == y + 2 else "V"
    for x in range(cx - half + 2, cx + half - 1, 4):
        if 0 <= x < N:
            g[y + 1][x] = "W"
    if eyes:
        stamp(g, ["B.B", ".B."], cx - 3, y)
        stamp(g, ["B.B", ".B."], cx + 1, y)


def frame(cx=14, base=30, ch=8, lean=0, eyes="normal", feet=(0, 0), crooked=0, behind=(), arms=(), shells=(),
           por=(), melts=0, hat=None):
    """One 32x32 frame and the add-on anchor (attached to the hat brim). `melts` 0..3 sinks the body into a puddle;
    `hat` (bx, by) drops the hat; `arms`: ((x0, y0), (x1, y1)) sleeves with hands; `shells`: (hand, tip, full)."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    if melts >= 3:                          # only the puddle and the hat
        _puddle(g, cx, base - 3, 11, eyes=True)
        bx, by = hat
        _hat(g, bx, by, crooked)
        for s, x, y in por:
            stamp(g, s, x, y)
        return ["".join(l) for l in g], (bx - 12, by - 10)
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 4
    if melts:
        _puddle(g, cx, base - 3, 6 + 3 * melts)
    dress = set()
    for y in range(ctop, base - 1):
        t = (y - ctop) / max(ch - 1, 1)
        half = 3.5 + t * (3.5 + melts)
        c = cx + lean * (1 - t)
        dress |= {(x, y) for x in range(round(c - half), round(c + half) + 1)}
    head = {(x, y) for x in range(hx - 6, hx + 7) for y in range(hy - 6, hy + 7)
              if (x - hx) ** 2 + (y - hy) ** 2 <= 27}
    nose = {(hx + 6, hy + 1), (hx + 7, hy + 2)}
    body = dress | head | nose
    for x, y in body:
        if (x, y) in dress and (x, y) not in head:
            edge = (x + 1, y) not in body or (x, y + 1) not in body
            g[y][x] = "r" if edge else "R"
        elif x - hx <= -2 and (x, y) in head:
            g[y][x] = "L"                     # moss hair
        else:
            g[y][x] = "g" if (x, y + 1) not in body and y > hy else "G"
    if not melts:
        for i, (px, dx) in enumerate(((cx - 4, feet[0]), (cx + 2, feet[1]))):
            for x in range(px + dx, px + dx + 3):
                for y in (base - 2, base - 1):
                    body.add((x, y)); g[y][x] = "k"
    else:                                     # drips running down the dress
        for x in range(cx - 4, cx + 5, 3):
            body.add((x, base - 2)); g[base - 2][x] = "V"
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for x in range(hx - 5, hx - 1):           # locks falling on the shoulders
        if (x, hy + 5) in head or (x, hy + 4) in head:
            g[min(hy + 6, N - 1)][x] = "L" if x % 2 else g[min(hy + 6, N - 1)][x]
    _face(g, hx, hy, eyes)
    for a, b in arms:
        _trait(g, a, b, "R")
        stamp(g, HAND, b[0] - 1, b[1] - 1)
    for hand, tip, full in shells:
        _shell(g, hand, tip, full)
        stamp(g, HAND, hand[0] - 1, hand[1] - 1)
    bx, by = hat or (hx, hy - 4)
    _hat(g, bx, by, crooked - lean)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (bx - 12, by - 10)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


def _c(hand, tip, full=True):
    return (hand, tip, full)


# shoulder ~(cx + 2, ctop + 2); base=30, ch=8 -> ctop=21, head hy=17, brim y=13
_SPECS = {
    # standing, stirs with the ladle and a bubble rises from the broth
    "idle": [dict(arms=(((16, 23), (20, 24)),), shells=(_c((20, 24), (23, 19)),)),
             dict(arms=(((16, 23), (20, 24)),), shells=(_c((20, 24), (24, 20)),), por=((BUBBLE_S, 24, 15),)),
             dict(eyes="closed", crooked=1, arms=(((16, 23), (20, 24)),), shells=(_c((20, 24), (23, 19)),),
                  por=((BUBBLE, 23, 11),)),
             dict(arms=(((16, 23), (20, 24)),), shells=(_c((20, 24), (22, 20)),), por=((BUBBLE_S, 24, 8),))],
    # runs leaning, little boots alternating, ladle behind, hat tip swaying
    "run_r": [dict(cx=15, lean=2, feet=(-2, 2), crooked=-2, arms=(((14, 23), (9, 24)),), shells=(_c((9, 24), (4, 21)),)),
              dict(cx=15, lean=3, base=29, crooked=-4, arms=(((14, 22), (10, 23)),), shells=(_c((10, 23), (5, 22)),)),
              dict(cx=15, lean=2, feet=(2, -2), crooked=-2, arms=(((14, 23), (9, 24)),), shells=(_c((9, 24), (4, 22)),)),
              dict(cx=15, lean=3, base=29, crooked=-4, arms=(((14, 22), (10, 23)),), shells=(_c((10, 23), (5, 21)),))],
    # waves with her hand, ladle in the other one (behind)
    "waving": [dict(eyes="happy", shells=(_c((9, 25), (5, 21)),), arms=(((16, 23), (21, 20)),)),
               dict(eyes="happy", crooked=1, shells=(_c((9, 25), (5, 21)),), arms=(((16, 23), (21, 16)),)),
               dict(eyes="happy", crooked=2, shells=(_c((9, 25), (5, 21)),), arms=(((16, 23), (24, 16)),)),
               dict(eyes="happy", crooked=1, shells=(_c((9, 25), (5, 21)),), arms=(((16, 23), (21, 16)),))],
    # crouches, jumps with the ladle up high, falls, lands (the hat lags behind)
    "jumping": [dict(ch=6, eyes="closed", crooked=2, arms=(((16, 25), (20, 27)),), shells=(_c((20, 27), (24, 24)),)),
                dict(ch=9, base=29, crooked=-2, arms=(((16, 21), (22, 18)),), shells=(_c((22, 18), (25, 13)),)),
                dict(ch=8, base=27, eyes="happy", crooked=-3, arms=(((16, 19), (23, 16)),), shells=(_c((23, 16), (26, 11)),)),
                dict(ch=9, base=29, crooked=2, arms=(((16, 22), (22, 21)),), shells=(_c((22, 21), (25, 17)),)),
                dict(ch=6, eyes="happy", crooked=3, arms=(((16, 25), (20, 26)),), shells=(_c((20, 26), (24, 23)),))],
    # sad, melts into a swamp puddle; the hat falls onto the puddle
    "failed": [dict(eyes="sad", arms=(((16, 23), (19, 26)),), shells=(_c((19, 26), (22, 28), False),),
                    por=((TEAR, 20, 18),)),
               dict(ch=6, eyes="sad", melts=1, por=((TEAR, 20, 21), (DROP, 21, 24))),
               dict(ch=4, eyes="closed", melts=2),
               dict(melts=3, hat=(14, 23), crooked=1, por=((BUBBLE_S, 24, 22),)),
               dict(melts=3, hat=(14, 23), crooked=2, por=((BUBBLE, 22, 19),))],
    # naps sitting, head tilting, "z" rising
    "waiting": [dict(ch=7, lean=-1, eyes="closed", crooked=2),
                dict(ch=7, lean=-2, eyes="closed", crooked=3, por=((Z_S, 23, 4),)),
                dict(ch=7, lean=-2, eyes="closed", crooked=3, por=((Z_S, 22, 4), (Z_L, 26, 0))),
                dict(ch=7, lean=-1, eyes="closed", crooked=2, por=((Z_L, 26, 0),))],
    # attack: pulls the ladle back, swings it overhead and throws the broth, which bursts into green fire
    "running": [dict(cx=14, lean=-2, eyes="angry", crooked=2, arms=(((15, 23), (10, 21)),), shells=(_c((10, 21), (5, 17)),)),
                dict(cx=14, lean=1, eyes="angry", crooked=-1, arms=(((16, 22), (20, 16)),), shells=(_c((20, 16), (22, 9)),)),
                dict(cx=14, lean=3, eyes="angry", crooked=-3, arms=(((17, 23), (22, 21)),), shells=(_c((22, 21), (27, 19), False),),
                     por=((SPELL, 21, 6),)),
                dict(cx=14, lean=2, eyes="angry", crooked=-2, arms=(((17, 23), (21, 24)),), shells=(_c((21, 24), (26, 24), False),),
                     por=((SPLASH, 21, 4), (BUBBLE_S, 19, 2), (BUBBLE_S, 30, 11)))],
    # finger on the chin, looking up, "?" appears
    "review": [dict(cx=12, eyes="up", arms=(((14, 23), (18, 21)),), shells=(_c((8, 26), (4, 22)),)),
               dict(cx=12, eyes="up", arms=(((14, 23), (18, 21)),), shells=(_c((8, 26), (4, 22)),),
                    por=((QMARK_S, 25, 2),)),
               dict(cx=12, eyes="up", crooked=1, arms=(((14, 23), (18, 21)),), shells=(_c((8, 26), (4, 22)),),
                    por=((QMARK, 25, 0),)),
               dict(cx=12, eyes="normal", crooked=1, arms=(((14, 23), (18, 21)),), shells=(_c((8, 26), (4, 22)),),
                    por=((QMARK, 25, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# little cauldron floating beside her (behind, on the left), with a bubble; anchor = (brim - 12, brim - 10).
# One spare column on the left so the cauldron never touches the edge.
_EMPTY = "." * 25
CAULDRON = [_EMPTY] * 11 + [
    "...KK....................",
    "..KVVK...................",
    ".KKVVKK..................",
    ".KSSSSSK.................",
    ".KSkkkSK.................",
    ".KSkkkSK.................",
    "..KSSSK..................",
    "...KKK...................",
]
# little crow perched on the brim and fireflies around the hat
MATRIARCH = CAULDRON[:]
for _i, _lin in {
    0: ".KK..................KK..",
    1: "KYYK................KYYK.",
    2: ".KK..................KK..",
    5: "...KKK...................",
    6: "..KkkkK..................",
    7: ".KkYkkkK.................",
    8: "KOKkkkkkK................",
    9: ".KKkkkkK..............KK.",
    10: "..KKKKK..............KYYK",
    11: "...KK.................KK.",
}.items():
    MATRIARCH[_i] = _lin
STAGES = [
    {"title": "Witchling", "floor": 1, "extra": None},
    {"title": "Swamp Witch", "floor": 4, "extra": CAULDRON},
    {"title": "Bog Matriarch", "floor": 10, "extra": MATRIARCH},
]
