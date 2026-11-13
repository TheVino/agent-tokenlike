"""Freira das Cinzas, 32 px, olhando para a direita. Uma freirinha baixinha de hábito cinza-cinza (cor de cinza
de lareira), véu escuro arredondado caindo pelas costas e touca branca emoldurando o rosto redondo. O símbolo é o
terço de ossinhos (contas de osso com uma caveirinha na ponta): balança no idle, vira chicote no `running` (a
caveirinha estala no inimigo numa explosão de brasas). No `failed` ela se desfaz em cinza: o hábito esfarela e
sobra um montinho de cinza com brasas, com o véu caído por cima e o terço ao lado.
O tronco e a cabeça andam juntos (só pés e braços mudam), para o cordão e o véu longo dos acréscimos ficarem
sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha

PAL = {
    "K": "#16121c", "H": "#aaa3b0", "h": "#7d7688", "V": "#6d6580", "v": "#4c455c", "C": "#efebf2",
    "F": "#f6dccb", "f": "#d8b3a0", "P": "#ff8fae", "L": "#bfe8ff", "d": "#3a3340", "k": "#3a2e3e",
    "W": "#efe6cf", "w": "#c7b993", "Q": "#c3bdc6", "q": "#8d8794", "O": "#ff8a3d", "o": "#c2421e",
    "Y": "#ffd23f", "T": "#8fd8ff", "D": "#8a5a32",
}

HABITO = (3, 4, 4, 5, 5, 6, 6, 7, 7, 7)       # meia-largura do hábito por linha (10 linhas, até o chão)

CRANIO = [".KKKK.", "KWWWWK", "KOWWOK", "KWWWWK", ".KwwK.", "..KK.."]   # caveirinha de olhos em brasa
BRASA = [                                       # a caveirinha estala: explosão de brasas
    "...K...K....",
    "..KOK.KYK...",
    "K.KOOKKYOK.K",
    "OKKOYYOYOKKO",
    ".KOYYWYYOOK.",
    "..KOYWWYOK..",
    ".KOOYYYYOOK.",
    "OKKOOYOOOKKO",
    "K.KOoKKOoK.K",
    "..KoK..KoK..",
    "...K....K...",
]
FAGULHA = [".K.", "KOK", ".K."]
FAGULHA_Y = [".K.", "KYK", ".K."]
RISCO = ["QQQ.", ".QQQ", "QQQ."]
FUMACA = [
    "..KKK...",
    ".KQQQK..",
    "KQqQQQK.",
    "KQQQqQK.",
    ".KKQQQK.",
    "...KKK..",
]
FUMACA_P = [".KK.", "KQQK", "KqQK", ".KK."]
CINZA = ["Q.", ".q"]                             # flocos de cinza caindo


def _braco(g, a, b, mao=True):
    """Manga larga do hábito de `a` (ombro) a `b` (mão), com a mãozinha de pele na ponta."""
    px = {}
    for x, y in linha(*a, *b):
        px[(x, y)] = px[(x, y + 1)] = "h"
    contornar(g, px)
    if mao:
        carimbar(g, [".KK.", "KFFK", "KFfK", ".KK."], b[0] - 1, b[1] - 1)


def _terco(g, mao, ponta):
    """Terço de ossinhos: contas de osso da mão até a ponta, com a caveirinha pendurada nela."""
    px = {}
    for i, (x, y) in enumerate(linha(*mao, *ponta)[1:]):    # contas de 2 px, alternando osso claro e escuro
        px[(x, y)] = "W" if i % 3 == 0 else "w"
        if i % 3 == 0:                            # conta de osso 2x2, cordão fininho entre elas
            px[(x + 1, y)] = px[(x, y + 1)] = px[(x + 1, y + 1)] = "W"
    contornar(g, px)
    carimbar(g, CRANIO, ponta[0] - 2, ponta[1])


def _monte(g, cx, base, fase):
    """Montinho de cinza com brasas e o véu caído por cima (fase 1 = ainda desmanchando, 2 = só o montinho)."""
    px = {}
    # montes de tamanhos diferentes (centro x, centro y, raio x, raio y) somados: contorno de cima irregular
    for mx, my, rx, ry in ((cx - 6, base, 4, 3), (cx, base - 1, 5, 3), (cx + 6, base - 1, 4, 5),
                           (cx + 10, base + 1, 2, 2), (cx - 10, base + 1, 1, 1)):
        for x in range(mx - rx, mx + rx + 1):
            for y in range(my - ry, min(my + ry, base) + 1):
                if (x - mx) ** 2 / (rx + 0.5) ** 2 + (y - my) ** 2 / (ry + 0.5) ** 2 <= 1:
                    px[(x, y)] = "q" if (3 * x + 7 * y) % 11 < 2 else "Q"
    for x, y in ((cx - 12, base), (cx + 13, base), (cx + 3, base - 6)):   # farelos soltos
        px[(x, y)] = "Q"
    hx, hy = cx - 1, base - 5                    # o véu caído e amassado em cima do montinho, escorregando à direita
    for x in range(hx - 6, hx + 7):
        for y in range(hy - 4, hy + 3):
            if (x - hx) ** 2 / 26 + (y - hy - 1 - (x - hx) // 3) ** 2 / 9 <= 1:
                px[(x, y)] = "v" if x <= hx - 3 else "V"
    for x in range(hx - 1, hx + 6):              # pontinha da touca aparecendo debaixo do véu
        px[(x, hy + 3)] = "C"
    contornar(g, px)
    brasas = [(cx - 5, base - 1), (cx + 4, base - 2), (cx - 1, base)] if fase == 2 else [(cx + 3, base - 1)]
    for x, y in brasas:
        g[y][x] = "O"
        g[y - 1][x] = "o"


def quadro(cx=13, base=30, perna=1, olho="n", pes=(0, 0), bracos=(), terco=None, por=(), monte=0, esfarela=False):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 12 acima do topo do hábito).
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-4, t+1) e o da frente em (cx+4, t+1);
    `terco`: ((mão), (ponta)) desenhado por cima da mão; `monte`: 1 ou 2 = virou montinho de cinza."""
    g = [["."] * N for _ in range(N)]
    if monte:
        _monte(g, cx, base, monte)
        for s, x, y in por:
            carimbar(g, s, x, y)
        return ["".join(l) for l in g], (cx - 8, base - 16)
    t = base - perna - len(HABITO)
    hx, hy = cx + 1, t - 5
    px = {}
    for i, x0 in enumerate((cx - 3, cx + 1)):     # sapatinhos aparecendo embaixo do hábito
        x = x0 + pes[i]
        for y in range(base - perna, base + 1):
            for x1 in range(x, x + 3):
                px[(x1, y)] = "d"
    for r, w in enumerate(HABITO):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "h" if x <= cx - w + 1 else "H"
        if esfarela and r >= 6:                   # a barra do hábito vira cinza
            for x in range(cx - w, cx + w + 1):
                px[(x, y)] = "q" if (x + y) % 3 else "Q"
    for y in range(hy, t + 4):                    # o véu cai pelas costas até os ombros
        for x in range(hx - 6, hx - 1):
            px[(x, y)] = "v" if x <= hx - 4 else "V"
    for x in range(hx - 5, hx + 6):
        for y in range(hy - 5, hy + 6):
            d = (x - hx) ** 2 + (y - hy) ** 2
            if d <= 27:
                px[(x, y)] = "v" if x <= hx - 3 else "V"
            fd = (x - hx - 1) ** 2 + (y - hy - 1) ** 2
            if fd <= 15 and d <= 27:
                px[(x, y)] = "F" if fd <= 7 else "C"
    contornar(g, px)
    # rosto: dois olhinhos, bochecha e boquinha
    olhos = {"n": (["K", "K"], ["K", "L"]), "fechado": (["k"], ["k"]), "feliz": ([".", "K"], [".", "K"]),
             "x": (["K.K", ".K.", "K.K"], None), "bravo": (["K", "K"], ["K", "K"]), "cima": (["K"], ["L"]),
             "triste": (["K", "K"], ["K", "K"])}[olho]
    ex, ey = hx, hy
    if olho == "x":                               # olhinhos ">" e "<"
        carimbar(g, ["K.", ".K", "K."], ex - 1, ey - 1)
        carimbar(g, [".K", "K.", ".K"], ex + 2, ey - 1)
    else:
        carimbar(g, olhos[0], ex, ey)
        carimbar(g, olhos[1], ex + 2, ey)
    if olho == "feliz":
        g[ey][ex - 1] = g[ey][ex + 1] = g[ey][ex + 3] = "F"
        g[ey][ex], g[ey][ex + 2] = "K", "K"
        g[ey + 1][ex], g[ey + 1][ex + 2] = "F", "F"
    if olho == "bravo":
        g[ey - 1][ex] = g[ey - 1][ex + 2] = "K"
    if olho == "cima":
        g[ey - 1][ex] = g[ey - 1][ex + 2] = "K"
    g[hy + 2][hx + 3] = "P"                       # bochecha
    g[hy + 3][hx + 1] = "f" if olho not in ("x", "triste") else "K"
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 1, hy + 2)
    for a, b in bracos:
        _braco(g, a, b)
    if terco:
        _terco(g, *terco)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 12)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=1 -> hábito 19-28 (cx=13), cabeça 9-19 (hx=14, hy=14); ombros em (9, 20) e (17, 20)
