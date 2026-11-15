"""Plague Doctor, 32 px, facing right. Each frame is made of parts: coat (bell shape with shade and buttons),
hooded head with a beak mask and green goggles, little boots, arms as thick lines (with outline) and objects
(herb lantern, poison flask, little cloud). In `failed` the mask comes loose and falls, showing the little face.
Hero format from heroes/assemble.py: PAL, FRAMES, STAGES, ANCHOR."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, line

PAL = {
    "K": "#231b33", "C": "#4a3f66", "c": "#342b4c", "H": "#5b4d7d", "h": "#3f3560",
    "M": "#efe6cf", "m": "#bfae8a", "E": "#8ff07a", "e": "#3d9a4a", "W": "#ffffff",
    "F": "#f6d7c3", "P": "#ff9ec4", "B": "#231b33", "T": "#8fd8ff", "Y": "#ffd23f",
    "V": "#a6e86b", "v": "#4c8a3a", "N": "#8a5a36", "k": "#2c2233", "R": "#8e2a44", "r": "#5e1a2e",
    "S": "#c9c3d6",
}

LANTERN = [".KKK.", ".K.K.", "KKKKK", "KVYVK", "KYVvK", "KvVVK", "KKKKK", ".KKK."]
LANTERN_OFF = [".KKK.", ".K.K.", "KKKKK", "KSSSK", "KSSSK", "KSSSK", "KKKKK", ".KKK."]
FLASK = [".KK.", "KNNK", ".KK.", "KVVK", "KVvK", "KvVK", ".KK."]
FLASK_FLYING = ["..KKKK..", "..KNNK..", "..KNNK..", "..KKKK..", "...KSK..", "..KKSKK.", ".KVVVVVK", "KVVvVVVK", "KVvVVvVK", "KVVVVVVK", ".KKKKKK."]
CLOUD = ["...KKK.KK.", "..KVVVKVVK", ".KVVvVVVVK", "KVVVVVvVVK", "KVvVVVVVK.", ".KVVVvVVVK", "..KKVVKKK.", "....KK...."]
CLOUD_S = [".KK.", "KVVK", "KvVK", ".KK."]
GLOVE = [".KKK.", "KNNNK", "KNNNK", "KNNNK", ".KKK."]
HAND_FACE = [".KKK.", "KNNNK", "KNNNK", ".KKK."]


def _arm(g, a, b):
    """Thick coat sleeve from `a` to `b`, with a dark outline."""
    pts = line(*a, *b)
    for x, y in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= x + dx < N and 0 <= y + dy < N:
                    g[y + dy][x + dx] = "K"
    for x, y in pts:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = "H"


def frame(cx=14, base=30, ch=9, lean=0, eyes="normal", cheek=True, mask=(0, 0), face_kind="normal",
           feet=(0, 0), behind=(), arms=(), por=(), lantern_ok=True):
    """One 32x32 frame and the anchor (top of the head) for the add-on. `mask` None = attached; (dx, dy) = loose and offset.
    `behind`: (sprite, x, y) drawn before the body; `arms`: ((x0, y0), (x1, y1)) on top; `por`: sprites at the end."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 5
    coat = set()
    for y in range(ctop, base - 1):
        t = (y - ctop) / ch
        half = 4.5 + t * 3.5
        c = cx + lean * (1 - t)
        coat |= {(x, y) for x in range(round(c - half), round(c + half) + 1)}
    head = {(x, y) for x in range(hx - 7, hx + 8) for y in range(hy - 7, hy + 8)
              if (x - hx) ** 2 + (y - hy) ** 2 <= 42}
    face = {(x, y) for x, y in head if x >= hx - 3 and y >= hy - 2}
    beak = set()
    for i, L in enumerate((3, 6, 8, 7, 4)):
        beak |= {(x, hy + i) for x in range(hx + 5, hx + 5 + L)}
    fang = mask == (0, 0)
    body = coat | head | (beak if fang else set())
    for x, y in body:
        if (x, y) in head:
            g[y][x] = "h" if (x - hx) < -3 and y > hy - 2 else "H"
        elif (x, y) in coat:
            edge = (x + 1, y) not in body or (x, y + 1) not in body
            g[y][x] = "c" if edge else "C"
    if fang:
        for x, y in face | beak:
            g[y][x] = "m" if (x, y + 1) not in face | beak or y == hy + 2 and x > hx + 6 else "M"
    else:
        for x, y in face:                      # little face with an outline where it touches the hood
            g[y][x] = "K" if any(n in head and n not in face for n in ((x - 1, y), (x, y - 1))) else "F"
    for x, y in coat:                      # buttons in the middle of the coat
        if x == round(cx + lean * 0.4) + 1 and (y - ctop) % 3 == 2 and y < base - 2:
            g[y][x] = "Y"
    foot_y = base - 2
    for i, (px, dx) in enumerate(((cx - 4, feet[0]), (cx + 2, feet[1]))):
        for x in range(px + dx, px + dx + 3):
            for y in (foot_y, foot_y + 1):
                body.add((x, y)); g[y][x] = "k"
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # eyes: with the mask, two green goggles; without it, little eyes on the face
    if fang:
        for ox in (hx - 3, hx + 2):
            oy = hy - 2
            if eyes == "closed":
                stamp(g, ["KKKKK", "K...K", "KKKKK"], ox, oy + 1)
                for x in range(ox + 1, ox + 4):
                    g[oy + 2][x] = "e"
            elif eyes == "happy":
                stamp(g, [".KKK.", "KE.EK", "K...K"], ox, oy + 1)
            else:
                stamp(g, [".KKK.", "KEEEK", "KEEEK", "KeEeK", ".KKK."], ox, oy)
                g[oy + 1][ox + 1] = "W" if eyes != "up" else "E"
                if eyes == "up":
                    g[oy + 1][ox + 2] = "W"
                if eyes == "angry":
                    stamp(g, ["KK...", "..KKK"] if ox < hx else ["KKK..", "...KK"], ox, oy - 1)
                if eyes == "sad":
                    stamp(g, ["...KK", "KKK.."] if ox < hx else ["..KKK", "KK..."], ox, oy - 1)
        if cheek:
            g[hy + 3][hx - 2] = g[hy + 3][hx - 1] = "P"
        g[hy + 1][hx + 9] = "m"               # nostril on the beak
    else:
        dx, dy = mask
        for x, y in face | beak:              # fallen mask, drawn offset
            if 0 <= x + dx < N and 0 <= y + dy < N:
                g[y + dy][x + dx] = "m" if (x, y + 1) not in face | beak else "M"
        for x, y in face | beak:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in face | beak and 0 <= nx + dx < N and 0 <= ny + dy < N \
                        and g[ny + dy][nx + dx] in ".FHhCck":
                    g[ny + dy][nx + dx] = "K"
        for ox in (hx - 3, hx + 2):
            stamp(g, [".KKK.", "KEEEK", "KeEeK", ".KKK."], ox + dx, hy - 2 + dy)
        ex, ey = hx - 1, hy
        if face_kind == "x":
            stamp(g, ["B.B", ".B.", "B.B"], ex - 1, ey - 1); stamp(g, ["B.B", ".B.", "B.B"], ex + 3, ey - 1)
        else:
            for x in (ex, ex + 4):                # 2x3 eyes with a shine
                stamp(g, ["WB", "BB", "BB"], x - 1 + (x > ex), ey - 1)
            if face_kind != "o":                      # sad eyebrows
                stamp(g, ["..B", "BB."], ex - 2, ey - 3); stamp(g, ["B..", ".BB"], ex + 4, ey - 3)
        if face_kind == "o":
            stamp(g, [".B.", "B.B", ".B."], ex + 1, ey + 3)
        else:
            stamp(g, [".BBB.", "B...B"], ex, ey + 3)
        g[ey + 2][ex - 2] = g[ey + 2][ex + 6] = "P"
    for a, b in arms:
        _arm(g, a, b)
    for s, x, y in por:
        if s is LANTERN and not lantern_ok:
            s = LANTERN_OFF
        stamp(g, s, x, y)
    top = min(y for _, y in head)
    return ["".join(l) for l in g], (hx - 7, top - 5)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


