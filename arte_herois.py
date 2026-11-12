"""Pixel art dos heróis embutidos em grade de texto e os 9 estados de animação (puro, sem tkinter).

Os quadros saem da arte base por transformações puras (subir, achatar, espelhar, trocar olhos e
sobrepor mão, lágrima, "z" e gotas de pensamento), não desenhados do zero. Olhos são as letras
"W"/"B"; corpo "G"; contorno "K". O Fantasma (tools/gerar_folhas.py) usa as mesmas regras.
"""

SLIME_PALETTE = {
    "K": "#1b1b2f", "G": "#57d36b", "L": "#b4f5a8", "D": "#2f9a4a",
    "W": "#ffffff", "B": "#1b1b2f", "P": "#ff8fb1",
    "S": "#d7dde9", "s": "#8a94a8", "R": "#e2384d", "Y": "#ffd23f", "y": "#c99a00",
    "T": "#8fd8ff",   # lágrima, gotas de pensamento e o "z" do sono
}

SLIME_GOTINHA = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".......KK.......",
    "......KLGK......",
    ".....KLGGGK.....",
    "....KGGGGGGK....",
    "....KGWBGWBK....",
    "...KGGGGGGGGK...",
    "...KPGGKKGGPK...",
    "...KDGGGGGGDK...",
    "....KKKKKKKK....",
]

SLIME = [
    "................",
    "................",
    "................",
    "......KKKK......",
    "....KKLLGGKK....",
    "...KLLGGGGGGK...",
    "..KLGGGGGGGGGK..",
    "..KLGGGGGGGGGK..",
    ".KGGGWWGGWWGGGK.",
    ".KGGGWBGGWBGGGK.",
    ".KGPPGGGGGGPPGK.",
    ".KGGGGGKKGGGGGK.",
    ".KGGGGGGGGGGGGK.",
    ".KDGGGGGGGGGGDK.",
    "..KDDDDDDDDDDK..",
    "...KKKKKKKKKK...",
]

SLIME_CAVALEIRO = [
    "........RR......",
    ".......RRK......",
    ".....KKKKKK.....",
    "....KSSSSSSK....",
    "...KSLSSSSSsK...",
    "..KSLSSSSSSSsK..",
    "..KssssssssssK..",
    ".KGGGGGGGGGGGGK.",
    ".KGGGWWGGWWGGGK.",
    ".KGGGWBGGWBGGGK.",
    ".KGPPGGGGGGPPGK.",
    ".KGGGGGKKGGGGGK.",
    ".KGGGGGGGGGGGGK.",
    ".KDGGGGGGGGGGDK.",
    "..KDDDDDDDDDDK..",
    "...KKKKKKKKKK...",
]

REI_SLIME = [
    "....Y..YY..Y....",
    "....YY.YY.YY....",
    "....YYYYYYYY....",
    "....YRYYYYRY....",
    "...KyyyyyyyyK...",
    "..KLGGGGGGGGGK..",
    ".KLGGGGGGGGGGGK.",
    "KLGGGGGGGGGGGGGK",
    "KGGGGWWGGWWGGGGK",
    "KGGGGWBGGWBGGGGK",
    "KGGPPGGGGGGPPGGK",
    "KGGGGKGGGGKGGGGK",
    "KGGGGGKKKKGGGGGK",
    "KDGGGGGGGGGGGGDK",
    ".KDDDDDDDDDDDDK.",
    "..KKKKKKKKKKKK..",
]


def blink_grid(grid: list[str], eye_chars: str, body_char: str) -> list[str]:
    """Fecha os olhos: a última linha do olho vira traço, as de cima viram corpo."""
    eyes = [(y, x) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch in eye_chars]
    bottom = {}
    for y, x in eyes:
        bottom[x] = max(bottom.get(x, y), y)
    rows = [list(r) for r in grid]
    for y, x in eyes:
        rows[y][x] = "K" if y == bottom[x] else body_char
    return ["".join(r) for r in rows]


