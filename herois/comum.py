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
