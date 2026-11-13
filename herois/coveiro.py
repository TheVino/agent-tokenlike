"""Coveiro, 32 px, olhando para a direita. Cada quadro sai de partes: casaco comprido marrom com remendos, cabeça
redonda e clara com boné chato (aba para a frente), botas, braços em linha grossa e a pá (cabo de pau, lâmina de
ferro). No `failed` ele escorrega para dentro da própria cova; sobra o monte de terra com a pá fincada e o boné.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, linha, contornar, traco

PAL = {
    "K": "#1a1820", "C": "#6b4a32", "c": "#4a321f", "Q": "#9a8a55", "q": "#d8c98f", "F": "#efdcc4",
    "f": "#c9b49a", "D": "#454a5c", "d": "#2c303c", "N": "#a8743f", "S": "#a7b0ba", "s": "#68717c",
    "W": "#ffffff", "B": "#1a1820", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f", "O": "#ff8a3d",
    "k": "#2a2228", "E": "#6a4a30", "e": "#3e2a1a", "H": "#24242e", "R": "#8a2f45", "G": "#7d7790",
}

MAO = ["KKK", "KFK", "KKK"]
TERRA = [".KK.", "KEEK", "KeEK", ".KK."]          # torrão voando
TERRA_P = ["KK", "KK"]
FUMACA = [".G.", "G.G", ".G.", "G..", ".G."]       # fumacinha do lampião apagando


def _pa(g, cabo, ponta):
    """Pá: cabo de pau de `cabo` até `ponta` e lâmina de ferro (5x5 arredondada) na ponta, apontando para fora."""
    px = {p: "N" for p in linha(*cabo, *ponta)}
    cx, cy = cabo
    px[(cx, cy)] = "N"
    px[(cx + (1 if cx <= ponta[0] else -1), cy)] = "N"     # puxador em T
    px[(cx - (1 if cx <= ponta[0] else -1), cy)] = "N"
    dx, dy = ponta[0] - cx, ponta[1] - cy
    n = max(abs(dx), abs(dy), 1)
    bx, by = round(ponta[0] + 2 * dx / n), round(ponta[1] + 2 * dy / n)
    for x in range(bx - 2, bx + 3):
        for y in range(by - 2, by + 3):
            if (x - bx) ** 2 + (y - by) ** 2 <= 5:
                px[(x, y)] = "s" if (x - bx) + (y - by) > 1 else "S"
    px[(bx - 1, by - 1)] = "W"
    contornar(g, px)


def _bone(g, hx, hy):
    """Boné chato de lã sobre a cabeça, com aba curta para a frente (direita)."""
    px = {}
    for y in range(hy - 6, hy - 2):
        meia = 4 if y == hy - 6 else 5
        for x in range(hx - meia, hx + meia + 1):
            px[(x, y)] = "d" if y == hy - 3 else "D"
    for x in range(hx + 3, hx + 8):
        px[(x, hy - 3)] = "d"
    contornar(g, px)


def _rosto(g, hx, hy, olhos):
    for x in (hx + 1, hx + 4):
        if olhos == "fechado":
            carimbar(g, ["BB"], x, hy + 1)
        elif olhos == "feliz":
            carimbar(g, [".B.", "B.B"], x - 1, hy)
        elif olhos == "x":
            carimbar(g, ["B.B", ".B.", "B.B"], x - 1, hy - 1)
        else:
            dy = -1 if olhos == "cima" else 0
            carimbar(g, ["B", "B"], x, hy + dy)
            if olhos == "bravo":
                g[hy - 1][x - 1 if x == hx + 1 else x + 1] = "B"
                g[hy - 2][x - 2 if x == hx + 1 else x + 2] = "B"
            if olhos == "triste":
                g[hy - 1][x + 1 if x == hx + 1 else x - 1] = "B"
    if olhos in ("triste", "x"):
        carimbar(g, [".B.", "B.B"], hx + 2, hy + 3)
    elif olhos == "bravo":
        carimbar(g, ["BBB"], hx + 2, hy + 3)
    else:
        carimbar(g, ["B.B", ".B."], hx + 2, hy + 3)
    g[hy + 2][hx] = g[hy + 2][hx + 6] = "P"


def _cova(g, cx, y, meia):
    """Boca da cova: buraco escuro com a borda de terra na frente (por cima do corpo que afunda)."""
    px = {}
    for x in range(cx - meia, cx + meia + 1):
        for yy in range(y, N - 1):
            px[(x, yy)] = "e" if yy < y + 1 else "E"
    contornar(g, px)


def _monte(g, cx, y):
    """Monte de terra da cova fechada."""
    px = {}
    for dy, meia in ((0, 5), (1, 8), (2, 10), (3, 11)):
        for x in range(cx - meia, cx + meia + 1):
            px[(x, y + dy)] = "e" if dy == 3 else "E"
    for x in range(cx - 7, cx + 8, 4):
        px[(x, y + 1)] = "e"
    contornar(g, px)


def quadro(cx=14, base=30, ch=9, lean=0, olhos="normal", pes=(0, 0), atras=(), bracos=(), pas=(), por=(),
           afunda=0, cova=None, monte=None):
    """Um quadro 32x32 e a âncora do acréscimo (cabeça - 12). `afunda` desce o corpo na cova `cova` (cx, y, meia);
    `monte` (cx, y) desenha só a cova fechada com a pá fincada e o boné pendurado nela; `pas`: (cabo, ponta)."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    if monte:
        mx, my = monte
        _pa(g, (mx + 6, my - 8), (mx + 6, my - 2))
        _monte(g, mx, my)
        _bone(g, mx + 6, my - 4)              # boné pendurado no cabo da pá
        for s, x, y in por:
            carimbar(g, s, x, y)
        return ["".join(l) for l in g], (mx - 6, my - 16)
    base += afunda
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 4
    casaco = set()
    for y in range(ctop, base - 1):
        t = (y - ctop) / max(ch - 1, 1)
        meia = 3.5 + t * 2.5
        c = cx + lean * (1 - t) * 0.6
        casaco |= {(x, y) for x in range(round(c - meia), round(c + meia) + 1)}
    cabeca = {(x, y) for x in range(hx - 5, hx + 6) for y in range(hy - 5, hy + 6)
              if (x - hx) ** 2 + (y - hy) ** 2 <= 22}
    px = {}
    for p in casaco:
        borda = (p[0] + 1, p[1]) not in casaco or (p[0], p[1] + 1) not in casaco
        px[p] = "c" if borda else "C"
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
    for p in cabeca:
        px[p] = "f" if (p[0], p[1] + 1) not in cabeca and p[1] > hy else "F"
    if not afunda:
        for x0 in (cx - 4 + pes[0], cx + 2 + pes[1]):
            for x in range(x0, x0 + 3):
                for y in (base - 2, base - 1):
                    px[(x, y)] = "k"
    contornar(g, px)
    _rosto(g, hx, hy, olhos)
    _bone(g, hx, hy)
    for a, b in bracos:
        traco(g, a, b, "C")
        carimbar(g, MAO, b[0] - 1, b[1] - 1)
    for cabo, ponta in pas:
        _pa(g, cabo, ponta)
        carimbar(g, MAO, cabo[0] + (1 if ponta[0] >= cabo[0] else -1) * 2 - 1, cabo[1] - 1 + (ponta[1] > cabo[1]) * 2)
    if cova:
        _cova(g, *cova)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (hx - 12, hy - 12)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, ch=9 -> ctop=20, cabeça hy=16; ombro ~(cx + 2, 22)
