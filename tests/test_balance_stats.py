import sys, json, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import dungeon as M
import balance_stats as E


def line(char, floor, items, killer="Rat", gave_up=False, mode="auto", consumed=(), version=None):
    """Run line in the M.run_record format, built by hand."""
    return {"run": 1, "char": char, "floor": floor, "room": 1, "killer": killer, "gave_up": gave_up,
            "items": [{"key": k, "rar": "common", "floor": f} for k, f in items],
            "consumed": [{"key": k, "rar": "common", "floor": f} for k, f in consumed],
            "gold": 0, "kills": 0, "bosses": 0, "date": "2026-11-11", "mode": mode,
            "version": M.BALANCE_VERSION if version is None else version, "achievements": []}


recs = [line("slime", 10, [("dagger", 2)]), line("slime", 4, [("dagger", 3)]),
        line("slime", 8, []), line("slime", 3, [("candle", 2)], gave_up=True)]
v = E.valid(recs); assert len(v) == 3
esp = E.expected(v); assert esp[2] == ((10 - 2) + (4 - 2) + (8 - 2)) / 3
it = E.per_item(v)
assert it["dagger"]["n"] == 2 and it["dagger"]["lasted"] == ((10 - 2) + (4 - 3)) / 2
assert it["dagger"]["quick_deaths"] == 0.5                        # 4 - 3 <= 2
assert it["candle"]["n"] == 0 and it["candle"]["lasted"] is None         # used to appear only on give-up
assert set(it) == set(M.ITEMS)
assert E.summary([])["n"] == 0
assert E.check_targets({"passed_boss1": 0.4, "p90": 15, "max": 50}) == {"passed_boss1": True, "p90": True, "max": True}
assert E.check_targets({"passed_boss1": 0.5, "p90": 10, "max": 51}) == {"passed_boss1": False, "p90": False, "max": False}
# file: version, demo, broken line, empty folder
d = Path(tempfile.mkdtemp())
assert E.load_real(d) == ([], {"other_versions": 0, "ignored": 0, "gave_ups": 0, "modes": {}})
(d / "runs.jsonl").write_text(json.dumps(recs[0]) + "\n{quebrada\n" + json.dumps(dict(recs[1], version="x")) + "\n")
(d / "runs-demo.jsonl").write_text(json.dumps(recs[2]) + "\n")
real_ones, info = E.load_real(d)
assert len(real_ones) == 1 and info["ignored"] == 1 and info["other_versions"] == 1
assert len(E.load_real(d, all_versions=True)[0]) == 2
# pairs: minimum sample
many = [line("slime", 12, [("dagger", 2), ("pot_lid", 3)]) for _ in range(30)]
assert E.pairs(many, minimum=30)["best_items"][0]["n"] == 30 and E.pairs(many, minimum=31)["best_items"] == []

# extras: vs_expected, consumed per mode, item without floor, deaths, heroes, summary
assert it["dagger"]["vs_expected"] == ((8 - esp[2]) + (1 - esp[3])) / 2
c = E.per_item([line("slime", 6, [("pot_lid", 2)], consumed=[("pot_lid", 1), ("pot_lid", 3)], mode="interactive"),
                line("slime", 6, [("dagger", None)], consumed=[("pot_lid", 4)])])
assert c["pot_lid"]["consumed_pct"] == 3 / 4 and c["pot_lid"]["consumed_by_mode"] == {"interactive": 2 / 3, "auto": 1.0}
assert c["dagger"]["n"] == 0 and c["dagger"]["consumed_pct"] is None     # floor None is ignored
p = E.pairs(many, minimum=30)["best_items"][0]
assert (p["a"], p["b"]) == ("dagger", "pot_lid") and p["vs_expected"] == 0
assert p["gain"] == 0 - max(E.per_item(many)["dagger"]["vs_expected"], E.per_item(many)["pot_lid"]["vs_expected"])
mo = E.deaths(recs)
assert mo["per_floor"] == {4: 1, 8: 1, 10: 1} and mo["killers"] == [("Rat", 3)]
kk = [dict(line("slime", 5, []), killer_kind="horde"), dict(line("slime", 6, []), killer_kind="horde"),
      dict(line("slime", 7, []), killer_kind="boss"), line("slime", 8, [])]   # without the key: old
