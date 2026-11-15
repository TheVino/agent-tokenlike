"""Graveyard Cat, 32 px, facing forward. A little black cat sitting, big-headed, with pointed
ears with pink insides, big yellow eyes, light whiskers, little white paws (socks) and the tail curved behind.
It wears a red collar with a golden bell. Since the body is black, the whole top and right border gets a
lilac glow (and the left one a darker lilac), so the cat does not vanish on a dark background; closed eyes,
mouth and eyebrows are lilac strokes for the same reason.
The `running` symbol is the swipe: winds the paw up, lunges and scratches the air with three white claw marks. In `failed` it
curls up: gets sad, lies down curled into a little ball with the tail in front and the bell rings one last time.
Gestures always use the front paw (right); the 2nd stage scarf ties its knot on the back side (left).
The torso and head move together (only paws, legs and tail change), so the add-ons' scarf and little candles
always stay in place. Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line, trait

PAL = {
    "K": "#07060c", "P": "#2c2742", "M": "#a597ec", "m": "#5f5596", "Y": "#ffd23f", "y": "#b8841a",
    "W": "#f4f2fa", "w": "#bab6cc", "R": "#ff8fb0", "r": "#b05a7e", "V": "#e0384e", "v": "#8e1e30",
    "L": "#9a5cd8", "l": "#5e2f94", "I": "#fff4dc", "i": "#d8c8a0", "F": "#ff9a3c", "T": "#8fd8ff",
}

HEAD = (5, 6, 7, 7, 7, 7, 7, 6, 5)            # head half-width per row (9 rows; the last one is the collar)
TRUNK = (5, 6, 6, 7, 7, 7, 7, 6)               # torso half-width per row (8 rows; the 1st is the collar's)


def _claws(n=3, comp=8):
    """Claw marks: `n` white diagonal strokes, from the top right down to the bottom left, with an outline."""
    g = [["."] * N for _ in range(N)]
    px = {}
    for i in range(n):
        for x, y in line(comp - 1 + 3 * i, 1, 1 + 3 * i, comp):
            px[(x, y)] = "W"
    outline_cells(g, px)
    w = 3 * n + comp
    return ["".join(l[:w]) for l in g[:comp + 2]]


SCRATCH = _claws(3, 7)
SCRATCH_S = _claws(3, 5)
SPARK = [".K.", "KYK", ".K."]


def _rim(px):
    """Lilac glow on the edges of the black fur: light on the top and right, dark on the left."""
    out = {}
    for (x, y), c in px.items():
        if c == "P":
            if (x, y - 1) not in px or (x + 1, y) not in px:
                c = "M"
            elif (x - 1, y) not in px:
                c = "m"
        out[(x, y)] = c
    return out


def _arm(g, a, b):
    """2 px little leg from `a` (shoulder) to `b` (paw), with the white 3x3 paw and the little pink bean in the middle."""
    px = {}
    for x, y in line(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px.setdefault((x + dx, y + dy), "m" if dy == 0 else "P")
    bx, by = b
    for x in range(bx - 1, bx + 2):
        for y in range(by - 1, by + 2):
            px[(x, y)] = "W"
    px[(bx, by)] = "R"
    px[(bx - 1, by + 1)] = px[(bx + 1, by + 1)] = "w"
    outline_cells(g, px)


def _tail(px, pts):
    """2 px tail through the points `pts` (from the base to the tip)."""
    for p, q in zip(pts, pts[1:]):
        for x, y in line(*p, *q):
            px[(x, y)] = px[(x + 1, y)] = "P"


def _bell(g, x, y, sound=0):
    """Golden bell hanging at (x, y); `sound` draws the ringing streaks (size 0, 1 or 2)."""
    px = {(x, y): "y", (x - 1, y + 1): "Y", (x, y + 1): "W", (x + 1, y + 1): "Y", (x - 1, y + 2): "Y",
          (x, y + 2): "Y", (x + 1, y + 2): "y", (x, y + 3): "y"}
    outline_cells(g, px)
    for k in range(sound):                        # ringing streaks in "\ /" coming out of the bell, one pair per level
        for s in (-1, 1):
            trait(g, (x + s * (3 + k), y + 1 - 3 * k), (x + s * (5 + k), y - 1 - 3 * k), "Y")


def _move(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


EYES = {"n": ["YYY", "YKY", "YKY"], "fechado": ["...", "MMM", "..."], "feliz": [".M.", "M.M", "..."],
         "x": ["M.M", ".M.", "M.M"], "cima": ["YKY", "YKY", "YYY"], "triste": ["...", "YYY", "YKY"],
         "bravo": (["M..", "YYY", "YKY"], ["..M", "YYY", "YKY"])}


def _face(g, hx, h0, eye):
    back, front = EYES[eye] if isinstance(EYES[eye], tuple) else (EYES[eye], EYES[eye])
    stamp(g, back, hx - 4, h0 + 2)
    stamp(g, front, hx + 2, h0 + 2)
    if eye == "triste":
        stamp(g, TEAR, hx - 4, h0 + 5)
    g[h0 + 5][hx] = "R"                         # muzzle
    for x in (hx - 1, hx + 1):                  # little "w" mouth
        g[h0 + 6][x] = "M"
    for y in (h0 + 5, h0 + 7):                  # whiskers
        for d in (5, 6, 7, 8):
            for x in (hx - d, hx + d):
                if 0 <= x < N and (g[y][x] != "." or d >= 7):
                    g[y][x] = "w"


def frame(cx=16, base=30, leg=2, eye="n", feet=(0, 0), arms=(), tail=0, sound=0, por=()):
    """One 32x32 frame and the add-on anchor (9 to the left of the center and 11 above the head top).
    `leg`: leg height (0 = lying down); `arms`: ((shoulder), (paw)) written for the default pose
    (cx=16, base=30, leg=2: shoulders at (11, 23) and (21, 23)) and shifted along with the body;
    `tail`: tail pose (0 to 3); `por`: sprites stamped last, without shifting."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, (base - 30) + (2 - leg)
    a0 = 21 + dy                                    # torso top (= collar, last row of the head)
    h0 = a0 - 8
    hx = cx + 1
    px = {}
    tip = ((-11, -1), (-12, -4), (-10, -6), (-13, -2))[tail]
    _tail(px, [(cx - 5, a0 + 6), (cx - 10, a0 + 4), (cx + tip[0], a0 + tip[1])])
    for i, x0 in enumerate((cx - 4, cx + 2)):       # little legs with white socks
        x = x0 + feet[i]
        for y in range(base - leg + 1, base + 1):
            px[(x, y)] = px[(x + 1, y)] = "P"
    for r, w in enumerate(TRUNK):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "P"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "P"
    for s in (-1, 1):                               # pointed ears
        for r in range(3):
            for k in range(r + 1):
                px[(hx + s * (6 - k), h0 - 3 + r)] = "P"
    px = _rim(px)
    for i, x0 in enumerate((cx - 4, cx + 2)):
        x = x0 + feet[i]
        for xx in (x, x + 1, x + 2):
            px[(xx, base)] = "W"
    outline_cells(g, px)
    for s in (-1, 1):                               # pink inner ears
        g[h0 - 1][hx + s * 5] = "r"
        g[h0][hx + s * 5] = "r"
        g[h0][hx + s * 4] = "r"
    _face(g, hx, h0, eye)
    for x in range(hx - 5, hx + 6):                 # collar
        g[a0][x] = "V" if x != hx - 5 else "v"
    _bell(g, hx, a0 + 1, sound)
    for a, b in arms:
        _arm(g, _move(a, dx, dy), _move(b, dx, dy))
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 9, h0 - 11)


