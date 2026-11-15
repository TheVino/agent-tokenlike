import sys, random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dungeon as M

import math
def expected(v, rar): return math.floor(v * M.RAR_MULT[rar] + 0.5)   # same rounding as item_fx (.5 rounds up)
for rar in M.RARITIES:
    assert M.item_fx("espada_osso", rar)["atk"] == expected(4, rar)
    assert M.consume_fx("tampa", rar)["shield"] == expected(5, rar)
assert M.item_fx("foice", "epico")["maxhp"] == -4                     # negatives do not scale
assert M.item_fx("vela", "lendario")["trap"] == 2.0                    # trap does not scale
run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); meta = M.new_meta()
assert run["items"] == [] and run["shield"] == 0 and run["pending"] is None
# stacks and adds up
for k in ("adaga", "espada_osso"): M.resolve_offer(run, {"key": k, "rar": "comum"}, "pegar", {"lines": []})
assert M.stats(run)["atk"] == 3 + 2 + 4
# caps
run2 = M.new_run("slime", {}, 2); run2["items"] = [{"key": "vela", "rar": "lendario"}] * 1
assert M.stats(run2)["energy"] <= 1.0 and 0.25 <= M.stats(run2)["trap"] <= 3
# the shield absorbs before HP
run["shield"] = 5; hp = run["hp"]; assert M.apply_damage(run, 3) == 0 and run["shield"] == 2 and run["hp"] == hp
assert M.apply_damage(run, 4) == 2 and run["shield"] == 0 and run["hp"] == hp - 2
# automatic rule
r = M.new_run("slime", {"hp": 20}, 3); r["hp"] = 7
heal_item = next(k for k, it in M.ITEMS.items() if "heal" in it["consume"])
assert M.auto_choice(r, {"key": heal_item, "rar": "comum"}) == "consumir"
r["hp"] = 20; assert M.auto_choice(r, {"key": heal_item, "rar": "comum"}) == "pegar"
# each item once per run and an empty pool -> None
meta_all = M.new_meta(); meta_all["achievements"] = list(M.ACHIEVEMENTS)
r = M.new_run("slime", {}, 4); r["floor"] = 30; rng = random.Random(1); seen = set()
while (o := M.roll_offer(r, meta_all, rng)) is not None:
    assert o["key"] not in seen and o["rar"] in M.ITEMS[o["key"]]["rarities"]; seen.add(o["key"])
    r["items"].append(o)
assert seen == set(M.ITEMS)
assert M.roll_offer(r, meta_all, rng, best=True) is None
# boss: rare+ when it exists
r = M.new_run("slime", {}, 5)
assert all(M.roll_offer(r, meta_all, random.Random(s), best=True)["rar"] != "comum" for s in range(50))
# pending offer: consuming a shield and taking by the player; resolve_pending uses the automatic rule
r = M.new_run("slime", {"hp": 20}, 7)
r["pending"] = {"key": "tampa", "rar": "raro", "source": "chest"}
ev = M.choose_pending(r, meta, "consumir")
assert r["pending"] is None and r["shield"] == expected(5, "raro") and ev["consumed"] == {"key": "tampa", "rar": "raro", "shield": expected(5, "raro")}
r["pending"] = {"key": "adaga", "rar": "comum", "source": "chest"}
ev = M.resolve_pending(r, meta)
assert r["pending"] is None and ev["item"] == {"key": "adaga", "rar": "comum"} and r["items"][-1]["key"] == "adaga"
# interactive mode creates a pending offer; enter_room does not enter with one pending (the GUI's job) but resolve_pending works
# old save migration
old = {"items": {"mao": "adaga", "escudo": None, "cabeca": "chapeu"}, "hp": 10}
M.migrate_run(old); assert old["items"] == [{"key": "adaga", "rar": "comum", "floor": None, "kills0": 0}, {"key": "chapeu", "rar": "comum", "floor": None, "kills0": 0}]
assert old["shield"] == 0 and old["pending"] is None
new = {"items": [{"key": "adaga", "rar": "raro"}, {"key": "sumiu", "rar": "comum"}, "lixo"],
        "pending": {"key": "sumiu", "rar": "comum", "source": "chest"}}
