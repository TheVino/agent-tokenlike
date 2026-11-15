"""Boneca de Pano, 32 px, olhando para a direita. Cabeça grande de linho com cabelo de lã ameixa, dois olhos de
botão que não combinam (um azul, um vermelho, e os furinhos giram), boca costurada, vestidinho com remendo,
meias listradas e braços de pano em linha grossa. O símbolo é a agulha com linha. No `failed` a boneca desmonta:
a costura do vestido rasga, o enchimento escapa, um botão-olho fica pendurado pela linha e ela desaba.
Formato de herói de herois/montar.py: PAL, QUADROS, ESTAGIOS, ANCORA."""
from heroes.common import N, Z_S, Z_L, QMARK_S, QMARK, TEAR, stamp, line, trait

PAL = {
    "K": "#1c1424", "C": "#f1dcc4", "c": "#cfb193", "H": "#7b4f9e", "h": "#4f3070",
    "V": "#4f8a8b", "v": "#33605f", "Q": "#e0a458", "E": "#3f78c0", "e": "#b8384e",
    "S": "#dfe3ee", "W": "#ffffff", "L": "#e0485f", "l": "#9c2a3f", "F": "#fff8ec", "f": "#d9ccb6",
    "D": "#3a2a20", "P": "#ff9ec4", "T": "#8fd8ff", "Y": "#ffd23f",
}

HH = 11                                          # altura da cabeça
HEAD = (3, 5, 6, 6, 6, 6, 6, 6, 6, 5, 3)       # meia-largura da cabeça por linha
# furinhos do botão em 4 giros (o botão "pisca" girando)
BUTTON = {"h": ["EEE", "KEK", "EEE"], "v": ["EKE", "EEE", "EKE"],
         "d1": ["KEE", "EEE", "EEK"], "d2": ["EEK", "EEE", "KEE"]}

# agulha: o olho é um anel na ponta de trás (o resto é um traço prateado feito em `agulha`)
EYE_SHARP = [".KKK.", "KSSSK", "KSKSK", "KSSSK", ".KKK."]
SHINE = ["...K...", "..KWK..", ".KWYWK.", "KWYWYWK", ".KWYWK.", "..KWK..", "...K..."]
STITCH = ["L...L", ".L.L.", "..L..", ".L.L.", "L...L"]           # um X de linha no ar
FLUFF_S = [".KK.", "KFFK", "KFfK", ".KK."]
FLUFF_L = ["..KKK..", ".KFFFKK", "KFFfFFK", "KFFFFfK", ".KfFFK.", "..KKK.."]
RIP = ["K.K.K", "KFFFK", "FFfFF", "KFFFK"]                       # costura aberta com enchimento
HAND = [".KK.", "KCCK", "KCCK", ".KK."]


def needle(g, eye, tip):
    """Agulha grande do olho (anel) até a ponta, com brilho na ponta."""
    trait(g, eye, tip, "S")
    stamp(g, EYE_SHARP, eye[0] - 2, eye[1] - 2)
    g[tip[1]][tip[0]] = "W"


def fio(g, pts):
    """Linha vermelha fina passando pelos pontos."""
    for a, b in zip(pts, pts[1:]):
        for x, y in line(*a, *b):
            if 0 <= x < N and 0 <= y < N and g[y][x] == ".":
                g[y][x] = "L"


