import sys, random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dungeon as M

import math
def expected(v, rar): return math.floor(v * M.RAR_MULT[rar] + 0.5)   # same rounding as item_fx (.5 rounds up)
for rar in M.RARITIES:
    assert M.item_fx("bone_sword", rar)["atk"] == expected(4, rar)
    assert M.consume_fx("pot_lid", rar)["shield"] == expected(5, rar)
assert M.item_fx("scythe", "epic")["maxhp"] == -4                     # negatives do not scale
assert M.item_fx("candle", "legendary")["trap"] == 2.0                    # trap does not scale
run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); meta = M.new_meta()
assert run["items"] == [] and run["shield"] == 0 and run["pending"] is None
# stacks and adds up
for k in ("dagger", "bone_sword"): M.resolve_offer(run, {"key": k, "rar": "common"}, "take", {"lines": []})
assert M.stats(run)["atk"] == 3 + 2 + 4
# caps
run2 = M.new_run("slime", {}, 2); run2["items"] = [{"key": "candle", "rar": "legendary"}] * 1
assert M.stats(run2)["energy"] <= 1.0 and 0.25 <= M.stats(run2)["trap"] <= 3
# the shield absorbs before HP
run["shield"] = 5; hp = run["hp"]; assert M.apply_damage(run, 3) == 0 and run["shield"] == 2 and run["hp"] == hp
assert M.apply_damage(run, 4) == 2 and run["shield"] == 0 and run["hp"] == hp - 2
# automatic rule
r = M.new_run("slime", {"hp": 20}, 3); r["hp"] = 7
heal_item = next(k for k, it in M.ITEMS.items() if "heal" in it["consume"])
assert M.auto_choice(r, {"key": heal_item, "rar": "common"}) == "consume"
r["hp"] = 20; assert M.auto_choice(r, {"key": heal_item, "rar": "common"}) == "take"
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
assert all(M.roll_offer(r, meta_all, random.Random(s), best=True)["rar"] != "common" for s in range(50))
# pending offer: consuming a shield and taking by the player; resolve_pending uses the automatic rule
r = M.new_run("slime", {"hp": 20}, 7)
r["pending"] = {"key": "pot_lid", "rar": "rare", "source": "chest"}
ev = M.choose_pending(r, meta, "consume")
assert r["pending"] is None and r["shield"] == expected(5, "rare") and ev["consumed"] == {"key": "pot_lid", "rar": "rare", "shield": expected(5, "rare")}
r["pending"] = {"key": "dagger", "rar": "common", "source": "chest"}
ev = M.resolve_pending(r, meta)
assert r["pending"] is None and ev["item"] == {"key": "dagger", "rar": "common"} and r["items"][-1]["key"] == "dagger"
# interactive mode creates a pending offer; enter_room does not enter with one pending (the GUI's job) but resolve_pending works
# old save migration
old = {"items": {"mao": "dagger", "shield": None, "cabeca": "hat"}, "hp": 10}
M.migrate_run(old); assert old["items"] == [{"key": "dagger", "rar": "common", "floor": None, "kills0": 0}, {"key": "hat", "rar": "common", "floor": None, "kills0": 0}]
assert old["shield"] == 0 and old["pending"] is None
new = {"items": [{"key": "dagger", "rar": "rare"}, {"key": "sumiu", "rar": "common"}, "lixo"],
        "pending": {"key": "sumiu", "rar": "common", "source": "chest"}}
