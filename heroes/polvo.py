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
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line, trait

PAL = {
    "K": "#0b0812", "P": "#ee6282", "p": "#a83659", "H": "#ffb0c2", "S": "#ffe2c8", "W": "#f6f4fb",
    "B": "#a86e3c", "b": "#5e3b1c", "k": "#24160c", "g": "#56606c", "A": "#c9d3df", "a": "#7d8896",
    "O": "#c0652a", "T": "#8fd8ff", "t": "#3f8fc8", "Y": "#ffd23f",
}

MANTLE = (3, 5, 6, 7, 8, 8, 9, 9, 9, 9, 9, 8, 8, 7)     # meia-largura da cabeça (manto) por linha (14 linhas)

# tentáculos de baixo: pontos (dx a partir do centro, dy a partir do fim do manto, escala de 0 a 8)
SKIRTS = (
    (((-6, 0), (-7, 5), (-9, 8), (-11, 7)), ((-2, 0), (-3, 6), (-4, 8), (-6, 8)),
     ((2, 0), (2, 6), (3, 8), (5, 8)), ((6, 0), (7, 5), (9, 8), (11, 7))),           # parado
    (((-6, 0), (-8, 4), (-10, 8), (-12, 6)), ((-2, 0), (-2, 6), (-3, 8), (-5, 7)),
     ((2, 0), (3, 6), (4, 8), (6, 7)), ((6, 0), (6, 5), (8, 8), (10, 8))),            # mexendo
    (((-6, 0), (-10, 6), (-13, 8), (-14, 6)), ((-2, 0), (-4, 8), (-6, 8)),
     ((2, 0), (4, 8), (6, 8)), ((6, 0), (10, 6), (13, 8), (14, 6))),                  # espalhado (sono, agacha)
    (((-6, 0), (-6, 5), (-7, 8)), ((-2, 0), (-1, 5), (-2, 8)),
     ((2, 0), (1, 5), (2, 8)), ((6, 0), (6, 5), (7, 8))),                            # pendurado (no ar)
)

EYES = {"n": ["KKK", "KWK", "KKK", "KKK"], "cima": ["KWK", "KKK", "KKK", ".K."],
         "fechado": ["...", "...", "KKK", "..."], "feliz": ["...", ".K.", "K.K", "..."],
         "triste": ["...", "KKK", "KWK", "KKK"], "x": ["K.K", ".K.", "K.K", "..."],
         "bravo": (["K..", ".KK", "KWK", "KKK"], ["..K", "KK.", "KWK", "KKK"])}

BUBBLE = [".KK.", "KTWK", "KTTK", ".KK."]
BUBBLE_S = [".K.", "KWK", ".K."]
ICE = ["..K..", ".KTK.", "KTWTK", ".KTK.", "..K.."]


def _drawing(pts, larg, alt):
    """Sprite `larg` x `alt` com os pixels `pts` ({(x, y): cor}) e contorno escuro."""
    g = [["."] * N for _ in range(N)]
    outline_cells(g, pts)
    return ["".join(l[:larg]) for l in g[:alt]]


# respingo de água gelada do golpe (9x8): gotas subindo em leque sobre uma poça
SPLASH = _drawing({**{(x, 6): "T" for x in range(2, 7)}, **{(x, 5): "t" if x % 2 else "T" for x in range(3, 6)},
                     (4, 4): "W", (4, 3): "T", (1, 3): "T", (7, 3): "T", (2, 1): "W", (6, 1): "W", (4, 1): "T"},
                    9, 8)
# risco do chicote no ar (7x9)
BUZZ = _drawing({p: "W" for p in line(1, 1, 4, 2) + line(4, 2, 5, 5) + line(5, 5, 5, 7)}, 7, 9)


def _tent(px, pts, color="P"):
    """Tentáculo de 2 px pelos pontos `pts` (da base à ponta), afinando na ponta, com ventosas creme."""
    seg = []
    for p, q in zip(pts, pts[1:]):
        seg += line(*p, *q)[(1 if seg else 0):]
    n = len(seg)
    vent = []
    for i, (x, y) in enumerate(seg):
        d = (0,) if i >= n - 2 else (0, 1)
        for dx in d:
            for dy in d:
                px.setdefault((x + dx, y + dy), color)
        if 2 <= i < n - 2 and i % 3 == 2:
            vent.append((x + 1, y + 1))
    for v in vent:
        if v in px:
            px[v] = "S"


def _arm(g, pts):
    px = {}
    _tent(px, pts)
    outline_cells(g, px)


