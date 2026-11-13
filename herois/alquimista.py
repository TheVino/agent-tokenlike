"""Alquimista, 32 px, olhando para a direita. Uma aprendiz de túnica verde-azulada com chapéu de couro de aba larga,
cabelo cor de cobre e um monóculo dourado de corrente no olho da frente. O símbolo é o frasco de vidro com
líquido verde: borbulha no idle, vira granada no `running` (arremesso e estouro verde). No `failed` o frasco racha
na mão, solta fumaça e ela senta no chão tonta, com cacos e uma poça verde ao lado.
O tronco, a cabeça e o chapéu andam juntos (só pernas e braços mudam), para o cinto e os óculos do acréscimo
ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha

PAL = {
    "K": "#1a1422", "R": "#3f9a84", "r": "#2a6658", "E": "#9fe8c8", "F": "#f6d7c3", "f": "#d8a98e",
    "O": "#e0782e", "o": "#a8501e", "D": "#9a6236", "d": "#5e3a20", "B": "#c8334a",
    "G": "#ffd23f", "g": "#b8860b", "L": "#bfe8ff", "W": "#ffffff", "S": "#d8e6f0",
    "V": "#a6f06b", "v": "#4c9a3a", "P": "#ff6fae", "A": "#ffa94d", "Q": "#b8c4bc", "q": "#7d8a84",
    "k": "#3a2e3e", "T": "#8fd8ff", "Y": "#ffd23f",
}

TUNICA = (4, 4, 5, 5, 5, 6, 6, 7, 7)          # meia-largura da túnica por linha (9 linhas)

FRASCO = [
    ".KKKKK.",
    "..KSK..",
    "..KSK..",
    ".KSSSK.",
    "KVVVVWK",
    "KVvVVVK",
    "KvVVVvK",
    ".KKKKK.",
]
FRASCO_RACHADO = [
    ".KKKKK.",
    "..KSK..",
    "..KKK..",
    ".KSKSK.",
    "KVKVKWK",
    "KVvKVVK",
    "KvVVKvK",
    ".KKKKK.",
]
FRASCO_DEITADO = [                               # girado, voando de lado
    ".KKKK...",
    "KVVvVK..",
    "KVVVVSKK",
    "KvVVVSSK",
    "KVVvVSKK",
    ".KKKK...",
]
BOLHA = [".K.", "KVK", ".K."]
BOLHA_G = [".KK.", "KVWK", "KVVK", ".KK."]
ESTOURO = [                                       # o frasco estoura verde no inimigo
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
RISCO = ["QQQ.", ".QQQ", "QQQ."]      # risquinhos de movimento do arremesso
FUMACA = [
    "...KKK....",
    "..KQQQK.K.",
    ".KQQqQQKQK",
    "KQQQQQqQQK",
    "KQqQQQQQK.",
    ".KKQQqQQK.",
    "...KKKKK..",
]
FUMACA_P = [".KK.", "KQQK", "KqQK", ".KK."]
CACOS = [                                         # frasco quebrado: gargalo caído, cacos e poça verde
    "..KK.....K.",
    ".KSSK...KSK",
    "KSSK.K..KSK",
    ".KK.KSK.KK.",
    "KKKKKKKKKKK",
    "KVVvVVVVvVK",
    ".KKKKKKKKK.",
]
BRILHO = ["..K..", ".KWK.", "KWLWK", ".KWK.", "..K.."]
BOTA = ["KKKK.", "KddKK", "KdddK", "KKKKK"]


def _braco(g, a, b, mao=True):
    """Manga grossa da túnica de `a` (ombro) a `b` (mão), com a mão de pele na ponta."""
    px = {}
    for x, y in linha(*a, *b):                   # manga de 2 px de grossura
        px[(x, y)] = px[(x, y + 1)] = "R"
    contornar(g, px)
    if mao:
        carimbar(g, [".KK.", "KFFK", "KFfK", ".KK."], b[0] - 1, b[1] - 1)


def quadro(cx=13, base=30, perna=2, sentada=False, olho="n", pes=(0, 0), bracos=(), frasco=None, por=(),
           atras=()):
    """Um quadro 32x32 e a âncora do acréscimo (7 à esquerda e 12 acima do topo da túnica).
    `perna`: altura das pernas (0 = agachada); `sentada`: pernas esticadas para a frente, túnica no chão;
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-4, t+1) e o da frente em (cx+4, t+1);
    `frasco`: (sprite, x, y) desenhado por cima da mão."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    t = (base - len(TUNICA) + 1) if sentada else (base - perna - len(TUNICA))
    hx, hy = cx + 1, t - 4
    px = {}
    if sentada:
        carimbar(g, BOTA, cx + 5, base - 3)
    else:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + pes[i]
            for y in range(base - perna, base):
                px[(x, y)] = "k"
                px[(x + 1, y)] = "k"
            for x1 in range(x - 1, x + 3):
                px[(x1, base)] = "d"
    for r, w in enumerate(TUNICA):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "r" if x <= cx - w + 1 else ("E" if x == cx + 1 and r > 1 else "R")
    for x in range(hx - 4, hx + 5):
        for y in range(hy - 4, hy + 5):
            if (x - hx) ** 2 + (y - hy) ** 2 <= 21:
                cabelo = x <= hx - 2 or y <= hy - 3
                px[(x, y)] = ("o" if x <= hx - 4 else "O") if cabelo else "F"
    for x in range(hx - 7, hx + 7):               # aba do chapéu
        px[(x, hy - 3)] = "D"
    for i, (a, b) in enumerate(((-4, 4), (-4, 3), (-4, 2), (-4, 1), (-5, -1))):   # copa, tombando para trás
        for x in range(hx + a, hx + b + 1):
            px[(x, hy - 4 - i)] = "B" if i == 0 else ("d" if x == hx + a else "D")
    contornar(g, px)
    for x in range(hx - 7, hx + 7):
        g[hy - 2][x] = "K" if x in (hx - 7, hx + 6) or not (hx - 4 <= x <= hx + 4) else g[hy - 2][x]
    # rosto: olho de trás livre, olho da frente dentro do monóculo dourado com corrente
    ox, oy = hx + 2, hy
    carimbar(g, [".GG.", "G..G", "G..G", ".GG."], ox - 1, oy - 1)
    olhos = {"n": (["K", "K"], ["KL", "KL"]), "fechado": (["..", "kk"], ["kk", "LL"]),
             "feliz": ([".K", "K."], ["KK", "LL"]), "x": (["K.K", ".K.", "K.K"], ["KK", "KK"]),
             "bravo": (["K.", ".K"], ["KK", "KL"]), "cima": (["K", "F"], ["KL", "LL"]),
             "triste": (["K.", "KK"], ["LL", "KK"])}[olho]
    tras, frente = olhos
    carimbar(g, tras, hx - 1 - (len(tras[0]) > 2), hy - (len(tras) > 2))
    carimbar(g, frente, ox, oy)
    g[oy + 3][ox - 1] = "g"
    g[oy + 4][ox - 2] = "g"
    g[hy + 2][hx - 2] = "P"                       # bochecha
    g[hy + 3][hx + 1] = "f" if olho not in ("x", "triste") else "K"
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 1, hy + 2)
    for a, b in bracos:
        _braco(g, a, b)
    if frasco:
        carimbar(g, *frasco)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 7, t - 12)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=2 -> túnica 19-27 (cx=13), cabeça 11-19 (hx=14), chapéu 6-12; ombros em (9, 20) e (17, 20)
