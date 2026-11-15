"""Corvo Mensageiro, 32 px, olhando para a direita. Um corvinho redondo de penas ardósia, bico âmbar, olho branco
brilhante, rabo em leque e asas grandes de pontas claras. O símbolo é a carta lacrada (envelope creme com lacre
vermelho), que ele leva no bico: balança no idle, vira arma na bicada dupla do `running`. No `failed` ele leva o
golpe, a carta escapa do bico e voa para longe enquanto o corvo desaba de asas abertas, com uma pena solta no ar.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, mirror, trait

PAL = {
    "K": "#0d0a12", "B": "#3d3858", "b": "#29253c", "P": "#5e5882", "A": "#4b4574", "a": "#9a94c8",
    "W": "#f4f6fb", "Y": "#f0b030", "y": "#a8701c", "L": "#e0913a", "C": "#f4ead2", "c": "#c9b994",
    "R": "#c8334a", "r": "#7e1f33", "D": "#7a4a28", "d": "#4e2e16", "H": "#5a2a6e", "h": "#3a1a48",
    "G": "#ffd23f", "g": "#b8860b", "T": "#8fd8ff", "N": "#7f92d6",
}

BODY = (3, 5, 6, 7, 7, 7, 7, 7, 6, 6, 5, 3)           # meia-largura do corpo por linha (12 linhas)
BODY_LOW = (4, 6, 7, 7, 7, 7, 6, 5, 3)              # corpo agachado (9 linhas)
BODY_FLAT = (5, 7, 8, 8, 8, 7, 5)                    # corpo desabado (7 linhas)
HEAD = (2, 4, 5, 5, 5, 5, 5, 4, 3)                   # meia-largura da cabeça (9 linhas)

CARD = [
    "KKKKKKKKK",
    "KCcCCCcCK",
    "KCCcRRCCK",
    "KCCCrRCCK",
    "KKKKKKKKK",
]
CARD_STANDING = [                                         # a carta girada (voando no failed)
    "KKKKK",
    "KCCCK",
    "KcCCK",
    "KCcCK",
    "KCRrK",
    "KCRRK",
    "KCcCK",
    "KcCCK",
    "KKKKK",
]
# asa erguida (pontas para cima), a base encosta nas costas
WING_UP = [
    "K.K.K.....",
    "KaKaKK....",
    "KaKaKaK...",
    "KaAaAaAK..",
    "KAAAAAAaK.",
    ".KAAAAAAAK",
    "..KAAAAAAK",
    "...KAAAAK.",
    "....KKKK..",
]
WING_DOWN = WING_UP[::-1]                              # empurrando o ar para baixo
WING_WAVE = mirror(WING_UP)                           # pontas para a frente (acenando)
WING_FRONT = [                                          # esticada para a frente, pontas para a direita
    ".KKKKKKKKK...",
    "KAAAAAAAAAKK.",
    "KAAAAAAaaaaaK",
    ".KAAAAaKaKaKK",
    "..KKKKK.K.K..",
]
WING_CLOSED = [
    "..KKKKKK.",
    ".KAAAAAAK",
    "KAaAAAAAK",
    "KAAaAAAK.",
    ".KAAaAK..",
    "..KaAK...",
    "...KK....",
]
WING_DROOP = [                                           # asa largada no chão
    ".KKKKKKK..",
    "KAAAAAAAKK",
    "KaAaAaAaAK",
    ".KaKaKaKK.",
    "..K.K.K...",
]
SHINE = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
SHINE_S = [".K.", "KWK", ".K."]
FEATHER = ["...KK", "..KaK", ".KaAK", "KaAK.", "KKK.."]
WIND = ["KKKK...", "..KKKK.", "....KKK"]                # risquinhos de vento do golpe de asa


def frame(cx=12, base=30, leg=3, body=BODY, eye="n", beak="f", card="bico", cdy=0, wing=(WING_CLOSED, -5, -2),
           feet=(0, 0), por=(), behind=()):
    """Um quadro 32x32 e a âncora do acréscimo (10 à esquerda e 5 acima do topo da cabeça).
    `asa`: (sprite, dx, dy) relativo ao centro do corpo; `carta`: "bico" (presa no bico, `cdy` balança),
    None ou (sprite, x, y) absoluto."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    backdrop = base - leg - 1
    bt = backdrop - len(body) + 1
    htop, hx = bt - 6, cx + 3
    for i, px in enumerate((cx - 2, cx + 2)):          # perninhas com dedos
        if leg:
            x = px + feet[i]
            trait(g, (x, backdrop), (x, base - 1), "L")
            trait(g, (x - 1, base), (x + 1, base), "L")
    px = {}
    for r, w in enumerate(body):
        y = bt + r
        for x in range(cx - w, cx + w + 1):
            front = x > cx and r > len(body) // 3
            px[(x, y)] = "P" if front else ("b" if x <= cx - w + 1 else "B")
    tail_tip = ((-11, -6), (-12, -6), (-12, -7), (-11, -9))  # leque do rabo, para trás e para baixo
    for i, (a, b) in enumerate(tail_tip):
        for x in range(cx + a, cx + b + 1):
            px[(x, bt + 5 + i)] = "B" if (x + i) % 3 == 0 else "b"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, htop + r)] = "P" if r == 1 and x < hx + 2 else "B"
    if beak == "f":
        parts = ((4, 4, 8, "Y"), (5, 4, 9, "Y"), (6, 4, 7, "y"))
    else:                                               # aberto: uma fresta escura entre as duas metades
        parts = ((3, 4, 8, "Y"), (4, 4, 9, "Y"), (6, 4, 8, "y"))
    for r, a, b, color in parts:
        for x in range(hx + a, hx + b + 1):
            px[(x, htop + r)] = color
    for (x, y), c in list(px.items()):                  # brilho azulado no alto das penas (contraste em fundo escuro)
        if c in "BbP" and (x, y - 1) not in px:
            px[(x, y)] = "N"
    outline_cells(g, px)
    if beak != "f":
        for x in range(hx + 5, hx + 9):
            g[htop + 5][x] = "K"
    ex, ey = hx + 1, htop + 3
    eyes = {"n": ["WK", "WW"], "baixo": ["WW", "WK"], "fechado": ["..", "aa"], "feliz": [".W.", "W.W"],
             "x": ["W.W", ".W.", "W.W"], "triste": ["a..", "WW.", "WK."], "bravo": ["aa.", ".aa", ".WK"]}[eye]
    stamp(g, eyes, ex - (eye in ("triste", "bravo", "x")), ey - (eye in ("triste", "bravo", "x")))
    if eye == "triste":
        stamp(g, TEAR, ex, ey + 2)
    if wing:
        s, dx, dy = wing
        stamp(g, s, cx + dx, bt + 5 + dy)
    if card == "bico":
        stamp(g, CARD, hx + 7, htop + 4 + cdy)
    elif card:
        stamp(g, *card)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (hx - 10, htop - 5)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=3 -> corpo 15-26 (centro x=12), cabeça 9-17 (centro x=15), bico até x=24, carta em 22-30
