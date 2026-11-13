"""Gera as folhas do Fantasma (characters/fantasma/folha1..3.png) e a prévia de todos os estados dos
heróis embutidos (tools/saida/preview_herois.png). Só biblioteca padrão.

Folha: grade 8 x 9 (linhas na ordem de folha.ESTADOS), células de 40 px (heróis 32 px) com o quadro embaixo.
Cada estado tem 4 a 6 quadros; as colunas sobrando ficam vazias (o leitor ignora célula vazia).
Uso: python tools/gerar_folhas.py [--so-preview]
"""
import importlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))
import folha  # noqa: E402
from herois import montar  # noqa: E402
from _png import escrever_png  # noqa: E402

CEL = 40


def _rgba(cor):
    return bytes(int(cor[i:i + 2], 16) for i in (1, 3, 5)) + b"\xff"


def gerar_folha(path, est, pal, cel=CEL):
    """Grade 8 x 9, quadro 32 px centrado na célula e com a base no fundo dela."""
    w, h = 8 * cel, 9 * cel
    px = [[b"\0\0\0\0"] * w for _ in range(h)]
    for r, e in enumerate(folha.ESTADOS):
        quadros = est[e]
        for c, g in enumerate(quadros[:8]):   # só os quadros reais; as células sobrando ficam vazias
            n = len(g)
            ox, oy = c * cel + (cel - n) // 2, r * cel + cel - n
            for y, lin in enumerate(g):
                for x, ch in enumerate(lin):
                    if ch != ".":
                        px[oy + y][ox + x] = _rgba(pal[ch])
    escrever_png(path, w, h, [b"".join(lin) for lin in px])


def preview(path, herois, esc=4):
    """Uma faixa por estágio: os 9 estados lado a lado, até 6 quadros de cada. Fundo xadrez."""
    n, folga = 32, 2
    cel = n + folga
    larg = 6 * cel + 4
    w, h = 9 * larg, len(herois) * cel
    px = [[b"\x50\x50\x60\xff" if ((x // 4 + y // 4) % 2) else b"\x46\x46\x54\xff" for x in range(w)]
          for y in range(h)]
    for i, (est, pal) in enumerate(herois):
        for j, e in enumerate(folha.ESTADOS):
            for q, g in enumerate(est[e][:6]):
                ox, oy = j * larg + q * cel + folga // 2 + (n - len(g[0])) // 2, i * cel + folga // 2 + n - len(g)
                for y, lin in enumerate(g):
                    for x, ch in enumerate(lin):
                        if ch != ".":
                            px[oy + y][ox + x] = _rgba(pal[ch])
            for y in range(i * cel, (i + 1) * cel):
                px[y][j * larg + larg - 2] = b"\x20\x20\x28\xff"
    linhas = [b"".join(p * esc for p in lin) for lin in px for _ in range(esc)]
    escrever_png(path, w * esc, h * esc, linhas)


HEROIS = ["slime", "fantasma", "medico", "bruxa"]


def main():
    sem = "--so-preview" in sys.argv
    faixas = []
    for k in HEROIS:
        try:
            mod = importlib.import_module("herois." + k)
        except ModuleNotFoundError:
            print("sem módulo herois." + k + ", pulando")
            continue
        montar.validar(mod)
        for i in range(3):
            est = montar.estados(mod, i)
            faixas.append((est, mod.PAL))
            if k != "slime" and not sem:
                path = RAIZ / "characters" / k / f"folha{i + 1}.png"
                gerar_folha(path, est, mod.PAL)
                print("gerado", path)
    saida = RAIZ / "tools" / "saida" / "preview_herois.png"
    preview(saida, faixas)
    print("prévia", saida, "| colunas:", ", ".join(folha.ESTADOS))


if __name__ == "__main__":
    main()
