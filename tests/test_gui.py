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
    """Guarda posição e texto de cada item para bbox realista (6 px por letra, 10 de altura)."""
    n=0
    def __init__(self,*a,**k): self.it={}
    def _new(self,kind,a,k): Canvas.n+=1; self.it[Canvas.n]=[kind,list(a[:4]),dict(k)]; return Canvas.n
    def create_image(self,*a,**k): return self._new("img",a,k)
    def create_rectangle(self,*a,**k): return self._new("rect",a,k)
    def create_text(self,*a,**k): return self._new("text",a,k)
    def coords(self,i,*a):
        if i in self.it and a: self.it[i][1]=list(a)
    def move(self,i,dx,dy):
        if i in self.it: c=self.it[i][1]; self.it[i][1]=[v+(dx if j%2==0 else dy) for j,v in enumerate(c)]
    def itemconfigure(self,i,**k):
        if i in self.it: self.it[i][2].update(k)
    def delete(self,i):
        if i=="all": self.it.clear()
        else: self.it.pop(i,None)
    def bbox(self,i):
        if i not in self.it: return (100,0,140,10)
        kind,c,k=self.it[i]
        if kind=="rect": return tuple(c[:4])
        if kind=="text":
            w=6*len(str(k.get("text",""))); a=k.get("anchor","center")
            x0=c[0] if a=="w" else c[0]-w if a=="e" else c[0]-w/2
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
h0 = app4.H; assert set(app4.limit_rows) == {"sessao", "semana"}   # sem terminal: modo só-tokens
cv = app4.canvas
def row_text(k): return cv.it[app4.limit_rows[k][1]][2]["text"]
tp.add_usage(app4.state, time.time() - 60, 1_200_000); app4.state["usage_hist_desde"] = 0; app4.refresh_limits()
assert row_text("sessao") == "Sessão  1.2M", row_text("sessao")
lim_file = tp.DATA_DIR / "limites.json"
lim_file.write_text(json.dumps({"five_hour": {"used_percentage": 42, "resets_at": time.time() + 3600},
                                "seven_day": {"used_percentage": 95, "resets_at": time.time() - 5},
                                "updated": time.time()}))
app4.refresh_limits()
assert app4.H == h0 and app4.limits["sessao"][0] == 42 and app4.limits["semana"][0] is None
assert row_text("sessao") == "Sessão  42%"
app4.limits["updated"] = time.time() - 3600; app4.update_limits()
assert row_text("sessao") == "Sessão  ~42%", row_text("sessao")          # estimado com o fator
app4.refresh_limits(); app4.update_panel(); pump(app4, 20)
for size in ("Pequeno", "Médio", "Grande"):
    app4.size_var.set(size); app4.change_size(); app4.update_limits()
    for k, row in app4.limit_rows.items():
        lx0, lx1, back = row[4], row[5], row[7]
        assert cv.bbox(row[1])[2] < lx0 < lx1 < cv.bbox(row[3])[0], (size, k, cv.bbox(row[1]), lx0, lx1, cv.bbox(row[3]))
        assert cv.bbox(back)[2] < cv.bbox(row[3])[0]
# floaters simultâneos não dividem lugar, nem cobrem o painel
for f in app4.floaters[:]:
    for i in f[0]: cv.delete(i)
app4.floaters.clear()
for i in range(6): app4.floater(f"-{i}", x=app4.fcx)
caixas = [cv.bbox(f[0][0]) for f in app4.floaters]
for i, a in enumerate(caixas):
    assert a[3] < app4.panel_y
    for b in caixas[i+1:]:
        assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]), (a, b)
lim_file.unlink(); app4.refresh_limits()
assert app4.limits is None and set(app4.limit_rows) == {"sessao", "semana"}
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
# cura_sala / cura_andar: floater "+N ♥" quando o item cura ao entrar na sala ou na escada
er0, PENDING[:] = M.enter_room, []
M.enter_room = lambda *a, **k: {"kind": "shop", "name": "Loja", "sprite": "loja", "lines": [], "won": False,
                                "died": False, "cura_item": 37}
app6.play_room()
M.enter_room = er0
for fn in PENDING[:]:
    if fn is not None and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
