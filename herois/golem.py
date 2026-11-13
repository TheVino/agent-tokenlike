"""Golem de Musgo, 32 px, olhando para a direita. Um golenzinho atarracado de pedra cinza, cabeça de pedra
arredondada sobre o tronco largo, olhos de brilho amarelo-esverdeado, manchas de musgo no alto da cabeça e nos
ombros e uma florzinha cor-de-rosa brotando no topo. Braços grossos de pedra com punhos enormes. O símbolo do
`running` é o soco de pedra: puxa o punho para trás, soca para a frente e a pedra estoura em lascas.
No `failed` ele racha em pedrinhas: as rachaduras se espalham, o braço da frente cai e ele desmorona num monte
de pedras com a cabeça por cima.
O tronco e a cabeça andam juntos (só pernas e braços mudam), para a flor, o ninho e os cogumelos dos acréscimos
ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha

PAL = {
    "K": "#141a14", "P": "#a39e93", "p": "#6e6a62", "l": "#cfc9bc", "k": "#3e3b36",
    "G": "#6cbf44", "g": "#3f8a2c", "E": "#e8ff8a", "R": "#ff7aa8", "r": "#c94a7a", "Y": "#ffd23f",
    "M": "#d8483a", "m": "#9a2c24", "W": "#ffffff", "D": "#9a6a3a", "d": "#634020", "B": "#bfe8ff",
    "T": "#8fd8ff", "Q": "#d8e0e8",
}

TRONCO = (5, 6, 7, 7, 7, 7, 6, 5)              # meia-largura do tronco por linha (8 linhas)
CABECA = (3, 4, 5, 5, 5, 5, 4)                 # meia-largura da cabeça por linha (7 linhas, acima do tronco)

PUNHO = [                                       # punho de pedra 7x7
    ".KKKKK.",
    "KlPkPkK",
    "KPPkPkK",
    "KPPPPpK",
    "KPPPPpK",
    "KpPppkK",
    ".KKKKK.",
]
LASCAS = [                                      # o soco estoura: lascas de pedra e poeira
    "....K...K...",
    "...KlK.KPK..",
    "K..KPKKlK..K",
    "lK..KKKK..Kl",
    ".KK.KQQK.KK.",
    "..KKQWWQKK..",
    "KKPKQWWQKPKK",
    "..KKQQQQKK..",
    ".KK.KKKK.KK.",
    "pK.KPK.KlK.K",
    "K..KpK..KK..",
    "....K.......",
]
RISCO = ["QQQQ.", ".QQQQ", "QQQQ."]
PEDRINHA = [".KK.", "KPlK", "KppK", ".KK."]
PEDRINHA_P = ["KK", "Kp"]
FOLHA = [".KK", "KGK", "Kg."]
MONTE = [                                       # monte de pedras onde ele desmorona
    ".....KKK...KKKK.......",
    "...KKPlPK.KPPlPK.KKK..",
    "..KPPPPpKKPPPPpKKPlPK.",
    ".KPlPPpPKPPlPPPpKPPPpK",
    "KPPPpPPPKPPPPpPPKPpPPK",
    "KpPPPPpPPPPpPPPPPPPpPK",
    ".KKKKKKKKKKKKKKKKKKKK.",
]


def _braco(g, a, b, punho=True):
    """Braço de pedra de 3 px de `a` (ombro) a `b` (mão), com o punho enorme na ponta."""
    px = {}
    for x, y in linha(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1, 2):
                px[(x + dx, y + dy - 1)] = "p" if dy == 2 else "P"
    contornar(g, px)
    if punho:
        carimbar(g, PUNHO, b[0] - 3, b[1] - 3)


def quadro(cx=14, base=30, perna=3, sentado=False, olho="n", pes=(0, 0), bracos=(), por=(), racha=0, flor=True):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 14 acima do topo do tronco).
    `perna`: altura das pernas (0 = agachado); `sentado`: desmoronado no chão, sem pernas;
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-6, t+1) e o da frente em (cx+6, t+1);
    `racha`: 0 a 2, rachaduras na pedra; `flor`: False quando a florzinha caiu."""
    g = [["."] * N for _ in range(N)]
    t = (base - len(TRONCO) + 1) if sentado else (base - perna - len(TRONCO))
    hx, h0 = cx + 1, t - len(CABECA)
    px = {}
    if not sentado:
        for i, x0 in enumerate((cx - 5, cx + 2)):
            x = x0 + pes[i]
            for y in range(base - perna, base + 1):
                for x1 in range(x, x + 4):
                    px[(x1, y)] = "p" if i == 0 or x1 == x else "P"
    for r, w in enumerate(TRONCO):
        for x in range(cx - w, cx + w + 1):
            px[(x, t + r)] = "p" if x <= cx - w + 1 else "P"
    for r, w in enumerate(CABECA):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "p" if x <= hx - w + 1 else "P"
    for x, y in ((cx + 2, t + 3), (cx + 4, t + 5), (cx - 2, t + 6), (hx + 3, h0 + 5)):   # pintinhas claras
        px[(x, y)] = "l"
    for x in range(hx - 3, hx + 4):              # musgo no alto da cabeça
        px[(x, h0)] = "G"
        px[(x, h0 + 1)] = "G" if x % 3 else "g"
    for x in (hx - 5, hx + 5):
        px[(x, h0 + 2)] = "g"
    for x in list(range(cx - 5, cx - 1)) + list(range(cx + 3, cx + 6)):   # musgo nos ombros
        px[(x, t)] = "G"
        px[(x, t + 1)] = "g" if x % 2 else "G"
    if flor:                                      # florzinha no topo
        px[(hx + 1, h0 - 1)] = "g"
        for x, y in ((hx, h0 - 2), (hx + 2, h0 - 2), (hx + 1, h0 - 3)):
            px[(x, y)] = "R"
        px[(hx + 1, h0 - 2)] = "Y"
    contornar(g, px)
    # rosto: olhos de brilho num sulco escuro e a boca-rachadura
    ey = h0 + 3
    olhos = {"n": (["EE", "Ek"], ["EE", "Ek"]), "fechado": (["..", "kk"], ["..", "kk"]),
             "feliz": ([".E", "E."], [".E", "E."]), "x": (["k.k", ".k.", "k.k"], ["k.k", ".k.", "k.k"]),
             "bravo": (["E.", "EE"], [".E", "EE"]), "cima": (["Ek", "kk"], ["Ek", "kk"]),
             "triste": (["EE", "k."], ["EE", ".k"])}[olho]
    tras, frente = olhos
    carimbar(g, tras, hx - 2 - (len(tras[0]) > 2), ey - (len(tras) > 2))
    carimbar(g, frente, hx + 2, ey - (len(frente) > 2))
    for x in range(hx, hx + 3):
        g[h0 + 5][x] = "k"
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 2, ey + 2)
    if racha:                                     # rachaduras
        for x, y in ((cx - 1, t + 1), (cx, t + 2), (cx, t + 3), (cx + 1, t + 4), (cx + 1, t + 5), (cx + 2, t + 6)):
            g[y][x] = "K"
    if racha > 1:
        for x, y in ((hx - 1, h0 + 1), (hx - 1, h0 + 2), (hx - 2, h0 + 3), (cx - 4, t + 3), (cx - 3, t + 4),
                     (cx + 4, t + 2), (cx + 5, t + 3), (cx - 4, t + 5)):
            g[y][x] = "K"
    for a, b in bracos:
        _braco(g, a, b)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 14)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=3 -> tronco 19-26 (cx=14), cabeça 12-18 (hx=15), flor 9-11; ombros em (8, 20) e (20, 20)
