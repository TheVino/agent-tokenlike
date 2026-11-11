import sys, json, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import masmorra as M
import estatisticas as E


def linha(char, floor, items, killer="Rato", gave_up=False, mode="auto", consumed=(), version=None):
    """Linha de run no formato de M.run_record, montada à mão."""
    return {"run": 1, "char": char, "floor": floor, "room": 1, "killer": killer, "gave_up": gave_up,
            "items": [{"key": k, "rar": "comum", "floor": f} for k, f in items],
            "consumed": [{"key": k, "rar": "comum", "floor": f} for k, f in consumed],
            "gold": 0, "kills": 0, "bosses": 0, "date": "2026-11-11", "mode": mode,
            "version": M.BALANCE_VERSION if version is None else version, "achievements": []}


recs = [linha("slime", 10, [("adaga", 2)]), linha("slime", 4, [("adaga", 3)]),
        linha("slime", 8, []), linha("slime", 3, [("vela", 2)], gave_up=True)]
v = E.validas(recs); assert len(v) == 3
esp = E.esperado(v); assert esp[2] == ((10 - 2) + (4 - 2) + (8 - 2)) / 3
it = E.por_item(v)
assert it["adaga"]["n"] == 2 and it["adaga"]["durou"] == ((10 - 2) + (4 - 3)) / 2
assert it["adaga"]["mortes_rapidas"] == 0.5                        # 4 - 3 <= 2
assert it["vela"]["n"] == 0 and it["vela"]["durou"] is None         # só aparecia na desistência
assert set(it) == set(M.ITEMS)
assert E.resumo([])["n"] == 0
assert E.checar_metas({"passou_chefe1": 0.4, "p90": 15, "max": 25}) == {"passou_chefe1": True, "p90": True, "max": True}
assert E.checar_metas({"passou_chefe1": 0.5, "p90": 10, "max": 26}) == {"passou_chefe1": False, "p90": False, "max": False}
# arquivo: versão, demo, linha quebrada, pasta vazia
d = Path(tempfile.mkdtemp())
assert E.carregar_reais(d) == ([], {"outras_versoes": 0, "ignoradas": 0, "desistencias": 0, "modos": {}})
(d / "runs.jsonl").write_text(json.dumps(recs[0]) + "\n{quebrada\n" + json.dumps(dict(recs[1], version="x")) + "\n")
(d / "runs-demo.jsonl").write_text(json.dumps(recs[2]) + "\n")
reais, info = E.carregar_reais(d)
assert len(reais) == 1 and info["ignoradas"] == 1 and info["outras_versoes"] == 1
assert len(E.carregar_reais(d, todas_versoes=True)[0]) == 2
# pares: mínimo de amostra
many = [linha("slime", 12, [("adaga", 2), ("tampa", 3)]) for _ in range(30)]
assert E.pares(many, minimo=30)["melhores"][0]["n"] == 30 and E.pares(many, minimo=31)["melhores"] == []

# extras: vs_esperado, consumido por modo, item sem floor, mortes, heróis, resumo
assert it["adaga"]["vs_esperado"] == ((8 - esp[2]) + (1 - esp[3])) / 2
c = E.por_item([linha("slime", 6, [("tampa", 2)], consumed=[("tampa", 1), ("tampa", 3)], mode="interativo"),
                linha("slime", 6, [("adaga", None)], consumed=[("tampa", 4)])])
assert c["tampa"]["consumido"] == 3 / 4 and c["tampa"]["consumido_por_modo"] == {"interativo": 2 / 3, "auto": 1.0}
assert c["adaga"]["n"] == 0 and c["adaga"]["consumido"] is None     # floor None é ignorado
p = E.pares(many, minimo=30)["melhores"][0]
assert (p["a"], p["b"]) == ("adaga", "tampa") and p["vs_esperado"] == 0
assert p["ganho"] == 0 - max(E.por_item(many)["adaga"]["vs_esperado"], E.por_item(many)["tampa"]["vs_esperado"])
mo = E.mortes(recs)
assert mo["por_andar"] == {4: 1, 8: 1, 10: 1} and mo["matadores"] == [("Rato", 3)]
h = E.herois(recs + [linha("fantasma", 7, [])])
assert h["slime"]["n"] == 3 and h["slime"]["mediana"] == 8 and h["fantasma"]["p90"] == 7
r = E.resumo(v)
assert r["n"] == 3 and r["max"] == 10 and r["mediana"] == 8 and r["passou_chefe1"] == 2 / 3 and r["itens_med"] == 1
print("ok: estatisticas")