assert E.deaths(kk)["per_kind"] == {"horde": 2, "boss": 1, "?": 1} and E._line_ok(kk[3])
h = E.heroes(recs + [line("ghost", 7, [])])
assert h["slime"]["n"] == 3 and h["slime"]["median"] == 8 and h["ghost"]["p90"] == 7
r = E.summary(v)
assert r["n"] == 3 and r["max"] == 10 and r["median"] == 8 and r["passed_boss1"] == 2 / 3 and r["items_median"] == 1
# p90 does not go above the maximum on a small sample
assert E.summary(v)["p90"] == 10 and E.heroes([line("slime", 5, []), line("slime", 7, [])])["slime"]["p90"] == 7
# pair with hand-made values: exp[1]=16/3, exp[2]=13/3, exp[5]=3
pq = [line("slime", 10, [("dagger", 2), ("pot_lid", 5)]), line("slime", 6, [("pot_lid", 1)]),
      line("slime", 3, [("dagger", 1)])]
pp = E.pairs(pq, minimum=1)["best_items"][0]
assert pp["n"] == 1 and abs(pp["vs_expected"] - 2) < 1e-9     # counted from the 2nd item: 10 - 5 - 3
assert abs(pp["gain"] - (2 - 5 / 6)) < 1e-9                   # max(dagger 1/6, lid 5/6)
# a valid JSON line with a bad floor counts as ignored
(d / "runs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in
                              [recs[0], dict(recs[0], floor="3"), line("slime", 5, [("dagger", "x")])]))
assert E.load_real(d)[1]["ignored"] == 2
# page, JSON and command line (no real runs)
d = Path(tempfile.mkdtemp())
data = E.collect(n_sim=60, real_folder=d, all_versions=False)
assert data["real"]["n"] == 0 and set(data["items"]) == set(M.ITEMS)
page = E.make_html(data)
for sec in ("Summary", "Items", "Best pairs", "Where runs die", "Heroes", "no real runs"):
    assert sec in page, sec
assert "Horde" in page and "Monster" in page
assert "http://" not in page and "https://" not in page          # nothing external
json.dumps(data)                                                  # serializable
out = Path(tempfile.mkdtemp())
E.main(["--runs", "40", "--no-open", "--real-dir", str(d), "--out", str(out)])
assert (out / "balance_stats.html").exists() and json.loads((out / "balance_stats.json").read_text(encoding="utf-8"))["version"] == M.BALANCE_VERSION
# consumed per mode shows on the item line (real)
d2 = Path(tempfile.mkdtemp())
(d2 / "runs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in [
    line("slime", 6, [("pot_lid", 2)], consumed=[("pot_lid", 1)], mode="interactive"),
    line("slime", 6, [("pot_lid", 2)], consumed=[("pot_lid", 3)], mode="auto")]), encoding="utf-8")
pg = E.make_html(E.collect(n_sim=20, real_folder=d2, all_versions=False))
lid_line = pg[pg.index(M.ITEMS["pot_lid"]["name"]):].split("</tr>")[0]
assert "auto 50%" in lid_line and "interactive 50%" in lid_line
# valid but malformed JSON lines: all ignored, nothing breaks (also with all_versions)
bad_ones = [dict(recs[0], items=None), {k: x for k, x in recs[0].items() if k != "items"},
         {k: x for k, x in recs[0].items() if k != "char"}, dict(recs[0], char=3),
         dict(recs[0], items=[{"rar": "common", "floor": 2}]), dict(recs[0], items=[{"key": 5, "floor": 2}]),
         line("slime", 6, [("dagger", 0)]), line("slime", 6, [("dagger", 9)]),
         line("slime", 6, [], consumed=[("pot_lid", 9)]), dict(recs[0], consumed=None), dict(recs[0], items=["dagger"]),
         {k: x for k, x in dict(recs[0], version="velha").items() if k != "items"}, [1, 2]]
