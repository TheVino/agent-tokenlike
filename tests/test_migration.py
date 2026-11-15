"""Migration ~/.tokenpet -> ~/.tokenlike: copies the progress, does not delete the old one, does not overwrite."""
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("tkinter", __import__("types").ModuleType("tkinter"))
import tokenlike as tp

tmp = Path(tempfile.mkdtemp())
old, new = tmp/".tokenpet", tmp/".tokenlike"
tp.DATA_DIR, tp.LOG_FILE = new, new/"tokenlike.log"

# no old folder: nothing to do
assert tp.migrate_old_data(old, new) is False and not new.exists()

old.mkdir()
(old/"state.json").write_text('{"meta": {"runs": 7}}', encoding="utf-8")
(old/"state-demo.json").write_text('{"demo": 1}', encoding="utf-8")
(old/"tokenpet.lock").write_text("")
assert tp.migrate_old_data(old, new) is True
assert (new/"state.json").read_text(encoding="utf-8") == '{"meta": {"runs": 7}}'
assert (new/"state-demo.json").read_text(encoding="utf-8") == '{"demo": 1}'
assert not (new/"tokenpet.lock").exists(), "só o progresso é copiado"
assert (old/"state.json").exists() and (old/"state-demo.json").exists(), "o antigo fica intacto"

# second run: .tokenlike already exists, the new progress is not overwritten
(new/"state.json").write_text('{"meta": {"runs": 9}}', encoding="utf-8")
assert tp.migrate_old_data(old, new) is False
assert '"runs": 9' in (new/"state.json").read_text(encoding="utf-8")

# the migrated state loads normally
state, is_new = tp.load_state(new/"state.json")
assert not is_new and state["meta"]["runs"] == 9
print("ok: migration")

# saves from the Portuguese-named versions: state.json and runs.jsonl converted once, with a .pt.bak copy
import legacy
d = Path(tempfile.mkdtemp())
old = {"mode": "interativo", "size": "Grande", "so_com_uso": True, "janelas": {"conq_win": [1, 2]}, "pico": {"sessao": 5},
       "run": {"char": "fantasma", "traco": {"queimar": 0.1}, "cont": {"esquivas": 2}, "items": [{"key": "adaga", "rar": "lendario"}]},
       "meta": {"achievements": ["chefe1"], "next_char": "medico", "chefes": 3,
                "graveyard": [{"killer": "Rei Rato", "kind": "status", "date": "2026-11-11"}]}}
(d / "state.json").write_text(json.dumps(old), encoding="utf-8")
(d / "runs.jsonl").write_text(json.dumps({"char": "fantasma", "killer": "Veneno", "items": [{"key": "adaga"}]}) + "\n", encoding="utf-8")
assert legacy.migrate_all(d) == ["state.json", "runs.jsonl"] and legacy.migrate_all(d) == []
st = json.loads((d / "state.json").read_text(encoding="utf-8"))
assert st["mode"] == "interactive" and st["size"] == "Large" and st["only_when_used"] and st["windows"] == {"ach_win": [1, 2]}
assert st["run"]["char"] == "ghost" and st["run"]["trait"] == {"burn": 0.1} and st["run"]["counters"] == {"dodges": 2}
assert st["run"]["items"] == [{"key": "dagger", "rar": "legendary"}] and st["meta"]["achievements"] == ["boss1"]
assert st["meta"]["next_char"] == "doctor" and st["meta"]["bosses"] == 3 and st["meta"]["graveyard"][0]["killer"] == "Rat King"
assert json.loads((d / "runs.jsonl").read_text(encoding="utf-8"))["killer"] == "Poison" and (d / "state.json.pt.bak").exists()
s2, _ = tp.load_state(d / "state.json"); assert s2["run"]["char"] == "ghost" and s2["data_version"] == legacy.DATA_VERSION
assert legacy.migrate_state(s2) is s2                             # already migrated: unchanged
print("ok: legacy")
