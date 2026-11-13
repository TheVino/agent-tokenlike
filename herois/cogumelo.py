"""Cogumelo de Caverna, 32 px, olhando para a direita. Cada quadro sai de partes: talo com rostinho (e sombra),
chapéu em cúpula com pintas que brilham (2 fases), pezinhos, braços em linha grossa e objetos (esporos, nuvem).
No `failed` o chapéu murcha e tomba, o talo encolhe e os esporos escapam.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from math import sqrt

from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, traco

PAL = {
    "K": "#241a2c", "C": "#efe3cf", "c": "#c2ae98", "U": "#7a4fb0", "u": "#4c2e78",
    "L": "#7ff5d6", "l": "#3fae9a", "E": "#a8e07a", "e": "#6aa848", "O": "#e0743a",
    "W": "#ffffff", "B": "#241a2c", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f",
}

ESPORO = ["..K..", ".KLK.", "KLWLK", ".KLK.", "..K.."]
ESPORO_P = [".K.", "KLK", ".K."]
NUVEM = [
    "....KKK.....",
    "..KKEEEKKK..",
    ".KEEELEEEEK.",
    "KEELEEEeEEEK",
    "KEEEEeELEEEK",
    "KeEEEEEEEeK.",
    ".KKeELEeKK..",
    "...KKKKK....",
]
PUFF = ["..KKK..", ".KEEEK.", "KEELEEK", "KEEEeEK", ".KEEEK.", "..KKK.."]
MAO = [".KKK.", "KCCCK", "KCCCK", ".KKK."]
# pintas do chapéu: (dx do centro da linha, linha a partir do topo, largura, altura, fase em que acende)
PINTAS = ((-4, 2, 2, 2, 0), (2, 1, 2, 1, 1), (4, 3, 2, 2, 0), (-1, 4, 1, 1, 1), (-7, 4, 1, 1, 1))


def quadro(cx=15, base=30, h=9, lean=0, chapeu=9, hc=7, tilt=0, olhos="normal", brilho=0, bracos=(), por=(),
           atras=(), pes=(0, 0)):
    """Um quadro 32x32 e a âncora (canto do acréscimo, 13 px à esquerda e 6 acima do topo do chapéu).
    `chapeu`: meia-largura do chapéu; `hc`: altura; `tilt`: quanto o topo do chapéu tomba para o lado."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    top = base - h
    talo = set()
    for y in range(top, base):
        t = (y - top) / max(h - 1, 1)
        c = cx + round(lean * (1 - t))
        talo |= {(x, y) for x in range(c - 5, c + 6)}
    for px, dx in ((cx - 4, pes[0]), (cx + 2, pes[1])):   # pezinhos
        talo |= {(x, base) for x in range(px + dx, px + dx + 3)}
    ct = cx + lean
    ytop = top + 2 - hc
    cap = {}
    for r in range(hc):
        tt = (hc - 1 - r) / hc
        w = max(1, round(chapeu * sqrt(1 - tt * tt))) - (r == hc - 1)
        cc = ct + round(tilt * (hc - 1 - r) / max(hc - 1, 1))
        for x in range(cc - w, cc + w + 1):
            cap[(x, ytop + r)] = "u" if r == hc - 1 or x >= cc + w - 1 else "U"
        for dx, py, pw, ph, fase in PINTAS:
            if py <= r < py + ph:
                for x in range(cc + dx, cc + dx + pw):
                    if (x, ytop + r) in cap and cap[(x, ytop + r)] == "U" and abs(x - cc) < w:
                        cap[(x, ytop + r)] = "L" if fase == brilho else "l"
    corpo = talo | set(cap)
    for x, y in talo:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = "c" if (x + 1, y) not in talo or y >= base - 1 else "C"
    for (x, y), ch in cap.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = ch
    for x, y in corpo:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in corpo and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # rosto no talo, logo abaixo do chapéu
    fy = top + 2
    ex = ct - 3
    for x in (ex, ex + 5):
        if olhos == "fechado":
            carimbar(g, ["BB"], x, fy + 1)
        elif olhos == "feliz":
            carimbar(g, [".B.", "B.B"], x - (x > ex), fy)
        elif olhos == "x":
            carimbar(g, ["B.B", ".B.", "B.B"], x - (x > ex), fy)
        else:
            carimbar(g, ["WB", "BB"], x, fy)
            if olhos == "cima":
                g[fy + 1][x] = g[fy + 1][x + 1] = "B"; g[fy][x] = "B"; g[fy][x + 1] = "W"
    if olhos not in ("fechado", "x"):
        g[fy + 2][ex - 1] = g[fy + 2][ex + 7] = "P"
    my = fy + 3
    if olhos in ("triste", "x"):
        carimbar(g, [".BB.", "B..B"], ex + 2, my)
    elif olhos == "bravo":
        carimbar(g, ["BBBB"], ex + 2, my)
    elif olhos != "fechado":
        carimbar(g, ["B..B", ".BB."], ex + 2, my)
    for a, b in bracos:
        x, y = a
        while (x, y) in talo:              # o braço sai da beirada do talo, sem riscar o rosto
            x += 1 if x >= ct else -1
        traco(g, (x, y), b, "C")
        carimbar(g, MAO, b[0] - 2, b[1] - 1)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (ct + tilt - 13, ytop - 6)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, h=9 -> talo de 21 a 29, chapéu de 16 a 22; laterais do talo em cx-5 / cx+5 (cx=15: 10 e 20)