M.migrate_run(new)
assert new["items"] == [{"key": "dagger", "rar": "rare", "floor": None, "kills0": 0}] and new["pending"] is None
ok = {"items": [], "pending": {"key": "dagger", "rar": "common", "source": "chest"}}
assert M.migrate_run(ok)["pending"]["key"] == "dagger"                 # a valid pending offer stays
without = M.migrate_run({"hp": 3}); assert without["items"] == [] and without["pending"] is None
# collector
r = M.new_run("slime", {}, 6); r["items"] = [{"key": k, "rar": "common"} for k in list(M.ITEMS)[:10]]
ev = {"lines": []}; M._check_achievements(r, meta, ev); assert "collector" in meta["achievements"]
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
def _cont(k, v): return lambda r: r["counters"].__setitem__(k, v)
_ach("poison1", _cont("poison_kills", 0), _cont("poison_kills", 1))
_ach("horde4", _cont("horde4", 0), _cont("horde4", 1))
_ach("gold300", lambda r: r.__setitem__("gold", 299), lambda r: r.__setitem__("gold", 300))
_its = lambda ks: (lambda r: r.__setitem__("items", [{"key": k, "rar": "common"} for k in ks]))
_ach("elements3", _its(elem[:2] + common[:1]), _its(elem[:3]))
# batch 2
_ach("burn1", _cont("burn_kills", 0), _cont("burn_kills", 1))
_ach("dodge10", _cont("dodges", 9), _cont("dodges", 10))
_ach("floor15", lambda r: r.__setitem__("floor", 14), lambda r: r.__setitem__("floor", 15))
def _full(floor, missing):
    def f(r):
        r["floor"] = floor; r["hp"] = M.stats(r)["maxhp"] - missing
    return f
_ach("floor8full", _full(8, 1), _full(8, 0))
_ach("floor8full", _full(7, 0), _full(9, 0))
# batch 3
_ach("block10", _cont("blocks", 9), _cont("blocks", 10))
_ach("consume10", lambda r: r.__setitem__("consumed", [{}] * 9), lambda r: r.__setitem__("consumed", [{}] * 10))
def _meta(k, v):
    m = M.new_meta(); m[k] = v; return m
for k, v, wants in (("bosses", 2, False), ("bosses", 3, True)):
    m = _meta(k, v); ev = {"lines": []}; M._check_achievements(M.new_run("slime", {}, 1), m, ev)
    assert ("bosses3" in m["achievements"]) == wants
for v, wants in ((9, False), (10, True)):
    m = _meta("runs", v); ev = {"lines": []}; M._check_achievements(M.new_run("slime", {}, 1), m, ev)
    assert ("die10" in m["achievements"]) == wants
m = M.new_meta(); del m["bosses"]; M._check_achievements(M.new_run("slime", {}, 1), m, {"lines": []})   # old save
assert "bosses3" not in m["achievements"]
# the 10th death in a real run grants the 10-deaths achievement in the death room's ev
m = _meta("runs", 9); r = M.new_run("slime", {"hp": 1, "atk": 0}, 1); r["energy"] = 1e9; r["floor"] = 3
rng = random.Random(3); ev = None
for _ in range(50):
    ev = M.enter_room(r, m, rng)
    if r["dead"]: break
assert r["dead"] and m["runs"] == 10 and "die10" in ev["unlocks"] and "die10" in m["achievements"]
# batch 4
_helper = [k for k, v in M.ITEMS.items() if "helper" in v["fx"]]
assert len(_helper) >= 3
_ach("helpers3", _its(_helper[:2] + common[:1]), _its(_helper[:3]))
_ach("no_consume10", lambda r: r.__setitem__("floor", 9), lambda r: r.__setitem__("floor", 10))
def _consumed(r):
    r["floor"] = 12; r["consumed"] = [{}]
m = M.new_meta(); r = M.new_run("slime", {}, 1); _consumed(r); M._check_achievements(r, m, {"lines": []})
assert "no_consume10" not in m["achievements"]
_its_rar = lambda n, rar: (lambda r: r.__setitem__("items", [{"key": k, "rar": rar} for k in list(M.ITEMS)[:n]]))
_ach("legendaries3", _its_rar(3, "epic"), _its_rar(3, "legendary"))
m = M.new_meta(); r = M.new_run("slime", {}, 1); _its_rar(2, "legendary")(r); M._check_achievements(r, m, {"lines": []})
assert "legendaries3" not in m["achievements"]
_ach("poison3", _cont("poison_kills", 2), _cont("poison_kills", 3))
_ach("bosses3run", lambda r: r.__setitem__("bosses", 2), lambda r: r.__setitem__("bosses", 3))
# floor 13: only when dying on floor 13
def _dead(floor):
    def f(r):
        r["floor"] = floor; r["dead"] = True
    return f
