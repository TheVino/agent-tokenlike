"""Cavaleiro Oco, 32 px, olhando para a direita. Uma armadura vazia: elmo de balde com a fenda do visor escura e,
lá dentro, um único olhinho dourado que espia de um lado para o outro. Peitoral com ombreiras, cinto, grevas,
manoplas em linha grossa e os símbolos: a espada e o escudo com a cruz dourada. No `failed` a armadura desaba
em peças (a espada e o escudo caem no chão, o elmo afunda no monte) e o olhinho foge correndo pelo chão.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, traco

PAL = {
    "K": "#1c1424", "s": "#0d0812", "M": "#a4adbf", "m": "#646c80", "W": "#eef2f8", "S": "#dfe6f2",
    "Y": "#ffd23f", "y": "#8a6a20", "G": "#ffd23f", "g": "#b8860b", "D": "#5a3a24",
    "B": "#3d5a9e", "b": "#28396a", "R": "#c8334a", "r": "#7e1f33", "T": "#8fd8ff",
}

HH = 9                                          # altura do elmo
ELMO = (3, 4, 5, 5, 5, 5, 5, 5, 4)              # meia-largura do elmo por linha

ESCUDO = [
    "KKKKKKKK",
    "KMMMMMMK",
    "KBBGGBBK",
    "KBGGGGBK",
    "KBBGGBBK",
    "KBBGGBbK",
    ".KBGGbK.",
    ".KBBbbK.",
    "..KBbK..",
    "...KK...",
]
ESCUDO_DEITADO = [
    ".KKKKKKKKK.",
    "KMBBBGBBbbK",
    "KMBGGGGGbbK",
    "KMBBBGBBbK.",
    ".KKKKKKKK..",
]
# olhinho que fugiu da armadura, com perninhas (dois passos)
OLHINHO = [[".KKKK.", "KYYWYK", "KYYYYK", ".KKKK.", ".K..K."],
           [".KKKK.", "KYYWYK", "KYYYYK", ".KKKK.", "K....K"]]
BRILHO = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
TALHO = ["KKK.....", "WWWKK...", "KKWWWK..", "..KKWWK.", "....KWWK", ".....KWK", ".....KWK",
         "....KWK."]                                                   # rastro branco do corte em arco
MAO = [".KK.", "KMMK", "KmmK", ".KK."]


def espada(g, punho, ponta):
    """Espada do punho (cabo marrom e pomo dourado) até a ponta, com guarda dourada atravessada."""
    (x0, y0), (x1, y1) = punho, ponta
    dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
    traco(g, (x0 + dx, y0 + dy), ponta, "S")
    traco(g, (x0 - dx, y0 - dy), (x0, y0), "D")
    gx, gy = x0 + 2 * dx, y0 + 2 * dy
    px, py = -dy, dx
    n = 1 if dx and dy else 2                     # guarda diagonal mais curta, para não virar um X
    traco(g, (gx - n * px, gy - n * py), (gx + n * px, gy + n * py), "G")
    traco(g, (x0 + 3 * dx, y0 + 3 * dy), ponta, "S")
    if 0 <= x1 < N and 0 <= y1 < N:
        g[y1][x1] = "W"
    px0, py0 = x0 - 2 * dx, y0 - 2 * dy
    if 0 <= px0 < N and 0 <= py0 < N:
        g[py0][px0] = "G"


def quadro(cx=15, base=30, hr=7, perna=3, lean=0, cai=0, olho=0, bracos=(), espadas=(), por=(), atras=(),
           pes=(0, 0)):
    """Um quadro 32x32 e a âncora do acréscimo (12 à esquerda e 8 acima do topo do elmo).
    `hr`: altura do peitoral; `perna`: altura das grevas; `cai`: quanto o elmo afunda no peitoral;
    `olho`: deslocamento do olhinho na fenda (-2..2) ou "fechado", "cima", "feliz", "bravo", "triste", "x", "fora"."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    cint = base - perna - hr
    ch = cx + lean
    top = cint - HH + cai
    peito = {}
    for r in range(hr):
        y = cint + r
        c = ch - round(lean * r / max(hr - 1, 1))
        m = 6 if r < 2 else (5 if r == hr - 1 else 4)
        for x in range(c - m, c + m + 1):
            if r == hr - 1 and hr > 2:
                cor = "G" if x in (c, c + 1) else "D"            # cinto com fivela
            elif x >= c + m - 1:
                cor = "m"
            elif r == 1 and x in (c - 5, c + 5):
                cor = "m"                                          # junta da ombreira
            elif r in (2, 3) and x == c - 2:
                cor = "W"
            else:
                cor = "M"
            peito[(x, y)] = cor
    perna_px = {}
    for px, dx in ((cx - 3, pes[0]), (cx + 1, pes[1])):
        for y in range(base - perna, base):
            perna_px[(px + dx, y)] = "M"
            perna_px[(px + dx + 1, y)] = "m"
        for x in range(px + dx - 1, px + dx + 2):
            perna_px[(x, base)] = "m"
    elmo = {}
    for r, w in enumerate(ELMO):
        for x in range(ch - w, ch + w + 1):
            if r == HH - 1 or x >= ch + w - 1 and r > 0:
                cor = "m"
            elif r in (1, 2) and x == ch - 3:
                cor = "W"
            else:
                cor = "M"
            elmo[(x, top + r)] = cor
    corpo = {**perna_px, **peito, **elmo}
    for (x, y), c in corpo.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c
    for x, y in corpo:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in corpo and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # fenda do visor (3 linhas escuras) e o olhinho lá dentro
    for y in range(top + 3, top + 6):
        for x in range(ch - 3, ch + 5):
            g[y][x] = "s"
    for x in (ch - 1, ch + 2):                                     # rebites
        g[top + 7][x] = "K"
    ex, ey = ch, top + 4
    if isinstance(olho, int):
        carimbar(g, ["YW", "YY"], ex + olho, ey)
    elif olho == "fechado":
        carimbar(g, ["yy"], ex, ey + 1)
    elif olho == "cima":
        carimbar(g, ["YW", "YY"], ex + 1, ey - 1)
    elif olho == "feliz":
        carimbar(g, [".Y.", "Y.Y"], ex, ey)
    elif olho == "bravo":
        carimbar(g, ["sYW", "YYY"], ex, ey)
    elif olho == "triste":
        carimbar(g, ["Ys", "YY"], ex, ey + 1)
    elif olho == "x":
        carimbar(g, ["Y.Y", ".Y.", "Y.Y"], ex, ey - 1)
    for a, b in bracos:
        x, y = a
        while (x, y) in corpo:             # o braço sai da beirada do corpo, sem riscar o peitoral
            x += 1 if x >= ch else -1
        traco(g, (x, y), b, "M")
        carimbar(g, MAO, b[0] - 1, b[1] - 1)
    for punho, ponta in espadas:
        espada(g, punho, ponta)
        carimbar(g, MAO, punho[0] - 1, punho[1] - 1)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (ch - 12, top - 8)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, hr=7, perna=3 -> peitoral 20-26, grevas 27-29, pés 30, elmo 11-19; ombros em (cx±6, 21)