PENDING.clear()
assert ("+37 ♥", None) in textos, textos[-5:]
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
# traço: chave inválida ignora o herói (e loga); chave válida chega no CharacterDef
for nome, tr in (("tr_ruim", {"voar": 1}), ("tr_bom", {"envenenar": 0.1})):
    (pasta / nome).mkdir(); (pasta / nome / "a.png").write_bytes(b"x")
    (pasta / nome / "character.json").write_text(json.dumps({"traço": tr, "stages": [{"frames": ["a.png"]}]}))
heroes = tp.load_png_characters(pasta)
assert "tr_ruim" not in [c.key for c in heroes] and [c.traco for c in heroes if c.key == "tr_bom"] == [{"envenenar": 0.1}]
assert "voar" in tp.LOG_FILE.read_text(encoding="utf-8")
# heróis por spritesheet: folha sintética de 9 linhas x 8 quadros, corpo opaco no meio de cada célula
sys.path.insert(0, str(ROOT / "tests")); from _png import folha_png   # PNG de verdade: exercita o decodificador
def pronto(app):   # espera a thread da folha e roda os after pendentes (o Tk falso não tem mainloop)
    for st in app.char.stages:
        if st.get("thread"): st["thread"].join()
    for _ in range(5):
        fns = PENDING[:]; PENDING.clear()
        for fn in fns:
            if fn and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
chars = Path(tempfile.mkdtemp())
folha_png(chars/"x"/"spritesheet.png", 512, 576, sobe={4: 10})   # grade 8x9 de 64 px; "jumping" 10 px acima
x = {c.key: c for c in tp.load_png_characters(chars)}["x"]
assert "estados" not in x.stages[0]                               # a descoberta não corta a folha
st = tp.completar_estagio(x.stages[0]); assert "erro" not in st, st.get("erro")
assert set(st["estados"]) == set(tp.folha.ESTADOS) and all(len(v) == 8 for v in st["estados"].values())
# ruído de alfa 8 no fundo todo não conta como opaco: a caixa é o corpo, não a célula
assert st["estados"]["failed"][0][2] == (16, 5 * 64 + 6, 48, 5 * 64 + 62) and st["estados"]["failed"][0][3] == 2
assert tp.spec_altura(st["frames"][0]) == 28 and tp.spec_k(st["frames"][0]) == 2   # 56 px aparados, N = 2
pm = tp.spec_to_map(st["frames"][0], 2); pj = tp.spec_to_map(st["estados"]["jumping"][0], 2)
assert max(y for _, y in pm) == 31 and min(y for _, y in pm) == 9 and set(pm.values()) == {"#c86432"}
assert max(y for _, y in pj) == 26 and min(x for x, _ in pj) == min(x for x, _ in pm)   # pulo sai do chão, mesmo pivô
# linhas com menos de 8 quadros: célula vazia não vira quadro (nunca pisca invisível); estado sem quadros usa o idle
folha_png(chars/"v"/"spritesheet.png", 512, 576, vazias={0: 2, 3: 5, 6: 8})
v = tp.completar_estagio({c.key: c for c in tp.load_png_characters(chars)}["v"].stages[0])
assert "erro" not in v, v.get("erro")
cont = {e: len(q) for e, q in v["estados"].items()}
assert cont["idle"] == 6 and cont["waving"] == 3 and cont["waiting"] == 6 and cont["run_r"] == 8, cont   # waiting (linha 6) vazia -> idle
assert all(tp.spec_to_map(sp, 2) for q in v["estados"].values() for sp in q)   # nenhum quadro em branco
# PNG de formato que o decodificador não lê: ignorado (e logado) na descoberta
(chars/"q").mkdir(); (chars/"q"/"spritesheet.png").write_bytes((chars/"x"/"spritesheet.png").read_bytes()[:24] + bytes([16]) + bytes(5))
assert "q" not in {c.key for c in tp.load_png_characters(chars)} and "formato de PNG não suportado" in tp.LOG_FILE.read_text(encoding="utf-8")
# Petdex num HOME temporário: PNG vira herói da comunidade; só WebP é ignorado; pet.json inválido não derruba
pets = Path(home)/".petdex"/"pets"
folha_png(pets/"y"/"spritesheet.png", 512, 576); (pets/"y"/"pet.json").write_text('{"name": "Yzinho", "x": 1}')
(pets/"w").mkdir(); (pets/"w"/"spritesheet.webp").write_bytes(b"w")
folha_png(pets/"z"/"a.png", 500, 600); (pets/"z"/"pet.json").write_text("{nada")   # corte automático
folha_png(Path(home)/".codex"/"pets"/"g"/"spritesheet.png", 1536, 1872)
grande = (Path(home)/".codex"/"pets"/"g"/"spritesheet.png").read_bytes()
for i in range(4):
    (Path(home)/".codex"/"pets"/f"g{i}").mkdir(); (Path(home)/".codex"/"pets"/f"g{i}"/"spritesheet.png").write_bytes(grande)
