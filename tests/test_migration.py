"""Migration ~/.tokenpet -> ~/.tokenlike: copies the progress, does not delete the old one, does not overwrite."""
import sys, tempfile
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
print("ok: migração")
