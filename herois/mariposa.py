"""Mariposa Lunar, 32 px, olhando para a direita. Uma mariposinha fofa de cabeça redonda de pelo creme, olhões
pretos, gola felpuda branca e barriga lilás listrada, com duas asas verde-lua de borda roxa abertas atrás do corpo,
cada uma com um olho amarelo desenhado e uma cauda na asa de baixo. Antenas curtinhas na base.
O símbolo do `running` é a rajada de pó brilhante: junta o pó numa bolinha na mão, empurra para a frente e o pó
estoura numa nuvem cintilante. No `failed` ela cai e o pó apaga: as asas murcham, ela despenca sentada com as asas
estendidas no chão, os olhos das asas e o brilho ficam cinzentos.
O tronco e a cabeça andam juntos (só asas, braços e pernas mudam), para as antenas grandes e a lua crescente dos
acréscimos ficarem sempre no lugar. As asas nunca saem do quadro (conferido ao montar cada quadro).
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha

PAL = {
    "K": "#16121e", "F": "#f4eedc", "f": "#c9bfa6", "W": "#ffffff", "B": "#c9b6f2", "b": "#9580c8",
    "V": "#a6eccf", "v": "#5fae94", "P": "#a77be0", "p": "#6f4aa8", "Y": "#ffd23f", "k": "#3a3048",
    "A": "#c4925a", "a": "#f0cf98", "L": "#fff6a8", "l": "#ffcf4a", "g": "#8a8a96", "q": "#5a5866",
    "Q": "#c6c6cf", "M": "#fff2a8", "m": "#d8b84a", "T": "#8fd8ff", "R": "#ff8fb0",
}

ABDOMEN = (3, 4, 4, 4, 4, 3, 3, 2)             # meia-largura da barriga por linha (8 linhas)
CABECA = (2, 3, 4, 4, 4, 4, 3, 2)              # meia-largura da cabeça por linha (8 linhas)
GOLA = (5, 6, 5)                                # gola felpuda (3 linhas, entre a cabeça e a barriga)

# asa: (centro do lobo de cima em relação ao ombro, raios), (centro do lobo de baixo, raios); dx para fora
ASAS = {
    "cima": ((5, -7, 4.5, 5.0), (4, 2, 3.0, 3.0)),
    "meio": ((6, -3, 4.5, 4.5), (4, 3, 3.0, 3.0)),
    "baixo": ((6, 0, 4.5, 4.0), (4, 4, 3.0, 2.4)),
    "fechada": ((3, -5, 2.6, 5.0), (2, 3, 2.0, 3.0)),
    "chao": ((7, 2, 4.5, 2.4), (4, 3, 3.0, 2.0)),
}

ORBE = [".KKK.", "KLWLK", "KWWWK", "KLWLK", ".KKK."]           # pó juntado na mão
BRILHO = ["..K..", ".KLK.", "KLWLK", ".KLK.", "..K.."]       # estrelinha de pó
BRILHO_P = [".K.", "KLK", ".K."]
APAGADO = ["..K..", ".KqK.", "KqQqK", ".KqK.", "..K.."]      # pó apagado
APAGADO_P = [".K.", "KqK", ".K."]
NUVEM = [                                       # a rajada estoura numa nuvem de pó brilhante
    "...K....K...",
    "..KLK..KWK..",
    "...KKKKKK.K.",
    ".K.KLLlLLKLK",
    "KWKLLWWLLlK.",
    ".KLlWWWWWLK.",
    ".KLLWWWWLLLK",
    "KLlLLWWLlLK.",
    ".KKLLLLLLK.K",
    "..KKlLKKK.KWK",
    ".KWK.KK....K.",
    "..K..........",
]
NUVEM = [l.ljust(13, ".") for l in NUVEM]
RASTRO = ["LL..", ".lLL", "LL.."]              # rastro do pó saindo da mão


def _asa(px, ombro, lado, pose, apagada):
    """Pinta uma asa (lobo de cima com olho, lobo de baixo com cauda) em `px`; lado -1 = trás, +1 = frente."""
    sx, sy = ombro
    (ux, uy, urx, ury), (lx, ly, lrx, lry) = ASAS[pose]
    claro, escuro, borda, olho = ("Q", "g", "q", "q") if apagada else ("V", "v", "P", "Y")
    lobos = ((sx + lado * lx, sy + ly, lrx, lry), (sx + lado * ux, sy + uy, urx, ury))
    for cx, cy, rx, ry in lobos:
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1:
                    px[(x, y)] = borda if d > 0.55 else (escuro if (x - sx) * lado < 2 else claro)
    cx, cy = lobos[1][0], lobos[1][1]
    if pose != "fechada":                          # olho desenhado na asa de cima
        cx, cy = round(cx), round(cy)
        for x, y in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            px[(x, y)] = olho
        px[(cx, cy)] = "K" if not apagada else "g"
    tx, ty = round(sx + lado * lx), round(sy + ly + lry)   # cauda da asa de baixo
    for i in range(1, 4 if pose != "chao" else 2):
        if ty + i <= N - 3:                         # perto do chão a cauda encurta
            px[(tx + lado * (i // 2), ty + i)] = borda


def _braco(g, a, b):
    """Bracinho felpudo de 2 px de `a` (ombro) a `b` (mão), com a mãozinha redonda na ponta."""
    px = {}
    for x, y in linha(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px[(x + dx, y + dy)] = "f" if dy else "F"
    bx, by = b
    for x, y in ((bx, by - 1), (bx - 1, by), (bx, by), (bx + 1, by), (bx, by + 1), (bx + 1, by + 1)):
        px[(x, y)] = "F"
    contornar(g, px)


def quadro(cx=16, base=30, perna=2, sentado=False, olho="n", pes=(0, 0), asas=("meio", "meio"), bracos=(),
           por=(), apagada=False):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda do centro e 9 acima do topo da cabeça).
    `perna`: altura das perninhas (0 = agachada); `sentado`: caída no chão, sem pernas;
    `asas`: pose da asa de trás e da da frente (ASAS); `bracos`: ((ombro), (mão)) com o ombro de trás em
    (cx-4, a+1) e o da frente em (cx+4, a+1), `a` = topo da barriga; `apagada`: asas e olhos sem cor."""
    g = [["."] * N for _ in range(N)]
    a0 = (base - len(ABDOMEN) + 1) if sentado else (base - perna - len(ABDOMEN) + 1)
    c0 = a0 - 2
    h0 = c0 - len(CABECA) + 1
    hx = cx + 1
    asa = {}
    for lado, pose in zip((-1, 1), asas):
        _asa(asa, (cx + 3 * lado, a0 - 1), lado, pose, apagada)
    xs = [x for x, _ in asa]
    ys = [y for _, y in asa]
    assert 1 <= min(xs) and max(xs) <= N - 2 and 1 <= min(ys) and max(ys) <= N - 2, ("asa fora do quadro", asas)
    contornar(g, asa)
    px = {}
    if not sentado:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + pes[i]
            for y in range(base - perna + 1, base + 1):
                for x1 in (x, x + 1):
                    px[(x1, y)] = "k"
    for r, w in enumerate(ABDOMEN):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "b" if r % 2 or x == cx - w else "B"
    for x in (hx - 2, hx + 2):                      # anteninhas curtas
        px[(x + (x > hx), h0 - 1)] = "A"
        px[(x + (x > hx) * 2 - (x < hx), h0 - 2)] = "a"
    for r, w in enumerate(CABECA):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "f" if x <= hx - w else "F"
    for r, w in enumerate(GOLA):
        for x in range(cx - w, cx + w + 1):
            if r == 2 and (x - cx) % 2:
                continue
            px[(x, c0 + r)] = "W" if (x + r) % 3 else "F"
    contornar(g, px)
    ey = h0 + 3                                     # rosto: olhões pretos virados para a direita
    olhos = {"n": (["KK", "KW", "KK"], ["KK", "KW", "KK"]), "fechado": (["..", "KK"], ["..", "KK"]),
             "feliz": ([".K", "K.", ".."], [".K", "K.", ".."]), "x": (["K.K", ".K.", "K.K"], ["K.K", ".K.", "K.K"]),
             "bravo": (["K.", "KK", "KW"], [".K", "KK", "WK"]), "cima": (["KW", "KK", ".."], ["KW", "KK", ".."]),
             "triste": (["KK", "KW", "K."], ["KK", "KW", ".K"])}[olho]
    tras, frente = olhos
    carimbar(g, tras, hx - 2 - (len(tras[0]) > 2), ey - (len(tras) > 2 and olho == "x"))
    carimbar(g, frente, hx + 2, ey - (len(frente) > 2 and olho == "x"))
    g[h0 + 6][hx + 1] = "R"                         # boquinha rosada
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 2, ey + 3)
    for a, b in bracos:
        _braco(g, a, b)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, h0 - 9)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=2 -> barriga 21-28 (cx=16), gola 19-21, cabeça 12-19 (hx=17); ombros em (12, 22) e (20, 22)
