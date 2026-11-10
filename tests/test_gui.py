"""Teste de fumaça da interface com um tkinter falso (roda sem tela)."""
import sys, types, tempfile, os, time
from pathlib import Path
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
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
class Canvas(Noop):
    n=0
    def _new(self,*a,**k): Canvas.n+=1; return Canvas.n
    create_image=create_rectangle=create_text=_new
    def bbox(self,i): return (100,0,140,10)
class PhotoImage(Noop):
    def __init__(self, width=16, height=16, file=None):
        if file: assert Path(file).is_file(), file
        self.w,self.h=width,height
    def width(self): return self.w
    def height(self): return self.h
    def zoom(self,z): return PhotoImage(self.w*z,self.h*z)
    def subsample(self,s): return PhotoImage(self.w//s,self.h//s)
    def transparency_get(self,x,y): return not (3<=x<13 and 2<=y<16)
class Var:
    def __init__(self, value=None): self.v=value
    def get(self): return self.v
    def set(self,v): self.v=v
fake = types.ModuleType("tkinter")
fake.Tk, fake.Canvas, fake.PhotoImage, fake.Toplevel = Tk, Canvas, PhotoImage, Tk
fake.Label = fake.Menu = Noop
fake.StringVar = fake.BooleanVar = Var
fake.TclError = TclError
sys.modules["tkinter"] = fake
import tokenlike as tp, masmorra as M
tp.DATA_DIR = Path(home)/".tokenlike"; tp.LOG_FILE = tp.DATA_DIR/"tokenlike.log"
import tkinter; tp.tk = tkinter
Args = lambda **k: types.SimpleNamespace(**{"demo":False,"import_history":False,"reset":False, **k})

def pump(app, n):
    for _ in range(n):
        app.busy_until = 0
        if app.run["dead"] and app.respawn_at: app.respawn_at = 1
        app.feed(200_000, 600_000)
        app.tick()
        fns = PENDING[:]; PENDING.clear()
        for fn in fns:
            if fn is None or getattr(fn, "__name__", "") in ("tick","poll"): continue
            fn()

for demo in (False, True):
    app = tp.PetApp(Args(demo=demo)); PENDING.clear()
    app.poll(); PENDING.clear()
    pump(app, 1500)
    m = app.meta
    print(("demo" if demo else "real"), "runs:", m["runs"], "best:", m["best"], "achs:", m["achievements"])
    assert m["runs"] > 3 and len(m["graveyard"]) == m["runs"]
    # unlock ghost and switch hero
    if "chefe1" in m["achievements"]:
        app.fill_char_menu()
        app.char_var.set("fantasma"); app.change_character()
        pump(app, 400)
        assert any(g["char"]=="fantasma" for g in m["graveyard"]) or app.run["char"]=="fantasma", "ghost never played"
    app.show_stats(); app.show_graveyard(); app.show_achievements()
    for size in ("Pequeno","Grande"): app.size_var.set(size); app.change_size()
    app.give_up(); app.reload_chars(); app.toggle_top()
    e = types.SimpleNamespace(x_root=50,y_root=50,x=app.pcx,y=app.base_y-10)
    app.on_press(e); app.on_release(e); app.on_menu(e)
    app.state["last_fed"] = time.time()-20*60; app.busy_until=0; app.run["energy"]=0; app.tick()
    app.last_rest_heal=0; app.run["hp"]=1; PENDING.clear(); app.demo=False; app.reader.poll=lambda:(0.0,0); app.poll()
    assert app.run["hp"]==2, app.run["hp"]
    app.quit()
    st = tp.DATA_DIR/("state-demo.json" if demo else "state.json"); assert st.is_file()
    # reload from disk keeps meta
    app2 = tp.PetApp(Args(demo=demo)); PENDING.clear()
    assert app2.meta["runs"] == m["runs"], (app2.meta["runs"], m["runs"])
log = tp.LOG_FILE.read_text() if tp.LOG_FILE.exists() else ""
assert "erro" not in log, log[-3000:]
print("gui ok; W,H =", app.W, app.H)