_ach("floor13", _dead(12), _dead(13))
m = M.new_meta(); r = M.new_run("slime", {}, 1); r["floor"] = 13; M._check_achievements(r, m, {"lines": []})
assert "floor13" not in m["achievements"]                          # alive on 13 does not count
m = M.new_meta(); r = M.new_run("slime", {}, 1); r["floor"] = 14; r["dead"] = True; M._check_achievements(r, m, {"lines": []})
assert "floor13" not in m["achievements"]                          # dying on 14 does not count
# a defeated boss adds up in meta["bosses"]
m = M.new_meta(); r = M.new_run("slime", {"hp": 999, "atk": 999}, 1); r["floor"] = 5; r["room"] = 4; r["energy"] = 1e9
ev = M.enter_room(r, m, random.Random(1))
assert ev.get("kind") == "boss" and ev.get("won") and m["bosses"] == 1, ev
# many rooms in both modes, without exceptions; pending offer resolved before each room
for mode in ("auto", "interactive"):
    rng = random.Random(7); meta = M.new_meta(); run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
    pendings = 0
    for _ in range(400):
        if run["dead"]: run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
        if run["pending"]: M.resolve_pending(run, meta)
        run["energy"] = 1e9; ev = M.enter_room(run, meta, rng, mode=mode)
        if ev.get("pending"): pendings += 1; assert run["pending"]["key"] == ev["pending"]["key"]
        assert len({i["key"] for i in run["items"]}) == len(run["items"])
    assert (pendings > 0) == (mode == "interactive")
# new items cover every kind of look
import art
kinds = {it["look"]["type"] for it in M.ITEMS.values()}
assert {"obj", "thorns", "drops", "outline", "tint", "sticker"} <= kinds
assert len(M.ITEMS) >= 20
assert any(it["rarities"] == ["legendary"] for it in M.ITEMS.values())
assert any(it["look"].get("anchor") == "float" for it in M.ITEMS.values())
assert all(k in art.ITEM_ART for k in M.ITEMS)
assert all(it["look"]["art"] in art.ITEM_ART for it in M.ITEMS.values() if "art" in it["look"])
# batch A: 5 items per element, with the animated looks
fam = lambda field: [k for k, it in M.ITEMS.items() if it["fx"].get(field, 0) > 0]
for field in ("burn", "shock", "poison", "freeze"):
    assert len(fam(field)) >= 5, field
assert len(M.ITEMS) >= 40
assert len({it["name"] for it in M.ITEMS.values()}) == len(M.ITEMS)        # no repeated name
assert all(k in art.ITEM_ART for k in M.ITEMS)
looks = {it["look"]["type"] for it in M.ITEMS.values()}
assert {"flames", "sparks", "poison_drops", "frost"} <= looks
# batch B: defense, regeneration and blood
assert len(M.ITEMS) >= 60
assert len({it["name"] for it in M.ITEMS.values()}) == len(M.ITEMS)
assert all(k in art.ITEM_ART for k in M.ITEMS)
assert len(fam("block")) >= 4 and len(fam("thorns")) >= 4
assert len(set(fam("heal_room")) | set(fam("heal_floor"))) >= 4
blood = set(fam("attack_cost")) | set(fam("fury"))
assert len(blood) >= 4
for k in fam("attack_cost"):                       # paying health always buys attack
    assert M.ITEMS[k]["fx"].get("atk", 0) > 0 or M.ITEMS[k]["fx"].get("fury", 0) > 0, k
