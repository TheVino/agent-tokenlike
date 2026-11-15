import sys, json, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import dungeon as M
import balance_stats as E


def line(char, floor, items, killer="Rato", gave_up=False, mode="auto", consumed=(), version=None):
    """Linha de run no formato de M.run_record, montada à mão."""
    return {"run": 1, "char": char, "floor": floor, "room": 1, "killer": killer, "gave_up": gave_up,
            "items": [{"key": k, "rar": "comum", "floor": f} for k, f in items],
            "consumed": [{"key": k, "rar": "comum", "floor": f} for k, f in consumed],
            "gold": 0, "kills": 0, "bosses": 0, "date": "2026-11-11", "mode": mode,
            "version": M.BALANCE_VERSION if version is None else version, "achievements": []}


recs = [line("slime", 10, [("adaga", 2)]), line("slime", 4, [("adaga", 3)]),
        line("slime", 8, []), line("slime", 3, [("vela", 2)], gave_up=True)]
v = E.valid(recs); assert len(v) == 3
esp = E.expected(v); assert esp[2] == ((10 - 2) + (4 - 2) + (8 - 2)) / 3
it = E.per_item(v)
assert it["adaga"]["n"] == 2 and it["adaga"]["durou"] == ((10 - 2) + (4 - 3)) / 2
assert it["adaga"]["mortes_rapidas"] == 0.5                        # 4 - 3 <= 2
assert it["vela"]["n"] == 0 and it["vela"]["durou"] is None         # só aparecia na desistência
assert set(it) == set(M.ITEMS)
assert E.summary([])["n"] == 0
assert E.check_targets({"passou_chefe1": 0.4, "p90": 15, "max": 50}) == {"passou_chefe1": True, "p90": True, "max": True}
assert E.check_targets({"passou_chefe1": 0.5, "p90": 10, "max": 51}) == {"passou_chefe1": False, "p90": False, "max": False}
# arquivo: versão, demo, linha quebrada, pasta vazia
d = Path(tempfile.mkdtemp())
assert E.load_real(d) == ([], {"outras_versoes": 0, "ignoradas": 0, "desistencias": 0, "modos": {}})
(d / "runs.jsonl").write_text(json.dumps(recs[0]) + "\n{quebrada\n" + json.dumps(dict(recs[1], version="x")) + "\n")
(d / "runs-demo.jsonl").write_text(json.dumps(recs[2]) + "\n")
real_ones, info = E.load_real(d)
assert len(real_ones) == 1 and info["ignoradas"] == 1 and info["outras_versoes"] == 1
assert len(E.load_real(d, all_versions=True)[0]) == 2
# pares: mínimo de amostra
many = [line("slime", 12, [("adaga", 2), ("tampa", 3)]) for _ in range(30)]
assert E.pairs(many, minimum=30)["melhores"][0]["n"] == 30 and E.pairs(many, minimum=31)["melhores"] == []

# extras: vs_esperado, consumido por modo, item sem floor, mortes, heróis, resumo
assert it["adaga"]["vs_esperado"] == ((8 - esp[2]) + (1 - esp[3])) / 2
c = E.per_item([line("slime", 6, [("tampa", 2)], consumed=[("tampa", 1), ("tampa", 3)], mode="interativo"),
                line("slime", 6, [("adaga", None)], consumed=[("tampa", 4)])])
assert c["tampa"]["consumido"] == 3 / 4 and c["tampa"]["consumido_por_modo"] == {"interativo": 2 / 3, "auto": 1.0}
assert c["adaga"]["n"] == 0 and c["adaga"]["consumido"] is None     # floor None é ignorado
p = E.pairs(many, minimum=30)["melhores"][0]
assert (p["a"], p["b"]) == ("adaga", "tampa") and p["vs_esperado"] == 0
assert p["ganho"] == 0 - max(E.per_item(many)["adaga"]["vs_esperado"], E.per_item(many)["tampa"]["vs_esperado"])
mo = E.deaths(recs)
assert mo["por_andar"] == {4: 1, 8: 1, 10: 1} and mo["matadores"] == [("Rato", 3)]
kk = [dict(line("slime", 5, []), killer_kind="horde"), dict(line("slime", 6, []), killer_kind="horde"),
      dict(line("slime", 7, []), killer_kind="boss"), line("slime", 8, [])]   # sem a chave: antigo
assert E.deaths(kk)["por_tipo"] == {"horde": 2, "boss": 1, "?": 1} and E._line_ok(kk[3])
h = E.heroes(recs + [line("fantasma", 7, [])])
assert h["slime"]["n"] == 3 and h["slime"]["mediana"] == 8 and h["fantasma"]["p90"] == 7
r = E.summary(v)
assert r["n"] == 3 and r["max"] == 10 and r["mediana"] == 8 and r["passou_chefe1"] == 2 / 3 and r["itens_med"] == 1
# p90 não passa do máximo em amostra pequena
assert E.summary(v)["p90"] == 10 and E.heroes([line("slime", 5, []), line("slime", 7, [])])["slime"]["p90"] == 7
# par com valores à mão: esp[1]=16/3, esp[2]=13/3, esp[5]=3
pq = [line("slime", 10, [("adaga", 2), ("tampa", 5)]), line("slime", 6, [("tampa", 1)]),
      line("slime", 3, [("adaga", 1)])]
pp = E.pairs(pq, minimum=1)["melhores"][0]
assert pp["n"] == 1 and abs(pp["vs_esperado"] - 2) < 1e-9     # conta do 2º item: 10 - 5 - 3
assert abs(pp["ganho"] - (2 - 5 / 6)) < 1e-9                   # max(adaga 1/6, tampa 5/6)
# linha JSON válida mas com floor ruim conta como ignorada
(d / "runs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in
                              [recs[0], dict(recs[0], floor="3"), line("slime", 5, [("adaga", "x")])]))
