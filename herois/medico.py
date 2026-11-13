"""Médico da Peste, 32 px, olhando para a direita. Cada quadro sai de partes: casaco (sino com sombra e botões),
cabeça de capuz com máscara de bico e óculos verdes, botinhas, braços em linha grossa (com contorno) e objetos
(lanterna de ervas, frasco de veneno, nuvenzinha). No `failed` a máscara se solta e cai, mostrando o rostinho.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar

PAL = {
    "K": "#231b33", "C": "#4a3f66", "c": "#342b4c", "H": "#5b4d7d", "h": "#3f3560",
    "M": "#efe6cf", "m": "#bfae8a", "E": "#8ff07a", "e": "#3d9a4a", "W": "#ffffff",
    "F": "#f6d7c3", "P": "#ff9ec4", "B": "#231b33", "T": "#8fd8ff", "Y": "#ffd23f",
    "V": "#a6e86b", "v": "#4c8a3a", "N": "#8a5a36", "k": "#2c2233", "R": "#8e2a44", "r": "#5e1a2e",
    "S": "#c9c3d6",
}

LANTERNA = [".KKK.", ".K.K.", "KKKKK", "KVYVK", "KYVvK", "KvVVK", "KKKKK", ".KKK."]
LANTERNA_APAG = [".KKK.", ".K.K.", "KKKKK", "KSSSK", "KSSSK", "KSSSK", "KKKKK", ".KKK."]
FRASCO = [".KK.", "KNNK", ".KK.", "KVVK", "KVvK", "KvVK", ".KK."]
FRASCO_VOANDO = ["..KKKK..", "..KNNK..", "..KNNK..", "..KKKK..", "...KSK..", "..KKSKK.", ".KVVVVVK", "KVVvVVVK", "KVvVVvVK", "KVVVVVVK", ".KKKKKK."]
NUVEM = ["...KKK.KK.", "..KVVVKVVK", ".KVVvVVVVK", "KVVVVVvVVK", "KVvVVVVVK.", ".KVVVvVVVK", "..KKVVKKK.", "....KK...."]
NUVEM_P = [".KK.", "KVVK", "KvVK", ".KK."]
LUVA = [".KKK.", "KNNNK", "KNNNK", "KNNNK", ".KKK."]
MAO_ROSTO = [".KKK.", "KNNNK", "KNNNK", ".KKK."]


def _linha(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)]


def _braco(g, a, b):
    """Manga grossa de casaco de `a` a `b`, com contorno escuro."""
    pts = _linha(*a, *b)
    for x, y in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= x + dx < N and 0 <= y + dy < N:
                    g[y + dy][x + dx] = "K"
    for x, y in pts:
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = "H"


def quadro(cx=14, base=30, ch=9, lean=0, olhos="normal", bochecha=True, mascara=(0, 0), rosto="normal",
           pes=(0, 0), atras=(), bracos=(), por=(), lanterna_ok=True):
    """Um quadro 32x32 e a âncora (topo da cabeça) do acréscimo. `mascara` None = presa; (dx, dy) = solta e deslocada.
    `atras`: (sprite, x, y) desenhados antes do corpo; `bracos`: ((x0, y0), (x1, y1)) por cima; `por`: sprites no fim."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 5
    casaco = set()
    for y in range(ctop, base - 1):
        t = (y - ctop) / ch
        meia = 4.5 + t * 3.5
        c = cx + lean * (1 - t)
        casaco |= {(x, y) for x in range(round(c - meia), round(c + meia) + 1)}
    cabeca = {(x, y) for x in range(hx - 7, hx + 8) for y in range(hy - 7, hy + 8)
              if (x - hx) ** 2 + (y - hy) ** 2 <= 42}
    face = {(x, y) for x, y in cabeca if x >= hx - 3 and y >= hy - 2}
    bico = set()
    for i, L in enumerate((3, 6, 8, 7, 4)):
        bico |= {(x, hy + i) for x in range(hx + 5, hx + 5 + L)}
    presa = mascara == (0, 0)
    corpo = casaco | cabeca | (bico if presa else set())
    for x, y in corpo:
        if (x, y) in cabeca:
            g[y][x] = "h" if (x - hx) < -3 and y > hy - 2 else "H"
        elif (x, y) in casaco:
            borda = (x + 1, y) not in corpo or (x, y + 1) not in corpo
            g[y][x] = "c" if borda else "C"
    if presa:
        for x, y in face | bico:
            g[y][x] = "m" if (x, y + 1) not in face | bico or y == hy + 2 and x > hx + 6 else "M"
    else:
        for x, y in face:                      # rostinho com contorno onde encosta no capuz
            g[y][x] = "K" if any(n in cabeca and n not in face for n in ((x - 1, y), (x, y - 1))) else "F"
    for x, y in casaco:                      # botões no meio do casaco
        if x == round(cx + lean * 0.4) + 1 and (y - ctop) % 3 == 2 and y < base - 2:
            g[y][x] = "Y"
    pe_y = base - 2
    for i, (px, dx) in enumerate(((cx - 4, pes[0]), (cx + 2, pes[1]))):
        for x in range(px + dx, px + dx + 3):
            for y in (pe_y, pe_y + 1):
                corpo.add((x, y)); g[y][x] = "k"
    for x, y in corpo:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in corpo and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # olhos: com máscara, dois óculos verdes; sem máscara, olhinhos no rosto
    if presa:
        for ox in (hx - 3, hx + 2):
            oy = hy - 2
            if olhos == "fechado":
                carimbar(g, ["KKKKK", "K...K", "KKKKK"], ox, oy + 1)
                for x in range(ox + 1, ox + 4):
                    g[oy + 2][x] = "e"
            elif olhos == "feliz":
                carimbar(g, [".KKK.", "KE.EK", "K...K"], ox, oy + 1)
            else:
                carimbar(g, [".KKK.", "KEEEK", "KEEEK", "KeEeK", ".KKK."], ox, oy)
                g[oy + 1][ox + 1] = "W" if olhos != "cima" else "E"
                if olhos == "cima":
                    g[oy + 1][ox + 2] = "W"
                if olhos == "bravo":
                    carimbar(g, ["KK...", "..KKK"] if ox < hx else ["KKK..", "...KK"], ox, oy - 1)
                if olhos == "triste":
                    carimbar(g, ["...KK", "KKK.."] if ox < hx else ["..KKK", "KK..."], ox, oy - 1)
        if bochecha:
            g[hy + 3][hx - 2] = g[hy + 3][hx - 1] = "P"
        g[hy + 1][hx + 9] = "m"               # narina no bico
    else:
        dx, dy = mascara
        for x, y in face | bico:              # máscara caída, desenhada deslocada
            if 0 <= x + dx < N and 0 <= y + dy < N:
                g[y + dy][x + dx] = "m" if (x, y + 1) not in face | bico else "M"
        for x, y in face | bico:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in face | bico and 0 <= nx + dx < N and 0 <= ny + dy < N \
                        and g[ny + dy][nx + dx] in ".FHhCck":
                    g[ny + dy][nx + dx] = "K"
        for ox in (hx - 3, hx + 2):
            carimbar(g, [".KKK.", "KEEEK", "KeEeK", ".KKK."], ox + dx, hy - 2 + dy)
        ex, ey = hx - 1, hy
        if rosto == "x":
            carimbar(g, ["B.B", ".B.", "B.B"], ex - 1, ey - 1); carimbar(g, ["B.B", ".B.", "B.B"], ex + 3, ey - 1)
        else:
            for x in (ex, ex + 4):                # olhos 2x3 com brilho
                carimbar(g, ["WB", "BB", "BB"], x - 1 + (x > ex), ey - 1)
            if rosto != "o":                      # sobrancelhas tristes
                carimbar(g, ["..B", "BB."], ex - 2, ey - 3); carimbar(g, ["B..", ".BB"], ex + 4, ey - 3)
        if rosto == "o":
            carimbar(g, [".B.", "B.B", ".B."], ex + 1, ey + 3)
        else:
            carimbar(g, [".BBB.", "B...B"], ex, ey + 3)
        g[ey + 2][ex - 2] = g[ey + 2][ex + 6] = "P"
    for a, b in bracos:
        _braco(g, a, b)
    for s, x, y in por:
        if s is LANTERNA and not lanterna_ok:
            s = LANTERNA_APAG
        carimbar(g, s, x, y)
    top = min(y for _, y in cabeca)
    return ["".join(l) for l in g], (hx - 7, top - 5)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