t0 = time.time(); dex = {c.key: c for c in tp.load_petdex_characters()}
dt = time.time() - t0; assert dt < 0.5, dt                        # 5 folhas grandes: só o cabeçalho é lido
y = dex["petdex:y"]
assert y.name == "Yzinho" and y.comunidade and y.unlock is None and y.stats["hp"] == 20 and y.stats["spd"] == 10
assert "petdex:w" not in dex and "converta para PNG" in tp.LOG_FILE.read_text()
z = tp.completar_estagio(dex["petdex:z"].stages[0]); assert dex["petdex:z"].name == "z" and len(z["estados"]["idle"]) == 8
assert "petdex:y" in tp.all_characters()
t0 = time.time()
app8 = tp.PetApp(Args()); PENDING.clear(); app8.rng = random.Random(SEED)
app8.char_var.set("petdex:g"); app8.change_character(); app8.new_run()
assert app8.char.key == "petdex:g" and "estados" not in app8.char.stages[0]   # ainda cortando: visual anterior
pronto(app8)
g = app8.char.stages[0]["frames"]; assert len(g) == 8 and tp.spec_altura(g[0]) <= 48
assert app8.hero_k >= 2 and set(app8.estados_fx) == set(tp.folha.ESTADOS)
dt = time.time() - t0; assert dt < 3.0, dt
pump(app8, 300); app8.quit()
# estados da folha na GUI: cada estado tem as próprias imagens, compostas uma vez
app9 = tp.PetApp(Args()); PENDING.clear(); app9.rng = random.Random(SEED)
app9.char_var.set("petdex:y"); app9.change_character(); app9.new_run(); pronto(app9)
fx = app9.estados_fx; assert set(fx) == set(tp.folha.ESTADOS)
def compostos(): return {ck[0] for ck in app9.fx_cache if ck[1] == app9.fx_sig}
assert compostos() <= {"idle"}, compostos()
def mostrando(): return cv9.it[app9.sprite][2]["image"]
cv9 = app9.canvas
def todas(e): return {id(i) for q in fx[e] for i in q}
app9.busy_until = time.time() + 99; app9.state["last_fed"] = time.time()
app9.tick(); assert id(mostrando()) in todas("idle")
app9.state["last_fed"] = time.time() - tp.REST_AFTER_S - 5; app9.busy_until = 0
app9.run["energy"] = 0; app9.tick(); assert id(mostrando()) in todas("waiting")
app9.run["pending"] = {"key": next(iter(M.ITEMS)), "rar": "comum"}; app9.busy_until = time.time() + 99
app9.tick(); assert id(mostrando()) in todas("review")          # escolha vence o descanso
app9.run["pending"] = None; app9.state["last_fed"] = time.time()
app9.luta_until = time.time() + 5; app9.tick(); assert id(mostrando()) in todas("running")
app9.luta_until = 0
app9.on_release(types.SimpleNamespace(x=app9.pcx, y=app9.base_y - 1)); app9.tick()
assert id(mostrando()) in todas("waving")
app9.run["dead"] = True; app9.meta["graveyard"].append({"killer": "x", "floor": 1, "room": 1, "kills": 0, "gold": 0, "kind": "monster"})
# pegar item recompõe só o idle e o estado na tela; outro estado é composto uma vez, na 1ª vez que aparece
app9.run["items"].append({"key": next(iter(M.ITEMS)), "rar": "comum"}); app9.refresh_look()
fx = app9.estados_fx; assert compostos() == {"idle", "waving"}, compostos()
assert fx["jumping"] is fx["jumping"] and compostos() == {"idle", "waving", "jumping"}
app9.on_death(); app9.tick(); assert id(mostrando()) in todas("failed")
for fn in PENDING[:]:
    if fn and getattr(fn, "__name__", "") not in ("tick", "poll"): fn()
