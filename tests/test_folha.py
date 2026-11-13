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

# decodificador de PNG: todos os filtros e tipos de cor de 8 bits
import random, tempfile
from _png import escrever_png
tmp = Path(tempfile.mkdtemp())
rnd = random.Random(3)
W, H = 7, 6
rgba = [bytes(rnd.randrange(256) for _ in range(W * 4)) for _ in range(H)]
escrever_png(tmp / "a.png", W, H, rgba, 6, filtros=(0, 1, 2, 3, 4))
assert F.ler_png(tmp / "a.png") == (W, H, b"".join(rgba))
rgb = [bytes(rnd.randrange(256) for _ in range(W * 3)) for _ in range(H)]
escrever_png(tmp / "b.png", W, H, rgb, 2, filtros=(4, 3, 2, 1, 0))
_, _, d = F.ler_png(tmp / "b.png")
assert d[0:4] == rgb[0][0:3] + bytes([255]) and d[-4:] == rgb[-1][-3:] + bytes([255])
escrever_png(tmp / "c.png", 2, 1, [bytes([9, 200, 7, 50])], 4)          # cinza + alfa
assert F.ler_png(tmp / "c.png")[2] == bytes([9, 9, 9, 200, 7, 7, 7, 50])
escrever_png(tmp / "d.png", 3, 1, [bytes([0, 1, 1])], 3, plte=bytes([1, 2, 3, 4, 5, 6]), trns=bytes([0]))
assert F.ler_png(tmp / "d.png")[2] == bytes([1, 2, 3, 0, 4, 5, 6, 255, 4, 5, 6, 255])
(tmp / "e.png").write_bytes((tmp / "d.png").read_bytes()[:24] + bytes([16]) + (tmp / "d.png").read_bytes()[25:])
try:
    F.ler_png(tmp / "e.png"); assert False
except ValueError as e:
    assert "formato de PNG não suportado" in str(e)

# ---- herois.montar + gerar_folha 32 px
import types
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from herois import montar
import gerar_folhas as GF


def falso(extra=None, anc=(5, 6)):
    q = ["." * 32 for _ in range(32)]
    q[10] = "." * 4 + "A" * 6 + "." * 22          # assimétrico, para o espelho valer
    q[31] = "A" + "." * 31
    return types.SimpleNamespace(
        PAL={"A": "#ff0000", "X": "#00ff00"},
        QUADROS={e: [q, q, q, q] for e in montar.DESENHADOS},
        ESTAGIOS=[{"title": "a", "floor": 0, "extra": None}, {"title": "b", "floor": 3, "extra": extra},
                  {"title": "c", "floor": 6, "extra": extra}],
        ANCORA={e: [anc] * 4 for e in montar.DESENHADOS})


h = falso()
est = montar.estados(h, 0)
assert tuple(est) == F.ESTADOS
assert all(est["run_l"][i] == [l[::-1] for l in est["run_r"][i]] for i in range(4))

h = falso(["X"])
est = montar.estados(h, 1)
for e, qs in est.items():
    for q in qs:
        assert q[6][31 - 5 if e == "run_l" else 5] == "X", e

h = falso(["XX", "XX"], anc=(31, -1))
est = montar.estados(h, 1)
assert all(len(q) == 32 and all(len(l) == 32 for l in q) for qs in est.values() for q in qs)
assert est["idle"][0][0][31] == "X"

montar.validar(falso())
for ruim in (lambda h: h.QUADROS["idle"].__setitem__(0, h.QUADROS["idle"][0][:31]),
             lambda h: h.QUADROS["idle"].__setitem__(0, ["." * 32] * 32),
             lambda h: h.QUADROS.pop("review"),
             lambda h: h.QUADROS.__setitem__("idle", h.QUADROS["idle"][:3]),
             lambda h: h.QUADROS.__setitem__("idle", h.QUADROS["idle"] * 2),
             lambda h: h.ESTAGIOS.pop(),
             lambda h: h.ESTAGIOS[0].__setitem__("extra", ["X"]),
             lambda h: h.ANCORA.__setitem__("idle", [(1.5, 2)] * 4)):
    h = falso(); h.QUADROS = {k: list(v) for k, v in h.QUADROS.items()}
    ruim(h)
    try:
        montar.validar(h); assert False, "validar aceitou"
    except AssertionError as e:
        assert "validar aceitou" not in str(e), e
for n in (5, 6):
    h = falso(); h.QUADROS["idle"] = h.QUADROS["idle"][:1] * n; h.ANCORA["idle"] = [(0, 0)] * n
    montar.validar(h)

# folha 32 px com 5 quadros por estado lê de volta (células de 40 px)
import tokenlike
h = falso(); h.QUADROS = {e: [h.QUADROS[e][0]] * 5 for e in h.QUADROS}; h.ANCORA = {e: [(0, 0)] * 5 for e in h.ANCORA}
est = montar.estados(h, 0)
GF.gerar_folha(tmp / "f32.png", est, h.PAL)
assert F.ler_png(tmp / "f32.png")[:2] == (320, 360)
linhas, n, mapas = tokenlike.ler_folha(tmp / "f32.png")
assert len(linhas) == 9 and all(len(l) == 5 for l in linhas), [len(l) for l in linhas]
assert all(mapas[c] for l in linhas for c in l)
assert n == 1 and max(c[3] - c[1] for l in linhas for c in l) <= 32

print("test_folha ok")
