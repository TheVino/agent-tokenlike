"""Mariposa Lunar, 32 px, olhando para a direita. Uma mariposinha fofa de cabeça redonda de pelo creme, olhões
pretos, gola felpuda branca e barriga lilás listrada, com duas asas verde-lua de borda roxa abertas atrás do corpo,
cada uma com um olho amarelo desenhado e uma cauda na asa de baixo. Antenas curtinhas na base.
O símbolo do `running` é a rajada de pó brilhante: junta o pó numa bolinha na mão, empurra para a frente e o pó
estoura numa nuvem cintilante. No `failed` ela cai e o pó apaga: as asas murcham, ela despenca sentada com as asas
estendidas no chão, os olhos das asas e o brilho ficam cinzentos.
O tronco e a cabeça andam juntos (só asas, braços e pernas mudam), para as antenas grandes e a lua crescente dos
acréscimos ficarem sempre no lugar. As asas nunca saem do quadro (conferido ao montar cada quadro).
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#16121e", "F": "#f4eedc", "f": "#c9bfa6", "W": "#ffffff", "B": "#c9b6f2", "b": "#9580c8",
    "V": "#a6eccf", "v": "#5fae94", "P": "#a77be0", "p": "#6f4aa8", "Y": "#ffd23f", "k": "#3a3048",
    "A": "#c4925a", "a": "#f0cf98", "L": "#fff6a8", "l": "#ffcf4a", "g": "#8a8a96", "q": "#5a5866",
    "Q": "#c6c6cf", "M": "#fff2a8", "m": "#d8b84a", "T": "#8fd8ff", "R": "#ff8fb0",
}

ABDOMEN = (3, 4, 4, 4, 4, 3, 3, 2)             # meia-largura da barriga por linha (8 linhas)
HEAD = (2, 3, 4, 4, 4, 4, 3, 2)              # meia-largura da cabeça por linha (8 linhas)
COLLAR = (5, 6, 5)                                # gola felpuda (3 linhas, entre a cabeça e a barriga)

# asa: (centro do lobo de cima em relação ao ombro, raios), (centro do lobo de baixo, raios); dx para fora
WINGS = {
    "cima": ((5, -7, 4.5, 5.0), (4, 2, 3.0, 3.0)),
    "meio": ((6, -3, 4.5, 4.5), (4, 3, 3.0, 3.0)),
    "baixo": ((6, 0, 4.5, 4.0), (4, 4, 3.0, 2.4)),
    "fechada": ((3, -5, 2.6, 5.0), (2, 3, 2.0, 3.0)),
    "chao": ((7, 2, 4.5, 2.4), (4, 3, 3.0, 2.0)),
}

ORB = [".KKK.", "KLWLK", "KWWWK", "KLWLK", ".KKK."]           # pó juntado na mão
SHINE = ["..K..", ".KLK.", "KLWLK", ".KLK.", "..K.."]       # estrelinha de pó
SHINE_S = [".K.", "KLK", ".K."]
UNLIT = ["..K..", ".KqK.", "KqQqK", ".KqK.", "..K.."]      # pó apagado
UNLIT_S = [".K.", "KqK", ".K."]
CLOUD = [                                       # a rajada estoura numa nuvem de pó brilhante
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
CLOUD = [l.ljust(13, ".") for l in CLOUD]
TRAIL = ["LL..", ".lLL", "LL.."]              # rastro do pó saindo da mão


def _wing(px, shoulder, side, pose, unlit):
    """Pinta uma asa (lobo de cima com olho, lobo de baixo com cauda) em `px`; lado -1 = trás, +1 = frente."""
    sx, sy = shoulder
    (ux, uy, urx, ury), (lx, ly, lrx, lry) = WINGS[pose]
    claro, dark, edge, eye = ("Q", "g", "q", "q") if unlit else ("V", "v", "P", "Y")
    lobos = ((sx + side * lx, sy + ly, lrx, lry), (sx + side * ux, sy + uy, urx, ury))
    for cx, cy, rx, ry in lobos:
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1:
                    px[(x, y)] = edge if d > 0.55 else (dark if (x - sx) * side < 2 else claro)
    cx, cy = lobos[1][0], lobos[1][1]
    if pose != "fechada":                          # olho desenhado na asa de cima
        cx, cy = round(cx), round(cy)
        for x, y in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            px[(x, y)] = eye
        px[(cx, cy)] = "K" if not unlit else "g"
    tx, ty = round(sx + side * lx), round(sy + ly + lry)   # cauda da asa de baixo
    for i in range(1, 4 if pose != "chao" else 2):
        if ty + i <= N - 3:                         # perto do chão a cauda encurta
            px[(tx + side * (i // 2), ty + i)] = edge


def _arm(g, a, b):
    """Bracinho felpudo de 2 px de `a` (ombro) a `b` (mão), com a mãozinha redonda na ponta."""
    px = {}
    for x, y in line(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px[(x + dx, y + dy)] = "f" if dy else "F"
    bx, by = b
    for x, y in ((bx, by - 1), (bx - 1, by), (bx, by), (bx + 1, by), (bx, by + 1), (bx + 1, by + 1)):
        px[(x, y)] = "F"
    outline_cells(g, px)


def frame(cx=16, base=30, leg=2, seated=False, eye="n", feet=(0, 0), wings=("meio", "meio"), arms=(),
           por=(), unlit=False):
    """Um quadro 32x32 e a âncora do acréscimo (8 à esquerda do centro e 9 acima do topo da cabeça).
    `perna`: altura das perninhas (0 = agachada); `sentado`: caída no chão, sem pernas;
    `asas`: pose da asa de trás e da da frente (ASAS); `bracos`: ((ombro), (mão)) com o ombro de trás em
    (cx-4, a+1) e o da frente em (cx+4, a+1), `a` = topo da barriga; `apagada`: asas e olhos sem cor."""
    g = [["."] * N for _ in range(N)]
    a0 = (base - len(ABDOMEN) + 1) if seated else (base - leg - len(ABDOMEN) + 1)
    c0 = a0 - 2
    h0 = c0 - len(HEAD) + 1
    hx = cx + 1
    wing = {}
    for side, pose in zip((-1, 1), wings):
        _wing(wing, (cx + 3 * side, a0 - 1), side, pose, unlit)
    xs = [x for x, _ in wing]
    ys = [y for _, y in wing]
    assert 1 <= min(xs) and max(xs) <= N - 2 and 1 <= min(ys) and max(ys) <= N - 2, ("asa fora do quadro", wings)
    outline_cells(g, wing)
    px = {}
    if not seated:
        for i, x0 in enumerate((cx - 3, cx + 1)):
            x = x0 + feet[i]
            for y in range(base - leg + 1, base + 1):
                for x1 in (x, x + 1):
                    px[(x1, y)] = "k"
    for r, w in enumerate(ABDOMEN):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "b" if r % 2 or x == cx - w else "B"
    for x in (hx - 2, hx + 2):                      # anteninhas curtas
        px[(x + (x > hx), h0 - 1)] = "A"
        px[(x + (x > hx) * 2 - (x < hx), h0 - 2)] = "a"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "f" if x <= hx - w else "F"
    for r, w in enumerate(COLLAR):
        for x in range(cx - w, cx + w + 1):
            if r == 2 and (x - cx) % 2:
                continue
            px[(x, c0 + r)] = "W" if (x + r) % 3 else "F"
    outline_cells(g, px)
    ey = h0 + 3                                     # rosto: olhões pretos virados para a direita
    eyes = {"n": (["KK", "KW", "KK"], ["KK", "KW", "KK"]), "fechado": (["..", "KK"], ["..", "KK"]),
             "feliz": ([".K", "K.", ".."], [".K", "K.", ".."]), "x": (["K.K", ".K.", "K.K"], ["K.K", ".K.", "K.K"]),
             "bravo": (["K.", "KK", "KW"], [".K", "KK", "WK"]), "cima": (["KW", "KK", ".."], ["KW", "KK", ".."]),
             "triste": (["KK", "KW", "K."], ["KK", "KW", ".K"])}[eye]
    back, front = eyes
    stamp(g, back, hx - 2 - (len(back[0]) > 2), ey - (len(back) > 2 and eye == "x"))
    stamp(g, front, hx + 2, ey - (len(front) > 2 and eye == "x"))
    g[h0 + 6][hx + 1] = "R"                         # boquinha rosada
    if eye == "triste":
        stamp(g, TEAR, hx - 2, ey + 3)
    for a, b in arms:
        _arm(g, a, b)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 8, h0 - 9)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=2 -> barriga 21-28 (cx=16), gola 19-21, cabeça 12-19 (hx=17); ombros em (12, 22) e (20, 22)
_STILL = (((12, 22), (11, 25)), ((20, 22), (21, 25)))   # bracinhos soltos ao lado da barriga
_SPECS = {
    # bate as asas devagar, pisca, uma estrelinha de pó cai
    "idle": [dict(arms=_STILL),
             dict(wings=("cima", "cima"), arms=_STILL),
             dict(arms=_STILL, por=((SHINE_S, 26, 22),)),
             dict(eye="fechado", wings=("baixo", "baixo"), arms=_STILL, por=((SHINE_S, 27, 26),)),
             dict(arms=_STILL)],
    # voa baixinho: asas batendo forte, o corpo sobe e desce, perninhas balançando
    "run_r": [dict(wings=("cima", "cima"), feet=(-1, 1), arms=(((12, 22), (9, 25)), ((20, 22), (24, 24)))),
              dict(base=29, wings=("meio", "meio"), arms=_STILL, por=((SHINE_S, 2, 26),)),
              dict(base=28, wings=("baixo", "baixo"), feet=(1, -1), arms=(((12, 20), (9, 23)), ((20, 20), (24, 22)))),
              dict(base=29, wings=("meio", "meio"), arms=_STILL, por=((SHINE_S, 1, 24),))],
    # acena alto com a mãozinha da frente
    "waving": [dict(eye="feliz", arms=(_STILL[0], ((20, 22), (25, 15)))),
               dict(eye="feliz", wings=("cima", "cima"), arms=(_STILL[0], ((20, 22), (23, 13)))),
               dict(eye="feliz", arms=(_STILL[0], ((20, 22), (26, 16))), por=((SHINE_S, 28, 11),)),
               dict(eye="feliz", wings=("cima", "cima"), arms=(_STILL[0], ((20, 22), (23, 13))))],
    # encolhe as asas, salta batendo as asas, desce planando, pousa
    "jumping": [dict(leg=0, eye="fechado", wings=("fechada", "fechada"),
                     arms=(((12, 24), (10, 28)), ((20, 24), (22, 28)))),
                dict(base=28, eye="cima", wings=("cima", "cima"), arms=(((12, 20), (8, 17)), ((20, 20), (24, 16)))),
                dict(base=27, eye="feliz", wings=("baixo", "baixo"), arms=(((12, 19), (8, 15)), ((20, 19), (24, 14))),
                     por=((SHINE_S, 2, 27), (SHINE_S, 27, 27))),
                dict(base=28, wings=("meio", "meio"), arms=(((12, 20), (9, 22)), ((20, 20), (23, 22)))),
                dict(leg=0, eye="feliz", wings=("fechada", "fechada"),
                     arms=(((12, 24), (10, 28)), ((20, 24), (22, 28))))],
    # cai e o pó apaga: asas murcham, despenca sentada com as asas no chão, o brilho fica cinza
    "failed": [dict(eye="triste", wings=("baixo", "baixo"), arms=_STILL, por=((UNLIT_S, 27, 9),)),
               dict(eye="x", wings=("fechada", "fechada"), arms=_STILL,
                    por=((UNLIT, 25, 12), (UNLIT_S, 4, 10), (UNLIT_S, 27, 22))),
               dict(eye="x", seated=True, wings=("chao", "chao"), unlit=True,
                    arms=(((12, 23), (9, 27)), ((20, 23), (23, 27))), por=((UNLIT, 26, 13), (UNLIT_S, 3, 15))),
               dict(eye="x", seated=True, wings=("chao", "chao"), unlit=True,
                    arms=(((12, 23), (9, 27)), ((20, 23), (23, 27))), por=((UNLIT_S, 27, 19),)),
               dict(eye="x", seated=True, wings=("chao", "chao"), unlit=True,
                    arms=(((12, 23), (9, 27)), ((20, 23), (23, 27))))],
    # dorme de asas fechadas, "z" subindo
    "waiting": [dict(eye="fechado", wings=("fechada", "fechada"), arms=_STILL),
                dict(eye="fechado", wings=("fechada", "fechada"), arms=_STILL, por=((Z_S, 26, 8),)),
                dict(eye="fechado", wings=("fechada", "fechada"), arms=_STILL, por=((Z_S, 25, 9), (Z_L, 26, 0))),
                dict(eye="fechado", wings=("fechada", "fechada"), arms=_STILL, por=((Z_L, 26, 0),))],
    # rajada de pó: junta o pó na mão lá atrás, empurra para a frente e a nuvem de pó estoura
    "running": [dict(cx=14, eye="bravo", wings=("cima", "cima"), arms=(((10, 22), (8, 26)), ((18, 22), (24, 15))),
                     por=((ORB, 23, 10),)),
                dict(cx=14, eye="bravo", wings=("baixo", "baixo"), arms=(((10, 22), (8, 26)), ((18, 22), (24, 21))),
                     por=((TRAIL, 19, 19), (ORB, 24, 19))),
                dict(cx=14, eye="bravo", wings=("meio", "meio"), arms=(((10, 22), (8, 26)), ((18, 22), (22, 21))),
                     por=((CLOUD, 19, 13),)),
                dict(cx=14, eye="feliz", wings=("cima", "cima"), arms=(((10, 22), (8, 26)), ((18, 22), (21, 23))),
                     por=((SHINE, 26, 10), (SHINE_S, 28, 22), (SHINE_S, 23, 16), (SHINE, 25, 25)))],
    # mãozinha no queixo, "?" aparece
    "review": [dict(eye="cima", arms=(_STILL[0], ((20, 22), (21, 20)))),
               dict(eye="cima", arms=(_STILL[0], ((20, 22), (21, 20))), por=((QMARK_S, 26, 4),)),
               dict(eye="cima", arms=(_STILL[0], ((20, 22), (21, 20))), por=((QMARK, 26, 2),)),
               dict(eye="n", arms=(_STILL[0], ((20, 22), (21, 20))), por=((QMARK, 26, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)


# grade 18x10 colada 8 à esquerda do centro e 9 acima do topo da cabeça (cabeça a partir da linha 9, centro na
# coluna 9): antenas grandes de pena; na Eclipse, uma lua crescente flutuando atrás da cabeça
def _antenna(px, base, tip):
    """Antena de pena: haste de `base` a `ponta` com farpas dos dois lados."""
    pts = line(*base, *tip)
    for i, (x, y) in enumerate(pts):
        px[(x, y)] = "A"
        if 1 <= i < len(pts) - 1:
            for dx in (-1, 1):
                if (x + dx, y) not in px:
                    px[(x + dx, y)] = "a"


def _extra(moon):
    g = [["."] * N for _ in range(N)]
    px = {}
    _antenna(px, (7, 9), (4, 2))
    _antenna(px, (11, 9), (15, 2))
    for x, y in ((3, 1), (4, 1), (15, 1), (16, 1)):  # pontinhas enroladas
        px[(x, y)] = "a"
    outline_cells(g, px)
    if moon:
        stamp(g, MOON, 6, 0)
    return ["".join(l[:18]) for l in g[:10]]


MOON = [                                         # lua crescente
    "..KKK.",
    ".KMMK.",
    "KMMK..",
    "KMmK..",
    "KMMK..",
    ".KMMK.",
    "..KKK.",
]
ANTENNAE = _extra(False)
ECLIPSE = _extra(True)
STAGES = [
    {"title": "Lagartinha Lunar", "floor": 1, "extra": None},
    {"title": "Mariposa Lunar", "floor": 4, "extra": ANTENNAE},
    {"title": "Mariposa Eclipse", "floor": 10, "extra": ECLIPSE},
]