_SPECS = {
    # parado, apoiado na pá fincada no chão; a pá balança e ele pisca
    "idle": [dict(bracos=(((16, 22), (20, 21)),), pas=(((21, 18), (21, 25)),)),
             dict(bracos=(((16, 22), (20, 21)),), pas=(((21, 18), (22, 25)),)),
             dict(olhos="fechado", bracos=(((16, 22), (20, 21)),), pas=(((21, 18), (22, 25)),)),
             dict(bracos=(((16, 22), (20, 22)),), pas=(((21, 19), (21, 26)),), por=((TERRA_P, 26, 28),))],
    # corre de lado olhando para a frente, pá no ombro, botas alternando
    "run_r": [dict(cx=15, lean=1, pes=(-2, 2), bracos=(((15, 22), (18, 21)),), pas=(((19, 21), (8, 14)),)),
              dict(cx=15, lean=2, base=29, bracos=(((15, 21), (18, 20)),), pas=(((19, 20), (8, 12)),)),
              dict(cx=15, lean=1, pes=(2, -2), bracos=(((15, 22), (18, 21)),), pas=(((19, 21), (8, 15)),)),
              dict(cx=15, lean=2, base=29, bracos=(((15, 21), (18, 20)),), pas=(((19, 20), (8, 13)),))],
    # acena com a mão livre, pá fincada atrás
    "waving": [dict(olhos="feliz", pas=(((9, 18), (8, 25)),), bracos=(((16, 22), (21, 19)),)),
               dict(olhos="feliz", pas=(((9, 18), (8, 25)),), bracos=(((16, 22), (21, 15)),)),
               dict(olhos="feliz", pas=(((9, 18), (8, 25)),), bracos=(((16, 22), (24, 15)),)),
               dict(olhos="feliz", pas=(((9, 18), (8, 25)),), bracos=(((16, 22), (21, 15)),))],
    # agacha, salta com a pá erguida, cai, pousa
    "jumping": [dict(ch=7, olhos="fechado", bracos=(((16, 24), (20, 25)),), pas=(((21, 22), (22, 28)),)),
                dict(ch=10, base=28, bracos=(((16, 19), (21, 16)),), pas=(((22, 16), (25, 7)),)),
                dict(ch=9, base=26, olhos="feliz", bracos=(((16, 17), (21, 13)),), pas=(((22, 13), (25, 4)),)),
                dict(ch=10, base=28, bracos=(((16, 20), (21, 18)),), pas=(((22, 18), (25, 10)),)),
                dict(ch=7, olhos="feliz", bracos=(((16, 24), (20, 25)),), pas=(((21, 22), (23, 28)),))],
    # triste, solta a pá, escorrega para a própria cova, que se fecha; fica o boné no monte
    "failed": [dict(olhos="triste", pas=(((21, 22), (26, 28)),), por=((LAGRIMA, 20, 17),)),
               dict(olhos="triste", afunda=4, cova=(14, 28, 9), por=((LAGRIMA, 20, 21),)),
               dict(olhos="x", afunda=7, cova=(14, 28, 9)),
               dict(monte=(14, 26), por=((FUMACA, 9, 5),)),
               dict(monte=(14, 26), por=((FUMACA, 8, 2),))],
    # cochila apoiado na pá, cabeça pende, "z" subindo
    "waiting": [dict(ch=8, lean=-1, olhos="fechado", bracos=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),)),
                dict(ch=8, lean=-2, olhos="fechado", bracos=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),),
                     por=((Z_P, 23, 4),)),
                dict(ch=8, lean=-2, olhos="fechado", bracos=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),),
                     por=((Z_P, 22, 4), (Z_G, 26, 0))),
                dict(ch=8, lean=-1, olhos="fechado", bracos=(((15, 23), (19, 22)),), pas=(((20, 19), (21, 26)),),
                     por=((Z_G, 26, 0),))],
    # golpe: ergue a pá atrás da cabeça, desce num arco e bate no chão levantando terra
    "running": [dict(cx=13, lean=-2, olhos="bravo", bracos=(((13, 22), (10, 18)),), pas=(((10, 17), (5, 7)),)),
                dict(cx=14, lean=0, olhos="bravo", bracos=(((15, 21), (18, 15)),), pas=(((18, 14), (20, 4)),)),
                dict(cx=14, lean=2, olhos="bravo", bracos=(((16, 22), (21, 19)),), pas=(((21, 19), (28, 14)),),
                     por=((TERRA_P, 29, 9),)),
                dict(cx=14, lean=2, olhos="bravo", bracos=(((16, 23), (20, 23)),), pas=(((20, 22), (26, 27)),),
                     por=((TERRA, 27, 20), (TERRA_P, 23, 18), (TERRA_P, 30, 24)))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=12, olhos="cima", bracos=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),)),
               dict(cx=12, olhos="cima", bracos=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),),
                    por=((INTERROG_P, 24, 2),)),
               dict(cx=12, olhos="cima", bracos=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),),
                    por=((INTERROG, 24, 0),)),
               dict(cx=12, olhos="normal", bracos=(((14, 22), (17, 20)),), pas=(((7, 18), (6, 25)),),
                    por=((INTERROG, 24, 0),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# lampião pendurado num gancho, flutuando atrás (à esquerda); âncora = cabeça - 12
_VAZIO = "." * 25
LAMPIAO = [_VAZIO] * 12 + [
    "..KK.....................",
    ".K..K....................",
    "KKKKKK...................",
    "KYOOYK...................",
    "KYWYYK...................",
    "KOYYOK...................",
    "KKKKKK...................",
    ".KssK....................",
    "..KK.....................",
]
# chapéu alto de guardião com fita vinho, por cima do boné
GUARDIAO = LAMPIAO[:]
for _i, _lin in {
    0: "........KKKKKKK..........",
    1: "........KHHHHHK..........",
    2: "........KHHHHHK..........",
    3: "........KHHHHHK..........",
    4: "........KRRRRRK..........",
    5: "......KKKKKKKKKKK........",
    6: "......KHHHHHHHHHK........",
    7: "......KKKKKKKKKKK........",
}.items():
    GUARDIAO[_i] = _lin
ESTAGIOS = [
    {"title": "Ajudante de Coveiro", "floor": 1, "extra": None},
    {"title": "Coveiro", "floor": 4, "extra": LAMPIAO},
    {"title": "Guardião do Cemitério", "floor": 10, "extra": GUARDIAO},
]