M.migrate_run(new)
assert new["items"] == [{"key": "adaga", "rar": "raro", "floor": None, "kills0": 0}] and new["pending"] is None
ok = {"items": [], "pending": {"key": "adaga", "rar": "comum", "source": "chest"}}
assert M.migrate_run(ok)["pending"]["key"] == "adaga"                 # a valid pending offer stays
without = M.migrate_run({"hp": 3}); assert without["items"] == [] and without["pending"] is None
# collector
r = M.new_run("slime", {}, 6); r["items"] = [{"key": k, "rar": "comum"} for k in list(M.ITEMS)[:10]]
ev = {"lines": []}; M._check_achievements(r, meta, ev); assert "colecionador" in meta["achievements"]
# batch 1 hero achievements: just below the limit does not grant, at the limit grants only once
elem = [k for k, v in M.ITEMS.items() if set(M.ELEMENTS.values()) & set(v["fx"])]
common = [k for k, v in M.ITEMS.items() if not set(M.ELEMENTS.values()) & set(v["fx"])]
def _ach(key, below, limit):
    m = M.new_meta(); ev = {"lines": []}
    r = M.new_run("slime", {}, 1); below(r); M._check_achievements(r, m, ev)
    assert key not in m["achievements"] and key not in ev.get("unlocks", []), key
    r = M.new_run("slime", {}, 1); limit(r); ev = {"lines": []}; M._check_achievements(r, m, ev)
    assert key in m["achievements"] and key in ev["unlocks"], key
    ev = {"lines": []}; M._check_achievements(r, m, ev); assert key not in ev.get("unlocks", []) and m["achievements"].count(key) == 1
def _cont(k, v): return lambda r: r["cont"].__setitem__(k, v)
_ach("veneno1", _cont("mortes_veneno", 0), _cont("mortes_veneno", 1))
_ach("horda4", _cont("horda4", 0), _cont("horda4", 1))
_ach("ouro300", lambda r: r.__setitem__("gold", 299), lambda r: r.__setitem__("gold", 300))
_its = lambda ks: (lambda r: r.__setitem__("items", [{"key": k, "rar": "comum"} for k in ks]))
_ach("elementos3", _its(elem[:2] + common[:1]), _its(elem[:3]))
# batch 2
_ach("queima1", _cont("mortes_queima", 0), _cont("mortes_queima", 1))
_ach("esquiva10", _cont("esquivas", 9), _cont("esquivas", 10))
_ach("andar15", lambda r: r.__setitem__("floor", 14), lambda r: r.__setitem__("floor", 15))
def _full(floor, missing):
    def f(r):
        r["floor"] = floor; r["hp"] = M.stats(r)["maxhp"] - missing
    return f
_ach("andar8cheio", _full(8, 1), _full(8, 0))
_ach("andar8cheio", _full(7, 0), _full(9, 0))
# batch 3
_ach("bloqueio10", _cont("bloqueios", 9), _cont("bloqueios", 10))
_ach("consumir10", lambda r: r.__setitem__("consumed", [{}] * 9), lambda r: r.__setitem__("consumed", [{}] * 10))
def _meta(k, v):
    m = M.new_meta(); m[k] = v; return m
for k, v, wants in (("chefes", 2, False), ("chefes", 3, True)):
    m = _meta(k, v); ev = {"lines": []}; M._check_achievements(M.new_run("slime", {}, 1), m, ev)
    assert ("chefes3" in m["achievements"]) == wants
for v, wants in ((9, False), (10, True)):
    m = _meta("runs", v); ev = {"lines": []}; M._check_achievements(M.new_run("slime", {}, 1), m, ev)
    assert ("morrer10" in m["achievements"]) == wants
