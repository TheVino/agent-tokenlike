"""Vela Viva, 32 px, olhando para a direita. Cada quadro sai de partes: corpo de cera (com escorridos e sombra),
pavio, chama em 3 fases (tremula), rostinho, braços de cera em linha grossa e objetos (bola de fogo, fumaça).
No `failed` a chama encolhe, apaga e a cera escorre numa poça.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, trait

PAL = {
    "K": "#2a1d24", "C": "#f3e6c4", "c": "#cdb48a", "w": "#3a2a20",
    "F": "#ffd23f", "f": "#ff8a2a", "R": "#e8452c", "W": "#ffffff",
    "B": "#2a1d24", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f", "S": "#9a93a6",
    "r": "#b8283a", "q": "#7e1a2a", "G": "#e8bb48", "g": "#9a7420",
}

# chama: 3 fases do tremor (7 de largura), mais a grande do salto/golpe e a pequenininha do failed
FLAMES = [
    ["...K...", "..KFK..", "..KFK..", ".KFfFK.", ".KfRfK.", "KFfRfFK", ".KFFFK.", "..KKK.."],
    ["....K..", "...KFK.", "..KFFK.", ".KFfFK.", ".KfRfK.", "KFfRfFK", ".KFFFK.", "..KKK.."],
    ["..K....", ".KFK...", ".KFFK..", ".KFfFK.", ".KfRfK.", "KFfRfFK", ".KFFFK.", "..KKK.."],
]
FLAME_L = ["...K...", "..KFK..", ".KFFK..", ".KFfFK.", "KFfRfFK", "KfRRRfK", "KFfRfFK", ".KFFFK.", "..KKK.."]
FLAME_S = ["..K..", ".KFK.", "KFfFK", ".KKK."]
SMOKE = ["..SS.", ".S...", "..S..", "...S.", "..S.."]
SMOKE2 = [".S...", "..S..", "...S.", "..S..", ".S..."]
BALL = ["..KKKK..", ".KFFFFK.", "KFfRRfFK", "KfRRRRfK", "KFfRRfFK", ".KFFFFK.", "..KKKK.."]
SPARKS = ["K.....K", ".F...F.", "...K...", ".F...F.", "K.....K"]
HAND = [".KKK.", "KCCCK", "KCCCK", ".KKK."]


def frame(cx=15, base=30, h=12, lean=0, eyes="normal", flame=0, arms=(), por=(), behind=(), puddle=0,
           feet=(0, 0)):
    """Um quadro 32x32 e a âncora (canto do colar, no topo do corpo). `chama`: 0..2 fase, "g" grande,
    "p" pequena, "fumaca"/"fumaca2" apagada. `poca`: meia-largura extra da cera escorrida na base."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    top = base - h
    body = set()
    for y in range(top, base):
        t = (y - top) / max(h - 1, 1)
        c = cx + round(lean * (1 - t))
        half = 5 + (round(puddle * t * t) if puddle else 0)
        body |= {(x, y) for x in range(c - half, c + half + 1)}
    for i, (px, dx) in enumerate(((cx - 4, feet[0]), (cx + 2, feet[1]))):   # pezinhos de cera
        body |= {(x, base) for x in range(px + dx, px + dx + 3)}
    for x, y in body:
        if 0 <= x < N and 0 <= y < N:
            shadow = (x + 1, y) not in body or y >= base - 1
            g[y][x] = "c" if shadow else "C"
    ct = cx + lean
    for dx, L in ((-4, 3), (3, 4), (-1, 2)):      # escorridos no alto
        for y in range(top, top + L):
            if (ct + dx, y) in body:
                g[y][ct + dx] = "c"
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # pavio e chama
    g[top - 1][ct] = g[top - 2][ct] = "w"
    if flame in (0, 1, 2):
        stamp(g, FLAMES[flame], ct - 3, top - 10)
    elif flame == "g":
        stamp(g, FLAME_L, ct - 3, top - 11)
    elif flame == "p":
        stamp(g, FLAME_S, ct - 2, top - 6)
    elif flame == "fumaca":
        stamp(g, SMOKE, ct - 2, top - 7)
    elif flame == "fumaca2":
        stamp(g, SMOKE2, ct - 1, top - 8)
    # rosto
    fy = top + 4 if h >= 9 else top + 2
    ex = ct - 3
    for x in (ex, ex + 5):
        if eyes == "fechado":
            stamp(g, ["BB"], x, fy + 1)
        elif eyes == "feliz":
            stamp(g, [".B.", "B.B"], x - (x > ex), fy)
        elif eyes == "x":
            stamp(g, ["B.B", ".B.", "B.B"], x - (x > ex), fy - 1)
        else:
            stamp(g, ["WB", "BB"], x, fy)
            if eyes == "bravo":
                stamp(g, ["BB."] if x == ex else [".BB"], x - (x > ex), fy - 1)
            if eyes == "triste":
                stamp(g, [".BB"] if x == ex else ["BB."], x - (x > ex), fy - 1)
            if eyes == "cima":
                g[fy + 1][x] = g[fy + 1][x + 1] = "B"; g[fy][x] = "B"; g[fy][x + 1] = "W"
    if eyes not in ("fechado", "x"):
        g[fy + 2][ex - 1] = g[fy + 2][ex + 7] = "P"
    my = fy + 3
    if eyes in ("triste", "x"):
        stamp(g, [".BB.", "B..B"], ex + 2, my)
    elif eyes == "bravo":
        stamp(g, ["BBBB"], ex + 2, my)
    elif eyes != "fechado":
        stamp(g, ["B..B", ".BB."], ex + 2, my)
    for a, b in arms:
        trait(g, a, b, "C")
        stamp(g, HAND, b[0] - 2, b[1] - 1)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (ct - 6, top - 1)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, h=12 -> top=18; laterais do corpo em cx-5 / cx+5 (cx=15: 10 e 20)
