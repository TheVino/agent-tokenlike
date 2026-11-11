# -*- coding: utf-8 -*-
"""Efeitos visuais puros sobre mapas de pixels (sem tkinter).

Um PixelMap é {(x, y): "#rrggbb"}. Nenhuma função altera a entrada: todas devolvem um mapa novo.
Usado para compor o visual do pet a partir dos itens empilhados.
"""

DARK = "#1b1b2f"
# área máxima em pixels de arte, relativa ao quadro 16x16 em (0, 0): (x0, y0, x1, y1), x1/y1 exclusivos
LOOK_BOX = (-8, -10, 24, 20)


def grid_to_map(grid, pal):
    """Grade de texto -> mapa. Pula '.' e letras sem cor na paleta."""
    return {(x, y): pal[ch] for y, row in enumerate(grid) for x, ch in enumerate(row) if ch in pal}


def bbox(pm):
    """(x0, y0, x1, y1) com x1/y1 exclusivos; (0, 0, 0, 0) se vazio."""
    if not pm:
        return (0, 0, 0, 0)
    xs = [p[0] for p in pm]; ys = [p[1] for p in pm]
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def _cols(pm, step, start):
    """Colunas x0+start, x0+start+step... que têm pixel, com (y mínimo, y máximo) de cada uma."""
    x0, _, x1, _ = bbox(pm)
    out = []
    for x in range(x0 + start, x1, step):
        ys = [y for (px, y) in pm if px == x]
        if ys:
            out.append((x, min(ys), max(ys)))
    return out


def espinhos(pm, color, nivel=1):
    out = dict(pm)
    n = 3 if nivel >= 2 else 1
    for x, ymin, _ in _cols(pm, 2 if nivel >= 2 else 3, 1):
        for k in range(1, n + 1):
            out[(x, ymin - k)] = color
        out[(x, ymin - n - 1)] = DARK
    return out


def gotas(pm, color, nivel=1):
    out = dict(pm)
    for i, (x, _, ymax) in enumerate(_cols(pm, 3, 1)):
        for k in range(1, 1 + (i % 3) + nivel):
            out[(x, ymax + k)] = color
    return out


def contorno(pm, color):
    out = dict(pm)
    for (x, y) in pm:
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if p not in pm:
                out[p] = color
    return out


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def tingir(pm, color, amount):
    alvo = _rgb(color)
    out = {}
    for p, c in pm.items():
        r, g, b = _rgb(c)
        if 0.299 * r + 0.587 * g + 0.114 * b < 40:   # contorno escuro fica intacto
            out[p] = c
        else:
            m = [round(v * (1 - amount) + t * amount) for v, t in zip((r, g, b), alvo)]
            out[p] = "#%02x%02x%02x" % tuple(m)
    return out


def _colar(pm, art, dx, dy):
    out = dict(pm)
    for (x, y), c in art.items():
        out[(x + dx, y + dy)] = c
    return out


def adesivo(pm, art, at, glow=None):
    x0, y0, x1, y1 = bbox(pm)
    if glow:
        art = contorno(art, glow)
    ax0, ay0, ax1, ay1 = bbox(art)
    cx = round(x0 + at[0] * (x1 - x0)); cy = round(y0 + at[1] * (y1 - y0))
    return _colar(pm, art, cx - (ax0 + ax1) // 2, cy - (ay0 + ay1) // 2)


def _colocar(pm, art, box, anchor, ordem, glow):
    """Cola `art` junto à caixa `box` (do corpo) na âncora pedida; `ordem` afasta para fora."""
    x0, y0, x1, y1 = box
    ax0, ay0, ax1, ay1 = bbox(art)
    aw, ah = ax1 - ax0, ay1 - ay0
    cx, cy = (x0 + x1) // 2 - aw // 2, (y0 + y1) // 2 - ah // 2
    if anchor == "topo":
        tx, ty = cx, y0 + 2 - ah - ordem * (ah - 2)
    elif anchor == "esq":
        tx, ty = x0 - aw - ordem * (aw - 2), y1 - ah
    elif anchor == "dir":
        tx, ty = x1 + ordem * (aw - 2), y1 - ah
    elif anchor == "base":
        tx, ty = cx, y1 + ordem * (ah - 2)
    elif anchor == "flutua":
        k = ordem // 4 + 1   # ao acabar as 4 posições, repete mais longe
        tx, ty = [(x0 - aw * k, y0 - ah * k), (x1 + aw * (k - 1), y0 - ah * k),
                  (x0 - aw * k, cy), (x1 + aw * (k - 1), cy)][ordem % 4]
    else:  # frente
        tx, ty = cx, cy
    dx, dy = tx - ax0, ty - ay0
    out = dict(pm)
    if glow:
        for (x, y), c in contorno(art, glow).items():
            if (x, y) not in art and (x + dx, y + dy) not in out:
                out[(x + dx, y + dy)] = c
    return _colar(out, art, dx, dy)


def objeto(pm, art, anchor, ordem, glow=None):
    return _colocar(pm, art, bbox(pm), anchor, ordem, glow)


def compose(base, looks, arts):
    """looks = [(look, glow_color), ...] na ordem em que os itens foram pegos."""
    tipos = [l["type"] for l, _ in looks]
    out = dict(base)
    cont = {}
    for l, glow in looks:
        t = l["type"]
        if t in ("espinhos", "gotas"):
            out = (espinhos if t == "espinhos" else gotas)(out, l["color"], tipos.count(t))
        elif t == "contorno":
            out = contorno(out, l["color"])
        elif t == "tingir":
            out = tingir(out, l["color"], l["amount"])
        elif t == "adesivo":
            out = adesivo(out, arts[l["art"]], l["at"], glow)
    box = bbox(out)   # os objetos usam a caixa do corpo já mutado
    for l, glow in looks:
        if l["type"] == "obj":
            a = l["anchor"]
            out = _colocar(out, arts[l["art"]], box, a, cont.get(a, 0), glow)
            cont[a] = cont.get(a, 0) + 1
    return out


def crop(pm, box):
    x0, y0, x1, y1 = box
    return {p: c for p, c in pm.items() if x0 <= p[0] < x1 and y0 <= p[1] < y1}