def ball(cx=15, eye="fechado", sound=0, por=()):
    """The cat curled into a little ball on the ground: oval body, head resting on the right, tail passing in front."""
    g = [["."] * N for _ in range(N)]
    px = {}
    for y in range(22, 31):
        for x in range(cx - 10, cx + 7):
            if ((x - cx + 1.5) / 8.5) ** 2 + ((y - 26.5) / 4.6) ** 2 <= 1:
                px[(x, y)] = "P"
    hx, h0 = cx + 6, 20                             # head (center, top)
    for y in range(h0, h0 + 8):
        for x in range(hx - 5, hx + 6):
            if ((x - hx) / 5.4) ** 2 + ((y - h0 - 3.8) / 4.3) ** 2 <= 1:
                px[(x, y)] = "P"
    for s in (-1, 1):
        for r in range(3):
            for k in range(r + 1):
                px[(hx + s * (4 - k), h0 - 2 + r)] = "P"
    px = _rim(px)
    outline_cells(g, px)
    for s in (-1, 1):
        g[h0][hx + s * 3] = "r"
    for x, y in ((hx - 2, h0 + 3), (hx + 2, h0 + 3)):
        stamp(g, [EYES[eye][1][:2]] if eye == "fechado" else [l[:2] for l in EYES[eye][1:]], x - 1, y)
    g[h0 + 5][hx] = "R"
    tail_tip = {}                                       # curled tail passing in front of the ball
    _tail(tail_tip, [(cx - 10, 26), (cx - 7, 29), (cx - 1, 29), (cx + 3, 27)])
    tail_tip = _rim(tail_tip)
    outline_cells(g, tail_tip)
    for x in range(hx - 4, hx + 3):                 # collar
        g[h0 + 7][x] = "V"
    _bell(g, hx - 1, h0 + 8, sound)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (hx - 11, h0 - 12)