_SPECS = {
    # parado, chama tremulando, mãozinhas balançando
    "idle": [dict(flame=0, arms=(((20, 23), (24, 25)), ((10, 23), (6, 25)))),
             dict(flame=1, arms=(((20, 23), (24, 24)), ((10, 23), (6, 26)))),
             dict(flame=2, eyes="fechado", arms=(((20, 23), (24, 25)), ((10, 23), (6, 25)))),
             dict(flame=1, arms=(((20, 23), (24, 26)), ((10, 23), (6, 24))))],
    # corre inclinado, chama puxada para trás, braço balançando
    "run_r": [dict(lean=2, flame=2, feet=(-2, 2), arms=(((12, 23), (7, 26)),), por=((SMOKE2, 5, 6),)),
              dict(lean=3, base=29, flame=2, arms=(((12, 22), (7, 22)),)),
              dict(lean=2, flame=2, feet=(2, -2), arms=(((12, 23), (7, 25)),), por=((SMOKE2, 4, 7),)),
              dict(lean=3, base=29, flame=2, arms=(((12, 22), (8, 20)),))],
    # acena alto com a mão direita
    "waving": [dict(eyes="feliz", flame=0, arms=(((20, 22), (25, 18)), ((10, 23), (6, 25)))),
               dict(eyes="feliz", flame=1, arms=(((20, 22), (26, 14)), ((10, 23), (6, 25)))),
               dict(eyes="feliz", flame=2, arms=(((20, 22), (28, 16)), ((10, 23), (6, 25)))),
               dict(eyes="feliz", flame=1, arms=(((20, 22), (26, 14)), ((10, 23), (6, 25))))],
    # agacha, salta com os braços para cima e a chama grande, cai, pousa
    "jumping": [dict(h=9, eyes="fechado", flame=0, arms=(((20, 25), (24, 27)), ((10, 25), (6, 27)))),
                dict(h=13, base=28, flame="g", arms=(((20, 19), (24, 15)), ((10, 19), (6, 15)))),
                dict(h=12, base=25, eyes="feliz", flame="g", arms=(((20, 16), (25, 11)), ((10, 16), (5, 11)))),
                dict(h=13, base=28, flame=1, arms=(((20, 20), (24, 22)), ((10, 20), (6, 22)))),
                dict(h=10, eyes="feliz", flame=0, arms=(((20, 24), (24, 26)), ((10, 24), (6, 26))))],
    # triste, a chama encolhe e apaga em fumaça, a cera derrete numa poça
    "failed": [dict(eyes="triste", flame=2, arms=(((20, 23), (23, 27)), ((10, 23), (7, 27))),
                    por=((TEAR, 11, 23),)),
               dict(eyes="triste", flame="p", h=11, puddle=2, arms=(((20, 24), (23, 28)), ((10, 24), (7, 28)))),
               dict(eyes="triste", flame="fumaca", h=9, puddle=4, por=((TEAR, 11, 25),)),
               dict(eyes="x", flame="fumaca2", h=7, puddle=6),
               dict(eyes="x", flame="fumaca2", h=6, puddle=8, lean=-1)],
    # cochila mais baixinha, chama pequena, "z" subindo
    "waiting": [dict(h=10, eyes="fechado", flame="p"),
                dict(h=10, lean=-1, eyes="fechado", flame="p", por=((Z_S, 22, 6),)),
                dict(h=10, lean=-1, eyes="fechado", flame="p", por=((Z_S, 21, 6), (Z_L, 25, 0))),
                dict(h=10, eyes="fechado", flame="p", por=((Z_L, 25, 0),))],
    # golpe: puxa a chama na mão, gira e arremessa uma bola de fogo que estoura em faíscas
    "running": [dict(cx=13, lean=-2, eyes="bravo", flame="g", arms=(((9, 22), (4, 18)),),
                     por=((FLAME_S, 2, 13),)),
                dict(cx=14, lean=2, eyes="bravo", flame="g", arms=(((19, 22), (24, 16)),),
                     por=((BALL, 22, 9),)),
                dict(cx=14, lean=3, eyes="bravo", flame=2, arms=(((19, 22), (25, 22)),),
                     por=((BALL, 24, 14),)),
                dict(cx=14, lean=1, eyes="bravo", flame=1, arms=(((19, 22), (23, 25)),),
                     por=((SPARKS, 24, 13), (FLAME_S, 26, 9)))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=13, eyes="cima", flame=0, arms=(((18, 25), (21, 23)),)),
               dict(cx=13, eyes="cima", flame=1, arms=(((18, 25), (21, 23)),), por=((QMARK_S, 24, 4),)),
               dict(cx=13, eyes="cima", flame=2, arms=(((18, 25), (21, 23)),), por=((QMARK, 24, 2),)),
               dict(cx=13, eyes="normal", flame=1, arms=(((18, 25), (21, 23)),), por=((QMARK, 24, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# colar de cera vermelha escorrida no topo do corpo (acima dos olhos)
NECKLACE = [
    ".KKKKKKKKKKK.",
    "KrrrrrrrrrrrK",
    "KrqKrrKrqKrrK",
    ".KrK..KrK.KK.",
]
# círio antigo: colar com faixa dourada e argola de castiçal do lado
TAPER = [
    ".KKKKKKKKKKK.....",
    "KGgGgGgGgGgGK....",
    "KrqKrrKrqKrrKKKK.",
    ".KrK..KrK.KKKGGGK",
    "............KG.GK",
    "............KG.GK",
    "............KGGGK",
    ".............KKK.",
]
STAGES = [
    {"title": "Tôco de Vela", "floor": 1, "extra": None},
    {"title": "Vela Viva", "floor": 4, "extra": NECKLACE},
    {"title": "Círio Antigo", "floor": 10, "extra": TAPER},
]
