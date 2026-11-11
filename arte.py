# -*- coding: utf-8 -*-
"""Pixel art da Masmorra de Tokens (tudo original). '.' = transparente."""

PAL = {
    "K": "#1b1b2f", "x": "#0b0b14", "w": "#f2f0ff", "G": "#d7dde9", "g": "#8a94a8",
    "b": "#7a4a2a", "B": "#b0763f", "y": "#ffd23f", "Y": "#c99a00",
    "r": "#e2384d", "R": "#8f1d2c", "p": "#6a3fb5", "P": "#b48cff",
    "o": "#ff9f43", "e": "#fff27a", "n": "#e8dcc0", "c": "#6fd6ff", "v": "#4fbf5a",
}
# chefes: mesmas formas, cores mais sombrias
BOSS_PAL = dict(PAL, p="#3d1f6e", P="#7a3fd1", g="#5a5f73", G="#a3a9bb", n="#cfc0a0",
                w="#ffd9e0", b="#4a2a1a", B="#7a4a2a")

# ------------------------------------------------------------------ itens
ITEM_ART = {
    "adaga": [
        "..K..",
        ".KoK.",
        ".KoK.",
        ".KoK.",
        "KKKKK",
        ".KbK.",
        ".KbK.",
        "..K..",
    ],
    "espada_osso": [
        "..K..",
        ".KnK.",
        ".KnK.",
        ".KnK.",
        ".KnK.",
        "KKnKK",
        "KnnnK",
        ".KbK.",
        ".KKK.",
    ],
    "cajado": [
        ".KKK.",
        "KcwcK",
        "KcccK",
        ".KKK.",
        ".KbK.",
        ".KbK.",
        ".KbK.",
        ".KbK.",
        "..K..",
    ],
    "foice": [
        "KKKKK.",
        "KPPPPK",
        ".KKKpK",
        "...KbK",
        "...KbK",
        "...KbK",
        "...KbK",
        "...KbK",
        "...KK.",
    ],
    "tampa": [
        "..KKK..",
        ".KGKGK.",
        "KGGGGGK",
        "KgggggK",
        "KgggggK",
        ".KgggK.",
        "..KKK..",
    ],
    "escudo_ferro": [
        "KKKKKK",
        "KGGGgK",
        "KGrrgK",
        "KGrrgK",
        "KGGggK",
        ".KGgK.",
        ".KggK.",
        "..KK..",
    ],
    "lanterna": [
        "..K..",
        ".K.K.",
        "KKKKK",
        "KcwcK",
        "KcwcK",
        "KcccK",
        "KKKKK",
        ".KKK.",
    ],
    "grimorio": [
        "KKKKKKK",
        "KpppppK",
        "KpPyPpK",
        "KpPPPpK",
        "KpppppK",
        "KKKKKKK",
    ],
    "chapeu": [
        ".....KK...",
        "....KpK...",
        "...KppK...",
        "..KpPppK..",
        ".KyyyyyyK.",
        "KppppppppK",
        "KKKKKKKKKK",
    ],
    "gorro": [
        "...KKKK...",
        ".KKggggKK.",
        "KggggggggK",
        "KKKKKKKKKK",
    ],
    "chifres": [
        "K..........K",
        "KrK......KrK",
        ".KrK....KrK.",
        "..KRK..KRK..",
    ],
    "aureola": [
        ".KKKKKKKK.",
        "KyyyKyyyyK",
        ".KKKKKKKK.",
    ],
    "vela": [
        "..K..",
        ".KoK.",
        ".KeK.",
        "..K..",
        ".KKK.",
        "KwwwK",
        "KwnwK",
        "KwwwK",
        "KKKKK",
    ],
    "carapaca": [
        "..K.K.K..",
        ".KgKgKgK.",
        "KgGgGgGgK",
        "KgGKGKGgK",
        "KgGgGgGgK",
        ".KgggggK.",
        "..KKKKK..",
    ],
    "baba": [
        ".KKKKK.",
        "KvvvvvK",
        "KvKvvvK",
        "KvvvKvK",
        ".KvvvK.",
        ".v...v.",
        ".c...v.",
    ],
    "aura": [
        "..KKKKK..",
        ".KpPPPpK.",
        "KpP...PpK",
        "KP.....PK",
        "KpP...PpK",
        ".KpPPPpK.",
        "..KKKKK..",
    ],
    "veneno": [
        "..KKK..",
        "..KgK..",
        ".KKrKK.",
        "KrrRrrK",
        "KrRrrRK",
        "KrrrrrK",
        ".KKKKK.",
    ],
    "terceiro_olho": [
        ".KKKKK.",
        "KwwpwwK",
        "KwpxpwK",
        "KwwpwwK",
        ".KKKKK.",
    ],
    "orbe": [
        "..KKK..",
        ".KcwcK.",
        "KcwccPK",
        "KccccPK",
        ".KcPPK.",
        "..KKK..",
    ],
    "coroa_cinzas": [
        "K..K.K..K",
        "KgKKgKKgK",
        "KgGgGgGgK",
        "KgGyGyGgK",
        "KgggggggK",
        "KKKKKKKKK",
    ],}