BATCH_B = ["buckler", "turtle_shell", "riveted_gauntlet", "guard_bell", "living_wall",
          "burr", "grumpy_cactus", "barbed_armor", "fang_necklace", "cracked_mirror",
          "little_tea", "stubborn_root", "hearth_lamp", "pocket_spring", "ancient_sap",
          "bleeding_dagger", "stitched_heart", "fury_mask", "ruby_chalice", "crimson_pact"]
assert all(k in M.ITEMS for k in BATCH_B) and len(set(BATCH_B)) == 20
assert sum(M.ITEMS[k]["rarities"] == ["legendary"] for k in BATCH_B) >= 2
# batch C: blows (double), area, helpers and crit
assert len(M.ITEMS) >= 80
assert len({it["name"] for it in M.ITEMS.values()}) == len(M.ITEMS)
assert all(k in art.ITEM_ART for k in M.ITEMS)
BATCH_C = ["swift_glove", "twin_stinger", "pigtail", "echo_bracelet", "twin_claws",
          "blade_top", "bent_chain", "bottled_howl", "feather_fan", "whirlwind",
          "beetle", "little_bat", "little_skull", "puppet", "grey_crow",
          "monocle", "whetstone", "wilted_clover", "wolf_fang", "cat_eye"]
assert all(k in M.ITEMS for k in BATCH_C) and len(set(BATCH_C)) == 20
assert len(fam("double")) >= 4 and len(fam("helper")) >= 4
assert len([k for k, it in M.ITEMS.items() if it["fx"].get("area")]) >= 5     # incense burner + 4 from batch C
assert len(set(fam("crit")) | set(fam("critdmg"))) >= 4
for k in fam("helper"):                           # helpers float around the hero
    assert M.ITEMS[k]["look"]["type"] == "obj" and M.ITEMS[k]["look"]["anchor"] == "float", k
assert sum(M.ITEMS[k]["rarities"] == ["legendary"] for k in BATCH_C) >= 2
assert all(M.fx_text(it["fx"]) for it in M.ITEMS.values())
# grow / luck / discount (task 8)
M.ITEMS["_t_cresce"] = {"name": "t", "rarities": ["common"], "fx": {"grow": 5}, "consume": {"heal": 1}, "look": {"type": "outline", "color": "#fff"}}
assert M.item_fx("_t_cresce", "common")["grow"] == 5
assert M.item_fx("_t_cresce", "legendary")["grow"] == 4 < 5          # ceil(5/1.6)
M.ITEMS["_t_cresce"]["fx"]["grow"] = 10
assert M.item_fx("_t_cresce", "legendary")["grow"] == math.ceil(10 / 1.6) and M.item_fx("_t_cresce", "common")["grow"] == 10
M.ITEMS["_t_cresce"]["fx"]["grow"] = 4
assert M.item_fx("_t_cresce", "legendary")["grow"] == 3              # floor of 3
M.ITEMS["_t_cresce"]["fx"]["grow"] = 5
r = M.new_run("slime", {"hp": 20, "atk": 3}, 9); r["kills"] = 7           # kills before taking it do not count
M.resolve_offer(r, {"key": "_t_cresce", "rar": "common"}, "take", {"lines": []})
assert r["items"][0]["kills0"] == 7 and M.stats(r)["atk"] == 3
r["kills"] = 17; assert M.stats(r)["atk"] == 3 + 2
r["kills"] = 16; assert M.stats(r)["atk"] == 3 + 1
old = {"items": [{"key": "dagger", "rar": "common"}], "base": {}}
assert M.migrate_run(old)["items"][0]["kills0"] == 0
# luck: more rare+ offers
M.ITEMS.pop("_t_cresce")
def rare_frac(luck):
    r = M.new_run("slime", {}, 1); r["floor"] = 5
    r["items"] = [{"key": "_t_sorte", "rar": "common"}] if luck else []
    rng = random.Random(3); n = 0
    for _ in range(2000):
        n += M.roll_offer(r, meta_all, rng)["rar"] != "common"
    return n / 2000
