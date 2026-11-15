"""Espantalho, 32 px, olhando para a direita. Um espantalhinho de cabeça de saco de estopa (olhos de botão e boca
costurada), chapéu de palha de aba larga com fita vermelha, camisa azul cheia de remendos, calça marrom e tufos de
palha saindo do pescoço, das mangas, da barra e dos pés. Parado ele fica de braços abertos (a pose de espantalho);
o símbolo do `running` é a foice: arma no alto, golpeia e solta um corte em meia-lua com palha voando.
No `failed` ele desmonta em palha: a palha escapa das mangas, o chapéu voa e ele afunda num monte de palha.
O tronco e a cabeça andam juntos (só pernas e braços mudam), para o corvinho no ombro e a lanterna de abóbora dos
acréscimos ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#1a1410", "S": "#dcbc8c", "s": "#a9875a", "Y": "#f5d35e", "y": "#c3922c",
    "C": "#5b86d0", "c": "#3c5c9a", "R": "#d0473c", "G": "#6fb44c", "D": "#8a5a32", "d": "#5e3a20",
    "k": "#4a3628", "W": "#ffffff", "Q": "#d8e0e8", "q": "#8e9aa6", "O": "#f08a24", "o": "#b0541a",
    "L": "#ffe680", "A": "#ff9a3c", "T": "#8fd8ff", "V": "#6a5a86", "v": "#43385a",
}

SHIRT = (4, 4, 5, 5, 5, 6, 6, 6)              # meia-largura da camisa por linha (8 linhas)

SCYTHE = [                                       # cabo embaixo à esquerda, lâmina curva por cima e para a frente
    "..KKKKK..",
    ".KQQWWWK.",
    "KQKKKKKWK",
    "KQK...KWK",
    "KQK...KWK",
    "KDK....K.",
    "KDK......",
    "KDK......",
    ".K.......",
]


def _rotate(s):
    """Gira o sprite 90 graus no sentido horário."""
    return ["".join(s[len(s) - 1 - r][c] for r in range(len(s))) for c in range(len(s[0]))]


SCYTHE_FRONT = _rotate(SCYTHE)                   # cabo para trás, lâmina à frente apontando para baixo
CUT = [                                       # meia-lua do golpe
    "...KKKK.....",
    "..KWWWWKK...",
    "...KKKWWWK..",
    "......KKWWK.",
    ".......KKWWK",
    "........KWWK",
    "........KWWK",
    ".......KKWWK",
    "......KKWWK.",
    "...KKKWWWK..",
    "..KWWWWKK...",
    "...KKKK.....",
]
STRAW = ["KKK...", "KYYKK.", ".KKYYK", "...KKK"]   # fiapo de palha voando
STRAW_V = ["KK.", "KYK", "KYK", ".KK"]
STREAK = ["QQQ.", ".QQQ", "QQQ."]
MOUND = [                                       # monte de palha onde ele afunda
    "....KK.K..KK.K....",
    "..KKYYKYKKYYKYKK..",
    ".KYYyYYYYYYyYYYYK.",
    "KYyYYYyYYyYYYYyYYK",
    "KYYYyYYYYYYYyYYYYK",
    ".KKKKKKKKKKKKKKKK.",
]
HAT = [                                      # chapéu caído, de lado no chão
    "....KKKKK....",
    "...KYYYYYK...",
    "..KYYYYYYYK..",
    "..KRRRRRRRK..",
    "KKYYYYYYYYYKK",
    "KYYyYYYYYyYYK",
    ".KKKKKKKKKKK.",
]
HAT_FLYING = [                               # chapéu girando no ar
    "...KKKK...",
    "..KYYYYK..",
    ".KKRRRRKK.",
    "KYYYYYYYYK",
    ".KKyYYyKK.",
    "...KKKK...",
]
HAND = [".K.K.", "KYKYK", "KYYYK", "KYyYK", ".KKK."]   # mão de tufo de palha


def _arm(g, a, b, hand=True):
    """Manga de 2 px da camisa de `a` (ombro) a `b` (mão), com o tufo de palha na ponta."""
    px = {}
    for x, y in line(*a, *b):
        px[(x, y)] = px[(x, y + 1)] = "C"
    outline_cells(g, px)
    if hand:
        stamp(g, HAND, b[0] - 2, b[1] - 2)


def frame(cx=13, base=30, leg=3, seated=False, eye="n", feet=(0, 0), arms=(), scythe=None, por=(),
           hat=True):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 12 acima do topo da camisa).
    `perna`: altura das pernas (0 = agachado); `sentado`: afundado no chão, sem pernas;
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-4, t+1) e o da frente em (cx+4, t+1);
    `foice`: (sprite, x, y) desenhado por cima da mão; `chapeu`: False quando o chapéu caiu da cabeça."""
    g = [["."] * N for _ in range(N)]
    t = (base - len(SHIRT) + 1) if seated else (base - leg - len(SHIRT))
    hx, hy = cx + 1, t - 4
    px = {}
    if not seated:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + feet[i]
            for y in range(base - leg, base):
                px[(x, y)] = "D" if i else "d"
                px[(x + 1, y)] = "D" if i else "d"
            for x1 in range(x - 1, x + 3):          # pé de palha
                px[(x1, base)] = "Y" if x1 % 2 else "y"
    for r, w in enumerate(SHIRT):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "c" if x <= cx - w + 1 else "C"
    for x in range(cx - 5, cx + 7, 2):               # palha saindo da barra
        px[(x, t + len(SHIRT))] = "Y"
    for x in range(hx - 4, hx + 5):
        for y in range(hy - 4, hy + 5):
            if (x - hx) ** 2 + (y - hy) ** 2 <= 21:
                px[(x, y)] = "s" if x <= hx - 3 else "S"
    for x in (hx - 2, hx, hx + 2):                   # palha do pescoço
        px[(x, hy + 5)] = "Y"
    if hat:
        for x in range(hx - 7, hx + 7):              # aba
            px[(x, hy - 3)] = "Y"
        px[(hx - 8, hy - 2)] = px[(hx + 7, hy - 2)] = "y"
        for i, (a, b) in enumerate(((-4, 4), (-4, 3), (-3, 3), (-2, 2))):   # copa
            for x in range(hx + a, hx + b + 1):
                px[(x, hy - 4 - i)] = "R" if i == 0 else ("y" if x == hx + a else "Y")
    outline_cells(g, px)
    # remendos e cordinha da cintura
    stamp(g, ["RRR", "RkR", "RRR"], cx - 3, t + 2)
    stamp(g, ["GG", "GG"], cx + 3, t + 5)
    for x in range(cx - 5, cx + 6):
        if g[t + 4][x] in "Cc":
            g[t + 4][x] = "y"
    # rosto: olhos de botão e boca costurada
    eyes = {"n": (["KK", "KW"], ["KK", "KW"]), "fechado": (["..", "kk"], ["..", "kk"]),
             "feliz": ([".k", "k."], [".k", "k."]), "x": (["K.K", ".K.", "K.K"], ["K.K", ".K.", "K.K"]),
             "bravo": (["K.", "KK"], [".K", "KK"]), "cima": (["KW", "KK"], ["KW", "KK"]),
             "triste": (["KK", "K."], ["KK", ".K"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 1 - (len(back[0]) > 2), hy - 1 - (len(back) > 2))
    stamp(g, front, hx + 2, hy - 1 - (len(front) > 2))
    g[hy + 2][hx] = g[hy + 2][hx + 3] = "k"       # sorrisinho costurado
    g[hy + 3][hx + 1] = g[hy + 3][hx + 2] = "k"
    if eye == "triste":
        stamp(g, TEAR, hx - 1, hy + 1)
    for a, b in arms:
        _arm(g, a, b)
    if scythe:
        stamp(g, *scythe)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=3 -> camisa 19-26 (cx=13), cabeça 11-19 (hx=14), chapéu 7-12; ombros em (9, 20) e (17, 20)
_OPEN = (((9, 20), (3, 20)), ((17, 20), (25, 20)))     # braços abertos, a pose de espantalho
_FALLEN = (((9, 20), (7, 26)), ((17, 20), (19, 26)))      # braços pendurados
_SPECS = {
    # braços abertos; a palha das mãos balança, um fiapo cai e ele pisca
    "idle": [dict(arms=_OPEN),
             dict(arms=(((9, 20), (3, 21)), ((17, 20), (25, 19)))),
             dict(arms=_OPEN, por=((STRAW_V, 25, 23),)),
             dict(eye="fechado", arms=(((9, 20), (3, 19)), ((17, 20), (25, 21))), por=((STRAW_V, 26, 26),)),
             dict(arms=_OPEN)],
    # corre desengonçado: pernas alternando, braços balançando
    "run_r": [dict(feet=(-2, 2), arms=(((9, 20), (4, 23)), ((17, 20), (23, 17)))),
              dict(base=29, arms=(((9, 20), (5, 20)), ((17, 20), (23, 21)))),
              dict(feet=(2, -2), arms=(((9, 20), (4, 17)), ((17, 20), (22, 24)))),
              dict(base=29, arms=(((9, 20), (5, 20)), ((17, 20), (23, 21))))],
    # acena alto com a mão da frente, palha voando da mão
    "waving": [dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (24, 13)))),
               dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (21, 9)))),
               dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (26, 11))), por=((STRAW, 25, 3),)),
               dict(eye="feliz", arms=(((9, 20), (5, 24)), ((17, 20), (21, 9))))],
    # agacha, salta de braços para cima, desce, pousa
    "jumping": [dict(leg=0, eye="fechado", arms=(((9, 23), (4, 26)), ((17, 23), (22, 26)))),
                dict(base=28, eye="cima", arms=(((9, 18), (4, 13)), ((17, 18), (23, 13)))),
                dict(base=26, eye="feliz", arms=(((9, 16), (3, 10)), ((17, 16), (24, 10)))),
                dict(base=28, arms=(((9, 18), (3, 18)), ((17, 18), (24, 18)))),
                dict(leg=0, eye="feliz", arms=(((9, 23), (4, 26)), ((17, 23), (22, 26))))],
    # a palha escapa das mangas, o chapéu voa e ele afunda num monte de palha
    "failed": [dict(eye="triste", arms=_FALLEN, por=((STRAW_V, 5, 27), (STRAW_V, 20, 27))),
               dict(eye="x", hat=False, arms=(((9, 21), (5, 27)), ((17, 21), (21, 27))),
                    por=((HAT_FLYING, 18, 1), (STRAW, 1, 23), (STRAW, 23, 22))),
               dict(eye="x", seated=True, hat=False, arms=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MOUND, 5, 26), (HAT, 19, 3), (STRAW, 0, 14), (STRAW, 25, 13))),
               dict(eye="x", seated=True, hat=False, arms=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MOUND, 5, 26), (HAT, 19, 11), (STRAW_V, 2, 20))),
               dict(eye="x", seated=True, hat=False, arms=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MOUND, 5, 26), (HAT, 19, 25)))],
    # cochila de pé, braços pendurados, "z" subindo
    "waiting": [dict(eye="fechado", arms=_FALLEN),
                dict(eye="fechado", arms=_FALLEN, por=((Z_S, 23, 7),)),
                dict(eye="fechado", arms=_FALLEN, por=((Z_S, 22, 8), (Z_L, 25, 0))),
                dict(eye="fechado", arms=_FALLEN, por=((Z_L, 25, 0),))],
    # foice: arma no alto atrás da cabeça, golpeia para a frente, corte em meia-lua com palha voando
    "running": [dict(cx=11, eye="bravo", arms=(((7, 20), (3, 23)), ((15, 20), (19, 10))),
                     scythe=(SCYTHE, 18, 2)),
                dict(cx=11, eye="bravo", arms=(((7, 20), (3, 23)), ((15, 20), (22, 16))),
                     scythe=(_rotate(SCYTHE), 21, 10), por=((STREAK, 21, 4),)),
                dict(cx=11, eye="bravo", arms=(((7, 20), (3, 23)), ((15, 20), (21, 20))),
                     scythe=(SCYTHE_FRONT, 20, 19), por=((CUT, 20, 6), (STRAW, 25, 2))),
                dict(cx=11, eye="feliz", arms=(((7, 20), (3, 23)), ((15, 20), (20, 23))),
                     scythe=(SCYTHE_FRONT, 19, 22), por=((STRAW, 24, 8), (STRAW_V, 28, 14)))],
    # mão no queixo, "?" aparece
    "review": [dict(eye="cima", arms=(_FALLEN[0], ((17, 20), (20, 17)))),
               dict(eye="cima", arms=(_FALLEN[0], ((17, 20), (20, 17))), por=((QMARK_S, 24, 3),)),
               dict(eye="cima", arms=(_FALLEN[0], ((17, 20), (20, 17))), por=((QMARK, 24, 1),)),
               dict(eye="n", arms=(_FALLEN[0], ((17, 20), (20, 17))), por=((QMARK, 24, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 16x21 colada 8 à esquerda e 12 acima do topo da camisa (camisa a partir da linha 12, centro na coluna 8):
# corvinho sentado no ombro de trás (linhas 7-12) e lanterna de abóbora pendurada no quadril de trás
_CROW = [                                     # corvinho de penas escuras, bico laranja encostado na cabeça
    "..KK..",
    ".KVVK.",
    "KVVWKK",
    "KvVVKA",
    "KvvVVK",
    ".KKKK.",
]
_LANTERN = [
    "...K...",
    "..KGK..",
    ".KKKKK.",
    "KOLOLOK",
    "KOOOOOK",
    "KoLLLoK",
    ".KKKKK.",
]


def _extra(pieces, w=16, h=21):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CROW = _extra(((_CROW, 0, 7),))
CROW_LANTERN = _extra(((_CROW, 0, 7), (_LANTERN, 0, 14)))
STAGES = [
    {"title": "Espantalhinho", "floor": 1, "extra": None},
    {"title": "Espantalho", "floor": 4, "extra": CROW},
    {"title": "Guardião da Lavoura", "floor": 10, "extra": CROW_LANTERN},
]
