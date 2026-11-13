"""Polvo do Poço, 32 px, olhando para a frente. Um polvinho coral de cabeça (manto) grande e redonda, com brilho
no alto, pintinhas mais escuras, olhões pretos com brilho e quatro tentáculos curtos enrolando na ponta embaixo.
Os dois tentáculos de cima (um de cada lado) são os "braços" e fazem os gestos; têm ventosas creme.
Mora num poço e o seu objeto é um balde velho de madeira com aros de ferro.
O símbolo do `running` é a chicotada de tentáculo: arma o tentáculo atrás da cabeça, chicoteia para a frente e o
golpe estoura em respingos de água gelada. No `failed` ele volta para dentro do balde: fica triste, entra no balde,
afunda até sobrar só o alto da cabeça e um tentáculo pendurado na borda.
Os gestos são sempre do tentáculo da direita; a âncora do 3º estágio fica pendurada do lado esquerdo.
O manto anda inteiro (só tentáculos mudam), para o balde e a corrente dos acréscimos ficarem sempre no lugar.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha, traco

PAL = {
    "K": "#0b0812", "P": "#ee6282", "p": "#a83659", "H": "#ffb0c2", "S": "#ffe2c8", "W": "#f6f4fb",
    "B": "#a86e3c", "b": "#5e3b1c", "k": "#24160c", "g": "#56606c", "A": "#c9d3df", "a": "#7d8896",
    "O": "#c0652a", "T": "#8fd8ff", "t": "#3f8fc8", "Y": "#ffd23f",
}

MANTO = (3, 5, 6, 7, 8, 8, 9, 9, 9, 9, 9, 8, 8, 7)     # meia-largura da cabeça (manto) por linha (14 linhas)

# tentáculos de baixo: pontos (dx a partir do centro, dy a partir do fim do manto, escala de 0 a 8)
SAIAS = (
    (((-6, 0), (-7, 5), (-9, 8), (-11, 7)), ((-2, 0), (-3, 6), (-4, 8), (-6, 8)),
     ((2, 0), (2, 6), (3, 8), (5, 8)), ((6, 0), (7, 5), (9, 8), (11, 7))),           # parado
    (((-6, 0), (-8, 4), (-10, 8), (-12, 6)), ((-2, 0), (-2, 6), (-3, 8), (-5, 7)),
     ((2, 0), (3, 6), (4, 8), (6, 7)), ((6, 0), (6, 5), (8, 8), (10, 8))),            # mexendo
    (((-6, 0), (-10, 6), (-13, 8), (-14, 6)), ((-2, 0), (-4, 8), (-6, 8)),
     ((2, 0), (4, 8), (6, 8)), ((6, 0), (10, 6), (13, 8), (14, 6))),                  # espalhado (sono, agacha)
    (((-6, 0), (-6, 5), (-7, 8)), ((-2, 0), (-1, 5), (-2, 8)),
     ((2, 0), (1, 5), (2, 8)), ((6, 0), (6, 5), (7, 8))),                            # pendurado (no ar)
)

OLHOS = {"n": ["KKK", "KWK", "KKK", "KKK"], "cima": ["KWK", "KKK", "KKK", ".K."],
         "fechado": ["...", "...", "KKK", "..."], "feliz": ["...", ".K.", "K.K", "..."],
         "triste": ["...", "KKK", "KWK", "KKK"], "x": ["K.K", ".K.", "K.K", "..."],
         "bravo": (["K..", ".KK", "KWK", "KKK"], ["..K", "KK.", "KWK", "KKK"])}

BOLHA = [".KK.", "KTWK", "KTTK", ".KK."]
BOLHA_P = [".K.", "KWK", ".K."]
GELO = ["..K..", ".KTK.", "KTWTK", ".KTK.", "..K.."]


def _desenho(pts, larg, alt):
    """Sprite `larg` x `alt` com os pixels `pts` ({(x, y): cor}) e contorno escuro."""
    g = [["."] * N for _ in range(N)]
    contornar(g, pts)
    return ["".join(l[:larg]) for l in g[:alt]]


# respingo de água gelada do golpe (9x8): gotas subindo em leque sobre uma poça
RESPINGO = _desenho({**{(x, 6): "T" for x in range(2, 7)}, **{(x, 5): "t" if x % 2 else "T" for x in range(3, 6)},
                     (4, 4): "W", (4, 3): "T", (1, 3): "T", (7, 3): "T", (2, 1): "W", (6, 1): "W", (4, 1): "T"},
                    9, 8)
# risco do chicote no ar (7x9)
ZUNIDO = _desenho({p: "W" for p in linha(1, 1, 4, 2) + linha(4, 2, 5, 5) + linha(5, 5, 5, 7)}, 7, 9)


def _tent(px, pts, cor="P"):
    """Tentáculo de 2 px pelos pontos `pts` (da base à ponta), afinando na ponta, com ventosas creme."""
    seg = []
    for p, q in zip(pts, pts[1:]):
        seg += linha(*p, *q)[(1 if seg else 0):]
    n = len(seg)
    vent = []
    for i, (x, y) in enumerate(seg):
        d = (0,) if i >= n - 2 else (0, 1)
        for dx in d:
            for dy in d:
                px.setdefault((x + dx, y + dy), cor)
        if 2 <= i < n - 2 and i % 3 == 2:
            vent.append((x + 1, y + 1))
    for v in vent:
        if v in px:
            px[v] = "S"


def _braco(g, pts):
    px = {}
    _tent(px, pts)
    contornar(g, px)


def _mover(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def _balde_chao(g, cx=16, topo=17):
    """Balde de madeira de pé no chão: boca escura atrás (topo) e a frente com tábuas e aros de ferro."""
    boca = {}
    for x in range(cx - 8, cx + 9):
        boca[(x, topo)] = "k"
    for x in range(cx - 9, cx + 10):
        boca[(x, topo + 1)] = "k"
    contornar(g, boca)


def _balde_frente(g, cx=16, topo=17):
    px = {}
    for r, y in enumerate(range(topo + 2, 31)):
        w = 9 - r // 4
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "b" if (x - cx) % 3 == 0 else "B"
    for y in (topo + 3, 28):
        for x in range(cx - 9, cx + 10):
            if (x, y) in px:
                px[(x, y)] = "g"
    for x, y in ((cx - 4, topo + 3), (cx + 6, 28), (cx + 2, topo + 6)):
        px[(x, y)] = "O"                            # ferrugem e uma mancha velha
    contornar(g, px)


def quadro(cx=16, h0=8, base=30, olho="n", saia=0, bracos=(), por=(), balde=False, tras=()):
    """Um quadro 32x32 e a âncora do acréscimo (15 à esquerda do centro e 6 acima do topo do manto).
    `bracos`: listas de pontos dos tentáculos-braço escritas para a pose padrão (cx=16, h0=8: ombros em (8, 19)
    e (24, 19)) e deslocadas junto com o manto; `balde`: o polvo está dentro do balde (corta tudo abaixo da boca);
    `tras`: sprites carimbados antes do corpo; `por`: sprites carimbados por último, sem deslocar."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, h0 - 8
    for s, x, y in tras:
        carimbar(g, s, x, y)
    yb = h0 + 13
    px = {}
    if not balde:
        esc = (base - yb - 1) / 8
        for t in SAIAS[saia]:
            _tent(px, [(cx + a, yb + round(b * esc)) for a, b in t])
    manto = {}
    for r, w in enumerate(MANTO):
        for x in range(cx - w, cx + w + 1):
            manto[(x, h0 + r)] = "P"
    for (x, y) in manto:
        if (x + 1, y) not in manto or (x, y + 1) not in manto and (x + 1, y + 1) not in manto:
            manto[(x, y)] = "p"
    for x, y in ((cx - 4, h0 + 1), (cx - 5, h0 + 2), (cx - 4, h0 + 2), (cx - 6, h0 + 3), (cx - 5, h0 + 3)):
        manto[(x, y)] = "H"
    for x, y in ((cx + 2, h0 + 2), (cx + 4, h0 + 3), (cx + 5, h0 + 4), (cx + 1, h0 + 4)):
        manto[(x, y)] = "p"                         # pintinhas
    px.update(manto)
    if balde:
        _balde_chao(g)
        px = {p: c for p, c in px.items() if p[1] <= 18}
    contornar(g, px)
    tr, fr = OLHOS[olho] if isinstance(OLHOS[olho], tuple) else (OLHOS[olho], OLHOS[olho])
    carimbar(g, tr, cx - 5, h0 + 6)
    carimbar(g, fr, cx + 3, h0 + 6)
    if olho == "triste":
        carimbar(g, LAGRIMA, cx - 5, h0 + 10)
    for x, y in ((cx - 1, h0 + 10), (cx + 1, h0 + 10), (cx, h0 + 11)):
        if y <= (18 if balde else 31):
            g[y][x] = "K"                           # boquinha
    if balde:
        _balde_frente(g)
    for b in bracos:
        _braco(g, b if balde else _mover(b, dx, dy))
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 15, h0 - 6)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# pose padrão: manto 8-21 (cx=16), olhos 14-17, ombros dos tentáculos-braço em (8, 19) e (24, 19)
_E = [(8, 19), (5, 22), (4, 25), (6, 26)]            # braço esquerdo enrolado no chão
_D = [(24, 19), (27, 22), (28, 25), (26, 26)]        # braço direito enrolado no chão
_E2 = [(8, 19), (5, 21), (3, 24), (4, 26)]
_D2 = [(24, 19), (27, 21), (29, 24), (28, 26)]
_SPECS = {
    # parado: respira (o manto desce 1 px), os tentáculos mexem, pisca, solta uma bolha
    "idle": [dict(bracos=(_E, _D)),
             dict(h0=9, saia=1, bracos=(_E2, _D2), por=((BOLHA_P, 26, 11),)),
             dict(h0=9, saia=1, bracos=(_E2, _D2), por=((BOLHA, 26, 7),)),
             dict(olho="fechado", bracos=(_E, _D), por=((BOLHA, 27, 3),)),
             dict(bracos=(_E, _D))],
    # anda: o manto sobe e desce, os tentáculos alternam
    "run_r": [dict(cx=16, h0=8, saia=0, bracos=([(8, 19), (4, 21), (2, 23)], [(24, 19), (28, 21), (30, 24)])),
              dict(cx=16, h0=7, saia=1, base=29, bracos=([(8, 19), (5, 23), (5, 26)], [(24, 19), (27, 23), (26, 26)])),
              dict(cx=16, h0=8, saia=2, bracos=([(8, 19), (4, 22), (3, 25)], [(24, 19), (29, 20), (30, 22)])),
              dict(cx=16, h0=7, saia=1, base=29, bracos=([(8, 19), (6, 23), (6, 26)], [(24, 19), (27, 23), (28, 26)]))],
    # acena bem alto com o tentáculo da direita, feliz
    "waving": [dict(olho="feliz", bracos=(_E, [(24, 19), (27, 14), (28, 9), (26, 7)])),
               dict(olho="feliz", saia=1, bracos=(_E, [(24, 19), (29, 15), (31, 10), (30, 8)])),
               dict(olho="feliz", bracos=(_E, [(24, 19), (27, 14), (28, 9), (26, 7)])),
               dict(olho="feliz", saia=1, bracos=(_E, [(24, 19), (29, 15), (31, 10), (30, 8)]))],
    # agacha, pula com o tentáculo para cima, desce, pousa
    "jumping": [dict(h0=11, saia=2, olho="fechado", bracos=(_E2, _D2)),
                dict(h0=7, base=27, saia=3, olho="cima", bracos=([(8, 19), (4, 21), (2, 24)],
                                                                [(24, 19), (27, 13), (28, 8), (26, 6)])),
                dict(h0=7, base=27, saia=3, olho="feliz", bracos=([(8, 19), (3, 20), (1, 22)],
                                                                 [(24, 19), (28, 13), (30, 8), (29, 6)]),
                     por=((BOLHA_P, 3, 28), (BOLHA_P, 27, 27))),
                dict(h0=8, saia=1, bracos=([(8, 19), (4, 21), (3, 24)], [(24, 19), (28, 21), (29, 24)])),
                dict(h0=10, saia=2, olho="feliz", bracos=(_E2, _D2))],
    # volta para dentro do balde: fica triste, entra, afunda e só sobra um tentáculo pendurado na borda
    "failed": [dict(olho="triste", saia=3, bracos=([(8, 19), (7, 23), (7, 27)], [(24, 19), (25, 23), (25, 27)])),
               dict(h0=8, olho="triste", balde=True,
                    bracos=([(9, 17), (6, 19), (5, 22)], [(23, 17), (26, 19), (27, 22)])),
               dict(h0=11, olho="triste", balde=True,
                    bracos=([(10, 18), (6, 19), (5, 22)], [(22, 18), (26, 16), (28, 12), (27, 10)])),
               dict(h0=14, olho="fechado", balde=True,
                    bracos=([(22, 18), (26, 18), (28, 21), (27, 24)],)),
               dict(h0=16, olho="fechado", balde=True,
                    bracos=([(22, 18), (26, 18), (27, 21), (26, 24)],))],
    # cochila esparramado, olhos fechados, "z" subindo
    "waiting": [dict(h0=10, saia=2, olho="fechado", bracos=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)])),
                dict(h0=10, saia=2, olho="fechado", bracos=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)]),
                     por=((Z_P, 26, 6),)),
                dict(h0=11, saia=2, olho="fechado", bracos=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)]),
                     por=((Z_P, 25, 7), (Z_G, 26, 0))),
                dict(h0=10, saia=2, olho="fechado", bracos=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)]),
                     por=((Z_G, 26, 0),))],
    # chicotada: arma o tentáculo atrás da cabeça, chicoteia para a frente, estoura em água gelada, recolhe
    "running": [dict(olho="bravo", saia=1, bracos=(_E, [(24, 19), (28, 15), (29, 10), (27, 7), (25, 8)])),
                dict(olho="bravo", saia=0, bracos=(_E, [(24, 19), (28, 16), (31, 12)]),
                     por=((ZUNIDO, 25, 1),)),
                dict(olho="bravo", saia=2, bracos=(_E, [(24, 19), (28, 17), (31, 16)]),
                     por=((RESPINGO, 24, 8), (GELO, 27, 1))),
                dict(olho="feliz", saia=1, bracos=(_E, [(24, 19), (28, 22), (28, 26), (26, 27)]),
                     por=((BOLHA_P, 28, 14), (BOLHA_P, 25, 11)))],
    # tentáculo no queixo, olhando para cima, "?" aparece
    "review": [dict(olho="cima", bracos=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)])),
               dict(olho="cima", saia=1, bracos=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)]),
                    por=((INTERROG_P, 26, 1),)),
               dict(olho="cima", bracos=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)]), por=((INTERROG, 26, 0),)),
               dict(olho="n", saia=1, bracos=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)]),
                    por=((INTERROG, 26, 0),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)


