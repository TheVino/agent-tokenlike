import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import masmorra as M

run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
st = M.stats(run)
assert st["spd"] == 10 and st["crit"] == 0.05 and st["critdmg"] == 1.5 and st["area"] is False
assert st["queimar"] == 0 and st["congelar"] == 0
assert M.new_run("x", {"spd": 14}, 2)["base"]["spd"] == 14
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0}}
M.migrate_run(old); assert old["base"]["spd"] == 10 and M.stats(old)["spd"] == 10
M.ITEMS["_t"] = {"name": "t", "fx": {"crit": 0.9, "queimar": 0.9, "spd": -50, "area": True},
                 "rarities": ["comum"], "consume": {"heal": 1}, "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
run["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
st = M.stats(run)
assert st["crit"] == M.MAX_CRIT and st["queimar"] == M.MAX_ELEM_CHANCE and st["spd"] == 1 and st["area"] is True
del M.ITEMS["_t"]
bat = next(m for m in M.MONSTERS if m[0] == "morcego"); ske = next(m for m in M.MONSTERS if m[0] == "esqueleto")
assert M.make_foe(bat, 5)["spd"] > M.make_foe(ske, 5)["spd"]
assert M.make_foe(bat, 5)["element"] is None and M.make_foe(bat, 5, boss=True)["element"] == "raio"
# mult é aplicado ANTES do arredondamento (um round só)
assert M.make_foe(bat, 5, mult=0.5)["hp"] == max(1, round((M.MON_HP[0] + M.MON_HP[1] * 5) * bat[2] * 0.5))
assert M.make_mimic(3)["element"] is None and M.make_mimic(3)["hp"] == M.make_mimic(3)["hp_max"]
print("ok: combate")
