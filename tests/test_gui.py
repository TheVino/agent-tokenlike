"""Smoke test of the interface with a fake tkinter (runs without a screen)."""
import json, random, sys, types, tempfile, os, time
from pathlib import Path
from datetime import date
home = tempfile.mkdtemp(); os.environ["HOME"]=home; os.environ["USERPROFILE"]=home
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PENDING=[]
class Noop:
    def __init__(self,*a,**k): pass
    def __getattr__(self, n): return lambda *a, **k: None
class TclError(Exception): pass
class Tk(Noop):
    def after(self, ms, fn=None, *a): PENDING.append(fn)
    def winfo_x(self): return 300
    def winfo_y(self): return 300
    def winfo_width(self): return 150
    def winfo_height(self): return 120
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def winfo_vrootx(self): return 0
    def winfo_vrooty(self): return 0
    def winfo_vrootwidth(self): return 1920
    def winfo_vrootheight(self): return 1080
class Canvas(Noop):
    """Keeps the position and text of each item for a realistic bbox (6 px per letter, 10 tall)."""
    n=0
    def __init__(self,*a,**k): self.it={}; self.binds={}; self.cfg=dict(k); self.moveto=None
    def bind(self,seq,fn=None,*a,**k): self.binds[seq]=fn
    def configure(self,**k): self.cfg.update(k)
    def yview_moveto(self,f): self.moveto=f
    def _new(self,kind,a,k): Canvas.n+=1; self.it[Canvas.n]=[kind,list(a[:4]),dict(k)]; return Canvas.n
    def create_image(self,*a,**k): return self._new("img",a,k)
    def create_rectangle(self,*a,**k): return self._new("rect",a,k)
    def create_text(self,*a,**k): return self._new("text",a,k)
    def _ids(self,i):   # id or tag (string or tuple in tags=)
        if i in self.it: return [i]
        return [n for n,v in self.it.items() if i in ((v[2].get("tags"),) if isinstance(v[2].get("tags"),str) else (v[2].get("tags") or ()))]
    def coords(self,i,*a):
        if i in self.it and a: self.it[i][1]=list(a)
    def move(self,i,dx,dy):
        for n in self._ids(i): c=self.it[n][1]; self.it[n][1]=[v+(dx if j%2==0 else dy) for j,v in enumerate(c)]
    def itemconfigure(self,i,**k):
        for n in self._ids(i): self.it[n][2].update(k)
    def delete(self,i):
        if i=="all": self.it.clear()
        for n in self._ids(i): self.it.pop(n,None)
    def bbox(self,i):
        ids=self._ids(i)
        if not ids: return (100,0,140,10)
        bs=[self._bbox(n) for n in ids]
        return (min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs))
    def _bbox(self,i):
        kind,c,k=self.it[i]
        if kind=="rect": return tuple(c[:4])
        if kind=="text":
            w=6*len(str(k.get("text",""))); a=k.get("anchor","center")
            x0=c[0] if a in ("w","nw","sw") else c[0]-w if a in ("e","ne","se") else c[0]-w/2
            return (x0,c[1]-5,x0+w,c[1]+5)
        return (c[0]-8,c[1]-16,c[0]+8,c[1])