def frame(cx=15, base=30, hr=6, leg=3, lean=0, falls=0, eyes="h", mouth="", arms=(), needles=(), strands=(),
           por=(), behind=(), feet=(0, 0), loose=False, tear=False):
    """Um quadro 32x32 e a âncora do acréscimo (12 à esquerda e 6 acima do topo da cabeça).
    `hr`: altura do vestido; `perna`: altura das pernas; `cai`: quanto a cabeça afunda no vestido;
    `solto`: o botão da direita pendurado pela linha."""
    g = [["."] * N for _ in range(N)]
    for s, x, y in behind:
        stamp(g, s, x, y)
    cint = base - leg - hr                      # primeira linha do vestido
    ch = cx + lean
    top = cint - HH + 1 + falls
    vest = set()
    for y in range(cint, base - leg):
        t = (y - cint) / max(hr - 1, 1)
        c = ch - round(lean * t)
        m = 3 + round(3 * t)
        vest |= {(x, y) for x in range(c - m, c + m + 1)}
    legs = {(x, y) for px, dx in ((cx - 3, feet[0]), (cx + 1, feet[1]))
              for x in range(px + dx, px + dx + 2) for y in range(base - leg, base)}
    sap = {(x, base) for px, dx in ((cx - 4, feet[0]), (cx + 1, feet[1])) for x in range(px + dx, px + dx + 3)}
    cab = {(x, top + r) for r, w in enumerate(HEAD) for x in range(ch - w, ch + w + 1)}
    tufts = {(ch - 3, top - 1), (ch, top - 1), (ch + 3, top - 1)}
    body = vest | legs | sap | cab | tufts
    for x, y in body:
        if not (0 <= x < N and 0 <= y < N):
            continue
        if (x, y) in cab or (x, y) in tufts:
            r = y - top
            if r < 0 or r < 3 or (r == 3 and x % 3) or (r <= 7 and x <= ch - 5):
                c = "h" if (x + r) % 3 == 0 else "H"           # lã com textura
            else:
                c = "C"
        elif (x, y) in sap:
            c = "D"
        elif (x, y) in legs:
            c = "h" if (y - base) % 2 else "C"                 # meia listrada
        else:
            c = "v" if (x + 1, y) not in vest else "V"
        g[y][x] = c
    for x, y in body:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in body and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    # gola, costura tracejada na lateral e remendo cor de mostarda com pontos nos cantos
    for x in range(ch - 2, ch + 3):
        if (x, cint + 1 - (falls > 0)) in vest and top + HH <= cint + 1:
            g[cint + 1][x] = "F"
    for y in range(cint + 2, base - leg, 2):
        g[y][ch - 2 - round(lean * (y - cint) / max(hr - 1, 1))] = "K"
    if hr >= 5:
        px, py = cx + 1, base - leg - 3
        stamp(g, ["KQK", "QQQ", "KQK"], px, py)
    # rosto: olhos de botão (esquerdo azul, direito vermelho), boca costurada, bochechas
    fc = ch + 1
    ey = top + 5
    for i, x in enumerate((fc - 4, fc + 1)):
        color = "E" if i == 0 else "e"
        if i == 1 and loose:
            stamp(g, ["K.K", ".K.", "K.K"], x, ey)          # buraco do botão com a linha
            continue
        if eyes == "fechado":
            stamp(g, ["KKK"], x, ey + 1)
        elif eyes == "cima":
            stamp(g, [l.replace("E", color) for l in BUTTON["h"]], x, ey - 1)
        else:
            stamp(g, [l.replace("E", color) for l in BUTTON.get(eyes, BUTTON["h"])], x, ey)
    if eyes == "bravo":
        g[ey - 1][fc - 1] = g[ey - 1][fc + 1] = "K"
    elif eyes == "triste":
        g[ey - 1][fc - 4] = g[ey - 1][fc + 3] = "K"
    if eyes != "fechado":
        g[ey + 3][fc - 5] = g[ey + 3][fc + 4] = "P"
    my = top + 9
    if mouth == "feliz":
        for x in (fc - 2, fc + 2):
            g[my - 1][x] = "K"
        for x in range(fc - 1, fc + 2):
            g[my][x] = "K"
    elif mouth == "triste":
        for x in range(fc - 1, fc + 2):
            g[my - 1][x] = "K"
        g[my][fc - 2] = g[my][fc + 2] = "K"
    elif mouth == "o":
        stamp(g, ["KK", "KK"], fc, my - 1)
    elif mouth == "grito":
        stamp(g, ["KKKK", "KLLK", "KKKK"], fc - 1, my - 1)
    else:                                                       # boca costurada
        for x in range(fc - 2, fc + 3):
            g[my][x] = "K"
        g[my - 1][fc - 1] = g[my - 1][fc + 1] = "K"
    if loose:                                                   # botão pendurado do lado de fora da cabeça
        fio(g, [(fc + 3, ey + 1), (fc + 5, ey + 3), (fc + 6, ey + 5)])
        stamp(g, [".KKK.", "KeeeK", "KeKeK", "KeeeK", ".KKK."], fc + 5, ey + 5)
    if tear:
        stamp(g, TEAR, fc - 3, ey + 3)
    for a, b in arms:
        x, y = a
        while (x, y) in body:             # o braço sai da beirada do corpo, sem riscar o vestido
            x += 1 if x >= ch else -1
        trait(g, (x, y), b, "C")
        stamp(g, HAND, b[0] - 1, b[1] - 1)
    for pts in strands:
        fio(g, pts)
    for eye, tip in needles:
        needle(g, eye, tip)
    for s, x, y in por:
        stamp(g, s, x, y)
    return ["".join(l) for l in g], (ch - 12, top - 6)


def _state(specs):
    qs = [frame(**s) for s in specs]
    return [q for q, _ in qs], [a for _, a in qs]


