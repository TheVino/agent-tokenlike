"""Corvo Mensageiro, 32 px, olhando para a direita. Um corvinho redondo de penas ardósia, bico âmbar, olho branco
brilhante, rabo em leque e asas grandes de pontas claras. O símbolo é a carta lacrada (envelope creme com lacre
vermelho), que ele leva no bico: balança no idle, vira arma na bicada dupla do `running`. No `failed` ele leva o
golpe, a carta escapa do bico e voa para longe enquanto o corvo desaba de asas abertas, com uma pena solta no ar.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, espelho, traco

PAL = {
    "K": "#0d0a12", "B": "#3d3858", "b": "#29253c", "P": "#5e5882", "A": "#4b4574", "a": "#9a94c8",
    "W": "#f4f6fb", "Y": "#f0b030", "y": "#a8701c", "L": "#e0913a", "C": "#f4ead2", "c": "#c9b994",
    "R": "#c8334a", "r": "#7e1f33", "D": "#7a4a28", "d": "#4e2e16", "H": "#5a2a6e", "h": "#3a1a48",
    "G": "#ffd23f", "g": "#b8860b", "T": "#8fd8ff", "N": "#7f92d6",
}

CORPO = (3, 5, 6, 7, 7, 7, 7, 7, 6, 6, 5, 3)           # meia-largura do corpo por linha (12 linhas)
CORPO_BAIXO = (4, 6, 7, 7, 7, 7, 6, 5, 3)              # corpo agachado (9 linhas)
CORPO_CHATO = (5, 7, 8, 8, 8, 7, 5)                    # corpo desabado (7 linhas)
CABECA = (2, 4, 5, 5, 5, 5, 5, 4, 3)                   # meia-largura da cabeça (9 linhas)

CARTA = [
    "KKKKKKKKK",
    "KCcCCCcCK",
    "KCCcRRCCK",
    "KCCCrRCCK",
    "KKKKKKKKK",
]
CARTA_EM_PE = [                                         # a carta girada (voando no failed)
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
ASA_CIMA = [
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
ASA_BAIXO = ASA_CIMA[::-1]                              # empurrando o ar para baixo
ASA_ACENO = espelho(ASA_CIMA)                           # pontas para a frente (acenando)
ASA_FRENTE = [                                          # esticada para a frente, pontas para a direita
    ".KKKKKKKKK...",
    "KAAAAAAAAAKK.",
    "KAAAAAAaaaaaK",
    ".KAAAAaKaKaKK",
    "..KKKKK.K.K..",
]
ASA_FECHADA = [
    "..KKKKKK.",
    ".KAAAAAAK",
    "KAaAAAAAK",
    "KAAaAAAK.",
    ".KAAaAK..",
    "..KaAK...",
    "...KK....",
]
ASA_CAIDA = [                                           # asa largada no chão
    ".KKKKKKK..",
    "KAAAAAAAKK",
    "KaAaAaAaAK",
    ".KaKaKaKK.",
    "..K.K.K...",
]
BRILHO = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
BRILHO_P = [".K.", "KWK", ".K."]
PENA = ["...KK", "..KaK", ".KaAK", "KaAK.", "KKK.."]
VENTO = ["KKKK...", "..KKKK.", "....KKK"]                # risquinhos de vento do golpe de asa


def quadro(cx=12, base=30, perna=3, corpo=CORPO, olho="n", bico="f", carta="bico", cdy=0, asa=(ASA_FECHADA, -5, -2),
           pes=(0, 0), por=(), atras=()):
    """Um quadro 32x32 e a âncora do acréscimo (10 à esquerda e 5 acima do topo da cabeça).
    `asa`: (sprite, dx, dy) relativo ao centro do corpo; `carta`: "bico" (presa no bico, `cdy` balança),
    None ou (sprite, x, y) absoluto."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in atras:
        carimbar(g, s, x, y)
    fundo = base - perna - 1
    bt = fundo - len(corpo) + 1
    htop, hx = bt - 6, cx + 3
    for i, px in enumerate((cx - 2, cx + 2)):          # perninhas com dedos
        if perna:
            x = px + pes[i]
            traco(g, (x, fundo), (x, base - 1), "L")
            traco(g, (x - 1, base), (x + 1, base), "L")
    px = {}
    for r, w in enumerate(corpo):
        y = bt + r
        for x in range(cx - w, cx + w + 1):
            frente = x > cx and r > len(corpo) // 3
            px[(x, y)] = "P" if frente else ("b" if x <= cx - w + 1 else "B")
    rabo = ((-11, -6), (-12, -6), (-12, -7), (-11, -9))  # leque do rabo, para trás e para baixo
    for i, (a, b) in enumerate(rabo):
        for x in range(cx + a, cx + b + 1):
            px[(x, bt + 5 + i)] = "B" if (x + i) % 3 == 0 else "b"
    for r, w in enumerate(CABECA):
        for x in range(hx - w, hx + w + 1):
            px[(x, htop + r)] = "P" if r == 1 and x < hx + 2 else "B"
    if bico == "f":
        partes = ((4, 4, 8, "Y"), (5, 4, 9, "Y"), (6, 4, 7, "y"))
    else:                                               # aberto: uma fresta escura entre as duas metades
        partes = ((3, 4, 8, "Y"), (4, 4, 9, "Y"), (6, 4, 8, "y"))
    for r, a, b, cor in partes:
        for x in range(hx + a, hx + b + 1):
            px[(x, htop + r)] = cor
    for (x, y), c in list(px.items()):                  # brilho azulado no alto das penas (contraste em fundo escuro)
        if c in "BbP" and (x, y - 1) not in px:
            px[(x, y)] = "N"
    contornar(g, px)
    if bico != "f":
        for x in range(hx + 5, hx + 9):
            g[htop + 5][x] = "K"
    ex, ey = hx + 1, htop + 3
    olhos = {"n": ["WK", "WW"], "baixo": ["WW", "WK"], "fechado": ["..", "aa"], "feliz": [".W.", "W.W"],
             "x": ["W.W", ".W.", "W.W"], "triste": ["a..", "WW.", "WK."], "bravo": ["aa.", ".aa", ".WK"]}[olho]
    carimbar(g, olhos, ex - (olho in ("triste", "bravo", "x")), ey - (olho in ("triste", "bravo", "x")))
    if olho == "triste":
        carimbar(g, LAGRIMA, ex, ey + 2)
    if asa:
        s, dx, dy = asa
        carimbar(g, s, cx + dx, bt + 5 + dy)
    if carta == "bico":
        carimbar(g, CARTA, hx + 7, htop + 4 + cdy)
    elif carta:
        carimbar(g, *carta)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (hx - 10, htop - 5)


