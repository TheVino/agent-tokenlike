"""Teste de fumaça da interface com um tkinter falso (roda sem tela)."""
import json, random, sys, types, tempfile, os, time
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
    def winfo_height(self): return 120
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
    def get(self,x,y): return (200,100,50)
class Var:
    def __init__(self, value=None): self.v=value
    def get(self): return self.v
    def set(self,v): self.v=v
fake = types.ModuleType("tkinter")
fake.Tk, fake.Canvas, fake.PhotoImage, fake.Toplevel = Tk, Canvas, PhotoImage, Tk
fake.Label = fake.Menu = fake.Button = fake.Frame = Noop
fake.StringVar = fake.BooleanVar = Var
fake.TclError = TclError
sys.modules["tkinter"] = fake
SEED = 1
import tokenlike as tp, masmorra as M
tp.DATA_DIR = Path(home)/".tokenlike"; tp.LOG_FILE = tp.DATA_DIR/"tokenlike.log"
import tkinter; tp.tk = tkinter
Args = lambda **k: types.SimpleNamespace(**{"demo":False,"import_history":False,"reset":False, **k})

def pump(app, n):
    for _ in range(n):
        app.busy_until = 0
        if app.run["dead"] and app.respawn_at: app.respawn_at = 1
        app.feed(200_000, 600_000)
        if app.run["pending"]: app.pending_since = 0   # envelhece a escolha para não travar
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
    assert m["runs"] > 3 and len(m["graveyard"]) == min(m["runs"], 50)   # o cemitério guarda só as últimas 50
    # unlock ghost and switch hero
    if "chefe1" in m["achievements"]:
        app.fill_char_menu()
        app.char_var.set("fantasma"); app.change_character()
        pump(app, 400)
        assert any(g["char"]=="fantasma" for g in m["graveyard"]) or app.run["char"]=="fantasma", "ghost never played"
    app.run["items"] = [{"key": k, "rar": "lendario"} for k in list(M.ITEMS)[:12]]
    app.refresh_look(); w_full = app.frames_fx[0][0].width()
    app.run["items"] = []; app.refresh_look(); w_empty = app.frames_fx[0][0].width()
    assert w_full == w_empty                       # imagem sempre do tamanho de LOOK_BOX: pivô fixo
    app.run["items"] = [{"key": "chifres", "rar": "raro"}]; app.refresh_look()
    for size in ("Pequeno", "Grande"): app.size_var.set(size); app.change_size()
    app.evolve(); app.reload_chars(); app.give_up()
    assert not hasattr(app, "acc_items")
    app.show_stats(); app.show_graveyard(); app.show_achievements()
    for size in ("Pequeno","Grande"): app.size_var.set(size); app.change_size()
    app.give_up(); app.reload_chars(); app.toggle_top()
    e = types.SimpleNamespace(x_root=50,y_root=50,x=app.pcx,y=app.base_y-10)
    app.on_press(e); app.on_release(e); app.on_menu(e)
    app.state["last_fed"] = time.time()-20*60; app.busy_until=0; app.run["energy"]=0; app.tick()
    if app.run["dead"]: app.new_run(announce=False)   # o pump pode parar logo depois de uma morte (depende do relógio)
    app.last_rest_heal=0; app.run["hp"]=1; PENDING.clear(); app.demo=False; app.reader.poll=lambda:(0.0,0); app.poll()
    assert app.run["hp"]==2, app.run["hp"]
    app.quit()
    st = tp.DATA_DIR/("state-demo.json" if demo else "state.json"); assert st.is_file()
    # reload from disk keeps meta
    app2 = tp.PetApp(Args(demo=demo)); PENDING.clear(); app2.rng = random.Random(SEED)
    assert app2.meta["runs"] == m["runs"], (app2.meta["runs"], m["runs"])
    # modo interativo: janela de escolha
    if app2.run["dead"]: app2.new_run(announce=False)
    app2.state["mode"] = "interativo"; app2.run["pending"] = None
    app2.run["energy"] = 5 * M.ROOM_COST; app2.busy_until = 0
    offer = {"key": "adaga", "rar": "raro", "source": "chest"}; app2.run["pending"] = dict(offer)
    app2.pending_since = time.time(); room_before = (app2.run["floor"], app2.run["room"])
    app2.tick(); assert (app2.run["floor"], app2.run["room"]) == room_before   # espera a janela
    app2.feed(300_000, 300_000); app2.tick(); assert app2.run["pending"]       # tokens vão para a mochila
    app2.pending_since = time.time() - M.CHOICE_WINDOW_S - 1; app2.tick()
    assert app2.run["pending"] is None                                       # resolveu sozinho e seguiu
    app2.run["pending"] = dict(offer, key="tampa"); app2.pending_since = time.time(); app2.choose("consumir")
    assert app2.run["pending"] is None and not any(i["key"] == "tampa" for i in app2.run["items"])
    assert app2.choice_win is None
    # desistir com escolha aberta: o painel fecha e a run nova não herda a oferta
    app2.run["pending"] = dict(offer, key="gorro"); app2.busy_until = 0; app2.tick()
    assert app2.choice_win is not None
    app2.give_up(); assert app2.run["pending"] is None and app2.choice_win is None
    # escolher numa run morta não muda nada
    app2.run["pending"] = dict(offer, key="gorro"); app2.run["dead"] = True
    before = (list(app2.run["items"]), app2.run["hp"]); app2.choose("pegar")
    assert (app2.run["items"], app2.run["hp"]) == before
    app2.run["dead"] = False; app2.run["pending"] = None
    app2.run["pending"] = dict(offer, key="gorro"); app2.pending_since = time.time() - 999
    app2.run["energy"] = 0; app2.busy_until = 0; app2.tick(); assert app2.run["pending"]   # sem energia: espera
    app2.mode_var.set("auto"); app2.change_mode(); assert app2.run["pending"] is None    # trocar p/ auto resolve
    # reabrir com pendência no save
    app2.state["mode"] = "interativo"; app2.run["pending"] = dict(offer, key="chapeu"); app2.quit()
    app3 = tp.PetApp(Args(demo=demo)); PENDING.clear(); app3.rng = random.Random(SEED)
    app3.busy_until = 0; app3.run["energy"] = 5 * M.ROOM_COST
    app3.tick(); assert app3.run["pending"] and app3.pending_since is not None
    # pump nos dois modos
    app3.state["mode"] = "interativo"; pump(app3, 300)
    app3.mode_var.set("auto"); app3.change_mode(); pump(app3, 100)
    app3.quit()