_SPECS = {
    # parado, pintas piscando, esporinhos subindo de um lado e do outro, mãozinhas balançando
    "idle": [dict(brilho=0, bracos=(((20, 25), (24, 27)), ((10, 25), (6, 27))), por=((ESPORO, 26, 18),)),
             dict(brilho=1, bracos=(((20, 25), (24, 26)), ((10, 25), (6, 28))), por=((ESPORO, 27, 13),)),
             dict(brilho=0, olhos="fechado", bracos=(((20, 25), (24, 27)), ((10, 25), (6, 27))),
                  por=((ESPORO, 2, 17), (ESPORO_P, 28, 9))),
             dict(brilho=1, bracos=(((20, 25), (24, 28)), ((10, 25), (6, 26))), por=((ESPORO, 1, 12),))],
    # corre inclinado, chapéu puxado para trás, esporos ficando para trás
    "run_r": [dict(lean=2, tilt=-2, pes=(-2, 2), bracos=(((12, 25), (7, 28)),), por=((ESPORO, 1, 20),)),
              dict(lean=3, base=29, tilt=-3, brilho=1, bracos=(((12, 24), (7, 23)),), por=((ESPORO_P, 2, 17),)),
              dict(lean=2, tilt=-2, pes=(2, -2), bracos=(((12, 25), (7, 27)),), por=((ESPORO, 0, 19),)),
              dict(lean=3, base=29, tilt=-3, brilho=1, bracos=(((12, 24), (8, 21)),), por=((ESPORO_P, 1, 15),))],
    # acena alto com a mão direita, chapéu balança junto
    "waving": [dict(olhos="feliz", bracos=(((20, 24), (28, 21)), ((10, 25), (6, 27)))),
               dict(olhos="feliz", tilt=1, brilho=1, bracos=(((20, 24), (29, 16)), ((10, 25), (6, 27)))),
               dict(olhos="feliz", tilt=2, bracos=(((20, 24), (25, 14)), ((10, 25), (6, 27)))),
               dict(olhos="feliz", tilt=1, brilho=1, bracos=(((20, 24), (29, 16)), ((10, 25), (6, 27))))],
    # agacha (chapéu achata), salta com os braços para cima, cai, pousa
    "jumping": [dict(h=7, chapeu=10, hc=6, olhos="fechado", bracos=(((20, 26), (24, 28)), ((10, 26), (6, 28)))),
                dict(base=27, hc=8, chapeu=8, bracos=(((20, 22), (25, 18)), ((10, 22), (5, 18)))),
                dict(base=24, hc=8, chapeu=8, olhos="feliz", brilho=1,
                     bracos=(((20, 19), (26, 14)), ((10, 19), (4, 14)))),
                dict(base=27, brilho=1, bracos=(((20, 22), (25, 24)), ((10, 22), (5, 24)))),
                dict(h=8, chapeu=10, hc=6, olhos="feliz", bracos=(((20, 26), (24, 28)), ((10, 26), (6, 28))))],
    # triste, o chapéu murcha e tomba, o talo encolhe e os esporos escapam
    "failed": [dict(olhos="triste", bracos=(((20, 25), (23, 29)), ((10, 25), (7, 29))), por=((LAGRIMA, 11, 25),)),
               dict(olhos="triste", h=8, hc=6, chapeu=10, tilt=-2, brilho=1,
                    bracos=(((20, 26), (23, 29)), ((10, 26), (7, 29))), por=((ESPORO, 25, 12),)),
               dict(cx=16, olhos="triste", h=8, hc=5, chapeu=10, tilt=-3, por=((LAGRIMA, 11, 26), (ESPORO, 24, 9),
                                                                      (ESPORO, 3, 13))),
               dict(cx=17, olhos="x", h=7, hc=4, chapeu=10, tilt=-3, lean=-1, brilho=1,
                    por=((ESPORO_P, 25, 8), (ESPORO, 4, 9), (ESPORO, 26, 14))),
               dict(cx=18, olhos="x", h=7, hc=4, chapeu=11, tilt=-4, lean=-1, brilho=2, por=((ESPORO_P, 6, 6),))],
    # cochila com o chapéu caído para a frente, "z" subindo
    "waiting": [dict(h=8, olhos="fechado", tilt=2, brilho=2),
                dict(h=8, olhos="fechado", tilt=3, brilho=2, por=((Z_P, 24, 6),)),
                dict(h=8, olhos="fechado", tilt=3, brilho=2, por=((Z_P, 23, 6), (Z_G, 26, 0))),
                dict(h=8, olhos="fechado", tilt=2, brilho=2, por=((Z_G, 26, 0),))],
    # golpe: puxa o braço, espreme o chapéu e sopra uma nuvem de esporos que se espalha
    "running": [dict(cx=15, lean=-1, tilt=-1, hc=8, chapeu=8, olhos="bravo", bracos=(((8, 25), (3, 21)),)),
                dict(cx=14, lean=1, hc=5, chapeu=11, olhos="bravo", brilho=1, bracos=(((19, 24), (24, 22)),),
                     por=((PUFF, 25, 22),)),
                dict(cx=14, lean=3, tilt=1, olhos="bravo", bracos=(((19, 24), (22, 24)),),
                     por=((NUVEM, 20, 18),)),
                dict(cx=14, lean=1, tilt=1, olhos="bravo", brilho=1, bracos=(((19, 24), (23, 27)),),
                     por=((NUVEM, 19, 9), (ESPORO, 25, 21), (ESPORO_P, 28, 26), (ESPORO_P, 22, 19)))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=13, olhos="cima", bracos=(((18, 27), (21, 25)),)),
               dict(cx=13, olhos="cima", brilho=1, bracos=(((18, 27), (21, 25)),), por=((INTERROG_P, 25, 4),)),
               dict(cx=13, olhos="cima", bracos=(((18, 27), (21, 25)),), por=((INTERROG, 25, 2),)),
               dict(cx=13, olhos="normal", brilho=1, bracos=(((18, 27), (21, 25)),), por=((INTERROG, 25, 2),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)


def _extra(pecas, w=27, h=14):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


# esporos brilhando em volta do chapéu (o topo do chapéu fica na linha 6, centrado na coluna 13); o extra tem 27
# colunas, então o topo do chapéu (ct + tilt) fica entre x=13 e x=18 em todo quadro para os esporos caberem
_BRILHO = ((ESPORO, 2, 1), (ESPORO, 22, 6), (ESPORO, 0, 9))
ESPOROS = _extra(_BRILHO)
# ancião: cogumelinhos brotando do topo do chapéu e dois esporos dos lados
MINI_P = [".KKK.", "KOLOK", "KKKKK", ".KCK.", ".KCK."]
MINI_G = ["..KKK..", ".KOOOK.", "KOLOOOK", "KKKKKKK", "..KCK..", "..KCK.."]
ANCIAO = _extra(((ESPORO, 22, 6), (ESPORO, 0, 9), (MINI_P, 7, 1), (MINI_G, 12, 0)))
ESTAGIOS = [
    {"title": "Esporinho", "floor": 1, "extra": None},
    {"title": "Cogumelo de Caverna", "floor": 4, "extra": ESPOROS},
    {"title": "Ancião do Micélio", "floor": 10, "extra": ANCIAO},
]
