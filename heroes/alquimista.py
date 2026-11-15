"""Alquimista, 32 px, olhando para a direita. Uma aprendiz de túnica verde-azulada com chapéu de couro de aba larga,
cabelo cor de cobre e um monóculo dourado de corrente no olho da frente. O símbolo é o frasco de vidro com
líquido verde: borbulha no idle, vira granada no `running` (arremesso e estouro verde). No `failed` o frasco racha
na mão, solta fumaça e ela senta no chão tonta, com cacos e uma poça verde ao lado.
O tronco, a cabeça e o chapéu andam juntos (só pernas e braços mudam), para o cinto e os óculos do acréscimo
ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#1a1422", "R": "#3f9a84", "r": "#2a6658", "E": "#9fe8c8", "F": "#f6d7c3", "f": "#d8a98e",
    "O": "#e0782e", "o": "#a8501e", "D": "#9a6236", "d": "#5e3a20", "B": "#c8334a",
    "G": "#ffd23f", "g": "#b8860b", "L": "#bfe8ff", "W": "#ffffff", "S": "#d8e6f0",
    "V": "#a6f06b", "v": "#4c9a3a", "P": "#ff6fae", "A": "#ffa94d", "Q": "#b8c4bc", "q": "#7d8a84",
    "k": "#3a2e3e", "T": "#8fd8ff", "Y": "#ffd23f",
}

TUNIC = (4, 4, 5, 5, 5, 6, 6, 7, 7)          # meia-largura da túnica por linha (9 linhas)

FLASK = [
    ".KKKKK.",
    "..KSK..",
    "..KSK..",
    ".KSSSK.",
    "KVVVVWK",
    "KVvVVVK",
    "KvVVVvK",
    ".KKKKK.",
]
FLASK_CRACKED = [
    ".KKKKK.",
    "..KSK..",
    "..KKK..",
    ".KSKSK.",
    "KVKVKWK",
    "KVvKVVK",
    "KvVVKvK",
    ".KKKKK.",
]
FLASK_FLAT = [                               # girado, voando de lado
    ".KKKK...",
    "KVVvVK..",
    "KVVVVSKK",
    "KvVVVSSK",
    "KVVvVSKK",
    ".KKKK...",
]
BUBBLE = [".K.", "KVK", ".K."]
BUBBLE_L = [".KK.", "KVWK", "KVVK", ".KK."]
BURST = [                                       # o frasco estoura verde no inimigo
    "...K....K...",
    "..KVK..KVK..",
    "K.KVVKKVVK.K",
    "VKKVVVVVVKKV",
    ".KVVWVVWVVK.",
    "..KVVWWVVK..",
    ".KVVWVVWVVK.",
    "VKKVVVVVVKKV",
    "K.KVVKKVVK.K",
    "..KVK..KVK..",
    "...K....K...",
]
STREAK = ["QQQ.", ".QQQ", "QQQ."]      # risquinhos de movimento do arremesso
SMOKE = [
    "...KKK....",
    "..KQQQK.K.",
    ".KQQqQQKQK",
    "KQQQQQqQQK",
    "KQqQQQQQK.",
    ".KKQQqQQK.",
    "...KKKKK..",
]
SMOKE_S = [".KK.", "KQQK", "KqQK", ".KK."]
SHARDS = [                                         # frasco quebrado: gargalo caído, cacos e poça verde
    "..KK.....K.",
    ".KSSK...KSK",
    "KSSK.K..KSK",
    ".KK.KSK.KK.",
    "KKKKKKKKKKK",
    "KVVvVVVVvVK",
    ".KKKKKKKKK.",
]
SHINE = ["..K..", ".KWK.", "KWLWK", ".KWK.", "..K.."]
BOOT = ["KKKK.", "KddKK", "KdddK", "KKKKK"]


def _arm(g, a, b, hand=True):
    """Manga grossa da túnica de `a` (ombro) a `b` (mão), com a mão de pele na ponta."""
    px = {}
    for x, y in line(*a, *b):                   # manga de 2 px de grossura
        px[(x, y)] = px[(x, y + 1)] = "R"
    outline_cells(g, px)
    if hand:
        stamp(g, [".KK.", "KFFK", "KFfK", ".KK."], b[0] - 1, b[1] - 1)


def frame(cx=13, base=30, leg=2, sitting=False, eye="n", feet=(0, 0), arms=(), flask=None, por=(),
           behind=()):
    """Um quadro 32x32 e a âncora do acréscimo (7 à esquerda e 12 acima do topo da túnica).
    `perna`: altura das pernas (0 = agachada); `sentada`: pernas esticadas para a frente, túnica no chão;
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-4, t+1) e o da frente em (cx+4, t+1);
    `frasco`: (sprite, x, y) desenhado por cima da mão."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    t = (base - len(TUNIC) + 1) if sitting else (base - leg - len(TUNIC))
    hx, hy = cx + 1, t - 4
    px = {}
    if sitting:
        stamp(g, BOOT, cx + 5, base - 3)
    else:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + feet[i]
            for y in range(base - leg, base):
                px[(x, y)] = "k"
                px[(x + 1, y)] = "k"
            for x1 in range(x - 1, x + 3):
                px[(x1, base)] = "d"
    for r, w in enumerate(TUNIC):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "r" if x <= cx - w + 1 else ("E" if x == cx + 1 and r > 1 else "R")
    for x in range(hx - 4, hx + 5):
        for y in range(hy - 4, hy + 5):
            if (x - hx) ** 2 + (y - hy) ** 2 <= 21:
                hair = x <= hx - 2 or y <= hy - 3
                px[(x, y)] = ("o" if x <= hx - 4 else "O") if hair else "F"
    for x in range(hx - 7, hx + 7):               # aba do chapéu
        px[(x, hy - 3)] = "D"
    for i, (a, b) in enumerate(((-4, 4), (-4, 3), (-4, 2), (-4, 1), (-5, -1))):   # copa, tombando para trás
        for x in range(hx + a, hx + b + 1):
            px[(x, hy - 4 - i)] = "B" if i == 0 else ("d" if x == hx + a else "D")
    outline_cells(g, px)
    for x in range(hx - 7, hx + 7):
        g[hy - 2][x] = "K" if x in (hx - 7, hx + 6) or not (hx - 4 <= x <= hx + 4) else g[hy - 2][x]
    # rosto: olho de trás livre, olho da frente dentro do monóculo dourado com corrente
    ox, oy = hx + 2, hy
    stamp(g, [".GG.", "G..G", "G..G", ".GG."], ox - 1, oy - 1)
    eyes = {"n": (["K", "K"], ["KL", "KL"]), "fechado": (["..", "kk"], ["kk", "LL"]),
             "feliz": ([".K", "K."], ["KK", "LL"]), "x": (["K.K", ".K.", "K.K"], ["KK", "KK"]),
             "bravo": (["K.", ".K"], ["KK", "KL"]), "cima": (["K", "F"], ["KL", "LL"]),
             "triste": (["K.", "KK"], ["LL", "KK"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 1 - (len(back[0]) > 2), hy - (len(back) > 2))
    stamp(g, front, ox, oy)
    g[oy + 3][ox - 1] = "g"
    g[oy + 4][ox - 2] = "g"
    g[hy + 2][hx - 2] = "P"                       # bochecha
    g[hy + 3][hx + 1] = "f" if eye not in ("x", "triste") else "K"
    if eye == "triste":
        stamp(g, TEAR, hx - 1, hy + 2)
    for a, b in arms:
        _arm(g, a, b)
    if flask:
        stamp(g, *flask)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 7, t - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=2 -> túnica 19-27 (cx=13), cabeça 11-19 (hx=14), chapéu 6-12; ombros em (9, 20) e (17, 20)
_T = ((9, 20), (6, 25))                        # braço de trás solto ao lado
_SEG = ((17, 20), (21, 22))                    # braço da frente segurando o frasco
_F = (FLASK, 18, 14)
_SPECS = {
    # parada com o frasco na mão; o líquido borbulha (bolhas sobem e estouram) e ela pisca
    "idle": [dict(arms=(_T, _SEG), flask=_F),
             dict(arms=(_T, _SEG), flask=_F, por=((BUBBLE, 20, 11),)),
             dict(arms=(_T, _SEG), flask=_F, por=((BUBBLE, 19, 9), (BUBBLE_L, 21, 6))),
             dict(eye="fechado", arms=(_T, _SEG), flask=_F, por=((BUBBLE_L, 20, 4),)),
             dict(arms=(_T, _SEG), flask=_F, por=((BUBBLE, 22, 3),))],
    # corre com as pernas alternando, o frasco à frente e o braço de trás balançando
    "run_r": [dict(feet=(-2, 2), arms=(((9, 20), (5, 23)), ((17, 20), (22, 21))), flask=(FLASK, 19, 13)),
              dict(base=29, feet=(0, 0), arms=(((9, 20), (6, 21)), ((17, 20), (22, 22))),
                   flask=(FLASK, 19, 14)),
              dict(feet=(2, -2), arms=(((9, 20), (5, 23)), ((17, 20), (22, 21))), flask=(FLASK, 19, 13)),
              dict(base=29, feet=(0, 0), arms=(((9, 20), (6, 21)), ((17, 20), (22, 22))),
                   flask=(FLASK, 19, 14))],
    # acena alto com a mão da frente; o frasco fica na outra mão, ao lado
    "waving": [dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (24, 15))), flask=(FLASK, 2, 16)),
               dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (23, 11))), flask=(FLASK, 2, 16)),
               dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (27, 13))), flask=(FLASK, 2, 16)),
               dict(eye="feliz", arms=(((9, 20), (5, 23)), ((17, 20), (23, 11))), flask=(FLASK, 2, 16))],
    # agacha, salta com o frasco erguido, desce, pousa
    "jumping": [dict(leg=0, eye="fechado", arms=(((9, 22), (5, 26)), ((17, 22), (22, 25))),
                     flask=(FLASK, 19, 17)),
                dict(base=28, eye="cima", arms=(((9, 18), (5, 14)), ((17, 18), (22, 12))),
                     flask=(FLASK, 19, 4)),
                dict(base=26, eye="feliz", arms=(((9, 16), (4, 12)), ((17, 16), (23, 10))),
                     flask=(FLASK, 20, 2)),
                dict(base=28, arms=(((9, 18), (5, 21)), ((17, 18), (22, 16))), flask=(FLASK, 19, 8)),
                dict(leg=0, eye="feliz", arms=(((9, 22), (5, 26)), ((17, 22), (22, 25))),
                     flask=(FLASK, 19, 17))],
    # o frasco racha na mão e solta fumaça; ela senta no chão tonta, com cacos e poça verde ao lado
    "failed": [dict(eye="triste", arms=(_T, _SEG), flask=(FLASK_CRACKED, 18, 14)),
               dict(eye="x", arms=(_T, ((17, 20), (21, 23))), flask=(FLASK_CRACKED, 18, 15),
                    por=((SMOKE, 20, 4),)),
               dict(eye="x", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((SHARDS, 21, 24), (SMOKE, 21, 3))),
               dict(eye="x", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((SHARDS, 21, 24), (SMOKE_S, 24, 2), (SMOKE, 21, 7))),
               dict(eye="x", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((SHARDS, 21, 24), (SMOKE_S, 26, 1)))],
    # cochila sentada no chão, frasco ao lado, "z" subindo
    "waiting": [dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22)),
                dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22), por=((Z_S, 25, 8),)),
                dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22), por=((Z_S, 24, 9), (Z_L, 26, 1))),
                dict(eye="fechado", sitting=True, arms=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     flask=(FLASK, 24, 22), por=((Z_L, 26, 1),))],
    # arremesso: arma o frasco para trás no alto, lança (riscos), o frasco voa, estoura verde no inimigo
    "running": [dict(cx=12, eye="bravo", arms=(((8, 20), (3, 12)), ((16, 20), (20, 23))),
                     flask=(FLASK, 0, 4)),
                dict(cx=12, eye="bravo", arms=(((8, 20), (5, 24)), ((16, 20), (24, 17))),
                     flask=(FLASK_FLAT, 23, 10), por=((STREAK, 20, 9),)),
                dict(cx=12, eye="bravo", arms=(((8, 20), (5, 24)), ((16, 20), (22, 22))),
                     flask=(FLASK_FLAT, 24, 7), por=((STREAK, 21, 8),)),
                dict(cx=12, eye="feliz", arms=(((8, 20), (5, 24)), ((16, 20), (22, 22))),
                     por=((BURST, 20, 5),))],
    # mão no queixo, olho de lado pelo monóculo (que brilha), "?" aparece
    "review": [dict(eye="cima", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18)),
               dict(eye="cima", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18),
                    por=((QMARK_S, 25, 4),)),
               dict(eye="cima", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18),
                    por=((QMARK, 25, 2), (SHINE, 18, 7))),
               dict(eye="n", arms=(_T, ((17, 20), (20, 17))), flask=(FLASK, 1, 18),
                    por=((QMARK, 25, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 15x21 colada 7 à esquerda e 12 acima do topo da túnica (túnica a partir da linha 12, centro na coluna 7;
# faixa do chapéu na linha 4, cabeça centrada na coluna 8): cinto de couro com três frascos coloridos na cintura;
# óculos de lente dupla com aro de latão presos na faixa do chapéu, dentro da copa (linhas 2-5, colunas 5-11)
_BELT = [
    "KddddKGKddddK",
    ".KdK...KdKKdK",
    ".KAK...KVKKPK",
    ".KAK...KVKKPK",
    ".KKK...KKKKKK",
]
_GOGGLES = [                                       # aro de latão, sem contorno escuro, para destacar no chapéu
    ".gg.gg.",                                    # 7 de largura: cabe dentro da copa sem comer o contorno dela
    "gLWgLWg",
    "gLLgLLg",
    ".gg.gg.",
]


def _extra(pieces, w=15, h=21):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BELT = _extra(((_BELT, 1, 15),))
BELT_GOGGLES = _extra(((_BELT, 1, 15), (_GOGGLES, 5, 2)))
STAGES = [
    {"title": "Aprendiz de Alquimia", "floor": 1, "extra": None},
    {"title": "Alquimista", "floor": 4, "extra": BELT},
    {"title": "Mestre Alquimista", "floor": 10, "extra": BELT_GOGGLES},
]
