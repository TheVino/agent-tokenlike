import sys, random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import masmorra as M

assert M.item_fx("adaga", "raro")["atk"] == 3 and M.item_fx("adaga", "lendario")["atk"] == 6
assert M.item_fx("foice", "epico")["maxhp"] == -4                     # negativo não escala
assert M.item_fx("vela", "lendario")["trap"] == 2.0                    # trap não escala
run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); meta = M.new_meta()
assert run["items"] == [] and run["shield"] == 0 and run["pending"] is None
# empilha e soma
for k in ("adaga", "espada_osso"): M.resolve_offer(run, {"key": k, "rar": "comum"}, "pegar", {"lines": []})
assert M.stats(run)["atk"] == 3 + 2 + 4
# tetos
run2 = M.new_run("slime", {}, 2); run2["items"] = [{"key": "vela", "rar": "lendario"}] * 1
assert M.stats(run2)["energy"] <= 1.0 and 0.25 <= M.stats(run2)["trap"] <= 3
# escudo absorve antes do HP
run["shield"] = 5; hp = run["hp"]; assert M.apply_damage(run, 3) == 0 and run["shield"] == 2 and run["hp"] == hp
assert M.apply_damage(run, 4) == 2 and run["shield"] == 0 and run["hp"] == hp - 2
# regra automática
r = M.new_run("slime", {"hp": 20}, 3); r["hp"] = 7
heal_item = next(k for k, it in M.ITEMS.items() if "heal" in it["consume"])
assert M.auto_choice(r, {"key": heal_item, "rar": "comum"}) == "consumir"
r["hp"] = 20; assert M.auto_choice(r, {"key": heal_item, "rar": "comum"}) == "pegar"
# um de cada por run e pool vazio -> None
meta_all = M.new_meta(); meta_all["achievements"] = list(M.ACHIEVEMENTS)
r = M.new_run("slime", {}, 4); r["floor"] = 30; rng = random.Random(1); seen = set()
while (o := M.roll_offer(r, meta_all, rng)) is not None:
    assert o["key"] not in seen and o["rar"] in M.ITEMS[o["key"]]["rarities"]; seen.add(o["key"])
    r["items"].append(o)
assert seen == set(M.ITEMS)
assert M.roll_offer(r, meta_all, rng, best=True) is None
# chefe: raro+ quando existe
r = M.new_run("slime", {}, 5)
assert all(M.roll_offer(r, meta_all, random.Random(s), best=True)["rar"] != "comum" for s in range(50))
# pendência: consumir escudo e pegar pelo jogador; resolve_pending usa a regra automática
r = M.new_run("slime", {"hp": 20}, 7)
r["pending"] = {"key": "tampa", "rar": "raro", "source": "chest"}
ev = M.choose_pending(r, meta, "consumir")
assert r["pending"] is None and r["shield"] == 8 and ev["consumed"] == {"key": "tampa", "rar": "raro", "shield": 8}
r["pending"] = {"key": "adaga", "rar": "comum", "source": "chest"}
ev = M.resolve_pending(r, meta)
assert r["pending"] is None and ev["item"] == {"key": "adaga", "rar": "comum"} and r["items"][-1]["key"] == "adaga"
# modo interativo cria pendência; enter_room não entra com pendência (responsabilidade da GUI) mas resolve_pending funciona
# migração de save antigo
old = {"items": {"mao": "adaga", "escudo": None, "cabeca": "chapeu"}, "hp": 10}
M.migrate_run(old); assert old["items"] == [{"key": "adaga", "rar": "comum"}, {"key": "chapeu", "rar": "comum"}]
assert old["shield"] == 0 and old["pending"] is None
# colecionador
r = M.new_run("slime", {}, 6); r["items"] = [{"key": k, "rar": "comum"} for k in list(M.ITEMS)[:10]]
ev = {"lines": []}; M._check_achievements(r, meta, ev); assert "colecionador" in meta["achievements"]
# muitas salas nos dois modos, sem exceção; pendência resolvida antes de cada sala
for mode in ("auto", "interativo"):
    rng = random.Random(7); meta = M.new_meta(); run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
    pendings = 0
    for _ in range(400):
        if run["dead"]: run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
        if run["pending"]: M.resolve_pending(run, meta)
        run["energy"] = 1e9; ev = M.enter_room(run, meta, rng, mode=mode)
        if ev.get("pending"): pendings += 1; assert run["pending"]["key"] == ev["pending"]["key"]
        assert len({i["key"] for i in run["items"]}) == len(run["items"])
    assert (pendings > 0) == (mode == "interativo")
# itens novos cobrem todos os tipos de visual
import arte
tipos = {it["look"]["type"] for it in M.ITEMS.values()}
assert {"obj", "espinhos", "gotas", "contorno", "tingir", "adesivo"} <= tipos
assert len(M.ITEMS) >= 20
assert any(it["rarities"] == ["lendario"] for it in M.ITEMS.values())
assert any(it["look"].get("anchor") == "flutua" for it in M.ITEMS.values())
assert all(k in arte.ITEM_ART for k in M.ITEMS)
assert all(it["look"]["art"] in arte.ITEM_ART for it in M.ITEMS.values() if "art" in it["look"])
print("ok: itens")