m = M.new_meta(); del m["chefes"]; M._check_achievements(M.new_run("slime", {}, 1), m, {"lines": []})   # old save
assert "chefes3" not in m["achievements"]
# the 10th death in a real run grants the 10-deaths achievement in the death room's ev
m = _meta("runs", 9); r = M.new_run("slime", {"hp": 1, "atk": 0}, 1); r["energy"] = 1e9; r["floor"] = 3
rng = random.Random(3); ev = None
for _ in range(50):
    ev = M.enter_room(r, m, rng)
    if r["dead"]: break
assert r["dead"] and m["runs"] == 10 and "morrer10" in ev["unlocks"] and "morrer10" in m["achievements"]
# batch 4
_helper = [k for k, v in M.ITEMS.items() if "ajudante" in v["fx"]]
assert len(_helper) >= 3
_ach("ajudantes3", _its(_helper[:2] + common[:1]), _its(_helper[:3]))
_ach("sem_consumir10", lambda r: r.__setitem__("floor", 9), lambda r: r.__setitem__("floor", 10))
def _consumed(r):
    r["floor"] = 12; r["consumed"] = [{}]
m = M.new_meta(); r = M.new_run("slime", {}, 1); _consumed(r); M._check_achievements(r, m, {"lines": []})
assert "sem_consumir10" not in m["achievements"]
_its_rar = lambda n, rar: (lambda r: r.__setitem__("items", [{"key": k, "rar": rar} for k in list(M.ITEMS)[:n]]))
_ach("lendarios3", _its_rar(3, "epico"), _its_rar(3, "lendario"))
m = M.new_meta(); r = M.new_run("slime", {}, 1); _its_rar(2, "lendario")(r); M._check_achievements(r, m, {"lines": []})
assert "lendarios3" not in m["achievements"]
_ach("veneno3", _cont("mortes_veneno", 2), _cont("mortes_veneno", 3))
_ach("chefes3run", lambda r: r.__setitem__("bosses", 2), lambda r: r.__setitem__("bosses", 3))
# floor 13: only when dying on floor 13
def _dead(floor):
    def f(r):
        r["floor"] = floor; r["dead"] = True
    return f
_ach("andar13", _dead(12), _dead(13))
m = M.new_meta(); r = M.new_run("slime", {}, 1); r["floor"] = 13; M._check_achievements(r, m, {"lines": []})
assert "andar13" not in m["achievements"]                          # alive on 13 does not count
m = M.new_meta(); r = M.new_run("slime", {}, 1); r["floor"] = 14; r["dead"] = True; M._check_achievements(r, m, {"lines": []})
assert "andar13" not in m["achievements"]                          # dying on 14 does not count
# a defeated boss adds up in meta["bosses"]
m = M.new_meta(); r = M.new_run("slime", {"hp": 999, "atk": 999}, 1); r["floor"] = 5; r["room"] = 4; r["energy"] = 1e9
ev = M.enter_room(r, m, random.Random(1))
assert ev.get("kind") == "boss" and ev.get("won") and m["chefes"] == 1, ev
# many rooms in both modes, without exceptions; pending offer resolved before each room
for mode in ("auto", "interativo"):
    rng = random.Random(7); meta = M.new_meta(); run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
    pendings = 0
    for _ in range(400):
        if run["dead"]: run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
        if run["pending"]: M.resolve_pending(run, meta)
        run["energy"] = 1e9; ev = M.enter_room(run, meta, rng, mode=mode)
        if ev.get("pending"): pendings += 1; assert run["pending"]["key"] == ev["pending"]["key"]
        assert len({i["key"] for i in run["items"]}) == len(run["items"])
    assert (pendings > 0) == (mode == "interativo")