# ------------------------------------------------------------ transformações
def _vazia(row):
    return set(row) <= {"."}


def _olhos(grid):
    """Olhos agrupados por proximidade em x: [{x: [linhas]}], da esquerda para a direita."""
    cels = sorted((x, y) for y, r in enumerate(grid) for x, ch in enumerate(r) if ch in "WB")
    grupos = []
    for x, y in cels:
        if not grupos or x - max(grupos[-1]) > 1:
            grupos.append({})
        grupos[-1].setdefault(x, []).append(y)
    return grupos


def _por(rows, x, y, ch):
    if 0 <= y < len(rows) and 0 <= x < len(rows[y]):
        rows[y][x] = ch


def _mudar_olhos(grid, fn):
    rows = [list(r) for r in grid]
    gs = _olhos(grid)
    for i, g in enumerate(gs):
        xs = sorted(g)
        y0, y1 = min(min(v) for v in g.values()), max(max(v) for v in g.values())
        dentro = xs[-1] if i == 0 else xs[0]          # canto voltado para o nariz
        fora = xs[0] if i == 0 else xs[-1]
        fn(rows, xs, y0, y1, dentro, fora, g)
    return ["".join(r) for r in rows]


def fechar(grid):
    """Olhos fechados (traço embaixo): sono e piscar."""
    def f(rows, xs, y0, y1, *_):
        for x in xs:
            for y in range(y0, y1 + 1):
                rows[y][x] = "K" if y == y1 else "G"
    return _mudar_olhos(grid, f)


def feliz(grid):
    """Olhos em arco (traço em cima): aceno, contente."""
    def f(rows, xs, y0, y1, *_):
        for x in xs:
            for y in range(y0, y1 + 1):
                rows[y][x] = "K" if y == y0 else "G"
    return _mudar_olhos(grid, f)


def triste(grid):
    """Olhos caídos (traço que desce para fora)."""
    def f(rows, xs, y0, y1, dentro, fora, g):
        for x in xs:
            for y in range(y0, y1 + 1):
                rows[y][x] = "G"
        for x in xs:
            rows[y0 if x == dentro else y1][x] = "K"
    return _mudar_olhos(grid, f)


def bravo(grid):
    """Sobrancelha descendo para dentro: o olho perde o canto de cima de fora e ganha um traço por cima."""
    def f(rows, xs, y0, y1, dentro, fora, g):
        rows[y0][fora] = "K"
        _por(rows, dentro, y0 - 1, "K")
    return _mudar_olhos(grid, f)


def olhar_cima(grid):
    """Pupila para cima (olho com branco) ou o olho todo um pixel acima (olho só escuro)."""
    def f(rows, xs, y0, y1, dentro, fora, g):
        cols = {x: [rows[y][x] for y in range(y0, y1 + 1)] for x in xs}
        if any("W" in c for c in cols.values()):
            for x, c in cols.items():
                for i, ch in enumerate(reversed(c)):
                    rows[y0 + i][x] = ch
        else:
            for x in xs:
                _por(rows, x, y0 - 1, rows[y0][x])
                rows[y1][x] = "G"
    return _mudar_olhos(grid, f)


def espelhar(grid):
    return [r[::-1] for r in grid]


def _livres(grid):
    """Linhas lisas do corpo (só contorno e corpo), fora do topo e das 2 de baixo, do meio para fora."""
    nao_vazias = [y for y, r in enumerate(grid) if not _vazia(r)]
    if not nao_vazias:
        return []
    topo, base = nao_vazias[0], nao_vazias[-1]
    cand = [y for y in range(topo + 1, base - 1) if set(grid[y]) <= set(".KGLD")]
    meio = (topo + base) / 2
    return sorted(cand, key=lambda y: abs(y - meio))


def achatar(grid, n):
    """Tira n linhas lisas do corpo; a base fica onde estava (mesma altura de grade)."""
    rows = list(grid)
    for _ in range(n):
        c = _livres(rows)
        if not c:
            break
        del rows[c[0]]
        rows.insert(0, "." * len(grid[0]))
    return rows


