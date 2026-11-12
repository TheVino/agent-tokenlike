import sys, json, tempfile, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("tkinter", __import__("types").ModuleType("tkinter"))
import tokenlike as tp

tmp = Path(tempfile.mkdtemp()); proj = tmp/"projects"/"-C-proj"; (proj/"sess"/"subagents").mkdir(parents=True)
f = proj/"a.jsonl"
def asst(mid, rid, i,o,cc,cr, block="text"):
    return json.dumps({"type":"assistant","requestId":rid,"message":{"id":mid,"content":[{"type":block}],
        "usage":{"input_tokens":i,"output_tokens":o,"cache_creation_input_tokens":cc,"cache_read_input_tokens":cr}}})
old = asst("m0","r0",999,999,0,0)+"\n"
f.write_text(old + json.dumps({"type":"user","message":{"content":"segredo usage"}})+"\n")

state = {}
r = tp.TokenReader(state, dirs=[tmp/"projects"])
r.skip_existing()
assert r.poll() == (0.0, 0), "history should be skipped"

with open(f,"a") as fh:
    fh.write(asst("m1","r1",10,20,100,1000,"thinking")+"\n")
    fh.write(asst("m1","r1",10,20,100,1000,"tool_use")+"\n")   # duplicate of same message
    fh.write(asst("m2","r2",5,5,0,0)[:30])                       # partial line (being written)
xp, raw = r.poll()
assert raw == 1130 and abs(xp - (10+20+100+100)) < 1e-9, (xp, raw)
with open(f,"a") as fh: fh.write(asst("m2","r2",5,5,0,0)[30:]+"\n")
assert r.poll() == (10.0, 10)

# new subagent file created later is read from start
(proj/"sess"/"subagents"/"x.jsonl").write_text(asst("m3","r3",1,1,0,0)+"\n")
r._files_at = 0
assert r.poll() == (2.0, 2)

# persistence: new reader from saved state doesn't double count
r.export(); st2 = json.loads(json.dumps(state))
r2 = tp.TokenReader(st2, dirs=[tmp/"projects"])
assert r2.poll() == (0.0, 0)
# garbage line
with open(f,"a") as fh: fh.write('{"usage": broken\n')
assert r2.poll() == (0.0, 0)

# import-history path: fresh reader without skip reads everything
r3 = tp.TokenReader({}, dirs=[tmp/"projects"])
xp, raw = r3.poll(); assert raw == 1998+1130+10+2, raw

assert tp.fmt(1500)=="1.5K" and tp.fmt(1000)=="1K" and tp.fmt(2_340_000)=="2.3M" and tp.fmt(12)=="12"
chars = tp.all_characters(); print({k:[s["title"] for s in c.stages] for k,c in chars.items()})
assert chars["slime"].stage_floors == [1, 3, 8, 15] and chars["fantasma"].unlock == "chefe1"
import arte; arte.validate()
print("reader tests ok")

# horário das respostas: histórico de uso por baldes de 5 min (só o timestamp, nada de conteúdo)
import time as _t
from datetime import datetime as _dt, timezone as _tz
def iso(ts): return _dt.fromtimestamp(ts, _tz.utc).strftime("%Y-%m-%dT%H:%M:%S.123Z")
def asst_ts(mid, rid, i, ts):
    d = json.loads(asst(mid, rid, i, 0, 0, 0)); d["timestamp"] = iso(ts); return json.dumps(d)
tmp2 = Path(tempfile.mkdtemp()); (tmp2/"p").mkdir(); g = tmp2/"p"/"b.jsonl"
now = _t.time()
g.write_text("\n".join([asst_ts("t1","r",100,now), asst_ts("t1","r",100,now),        # duplicada
                        asst_ts("t2","r",50,now - 9*86400),                          # velha: podada
                        asst("t3","r",7,0,0,0)]) + "\n")                             # sem horário
st = {}; rd = tp.TokenReader(st, dirs=[tmp2])
assert rd.poll() == (157.0, 157)                         # energia conta tudo, sem duplicar
assert sum(st["usage_hist"].values()) == 100, st["usage_hist"]   # sem horário fica fora; >8 dias podado
assert tp.parse_ts("2026-01-01T00:00:00Z") == _dt(2026,1,1,tzinfo=_tz.utc).timestamp()
assert tp.parse_ts(None) is None and tp.parse_ts("lixo") is None
assert abs(tp.usage_between(st, now - 600, now + 1) - 100) < 1e-9 and tp.usage_between(st, now - 9e6, now - 3600) == 0
print("reader timestamp ok")

# backfill: linhas já existentes enchem o histórico, mas não dão energia nem entram no `seen`
tmp3 = Path(tempfile.mkdtemp()); (tmp3/"p").mkdir(); h = tmp3/"p"/"c.jsonl"
h.write_text("\n".join([asst_ts("b1","r",300,now), asst_ts("b1","r",300,now), asst_ts("b2","r",20,now)]) + "\n")
sb = {}; rb = tp.TokenReader(sb, dirs=[tmp3]); rb.skip_existing(); rb.backfill()
assert sum(sb["usage_hist"].values()) == 320, sb["usage_hist"]
assert rb.poll() == (0.0, 0) and not rb.seen
print("reader backfill ok")

# Petdex: pasta só com WebP é ignorada com aviso; pet.json inválido não derruba (sem tkinter)
dex = Path(tempfile.mkdtemp()); (dex/"w").mkdir(); (dex/"w"/"pet.json").write_text("{x")
(dex/"w"/"spritesheet.webp").write_bytes(b"w")
tp.LOG_FILE = dex/"log.txt"; tp.DATA_DIR = dex
tp.petdex_dirs = lambda: [dex, dex/"nao-existe"]
assert tp.load_petdex_characters() == []
_l = tp.LOG_FILE.read_text(encoding="utf-8")
assert "converta para PNG" in _l and "converter_webp.py" in _l and "erro" not in _l
# OpenPets: displayName + spritesheetPath .webp com .png de mesmo nome ao lado
sys.path.insert(0, str(Path(__file__).parent)); from _png import folha_png as _png0
def _png(path): _png0(path, 8 * 9, 9 * 8)
(dex/"o").mkdir(); (dex/"o"/"pet.json").write_text('{"displayName":"Bitty","spritesheetPath":"sheet.webp"}')
(dex/"o"/"sheet.webp").write_bytes(b"w"); _png(dex/"o"/"sheet.png")
assert [c.name for c in tp.load_petdex_characters()] == ["Bitty"]
tp.CHARACTERS_DIR = dex/"nao-existe"
chd = Path(tempfile.mkdtemp()); (chd/"o").mkdir(); (chd/"o"/"pet.json").write_text('{"name":"Nome","displayName":"Bitty"}'); _png(chd/"o"/"x.png")
assert [c.name for c in tp.load_png_characters(chd)] == ["Bitty"]
print("reader petdex ok")