# base=30, hr=6, perna=3 -> vestido 21-26, pernas 27-29, sapatos 30, cabeça 11-21; ombros em (cx±4, 22)
_SPECS = {
    # parada, os furinhos dos botões giram (a boneca "pisca") e a agulhinha balança na mão
    "idle": [dict(eyes="h", arms=(((19, 23), (23, 23)), ((11, 23), (8, 27))),
                  needles=(((24, 26), (25, 17)),), strands=([(24, 27), (25, 29)],)),
             dict(eyes="d1", arms=(((19, 23), (23, 24)), ((11, 23), (8, 27))),
                  needles=(((24, 27), (26, 18)),), strands=([(24, 28), (23, 30)],)),
             dict(eyes="v", arms=(((19, 23), (23, 23)), ((11, 23), (8, 27))),
                  needles=(((24, 26), (25, 17)),), strands=([(24, 27), (25, 29)],)),
             dict(eyes="d2", arms=(((19, 23), (23, 24)), ((11, 23), (8, 27))),
                  needles=(((24, 27), (26, 18)),), strands=([(24, 28), (26, 30)],))],
    # corre inclinada, braços de pano balançando, a linha voando atrás
    "run_r": [dict(lean=2, feet=(-2, 2), arms=(((19, 23), (24, 20)), ((12, 23), (6, 26))),
                   strands=([(5, 27), (2, 25), (0, 27)],)),
              dict(lean=3, base=29, eyes="d1", arms=(((19, 22), (23, 26)), ((12, 22), (6, 19))),
                   strands=([(5, 19), (2, 21), (0, 19)],)),
              dict(lean=2, feet=(2, -2), arms=(((19, 23), (24, 26)), ((12, 23), (6, 21))),
                   strands=([(5, 21), (2, 19), (0, 21)],)),
              dict(lean=3, base=29, eyes="d2", arms=(((19, 22), (24, 19)), ((12, 22), (6, 26))),
                   strands=([(5, 26), (2, 28), (0, 26)],))],
    # acena alto com a mão direita; a outra segura a agulha para baixo
    "waving": [dict(mouth="feliz", arms=(((19, 23), (25, 18)), ((11, 23), (7, 25))),
                    needles=(((7, 23), (4, 30)),)),
               dict(mouth="feliz", arms=(((19, 23), (26, 13)), ((11, 23), (7, 25))),
                    needles=(((7, 23), (4, 30)),)),
               dict(mouth="feliz", eyes="v", arms=(((19, 23), (29, 15)), ((11, 23), (7, 25))),
                    needles=(((7, 23), (4, 30)),)),
               dict(mouth="feliz", arms=(((19, 23), (26, 13)), ((11, 23), (7, 25))),
                    needles=(((7, 23), (4, 30)),))],
    # agacha (vestido amassado), salta de braços para cima, cai, pousa
    "jumping": [dict(hr=5, leg=2, eyes="fechado", arms=(((19, 25), (24, 28)), ((11, 25), (6, 28)))),
                dict(base=27, arms=(((19, 20), (24, 14)), ((11, 20), (6, 14)))),
                dict(base=25, mouth="o", eyes="cima", feet=(-1, 1),
                     arms=(((19, 18), (25, 11)), ((11, 18), (5, 11)))),
                dict(base=27, arms=(((19, 20), (25, 22)), ((11, 20), (5, 22)))),
                dict(hr=5, mouth="feliz", arms=(((19, 24), (24, 27)), ((11, 24), (6, 27))))],
    # desmonta: chora, o vestido rasga, o enchimento escapa, o botão fica pendurado e ela desaba
    "failed": [dict(eyes="triste", mouth="triste", tear=True,
                    arms=(((19, 23), (22, 27)), ((11, 23), (8, 27)))),
               dict(eyes="triste", mouth="triste", arms=(((19, 23), (22, 28)), ((11, 23), (8, 28))),
                    por=((RIP, 11, 24), (FLUFF_S, 6, 21))),
               dict(eyes="triste", mouth="triste", hr=5, falls=1, loose=True,
                    arms=(((19, 24), (23, 29)), ((11, 24), (8, 29))),
                    por=((RIP, 11, 25), (FLUFF_S, 5, 20), (FLUFF_S, 2, 26))),
               dict(eyes="x", hr=4, leg=2, falls=2, lean=-1, loose=True, feet=(-2, 2),
                    arms=(((18, 26), (24, 29)), ((10, 26), (5, 29))),
                    por=((FLUFF_L, 0, 23), (FLUFF_S, 9, 18), (FLUFF_S, 26, 20))),
               dict(eyes="x", hr=3, leg=1, falls=3, lean=-1, loose=True, feet=(-3, 3),
                    arms=(((18, 27), (25, 30)), ((10, 27), (4, 30))),
                    por=((FLUFF_L, 0, 24), (FLUFF_L, 24, 21), (FLUFF_S, 8, 18)))],
    # cochila de cabeça caída, olhos de botão costurados fechados, "z" subindo
    "waiting": [dict(hr=5, falls=1, lean=1, eyes="fechado", arms=(((19, 24), (21, 28)), ((11, 24), (10, 28)))),
                dict(hr=5, falls=1, lean=1, eyes="fechado", arms=(((19, 24), (21, 28)), ((11, 24), (10, 28))),
                     por=((Z_S, 24, 6),)),
                dict(hr=5, falls=1, lean=1, eyes="fechado", arms=(((19, 24), (21, 28)), ((11, 24), (10, 28))),
                     por=((Z_S, 23, 6), (Z_L, 26, 0))),
                dict(hr=5, falls=1, lean=1, eyes="fechado", arms=(((19, 24), (21, 28)), ((11, 24), (10, 28))),
                     por=((Z_L, 26, 0),))],
    # golpe de agulha: ergue, espeta com tudo (brilho), puxa a linha dando um ponto em X, espeta de novo
    "running": [dict(cx=14, lean=-1, eyes="bravo", arms=(((20, 23), (22, 17)),),
                     needles=(((23, 15), (31, 11)),), strands=([(22, 17), (26, 21), (25, 25)],)),
                dict(cx=13, lean=2, eyes="bravo", mouth="grito", arms=(((17, 23), (21, 24)),),
                     needles=(((22, 24), (31, 24)),), strands=([(20, 25), (14, 29), (8, 27)],),
                     por=((SHINE, 25, 16),)),
                dict(cx=13, lean=1, eyes="bravo", arms=(((17, 23), (20, 26)),),
                     needles=(((21, 27), (27, 21)),), strands=([(26, 15), (23, 19), (20, 26)],),
                     por=((STITCH, 25, 9),)),
                dict(cx=13, lean=2, eyes="bravo", mouth="grito", arms=(((17, 23), (21, 24)),),
                     needles=(((22, 24), (31, 24)),), strands=([(20, 25), (16, 28), (10, 26)],),
                     por=((STITCH, 25, 9), (SHINE, 25, 17)))],
    # mão no queixo, botões olhando para cima, "?" aparece
    "review": [dict(cx=13, eyes="cima", arms=(((17, 25), (19, 21)),)),
               dict(cx=13, eyes="cima", arms=(((17, 25), (19, 21)),), por=((QMARK_S, 25, 4),)),
               dict(cx=13, eyes="cima", arms=(((17, 25), (19, 21)),), por=((QMARK, 25, 2),)),
               dict(cx=13, eyes="v", arms=(((17, 25), (19, 21)),), por=((QMARK, 25, 2),))],
}

