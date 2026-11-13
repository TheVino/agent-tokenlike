# -*- coding: utf-8 -*-
"""Efeitos visuais puros sobre mapas de pixels (sem tkinter).

Um PixelMap é {(x, y): "#rrggbb"}. Nenhuma função altera a entrada: todas devolvem um mapa novo.
Usado para compor o visual do pet a partir dos itens empilhados.
"""

DARK = "#1b1b2f"
# área máxima em pixels de arte, relativa ao quadro 16x16 em (0, 0): (x0, y0, x1, y1), x1/y1 exclusivos
LOOK_BOX = (-8, -10, 24, 20)


def look_box(k=1):
    """LOOK_BOX para um herói k vezes maior que 16 px (quadro k*16 em (0, 0))."""
    return tuple(v * k for v in LOOK_BOX)


def escalar(pm, k):
    """Cada pixel vira k x k."""
    if k == 1:
        return pm
    return {(x * k + i, y * k + j): c for (x, y), c in pm.items() for i in range(k) for j in range(k)}


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


def _externo(pm):
    """Células vazias ligadas à borda (flood fill numa caixa com 1 px de folga). Buracos internos da silhueta
    (olhos vazados, o quadriculado do fantasma sumindo) não entram, para os efeitos de borda não pintarem o meio."""
    x0, y0, x1, y1 = bbox(pm)
    x0, y0, x1, y1 = x0 - 1, y0 - 1, x1 + 1, y1 + 1
    fora, pilha = set(), [(x0, y0)]
    while pilha:
        q = pilha.pop()
        if q in fora or q in pm or not (x0 <= q[0] < x1 and y0 <= q[1] < y1):
            continue
        fora.add(q)
        x, y = q
        pilha += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return fora


def contorno(pm, color):
    out = dict(pm)
    fora = _externo(pm)
    for (x, y) in pm:
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if p in fora:
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


def _anel(art, glow, k=1):
    """Arte + brilho de k pixels de espessura (k=1: o contorno de sempre)."""
    for _ in range(k):
        art = contorno(art, glow)
    return art