PENDING.clear(); assert mostrando() is app9.art_img("lapide")
app9.new_run(); pump(app9, 400)
# Virar herói: espelha o mapa final em torno do pivô (x -> 16k-1-x), troca run_r/run_l, persiste no state
app9.virar_var.set(False); app9.toggle_virar(); assert not app9.virar
normal = app9.look_maps; k = app9.hero_k
app9.virar_var.set(True); app9.toggle_virar()
assert app9.virar and app9.state["virar"][app9.run["char"]] is True and app9.fx_sig[4] is True
assert app9.look_maps == [{(16 * k - 1 - x, y): c for (x, y), c in m.items()} for m in normal] and app9.look_maps != normal
n0 = len(app9.fx_cache); app9.estados_fx["run_r"]; app9.estados_fx["run_r"]; assert len(app9.fx_cache) == n0 + 1   # compõe uma vez
saved = json.loads((tp.DATA_DIR / "state.json").read_text(encoding="utf-8")); assert saved["virar"][app9.run["char"]] is True
app9.fill_char_menu(); app9.quit()
# Slime (grade) e Fantasma (folha) têm os 9 estados, >= 4 quadros cada, mesmo pivô (base em y = 15)
app10 = tp.PetApp(Args()); PENDING.clear(); app10.char_var.set("slime"); app10.change_character(); app10.new_run()
assert app10.char.key == "slime" and set(app10.estados_fx) == set(tp.folha.ESTADOS)
assert app10.estado_atual(time.time(), True) == "waiting"
for st in tp.all_characters()["slime"].stages + tp.all_characters()["fantasma"].stages:
    if st.get("sheet"): tp.completar_estagio(st)
    assert set(st["estados"]) == set(tp.folha.ESTADOS) and all(len(v) >= 4 for v in st["estados"].values())
    base = {e: max(y for sp in v for _, y in tp.spec_to_map(sp, 1)) for e, v in st["estados"].items() if e != "jumping"}
    assert set(base.values()) == {15}, (st["title"], base)
    assert max(tp.spec_altura(sp) for v in st["estados"].values() for sp in v) > 16 or not st.get("sheet")   # Fantasma 32 px
app10.run["dead"] = True; app10.meta["graveyard"].append({"killer": "x", "floor": 1, "room": 1, "kills": 0, "gold": 0, "kind": "monster"})
app10.on_death(); app10.tick(); assert app10.estado_visto == "failed"
app10.new_run(); pump(app10, 300); app10.quit()
# test_slime_32: 3 estágios, 9 estados, quadros 32x32
sl = tp.builtin_characters()[0]
assert [s["title"] for s in sl.stages] == ["Gotinha", "Slime", "Rei Slime"] and sl.stage_floors == [1, 4, 10]
for st in sl.stages:
    assert set(st["estados"]) == set(tp.folha.ESTADOS)
    assert all(len(sp[1]) == 32 and all(len(l) == 32 for l in sp[1]) for v in st["estados"].values() for sp in v)
    assert len(st["blink"][1]) == 32 and st["blink"][1] != st["frames"][0][1]
# herói com unlock: bloqueado sem a conquista; next_char nele cai no Slime
app12 = tp.PetApp(Args()); PENDING.clear()
fake = tp.CharacterDef("fakeouro", "Fake", app12.chars["slime"].stages, unlock="ouro300"); app12.chars["fakeouro"] = fake
app12.meta["achievements"] = [a for a in app12.meta["achievements"] if a != "ouro300"]
assert not app12.is_unlocked(fake) and M.ACHIEVEMENTS["ouro300"]
app12.meta["next_char"] = "fakeouro"; app12.new_run(announce=False); assert app12.run["char"] == "slime"
app12.meta["achievements"].append("ouro300"); assert app12.is_unlocked(fake)
app12.new_run(announce=False); assert app12.run["char"] == "fakeouro"
app12.meta["achievements"].remove("ouro300"); app12.demo = True; assert app12.is_unlocked(fake)   # demo libera todos
app12.quit()
# test_heroi32_mesmo_tamanho: k = 2 e o quadro desenhado fica do tamanho do 16 px antigo
app11 = tp.PetApp(Args()); PENDING.clear(); app11.char_var.set("slime"); app11.change_character(); app11.new_run()
app11.refresh_look()
assert app11.hero_k == 2 and abs(32 * app11.hero_px - 16 * app11.px) <= 2, (app11.hero_px, app11.px)
app11.run["stage"] = 3; app11.load_images(); app11.refresh_look()   # save antigo de 4 estágios: não quebra
app11.quit()
# menu em pixel art: abre, grade lista todos os heróis, bloqueado não troca, liberado troca, sem vazar janelas
VIVAS = set()
class Janela(Tk):
    def __init__(self, *a, **k): VIVAS.add(self)
    def destroy(self): VIVAS.discard(self)