def _lant(mx, my):
    """Hand at (mx, my) holding the lantern hanging just below."""
    return (LANTERN, mx - 2, my + 1)


# shoulder: ~(cx + 3, ctop + 2); base=30, ch=9 -> ctop=20
_SPECS = {
    # standing, swings the herb lantern in front
    "idle": [dict(arms=(((17, 22), (21, 21)),), por=(_lant(21, 21),)),
             dict(arms=(((17, 22), (22, 22)),), por=(_lant(22, 22),)),
             dict(eyes="closed", arms=(((17, 22), (23, 21)),), por=(_lant(23, 21),)),
             dict(arms=(((17, 22), (22, 22)),), por=(_lant(22, 22),))],
    # runs leaning, little boots alternating, lantern swinging back
    "run_r": [dict(cx=15, lean=2, feet=(-2, 2), arms=(((13, 22), (8, 24)),), behind=(_lant(7, 24),)),
              dict(cx=15, lean=3, base=29, feet=(0, 0), arms=(((13, 21), (9, 22)),), behind=(_lant(8, 22),)),
              dict(cx=15, lean=2, feet=(2, -2), arms=(((13, 22), (8, 23)),), behind=(_lant(7, 23),)),
              dict(cx=15, lean=3, base=29, feet=(0, 0), arms=(((13, 21), (9, 21)),), behind=(_lant(8, 21),))],
    # waves with the glove, lantern in the other hand (behind)
    "waving": [dict(eyes="happy", behind=(_lant(6, 23),), arms=(((16, 22), (20, 19)),), por=((GLOVE, 19, 17),)),
               dict(eyes="happy", behind=(_lant(6, 23),), arms=(((16, 22), (20, 16)),), por=((GLOVE, 19, 13),)),
               dict(eyes="happy", behind=(_lant(6, 23),), arms=(((16, 22), (23, 16)),), por=((GLOVE, 22, 13),)),
               dict(eyes="happy", behind=(_lant(6, 23),), arms=(((16, 22), (20, 16)),), por=((GLOVE, 19, 13),))],
    # crouches, jumps with the lantern up high, falls, lands
    "jumping": [dict(ch=6, eyes="closed", arms=(((17, 25), (21, 27)),), por=(_lant(22, 26),)),
                dict(ch=10, base=29, arms=(((17, 20), (24, 19)),), por=(_lant(24, 19),)),
                dict(ch=9, base=26, eyes="happy", arms=(((17, 18), (25, 16)),), por=(_lant(25, 16),)),
                dict(ch=10, base=29, arms=(((17, 21), (23, 21)),), por=(_lant(23, 21),)),
                dict(ch=7, eyes="happy", arms=(((17, 24), (21, 25)),), por=(_lant(22, 25),))],
    # sad, the mask slips, falls to the ground and the lantern goes out
    "failed": [dict(eyes="sad", arms=(((17, 22), (20, 25)),), por=(_lant(21, 25), (TEAR, 11, 13))),
               dict(mask=(2, 4), face_kind="o", arms=(((17, 22), (20, 25)),), por=(_lant(21, 25),)),
               dict(cx=12, mask=(5, 9), face_kind="o", arms=(((15, 22), (18, 26)),), por=(_lant(19, 26),)),
               dict(cx=10, ch=7, mask=(9, 8), face_kind="sad", lantern_ok=False,
                    behind=(_lant(3, 22),), por=((TEAR, 7, 19),)),
               dict(cx=10, ch=6, lean=-1, mask=(10, 9), face_kind="x", lantern_ok=False,
                    behind=(_lant(2, 22),))],
    # naps sitting sideways, lantern on the ground, "z" rising
    "waiting": [dict(ch=7, lean=-1, eyes="closed", behind=(_lant(23, 21),)),
                dict(ch=7, lean=-2, eyes="closed", behind=(_lant(23, 21),), por=((Z_S, 22, 4),)),
                dict(ch=7, lean=-2, eyes="closed", behind=(_lant(23, 21),), por=((Z_S, 21, 4), (Z_L, 26, 0))),
                dict(ch=7, lean=-1, eyes="closed", behind=(_lant(23, 21),), por=((Z_L, 26, 0),))],
    # attack: pulls the lantern back, swings forward and throws the poison flask, which bursts into a cloud
    "running": [dict(cx=13, lean=-2, eyes="angry", arms=(((12, 22), (6, 18)),), behind=(_lant(5, 18),)),
                dict(cx=14, lean=2, eyes="angry", arms=(((17, 21), (22, 14)),), por=(_lant(22, 14),)),
                dict(cx=14, lean=3, eyes="angry", arms=(((18, 22), (24, 20)),),
                     por=(_lant(24, 20), (FLASK_FLYING, 24, 1))),
                dict(cx=14, lean=1, eyes="angry", arms=(((17, 22), (21, 24)),),
                     por=(_lant(22, 24), (CLOUD, 22, 3), (CLOUD_S, 27, 11), (CLOUD_S, 19, 1)))],
    # glove on the beak's chin, thinking, "?" appears
    "review": [dict(cx=12, eyes="up", arms=(((15, 22), (19, 18)),), por=((HAND_FACE, 18, 16),)),
               dict(cx=12, eyes="up", arms=(((15, 22), (19, 18)),), por=((HAND_FACE, 18, 16), (QMARK_S, 25, 2))),
               dict(cx=12, eyes="up", arms=(((15, 22), (19, 18)),), por=((HAND_FACE, 18, 16), (QMARK, 25, 0))),
               dict(cx=12, eyes="normal", arms=(((15, 22), (19, 18)),), por=((HAND_FACE, 18, 16), (QMARK, 25, 0)))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# wide-brimmed hat (crown + brim), resting on top of the hood by the anchor
HAT = [
    "....KKKKKKK....",
    "....KkkkkkK....",
    "....KkkkkkK....",
    "....KRRRRRK....",
    "KKKKKKKKKKKKKKK",
    "KkkkkkkkkkkkkkK",
    ".KKKKKKKKKKKKK.",
]
# short cape draped over the back shoulder (below the neck); stops at the anchor column + 7 (x = head center)
# so it does not cover the front arm's joint, which starts at x >= center + 1
CAPE = ["." * 15] * 16 + [
    "..KKKKKK.......",
    ".KRRRRRK.......",
    "KRRRRRYK.......",
    "KRRRRRRK.......",
    "KrRRRRK........",
    "KrRRRRK........",
    "KrrRRK.........",
    "KrrrK..........",
    ".KKK...........",
]
DOCTOR = [HAT[i] if i < len(HAT) else CAPE[i] for i in range(len(CAPE))]
STAGES = [
    {"title": "Plague Apprentice", "floor": 1, "extra": None},
    {"title": "Plague Doctor", "floor": 4, "extra": HAT},
    {"title": "Blight Doctor", "floor": 10, "extra": DOCTOR},
]