# barras de sessão/semana (statusline opcional): aparecem, mostram "—" se velho, somem sem o arquivo
app4 = tp.PetApp(Args()); PENDING.clear(); app4.rng = random.Random(SEED)
h0 = app4.H; assert app4.limit_rows == {}
lim_file = tp.DATA_DIR / "limites.json"
lim_file.write_text(json.dumps({"five_hour": {"used_percentage": 42, "resets_at": time.time() + 3600},
                                "seven_day": {"used_percentage": 95, "resets_at": time.time() - 5}}))
app4.refresh_limits()
assert app4.H > h0 and set(app4.limit_rows) == {"sessao", "semana"}
assert app4.limits["sessao"][0] == 42 and app4.limits["semana"][0] is None
app4.refresh_limits(); app4.update_panel(); pump(app4, 20)
for size in ("Pequeno", "Grande"): app4.size_var.set(size); app4.change_size()
lim_file.unlink(); app4.refresh_limits()
assert app4.limit_rows == {} and app4.limits is None
app4.quit()

runs_file = tp.DATA_DIR / "runs.jsonl"; demo_file = tp.DATA_DIR / "runs-demo.jsonl"
lines = [json.loads(l) for l in runs_file.read_text(encoding="utf-8").splitlines()]
assert lines and all(l["version"] == M.BALANCE_VERSION for l in lines)
assert any(l["gave_up"] for l in lines) and any(not l["gave_up"] for l in lines)
assert demo_file.exists()                                        # o demo grava separado
assert all(isinstance(l["achievements"], list) for l in lines)
# falha ao gravar só loga
real_dir = tp.DATA_DIR; tp.DATA_DIR = runs_file / "sub"          # "pasta" dentro de um arquivo: mkdir falha
tp.append_run_record({"x": 1}, False); tp.DATA_DIR = real_dir
# save antigo: run sem ach_start/consumed/floor termina sem exceção
app5 = tp.PetApp(Args()); PENDING.clear(); app5.rng = random.Random(SEED)
app5.run.pop("ach_start", None); app5.run.pop("consumed", None)
app5.run["items"] = [{"key": "adaga", "rar": "comum"}]; M.migrate_run(app5.run)
app5.give_up(); app5.quit()
# combate novo: W estável ao trocar o tamanho, hordas na tela, status
app6 = tp.PetApp(Args()); PENDING.clear(); app6.rng = random.Random(SEED)
app6.size_var.set("Médio"); app6.change_size()                # o app4 deixou "Grande" no save
w0 = app6.W
for size in ("Pequeno", "Grande", "Médio"): app6.size_var.set(size); app6.change_size()
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
    seen_horde = seen_horde or any(k == "horde" for k in getattr(app6, "_ultimo_kind", [""]))