def _state(specs):
    qs = [ball(**s["ball"]) if "ball" in s else frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# default pose: collar on row 21, head 13-21 (hx=17), eyes 15-17, ears 10-12; shoulders at (11, 23) and (21, 23)
_BACK = ((11, 23), (11, 27))                    # back paw on the ground, in front of the body
_FRONT = ((21, 23), (21, 27))                  # front paw on the ground
_SPECS = {
    # sitting: the tail sways, blinks, the bell shines
    "idle": [dict(arms=(_BACK, _FRONT)),
             dict(arms=(_BACK, _FRONT), tail=1),
             dict(arms=(_BACK, _FRONT), tail=2, por=((SPARK, 19, 22),)),
             dict(eye="fechado", arms=(_BACK, _FRONT), tail=1),
             dict(arms=(_BACK, _FRONT))],
    # trots: the body bobs, little legs alternate, tail raised
    "run_r": [dict(cx=17, base=30, feet=(-1, 1), arms=(((11, 23), (9, 26)), ((21, 23), (24, 25))), tail=2),
              dict(cx=17, base=29, leg=3, feet=(1, -1), arms=(((11, 23), (12, 27)), ((21, 23), (22, 27))),
                   tail=1),
              dict(cx=17, base=30, feet=(-1, 1), arms=(((11, 23), (8, 25)), ((21, 23), (25, 24))), tail=2),
              dict(cx=17, base=29, leg=3, feet=(1, -1), arms=(((11, 23), (13, 27)), ((21, 23), (21, 27))),
                   tail=1)],
    # waves very high with the front paw, happy
    "waving": [dict(eye="feliz", arms=(_BACK, ((21, 23), (26, 14))), tail=1),
               dict(eye="feliz", arms=(_BACK, ((21, 23), (28, 17))), tail=2),
               dict(eye="feliz", arms=(_BACK, ((21, 23), (25, 13))), tail=1),
               dict(eye="feliz", arms=(_BACK, ((21, 23), (28, 17))), tail=2)],
    # crouches, jumps with paws up, comes down, lands
    "jumping": [dict(leg=0, eye="fechado", arms=(_BACK, _FRONT), tail=0),
                dict(base=29, leg=3, eye="cima", feet=(-1, 1), arms=(((11, 23), (6, 17)), ((21, 23), (26, 17))),
                     tail=2),
                dict(base=29, leg=3, eye="feliz", feet=(-1, 1), arms=(((11, 23), (5, 16)), ((21, 23), (27, 16))),
                     tail=2, por=((SPARK, 2, 27), (SPARK, 28, 26))),
                dict(base=30, leg=3, arms=(((11, 23), (7, 21)), ((21, 23), (25, 21))), tail=1),
                dict(leg=0, eye="feliz", arms=(_BACK, _FRONT), tail=0)],
    # curls up: gets sad, lies down curled up, the bell rings one last time and stops
    "failed": [dict(eye="triste", arms=(_BACK, _FRONT), tail=0),
               dict(ball=dict(eye="triste")),
               dict(ball=dict(sound=2)),
               dict(ball=dict(sound=1)),
               dict(ball=dict())],
    # naps lying down (legs tucked), "z" rising
    "waiting": [dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=0),
                dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=0,
                     por=((Z_S, 26, 6),)),
                dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=3,
                     por=((Z_S, 25, 7), (Z_L, 26, 0))),
                dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=0,
                     por=((Z_L, 26, 0),))],
    # swipe: winds the paw up high, lunges, scratches the air with three claw marks, pulls back
    "running": [dict(cx=12, eye="bravo", arms=(((11, 23), (9, 27)), ((21, 23), (27, 14))), tail=2),
                dict(cx=12, eye="bravo", arms=(((11, 23), (9, 27)), ((21, 23), (30, 17))), tail=2,
                     por=((SCRATCH_S, 23, 4),)),
                dict(cx=12, eye="bravo", arms=(((11, 23), (9, 27)), ((21, 23), (30, 26))), tail=3,
                     por=((SCRATCH, 19, 8),)),
                dict(cx=12, eye="feliz", arms=(((11, 23), (9, 27)), ((21, 23), (26, 27))), tail=1,
                     por=((SCRATCH_S, 21, 15),))],
    # paw on the chin, looking up, "?" appears
    "review": [dict(eye="cima", arms=(_BACK, ((21, 23), (20, 20))), tail=1),
               dict(eye="cima", arms=(_BACK, ((21, 23), (20, 20))), tail=2, por=((QMARK_S, 26, 1),)),
               dict(eye="cima", arms=(_BACK, ((21, 23), (20, 20))), tail=1, por=((QMARK, 26, 0),)),
               dict(eye="n", arms=(_BACK, ((21, 23), (20, 20))), tail=2, por=((QMARK, 26, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)


# 21x24 grid attached 9 to the left of the center and 11 above the head top (head top on row 11, center
# on column 10, ears 8-10, collar on row 19): purple scarf on the neck with the knot behind (on the left), leaving the
# bell visible; on the 3rd stage, seven little candles floating in an arc over the head
CANDLE = [".K.", "KYK", "KFK", "KIK", "KiK", "KKK"]


def _extra(candles):
    g = [["."] * N for _ in range(N)]
    px = {}
    for x in range(4, 17):
        px[(x, 19)] = "L"
    for x in range(5, 16):
        if not 9 <= x <= 11:
            px[(x, 20)] = "l"
    for x, y in ((3, 19), (2, 20), (3, 20), (1, 21), (2, 21), (3, 21), (2, 22), (0, 22), (1, 23)):
        px[(x, y)] = "L" if y < 22 else "l"     # knot ends falling behind
    outline_cells(g, px)
    if candles:
        for x, y in zip((0, 3, 6, 9, 12, 15, 18), (4, 2, 1, 0, 1, 2, 4)):
            stamp(g, CANDLE, x, y)
    return ["".join(l[:21]) for l in g[:24]]


SCARF = _extra(False)
CANDLES = _extra(True)
STAGES = [
    {"title": "Gatinho Preto", "floor": 1, "extra": None},
    {"title": "Gato de Cemitério", "floor": 4, "extra": SCARF},
    {"title": "Gato das Sete Vidas", "floor": 10, "extra": CANDLES},
]