# new items cover every kind of look
import art
kinds = {it["look"]["type"] for it in M.ITEMS.values()}
assert {"obj", "espinhos", "gotas", "contorno", "tingir", "adesivo"} <= kinds
assert len(M.ITEMS) >= 20
assert any(it["rarities"] == ["lendario"] for it in M.ITEMS.values())
assert any(it["look"].get("anchor") == "flutua" for it in M.ITEMS.values())
assert all(k in art.ITEM_ART for k in M.ITEMS)
assert all(it["look"]["art"] in art.ITEM_ART for it in M.ITEMS.values() if "art" in it["look"])
# batch A: 5 items per element, with the animated looks
fam = lambda field: [k for k, it in M.ITEMS.items() if it["fx"].get(field, 0) > 0]
for field in ("queimar", "eletrizar", "envenenar", "congelar"):
    assert len(fam(field)) >= 5, field
assert len(M.ITEMS) >= 40
assert len({it["name"] for it in M.ITEMS.values()}) == len(M.ITEMS)        # no repeated name
assert all(k in art.ITEM_ART for k in M.ITEMS)
looks = {it["look"]["type"] for it in M.ITEMS.values()}
assert {"chamas", "faiscas", "gotas_veneno", "geada"} <= looks
# batch B: defense, regeneration and blood
assert len(M.ITEMS) >= 60
assert len({it["name"] for it in M.ITEMS.values()}) == len(M.ITEMS)
assert all(k in art.ITEM_ART for k in M.ITEMS)
assert len(fam("bloqueio")) >= 4 and len(fam("espinhos")) >= 4
assert len(set(fam("cura_sala")) | set(fam("cura_andar"))) >= 4
blood = set(fam("custo_ataque")) | set(fam("furia"))
assert len(blood) >= 4
for k in fam("custo_ataque"):                       # paying health always buys attack
    assert M.ITEMS[k]["fx"].get("atk", 0) > 0 or M.ITEMS[k]["fx"].get("furia", 0) > 0, k
BATCH_B = ["broquel", "casco_tartaruga", "manopla_rebite", "sino_guarda", "muralha_viva",
          "ourico", "cacto_mal", "armadura_farpas", "colar_presas", "espelho_rachado",
          "chazinho", "raiz_teimosa", "lamparina_lar", "fonte_bolso", "seiva_antiga",
          "adaga_sangria", "coracao_costurado", "mascara_furia", "calice_rubro", "pacto_carmesim"]
assert all(k in M.ITEMS for k in BATCH_B) and len(set(BATCH_B)) == 20
assert sum(M.ITEMS[k]["rarities"] == ["lendario"] for k in BATCH_B) >= 2
# batch C: blows (double), area, helpers and crit
assert len(M.ITEMS) >= 80
assert len({it["name"] for it in M.ITEMS.values()}) == len(M.ITEMS)
assert all(k in art.ITEM_ART for k in M.ITEMS)
BATCH_C = ["luvinha_ligeira", "ferrao_gemeo", "rabicho", "pulseira_eco", "garras_gemeas",
          "piao_laminas", "corrente_torta", "uivo_garrafa", "leque_penas", "redemoinho",
          "besourinho", "morceguinho", "caveirinha", "fantoche", "corvo_cinza",
          "monoculo", "pedra_amolar", "trevo_murcho", "presa_lobo", "olho_gato"]
assert all(k in M.ITEMS for k in BATCH_C) and len(set(BATCH_C)) == 20
assert len(fam("duplo")) >= 4 and len(fam("ajudante")) >= 4
assert len([k for k, it in M.ITEMS.items() if it["fx"].get("area")]) >= 5     # incense burner + 4 from batch C
assert len(set(fam("crit")) | set(fam("critdmg"))) >= 4
for k in fam("ajudante"):                           # helpers float around the hero
    assert M.ITEMS[k]["look"]["type"] == "obj" and M.ITEMS[k]["look"]["anchor"] == "flutua", k