def adesivo(pm, art, at, glow=None, k=1):
    x0, y0, x1, y1 = bbox(pm)
    if glow:
        art = _anel(art, glow, k)
    ax0, ay0, ax1, ay1 = bbox(art)
    cx = round(x0 + at[0] * (x1 - x0)); cy = round(y0 + at[1] * (y1 - y0))
    return _colar(pm, art, cx - (ax0 + ax1) // 2, cy - (ay0 + ay1) // 2)


def _colocar(pm, art, box, anchor, ordem, glow, k=1):
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
        n = ordem // 4 + 1   # ao acabar as 4 posições, repete mais longe
        tx, ty = [(x0 - aw * n, y0 - ah * n), (x1 + aw * (n - 1), y0 - ah * n),
                  (x0 - aw * n, cy), (x1 + aw * (n - 1), cy)][ordem % 4]
    else:  # frente: ordem alterna direita/esquerda do centro, afastando
        lado = 1 if ordem % 2 else -1
        if ordem == 0:
            lado = 0
        tx, ty = cx + lado * ((ordem + 1) // 2) * max(aw - 2, 1), cy
    dx, dy = tx - ax0, ty - ay0
    out = dict(pm)
    if glow:
        for (x, y), c in _anel(art, glow, k).items():
            if (x, y) not in art and (x + dx, y + dy) not in out:
                out[(x + dx, y + dy)] = c
    return _colar(out, art, dx, dy)


def objeto(pm, art, anchor, ordem, glow=None):
    return _colocar(pm, art, bbox(pm), anchor, ordem, glow)


FASES = 3   # quadros da animação dos looks elementais


def chamas(pm, nivel=1, fase=0, cor="#ff9f43", ponta="#ffd23f"):
    """Chamas no topo de cada 2ª coluna; a altura gira com a fase."""
    out = dict(pm)
    for i, (x, ymin, _) in enumerate(_cols(pm, 2, 0)):
        h = 1 + (i + fase) % 3 + (nivel - 1)
        for k in range(1, h + 1):
            out[(x, ymin - k)] = ponta if k == h else cor
    return out


def faiscas(pm, nivel=1, fase=0, cor="#fff27a"):
    """Faíscas no contorno (pixels logo fora da silhueta); a fase muda o subconjunto aceso."""
    ext = _externo(pm)
    fora = sorted({q for (x, y) in pm for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if q in ext},
                  key=lambda q: (q[1], q[0]))
    out = dict(pm)
    for j, q in enumerate(fora):
        if (j + fase) % 4 < nivel:
            out[q] = cor
    return out


def gotas_veneno(pm, nivel=1, fase=0, cor="#4fbf5a"):
    """Gotas que caem: comprimento fixo, começam 1 px mais abaixo a cada fase (e voltam ao topo)."""
    out = dict(pm)
    for i, (x, _, ymax) in enumerate(_cols(pm, 2, 0)):
        off = (i + fase) % 3
        for k in range(1 + nivel):
            out[(x, ymax + 1 + off + k)] = cor
    return out


def geada(pm, nivel=1, fase=0, cor="#9fe8ff", branco="#ffffff"):
    """Recolore a borda do corpo com gelo (silhueta igual); a fase muda quais pixels."""
    out = dict(pm)
    ext = _externo(pm)
    for (x, y) in pm:
        if any(p in ext for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
            r = (x + y + fase) % 3
            if r < nivel:
                out[(x, y)] = branco if r == 0 else cor
    return out


ELEMENTAIS = {"chamas": chamas, "faiscas": faiscas, "gotas_veneno": gotas_veneno, "geada": geada}


def tem_animacao(looks):
    return any(l["type"] in ELEMENTAIS for l, _ in looks)


def compose(base, looks, arts, fase=0, k=1):
    """looks = [(look, glow_color), ...] na ordem em que os itens foram pegos.

    k = quantas vezes o herói é maior que 16 px. Objetos e adesivos (arte de item, desenhada em 16 px) são
    ampliados por k, para terem o mesmo tamanho na tela do herói (que é desenhado com px/k). O brilho de raridade
    desses objetos tem k pixels de espessura. Efeitos sobre o corpo (espinhos, gotas, contorno, chamas, faíscas, veneno, geada) ficam com 1 pixel de herói de espessura:
    seguem a silhueta grande sem engrossar. Com k=1 o resultado é idêntico ao de sempre."""
    tipos = [l["type"] for l, _ in looks]
    out = dict(base)
    feito = set()
    for l, glow in looks:
        t = l["type"]
        if t in ELEMENTAIS:
            continue   # animados entram depois da caixa dos objetos, para ela não mudar com a fase
        if t in ("espinhos", "gotas"):
            # aplica uma vez só, no nível = nº de looks do tipo, com a cor do PRIMEIRO look do tipo
            if t not in feito:
                feito.add(t)
                out = (espinhos if t == "espinhos" else gotas)(out, l["color"], tipos.count(t))
        elif t == "contorno":
            out = contorno(out, l["color"])
        elif t == "tingir":
            out = tingir(out, l["color"], l["amount"])
        elif t == "adesivo":
            out = adesivo(out, escalar(arts[l["art"]], k), l["at"], glow, k)
    box = bbox(out)   # os objetos usam a caixa do corpo já mutado (sem os looks animados: igual em todas as fases)
    for l, _ in looks:
        t = l["type"]
        if t in ELEMENTAIS and t not in feito:
            # como espinhos: uma vez só, nível = nº de looks do tipo, cor do primeiro (padrão se não houver)
            feito.add(t)
            kw = {"cor": l["color"]} if "color" in l else {}
            out = ELEMENTAIS[t](out, tipos.count(t), fase, **kw)
    por_ponto = {}
    for l, glow in looks:
        if l["type"] == "obj":
            por_ponto.setdefault(l["anchor"], []).append((escalar(arts[l["art"]], k), glow))
    for a, objs in por_ponto.items():
        # se faltar espaço, ficam os mais recentes do ponto: o maior k em que os k últimos cabem em LOOK_BOX
        n = len(objs)
        while n > 1 and not all(_cabe(art, box, a, o, k) for o, (art, _) in enumerate(objs[-n:])):
            n -= 1
        for o, (art, glow) in enumerate(objs[-n:]):
            out = _colocar(out, art, box, a, o, glow, k)
    return out


def _cabe(art, box, anchor, ordem, k=1):
    """A arte (sem o brilho) inteira dentro de look_box(k) nessa posição?"""
    x0, y0, x1, y1 = look_box(k)
    return all(x0 <= x < x1 and y0 <= y < y1 for (x, y) in _colocar({}, art, box, anchor, ordem, None))


def crop(pm, box):
    x0, y0, x1, y1 = box
    return {p: c for p, c in pm.items() if x0 <= p[0] < x1 and y0 <= p[1] < y1}
