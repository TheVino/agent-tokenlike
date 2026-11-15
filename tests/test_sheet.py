import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sheet as F


def synthetic_sheet(lines, h=10, gap=3, noises=()):
    """lines: list of lists of widths. Returns (w, total_h, opaque)."""
    px, y = set(), 1
    for widths in lines:
        x = 1
        for lg in widths:
            px |= {(i, j) for i in range(x, x + lg) for j in range(y, y + h)}
            x += lg + gap
        y += h + gap
    px |= set(noises)
    w = max((p[0] for p in px), default=0) + 2
    return w, y, (lambda x, y: (x, y) in px)


assert F.STATES == ("idle", "run_r", "run_l", "waving", "jumping", "failed", "waiting", "running", "review")

# 9 rows, 4 to 8 frames of different widths
cont = [4, 5, 6, 7, 8, 4, 5, 6, 7]
w, h, op = synthetic_sheet([[6 + (i % 3) * 2 for i in range(n)] for n in cont])
r = F.cut(w, h, op)
assert [len(l) for l in r] == cont, [len(l) for l in r]
assert F.shared_box([c for l in r for c in l]) == (10, 10)

# empty row -> []
w, h = 30, 40
px = {(x, y) for x in range(2, 8) for y in range(2, 8)} | {(x, y) for x in range(2, 8) for y in range(26, 32)}
r = F.cut(w, h, lambda x, y: (x, y) in px)
assert [len(l) for l in r] == [1, 1], r  # an empty strip does not show up in the automatic cut
r = F.cut(w, h, lambda x, y: (x, y) in px, grid=(1, 3))
assert [len(l) for l in r] == [1, 0, 1], r

# 1 and 2 px islands ignored (they do not become frames or stretch the box)
w, h, op = synthetic_sheet([[6, 6, 6]], noises=[(50, 1), (40, 3), (41, 3), (20, 12)])
r = F.cut(w + 30, h + 5, op)
assert len(r) == 1 and len(r[0]) == 3, r
assert all(c[0] >= 1 and c[1] >= 1 for c in r[0]), r

# a stray hand (2 islands of 2 px) next to the frame does not split it
w, h, op0 = synthetic_sheet([[8, 8, 8]])
extra = {(11, 4), (11, 5), (24, 4), (24, 5)}
r = F.cut(w, h, lambda x, y: op0(x, y) or (x, y) in extra)
assert len(r[0]) == 3

# 12 pieces (8 wide frames + 4 crumbs of 3 px) -> 8
larg = [8, 2, 8, 8, 2, 8, 8, 2, 8, 8, 2, 8]
w, h, op = synthetic_sheet([larg], gap=2)
r = F.cut(w, h, op)
assert len(r[0]) == 8, len(r[0])

# 12 equal pieces -> 8 cells of equal width
w, h, op = synthetic_sheet([[4] * 12], gap=2)
r = F.cut(w, h, op)
assert len(r[0]) == 8 and len({c[2] - c[0] for c in r[0]}) <= 2, r[0]

# fixed grid
r = F.cut(16, 18, lambda x, y: True, grid=(8, 9))
assert len(r) == 9 and all(len(l) == 8 for l in r) and r[0][0] == (0, 0, 2, 2) and r[8][7] == (14, 16, 16, 18)

assert F.detect_grid(1536, 1872) == (8, 9)
assert F.detect_grid(1536, 2288) == (8, 11)
assert F.detect_grid(1000, 300) is None
assert F.detect_grid(1536, 900) is None  # 192x100 cells: nothing square

assert F.reduction_factor(208) == 5 and F.reduction_factor(64) == 2 and F.reduction_factor(16) == 1
assert F.reduction_factor(48) == 1 and F.reduction_factor(49) == 2

