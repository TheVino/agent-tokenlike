"""Barras de sessão/semana: statusline.py grava só os limites; tokenlike lê, marca dado velho e formata."""
import io, json, sys, tempfile, time
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("tkinter", __import__("types").ModuleType("tkinter"))
import statusline as SL
import tokenlike as tp

now = time.time()
payload = {
    "session_id": "abc", "cwd": "C:/segredo", "transcript_path": "C:/segredo/t.jsonl",
    "model": {"display_name": "Opus"}, "workspace": {"current_dir": "C:/segredo"},
    "rate_limits": {"five_hour": {"used_percentage": 42.4, "resets_at": int(now) + 3600},
                    "seven_day": {"used_percentage": 18, "resets_at": "2099-01-02T03:04:05Z"}},
}
lim = SL.extrair(payload)
assert set(lim) == {"five_hour", "seven_day", "updated"}, lim
assert lim["five_hour"] == {"used_percentage": 42.4, "resets_at": float(int(now) + 3600)}
assert lim["seven_day"]["resets_at"] == datetime(2099, 1, 2, 3, 4, 5).replace(
    tzinfo=__import__("datetime").timezone.utc).timestamp()
assert "segredo" not in json.dumps(lim)                       # nada além dos limites
assert SL.extrair({"model": {}}) is None                      # sem rate_limits: não grava nada
assert SL.extrair({"rate_limits": {"five_hour": {"used_percentage": "x"}}}) is None
assert SL.formatar_linha(lim) == "sessão 42% · semana 18%"
assert SL.formatar_linha(None) == ""

# main(): lê stdin, grava o arquivo atomicamente e imprime a linha
d = Path(tempfile.mkdtemp())
out = io.StringIO()
SL.main(io.StringIO(json.dumps(payload)), out, d)
saved = json.loads((d / "limites.json").read_text(encoding="utf-8"))
assert saved["five_hour"]["used_percentage"] == 42.4 and "cwd" not in saved
assert out.getvalue().strip() == "sessão 42% · semana 18%"
SL.main(io.StringIO("{lixo"), io.StringIO(), d)               # stdin quebrado: não apaga o último
SL.main(io.StringIO(json.dumps({"model": {}})), io.StringIO(), d)
assert json.loads((d / "limites.json").read_text(encoding="utf-8"))["five_hour"]["used_percentage"] == 42.4

# leitura no app
assert tp.read_limits(d / "nao_existe.json", now) is None
r = tp.read_limits(d / "limites.json", now)
assert r["sessao"][0] == 42.4 and r["semana"][0] == 18
old = dict(saved, five_hour={"used_percentage": 90, "resets_at": now - 10})
(d / "velho.json").write_text(json.dumps(old), encoding="utf-8")
r = tp.read_limits(d / "velho.json", now)
assert r["sessao"][0] is None and r["semana"][0] == 18       # reset já passou: dado velho vira "—"
(d / "ruim.json").write_text("{", encoding="utf-8")
assert tp.read_limits(d / "ruim.json", now) is None

# cores e horário de reset no fuso local
assert tp.limit_color(50) == tp.GOOD and tp.limit_color(80) == tp.GOLD and tp.limit_color(81) == tp.HURT
base = datetime(2026, 11, 11, 10, 0).timestamp()             # quarta, 10:00 local
assert tp.fmt_reset(datetime(2026, 11, 11, 14, 30).timestamp(), base) == "14:30"
assert tp.fmt_reset(datetime(2026, 11, 13, 9, 0).timestamp(), base) == "sex 09:00"
print("ok: limites")
