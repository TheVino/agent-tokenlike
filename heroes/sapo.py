"""Sapo Xamã, 32 px, olhando para a direita. Um sapinho gorducho azul-esverdeado de barriga creme, com os dois
olhões saltados no alto da cabeça e uma máscara de folha (folha verde de nervura clara, ponta para a frente)
cobrindo o rosto abaixo dos olhos. Segura na mão da frente um cajado de madeira com uma bolota de veneno brilhante
na ponta. O símbolo do `running` é o cajado: carrega a bolota, gira o cajado para a frente e o veneno estoura numa
nuvem de bolhas. No `failed` ele afunda na poça do brejo e a máscara boia: entra na água devagar, o cajado tomba,
só os olhos ficam de fora e a máscara de folha fica boiando ao lado.
O tronco e a cabeça andam juntos (só braços, pernas e cajado mudam), para o colar de dentes e o cocar de folhas
dos acréscimos ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line

PAL = {
    "K": "#121a16", "S": "#58c0d0", "s": "#2f7f9a", "C": "#f4ecc0", "c": "#c8bd88", "W": "#ffffff",
    "L": "#6cc24a", "l": "#2f7a2e", "V": "#e2f58a", "D": "#a8743e", "d": "#6a4422", "O": "#b8ff5a",
    "o": "#4fae2e", "U": "#c58cff", "I": "#fff4dc", "F": "#f08a3c", "f": "#a8441e", "A": "#5f7d4a",
    "a": "#3c5430", "B": "#b4d49a", "T": "#8fd8ff", "Y": "#ffd23f", "R": "#ff8fb0",
}

HEAD = (4, 6, 7, 7, 7, 7, 6)                 # meia-largura da cabeça por linha (7 linhas)
TRUNK = (7, 7, 7, 7, 7, 6, 6, 5)              # meia-largura do tronco por linha (8 linhas; a 1ª é a da cabeça)

MASK = [                                     # máscara de folha (17x5), cabinho atrás e ponta na frente
    "....KKKKKKKKK....",
    "..KKLLlLLLlLLKK..",
    "KKdlVVVVVVVVVVLLK",
    "..KKLLlLLLlLLKK..",
    "....KKKKKKKKK....",
]
ORB = [".KKK.", "KOOoK", "KOWOK", "KoOoK", ".KKK."]           # bolota de veneno na ponta do cajado
ORB_L = ["..K.K..", ".KOKOK.", "KOOOOoK", ".OWWWO.", "KOWWWOK", ".KOOoK.", "..KKK.."]  # bolota carregada
BUBBLE = [".K.", "KOK", ".K."]
BUBBLE_L = [".KK.", "KOWK", "KOoK", ".KK."]
DROP = [".K.", "KOK", "KoK", ".K."]
CLOUD = [                                       # o veneno estoura numa nuvem de bolhas
    "...KK....KK..",
    "..KOWK..KUUK.",
    "..KOOK.KKKKK.",
    ".KKKKKKOOOOOK",
    "KOWKOOOWWOOoK",
    "KOOKOOWWWWOK.",
    ".KKOOOOWWOOoK",
    "..KoOOOOOOOK.",
    ".KKKOOoOoOKK.",
    "KUUK.KKKKK.KK",
    "KUWK....KOWK.",
    ".KK......KK..",
]


def _arm(g, a, b):
    """Bracinho de sapo de 2 px de `a` (ombro) a `b` (mão), com a mão de dedinhos redondos na ponta."""
    px = {}
    for x, y in line(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px[(x + dx, y + dy)] = "s" if dy else "S"
    bx, by = b
    for x, y in ((bx - 1, by - 1), (bx + 1, by - 1), (bx, by), (bx + 1, by), (bx - 1, by + 1), (bx + 2, by + 1)):
        px[(x, y)] = "S"
    outline_cells(g, px)


def _staff(g, top, foot, orb=ORB):
    """Cajado de 2 px de `topo` a `pe` com a bolota de veneno no topo."""
    px = {}
    for x, y in line(*top, *foot):
        px[(x, y)] = "D"
        px[(x + 1, y)] = "d"
    outline_cells(g, px)
    tx, ty = top
    w = len(orb[0])
    stamp(g, orb, tx + 1 - w // 2, ty - len(orb) + 1)


def _puddle(g, sup, x0, x1):
    """Poça do brejo da linha `sup` até o fundo do quadro, entre x0 e x1 (bordas arredondadas)."""
    px = {}
    for y in range(sup, N):
        r = y - sup
        ind = (3, 1, 0)[min(r, 2)]
        for x in range(x0 + ind, x1 - ind + 1):
            px[(x, y)] = "B" if r == 0 and x % 3 else ("a" if r >= 3 or x in (x0, x1) else "A")
    outline_cells(g, px)


def _move(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


def frame(cx=16, base=30, leg=2, sink=0, eye="n", feet=(0, 0), arms=(), staff=None, orb=ORB,
           puddle=None, mask=True, por=()):
    """Um quadro 32x32 e a âncora do acréscimo (9 à esquerda do centro e 11 acima do topo da cabeça).
    `perna`: altura das pernas (0 = agachado); `afundar`: px que o corpo desceu na poça;
    `bracos`: ((ombro), (mão)) e `cajado`: (topo, pé), ambos escritos para a pose padrão (cx=16, base=30,
    perna=2: ombros em (11, 22) e (21, 22)) e deslocados junto com o corpo; `poca`: (linha da superfície,
    x0, x1); `por`: sprites carimbados por último, sem deslocar."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, (base - 30) + (2 - leg) + sink
    a0 = 21 + dy                                    # topo do tronco (= última linha da cabeça)
    h0 = a0 - 6
    hx = cx + 1
    px = {}
    for i, x0 in enumerate((cx - 5, cx + 2)):       # pernas curtas e pés de nadadeira
        x = x0 + feet[i]
        for y in range(base - leg + 1 + sink, base + 1 + sink):
            px[(x, y)] = px[(x + 1, y)] = "s"
        for xx in range(x - 1, x + 3):
            px[(xx, base + sink)] = "S"
    for r, w in enumerate(TRUNK):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "s" if x == cx - w else "S"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "s" if x == hx - w else "S"
    for ox in (-3, 3):                              # olhos saltados no alto da cabeça
        for y in range(h0 - 3, h0 + 2):
            for x in range(hx + ox - 2, hx + ox + 3):
                if (x - hx - ox) ** 2 + (y - h0 + 1) ** 2 <= 5:
                    px[(x, y)] = "S"
    outline_cells(g, px)
    for r in range(1, 7):                           # barriga creme
        for x in range(cx - 2, cx + TRUNK[r] - 1):
            if 0 <= a0 + r < N:
                g[a0 + r][x] = "c" if x == cx - 2 else "C"
    eyes = {"n": ["WWW", "WKK", "WKK"], "fechado": ["...", "KKK", "..."], "feliz": [".K.", "K.K", "..."],
             "x": ["K.K", ".K.", "K.K"], "cima": ["WKK", "WKK", "WWW"], "triste": ["KKK", "WKK", "WWW"],
             "bravo": (["KK.", "WKK", "WKK"], [".KK", "KKW", "KKW"])}[eye]
    back, front = eyes if isinstance(eyes, tuple) else (eyes, eyes)
    stamp(g, back, hx - 4, h0 - 2)
    stamp(g, front, hx + 2, h0 - 2)
    if eye == "triste":
        stamp(g, TEAR, hx - 4, h0 + 1)
    if mask:
        stamp(g, MASK, hx - 8, h0 + 1)
    if puddle:
        _puddle(g, *puddle)
    if staff:
        _staff(g, _move(staff[0], dx, dy), _move(staff[1], dx, dy), orb)
    for a, b in arms:
        _arm(g, _move(a, dx, dy), _move(b, dx, dy))
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 9, h0 - 11)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# pose padrão: tronco 21-28, cabeça 15-21 (hx=17), olhos 12-16; ombros em (11, 22) e (21, 22)
_BACK = ((11, 22), (8, 26))                     # braço de trás solto
_HOLD = ((21, 22), (25, 23))                  # mão da frente no cajado
_STAFF = ((26, 11), (26, 30))                  # cajado fincado no chão
_SPECS = {
    # parado com o cajado fincado: a bolota brilha, pisca, uma bolha sobe
    "idle": [dict(arms=(_BACK, _HOLD), staff=_STAFF),
             dict(arms=(_BACK, _HOLD), staff=_STAFF, por=((BUBBLE, 28, 3),)),
             dict(arms=(_BACK, _HOLD), staff=_STAFF, orb=ORB_L),
             dict(eye="fechado", arms=(_BACK, _HOLD), staff=_STAFF, por=((BUBBLE, 29, 1),)),
             dict(arms=(_BACK, _HOLD), staff=_STAFF)],
    # pula como sapo: agacha, salta com as pernas esticadas, cai e amortece, cajado deitado para a frente
    "run_r": [dict(leg=0, arms=(((11, 22), (8, 25)), ((21, 22), (25, 24))), staff=((29, 15), (21, 29))),
              dict(base=28, leg=3, feet=(-2, 1), arms=(((11, 22), (6, 21)), ((21, 22), (25, 22))),
                   staff=((29, 13), (21, 27))),
              dict(base=27, leg=2, feet=(-1, 1), arms=(((11, 22), (7, 24)), ((21, 22), (25, 23))),
                   staff=((29, 14), (21, 28)), por=((BUBBLE, 2, 27),)),
              dict(base=30, leg=1, arms=(((11, 22), (8, 25)), ((21, 22), (25, 24))), staff=((29, 15), (21, 29)))],
    # acena bem alto com a mão de trás, o cajado fincado
    "waving": [dict(eye="feliz", arms=(((11, 22), (5, 14)), _HOLD), staff=_STAFF),
               dict(eye="feliz", arms=(((11, 22), (3, 17)), _HOLD), staff=_STAFF),
               dict(eye="feliz", arms=(((11, 22), (6, 13)), _HOLD), staff=_STAFF, orb=ORB_L),
               dict(eye="feliz", arms=(((11, 22), (3, 17)), _HOLD), staff=_STAFF)],
    # agacha, pula alto erguendo o cajado, desce, pousa
    "jumping": [dict(leg=0, eye="fechado", arms=(((11, 22), (8, 26)), _HOLD), staff=_STAFF),
                dict(base=27, leg=3, eye="cima", feet=(-1, 1), arms=(((11, 22), (6, 16)), ((21, 22), (25, 17))),
                     staff=((26, 11), (26, 27)), orb=ORB_L),
                dict(base=27, leg=3, eye="feliz", feet=(-1, 1), arms=(((11, 22), (6, 15)), ((21, 22), (25, 16))),
                     staff=((26, 10), (26, 26)), orb=ORB_L, por=((BUBBLE, 2, 25), (BUBBLE_L, 1, 18))),
                dict(base=29, leg=2, arms=(((11, 22), (7, 20)), ((21, 22), (25, 21))), staff=((26, 9), (26, 28))),
                dict(leg=0, eye="feliz", arms=(((11, 22), (8, 26)), _HOLD), staff=_STAFF)],
    # afunda na poça do brejo: entra na água, o cajado tomba e boia, só os olhos ficam de fora, a máscara boia
    "failed": [dict(eye="triste", arms=(_BACK, _HOLD), staff=((28, 12), (25, 30)), puddle=(29, 2, 29)),
               dict(eye="x", sink=3, arms=(((11, 22), (6, 20)), ((21, 22), (26, 19))),
                    staff=((30, 18), (23, 27)), puddle=(27, 1, 30), por=((BUBBLE, 4, 21),)),
               dict(eye="x", sink=6, mask=False, puddle=(26, 0, 31),
                    por=(([l[:12] for l in MASK], 1, 23), (BUBBLE_L, 26, 18), (BUBBLE, 23, 13))),
               dict(eye="x", sink=7, mask=False, puddle=(25, 0, 31),
                    por=((MASK, 15, 23), (BUBBLE, 3, 20))),
               dict(eye="x", sink=7, mask=False, puddle=(25, 0, 31),
                    por=((MASK, 15, 23), (BUBBLE_L, 2, 18)))],
    # cochila agachado abraçado ao cajado, "z" subindo
    "waiting": [dict(leg=0, eye="fechado", arms=(_BACK, ((21, 22), (24, 24))), staff=((25, 17), (25, 30))),
                dict(leg=0, eye="fechado", arms=(_BACK, ((21, 22), (24, 24))), staff=((25, 17), (25, 30)),
                     por=((Z_S, 26, 6),)),
                dict(leg=0, eye="fechado", arms=(_BACK, ((21, 22), (24, 24))), staff=((25, 17), (25, 30)),
                     por=((Z_S, 25, 7), (Z_L, 26, 0))),
                dict(leg=0, eye="fechado", arms=(_BACK, ((21, 22), (24, 24))), staff=((25, 17), (25, 30)),
                     por=((Z_L, 26, 0),))],
    # cajado: ergue e carrega a bolota, gira o cajado para a frente e o veneno estoura numa nuvem de bolhas
    "running": [dict(cx=14, eye="bravo", arms=(((11, 22), (7, 25)), ((21, 22), (25, 16))),
                     staff=((26, 7), (26, 24)), orb=ORB_L, por=((BUBBLE, 30, 10), (BUBBLE, 21, 4))),
                dict(cx=14, eye="bravo", arms=(((11, 22), (6, 24)), ((21, 22), (26, 20))),
                     staff=((30, 11), (22, 27)), orb=ORB_L),
                dict(cx=14, eye="bravo", arms=(((11, 22), (6, 24)), ((21, 22), (26, 22))),
                     staff=((31, 18), (21, 25)), por=((CLOUD, 19, 7),)),
                dict(cx=14, eye="feliz", arms=(((11, 22), (7, 25)), ((21, 22), (25, 23))),
                     staff=((26, 11), (26, 30)), por=((BUBBLE_L, 28, 6), (DROP, 29, 20), (BUBBLE, 23, 14),
                                                        (BUBBLE_L, 28, 1)))],
    # mão no queixo da máscara, cajado encostado no ombro, "?" aparece
    "review": [dict(eye="cima", arms=(_BACK, ((21, 22), (24, 20))), staff=((27, 14), (25, 30))),
               dict(eye="cima", arms=(_BACK, ((21, 22), (24, 20))), staff=((27, 14), (25, 30)),
                    por=((QMARK_S, 26, 1),)),
               dict(eye="cima", arms=(_BACK, ((21, 22), (24, 20))), staff=((27, 14), (25, 30)),
                    por=((QMARK, 26, 0),)),
               dict(eye="n", arms=(_BACK, ((21, 22), (24, 20))), staff=((27, 14), (25, 30)),
                    por=((QMARK, 26, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)


# grade 20x21 colada 9 à esquerda do centro e 11 acima do topo da cabeça (topo da cabeça na linha 11, centro
# na coluna 9, olhos nas linhas 8-12): colar de dentes no peito (linhas 15-21); no Ancião, cocar de folhas no alto
def _sheet(px, base, tip, claro, dark):
    """Folha pontuda de `base` a `ponta`: nervura escura no meio e as laterais claras."""
    pts = line(*base, *tip)
    vert = abs(tip[1] - base[1]) >= abs(tip[0] - base[0])
    for i, (x, y) in enumerate(pts):
        px[(x, y)] = dark
        if 0 < i < len(pts) - 1:
            for d in (-1, 1):
                q = (x + d, y) if vert else (x, y + d)
                px.setdefault(q, claro)


def _extra(headdress):
    g = [["."] * N for _ in range(N)]
    if headdress:
        px = {}
        for tip, (c, e) in (((4, 2), ("L", "l")), ((16, 2), ("L", "l")), ((7, 0), ("F", "f")),
                              ((13, 0), ("F", "f")), ((10, 0), ("L", "l"))):
            _sheet(px, (10, 6), tip, c, e)
        for x, y in ((9, 6), (10, 6), (11, 6), (10, 7)):   # nó do cocar sobre os olhos
            px[(x, y)] = "f"
        outline_cells(g, px)
    px = {p: "d" for p in ((5, 16), (6, 17), (7, 17), (8, 18), (9, 18), (10, 18), (11, 17), (12, 17), (13, 16))}
    for t in ((6, 18), (12, 18), (9, 19), (9, 20)):    # dentes e a presa grande no meio do colar
        px[t] = "I"
    outline_cells(g, px)
    return ["".join(l[:20]) for l in g[:21]]


NECKLACE = _extra(False)
HEADDRESS = _extra(True)
STAGES = [
    {"title": "Girino Xamã", "floor": 1, "extra": None},
    {"title": "Sapo Xamã", "floor": 4, "extra": NECKLACE},
    {"title": "Ancião do Brejo", "floor": 10, "extra": HEADDRESS},
]