def subir(grid, n, teto=None):
    """Sobe o desenho n px (linhas vazias embaixo). Sem `teto` a grade cresce (o pivô fica na base);
    com `teto` (folha de 16 px) usa o espaço vazio de cima e, se faltar, achata o corpo."""
    w = len(grid[0])
    rows = list(grid) + ["." * w] * n
    if teto:
        while len(rows) > teto and _vazia(rows[0]):
            rows.pop(0)
        falta = len(rows) - teto
        if falta > 0:
            rows = achatar(rows[:-n], falta)[falta:] + ["." * w] * n
    return rows


def sobrepor(grid, sprite, x, y):
    """Desenha `sprite` (grade com '.' transparente) com o canto em (x, y); o que sair da grade é cortado."""
    rows = [list(r) for r in grid]
    for dy, r in enumerate(sprite):
        for dx, ch in enumerate(r):
            if ch != ".":
                _por(rows, x + dx, y + dy, ch)
    return ["".join(r) for r in rows]


MAO = [".K.", "KLK", "KGK"]
Z = ["TTT", ".T.", "TTT"]
GOTA = ["T", "T"]


def estados(base, mao, bolha, teto=None):
    """Os 9 estados (4 quadros cada) a partir da grade base.
    `mao` = (x, y) da mãozinha do aceno; `bolha` = (x, y) do "z" e das gotas de pensamento."""
    s = lambda g, n: subir(g, n, teto)
    mx, my = mao
    bx, by = bolha
    lagrima = _olhos(base)[0]
    lx, ly = min(lagrima), max(max(v) for v in lagrima.values()) + 1
    run = [s(base, 1), achatar(base, 1), s(base, 2), base]
    pensa = olhar_cima(base)
    return {
        "idle": [base, base, achatar(base, 1), s(base, 1)],
        "run_r": run,
        "run_l": [espelhar(g) for g in run],
        "waving": [sobrepor(feliz(base), MAO, mx, my), sobrepor(feliz(s(base, 1)), MAO, mx + 1, my - 1),
                   sobrepor(feliz(base), MAO, mx, my), sobrepor(feliz(s(base, 1)), MAO, mx + 1, my - 1)],
        "jumping": [achatar(base, 2), s(base, 2), s(base, 4), s(base, 1)],
        "failed": [sobrepor(triste(base), GOTA, lx, ly), sobrepor(triste(achatar(base, 1)), GOTA, lx, ly + 2),
                   triste(achatar(base, 2)), triste(achatar(base, 3))],
        "waiting": [fechar(base), sobrepor(fechar(base), Z, bx, by + 2),
                    sobrepor(fechar(achatar(base, 1)), Z, bx + 1, by + 1), sobrepor(fechar(base), Z, bx + 1, by)],
        "running": [bravo(base), bravo(achatar(base, 1)), bravo(s(base, 1)), bravo(s(base, 2))],
        "review": [pensa, sobrepor(pensa, ["T"], bx, by + 3), sobrepor(pensa, ["T.", ".T"], bx, by + 2),
                   sobrepor(pensa, [".TT", ".TT", "T.."], bx, by + 1)],
    }


# âncoras (mão, bolha) de cada estágio do Slime
_ANCORAS_SLIME = {"Gotinha": ((11, 8), (12, 3)), "Slime": ((13, 5), (13, 0)),
                  "Slime Cavaleiro": ((13, 5), (12, 0)), "Rei Slime": ((13, 4), (13, 0))}
GRADES_SLIME = {"Gotinha": SLIME_GOTINHA, "Slime": SLIME, "Slime Cavaleiro": SLIME_CAVALEIRO, "Rei Slime": REI_SLIME}


def estados_slime(titulo):
    return estados(GRADES_SLIME[titulo], *_ANCORAS_SLIME[titulo])
