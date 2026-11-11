import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("tkinter", __import__("types").ModuleType("tkinter"))
import tokenlike as tp
import arte
import visual as V

slime = V.grid_to_map(tp.SLIME, tp.SLIME_PALETTE)
assert V.bbox(slime) == (1, 3, 15, 16), V.bbox(slime)
assert V.grid_to_map(["A.", ".B"], {"A": "#111111"}) == {(0, 0): "#111111"}  # pula '.' e letra sem cor

# mapa qualquer (PNG da comunidade): retângulo 6x10 com borda escura e cores arbitrárias
outro = {(x, y): ("#1b1b2f" if x in (0, 5) or y in (0, 9) else ("#c0ffee" if (x + y) % 2 else "#ba5e11"))
         for x in range(6) for y in range(10)}

for pm in (slime, outro):
    pm_original = dict(pm)
    x0, y0, x1, y1 = V.bbox(pm)
    e = V.espinhos(pm, "#e2384d"); assert V.bbox(e)[1] < y0 and len(e) > len(pm)
    g = V.gotas(pm, "#4fbf5a"); assert V.bbox(g)[3] > y1
    c = V.contorno(pm, "#ffd23f"); assert all(p in c for p in pm) and len(c) > len(pm)
    assert all(c[p] == "#ffd23f" for p in c if p not in pm)
    t = V.tingir(pm, "#9b6ad6", 0.5); assert t.keys() == pm.keys()
    assert all(t[p] == pm[p] for p in pm if pm[p] == "#1b1b2f")      # contorno escuro intacto
    assert any(t[p] != pm[p] for p in pm)
    assert V.espinhos(pm, "#e2384d", 2) != e                          # nível maior reforça
    assert V.gotas(pm, "#4fbf5a", 2) != g
    assert pm == pm_original                                          # entrada não muda

# objetos no mesmo ponto não se sobrepõem por completo
arte_obj = V.grid_to_map(arte.ITEM_ART["chifres"], arte.PAL)
a = V.objeto(slime, arte_obj, "topo", 0); b = V.objeto(a, arte_obj, "topo", 1)
assert V.bbox(b)[1] < V.bbox(a)[1]
# glow: pixels vizinhos ao objeto na cor da raridade
gl = V.objeto(slime, arte_obj, "dir", 0, glow="#6fd6ff"); assert "#6fd6ff" in gl.values()
# adesivo no centro do mapa
ad = V.adesivo(slime, {(0, 0): "#ff00ff"}, (0.5, 0.5)); assert "#ff00ff" in ad.values()
# todas as âncoras mudam o mapa
for anc in ("topo", "esq", "dir", "frente", "base", "flutua"):
    for o in (0, 5):
        assert V.objeto(slime, arte_obj, anc, o) != slime, anc
# ordem 1 não esconde por completo o objeto de ordem 0
for anc in ("topo", "esq", "dir", "frente", "base", "flutua"):
    o0 = V.objeto(slime, arte_obj, anc, 0); o1 = V.objeto(o0, arte_obj, anc, 1)
    assert o1 != o0 and V.objeto(slime, arte_obj, anc, 1) != o0, anc
    n0 = {p for p in o0 if o0[p] != slime.get(p)}; n1 = {p for p in o1 if o1[p] != o0.get(p)}
    assert n1 and n1 != n0, anc
# compose + crop: caixa máxima respeitada com muitos objetos
looks = [({"type": "obj", "anchor": "topo", "art": "chifres"}, None)] * 12
pm2 = V.crop(V.compose(slime, looks, {"chifres": arte_obj}), V.LOOK_BOX)
bx0, by0, bx1, by1 = V.bbox(pm2)
assert bx0 >= V.LOOK_BOX[0] and by0 >= V.LOOK_BOX[1] and bx1 <= V.LOOK_BOX[2] and by1 <= V.LOOK_BOX[3]
assert V.compose(slime, [], {}) == slime
# compose de mutações
mut = V.compose(slime, [({"type": "espinhos", "color": "#e2384d"}, None),
                        ({"type": "tingir", "color": "#9b6ad6", "amount": 0.3}, None)], {})