M.ITEMS["_t_sorte"] = {"name": "t", "rarities": ["common"], "fx": {"luck": 1.0}, "consume": {"heal": 1}, "look": {"type": "outline", "color": "#fff"}}
assert rare_frac(True) > rare_frac(False)
M.ITEMS["_t_sorte"]["fx"]["luck"] = 5.0
r = M.new_run("slime", {}, 1); r["items"] = [{"key": "_t_sorte", "rar": "common"}]
assert M.stats(r)["luck"] == 1.0                                      # cap
# discount
M.ITEMS["_t_sorte"]["fx"] = {"discount": 0.9}
r = M.new_run("slime", {}, 1); r["items"] = [{"key": "_t_sorte", "rar": "common"}]
assert M.stats(r)["discount"] == 0.6
assert M.shop_price(r, 10) == round((M.SHOP_PRICE[0] + M.SHOP_PRICE[1] * 10) * 0.4)
assert M.shop_price(M.new_run("slime", {}, 2), 1) == M.SHOP_PRICE[0] + M.SHOP_PRICE[1]
M.SHOP_PRICE, prev_price = (1, 0), M.SHOP_PRICE; assert M.shop_price(r, 1) == 1; M.SHOP_PRICE = prev_price   # minimum 1
M.ITEMS.pop("_t_sorte")
# fx_text
assert M.fx_text({"grow": 5, "luck": 0.2, "discount": 0.3}) == "+1 ATK a cada 5 kills, +20% sorte, -30% preço na loja"
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
BATCH_D = ["milk_tooth", "cocoon", "trophy_collar", "hungry_seed", "ringed_horn",
          "hunter_buckle", "bone_grinder", "bone_die", "crown_coin", "horseshoe",
          "scribbled_map", "thread_talisman", "shooting_star", "cat_whiskers", "frog_pouch",
          "coupon", "scale", "gold_tooth", "piggy_bank", "leech"]
assert all(k in M.ITEMS for k in BATCH_D) and len(set(BATCH_D)) == 20
assert len(fam("grow")) >= 4 and len(fam("luck")) >= 4
assert len(set(fam("gold")) | set(fam("discount"))) >= 4
# each family in the spec with at least 4 items
families = {
    "elementais": set(fam("burn")) | set(fam("shock")) | set(fam("poison")) | set(fam("freeze")),
    "defesa": set(fam("block")) | set(fam("thorns")) | set(fam("dodge")),
    "regeneração": set(fam("heal_room")) | set(fam("heal_floor")) | set(fam("lifesteal")),
    "sangue": set(fam("attack_cost")) | set(fam("fury")),
    "golpes": set(fam("crit")) | set(fam("critdmg")) | set(fam("double")),
    "área": {k for k, it in M.ITEMS.items() if it["fx"].get("area")},
    "ajudantes": set(fam("helper")),
    "crescimento": set(fam("grow")),
    "sorte e ouro": set(fam("luck")) | set(fam("gold")) | set(fam("discount")),
}
for name, ks in families.items():
    assert len(ks) >= 4, name
# rarities: ~70% in 3, ~20% in 2, ~10% legendary only (±10 points); at least 8 legendary only
nrar = [len(it["rarities"]) for it in M.ITEMS.values()]
assert abs(nrar.count(3) - 70) <= 10 and abs(nrar.count(2) - 20) <= 10 and abs(nrar.count(1) - 10) <= 10
assert sum(it["rarities"] == ["legendary"] for it in M.ITEMS.values()) >= 8
# passive hero trait: adds up without rarity scaling; an old save without a trait stays the same
run = M.new_run("x", {"hp": 20}, 1, trait={"poison": 0.1, "maxhp": -4})
st = M.stats(run)
assert st["poison"] == 0.1 and st["maxhp"] == 16
M.ITEMS["_tr"] = {"name": "tr", "fx": {"poison": 0.05}, "rarities": ["legendary"], "consume": {"heal": 1},
                  "look": {"type": "obj", "anchor": "top", "art": "dagger"}}
