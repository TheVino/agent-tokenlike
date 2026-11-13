"""Vela Viva, 32 px, olhando para a direita. Cada quadro sai de partes: corpo de cera (com escorridos e sombra),
pavio, chama em 3 fases (tremula), rostinho, braços de cera em linha grossa e objetos (bola de fogo, fumaça).
No `failed` a chama encolhe, apaga e a cera escorre numa poça.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, traco

PAL = {
    "K": "#2a1d24", "C": "#f3e6c4", "c": "#cdb48a", "w": "#3a2a20",
    "F": "#ffd23f", "f": "#ff8a2a", "R": "#e8452c", "W": "#ffffff",
    "B": "#2a1d24", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f", "S": "#9a93a6",
    "r": "#b8283a", "q": "#7e1a2a", "G": "#e8bb48", "g": "#9a7420",
}

# chama: 3 fases do tremor (7 de largura), mais a grande do salto/golpe e a pequenininha do failed
CHAMAS = [
    ["...K...", "..KFK..", "..KFK..", ".KFfFK.", ".KfRfK.", "KFfRfFK", ".KFFFK.", "..KKK.."],
    ["....K..", "...KFK.", "..KFFK.", ".KFfFK.", ".KfRfK.", "KFfRfFK", ".KFFFK.", "..KKK.."],
    ["..K....", ".KFK...", ".KFFK..", ".KFfFK.", ".KfRfK.", "KFfRfFK", ".KFFFK.", "..KKK.."],
]
CHAMA_G = ["...K...", "..KFK..", ".KFFK..", ".KFfFK.", "KFfRfFK", "KfRRRfK", "KFfRfFK", ".KFFFK.", "..KKK.."]
CHAMA_P = ["..K..", ".KFK.", "KFfFK", ".KKK."]
FUMACA = ["..SS.", ".S...", "..S..", "...S.", "..S.."]
FUMACA2 = [".S...", "..S..", "...S.", "..S..", ".S..."]
BOLA = ["..KKKK..", ".KFFFFK.", "KFfRRfFK", "KfRRRRfK", "KFfRRfFK", ".KFFFFK.", "..KKKK.."]
FAISCAS = ["K.....K", ".F...F.", "...K...", ".F...F.", "K.....K"]
MAO = [".KKK.", "KCCCK", "KCCCK", ".KKK."]


def quadro(cx=15, base=30, h=12, lean=0, olhos="normal", chama=0, bracos=(), por=(), atras=(), poca=0,
           pes=(0, 0)):
    """Um quadro 32x32 e a âncora (canto do colar, no topo do corpo). `chama`: 0..2 fase, "g" grande,
    "p" pequena, "fumaca"/"fumaca2" apagada. `poca`: meia-largura extra da cera escorrida na base."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    top = base - h
    corpo = set()
    for y in range(top, base):
        t = (y - top) / max(h - 1, 1)
        c = cx + round(lean * (1 - t))
        meia = 5 + (round(poca * t * t) if poca else 0)
        corpo |= {(x, y) for x in range(c - meia, c + meia + 1)}
    for i, (px, dx) in enumerate(((cx - 4, pes[0]), (cx + 2, pes[1]))):   # pezinhos de cera
        corpo |= {(x, base) for x in range(px + dx, px + dx + 3)}
    for x, y in corpo:
        if 0 <= x < N and 0 <= y < N:
            sombra = (x + 1, y) not in corpo or y >= base - 1
            g[y][x] = "c" if sombra else "C"
    ct = cx + lean
    for dx, L in ((-4, 3), (3, 4), (-1, 2)):      # escorridos no alto
        for y in range(top, top + L):
            if (ct + dx, y) in corpo:
                g[y][ct + dx] = "c"
    for x, y in corpo:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in corpo and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # pavio e chama
    g[top - 1][ct] = g[top - 2][ct] = "w"
    if chama in (0, 1, 2):
        carimbar(g, CHAMAS[chama], ct - 3, top - 10)
    elif chama == "g":
        carimbar(g, CHAMA_G, ct - 3, top - 11)
    elif chama == "p":
        carimbar(g, CHAMA_P, ct - 2, top - 6)
    elif chama == "fumaca":
        carimbar(g, FUMACA, ct - 2, top - 7)
    elif chama == "fumaca2":
        carimbar(g, FUMACA2, ct - 1, top - 8)
    # rosto
    fy = top + 4 if h >= 9 else top + 2
    ex = ct - 3
    for x in (ex, ex + 5):
        if olhos == "fechado":
            carimbar(g, ["BB"], x, fy + 1)
        elif olhos == "feliz":
            carimbar(g, [".B.", "B.B"], x - (x > ex), fy)
        elif olhos == "x":
            carimbar(g, ["B.B", ".B.", "B.B"], x - (x > ex), fy - 1)
        else:
            carimbar(g, ["WB", "BB"], x, fy)
            if olhos == "bravo":
                carimbar(g, ["BB."] if x == ex else [".BB"], x - (x > ex), fy - 1)
            if olhos == "triste":
                carimbar(g, [".BB"] if x == ex else ["BB."], x - (x > ex), fy - 1)
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
        traco(g, a, b, "C")
        carimbar(g, MAO, b[0] - 2, b[1] - 1)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (ct - 6, top - 1)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, h=12 -> top=18; laterais do corpo em cx-5 / cx+5 (cx=15: 10 e 20)
