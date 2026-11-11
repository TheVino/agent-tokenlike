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
print("ok: visual")
