"""Gato Preto de Cemitério, 32 px, olhando para a frente. Um gatinho preto sentado, cabeçudo, de orelhas
pontudas com o miolo rosado, olhões amarelos, bigodes claros, patinhas brancas (meias) e o rabo curvado atrás.
Usa uma coleira vermelha com um sino dourado. Como o corpo é preto, toda a borda de cima e da direita leva um
brilho lilás (e a da esquerda um lilás mais escuro), para o gato não sumir num fundo escuro; olhos fechados,
boca e sobrancelhas são riscos lilás pelo mesmo motivo.
O símbolo do `running` é a patada: arma a pata, avança e risca o ar com três arranhões brancos. No `failed` ele
se enrola: fica triste, deita enrolado numa bolinha com o rabo na frente e o sino toca uma última vez.
Os gestos são sempre da pata da frente (direita); o lenço do 2º estágio dá o nó do lado de trás (esquerda).
O tronco e a cabeça andam juntos (só patas, pernas e rabo mudam), para o lenço e as velinhas dos acréscimos
ficarem sempre no lugar. Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, outline_cells, line, trait

PAL = {
    "K": "#07060c", "P": "#2c2742", "M": "#a597ec", "m": "#5f5596", "Y": "#ffd23f", "y": "#b8841a",
    "W": "#f4f2fa", "w": "#bab6cc", "R": "#ff8fb0", "r": "#b05a7e", "V": "#e0384e", "v": "#8e1e30",
    "L": "#9a5cd8", "l": "#5e2f94", "I": "#fff4dc", "i": "#d8c8a0", "F": "#ff9a3c", "T": "#8fd8ff",
}

HEAD = (5, 6, 7, 7, 7, 7, 7, 6, 5)            # meia-largura da cabeça por linha (9 linhas; a última é a coleira)
TRUNK = (5, 6, 6, 7, 7, 7, 7, 6)               # meia-largura do tronco por linha (8 linhas; a 1ª é a da coleira)


def _claws(n=3, comp=8):
    """Arranhões: `n` riscos brancos na diagonal, do alto à direita para baixo à esquerda, com contorno."""
    g = [["."] * N for _ in range(N)]
    px = {}
    for i in range(n):
        for x, y in line(comp - 1 + 3 * i, 1, 1 + 3 * i, comp):
            px[(x, y)] = "W"
    outline_cells(g, px)
    w = 3 * n + comp
    return ["".join(l[:w]) for l in g[:comp + 2]]


SCRATCH = _claws(3, 7)
SCRATCH_S = _claws(3, 5)
SPARK = [".K.", "KYK", ".K."]


def _rim(px):
    """Brilho lilás nas bordas do pelo preto: claro em cima e à direita, escuro à esquerda."""
    out = {}
    for (x, y), c in px.items():
        if c == "P":
            if (x, y - 1) not in px or (x + 1, y) not in px:
                c = "M"
            elif (x - 1, y) not in px:
                c = "m"
        out[(x, y)] = c
    return out


def _arm(g, a, b):
    """Patinha de 2 px de `a` (ombro) a `b` (pata), com a pata branca 3x3 e o feijãozinho rosa no meio."""
    px = {}
    for x, y in line(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px.setdefault((x + dx, y + dy), "m" if dy == 0 else "P")
    bx, by = b
    for x in range(bx - 1, bx + 2):
        for y in range(by - 1, by + 2):
            px[(x, y)] = "W"
    px[(bx, by)] = "R"
    px[(bx - 1, by + 1)] = px[(bx + 1, by + 1)] = "w"
    outline_cells(g, px)


def _tail(px, pts):
    """Rabo de 2 px pelos pontos `pts` (da base à ponta)."""
    for p, q in zip(pts, pts[1:]):
        for x, y in line(*p, *q):
            px[(x, y)] = px[(x + 1, y)] = "P"


def _bell(g, x, y, sound=0):
    """Sino dourado pendurado em (x, y); `som` desenha os riscos de toque (0, 1 ou 2 de tamanho)."""
    px = {(x, y): "y", (x - 1, y + 1): "Y", (x, y + 1): "W", (x + 1, y + 1): "Y", (x - 1, y + 2): "Y",
          (x, y + 2): "Y", (x + 1, y + 2): "y", (x, y + 3): "y"}
    outline_cells(g, px)
    for k in range(sound):                        # riscos de toque em "\ /" saindo do sino, um par por nível
        for s in (-1, 1):
            trait(g, (x + s * (3 + k), y + 1 - 3 * k), (x + s * (5 + k), y - 1 - 3 * k), "Y")


def _move(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


EYES = {"n": ["YYY", "YKY", "YKY"], "fechado": ["...", "MMM", "..."], "feliz": [".M.", "M.M", "..."],
         "x": ["M.M", ".M.", "M.M"], "cima": ["YKY", "YKY", "YYY"], "triste": ["...", "YYY", "YKY"],
         "bravo": (["M..", "YYY", "YKY"], ["..M", "YYY", "YKY"])}


def _face(g, hx, h0, eye):
    back, front = EYES[eye] if isinstance(EYES[eye], tuple) else (EYES[eye], EYES[eye])
    stamp(g, back, hx - 4, h0 + 2)
    stamp(g, front, hx + 2, h0 + 2)
    if eye == "triste":
        stamp(g, TEAR, hx - 4, h0 + 5)
    g[h0 + 5][hx] = "R"                         # focinho
    for x in (hx - 1, hx + 1):                  # boquinha "w"
        g[h0 + 6][x] = "M"
    for y in (h0 + 5, h0 + 7):                  # bigodes
        for d in (5, 6, 7, 8):
            for x in (hx - d, hx + d):
                if 0 <= x < N and (g[y][x] != "." or d >= 7):
                    g[y][x] = "w"


def frame(cx=16, base=30, leg=2, eye="n", feet=(0, 0), arms=(), tail=0, sound=0, por=()):
    """Um quadro 32x32 e a âncora do acréscimo (9 à esquerda do centro e 11 acima do topo da cabeça).
    `perna`: altura das pernas (0 = deitado); `bracos`: ((ombro), (pata)) escritos para a pose padrão
    (cx=16, base=30, perna=2: ombros em (11, 23) e (21, 23)) e deslocados junto com o corpo;
    `cauda`: pose do rabo (0 a 3); `por`: sprites carimbados por último, sem deslocar."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, (base - 30) + (2 - leg)
    a0 = 21 + dy                                    # topo do tronco (= coleira, última linha da cabeça)
    h0 = a0 - 8
    hx = cx + 1
    px = {}
    tip = ((-11, -1), (-12, -4), (-10, -6), (-13, -2))[tail]
    _tail(px, [(cx - 5, a0 + 6), (cx - 10, a0 + 4), (cx + tip[0], a0 + tip[1])])
    for i, x0 in enumerate((cx - 4, cx + 2)):       # perninhas com meia branca
        x = x0 + feet[i]
        for y in range(base - leg + 1, base + 1):
            px[(x, y)] = px[(x + 1, y)] = "P"
    for r, w in enumerate(TRUNK):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "P"
    for r, w in enumerate(HEAD):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "P"
    for s in (-1, 1):                               # orelhas pontudas
        for r in range(3):
            for k in range(r + 1):
                px[(hx + s * (6 - k), h0 - 3 + r)] = "P"
    px = _rim(px)
    for i, x0 in enumerate((cx - 4, cx + 2)):
        x = x0 + feet[i]
        for xx in (x, x + 1, x + 2):
            px[(xx, base)] = "W"
    outline_cells(g, px)
    for s in (-1, 1):                               # miolo rosado das orelhas
        g[h0 - 1][hx + s * 5] = "r"
        g[h0][hx + s * 5] = "r"
        g[h0][hx + s * 4] = "r"
    _face(g, hx, h0, eye)
    for x in range(hx - 5, hx + 6):                 # coleira
        g[a0][x] = "V" if x != hx - 5 else "v"
    _bell(g, hx, a0 + 1, sound)
    for a, b in arms:
        _arm(g, _move(a, dx, dy), _move(b, dx, dy))
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (cx - 9, h0 - 11)


