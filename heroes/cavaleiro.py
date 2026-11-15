"""Cavaleiro Oco, 32 px, olhando para a direita. Uma armadura vazia: elmo de balde com a fenda do visor escura e,
lá dentro, um único olhinho dourado que espia de um lado para o outro. Peitoral com ombreiras, cinto, grevas,
manoplas em linha grossa e os símbolos: a espada e o escudo com a cruz dourada. No `failed` a armadura desaba
em peças (a espada e o escudo caem no chão, o elmo afunda no monte) e o olhinho foge correndo pelo chão.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, trait

PAL = {
    "K": "#1c1424", "s": "#0d0812", "M": "#a4adbf", "m": "#646c80", "W": "#eef2f8", "S": "#dfe6f2",
    "Y": "#ffd23f", "y": "#8a6a20", "G": "#ffd23f", "g": "#b8860b", "D": "#5a3a24",
    "B": "#3d5a9e", "b": "#28396a", "R": "#c8334a", "r": "#7e1f33", "T": "#8fd8ff",
}

HH = 9                                          # altura do elmo
HELM = (3, 4, 5, 5, 5, 5, 5, 5, 4)              # meia-largura do elmo por linha

SHIELD = [
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
SHIELD_FLAT = [
    ".KKKKKKKKK.",
    "KMBBBGBBbbK",
    "KMBGGGGGbbK",
    "KMBBBGBBbK.",
    ".KKKKKKKK..",
]
# olhinho que fugiu da armadura, com perninhas (dois passos)
EYE_TINY = [[".KKKK.", "KYYWYK", "KYYYYK", ".KKKK.", ".K..K."],
           [".KKKK.", "KYYWYK", "KYYYYK", ".KKKK.", "K....K"]]
SHINE = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
GASH = ["KKK.....", "WWWKK...", "KKWWWK..", "..KKWWK.", "....KWWK", ".....KWK", ".....KWK",
         "....KWK."]                                                   # rastro branco do corte em arco
HAND = [".KK.", "KMMK", "KmmK", ".KK."]


def sword(g, fist, tip):
    """Espada do punho (cabo marrom e pomo dourado) até a ponta, com guarda dourada atravessada."""
    (x0, y0), (x1, y1) = fist, tip
    dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
    trait(g, (x0 + dx, y0 + dy), tip, "S")
    trait(g, (x0 - dx, y0 - dy), (x0, y0), "D")
    gx, gy = x0 + 2 * dx, y0 + 2 * dy
    px, py = -dy, dx
    n = 1 if dx and dy else 2                     # guarda diagonal mais curta, para não virar um X
    trait(g, (gx - n * px, gy - n * py), (gx + n * px, gy + n * py), "G")
    trait(g, (x0 + 3 * dx, y0 + 3 * dy), tip, "S")
    if 0 <= x1 < N and 0 <= y1 < N:
        g[y1][x1] = "W"
    px0, py0 = x0 - 2 * dx, y0 - 2 * dy
    if 0 <= px0 < N and 0 <= py0 < N:
        g[py0][px0] = "G"


def frame(cx=15, base=30, hr=7, leg=3, lean=0, falls=0, eye=0, arms=(), swords=(), por=(), behind=(),
           feet=(0, 0)):
    """Um quadro 32x32 e a âncora do acréscimo (12 à esquerda e 8 acima do topo do elmo).
    `hr`: altura do peitoral; `perna`: altura das grevas; `cai`: quanto o elmo afunda no peitoral;
    `olho`: deslocamento do olhinho na fenda (-2..2) ou "fechado", "cima", "feliz", "bravo", "triste", "x", "fora"."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    cint = base - leg - hr
    ch = cx + lean
    top = cint - HH + falls
    chest = {}
    for r in range(hr):
        y = cint + r
        c = ch - round(lean * r / max(hr - 1, 1))
        m = 6 if r < 2 else (5 if r == hr - 1 else 4)
        for x in range(c - m, c + m + 1):
            if r == hr - 1 and hr > 2:
                color = "G" if x in (c, c + 1) else "D"            # cinto com fivela
            elif x >= c + m - 1:
                color = "m"
            elif r == 1 and x in (c - 5, c + 5):
                color = "m"                                          # junta da ombreira
            elif r in (2, 3) and x == c - 2:
                color = "W"
            else:
                color = "M"
            chest[(x, y)] = color
    leg_px = {}
    for px, dx in ((cx - 3, feet[0]), (cx + 1, feet[1])):
        for y in range(base - leg, base):
            leg_px[(px + dx, y)] = "M"
            leg_px[(px + dx + 1, y)] = "m"
        for x in range(px + dx - 1, px + dx + 2):
            leg_px[(x, base)] = "m"
    helm = {}
    for r, w in enumerate(HELM):
        for x in range(ch - w, ch + w + 1):
            if r == HH - 1 or x >= ch + w - 1 and r > 0:
                color = "m"
            elif r in (1, 2) and x == ch - 3:
                color = "W"
            else:
                color = "M"
            helm[(x, top + r)] = color
    body = {**leg_px, **chest, **helm}
    for (x, y), c in body.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # fenda do visor (3 linhas escuras) e o olhinho lá dentro
    for y in range(top + 3, top + 6):
        for x in range(ch - 3, ch + 5):
            g[y][x] = "s"
    for x in (ch - 1, ch + 2):                                     # rebites
        g[top + 7][x] = "K"
    ex, ey = ch, top + 4
    if isinstance(eye, int):
        stamp(g, ["YW", "YY"], ex + eye, ey)
    elif eye == "fechado":
        stamp(g, ["yy"], ex, ey + 1)
    elif eye == "cima":
        stamp(g, ["YW", "YY"], ex + 1, ey - 1)
    elif eye == "feliz":
        stamp(g, [".Y.", "Y.Y"], ex, ey)
    elif eye == "bravo":
        stamp(g, ["sYW", "YYY"], ex, ey)
    elif eye == "triste":
        stamp(g, ["Ys", "YY"], ex, ey + 1)
    elif eye == "x":
        stamp(g, ["Y.Y", ".Y.", "Y.Y"], ex, ey - 1)
    for a, b in arms:
        x, y = a
        while (x, y) in body:             # o braço sai da beirada do corpo, sem riscar o peitoral
            x += 1 if x >= ch else -1
        trait(g, (x, y), b, "M")
        stamp(g, HAND, b[0] - 1, b[1] - 1)
    for fist, tip in swords:
        sword(g, fist, tip)
        stamp(g, HAND, fist[0] - 1, fist[1] - 1)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (ch - 12, top - 8)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, hr=7, perna=3 -> peitoral 20-26, grevas 27-29, pés 30, elmo 11-19; ombros em (cx±6, 21)
