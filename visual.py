# -*- coding: utf-8 -*-
"""Pure visual effects on pixel maps (no tkinter).

A PixelMap is {(x, y): "#rrggbb"}. No function changes its input: all of them return a new map.
Used to compose the pet's look from the stacked items.
"""

DARK = "#1b1b2f"
# max area in art pixels, relative to the 16x16 frame at (0, 0): (x0, y0, x1, y1), x1/y1 exclusive
LOOK_BOX = (-8, -10, 24, 20)


def look_box(k=1):
    """LOOK_BOX for a hero k times bigger than 16 px (k*16 frame at (0, 0))."""
    return tuple(v * k for v in LOOK_BOX)


def scale(pm, k):
    """Each pixel becomes k x k."""
    if k == 1:
        return pm
    return {(x * k + i, y * k + j): c for (x, y), c in pm.items() for i in range(k) for j in range(k)}


def grid_to_map(grid, pal):
    """Text grid -> map. Skips '.' and letters without a color in the palette."""
    return {(x, y): pal[ch] for y, row in enumerate(grid) for x, ch in enumerate(row) if ch in pal}


def bbox(pm):
    """(x0, y0, x1, y1) with x1/y1 exclusive; (0, 0, 0, 0) if empty."""
    if not pm:
        return (0, 0, 0, 0)
    xs = [p[0] for p in pm]; ys = [p[1] for p in pm]
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _cols(pm, step, start):
    """Columns x0+start, x0+start+step... that have pixels, with (min y, max y) of each one."""
    x0, _, x1, _ = bbox(pm)
    out = []
    for x in range(x0 + start, x1, step):
        ys = [y for (px, y) in pm if px == x]
        if ys:
            out.append((x, min(ys), max(ys)))
    return out


def thorns(pm, color, level=1):
    out = dict(pm)
    n = 3 if level >= 2 else 1
    for x, ymin, _ in _cols(pm, 2 if level >= 2 else 3, 1):
        for k in range(1, n + 1):
            out[(x, ymin - k)] = color
        out[(x, ymin - n - 1)] = DARK
    return out


def drops(pm, color, level=1):
    out = dict(pm)
    for i, (x, _, ymax) in enumerate(_cols(pm, 3, 1)):
        for k in range(1, 1 + (i % 3) + level):
            out[(x, ymax + k)] = color
    return out


def _external(pm):
    """Empty cells connected to the border (flood fill in a box with 1 px of slack). Holes inside the silhouette
    (hollow eyes, the ghost's fading checkerboard) are left out, so border effects do not paint the middle."""
    x0, y0, x1, y1 = bbox(pm)
    x0, y0, x1, y1 = x0 - 1, y0 - 1, x1 + 1, y1 + 1
    outside, stack = set(), [(x0, y0)]
    while stack:
        q = stack.pop()
        if q in outside or q in pm or not (x0 <= q[0] < x1 and y0 <= q[1] < y1):
            continue
        outside.add(q)
        x, y = q
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return outside


def contour(pm, color):
    out = dict(pm)
    outside = _external(pm)
    for (x, y) in pm:
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if p in outside:
                out[p] = color
    return out


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def tint(pm, color, amount):
    target = _rgb(color)
    out = {}
    for p, c in pm.items():
        r, g, b = _rgb(c)
        if 0.299 * r + 0.587 * g + 0.114 * b < 40:   # the dark outline stays intact
            out[p] = c
        else:
            m = [round(v * (1 - amount) + t * amount) for v, t in zip((r, g, b), target)]
            out[p] = "#%02x%02x%02x" % tuple(m)
    return out


def _necklace(pm, art, dx, dy):
    out = dict(pm)
    for (x, y), c in art.items():
        out[(x + dx, y + dy)] = c
    return out


def _anel(art, glow, k=1):
    """Art + glow k pixels thick (k=1: the usual outline)."""
    for _ in range(k):
        art = contour(art, glow)
    return art