class PhotoImage(Noop):
    def __init__(self, width=16, height=16, file=None, **k):
        self.op=None
        if file:
            assert Path(file).is_file(), file
        self.w,self.h=width,height
    def width(self): return self.w
    def height(self): return self.h
    def zoom(self,z): return PhotoImage(self.w*z,self.h*z)
    def subsample(self,s): return PhotoImage(self.w//s,self.h//s)
    def transparency_get(self,x,y): return not self.op(x,y) if self.op else not (3<=x<13 and 2<=y<16)
    def get(self,x,y): return (200,100,50)
class Var:
    def __init__(self, value=None): self.v=value
    def get(self): return self.v
    def set(self,v): self.v=v
fake = types.ModuleType("tkinter")
fake.Tk, fake.Canvas, fake.PhotoImage, fake.Toplevel = Tk, Canvas, PhotoImage, Tk
class Wid(Noop):
    def __init__(self,*a,**k): self.binds={}
    def bind(self,seq,fn=None,*a,**k): self.binds[seq]=fn
fake.Label = fake.Menu = fake.Button = fake.Frame = Wid
fake.StringVar = fake.BooleanVar = Var
fake.TclError = TclError
sys.modules["tkinter"] = fake
SEED = 1
import tokenlike as tp, dungeon as M
tp.DATA_DIR = Path(home)/".tokenlike"; tp.LOG_FILE = tp.DATA_DIR/"tokenlike.log"
import tkinter; tp.tk = tkinter
Args = lambda **k: types.SimpleNamespace(**{"demo":False,"import_history":False,"reset":False, **k})

def pump(app, n):
    for _ in range(n):
        app.busy_until = 0
        if app.run["dead"] and app.respawn_at: app.respawn_at = 1
        app.feed(200_000, 600_000)
        if app.run["pending"]: app.pending_since = 0   # ages the choice so it does not get stuck
        app.tick()
        fns = PENDING[:]; PENDING.clear()
        for fn in fns:
            if fn is None or getattr(fn, "__name__", "") in ("tick","poll"): continue
            fn()

for demo in (False, True):
    app = tp.PetApp(Args(demo=demo)); PENDING.clear(); app.rng = random.Random(SEED)
    app.poll(); PENDING.clear()
    pump(app, 1500)
    m = app.meta
    print(("demo" if demo else "real"), "runs:", m["runs"], "best:", m["best"], "achs:", m["achievements"])
    assert m["runs"] > 3 and len(m["graveyard"]) == min(m["runs"], 50)   # the graveyard keeps only the last 50
    # unlock ghost and switch hero
    if "boss1" in m["achievements"]:
        app.fill_char_menu()
        app.char_var.set("ghost"); app.change_character()
        pump(app, 400)
        assert any(g["char"]=="ghost" for g in m["graveyard"]) or app.run["char"]=="ghost", "ghost never played"
    app.run["items"] = [{"key": k, "rar": "legendary"} for k in list(M.ITEMS)[:12]]
    app.refresh_look(); w_full = app.frames_fx[0][0].width()
    app.run["items"] = []; app.refresh_look(); w_empty = app.frames_fx[0][0].width()
    assert w_full == w_empty                       # image always the size of LOOK_BOX: fixed pivot
    app.run["items"] = [{"key": "horns", "rar": "rare"}]; app.refresh_look()
    for size in ("Small", "Large"): app.size_var.set(size); app.change_size()
    app.evolve(); app.reload_chars(); app.give_up()
    assert not hasattr(app, "acc_items")
    app.show_stats(); app.show_graveyard(); app.show_achievements()
    for size in ("Small","Large"): app.size_var.set(size); app.change_size()
    app.give_up(); app.reload_chars(); app.toggle_top()
    e = types.SimpleNamespace(x_root=50,y_root=50,x=app.pcx,y=app.base_y-10)
    app.on_press(e); app.on_release(e); app.on_menu(e)
    app.state["last_fed"] = time.time()-20*60; app.busy_until=0; app.run["energy"]=0; app.tick()
    if app.run["dead"]: app.new_run(announce=False)   # the pump may stop right after a death (depends on the clock)
    app.last_rest_heal=0; app.run["hp"]=1; PENDING.clear(); app.demo=False; app.reader.poll=lambda:(0.0,0); app.poll()
    assert app.run["hp"]==2, app.run["hp"]
    app.quit()
    st = tp.DATA_DIR/("state-demo.json" if demo else "state.json"); assert st.is_file()
    # reload from disk keeps meta
    app2 = tp.PetApp(Args(demo=demo)); PENDING.clear(); app2.rng = random.Random(SEED)
    assert app2.meta["runs"] == m["runs"], (app2.meta["runs"], m["runs"])
    # interactive mode: choice window
    if app2.run["dead"]: app2.new_run(announce=False)
    app2.state["mode"] = "interactive"; app2.run["pending"] = None
    app2.run["energy"] = 5 * M.ROOM_COST; app2.busy_until = 0
    offer = {"key": "dagger", "rar": "rare", "source": "chest"}; app2.run["pending"] = dict(offer)
    app2.pending_since = time.time(); room_before = (app2.run["floor"], app2.run["room"])
    app2.tick(); assert (app2.run["floor"], app2.run["room"]) == room_before   # waits for the window
    app2.feed(300_000, 300_000); app2.tick(); assert app2.run["pending"]       # tokens go into the backpack
    app2.pending_since = time.time() - M.CHOICE_WINDOW_S - 1; app2.tick()
    assert app2.run["pending"] is None                                       # resolved by itself and moved on
    app2.run["pending"] = dict(offer, key="pot_lid"); app2.pending_since = time.time(); app2.choose("consume")
    assert app2.run["pending"] is None and not any(i["key"] == "pot_lid" for i in app2.run["items"])
    assert app2.choice_win is None
    # giving up with an open choice: the panel closes and the new run does not inherit the offer
    app2.run["pending"] = dict(offer, key="beanie"); app2.busy_until = 0; app2.tick()
    assert app2.choice_win is not None
    app2.give_up(); assert app2.run["pending"] is None and app2.choice_win is None
    # choosing in a dead run changes nothing
    app2.run["pending"] = dict(offer, key="beanie"); app2.run["dead"] = True
    before = (list(app2.run["items"]), app2.run["hp"]); app2.choose("take")
    assert (app2.run["items"], app2.run["hp"]) == before
    app2.run["dead"] = False; app2.run["pending"] = None
    app2.run["pending"] = dict(offer, key="beanie"); app2.pending_since = time.time() - 999
    app2.run["energy"] = 0; app2.busy_until = 0; app2.tick(); assert app2.run["pending"]   # no energy: waits
    app2.mode_var.set("auto"); app2.change_mode(); assert app2.run["pending"] is None    # switching to auto resolves it
    # reopening with a pending offer in the save
    app2.state["mode"] = "interactive"; app2.run["pending"] = dict(offer, key="hat"); app2.quit()
    app3 = tp.PetApp(Args(demo=demo)); PENDING.clear(); app3.rng = random.Random(SEED)
    app3.busy_until = 0; app3.run["energy"] = 5 * M.ROOM_COST
    app3.tick(); assert app3.run["pending"] and app3.pending_since is not None
    # pump in both modes
    app3.state["mode"] = "interactive"; pump(app3, 300)
    app3.mode_var.set("auto"); app3.change_mode(); pump(app3, 100)
    app3.quit()

# session/week bars (optional statusline): they show, show "—" when stale, disappear without the file
app4 = tp.PetApp(Args()); PENDING.clear(); app4.rng = random.Random(SEED)
h0 = app4.H; assert set(app4.limit_rows) == {"session", "week"}   # no terminal: tokens-only mode
cv = app4.canvas
def row_text(k): return cv.it[app4.limit_rows[k][1]][2]["text"]
tp.add_usage(app4.state, time.time() - 60, 1_200_000); app4.state["usage_hist_since"] = 0; app4.refresh_limits()
assert row_text("session") == "Sessão  1.2M", row_text("session")
lim_file = tp.DATA_DIR / "limits.json"
lim_file.write_text(json.dumps({"five_hour": {"used_percentage": 42, "resets_at": time.time() + 3600},
                                "seven_day": {"used_percentage": 95, "resets_at": time.time() - 5},
                                "updated": time.time()}))
app4.refresh_limits()
assert app4.H == h0 and app4.limits["session"][0] == 42 and app4.limits["week"][0] is None
assert row_text("session") == "Sessão  42%"
app4.limits["updated"] = time.time() - 3600; app4.update_limits()
assert row_text("session") == "Sessão  ~42%", row_text("session")          # estimated with the factor
app4.refresh_limits(); app4.update_panel(); pump(app4, 20)
for size in ("Small", "Medium", "Large"):
    app4.size_var.set(size); app4.change_size(); app4.update_limits()
    for k, row in app4.limit_rows.items():
        lx0, lx1, back = row[4], row[5], row[7]
        assert cv.bbox(row[1])[2] < lx0 < lx1 < cv.bbox(row[3])[0], (size, k, cv.bbox(row[1]), lx0, lx1, cv.bbox(row[3]))
        assert cv.bbox(back)[2] < cv.bbox(row[3])[0]
# simultaneous floaters do not share a spot, nor cover the panel
for f in app4.floaters[:]:
    for i in f[0]: cv.delete(i)
app4.floaters.clear()
for i in range(6): app4.floater(f"-{i}", x=app4.fcx)
boxes = [cv.bbox(f[0][0]) for f in app4.floaters]
for i, a in enumerate(boxes):
    assert a[3] < app4.panel_y
    for b in boxes[i+1:]:
        assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]), (a, b)