_CAIDO = (((8, 20), (5, 26)), ((20, 20), (23, 26)))      # braços pendurados, punhos no chão de tão pesados
_SPECS = {
    # respira devagar, pisca, uma folhinha de musgo cai
    "idle": [dict(bracos=_CAIDO),
             dict(bracos=(((8, 20), (5, 25)), ((20, 20), (23, 25)))),
             dict(bracos=_CAIDO, por=((FOLHA, 26, 12),)),
             dict(olho="fechado", bracos=_CAIDO, por=((FOLHA, 27, 17),)),
             dict(bracos=(((8, 20), (5, 25)), ((20, 20), (23, 25))))],
    # anda pesado: pernas alternando, braços balançando
    "run_r": [dict(pes=(-2, 2), bracos=(((8, 20), (4, 25)), ((20, 20), (25, 23)))),
              dict(base=29, bracos=(((8, 20), (5, 26)), ((20, 20), (23, 26)))),
              dict(pes=(2, -2), bracos=(((8, 20), (6, 26)), ((20, 20), (22, 25)))),
              dict(base=29, bracos=(((8, 20), (5, 26)), ((20, 20), (23, 26))))],
    # acena alto com o punho da frente
    "waving": [dict(olho="feliz", bracos=(_CAIDO[0], ((20, 20), (26, 12)))),
               dict(olho="feliz", bracos=(_CAIDO[0], ((20, 20), (23, 9)))),
               dict(olho="feliz", bracos=(_CAIDO[0], ((20, 20), (27, 13))), por=((FOLHA, 28, 4),)),
               dict(olho="feliz", bracos=(_CAIDO[0], ((20, 20), (23, 9))))],
    # agacha, salta de punhos para cima, desce, pousa
    "jumping": [dict(perna=0, olho="fechado", bracos=(((8, 23), (5, 28)), ((20, 23), (23, 28)))),
                dict(base=28, olho="cima", bracos=(((8, 18), (4, 15)), ((20, 18), (25, 12)))),
                dict(base=26, olho="feliz", bracos=(((8, 16), (4, 12)), ((20, 16), (26, 9)))),
                dict(base=28, bracos=(((8, 18), (4, 19)), ((20, 18), (25, 18)))),
                dict(perna=0, olho="feliz", bracos=(((8, 23), (5, 28)), ((20, 23), (23, 28))))],
    # racha em pedrinhas: rachaduras, o braço da frente cai, desmorona num monte de pedras
    "failed": [dict(olho="triste", racha=1, bracos=_CAIDO, por=((PEDRINHA_P, 26, 22),)),
               dict(olho="x", racha=2, bracos=(_CAIDO[0],),
                    por=((PUNHO, 24, 25), (PEDRINHA, 26, 15), (PEDRINHA_P, 3, 17), (PEDRINHA_P, 22, 10))),
               dict(olho="x", racha=2, sentado=True, bracos=(((8, 24), (5, 28)),),
                    por=((MONTE, 5, 25), (PUNHO, 25, 25), (PEDRINHA, 1, 16), (PEDRINHA, 27, 13))),
               dict(olho="x", racha=2, sentado=True, flor=False, bracos=(((8, 24), (5, 28)),),
                    por=((MONTE, 5, 25), (PUNHO, 25, 25), (PEDRINHA_P, 1, 24), (PEDRINHA, 27, 20))),
               dict(olho="x", racha=2, sentado=True, flor=False, bracos=(((8, 24), (5, 28)),),
                    por=((MONTE, 5, 25), (PUNHO, 25, 25), (PEDRINHA, 27, 26)))],
    # cochila de pé, punhos no chão, "z" subindo
    "waiting": [dict(olho="fechado", bracos=_CAIDO),
                dict(olho="fechado", bracos=_CAIDO, por=((Z_P, 23, 6),)),
                dict(olho="fechado", bracos=_CAIDO, por=((Z_P, 22, 7), (Z_G, 25, 0))),
                dict(olho="fechado", bracos=_CAIDO, por=((Z_G, 25, 0),))],
    # soco de pedra: puxa o punho para trás, soca para a frente, a pedra estoura em lascas
    "running": [dict(cx=11, olho="bravo", bracos=(((5, 20), (3, 25)), ((17, 20), (20, 9)))),
                dict(cx=11, olho="bravo", bracos=(((5, 20), (3, 25)), ((17, 20), (24, 20))),
                     por=((RISCO, 19, 14), (RISCO, 18, 24))),
                dict(cx=11, olho="bravo", bracos=(((5, 20), (3, 25)), ((17, 20), (22, 20))),
                     por=((LASCAS, 20, 12), (PUNHO, 19, 17))),
                dict(cx=11, olho="feliz", bracos=(((5, 20), (3, 25)), ((17, 20), (22, 22))),
                     por=((PEDRINHA, 27, 12), (PEDRINHA_P, 29, 24), (PEDRINHA_P, 24, 9)))],
    # punho no queixo, "?" aparece
    "review": [dict(olho="cima", bracos=(_CAIDO[0], ((20, 20), (21, 18)))),
               dict(olho="cima", bracos=(_CAIDO[0], ((20, 20), (21, 18))), por=((INTERROG_P, 25, 3),)),
               dict(olho="cima", bracos=(_CAIDO[0], ((20, 20), (21, 18))), por=((INTERROG, 25, 1),)),
               dict(olho="n", bracos=(_CAIDO[0], ((20, 20), (21, 18))), por=((INTERROG, 25, 1),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# grade 18x14 colada 8 à esquerda e 14 acima do topo do tronco (cabeça a partir da linha 7, centro na coluna 9):
# flor grande brotando do topo; no Ancião, um ninho com ovinho atrás da flor e cogumelos na nuca
_FLOR = [                                      # flor grande de 5 pétalas com folha no caule
    "..KKK..",
    ".KRRRK.",
    "KRRYRRK",
    "KrRYRrK",
    ".KrRrK.",
    "KKKgKK.",
    "KGGgK..",
    ".KKgK..",
]
_NINHO = [
    "...KKK...",
    "..KBBWK..",
    "KKKBBBKKK",
    "KdDdDdDdK",
    ".KDdDdDK.",
    "..KKKKK..",
]
_COGUMELOS = [                                 # dois cogumelos vermelhos de pintinhas brancas
    ".KKK..",
    "KMWMK.",
    "KmMmKK",
    ".KQKMK",
    ".KQKmK",
    ".KKKQK",
    "...KKK",
]


def _extra(pecas, w=18, h=14):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


FLOR = _extra(((_FLOR, 8, 1),))
ANCIAO = _extra(((_NINHO, 1, 4), (_COGUMELOS, 0, 7), (_FLOR, 8, 1)))
ESTAGIOS = [
    {"title": "Pedrinha", "floor": 1, "extra": None},
    {"title": "Golem de Musgo", "floor": 4, "extra": FLOR},
    {"title": "Golem Ancião", "floor": 10, "extra": ANCIAO},
]