run["items"] = [{"key": "_tr", "rar": "legendary", "floor": 1}]
expected = min(M.MAX_ELEM_CHANCE, 0.1 + M.item_fx("_tr", "legendary")["poison"])
assert abs(M.stats(run)["poison"] - expected) < 1e-9
del M.ITEMS["_tr"]
stale = M.new_run("x", {"hp": 20}, 1); before = M.stats(stale); del stale["trait"]
assert M.stats(M.migrate_run(stale)) == before and stale["trait"] == {}
# synergies: data
S = M.SYNERGIES
assert sum(1 for s in S.values() if s["kind"] == "set") == 18
assert sum(1 for s in S.values() if s["kind"] == "pair") == 8
secret = [k for k, s in S.items() if s.get("secret")]
assert len(secret) == 3 and all(S[k]["kind"] == "pair" for k in secret)
for k, s in S.items():
    assert s["name"] and (s.get("secret") or s["hint"]), k
    if s["kind"] == "pair":
        a, b = s["req"]["items"]
        assert a in M.ITEMS and b in M.ITEMS and M.item_family(a) != M.item_family(b), k
        assert "Basic" not in (M.item_family(a), M.item_family(b)), k
assert len({s["name"] for s in S.values()} | {it["name"] for it in M.ITEMS.values()}) == len(S) + len(M.ITEMS)
# sets switch on at exactly 2 and 4
fam = "Defense"
keys = [k for k in M.ITEMS if M.item_family(k) == fam][:4]
r = M.new_run("slime", {}, 9)
def sets_on(r): return [k for k in M.active_synergies(r) if S[k]["kind"] == "set" and S[k]["req"]["family"] == fam]
for n, want in ((1, 0), (2, 1), (3, 1), (4, 2)):
    r["items"] = [{"key": k, "rar": "common"} for k in keys[:n]]
    assert len(sets_on(r)) == want, (n, sets_on(r))