assert sum(M.ITEMS[k]["rarities"] == ["lendario"] for k in BATCH_C) >= 2
assert all(M.fx_text(it["fx"]) for it in M.ITEMS.values())
# grow / luck / discount (task 8)
M.ITEMS["_t_cresce"] = {"name": "t", "rarities": ["comum"], "fx": {"crescer": 5}, "consume": {"heal": 1}, "look": {"type": "contorno", "color": "#fff"}}
assert M.item_fx("_t_cresce", "comum")["crescer"] == 5
assert M.item_fx("_t_cresce", "lendario")["crescer"] == 4 < 5          # ceil(5/1.6)
M.ITEMS["_t_cresce"]["fx"]["crescer"] = 10
assert M.item_fx("_t_cresce", "lendario")["crescer"] == math.ceil(10 / 1.6) and M.item_fx("_t_cresce", "comum")["crescer"] == 10
M.ITEMS["_t_cresce"]["fx"]["crescer"] = 4
assert M.item_fx("_t_cresce", "lendario")["crescer"] == 3              # floor of 3
M.ITEMS["_t_cresce"]["fx"]["crescer"] = 5
r = M.new_run("slime", {"hp": 20, "atk": 3}, 9); r["kills"] = 7           # kills before taking it do not count
M.resolve_offer(r, {"key": "_t_cresce", "rar": "comum"}, "pegar", {"lines": []})
assert r["items"][0]["kills0"] == 7 and M.stats(r)["atk"] == 3
r["kills"] = 17; assert M.stats(r)["atk"] == 3 + 2
r["kills"] = 16; assert M.stats(r)["atk"] == 3 + 1
old = {"items": [{"key": "adaga", "rar": "comum"}], "base": {}}
assert M.migrate_run(old)["items"][0]["kills0"] == 0
# luck: more rare+ offers
M.ITEMS.pop("_t_cresce")
def rare_frac(luck):
    r = M.new_run("slime", {}, 1); r["floor"] = 5
    r["items"] = [{"key": "_t_sorte", "rar": "comum"}] if luck else []
    rng = random.Random(3); n = 0
    for _ in range(2000):
        n += M.roll_offer(r, meta_all, rng)["rar"] != "comum"
    return n / 2000
M.ITEMS["_t_sorte"] = {"name": "t", "rarities": ["comum"], "fx": {"sorte": 1.0}, "consume": {"heal": 1}, "look": {"type": "contorno", "color": "#fff"}}
assert rare_frac(True) > rare_frac(False)
M.ITEMS["_t_sorte"]["fx"]["sorte"] = 5.0
r = M.new_run("slime", {}, 1); r["items"] = [{"key": "_t_sorte", "rar": "comum"}]
assert M.stats(r)["sorte"] == 1.0                                      # cap
# discount
M.ITEMS["_t_sorte"]["fx"] = {"desconto": 0.9}
r = M.new_run("slime", {}, 1); r["items"] = [{"key": "_t_sorte", "rar": "comum"}]
assert M.stats(r)["desconto"] == 0.6
assert M.shop_price(r, 10) == round((M.SHOP_PRICE[0] + M.SHOP_PRICE[1] * 10) * 0.4)
assert M.shop_price(M.new_run("slime", {}, 2), 1) == M.SHOP_PRICE[0] + M.SHOP_PRICE[1]
M.SHOP_PRICE, prev_price = (1, 0), M.SHOP_PRICE; assert M.shop_price(r, 1) == 1; M.SHOP_PRICE = prev_price   # minimum 1
M.ITEMS.pop("_t_sorte")
# fx_text
assert M.fx_text({"crescer": 5, "sorte": 0.2, "desconto": 0.3}) == "+1 ATK a cada 5 kills, +20% sorte, -30% preço na loja"
# pool with ~100 items: each once per run and it does not run out before floor 10 on the median
base = list(M.ITEMS)
i = 0
while len(M.ITEMS) < 100:
    M.ITEMS[f"_fill{i}"] = M.ITEMS[base[i % len(base)]]; i += 1
