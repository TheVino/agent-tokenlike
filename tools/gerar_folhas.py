"""Gera as folhas do Fantasma (characters/fantasma/folha1..3.png) e a prévia de todos os estados dos
heróis embutidos (tools/saida/preview_herois.png). Só biblioteca padrão.

Folha: grade 8 x 9 (linhas na ordem de folha.ESTADOS), células de 20 px com o quadro de 16 px embaixo.
Cada estado tem 4 quadros, repetidos para encher as 8 colunas (a grade fixa usa todas).
Uso: python tools/gerar_folhas.py [--so-preview]
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))
import arte_herois as AH  # noqa: E402
import folha  # noqa: E402
from _png import escrever_png  # noqa: E402

FANTASMA_PAL = {
    "K": "#2a2140", "B": "#2a2140", "G": "#f2f0ff", "D": "#c6c0e8", "L": "#ffffff", "P": "#ff9ec4",
    "H": "#8f86c9", "Y": "#ffd23f", "O": "#ff9f43", "T": "#8fd8ff",
}

FANTASMINHA = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "......KKKK......",
    ".....KGGGGK.....",
    "....KGGGGGGK....",
    "....KGBGGBGK....",
    "....KGBGGBGK....",
    "....KPGKKGPK....",
    "....KGGGGGDK....",
    "....KDGGGGDK....",
    "....KGKGGKGK....",
    ".....K.KK.K.....",
]

FANTASMA = [
    "................",
    "................",
    ".....KKKKKK.....",
    "....KGGGGGGK....",
    "...KGGGGGGGGK...",
    "..KGGGGGGGGGGK..",
    "..KGGBBGGBBGGK..",
    "..KGGBBGGBBGGK..",
    "..KGPGGGGGGPGK..",
    "..KGGGGKKGGGGK..",
    "..KGGGGGGGGGGK..",
    "..KDGGGGGGGGDK..",
    "..KDGGGGGGGGDK..",
    "..KDDGGGGGGDDK..",
    "..KGKGGKKGGKGK..",
    "...K.KK..KK.K...",
]

FANTASMA_MAGO = [
    "......KHK.......",
    ".....KHHHK......",
    "...KKHHHHHHKK...",
    "....KKKKKKKK....",
    "...KGGGGGGGGK...",
    "..KGGGGGGGGGGK..",
    "..KGGBBGGBBGGK..",
    "..KGGBBGGBBGGK..",
    "..KGPGGGGGGPGKK.",
    "..KGGGGKKGGGGKYK",
    "..KGGGGGGGGGGKOK",
    "..KDGGGGGGGGDKOK",
    "..KDGGGGGGGGDKKK",
    "..KDDGGGGGGDDK..",
    "..KGKGGKKGGKGK..",
    "...K.KK..KK.K...",
]

# (arquivo, grade, mão, bolha)
FANTASMAS = [("folha1.png", FANTASMINHA, (11, 7), (12, 3)),
             ("folha2.png", FANTASMA, (13, 3), (13, 0)),
             ("folha3.png", FANTASMA_MAGO, (12, 3), (13, 0))]

CEL = 20


def estados_fantasma(grade, mao, bolha):
    return AH.estados(grade, mao, bolha, teto=16)


def _rgba(cor):
    return bytes(int(cor[i:i + 2], 16) for i in (1, 3, 5)) + b"\xff"


def gerar_folha(path, est, pal):
    w, h = 8 * CEL, 9 * CEL
    px = [[b"\0\0\0\0"] * w for _ in range(h)]
    for r, e in enumerate(folha.ESTADOS):
        quadros = est[e]
        for c in range(8):
            g = quadros[c % len(quadros)]
            assert len(g) == 16, (e, len(g))
            ox, oy = c * CEL + (CEL - 16) // 2, r * CEL + CEL - 16
            for y, lin in enumerate(g):
                for x, ch in enumerate(lin):
                    if ch != ".":
                        px[oy + y][ox + x] = _rgba(pal[ch])
    escrever_png(path, w, h, [b"".join(lin) for lin in px])


def preview(path, herois, esc=5):
    """Uma faixa por estágio: os 9 estados lado a lado, cada um com os 4 quadros. Fundo xadrez cinza."""
    cel, topo = 22, 6          # quadro de 16 px com 6 px de folga em cima (pulo) e sobra dos lados
    faixas = [(est, pal) for est, pal in herois]
    w = 9 * (4 * cel + 4)
    h = len(faixas) * (cel + topo)
    px = [[b"\x50\x50\x60\xff" if ((x // 4 + y // 4) % 2) else b"\x46\x46\x54\xff" for x in range(w)]
          for y in range(h)]
    for i, (est, pal) in enumerate(faixas):
        for j, e in enumerate(folha.ESTADOS):
            for q, g in enumerate(est[e]):
                ox = j * (4 * cel + 4) + q * cel + (cel - len(g[0])) // 2
                oy = i * (cel + topo) + topo + 16 - len(g)      # base em y = 16 (como spec_to_map)
                for y, lin in enumerate(g):
                    for x, ch in enumerate(lin):
                        if ch != "." and 0 <= oy + y < h:
                            px[oy + y][ox + x] = _rgba(pal[ch])
            for y in range(i * (cel + topo), (i + 1) * (cel + topo)):   # separador entre estados
                px[y][j * (4 * cel + 4) + 4 * cel + 1] = b"\x20\x20\x28\xff"
    linhas = [b"".join(p * esc for p in lin) for lin in px for _ in range(esc)]
    escrever_png(path, w * esc, h * esc, linhas)


def main():
    pasta = RAIZ / "characters" / "fantasma"
    fantasmas = [(estados_fantasma(g, m, b), FANTASMA_PAL) for _, g, m, b in FANTASMAS]
    if "--so-preview" not in sys.argv:
        for (nome, *_), (est, pal) in zip(FANTASMAS, fantasmas):
            gerar_folha(pasta / nome, est, pal)
            print("gerado", pasta / nome)
    slimes = [(AH.estados_slime(t), AH.SLIME_PALETTE) for t in AH.GRADES_SLIME]
    saida = RAIZ / "tools" / "saida" / "preview_herois.png"
    preview(saida, slimes + fantasmas)
    print("prévia", saida, "| colunas:", ", ".join(folha.ESTADOS))


if __name__ == "__main__":
    main()