FRAMES, ANCHOR = {}, {}
for _e, _s in _SPECS.items():
    FRAMES[_e], ANCHOR[_e] = _state(_s)

# grade 22x12 colada 12 à esquerda e 6 acima do topo da cabeça (topo da cabeça na linha 6, de x=6 a x=18):
# laço de fita no alto da cabeça, à direita; a agulha espetada no cabelo de trás, com a linha caindo nas costas
_BOW = [
    "KKK...KKK",
    "KLLK.KLLK",
    "KLlLKLlLK",
    "KLLKlKLLK",
    "KKKKKKKKK",
    "..KLK.KLK",
    "..KK...KK",
]
_NEEDLE_BACK = [
    ".KKK......",
    "KSSSK.....",
    "KSKSK.....",
    "KSSSKK....",
    ".KKKSSK...",
    "..L.KSSK..",
    "..L..KSSK.",
    ".L....KSK.",
    ".L.....K..",
    "..L.......",
    "..L.......",
    "...L......",
]


def _extra(pieces, w=22, h=12):
    g = [["."] * w for _ in range(h)]
    for s, x, y in pieces:
        for dy, lin in enumerate(s):
            for dx, ch in enumerate(lin):
                if ch != "." and 0 <= y + dy < h and 0 <= x + dx < w:
                    g[y + dy][x + dx] = ch
    return ["".join(l) for l in g]


BOW = _extra(((_BOW, 12, 2),))
BOW_NEEDLE = _extra(((_BOW, 12, 2), (_NEEDLE_BACK, 0, 0)))
STAGES = [
    {"title": "Retalho", "floor": 1, "extra": None},
    {"title": "Boneca de Pano", "floor": 4, "extra": BOW},
    {"title": "Boneca Remendada", "floor": 10, "extra": BOW_NEEDLE},
]