assert E.load_real(d)[1]["ignoradas"] == 2
# página, JSON e linha de comando (sem runs reais)
d = Path(tempfile.mkdtemp())
data = E.collect(n_sim=60, real_folder=d, all_versions=False)
assert data["real"]["n"] == 0 and set(data["itens"]) == set(M.ITEMS)
page = E.make_html(data)
for sec in ("Resumo", "Itens", "Melhores pares", "Onde as runs morrem", "Heróis", "sem runs reais"):
    assert sec in page, sec
assert "Horda" in page and "Monstro" in page
assert "http://" not in page and "https://" not in page          # nada externo
json.dumps(data)                                                  # serializável
out = Path(tempfile.mkdtemp())
E.main(["--runs", "40", "--no-open", "--real-dir", str(d), "--out", str(out)])
assert (out / "estatisticas.html").exists() and json.loads((out / "estatisticas.json").read_text(encoding="utf-8"))["versao"] == M.BALANCE_VERSION
# consumido por modo aparece na linha do item (real)
d2 = Path(tempfile.mkdtemp())
(d2 / "runs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in [
    line("slime", 6, [("tampa", 2)], consumed=[("tampa", 1)], mode="interativo"),
    line("slime", 6, [("tampa", 2)], consumed=[("tampa", 3)], mode="auto")]), encoding="utf-8")
pg = E.make_html(E.collect(n_sim=20, real_folder=d2, all_versions=False))
lid_line = pg[pg.index(M.ITEMS["tampa"]["name"]):].split("</tr>")[0]
assert "auto 50%" in lid_line and "interativo 50%" in lid_line
# linhas JSON válidas mas malformadas: todas ignoradas, nada quebra (também com todas_versoes)
bad_ones = [dict(recs[0], items=None), {k: x for k, x in recs[0].items() if k != "items"},
         {k: x for k, x in recs[0].items() if k != "char"}, dict(recs[0], char=3),
         dict(recs[0], items=[{"rar": "comum", "floor": 2}]), dict(recs[0], items=[{"key": 5, "floor": 2}]),
         line("slime", 6, [("adaga", 0)]), line("slime", 6, [("adaga", 9)]),
         line("slime", 6, [], consumed=[("tampa", 9)]), dict(recs[0], consumed=None), dict(recs[0], items=["adaga"]),
         {k: x for k, x in dict(recs[0], version="velha").items() if k != "items"}, [1, 2]]
d3 = Path(tempfile.mkdtemp())
(d3 / "runs.jsonl").write_bytes(("".join(json.dumps(x) + "\n" for x in [recs[0]] + bad_ones)).encode() + b"\xff\xfe\n")
for tv in (False, True):
    rr, inf = E.load_real(d3, all_versions=tv)
    assert len(rr) == 1 and inf["ignoradas"] == len(bad_ones) + 1, inf
    dd = E.collect(n_sim=10, real_folder=d3, all_versions=tv); E.make_html(dd); json.dumps(dd)
# linha sem consumed (antiga) continua valendo
assert E._line_ok({k: x for k, x in recs[0].items() if k != "consumed"})
# metas reais sem runs: None (página mostra —)
assert E.check_targets(E.summary([])) == {k: None for k in E.TARGETS}
# vs_media: vs_esperado menos a média ponderada por n, soma ponderada ~0
mix = [line("slime", 10, [("adaga", 2), ("tampa", 4)]), line("slime", 4, [("adaga", 3)]),
       line("slime", 8, [("tampa", 1), ("vela", 5)]), line("slime", 3, [])]
pm = E.per_item(mix)
assert abs(sum(x["n"] * x["vs_media"] for x in pm.values() if x["n"])) < 1e-9
assert pm["adaga"]["vs_media"] != pm["adaga"]["vs_esperado"]
assert all(x["vs_media"] is None for x in pm.values() if not x["n"])
# piores não repetem os melhores
pr = E.pairs([line("slime", 12, [("adaga", 2), ("tampa", 3)])] * 30 + [line("slime", 9, [("adaga", 2), ("vela", 3)])] * 30, minimum=30)
assert len(pr["melhores"]) == 2 and pr["piores"] == []
# calibração: só slime, igual ao simular.py; metas julgadas nela
assert set(data["calibracao"]) == {"sem_conquistas", "com_conquistas"} and set(data["metas"]) == {"sem_conquistas", "com_conquistas", "real"}
assert data["metas"]["real"] == {k: None for k in E.TARGETS}
import simulate as S
cal = E.summary(S.simulate(60, achs=(), seed=1)[0])
assert data["calibracao"]["sem_conquistas"] == cal
assert "calibração (slime) sem conquistas" in page and "calibração (slime) com conquistas" in page
pg3 = E.make_html(E.collect(n_sim=10, real_folder=d3, all_versions=False))
assert "auto: 1" in pg3 and "linhas ignoradas" in pg3
# herói com traço: o traço chega na run simulada
import tokenlike as _tk
_hs = S.all_heroes()
assert all(len(h) == 3 for h in _hs) and any(h[2] for h in _hs), _hs
# unlock de todo herói real existe em ACHIEVEMENTS
for _c in _tk.all_characters().values():
    assert not _c.unlock or _c.unlock in M.ACHIEVEMENTS, (_c.key, _c.unlock)
_tr = {"crit": 0.08}
_run = M.new_run("x", {"hp": 20, "atk": 3}, 1, _tr)
assert _run["traco"] == _tr
print("ok: estatisticas")