# PNG decoder: every filter and every 8-bit color type
import random, tempfile
from _png import write_png
tmp = Path(tempfile.mkdtemp())
rnd = random.Random(3)
W, H = 7, 6
rgba = [bytes(rnd.randrange(256) for _ in range(W * 4)) for _ in range(H)]
write_png(tmp / "a.png", W, H, rgba, 6, filters=(0, 1, 2, 3, 4))
assert F.read_png(tmp / "a.png") == (W, H, b"".join(rgba))
rgb = [bytes(rnd.randrange(256) for _ in range(W * 3)) for _ in range(H)]
write_png(tmp / "b.png", W, H, rgb, 2, filters=(4, 3, 2, 1, 0))
_, _, d = F.read_png(tmp / "b.png")
assert d[0:4] == rgb[0][0:3] + bytes([255]) and d[-4:] == rgb[-1][-3:] + bytes([255])
write_png(tmp / "c.png", 2, 1, [bytes([9, 200, 7, 50])], 4)          # grey + alpha
assert F.read_png(tmp / "c.png")[2] == bytes([9, 9, 9, 200, 7, 7, 7, 50])
write_png(tmp / "d.png", 3, 1, [bytes([0, 1, 1])], 3, plte=bytes([1, 2, 3, 4, 5, 6]), trns=bytes([0]))
assert F.read_png(tmp / "d.png")[2] == bytes([1, 2, 3, 0, 4, 5, 6, 255, 4, 5, 6, 255])
(tmp / "e.png").write_bytes((tmp / "d.png").read_bytes()[:24] + bytes([16]) + (tmp / "d.png").read_bytes()[25:])
try:
    F.read_png(tmp / "e.png"); assert False
except ValueError as e:
    assert "formato de PNG não suportado" in str(e)

# ---- heroes.assemble + make_sheet 32 px
import types
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from heroes import assemble
import make_sheets as GF


def falso(extra=None, anc=(5, 6)):
    q = ["." * 32 for _ in range(32)]
    q[10] = "." * 4 + "A" * 6 + "." * 22          # asymmetric, so the mirror matters
    q[31] = "A" + "." * 31
    return types.SimpleNamespace(
        PAL={"A": "#ff0000", "X": "#00ff00"},
        FRAMES={e: [q, q, q, q] for e in assemble.DRAWN},
        STAGES=[{"title": "a", "floor": 0, "extra": None}, {"title": "b", "floor": 3, "extra": extra},
                  {"title": "c", "floor": 6, "extra": extra}],
        ANCHOR={e: [anc] * 4 for e in assemble.DRAWN})


h = falso()
est = assemble.states(h, 0)
assert tuple(est) == F.STATES
assert all(est["run_l"][i] == [l[::-1] for l in est["run_r"][i]] for i in range(4))

h = falso(["X"])
est = assemble.states(h, 1)
for e, qs in est.items():
    for q in qs:
        assert q[6][31 - 5 if e == "run_l" else 5] == "X", e

h = falso(["XX", "XX"], anc=(31, -1))
est = assemble.states(h, 1)
assert all(len(q) == 32 and all(len(l) == 32 for l in q) for qs in est.values() for q in qs)
assert est["idle"][0][0][31] == "X"

assemble.validate(falso())
for bad in (lambda h: h.FRAMES["idle"].__setitem__(0, h.FRAMES["idle"][0][:31]),
             lambda h: h.FRAMES["idle"].__setitem__(0, ["." * 32] * 32),
             lambda h: h.FRAMES.pop("review"),
             lambda h: h.FRAMES.__setitem__("idle", h.FRAMES["idle"][:3]),
             lambda h: h.FRAMES.__setitem__("idle", h.FRAMES["idle"] * 2),
             lambda h: h.STAGES.pop(),
             lambda h: h.STAGES[0].__setitem__("extra", ["X"]),
             lambda h: h.ANCHOR.__setitem__("idle", [(1.5, 2)] * 4)):
    h = falso(); h.FRAMES = {k: list(v) for k, v in h.FRAMES.items()}
    bad(h)
    try:
        assemble.validate(h); assert False, "validar aceitou"
    except AssertionError as e:
        assert "validar aceitou" not in str(e), e
for n in (5, 6):
    h = falso(); h.FRAMES["idle"] = h.FRAMES["idle"][:1] * n; h.ANCHOR["idle"] = [(0, 0)] * n
    assemble.validate(h)

