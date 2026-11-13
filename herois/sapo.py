"""Sapo Xamã, 32 px, olhando para a direita. Um sapinho gorducho azul-esverdeado de barriga creme, com os dois
olhões saltados no alto da cabeça e uma máscara de folha (folha verde de nervura clara, ponta para a frente)
cobrindo o rosto abaixo dos olhos. Segura na mão da frente um cajado de madeira com uma bolota de veneno brilhante
na ponta. O símbolo do `running` é o cajado: carrega a bolota, gira o cajado para a frente e o veneno estoura numa
nuvem de bolhas. No `failed` ele afunda na poça do brejo e a máscara boia: entra na água devagar, o cajado tomba,
só os olhos ficam de fora e a máscara de folha fica boiando ao lado.
O tronco e a cabeça andam juntos (só braços, pernas e cajado mudam), para o colar de dentes e o cocar de folhas
dos acréscimos ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha

PAL = {
    "K": "#121a16", "S": "#58c0d0", "s": "#2f7f9a", "C": "#f4ecc0", "c": "#c8bd88", "W": "#ffffff",
    "L": "#6cc24a", "l": "#2f7a2e", "V": "#e2f58a", "D": "#a8743e", "d": "#6a4422", "O": "#b8ff5a",
    "o": "#4fae2e", "U": "#c58cff", "I": "#fff4dc", "F": "#f08a3c", "f": "#a8441e", "A": "#5f7d4a",
    "a": "#3c5430", "B": "#b4d49a", "T": "#8fd8ff", "Y": "#ffd23f", "R": "#ff8fb0",
}

CABECA = (4, 6, 7, 7, 7, 7, 6)                 # meia-largura da cabeça por linha (7 linhas)
TRONCO = (7, 7, 7, 7, 7, 6, 6, 5)              # meia-largura do tronco por linha (8 linhas; a 1ª é a da cabeça)

MASCARA = [                                     # máscara de folha (17x5), cabinho atrás e ponta na frente
    "....KKKKKKKKK....",
    "..KKLLlLLLlLLKK..",
    "KKdlVVVVVVVVVVLLK",
    "..KKLLlLLLlLLKK..",
    "....KKKKKKKKK....",
]
ORBE = [".KKK.", "KOOoK", "KOWOK", "KoOoK", ".KKK."]           # bolota de veneno na ponta do cajado
ORBE_G = ["..K.K..", ".KOKOK.", "KOOOOoK", ".OWWWO.", "KOWWWOK", ".KOOoK.", "..KKK.."]  # bolota carregada
BOLHA = [".K.", "KOK", ".K."]
BOLHA_G = [".KK.", "KOWK", "KOoK", ".KK."]
GOTA = [".K.", "KOK", "KoK", ".K."]
NUVEM = [                                       # o veneno estoura numa nuvem de bolhas
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


def _braco(g, a, b):
    """Bracinho de sapo de 2 px de `a` (ombro) a `b` (mão), com a mão de dedinhos redondos na ponta."""
    px = {}
    for x, y in linha(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px[(x + dx, y + dy)] = "s" if dy else "S"
    bx, by = b
    for x, y in ((bx - 1, by - 1), (bx + 1, by - 1), (bx, by), (bx + 1, by), (bx - 1, by + 1), (bx + 2, by + 1)):
        px[(x, y)] = "S"
    contornar(g, px)


def _cajado(g, topo, pe, orbe=ORBE):
    """Cajado de 2 px de `topo` a `pe` com a bolota de veneno no topo."""
    px = {}
    for x, y in linha(*topo, *pe):
        px[(x, y)] = "D"
        px[(x + 1, y)] = "d"
    contornar(g, px)
    tx, ty = topo
    w = len(orbe[0])
    carimbar(g, orbe, tx + 1 - w // 2, ty - len(orbe) + 1)


def _poca(g, sup, x0, x1):
    """Poça do brejo da linha `sup` até o fundo do quadro, entre x0 e x1 (bordas arredondadas)."""
    px = {}
    for y in range(sup, N):
        r = y - sup
        ind = (3, 1, 0)[min(r, 2)]
        for x in range(x0 + ind, x1 - ind + 1):
            px[(x, y)] = "B" if r == 0 and x % 3 else ("a" if r >= 3 or x in (x0, x1) else "A")
    contornar(g, px)


def _mover(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


def quadro(cx=16, base=30, perna=2, afundar=0, olho="n", pes=(0, 0), bracos=(), cajado=None, orbe=ORBE,
           poca=None, mascara=True, por=()):
    """Um quadro 32x32 e a âncora do acréscimo (9 à esquerda do centro e 11 acima do topo da cabeça).
    `perna`: altura das pernas (0 = agachado); `afundar`: px que o corpo desceu na poça;
    `bracos`: ((ombro), (mão)) e `cajado`: (topo, pé), ambos escritos para a pose padrão (cx=16, base=30,
    perna=2: ombros em (11, 22) e (21, 22)) e deslocados junto com o corpo; `poca`: (linha da superfície,
    x0, x1); `por`: sprites carimbados por último, sem deslocar."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, (base - 30) + (2 - perna) + afundar
    a0 = 21 + dy                                    # topo do tronco (= última linha da cabeça)
    h0 = a0 - 6
    hx = cx + 1
    px = {}
    for i, x0 in enumerate((cx - 5, cx + 2)):       # pernas curtas e pés de nadadeira
        x = x0 + pes[i]
        for y in range(base - perna + 1 + afundar, base + 1 + afundar):
            px[(x, y)] = px[(x + 1, y)] = "s"
        for xx in range(x - 1, x + 3):
            px[(xx, base + afundar)] = "S"
    for r, w in enumerate(TRONCO):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "s" if x == cx - w else "S"
    for r, w in enumerate(CABECA):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "s" if x == hx - w else "S"
    for ox in (-3, 3):                              # olhos saltados no alto da cabeça
        for y in range(h0 - 3, h0 + 2):
            for x in range(hx + ox - 2, hx + ox + 3):
                if (x - hx - ox) ** 2 + (y - h0 + 1) ** 2 <= 5:
                    px[(x, y)] = "S"
    contornar(g, px)
    for r in range(1, 7):                           # barriga creme
        for x in range(cx - 2, cx + TRONCO[r] - 1):
            if 0 <= a0 + r < N:
                g[a0 + r][x] = "c" if x == cx - 2 else "C"
    olhos = {"n": ["WWW", "WKK", "WKK"], "fechado": ["...", "KKK", "..."], "feliz": [".K.", "K.K", "..."],
             "x": ["K.K", ".K.", "K.K"], "cima": ["WKK", "WKK", "WWW"], "triste": ["KKK", "WKK", "WWW"],
             "bravo": (["KK.", "WKK", "WKK"], [".KK", "KKW", "KKW"])}[olho]
    tras, frente = olhos if isinstance(olhos, tuple) else (olhos, olhos)
    carimbar(g, tras, hx - 4, h0 - 2)
    carimbar(g, frente, hx + 2, h0 - 2)
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 4, h0 + 1)
    if mascara:
        carimbar(g, MASCARA, hx - 8, h0 + 1)
    if poca:
        _poca(g, *poca)
    if cajado:
        _cajado(g, _mover(cajado[0], dx, dy), _mover(cajado[1], dx, dy), orbe)
    for a, b in bracos:
        _braco(g, _mover(a, dx, dy), _mover(b, dx, dy))
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 9, h0 - 11)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# pose padrão: tronco 21-28, cabeça 15-21 (hx=17), olhos 12-16; ombros em (11, 22) e (21, 22)
_TRAS = ((11, 22), (8, 26))                     # braço de trás solto
_SEGURA = ((21, 22), (25, 23))                  # mão da frente no cajado
_CAJADO = ((26, 11), (26, 30))                  # cajado fincado no chão
_SPECS = {
    # parado com o cajado fincado: a bolota brilha, pisca, uma bolha sobe
    "idle": [dict(bracos=(_TRAS, _SEGURA), cajado=_CAJADO),
             dict(bracos=(_TRAS, _SEGURA), cajado=_CAJADO, por=((BOLHA, 28, 3),)),
             dict(bracos=(_TRAS, _SEGURA), cajado=_CAJADO, orbe=ORBE_G),
             dict(olho="fechado", bracos=(_TRAS, _SEGURA), cajado=_CAJADO, por=((BOLHA, 29, 1),)),
             dict(bracos=(_TRAS, _SEGURA), cajado=_CAJADO)],
    # pula como sapo: agacha, salta com as pernas esticadas, cai e amortece, cajado deitado para a frente
    "run_r": [dict(perna=0, bracos=(((11, 22), (8, 25)), ((21, 22), (25, 24))), cajado=((29, 15), (21, 29))),
              dict(base=28, perna=3, pes=(-2, 1), bracos=(((11, 22), (6, 21)), ((21, 22), (25, 22))),
                   cajado=((29, 13), (21, 27))),
              dict(base=27, perna=2, pes=(-1, 1), bracos=(((11, 22), (7, 24)), ((21, 22), (25, 23))),
                   cajado=((29, 14), (21, 28)), por=((BOLHA, 2, 27),)),
              dict(base=30, perna=1, bracos=(((11, 22), (8, 25)), ((21, 22), (25, 24))), cajado=((29, 15), (21, 29)))],
    # acena bem alto com a mão de trás, o cajado fincado
    "waving": [dict(olho="feliz", bracos=(((11, 22), (5, 14)), _SEGURA), cajado=_CAJADO),
               dict(olho="feliz", bracos=(((11, 22), (3, 17)), _SEGURA), cajado=_CAJADO),
               dict(olho="feliz", bracos=(((11, 22), (6, 13)), _SEGURA), cajado=_CAJADO, orbe=ORBE_G),
               dict(olho="feliz", bracos=(((11, 22), (3, 17)), _SEGURA), cajado=_CAJADO)],
    # agacha, pula alto erguendo o cajado, desce, pousa
    "jumping": [dict(perna=0, olho="fechado", bracos=(((11, 22), (8, 26)), _SEGURA), cajado=_CAJADO),
                dict(base=27, perna=3, olho="cima", pes=(-1, 1), bracos=(((11, 22), (6, 16)), ((21, 22), (25, 17))),
                     cajado=((26, 11), (26, 27)), orbe=ORBE_G),
                dict(base=27, perna=3, olho="feliz", pes=(-1, 1), bracos=(((11, 22), (6, 15)), ((21, 22), (25, 16))),
                     cajado=((26, 10), (26, 26)), orbe=ORBE_G, por=((BOLHA, 2, 25), (BOLHA_G, 1, 18))),
                dict(base=29, perna=2, bracos=(((11, 22), (7, 20)), ((21, 22), (25, 21))), cajado=((26, 9), (26, 28))),
                dict(perna=0, olho="feliz", bracos=(((11, 22), (8, 26)), _SEGURA), cajado=_CAJADO)],
    # afunda na poça do brejo: entra na água, o cajado tomba e boia, só os olhos ficam de fora, a máscara boia
    "failed": [dict(olho="triste", bracos=(_TRAS, _SEGURA), cajado=((28, 12), (25, 30)), poca=(29, 2, 29)),
               dict(olho="x", afundar=3, bracos=(((11, 22), (6, 20)), ((21, 22), (26, 19))),
                    cajado=((30, 18), (23, 27)), poca=(27, 1, 30), por=((BOLHA, 4, 21),)),
               dict(olho="x", afundar=6, mascara=False, poca=(26, 0, 31),
                    por=(([l[:12] for l in MASCARA], 1, 23), (BOLHA_G, 26, 18), (BOLHA, 23, 13))),
               dict(olho="x", afundar=7, mascara=False, poca=(25, 0, 31),
                    por=((MASCARA, 15, 23), (BOLHA, 3, 20))),
               dict(olho="x", afundar=7, mascara=False, poca=(25, 0, 31),
                    por=((MASCARA, 15, 23), (BOLHA_G, 2, 18)))],
    # cochila agachado abraçado ao cajado, "z" subindo
    "waiting": [dict(perna=0, olho="fechado", bracos=(_TRAS, ((21, 22), (24, 24))), cajado=((25, 17), (25, 30))),
                dict(perna=0, olho="fechado", bracos=(_TRAS, ((21, 22), (24, 24))), cajado=((25, 17), (25, 30)),
                     por=((Z_P, 26, 6),)),
                dict(perna=0, olho="fechado", bracos=(_TRAS, ((21, 22), (24, 24))), cajado=((25, 17), (25, 30)),
                     por=((Z_P, 25, 7), (Z_G, 26, 0))),
                dict(perna=0, olho="fechado", bracos=(_TRAS, ((21, 22), (24, 24))), cajado=((25, 17), (25, 30)),
                     por=((Z_G, 26, 0),))],
    # cajado: ergue e carrega a bolota, gira o cajado para a frente e o veneno estoura numa nuvem de bolhas
    "running": [dict(cx=14, olho="bravo", bracos=(((11, 22), (7, 25)), ((21, 22), (25, 16))),
                     cajado=((26, 7), (26, 24)), orbe=ORBE_G, por=((BOLHA, 30, 10), (BOLHA, 21, 4))),
                dict(cx=14, olho="bravo", bracos=(((11, 22), (6, 24)), ((21, 22), (26, 20))),
                     cajado=((30, 11), (22, 27)), orbe=ORBE_G),
                dict(cx=14, olho="bravo", bracos=(((11, 22), (6, 24)), ((21, 22), (26, 22))),
                     cajado=((31, 18), (21, 25)), por=((NUVEM, 19, 7),)),
                dict(cx=14, olho="feliz", bracos=(((11, 22), (7, 25)), ((21, 22), (25, 23))),
                     cajado=((26, 11), (26, 30)), por=((BOLHA_G, 28, 6), (GOTA, 29, 20), (BOLHA, 23, 14),
                                                        (BOLHA_G, 28, 1)))],
    # mão no queixo da máscara, cajado encostado no ombro, "?" aparece
    "review": [dict(olho="cima", bracos=(_TRAS, ((21, 22), (24, 20))), cajado=((27, 14), (25, 30))),
               dict(olho="cima", bracos=(_TRAS, ((21, 22), (24, 20))), cajado=((27, 14), (25, 30)),
                    por=((INTERROG_P, 26, 1),)),
               dict(olho="cima", bracos=(_TRAS, ((21, 22), (24, 20))), cajado=((27, 14), (25, 30)),
                    por=((INTERROG, 26, 0),)),
               dict(olho="n", bracos=(_TRAS, ((21, 22), (24, 20))), cajado=((27, 14), (25, 30)),
                    por=((INTERROG, 26, 0),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)


# grade 20x21 colada 9 à esquerda do centro e 11 acima do topo da cabeça (topo da cabeça na linha 11, centro
# na coluna 9, olhos nas linhas 8-12): colar de dentes no peito (linhas 15-21); no Ancião, cocar de folhas no alto
def _folha(px, base, ponta, claro, escuro):
    """Folha pontuda de `base` a `ponta`: nervura escura no meio e as laterais claras."""
    pts = linha(*base, *ponta)
    vert = abs(ponta[1] - base[1]) >= abs(ponta[0] - base[0])
    for i, (x, y) in enumerate(pts):
        px[(x, y)] = escuro
        if 0 < i < len(pts) - 1:
            for d in (-1, 1):
                q = (x + d, y) if vert else (x, y + d)
                px.setdefault(q, claro)


def _extra(cocar):
    g = [["."] * N for _ in range(N)]
    if cocar:
        px = {}
        for ponta, (c, e) in (((4, 2), ("L", "l")), ((16, 2), ("L", "l")), ((7, 0), ("F", "f")),
                              ((13, 0), ("F", "f")), ((10, 0), ("L", "l"))):
            _folha(px, (10, 6), ponta, c, e)
        for x, y in ((9, 6), (10, 6), (11, 6), (10, 7)):   # nó do cocar sobre os olhos
            px[(x, y)] = "f"
        contornar(g, px)
    px = {p: "d" for p in ((5, 16), (6, 17), (7, 17), (8, 18), (9, 18), (10, 18), (11, 17), (12, 17), (13, 16))}
    for t in ((6, 18), (12, 18), (9, 19), (9, 20)):    # dentes e a presa grande no meio do colar
        px[t] = "I"
    contornar(g, px)
    return ["".join(l[:20]) for l in g[:21]]


COLAR = _extra(False)
COCAR = _extra(True)
ESTAGIOS = [
    {"title": "Girino Xamã", "floor": 1, "extra": None},
    {"title": "Sapo Xamã", "floor": 4, "extra": COLAR},
    {"title": "Ancião do Brejo", "floor": 10, "extra": COCAR},
]