lim_file.unlink(); app4.refresh_limits()
assert app4.limits is None and set(app4.limit_rows) == {"session", "week"}
app4.quit()

runs_file = tp.DATA_DIR / "runs.jsonl"; demo_file = tp.DATA_DIR / "runs-demo.jsonl"
lines = [json.loads(l) for l in runs_file.read_text(encoding="utf-8").splitlines()]
assert lines and all(l["version"] == M.BALANCE_VERSION for l in lines)
assert any(l["gave_up"] for l in lines) and any(not l["gave_up"] for l in lines)
assert demo_file.exists()                                        # the demo saves separately
assert all(isinstance(l["achievements"], list) for l in lines)
# a failed save only logs
real_dir = tp.DATA_DIR; tp.DATA_DIR = runs_file / "sub"          # "folder" inside a file: mkdir fails
tp.append_run_record({"x": 1}, False); tp.DATA_DIR = real_dir
# old save: a run without ach_start/consumed/floor ends without an exception
app5 = tp.PetApp(Args()); PENDING.clear(); app5.rng = random.Random(SEED)
app5.run.pop("ach_start", None); app5.run.pop("consumed", None)
app5.run["items"] = [{"key": "dagger", "rar": "common"}]; M.migrate_run(app5.run)
app5.give_up(); app5.quit()
# new combat: stable W when changing the size, hordes on screen, status
app6 = tp.PetApp(Args()); PENDING.clear(); app6.rng = random.Random(SEED)
app6.size_var.set("Medium"); app6.change_size()                # app4 left "Large" in the save
w0 = app6.W
for size in ("Small", "Large", "Medium"): app6.size_var.set(size); app6.change_size()
assert app6.W == w0
seen_horde = False
for _ in range(600):
    app6.busy_until = 0
    if app6.run["dead"]:
        app6.respawn_at = 1
    app6.run["energy"] = 10 * M.ROOM_COST
    app6.run["floor"] = max(app6.run["floor"], 3)
    app6.tick()
    fns = PENDING[:]; PENDING.clear()
    for fn in fns:
        if fn is None or getattr(fn, "__name__", "") in ("tick", "poll"): continue
        fn()
    seen_horde = seen_horde or any(k == "horde" for k in getattr(app6, "_last_kind", [""]))
assert seen_horde
# area elemental attack (temporary _t item): tint and flash on the enemy; the pet status disappears at the end of the fight
M.ITEMS["_t"] = {"name": "t", "fx": {"burn": 0.6, "area": True}, "rarities": ["common"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "top", "art": "dagger"}}
inks, status_pet = [], []
draw0, set0 = app6.draw_foe, app6.set_pet_status
app6.draw_foe = lambda i, status=None: (status and inks.append(status), draw0(i, status))
app6.set_pet_status = lambda s: (s and status_pet.append(s), set0(s))
for _ in range(400):
    app6.busy_until = 0
    if app6.run["dead"]:
        app6.respawn_at = 1
    app6.run["items"] = [{"key": "_t", "rar": "common", "floor": 1}]
    app6.run["energy"] = 10 * M.ROOM_COST
    app6.run["floor"] = max(app6.run["floor"], 5)
    app6.tick()
    fns = PENDING[:]; PENDING.clear()
    for fn in fns:
        if fn is None or getattr(fn, "__name__", "") in ("tick", "poll"): continue
        fn()
    assert app6.pet_status is None, app6.pet_status
app6.run["items"] = []; del M.ITEMS["_t"]; app6.refresh_look()
del app6.draw_foe, app6.set_pet_status
assert inks and status_pet, (len(inks), len(status_pet))
# pet tinted in the status color (only when it changes); without a status it goes back to normal; a new run clears the status
normal = app6.look_maps[0]
app6.set_pet_status("poison"); assert app6.pet_status == "poison" and app6.look_maps[0] != normal
app6.set_pet_status(None); assert app6.look_maps[0] == normal
app6.set_pet_status("burn"); app6.new_run(); assert app6.pet_status is None
# double hit and helper (temporary _t item): hundreds of rooms without exceptions; "x2" and the helper's number on screen
M.ITEMS["_t"] = {"name": "t", "fx": {"double": 0.5, "helper": 3}, "rarities": ["common"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "float", "art": "dagger"}}
texts, fl0 = [], app6.floater
app6.floater = lambda text, *a, **k: (texts.append((text, k.get("x"))), fl0(text, *a, **k))
steps_seen = []
hit0 = app6.anim_hit
app6.anim_hit = lambda h, *a: (steps_seen.append(h), hit0(h, *a))
for _ in range(300):
    app6.busy_until = 0
    if app6.run["dead"]:
        app6.respawn_at = 1
    app6.run["items"] = [{"key": "_t", "rar": "common", "floor": 1}]
    app6.run["energy"] = 10 * M.ROOM_COST
    app6.tick()
    fns = PENDING[:]; PENDING.clear()
    for fn in fns:
        if fn is None or getattr(fn, "__name__", "") in ("tick", "poll"): continue
        fn()
app6.run["items"] = []; del M.ITEMS["_t"]; app6.refresh_look()
# heal_room / heal_floor: "+N ♥" floater when the item heals on entering the room or on the stairs
er0, PENDING[:] = M.enter_room, []
M.enter_room = lambda *a, **k: {"kind": "shop", "name": "Loja", "sprite": "shop", "lines": [], "won": False,
                                "died": False, "item_heal": 37}
app6.play_room()
M.enter_room = er0
for fn in PENDING[:]:
    if fn is not None and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
PENDING.clear()
assert ("+37 ♥", None) in texts, texts[-5:]
# synergy log lines: a new discovery floats in gold, a known one in the normal color
cols = []
fl1 = app6.floater
app6.floater = lambda text, color=tp.TEXT, *a, **k: (cols.append((text, color)), fl1(text, color, *a, **k))
for new in (True, False):
    line = f"{'New synergy' if new else 'Synergy'}: Shatter!"
    M.enter_room = lambda *a, **k: {"kind": "shop", "name": "Loja", "sprite": "shop", "lines": [line], "won": False,
                                    "died": False, "synergies": [{"key": "shatter", "new": new}]}
    PENDING[:] = []; app6.play_room()
    for fn in PENDING[:]:
        if fn is not None and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
    assert (tp._t(line), tp.GOLD if new else tp.TEXT) in cols, (new, cols[-4:])