# a 32 px sheet with 5 frames per state reads back (40 px cells)
import tokenlike
h = falso(); h.FRAMES = {e: [h.FRAMES[e][0]] * 5 for e in h.FRAMES}; h.ANCHOR = {e: [(0, 0)] * 5 for e in h.ANCHOR}
est = assemble.states(h, 0)
GF.make_sheet(tmp / "f32.png", est, h.PAL)
assert F.read_png(tmp / "f32.png")[:2] == (320, 360)
lines, n, maps = tokenlike.read_sheet(tmp / "f32.png")
assert len(lines) == 9 and all(len(l) == 5 for l in lines), [len(l) for l in lines]
assert all(maps[c] for l in lines for c in l)
assert n == 1 and max(c[3] - c[1] for l in lines for c in l) <= 32

# Ghost 32 px: the 3 sheets exist, 9 states with >= 4 frames and trimmed height > 16
REPO_ROOT = Path(__file__).resolve().parent.parent
for i in (1, 2, 3):
    lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "fantasma" / f"folha{i}.png")
    assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
    assert max(c[3] - c[1] for l in lines for c in l) > 16, i


def extra_inside(mod, slack=0):
    """Every pixel of each stage's `extra` falls inside the frame (with `slack` px of margin), in every frame."""
    for s in mod.STAGES[1:]:
        ex = s["extra"]
        for e, ancs in mod.ANCHOR.items():
            for j, (ax, ay) in enumerate(ancs):
                for dy, lin in enumerate(ex):
                    for dx, ch in enumerate(lin):
                        if ch != ".":
                            x, y = ax + dx, ay + dy
                            assert slack <= x < 32 - slack and slack <= y < 32 - slack, (s["title"], e, j, x, y)


import heroes.fantasma as _fa
extra_inside(_fa, slack=1)   # hat with real slack even at the top of the jump
for i in range(3):
    ult = assemble.states(_fa, i)["failed"][-1]
    assert sum(ch != "." for l in ult for ch in l) >= 40, i

