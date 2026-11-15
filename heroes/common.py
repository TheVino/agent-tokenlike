"""Pieces shared by the 32 px heroes: "z", "?", "!", tear (colors K, T, Y) and sprite stamping on a grid."""

N = 32
Z_S = ["KKKKK", "KTTTK", "KKKTK", "KKTKK", "KTKKK", "KTTTK", "KKKKK"]
Z_L = ["KKKKKK", "KTTTTK", "KKKKTK", "KKKTKK", "KKTKKK", "KTKKKK", "KTTTTK", "KKKKKK"]
QMARK_S = [".KKK.", "KTTTK", "KKKTK", "..KKK", "..KTK", "..KKK"]
QMARK = [".KKKK.", "KTTTTK", "KTKKTK", "KKKKTK", "..KTTK", "..KTK.", "..KKK.", "..KTK.", "..KKK."]
EXCLAM = ["KKK", "KYK", "KYK", "KYK", "KKK", "KYK", "KKK"]
TEAR = ["T", "T"]


def mirror(s):
    return [l[::-1] for l in s]


def stamp(g, s, x, y):
    """Stamps sprite `s` on grid `g` at (x, y); '.' is transparent and whatever leaves the grid is cut off."""
    for dy, lin in enumerate(s):
        for dx, ch in enumerate(lin):
            if ch != "." and 0 <= x + dx < N and 0 <= y + dy < N:
                g[y + dy][x + dx] = ch


def line(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(n + 1)]


def outline_cells(g, px):
    for (x, y) in px:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in px and 0 <= nx < N and 0 <= ny < N:
                g[ny][nx] = "K"
    for (x, y), c in px.items():
        if 0 <= x < N and 0 <= y < N:
            g[y][x] = c


def trait(g, a, b, color):
    px = {}
    for x, y in line(*a, *b):
        px[(x, y)] = color
    outline_cells(g, px)