M.enter_room = er0; app6.floater = fl1
del app6.floater, app6.anim_hit
assert any(h["who"] == "helper" for h in steps_seen) and any(h["double"] for h in steps_seen)
assert any(t.endswith(" x2") for t, _ in texts)
assert any(t == f"-{h['dmg']}" and x is None for h in steps_seen if h["who"] == "helper" for t, x in texts)
app6.show_stats(); app6.quit()
# animated elemental looks: 3 phases per frame (also when blinking/sleeping); without animation, a single phase
app7 = tp.PetApp(Args()); PENDING.clear(); app7.rng = random.Random(SEED)
ELEM = ("flames", "sparks", "poison_drops", "frost")
for t in ELEM:   # temporary items with each animated look
    M.ITEMS["_" + t] = {"name": t, "fx": {"atk": 1}, "rarities": ["common"], "consume": {"heal": 1},
                        "look": {"type": t}}
app7.run["items"] = [{"key": "_" + t, "rar": "common", "floor": 1} for t in ELEM]
t0 = time.perf_counter(); app7.refresh_look(); dt = time.perf_counter() - t0
assert dt < 3.0, dt
assert len(app7.frames_fx[0]) == 3 and all(len(q) == 3 for q in app7.frames_fx)
assert len(app7.sleep_fx) == 3 and (app7.blink_fx is None or len(app7.blink_fx) == 3)
app7.set_pet_status("freeze"); assert all(len(q) == 3 for q in app7.frames_fx)   # tint in every phase
app7.set_pet_status(None)
app7.busy_until = 0; app7.run["energy"] = 0; app7.tick()
app7.run["items"] = []; app7.refresh_look(); assert len(app7.frames_fx[0]) == 1 and len(app7.sleep_fx) == 1
for t in ELEM: M.ITEMS.pop("_" + t)
app7.quit()
# a hero with invalid stats is ignored (and logged) when loading, not on every tick
folder = Path(tempfile.mkdtemp())
for name, stats in (("ruim1", {"spd": "rapido"}), ("ruim2", {"hp": None}), ("bom", {"spd": 12, "hp": "18"})):
    (folder / name).mkdir(); (folder / name / "a.png").write_bytes(b"x")
    (folder / name / "character.json").write_text(json.dumps({"stats": stats, "stages": [{"frames": ["a.png"]}]}))
heroes = tp.load_png_characters(folder)
assert [c.key for c in heroes] == ["bom"] and heroes[0].stats["spd"] == 12.0 and heroes[0].stats["hp"] == 18
assert tp.LOG_FILE.read_text().count("ignored") >= 2
# trait: an invalid key ignores the hero (and logs); a valid key reaches the CharacterDef
for name, tr in (("tr_ruim", {"fly": 1}), ("tr_bom", {"poison": 0.1})):
    (folder / name).mkdir(); (folder / name / "a.png").write_bytes(b"x")
    (folder / name / "character.json").write_text(json.dumps({"trait": tr, "stages": [{"frames": ["a.png"]}]}))
heroes = tp.load_png_characters(folder)
assert "tr_ruim" not in [c.key for c in heroes] and [c.trait for c in heroes if c.key == "tr_bom"] == [{"poison": 0.1}]
assert "fly" in tp.LOG_FILE.read_text(encoding="utf-8")
# spritesheet heroes: synthetic sheet of 9 rows x 8 frames, opaque body in the middle of each cell
sys.path.insert(0, str(ROOT / "tests")); from _png import sheet_png   # real PNG: exercises the decoder
def ready(app):   # waits for the sheet thread and runs the pending afters (the fake Tk has no mainloop)
    for st in app.char.stages:
        if st.get("thread"): st["thread"].join()
    for _ in range(5):
        fns = PENDING[:]; PENDING.clear()
        for fn in fns:
            if fn and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
chars = Path(tempfile.mkdtemp())
sheet_png(chars/"x"/"spritesheet.png", 512, 576, rises={4: 10})   # 8x9 grid of 64 px; "jumping" 10 px higher
x = {c.key: c for c in tp.load_png_characters(chars)}["x"]
assert "states" not in x.stages[0]                               # discovery does not cut the sheet
st = tp.complete_stage(x.stages[0]); assert "error" not in st, st.get("error")
assert set(st["states"]) == set(tp.sheet.STATES) and all(len(v) == 8 for v in st["states"].values())
# alpha-8 noise on the whole background does not count as opaque: the box is the body, not the cell
assert st["states"]["failed"][0][2] == (16, 5 * 64 + 6, 48, 5 * 64 + 62) and st["states"]["failed"][0][3] == 2
assert tp.spec_height(st["frames"][0]) == 28 and tp.spec_k(st["frames"][0]) == 2   # 56 px trimmed, N = 2
pm = tp.spec_to_map(st["frames"][0], 2); pj = tp.spec_to_map(st["states"]["jumping"][0], 2)
assert max(y for _, y in pm) == 31 and min(y for _, y in pm) == 9 and set(pm.values()) == {"#c86432"}
assert max(y for _, y in pj) == 26 and min(x for x, _ in pj) == min(x for x, _ in pm)   # the jump leaves the ground, same pivot
# rows with fewer than 8 frames: an empty cell does not become a frame (never blinks invisible); a state without frames uses idle
sheet_png(chars/"v"/"spritesheet.png", 512, 576, empties={0: 2, 3: 5, 6: 8})
v = tp.complete_stage({c.key: c for c in tp.load_png_characters(chars)}["v"].stages[0])
assert "error" not in v, v.get("error")
cont = {e: len(q) for e, q in v["states"].items()}
assert cont["idle"] == 6 and cont["waving"] == 3 and cont["waiting"] == 6 and cont["run_r"] == 8, cont   # empty waiting (row 6) -> idle
assert all(tp.spec_to_map(sp, 2) for q in v["states"].values() for sp in q)   # no blank frame
# PNG in a format the decoder cannot read: ignored (and logged) at discovery
(chars/"q").mkdir(); (chars/"q"/"spritesheet.png").write_bytes((chars/"x"/"spritesheet.png").read_bytes()[:24] + bytes([16]) + bytes(5))
assert "q" not in {c.key for c in tp.load_png_characters(chars)} and "unsupported PNG format" in tp.LOG_FILE.read_text(encoding="utf-8")
# Petdex in a temporary HOME: a PNG becomes a community hero; WebP only is ignored; an invalid pet.json does not crash
pets = Path(home)/".petdex"/"pets"
sheet_png(pets/"y"/"spritesheet.png", 512, 576); (pets/"y"/"pet.json").write_text('{"name": "Yzinho", "x": 1}')
(pets/"w").mkdir(); (pets/"w"/"spritesheet.webp").write_bytes(b"w")
sheet_png(pets/"z"/"a.png", 500, 600); (pets/"z"/"pet.json").write_text("{nada")   # automatic cut
sheet_png(Path(home)/".codex"/"pets"/"g"/"spritesheet.png", 1536, 1872)
big = (Path(home)/".codex"/"pets"/"g"/"spritesheet.png").read_bytes()
for i in range(4):
    (Path(home)/".codex"/"pets"/f"g{i}").mkdir(); (Path(home)/".codex"/"pets"/f"g{i}"/"spritesheet.png").write_bytes(big)