assert V.bbox(mut)[1] < V.bbox(slime)[1]
for tipo, fn in (("espinhos", V.espinhos), ("gotas", V.gotas)):
    lk = ({"type": tipo, "color": "#e2384d"}, None)
    assert V.compose(slime, [lk] * 2, {}) == fn(slime, "#e2384d", 2), tipo
# todos os itens de masmorra.ITEMS juntos: o mais novo de cada ponto aparece inteiro dentro de LOOK_BOX
import masmorra as M
arts = {k: V.grid_to_map(g, arte.PAL) for k, g in arte.ITEM_ART.items()}
todos = [(it["look"], None) for it in M.ITEMS.values()]
cheio = V.compose(slime, todos, arts)
dentro = lambda p: V.LOOK_BOX[0] <= p[0] < V.LOOK_BOX[2] and V.LOOK_BOX[1] <= p[1] < V.LOOK_BOX[3]
for anc in {l["anchor"] for l, _ in todos if l["type"] == "obj"}:
    i = max(j for j, (l, _) in enumerate(todos) if l.get("anchor") == anc)
    sem_ele = V.compose(slime, todos[:i] + todos[i + 1:], arts)
    novo = {p for p in cheio if cheio[p] != sem_ele.get(p)}
    assert novo and all(dentro(p) for p in novo), (anc, todos[i][0]["art"], [p for p in novo if not dentro(p)])
# além da capacidade, o mais antigo do ponto some (12 chapéus: só os últimos cabem)
chapeu = ({"type": "obj", "anchor": "topo", "art": "chapeu"}, None)
vela = ({"type": "obj", "anchor": "topo", "art": "vela"}, None)
assert V.compose(slime, [vela] + [chapeu] * 12, arts) == V.compose(slime, [chapeu] * 12, arts)
assert V.compose(slime, [vela], arts) != slime                        # sozinho ele aparece
# poucos itens: nada muda (dois de um ponto que cabem continuam os dois)
adaga = ({"type": "obj", "anchor": "dir", "art": "adaga"}, None)
bx = V.bbox(slime)
assert V.compose(slime, [adaga] * 2, arts) == V._colocar(V._colocar(slime, arts["adaga"], bx, "dir", 0, None),
                                                         arts["adaga"], bx, "dir", 1, None)
# looks elementais animados: 3 quadros diferentes, corpo preservado (geada recolore a borda), puros
for fn in (V.chamas, V.faiscas, V.gotas_veneno, V.geada):
    for pm in (slime, outro):
        copia = dict(pm)
        frames = [fn(pm, 1, f) for f in range(V.FASES)]
        assert len({tuple(sorted(f.items())) for f in frames}) == V.FASES, fn.__name__
        assert all(set(pm) <= set(f) or fn is V.geada for f in frames), fn.__name__
        assert pm == copia, fn.__name__
        assert fn(pm, 2, 0) != fn(pm, 1, 0), fn.__name__
lk = [({"type": "chamas"}, None)]
assert V.tem_animacao(lk) and not V.tem_animacao([({"type": "obj", "anchor": "topo", "art": "chifres"}, None)])
c0, c1 = V.crop(V.compose(slime, lk, {}, fase=0), V.LOOK_BOX), V.crop(V.compose(slime, lk, {}, fase=1), V.LOOK_BOX)
assert c0 != c1 and V.compose(slime, [], {}, fase=2) == slime
# objetos não dependem da fase (caixa de âncora fixa)
_arts = {k: V.grid_to_map(g, arte.PAL) for k, g in arte.ITEM_ART.items()}
_lk = [({"type": "chamas"}, None), ({"type": "gotas_veneno"}, None),
       ({"type": "obj", "anchor": "topo", "art": "chapeu"}, None), ({"type": "obj", "anchor": "base", "art": "adaga"}, None)]
_obj = [l for l in _lk if l[0]["type"] == "obj"]
_sem = V.compose(slime, _obj, _arts)
for f in range(V.FASES):
    _c = V.compose(slime, _lk, _arts, fase=f)
    assert all(_c.get(p) == c for p, c in _sem.items() if p not in slime), f   # objetos nos mesmos pixels e cores
