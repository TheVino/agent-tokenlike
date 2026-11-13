"""Espantalho, 32 px, olhando para a direita. Um espantalhinho de cabeça de saco de estopa (olhos de botão e boca
costurada), chapéu de palha de aba larga com fita vermelha, camisa azul cheia de remendos, calça marrom e tufos de
palha saindo do pescoço, das mangas, da barra e dos pés. Parado ele fica de braços abertos (a pose de espantalho);
o símbolo do `running` é a foice: arma no alto, golpeia e solta um corte em meia-lua com palha voando.
No `failed` ele desmonta em palha: a palha escapa das mangas, o chapéu voa e ele afunda num monte de palha.
O tronco e a cabeça andam juntos (só pernas e braços mudam), para o corvinho no ombro e a lanterna de abóbora dos
acréscimos ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha

PAL = {
    "K": "#1a1410", "S": "#dcbc8c", "s": "#a9875a", "Y": "#f5d35e", "y": "#c3922c",
    "C": "#5b86d0", "c": "#3c5c9a", "R": "#d0473c", "G": "#6fb44c", "D": "#8a5a32", "d": "#5e3a20",
    "k": "#4a3628", "W": "#ffffff", "Q": "#d8e0e8", "q": "#8e9aa6", "O": "#f08a24", "o": "#b0541a",
    "L": "#ffe680", "A": "#ff9a3c", "T": "#8fd8ff", "V": "#6a5a86", "v": "#43385a",
}

CAMISA = (4, 4, 5, 5, 5, 6, 6, 6)              # meia-largura da camisa por linha (8 linhas)

FOICE = [                                       # cabo embaixo à esquerda, lâmina curva por cima e para a frente
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


def _girar(s):
    """Gira o sprite 90 graus no sentido horário."""
    return ["".join(s[len(s) - 1 - r][c] for r in range(len(s))) for c in range(len(s[0]))]


FOICE_FRENTE = _girar(FOICE)                   # cabo para trás, lâmina à frente apontando para baixo
CORTE = [                                       # meia-lua do golpe
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
PALHA = ["KKK...", "KYYKK.", ".KKYYK", "...KKK"]   # fiapo de palha voando
PALHA_V = ["KK.", "KYK", "KYK", ".KK"]
RISCO = ["QQQ.", ".QQQ", "QQQ."]
MONTE = [                                       # monte de palha onde ele afunda
    "....KK.K..KK.K....",
    "..KKYYKYKKYYKYKK..",
    ".KYYyYYYYYYyYYYYK.",
    "KYyYYYyYYyYYYYyYYK",
    "KYYYyYYYYYYYyYYYYK",
    ".KKKKKKKKKKKKKKKK.",
]
CHAPEU = [                                      # chapéu caído, de lado no chão
    "....KKKKK....",
    "...KYYYYYK...",
    "..KYYYYYYYK..",
    "..KRRRRRRRK..",
    "KKYYYYYYYYYKK",
    "KYYyYYYYYyYYK",
    ".KKKKKKKKKKK.",
]
CHAPEU_VOANDO = [                               # chapéu girando no ar
    "...KKKK...",
    "..KYYYYK..",
    ".KKRRRRKK.",
    "KYYYYYYYYK",
    ".KKyYYyKK.",
    "...KKKK...",
]
MAO = [".K.K.", "KYKYK", "KYYYK", "KYyYK", ".KKK."]   # mão de tufo de palha


def _braco(g, a, b, mao=True):
    """Manga de 2 px da camisa de `a` (ombro) a `b` (mão), com o tufo de palha na ponta."""
    px = {}
    for x, y in linha(*a, *b):
        px[(x, y)] = px[(x, y + 1)] = "C"
    contornar(g, px)
    if mao:
        carimbar(g, MAO, b[0] - 2, b[1] - 2)


def quadro(cx=13, base=30, perna=3, sentado=False, olho="n", pes=(0, 0), bracos=(), foice=None, por=(),
           chapeu=True):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 12 acima do topo da camisa).
    `perna`: altura das pernas (0 = agachado); `sentado`: afundado no chão, sem pernas;
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-4, t+1) e o da frente em (cx+4, t+1);
    `foice`: (sprite, x, y) desenhado por cima da mão; `chapeu`: False quando o chapéu caiu da cabeça."""
    g = [["."] * N for _ in range(N)]
    t = (base - len(CAMISA) + 1) if sentado else (base - perna - len(CAMISA))
    hx, hy = cx + 1, t - 4
    px = {}
    if not sentado:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + pes[i]
            for y in range(base - perna, base):
                px[(x, y)] = "D" if i else "d"
                px[(x + 1, y)] = "D" if i else "d"
            for x1 in range(x - 1, x + 3):          # pé de palha
                px[(x1, base)] = "Y" if x1 % 2 else "y"
    for r, w in enumerate(CAMISA):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "c" if x <= cx - w + 1 else "C"
    for x in range(cx - 5, cx + 7, 2):               # palha saindo da barra
        px[(x, t + len(CAMISA))] = "Y"
    for x in range(hx - 4, hx + 5):
        for y in range(hy - 4, hy + 5):
            if (x - hx) ** 2 + (y - hy) ** 2 <= 21:
                px[(x, y)] = "s" if x <= hx - 3 else "S"
    for x in (hx - 2, hx, hx + 2):                   # palha do pescoço
        px[(x, hy + 5)] = "Y"
    if chapeu:
        for x in range(hx - 7, hx + 7):              # aba
            px[(x, hy - 3)] = "Y"
        px[(hx - 8, hy - 2)] = px[(hx + 7, hy - 2)] = "y"
        for i, (a, b) in enumerate(((-4, 4), (-4, 3), (-3, 3), (-2, 2))):   # copa
            for x in range(hx + a, hx + b + 1):
                px[(x, hy - 4 - i)] = "R" if i == 0 else ("y" if x == hx + a else "Y")
    contornar(g, px)
    # remendos e cordinha da cintura
    carimbar(g, ["RRR", "RkR", "RRR"], cx - 3, t + 2)
    carimbar(g, ["GG", "GG"], cx + 3, t + 5)
    for x in range(cx - 5, cx + 6):
        if g[t + 4][x] in "Cc":
            g[t + 4][x] = "y"
    # rosto: olhos de botão e boca costurada
    olhos = {"n": (["KK", "KW"], ["KK", "KW"]), "fechado": (["..", "kk"], ["..", "kk"]),
             "feliz": ([".k", "k."], [".k", "k."]), "x": (["K.K", ".K.", "K.K"], ["K.K", ".K.", "K.K"]),
             "bravo": (["K.", "KK"], [".K", "KK"]), "cima": (["KW", "KK"], ["KW", "KK"]),
             "triste": (["KK", "K."], ["KK", ".K"])}[olho]
    tras, frente = olhos
    carimbar(g, tras, hx - 1 - (len(tras[0]) > 2), hy - 1 - (len(tras) > 2))
    carimbar(g, frente, hx + 2, hy - 1 - (len(frente) > 2))
    g[hy + 2][hx] = g[hy + 2][hx + 3] = "k"       # sorrisinho costurado
    g[hy + 3][hx + 1] = g[hy + 3][hx + 2] = "k"
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 1, hy + 1)
    for a, b in bracos:
        _braco(g, a, b)
    if foice:
        carimbar(g, *foice)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 12)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=3 -> camisa 19-26 (cx=13), cabeça 11-19 (hx=14), chapéu 7-12; ombros em (9, 20) e (17, 20)
