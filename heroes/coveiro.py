"""Coveiro, 32 px, olhando para a direita. Cada quadro sai de partes: casaco comprido marrom com remendos, cabeça
redonda e clara com boné chato (aba para a frente), botas, braços em linha grossa e a pá (cabo de pau, lâmina de
ferro). No `failed` ele escorrega para dentro da própria cova; sobra o monte de terra com a pá fincada e o boné.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, line, outline_cells, trait

PAL = {
    "K": "#1a1820", "C": "#6b4a32", "c": "#4a321f", "Q": "#9a8a55", "q": "#d8c98f", "F": "#efdcc4",
    "f": "#c9b49a", "D": "#454a5c", "d": "#2c303c", "N": "#a8743f", "S": "#a7b0ba", "s": "#68717c",
    "W": "#ffffff", "B": "#1a1820", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f", "O": "#ff8a3d",
    "k": "#2a2228", "E": "#6a4a30", "e": "#3e2a1a", "H": "#24242e", "R": "#8a2f45", "G": "#7d7790",
}

HAND = ["KKK", "KFK", "KKK"]
DIRT = [".KK.", "KEEK", "KeEK", ".KK."]          # torrão voando
DIRT_S = ["KK", "KK"]
SMOKE = [".G.", "G.G", ".G.", "G..", ".G."]       # fumacinha do lampião apagando


def _pa(g, handle, tip):
    """Pá: cabo de pau de `cabo` até `ponta` e lâmina de ferro (5x5 arredondada) na ponta, apontando para fora."""
    px = {p: "N" for p in line(*handle, *tip)}
    cx, cy = handle
    px[(cx, cy)] = "N"
    px[(cx + (1 if cx <= tip[0] else -1), cy)] = "N"     # puxador em T
    px[(cx - (1 if cx <= tip[0] else -1), cy)] = "N"
    dx, dy = tip[0] - cx, tip[1] - cy
    n = max(abs(dx), abs(dy), 1)
    bx, by = round(tip[0] + 2 * dx / n), round(tip[1] + 2 * dy / n)
    for x in range(bx - 2, bx + 3):
        for y in range(by - 2, by + 3):
            if (x - bx) ** 2 + (y - by) ** 2 <= 5:
                px[(x, y)] = "s" if (x - bx) + (y - by) > 1 else "S"
    px[(bx - 1, by - 1)] = "W"
    outline_cells(g, px)


def _cap(g, hx, hy):
    """Boné chato de lã sobre a cabeça, com aba curta para a frente (direita)."""
    px = {}
    for y in range(hy - 6, hy - 2):
        half = 4 if y == hy - 6 else 5
        for x in range(hx - half, hx + half + 1):
            px[(x, y)] = "d" if y == hy - 3 else "D"
    for x in range(hx + 3, hx + 8):
        px[(x, hy - 3)] = "d"
    outline_cells(g, px)


def _face(g, hx, hy, eyes):
    for x in (hx + 1, hx + 4):
        if eyes == "fechado":
            stamp(g, ["BB"], x, hy + 1)
        elif eyes == "feliz":
            stamp(g, [".B.", "B.B"], x - 1, hy)
        elif eyes == "x":
            stamp(g, ["B.B", ".B.", "B.B"], x - 1, hy - 1)
        else:
            dy = -1 if eyes == "cima" else 0
            stamp(g, ["B", "B"], x, hy + dy)
            if eyes == "bravo":
                g[hy - 1][x - 1 if x == hx + 1 else x + 1] = "B"
                g[hy - 2][x - 2 if x == hx + 1 else x + 2] = "B"
            if eyes == "triste":
                g[hy - 1][x + 1 if x == hx + 1 else x - 1] = "B"
    if eyes in ("triste", "x"):
        stamp(g, [".B.", "B.B"], hx + 2, hy + 3)
    elif eyes == "bravo":
        stamp(g, ["BBB"], hx + 2, hy + 3)
    else:
        stamp(g, ["B.B", ".B."], hx + 2, hy + 3)
    g[hy + 2][hx] = g[hy + 2][hx + 6] = "P"


def _grave(g, cx, y, half):
    """Boca da cova: buraco escuro com a borda de terra na frente (por cima do corpo que afunda)."""
    px = {}
    for x in range(cx - half, cx + half + 1):
        for yy in range(y, N - 1):
            px[(x, yy)] = "e" if yy < y + 1 else "E"
    outline_cells(g, px)


def _mound(g, cx, y):
    """Monte de terra da cova fechada."""
    px = {}
    for dy, half in ((0, 5), (1, 8), (2, 10), (3, 11)):
        for x in range(cx - half, cx + half + 1):
            px[(x, y + dy)] = "e" if dy == 3 else "E"
    for x in range(cx - 7, cx + 8, 4):
        px[(x, y + 1)] = "e"
    outline_cells(g, px)


def frame(cx=14, base=30, ch=9, lean=0, eyes="normal", feet=(0, 0), behind=(), arms=(), pas=(), por=(),
           sinks=0, grave=None, mound=None):
    """Um quadro 32x32 e a âncora do acréscimo (cabeça - 12). `afunda` desce o corpo na cova `cova` (cx, y, meia);
    `monte` (cx, y) desenha só a cova fechada com a pá fincada e o boné pendurado nela; `pas`: (cabo, ponta)."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    if mound:
        mx, my = mound
        _pa(g, (mx + 6, my - 8), (mx + 6, my - 2))
        _mound(g, mx, my)
        _cap(g, mx + 6, my - 4)              # boné pendurado no cabo da pá
        for s, x, y in por:
            stamp(g, s, x, y)
        return ["".join(l) for l in g], (mx - 6, my - 16)
    base += sinks
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 4
    coat = set()
    for y in range(ctop, base - 1):
        t = (y - ctop) / max(ch - 1, 1)
        half = 3.5 + t * 2.5
        c = cx + lean * (1 - t) * 0.6
        coat |= {(x, y) for x in range(round(c - half), round(c + half) + 1)}
    head = {(x, y) for x in range(hx - 5, hx + 6) for y in range(hy - 5, hy + 6)
              if (x - hx) ** 2 + (y - hy) ** 2 <= 22}
    px = {}
    for p in coat:
        edge = (p[0] + 1, p[1]) not in coat or (p[0], p[1] + 1) not in coat
        px[p] = "c" if edge else "C"
    rx, ry = round(cx - 3 + lean * 0.3), ctop + ch // 2       # remendo com pontos
    for x in range(rx, rx + 3):
        for y in range(ry, ry + 3):
            if (x, y) in px:
                px[(x, y)] = "Q"
    if (rx + 1, ry + 1) in px:
        px[(rx + 1, ry + 1)] = "q"
    for y in range(ctop + 1, base - 2, 2):                     # botões
        if (round(cx + 2 + lean * 0.3), y) in px:
            px[(round(cx + 2 + lean * 0.3), y)] = "k"
    for p in head:
        px[p] = "f" if (p[0], p[1] + 1) not in head and p[1] > hy else "F"
    if not sinks:
        for x0 in (cx - 4 + feet[0], cx + 2 + feet[1]):
            for x in range(x0, x0 + 3):
                for y in (base - 2, base - 1):
                    px[(x, y)] = "k"
    outline_cells(g, px)
    _face(g, hx, hy, eyes)
    _cap(g, hx, hy)
    for a, b in arms:
        trait(g, a, b, "C")
        stamp(g, HAND, b[0] - 1, b[1] - 1)
    for handle, tip in pas:
        _pa(g, handle, tip)
        stamp(g, HAND, handle[0] + (1 if tip[0] >= handle[0] else -1) * 2 - 1, handle[1] - 1 + (tip[1] > handle[1]) * 2)
    if grave:
        _grave(g, *grave)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (hx - 12, hy - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, ch=9 -> ctop=20, cabeça hy=16; ombro ~(cx + 2, 22)
_SPECS = {
    # parado, apoiado na pá fincada no chão; a pá balança e ele pisca
    "idle": [dict(arms=(((16, 22), (20, 21)),), pas=(((21, 18), (21, 25)),)),
             dict(arms=(((16, 22), (20, 21)),), pas=(((21, 18), (22, 25)),)),
             dict(eyes="fechado", arms=(((16, 22), (20, 21)),), pas=(((21, 18), (22, 25)),)),
             dict(arms=(((16, 22), (20, 22)),), pas=(((21, 19), (21, 26)),), por=((DIRT_S, 26, 28),))],
    # corre de lado olhando para a frente, pá no ombro, botas alternando
    "run_r": [dict(cx=15, lean=1, feet=(-2, 2), arms=(((15, 22), (18, 21)),), pas=(((19, 21), (8, 14)),)),
              dict(cx=15, lean=2, base=29, arms=(((15, 21), (18, 20)),), pas=(((19, 20), (8, 12)),)),
              dict(cx=15, lean=1, feet=(2, -2), arms=(((15, 22), (18, 21)),), pas=(((19, 21), (8, 15)),)),
              dict(cx=15, lean=2, base=29, arms=(((15, 21), (18, 20)),), pas=(((19, 20), (8, 13)),))],
    # acena com a mão livre, pá fincada atrás
    "waving": [dict(eyes="feliz", pas=(((9, 18), (8, 25)),), arms=(((16, 22), (21, 19)),)),
               dict(eyes="feliz", pas=(((9, 18), (8, 25)),), arms=(((16, 22), (21, 15)),)),
               dict(eyes="feliz", pas=(((9, 18), (8, 25)),), arms=(((16, 22), (24, 15)),)),
               dict(eyes="feliz", pas=(((9, 18), (8, 25)),), arms=(((16, 22), (21, 15)),))],
    # agacha, salta com a pá erguida, cai, pousa
    "jumping": [dict(ch=7, eyes="fechado", arms=(((16, 24), (20, 25)),), pas=(((21, 22), (22, 28)),)),
                dict(ch=10, base=28, arms=(((16, 19), (21, 16)),), pas=(((22, 16), (25, 7)),)),
                dict(ch=9, base=26, eyes="feliz", arms=(((16, 17), (21, 13)),), pas=(((22, 13), (25, 4)),)),
                dict(ch=10, base=28, arms=(((16, 20), (21, 18)),), pas=(((22, 18), (25, 10)),)),
                dict(ch=7, eyes="feliz", arms=(((16, 24), (20, 25)),), pas=(((21, 22), (23, 28)),))],
    # triste, solta a pá, escorrega para a própria cova, que se fecha; fica o boné no monte
    "failed": [dict(eyes="triste", pas=(((21, 22), (26, 28)),), por=((TEAR, 20, 17),)),
               dict(eyes="triste", sinks=4, grave=(14, 28, 9), por=((TEAR, 20, 21),)),
               dict(eyes="x", sinks=7, grave=(14, 28, 9)),
               dict(mound=(14, 26), por=((SMOKE, 28, 14),)),
               dict(mound=(14, 26), por=((SMOKE, 29, 10),))],
    # cochila apoiado na pá, cabeça pende, "z" subindo
    "waiting": [dict(ch=8, lean=-1, eyes="fechado", arms=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),)),
                dict(ch=8, lean=-2, eyes="fechado", arms=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),),
                     por=((Z_S, 23, 4),)),
                dict(ch=8, lean=-2, eyes="fechado", arms=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),),
                     por=((Z_S, 22, 4), (Z_L, 26, 0))),
                dict(ch=8, lean=-1, eyes="fechado", arms=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),),
                     por=((Z_L, 26, 0),))],
    # golpe: ergue a pá atrás da cabeça, desce num arco e bate no chão levantando terra
    "running": [dict(cx=13, lean=-2, eyes="bravo", arms=(((13, 22), (10, 18)),), pas=(((10, 17), (5, 7)),)),
                dict(cx=14, lean=0, eyes="bravo", arms=(((15, 21), (18, 15)),), pas=(((18, 14), (20, 4)),)),
                dict(cx=14, lean=2, eyes="bravo", arms=(((16, 22), (21, 19)),), pas=(((21, 19), (28, 14)),),
                     por=((DIRT_S, 29, 9),)),
                dict(cx=14, lean=2, eyes="bravo", arms=(((16, 23), (20, 23)),), pas=(((20, 22), (26, 27)),),
                     por=((DIRT, 27, 20), (DIRT_S, 23, 18), (DIRT_S, 30, 24)))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=12, eyes="cima", arms=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),)),
               dict(cx=12, eyes="cima", arms=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),),
                    por=((QMARK_S, 24, 2),)),
               dict(cx=12, eyes="cima", arms=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),),
                    por=((QMARK, 24, 0),)),
               dict(cx=12, eyes="normal", arms=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),),
                    por=((QMARK, 24, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# O extra tem duas cópias lado a lado: a normal (colunas 0-24, presa em cabeça - 12) e, a partir da coluna _COVA,
# a da cova fechada (32x32, coordenadas do próprio quadro): lampião apagado no chão à direita do monte (a fumaça
# do quadro base sai dele) e, no estágio 3, o chapéu alto largado no monte. Nos 2 últimos quadros do failed a âncora
# vai para (-_COVA, 0): a cópia normal sai pela esquerda (cortada) e só a da cova aparece; no resto a da cova sai pela direita.
_GRAVE = 40
ANCHOR["failed"][3:] = [(-_GRAVE, 0)] * 2
_EMPTY = "." * _GRAVE

# lampião pendurado num gancho, flutuando atrás (à esquerda); âncora = cabeça - 12; apagado na cova
_LAMP = ["..KK..", ".K..K.", "KKKKKK", "KYOOYK", "KYWYYK", "KOYYOK", "KKKKKK", ".KssK.", "..KK.."]
_LAMP_OFF = ["..KK..", ".K..K.", "KKKKKK", "KddddK", "KdDddK", "KddddK", "KKKKKK", ".KssK.", "..KK.."]
# chapéu alto de guardião com fita vinho, por cima do boné
_TOPHAT = [
    "..KKKKKKK..",
    "..KHHHHHK..",
    "..KHHHHHK..",
    "..KHHHHHK..",
    "..KRRRRRK..",
    "KKKKKKKKKKK",
    "KHHHHHHHHHK",
    "KKKKKKKKKKK",
]


def _extra(top_hat):
    g = [["."] * (_GRAVE + N) for _ in range(N)]
    pieces = [(_LAMP, 0, 12), (_LAMP_OFF, _GRAVE + 26, 22)]
    if top_hat:
        pieces += [(_TOPHAT, 6, 0), (_TOPHAT, _GRAVE + 5, 18)]   # na cova: largado no ombro esquerdo do monte
    for sp, x, y in pieces:
        for dy, lin in enumerate(sp):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


LAMP = _extra(False)
GUARDIAN = _extra(True)
STAGES = [
    {"title": "Ajudante de Coveiro", "floor": 1, "extra": None},
    {"title": "Coveiro", "floor": 4, "extra": LAMP},
    {"title": "Guardião do Cemitério", "floor": 10, "extra": GUARDIAN},
]
