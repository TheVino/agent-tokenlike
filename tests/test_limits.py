"""Session/week bars: statusline.py writes only the limits; tokenlike reads them, flags stale data and formats them."""
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
lim = SL.extract(payload)
assert set(lim) == {"five_hour", "seven_day", "updated"}, lim
assert lim["five_hour"] == {"used_percentage": 42.4, "resets_at": float(int(now) + 3600)}
assert lim["seven_day"]["resets_at"] == datetime(2099, 1, 2, 3, 4, 5).replace(
    tzinfo=__import__("datetime").timezone.utc).timestamp()
assert "segredo" not in json.dumps(lim)                       # nothing besides the limits
assert SL.extract({"model": {}}) is None                      # no rate_limits: writes nothing
assert SL.extract({"rate_limits": {"five_hour": {"used_percentage": "x"}}}) is None
assert SL.format_line(lim) == "sessão 42% · semana 18%"
assert SL.format_line(None) == ""

# main(): reads stdin, writes the file atomically and prints the line
d = Path(tempfile.mkdtemp())
out = io.StringIO()
SL.main(io.StringIO(json.dumps(payload)), out, d)
saved = json.loads((d / "limites.json").read_text(encoding="utf-8"))
assert saved["five_hour"]["used_percentage"] == 42.4 and "cwd" not in saved
assert out.getvalue().strip() == "sessão 42% · semana 18%"
SL.main(io.StringIO("{lixo"), io.StringIO(), d)               # broken stdin: does not erase the last one
SL.main(io.StringIO(json.dumps({"model": {}})), io.StringIO(), d)
assert json.loads((d / "limites.json").read_text(encoding="utf-8"))["five_hour"]["used_percentage"] == 42.4

# reading in the app
assert tp.read_limits(d / "nao_existe.json", now) is None
r = tp.read_limits(d / "limites.json", now)
assert r["sessao"][0] == 42.4 and r["semana"][0] == 18
old = dict(saved, five_hour={"used_percentage": 90, "resets_at": now - 10})
(d / "velho.json").write_text(json.dumps(old), encoding="utf-8")
r = tp.read_limits(d / "velho.json", now)
assert r["sessao"][0] is None and r["semana"][0] == 18       # the reset already passed: stale data becomes "—"
(d / "ruim.json").write_text("{", encoding="utf-8")
assert tp.read_limits(d / "ruim.json", now) is None

# colors and reset time in the local time zone
assert tp.limit_color(50) == tp.GOOD and tp.limit_color(80) == tp.GOLD and tp.limit_color(81) == tp.HURT
base = datetime(2026, 11, 11, 10, 0).timestamp()             # Wednesday, 10:00 local
assert tp.fmt_reset(datetime(2026, 11, 11, 14, 30).timestamp(), base) == "14:30"
assert tp.fmt_reset(datetime(2026, 11, 13, 9, 0).timestamp(), base) == "sex 09:00"
print("ok: limites")