def sticker(pm, art, at, glow=None, k=1):
    x0, y0, x1, y1 = bbox(pm)
    if glow:
        art = _anel(art, glow, k)
    ax0, ay0, ax1, ay1 = bbox(art)
    cx = round(x0 + at[0] * (x1 - x0)); cy = round(y0 + at[1] * (y1 - y0))
    return _necklace(pm, art, cx - (ax0 + ax1) // 2, cy - (ay0 + ay1) // 2)


def _place(pm, art, box, anchor, order, glow, k=1):
    """Pastes `art` next to box `box` (the body's) at the requested anchor; `order` moves it outward."""
    x0, y0, x1, y1 = box
    ax0, ay0, ax1, ay1 = bbox(art)
    aw, ah = ax1 - ax0, ay1 - ay0
    cx, cy = (x0 + x1) // 2 - aw // 2, (y0 + y1) // 2 - ah // 2
    if anchor == "top":
        tx, ty = cx, y0 + 2 - ah - order * (ah - 2)
    elif anchor == "left":
        tx, ty = x0 - aw - order * (aw - 2), y1 - ah
    elif anchor == "right":
        tx, ty = x1 + order * (aw - 2), y1 - ah
    elif anchor == "base":
        tx, ty = cx, y1 + order * (ah - 2)
    elif anchor == "float":
        n = order // 4 + 1   # after the 4 positions, repeat farther out
        tx, ty = [(x0 - aw * n, y0 - ah * n), (x1 + aw * (n - 1), y0 - ah * n),
                  (x0 - aw * n, cy), (x1 + aw * (n - 1), cy)][order % 4]
    else:  # front: order alternates right/left of the center, moving away
        side = 1 if order % 2 else -1
        if order == 0:
            side = 0
        tx, ty = cx + side * ((order + 1) // 2) * max(aw - 2, 1), cy
    dx, dy = tx - ax0, ty - ay0
    out = dict(pm)
    if glow:
        for (x, y), c in _anel(art, glow, k).items():
            if (x, y) not in art and (x + dx, y + dy) not in out:
                out[(x + dx, y + dy)] = c
    return _necklace(out, art, dx, dy)


def place_object(pm, art, anchor, order, glow=None):
    return _place(pm, art, bbox(pm), anchor, order, glow)


PHASES = 3   # frames of the elemental look animation


def flames(pm, level=1, phase=0, color="#ff9f43", tip="#ffd23f"):
    """Flames on top of every 2nd column; the height cycles with the phase."""
    out = dict(pm)
    for i, (x, ymin, _) in enumerate(_cols(pm, 2, 0)):
        h = 1 + (i + phase) % 3 + (level - 1)
        for k in range(1, h + 1):
            out[(x, ymin - k)] = tip if k == h else color
    return out


def sparks(pm, level=1, phase=0, color="#fff27a"):
    """Sparks on the outline (pixels just outside the silhouette); the phase changes which subset is lit."""
    ext = _external(pm)
    outside = sorted({q for (x, y) in pm for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if q in ext},
                  key=lambda q: (q[1], q[0]))
    out = dict(pm)
    for j, q in enumerate(outside):
        if (j + phase) % 4 < level:
            out[q] = color
    return out


def poison_drops(pm, level=1, phase=0, color="#4fbf5a"):
    """Falling drops: fixed length, start 1 px lower each phase (and go back to the top)."""
    out = dict(pm)
    for i, (x, _, ymax) in enumerate(_cols(pm, 2, 0)):
        off = (i + phase) % 3
        for k in range(1 + level):
            out[(x, ymax + 1 + off + k)] = color
    return out


def frost(pm, level=1, phase=0, color="#9fe8ff", white="#ffffff"):
    """Recolors the body's border with frost (same silhouette); the phase changes which pixels."""
    out = dict(pm)
    ext = _external(pm)
    for (x, y) in pm:
        if any(p in ext for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
            r = (x + y + phase) % 3
            if r < level:
                out[(x, y)] = white if r == 0 else color
    return out


ELEMENTALS = {"flames": flames, "sparks": sparks, "poison_drops": poison_drops, "frost": frost}


def has_anim(looks):
    return any(l["type"] in ELEMENTALS for l, _ in looks)


def compose(base, looks, arts, phase=0, k=1):
    """looks = [(look, glow_color), ...] in the order the items were taken.

    k = how many times the hero is bigger than 16 px. Objects and stickers (item art, drawn at 16 px) are
    scaled by k, so they have the same on-screen size as the hero (which is drawn with px/k). The rarity glow
    of those objects is k pixels thick. Effects on the body (thorns, drops, outline, flames, sparks, poison, frost) are 1 hero pixel thick:
    they follow the big silhouette without getting thicker. With k=1 the result is identical to before."""
    kinds = [l["type"] for l, _ in looks]
    out = dict(base)
    done = set()
    for l, glow in looks:
        t = l["type"]
        if t in ELEMENTALS:
            continue   # animated looks come after the objects box, so it does not change with the phase
        if t in ("thorns", "drops"):
            # applied only once, at level = number of looks of that type, with the color of the FIRST look of the type
            if t not in done:
                done.add(t)
                out = (thorns if t == "thorns" else drops)(out, l["color"], kinds.count(t))
        elif t == "outline":
            out = contour(out, l["color"])
        elif t == "tint":
            out = tint(out, l["color"], l["amount"])
        elif t == "sticker":
            out = sticker(out, scale(arts[l["art"]], k), l["at"], glow, k)
    box = bbox(out)   # objects use the box of the already mutated body (without the animated looks: the same in every phase)
    for l, _ in looks:
        t = l["type"]
        if t in ELEMENTALS and t not in done:
            # like thorns: only once, level = number of looks of that type, color of the first one (default if none)
            done.add(t)
            kw = {"color": l["color"]} if "color" in l else {}
            out = ELEMENTALS[t](out, kinds.count(t), phase, **kw)
    per_anchor = {}
    for l, glow in looks:
        if l["type"] == "obj":
            per_anchor.setdefault(l["anchor"], []).append((scale(arts[l["art"]], k), glow))
    for a, objs in per_anchor.items():
        # if space runs out, the most recent ones at that anchor stay: the largest k whose last k fit in LOOK_BOX
        n = len(objs)
        while n > 1 and not all(_fits(art, box, a, o, k) for o, (art, _) in enumerate(objs[-n:])):
            n -= 1
        for o, (art, glow) in enumerate(objs[-n:]):
            out = _place(out, art, box, a, o, glow, k)
    return out


def _fits(art, box, anchor, order, k=1):
    """Does the art (without the glow) fit entirely inside look_box(k) at this position?"""
    x0, y0, x1, y1 = look_box(k)
    return all(x0 <= x < x1 and y0 <= y < y1 for (x, y) in _place({}, art, box, anchor, order, None))


def crop(pm, box):
    x0, y0, x1, y1 = box
    return {p: c for p, c in pm.items() if x0 <= p[0] < x1 and y0 <= p[1] < y1}
