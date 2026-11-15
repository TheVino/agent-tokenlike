"""Freira das Cinzas, 32 px, olhando para a direita. Uma freirinha baixinha de hábito cinza-cinza (cor de cinza
de lareira), véu escuro arredondado caindo pelas costas e touca branca emoldurando o rosto redondo. O símbolo é o
terço de ossinhos (contas de osso com uma caveirinha na ponta): balança no idle, vira chicote no `running` (a
caveirinha estala no inimigo numa explosão de brasas). No `failed` ela se desfaz em cinza: o hábito esfarela e
sobra um montinho de cinza com brasas, com o véu caído por cima e o terço ao lado.
O tronco e a cabeça andam juntos (só pés e braços mudam), para o cordão e o véu longo dos acréscimos ficarem
sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#16121c", "H": "#aaa3b0", "h": "#7d7688", "V": "#6d6580", "v": "#4c455c", "C": "#efebf2",
    "F": "#f6dccb", "f": "#d8b3a0", "P": "#ff8fae", "L": "#bfe8ff", "d": "#3a3340", "k": "#3a2e3e",
    "W": "#efe6cf", "w": "#c7b993", "Q": "#c3bdc6", "q": "#8d8794", "O": "#ff8a3d", "o": "#c2421e",
    "Y": "#ffd23f", "T": "#8fd8ff", "D": "#8a5a32",
}

HABIT = (3, 4, 4, 5, 5, 6, 6, 7, 7, 7)       # meia-largura do hábito por linha (10 linhas, até o chão)

SKULL = [".KKKK.", "KWWWWK", "KOWWOK", "KWWWWK", ".KwwK.", "..KK.."]   # caveirinha de olhos em brasa
EMBER = [                                       # a caveirinha estala: explosão de brasas
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
FLICKER = [".K.", "KOK", ".K."]
FLICKER_Y = [".K.", "KYK", ".K."]
STREAK = ["QQQ.", ".QQQ", "QQQ."]
SMOKE = [
    "..KKK...",
    ".KQQQK..",
    "KQqQQQK.",
    "KQQQqQK.",
    ".KKQQQK.",
    "...KKK..",
]
SMOKE_S = [".KK.", "KQQK", "KqQK", ".KK."]
GREY = ["Q.", ".q"]                             # flocos de cinza caindo


def _arm(g, a, b, hand=True):
    """Manga larga do hábito de `a` (ombro) a `b` (mão), com a mãozinha de pele na ponta."""
    px = {}
    for x, y in line(*a, *b):
        px[(x, y)] = px[(x, y + 1)] = "h"
    outline_cells(g, px)
    if hand:
        stamp(g, [".KK.", "KFFK", "KFfK", ".KK."], b[0] - 1, b[1] - 1)


def _rosary(g, hand, tip):
    """Terço de ossinhos: contas de osso da mão até a ponta, com a caveirinha pendurada nela."""
    px = {}
    for i, (x, y) in enumerate(line(*hand, *tip)[1:]):    # contas de 2 px, alternando osso claro e escuro
        px[(x, y)] = "W" if i % 3 == 0 else "w"
        if i % 3 == 0:                            # conta de osso 2x2, cordão fininho entre elas
            px[(x + 1, y)] = px[(x, y + 1)] = px[(x + 1, y + 1)] = "W"
    outline_cells(g, px)
    stamp(g, SKULL, tip[0] - 2, tip[1])


def _mound(g, cx, base, phase):
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
    outline_cells(g, px)
    embers = [(cx - 5, base - 1), (cx + 4, base - 2), (cx - 1, base)] if phase == 2 else [(cx + 3, base - 1)]
    for x, y in embers:
        g[y][x] = "O"
        g[y - 1][x] = "o"


def frame(cx=13, base=30, leg=1, eye="n", feet=(0, 0), arms=(), rosary=None, por=(), mound=0, crumbles=False):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 12 acima do topo do hábito).
    `bracos`: ((ombro), (mão)) com o ombro de trás em (cx-4, t+1) e o da frente em (cx+4, t+1);
    `terco`: ((mão), (ponta)) desenhado por cima da mão; `monte`: 1 ou 2 = virou montinho de cinza."""
    g = [["."] * N for _ in range(N)]
    if mound:
        _mound(g, cx, base, mound)
        for s, x, y in por:
            stamp(g, s, x, y)
        return ["".join(l) for l in g], (cx - 8, base - 16)
    t = base - leg - len(HABIT)
    hx, hy = cx + 1, t - 5
    px = {}
    for i, x0 in enumerate((cx - 3, cx + 1)):     # sapatinhos aparecendo embaixo do hábito
        x = x0 + feet[i]
        for y in range(base - leg, base + 1):
            for x1 in range(x, x + 3):
                px[(x1, y)] = "d"
    for r, w in enumerate(HABIT):
        y = t + r
        for x in range(cx - w, cx + w + 1):
            px[(x, y)] = "h" if x <= cx - w + 1 else "H"
        if crumbles and r >= 6:                   # a barra do hábito vira cinza
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
    outline_cells(g, px)
    # rosto: dois olhinhos, bochecha e boquinha
    eyes = {"n": (["K", "K"], ["K", "L"]), "fechado": (["k"], ["k"]), "feliz": ([".", "K"], [".", "K"]),
             "x": (["K.K", ".K.", "K.K"], None), "bravo": (["K", "K"], ["K", "K"]), "cima": (["K"], ["L"]),
             "triste": (["K", "K"], ["K", "K"])}[eye]
    ex, ey = hx, hy
    if eye == "x":                               # olhinhos ">" e "<"
        stamp(g, ["K.", ".K", "K."], ex - 1, ey - 1)
        stamp(g, [".K", "K.", ".K"], ex + 2, ey - 1)
    else:
        stamp(g, eyes[0], ex, ey)
        stamp(g, eyes[1], ex + 2, ey)
    if eye == "feliz":
        g[ey][ex - 1] = g[ey][ex + 1] = g[ey][ex + 3] = "F"
        g[ey][ex], g[ey][ex + 2] = "K", "K"
        g[ey + 1][ex], g[ey + 1][ex + 2] = "F", "F"
    if eye == "bravo":
        g[ey - 1][ex] = g[ey - 1][ex + 2] = "K"
    if eye == "cima":
        g[ey - 1][ex] = g[ey - 1][ex + 2] = "K"
    g[hy + 2][hx + 3] = "P"                       # bochecha
    g[hy + 3][hx + 1] = "f" if eye not in ("x", "triste") else "K"
    if eye == "triste":
        stamp(g, TEAR, hx - 1, hy + 2)
    for a, b in arms:
        _arm(g, a, b)
    if rosary:
        _rosary(g, *rosary)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, t - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=1 -> hábito 19-28 (cx=13), cabeça 9-19 (hx=14, hy=14); ombros em (9, 20) e (17, 20)