_T = ((9, 20), (6, 25))                         # braço de trás solto ao lado
_F = ((17, 20), (20, 22))                       # braço da frente segurando o terço
_SPECS = {
    # parada com o terço pendurado na mão da frente; ele balança de um lado para o outro e ela pisca
    "idle": [dict(bracos=(_T, _F), terco=((20, 22), (21, 27))),
             dict(bracos=(_T, _F), terco=((20, 22), (24, 26))),
             dict(bracos=(_T, _F), terco=((20, 22), (26, 25))),
             dict(olho="fechado", bracos=(_T, _F), terco=((20, 22), (24, 26))),
             dict(bracos=(_T, _F), terco=((20, 22), (21, 27)))],
    # trotando com os sapatinhos alternando e o terço balançando para trás
    "run_r": [dict(pes=(-2, 2), bracos=(((9, 20), (5, 23)), ((17, 20), (21, 21))), terco=((21, 21), (18, 26))),
              dict(base=29, bracos=(((9, 20), (6, 22)), ((17, 20), (21, 22))), terco=((21, 22), (20, 26))),
              dict(pes=(2, -2), bracos=(((9, 20), (5, 23)), ((17, 20), (21, 21))), terco=((21, 21), (18, 26))),
              dict(base=29, bracos=(((9, 20), (6, 22)), ((17, 20), (21, 22))), terco=((21, 22), (20, 26)))],
    # acena alto com a mão da frente; o terço gira pendurado no pulso
    "waving": [dict(olho="feliz", bracos=(_T, ((17, 20), (23, 14))), terco=((23, 14), (26, 18))),
               dict(olho="feliz", bracos=(_T, ((17, 20), (21, 10))), terco=((21, 10), (25, 13))),
               dict(olho="feliz", bracos=(_T, ((17, 20), (26, 12))), terco=((26, 12), (27, 17))),
               dict(olho="feliz", bracos=(_T, ((17, 20), (21, 10))), terco=((21, 10), (25, 13)))],
    # agacha, salta com o terço erguido, desce, pousa
    "jumping": [dict(perna=0, olho="fechado", bracos=(((9, 21), (5, 25)), ((17, 21), (21, 24))),
                     terco=((21, 24), (23, 27))),
                dict(base=28, olho="cima", bracos=(((9, 18), (5, 14)), ((17, 18), (22, 12))),
                     terco=((22, 12), (25, 16))),
                dict(base=26, olho="feliz", bracos=(((9, 16), (4, 11)), ((17, 16), (23, 9))),
                     terco=((23, 9), (26, 13))),
                dict(base=28, bracos=(((9, 18), (5, 21)), ((17, 18), (22, 16))), terco=((22, 16), (24, 21))),
                dict(perna=0, olho="feliz", bracos=(((9, 21), (5, 25)), ((17, 21), (21, 24))),
                     terco=((21, 24), (23, 27)))],
    # desfaz em cinza: chora, o hábito esfarela, vira montinho de cinza com o véu por cima e o terço ao lado
    "failed": [dict(olho="triste", bracos=(_T, _F), terco=((20, 22), (21, 27))),
               dict(olho="x", esfarela=True, bracos=(((9, 20), (5, 24)), ((17, 20), (22, 24))),
                    terco=((22, 24), (25, 27)), por=((CINZA, 4, 27), (CINZA, 24, 29), (CINZA, 7, 30))),
               dict(monte=1, por=((CRANIO, 24, 25), (FUMACA, 18, 10), (CINZA, 6, 19))),
               dict(monte=2, por=((CRANIO, 24, 25), (FUMACA_P, 21, 9), (FUMACA, 18, 4))),
               dict(monte=2, por=((CRANIO, 24, 25), (FUMACA_P, 22, 2)))],
    # cochila de cabeça baixa, terço pendurado, "z" subindo
    "waiting": [dict(perna=0, olho="fechado", bracos=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     terco=((19, 25), (20, 29))),
                dict(perna=0, olho="fechado", bracos=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     terco=((19, 25), (20, 29)), por=((Z_P, 24, 7),)),
                dict(perna=0, olho="fechado", bracos=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     terco=((19, 25), (20, 29)), por=((Z_P, 23, 8), (Z_G, 25, 0))),
                dict(perna=0, olho="fechado", bracos=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     terco=((19, 25), (20, 29)), por=((Z_G, 25, 0),))],
    # chicotada: ergue o terço para trás no alto, gira para a frente (riscos), a caveirinha estala em brasas
    "running": [dict(cx=11, olho="bravo", bracos=(((7, 20), (4, 25)), ((15, 20), (19, 7))),
                     terco=((19, 7), (9, 1))),
                dict(cx=11, olho="bravo", bracos=(((7, 20), (4, 25)), ((15, 20), (21, 17))),
                     terco=((21, 17), (27, 12)), por=((RISCO, 21, 5),)),
                dict(cx=11, olho="bravo", bracos=(((7, 20), (4, 25)), ((15, 20), (22, 19))),
                     terco=((21, 18), (27, 15)), por=((BRASA, 19, 3),)),
                dict(cx=11, olho="feliz", bracos=(((7, 20), (4, 25)), ((15, 20), (20, 22))),
                     terco=((20, 22), (22, 27)), por=((FAGULHA, 25, 9), (FAGULHA_Y, 28, 14), (FAGULHA, 23, 4)))],
    # mão no queixo, olhando para cima, "?" aparece; o terço pendurado na outra mão
    "review": [dict(olho="cima", bracos=(((9, 20), (5, 24)), ((17, 20), (19, 18))), terco=((5, 24), (4, 28))),
               dict(olho="cima", bracos=(((9, 20), (5, 24)), ((17, 20), (19, 18))), terco=((5, 24), (4, 28)),
                    por=((INTERROG_P, 24, 4),)),
               dict(olho="cima", bracos=(((9, 20), (5, 24)), ((17, 20), (19, 18))), terco=((5, 24), (5, 28)),
                    por=((INTERROG, 24, 2),)),
               dict(olho="n", bracos=(((9, 20), (5, 24)), ((17, 20), (19, 18))), terco=((5, 24), (4, 28)),
                    por=((INTERROG, 24, 2),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# grade 17x18 colada 8 à esquerda e 12 acima do topo do hábito (hábito a partir da linha 12, centro na coluna 8;
# cabeça centrada em (9, 7), alto do véu na linha 2): cordão de carvão na cintura com nós de brasa; brasas acesas
# salpicadas no véu, do alto até a barra nas costas (no montinho de cinza do `failed` elas sobem soltas como
# fagulhas, e o cordão fica caído na cinza)
_CORDAO = [
    "KKKKKKKKKKK",
    "dQdOdQdQdOd",
    "KKKKKKKKKKK",
]
_BRASA_P = ["YO", "Oo"]


def _extra(pecas, w=17, h=18):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != "." and 0 <= y + dy < h and 0 <= x + dx < w:
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CORDAO = _extra(((_CORDAO, 3, 15),))
CORDAO_BRASAS = _extra(((_BRASA_P, 7, 3), (_BRASA_P, 4, 6), (_BRASA_P, 4, 11), (["Y"], 6, 9), (["O"], 11, 1),
                        (["Y"], 3, 0), (_CORDAO, 3, 15)))
ESTAGIOS = [
    {"title": "Noviça das Cinzas", "floor": 1, "extra": None},
    {"title": "Freira das Cinzas", "floor": 4, "extra": CORDAO},
    {"title": "Abadessa das Cinzas", "floor": 10, "extra": CORDAO_BRASAS},
]
