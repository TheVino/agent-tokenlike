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
from herois.comum import N, Z_P, Z_G, INTERROG_P, INTERROG, LAGRIMA, carimbar, contornar, linha, traco

PAL = {
    "K": "#07060c", "P": "#2c2742", "M": "#a597ec", "m": "#5f5596", "Y": "#ffd23f", "y": "#b8841a",
    "W": "#f4f2fa", "w": "#bab6cc", "R": "#ff8fb0", "r": "#b05a7e", "V": "#e0384e", "v": "#8e1e30",
    "L": "#9a5cd8", "l": "#5e2f94", "I": "#fff4dc", "i": "#d8c8a0", "F": "#ff9a3c", "T": "#8fd8ff",
}

CABECA = (5, 6, 7, 7, 7, 7, 7, 6, 5)            # meia-largura da cabeça por linha (9 linhas; a última é a coleira)
TRONCO = (5, 6, 6, 7, 7, 7, 7, 6)               # meia-largura do tronco por linha (8 linhas; a 1ª é a da coleira)


def _garras(n=3, comp=8):
    """Arranhões: `n` riscos brancos na diagonal, do alto à direita para baixo à esquerda, com contorno."""
    g = [["."] * N for _ in range(N)]
    px = {}
    for i in range(n):
        for x, y in linha(comp - 1 + 3 * i, 1, 1 + 3 * i, comp):
            px[(x, y)] = "W"
    contornar(g, px)
    w = 3 * n + comp
    return ["".join(l[:w]) for l in g[:comp + 2]]


ARRANHAO = _garras(3, 7)
ARRANHAO_P = _garras(3, 5)
FAISCA = [".K.", "KYK", ".K."]


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


def _braco(g, a, b):
    """Patinha de 2 px de `a` (ombro) a `b` (pata), com a pata branca 3x3 e o feijãozinho rosa no meio."""
    px = {}
    for x, y in linha(*a, *b):
        for dx in (0, 1):
            for dy in (0, 1):
                px.setdefault((x + dx, y + dy), "m" if dy == 0 else "P")
    bx, by = b
    for x in range(bx - 1, bx + 2):
        for y in range(by - 1, by + 2):
            px[(x, y)] = "W"
    px[(bx, by)] = "R"
    px[(bx - 1, by + 1)] = px[(bx + 1, by + 1)] = "w"
    contornar(g, px)


def _cauda(px, pts):
    """Rabo de 2 px pelos pontos `pts` (da base à ponta)."""
    for p, q in zip(pts, pts[1:]):
        for x, y in linha(*p, *q):
            px[(x, y)] = px[(x + 1, y)] = "P"


def _sino(g, x, y, som=0):
    """Sino dourado pendurado em (x, y); `som` desenha os riscos de toque (0, 1 ou 2 de tamanho)."""
    px = {(x, y): "y", (x - 1, y + 1): "Y", (x, y + 1): "W", (x + 1, y + 1): "Y", (x - 1, y + 2): "Y",
          (x, y + 2): "Y", (x + 1, y + 2): "y", (x, y + 3): "y"}
    contornar(g, px)
    for k in range(som):                        # riscos de toque em "\ /" saindo do sino, um par por nível
        for s in (-1, 1):
            traco(g, (x + s * (3 + k), y + 1 - 3 * k), (x + s * (5 + k), y - 1 - 3 * k), "Y")


def _mover(p, dx, dy):
    return (p[0] + dx, p[1] + dy)


OLHOS = {"n": ["YYY", "YKY", "YKY"], "fechado": ["...", "MMM", "..."], "feliz": [".M.", "M.M", "..."],
         "x": ["M.M", ".M.", "M.M"], "cima": ["YKY", "YKY", "YYY"], "triste": ["...", "YYY", "YKY"],
         "bravo": (["M..", "YYY", "YKY"], ["..M", "YYY", "YKY"])}


