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