t0 = time.time(); dex = {c.key: c for c in tp.load_petdex_characters()}
dt = time.time() - t0; assert dt < 0.5, dt                        # 5 big sheets: only the header is read
y = dex["petdex:y"]
assert y.name == "Yzinho" and y.community and y.unlock is None and y.stats["hp"] == 20 and y.stats["spd"] == 10
assert "petdex:w" not in dex and "convert it to PNG" in tp.LOG_FILE.read_text()
z = tp.complete_stage(dex["petdex:z"].stages[0]); assert dex["petdex:z"].name == "z" and len(z["states"]["idle"]) == 8
assert "petdex:y" in tp.all_characters()
t0 = time.time()
app8 = tp.PetApp(Args()); PENDING.clear(); app8.rng = random.Random(SEED)
app8.char_var.set("petdex:g"); app8.change_character(); app8.new_run()
assert app8.char.key == "petdex:g" and "states" not in app8.char.stages[0]   # still cutting: previous look
ready(app8)
g = app8.char.stages[0]["frames"]; assert len(g) == 8 and tp.spec_height(g[0]) <= 48
assert app8.hero_k >= 2 and set(app8.states_fx) == set(tp.sheet.STATES)
dt = time.time() - t0; assert dt < 3.0, dt
pump(app8, 300); app8.quit()
# sheet states in the GUI: each state has its own images, composed once
app9 = tp.PetApp(Args()); PENDING.clear(); app9.rng = random.Random(SEED)
app9.char_var.set("petdex:y"); app9.change_character(); app9.new_run(); ready(app9)
fx = app9.states_fx; assert set(fx) == set(tp.sheet.STATES)
def composed(): return {ck[0] for ck in app9.fx_cache if ck[1] == app9.fx_sig}
assert composed() <= {"idle"}, composed()
def showing(): return cv9.it[app9.sprite][2]["image"]
cv9 = app9.canvas
def all_(e): return {id(i) for q in fx[e] for i in q}
app9.busy_until = time.time() + 99; app9.state["last_fed"] = time.time()
app9.tick(); assert id(showing()) in all_("idle")
app9.state["last_fed"] = time.time() - tp.REST_AFTER_S - 5; app9.busy_until = 0
app9.run["energy"] = 0; app9.tick(); assert id(showing()) in all_("waiting")
app9.run["pending"] = {"key": next(iter(M.ITEMS)), "rar": "common"}; app9.busy_until = time.time() + 99
app9.tick(); assert id(showing()) in all_("review")          # the choice beats resting
app9.run["pending"] = None; app9.state["last_fed"] = time.time()
app9.fight_until = time.time() + 5; app9.tick(); assert id(showing()) in all_("running")
app9.fight_until = 0
app9.on_release(types.SimpleNamespace(x=app9.pcx, y=app9.base_y - 1)); app9.tick()
assert id(showing()) in all_("waving")
app9.run["dead"] = True; app9.meta["graveyard"].append({"killer": "x", "floor": 1, "room": 1, "kills": 0, "gold": 0, "kind": "monster"})
# taking an item recomposes only idle and the state on screen; another state is composed once, the 1st time it appears
app9.run["items"].append({"key": next(iter(M.ITEMS)), "rar": "common"}); app9.refresh_look()
fx = app9.states_fx; assert composed() == {"idle", "waving"}, composed()
assert fx["jumping"] is fx["jumping"] and composed() == {"idle", "waving", "jumping"}
app9.on_death(); app9.tick(); assert id(showing()) in all_("failed")
for fn in PENDING[:]:
    if fn and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
PENDING.clear(); assert showing() is app9.art_img("tombstone")
app9.new_run(); pump(app9, 400)
if not any(i["key"] == "dagger" for i in app9.run["items"]):    # an asymmetric look, or mirroring changes nothing
    app9.run["items"].append({"key": "dagger", "rar": "common"}); app9.refresh_look()
# Flip hero: mirrors the final map around the pivot (x -> 16k-1-x), swaps run_r/run_l, persists in the state
app9.flip_var.set(False); app9.toggle_flip(); assert not app9.flip
normal = app9.look_maps; k = app9.hero_k
app9.flip_var.set(True); app9.toggle_flip()
assert app9.flip and app9.state["flip"][app9.run["char"]] is True and app9.fx_sig[4] is True
assert app9.look_maps == [{(16 * k - 1 - x, y): c for (x, y), c in m.items()} for m in normal] and app9.look_maps != normal
n0 = len(app9.fx_cache); app9.states_fx["run_r"]; app9.states_fx["run_r"]; assert len(app9.fx_cache) == n0 + 1   # composes once
saved = json.loads((tp.DATA_DIR / "state.json").read_text(encoding="utf-8")); assert saved["flip"][app9.run["char"]] is True
app9.fill_char_menu(); app9.quit()
# Slime (grid) and Ghost (sheet) have the 9 states, >= 4 frames each, same pivot (base at y = 15)
app10 = tp.PetApp(Args()); PENDING.clear(); app10.char_var.set("slime"); app10.change_character(); app10.new_run()
assert app10.char.key == "slime" and set(app10.states_fx) == set(tp.sheet.STATES)
assert app10.current_state(time.time(), True) == "waiting"
for st in tp.all_characters()["slime"].stages + tp.all_characters()["ghost"].stages:
    if st.get("sheet"): tp.complete_stage(st)
    assert set(st["states"]) == set(tp.sheet.STATES) and all(len(v) >= 4 for v in st["states"].values())
    base = {e: max(y for sp in v for _, y in tp.spec_to_map(sp, 1)) for e, v in st["states"].items() if e != "jumping"}
    assert set(base.values()) == {15}, (st["title"], base)
    assert max(tp.spec_height(sp) for v in st["states"].values() for sp in v) > 16 or not st.get("sheet")   # Ghost 32 px
