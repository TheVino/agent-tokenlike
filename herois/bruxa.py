"""Bruxa do Pântano, 32 px, olhando para a direita. Cada quadro sai de partes: vestido em sino roxo, cabeça verde-clara
com nariz pontudo e cabelo de musgo atrás, chapéu de ponta torta (segue a inclinação do corpo), botinhas, braços em
linha grossa e a concha de pau com caldo do brejo. No `failed` ela derrete numa poça verde e só sobra o chapéu.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar

PAL = {
    "K": "#1c1a2a", "R": "#5f3f86", "r": "#3f2a5e", "G": "#b3dc8e", "g": "#7fae66", "L": "#3d6e45",
    "H": "#33402f", "h": "#232c21", "U": "#b06ad8", "N": "#8a5a36", "V": "#a6e86b", "v": "#4c8a3a",
    "W": "#ffffff", "B": "#1c1a2a", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f", "k": "#2c2440",
    "O": "#ff8a3d", "S": "#7d7790",
}

BOLHA = [".KK.", "KVVK", "KvVK", ".KK."]
BOLHA_P = ["KK", "KK"]
GOTA = [".KKK.", "KVVVK", "KVWVK", "KvVVK", ".KKK."]
# caldo voando com fogo verde (o traço é queimar)
FEITICO = ["...KK.KK..", "..KVKKYK..", ".KVVVKYOK.", "KVVWVVKOK.", "KVVVVvVVK.", "KvVVVVVvK.", ".KVvVVVK..", "..KKKKK..."]
RESPINGO = ["..KK...KK.", ".KYOK.KVK.", "KVYOVKKVVK", "KVVVVVVvK.", ".KVvVVVVVK", "KVVVYVvVK.", ".KKVVOVKK.", "...KKKKK.."]
MAO = ["KKK", "KGK", "KKK"]


def _linha(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)]


def _traco(g, a, b, cor, grosso=1):
    pts = _linha(*a, *b)
    r = range(-grosso, grosso + 1)
    for x, y in pts:
        for dx in r:
            for dy in r:
                if 0 <= x + dx < N and 0 <= y + dy < N:
                    g[y + dy][x + dx] = "K"
    for x, y in pts:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = cor


def _concha(g, mao, ponta, cheia=True):
    """Cabo de pau da mão até a ponta e a concha (3x3, com caldo) na ponta."""
    _traco(g, mao, ponta, "N")
    px, py = ponta
    carimbar(g, [".KKK.", "KVVVK" if cheia else "KNNNK", "KvVvK" if cheia else "KNNNK", ".KKK."], px - 2, py - 2)


def _chapeu(g, bx, by, torto=0):
    """Chapéu de bruxa com aba em (bx, by) e ponta torta para trás; `torto` empurra a ponta (acompanha o corpo)."""
    px = {}
    for x in range(bx - 8, bx + 9):          # aba
        px[(x, by)] = "H"
        if abs(x - bx) < 8:
            px[(x, by + 1)] = "h"
    for i in range(1, 10):                   # copa: afina e entorta para trás
        meia = max(0, round(4.5 - i * 0.5))
        c = bx - round(i * i / 14) + round(torto * i / 9)
        for x in range(c - meia, c + meia + 1):
            px[(x, by - i)] = "h" if x == c - meia and meia else "H"
    tip = bx - round(81 / 14) + torto
    px[(tip - 1, by - 9)] = px[(tip - 2, by - 8)] = "H"   # pontinha caída
    for x in range(bx - 4, bx + 5):          # fita roxa
        px[(x, by - 1)] = "U"
    for (x, y) in px:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in px and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for (x, y), c in px.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c
    g[by - 1][bx + 2] = "Y"                  # fivela


def _rosto(g, hx, hy, olhos):
    """Rosto enxuto: dois olhos (blocos 2x2, ou traço/arco) e uma boquinha; sem brilho nem bochecha soltos."""
    ex, ey = hx + 1, hy - 1
    for x in (ex - 2, ex + 2):
        if olhos == "fechado":
            carimbar(g, ["BB"], x, ey + 1)
        elif olhos == "feliz":
            carimbar(g, [".B.", "B.B"], x - (x > ex), ey)
        elif olhos == "x":
            carimbar(g, ["B.B", ".B.", "B.B"], x - (x > ex), ey - 1)
        else:
            carimbar(g, ["BB", "BB"], x, ey - (olhos == "cima"))
            if olhos == "bravo":
                carimbar(g, ["BB."] if x < ex else [".BB"], x - (x < ex), ey - 2)
            if olhos == "triste":
                carimbar(g, [".BB"] if x < ex else ["BB."], x - (x < ex), ey - 2)
    boca = {"feliz": ["B..B", ".BB."], "triste": [".BB.", "B..B"], "bravo": [".BB.", "B..B"]}.get(olhos, [".BB."])
    carimbar(g, boca, ex - 1, ey + 3)


def _poca(g, cx, y, meia, olhos=False):
    """Poça de brejo: elipse rasa verde com bolhas; `olhos` desenha dois olhinhos tristes nela."""
    px = set()
    for dy, f in ((0, 0.6), (1, 1.0), (2, 0.85)):
        w = round(meia * f)
        px |= {(x, y + dy) for x in range(cx - w, cx + w + 1)}
    for x, yy in px:
        for nx, ny in ((x + 1, yy), (x - 1, yy), (x, yy + 1), (x, yy - 1)):
            if (nx, ny) not in px and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for x, yy in px:
        if 0 <= x < N and 0 <= yy < N:
            g[yy][x] = "v" if yy == y + 2 else "V"
    for x in range(cx - meia + 2, cx + meia - 1, 4):
        if 0 <= x < N:
            g[y + 1][x] = "W"
    if olhos:
        carimbar(g, ["B.B", ".B."], cx - 3, y)
        carimbar(g, ["B.B", ".B."], cx + 1, y)


def quadro(cx=14, base=30, ch=8, lean=0, olhos="normal", pes=(0, 0), torto=0, atras=(), bracos=(), conchas=(),
           por=(), derrete=0, chapeu=None):
    """Um quadro 32x32 e a âncora do acréscimo (presa à aba do chapéu). `derrete` 0..3 afunda o corpo numa poça;
    `chapeu` (bx, by) solta o chapéu; `bracos`: ((x0, y0), (x1, y1)) mangas com mão; `conchas`: (mão, ponta, cheia)."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    if derrete >= 3:                          # só a poça e o chapéu
        _poca(g, cx, base - 3, 11, olhos=True)
        bx, by = chapeu
        _chapeu(g, bx, by, torto)
        for s, x, y in por:
            carimbar(g, s, x, y)
        return ["".join(l) for l in g], (bx - 12, by - 10)
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 4
    if derrete:
        _poca(g, cx, base - 3, 6 + 3 * derrete)
    vestido = set()
    for y in range(ctop, base - 1):
        t = (y - ctop) / max(ch - 1, 1)
        meia = 3.5 + t * (3.5 + derrete)
        c = cx + lean * (1 - t)
        vestido |= {(x, y) for x in range(round(c - meia), round(c + meia) + 1)}
    cabeca = {(x, y) for x in range(hx - 6, hx + 7) for y in range(hy - 6, hy + 7)
              if (x - hx) ** 2 + (y - hy) ** 2 <= 27}
    nariz = {(hx + 6, hy + 1), (hx + 7, hy + 2)}
    corpo = vestido | cabeca | nariz
    for x, y in corpo:
        if (x, y) in vestido and (x, y) not in cabeca:
            borda = (x + 1, y) not in corpo or (x, y + 1) not in corpo
            g[y][x] = "r" if borda else "R"
        elif x - hx <= -2 and (x, y) in cabeca:
            g[y][x] = "L"                     # cabelo de musgo
        else:
            g[y][x] = "g" if (x, y + 1) not in corpo and y > hy else "G"
    if not derrete:
        for i, (px, dx) in enumerate(((cx - 4, pes[0]), (cx + 2, pes[1]))):
            for x in range(px + dx, px + dx + 3):
                for y in (base - 2, base - 1):
                    corpo.add((x, y)); g[y][x] = "k"
    else:                                     # pingos escorrendo do vestido
        for x in range(cx - 4, cx + 5, 3):
            corpo.add((x, base - 2)); g[base - 2][x] = "V"
    for x, y in corpo:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in corpo and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for x in range(hx - 5, hx - 1):           # mechas caindo nos ombros
        if (x, hy + 5) in cabeca or (x, hy + 4) in cabeca:
            g[min(hy + 6, N - 1)][x] = "L" if x % 2 else g[min(hy + 6, N - 1)][x]
    _rosto(g, hx, hy, olhos)
    for a, b in bracos:
        _traco(g, a, b, "R")
        carimbar(g, MAO, b[0] - 1, b[1] - 1)
    for mao, ponta, cheia in conchas:
        _concha(g, mao, ponta, cheia)
        carimbar(g, MAO, mao[0] - 1, mao[1] - 1)
    bx, by = chapeu or (hx, hy - 4)
    _chapeu(g, bx, by, torto - lean)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (bx - 12, by - 10)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