_SPECS = {
    # parado com a carta no bico, que balança; pisca uma vez
    "idle": [dict(), dict(cdy=1), dict(cdy=1, eye="fechado"), dict(), dict(cdy=-1)],
    # trotando com as perninhas, asas meio abertas batendo, carta firme no bico
    "run_r": [dict(feet=(-2, 2), wing=(WING_CLOSED, -6, -3)),
              dict(base=29, leg=2, wing=(WING_UP, -11, -10)),
              dict(feet=(2, -2), wing=(WING_CLOSED, -6, -3)),
              dict(base=29, leg=2, wing=(WING_UP, -11, -10))],
    # abana a asa erguida para um lado e para o outro, olho feliz
    "waving": [dict(eye="feliz", wing=(WING_UP, -11, -12)),
               dict(eye="feliz", wing=(WING_WAVE, -9, -13)),
               dict(eye="feliz", wing=(WING_UP, -11, -12)),
               dict(eye="feliz", wing=(WING_WAVE, -9, -13))],
    # agacha, empurra o ar com as asas, sobe de asas abertas, desce e pousa
    "jumping": [dict(leg=1, body=BODY_LOW, eye="fechado", wing=(WING_CLOSED, -5, -3)),
                dict(base=28, wing=(WING_DOWN, -7, -1)),
                dict(base=26, eye="feliz", wing=(WING_UP, -11, -12)),
                dict(base=27, wing=(WING_UP, -11, -11)),
                dict(leg=1, body=BODY_LOW, eye="feliz", wing=(WING_CLOSED, -5, -3))],
    # leva o golpe, solta a carta (que voa para longe) e desaba de asas abertas no chão
    "failed": [dict(eye="triste", beak="a", card=(CARD, 22, 16)),
               dict(eye="x", beak="a", leg=2, body=BODY_LOW, wing=(WING_UP, -11, -10),
                    card=(CARD_STANDING, 25, 6), por=((FEATHER, 25, 20),)),
               dict(eye="x", beak="a", leg=0, body=BODY_FLAT, wing=(WING_DROOP, -12, 1),
                    card=(CARD, 22, 1), por=((FEATHER, 24, 15),)),
               dict(eye="x", leg=0, body=BODY_FLAT, wing=(WING_DROOP, -12, 1),
                    card=(CARD_STANDING, 26, 0), por=((FEATHER, 23, 22),)),
               dict(eye="x", leg=0, body=BODY_FLAT, wing=(WING_DROOP, -12, 1),
                    card=None, por=((FEATHER, 25, 25),))],
    # cochila sentadinho, cabeça baixa, carta no chão ao lado, "z" subindo
    "waiting": [dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26)),
                dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26), por=((Z_S, 25, 7),)),
                dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26),
                     por=((Z_S, 24, 8), (Z_L, 26, 0))),
                dict(leg=1, body=BODY_LOW, eye="fechado", card=(CARD, 21, 26), por=((Z_L, 26, 0),))],
    # bicada dupla: arma para trás, bica com a carta (brilho), bica de novo com golpe de asa, volta
    "running": [dict(cx=11, eye="bravo", wing=(WING_UP, -11, -12)),
                dict(cx=13, eye="bravo", wing=(WING_DOWN, -8, -1), cdy=-1, por=((SHINE, 25, 5),)),
                dict(cx=13, eye="bravo", wing=(WING_FRONT, 0, 3), cdy=1,
                     por=((SHINE, 25, 12), (SHINE_S, 29, 7), (WIND, 24, 27))),
                dict(cx=12, eye="bravo", wing=(WING_CLOSED, -5, -2))],
    # lê a carta segurada na ponta da asa, olho baixo; "?" aparece
    "review": [dict(eye="baixo", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3)),
               dict(eye="baixo", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3), por=((QMARK_S, 25, 3),)),
               dict(eye="n", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3), por=((QMARK, 25, 1),)),
               dict(eye="baixo", card=(CARD, 22, 23), wing=(WING_FRONT, -1, 3), por=((QMARK, 25, 1),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 16x20 colada 10 à esquerda e 5 acima do topo da cabeça (cabeça nas linhas 5-13, centro na coluna 10;
# corpo a partir da linha 11, centro na coluna 7): bolsa de cartas no peito com alça no pescoço; capuz roxo de
# arauto com uma pluma dourada
_BAG = [
    "K.......",
    "dK......",
    ".dK.KKK.",
    "..dKCCK.",
    "..KKKKKKK",
    "..KDDDDDK",
    "..KdddddK",
    "..KDDGDDK",
    "..KDDDDDK",
    "...KKKKK.",
]
_HOOD = [
    "...KK...........",
    "..KGGK..........",
    "..KGgGK.........",
    "...KGgGKKKK.....",
    "....KHHHHHHKK...",
    "...KHHHHHHHHHK..",
    "..KHhHHHHHHHHHK.",
    "..KHhHHHHKKKKKK.",
    "..KHHhHHK.......",
    "..KHHhHK........",
    "...KKKK.........",
]


def _extra(pieces, w=16, h=20):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BAG = _extra(((_BAG, 6, 10),))
BAG_HOOD = _extra(((_BAG, 6, 10), (_HOOD, 0, 0)))
STAGES = [
    {"title": "Filhote de Corvo", "floor": 1, "extra": None},
    {"title": "Corvo Mensageiro", "floor": 4, "extra": BAG},
    {"title": "Corvo Arauto", "floor": 10, "extra": BAG_HOOD},
]