d3 = Path(tempfile.mkdtemp())
(d3 / "runs.jsonl").write_bytes(("".join(json.dumps(x) + "\n" for x in [recs[0]] + bad_ones)).encode() + b"\xff\xfe\n")
for tv in (False, True):
    rr, inf = E.load_real(d3, all_versions=tv)
    assert len(rr) == 1 and inf["ignored"] == len(bad_ones) + 1, inf
    dd = E.collect(n_sim=10, real_folder=d3, all_versions=tv); E.make_html(dd); json.dumps(dd)
# a line without consumed (old) still counts
assert E._line_ok({k: x for k, x in recs[0].items() if k != "consumed"})
# real targets without runs: None (the page shows —)
assert E.check_targets(E.summary([])) == {k: None for k in E.TARGETS}
# vs_mean: vs_expected minus the n-weighted mean, weighted sum ~0
mix = [line("slime", 10, [("dagger", 2), ("pot_lid", 4)]), line("slime", 4, [("dagger", 3)]),
       line("slime", 8, [("pot_lid", 1), ("candle", 5)]), line("slime", 3, [])]
pm = E.per_item(mix)
assert abs(sum(x["n"] * x["vs_mean"] for x in pm.values() if x["n"])) < 1e-9
assert pm["dagger"]["vs_mean"] != pm["dagger"]["vs_expected"]
assert all(x["vs_mean"] is None for x in pm.values() if not x["n"])
# the worst ones do not repeat the best ones
pr = E.pairs([line("slime", 12, [("dagger", 2), ("pot_lid", 3)])] * 30 + [line("slime", 9, [("dagger", 2), ("candle", 3)])] * 30, minimum=30)
assert len(pr["best_items"]) == 2 and pr["worst_items"] == []
# calibration: slime only, same as simulate.py; targets are judged on it
assert set(data["calibration"]) == {"without_achievements", "with_achievements"} and set(data["targets"]) == {"without_achievements", "with_achievements", "real"}
assert data["targets"]["real"] == {k: None for k in E.TARGETS}
import simulate as S
cal = E.summary(S.simulate(60, achs=(), seed=1)[0])
assert data["calibration"]["without_achievements"] == cal
assert "calibration (slime) without achievements" in page and "calibration (slime) with achievements" in page
pg3 = E.make_html(E.collect(n_sim=10, real_folder=d3, all_versions=False))
assert "auto: 1" in pg3 and "ignored lines" in pg3
# hero with a trait: the trait reaches the simulated run
import tokenlike as _tk
_hs = S.all_heroes()
assert all(len(h) == 3 for h in _hs) and any(h[2] for h in _hs), _hs
# every real hero's unlock exists in ACHIEVEMENTS
for _c in _tk.all_characters().values():
    assert not _c.unlock or _c.unlock in M.ACHIEVEMENTS, (_c.key, _c.unlock)
_tr = {"crit": 0.08}
_run = M.new_run("x", {"hp": 20, "atk": 3}, 1, _tr)
assert _run["trait"] == _tr
# synergies: per key n / median with / without, in the data, the page and simulate.py
sy = data["synergies"]
assert set(sy) == {"sim", "real"} and set(sy["sim"]) == set(M.SYNERGIES) == set(sy["real"])
assert set(sy["sim"]["defense2"]) == {"n", "median_with", "median_without"}
_s = E.synergies([dict(line("slime", 9, []), synergies=["defense2"]), line("slime", 5, [])])
assert _s["defense2"] == {"n": 1, "median_with": 9, "median_without": 5} and _s["defense4"]["median_with"] is None
assert "<h2>Synergies</h2>" in page
print("ok: balance_stats")
