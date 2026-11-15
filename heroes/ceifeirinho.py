"""Ceifeirinho, 32 px, olhando para a direita. Capuz redondo e escuro com dois olhos que brilham na sombra, manto
comprido de barra rasgada, mãozinhas de osso e uma foice pequena (cabo de pau, lâmina curva de prata). No `running`
ele dá um golpe largo com rastro em arco; no `failed` o manto desaba vazio no chão com a foice caída por cima.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
import math

from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, line, outline_cells, trait

PAL = {
    "K": "#1a1820", "H": "#3a3354", "h": "#28233d", "M": "#4a4266", "m": "#332d4a", "k": "#0b0a12",
    "V": "#8dffe0", "v": "#3fb894", "N": "#8a5a35", "n": "#5e3c22", "S": "#d3dae4", "s": "#7f8896",
    "G": "#ece4cf", "W": "#ffffff", "A": "#b8f0ff", "T": "#8fd8ff", "Y": "#ffd23f", "B": "#1a1820",
}

HAND = ["KKK", "KGK", "KKK"]
SOUL = [".A.", "AWA", ".A.", "..A"]          # fiapo de alma subindo


def _scythe(g, handle, tip, side=1):
    """Foice: cabo de `cabo` até `ponta` e lâmina curva saindo da ponta para o `lado` (+1 direita do cabo)."""
    px = {p: ("n" if i % 3 == 2 else "N") for i, p in enumerate(line(*handle, *tip))}
    ux, uy = tip[0] - handle[0], tip[1] - handle[1]
    d = math.hypot(ux, uy) or 1
    ux, uy = ux / d, uy / d
    pxx, pyy = -uy * side, ux * side
    for i in range(8):
        cv = i * i / 9
        for esp in ((0, 1) if i < 6 else (0,)):
            x = round(tip[0] + pxx * i - ux * (cv + esp))
            y = round(tip[1] + pyy * i - uy * (cv + esp))
            px[(x, y)] = "s" if esp else "S"
    px[(round(tip[0] + pxx * 2), round(tip[1] + pyy * 2))] = "W"
    outline_cells(g, px)


def _arc(g, cx, cy, r, a0, a1, color="A"):
    """Rastro do golpe: arco de círculo (graus, 0 = direita, 90 = baixo) em duas camadas, sem contorno."""
    n = max(int(abs(a1 - a0) / 4), 2)
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        for dr, c in ((0, "W"), (-1, color), (1, color)):
            x, y = round(cx + (r + dr) * math.cos(a)), round(cy + (r + dr) * math.sin(a))
            if 0 <= x < N and 0 <= y < N and g[y][x] == ".":
                g[y][x] = c


def _eyes(g, hx, hy, eyes):
    for x in (hx, hx + 3):
        if eyes == "fechado":
            stamp(g, ["vv"], x, hy + 1)
        elif eyes == "feliz":
            stamp(g, [".V.", "V.V"], x - 1, hy)
        elif eyes == "x":
            stamp(g, ["v.v", ".v.", "v.v"], x - 1, hy - 1)
        elif eyes == "apagado":
            stamp(g, ["v"], x, hy + 1)
        else:
            dy = -1 if eyes == "cima" else 0
            stamp(g, ["V", "V"], x, hy + dy)
            if eyes == "bravo":
                g[hy - 1][x - 1 if x == hx else x + 1] = "V"
            if eyes == "triste":
                g[hy - 1][x + 1 if x == hx else x - 1] = "v"


def _hood(g, hx, hy, ry=5.5, empty=False):
    """Capuz redondo (bico curto para trás) e a abertura escura do rosto voltada para a direita."""
    px = {}
    for x in range(hx - 7, hx + 7):
        for y in range(hy - 7, hy + 7):
            if ((x - hx) / 5.6) ** 2 + ((y - hy) / ry) ** 2 <= 1:
                px[(x, y)] = "h" if x < hx - 3 or y > hy + ry - 1.5 else "H"
    px[(hx - 5, round(hy - ry + 2))] = "H"                    # bico do capuz caindo para trás
    px[(hx - 6, round(hy - ry + 3))] = "h"
    for x in range(hx - 3, hx + 6):
        for y in range(hy - 4, hy + 5):
            if ((x - hx - 1.5) / 3.6) ** 2 + ((y - hy - 0.5) / min(3.3, ry - 1.6)) ** 2 <= 1:
                px[(x, y)] = "k"
    outline_cells(g, px)


def _mantle(g, cx, base, ch, lean):
    ctop = base - 1 - ch
    px = {}
    for y in range(ctop, base):
        t = (y - ctop) / max(ch - 1, 1)
        half = 3 + t * 3.5
        c = cx + lean * (1 - t) * 0.6
        for x in range(round(c - half), round(c + half) + 1):
            if y == base - 1 and (x - cx) % 3 == 0:          # barra rasgada
                continue
            edge = x >= round(c + half) - 1 or y >= base - 2
            px[(x, y)] = "m" if edge else "M"
    outline_cells(g, px)


def _mound(g, cx, y):
    """Manto vazio desabado: montinho de pano com o capuz vazio caído na frente."""
    px = {}
    for dy, half in ((0, 4), (1, 7), (2, 9), (3, 10), (4, 10)):
        for x in range(cx - half, cx + half + 1):
            if dy == 4 and (x - cx) % 3 == 0:
                continue
            px[(x, y + dy)] = "m" if dy >= 3 else "M"
    outline_cells(g, px)


def frame(cx=14, base=30, ch=9, lean=0, eyes="normal", arms=(), scythes=(), por=(), arcs=(), ry=5.5,
           mound=None):
    """Um quadro 32x32 e a âncora do acréscimo (capuz - 12). `foices`: (cabo, ponta, lado); `arcos`: rastros
    (cx, cy, r, a0, a1) desenhados atrás de tudo; `monte` (cx, y) desenha só o manto vazio caído."""
    g = [["."] * N for _ in range(N)]
    for a in arcs:
        _arc(g, *a)
    if mound:
        mx, my = mound
        _mound(g, mx, my)
        _hood(g, mx + 3, my - 3, ry=3.6)
        for f in scythes:
            _scythe(g, *f)
        for s, x, y in por:
            stamp(g, s, x, y)
        return ["".join(l) for l in g], (mx + 3 - 12, my - 3 - 12)
    ctop = base - 1 - ch
    hx, hy = cx + lean, ctop - 4
    _mantle(g, cx, base, ch, lean)
    _hood(g, hx, hy, ry)
    _eyes(g, hx, hy, eyes)
    for f in scythes:
        _scythe(g, *f)
    for a, b in arms:
        trait(g, a, b, "M")
        stamp(g, HAND, b[0] - 1, b[1] - 1)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (hx - 12, hy - 12)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, ch=9 -> ctop=20, capuz hy=16 (topo ~10); ombro ~(cx + 2, 22)
_SPECS = {
    # parado com a foice em pé ao lado; a lâmina balança e ele pisca
    "idle": [dict(arms=(((16, 23), (20, 23)),), scythes=(((21, 29), (21, 9), 1),)),
             dict(arms=(((16, 23), (20, 23)),), scythes=(((21, 29), (22, 9), 1),)),
             dict(eyes="fechado", arms=(((16, 23), (20, 23)),), scythes=(((21, 29), (22, 9), 1),)),
             dict(arms=(((16, 23), (20, 22)),), scythes=(((21, 29), (20, 9), 1),))],
    # corre de lado (manto inclinado, sobe e desce) com a foice no ombro, lâmina atrás
    "run_r": [dict(cx=15, lean=1, arms=(((15, 22), (18, 21)),), scythes=(((20, 22), (8, 12), -1),)),
              dict(cx=15, lean=2, base=29, arms=(((15, 21), (18, 20)),), scythes=(((20, 21), (8, 10), -1),)),
              dict(cx=15, lean=1, arms=(((15, 22), (18, 21)),), scythes=(((20, 22), (8, 13), -1),)),
              dict(cx=15, lean=2, base=29, arms=(((15, 21), (18, 20)),), scythes=(((20, 21), (8, 11), -1),))],
    # acena com a mãozinha de osso, foice fincada atrás
    "waving": [dict(eyes="feliz", scythes=(((8, 29), (8, 10), -1),), arms=(((16, 22), (21, 19)),)),
               dict(eyes="feliz", scythes=(((8, 29), (8, 10), -1),), arms=(((16, 22), (21, 15)),)),
               dict(eyes="feliz", scythes=(((8, 29), (8, 10), -1),), arms=(((16, 22), (24, 16)),)),
               dict(eyes="feliz", scythes=(((8, 29), (8, 10), -1),), arms=(((16, 22), (21, 15)),))],
    # agacha, salta com a foice erguida, cai, pousa
    "jumping": [dict(ch=7, eyes="fechado", arms=(((16, 25), (20, 25)),), scythes=(((21, 30), (21, 13), 1),)),
                dict(ch=10, base=28, arms=(((16, 19), (21, 17)),), scythes=(((22, 24), (24, 6), 1),)),
                dict(ch=9, base=26, eyes="feliz", arms=(((16, 17), (21, 15)),), scythes=(((22, 22), (24, 4), 1),)),
                dict(ch=10, base=28, arms=(((16, 20), (21, 19)),), scythes=(((22, 26), (24, 8), 1),)),
                dict(ch=7, eyes="feliz", arms=(((16, 25), (20, 25)),), scythes=(((21, 30), (22, 13), 1),))],
    # triste, solta a foice, o manto desaba vazio; a foice fica caída sobre o pano e um fiapo de alma sobe
    "failed": [dict(eyes="triste", scythes=(((19, 29), (25, 13), 1),), por=((TEAR, 18, 18),)),
               dict(ch=6, ry=4.8, eyes="triste", scythes=(((17, 30), (28, 22), 1),), por=((TEAR, 18, 22),)),
               dict(ch=3, ry=4.0, eyes="x", scythes=(((14, 30), (29, 27), -1),)),
               dict(mound=(14, 26), scythes=(((4, 29), (24, 29), -1),)),
               dict(mound=(14, 26), scythes=(((4, 29), (24, 29), -1),), por=((SOUL, 18, 9),))],
    # cochila apoiado na foice, capuz pende, "z" subindo
    "waiting": [dict(ch=8, lean=-1, eyes="fechado", arms=(((15, 23), (19, 23)),), scythes=(((20, 29), (20, 10), 1),)),
                dict(ch=8, lean=-2, eyes="fechado", arms=(((15, 23), (19, 23)),), scythes=(((20, 29), (20, 10), 1),),
                     por=((Z_S, 24, 2),)),
                dict(ch=8, lean=-2, eyes="fechado", arms=(((15, 23), (19, 23)),), scythes=(((20, 29), (20, 10), 1),),
                     por=((Z_S, 23, 3), (Z_L, 26, 0))),
                dict(ch=8, lean=-1, eyes="fechado", arms=(((15, 23), (19, 23)),), scythes=(((20, 29), (20, 10), 1),),
                     por=((Z_L, 26, 0),))],
    # golpe: foice atrás da cabeça, passa por cima e corta para a frente num arco largo
    "running": [dict(cx=13, lean=-2, eyes="bravo", arms=(((12, 22), (9, 19)),), scythes=(((10, 24), (4, 8), -1),)),
                dict(cx=14, eyes="bravo", arms=(((15, 21), (17, 16)),), scythes=(((17, 21), (17, 3), 1),),
                     arcs=((14, 18, 13, 200, 270),)),
                dict(cx=14, lean=2, eyes="bravo", arms=(((16, 22), (21, 20)),), scythes=(((19, 21), (30, 15), 1),),
                     arcs=((14, 20, 14, 230, 340),)),
                dict(cx=14, lean=2, eyes="bravo", arms=(((16, 23), (21, 24)),), scythes=(((17, 23), (29, 24), 1),),
                     arcs=((14, 18, 13, 270, 400),))],
    # mão no queixo, olhando para cima, "?" aparece
    "review": [dict(cx=12, eyes="cima", arms=(((14, 23), (17, 21)),), scythes=(((6, 29), (6, 10), -1),)),
               dict(cx=12, eyes="cima", arms=(((14, 23), (17, 21)),), scythes=(((6, 29), (6, 10), -1),),
                    por=((QMARK_S, 24, 2),)),
               dict(cx=12, eyes="cima", arms=(((14, 23), (17, 21)),), scythes=(((6, 29), (6, 10), -1),),
                    por=((QMARK, 24, 0),)),
               dict(cx=12, arms=(((14, 23), (17, 21)),), scythes=(((6, 29), (6, 10), -1),),
                    por=((QMARK, 24, 0),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# capuz maior: ponta comprida caindo para trás por cima do capuz; âncora = capuz - 12
_EMPTY = "." * 25
HOOD = [_EMPTY] * 3 + [
    "..........KKKKK..........",
    ".......KKKHHHHHKK........",
    ".....KKhhHHHHHHHHK.......",
    "....KhhK.................",
    "...KhK...................",
    "...KK....................",
]
# Ancião: capuz maior e lanterna de almas flutuando atrás (à esquerda)
LANTERN = [_EMPTY] * 12 + [
    "..KK.....................",
    ".K..K....................",
    "KKKKKK...................",
    "KAWAAK...................",
    "KAAVAK...................",
    "KVAAAK...................",
    "KKKKKK...................",
    "..KK.....................",
]
ELDER = [HOOD[i] if i < len(HOOD) else LANTERN[i] for i in range(len(LANTERN))]
STAGES = [
    {"title": "Ceifeirinho", "floor": 1, "extra": None},
    {"title": "Ceifador", "floor": 4, "extra": HOOD},
    {"title": "Ceifador Ancião", "floor": 10, "extra": ELDER},
]
