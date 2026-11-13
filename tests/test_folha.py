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

# Fantasma 32 px: as 3 folhas existem, 9 estados com >= 4 quadros e altura aparada > 16
RAIZ = Path(__file__).resolve().parent.parent
for i in (1, 2, 3):
    linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "fantasma" / f"folha{i}.png")
    assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
    assert max(c[3] - c[1] for l in linhas for c in l) > 16, i


def extra_dentro(mod, folga=0):
    """Todo pixel do `extra` de cada estágio cai dentro do quadro (com `folga` px de margem), em todo quadro."""
    for s in mod.ESTAGIOS[1:]:
        ex = s["extra"]
        for e, ancs in mod.ANCORA.items():
            for j, (ax, ay) in enumerate(ancs):
                for dy, lin in enumerate(ex):
                    for dx, ch in enumerate(lin):
                        if ch != ".":
                            x, y = ax + dx, ay + dy
                            assert folga <= x < 32 - folga and folga <= y < 32 - folga, (s["title"], e, j, x, y)


import herois.fantasma as _fa
extra_dentro(_fa, folga=1)   # chapéu com folga real até no alto do pulo
for i in range(3):
    ult = montar.estados(_fa, i)["failed"][-1]
    assert sum(ch != "." for l in ult for ch in l) >= 40, i