def _move(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def _bucket_floor(g, cx=16, top=17):
    """Balde de madeira de pé no chão: boca escura atrás (topo) e a frente com tábuas e aros de ferro."""
    mouth = {}
    for x in range(cx - 8, cx + 9):
        mouth[(x, top)] = "k"
    for x in range(cx - 9, cx + 10):
        mouth[(x, top + 1)] = "k"
    outline_cells(g, mouth)


def _bucket_front(g, cx=16, top=17):
    px = {}
    for r, y in enumerate(range(top + 2, 31)):
        w = 9 - r // 4
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "b" if (x - cx) % 3 == 0 else "B"
    for y in (top + 3, 28):
        for x in range(cx - 9, cx + 10):
            if (x, y) in px:
                px[(x, y)] = "g"
    for x, y in ((cx - 4, top + 3), (cx + 6, 28), (cx + 2, top + 6)):
        px[(x, y)] = "O"                            # ferrugem e uma mancha velha
    outline_cells(g, px)


def frame(cx=16, h0=8, base=30, eye="n", skirt=0, arms=(), por=(), bucket=False, back=()):
    """Um quadro 32x32 e a âncora do acréscimo (15 à esquerda do centro e 6 acima do topo do manto).
    `bracos`: listas de pontos dos tentáculos-braço escritas para a pose padrão (cx=16, h0=8: ombros em (8, 19)
    e (24, 19)) e deslocadas junto com o manto; `balde`: o polvo está dentro do balde (corta tudo abaixo da boca);
    `tras`: sprites carimbados antes do corpo; `por`: sprites carimbados por último, sem deslocar."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, h0 - 8
    for s, x, y in back:
        stamp(g, s, x, y)
    yb = h0 + 13
    px = {}
    if not bucket:
        esc = (base - yb - 1) / 8
        for t in SKIRTS[skirt]:
            _tent(px, [(cx + a, yb + round(b * esc)) for a, b in t])
    mantle = {}
    for r, w in enumerate(MANTLE):
        for x in range(cx - w, cx + w + 1):
            mantle[(x, h0 + r)] = "P"
    for (x, y) in mantle:
        if (x + 1, y) not in mantle or (x, y + 1) not in mantle and (x + 1, y + 1) not in mantle:
            mantle[(x, y)] = "p"
    for x, y in ((cx - 4, h0 + 1), (cx - 5, h0 + 2), (cx - 4, h0 + 2), (cx - 6, h0 + 3), (cx - 5, h0 + 3)):
        mantle[(x, y)] = "H"
    for x, y in ((cx + 2, h0 + 2), (cx + 4, h0 + 3), (cx + 5, h0 + 4), (cx + 1, h0 + 4)):
        mantle[(x, y)] = "p"                         # pintinhas
    px.update(mantle)
    if bucket:
        _bucket_floor(g)
        px = {p: c for p, c in px.items() if p[1] <= 18}
    outline_cells(g, px)
    tr, fr = EYES[eye] if isinstance(EYES[eye], tuple) else (EYES[eye], EYES[eye])
    stamp(g, tr, cx - 5, h0 + 6)
    stamp(g, fr, cx + 3, h0 + 6)
    if eye == "triste":
        stamp(g, TEAR, cx - 5, h0 + 10)
    for x, y in ((cx - 1, h0 + 10), (cx + 1, h0 + 10), (cx, h0 + 11)):
        if y <= (18 if bucket else 31):
            g[y][x] = "K"                           # boquinha
    if bucket:
        _bucket_front(g)
    for b in arms:
        _arm(g, b if bucket else _move(b, dx, dy))
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 15, h0 - 6)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# pose padrão: manto 8-21 (cx=16), olhos 14-17, ombros dos tentáculos-braço em (8, 19) e (24, 19)
_E = [(8, 19), (5, 22), (4, 25), (6, 26)]            # braço esquerdo enrolado no chão
_D = [(24, 19), (27, 22), (28, 25), (26, 26)]        # braço direito enrolado no chão
_E2 = [(8, 19), (5, 21), (3, 24), (4, 26)]
_D2 = [(24, 19), (27, 21), (29, 24), (28, 26)]
_SPECS = {
    # parado: respira (o manto desce 1 px), os tentáculos mexem, pisca, solta uma bolha
    "idle": [dict(arms=(_E, _D)),
             dict(h0=9, skirt=1, arms=(_E2, _D2), por=((BUBBLE_S, 26, 11),)),
             dict(h0=9, skirt=1, arms=(_E2, _D2), por=((BUBBLE, 26, 7),)),
             dict(eye="fechado", arms=(_E, _D), por=((BUBBLE, 27, 3),)),
             dict(arms=(_E, _D))],
    # anda: o manto sobe e desce, os tentáculos alternam
    "run_r": [dict(cx=16, h0=8, skirt=0, arms=([(8, 19), (4, 21), (2, 23)], [(24, 19), (28, 21), (30, 24)])),
              dict(cx=16, h0=7, skirt=1, base=29, arms=([(8, 19), (5, 23), (5, 26)], [(24, 19), (27, 23), (26, 26)])),
              dict(cx=16, h0=8, skirt=2, arms=([(8, 19), (4, 22), (3, 25)], [(24, 19), (29, 20), (30, 22)])),
              dict(cx=16, h0=7, skirt=1, base=29, arms=([(8, 19), (6, 23), (6, 26)], [(24, 19), (27, 23), (28, 26)]))],
    # acena bem alto com o tentáculo da direita, feliz
    "waving": [dict(eye="feliz", arms=(_E, [(24, 19), (27, 14), (28, 9), (26, 7)])),
               dict(eye="feliz", skirt=1, arms=(_E, [(24, 19), (29, 15), (31, 10), (30, 8)])),
               dict(eye="feliz", arms=(_E, [(24, 19), (27, 14), (28, 9), (26, 7)])),
               dict(eye="feliz", skirt=1, arms=(_E, [(24, 19), (29, 15), (31, 10), (30, 8)]))],
    # agacha, pula com o tentáculo para cima, desce, pousa
    "jumping": [dict(h0=11, skirt=2, eye="fechado", arms=(_E2, _D2)),
                dict(h0=7, base=27, skirt=3, eye="cima", arms=([(8, 19), (4, 21), (2, 24)],
                                                                [(24, 19), (27, 13), (28, 8), (26, 6)])),
                dict(h0=7, base=27, skirt=3, eye="feliz", arms=([(8, 19), (3, 20), (1, 22)],
                                                                 [(24, 19), (28, 13), (30, 8), (29, 6)]),
                     por=((BUBBLE_S, 3, 28), (BUBBLE_S, 27, 27))),
                dict(h0=8, skirt=1, arms=([(8, 19), (4, 21), (3, 24)], [(24, 19), (28, 21), (29, 24)])),
                dict(h0=10, skirt=2, eye="feliz", arms=(_E2, _D2))],
    # volta para dentro do balde: fica triste, entra, afunda e só sobra um tentáculo pendurado na borda
    "failed": [dict(eye="triste", skirt=3, arms=([(8, 19), (7, 23), (7, 27)], [(24, 19), (25, 23), (25, 27)])),
               dict(h0=8, eye="triste", bucket=True,
                    arms=([(9, 17), (6, 19), (5, 22)], [(23, 17), (26, 19), (27, 22)])),
               dict(h0=11, eye="triste", bucket=True,
                    arms=([(10, 18), (6, 19), (5, 22)], [(22, 18), (26, 16), (28, 12), (27, 10)])),
               dict(h0=14, eye="fechado", bucket=True,
                    arms=([(22, 18), (26, 18), (28, 21), (27, 24)],)),
               dict(h0=16, eye="fechado", bucket=True,
                    arms=([(22, 18), (26, 18), (27, 21), (26, 24)],))],
    # cochila esparramado, olhos fechados, "z" subindo
    "waiting": [dict(h0=10, skirt=2, eye="fechado", arms=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)])),
                dict(h0=10, skirt=2, eye="fechado", arms=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)]),
                     por=((Z_S, 26, 6),)),
                dict(h0=11, skirt=2, eye="fechado", arms=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)]),
                     por=((Z_S, 25, 7), (Z_L, 26, 0))),
                dict(h0=10, skirt=2, eye="fechado", arms=([(8, 19), (4, 23), (2, 26)], [(24, 19), (28, 23), (30, 26)]),
                     por=((Z_L, 26, 0),))],
    # chicotada: arma o tentáculo atrás da cabeça, chicoteia para a frente, estoura em água gelada, recolhe
    "running": [dict(eye="bravo", skirt=1, arms=(_E, [(24, 19), (28, 15), (29, 10), (27, 7), (25, 8)])),
                dict(eye="bravo", skirt=0, arms=(_E, [(24, 19), (28, 16), (31, 12)]),
                     por=((BUZZ, 25, 1),)),
                dict(eye="bravo", skirt=2, arms=(_E, [(24, 19), (28, 17), (31, 16)]),
                     por=((SPLASH, 24, 8), (ICE, 27, 1))),
                dict(eye="feliz", skirt=1, arms=(_E, [(24, 19), (28, 22), (28, 26), (26, 27)]),
                     por=((BUBBLE_S, 28, 14), (BUBBLE_S, 25, 11)))],
    # tentáculo no queixo, olhando para cima, "?" aparece
    "review": [dict(eye="cima", arms=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)])),
               dict(eye="cima", skirt=1, arms=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)]),
                    por=((QMARK_S, 26, 1),)),
               dict(eye="cima", arms=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)]), por=((QMARK, 26, 0),)),
               dict(eye="n", skirt=1, arms=(_E, [(24, 19), (27, 17), (26, 14), (23, 15)]),
                    por=((QMARK, 26, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)


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
    outline_cells(g, px)
    return ["".join(l[:25]) for l in g[:18]]


BUCKET = _extra(False)
ANCHOR_EXTRA = _extra(True)
STAGES = [
    {"title": "Polvinho", "floor": 1, "extra": None},
    {"title": "Polvo do Poço", "floor": 4, "extra": BUCKET},
    {"title": "Senhor do Poço", "floor": 10, "extra": ANCHOR_EXTRA},
]