_E = ((9, 22), (6, 25))                 # braço de trás segurando o escudo ao lado
_SPECS = {
    # parado com a espada fincada no chão; o olhinho espia pelo visor de um lado para o outro e pisca
    "idle": [dict(eye=0, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye=2, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye=2, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye=-2, arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),)),
             dict(eye="fechado", arms=(_E, ((21, 22), (24, 21))), swords=(((24, 21), (24, 30)),),
                  por=((SHIELD, 1, 21),))],
    # corre inclinado, espada em riste para a frente, escudo nas costas balançando
    "run_r": [dict(lean=2, eye=2, feet=(-2, 2), arms=(((11, 22), (6, 25)), ((22, 22), (24, 23))),
                   swords=(((24, 23), (31, 17)),), por=((SHIELD, 0, 20),)),
              dict(lean=3, base=29, eye=2, arms=(((12, 21), (7, 23)), ((23, 21), (25, 22))),
                   swords=(((25, 22), (31, 15)),), por=((SHIELD, 1, 17),)),
              dict(lean=2, eye=2, feet=(2, -2), arms=(((11, 22), (6, 25)), ((22, 22), (24, 23))),
                   swords=(((24, 23), (31, 17)),), por=((SHIELD, 0, 21),)),
              dict(lean=3, base=29, eye=2, arms=(((12, 21), (7, 23)), ((23, 21), (25, 22))),
                   swords=(((25, 22), (31, 15)),), por=((SHIELD, 1, 18),))],
    # acena alto com a manopla; o escudo fica no outro braço
    "waving": [dict(eye="feliz", arms=(_E, ((21, 22), (26, 17))), por=((SHIELD, 1, 21),)),
               dict(eye="feliz", arms=(_E, ((21, 22), (27, 13))), por=((SHIELD, 1, 21),)),
               dict(eye="feliz", arms=(_E, ((21, 22), (29, 15))), por=((SHIELD, 1, 21),)),
               dict(eye="feliz", arms=(_E, ((21, 22), (27, 13))), por=((SHIELD, 1, 21),))],
    # agacha (armadura encolhe), salta com a espada para o alto, cai, pousa
    "jumping": [dict(hr=6, leg=2, eye="fechado", arms=(((9, 24), (5, 28)),), swords=(((24, 26), (30, 29)),)),
                dict(base=28, eye="cima", arms=(((9, 20), (5, 15)),), swords=(((25, 15), (29, 6)),)),
                dict(base=27, eye="feliz", arms=(((9, 19), (4, 13)),), swords=(((25, 13), (28, 3)),)),
                dict(base=28, eye=0, arms=(((9, 20), (5, 23)),), swords=(((25, 22), (30, 17)),)),
                dict(hr=6, eye="feliz", arms=(((9, 23), (5, 27)),), swords=(((24, 25), (30, 28)),))],
    # desaba: a espada cai, a armadura afunda peça por peça, o elmo cai no monte e o olhinho foge correndo
    "failed": [dict(eye="triste", arms=(_E, ((21, 22), (23, 27))), por=((SHIELD, 1, 21), (TEAR, 16, 17))),
               dict(eye="triste", hr=6, leg=2, arms=(((9, 22), (7, 28)), ((21, 22), (23, 28))),
                    swords=(((20, 29), (31, 29)),), por=((SHIELD, 0, 21),)),
               dict(eye="x", hr=5, leg=1, falls=1, arms=(((9, 25), (6, 29)), ((21, 25), (24, 29))),
                    swords=(((20, 29), (31, 29)),), por=((SHIELD_FLAT, 0, 26),)),
               dict(eye="fora", hr=3, leg=1, falls=2, swords=(((20, 29), (31, 29)),),
                    por=((SHIELD_FLAT, 0, 26), (EYE_TINY[0], 24, 22))),
               dict(eye="fora", hr=3, leg=0, falls=3, swords=(((20, 29), (31, 29)),),
                    por=((SHIELD_FLAT, 0, 26), (EYE_TINY[1], 26, 22)))],
    # cochila apoiado na espada fincada, o olhinho apagado, "z" subindo
    "waiting": [dict(hr=6, falls=1, eye="fechado", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22),)),
                dict(hr=6, falls=1, eye="fechado", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22), (Z_S, 25, 8))),
                dict(hr=6, falls=1, eye="fechado", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22), (Z_S, 24, 8), (Z_L, 26, 1))),
                dict(hr=6, falls=1, eye="fechado", arms=(_E, ((21, 23), (24, 23))),
                     swords=(((24, 23), (24, 30)),), por=((SHIELD, 1, 22), (Z_L, 26, 1)))],
    # golpe: ergue a espada, corta para baixo (rastro branco), empurra o escudo (baque), estoca com brilho
    "running": [dict(cx=14, eye="bravo", arms=(((8, 22), (5, 25)),), swords=(((23, 14), (29, 3)),),
                     por=((SHIELD, 0, 21),)),
                dict(cx=14, lean=1, eye="bravo", arms=(((9, 22), (6, 25)),), swords=(((24, 21), (31, 28)),),
                     por=((SHIELD, 1, 21), (GASH, 23, 8))),
                dict(cx=14, lean=2, eye="bravo", arms=(((22, 22), (25, 21)),),
                     swords=(((10, 25), (6, 30)),), por=((SHIELD, 23, 16), (SHINE, 25, 7))),
                dict(cx=14, lean=2, eye="bravo", arms=(((10, 22), (7, 25)),), swords=(((24, 21), (31, 21)),),
                     por=((SHIELD, 1, 20), (SHINE, 25, 13)))],
    # manopla no queixo do elmo, olhinho olhando para cima, "?" aparece
    "review": [dict(eye="cima", arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21),)),
               dict(eye="cima", arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21), (QMARK_S, 25, 4))),
               dict(eye="cima", arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21), (QMARK, 25, 2))),
               dict(eye=2, arms=(_E, ((21, 22), (22, 20))), por=((SHIELD, 1, 21), (QMARK, 25, 2)))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 17x10 colada 12 à esquerda e 8 acima do topo do elmo (topo do elmo na linha 8, centro na coluna 12):
# pluma vermelha presa no alto do elmo, caindo para trás; o estandarte azul de cruz dourada espeta das costas
_PLUME = [
    "....KKKK.",
    "..KKRRRRK",
    ".KRRRRrRK",
    "KRRrrKKRK",
    "KRrK.KGGK",
    ".KK..KGK.",
]
_BANNER = [
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


def _extra(pieces, w=17, h=10):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


PLUME = _extra(((_PLUME, 7, 2),))
PLUME_BANNER = _extra(((_BANNER, 0, 0), (_PLUME, 7, 2)))
STAGES = [
    {"title": "Armadura Vazia", "floor": 1, "extra": None},
    {"title": "Cavaleiro Oco", "floor": 4, "extra": PLUME},
    {"title": "Paladino Oco", "floor": 10, "extra": PLUME_BANNER},
]