def _rosto(g, hx, h0, olho):
    tras, frente = OLHOS[olho] if isinstance(OLHOS[olho], tuple) else (OLHOS[olho], OLHOS[olho])
    carimbar(g, tras, hx - 4, h0 + 2)
    carimbar(g, frente, hx + 2, h0 + 2)
    if olho == "triste":
        carimbar(g, LAGRIMA, hx - 4, h0 + 5)
    g[h0 + 5][hx] = "R"                         # focinho
    for x in (hx - 1, hx + 1):                  # boquinha "w"
        g[h0 + 6][x] = "M"
    for y in (h0 + 5, h0 + 7):                  # bigodes
        for d in (5, 6, 7, 8):
            for x in (hx - d, hx + d):
                if 0 <= x < N and (g[y][x] != "." or d >= 7):
                    g[y][x] = "w"


def quadro(cx=16, base=30, perna=2, olho="n", pes=(0, 0), bracos=(), cauda=0, som=0, por=()):
    """Um quadro 32x32 e a âncora do acréscimo (9 à esquerda do centro e 11 acima do topo da cabeça).
    `perna`: altura das pernas (0 = deitado); `bracos`: ((ombro), (pata)) escritos para a pose padrão
    (cx=16, base=30, perna=2: ombros em (11, 23) e (21, 23)) e deslocados junto com o corpo;
    `cauda`: pose do rabo (0 a 3); `por`: sprites carimbados por último, sem deslocar."""
    g = [["."] * N for _ in range(N)]
    dx, dy = cx - 16, (base - 30) + (2 - perna)
    a0 = 21 + dy                                    # topo do tronco (= coleira, última linha da cabeça)
    h0 = a0 - 8
    hx = cx + 1
    px = {}
    ponta = ((-11, -1), (-12, -4), (-10, -6), (-13, -2))[cauda]
    _cauda(px, [(cx - 5, a0 + 6), (cx - 10, a0 + 4), (cx + ponta[0], a0 + ponta[1])])
    for i, x0 in enumerate((cx - 4, cx + 2)):       # perninhas com meia branca
        x = x0 + pes[i]
        for y in range(base - perna + 1, base + 1):
            px[(x, y)] = px[(x + 1, y)] = "P"
    for r, w in enumerate(TRONCO):
        for x in range(cx - w, cx + w + 1):
            px[(x, a0 + r)] = "P"
    for r, w in enumerate(CABECA):
        for x in range(hx - w, hx + w + 1):
            px[(x, h0 + r)] = "P"
    for s in (-1, 1):                               # orelhas pontudas
        for r in range(3):
            for k in range(r + 1):
                px[(hx + s * (6 - k), h0 - 3 + r)] = "P"
    px = _rim(px)
    for i, x0 in enumerate((cx - 4, cx + 2)):
        x = x0 + pes[i]
        for xx in (x, x + 1, x + 2):
            px[(xx, base)] = "W"
    contornar(g, px)
    for s in (-1, 1):                               # miolo rosado das orelhas
        g[h0 - 1][hx + s * 5] = "r"
        g[h0][hx + s * 5] = "r"
        g[h0][hx + s * 4] = "r"
    _rosto(g, hx, h0, olho)
    for x in range(hx - 5, hx + 6):                 # coleira
        g[a0][x] = "V" if x != hx - 5 else "v"
    _sino(g, hx, a0 + 1, som)
    for a, b in bracos:
        _braco(g, _mover(a, dx, dy), _mover(b, dx, dy))
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (cx - 9, h0 - 11)