_T = ((9, 20), (6, 25))                        # braço de trás solto ao lado
_SEG = ((17, 20), (21, 22))                    # braço da frente segurando o frasco
_F = (FRASCO, 18, 14)
_SPECS = {
    # parada com o frasco na mão; o líquido borbulha (bolhas sobem e estouram) e ela pisca
    "idle": [dict(bracos=(_T, _SEG), frasco=_F),
             dict(bracos=(_T, _SEG), frasco=_F, por=((BOLHA, 20, 11),)),
             dict(bracos=(_T, _SEG), frasco=_F, por=((BOLHA, 19, 9), (BOLHA_G, 21, 6))),
             dict(olho="fechado", bracos=(_T, _SEG), frasco=_F, por=((BOLHA_G, 20, 4),)),
             dict(bracos=(_T, _SEG), frasco=_F, por=((BOLHA, 22, 3),))],
    # corre com as pernas alternando, o frasco à frente e o braço de trás balançando
    "run_r": [dict(pes=(-2, 2), bracos=(((9, 20), (5, 23)), ((17, 20), (22, 21))), frasco=(FRASCO, 19, 13)),
              dict(base=29, pes=(0, 0), bracos=(((9, 20), (6, 21)), ((17, 20), (22, 22))),
                   frasco=(FRASCO, 19, 14)),
              dict(pes=(2, -2), bracos=(((9, 20), (5, 23)), ((17, 20), (22, 21))), frasco=(FRASCO, 19, 13)),
              dict(base=29, pes=(0, 0), bracos=(((9, 20), (6, 21)), ((17, 20), (22, 22))),
                   frasco=(FRASCO, 19, 14))],
    # acena alto com a mão da frente; o frasco fica na outra mão, ao lado
    "waving": [dict(olho="feliz", bracos=(((9, 20), (5, 23)), ((17, 20), (24, 15))), frasco=(FRASCO, 2, 16)),
               dict(olho="feliz", bracos=(((9, 20), (5, 23)), ((17, 20), (23, 11))), frasco=(FRASCO, 2, 16)),
               dict(olho="feliz", bracos=(((9, 20), (5, 23)), ((17, 20), (27, 13))), frasco=(FRASCO, 2, 16)),
               dict(olho="feliz", bracos=(((9, 20), (5, 23)), ((17, 20), (23, 11))), frasco=(FRASCO, 2, 16))],
    # agacha, salta com o frasco erguido, desce, pousa
    "jumping": [dict(perna=0, olho="fechado", bracos=(((9, 22), (5, 26)), ((17, 22), (22, 25))),
                     frasco=(FRASCO, 19, 17)),
                dict(base=28, olho="cima", bracos=(((9, 18), (5, 14)), ((17, 18), (22, 12))),
                     frasco=(FRASCO, 19, 4)),
                dict(base=26, olho="feliz", bracos=(((9, 16), (4, 12)), ((17, 16), (23, 10))),
                     frasco=(FRASCO, 20, 2)),
                dict(base=28, bracos=(((9, 18), (5, 21)), ((17, 18), (22, 16))), frasco=(FRASCO, 19, 8)),
                dict(perna=0, olho="feliz", bracos=(((9, 22), (5, 26)), ((17, 22), (22, 25))),
                     frasco=(FRASCO, 19, 17))],
    # o frasco racha na mão e solta fumaça; ela senta no chão tonta, com cacos e poça verde ao lado
    "failed": [dict(olho="triste", bracos=(_T, _SEG), frasco=(FRASCO_RACHADO, 18, 14)),
               dict(olho="x", bracos=(_T, ((17, 20), (21, 23))), frasco=(FRASCO_RACHADO, 18, 15),
                    por=((FUMACA, 20, 4),)),
               dict(olho="x", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((CACOS, 21, 24), (FUMACA, 21, 3))),
               dict(olho="x", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((CACOS, 21, 24), (FUMACA_P, 24, 2), (FUMACA, 21, 7))),
               dict(olho="x", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (19, 27))),
                    por=((CACOS, 21, 24), (FUMACA_P, 26, 1)))],
    # cochila sentada no chão, frasco ao lado, "z" subindo
    "waiting": [dict(olho="fechado", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     frasco=(FRASCO, 24, 22)),
                dict(olho="fechado", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     frasco=(FRASCO, 24, 22), por=((Z_P, 25, 8),)),
                dict(olho="fechado", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     frasco=(FRASCO, 24, 22), por=((Z_P, 24, 9), (Z_G, 26, 1))),
                dict(olho="fechado", sentada=True, bracos=(((9, 23), (5, 28)), ((17, 23), (20, 27))),
                     frasco=(FRASCO, 24, 22), por=((Z_G, 26, 1),))],
    # arremesso: arma o frasco para trás no alto, lança (riscos), o frasco voa, estoura verde no inimigo
    "running": [dict(cx=12, olho="bravo", bracos=(((8, 20), (3, 12)), ((16, 20), (20, 23))),
                     frasco=(FRASCO, 0, 4)),
                dict(cx=12, olho="bravo", bracos=(((8, 20), (5, 24)), ((16, 20), (24, 17))),
                     frasco=(FRASCO_DEITADO, 23, 10), por=((RISCO, 20, 9),)),
                dict(cx=12, olho="bravo", bracos=(((8, 20), (5, 24)), ((16, 20), (22, 22))),
                     frasco=(FRASCO_DEITADO, 24, 7), por=((RISCO, 21, 8),)),
                dict(cx=12, olho="feliz", bracos=(((8, 20), (5, 24)), ((16, 20), (22, 22))),
                     por=((ESTOURO, 20, 5),))],
    # mão no queixo, olho de lado pelo monóculo (que brilha), "?" aparece
    "review": [dict(olho="cima", bracos=(_T, ((17, 20), (20, 17))), frasco=(FRASCO, 1, 18)),
               dict(olho="cima", bracos=(_T, ((17, 20), (20, 17))), frasco=(FRASCO, 1, 18),
                    por=((INTERROG_P, 25, 4),)),
               dict(olho="cima", bracos=(_T, ((17, 20), (20, 17))), frasco=(FRASCO, 1, 18),
                    por=((INTERROG, 25, 2), (BRILHO, 18, 7))),
               dict(olho="n", bracos=(_T, ((17, 20), (20, 17))), frasco=(FRASCO, 1, 18),
                    por=((INTERROG, 25, 2),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# grade 15x21 colada 7 à esquerda e 12 acima do topo da túnica (túnica a partir da linha 12, centro na coluna 7;
# faixa do chapéu na linha 4, cabeça centrada na coluna 8): cinto de couro com três frascos coloridos na cintura;
# óculos de lente dupla com aro de latão presos na faixa do chapéu, dentro da copa (linhas 2-5, colunas 5-11)
_CINTO = [
    "KddddKGKddddK",
    ".KdK...KdKKdK",
    ".KAK...KVKKPK",
    ".KAK...KVKKPK",
    ".KKK...KKKKKK",
]
_OCULOS = [                                       # aro de latão, sem contorno escuro, para destacar no chapéu
    ".gg.gg.",                                    # 7 de largura: cabe dentro da copa sem comer o contorno dela
    "gLWgLWg",
    "gLLgLLg",
    ".gg.gg.",
]


def _extra(pecas, w=15, h=21):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CINTO = _extra(((_CINTO, 1, 15),))
CINTO_OCULOS = _extra(((_CINTO, 1, 15), (_OCULOS, 5, 2)))
ESTAGIOS = [
    {"title": "Aprendiz de Alquimia", "floor": 1, "extra": None},
    {"title": "Alquimista", "floor": 4, "extra": CINTO},
    {"title": "Mestre Alquimista", "floor": 10, "extra": CINTO_OCULOS},
]