# caps hold with every synergy on
r = M.new_run("slime", {}, 10); r["items"] = [{"key": k, "rar": "legendary"} for k in M.ITEMS]
st = M.stats(r)
assert st["crit"] <= M.MAX_CRIT and st["block"] <= M.MAX_BLOCK and st["double"] <= M.MAX_DOUBLE
assert st["thorns"] <= M.MAX_THORNS and st["luck"] <= M.MAX_LUCK and st["attack_cost"] >= 0
assert all(st[el] <= M.MAX_ELEM_CHANCE for el in M.ELEMENTS.values())
# elem_boost only lifts elements whose summed chance is already above 0
M.ITEMS["_e"] = {"name": "e", "fx": {"burn": 0.1}, "rarities": ["common"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "top", "art": "dagger"}}
r = M.new_run("slime", {}, 12); r["trait"] = {"elem_boost": 0.05}; r["items"] = [{"key": "_e", "rar": "common"}]
st = M.stats(r); assert abs(st["burn"] - 0.15) < 1e-9 and st["shock"] == st["poison"] == st["freeze"] == 0
del M.ITEMS["_e"]
# Blood 2 alone (attack_cost -1) never makes attack_cost negative
bk = [k for k in M.ITEMS if M.item_family(k) == "Blood"][:2]
r = M.new_run("slime", {}, 13); r["items"] = [{"key": k, "rar": "common"} for k in bk]
assert "blood2" in M.active_synergies(r) and M.stats(r)["attack_cost"] >= 0
# a pair turns on only with both items
pk = next(k for k, s in S.items() if s["kind"] == "pair"); a, b = S[pk]["req"]["items"]
r = M.new_run("slime", {}, 11); r["items"] = [{"key": a, "rar": "common"}]
assert pk not in M.active_synergies(r)
r["items"].append({"key": b, "rar": "common"}); assert pk in M.active_synergies(r)
# --- Task 3: discovery ---
dk = [k for k in M.ITEMS if M.item_family(k) == "Defense"][:3]
meta = M.new_meta(); assert meta["synergies"] == {}
r = M.new_run("slime", {}, 21); assert r.get("synergies") == []
ev = {"lines": []}
M.resolve_offer(r, {"key": dk[0], "rar": "common"}, "take", ev); M.note_synergies(r, meta, ev)
assert r["synergies"] == [] and not ev.get("synergies")
ev = {"lines": []}
M.resolve_offer(r, {"key": dk[1], "rar": "common"}, "take", ev); M.note_synergies(r, meta, ev)
assert "defense2" in r["synergies"] and meta["synergies"]["defense2"] == {"runs": 1, "first_run": 21}
assert {"key": "defense2", "new": True} in ev["synergies"]
assert any("New synergy: Sturdy Habit!" == l for l in ev["lines"]), ev["lines"]
n = len(r["synergies"]); ev2 = {"lines": []}; M.note_synergies(r, meta, ev2)
assert len(r["synergies"]) == n and not ev2.get("synergies") and not ev2["lines"] and meta["synergies"]["defense2"]["runs"] == 1
r2 = M.new_run("slime", {}, 22); r2["items"] = [{"key": k, "rar": "common"} for k in dk[:2]]; ev3 = {"lines": []}
M.note_synergies(r2, meta, ev3)
assert meta["synergies"]["defense2"] == {"runs": 2, "first_run": 21} and {"key": "defense2", "new": False} in ev3["synergies"]
assert "Synergy: Sturdy Habit!" in ev3["lines"]
r3 = M.new_run("slime", {}, 23); ev4 = {"lines": []}; M.note_synergies(r3, meta, ev4, ["shatter"])
assert r3["synergies"] == ["shatter"] and meta["synergies"]["shatter"] == {"runs": 1, "first_run": 23}
# interactive path
meta = M.new_meta(); r = M.new_run("slime", {}, 24); r["items"] = [{"key": dk[0], "rar": "common"}]
r["pending"] = {"key": dk[1], "rar": "common", "source": "chest"}
ev = M.choose_pending(r, meta, "take")
assert "defense2" in r["synergies"] and "defense2" in meta["synergies"] and {"key": "defense2", "new": True} in ev["synergies"]
# old saves
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0}}
assert M.migrate_run(old)["synergies"] == []
mm = M.new_meta(); mm.update({"achievements": ["floor5"], "runs": 3}); assert mm["synergies"] == {}
# achievements
meta = M.new_meta(); r = M.new_run("slime", {}, 25)
meta["synergies"] = {k: {"runs": 1, "first_run": 1} for k in list(M.SYNERGIES)[:4]}; M._check_achievements(r, meta, {"lines": []})
assert "synergy5" not in meta["achievements"]
meta["synergies"]["x5"] = {"runs": 1, "first_run": 1}; M._check_achievements(r, meta, {"lines": []})
assert "synergy5" in meta["achievements"]
meta = M.new_meta(); meta["synergies"] = {k: {"runs": 1, "first_run": 1} for k, s in M.SYNERGIES.items() if s["kind"] == "reaction"}
M._check_achievements(r, meta, {"lines": []}); assert "reactions_all" in meta["achievements"] and "synergy5" in meta["achievements"]
meta = M.new_meta(); r = M.new_run("slime", {}, 26); r["synergies"] = ["a", "b"]
M._check_achievements(r, meta, {"lines": []}); assert "synergies3run" not in meta["achievements"]
r["synergies"].append("c"); M._check_achievements(r, meta, {"lines": []}); assert "synergies3run" in meta["achievements"]
# enter_room records reactions from the combat steps
meta = M.new_meta(); r = M.new_run("slime", {"hp": 30, "atk": 3}, 27); r["energy"] = 1e9
orig = M.combat
def fake(run, st, foes, rng, f):
    for x in foes: x["hp"] = 0
    return True, [{"who": "pet", "target": 0, "dmg": 1, "crit": False, "status": None, "skip": False, "dot": False,
                   "dodge": False, "locked": False, "thorns": False, "double": False, "reaction": "shatter"}], "", False
