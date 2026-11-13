"""Peças comuns aos heróis 32 px: "z", "?", "!", lágrima (cores K, T, Y) e o carimbo de sprite numa grade."""

N = 32
Z_P = ["KKKKK", "KTTTK", "KKKTK", "KKTKK", "KTKKK", "KTTTK", "KKKKK"]
Z_G = ["KKKKKK", "KTTTTK", "KKKKTK", "KKKTKK", "KKTKKK", "KTKKKK", "KTTTTK", "KKKKKK"]
INTERROG_P = [".KKK.", "KTTTK", "KKKTK", "..KKK", "..KTK", "..KKK"]
INTERROG = [".KKKK.", "KTTTTK", "KTKKTK", "KKKKTK", "..KTTK", "..KTK.", "..KKK.", "..KTK.", "..KKK."]
EXCLAM = ["KKK", "KYK", "KYK", "KYK", "KKK", "KYK", "KKK"]
LAGRIMA = ["T", "T"]


def espelho(s):
    return [l[::-1] for l in s]


def carimbar(g, s, x, y):
    """Carimba o sprite `s` na grade `g` em (x, y); '.' é transparente e o que sai da grade é cortado."""
    for dy, lin in enumerate(s):
        for dx, ch in enumerate(lin):
            if ch != "." and 0 <= x + dx < N and 0 <= y + dy < N:
                g[y + dy][x + dx] = ch


def linha(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)]


def contornar(g, px):
    for (x, y) in px:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in px and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for (x, y), c in px.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c


def traco(g, a, b, cor):
    px = {}
    for x, y in linha(*a, *b):
        px[(x, y)] = cor
    contornar(g, px)