def _c(mao, ponta, cheia=True):
    return (mao, ponta, cheia)


# ombro ~(cx + 2, ctop + 2); base=30, ch=8 -> ctop=21, cabeça hy=17, aba y=13
_SPECS = {
    # parada, mexe a concha e uma bolha sobe do caldo
    "idle": [dict(bracos=(((16, 23), (20, 24)),), conchas=(_c((20, 24), (23, 19)),)),
             dict(bracos=(((16, 23), (20, 24)),), conchas=(_c((20, 24), (24, 20)),), por=((BOLHA_P, 24, 15),)),
             dict(olhos="fechado", torto=1, bracos=(((16, 23), (20, 24)),), conchas=(_c((20, 24), (23, 19)),),
                  por=((BOLHA, 23, 11),)),
             dict(bracos=(((16, 23), (20, 24)),), conchas=(_c((20, 24), (22, 20)),), por=((BOLHA_P, 24, 8),))],
    # corre inclinada, botinhas alternando, concha para trás, ponta do chapéu balançando
    "run_r": [dict(cx=15, lean=2, pes=(-2, 2), torto=-2, bracos=(((14, 23), (9, 24)),), conchas=(_c((9, 24), (4, 21)),)),
              dict(cx=15, lean=3, base=29, torto=-4, bracos=(((14, 22), (10, 23)),), conchas=(_c((10, 23), (5, 22)),)),
              dict(cx=15, lean=2, pes=(2, -2), torto=-2, bracos=(((14, 23), (9, 24)),), conchas=(_c((9, 24), (4, 22)),)),
              dict(cx=15, lean=3, base=29, torto=-4, bracos=(((14, 22), (10, 23)),), conchas=(_c((10, 23), (5, 21)),))],
    # acena com a mão, concha na outra (atrás)
    "waving": [dict(olhos="feliz", conchas=(_c((9, 25), (5, 21)),), bracos=(((16, 23), (21, 20)),)),
               dict(olhos="feliz", torto=1, conchas=(_c((9, 25), (5, 21)),), bracos=(((16, 23), (21, 16)),)),
               dict(olhos="feliz", torto=2, conchas=(_c((9, 25), (5, 21)),), bracos=(((16, 23), (24, 16)),)),
               dict(olhos="feliz", torto=1, conchas=(_c((9, 25), (5, 21)),), bracos=(((16, 23), (21, 16)),))],
    # agacha, salta com a concha no alto, cai, pousa (o chapéu atrasa)
    "jumping": [dict(ch=6, olhos="fechado", torto=2, bracos=(((16, 25), (20, 27)),), conchas=(_c((20, 27), (24, 24)),)),
                dict(ch=9, base=29, torto=-2, bracos=(((16, 21), (22, 18)),), conchas=(_c((22, 18), (25, 13)),)),
                dict(ch=8, base=27, olhos="feliz", torto=-3, bracos=(((16, 19), (23, 16)),), conchas=(_c((23, 16), (26, 11)),)),
                dict(ch=9, base=29, torto=2, bracos=(((16, 22), (22, 21)),), conchas=(_c((22, 21), (25, 17)),)),
                dict(ch=6, olhos="feliz", torto=3, bracos=(((16, 25), (20, 26)),), conchas=(_c((20, 26), (24, 23)),))],
    # triste, derrete numa poça de brejo; o chapéu cai sobre a poça
    "failed": [dict(olhos="triste", bracos=(((16, 23), (19, 26)),), conchas=(_c((19, 26), (22, 28), False),),
                    por=((LAGRIMA, 20, 18),)),
               dict(ch=6, olhos="triste", derrete=1, por=((LAGRIMA, 20, 21), (GOTA, 21, 24))),
               dict(ch=4, olhos="fechado", derrete=2),
               dict(derrete=3, chapeu=(14, 23), torto=1, por=((BOLHA_P, 24, 22),)),
               dict(derrete=3, chapeu=(14, 23), torto=2, por=((BOLHA, 22, 19),))],
    # cochila sentada, cabeça pende, "z" subindo
    "waiting": [dict(ch=7, lean=-1, olhos="fechado", torto=2),
                dict(ch=7, lean=-2, olhos="fechado", torto=3, por=((Z_P, 23, 4),)),
                dict(ch=7, lean=-2, olhos="fechado", torto=3, por=((Z_P, 22, 4), (Z_G, 26, 0))),
                dict(ch=7, lean=-1, olhos="fechado", torto=2, por=((Z_G, 26, 0),))],
    # golpe: recua a concha, gira por cima e arremessa o caldo, que estoura em fogo verde
    "running": [dict(cx=14, lean=-2, olhos="bravo", torto=2, bracos=(((15, 23), (10, 21)),), conchas=(_c((10, 21), (5, 17)),)),
                dict(cx=14, lean=1, olhos="bravo", torto=-1, bracos=(((16, 22), (20, 16)),), conchas=(_c((20, 16), (22, 9)),)),
                dict(cx=14, lean=3, olhos="bravo", torto=-3, bracos=(((17, 23), (22, 21)),), conchas=(_c((22, 21), (27, 19), False),),
                     por=((FEITICO, 21, 6),)),
                dict(cx=14, lean=2, olhos="bravo", torto=-2, bracos=(((17, 23), (21, 24)),), conchas=(_c((21, 24), (26, 24), False),),
                     por=((RESPINGO, 21, 4), (BOLHA_P, 19, 2), (BOLHA_P, 30, 11)))],
    # dedo no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=12, olhos="cima", bracos=(((14, 23), (18, 21)),), conchas=(_c((8, 26), (4, 22)),)),
               dict(cx=12, olhos="cima", bracos=(((14, 23), (18, 21)),), conchas=(_c((8, 26), (4, 22)),),
                    por=((INTERROG_P, 25, 2),)),
               dict(cx=12, olhos="cima", torto=1, bracos=(((14, 23), (18, 21)),), conchas=(_c((8, 26), (4, 22)),),
                    por=((INTERROG, 25, 0),)),
               dict(cx=12, olhos="normal", torto=1, bracos=(((14, 23), (18, 21)),), conchas=(_c((8, 26), (4, 22)),),
                    por=((INTERROG, 25, 0),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# caldeirãozinho flutuando ao lado (atrás, à esquerda), com bolha; âncora = (aba - 12, aba - 10).
# Uma coluna de folga à esquerda para o caldeirão nunca encostar na borda.
_VAZIO = "." * 25
CALDEIRAO = [_VAZIO] * 11 + [
    "...KK....................",
    "..KVVK...................",
    ".KKVVKK..................",
    ".KSSSSSK.................",
    ".KSkkkSK.................",
    ".KSkkkSK.................",
    "..KSSSK..................",
    "...KKK...................",
]
# corvinho pousado na aba e vagalumes em volta do chapéu
MATRIARCA = CALDEIRAO[:]
for _i, _lin in {
    0: ".KK..................KK..",
    1: "KYYK................KYYK.",
    2: ".KK..................KK..",
    5: "...KKK...................",
    6: "..KkkkK..................",
    7: ".KkYkkkK.................",
    8: "KOKkkkkkK................",
    9: ".KKkkkkK..............KK.",
    10: "..KKKKK..............KYYK",
    11: "...KK.................KK.",
}.items():
    MATRIARCA[_i] = _lin
ESTAGIOS = [
    {"title": "Bruxinha", "floor": 1, "extra": None},
    {"title": "Bruxa do Pântano", "floor": 4, "extra": CALDEIRAO},
    {"title": "Matriarca do Brejo", "floor": 10, "extra": MATRIARCA},
]