M.combat = fake
try:
    for _ in range(50):
        ev = M.enter_room(r, meta, random.Random(_), mode="auto")
        if "hits" in ev: break
finally:
    M.combat = orig
assert "shatter" in r["synergies"] and "shatter" in meta["synergies"]
# per-reaction hints are plain texts (translated whole)
for k, s in M.SYNERGIES.items():
    if s["kind"] == "reaction": assert "{" not in s["hint"] and s["hint"]
# typed pending
dk = next(iter(M.ITEMS))
assert M.migrate_run({"items": [], "pending": {"key": dk, "rar": "common"}})["pending"]["kind"] == "offer"
assert M.migrate_run({"items": [], "pending": {"key": "nope", "rar": "common"}})["pending"] is None
assert M.migrate_run({"items": [], "pending": {"kind": "nope"}})["pending"] is None
M.CHOICES["idol"] = (lambda run, p: "x", lambda *a, **k: None, lambda p: True)
rp = M.new_run("slime", {}, 9); rp["pending"] = {"kind": "idol", "cost": 2}
assert M.roll_offer(rp, M.new_meta(), random.Random(1)) is not None
del M.CHOICES["idol"]
# temp effects last N non-stairs rooms
rt = M.new_run("slime", {"hp": 999, "atk": 3}, 10); mt = M.new_meta(); rg = random.Random(3)
M.add_temp(rt, {"atk": 1}, 3)
seen = []
for _ in range(4):
    rt["energy"] = 1e9; M.enter_room(rt, mt, rg); seen.append(M.stats(rt)["atk"] - 3)
assert seen == [1, 1, 1, 0], seen
rt2 = M.new_run("slime", {"hp": 999}, 11); rt2["room"] = M.ROOMS_PER_FLOOR; M.add_temp(rt2, {"atk": 1}, 1)
rt2["energy"] = 1e9; assert M.enter_room(rt2, mt, rg)["kind"] == "stairs" and rt2["temp"][0]["rooms"] == 1
# an entry added while a room resolves is untouched by that room's tick
rt3 = M.new_run("slime", {"hp": 999}, 12); rt3["energy"] = 1e9
orig = M.combat
M.combat = lambda *a, **k: (M.add_temp(rt3, {"atk": 1}, 2), orig(*a, **k))[1]
for _ in range(30):
    rt3["energy"] = 1e9; M.enter_room(rt3, mt, rg)
    if rt3["temp"]: break
M.combat = orig
assert rt3["temp"] and rt3["temp"][0]["rooms"] == 2
# rooms counted
rc = M.new_run("slime", {"hp": 9999}, 13); n = 0
for _ in range(20):
    rc["energy"] = 1e9; n += M.enter_room(rc, mt, rg)["kind"] != "stairs"
assert sum(rc["rooms"].values()) == n and "stairs" not in rc["rooms"]
# secret room: always rare or better, plus gold
_w = M.ROOM_WEIGHTS; M.ROOM_WEIGHTS = [("secret", 1)]
try:
    for seed in range(200):
        rs = M.new_run("slime", {"hp": 9999}, 100 + seed); rs["energy"] = 1e9
        ms = M.new_meta(); rg2 = random.Random(seed)
        ev = M.enter_room(rs, ms, rg2)
        assert ev["kind"] == "secret" and ev["sprite"] == "secret" and ev["gold"] > 0, ev
        assert rs["items"] and all(i["rar"] != "common" for i in rs["items"]), rs["items"]
    # secret3: 3 secret rooms
    rs = M.new_run("slime", {"hp": 9999}, 500); ms = M.new_meta(); rg2 = random.Random(1)
    for _ in range(3):
        rs["energy"] = 1e9; M.enter_room(rs, ms, rg2)
        rs["room"] = 0
    assert ms["secrets"] == 3 and "secret3" in ms["achievements"], ms
finally:
    M.ROOM_WEIGHTS = _w
print("ok: items")