app10.run["dead"] = True; app10.meta["graveyard"].append({"killer": "x", "floor": 1, "room": 1, "kills": 0, "gold": 0, "kind": "monster"})
app10.on_death(); app10.tick(); assert app10.state_seen == "failed"
app10.new_run(); pump(app10, 300); app10.quit()
# test_slime_32: 3 stages, 9 states, 32x32 frames
sl = tp.builtin_characters()[0]
assert [s["title"] for s in sl.stages] == ["Droplet", "Slime", "Slime Monarch"] and sl.stage_floors == [1, 4, 10]
for st in sl.stages:
    assert set(st["states"]) == set(tp.sheet.STATES)
    assert all(len(sp[1]) == 32 and all(len(l) == 32 for l in sp[1]) for v in st["states"].values() for sp in v)
    assert len(st["blink"][1]) == 32 and st["blink"][1] != st["frames"][0][1]
# hero with an unlock: locked without the achievement; next_char on it falls back to the Slime
app12 = tp.PetApp(Args()); PENDING.clear()
fake = tp.CharacterDef("fakeouro", "Fake", app12.chars["slime"].stages, unlock="gold300"); app12.chars["fakeouro"] = fake
app12.meta["achievements"] = [a for a in app12.meta["achievements"] if a != "gold300"]
assert not app12.is_unlocked(fake) and M.ACHIEVEMENTS["gold300"]
app12.meta["next_char"] = "fakeouro"; app12.new_run(announce=False); assert app12.run["char"] == "slime"
app12.meta["achievements"].append("gold300"); assert app12.is_unlocked(fake)
app12.new_run(announce=False); assert app12.run["char"] == "fakeouro"
app12.meta["achievements"].remove("gold300"); app12.demo = True; assert app12.is_unlocked(fake)   # the demo unlocks everyone
app12.quit()
# test_hero32_same_size: k = 2 and the drawn frame is the size of the old 16 px one
app11 = tp.PetApp(Args()); PENDING.clear(); app11.char_var.set("slime"); app11.change_character(); app11.new_run()
app11.refresh_look()
assert app11.hero_k == 2 and abs(32 * app11.hero_px - 16 * app11.px) <= 2, (app11.hero_px, app11.px)
app11.run["stage"] = 3; app11.load_images(); app11.refresh_look()   # old save with 4 stages: does not break
app11.quit()
# pixel art menu: opens, the grid lists every hero, a locked one does not switch, an unlocked one does, no leaked windows
ALIVE = set()
class Window(Tk):
    def __init__(self, *a, **k): ALIVE.add(self)
    def destroy(self): ALIVE.discard(self)
    def geometry(self, g=None): self.geo = g
tkinter.Toplevel = Window
appm = tp.PetApp(Args()); PENDING.clear(); appm.close_choice(); ALIVE.clear()
appm.meta["achievements"] = ["boss1"]; appm.meta["next_char"] = "slime"; appm.char_var.set("slime")
ev = types.SimpleNamespace(x_root=1900, y_root=1070)
for _ in range(2):
    appm.on_menu(ev); assert appm.menu_win in ALIVE
    appm.menu_do(appm.show_heroes); assert appm.menu_win is None and appm.heroes_win in ALIVE
    assert set(appm.hero_cards) == set(appm.chars)
    bloq = [k for k, c in appm.chars.items() if not appm.is_unlocked(c)]
    assert bloq and all(appm.hero_cards[k] is None for k in bloq)
    appm.show_heroes(); appm.on_menu(ev); assert len(ALIVE) == 2     # reopening replaces the window, does not stack
    appm.close_win(appm.menu_win); appm.close_win(appm.heroes_win); assert not ALIVE
appm.show_heroes(); appm.hero_cards["ghost"](); assert appm.meta["next_char"] == "ghost" and not ALIVE - {appm.popup_win}
for fn in PENDING[:]:
    if fn and getattr(fn, "__name__", "") == "wait": fn()    # thumbnails thread
# achievements, graveyard and status windows: empty and full, reopening replaces the window, closing does not leak
import art
assert set(art.ACH_ART) == set(M.ACHIEVEMENTS)
fields = set(M.stats(appm.run)) | {"grow"}
assert fields <= set(art.STAT_ART) and fields == {k for k, *_ in tp.STAT_LINES}
JAN = (("grave_win", appm.show_graveyard), ("ach_win", appm.show_achievements), ("stats_win", appm.show_stats), ("profile_win", appm.show_profile))
def open_close():
    for _ in range(2):
        for attr, fn in JAN:
            fn(); fn(); assert getattr(appm, attr) in ALIVE
        assert len(ALIVE - {appm.popup_win}) == len(JAN)
        for attr, _ in JAN:
            appm.close_win(getattr(appm, attr)); assert getattr(appm, attr) is None
        assert not ALIVE - {appm.popup_win}
appm.meta.update(graveyard=[], achievements=[]); appm.run.update(items=[], consumed=[], trait={})
appm.state.update(usage_hist={}, daily={}, tokens_total=0); appm.limits = None
open_close()
deaths = [("Rat", "monster"), ("Rat King", "boss"), ("Poison", "status"), ("Burn", "status"), ("Mimic", "mimic"),
          ("Trap", "trap"), ("Gave up", "gave_up"), ("Coisa Nova", "monster")]
appm.meta["graveyard"] = [{"run": i, "char": "naoexiste" if i % 3 else "slime", "floor": 9, "room": 2,
                           "killer": deaths[i % 8][0], "kind": deaths[i % 8][1], "gold": 5, "kills": 3, "date": "2026-11-13",
                           "items": [k if i % 2 else {"key": k, "rar": "epic"} for k in list(M.ITEMS)[:i]]}
                          for i in range(50)]
appm.meta["achievements"] = list(M.ACHIEVEMENTS)[::2]
appm.run.update(items=[{"key": k, "rar": "legendary"} for k in M.ITEMS], kills=40, shield=3, trait={"dodge": 0.1},
                consumed=[{"key": k, "rar": "common", "floor": 1} for k in list(M.ITEMS)[:4]])