_ABERTO = (((9, 20), (3, 20)), ((17, 20), (25, 20)))     # braços abertos, a pose de espantalho
_CAIDO = (((9, 20), (7, 26)), ((17, 20), (19, 26)))      # braços pendurados
_SPECS = {
    # braços abertos; a palha das mãos balança, um fiapo cai e ele pisca
    "idle": [dict(bracos=_ABERTO),
             dict(bracos=(((9, 20), (3, 21)), ((17, 20), (25, 19)))),
             dict(bracos=_ABERTO, por=((PALHA_V, 25, 23),)),
             dict(olho="fechado", bracos=(((9, 20), (3, 19)), ((17, 20), (25, 21))), por=((PALHA_V, 26, 26),)),
             dict(bracos=_ABERTO)],
    # corre desengonçado: pernas alternando, braços balançando
    "run_r": [dict(pes=(-2, 2), bracos=(((9, 20), (4, 23)), ((17, 20), (23, 17)))),
              dict(base=29, bracos=(((9, 20), (5, 20)), ((17, 20), (23, 21)))),
              dict(pes=(2, -2), bracos=(((9, 20), (4, 17)), ((17, 20), (22, 24)))),
              dict(base=29, bracos=(((9, 20), (5, 20)), ((17, 20), (23, 21))))],
    # acena alto com a mão da frente, palha voando da mão
    "waving": [dict(olho="feliz", bracos=(((9, 20), (5, 24)), ((17, 20), (24, 13)))),
               dict(olho="feliz", bracos=(((9, 20), (5, 24)), ((17, 20), (21, 9)))),
               dict(olho="feliz", bracos=(((9, 20), (5, 24)), ((17, 20), (26, 11))), por=((PALHA, 25, 3),)),
               dict(olho="feliz", bracos=(((9, 20), (5, 24)), ((17, 20), (21, 9))))],
    # agacha, salta de braços para cima, desce, pousa
    "jumping": [dict(perna=0, olho="fechado", bracos=(((9, 23), (4, 26)), ((17, 23), (22, 26)))),
                dict(base=28, olho="cima", bracos=(((9, 18), (4, 13)), ((17, 18), (23, 13)))),
                dict(base=26, olho="feliz", bracos=(((9, 16), (3, 10)), ((17, 16), (24, 10)))),
                dict(base=28, bracos=(((9, 18), (3, 18)), ((17, 18), (24, 18)))),
                dict(perna=0, olho="feliz", bracos=(((9, 23), (4, 26)), ((17, 23), (22, 26))))],
    # a palha escapa das mangas, o chapéu voa e ele afunda num monte de palha
    "failed": [dict(olho="triste", bracos=_CAIDO, por=((PALHA_V, 5, 27), (PALHA_V, 20, 27))),
               dict(olho="x", chapeu=False, bracos=(((9, 21), (5, 27)), ((17, 21), (21, 27))),
                    por=((CHAPEU_VOANDO, 18, 1), (PALHA, 1, 23), (PALHA, 23, 22))),
               dict(olho="x", sentado=True, chapeu=False, bracos=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MONTE, 5, 26), (CHAPEU, 19, 3), (PALHA, 0, 14), (PALHA, 25, 13))),
               dict(olho="x", sentado=True, chapeu=False, bracos=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MONTE, 5, 26), (CHAPEU, 19, 11), (PALHA_V, 2, 20))),
               dict(olho="x", sentado=True, chapeu=False, bracos=(((9, 24), (4, 28)), ((17, 24), (22, 28))),
                    por=((MONTE, 5, 26), (CHAPEU, 19, 25)))],
    # cochila de pé, braços pendurados, "z" subindo
    "waiting": [dict(olho="fechado", bracos=_CAIDO),
                dict(olho="fechado", bracos=_CAIDO, por=((Z_P, 23, 7),)),
                dict(olho="fechado", bracos=_CAIDO, por=((Z_P, 22, 8), (Z_G, 25, 0))),
                dict(olho="fechado", bracos=_CAIDO, por=((Z_G, 25, 0),))],
    # foice: arma no alto atrás da cabeça, golpeia para a frente, corte em meia-lua com palha voando
    "running": [dict(cx=11, olho="bravo", bracos=(((7, 20), (3, 23)), ((15, 20), (19, 10))),
                     foice=(FOICE, 18, 2)),
                dict(cx=11, olho="bravo", bracos=(((7, 20), (3, 23)), ((15, 20), (22, 16))),
                     foice=(_girar(FOICE), 21, 10), por=((RISCO, 21, 4),)),
                dict(cx=11, olho="bravo", bracos=(((7, 20), (3, 23)), ((15, 20), (21, 20))),
                     foice=(FOICE_FRENTE, 20, 19), por=((CORTE, 20, 6), (PALHA, 25, 2))),
                dict(cx=11, olho="feliz", bracos=(((7, 20), (3, 23)), ((15, 20), (20, 23))),
                     foice=(FOICE_FRENTE, 19, 22), por=((PALHA, 24, 8), (PALHA_V, 28, 14)))],
    # mão no queixo, "?" aparece
    "review": [dict(olho="cima", bracos=(_CAIDO[0], ((17, 20), (20, 17)))),
               dict(olho="cima", bracos=(_CAIDO[0], ((17, 20), (20, 17))), por=((INTERROG_P, 24, 3),)),
               dict(olho="cima", bracos=(_CAIDO[0], ((17, 20), (20, 17))), por=((INTERROG, 24, 1),)),
               dict(olho="n", bracos=(_CAIDO[0], ((17, 20), (20, 17))), por=((INTERROG, 24, 1),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# grade 16x21 colada 8 à esquerda e 12 acima do topo da camisa (camisa a partir da linha 12, centro na coluna 8):
# corvinho sentado no ombro de trás (linhas 7-12) e lanterna de abóbora pendurada no quadril de trás
_CORVO = [                                     # corvinho de penas escuras, bico laranja encostado na cabeça
    "..KK..",
    ".KVVK.",
    "KVVWKK",
    "KvVVKA",
    "KvvVVK",
    ".KKKK.",
]
_LANTERNA = [
    "...K...",
    "..KGK..",
    ".KKKKK.",
    "KOLOLOK",
    "KOOOOOK",
    "KoLLLoK",
    ".KKKKK.",
]


def _extra(pecas, w=16, h=21):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CORVO = _extra(((_CORVO, 0, 7),))
CORVO_LANTERNA = _extra(((_CORVO, 0, 7), (_LANTERNA, 0, 14)))
ESTAGIOS = [
    {"title": "Espantalhinho", "floor": 1, "extra": None},
    {"title": "Espantalho", "floor": 4, "extra": CORVO},
    {"title": "Guardião da Lavoura", "floor": 10, "extra": CORVO_LANTERNA},
]