# Plague Doctor (batch 1): validate, sheets, loader, add-on in every frame, visible failed
def test_heroi_medico():
    import heroes.medico as med
    assemble.validate(med)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "medico" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["medico"]
    assert c.trait == {"envenenar": 0.10} and c.unlock == "veneno1", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    base = assemble.states(med, 0)
    for i in (1, 2):
        est = assemble.states(med, i)
        for e, qs in est.items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = assemble.states(med, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_medico()


def test_heroi_bruxa():
    import heroes.bruxa as bx
    assemble.validate(bx)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "bruxa" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["bruxa"]
    assert c.trait == {"queimar": 0.08, "sorte": 0.2} and c.unlock == "elementos3", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    base = assemble.states(bx, 0)
    for i in (1, 2):
        for e, qs in assemble.states(bx, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = assemble.states(bx, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i
    extra_inside(bx)   # cauldron (and fireflies) whole inside the frame, including in failed


test_heroi_bruxa()


def test_heroi_coveiro():
    import heroes.coveiro as cv
    assemble.validate(cv)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "coveiro" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["coveiro"]
    assert c.trait == {"gold": 0.4} and c.unlock == "ouro300", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    base = assemble.states(cv, 0)
    for i in (1, 2):
        for e, qs in assemble.states(cv, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = assemble.states(cv, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i
    for i in (1, 2):   # lamp lit when standing, unlit in the closed grave
        est = assemble.states(cv, i)
        assert "Y" in "".join(est["idle"][0]) and "Y" in "".join(est["failed"][0]), i
        assert not any("Y" in "".join(q) or "O" in "".join(q) for q in est["failed"][3:]), i


test_heroi_coveiro()

def test_heroi_ceifeirinho():
    import heroes.ceifeirinho as cf
    assemble.validate(cf)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "ceifeirinho" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["ceifeirinho"]
    assert c.trait == {"crit": 0.08} and c.unlock == "horda4", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    assert c.stats["hp"] == 16, c.stats
    base = assemble.states(cf, 0)
    for i in (1, 2):
        for e, qs in assemble.states(cf, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = assemble.states(cf, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_ceifeirinho()


def test_heroi_vela():
    import heroes.vela as vl
    import dungeon
    assemble.validate(vl)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "vela" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["vela"]
    assert c.trait == {"queimar": 0.12, "maxhp": -4} and c.unlock == "queima1", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("vela", {"hp": 20, "atk": 3, "def": 0}, 1, c.trait)
    assert dungeon.stats(run)["maxhp"] == 16
    run["traco"] = {"maxhp": -100}
    assert dungeon.stats(run)["maxhp"] >= 1
    base = assemble.states(vl, 0)
    for i in (1, 2):
        for e, qs in assemble.states(vl, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = assemble.states(vl, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_vela()


def test_heroi_cogumelo():
    import heroes.cogumelo as cg
    import dungeon
    assemble.validate(cg)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "cogumelo" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["cogumelo"]
    assert c.trait == {"cura_sala": 1} and c.unlock == "andar8cheio", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("cogumelo", {"hp": 20, "atk": 3, "def": 0}, 1, c.trait)
    assert dungeon.stats(run)["cura_sala"] == 1
    base = assemble.states(cg, 0)
    for i in (1, 2):
        for e, qs in assemble.states(cg, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    for i in range(3):
        ult = assemble.states(cg, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i
    extra_inside(cg)   # side spores whole, even with the body moving to the left


test_heroi_cogumelo()


def test_heroi_inquisidor():
    import heroes.inquisidor as iq
    import dungeon
    assemble.validate(iq)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "inquisidor" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["inquisidor"]
    assert c.trait == {"def": 1, "espinhos": 0.1} and c.unlock == "andar15", (c.trait, c.unlock)
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("inquisidor", {"hp": 20, "atk": 3, "def": 0}, 1, c.trait)
    st = dungeon.stats(run)
    assert st["def"] == 1 and st["espinhos"] == 0.1, st
    base = assemble.states(iq, 0)
    for i in (1, 2):
        for e, qs in assemble.states(iq, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # the mitre fits whole in the frame even at the top of the jump (anchor never above the top)
    assert all(a[1] >= 0 and 0 <= a[0] <= 32 - len(iq.MITRE_BELL[0]) for qs in iq.ANCHOR.values() for a in qs)
    for i in (1, 2):   # in waiting the waist bell does not cover the book lying beside him
        for j, q in enumerate(assemble.states(iq, i)["waiting"]):
            assert [l[20:31] for l in q[27:32]] == [l[20:31] for l in base["waiting"][j][27:32]], (i, j)
    for i in range(3):
        ult = assemble.states(iq, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_inquisidor()


def test_heroi_boneca():
    import heroes.boneca as bn
    import dungeon
    assemble.validate(bn)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "boneca" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["boneca"]
    assert c.trait == {"dodge": 0.1} and c.unlock == "esquiva10", (c.trait, c.unlock)
    assert "esquiva10" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("boneca", {"hp": 20, "atk": 3, "def": 0}, 1, c.trait)
    assert dungeon.stats(run)["dodge"] >= 0.1, dungeon.stats(run)
    base = assemble.states(bn, 0)
    for i in (1, 2):
        for e, qs in assemble.states(bn, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # bow and needle fit whole in the frame in every frame (including at the top of the jump)
    w, h = len(bn.BOW_NEEDLE[0]), len(bn.BOW_NEEDLE)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in bn.ANCHOR.values() for a in qs)
    for i in range(3):
        ult = assemble.states(bn, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_boneca()


def test_heroi_cavaleiro():
    import heroes.cavaleiro as cv
    import dungeon
    assemble.validate(cv)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "cavaleiro" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["cavaleiro"]
    assert c.trait == {"bloqueio": 1} and c.unlock == "bloqueio10", (c.trait, c.unlock)
    assert "bloqueio10" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    assert c.stats["spd"] == 8, c.stats
    run = dungeon.new_run("cavaleiro", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["spd"] == 8 and st["bloqueio"] == 1, st
    base = assemble.states(cv, 0)
    for i in (1, 2):
        for e, qs in assemble.states(cv, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # plume and banner fit whole in the frame in every frame (including at the top of the jump)
    w, h = len(cv.PLUME_BANNER[0]), len(cv.PLUME_BANNER)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in cv.ANCHOR.values() for a in qs)
    for i in range(3):
        ult = assemble.states(cv, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_cavaleiro()

def test_heroi_corvo():
    import heroes.corvo as co
    import dungeon
    assemble.validate(co)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "corvo" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["corvo"]
    assert c.trait == {"duplo": 0.08} and c.unlock == "chefes3", (c.trait, c.unlock)
    assert "chefes3" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    assert c.stats["spd"] == 12, c.stats
    run = dungeon.new_run("corvo", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["spd"] == 12 and st["duplo"] == 0.08, st
    base = assemble.states(co, 0)
    for i in (1, 2):
        for e, qs in assemble.states(co, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # bag and hood fit whole in the frame in every frame (including at the top of the jump)
    w, h = len(co.BAG_HOOD[0]), len(co.BAG_HOOD)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in co.ANCHOR.values() for a in qs)
    count = lambda q, c: sum(l.count(c) for l in q)
    for i in (1, 2):   # the bag does not cover the stretched wing (review and the 3rd running frame)
        est = assemble.states(co, i)
        for e, j in [("review", k) for k in range(4)] + [("running", 2)]:
            assert count(est[e][j], "A") == count(base[e][j], "A"), (i, e, j)
    assert all(count(q, "N") for qs in base.values() for q in qs)   # bluish shine on the feathers in every frame
    for i in range(3):
        ult = assemble.states(co, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_corvo()

def test_heroi_alquimista():
    import heroes.alquimista as aq
    import dungeon
    assemble.validate(aq)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "alquimista" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["alquimista"]
    assert c.trait == {"desconto": 0.2, "cura_andar": 3} and c.unlock == "consumir10", (c.trait, c.unlock)
    assert "consumir10" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("alquimista", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["desconto"] == 0.2 and st["cura_andar"] == 3, st
    base = assemble.states(aq, 0)
    for i in (1, 2):
        for e, qs in assemble.states(aq, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # belt and goggles fit whole in the frame in every frame (including at the top of the jump)
    w, h = len(aq.BELT_GOGGLES[0]), len(aq.BELT_GOGGLES)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in aq.ANCHOR.values() for a in qs)
    for e, ancs in aq.ANCHOR.items():   # the goggles stay inside the crown: they do not cover the hat's outline
        for j, (ax, ay) in enumerate(ancs):
            for dy, lin in enumerate(aq.BELT_GOGGLES[:8]):
                for dx, ch in enumerate(lin):
                    if ch != ".":
                        assert base[e][j][ay + dy][ax + dx] != "K", (e, j, dx, dy)
    for i in range(3):
        ult = assemble.states(aq, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_alquimista()

def test_heroi_freira():
    import heroes.freira as fr
    import dungeon
    assemble.validate(fr)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "freira" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["freira"]
    assert c.trait == {"lifesteal": 1, "congelar": 0.06} and c.unlock == "morrer10", (c.trait, c.unlock)
    assert "morrer10" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("freira", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["lifesteal"] == 1 and st["congelar"] == 0.06, st
    base = assemble.states(fr, 0)
    for i in (1, 2):
        for e, qs in assemble.states(fr, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    # cord and embers fit whole in the frame in every frame (including at the top of the jump and on the little mound)
    w, h = len(fr.CORD_EMBERS[0]), len(fr.CORD_EMBERS)
    assert all(0 <= a[0] <= 32 - w and 0 <= a[1] <= 32 - h for qs in fr.ANCHOR.values() for a in qs)
    for i in range(3):
        ult = assemble.states(fr, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_freira()

def test_heroi_espantalho():
    import heroes.espantalho as es
    import dungeon
    assemble.validate(es)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "espantalho" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["espantalho"]
    assert c.trait == {"ajudante": 1} and c.unlock == "ajudantes3", (c.trait, c.unlock)
    assert "ajudantes3" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("espantalho", c.stats, 1, c.trait)
    assert dungeon.stats(run)["ajudante"] == 1
    base = assemble.states(es, 0)
    for i in (1, 2):
        for e, qs in assemble.states(es, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    extra_inside(es)   # little crow and lantern fit whole, including at the top of the jump and on the straw pile
    for i in range(3):
        ult = assemble.states(es, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_espantalho()

def test_heroi_golem():
    import heroes.golem as go
    import dungeon
    assemble.validate(go)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "golem" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["golem"]
    assert c.trait == {"def": 1, "maxhp": 3} and c.unlock == "sem_consumir10", (c.trait, c.unlock)
    assert "sem_consumir10" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("golem", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["spd"] == 8 and st["maxhp"] == 23 and st["def"] == 1, st
    base = assemble.states(go, 0)
    for i in (1, 2):
        for e, qs in assemble.states(go, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    extra_inside(go)   # flower, nest and mushrooms fit whole, including at the top of the jump and on the stone pile
    for i in range(3):
        ult = assemble.states(go, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_golem()

def test_heroi_mariposa():
    import heroes.mariposa as ma
    import dungeon
    assemble.validate(ma)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "mariposa" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["mariposa"]
    assert c.trait == {"dodge": 0.05, "eletrizar": 0.06} and c.unlock == "lendarios3", (c.trait, c.unlock)
    assert "lendarios3" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("mariposa", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["eletrizar"] == 0.06 and st["dodge"] >= 0.05, st
    base = assemble.states(ma, 0)
    for i in (1, 2):
        for e, qs in assemble.states(ma, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    extra_inside(ma)   # antennae and moon fit whole, including at the top of the jump and fallen on the ground (wings: assert in frame())
    for i in range(3):
        ult = assemble.states(ma, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_mariposa()

def test_heroi_sapo():
    import heroes.sapo as sa
    import dungeon
    assemble.validate(sa)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "sapo" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["sapo"]
    assert c.trait == {"envenenar": 0.06, "cura_sala": 1} and c.unlock == "veneno3", (c.trait, c.unlock)
    assert "veneno3" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("sapo", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["envenenar"] == 0.06 and st["cura_sala"] >= 1, st
    base = assemble.states(sa, 0)
    for i in (1, 2):
        for e, qs in assemble.states(sa, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    extra_inside(sa)   # necklace and headdress fit whole, including at the top of the jump and sunk in the puddle
    for i in range(3):
        ult = assemble.states(sa, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_sapo()


def test_heroi_gato():
    import heroes.gato as ga
    import dungeon
    assemble.validate(ga)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "gato" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["gato"]
    assert c.trait == {"sorte": 0.3, "crit": 0.05} and c.unlock == "andar13", (c.trait, c.unlock)
    assert "andar13" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("gato", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["sorte"] == 0.3 and st["crit"] >= 0.05, st
    base = assemble.states(ga, 0)
    for i in (1, 2):
        for e, qs in assemble.states(ga, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    extra_inside(ga)   # scarf and little candles fit whole, including at the top of the jump and curled on the ground
    for i in range(3):
        ult = assemble.states(ga, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_gato()

def test_heroi_polvo():
    import heroes.polvo as po
    import dungeon
    assemble.validate(po)
    for i in (1, 2, 3):
        lines, n, maps = tokenlike.read_sheet(REPO_ROOT / "characters" / "polvo" / f"folha{i}.png")
        assert len(lines) == 9 and all(len(l) >= 4 for l in lines), (i, [len(l) for l in lines])
        assert max(c[3] - c[1] for l in lines for c in l) > 16, i
    c = {c.key: c for c in tokenlike.load_png_characters()}["polvo"]
    assert c.trait == {"duplo": 0.06, "congelar": 0.04} and c.unlock == "chefes3run", (c.trait, c.unlock)
    assert "chefes3run" in dungeon.ACHIEVEMENTS
    assert [s["floor"] for s in c.stages] == [1, 4, 10]
    run = dungeon.new_run("polvo", c.stats, 1, c.trait)
    st = dungeon.stats(run)
    assert st["duplo"] == 0.06 and st["congelar"] == 0.04, st
    base = assemble.states(po, 0)
    for i in (1, 2):
        for e, qs in assemble.states(po, i).items():
            for j, q in enumerate(qs):
                assert q != base[e][j], (i, e, j)
    extra_inside(po)   # bucket and anchor fit whole, including at the top of the jump and inside the bucket
    for i in range(3):
        ult = assemble.states(po, i)["failed"][-1]
        assert sum(ch != "." for l in ult for ch in l) >= 40, i


test_heroi_polvo()

print("test_folha ok")