assert len(tp.stat_lines(appm.run, M.stats(appm.run))) == len(tp.STAT_LINES)   # every field shows up
for d in range(8): tp.add_usage(appm.state, time.time() - d * 86400, 1e6 * d)
appm.state.update(tokens_total=47_000_000, daily={date.today().isoformat(): 5e6})
appm.limits = {"session": (42, time.time() + 3600), "week": (None, None), "updated": time.time()}
open_close()
# movable windows: dragging by the bar changes the geometry and saves it; reopening uses the position; off screen goes back beside the pet
appm.show_achievements(); w = appm.ach_win
w.progress_bar.binds["<Button-1>"](types.SimpleNamespace(x_root=310, y_root=305))
w.progress_bar.binds["<B1-Motion>"](types.SimpleNamespace(x_root=510, y_root=405))
assert w.geo == "+500+400" and appm.state["windows"]["ach_win"] == [500, 400], w.geo
appm.show_achievements(); assert appm.ach_win.geo == "+500+400", appm.ach_win.geo
appm.state["windows"]["ach_win"] = [500, 1070]; appm.show_achievements(); assert appm.ach_win.geo == "+500+960"
appm.state["windows"]["ach_win"] = [5000, -900]; appm.show_achievements(); assert appm.ach_win.geo == "+144+300"
appm.root.winfo_vrootx = lambda: -1680; appm.root.winfo_vrootwidth = lambda: 3600   # monitor on the left
appm.state["windows"]["ach_win"] = [-1000, 200]; appm.show_achievements(); assert appm.ach_win.geo == "+-1000+200"
del appm.root.winfo_vrootx, appm.root.winfo_vrootwidth
appm.close_win(appm.ach_win)
# scrollbar: dragging the thumb and clicking the track call yview_moveto with the right fraction
cv = tkinter.Canvas(); tr = appm.scrollbar(None, Tk(), cv, 100)
cv.cfg["yscrollcommand"]("0.0", "0.25")                      # 1/4 visible: thumb from 0 to 25 px
ev = lambda y: types.SimpleNamespace(y=y)
tr.binds["<Button-1>"](ev(10)); assert cv.moveto == 0.0       # grabbed the thumb 10 px from the top
tr.binds["<B1-Motion>"](ev(60)); assert abs(cv.moveto - 0.5) < 1e-9
tr.binds["<ButtonRelease-1>"](ev(60)); tr.binds["<B1-Motion>"](ev(0)); assert abs(cv.moveto - 0.5) < 1e-9   # released: does not drag
tr.binds["<Button-1>"](ev(90)); assert abs(cv.moveto - 0.75) < 1e-9   # track at the bottom: goes to the end (capped at 1 - 0.25)
tr.binds["<Button-1>"](ev(5)); assert cv.moveto == 0.0
# rounded corners: only straight rectangles, the (0,0) corner is left out and the inner area is fully covered
assert tp.steps(8) == [5, 3, 2, 1, 1, 0, 0, 0] and tp.steps(0) == []
cv = tkinter.Canvas(); tp.rounded_rect(cv, 0, 0, 40, 20, 8, "#000000", "#ffffff", 2, tag="t", extra=("card:1",))
rs = [c for kind, c, k in cv.it.values()]
covers = lambda x, y, tag: any(c[0] <= x < c[2] and c[1] <= y < c[3] for kind, c, k in cv.it.values() if tag in k["tags"])
assert not covers(0, 0, "t") and not covers(39, 19, "t") and covers(20, 10, "t_f") and covers(0, 10, "t_b") and not covers(0, 10, "t_f")
assert all(0 <= c[0] <= c[2] <= 40 and 0 <= c[1] <= c[3] <= 20 for c in rs) and cv.bbox("card:1") == (0, 0, 40, 20)
# items page: every item has a card; a locked one shows the silhouette and the achievement, no values; the demo unlocks everything
texts = lambda cv: [k.get("text", "") for kind, _, k in cv.it.values() if kind == "text"]
rar_txt = lambda cv: [t for t in texts(cv) if any(t.startswith(tp._t(n) + ":") for n in M.RAR_NAMES.values())]
for achs in ([], list(M.ACHIEVEMENTS)):
    appm.meta["achievements"] = achs
    for filter_by in ("all", "unlocked", "locked", "all"):
        appm.items_filter = filter_by; appm.show_items(); assert appm.items_win in ALIVE
    names = set(texts(appm.items_cv))
    assert all(tp._t(it["name"]) in names for it in M.ITEMS.values())
    bloq = [k for k in M.ITEMS if not appm.item_unlocked(k)]
    assert len(bloq) == (len(M.ITEMS) - len(M.unlocked_items(appm.meta)))
    assert bool(bloq) == (not achs)
    for k in M.ITEMS:
        cv = tkinter.Canvas(); appm.item_card(cv, 0, 0, k)
        assert len(rar_txt(cv)) == (0 if k in bloq else len(M.ITEMS[k]["rarities"])), k
    appm.close_win(appm.items_win); assert not ALIVE - {appm.popup_win}
appm.meta["achievements"] = []; appm.demo = True; assert all(appm.item_unlocked(k) for k in M.ITEMS); appm.demo = False
# synergies tab: one card per synergy; a secret one undiscovered shows only "???" (no name, no hint, no icons), in pt and en
import i18n
appm.meta["synergies"] = {}
secret = [k for k, s in M.SYNERGIES.items() if s["secret"]]
assert len(secret) == 3
for lang in ("pt", "en"):
    i18n.set_lang(lang)
    appm.items_tab = "synergies"; appm.show_items(); assert appm.items_win in ALIVE
    assert all(appm.items_cv.bbox(f"card:{k}") != (100, 0, 140, 10) for k in M.SYNERGIES), lang
    for k, s in M.SYNERGIES.items():
        cv = tkinter.Canvas(); appm.synergy_card(cv, 0, 0, k)
        tx = texts(cv)
        if k in secret:
            assert tx == ["???"], (k, tx)
        else:
            assert tp._t(s["name"]) in tx and tp._t(s["hint"]) in tx, (k, tx)
    allt = " | ".join(texts(appm.items_cv))
    assert not any(tp._t(M.SYNERGIES[k]["name"]) in allt or tp._t(M.SYNERGIES[k]["hint"]) in allt for k in secret)
    appm.close_win(appm.items_win)
appm.meta["synergies"] = {k: {"runs": 7, "first_run": 3} for k in M.SYNERGIES}
for k, s in M.SYNERGIES.items():
    cv = tkinter.Canvas(); appm.synergy_card(cv, 0, 0, k); tx = texts(cv)
    assert tp._t(s["name"]) in tx and tp._t("Active in {n} runs", n=7) in tx and tp._t("Discovered in run #{n}", n=3) in tx, (k, tx)
    assert (tp._t(M.fx_text(s["fx"])) if s["fx"] else tp._t(tp.REACTION_TEXT[k])) in tx, (k, tx)