# Médico da Peste (leva 1): validar, folhas, carregador, acréscimo em todo quadro, failed visível
def test_heroi_medico():
    import herois.medico as med
    montar.validar(med)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "medico" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["medico"]
    assert c.traco == {"envenenar": 0.10} and c.unlock == "veneno1", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    base = montar.estados(med, 0)
    for i in (1, 2):
        est = montar.estados(med, i)
        for e, qs in est.items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = montar.estados(med, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_medico()


def test_heroi_bruxa():
    import herois.bruxa as bx
    montar.validar(bx)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "bruxa" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["bruxa"]
    assert c.traco == {"queimar": 0.08, "sorte": 0.2} and c.unlock == "elementos3", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    base = montar.estados(bx, 0)
    for i in (1, 2):
        for e, qs in montar.estados(bx, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = montar.estados(bx, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i
    extra_dentro(bx)   # caldeirão (e vagalumes) inteiros no quadro, inclusive no failed


test_heroi_bruxa()


def test_heroi_coveiro():
    import herois.coveiro as cv
    montar.validar(cv)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "coveiro" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["coveiro"]
    assert c.traco == {"gold": 0.4} and c.unlock == "ouro300", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    base = montar.estados(cv, 0)
    for i in (1, 2):
        for e, qs in montar.estados(cv, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = montar.estados(cv, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i
    for i in (1, 2):   # lampião aceso de pé, apagado na cova fechada
        est = montar.estados(cv, i)
        assert "Y" in "".join(est["idle"][0]) and "Y" in "".join(est["failed"][0]), i
        assert not any("Y" in "".join(q) or "O" in "".join(q) for q in est["failed"][3:]), i


test_heroi_coveiro()

def test_heroi_ceifeirinho():
    import herois.ceifeirinho as cf
    montar.validar(cf)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "ceifeirinho" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["ceifeirinho"]
    assert c.traco == {"crit": 0.08} and c.unlock == "horda4", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    assert c.stats["hp"] == 16, c.stats
    base = montar.estados(cf, 0)
    for i in (1, 2):
        for e, qs in montar.estados(cf, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = montar.estados(cf, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_ceifeirinho()


def test_heroi_vela():
    import herois.vela as vl
    import masmorra
    montar.validar(vl)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "vela" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["vela"]
    assert c.traco == {"queimar": 0.12, "maxhp": -4} and c.unlock == "queima1", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = masmorra.new_run("vela", {"hp": 20, "atk": 3, "def": 0}, 1, c.traco)
    assert masmorra.stats(run)["maxhp"] == 16
    run["traco"] = {"maxhp": -100}
    assert masmorra.stats(run)["maxhp"] >= 1
    base = montar.estados(vl, 0)
    for i in (1, 2):
        for e, qs in montar.estados(vl, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = montar.estados(vl, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_vela()


def test_heroi_cogumelo():
    import herois.cogumelo as cg
    import masmorra
    montar.validar(cg)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "cogumelo" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["cogumelo"]
    assert c.traco == {"cura_sala": 1} and c.unlock == "andar8cheio", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = masmorra.new_run("cogumelo", {"hp": 20, "atk": 3, "def": 0}, 1, c.traco)
    assert masmorra.stats(run)["cura_sala"] == 1
    base = montar.estados(cg, 0)
    for i in (1, 2):
        for e, qs in montar.estados(cg, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = montar.estados(cg, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i
    extra_dentro(cg)   # esporos laterais inteiros, mesmo com o corpo indo para a esquerda


test_heroi_cogumelo()


def test_heroi_inquisidor():
    import herois.inquisidor as iq
    import masmorra
    montar.validar(iq)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "inquisidor" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["inquisidor"]
    assert c.traco == {"def": 1, "espinhos": 0.1} and c.unlock == "andar15", (c.traco, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = masmorra.new_run("inquisidor", {"hp": 20, "atk": 3, "def": 0}, 1, c.traco)
    st = masmorra.stats(run)
    assert st["def"] == 1 and st["espinhos"] == 0.1, st
    base = montar.estados(iq, 0)
    for i in (1, 2):
        for e, qs in montar.estados(iq, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # a mitra cabe inteira no quadro mesmo no alto do pulo (âncora nunca acima do topo)
    assert all(a[1] >= 0 and 0 <= a[0] <= 32 - len(iq.MITRA_SINO[0]) for qs in iq.ANCORA.values() for a in qs)
    for i in (1, 2):   # no waiting o sino da cintura não cobre o livro deitado ao lado
        for j, q in enumerate(montar.estados(iq, i)["waiting"]):
            assert [l[20:31] for l in q[27:32]] == [l[20:31] for l in base["waiting"][j][27:32]], (i, j)
    for i in range(3):
        ult = montar.estados(iq, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_inquisidor()


def test_heroi_boneca():
    import herois.boneca as bn
    import masmorra
    montar.validar(bn)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "boneca" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["boneca"]
    assert c.traco == {"dodge": 0.1} and c.unlock == "esquiva10", (c.traco, c.unlock)
    assert "esquiva10" in masmorra.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = masmorra.new_run("boneca", {"hp": 20, "atk": 3, "def": 0}, 1, c.traco)
    assert masmorra.stats(run)["dodge"] >= 0.1, masmorra.stats(run)
    base = montar.estados(bn, 0)
    for i in (1, 2):
        for e, qs in montar.estados(bn, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # laço e agulha cabem inteiros no quadro em todos os quadros (inclusive no alto do pulo)
    w, h = len(bn.LACO_AGULHA[0]), len(bn.LACO_AGULHA)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in bn.ANCORA.values() for a in qs)
    for i in range(3):
        ult = montar.estados(bn, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_boneca()


def test_heroi_cavaleiro():
    import herois.cavaleiro as cv
    import masmorra
    montar.validar(cv)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "cavaleiro" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["cavaleiro"]
    assert c.traco == {"bloqueio": 1} and c.unlock == "bloqueio10", (c.traco, c.unlock)
    assert "bloqueio10" in masmorra.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    assert c.stats["spd"] == 8, c.stats
    run = masmorra.new_run("cavaleiro", c.stats, 1, c.traco)
    st = masmorra.stats(run)
    assert st["spd"] == 8 and st["bloqueio"] == 1, st
    base = montar.estados(cv, 0)
    for i in (1, 2):
        for e, qs in montar.estados(cv, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # pluma e estandarte cabem inteiros no quadro em todos os quadros (inclusive no alto do pulo)
    w, h = len(cv.PLUMA_ESTANDARTE[0]), len(cv.PLUMA_ESTANDARTE)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in cv.ANCORA.values() for a in qs)
    for i in range(3):
        ult = montar.estados(cv, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_cavaleiro()

def test_heroi_corvo():
    import herois.corvo as co
    import masmorra
    montar.validar(co)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "corvo" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["corvo"]
    assert c.traco == {"duplo": 0.08} and c.unlock == "chefes3", (c.traco, c.unlock)
    assert "chefes3" in masmorra.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    assert c.stats["spd"] == 12, c.stats
    run = masmorra.new_run("corvo", c.stats, 1, c.traco)
    st = masmorra.stats(run)
    assert st["spd"] == 12 and st["duplo"] == 0.08, st
    base = montar.estados(co, 0)
    for i in (1, 2):
        for e, qs in montar.estados(co, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # bolsa e capuz cabem inteiros no quadro em todos os quadros (inclusive no alto do pulo)
    w, h = len(co.BOLSA_CAPUZ[0]), len(co.BOLSA_CAPUZ)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in co.ANCORA.values() for a in qs)
    for i in range(3):
        ult = montar.estados(co, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_corvo()

def test_heroi_alquimista():
    import herois.alquimista as aq
    import masmorra
    montar.validar(aq)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "alquimista" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["alquimista"]
    assert c.traco == {"desconto": 0.2, "cura_andar": 3} and c.unlock == "consumir10", (c.traco, c.unlock)
    assert "consumir10" in masmorra.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = masmorra.new_run("alquimista", c.stats, 1, c.traco)
    st = masmorra.stats(run)
    assert st["desconto"] == 0.2 and st["cura_andar"] == 3, st
    base = montar.estados(aq, 0)
    for i in (1, 2):
        for e, qs in montar.estados(aq, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # cinto e óculos cabem inteiros no quadro em todos os quadros (inclusive no alto do pulo)
    w, h = len(aq.CINTO_OCULOS[0]), len(aq.CINTO_OCULOS)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in aq.ANCORA.values() for a in qs)
    for i in range(3):
        ult = montar.estados(aq, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_alquimista()

def test_heroi_freira():
    import herois.freira as fr
    import masmorra
    montar.validar(fr)
    for i in (1, 2, 3):
        linhas, n, mapas = tokenlike.ler_folha(RAIZ / "characters" / "freira" / f"folha{i}.png")
        assert len(linhas) == 9 and all(len(l) >= 4 for l in linhas), (i, [len(l) for l in linhas])
        assert max(c[3] - c[1] for l in linhas for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["freira"]
    assert c.traco == {"lifesteal": 1, "congelar": 0.06} and c.unlock == "morrer10", (c.traco, c.unlock)
    assert "morrer10" in masmorra.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = masmorra.new_run("freira", c.stats, 1, c.traco)
    st = masmorra.stats(run)
    assert st["lifesteal"] == 1 and st["congelar"] == 0.06, st
    base = montar.estados(fr, 0)
    for i in (1, 2):
        for e, qs in montar.estados(fr, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # cordão e brasas cabem inteiros no quadro em todos os quadros (inclusive no alto do pulo e no montinho)
    w, h = len(fr.CORDAO_BRASAS[0]), len(fr.CORDAO_BRASAS)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in fr.ANCORA.values() for a in qs)
    for i in range(3):
        ult = montar.estados(fr, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_freira()

print("test_folha ok")