_T = ((9, 20), (6, 25))                         # braço de trás solto ao lado
_F = ((17, 20), (20, 22))                       # braço da frente segurando o terço
_SPECS = {
    # parada com o terço pendurado na mão da frente; ele balança de um lado para o outro e ela pisca
    "idle": [dict(arms=(_T, _F), rosary=((20, 22), (21, 27))),
             dict(arms=(_T, _F), rosary=((20, 22), (24, 26))),
             dict(arms=(_T, _F), rosary=((20, 22), (26, 25))),
             dict(eye="fechado", arms=(_T, _F), rosary=((20, 22), (24, 26))),
             dict(arms=(_T, _F), rosary=((20, 22), (21, 27)))],
    # trotando com os sapatinhos alternando e o terço balançando para trás
    "run_r": [dict(feet=(-2, 2), arms=(((9, 20), (5, 23)), ((17, 20), (21, 21))), rosary=((21, 21), (18, 26))),
              dict(base=29, arms=(((9, 20), (6, 22)), ((17, 20), (21, 22))), rosary=((21, 22), (20, 26))),
              dict(feet=(2, -2), arms=(((9, 20), (5, 23)), ((17, 20), (21, 21))), rosary=((21, 21), (18, 26))),
              dict(base=29, arms=(((9, 20), (6, 22)), ((17, 20), (21, 22))), rosary=((21, 22), (20, 26)))],
    # acena alto com a mão da frente; o terço gira pendurado no pulso
    "waving": [dict(eye="feliz", arms=(_T, ((17, 20), (23, 14))), rosary=((23, 14), (26, 18))),
               dict(eye="feliz", arms=(_T, ((17, 20), (21, 10))), rosary=((21, 10), (25, 13))),
               dict(eye="feliz", arms=(_T, ((17, 20), (26, 12))), rosary=((26, 12), (27, 17))),
               dict(eye="feliz", arms=(_T, ((17, 20), (21, 10))), rosary=((21, 10), (25, 13)))],
    # agacha, salta com o terço erguido, desce, pousa
    "jumping": [dict(leg=0, eye="fechado", arms=(((9, 21), (5, 25)), ((17, 21), (21, 24))),
                     rosary=((21, 24), (23, 27))),
                dict(base=28, eye="cima", arms=(((9, 18), (5, 14)), ((17, 18), (22, 12))),
                     rosary=((22, 12), (25, 16))),
                dict(base=26, eye="feliz", arms=(((9, 16), (4, 11)), ((17, 16), (23, 9))),
                     rosary=((23, 9), (26, 13))),
                dict(base=28, arms=(((9, 18), (5, 21)), ((17, 18), (22, 16))), rosary=((22, 16), (24, 21))),
                dict(leg=0, eye="feliz", arms=(((9, 21), (5, 25)), ((17, 21), (21, 24))),
                     rosary=((21, 24), (23, 27)))],
    # desfaz em cinza: chora, o hábito esfarela, vira montinho de cinza com o véu por cima e o terço ao lado
    "failed": [dict(eye="triste", arms=(_T, _F), rosary=((20, 22), (21, 27))),
               dict(eye="x", crumbles=True, arms=(((9, 20), (5, 24)), ((17, 20), (22, 24))),
                    rosary=((22, 24), (25, 27)), por=((GREY, 4, 27), (GREY, 24, 29), (GREY, 7, 30))),
               dict(mound=1, por=((SKULL, 24, 25), (SMOKE, 18, 10), (GREY, 6, 19))),
               dict(mound=2, por=((SKULL, 24, 25), (SMOKE_S, 21, 9), (SMOKE, 18, 4))),
               dict(mound=2, por=((SKULL, 24, 25), (SMOKE_S, 22, 2)))],
    # cochila de cabeça baixa, terço pendurado, "z" subindo
    "waiting": [dict(leg=0, eye="fechado", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29))),
                dict(leg=0, eye="fechado", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29)), por=((Z_S, 24, 7),)),
                dict(leg=0, eye="fechado", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29)), por=((Z_S, 23, 8), (Z_L, 25, 0))),
                dict(leg=0, eye="fechado", arms=(((9, 21), (6, 26)), ((17, 21), (19, 25))),
                     rosary=((19, 25), (20, 29)), por=((Z_L, 25, 0),))],
    # chicotada: ergue o terço para trás no alto, gira para a frente (riscos), a caveirinha estala em brasas
    "running": [dict(cx=11, eye="bravo", arms=(((7, 20), (4, 25)), ((15, 20), (19, 7))),
                     rosary=((19, 7), (9, 1))),
                dict(cx=11, eye="bravo", arms=(((7, 20), (4, 25)), ((15, 20), (21, 17))),
                     rosary=((21, 17), (27, 12)), por=((STREAK, 21, 5),)),
                dict(cx=11, eye="bravo", arms=(((7, 20), (4, 25)), ((15, 20), (22, 19))),
                     rosary=((21, 18), (27, 15)), por=((EMBER, 19, 3),)),
                dict(cx=11, eye="feliz", arms=(((7, 20), (4, 25)), ((15, 20), (20, 22))),
                     rosary=((20, 22), (22, 27)), por=((FLICKER, 25, 9), (FLICKER_Y, 28, 14), (FLICKER, 23, 4)))],
    # mão no queixo, olhando para cima, "?" aparece; o terço pendurado na outra mão
    "review": [dict(eye="cima", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (4, 28))),
               dict(eye="cima", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (4, 28)),
                    por=((QMARK_S, 24, 4),)),
               dict(eye="cima", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (5, 28)),
                    por=((QMARK, 24, 2),)),
               dict(eye="n", arms=(((9, 20), (5, 24)), ((17, 20), (19, 18))), rosary=((5, 24), (4, 28)),
                    por=((QMARK, 24, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 17x18 colada 8 à esquerda e 12 acima do topo do hábito (hábito a partir da linha 12, centro na coluna 8;
# cabeça centrada em (9, 7), alto do véu na linha 2): cordão de carvão na cintura com nós de brasa; brasas acesas
# salpicadas no véu, do alto até a barra nas costas (no montinho de cinza do `failed` elas sobem soltas como
# fagulhas, e o cordão fica caído na cinza)
_CORD = [
    "KKKKKKKKKKK",
    "dQdOdQdQdOd",
    "KKKKKKKKKKK",
]
_EMBER_S = ["YO", "Oo"]


def _extra(pieces, w=17, h=18):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != "." and 0 <= y + dy < h and 0 <= x + dx < w:
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


CORD = _extra(((_CORD, 3, 15),))
CORD_EMBERS = _extra(((_EMBER_S, 7, 3), (_EMBER_S, 4, 6), (_EMBER_S, 4, 11), (["Y"], 6, 9), (["O"], 11, 1),
                        (["Y"], 3, 0), (_CORD, 3, 15)))
STAGES = [
    {"title": "Noviça das Cinzas", "floor": 1, "extra": None},
    {"title": "Freira das Cinzas", "floor": 4, "extra": CORD},
    {"title": "Abadessa das Cinzas", "floor": 10, "extra": CORD_EMBERS},
]