def ball(cx=15, eye="fechado", sound=0, por=()):
    """O gato enrolado numa bolinha no chão: corpo oval, cabeça encostada à direita, rabo passando na frente."""
    g = [["."] * N for _ in range(N)]
    px = {}
    for y in range(22, 31):
        for x in range(cx - 10, cx + 7):
            if ((x - cx + 1.5) / 8.5) ** 2 + ((y - 26.5) / 4.6) ** 2 <= 1:
                px[(x, y)] = "P"
    hx, h0 = cx + 6, 20                             # cabeça (centro, topo)
    for y in range(h0, h0 + 8):
        for x in range(hx - 5, hx + 6):
            if ((x - hx) / 5.4) ** 2 + ((y - h0 - 3.8) / 4.3) ** 2 <= 1:
                px[(x, y)] = "P"
    for s in (-1, 1):
        for r in range(3):
            for k in range(r + 1):
                px[(hx + s * (4 - k), h0 - 2 + r)] = "P"
    px = _rim(px)
    outline_cells(g, px)
    for s in (-1, 1):
        g[h0][hx + s * 3] = "r"
    for x, y in ((hx - 2, h0 + 3), (hx + 2, h0 + 3)):
        stamp(g, [EYES[eye][1][:2]] if eye == "fechado" else [l[:2] for l in EYES[eye][1:]], x - 1, y)
    g[h0 + 5][hx] = "R"
    tail_tip = {}                                       # rabo enrolado passando na frente da bolinha
    _tail(tail_tip, [(cx - 10, 26), (cx - 7, 29), (cx - 1, 29), (cx + 3, 27)])
    tail_tip = _rim(tail_tip)
    outline_cells(g, tail_tip)
    for x in range(hx - 4, hx + 3):                 # coleira
        g[h0 + 7][x] = "V"
    _bell(g, hx - 1, h0 + 8, sound)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (hx - 11, h0 - 12)