def _lant(mx, my):
    """Mão em (mx, my) segurando a lanterna pendurada logo abaixo."""
    return (LANTERNA, mx - 2, my + 1)


# ombro: ~(cx + 3, ctop + 2); base=30, ch=9 -> ctop=20
_SPECS = {
    # parado, balança a lanterna de ervas na frente
    "idle": [dict(bracos=(((17, 22), (21, 21)),), por=(_lant(21, 21),)),
             dict(bracos=(((17, 22), (22, 22)),), por=(_lant(22, 22),)),
             dict(olhos="fechado", bracos=(((17, 22), (23, 21)),), por=(_lant(23, 21),)),
             dict(bracos=(((17, 22), (22, 22)),), por=(_lant(22, 22),))],
    # corre inclinado, botinhas alternando, lanterna balançando para trás
    "run_r": [dict(cx=15, lean=2, pes=(-2, 2), bracos=(((13, 22), (8, 24)),), atras=(_lant(7, 24),)),
              dict(cx=15, lean=3, base=29, pes=(0, 0), bracos=(((13, 21), (9, 22)),), atras=(_lant(8, 22),)),
              dict(cx=15, lean=2, pes=(2, -2), bracos=(((13, 22), (8, 23)),), atras=(_lant(7, 23),)),
              dict(cx=15, lean=3, base=29, pes=(0, 0), bracos=(((13, 21), (9, 21)),), atras=(_lant(8, 21),))],
    # acena com a luva, lanterna na outra mão (atrás)
    "waving": [dict(olhos="feliz", atras=(_lant(6, 23),), bracos=(((16, 22), (20, 19)),), por=((LUVA, 19, 17),)),
               dict(olhos="feliz", atras=(_lant(6, 23),), bracos=(((16, 22), (20, 16)),), por=((LUVA, 19, 13),)),
               dict(olhos="feliz", atras=(_lant(6, 23),), bracos=(((16, 22), (23, 16)),), por=((LUVA, 22, 13),)),
               dict(olhos="feliz", atras=(_lant(6, 23),), bracos=(((16, 22), (20, 16)),), por=((LUVA, 19, 13),))],
    # agacha, salta com a lanterna no alto, cai, pousa
    "jumping": [dict(ch=6, olhos="fechado", bracos=(((17, 25), (21, 27)),), por=(_lant(22, 26),)),
                dict(ch=10, base=29, bracos=(((17, 20), (24, 19)),), por=(_lant(24, 19),)),
                dict(ch=9, base=26, olhos="feliz", bracos=(((17, 18), (25, 16)),), por=(_lant(25, 16),)),
                dict(ch=10, base=29, bracos=(((17, 21), (23, 21)),), por=(_lant(23, 21),)),
                dict(ch=7, olhos="feliz", bracos=(((17, 24), (21, 25)),), por=(_lant(22, 25),))],
    # triste, a máscara escorrega, cai no chão e a lanterna apaga
    "failed": [dict(olhos="triste", bracos=(((17, 22), (20, 25)),), por=(_lant(21, 25), (LAGRIMA, 11, 13))),
               dict(mascara=(2, 4), rosto="o", bracos=(((17, 22), (20, 25)),), por=(_lant(21, 25),)),
               dict(cx=12, mascara=(5, 9), rosto="o", bracos=(((15, 22), (18, 26)),), por=(_lant(19, 26),)),
               dict(cx=10, ch=7, mascara=(9, 8), rosto="triste", lanterna_ok=False,
                    atras=(_lant(3, 22),), por=((LAGRIMA, 7, 19),)),
               dict(cx=10, ch=6, lean=-1, mascara=(10, 9), rosto="x", lanterna_ok=False,
                    atras=(_lant(2, 22),))],
    # cochila sentado de lado, lanterna no chão, "z" subindo
    "waiting": [dict(ch=7, lean=-1, olhos="fechado", atras=(_lant(23, 21),)),
                dict(ch=7, lean=-2, olhos="fechado", atras=(_lant(23, 21),), por=((Z_P, 22, 4),)),
                dict(ch=7, lean=-2, olhos="fechado", atras=(_lant(23, 21),), por=((Z_P, 21, 4), (Z_G, 26, 0))),
                dict(ch=7, lean=-1, olhos="fechado", atras=(_lant(23, 21),), por=((Z_G, 26, 0),))],
    # golpe: recua a lanterna, gira para a frente e arremessa o frasco de veneno, que estoura numa nuvem
    "running": [dict(cx=13, lean=-2, olhos="bravo", bracos=(((12, 22), (6, 18)),), atras=(_lant(5, 18),)),
                dict(cx=14, lean=2, olhos="bravo", bracos=(((17, 21), (22, 14)),), por=(_lant(22, 14),)),
                dict(cx=14, lean=3, olhos="bravo", bracos=(((18, 22), (24, 20)),),
                     por=(_lant(24, 20), (FRASCO_VOANDO, 24, 1))),
                dict(cx=14, lean=1, olhos="bravo", bracos=(((17, 22), (21, 24)),),
                     por=(_lant(22, 24), (NUVEM, 22, 3), (NUVEM_P, 27, 11), (NUVEM_P, 19, 1)))],
    # luva no queixo do bico, pensando, "?" aparece
    "review": [dict(cx=12, olhos="cima", bracos=(((15, 22), (19, 18)),), por=((MAO_ROSTO, 18, 16),)),
               dict(cx=12, olhos="cima", bracos=(((15, 22), (19, 18)),), por=((MAO_ROSTO, 18, 16), (INTERROG_P, 25, 2))),
               dict(cx=12, olhos="cima", bracos=(((15, 22), (19, 18)),), por=((MAO_ROSTO, 18, 16), (INTERROG, 25, 0))),
               dict(cx=12, olhos="normal", bracos=(((15, 22), (19, 18)),), por=((MAO_ROSTO, 18, 16), (INTERROG, 25, 0)))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# chapéu de aba larga (copa + aba), apoiado no alto do capuz pela âncora
CHAPEU = [
    "....KKKKKKK....",
    "....KkkkkkK....",
    "....KkkkkkK....",
    "....KRRRRRK....",
    "KKKKKKKKKKKKKKK",
    "KkkkkkkkkkkkkkK",
    ".KKKKKKKKKKKKK.",
]
# capa curta sobre os ombros (abaixo do pescoço)
CAPA = ["." * 15] * 16 + [
    "..KKKKKKKKKKK..",
    ".KRRRRRRRRRRRK.",
    "KRRRRRRYRRRRRrK",
    "KrRRRRRRRRRRrrK",
    ".KrrK.....KrK..",
    "..KK.......K...",
]
DOUTOR = [CHAPEU[i] if i < len(CHAPEU) else CAPA[i] for i in range(len(CAPA))]
ESTAGIOS = [
    {"title": "Aprendiz da Peste", "floor": 1, "extra": None},
    {"title": "Médico da Peste", "floor": 4, "extra": CHAPEU},
    {"title": "Doutor da Praga", "floor": 10, "extra": DOUTOR},
]
