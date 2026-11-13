"""Slime embutido, 32 px. Cada quadro sai de partes: corpo (domo paramétrico com contorno, sombra e brilho),
rosto (olhos, boca, bochechas) e sobreposições (gotinha, bracinho, "z", "?", poça).
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""

N = 32
PAL = {
    "K": "#1b1b2f", "G": "#57d36b", "L": "#b4f5a8", "D": "#2f9a4a",
    "W": "#ffffff", "B": "#1b1b2f", "P": "#ff8fb1", "R": "#c8304a",
    "S": "#d7dde9", "s": "#8a94a8", "Y": "#ffd23f", "y": "#c99a00", "T": "#8fd8ff",
}

# ---- partes do rosto (olho esquerdo; o direito é o espelho, menos onde o brilho tem de ficar do mesmo lado)
OLHO = ["WB", "BB", "BB", "BB"]
OLHO_FECHADO = ["...", "...", "BBB"]
OLHO_FELIZ = [".B.", "B.B"]
OLHO_X = ["B.B", ".B.", "B.B"]
OLHO_CIMA = ["WB", "BB", ".."]
SOBR_BRAVA = ["BB..", "..BB"]          # esquerda: desce para dentro
SOBR_TRISTE = ["..BB", "BB.."]         # esquerda: desce para fora
BOCA = {
    "sorriso": ["B..B", ".BB."],
    "aberta": ["BBBBB", "BRRRB", "BRPRB", ".BBB."],
    "dentes": ["BBBBB", "BWBWB", ".BBB."],
    "o": [".B.", "B.B", ".B."],
    "triste": [".BB.", "B..B"],
    "reta": ["BBB"],
}

GOTA = [".K.", "KGK", "KDK", ".K."]
GOTA_P = ["K", "K"]
BRACO_CIMA = ["...KK.", "..KGLK", ".KGGK.", "KGGK..", "KGGK..", "KGK..."]
BRACO_MEIO = [".....KK", "...KKGLK", "KKKGGGK.", "KGGGKK..", "KGK....."]
BRACO_BAIXO = ["KKK.....", "KGGKK...", ".KKGGKK.", "...KKGLK", ".....KK."]
Z_P = ["TT", ".T", "TT"]
Z_G = ["TTT", "..T", ".T.", "T..", "TTT"]
PERG_P = [".TT", "...", ".T."]
PERG = [".TTT.", "TT.TT", "...TT", "..TT.", "..T..", ".....", "..T.."]
LAGRIMA = ["T", "T"]


def _espelho(s):
    return [l[::-1] for l in s]


def _por(g, s, x, y):
    for dy, lin in enumerate(s):
        for dx, ch in enumerate(lin):
            if ch != "." and 0 <= x + dx < N and 0 <= y + dy < N:
                g[y + dy][x + dx] = ch


def _corpo(w, h, cx, base, lean):
    """Domo: largo embaixo, redondo em cima; `lean` desloca o topo (inclinar para frente ou pender)."""
    pts = set()
    for y in range(base - h + 1, base + 1):
        u = (base - y) / h                      # 0 na base, ~1 no topo
        meia = w / 2 * (1 - u ** 2.4) ** 0.5
        c = cx + lean * u
        for x in range(round(c - meia), round(c + meia)):
            if 0 < x < N - 1:
                pts.add((x, y))
    return pts


def quadro(w, h, cx=16, base=30, lean=0, olhos="normal", olhar=0, boca="sorriso", bochecha=True, por=()):
    """Um quadro 32x32 e a âncora (topo do corpo) para o acréscimo do estágio."""
    g = [["."] * N for _ in range(N)]
    pts = _corpo(w, h, cx, base, lean)
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
    fx = round(cx + lean * (base - ey) / h) + olhar
    lx, rx = fx - 5, fx + 3
    if olhos == "fechado":
        _por(g, OLHO_FECHADO, lx - 1, ey); _por(g, OLHO_FECHADO, rx, ey)
    elif olhos == "feliz":
        _por(g, OLHO_FELIZ, lx - 1, ey + 1); _por(g, OLHO_FELIZ, rx, ey + 1)
    elif olhos == "x":
        _por(g, OLHO_X, lx - 1, ey); _por(g, OLHO_X, rx, ey)
    elif olhos == "cima":
        _por(g, OLHO_CIMA, lx, ey - 1); _por(g, OLHO_CIMA, rx, ey - 1)
    else:
        _por(g, OLHO, lx, ey); _por(g, OLHO, rx, ey)
        if olhos == "bravo":
            _por(g, SOBR_BRAVA, lx - 2, ey - 3); _por(g, _espelho(SOBR_BRAVA), rx, ey - 3)
        elif olhos == "triste":
            _por(g, SOBR_TRISTE, lx - 2, ey - 3); _por(g, _espelho(SOBR_TRISTE), rx, ey - 3)
    if boca:
        b = BOCA[boca]
        _por(g, b, fx - len(b[0]) // 2, ey + 5)
    if bochecha and olhos in ("normal", "feliz", "fechado"):
        for x in (lx - 3, lx - 2, rx + 3, rx + 4):
            if (x, ey + 4) in pts:
                g[ey + 4][x] = "P"
    for s, x, y in por:
        _por(g, s, x, y)
    cxt = (xs_top[0] + xs_top[-1]) // 2
    return ["".join(l) for l in g], (cxt - 5, top - 4)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


_SPECS = {
    # respira (estica e encolhe) e pisca no 3º quadro
    "idle": [dict(w=24, h=18), dict(w=25, h=17), dict(w=25, h=17, olhos="fechado"), dict(w=23, h=19)],
    # estica para frente, olhos na direção, gotinha ficando para trás
    "run_r": [dict(w=24, h=16, cx=18, lean=4, olhar=2, por=((GOTA, 2, 25),)),
              dict(w=23, h=18, cx=18, lean=3, olhar=2, por=((GOTA, 0, 26), (GOTA_P, 4, 29))),
              dict(w=25, h=15, cx=17, lean=5, olhar=3, por=((GOTA_P, 2, 29),)),
              dict(w=24, h=17, cx=18, lean=4, olhar=2, por=((GOTA, 3, 26),))],
    # bracinho de gosma sai do lado direito e balança
    "waving": [dict(w=24, h=18, cx=14, olhos="feliz", boca="aberta", por=((BRACO_MEIO, 22, 17),)),
               dict(w=24, h=18, cx=14, olhos="feliz", boca="aberta", por=((BRACO_CIMA, 24, 13),)),
               dict(w=24, h=18, cx=14, olhos="feliz", boca="aberta", por=((BRACO_MEIO, 22, 17),)),
               dict(w=24, h=18, cx=14, olhos="feliz", boca="aberta", por=((BRACO_BAIXO, 23, 19),))],
    # agacha, estica no ar, alto, cai, achata ao cair
    "jumping": [dict(w=28, h=12, olhos="fechado", boca="reta"),
                dict(w=18, h=23, base=27, boca="o"),
                dict(w=22, h=19, base=22, olhos="feliz", boca="aberta"),
                dict(w=20, h=21, base=29, boca="o"),
                dict(w=28, h=11, olhos="feliz")],
    # derrete numa poça; olhos em X no último
    "failed": [dict(w=24, h=18, olhos="triste", boca="triste", por=((LAGRIMA, 9, 21),)),
               dict(w=26, h=14, olhos="triste", boca="triste", por=((GOTA, 1, 27), (GOTA, 28, 27))),
               dict(w=28, h=10, olhos="triste", boca="reta", por=((GOTA_P, 0, 29), (GOTA_P, 31, 29))),
               dict(w=30, h=7, olhos="fechado", boca=None, bochecha=False),
               dict(w=30, h=7, olhos="x", boca=None)],
    # cabeça pende de lado, olhos fechados, "z" subindo
    "waiting": [dict(w=25, h=17, cx=14, lean=-2, olhos="fechado", boca=None),
                dict(w=26, h=16, cx=14, lean=-4, olhos="fechado", boca=None, por=((Z_P, 22, 11),)),
                dict(w=26, h=16, cx=14, lean=-4, olhos="fechado", boca="o", por=((Z_P, 23, 8), (Z_G, 26, 3))),
                dict(w=25, h=17, cx=14, lean=-3, olhos="fechado", boca=None, por=((Z_G, 27, 1),))],
    # investe e morde: recua, avança de boca aberta, fecha os dentes
    "running": [dict(w=25, h=16, cx=15, lean=-3, olhos="bravo", boca="reta"),
                dict(w=26, h=16, cx=16, lean=5, olhar=3, olhos="bravo", boca="aberta"),
                dict(w=26, h=17, cx=16, lean=4, olhar=3, olhos="bravo", boca="dentes"),
                dict(w=24, h=18, cx=15, lean=1, olhar=1, olhos="bravo", boca="aberta")],
    # olha para cima e o "?" aparece
    "review": [dict(w=24, h=18, cx=14, olhos="cima", boca="reta"),
               dict(w=24, h=18, cx=14, olhos="cima", boca="o", por=((PERG_P, 24, 8),)),
               dict(w=23, h=19, cx=14, olhos="cima", boca="o", por=((PERG, 24, 3),)),
               dict(w=24, h=18, cx=14, olhos="cima", boca="o", por=((PERG, 24, 2),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

BLINK = QUADROS["idle"][2]     # quadro do idle com os olhos fechados

ELMO = [
    "...KKKK...",
    "..KSSSSK..",
    ".KSSSSSsK.",
    "KSSRSSSSsK",
    "KKKKKKKKKK",
]
COROA = [
    ".K...K...K.",
    "KYK.KYK.KYK",
    "KYYKYRYKYYK",
    "KYYYYYYYYYK",
    "KyyyyyyyyyK",
    ".KKKKKKKKK.",
]
ESTAGIOS = [
    {"title": "Gotinha", "floor": 1, "extra": None},
    {"title": "Slime", "floor": 4, "extra": ELMO},
    {"title": "Rei Slime", "floor": 10, "extra": COROA},
]