def bola(cx=15, olho="fechado", som=0, por=()):
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
    contornar(g, px)
    for s in (-1, 1):
        g[h0][hx + s * 3] = "r"
    for x, y in ((hx - 2, h0 + 3), (hx + 2, h0 + 3)):
        carimbar(g, [OLHOS[olho][1][:2]] if olho == "fechado" else [l[:2] for l in OLHOS[olho][1:]], x - 1, y)
    g[h0 + 5][hx] = "R"
    rabo = {}                                       # rabo enrolado passando na frente da bolinha
    _cauda(rabo, [(cx - 10, 26), (cx - 7, 29), (cx - 1, 29), (cx + 3, 27)])
    rabo = _rim(rabo)
    contornar(g, rabo)
    for x in range(hx - 4, hx + 3):                 # coleira
        g[h0 + 7][x] = "V"
    _sino(g, hx - 1, h0 + 8, som)
    for s, x, y in por:
        carimbar(g, s, x, y)
    return ["".join(l) for l in g], (hx - 11, h0 - 12)


def _estado(specs):
    qs = [bola(**s["bola"]) if "bola" in s else quadro(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# pose padrão: coleira na linha 21, cabeça 13-21 (hx=17), olhos 15-17, orelhas 10-12; ombros em (11, 23) e (21, 23)
_TRAS = ((11, 23), (11, 27))                    # pata de trás no chão, na frente do corpo
_FRENTE = ((21, 23), (21, 27))                  # pata da frente no chão
_SPECS = {
    # sentadinho: o rabo balança, pisca, o sino brilha
    "idle": [dict(bracos=(_TRAS, _FRENTE)),
             dict(bracos=(_TRAS, _FRENTE), cauda=1),
             dict(bracos=(_TRAS, _FRENTE), cauda=2, por=((FAISCA, 19, 22),)),
             dict(olho="fechado", bracos=(_TRAS, _FRENTE), cauda=1),
             dict(bracos=(_TRAS, _FRENTE))],
    # trota: corpo sobe e desce, perninhas alternam, rabo erguido
    "run_r": [dict(cx=17, base=30, pes=(-1, 1), bracos=(((11, 23), (9, 26)), ((21, 23), (24, 25))), cauda=2),
              dict(cx=17, base=29, perna=3, pes=(1, -1), bracos=(((11, 23), (12, 27)), ((21, 23), (22, 27))),
                   cauda=1),
              dict(cx=17, base=30, pes=(-1, 1), bracos=(((11, 23), (8, 25)), ((21, 23), (25, 24))), cauda=2),
              dict(cx=17, base=29, perna=3, pes=(1, -1), bracos=(((11, 23), (13, 27)), ((21, 23), (21, 27))),
                   cauda=1)],
    # acena bem alto com a pata da frente, feliz
    "waving": [dict(olho="feliz", bracos=(_TRAS, ((21, 23), (26, 14))), cauda=1),
               dict(olho="feliz", bracos=(_TRAS, ((21, 23), (28, 17))), cauda=2),
               dict(olho="feliz", bracos=(_TRAS, ((21, 23), (25, 13))), cauda=1),
               dict(olho="feliz", bracos=(_TRAS, ((21, 23), (28, 17))), cauda=2)],
    # agacha, pula com as patas para cima, desce, pousa
    "jumping": [dict(perna=0, olho="fechado", bracos=(_TRAS, _FRENTE), cauda=0),
                dict(base=29, perna=3, olho="cima", pes=(-1, 1), bracos=(((11, 23), (6, 17)), ((21, 23), (26, 17))),
                     cauda=2),
                dict(base=29, perna=3, olho="feliz", pes=(-1, 1), bracos=(((11, 23), (5, 16)), ((21, 23), (27, 16))),
                     cauda=2, por=((FAISCA, 2, 27), (FAISCA, 28, 26))),
                dict(base=30, perna=3, bracos=(((11, 23), (7, 21)), ((21, 23), (25, 21))), cauda=1),
                dict(perna=0, olho="feliz", bracos=(_TRAS, _FRENTE), cauda=0)],
    # se enrola: fica triste, deita enrolado, o sino toca uma última vez e para
    "failed": [dict(olho="triste", bracos=(_TRAS, _FRENTE), cauda=0),
               dict(bola=dict(olho="triste")),
               dict(bola=dict(som=2)),
               dict(bola=dict(som=1)),
               dict(bola=dict())],
    # cochila deitado (pernas recolhidas), "z" subindo
    "waiting": [dict(perna=0, olho="fechado", bracos=(((11, 23), (12, 28)), ((21, 23), (20, 28))), cauda=0),
                dict(perna=0, olho="fechado", bracos=(((11, 23), (12, 28)), ((21, 23), (20, 28))), cauda=0,
                     por=((Z_P, 26, 6),)),
                dict(perna=0, olho="fechado", bracos=(((11, 23), (12, 28)), ((21, 23), (20, 28))), cauda=3,
                     por=((Z_P, 25, 7), (Z_G, 26, 0))),
                dict(perna=0, olho="fechado", bracos=(((11, 23), (12, 28)), ((21, 23), (20, 28))), cauda=0,
                     por=((Z_G, 26, 0),))],
    # patada: arma a pata no alto, avança, risca o ar com três arranhões, recolhe
    "running": [dict(cx=12, olho="bravo", bracos=(((11, 23), (9, 27)), ((21, 23), (27, 14))), cauda=2),
                dict(cx=12, olho="bravo", bracos=(((11, 23), (9, 27)), ((21, 23), (30, 17))), cauda=2,
                     por=((ARRANHAO_P, 23, 4),)),
                dict(cx=12, olho="bravo", bracos=(((11, 23), (9, 27)), ((21, 23), (30, 26))), cauda=3,
                     por=((ARRANHAO, 19, 8),)),
                dict(cx=12, olho="feliz", bracos=(((11, 23), (9, 27)), ((21, 23), (26, 27))), cauda=1,
                     por=((ARRANHAO_P, 21, 15),))],
    # pata no queixo, olhando para cima, "?" aparece
    "review": [dict(olho="cima", bracos=(_TRAS, ((21, 23), (20, 20))), cauda=1),
               dict(olho="cima", bracos=(_TRAS, ((21, 23), (20, 20))), cauda=2, por=((INTERROG_P, 26, 1),)),
               dict(olho="cima", bracos=(_TRAS, ((21, 23), (20, 20))), cauda=1, por=((INTERROG, 26, 0),)),
               dict(olho="n", bracos=(_TRAS, ((21, 23), (20, 20))), cauda=2, por=((INTERROG, 26, 0),))],
}

QUADROS, ANCORA = {}, {}
for _e, _s in _SPECS.items():
    QUADROS[_e], ANCORA[_e] = _estado(_s)


# grade 21x24 colada 9 à esquerda do centro e 11 acima do topo da cabeça (topo da cabeça na linha 11, centro
# na coluna 10, orelhas 8-10, coleira na linha 19): lenço roxo no pescoço com o nó atrás (à esquerda), deixando o
# sino à mostra; no 3º estágio, sete velinhas flutuando num arco sobre a cabeça
VELA = [".K.", "KYK", "KFK", "KIK", "KiK", "KKK"]


def _extra(velas):
    g = [["."] * N for _ in range(N)]
    px = {}
    for x in range(4, 17):
        px[(x, 19)] = "L"
    for x in range(5, 16):
        if not 9 <= x <= 11:
            px[(x, 20)] = "l"
    for x, y in ((3, 19), (2, 20), (3, 20), (1, 21), (2, 21), (3, 21), (2, 22), (0, 22), (1, 23)):
        px[(x, y)] = "L" if y < 22 else "l"     # pontas do nó caindo atrás
    contornar(g, px)
    if velas:
        for x, y in zip((0, 3, 6, 9, 12, 15, 18), (4, 2, 1, 0, 1, 2, 4)):
            carimbar(g, VELA, x, y)
    return ["".join(l[:21]) for l in g[:24]]


LENCO = _extra(False)
VELAS = _extra(True)
ESTAGIOS = [
    {"title": "Gatinho Preto", "floor": 1, "extra": None},
    {"title": "Gato de Cemitério", "floor": 4, "extra": LENCO},
    {"title": "Gato das Sete Vidas", "floor": 10, "extra": VELAS},
]
