"""Language: every visible text (English, the key) has a PT translation (t() keys in the code + game data); fx_text in EN;
event lines translated by template; old Portuguese saves map back to English; rules and BALANCE_VERSION do not depend on the language."""
import ast, random, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import i18n, dungeon as M, tokenlike as tp

PT = i18n.PT
missing = []


def needs(en, where):
    if en not in PT:
        missing.append(f"{where}: {en!r}")


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
    needs(d, "achievement")
for m in M.MONSTERS:
    needs(m[1], "monster")
for n in list(M.BOSS_NAMES.values()) + ["Mimic", "Trap", "Burn", "Poison", "Gave up"]:
    needs(n, "killer")
for n in list(M.RAR_NAMES.values()) + list(M.STATUS_NAME.values()):
    needs(n, "rarity/status")
for _, name, *_ in tp.STAT_LINES:
    needs(name, "STAT_LINES")
for name, _ in M.FAMILIES + (("Basic", ()),):
    needs(name, "family")
for sy in M.SYNERGIES.values():
    needs(sy["name"], "synergy")
for k, tale in M.TALES.items():
    needs(tale["text"], f"tale {k}")
for k in M.BOONS:                                   # every boon_text template
    needs(M.BOONS[k]["text"], f"boon {k}")
needs(M.REFINE_FALLBACK, "boon refine")
for n in list(tp.SIZES) + list(tp.MODES.values()) + list(tp.DAYS):
    needs(n, "menu/days")
for k, c in tp.all_characters().items():
    if tp.own_hero(k):
        needs(c.name, f"hero {k}")
        for s in c.stages:
            needs(s["title"], f"stage {k}")
assert not missing, "no PT translation:\n" + "\n".join(missing)

# 3) EN names: no repeats among items and no names from existing games; the PT table is one-to-one
names = [it["name"] for it in M.ITEMS.values()]
assert len(set(names)) == len(names)
assert not [k for k in PT if "Hollow" in k or "Isaac" in k]
assert PT["Empty Knight"] == "Cavaleiro Oco" and len(set(PT.values())) == len(PT)

# 4) en returns the text itself; pt translates templates and built lines; unknown passes through
i18n.set_lang("pt")
for sy in M.SYNERGIES.values():                 # hints translate by template (family and item names too)
    assert i18n.t(sy["hint"]) != sy["hint"], sy["hint"]
assert i18n.t("Have 2 Luck & gold items") == "Tenha 2 itens de Sorte e ouro"
assert i18n.t("Floor {n}", n=3) == "Andar 3" and i18n.t("Quit") == "Sair"
assert i18n.t("Paid 12 gold") == "Pagou 12 ouro" and i18n.t("Bitty") == "Bitty"
assert i18n.t("Defeated by: Rat King") == "Derrotado por: Rei Rato"     # the template translates the piece too
v_pt, fx_pt = M.BALANCE_VERSION, M.fx_text({"block": 2})
assert fx_pt == "bloqueia 2 golpes"
i18n.set_lang("en")
assert i18n.t("Floor {n}", n=3) == "Floor 3" and i18n.t("Quit") == "Quit"
assert i18n.t("Defeated by: {k}", k=i18n.t("Rat King")) == "Defeated by: Rat King"
# old saves: Portuguese text -> English
assert i18n.legacy_en("Derrotado por: Rei Rato") == "Defeated by: Rat King" and i18n.legacy_en("Veneno") == "Poison"
assert i18n.legacy_en("Bitty") == "Bitty"
i18n.set_lang("xx"); assert i18n.LANG == "pt"; i18n.set_lang("en")

# 5) fx_text in EN for every field (and every item): no Portuguese left
fields = {"atk": 1, "def": 1, "maxhp": 1, "dodge": 0.1, "gold": 0.1, "energy": 0.1, "lifesteal": 1, "trap": 0.5,
          "spd": 2, "crit": 0.1, "critdmg": 0.5, "area": True, "burn": 0.1, "shock": 0.1, "poison": 0.1,
          "freeze": 0.1, "block": 1, "thorns": 0.1, "heal_room": 1, "heal_floor": 1, "attack_cost": 1,
          "fury": 1, "double": 0.1, "helper": 1, "grow": 5, "luck": 0.1, "discount": 0.1,
          "elem_boost": 0.03, "status_turns": 1}
used = {c for it in M.ITEMS.values() for c in it["fx"]} | {c for s in M.SYNERGIES.values() for c in s["fx"]} | set(M.stats(M.new_run("slime", {"hp": 20, "atk": 3, "def": 0}, 1)))
assert used - {"spd", "crit", "critdmg"} <= set(fields), used - set(fields)   # every item field is here
PT_WORDS = re.compile(r"[à-úÀ-Ú]|\b(por|de|do|da|ouro|golpe|dano|sorte|esquiva|cura|ataque|velocidade|loja|ajudante)\b")
txt = M.fx_text(fields)
assert len(txt.split(", ")) == len(fields) and not PT_WORDS.search(txt), txt   # one part per field
for it in M.ITEMS.values():
    assert not PT_WORDS.search(M.fx_text(it["fx"])), (it["name"], M.fx_text(it["fx"]))

# 6) what the dungeon returns (room name, lines) is English and comes out translated in PT; the rules do not change with the language
seen = set()
rng = random.Random(3)
for _ in range(300):
    run, meta = M.new_run("slime", {"hp": 20, "atk": 3, "def": 0}, 1), M.new_meta()
    while not run["dead"] and run["floor"] < 30:
        run["energy"] = M.room_cost(run)
        ev = M.enter_room(run, meta, rng)
        seen.update([ev.get("name", "")] + ev["lines"] + [ev.get("killed_by", "")])
for s in seen - {""}:
    assert not PT_WORDS.search(s), s
i18n.set_lang("pt")
for s in seen - {""}:
    assert i18n.t(s) != s or PT.get(s) == s, s
assert M.BALANCE_VERSION == v_pt == M._balance_version()
print("ok: i18n", len(PT), "texts;", len(seen), "names/event lines")
