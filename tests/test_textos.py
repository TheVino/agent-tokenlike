"""Textos sem cortar/sobrepor em todas as janelas, com Tk de verdade e dados de pior caso.
Sem tela (TclError ao abrir o Tk), pula com aviso."""
import os, sys, tempfile, time, types
from pathlib import Path
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["USERPROFILE"] = home
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import tkinter
try:
    tkinter.Tk().destroy()
except tkinter.TclError as e:
    print("AVISO: sem tela, test_textos pulado:", e)
    sys.exit(0)
import tkinter.font  # noqa: F401  (tokenlike mede texto com tk.font)
import tokenlike as tp, masmorra as M
from _textos import checar
tp.tk = tkinter
tp.DATA_DIR = Path(home) / ".tokenlike"; tp.LOG_FILE = tp.DATA_DIR / "tokenlike.log"

app = tp.PetApp(types.SimpleNamespace(demo=True, import_history=False, reset=False))
app.reader.poll = lambda: (0.0, 0); app.refresh_limits = lambda: None; app.fake_tokens = lambda: (0.0, 0)
now = time.time()
longo = lambda nomes: max(nomes, key=len)
heroi = max((k for k in app.chars if tp.heroi_proprio(k)), key=lambda k: len(app.chars[k].name))
app.meta["next_char"] = heroi; app.new_run(announce=False)
app.run.update(floor=99, room=5, gold=99999, kills=9999, hp=999, shield=999, bosses=99, stage=len(app.char.stages) - 1,
               items=[{"key": k, "rar": M.ITEMS[k]["rarities"][-1]} for k in M.ITEMS],
               consumed=[{"key": k, "rar": "lendario", "floor": 99} for k in list(M.ITEMS)[:30]])
app.pet_status = longo(list(tp.STATUS_COR))
for d in range(8):
    tp.add_usage(app.state, now - d * 86400, 9.9e11)
app.state.update(tokens_total=9.9e12, xp_total=9.9e12, daily={tp.date.today().isoformat(): 9.9e11})
app.limits = {"sessao": (100, now + 3600), "semana": (100, now + 6 * 86400), "updated": now}
assassino = longo([n for n in M.BOSS_NAMES.values()] + [m[1] for m in M.MONSTERS])
app.meta.update(runs=99999, chefes=9999, best={"floor": 999, "room": 5})
app.meta["graveyard"] = [{"run": 99999 - i, "char": heroi, "floor": 999, "room": 5, "killer": assassino,
                          "kind": "boss", "gold": 99999, "kills": 9999, "date": "2026-11-13",
                          "items": [{"key": k, "rar": "lendario"} for k in list(M.ITEMS)[:i]]} for i in range(50)]
app.build(); app.update_panel(); app.root.update()

problemas = []


def olha(nome, w):
    w.unbind("<FocusOut>")      # a checagem processa eventos: perder o foco aqui não pode fechar a janela
    for p in checar(w):
        problemas.append(f"[{nome}] {p}")


olha("hud", app.root)
for conqs, demo in (([], False), (list(M.ACHIEVEMENTS), True)):
    app.meta["achievements"], app.demo = conqs, demo
    for attr, fn in (("perfil_win", app.show_perfil), ("stats_win", app.show_stats), ("conq_win", app.show_achievements),
                     ("cemi_win", app.show_graveyard), ("heroes_win", app.show_heroes)):
        fn(); olha(attr, getattr(app, attr)); app.close_win(getattr(app, attr))
    for filtro in ("todos", "bloqueados"):
        app.itens_filtro = filtro; app.show_items(); olha(f"itens/{filtro}", app.itens_win); app.close_win(app.itens_win)
app.on_menu(types.SimpleNamespace(x_root=200, y_root=200)); olha("menu", app.menu_win); app.close_win(app.menu_win)
app.state["mode"] = "interativo"
app.run["pending"] = {"key": max(M.ITEMS, key=lambda k: len(M.ITEMS[k]["name"])), "rar": "lendario", "source": "chest"}
app.show_choice(); olha("escolha", app.choice_win)
app.popup([f"Conquista: {longo(list(M.ACHIEVEMENTS.values()))}", "Libera: " + longo([i["name"] for i in M.ITEMS.values()])])
olha("popup", app.popup_win)
# a checagem pega o que deve pegar: texto cortado, encostado na borda do cartão, palavra partida, texto sobre texto
w, f = app.pixel_box(0, 0, fecha=False)
card = app.cartao(f, larg=80, alto=40); card.pack()
tk_lbl = tkinter.Label(card, text="Um nome comprido demais", bg=tp.CARD_BG, font=app.font); tk_lbl.pack()
tkinter.Label(f, text="Supercalifragilístico", wraplength=30, font=app.font).pack()
cv = tkinter.Canvas(f, width=100, height=40); cv.pack()
tp.retangulo_arredondado(cv, 0, 0, 100, 40, 4, tp.CARD_BG, tag="cartao", extra=("card:x",))
cv.create_text(1, 20, anchor="w", text="encostado", font=app.font); cv.create_text(5, 22, anchor="w", text="por cima")
achados = " | ".join(checar(w))
for esperado in ("cortado", "encosta na borda do cartão", "não cabe na quebra", "textos sobrepostos", "borda do cartão card:x"):
    assert esperado in achados, (esperado, achados)
w.destroy()
app.root.destroy()
for p in problemas:
    print(p)
assert not problemas, f"{len(problemas)} problema(s) de texto"
print("ok: textos")