# grade 25x17 colada 15 à esquerda do centro e 6 acima do topo do manto (centro na coluna 15, topo do manto na
# linha 6): balde velho de cabeça para baixo como chapéu; no 3º estágio, uma corrente enrolada no balde e uma
# ancorazinha pendurada do lado esquerdo (longe do tentáculo que gesticula)
def _extra(ancora):
    g = [["."] * N for _ in range(N)]
    px = {}
    for r, w in enumerate((4, 5, 5, 6, 6, 7, 8)):
        y = 1 + r
        for x in range(15 - w, 16 + w):
            px[(x, y)] = "b" if (x - 15) % 3 == 0 else "B"
    for y in (2, 7):
        for x in range(7, 24):
            if (x, y) in px:
                px[(x, y)] = "g"
    for x, y in ((13, 2), (20, 7), (17, 5)):
        px[(x, y)] = "O"
    if ancora:
        for i, x in enumerate(range(10, 22)):       # corrente enrolada no balde
            px[(x, 4 + (x - 10) // 6)] = "A" if i % 2 else "a"
        for i, (x, y) in enumerate(((9, 6), (8, 7), (7, 8), (6, 9))):
            px[(x, y)] = "A" if i % 2 else "a"
        for y, lin in enumerate(("..AAA..", "..A.A..", "..AAA..", "AAAAAAA", "...A...", "A..A..A", "AA.A.AA",
                                 ".AAAAA.")):
            for x, ch in enumerate(lin):
                if ch == "A":
                    px[(1 + x, 10 + y)] = "a" if y >= 6 and x >= 3 else "A"
    contornar(g, px)
    return ["".join(l[:25]) for l in g[:18]]


BALDE = _extra(False)
ANCORA_EXTRA = _extra(True)
ESTAGIOS = [
    {"title": "Polvinho", "floor": 1, "extra": None},
    {"title": "Polvo do Poço", "floor": 4, "extra": BALDE},
    {"title": "Senhor do Poço", "floor": 10, "extra": ANCORA_EXTRA},
]
