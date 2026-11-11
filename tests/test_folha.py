import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import folha as F


def folha_sintetica(linhas, h=10, gap=3, ruidos=()):
    """linhas: lista de listas de larguras. Devolve (w, h_total, opaco)."""
    px, y = set(), 1
    for larguras in linhas:
        x = 1
        for lg in larguras:
            px |= {(i, j) for i in range(x, x + lg) for j in range(y, y + h)}
            x += lg + gap
        y += h + gap
    px |= set(ruidos)
    w = max((p[0] for p in px), default=0) + 2
    return w, y, (lambda x, y: (x, y) in px)


assert F.ESTADOS == ("idle", "run_r", "run_l", "waving", "jumping", "failed", "waiting", "running", "review")

# 9 linhas, 4 a 8 quadros de larguras diferentes
cont = [4, 5, 6, 7, 8, 4, 5, 6, 7]
w, h, op = folha_sintetica([[6 + (i % 3) * 2 for i in range(n)] for n in cont])
r = F.cortar(w, h, op)
assert [len(l) for l in r] == cont, [len(l) for l in r]
assert F.caixa_comum([c for l in r for c in l]) == (10, 10)

# linha vazia -> []
w, h = 30, 40
px = {(x, y) for x in range(2, 8) for y in range(2, 8)} | {(x, y) for x in range(2, 8) for y in range(26, 32)}
r = F.cortar(w, h, lambda x, y: (x, y) in px)
assert [len(l) for l in r] == [1, 1], r  # faixa vazia nao aparece no corte automatico
r = F.cortar(w, h, lambda x, y: (x, y) in px, grade=(1, 3))
assert [len(l) for l in r] == [1, 0, 1], r

# ilhas de 1 e 2 px ignoradas (nao viram quadro nem esticam a caixa)
w, h, op = folha_sintetica([[6, 6, 6]], ruidos=[(50, 1), (40, 3), (41, 3), (20, 12)])
r = F.cortar(w + 30, h + 5, op)
assert len(r) == 1 and len(r[0]) == 3, r
assert all(c[0] >= 1 and c[1] >= 1 for c in r[0]), r

# mao solta (2 ilhas de 2 px) colada ao quadro nao o divide
w, h, op0 = folha_sintetica([[8, 8, 8]])
extra = {(11, 4), (11, 5), (24, 4), (24, 5)}
r = F.cortar(w, h, lambda x, y: op0(x, y) or (x, y) in extra)
assert len(r[0]) == 3

# 12 pedacos (8 quadros largos + 4 migalhas de 3 px) -> 8
larg = [8, 2, 8, 8, 2, 8, 8, 2, 8, 8, 2, 8]
w, h, op = folha_sintetica([larg], gap=2)
r = F.cortar(w, h, op)
assert len(r[0]) == 8, len(r[0])

# 12 pedacos iguais -> 8 celulas de largura igual
w, h, op = folha_sintetica([[4] * 12], gap=2)
r = F.cortar(w, h, op)
assert len(r[0]) == 8 and len({c[2] - c[0] for c in r[0]}) <= 2, r[0]

# grade fixa
r = F.cortar(16, 18, lambda x, y: True, grade=(8, 9))
assert len(r) == 9 and all(len(l) == 8 for l in r) and r[0][0] == (0, 0, 2, 2) and r[8][7] == (14, 16, 16, 18)

assert F.detectar_grade(1536, 1872) == (8, 9)
assert F.detectar_grade(1536, 2288) == (8, 11)
assert F.detectar_grade(1000, 300) is None
assert F.detectar_grade(1536, 900) is None  # celulas 192x100: nada quadrado

assert F.fator_reducao(208) == 5 and F.fator_reducao(64) == 2 and F.fator_reducao(16) == 1
assert F.fator_reducao(48) == 1 and F.fator_reducao(49) == 2

print("test_folha ok")