# --------------------------------------------------------------- monstros
FOE_ART = {
    "morcego": [
        "K........K",
        "KpK.KK.KpK",
        "KppKppKppK",
        ".KprpprpK.",
        "..KppppK..",
        "...KKKK...",
    ],
    "rato": [
        "..KK.......",
        ".KGKKKKKK..",
        "KrgggggggK.",
        "KggggggggKK",
        ".KKgKKKgK.K",
        "...K...K...",
    ],
    "aranha": [
        "K..KKKK..K",
        ".KKxxxxKK.",
        "K.KxrrxK.K",
        ".KKxxxxKK.",
        "K..KxxK..K",
        "..K....K..",
    ],
    "esqueleto": [
        ".KKKKKK.",
        "KnnnnnnK",
        "KnxnnxnK",
        "KnxnnxnK",
        "KnnnKnnK",
        ".KnnnnK.",
        ".KnKnKnK",
        "..KKKKK.",
    ],
    "olho": [
        "..KKKK..",
        ".KwwwwK.",
        "KwwrrwwK",
        "KwrxxrwK",
        "KwrxxrwK",
        "KwwrrwwK",
        ".KwwwwK.",
        "..KKKK..",
    ],
    "mimico": [
        ".KKKKKK.",
        "KbBBBBbK",
        "KnKnKnKK",
        "KrrrrrrK",
        "KKnKnKnK",
        "KbBByBbK",
        "KKKKKKKK",
    ],
}

CROWN = [
    "y..y..y",
    "yy.y.yy",
    "yyyyyyy",
    "yryyyry",
    "KKKKKKK",
]

# ----------------------------------------------------------------- salas
ROOM_ART = {
    "bau": [
        ".KKKKKK.",
        "KbBBBBbK",
        "KbBBBBbK",
        "KKKyyKKK",
        "KbByyBbK",
        "KbBBBBbK",
        "KKKKKKKK",
    ],
    "armadilha": [
        "..K...K..",
        ".KGK.KGK.",
        "KGggKGggK",
        "KKKKKKKKK",
    ],
    "altar": [
        "...KK...",
        "..KorK..",
        "...KK...",
        "KKKKKKKK",
        "KpPPPPpK",
        ".KppppK.",
        "KKKKKKKK",
    ],
    "fonte": [
        "...KK...",
        "..KccK..",
        "...KK...",
        "KKKKKKKK",
        "KgccccgK",
        ".KggggK.",
        "KKKKKKKK",
    ],
    "loja": [
        "..KKK..",
        "...K...",
        ".KKKKK.",
        "KBBBBBK",
        "KBByBBK",
        "KByyyBK",
        "KBBBBBK",
        ".KKKKK.",
    ],
    "escada": [
        "KKKKKKKK",
        "KxxxxxGK",
        "KxxxxGGK",
        "KxxxGGGK",
        "KxxGGGGK",
        "KxGGGGGK",
        "KGGGGGGK",
        "KKKKKKKK",
    ],
    "lapide": [
        "..KKKK..",
        ".KGGGGK.",
        "KGGGGGgK",
        "KGKKKKgK",
        "KGGGGGgK",
        "KGKKKggK",
        "KGGGGGgK",
        "KGGGGggK",
        "KKKKKKKK",
    ],
    "pocao": [
        ".KKK.",
        "..K..",
        ".KrK.",
        "KrrrK",
        "KrwrK",
        "KrrrK",
        ".KKK.",
    ],
}


def all_art():
    out = {}
    for group in (ITEM_ART, FOE_ART, ROOM_ART):
        out.update(group)
    out["coroa"] = CROWN
    return out


def validate():
    for name, g in all_art().items():
        widths = {len(r) for r in g}
        assert len(widths) == 1, f"{name}: linhas com larguras diferentes {widths}"
        for r in g:
            for ch in r:
                assert ch == "." or ch in PAL, f"{name}: cor desconhecida {ch!r}"
