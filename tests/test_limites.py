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

# estimativa calibrada: fator = % oficial / tokens locais da janela
now = time.time()
st = {}
tp.add_usage(st, now - 3600, 10_000)                       # dentro da sessão e da semana
tp.add_usage(st, now - 3 * 86400, 30_000)                  # só na semana
st["usage_hist_desde"] = now - 8 * 86400                   # histórico cobre a semana toda
lim = {"sessao": (20.0, now + 3600), "semana": (40.0, now + 86400), "updated": now}
tp.calibrate(st, lim, now)
assert abs(st["calib"]["sessao"]["f"] - 20 / 10_000) < 1e-12
assert abs(st["calib"]["semana"]["f"] - 40 / 40_000) < 1e-12
# oficial recente: sem "~"
assert tp.limit_view("sessao", lim, st, now) == (20.0, now + 3600, False, None)
# oficial velho (>10 min): estimado com "~"
later = now + 1200
tp.add_usage(st, later - 60, 5_000)
pct, reset, est, tok = tp.limit_view("sessao", lim, st, later)
assert est and abs(pct - 15_000 * 20 / 10_000) < 1e-9 and reset == now + 3600
# reset passou: janela avança 5h a partir do último reset conhecido
after = now + 3600 + 600
tp.add_usage(st, after - 60, 2_000)
pct, reset, est, _ = tp.limit_view("sessao", None, st, after)
assert est and reset == now + 3600 + 5 * 3600 and abs(pct - 2_000 * 20 / 10_000) < 1e-9
# mesma leitura não recalibra; tokens ~0 não calibram
st["calib"]["sessao"]["f"] = 9; tp.calibrate(st, lim, now); assert st["calib"]["sessao"]["f"] == 9
vazio = {"usage_hist_desde": 0}; tp.calibrate(vazio, dict(lim, updated=now + 1), now); assert "sessao" not in vazio["calib"]
# sem leitura oficial nem fator: só tokens da janela
pct, reset, est, tok = tp.limit_view("sessao", None, vazio, now)
assert pct is None and not est and tok == 0
so = {}; tp.add_usage(so, now - 60, 1_200_000)
assert tp.limit_view("sessao", None, so, now)[3] == 1_200_000
r = tp.read_limits(d / "limites.json", now); assert r["updated"] == saved["updated"]
# histórico mais novo que o início da janela: não calibra e mantém o fator anterior
curto = {"calib": {"semana": {"f": 7, "reset": 1}}, "usage_hist_desde": now - 5 * 3600}; tp.add_usage(curto, now - 60, 50_000)
tp.calibrate(curto, dict(lim, updated=now + 2), now)
assert curto["calib"]["semana"]["f"] == 7 and "sessao" in curto["calib"]
# backfill cobre 8 dias: semana sem uso nos primeiros dias ainda calibra
tmpb = Path(tempfile.mkdtemp()); (tmpb / "p").mkdir()
iso = datetime.fromtimestamp(now - 3600, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
(tmpb / "p" / "a.jsonl").write_text(json.dumps({"type": "assistant", "requestId": "r", "timestamp": iso,
    "message": {"id": "m", "usage": {"input_tokens": 5000, "output_tokens": 0}}}) + "\n")
sb = {}; rb = tp.TokenReader(sb, dirs=[tmpb]); rb.skip_existing(); rb.backfill()
tp.calibrate(sb, {"semana": (10.0, now + 86400), "updated": now}, now)
assert abs(sb["calib"]["semana"]["f"] - 10 / 5000) < 1e-12
print("ok: estimativa")

# perfil: nível de domador, uso por dia, sequência e último uso (funções puras, só usage_hist/daily)
assert tp.nivel(0) == (0, 0.0, 1_000_000)
assert tp.nivel(999_999)[0] == 0 and tp.nivel(1_000_000)[:2] == (1, 0.0)
n, frac, falta = tp.nivel(2_500_000)                 # Nv 1 vai de 1M a 4M
assert n == 1 and abs(frac - 0.5) < 1e-12 and falta == 1_500_000
assert tp.nivel(4_000_000)[0] == 2 and tp.nivel(100_000_000)[0] == 10
meio_dia = datetime(2026, 11, 14, 12).timestamp()
dia = lambda d: str(int((meio_dia - d * 86400) // tp.BUCKET_S * tp.BUCKET_S))
assert tp.uso_por_dia({}, meio_dia)[-1] == (datetime(2026, 11, 14).date(), 0.0) and tp.dias_seguidos({}, meio_dia) == 0
assert tp.ultimo_uso({}) is None
s = {"usage_hist": {dia(0): 10, dia(1): 5, dia(2): 7, dia(4): 1, dia(9): 99}}
por_dia = tp.uso_por_dia(s, meio_dia)
assert len(por_dia) == 7 and [v for _, v in por_dia] == [0, 0, 1, 0, 7, 5, 10], por_dia
assert tp.dias_seguidos(s, meio_dia) == 3
del s["usage_hist"][dia(0)]
assert tp.dias_seguidos(s, meio_dia) == 2                                  # hoje sem uso não quebra a sequência
s["daily"] = {"2026-11-11": 3, "2026-11-10": 3, "2026-11-09": 0}
assert tp.dias_seguidos(s, meio_dia) == 4                                  # daily (60 dias) estende o histórico
assert tp.ultimo_uso(s) == int(dia(1)) + tp.BUCKET_S
assert tp.fmt_ha(30) == "agora" and tp.fmt_ha(600) == "há 10 min" and tp.fmt_ha(7200) == "há 2 h"
print("ok: perfil")
