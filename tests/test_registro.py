import sys, json, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import masmorra as M

run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); run["floor"] = 4
assert run["consumed"] == []
M.resolve_offer(run, {"key": "adaga", "rar": "raro"}, "pegar", {"lines": []})
M.resolve_offer(run, {"key": "tampa", "rar": "comum"}, "consumir", {"lines": []})
assert run["items"] == [{"key": "adaga", "rar": "raro", "floor": 4, "kills0": 0}]
assert run["consumed"] == [{"key": "tampa", "rar": "comum", "floor": 4}]
old = {"items": [{"key": "adaga", "rar": "comum"}], "hp": 5}
M.migrate_run(old); assert old["items"][0]["floor"] is None and old["consumed"] == []
rec = M.run_record(run, "Rei Rato", False, "auto", ["andar5"])
assert set(rec) == {"run", "char", "floor", "room", "killer", "gave_up", "items", "consumed", "gold",
                    "kills", "bosses", "date", "mode", "version", "achievements", "killer_kind"}
assert rec["killer_kind"] == ""
assert M.run_record(run, "x", False, "auto", [], killer_kind="horde")["killer_kind"] == "horde"
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
M.MONSTERS[0] = (M.MONSTERS[0][0], "Outro Nome") + M.MONSTERS[0][2:]
assert M._balance_version() == v0                              # nome de monstro não muda a versão
M.MONSTERS[0] = (M.MONSTERS[0][0], "Morcego") + M.MONSTERS[0][2:]
rev = M.REGRAS_REV; M.REGRAS_REV += 1
assert M._balance_version() != v0                              # regra/fórmula nova: sobe REGRAS_REV
M.REGRAS_REV = rev; assert M._balance_version() == v0
# simulador gera registros no formato real
sys.path.insert(0, str(ROOT / "tools")); import simular as S
recs, salas = S.simular(n=40, achs=list(M.ACHIEVEMENTS), seed=3, heroes=S.todos_os_herois())
assert len(recs) == 40 and len(salas) == 40
assert {r["char"] for r in recs} == {k for k, _ in S.todos_os_herois()}
assert all(set(r) == set(M.run_record(M.new_run("slime", {}, 0), "x", False, "auto", [])) for r in recs)
assert all(i["floor"] is not None for r in recs for i in r["items"])
a, _ = S.simular(n=20, seed=5); b, _ = S.simular(n=20, seed=5)
assert [r["floor"] for r in a] == [r["floor"] for r in b]       # determinístico
# cemitério guarda o tipo da morte
import random
def morre(kind_sala=None, **kw):
    rng = random.Random(1)
    for seed in range(400):
        rng = random.Random(seed); meta = M.new_meta(); r = M.new_run("slime", {"hp": 1, "atk": 0}, 0)
        r["floor"] = 8; r["energy"] = 1e9
        while not r["dead"]:
            M.enter_room(r, meta, rng, mode="auto")
        yield meta["graveyard"][-1]
tipos = {g["kind"] for g in morre()}
assert tipos <= {"monster", "horde", "boss", "mimic", "trap", "status"} and "horde" in tipos, tipos
assert all((g["kind"] == "status") == (g["killer"] in ("Queimadura", "Veneno")) for g in morre())
m2 = M.new_meta(); r2 = M.new_run("slime", {"hp": 5, "atk": 1}, 0)
M.die(r2, m2, {}, "Desistiu", "desistiu"); assert m2["graveyard"][-1]["kind"] == "desistiu"
print("ok: registro")