appm.items_tab = "items"; i18n.set_lang("pt")
# Status window lists the active synergies; Profile shows the counter
appm.run["synergies"] = ["shatter", "hearthfire"]
TXT = []; _tl = tkinter.Label
tkinter.Label = type("L", (Wid,), {"__init__": lambda self, *a, **k: (Wid.__init__(self), TXT.append(k.get("text", "")))[0]})
appm.show_stats(); appm.show_profile(); tkinter.Label = _tl
blob = " | ".join(TXT)
assert tp._t("Shatter") in blob and tp._t("Hearthfire") in blob, blob[:400]
assert tp._t("Synergies {n}/{total}", n=len(appm.meta["synergies"]), total=len(M.SYNERGIES)) in blob
appm.run["synergies"] = []; appm.meta["synergies"] = {}
appm.close_win(appm.stats_win); appm.close_win(appm.profile_win)
# hero grid: ours (module in heroes/) apart from the imported ones (characters/ without a module, Petdex)
assert tp.own_hero("slime") and tp.own_hero("ghost")
assert not tp.own_hero("bitty-openpets") and not tp.own_hero("naoexiste") and not tp.own_hero("x.y")
# language: the menu's EN chip switches the HUD and reopens the open windows; in EN no Portuguese text is left
import re, i18n
ev_m = types.SimpleNamespace(x_root=1900, y_root=1070)
TEXTS = []
class TextLabel(Wid):
    def __init__(self, *a, **k): super().__init__(); TEXTS.append(k.get("text", ""))
    def configure(self, **k): TEXTS.append(k.get("text", ""))
    config = configure
_ct = Canvas.create_text
Canvas.create_text = lambda self, *a, **k: (TEXTS.append(k.get("text", "")), _ct(self, *a, **k))[1]
tkinter.Label = TextLabel
appm.run["pending"] = {"key": "dagger", "rar": "rare", "source": "chest"}
def everything():
    TEXTS.clear(); appm.update_panel()
    TEXTS.extend(k.get("text", "") for kind, _, k in appm.canvas.it.values() if kind == "text")
    for fn in (appm.show_profile, appm.show_stats, appm.show_achievements, appm.show_graveyard, appm.show_heroes,
               appm.show_items, lambda: appm.on_menu(ev_m), appm.show_choice, lambda: appm.announce_unlocks(["gold300"])):
        fn()
    appm.close_choice()
    return " | ".join(TEXTS)
pt = everything()
assert "Sair" in pt and "Andar" in pt and "Quit" not in pt
appm.show_stats(); appm.show_achievements(); appm.on_menu(ev_m); before_ = (appm.stats_win, appm.ach_win)
appm.lang_var.set("en"); appm.menu_do(appm.change_lang)   # like the menu's EN chip
assert appm.state["lang"] == "en" and appm.menu_win is None
assert appm.stats_win in ALIVE and appm.ach_win in ALIVE and (appm.stats_win, appm.ach_win) != before_   # reopened
assert appm.canvas.it[appm.info_txt][2]["text"].startswith("Floor ")
en = everything()
assert "Quit" in en and "Sair" not in en and "Graveyard" in en, en[:400]
spare = re.findall(r"\S*[ãõáéíóúâêôçàÃÕÁÉÍÓÚÂÊÔÇ]\S*|\b(?:Andar|andar|Sair|Itens|Modo|ouro|sala|morto|nenhum|passe)\b", en)
assert not spare, spare
appm.lang_var.set("pt"); appm.change_lang(); assert i18n.LANG == "pt" and everything().count("Sair") == 1
tkinter.Label = Wid; Canvas.create_text = _ct
PENDING.clear(); appm.quit(); tkinter.Toplevel = Tk
# "Show only when in use": hides after HIDE_S without tokens, comes back on the 1st token; off it never hides
appv = tp.PetApp(Args()); PENDING.clear(); vis = []
appv.root.withdraw = lambda: vis.append("some"); appv.root.deiconify = lambda: vis.append("back")
t = time.time(); appv.busy_until = 0; appv.run["pending"] = None
appv.state["last_fed"] = appv.opened_at = t - tp.HIDE_S - 5
appv.adjust_visibility(t); assert vis == []                                       # option off
appv.usage_var.set(True); appv.toggle_usage(); appv.adjust_visibility(time.time()); assert vis == []   # just turned on: stays
appv.opened_at = t - tp.HIDE_S - 5
appv.run["pending"] = {"key": next(iter(M.ITEMS)), "rar": "common"}; appv.adjust_visibility(t); assert vis == []  # open choice
appv.run["pending"] = None; appv.adjust_visibility(t); assert vis == ["some"] and appv.escondido
appv.feed(1000, 1000); appv.adjust_visibility(time.time()); assert vis == ["some", "back"] and not appv.escondido
# startup shortcut (temporary APPDATA)
os.environ["APPDATA"] = home; ini = tp.startup_shortcut(); ini.parent.mkdir(parents=True)
appv.startup_var.set(True); appv.toggle_startup(); assert ini.is_file() and "tokenlike.py" in ini.read_text()
appv.startup_var.set(False); appv.toggle_startup(); assert not ini.exists() and appv.startup_var.get() is False
# tray: 0 = show (even when hidden by "only when in use"), 1 = quit; .ico icon with a 32x32 PNG inside
import tray, queue
icon_file = tray.ico(tp.png_bytes(tp.hero_idle("slime"), 32, square=True)[0], 32)
assert icon_file[:6] == b"\0\0\1\0\1\0" and icon_file[22:26] == b"\x89PNG"
appv.state["last_fed"] = appv.opened_at = time.time() - tp.HIDE_S - 1; appv.adjust_visibility(time.time())
assert appv.escondido
closed = []
appv.tray = types.SimpleNamespace(events=queue.Queue(), shutdown=lambda: closed.append(1))
appv.tray.events.put(0); appv.listen_tray(); assert not appv.escondido
appv.tray.events.put(1); PENDING.clear(); appv.listen_tray(); assert closed == [1] and appv.tray is None
log =tp.LOG_FILE.read_text() if tp.LOG_FILE.exists() else ""
assert "error" not in log, log[-3000:]
print("gui ok; W,H =", app.W, app.H)
