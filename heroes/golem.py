"""Golem de Musgo, 32 px, olhando para a direita. Um golenzinho atarracado de pedra cinza, cabeça de pedra
arredondada sobre o tronco largo, olhos de brilho amarelo-esverdeado, manchas de musgo no alto da cabeça e nos
ombros e uma florzinha cor-de-rosa brotando no topo. Braços grossos de pedra com punhos enormes. O símbolo do
`running` é o soco de pedra: puxa o punho para trás, soca para a frente e a pedra estoura em lascas.
No `failed` ele racha em pedrinhas: as rachaduras se espalham, o braço da frente cai e ele desmorona num monte
de pedras com a cabeça por cima.
O tronco e a cabeça andam juntos (só pernas e braços mudam), para a flor, o ninho e os cogumelos dos acréscimos
ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#141a14", "P": "#a39e93", "p": "#6e6a62", "l": "#cfc9bc", "k": "#3e3b36",
    "G": "#6cbf44", "g": "#3f8a2c", "E": "#e8ff8a", "R": "#ff7aa8", "r": "#c94a7a", "Y": "#ffd23f",
    "M": "#d8483a", "m": "#9a2c24", "W": "#ffffff", "D": "#9a6a3a", "d": "#634020", "B": "#bfe8ff",
    "T": "#8fd8ff", "Q": "#d8e0e8",
}

TRUNK = (5, 6, 7, 7, 7, 7, 6, 5)              # meia-largura do tronco por linha (8 linhas)
HEAD = (3, 4, 5, 5, 5, 5, 4)                 # meia-largura da cabeça por linha (7 linhas, acima do tronco)

FIST = [                                       # punho de pedra 7x7
    ".KKKKK.",
    "KlPkPkK",
    "KPPkPkK",
    "KPPPPpK",
    "KPPPPpK",
    "KpPppkK",
    ".KKKKK.",
]
SPLINTERS = [                                      # o soco estoura: lascas de pedra e poeira
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
STREAK = ["QQQQ.", ".QQQQ", "QQQQ."]
PEBBLE = [".KK.", "KPlK", "KppK", ".KK."]
PEBBLE_S = ["KK", "Kp"]
LEAF = [".KK", "KGK", "Kg."]
MOUND = [                                       # monte de pedras onde ele desmorona
    ".....KKK...KKKK.......",
    "...KKPlPK.KPPlPK.KKK..",
    "..KPPPPpKKPPPPpKKPlPK.",
    ".KPlPPpPKPPlPPPpKPPPpK",
    "KPPPpPPPKPPPPpPPKPpPPK",
    "KpPPPPpPPPPpPPPPPPPpPK",
    ".KKKKKKKKKKKKKKKKKKKK.",
]


def _arm(g, a, b, fist=True):
    """Braço de pedra de 3 px de `a` (ombro) a `b` (mão), com o punho enorme na ponta."""
    px = {}
    for x, y in line(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1, 2):
                px[(x + dx, y + dy - 1)] = "p" if dy == 2 else "P"
    outline_cells(g, px)
    if fist:
        stamp(g, FIST, b[0] - 3, b[1] - 3)


def frame(cx=14, base=30, leg=3, seated=False, eye="n", feet=(0, 0), arms=(), por=(), crack=0, flor=True):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 14 acima do topo do tronco).
    `perna`: altura das pernas (0 = agachado); `sentado`: desmoronado no chão, sem pernas;
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-6, t+1) e o da frente em (cx+6, t+1);
    `racha`: 0 a 2, rachaduras na pedra; `flor`: False quando a florzinha caiu."""
    g = [["."] * N for _ in range(N)]
    t = (base - len(TRUNK) + 1) if seated else (base - leg - len(TRUNK))
    hx, h0 = cx + 1, t - len(HEAD)
    px = {}
    if not seated:
        for i, x0 in enumerate((cx - 5, cx + 2)):
            x = x0 + feet[i]
            for y in range(base - leg, base + 1):
                for x1 in range(x, x + 4):
                    px[(x1, y)] = "p" if i == 0 or x1 == x else "P"
    for r, w in enumerate(TRUNK):
        for x in range(cx - w, cx + w + 1):
            px[(x, t + r)] = "p" if x <= cx - w + 1 else "P"
    for r, w in enumerate(HEAD):
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
    outline_cells(g, px)
    # rosto: olhos de brilho num sulco escuro e a boca-rachadura
    ey = h0 + 3
    eyes = {"n": (["EE", "Ek"], ["EE", "Ek"]), "fechado": (["..", "kk"], ["..", "kk"]),
             "feliz": ([".E", "E."], [".E", "E."]), "x": (["k.k", ".k.", "k.k"], ["k.k", ".k.", "k.k"]),
             "bravo": (["E.", "EE"], [".E", "EE"]), "cima": (["Ek", "kk"], ["Ek", "kk"]),
             "triste": (["EE", "k."], ["EE", ".k"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 2 - (len(back[0]) > 2), ey - (len(back) > 2))
    stamp(g, front, hx + 2, ey - (len(front) > 2))
    for x in range(hx, hx + 3):
        g[h0 + 5][x] = "k"
    if eye == "triste":
        stamp(g, TEAR, hx - 2, ey + 2)
    if crack:                                     # rachaduras
        for x, y in ((cx - 1, t + 1), (cx, t + 2), (cx, t + 3), (cx + 1, t + 4), (cx + 1, t + 5), (cx + 2, t + 6)):
            g[y][x] = "K"
    if crack > 1:
        for x, y in ((hx - 1, h0 + 1), (hx - 1, h0 + 2), (hx - 2, h0 + 3), (cx - 4, t + 3), (cx - 3, t + 4),
                     (cx + 4, t + 2), (cx + 5, t + 3), (cx - 4, t + 5)):
            g[y][x] = "K"
    for a, b in arms:
        _arm(g, a, b)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 14)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=3 -> tronco 19-26 (cx=14), cabeça 12-18 (hx=15), flor 9-11; ombros em (8, 20) e (20, 20)
_FALLEN = (((8, 20), (5, 26)), ((20, 20), (23, 26)))      # braços pendurados, punhos no chão de tão pesados
_SPECS = {
    # respira devagar, pisca, uma folhinha de musgo cai
    "idle": [dict(arms=_FALLEN),
             dict(arms=(((8, 20), (5, 25)), ((20, 20), (23, 25)))),
             dict(arms=_FALLEN, por=((LEAF, 26, 12),)),
             dict(eye="fechado", arms=_FALLEN, por=((LEAF, 27, 17),)),
             dict(arms=(((8, 20), (5, 25)), ((20, 20), (23, 25))))],
    # anda pesado: pernas alternando, braços balançando
    "run_r": [dict(feet=(-2, 2), arms=(((8, 20), (4, 25)), ((20, 20), (25, 23)))),
              dict(base=29, arms=(((8, 20), (5, 26)), ((20, 20), (23, 26)))),
              dict(feet=(2, -2), arms=(((8, 20), (6, 26)), ((20, 20), (22, 25)))),
              dict(base=29, arms=(((8, 20), (5, 26)), ((20, 20), (23, 26))))],
    # acena alto com o punho da frente
    "waving": [dict(eye="feliz", arms=(_FALLEN[0], ((20, 20), (26, 12)))),
               dict(eye="feliz", arms=(_FALLEN[0], ((20, 20), (23, 9)))),
               dict(eye="feliz", arms=(_FALLEN[0], ((20, 20), (27, 13))), por=((LEAF, 28, 4),)),
               dict(eye="feliz", arms=(_FALLEN[0], ((20, 20), (23, 9))))],
    # agacha, salta de punhos para cima, desce, pousa
    "jumping": [dict(leg=0, eye="fechado", arms=(((8, 23), (5, 28)), ((20, 23), (23, 28)))),
                dict(base=28, eye="cima", arms=(((8, 18), (4, 15)), ((20, 18), (25, 12)))),
                dict(base=26, eye="feliz", arms=(((8, 16), (4, 12)), ((20, 16), (26, 9)))),
                dict(base=28, arms=(((8, 18), (4, 19)), ((20, 18), (25, 18)))),
                dict(leg=0, eye="feliz", arms=(((8, 23), (5, 28)), ((20, 23), (23, 28))))],
    # racha em pedrinhas: rachaduras, o braço da frente cai, desmorona num monte de pedras
    "failed": [dict(eye="triste", crack=1, arms=_FALLEN, por=((PEBBLE_S, 26, 22),)),
               dict(eye="x", crack=2, arms=(_FALLEN[0],),
                    por=((FIST, 24, 25), (PEBBLE, 26, 15), (PEBBLE_S, 3, 17), (PEBBLE_S, 22, 10))),
               dict(eye="x", crack=2, seated=True, arms=(((8, 24), (5, 28)),),
                    por=((MOUND, 5, 25), (FIST, 25, 25), (PEBBLE, 1, 16), (PEBBLE, 27, 13))),
               dict(eye="x", crack=2, seated=True, flor=False, arms=(((8, 24), (5, 28)),),
                    por=((MOUND, 5, 25), (FIST, 25, 25), (PEBBLE_S, 1, 24), (PEBBLE, 27, 20))),
               dict(eye="x", crack=2, seated=True, flor=False, arms=(((8, 24), (5, 28)),),
                    por=((MOUND, 5, 25), (FIST, 25, 25), (PEBBLE, 27, 26)))],
    # cochila de pé, punhos no chão, "z" subindo
    "waiting": [dict(eye="fechado", arms=_FALLEN),
                dict(eye="fechado", arms=_FALLEN, por=((Z_S, 23, 6),)),
                dict(eye="fechado", arms=_FALLEN, por=((Z_S, 22, 7), (Z_L, 25, 0))),
                dict(eye="fechado", arms=_FALLEN, por=((Z_L, 25, 0),))],
    # soco de pedra: puxa o punho para trás, soca para a frente, a pedra estoura em lascas
    "running": [dict(cx=11, eye="bravo", arms=(((5, 20), (3, 25)), ((17, 20), (20, 9)))),
                dict(cx=11, eye="bravo", arms=(((5, 20), (3, 25)), ((17, 20), (24, 20))),
                     por=((STREAK, 19, 14), (STREAK, 18, 24))),
                dict(cx=11, eye="bravo", arms=(((5, 20), (3, 25)), ((17, 20), (22, 20))),
                     por=((SPLINTERS, 20, 12), (FIST, 19, 17))),
                dict(cx=11, eye="feliz", arms=(((5, 20), (3, 25)), ((17, 20), (22, 22))),
                     por=((PEBBLE, 27, 12), (PEBBLE_S, 29, 24), (PEBBLE_S, 24, 9)))],
    # punho no queixo, "?" aparece
    "review": [dict(eye="cima", arms=(_FALLEN[0], ((20, 20), (21, 18)))),
               dict(eye="cima", arms=(_FALLEN[0], ((20, 20), (21, 18))), por=((QMARK_S, 25, 3),)),
               dict(eye="cima", arms=(_FALLEN[0], ((20, 20), (21, 18))), por=((QMARK, 25, 1),)),
               dict(eye="n", arms=(_FALLEN[0], ((20, 20), (21, 18))), por=((QMARK, 25, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 18x14 colada 8 à esquerda e 14 acima do topo do tronco (cabeça a partir da linha 7, centro na coluna 9):
# flor grande brotando do topo; no Ancião, um ninho com ovinho atrás da flor e cogumelos na nuca
_FLOWER = [                                      # flor grande de 5 pétalas com folha no caule
    "..KKK..",
    ".KRRRK.",
    "KRRYRRK",
    "KrRYRrK",
    ".KrRrK.",
    "KKKgKK.",
    "KGGgK..",
    ".KKgK..",
]
_NEST = [
    "...KKK...",
    "..KBBWK..",
    "KKKBBBKKK",
    "KdDdDdDdK",
    ".KDdDdDK.",
    "..KKKKK..",
]
_MUSHROOMS = [                                 # dois cogumelos vermelhos de pintinhas brancas
    ".KKK..",
    "KMWMK.",
    "KmMmKK",
    ".KQKMK",
    ".KQKmK",
    ".KKKQK",
    "...KKK",
]


def _extra(pieces, w=18, h=14):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


FLOWER = _extra(((_FLOWER, 8, 1),))
ELDER = _extra(((_NEST, 1, 4), (_MUSHROOMS, 0, 7), (_FLOWER, 8, 1)))
STAGES = [
    {"title": "Pedrinha", "floor": 1, "extra": None},
    {"title": "Golem de Musgo", "floor": 4, "extra": FLOWER},
    {"title": "Golem Ancião", "floor": 10, "extra": ELDER},
]
