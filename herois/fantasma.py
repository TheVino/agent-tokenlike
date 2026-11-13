"""Fantasma, 32 px. Cada quadro sai de partes: lençol (domo com barra ondulada, contorno, sombra e brilho),
rosto (olhos, boca, bochechas) e sobreposições (mãozinha de lençol, rastro, "z", "?", buracos, sumiço).
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
import math
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, EXCLAM, LAGRIMA, espelho, carimbar

PAL = {
    "K": "#2a2140", "G": "#f2f0ff", "D": "#c6c0e8", "L": "#ffffff", "B": "#2a2140", "W": "#ffffff",
    "P": "#ff9ec4", "R": "#c8304a", "H": "#7b5cc9", "h": "#4f3a8f", "Y": "#ffd23f", "y": "#c99a00",
    "T": "#8fd8ff", "S": "#d7dde9", "s": "#8a94a8",
}

OLHO = [".BB.", "BWBB", "BBBB", "BBBB", ".BB."]
OLHO_FECHADO = ["....", "B..B", ".BB."]       # meia-lua para baixo (sono)
OLHO_FELIZ = [".BB.", "B..B"]
OLHO_X = ["B..B", ".BB.", ".BB.", "B..B"]
OLHO_CIMA = [".BB.", "BWBB", "BBBB", "...."]
SOBR_BRAVA = ["BB...", "..BBB"]
SOBR_TRISTE = ["...BB", "BBB.."]
BOCA = {
    "sorriso": ["B...B", ".BBB."],
    "buu": [".BBB.", "BRRRB", "BRRRB", "BRPRB", ".BBB."],
    "buu_g": [".BBBB.", "BRRRRB", "BRRRRB", "BRRRRB", "BRPPRB", ".BBBB."],
    "o": [".B.", "B.B", ".B."],
    "triste": [".BBB.", "B...B"],
    "reta": ["BBB"],
    "torta": ["BB..", "..BB"],
}

# mãozinha de lençol (raiz à esquerda, colada no corpo): baixa, reta, alta, no alto acenando
MAO_BAIXA = ["KK.......", "GGKK.....", "GGGGKK...", "KGGGGGKK.", ".KKGGGGLK", "...KKGGGK", ".....KKK."]
MAO_RETA = ["......KKK.", "KKKKKKGGLK", "GGGGGGGGGK", "GGGGGGGGDK", "KKKKKKKKK."]
MAO_ALTA = [".....KKK", "....KGLK", "...KGGGK", "..KGGGK.", ".KGGGK..", "KGGGK...", "GGGK....", "KKK....."]
MAO_CIMA = [".KKK.", "KGLGK", "KGGGK", "KGGGK", "KGGK.", "KGGK.", "KGGK.", "GGGK.", "KKK.."]
# coçando a cabeça: braço dobrado por cima do topo (raiz embaixo à direita)
COCA_A = ["..KKKK..", ".KGGLGK.", "KGGGGGGK", "KGKKKGGK", "KK..KGGK", "....KGGK", "....KGGK", "....GGGK", "....KKK."]
COCA_B = [".KKKK...", "KGLGGK..", "KGGGGGK.", ".KKKGGGK", "....KGGK", "....KGGK", "....KGGK", "....GGGK", "....KKK."]
RASTRO_1 = ["KKKKKK", "DDDDDK", "KKKKKK"]
RASTRO_2 = ["KKK", "DDK", "KKK"]




def _lencol(w, h, cx, base, lean, fase):
    """Domo em cima, laterais retas e barra com 3 pontas ondulando (`fase`); `lean` desloca o topo."""
    pts = set()
    r = w / 2
    top = base - h + 1
    for y in range(top, base + 1):
        u = (base - y) / h
        d = y - top
        meia = r if d >= r else (r * r - (r - d - 0.5) ** 2) ** 0.5
        c = cx + lean * u
        for x in range(round(c - meia), round(c + meia)):
            onda = 1.6 + 1.6 * math.sin(2 * math.pi * (x - c) / (w / 3) + fase)
            if 0 < x < N - 1 and y <= base - round(onda):
                pts.add((x, y))
    return pts


def quadro(w=20, h=24, cx=16, base=30, lean=0, fase=0.0, olhos="normal", olhar=0, boca="sorriso",
           bochecha=True, por=(), buracos=(), some=0):
    """Um quadro 32x32 e a âncora (topo da cabeça) para o acréscimo do estágio."""
    g = [["."] * N for _ in range(N)]
    pts = _lencol(w, h, cx, base, lean, fase)
    for bx, by, br in buracos:
        pts -= {(x, y) for x, y in pts if (x - bx) ** 2 + (y - by) ** 2 <= br * br}
    top = min(y for _, y in pts)
    xs_top = sorted(x for x, y in pts if y == top)
    for x, y in pts:
        dir_ = (x + 1, y) not in pts or (x + 2, y) not in pts
        baixo = (x, y + 1) not in pts or (x, y + 2) not in pts
        g[y][x] = "D" if (dir_ or baixo) else "G"
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
    fx = round(cx + lean * (base - ey) / h) + olhar
    lx, rx = fx - 6, fx + 2
    if olhos == "fechado":
        carimbar(g, OLHO_FECHADO, lx, ey); carimbar(g, OLHO_FECHADO, rx, ey)
    elif olhos == "feliz":
        carimbar(g, OLHO_FELIZ, lx, ey + 1); carimbar(g, OLHO_FELIZ, rx, ey + 1)
    elif olhos == "x":
        carimbar(g, OLHO_X, lx, ey); carimbar(g, OLHO_X, rx, ey)
    elif olhos == "cima":
        carimbar(g, OLHO_CIMA, lx, ey - 1); carimbar(g, OLHO_CIMA, rx, ey - 1)
    else:
        carimbar(g, OLHO, lx, ey); carimbar(g, OLHO, rx, ey)
        if olhos == "bravo":
            carimbar(g, SOBR_BRAVA, lx - 1, ey - 2); carimbar(g, espelho(SOBR_BRAVA), rx, ey - 2)
        elif olhos == "triste":
            carimbar(g, SOBR_TRISTE, lx - 1, ey - 2); carimbar(g, espelho(SOBR_TRISTE), rx, ey - 2)
    if boca:
        b = BOCA[boca]
        carimbar(g, b, fx - len(b[0]) // 2, ey + 6)
    if bochecha and olhos in ("normal", "feliz", "fechado"):
        for x in (lx - 2, lx - 1, rx + 4, rx + 5):
            if (x, ey + 5) in pts:
                g[ey + 5][x] = "P"
    for s, x, y in por:
        carimbar(g, s, x, y)
    cxt = (xs_top[0] + xs_top[-1]) // 2
    return ["".join(l) for l in g], (cxt - 7, ey - 11)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


_F = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
_SPECS = {
    # flutua devagar, barra ondulando; pisca no 3º quadro
    "idle": [dict(base=30, fase=_F[0]), dict(base=29, fase=_F[1]),
             dict(base=29, fase=_F[2], olhos="fechado"), dict(base=30, fase=_F[3])],
    # inclina para frente, olhar adiante, rastro de lençol ficando para trás
    "run_r": [dict(cx=18, lean=4, olhar=2, fase=_F[0], por=((RASTRO_1, 2, 22), (RASTRO_2, 0, 26))),
              dict(cx=18, lean=5, olhar=2, base=29, fase=_F[1], por=((RASTRO_1, 1, 20), (RASTRO_2, 3, 26))),
              dict(cx=18, lean=4, olhar=2, fase=_F[2], por=((RASTRO_2, 2, 21), (RASTRO_1, 0, 25))),
              dict(cx=18, lean=5, olhar=2, base=29, fase=_F[3], por=((RASTRO_1, 2, 24), (RASTRO_2, 1, 19)))],
    # mãozinha de lençol sai à direita e acena
    "waving": [dict(cx=13, olhos="feliz", boca="buu", fase=_F[0], por=((MAO_BAIXA, 22, 17),)),
               dict(cx=13, olhos="feliz", boca="buu", fase=_F[1], por=((MAO_RETA, 22, 14),)),
               dict(cx=13, olhos="feliz", boca="buu", fase=_F[2], por=((MAO_ALTA, 22, 8),)),
               dict(cx=13, olhos="feliz", boca="buu", fase=_F[3], por=((MAO_CIMA, 22, 6),))],
    # encolhe, dispara para cima, no alto abre os braços, desce, pousa
    "jumping": [dict(w=24, h=22, olhos="fechado", boca="reta"),
                dict(w=16, h=24, base=30, boca="o", fase=_F[1]),
                dict(w=20, h=21, base=27, olhos="feliz", boca="buu", fase=_F[2]),
                dict(w=18, h=22, base=29, boca="o", fase=_F[3]),
                dict(w=23, h=20, olhos="feliz")],
    # triste, abre buracos no lençol e some aos poucos
    "failed": [dict(olhos="triste", boca="triste", por=((LAGRIMA, 10, 17),)),
               dict(olhos="triste", boca="triste", fase=_F[1], buracos=((12, 27, 1.5), (21, 24, 1.2))),
               dict(olhos="triste", boca="reta", fase=_F[2], buracos=((12, 27, 2), (21, 24, 1.8), (16, 20, 1)), some=1),
               dict(olhos="fechado", boca=None, bochecha=False, fase=_F[3],
                    buracos=((12, 27, 2.5), (21, 24, 2.2), (16, 20, 1.5)), some=2),
               dict(olhos="x", boca=None, bochecha=False, base=30, buracos=((21, 22, 2),), some=3)],
    # cochila flutuando de lado, "z" subindo
    "waiting": [dict(cx=14, lean=-2, olhos="fechado", boca=None, base=30),
                dict(cx=14, lean=-3, olhos="fechado", boca=None, base=29, fase=_F[1], por=((Z_P, 22, 6),)),
                dict(cx=14, lean=-3, olhos="fechado", boca="o", base=29, fase=_F[2], por=((Z_P, 22, 6), (Z_G, 26, 0))),
                dict(cx=14, lean=-2, olhos="fechado", boca=None, base=29, fase=_F[3], por=((Z_G, 26, 0),))],
    # recua e avança de boca aberta: "Buu!"
    "running": [dict(cx=14, lean=-3, olhos="bravo", boca="reta"),
                dict(cx=17, lean=5, olhar=1, olhos="bravo", boca="buu", fase=_F[1], por=((RASTRO_2, 3, 22),)),
                dict(cx=18, lean=6, olhar=1, w=21, olhos="bravo", boca="buu_g", fase=_F[2],
                     por=((RASTRO_1, 1, 20), (EXCLAM, 28, 2))),
                dict(cx=16, lean=3, olhar=2, olhos="bravo", boca="buu", fase=_F[3], por=((EXCLAM, 28, 3),))],
    # coça a cabeça e o "?" aparece
    "review": [dict(cx=14, olhos="cima", boca="torta"),
               dict(cx=14, olhos="cima", boca="torta", fase=_F[1], por=((COCA_A, 17, 4), (INTERROG_P, 26, 4))),
               dict(cx=14, olhos="cima", boca="o", fase=_F[2], por=((COCA_B, 17, 4), (INTERROG, 25, 0))),
               dict(cx=14, olhos="cima", boca="o", fase=_F[3], por=((COCA_A, 17, 4), (INTERROG, 25, 0)))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# chapéu: 5 linhas de cone acima da cabeça + aba (âncora = olhos - 11; no lençol alto a aba cai no topo)
CHAPEU = [
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
CORRENTE = ["." * 14] * 22 + [
    "KsKsKsKsKsKsKs",
    "......KK......",
    ".....KYYK.....",
    "......KK......",
]
MAGO = [CHAPEU[i] if i < len(CHAPEU) else CORRENTE[i] for i in range(len(CORRENTE))]
ESTAGIOS = [
    {"title": "Fantasminha", "floor": 1, "extra": None},
    {"title": "Fantasma", "floor": 4, "extra": CORRENTE},
    {"title": "Fantasma Mago", "floor": 10, "extra": MAGO},
]
