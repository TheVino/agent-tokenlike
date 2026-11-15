"""Gera as folhas do Fantasma (characters/fantasma/folha1..3.png) e a prévia de todos os estados dos
heróis embutidos (tools/out/preview_heroes.png). Só biblioteca padrão.

Folha: grade 8 x 9 (linhas na ordem de folha.ESTADOS), células de 40 px (heróis 32 px) com o quadro embaixo.
Cada estado tem 4 a 6 quadros; as colunas sobrando ficam vazias (o leitor ignora célula vazia).
Uso: python tools/gerar_folhas.py [--so-preview]
"""
import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tests"))
import sheet  # noqa: E402
from heroes import assemble  # noqa: E402
from _png import write_png  # noqa: E402

CELL = 40


def _rgba(color):
    return bytes(int(color[i:i + 2], 16) for i in (1, 3, 5)) + b"\xff"


def make_sheet(path, est, pal, cel=CELL):
    """Grade 8 x 9, quadro 32 px centrado na célula e com a base no fundo dela."""
    w, h = 8 * cel, 9 * cel
    px = [[b"\0\0\0\0"] * w for _ in range(h)]
    for r, e in enumerate(sheet.STATES):
        frames = est[e]
        for c, g in enumerate(frames[:8]):   # só os quadros reais; as células sobrando ficam vazias
            n = len(g)
            ox, oy = c * cel + (cel - n) // 2, r * cel + cel - n
            for y, lin in enumerate(g):
                for x, ch in enumerate(lin):
                    if ch != ".":
                        px[oy + y][ox + x] = _rgba(pal[ch])
    write_png(path, w, h, [b"".join(lin) for lin in px])


def preview(path, heroes, esc=4):
    """Uma faixa por estágio: os 9 estados lado a lado, até 6 quadros de cada. Fundo xadrez."""
    n, slack = 32, 2
    cel = n + slack
    larg = 6 * cel + 4
    w, h = 9 * larg, len(heroes) * cel
    px = [[b"\x50\x50\x60\xff" if ((x // 4 + y // 4) % 2) else b"\x46\x46\x54\xff" for x in range(w)]
          for y in range(h)]
    for i, (est, pal) in enumerate(heroes):
        for j, e in enumerate(sheet.STATES):
            for q, g in enumerate(est[e][:6]):
                ox, oy = j * larg + q * cel + slack // 2 + (n - len(g[0])) // 2, i * cel + slack // 2 + n - len(g)
                for y, lin in enumerate(g):
                    for x, ch in enumerate(lin):
                        if ch != ".":
                            px[oy + y][ox + x] = _rgba(pal[ch])
            for y in range(i * cel, (i + 1) * cel):
                px[y][j * larg + larg - 2] = b"\x20\x20\x28\xff"
    lines = [b"".join(p * esc for p in lin) for lin in px for _ in range(esc)]
    write_png(path, w * esc, h * esc, lines)


HEROES = ["slime", "fantasma", "medico", "bruxa", "coveiro", "ceifeirinho", "vela", "cogumelo", "inquisidor", "boneca", "cavaleiro", "corvo", "alquimista", "freira", "espantalho", "golem", "mariposa", "sapo", "gato", "polvo"]


def main():
    preview_only = "--preview-only" in sys.argv
    bands = []
    for k in HEROES:
        try:
            mod = importlib.import_module("heroes." + k)
        except ModuleNotFoundError:
            print("sem módulo herois." + k + ", pulando")
            continue
        assemble.validate(mod)
        for i in range(3):
            est = assemble.states(mod, i)
            bands.append((est, mod.PAL))
            if k != "slime" and not preview_only:
                path = REPO_ROOT / "characters" / k / f"folha{i + 1}.png"
                make_sheet(path, est, mod.PAL)
                print("gerado", path)
    out = REPO_ROOT / "tools" / "out" / "preview_heroes.png"
    preview(out, bands)
    print("prévia", out, "| colunas:", ", ".join(sheet.STATES))


if __name__ == "__main__":
    main()