_PARADO = (((12, 22), (11, 25)), ((20, 22), (21, 25)))   # bracinhos soltos ao lado da barriga
_SPECS = {
    # bate as asas devagar, pisca, uma estrelinha de pó cai
    "idle": [dict(bracos=_PARADO),
             dict(asas=("cima", "cima"), bracos=_PARADO),
             dict(bracos=_PARADO, por=((BRILHO_P, 26, 22),)),
             dict(olho="fechado", asas=("baixo", "baixo"), bracos=_PARADO, por=((BRILHO_P, 27, 26),)),
             dict(bracos=_PARADO)],
    # voa baixinho: asas batendo forte, o corpo sobe e desce, perninhas balançando
    "run_r": [dict(asas=("cima", "cima"), pes=(-1, 1), bracos=(((12, 22), (9, 25)), ((20, 22), (24, 24)))),
              dict(base=29, asas=("meio", "meio"), bracos=_PARADO, por=((BRILHO_P, 2, 26),)),
              dict(base=28, asas=("baixo", "baixo"), pes=(1, -1), bracos=(((12, 20), (9, 23)), ((20, 20), (24, 22)))),
              dict(base=29, asas=("meio", "meio"), bracos=_PARADO, por=((BRILHO_P, 1, 24),))],
    # acena alto com a mãozinha da frente
    "waving": [dict(olho="feliz", bracos=(_PARADO[0], ((20, 22), (25, 15)))),
               dict(olho="feliz", asas=("cima", "cima"), bracos=(_PARADO[0], ((20, 22), (23, 13)))),
               dict(olho="feliz", bracos=(_PARADO[0], ((20, 22), (26, 16))), por=((BRILHO_P, 28, 11),)),
               dict(olho="feliz", asas=("cima", "cima"), bracos=(_PARADO[0], ((20, 22), (23, 13))))],
    # encolhe as asas, salta batendo as asas, desce planando, pousa
    "jumping": [dict(perna=0, olho="fechado", asas=("fechada", "fechada"),
                     bracos=(((12, 24), (10, 28)), ((20, 24), (22, 28)))),
                dict(base=28, olho="cima", asas=("cima", "cima"), bracos=(((12, 20), (8, 17)), ((20, 20), (24, 16)))),
                dict(base=27, olho="feliz", asas=("baixo", "baixo"), bracos=(((12, 19), (8, 15)), ((20, 19), (24, 14))),
                     por=((BRILHO_P, 2, 27), (BRILHO_P, 27, 27))),
                dict(base=28, asas=("meio", "meio"), bracos=(((12, 20), (9, 22)), ((20, 20), (23, 22)))),
                dict(perna=0, olho="feliz", asas=("fechada", "fechada"),
                     bracos=(((12, 24), (10, 28)), ((20, 24), (22, 28))))],
    # cai e o pó apaga: asas murcham, despenca sentada com as asas no chão, o brilho fica cinza
    "failed": [dict(olho="triste", asas=("baixo", "baixo"), bracos=_PARADO, por=((APAGADO_P, 27, 9),)),
               dict(olho="x", asas=("fechada", "fechada"), bracos=_PARADO,
                    por=((APAGADO, 25, 12), (APAGADO_P, 4, 10), (APAGADO_P, 27, 22))),
               dict(olho="x", sentado=True, asas=("chao", "chao"), apagada=True,
                    bracos=(((12, 23), (9, 27)), ((20, 23), (23, 27))), por=((APAGADO, 26, 13), (APAGADO_P, 3, 15))),
               dict(olho="x", sentado=True, asas=("chao", "chao"), apagada=True,
                    bracos=(((12, 23), (9, 27)), ((20, 23), (23, 27))), por=((APAGADO_P, 27, 19),)),
               dict(olho="x", sentado=True, asas=("chao", "chao"), apagada=True,
                    bracos=(((12, 23), (9, 27)), ((20, 23), (23, 27))))],
    # dorme de asas fechadas, "z" subindo
    "waiting": [dict(olho="fechado", asas=("fechada", "fechada"), bracos=_PARADO),
                dict(olho="fechado", asas=("fechada", "fechada"), bracos=_PARADO, por=((Z_P, 26, 8),)),
                dict(olho="fechado", asas=("fechada", "fechada"), bracos=_PARADO, por=((Z_P, 25, 9), (Z_G, 26, 0))),
                dict(olho="fechado", asas=("fechada", "fechada"), bracos=_PARADO, por=((Z_G, 26, 0),))],
    # rajada de pó: junta o pó na mão lá atrás, empurra para a frente e a nuvem de pó estoura
    "running": [dict(cx=14, olho="bravo", asas=("cima", "cima"), bracos=(((10, 22), (8, 26)), ((18, 22), (24, 15))),
                     por=((ORBE, 23, 10),)),
                dict(cx=14, olho="bravo", asas=("baixo", "baixo"), bracos=(((10, 22), (8, 26)), ((18, 22), (24, 21))),
                     por=((RASTRO, 19, 19), (ORBE, 24, 19))),
                dict(cx=14, olho="bravo", asas=("meio", "meio"), bracos=(((10, 22), (8, 26)), ((18, 22), (22, 21))),
                     por=((NUVEM, 19, 13),)),
                dict(cx=14, olho="feliz", asas=("cima", "cima"), bracos=(((10, 22), (8, 26)), ((18, 22), (21, 23))),
                     por=((BRILHO, 26, 10), (BRILHO_P, 28, 22), (BRILHO_P, 23, 16), (BRILHO, 25, 25)))],
    # mãozinha no queixo, "?" aparece
    "review": [dict(olho="cima", bracos=(_PARADO[0], ((20, 22), (21, 20)))),
               dict(olho="cima", bracos=(_PARADO[0], ((20, 22), (21, 20))), por=((INTERROG_P, 26, 4),)),
               dict(olho="cima", bracos=(_PARADO[0], ((20, 22), (21, 20))), por=((INTERROG, 26, 2),)),
               dict(olho="n", bracos=(_PARADO[0], ((20, 22), (21, 20))), por=((INTERROG, 26, 2),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)


# grade 18x10 colada 8 à esquerda do centro e 9 acima do topo da cabeça (cabeça a partir da linha 9, centro na
# coluna 9): antenas grandes de pena; na Eclipse, uma lua crescente flutuando atrás da cabeça
def _antena(px, base, ponta):
    """Antena de pena: haste de `base` a `ponta` com farpas dos dois lados."""
    pts = linha(*base, *ponta)
    for i, (x, y) in enumerate(pts):
        px[(x, y)] = "A"
        if 1 <= i < len(pts) - 1:
            for dx in (-1, 1):
                if (x + dx, y) not in px:
                    px[(x + dx, y)] = "a"


def _extra(lua):
    g = [["."] * N for _ in range(N)]
    px = {}
    _antena(px, (7, 9), (4, 2))
    _antena(px, (11, 9), (15, 2))
    for x, y in ((3, 1), (4, 1), (15, 1), (16, 1)):  # pontinhas enroladas
        px[(x, y)] = "a"
    contornar(g, px)
    if lua:
        carimbar(g, LUA, 6, 0)
    return ["".join(l[:18]) for l in g[:10]]


LUA = [                                         # lua crescente
    "..KKK.",
    ".KMMK.",
    "KMMK..",
    "KMmK..",
    "KMMK..",
    ".KMMK.",
    "..KKK.",
]
ANTENAS = _extra(False)
ECLIPSE = _extra(True)
ESTAGIOS = [
    {"title": "Lagartinha Lunar", "floor": 1, "extra": None},
    {"title": "Mariposa Lunar", "floor": 4, "extra": ANTENAS},
    {"title": "Mariposa Eclipse", "floor": 10, "extra": ECLIPSE},
]
