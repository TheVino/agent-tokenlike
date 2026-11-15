"""Slime embutido, 32 px. Cada quadro sai de partes: corpo (domo paramétrico com contorno, sombra e brilho),
rosto (olhos, boca, bochechas) e sobreposições (gotinha, bracinho, "z", "?", poça).
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, mirror, stamp

PAL = {
    "K": "#1b1b2f", "G": "#57d36b", "L": "#b4f5a8", "D": "#2f9a4a",
    "W": "#ffffff", "B": "#1b1b2f", "P": "#ff8fb1", "R": "#c8304a",
    "S": "#d7dde9", "s": "#8a94a8", "Y": "#ffd23f", "y": "#c99a00", "T": "#8fd8ff",
}

# ---- partes do rosto (olho esquerdo; o direito é o espelho, menos onde o brilho tem de ficar do mesmo lado)
EYE = ["WB", "BB", "BB", "BB"]
EYE_CLOSED = ["...", "...", "BBB"]
EYE_HAPPY = [".B.", "B.B"]
EYE_X = ["B.B", ".B.", "B.B"]
EYE_UP = ["WB", "BB", ".."]
BROW_ANGRY = ["BB..", "..BB"]          # esquerda: desce para dentro
BROW_SAD = ["..BB", "BB.."]         # esquerda: desce para fora
MOUTH = {
    "sorriso": ["B..B", ".BB."],
    "aberta": ["BBBBB", "BRRRB", "BRPRB", ".BBB."],
    "dentes": ["BBBBB", "BWBWB", ".BBB."],
    "o": [".B.", "B.B", ".B."],
    "triste": [".BB.", "B..B"],
    "reta": ["BBB"],
}

DROP = [".K.", "KGK", "KDK", ".K."]
DROP_S = ["K", "K"]
# bracinho de gosma (raiz embaixo à esquerda): baixo, horizontal, diagonal, para cima = arco do aceno
ARM_DOWN = ["KKK......", "KGGKK....", "KGGGGKK..", ".KKGGGGK.", "...KKGGLK", ".....KKK."]
ARM_HOR = ["......KKK.", "KKKKKKGGLK", "KGGGGGGGGK", "KGGGGGGGDK", "KKKKKKKKK."]
ARM_DIAG = [".....KKK", "....KGLK", "...KGGGK", "..KGGGK.", ".KGGGK..", "KGGGK...", "KGGK....", "KKK....."]
ARM_UP = [".KKK.", "KGLGK", "KGGGK", "KGGGK", "KGGK.", "KGGK.", "KGGK.", "KKK.."]




def _body(w, h, cx, base, lean):
    """Domo: largo embaixo, redondo em cima; `lean` desloca o topo (inclinar para frente ou pender)."""
    pts = set()
    for y in range(base - h + 1, base + 1):
        u = (base - y) / h                      # 0 na base, ~1 no topo
        half = w / 2 * (1 - u ** 2.4) ** 0.5
        c = cx + lean * u
        for x in range(round(c - half), round(c + half)):
            if 0 < x < N - 1:
                pts.add((x, y))
    return pts


def frame(w, h, cx=16, base=30, lean=0, eyes="normal", look=0, mouth="sorriso", cheek=True, por=()):
    """Um quadro 32x32 e a âncora (topo do corpo) para o acréscimo do estágio."""
    g = [["."] * N for _ in range(N)]
    pts = _body(w, h, cx, base, lean)
    top = min(y for _, y in pts)
    xs_top = sorted(x for x, y in pts if y == top)
    for x, y in pts:
        dir_ = (x + 1, y) not in pts or (x + 2, y) not in pts
        g[y][x] = "D" if (y >= base - 1 or dir_) else "G"
    for x, y in pts:                              # contorno de 4 vizinhos
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in pts and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # brilho no alto à esquerda
    bx, by = round(cx + lean * 0.75 - w * 0.28), top + max(1, h // 6)
    for x, y in ((bx, by), (bx + 1, by), (bx, by + 1), (bx + 2, by - 1)):
        if (x, y) in pts and g[y][x] == "G":
            g[y][x] = "L"
    # rosto
    ey = top + max(1, int(h * 0.38))
    fx = round(cx + lean * (base - ey) / h) + look
    lx, rx = fx - 5, fx + 3
    if eyes == "fechado":
        stamp(g, EYE_CLOSED, lx - 1, ey); stamp(g, EYE_CLOSED, rx, ey)
    elif eyes == "feliz":
        stamp(g, EYE_HAPPY, lx - 1, ey + 1); stamp(g, EYE_HAPPY, rx, ey + 1)
    elif eyes == "x":
        stamp(g, EYE_X, lx - 1, ey); stamp(g, EYE_X, rx, ey)
    elif eyes == "cima":
        stamp(g, EYE_UP, lx, ey - 1); stamp(g, EYE_UP, rx, ey - 1)
    else:
        stamp(g, EYE, lx, ey); stamp(g, EYE, rx, ey)
        if eyes == "bravo":
            stamp(g, BROW_ANGRY, lx - 2, ey - 3); stamp(g, mirror(BROW_ANGRY), rx, ey - 3)
        elif eyes == "triste":
            stamp(g, BROW_SAD, lx - 2, ey - 3); stamp(g, mirror(BROW_SAD), rx, ey - 3)
    if mouth:
        b = MOUTH[mouth]
        stamp(g, b, fx - len(b[0]) // 2, ey + 5)
    if cheek and eyes in ("normal", "feliz", "fechado"):
        for x in (lx - 3, lx - 2, rx + 3, rx + 4):
            if (x, ey + 4) in pts:
                g[ey + 4][x] = "P"
    for s, x, y in por:
        stamp(g, s, x, y)
    cxt = (xs_top[0] + xs_top[-1]) // 2
    return ["".join(l) for l in g], (cxt - 5, top - 4)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


_SPECS = {
    # respira (estica e encolhe) e pisca no 3º quadro
    "idle": [dict(w=24, h=18), dict(w=25, h=17), dict(w=25, h=17, eyes="fechado"), dict(w=23, h=19)],
    # estica para frente, olhos na direção, gotinha ficando para trás
    "run_r": [dict(w=24, h=16, cx=18, lean=4, look=2, por=((DROP, 2, 25),)),
              dict(w=23, h=18, cx=18, lean=3, look=2, por=((DROP, 0, 26), (DROP_S, 4, 29))),
              dict(w=25, h=15, cx=17, lean=5, look=3, por=((DROP_S, 2, 29),)),
              dict(w=24, h=17, cx=18, lean=4, look=2, por=((DROP, 3, 26),))],
    # bracinho de gosma sai do lado direito e balança
    "waving": [dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_DOWN, 22, 18),)),
               dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_HOR, 22, 16),)),
               dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_DIAG, 22, 11),)),
               dict(w=24, h=18, cx=13, eyes="feliz", mouth="aberta", por=((ARM_UP, 22, 9),))],
    # agacha, estica no ar, alto, cai, achata ao cair
    "jumping": [dict(w=28, h=12, eyes="fechado", mouth="reta"),
                dict(w=18, h=23, base=27, mouth="o"),
                dict(w=22, h=19, base=22, eyes="feliz", mouth="aberta"),
                dict(w=20, h=21, base=29, mouth="o"),
                dict(w=28, h=11, eyes="feliz")],
    # derrete numa poça; olhos em X no último
    "failed": [dict(w=24, h=18, eyes="triste", mouth="triste", por=((TEAR, 9, 21),)),
               dict(w=26, h=14, eyes="triste", mouth="triste", por=((DROP, 1, 27), (DROP, 28, 27))),
               dict(w=28, h=10, eyes="triste", mouth="reta", por=((DROP_S, 0, 29), (DROP_S, 31, 29))),
               dict(w=30, h=7, eyes="fechado", mouth=None, cheek=False),
               dict(w=30, h=7, eyes="x", mouth=None)],
    # cabeça pende de lado, olhos fechados, "z" subindo
    "waiting": [dict(w=25, h=17, cx=14, lean=-2, eyes="fechado", mouth=None),
                dict(w=26, h=16, cx=14, lean=-4, eyes="fechado", mouth=None, por=((Z_S, 21, 7),)),
                dict(w=26, h=16, cx=14, lean=-4, eyes="fechado", mouth="o", por=((Z_S, 21, 7), (Z_L, 25, 1))),
                dict(w=25, h=17, cx=14, lean=-3, eyes="fechado", mouth=None, por=((Z_L, 25, 0),))],
    # investe e morde: recua, avança de boca aberta, fecha os dentes
    "running": [dict(w=25, h=16, cx=15, lean=-3, eyes="bravo", mouth="reta"),
                dict(w=26, h=16, cx=16, lean=5, look=3, eyes="bravo", mouth="aberta"),
                dict(w=26, h=17, cx=16, lean=4, look=3, eyes="bravo", mouth="dentes"),
                dict(w=24, h=18, cx=15, lean=1, look=1, eyes="bravo", mouth="aberta")],
    # olha para cima e o "?" aparece
    "review": [dict(w=24, h=18, cx=14, eyes="cima", mouth="reta"),
               dict(w=24, h=18, cx=14, eyes="cima", mouth="o", por=((QMARK_S, 24, 7),)),
               dict(w=23, h=19, cx=14, eyes="cima", mouth="o", por=((QMARK, 24, 3),)),
               dict(w=24, h=18, cx=14, eyes="cima", mouth="o", por=((QMARK, 24, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

BLINK = FRAMES["idle"][2]     # quadro do idle com os olhos fechados

HELM = [
    "...KKKK...",
    "..KSSSSK..",
    ".KSSSSSsK.",
    "KSSRSSSSsK",
    "KKKKKKKKKK",
]
HERO_CROWN = [
    ".K...K...K.",
    "KYK.KYK.KYK",
    "KYYKYRYKYYK",
    "KYYYYYYYYYK",
    "KyyyyyyyyyK",
    ".KKKKKKKKK.",
]
STAGES = [
    {"title": "Gotinha", "floor": 1, "extra": None},
    {"title": "Slime", "floor": 4, "extra": HELM},
    {"title": "Rei Slime", "floor": 10, "extra": HERO_CROWN},
]