# gotas caem 1 px por fase: o quadro 1 é o 0 deslocado (exceto o retorno ao topo)
_g = [{p for p in V.gotas_veneno(slime, 1, f) if p not in slime} for f in range(3)]
assert _g[0] != _g[1] != _g[2] and any((x, y + 1) in _g[1] for x, y in _g[0])
# R11: item elemental sem look animado ainda mostra o elemento (look derivado, uma vez por elemento)
import masmorra as M
_run = M.new_run("slime", {}, 1)
_run["items"] = [{"key": "tocha", "rar": "comum"}]
_pl = tp.pet_looks(_run)
assert [l["type"] for l, _ in _pl].count("chamas") == 1
assert len({tuple(sorted(V.compose(slime, _pl, _arts, fase=f).items())) for f in range(V.FASES)}) == V.FASES
_run["items"] = [{"key": "brasa", "rar": "comum"}, {"key": "tocha", "rar": "comum"}]
assert [l["type"] for l, _ in tp.pet_looks(_run)].count("chamas") == 1        # brasa já tem chamas: não dobra
_run["items"] = [{"key": "brasa", "rar": "comum"}, {"key": "pelagem_chamuscada", "rar": "raro"}]
assert [l["type"] for l, _ in tp.pet_looks(_run)].count("chamas") == 2        # explícitos mantêm o nível
_run["items"] = []
assert tp.pet_looks(_run) == []
# escala k: k=1 igual; corpo 48x48 com k=3 -> objeto 3x mais largo, mesmo apoio entre fases
assert V.look_box(1) == V.LOOK_BOX and V.look_box(3) == (-24, -30, 72, 60)
_top = [({"type": "obj", "anchor": "topo", "art": "chapeu"}, None)]
assert V.compose(slime, _top, _arts, k=1) == V.compose(slime, _top, _arts)
_big = {(x, y): "#aa5522" for x in range(48) for y in range(48)}
def _larg(m, b):
    x0, _, x1, _ = V.bbox({p: c for p, c in m.items() if p not in b}); return x1 - x0
_w1 = _larg(V.compose(slime, _top, _arts), slime)
_w3 = _larg(V.compose(_big, _top, _arts, k=3), _big)
assert _w3 == 3 * _w1, (_w1, _w3)
_cen = lambda m, b: (lambda bb: (bb[0] + bb[2]) / 2)(V.bbox({p: c for p, c in m.items() if p not in b}))
assert _cen(V.compose(_big, _top, _arts, k=3), _big) == 24 and _cen(V.compose(slime, _top, _arts), slime) == 8
_lk3 = _top + [({"type": "chamas"}, None)]
_s3 = [V.compose(_big, _lk3, _arts, f, 3) for f in range(V.FASES)]
assert all(all(m.get(p) == c for p, c in V.compose(_big, _top, _arts, k=3).items() if p not in _big) for m in _s3)
# brilho do objeto escala com k: anel de 3 px em k=3, 1 px em k=1
_gl = "#ffd700"
for _k, _b in ((1, slime), (3, _big)):
    _o = {p: c for p, c in V.compose(_b, _top, _arts, k=_k).items() if p not in _b}
    _m2 = V.compose(_b, [(_top[0][0], _gl)], _arts, k=_k)
    _ring = {p for p, c in _m2.items() if c == _gl}
    _a = V.bbox({p for p in _o}); _a2 = V.bbox(_ring)
    assert _a2[1] == _a[1] - _k and _a2[0] == _a[0] - _k, (_k, _a, _a2)
# flutua: o k do brilho não pode ser sobrescrito pela posição (ordem>=4 em k=1; ordem 0 em k=3)
for _k, _b, _ord in ((1, slime, 4), (3, _big, 0)):
    _art = V.escalar(_arts["chapeu"], _k)
    _sem = V._colocar(dict(_b), _art, V.bbox(_b), "flutua", _ord, None, _k)
    _com = V._colocar(dict(_b), _art, V.bbox(_b), "flutua", _ord, _gl, _k)
    _nov = {p for p in _com if p not in _sem}
    _ba, _bn = V.bbox({p for p in _sem if p not in _b}), V.bbox(_nov)
    assert _bn[0] == _ba[0] - _k and _bn[3] == _ba[3] + _k, (_k, _ord, _ba, _bn)
print("ok: visual")