# calibrated estimate: factor = official % / local tokens in the window
now = time.time()
st = {}
tp.add_usage(st, now - 3600, 10_000)                       # inside the session and the week
tp.add_usage(st, now - 3 * 86400, 30_000)                  # only in the week
st["usage_hist_desde"] = now - 8 * 86400                   # history covers the whole week
lim = {"sessao": (20.0, now + 3600), "semana": (40.0, now + 86400), "updated": now}
tp.calibrate(st, lim, now)
assert abs(st["calib"]["sessao"]["f"] - 20 / 10_000) < 1e-12
assert abs(st["calib"]["semana"]["f"] - 40 / 40_000) < 1e-12
# recent official reading: no "~"
assert tp.limit_view("sessao", lim, st, now) == (20.0, now + 3600, False, None)
# old official reading (>10 min): estimated with "~"
later = now + 1200
tp.add_usage(st, later - 60, 5_000)
pct, reset, est, tok = tp.limit_view("sessao", lim, st, later)
assert est and abs(pct - 15_000 * 20 / 10_000) < 1e-9 and reset == now + 3600
# the reset passed: the window moves 5h ahead from the last known reset
after = now + 3600 + 600
tp.add_usage(st, after - 60, 2_000)
pct, reset, est, _ = tp.limit_view("sessao", None, st, after)
assert est and reset == now + 3600 + 5 * 3600 and abs(pct - 2_000 * 20 / 10_000) < 1e-9
# the same reading does not recalibrate; ~0 tokens do not calibrate
st["calib"]["sessao"]["f"] = 9; tp.calibrate(st, lim, now); assert st["calib"]["sessao"]["f"] == 9
empty = {"usage_hist_desde": 0}; tp.calibrate(empty, dict(lim, updated=now + 1), now); assert "sessao" not in empty["calib"]
# no official reading and no factor: only the window's tokens
pct, reset, est, tok = tp.limit_view("sessao", None, empty, now)
assert pct is None and not est and tok == 0
so = {}; tp.add_usage(so, now - 60, 1_200_000)
assert tp.limit_view("sessao", None, so, now)[3] == 1_200_000
# no factor: session rebuilt from the history (starts at the 1st use; usage after 5h opens another one) and the yardstick = your peak
h = {}; t0 = 1_800_000_000
tp.add_usage(h, t0, 4_000); tp.add_usage(h, t0 + 4 * 3600, 6_000)          # session 1: 10k
tp.add_usage(h, t0 + 6 * 3600, 3_000)                                        # session 2 (past the 5h): 3k
assert tp.sessions(h) == [[t0 // 300 * 300, 10_000], [(t0 + 6 * 3600) // 300 * 300, 3_000]]
pct, reset, est, tok = tp.limit_view("sessao", None, h, t0 + 7 * 3600)
assert pct is None and tok == 3_000 and reset == (t0 + 6 * 3600) // 300 * 300 + 5 * 3600
assert tp.limit_view("sessao", None, h, t0 + 12 * 3600) == (None, None, False, 0.0)   # the session ended
assert tp.peak(h, "sessao", 3_000) == 10_000 and h["pico"]["sessao"] == 10_000
h["usage_hist"].clear(); assert tp.peak(h, "sessao", 2_000) == 10_000            # the peak survives the history
assert tp.peak(h, "semana", 50_000) == 50_000 and tp.peak(h, "semana", 1) == 50_000
r = tp.read_limits(d / "limites.json", now); assert r["updated"] == saved["updated"]
# history newer than the window start: does not calibrate and keeps the previous factor
short = {"calib": {"semana": {"f": 7, "reset": 1}}, "usage_hist_desde": now - 5 * 3600}; tp.add_usage(short, now - 60, 50_000)
tp.calibrate(short, dict(lim, updated=now + 2), now)
assert short["calib"]["semana"]["f"] == 7 and "sessao" in short["calib"]
# backfill covers 8 days: a week with no usage in the first days still calibrates
tmpb = Path(tempfile.mkdtemp()); (tmpb / "p").mkdir()
iso = datetime.fromtimestamp(now - 3600, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
(tmpb / "p" / "a.jsonl").write_text(json.dumps({"type": "assistant", "requestId": "r", "timestamp": iso,
    "message": {"id": "m", "usage": {"input_tokens": 5000, "output_tokens": 0}}}) + "\n")
sb = {}; rb = tp.TokenReader(sb, dirs=[tmpb]); rb.skip_existing(); rb.backfill()
tp.calibrate(sb, {"semana": (10.0, now + 86400), "updated": now}, now)
assert abs(sb["calib"]["semana"]["f"] - 10 / 5000) < 1e-12
print("ok: estimativa")

# profile: tamer level (lifetime energy), usage per day, streak and last use (pure functions, only usage_hist/daily)
assert tp.level(0) == (0, 0.0, 1_000_000)
assert tp.level(999_999)[0] == 0 and tp.level(1_000_000)[:2] == (1, 0.0)
n, frac, missing = tp.level(2_500_000)                 # Lv 1 goes from 1M to 4M
assert n == 1 and abs(frac - 0.5) < 1e-12 and missing == 1_500_000
assert tp.level(4_000_000)[0] == 2 and tp.level(100_000_000)[0] == 10
noon = datetime(2026, 11, 14, 12).timestamp()
day = lambda d: str(int((noon - d * 86400) // tp.BUCKET_S * tp.BUCKET_S))
assert tp.usage_per_day({}, noon)[-1] == (datetime(2026, 11, 14).date(), 0.0) and tp.streak_days({}, noon) == 0
assert tp.last_use({}) is None
s = {"usage_hist": {day(0): 10, day(1): 5, day(2): 7, day(4): 1, day(9): 99}}
per_day = tp.usage_per_day(s, noon)
assert len(per_day) == 7 and [v for _, v in per_day] == [0, 0, 1, 0, 7, 5, 10], per_day
assert tp.streak_days(s, noon) == 3
del s["usage_hist"][day(0)]
assert tp.streak_days(s, noon) == 2                                  # today without usage does not break the streak
s["daily"] = {"2026-11-11": 3, "2026-11-10": 3, "2026-11-09": 0}
assert tp.streak_days(s, noon) == 4                                  # daily (60 days) extends the history
assert tp.last_use(s) == int(day(1)) + tp.BUCKET_S
assert tp.fmt_ago(30) == "agora" and tp.fmt_ago(600) == "há 10 min" and tp.fmt_ago(7200) == "há 2 h"
print("ok: perfil")