tkinter.Toplevel = Janela
appm = tp.PetApp(Args()); PENDING.clear(); appm.close_choice(); VIVAS.clear()
appm.meta["achievements"] = ["chefe1"]; appm.meta["next_char"] = "slime"; appm.char_var.set("slime")
ev = types.SimpleNamespace(x_root=1900, y_root=1070)
for _ in range(2):
    appm.on_menu(ev); assert appm.menu_win in VIVAS
    appm.menu_do(appm.show_heroes); assert appm.menu_win is None and appm.heroes_win in VIVAS
    assert set(appm.hero_cards) == set(appm.chars)
    bloq = [k for k, c in appm.chars.items() if not appm.is_unlocked(c)]
    assert bloq and all(appm.hero_cards[k] is None for k in bloq)
    appm.show_heroes(); appm.on_menu(ev); assert len(VIVAS) == 2     # reabrir troca a janela, não empilha
    appm.close_win(appm.menu_win); appm.close_win(appm.heroes_win); assert not VIVAS
appm.show_heroes(); appm.hero_cards["fantasma"](); assert appm.meta["next_char"] == "fantasma" and not VIVAS - {appm.popup_win}
for fn in PENDING[:]:
    if fn and getattr(fn, "__name__", "") == "esperar": fn()    # thread das miniaturas
# janelas de conquistas, cemitério e status: vazias e cheias, reabrir troca a janela, fechar não vaza
import arte
assert set(arte.CONQ_ART) == set(M.ACHIEVEMENTS)
JAN = (("cemi_win", appm.show_graveyard), ("conq_win", appm.show_achievements))
def abre_fecha():
    for _ in range(2):
        for attr, fn in JAN:
            fn(); fn(); assert getattr(appm, attr) in VIVAS
        assert len(VIVAS - {appm.popup_win}) == 2
        for attr, _ in JAN:
            appm.close_win(getattr(appm, attr)); assert getattr(appm, attr) is None
        assert not VIVAS - {appm.popup_win}
appm.meta.update(graveyard=[], achievements=[]); appm.run.update(items=[], consumed=[], traco={})
abre_fecha()
mortes = [("Rato", "monster"), ("Rei Rato", "boss"), ("Veneno", "status"), ("Queimadura", "status"), ("Mímico", "mimic"),
          ("Armadilha", "trap"), ("Desistiu", "desistiu"), ("Coisa Nova", "monster")]
appm.meta["graveyard"] = [{"run": i, "char": "naoexiste" if i % 3 else "slime", "floor": 9, "room": 2,
                           "killer": mortes[i % 8][0], "kind": mortes[i % 8][1], "gold": 5, "kills": 3, "date": "2026-11-13",
                           "items": [k if i % 2 else {"key": k, "rar": "epico"} for k in list(M.ITEMS)[:i]]}
                          for i in range(50)]
appm.meta["achievements"] = list(M.ACHIEVEMENTS)[::2]
appm.run.update(items=[{"key": k, "rar": "lendario"} for k in M.ITEMS], kills=40, shield=3, traco={"dodge": 0.1},
                consumed=[{"key": k, "rar": "comum", "floor": 1} for k in list(M.ITEMS)[:4]])
abre_fecha()
PENDING.clear(); appm.quit(); tkinter.Toplevel = Tk
log =tp.LOG_FILE.read_text() if tp.LOG_FILE.exists() else ""
assert "erro" not in log, log[-3000:]
print("gui ok; W,H =", app.W, app.H)
