"""Inquisidor, 32 px, olhando para a direita. Um noviço pequenino de capuz pontudo: o rosto é uma sombra com
dois olhos que brilham, a túnica alarga até os pés, cordão na cintura, braços de manga em linha grossa e os
símbolos: o livro trancado (cadeado dourado) e o sino. No `failed` a túnica afunda, o capuz murcha para a frente
e o livro escorrega da mão e tomba no chão.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, trait

PAL = {
    "K": "#1c1424", "B": "#1c1424", "s": "#2e2140", "R": "#7a2f45", "r": "#521d31",
    "Y": "#ffd23f", "W": "#ffffff", "C": "#f1d3b3", "A": "#d9b36a", "a": "#9a743a",
    "M": "#6b4226", "m": "#43281a", "p": "#efe3cf", "G": "#ffd23f", "g": "#b8860b",
    "D": "#3a2a20", "P": "#ff9ec4", "T": "#8fd8ff", "S": "#e8e0ff",
}

HH = 10                                       # altura do capuz (fixa: a cintura fica sempre 10 abaixo do topo)
HOOD = (1, 2, 3, 4, 5, 5, 6, 6, 6, 6)        # meia-largura do capuz por linha
FACE = {3: 2, 4: 3, 5: 4, 6: 4, 7: 3, 8: 2}  # linha do capuz -> meia-largura da abertura do rosto

# livro trancado em pé (na mão), inclinado (escorregando) e deitado (tombado no chão)
BOOK = [
    "KKKKKKKK.",
    "KMMMMMMpK",
    "KMmMMMMpK",
    "KGGGGGGGK",
    "KGgKKgGGK",
    "KGGKKGGGK",
    "KMmMMMMpK",
    "KMMMMMMpK",
    "KKKKKKKKK",
]
BOOK_TILT = [
    "...KKK....",
    "..KMMMKK..",
    ".KMMMMMpK.",
    "KGGMMMMMpK",
    "KgKGGMMMpK",
    ".KKgGGGMMK",
    "..KMMgGGGK",
    "...KMMMKK.",
    "....KKK...",
]
BOOK_FLAT = [
    "KKKKKKKKKKK",
    "KMMMGGGMMMK",
    "KMmMGKGMmMK",
    "KpppGGGpppK",
    "KKKKKKKKKKK",
]
# sino de mão: inclinado para trás, reto, inclinado para a frente (o cabo fica em cima)
BELL = [
    ["..KK....", ".KAAK...", "..KKK...", ".KGGGK..", ".KGGGgK.", "KGGGGgK.", "KGGGGGgK", ".KKKKKKK", "...KgK.."],
    ["...KK...", "..KAAK..", "...KK...", "..KGGK..", ".KGGGgK.", ".KGGGgK.", "KGGGGGgK", "KKKKKKKK", "...KgK.."],
    ["....KK..", "...KAAK.", "...KKK..", "..KGGGK.", ".KGGGGK.", ".KGGGGGK", "KGGGGGgK", "KKKKKKK.", "..KgK..."],
]
BELL_L = [
    "....KKK....",
    "...KAAAK...",
    "....KKK....",
    "...KGGGK...",
    "..KGGGGgK..",
    ".KGGWGGGgK.",
    ".KGWGGGGgK.",
    ".KGGGGGGgK.",
    "KGGGGGGGGgK",
    "KKKKKKKKKKK",
    "....KgK....",
    ".....K.....",
]
# ondas do sino e estrelinha do impacto do livro
WAVE_S = ["KS.", ".KS", ".KS", ".KS", "KS."]
WAVE_L = ["KS...", ".KS..", "..KS.", "..KS.", "..KS.", ".KS..", "KS..."]
THUD = ["...K...", ".K.Y.K.", "..KYK..", "KYYWYYK", "..KYK..", ".K.Y.K.", "...K..."]
HAND = [".KKK.", "KCCCK", "KCCCK", ".KKK."]


def frame(cx=15, base=30, hr=8, lean=0, tip=-1, eyes="normal", mouth="", arms=(), por=(), behind=(),
           feet=(0, 0)):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda e 7 acima do topo do capuz).
    `hr`: altura da túnica (a cintura fica em base - hr); `ponta`: para onde tomba a ponta do capuz."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    cint = base - hr
    ch = cx + lean
    top = cint - HH
    tunic = set()
    for y in range(cint, base):
        t = (y - cint) / max(hr - 1, 1)
        c = ch - round(lean * t)
        m = 5 + round(2 * t)
        tunic |= {(x, y) for x in range(c - m, c + m + 1)}
    capuz = set()
    for r, w in enumerate(HOOD):
        c = ch + (round(tip * (4 - r) / 4) if r < 4 else 0)
        capuz |= {(x, top + r) for x in range(c - w, c + w + 1)}
    capuz.add((ch + tip + (tip > 0) - (tip < 0), top - 1))
    foot = {(x, base) for px, dx in ((cx - 4, feet[0]), (cx + 2, feet[1])) for x in range(px + dx, px + dx + 3)}
    body = tunic | capuz | foot
    for x, y in body:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = "D" if (x, y) in foot else ("r" if (x + 1, y) not in body or y >= base - 1 else "R")
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # cordão na cintura com o nó caindo à esquerda
    for x in range(ch - 5, ch + 6):
        g[cint][x] = "A" if x % 2 else "a"
    for y in (cint + 1, cint + 2, cint + 3):
        if y < base:
            g[y][ch - 3] = "A"
    # rosto: abertura escura no capuz com olhos que brilham
    fc = ch + 1
    for r, w in FACE.items():
        for x in range(fc - w, fc + w + 1):
            g[top + r][x] = "s"
    ey = top + 5
    for x in (fc - 3, fc + 2):
        if eyes == "fechado":
            stamp(g, ["YY"], x, ey + 1)
        elif eyes == "feliz":
            stamp(g, [".YY.", "Y..Y"], x - 1, ey)
        elif eyes == "x":
            stamp(g, ["Y.Y", ".Y.", "Y.Y"], x - (x > fc), ey - 1)
        elif eyes == "bravo":
            stamp(g, ["YW", "YY"], x, ey)
            g[ey][x + 1 if x < fc else x] = "s"
        elif eyes == "triste":
            stamp(g, ["WY", "YY"], x, ey)
            g[ey][x if x < fc else x + 1] = "s"
        elif eyes == "cima":
            stamp(g, ["WY", "YY"], x + 1, ey - 1)
        else:
            stamp(g, ["WY", "YY"], x, ey)
    if eyes not in ("fechado", "x"):
        g[ey + 2][fc - 4] = g[ey + 2][fc + 4] = "P"
    if mouth == "o":
        g[ey + 2][fc] = "Y"
    elif mouth == "grito":
        g[ey + 2][fc] = g[ey + 2][fc + 1] = "Y"
    for a, b in arms:
        x, y = a
        while (x, y) in body:             # a manga sai da beirada do corpo, sem riscar a túnica
            x += 1 if x >= ch else -1
        trait(g, (x, y), b, "R")
        stamp(g, HAND, b[0] - 2, b[1] - 1)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (ch - 8, top - 7)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, hr=8 -> cintura em 22, capuz de 12 a 21; túnica na cintura de cx-5 a cx+5 (cx=15: 10 e 20)
_SPECS = {
    # parado, balança o sino de mão para lá e para cá, pisca
    "idle": [dict(arms=(((20, 23), (24, 21)), ((10, 23), (7, 26))), por=((BELL[0], 21, 21),)),
             dict(arms=(((20, 23), (24, 21)), ((10, 23), (7, 27))), por=((BELL[1], 21, 21),)),
             dict(arms=(((20, 23), (24, 21)), ((10, 23), (7, 26))), por=((BELL[2], 21, 21),)),
             dict(eyes="fechado", arms=(((20, 23), (24, 21)), ((10, 23), (7, 27))), por=((BELL[1], 21, 21),))],
    # corre inclinado, ponta do capuz voando para trás, braço balançando com o livro
    "run_r": [dict(lean=2, tip=-3, feet=(-2, 2), arms=(((12, 24), (6, 27)),), por=((BOOK, 1, 23),)),
              dict(lean=3, base=29, tip=-4, arms=(((12, 23), (7, 22)),), por=((BOOK, 2, 18),)),
              dict(lean=2, tip=-3, feet=(2, -2), arms=(((12, 24), (6, 26)),), por=((BOOK, 1, 22),)),
              dict(lean=3, base=29, tip=-4, arms=(((12, 23), (8, 20)),), por=((BOOK, 3, 16),))],
    # acena alto com a mão direita, o livro abraçado no outro braço
    "waving": [dict(eyes="feliz", arms=(((20, 23), (26, 18)), ((10, 23), (8, 26))), por=((BOOK, 3, 23),)),
               dict(eyes="feliz", tip=-2, arms=(((20, 23), (27, 13)), ((10, 23), (8, 26))),
                    por=((BOOK, 3, 23),)),
               dict(eyes="feliz", tip=-3, arms=(((20, 23), (29, 15)), ((10, 23), (8, 26))),
                    por=((BOOK, 3, 23),)),
               dict(eyes="feliz", tip=-2, arms=(((20, 23), (27, 13)), ((10, 23), (8, 26))),
                    por=((BOOK, 3, 23),))],
    # agacha (túnica curta), salta com os braços para cima, cai, pousa
    "jumping": [dict(hr=6, eyes="fechado", tip=-1, arms=(((20, 25), (24, 28)), ((10, 25), (6, 28)))),
                dict(base=28, hr=8, tip=-2, arms=(((20, 21), (25, 16)), ((10, 21), (5, 16)))),
                dict(base=26, hr=7, tip=-3, eyes="feliz", mouth="o",
                     arms=(((20, 20), (26, 13)), ((10, 20), (4, 13)))),
                dict(base=28, hr=8, tip=-2, arms=(((20, 21), (25, 23)), ((10, 21), (5, 23)))),
                dict(hr=7, eyes="feliz", tip=-1, arms=(((20, 24), (24, 27)), ((10, 24), (6, 27))))],
    # triste, a túnica afunda, o capuz murcha para a frente, o livro escorrega e tomba no chão
    "failed": [dict(eyes="triste", arms=(((20, 23), (24, 25)), ((10, 23), (7, 27))),
                    por=((BOOK, 23, 21), (TEAR, 13, 19))),
               dict(eyes="triste", hr=7, tip=1, arms=(((20, 24), (23, 28)), ((10, 24), (7, 28))),
                    por=((BOOK_TILT, 21, 22),)),
               dict(eyes="triste", hr=6, tip=2, arms=(((20, 26), (22, 29)), ((10, 26), (8, 29))),
                    por=((BOOK_FLAT, 21, 26), (TEAR, 13, 22))),
               dict(eyes="x", hr=5, tip=3, lean=1, por=((BOOK_FLAT, 21, 26),)),
               dict(eyes="x", hr=4, tip=4, lean=1, por=((BOOK_FLAT, 21, 26),))],
    # cochila com o livro deitado no chão ao lado (no colo o sino da cintura o cobria), capuz caindo para a frente, "z" subindo
    "waiting": [dict(hr=7, eyes="fechado", tip=2, arms=(((20, 24), (21, 26)), ((10, 24), (11, 26))),
                     behind=(), por=((BOOK_FLAT, 20, 27),)),
                dict(hr=7, eyes="fechado", tip=3, arms=(((20, 24), (21, 26)), ((10, 24), (11, 26))),
                     por=((BOOK_FLAT, 20, 27), (Z_S, 24, 6))),
                dict(hr=7, eyes="fechado", tip=3, arms=(((20, 24), (21, 26)), ((10, 24), (11, 26))),
                     por=((BOOK_FLAT, 20, 27), (Z_S, 23, 6), (Z_L, 26, 0))),
                dict(hr=7, eyes="fechado", tip=2, arms=(((20, 24), (21, 26)), ((10, 24), (11, 26))),
                     por=((BOOK_FLAT, 20, 27), (Z_L, 26, 0)))],
    # golpe: ergue o livro trancado, bate com tudo (baque), depois toca o sino grande e as ondas se espalham
    "running": [dict(cx=13, lean=-2, tip=-2, eyes="bravo", arms=(((9, 23), (5, 15)),), por=((BOOK, 1, 6),)),
                dict(cx=14, lean=2, tip=-3, eyes="bravo", mouth="grito", arms=(((19, 23), (24, 22)),),
                     por=((BOOK, 22, 18), (THUD, 25, 11))),
                dict(cx=14, lean=1, tip=-2, eyes="bravo", arms=(((19, 23), (23, 19)),),
                     por=((BELL_L, 19, 8), (WAVE_S, 30, 10))),
                dict(cx=14, lean=1, tip=-1, eyes="bravo", mouth="grito", arms=(((19, 23), (23, 19)),),
                     por=((BELL_L, 19, 8), (WAVE_S, 29, 9), (WAVE_L, 27, 18)))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=13, eyes="cima", arms=(((18, 26), (20, 21)),)),
               dict(cx=13, eyes="cima", arms=(((18, 26), (20, 21)),), por=((QMARK_S, 24, 4),)),
               dict(cx=13, eyes="cima", arms=(((18, 26), (20, 21)),), por=((QMARK, 24, 2),)),
               dict(cx=13, eyes="normal", arms=(((18, 26), (20, 21)),), por=((QMARK, 24, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 17x24 colada 8 à esquerda e 7 acima do topo do capuz: mitra nas linhas 0-8 (assenta nas 2 primeiras
# linhas do capuz) e o sino pendurado no cordão da cintura na linha 17 (topo do capuz + 10)
_BELL_BAND = ["..KK..", ".KAAK.", ".KGGK.", "KGGGgK", "KGGGgK", "KKKKKK", "..Kg.."]
_MITRE = [
    "....K....",
    "...KpK...",
    "..KpppK..",
    "..KpGpK..",
    ".KpGKGpK.",
    ".KppKppK.",
    ".KpppppK.",
    "KGGGGGGGK",
    "KgGgGgGgK",
    "KKKKKKKKK",
]


def _extra(pieces, w=17, h=24):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BELL_BAND = _extra(((_BELL_BAND, 6, 17),))
MITRE_BELL = _extra(((_BELL_BAND, 6, 17), (_MITRE, 4, 0)))
STAGES = [
    {"title": "Noviço", "floor": 1, "extra": None},
    {"title": "Inquisidor", "floor": 4, "extra": BELL_BAND},
    {"title": "Grão-Inquisidor", "floor": 10, "extra": MITRE_BELL},
]