_E = ((9, 22), (6, 25))                 # braço de trás segurando o escudo ao lado
_SPECS = {
    # parado com a espada fincada no chão; o olhinho espia pelo visor de um lado para o outro e pisca
    "idle": [dict(olho=0, bracos=(_E, ((21, 22), (24, 21))), espadas=(((24, 21), (24, 30)),),
                  por=((ESCUDO, 1, 21),)),
             dict(olho=2, bracos=(_E, ((21, 22), (24, 21))), espadas=(((24, 21), (24, 30)),),
                  por=((ESCUDO, 1, 21),)),
             dict(olho=2, bracos=(_E, ((21, 22), (24, 21))), espadas=(((24, 21), (24, 30)),),
                  por=((ESCUDO, 1, 21),)),
             dict(olho=-2, bracos=(_E, ((21, 22), (24, 21))), espadas=(((24, 21), (24, 30)),),
                  por=((ESCUDO, 1, 21),)),
             dict(olho="fechado", bracos=(_E, ((21, 22), (24, 21))), espadas=(((24, 21), (24, 30)),),
                  por=((ESCUDO, 1, 21),))],
    # corre inclinado, espada em riste para a frente, escudo nas costas balançando
    "run_r": [dict(lean=2, olho=2, pes=(-2, 2), bracos=(((11, 22), (6, 25)), ((22, 22), (24, 23))),
                   espadas=(((24, 23), (31, 17)),), por=((ESCUDO, 0, 20),)),
              dict(lean=3, base=29, olho=2, bracos=(((12, 21), (7, 23)), ((23, 21), (25, 22))),
                   espadas=(((25, 22), (31, 15)),), por=((ESCUDO, 1, 17),)),
              dict(lean=2, olho=2, pes=(2, -2), bracos=(((11, 22), (6, 25)), ((22, 22), (24, 23))),
                   espadas=(((24, 23), (31, 17)),), por=((ESCUDO, 0, 21),)),
              dict(lean=3, base=29, olho=2, bracos=(((12, 21), (7, 23)), ((23, 21), (25, 22))),
                   espadas=(((25, 22), (31, 15)),), por=((ESCUDO, 1, 18),))],
    # acena alto com a manopla; o escudo fica no outro braço
    "waving": [dict(olho="feliz", bracos=(_E, ((21, 22), (26, 17))), por=((ESCUDO, 1, 21),)),
               dict(olho="feliz", bracos=(_E, ((21, 22), (27, 13))), por=((ESCUDO, 1, 21),)),
               dict(olho="feliz", bracos=(_E, ((21, 22), (29, 15))), por=((ESCUDO, 1, 21),)),
               dict(olho="feliz", bracos=(_E, ((21, 22), (27, 13))), por=((ESCUDO, 1, 21),))],
    # agacha (armadura encolhe), salta com a espada para o alto, cai, pousa
    "jumping": [dict(hr=6, perna=2, olho="fechado", bracos=(((9, 24), (5, 28)),), espadas=(((24, 26), (30, 29)),)),
                dict(base=28, olho="cima", bracos=(((9, 20), (5, 15)),), espadas=(((25, 15), (29, 6)),)),
                dict(base=27, olho="feliz", bracos=(((9, 19), (4, 13)),), espadas=(((25, 13), (28, 3)),)),
                dict(base=28, olho=0, bracos=(((9, 20), (5, 23)),), espadas=(((25, 22), (30, 17)),)),
                dict(hr=6, olho="feliz", bracos=(((9, 23), (5, 27)),), espadas=(((24, 25), (30, 28)),))],
    # desaba: a espada cai, a armadura afunda peça por peça, o elmo cai no monte e o olhinho foge correndo
    "failed": [dict(olho="triste", bracos=(_E, ((21, 22), (23, 27))), por=((ESCUDO, 1, 21), (LAGRIMA, 16, 17))),
               dict(olho="triste", hr=6, perna=2, bracos=(((9, 22), (7, 28)), ((21, 22), (23, 28))),
                    espadas=(((20, 29), (31, 29)),), por=((ESCUDO, 0, 21),)),
               dict(olho="x", hr=5, perna=1, cai=1, bracos=(((9, 25), (6, 29)), ((21, 25), (24, 29))),
                    espadas=(((20, 29), (31, 29)),), por=((ESCUDO_DEITADO, 0, 26),)),
               dict(olho="fora", hr=3, perna=1, cai=2, espadas=(((20, 29), (31, 29)),),
                    por=((ESCUDO_DEITADO, 0, 26), (OLHINHO[0], 24, 22))),
               dict(olho="fora", hr=3, perna=0, cai=3, espadas=(((20, 29), (31, 29)),),
                    por=((ESCUDO_DEITADO, 0, 26), (OLHINHO[1], 26, 22)))],
    # cochila apoiado na espada fincada, o olhinho apagado, "z" subindo
    "waiting": [dict(hr=6, cai=1, olho="fechado", bracos=(_E, ((21, 23), (24, 23))),
                     espadas=(((24, 23), (24, 30)),), por=((ESCUDO, 1, 22),)),
                dict(hr=6, cai=1, olho="fechado", bracos=(_E, ((21, 23), (24, 23))),
                     espadas=(((24, 23), (24, 30)),), por=((ESCUDO, 1, 22), (Z_P, 25, 8))),
                dict(hr=6, cai=1, olho="fechado", bracos=(_E, ((21, 23), (24, 23))),
                     espadas=(((24, 23), (24, 30)),), por=((ESCUDO, 1, 22), (Z_P, 24, 8), (Z_G, 26, 1))),
                dict(hr=6, cai=1, olho="fechado", bracos=(_E, ((21, 23), (24, 23))),
                     espadas=(((24, 23), (24, 30)),), por=((ESCUDO, 1, 22), (Z_G, 26, 1)))],
    # golpe: ergue a espada, corta para baixo (rastro branco), empurra o escudo (baque), estoca com brilho
    "running": [dict(cx=14, olho="bravo", bracos=(((8, 22), (5, 25)),), espadas=(((23, 14), (29, 3)),),
                     por=((ESCUDO, 0, 21),)),
                dict(cx=14, lean=1, olho="bravo", bracos=(((9, 22), (6, 25)),), espadas=(((24, 21), (31, 28)),),
                     por=((ESCUDO, 1, 21), (TALHO, 23, 8))),
                dict(cx=14, lean=2, olho="bravo", bracos=(((22, 22), (25, 21)),),
                     espadas=(((10, 25), (6, 30)),), por=((ESCUDO, 23, 16), (BRILHO, 25, 7))),
                dict(cx=14, lean=2, olho="bravo", bracos=(((10, 22), (7, 25)),), espadas=(((24, 21), (31, 21)),),
                     por=((ESCUDO, 1, 20), (BRILHO, 25, 13)))],
    # manopla no queixo do elmo, olhinho olhando para cima, "?" aparece
    "review": [dict(olho="cima", bracos=(_E, ((21, 22), (22, 20))), por=((ESCUDO, 1, 21),)),
               dict(olho="cima", bracos=(_E, ((21, 22), (22, 20))), por=((ESCUDO, 1, 21), (INTERROG_P, 25, 4))),
               dict(olho="cima", bracos=(_E, ((21, 22), (22, 20))), por=((ESCUDO, 1, 21), (INTERROG, 25, 2))),
               dict(olho=2, bracos=(_E, ((21, 22), (22, 20))), por=((ESCUDO, 1, 21), (INTERROG, 25, 2)))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# grade 17x10 colada 12 à esquerda e 8 acima do topo do elmo (topo do elmo na linha 8, centro na coluna 12):
# pluma vermelha presa no alto do elmo, caindo para trás; o estandarte azul de cruz dourada espeta das costas
_PLUMA = [
    "....KKKK.",
    "..KKRRRRK",
    ".KRRRRrRK",
    "KRRrrKKRK",
    "KRrK.KGGK",
    ".KK..KGK.",
]
_ESTANDARTE = [
    ".....KGK",
    "KKKKKKDK",
    "KBBGBKDK",
    "KBGGGKDK",
    "KBBGBKDK",
    "KBBGBKDK",
    ".KBbKKDK",
    "..KK.KDK",
    ".....KDK",
    ".....KDK",
]


def _extra(pecas, w=17, h=10):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


PLUMA = _extra(((_PLUMA, 7, 2),))
PLUMA_ESTANDARTE = _extra(((_ESTANDARTE, 0, 0), (_PLUMA, 7, 2)))
ESTAGIOS = [
    {"title": "Armadura Vazia", "floor": 1, "extra": None},
    {"title": "Cavaleiro Oco", "floor": 4, "extra": PLUMA},
    {"title": "Paladino Oco", "floor": 10, "extra": PLUMA_ESTANDARTE},
]