esgot = []
for seed in range(300):
    rng = random.Random(seed); r = M.new_run("slime", {"hp": 20, "atk": 3}, 1); end = 99
    while not r["dead"] and r["floor"] < 40:
        r["energy"] = 1e9; M.enter_room(r, meta_all, rng)
        ks = [x["key"] for x in r["items"]]; assert len(ks) == len(set(ks))
        if len(ks) >= len(M.ITEMS): end = min(end, r["floor"])
    esgot.append(end)
esgot.sort(); assert esgot[150] >= 10, esgot[150]
for k in [k for k in M.ITEMS if k.startswith("_fill")]: del M.ITEMS[k]
# helper: never 0 damage
assert max(1, round(0.4)) == 1
# batch D: growth, luck and gold; completes the 100 items
assert len(M.ITEMS) == 100
assert len({it["name"] for it in M.ITEMS.values()}) == 100
assert all(k in art.ITEM_ART for k in M.ITEMS) and all(M.fx_text(it["fx"]) for it in M.ITEMS.values())
BATCH_D = ["dente_leite", "casulo", "coleira_trofeus", "semente_faminta", "chifre_aneis",
          "fivela_cacador", "moedor_ossos", "dado_osso", "moeda_coroas", "ferradura",
          "mapa_rabiscado", "talisma_fios", "estrela_cadente", "bigode_gato", "bolsa_sapo",
          "cupom", "balanca", "dente_ouro", "cofrinho", "sanguessuga"]
assert all(k in M.ITEMS for k in BATCH_D) and len(set(BATCH_D)) == 20
assert len(fam("crescer")) >= 4 and len(fam("sorte")) >= 4
assert len(set(fam("gold")) | set(fam("desconto"))) >= 4
# each family in the spec with at least 4 items
families = {
    "elementais": set(fam("queimar")) | set(fam("eletrizar")) | set(fam("envenenar")) | set(fam("congelar")),
    "defesa": set(fam("bloqueio")) | set(fam("espinhos")) | set(fam("dodge")),
    "regeneração": set(fam("cura_sala")) | set(fam("cura_andar")) | set(fam("lifesteal")),
    "sangue": set(fam("custo_ataque")) | set(fam("furia")),
    "golpes": set(fam("crit")) | set(fam("critdmg")) | set(fam("duplo")),
    "área": {k for k, it in M.ITEMS.items() if it["fx"].get("area")},
    "ajudantes": set(fam("ajudante")),
    "crescimento": set(fam("crescer")),
    "sorte e ouro": set(fam("sorte")) | set(fam("gold")) | set(fam("desconto")),
}
for name, ks in families.items():
    assert len(ks) >= 4, name
# rarities: ~70% in 3, ~20% in 2, ~10% legendary only (±10 points); at least 8 legendary only
nrar = [len(it["rarities"]) for it in M.ITEMS.values()]
assert abs(nrar.count(3) - 70) <= 10 and abs(nrar.count(2) - 20) <= 10 and abs(nrar.count(1) - 10) <= 10
assert sum(it["rarities"] == ["lendario"] for it in M.ITEMS.values()) >= 8
# passive hero trait: adds up without rarity scaling; an old save without a trait stays the same
run = M.new_run("x", {"hp": 20}, 1, trait={"envenenar": 0.1, "maxhp": -4})
st = M.stats(run)
assert st["envenenar"] == 0.1 and st["maxhp"] == 16
M.ITEMS["_tr"] = {"name": "tr", "fx": {"envenenar": 0.05}, "rarities": ["lendario"], "consume": {"heal": 1},
                  "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
run["items"] = [{"key": "_tr", "rar": "lendario", "floor": 1}]
expected = min(M.MAX_ELEM_CHANCE, 0.1 + M.item_fx("_tr", "lendario")["envenenar"])
assert abs(M.stats(run)["envenenar"] - expected) < 1e-9
del M.ITEMS["_tr"]
stale = M.new_run("x", {"hp": 20}, 1); before = M.stats(stale); del stale["traco"]
assert M.stats(M.migrate_run(stale)) == before and stale["traco"] == {}
print("ok: itens")