def _estado(specs):
    qs = [quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, perna=3 -> corpo 15-26 (centro x=12), cabeça 9-17 (centro x=15), bico até x=24, carta em 22-30
_SPECS = {
    # parado com a carta no bico, que balança; pisca uma vez
    "idle": [dict(), dict(cdy=1), dict(cdy=1, olho="fechado"), dict(), dict(cdy=-1)],
    # trotando com as perninhas, asas meio abertas batendo, carta firme no bico
    "run_r": [dict(pes=(-2, 2), asa=(ASA_FECHADA, -6, -3)),
              dict(base=29, perna=2, asa=(ASA_CIMA, -11, -10)),
              dict(pes=(2, -2), asa=(ASA_FECHADA, -6, -3)),
              dict(base=29, perna=2, asa=(ASA_CIMA, -11, -10))],
    # abana a asa erguida para um lado e para o outro, olho feliz
    "waving": [dict(olho="feliz", asa=(ASA_CIMA, -11, -12)),
               dict(olho="feliz", asa=(ASA_ACENO, -9, -13)),
               dict(olho="feliz", asa=(ASA_CIMA, -11, -12)),
               dict(olho="feliz", asa=(ASA_ACENO, -9, -13))],
    # agacha, empurra o ar com as asas, sobe de asas abertas, desce e pousa
    "jumping": [dict(perna=1, corpo=CORPO_BAIXO, olho="fechado", asa=(ASA_FECHADA, -5, -3)),
                dict(base=28, asa=(ASA_BAIXO, -7, -1)),
                dict(base=26, olho="feliz", asa=(ASA_CIMA, -11, -12)),
                dict(base=27, asa=(ASA_CIMA, -11, -11)),
                dict(perna=1, corpo=CORPO_BAIXO, olho="feliz", asa=(ASA_FECHADA, -5, -3))],
    # leva o golpe, solta a carta (que voa para longe) e desaba de asas abertas no chão
    "failed": [dict(olho="triste", bico="a", carta=(CARTA, 22, 16)),
               dict(olho="x", bico="a", perna=2, corpo=CORPO_BAIXO, asa=(ASA_CIMA, -11, -10),
                    carta=(CARTA_EM_PE, 25, 6), por=((PENA, 25, 20),)),
               dict(olho="x", bico="a", perna=0, corpo=CORPO_CHATO, asa=(ASA_CAIDA, -12, 1),
                    carta=(CARTA, 22, 1), por=((PENA, 24, 15),)),
               dict(olho="x", perna=0, corpo=CORPO_CHATO, asa=(ASA_CAIDA, -12, 1),
                    carta=(CARTA_EM_PE, 26, 0), por=((PENA, 23, 22),)),
               dict(olho="x", perna=0, corpo=CORPO_CHATO, asa=(ASA_CAIDA, -12, 1),
                    carta=None, por=((PENA, 25, 25),))],
    # cochila sentadinho, cabeça baixa, carta no chão ao lado, "z" subindo
    "waiting": [dict(perna=1, corpo=CORPO_BAIXO, olho="fechado", carta=(CARTA, 21, 26)),
                dict(perna=1, corpo=CORPO_BAIXO, olho="fechado", carta=(CARTA, 21, 26), por=((Z_P, 25, 7),)),
                dict(perna=1, corpo=CORPO_BAIXO, olho="fechado", carta=(CARTA, 21, 26),
                     por=((Z_P, 24, 8), (Z_G, 26, 0))),
                dict(perna=1, corpo=CORPO_BAIXO, olho="fechado", carta=(CARTA, 21, 26), por=((Z_G, 26, 0),))],
    # bicada dupla: arma para trás, bica com a carta (brilho), bica de novo com golpe de asa, volta
    "running": [dict(cx=11, olho="bravo", asa=(ASA_CIMA, -11, -12)),
                dict(cx=13, olho="bravo", asa=(ASA_BAIXO, -8, -1), cdy=-1, por=((BRILHO, 25, 5),)),
                dict(cx=13, olho="bravo", asa=(ASA_FRENTE, 0, 3), cdy=1,
                     por=((BRILHO, 25, 12), (BRILHO_P, 29, 7), (VENTO, 24, 27))),
                dict(cx=12, olho="bravo", asa=(ASA_FECHADA, -5, -2))],
    # lê a carta segurada na ponta da asa, olho baixo; "?" aparece
    "review": [dict(olho="baixo", carta=(CARTA, 22, 23), asa=(ASA_FRENTE, -1, 3)),
               dict(olho="baixo", carta=(CARTA, 22, 23), asa=(ASA_FRENTE, -1, 3), por=((INTERROG_P, 25, 3),)),
               dict(olho="n", carta=(CARTA, 22, 23), asa=(ASA_FRENTE, -1, 3), por=((INTERROG, 25, 1),)),
               dict(olho="baixo", carta=(CARTA, 22, 23), asa=(ASA_FRENTE, -1, 3), por=((INTERROG, 25, 1),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)

# grade 16x20 colada 10 à esquerda e 5 acima do topo da cabeça (cabeça nas linhas 5-13, centro na coluna 10;
# corpo a partir da linha 11, centro na coluna 7): bolsa de cartas no peito com alça no pescoço; capuz roxo de
# arauto com uma pluma dourada
_BOLSA = [
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
_CAPUZ = [
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


def _extra(pecas, w=16, h=20):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pecas:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != ".":
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BOLSA = _extra(((_BOLSA, 6, 10),))
BOLSA_CAPUZ = _extra(((_BOLSA, 6, 10), (_CAPUZ, 0, 0)))
ESTAGIOS = [
    {"title": "Filhote de Corvo", "floor": 1, "extra": None},
    {"title": "Corvo Mensageiro", "floor": 4, "extra": BOLSA},
    {"title": "Corvo Arauto", "floor": 10, "extra": BOLSA_CAPUZ},
]
