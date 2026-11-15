"""Fantasma, 32 px. Cada quadro sai de partes: lençol (domo com barra ondulada, contorno, sombra e brilho),
rosto (olhos, boca, bochechas) e sobreposições (mãozinha de lençol, rastro, "z", "?", buracos, sumiço).
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
import math
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, EXCLAM, TEAR, mirror, stamp

PAL = {
    "K": "#2a2140", "G": "#f2f0ff", "D": "#c6c0e8", "L": "#ffffff", "B": "#2a2140", "W": "#ffffff",
    "P": "#ff9ec4", "R": "#c8304a", "H": "#7b5cc9", "h": "#4f3a8f", "Y": "#ffd23f", "y": "#c99a00",
    "T": "#8fd8ff", "S": "#d7dde9", "s": "#8a94a8",
}

EYE = [".BB.", "BWBB", "BBBB", "BBBB", ".BB."]
EYE_CLOSED = ["....", "B..B", ".BB."]       # meia-lua para baixo (sono)
EYE_HAPPY = [".BB.", "B..B"]
EYE_X = ["B..B", ".BB.", ".BB.", "B..B"]
EYE_UP = [".BB.", "BWBB", "BBBB", "...."]
BROW_ANGRY = ["BB...", "..BBB"]
BROW_SAD = ["...BB", "BBB.."]
MOUTH = {
    "sorriso": ["B...B", ".BBB."],
    "buu": [".BBB.", "BRRRB", "BRRRB", "BRPRB", ".BBB."],
    "buu_g": [".BBBB.", "BRRRRB", "BRRRRB", "BRRRRB", "BRPPRB", ".BBBB."],
    "o": [".B.", "B.B", ".B."],
    "triste": [".BBB.", "B...B"],
    "reta": ["BBB"],
    "torta": ["BB..", "..BB"],
}

# mãozinha de lençol (raiz à esquerda, colada no corpo): baixa, reta, alta, no alto acenando
HAND_LOW = ["KK.......", "GGKK.....", "GGGGKK...", "KGGGGGKK.", ".KKGGGGLK", "...KKGGGK", ".....KKK."]
HAND_STRAIGHT = ["......KKK.", "KKKKKKGGLK", "GGGGGGGGGK", "GGGGGGGGDK", "KKKKKKKKK."]
HAND_HIGH = [".....KKK", "....KGLK", "...KGGGK", "..KGGGK.", ".KGGGK..", "KGGGK...", "GGGK....", "KKK....."]
HAND_UP = [".KKK.", "KGLGK", "KGGGK", "KGGGK", "KGGK.", "KGGK.", "KGGK.", "GGGK.", "KKK.."]
# coçando a cabeça: braço dobrado por cima do topo (raiz embaixo à direita)
ITCH_A = ["..KKKK..", ".KGGLGK.", "KGGGGGGK", "KGKKKGGK", "KK..KGGK", "....KGGK", "....KGGK", "....GGGK", "....KKK."]
ITCH_B = [".KKKK...", "KGLGGK..", "KGGGGGK.", ".KKKGGGK", "....KGGK", "....KGGK", "....KGGK", "....GGGK", "....KKK."]
TRAIL_1 = ["KKKKKK", "DDDDDK", "KKKKKK"]
TRAIL_2 = ["KKK", "DDK", "KKK"]




def _bedsheet(w, h, cx, base, lean, phase):
    """Domo em cima, laterais retas e barra com 3 pontas ondulando (`fase`); `lean` desloca o topo."""
    pts = set()
    r = w / 2
    top = base - h + 1
    for y in range(top, base + 1):
        u = (base - y) / h
        d = y - top
        half = r if d >= r else (r * r - (r - d - 0.5) ** 2) ** 0.5
        c = cx + lean * u
        for x in range(round(c - half), round(c + half)):
            wave = 1.6 + 1.6 * math.sin(2 * math.pi * (x - c) / (w / 3) + phase)
            if 0 < x < N - 1 and y <= base - round(wave):
                pts.add((x, y))
    return pts


def frame(w=20, h=24, cx=16, base=30, lean=0, phase=0.0, eyes="normal", look=0, mouth="sorriso",
           cheek=True, por=(), holes=(), some=0):
    """Um quadro 32x32 e a âncora (topo da cabeça) para o acréscimo do estágio."""
    g = [["."] * N for _ in range(N)]
    pts = _bedsheet(w, h, cx, base, lean, phase)
    for bx, by, br in holes:
        pts -= {(x, y) for x, y in pts if (x - bx) ** 2 + (y - by) ** 2 <= br * br}
    top = min(y for _, y in pts)
    xs_top = sorted(x for x, y in pts if y == top)
    for x, y in pts:
        dir_ = (x + 1, y) not in pts or (x + 2, y) not in pts
        low = (x, y + 1) not in pts or (x, y + 2) not in pts
        g[y][x] = "D" if (dir_ or low) else "G"
    for x, y in pts:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in pts and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # brilho no alto à esquerda
    bx, by = round(cx + lean * 0.8 - w * 0.25), top + 2
    for x, y in ((bx, by), (bx + 1, by - 1), (bx, by + 1), (bx, by + 2)):
        if (x, y) in pts and g[y][x] == "G":
            g[y][x] = "L"
    if some:   # sumindo (antes do rosto, que fica nítido): xadrez de baixo para cima (1/4, 1/2); some >= 3 deixa o fim ralo (1 em 4)
        corte = base - h * min(some, 2) // 4
        for y in range(N):
            for x in range(N):
                if g[y][x] != "." and y > corte and ((x + y) % 2 or (some >= 3 and y > corte + 4 and y % 2)):
                    g[y][x] = "."
    ey = top + max(3, int(h * 0.27))
    fx = round(cx + lean * (base - ey) / h) + look
    lx, rx = fx - 6, fx + 2
    if eyes == "fechado":
        stamp(g, EYE_CLOSED, lx, ey); stamp(g, EYE_CLOSED, rx, ey)
    elif eyes == "feliz":
        stamp(g, EYE_HAPPY, lx, ey + 1); stamp(g, EYE_HAPPY, rx, ey + 1)
    elif eyes == "x":
        stamp(g, EYE_X, lx, ey); stamp(g, EYE_X, rx, ey)
    elif eyes == "cima":
        stamp(g, EYE_UP, lx, ey - 1); stamp(g, EYE_UP, rx, ey - 1)
    else:
        stamp(g, EYE, lx, ey); stamp(g, EYE, rx, ey)
        if eyes == "bravo":
            stamp(g, BROW_ANGRY, lx - 1, ey - 2); stamp(g, mirror(BROW_ANGRY), rx, ey - 2)
        elif eyes == "triste":
            stamp(g, BROW_SAD, lx - 1, ey - 2); stamp(g, mirror(BROW_SAD), rx, ey - 2)
    if mouth:
        b = MOUTH[mouth]
        stamp(g, b, fx - len(b[0]) // 2, ey + 6)
    if cheek and eyes in ("normal", "feliz", "fechado"):
        for x in (lx - 2, lx - 1, rx + 4, rx + 5):
            if (x, ey + 5) in pts:
                g[ey + 5][x] = "P"
    for s, x, y in por:
        stamp(g, s, x, y)
    cxt = (xs_top[0] + xs_top[-1]) // 2
    return ["".join(l) for l in g], (cxt - 7, ey - 11)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


_F = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
_SPECS = {
    # flutua devagar, barra ondulando; pisca no 3º quadro
    "idle": [dict(base=30, phase=_F[0]), dict(base=29, phase=_F[1]),
             dict(base=29, phase=_F[2], eyes="fechado"), dict(base=30, phase=_F[3])],
    # inclina para frente, olhar adiante, rastro de lençol ficando para trás
    "run_r": [dict(cx=18, lean=4, look=2, phase=_F[0], por=((TRAIL_1, 2, 22), (TRAIL_2, 0, 26))),
              dict(cx=18, lean=5, look=2, base=29, phase=_F[1], por=((TRAIL_1, 1, 20), (TRAIL_2, 3, 26))),
              dict(cx=18, lean=4, look=2, phase=_F[2], por=((TRAIL_2, 2, 21), (TRAIL_1, 0, 25))),
              dict(cx=18, lean=5, look=2, base=29, phase=_F[3], por=((TRAIL_1, 2, 24), (TRAIL_2, 1, 19)))],
    # mãozinha de lençol sai à direita e acena
    "waving": [dict(cx=13, eyes="feliz", mouth="buu", phase=_F[0], por=((HAND_LOW, 22, 17),)),
               dict(cx=13, eyes="feliz", mouth="buu", phase=_F[1], por=((HAND_STRAIGHT, 22, 14),)),
               dict(cx=13, eyes="feliz", mouth="buu", phase=_F[2], por=((HAND_HIGH, 22, 8),)),
               dict(cx=13, eyes="feliz", mouth="buu", phase=_F[3], por=((HAND_UP, 22, 6),))],
    # encolhe, dispara para cima, no alto abre os braços, desce, pousa
    "jumping": [dict(w=24, h=22, eyes="fechado", mouth="reta"),
                dict(w=16, h=24, base=30, mouth="o", phase=_F[1]),
                dict(w=20, h=21, base=27, eyes="feliz", mouth="buu", phase=_F[2]),
                dict(w=18, h=22, base=29, mouth="o", phase=_F[3]),
                dict(w=23, h=20, eyes="feliz")],
    # triste, abre buracos no lençol e some aos poucos
    "failed": [dict(eyes="triste", mouth="triste", por=((TEAR, 10, 17),)),
               dict(eyes="triste", mouth="triste", phase=_F[1], holes=((12, 27, 1.5), (21, 24, 1.2))),
               dict(eyes="triste", mouth="reta", phase=_F[2], holes=((12, 27, 2), (21, 24, 1.8), (16, 20, 1)), some=1),
               dict(eyes="fechado", mouth=None, cheek=False, phase=_F[3],
                    holes=((12, 27, 2.5), (21, 24, 2.2), (16, 20, 1.5)), some=2),
               dict(eyes="x", mouth=None, cheek=False, base=30, holes=((21, 22, 2),), some=3)],
    # cochila flutuando de lado, "z" subindo
    "waiting": [dict(cx=14, lean=-2, eyes="fechado", mouth=None, base=30),
                dict(cx=14, lean=-3, eyes="fechado", mouth=None, base=29, phase=_F[1], por=((Z_S, 22, 6),)),
                dict(cx=14, lean=-3, eyes="fechado", mouth="o", base=29, phase=_F[2], por=((Z_S, 22, 6), (Z_L, 26, 0))),
                dict(cx=14, lean=-2, eyes="fechado", mouth=None, base=29, phase=_F[3], por=((Z_L, 26, 0),))],
    # recua e avança de boca aberta: "Buu!"
    "running": [dict(cx=14, lean=-3, eyes="bravo", mouth="reta"),
                dict(cx=17, lean=5, look=1, eyes="bravo", mouth="buu", phase=_F[1], por=((TRAIL_2, 3, 22),)),
                dict(cx=18, lean=6, look=1, w=21, eyes="bravo", mouth="buu_g", phase=_F[2],
                     por=((TRAIL_1, 1, 20), (EXCLAM, 28, 2))),
                dict(cx=16, lean=3, look=2, eyes="bravo", mouth="buu", phase=_F[3], por=((EXCLAM, 28, 3),))],
    # coça a cabeça e o "?" aparece
    "review": [dict(cx=14, eyes="cima", mouth="torta"),
               dict(cx=14, eyes="cima", mouth="torta", phase=_F[1], por=((ITCH_A, 17, 4), (QMARK_S, 26, 4))),
               dict(cx=14, eyes="cima", mouth="o", phase=_F[2], por=((ITCH_B, 17, 4), (QMARK, 25, 0))),
               dict(cx=14, eyes="cima", mouth="o", phase=_F[3], por=((ITCH_A, 17, 4), (QMARK, 25, 0)))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# chapéu: 5 linhas de cone acima da cabeça + aba (âncora = olhos - 11; no lençol alto a aba cai no topo)
HAT = [
    ".........KK...",
    ".......KKHK...",
    ".....KKHHYK...",
    "....KHHYHHHK..",
    "...KHHhhhhHHK.",
    ".KKhhhhhhhhhhK",
    "KhhhhhhhhhhhhK",
    ".KKKKKKKKKKKK.",
]
# correntinha no pescoço, logo abaixo da boca mais aberta ("buu"), presa na mesma âncora
CHAIN = ["." * 14] * 22 + [
    "KsKsKsKsKsKsKs",
    "......KK......",
    ".....KYYK.....",
    "......KK......",
]
MAGE = [HAT[i] if i < len(HAT) else CHAIN[i] for i in range(len(CHAIN))]
STAGES = [
    {"title": "Fantasminha", "floor": 1, "extra": None},
    {"title": "Fantasma", "floor": 4, "extra": CHAIN},
    {"title": "Fantasma Mago", "floor": 10, "extra": MAGE},
]