assert seen_horde
# ataque elemental com área (item _t temporário): tinta e clarão no inimigo; status do pet some no fim da luta
M.ITEMS["_t"] = {"name": "t", "fx": {"queimar": 0.6, "area": True}, "rarities": ["comum"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
tintas, status_pet = [], []
draw0, set0 = app6.draw_foe, app6.set_pet_status
app6.draw_foe = lambda i, status=None: (status and tintas.append(status), draw0(i, status))
app6.set_pet_status = lambda s: (s and status_pet.append(s), set0(s))
for _ in range(400):
    app6.busy_until = 0
    if app6.run["dead"]:
        app6.respawn_at = 1
    app6.run["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
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
assert tintas and status_pet, (len(tintas), len(status_pet))
# pet tingido na cor do status (só quando muda); sem status volta ao normal; run nova limpa o status
normal = app6.look_maps[0]
app6.set_pet_status("veneno"); assert app6.pet_status == "veneno" and app6.look_maps[0] != normal
app6.set_pet_status(None); assert app6.look_maps[0] == normal
app6.set_pet_status("queimadura"); app6.new_run(); assert app6.pet_status is None
# golpe duplo e ajudante (item _t temporário): centenas de salas sem exceção; "x2" e o número do ajudante na tela
M.ITEMS["_t"] = {"name": "t", "fx": {"duplo": 0.5, "ajudante": 3}, "rarities": ["comum"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "flutua", "art": "adaga"}}
textos, fl0 = [], app6.floater
app6.floater = lambda text, *a, **k: (textos.append((text, k.get("x"))), fl0(text, *a, **k))
passos_vistos = []
hit0 = app6.anim_hit
app6.anim_hit = lambda h, *a: (passos_vistos.append(h), hit0(h, *a))
for _ in range(300):
    app6.busy_until = 0
    if app6.run["dead"]:
        app6.respawn_at = 1
    app6.run["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
    app6.run["energy"] = 10 * M.ROOM_COST
    app6.tick()
    fns = PENDING[:]; PENDING.clear()
    for fn in fns:
        if fn is None or getattr(fn, "__name__", "") in ("tick", "poll"): continue
        fn()
app6.run["items"] = []; del M.ITEMS["_t"]; app6.refresh_look()
del app6.floater, app6.anim_hit
assert any(h["who"] == "ajudante" for h in passos_vistos) and any(h["duplo"] for h in passos_vistos)
assert any(t.endswith(" x2") for t, _ in textos)
assert any(t == f"-{h['dmg']}" and x is None for h in passos_vistos if h["who"] == "ajudante" for t, x in textos)
app6.show_stats(); app6.quit()
# looks elementais animados: 3 fases por quadro (e no piscar/dormir); sem animação, 1 fase só
app7 = tp.PetApp(Args()); PENDING.clear(); app7.rng = random.Random(SEED)
ELEM = ("chamas", "faiscas", "gotas_veneno", "geada")
for t in ELEM:   # itens temporários com cada look animado
    M.ITEMS["_" + t] = {"name": t, "fx": {"atk": 1}, "rarities": ["comum"], "consume": {"heal": 1},
                        "look": {"type": t}}
app7.run["items"] = [{"key": "_" + t, "rar": "comum", "floor": 1} for t in ELEM]
t0 = time.perf_counter(); app7.refresh_look(); dt = time.perf_counter() - t0
assert dt < 3.0, dt
assert len(app7.frames_fx[0]) == 3 and all(len(q) == 3 for q in app7.frames_fx)
assert len(app7.sleep_fx) == 3 and (app7.blink_fx is None or len(app7.blink_fx) == 3)
app7.set_pet_status("congelamento"); assert all(len(q) == 3 for q in app7.frames_fx)   # tinta em todas as fases
app7.set_pet_status(None)
app7.busy_until = 0; app7.run["energy"] = 0; app7.tick()
app7.run["items"] = []; app7.refresh_look(); assert len(app7.frames_fx[0]) == 1 and len(app7.sleep_fx) == 1
for t in ELEM: M.ITEMS.pop("_" + t)
app7.quit()
# herói com stats inválidos é ignorado (e logado) no carregamento, não a cada tick
pasta = Path(tempfile.mkdtemp())
for nome, stats in (("ruim1", {"spd": "rapido"}), ("ruim2", {"hp": None}), ("bom", {"spd": 12, "hp": "18"})):
    (pasta / nome).mkdir(); (pasta / nome / "a.png").write_bytes(b"x")
    (pasta / nome / "character.json").write_text(json.dumps({"stats": stats, "stages": [{"frames": ["a.png"]}]}))
heroes = tp.load_png_characters(pasta)
assert [c.key for c in heroes] == ["bom"] and heroes[0].stats["spd"] == 12.0 and heroes[0].stats["hp"] == 18
assert tp.LOG_FILE.read_text().count("ignorado") >= 2
log =tp.LOG_FILE.read_text() if tp.LOG_FILE.exists() else ""
assert "erro" not in log, log[-3000:]
print("gui ok; W,H =", app.W, app.H)