def _state(specs):
    qs = [ball(**s["ball"]) if "ball" in s else frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# pose padrão: coleira na linha 21, cabeça 13-21 (hx=17), olhos 15-17, orelhas 10-12; ombros em (11, 23) e (21, 23)
_BACK = ((11, 23), (11, 27))                    # pata de trás no chão, na frente do corpo
_FRONT = ((21, 23), (21, 27))                  # pata da frente no chão
_SPECS = {
    # sentadinho: o rabo balança, pisca, o sino brilha
    "idle": [dict(arms=(_BACK, _FRONT)),
             dict(arms=(_BACK, _FRONT), tail=1),
             dict(arms=(_BACK, _FRONT), tail=2, por=((SPARK, 19, 22),)),
             dict(eye="fechado", arms=(_BACK, _FRONT), tail=1),
             dict(arms=(_BACK, _FRONT))],
    # trota: corpo sobe e desce, perninhas alternam, rabo erguido
    "run_r": [dict(cx=17, base=30, feet=(-1, 1), arms=(((11, 23), (9, 26)), ((21, 23), (24, 25))), tail=2),
              dict(cx=17, base=29, leg=3, feet=(1, -1), arms=(((11, 23), (12, 27)), ((21, 23), (22, 27))),
                   tail=1),
              dict(cx=17, base=30, feet=(-1, 1), arms=(((11, 23), (8, 25)), ((21, 23), (25, 24))), tail=2),
              dict(cx=17, base=29, leg=3, feet=(1, -1), arms=(((11, 23), (13, 27)), ((21, 23), (21, 27))),
                   tail=1)],
    # acena bem alto com a pata da frente, feliz
    "waving": [dict(eye="feliz", arms=(_BACK, ((21, 23), (26, 14))), tail=1),
               dict(eye="feliz", arms=(_BACK, ((21, 23), (28, 17))), tail=2),
               dict(eye="feliz", arms=(_BACK, ((21, 23), (25, 13))), tail=1),
               dict(eye="feliz", arms=(_BACK, ((21, 23), (28, 17))), tail=2)],
    # agacha, pula com as patas para cima, desce, pousa
    "jumping": [dict(leg=0, eye="fechado", arms=(_BACK, _FRONT), tail=0),
                dict(base=29, leg=3, eye="cima", feet=(-1, 1), arms=(((11, 23), (6, 17)), ((21, 23), (26, 17))),
                     tail=2),
                dict(base=29, leg=3, eye="feliz", feet=(-1, 1), arms=(((11, 23), (5, 16)), ((21, 23), (27, 16))),
                     tail=2, por=((SPARK, 2, 27), (SPARK, 28, 26))),
                dict(base=30, leg=3, arms=(((11, 23), (7, 21)), ((21, 23), (25, 21))), tail=1),
                dict(leg=0, eye="feliz", arms=(_BACK, _FRONT), tail=0)],
    # se enrola: fica triste, deita enrolado, o sino toca uma última vez e para
    "failed": [dict(eye="triste", arms=(_BACK, _FRONT), tail=0),
               dict(ball=dict(eye="triste")),
               dict(ball=dict(sound=2)),
               dict(ball=dict(sound=1)),
               dict(ball=dict())],
    # cochila deitado (pernas recolhidas), "z" subindo
    "waiting": [dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=0),
                dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=0,
                     por=((Z_S, 26, 6),)),
                dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=3,
                     por=((Z_S, 25, 7), (Z_L, 26, 0))),
                dict(leg=0, eye="fechado", arms=(((11, 23), (12, 28)), ((21, 23), (20, 28))), tail=0,
                     por=((Z_L, 26, 0),))],
    # patada: arma a pata no alto, avança, risca o ar com três arranhões, recolhe
    "running": [dict(cx=12, eye="bravo", arms=(((11, 23), (9, 27)), ((21, 23), (27, 14))), tail=2),
                dict(cx=12, eye="bravo", arms=(((11, 23), (9, 27)), ((21, 23), (30, 17))), tail=2,
                     por=((SCRATCH_S, 23, 4),)),
                dict(cx=12, eye="bravo", arms=(((11, 23), (9, 27)), ((21, 23), (30, 26))), tail=3,
                     por=((SCRATCH, 19, 8),)),
                dict(cx=12, eye="feliz", arms=(((11, 23), (9, 27)), ((21, 23), (26, 27))), tail=1,
                     por=((SCRATCH_S, 21, 15),))],
    # pata no queixo, olhando para cima, "?" aparece
    "review": [dict(eye="cima", arms=(_BACK, ((21, 23), (20, 20))), tail=1),
               dict(eye="cima", arms=(_BACK, ((21, 23), (20, 20))), tail=2, por=((QMARK_S, 26, 1),)),
               dict(eye="cima", arms=(_BACK, ((21, 23), (20, 20))), tail=1, por=((QMARK, 26, 0),)),
               dict(eye="n", arms=(_BACK, ((21, 23), (20, 20))), tail=2, por=((QMARK, 26, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)


# grade 21x24 colada 9 à esquerda do centro e 11 acima do topo da cabeça (topo da cabeça na linha 11, centro
# na coluna 10, orelhas 8-10, coleira na linha 19): lenço roxo no pescoço com o nó atrás (à esquerda), deixando o
# sino à mostra; no 3º estágio, sete velinhas flutuando num arco sobre a cabeça
CANDLE = [".K.", "KYK", "KFK", "KIK", "KiK", "KKK"]


def _extra(candles):
    g = [["."] * N for _ in range(N)]
    px = {}
    for x in range(4, 17):
        px[(x, 19)] = "L"
    for x in range(5, 16):
        if not 9 <= x <= 11:
            px[(x, 20)] = "l"
    for x, y in ((3, 19), (2, 20), (3, 20), (1, 21), (2, 21), (3, 21), (2, 22), (0, 22), (1, 23)):
        px[(x, y)] = "L" if y < 22 else "l"     # pontas do nó caindo atrás
    outline_cells(g, px)
    if candles:
        for x, y in zip((0, 3, 6, 9, 12, 15, 18), (4, 2, 1, 0, 1, 2, 4)):
            stamp(g, CANDLE, x, y)
    return ["".join(l[:21]) for l in g[:24]]


SCARF = _extra(False)
CANDLES = _extra(True)
STAGES = [
    {"title": "Gatinho Preto", "floor": 1, "extra": None},
    {"title": "Gato de Cemitério", "floor": 4, "extra": SCARF},
    {"title": "Gato das Sete Vidas", "floor": 10, "extra": CANDLES},
]
