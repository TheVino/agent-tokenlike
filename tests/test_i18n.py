"""Language: every visible text has an EN translation (t() keys in the code + game data); fx_text in EN;
event lines translated by template; rules and BALANCE_VERSION do not depend on the language."""
import ast, random, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import i18n, dungeon as M, tokenlike as tp

EN = i18n.EN
faltam = []


def needs(pt, where):
    if pt not in EN:
        faltam.append(f"{where}: {pt!r}")


# 1) every literal t()/_t() key in the code
for arq in ("tokenlike.py", "dungeon.py"):
    for n in ast.walk(ast.parse((ROOT / arq).read_text(encoding="utf-8"))):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("t", "_t") and n.args:
            a = n.args[0]
            for c in (a.body, a.orelse) if isinstance(a, ast.IfExp) else (a,):
                if isinstance(c, ast.Constant):
                    needs(c.value, arq)
# 2) game data and interface tables translated at display time
for it in M.ITEMS.values():
    needs(it["name"], "item")
for d in M.ACHIEVEMENTS.values():
    needs(d, "conquista")
for m in M.MONSTERS:
    needs(m[1], "monstro")
for n in list(M.BOSS_NAMES.values()) + ["Mímico", "Armadilha", "Queimadura", "Veneno", "Desistiu"]:
    needs(n, "quem mata")
for n in list(M.RAR_NAMES.values()) + list(M.STATUS_NAME.values()):
    needs(n, "raridade/status")
for _, name, *_ in tp.STAT_LINES:
    needs(name, "STAT_LINHAS")
for name, _ in tp.FAMILIES + (("Básico", ()),):
    needs(name, "família")
for n in list(tp.SIZES) + list(tp.MODES.values()) + list(tp.DAYS):
    needs(n, "menu/dias")
for k, c in tp.all_characters().items():
    if tp.own_hero(k):
        needs(c.name, f"herói {k}")
        for s in c.stages:
            needs(s["title"], f"estágio {k}")
assert not faltam, "sem tradução EN:\n" + "\n".join(faltam)

# 3) EN names: no repeats among items and no names from existing games
names = [EN[it["name"]] for it in M.ITEMS.values()]
assert len(set(names)) == len(names)
assert not [v for v in EN.values() if "Hollow" in v or "Isaac" in v]
assert EN["Cavaleiro Oco"] == "Empty Knight"

# 4) pt returns the text itself; en translates templates and built lines; unknown passes through
i18n.set_lang("pt")
assert i18n.t("Andar {n}", n=3) == "Andar 3" and i18n.t("Sair") == "Sair"
v_pt, fx_pt = M.BALANCE_VERSION, M.fx_text({"bloqueio": 2})
assert fx_pt == "bloqueia 2 golpes"
i18n.set_lang("en")
assert i18n.t("Andar {n}", n=3) == "Floor 3" and i18n.t("Sair") == "Quit"
assert i18n.t("Pagou 12 ouro") == "Paid 12 gold" and i18n.t("Bitty") == "Bitty"
assert i18n.t("Derrotado por: {k}", k=i18n.t("Rei Rato")) == "Defeated by: Rat King"
assert i18n.t("Derrotado por: Rei Rato") == "Defeated by: Rat King"     # the template translates the piece too
i18n.set_lang("xx"); assert i18n.LANG == "pt"; i18n.set_lang("en")

# 5) fx_text in EN for every field (and every item): no Portuguese left
fields = {"atk": 1, "def": 1, "maxhp": 1, "dodge": 0.1, "gold": 0.1, "energy": 0.1, "lifesteal": 1, "trap": 0.5,
          "spd": 2, "crit": 0.1, "critdmg": 0.5, "area": True, "queimar": 0.1, "eletrizar": 0.1, "envenenar": 0.1,
          "congelar": 0.1, "bloqueio": 1, "espinhos": 0.1, "cura_sala": 1, "cura_andar": 1, "custo_ataque": 1,
          "furia": 1, "duplo": 0.1, "ajudante": 1, "crescer": 5, "sorte": 0.1, "desconto": 0.1}
used = {c for it in M.ITEMS.values() for c in it["fx"]} | set(M.stats(M.new_run("slime", {"hp": 20, "atk": 3, "def": 0}, 1)))
assert used - {"spd", "crit", "critdmg"} <= set(fields), used - set(fields)   # every item field is here
PT = re.compile(r"[à-úÀ-Ú]|\b(por|de|do|da|ouro|golpe|dano|sorte|esquiva|cura|ataque|velocidade|loja|ajudante)\b")
txt = M.fx_text(fields)
assert len(txt.split(", ")) == len(fields) and not PT.search(txt), txt   # one part per field
for it in M.ITEMS.values():
    assert not PT.search(M.fx_text(it["fx"])), (it["name"], M.fx_text(it["fx"]))

# 6) what the dungeon returns (room name, lines) comes out translated in EN; the rules do not change with the language
seen = set()
rng = random.Random(3)
for _ in range(300):
    run, meta = M.new_run("slime", {"hp": 20, "atk": 3, "def": 0}, 1), M.new_meta()
    while not run["dead"] and run["floor"] < 30:
        run["energy"] = M.room_cost(run)
        ev = M.enter_room(run, meta, rng)
        seen.update([ev.get("name", "")] + ev["lines"] + [ev.get("killed_by", "")])
for s in seen - {""}:
    assert not PT.search(i18n.t(s)) and i18n.t(s) != s, s
assert M.BALANCE_VERSION == v_pt == M._balance_version()
i18n.set_lang("pt")
print("ok: idioma", len(EN), "textos;", len(seen), "nomes/linhas de evento")