_SPECS = {
    # parado, chama tremulando, mãozinhas balançando
    "idle": [dict(chama=0, bracos=(((20, 23), (24, 25)), ((10, 23), (6, 25)))),
             dict(chama=1, bracos=(((20, 23), (24, 24)), ((10, 23), (6, 26)))),
             dict(chama=2, olhos="fechado", bracos=(((20, 23), (24, 25)), ((10, 23), (6, 25)))),
             dict(chama=1, bracos=(((20, 23), (24, 26)), ((10, 23), (6, 24))))],
    # corre inclinado, chama puxada para trás, braço balançando
    "run_r": [dict(lean=2, chama=2, pes=(-2, 2), bracos=(((12, 23), (7, 26)),), por=((FUMACA2, 5, 6),)),
              dict(lean=3, base=29, chama=2, bracos=(((12, 22), (7, 22)),)),
              dict(lean=2, chama=2, pes=(2, -2), bracos=(((12, 23), (7, 25)),), por=((FUMACA2, 4, 7),)),
              dict(lean=3, base=29, chama=2, bracos=(((12, 22), (8, 20)),))],
    # acena alto com a mão direita
    "waving": [dict(olhos="feliz", chama=0, bracos=(((20, 22), (25, 18)), ((10, 23), (6, 25)))),
               dict(olhos="feliz", chama=1, bracos=(((20, 22), (26, 14)), ((10, 23), (6, 25)))),
               dict(olhos="feliz", chama=2, bracos=(((20, 22), (28, 16)), ((10, 23), (6, 25)))),
               dict(olhos="feliz", chama=1, bracos=(((20, 22), (26, 14)), ((10, 23), (6, 25))))],
    # agacha, salta com os braços para cima e a chama grande, cai, pousa
    "jumping": [dict(h=9, olhos="fechado", chama=0, bracos=(((20, 25), (24, 27)), ((10, 25), (6, 27)))),
                dict(h=13, base=28, chama="g", bracos=(((20, 19), (24, 15)), ((10, 19), (6, 15)))),
                dict(h=12, base=25, olhos="feliz", chama="g", bracos=(((20, 16), (25, 11)), ((10, 16), (5, 11)))),
                dict(h=13, base=28, chama=1, bracos=(((20, 20), (24, 22)), ((10, 20), (6, 22)))),
                dict(h=10, olhos="feliz", chama=0, bracos=(((20, 24), (24, 26)), ((10, 24), (6, 26))))],
    # triste, a chama encolhe e apaga em fumaça, a cera derrete numa poça
    "failed": [dict(olhos="triste", chama=2, bracos=(((20, 23), (23, 27)), ((10, 23), (7, 27))),
                    por=((LAGRIMA, 11, 23),)),
               dict(olhos="triste", chama="p", h=11, poca=2, bracos=(((20, 24), (23, 28)), ((10, 24), (7, 28)))),
               dict(olhos="triste", chama="fumaca", h=9, poca=4, por=((LAGRIMA, 11, 25),)),
               dict(olhos="x", chama="fumaca2", h=7, poca=6),
               dict(olhos="x", chama="fumaca2", h=6, poca=8, lean=-1)],
    # cochila mais baixinha, chama pequena, "z" subindo
    "waiting": [dict(h=10, olhos="fechado", chama="p"),
                dict(h=10, lean=-1, olhos="fechado", chama="p", por=((Z_P, 22, 6),)),
                dict(h=10, lean=-1, olhos="fechado", chama="p", por=((Z_P, 21, 6), (Z_G, 25, 0))),
                dict(h=10, olhos="fechado", chama="p", por=((Z_G, 25, 0),))],
    # golpe: puxa a chama na mão, gira e arremessa uma bola de fogo que estoura em faíscas
    "running": [dict(cx=13, lean=-2, olhos="bravo", chama="g", bracos=(((9, 22), (4, 18)),),
                     por=((CHAMA_P, 2, 13),)),
                dict(cx=14, lean=2, olhos="bravo", chama="g", bracos=(((19, 22), (24, 16)),),
                     por=((BOLA, 22, 9),)),
                dict(cx=14, lean=3, olhos="bravo", chama=2, bracos=(((19, 22), (25, 22)),),
                     por=((BOLA, 24, 14),)),
                dict(cx=14, lean=1, olhos="bravo", chama=1, bracos=(((19, 22), (23, 25)),),
                     por=((FAISCAS, 24, 13), (CHAMA_P, 26, 9)))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=13, olhos="cima", chama=0, bracos=(((18, 25), (21, 23)),)),
               dict(cx=13, olhos="cima", chama=1, bracos=(((18, 25), (21, 23)),), por=((INTERROG_P, 24, 4),)),
               dict(cx=13, olhos="cima", chama=2, bracos=(((18, 25), (21, 23)),), por=((INTERROG, 24, 2),)),
               dict(cx=13, olhos="normal", chama=1, bracos=(((18, 25), (21, 23)),), por=((INTERROG, 24, 2),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# colar de cera vermelha escorrida no topo do corpo (acima dos olhos)
COLAR = [
    ".KKKKKKKKKKK.",
    "KrrrrrrrrrrrK",
    "KrqKrrKrqKrrK",
    ".KrK..KrK.KK.",
]
# círio antigo: colar com faixa dourada e argola de castiçal do lado
CIRIO = [
    ".KKKKKKKKKKK.....",
    "KGgGgGgGgGgGK....",
    "KrqKrrKrqKrrKKKK.",
    ".KrK..KrK.KKKGGGK",
    "............KG.GK",
    "............KG.GK",
    "............KGGGK",
    ".............KKK.",
]
ESTAGIOS = [
    {"title": "Tôco de Vela", "floor": 1, "extra": None},
    {"title": "Vela Viva", "floor": 4, "extra": COLAR},
    {"title": "Círio Antigo", "floor": 10, "extra": CIRIO},
]
