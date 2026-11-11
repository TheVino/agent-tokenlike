import sys, json, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import masmorra as M

run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); run["floor"] = 4
assert run["consumed"] == []
M.resolve_offer(run, {"key": "adaga", "rar": "raro"}, "pegar", {"lines": []})
M.resolve_offer(run, {"key": "tampa", "rar": "comum"}, "consumir", {"lines": []})
assert run["items"] == [{"key": "adaga", "rar": "raro", "floor": 4}]
assert run["consumed"] == [{"key": "tampa", "rar": "comum", "floor": 4}]
old = {"items": [{"key": "adaga", "rar": "comum"}], "hp": 5}
M.migrate_run(old); assert old["items"][0]["floor"] is None and old["consumed"] == []
rec = M.run_record(run, "Rei Rato", False, "auto", ["andar5"])
assert set(rec) == {"run", "char", "floor", "room", "killer", "gave_up", "items", "consumed", "gold",
                    "kills", "bosses", "date", "mode", "version", "achievements"}
assert rec["version"] == M.BALANCE_VERSION and len(M.BALANCE_VERSION) == 8
assert json.loads(json.dumps(rec)) == rec                       # serializável
v0 = M.BALANCE_VERSION
adaga = copy.deepcopy(M.ITEMS["adaga"])                         # restaura depois: outros testes usam ITEMS
M.ITEMS["adaga"]["look"] = {"type": "obj", "anchor": "esq", "art": "adaga"}
assert M._balance_version() == v0                              # visual não muda a versão
M.ITEMS["adaga"]["fx"] = {"atk": 99}
assert M._balance_version() != v0                              # número muda a versão
M.ITEMS["adaga"] = adaga
assert M._balance_version() == v0
print("ok: registro")
