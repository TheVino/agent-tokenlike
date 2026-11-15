import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dungeon as M

run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
st = M.stats(run)
assert st["spd"] == 10 and st["crit"] == M.PET_CRIT and st["critdmg"] == 1.5 and st["area"] is False
assert st["burn"] == 0 and st["freeze"] == 0
assert M.new_run("x", {"spd": 14}, 2)["base"]["spd"] == 14
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0}}
M.migrate_run(old); assert old["base"]["spd"] == 10 and M.stats(old)["spd"] == 10
# crit/critdmg: only the hero's go into the base; without them, stats() uses the constants (and so does the old save)
assert "crit" not in run["base"] and "critdmg" not in run["base"]
assert M.stats(M.new_run("x", {"crit": 0.3, "critdmg": 2}, 2))["crit"] == 0.3
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0, "spd": 10, "crit": 0.1, "critdmg": 1.5}}
M.migrate_run(old); crit0 = M.PET_CRIT; M.PET_CRIT = 0.2
assert M.stats(old)["crit"] == 0.2 and M.stats(run)["crit"] == 0.2; M.PET_CRIT = crit0
M.ITEMS["_t"] = {"name": "t", "fx": {"crit": 0.9, "burn": 0.9, "spd": -50, "area": True},
                 "rarities": ["common"], "consume": {"heal": 1}, "look": {"type": "obj", "anchor": "top", "art": "dagger"}}
run["items"] = [{"key": "_t", "rar": "common", "floor": 1}]
st = M.stats(run)
assert st["crit"] == M.MAX_CRIT and st["burn"] == M.MAX_ELEM_CHANCE and st["spd"] == 1 and st["area"] is True
del M.ITEMS["_t"]
bat = next(m for m in M.MONSTERS if m[0] == "bat"); ske = next(m for m in M.MONSTERS if m[0] == "skeleton")
assert M.make_foe(bat, 5)["spd"] > M.make_foe(ske, 5)["spd"]
assert M.make_foe(bat, 5)["element"] is None and M.make_foe(bat, 5, boss=True)["element"] == "lightning"
# mult is applied BEFORE rounding (a single round)
assert M.make_foe(bat, 5, mult=0.5)["hp"] == max(1, round((M.MON_HP[0] + M.MON_HP[1] * 5) * bat[2] * 0.5))
assert M.make_mimic(3)["element"] is None and M.make_mimic(3)["hp"] == M.make_mimic(3)["hp_max"]
# boss ramp: nothing up to BOSS_RAMP_FROM; after that HP and ATK x (1 + BOSS_RAMP * extra floors); monsters do not ramp
linear = lambda v, f: v[0] + v[1] * (f - M.BOSS_EVERY)
for f in (5, M.BOSS_RAMP_FROM):
    assert M.make_foe(bat, f, boss=True)["hp"] == round(linear(M.BOSS_HP, f))
ramp = 1 + M.BOSS_RAMP * (20 - M.BOSS_RAMP_FROM)
assert M.make_foe(bat, 20, boss=True)["hp"] == round(linear(M.BOSS_HP, 20) * ramp)
assert M.make_foe(bat, 20, boss=True)["atk"] == round(linear(M.BOSS_ATK, 20) * ramp)
assert M.make_foe(bat, 20)["hp"] == max(1, round((M.MON_HP[0] + M.MON_HP[1] * 20) * bat[2]))
# --- Task 2: round-based combat ---
import random
assert isinstance(M.new_run("x", {"spd": 14}, 2)["base"]["spd"], float)
M.ITEMS["_a"] = {"name": "a", "fx": {"area": True, "atk": 1}, "rarities": ["legendary"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "top", "art": "dagger"}}
assert M.item_fx("_a", "legendary")["area"] is True and M.item_fx("_a", "legendary")["atk"] > 1   # area does not scale
del M.ITEMS["_a"]


def foe(hp=10, atk=1, spd=5, boss=False, element=None, crit=0.0, name="Rat"):
    return {"sprite": "rat", "name": name, "boss": boss, "element": element, "hp": hp, "hp_max": hp,
            "atk": atk, "spd": spd, "crit": crit, "critdmg": 1.5, "status": {}}


def pet(spd=10, atk=3, crit=0.0, **fx):
    r = M.new_run("slime", {"hp": 30, "atk": atk, "spd": spd}, 1); r["base"]["crit"] = crit
    if fx:
        M.ITEMS["_t"] = {"name": "t", "fx": fx, "rarities": ["common"], "consume": {"heal": 1},
                         "look": {"type": "obj", "anchor": "top", "art": "dagger"}}
        r["items"] = [{"key": "_t", "rar": "common", "floor": 1}]
    return r


KEYS = {"who", "target", "dmg", "crit", "status", "skip", "dot", "dodge", "locked", "thorns", "double"}
# order: the faster enemy acts first; tie -> pet first
r = pet(spd=5); won, steps, _, _ = M.combat(r, M.stats(r), [foe(spd=9)], random.Random(1), 1)
assert steps[0]["who"] == 0 and all(set(x) == KEYS for x in steps)
r = pet(spd=9); won, steps, _, _ = M.combat(r, M.stats(r), [foe(spd=9)], random.Random(1), 1)
assert steps[0]["who"] == "pet"
# double speed: crit with damage x (critdmg*2); with base crit 0.5 + 0.5 = 1.0 it always crits
mc = M.MAX_CRIT; M.MAX_CRIT = 0.5                  # the current cap is below 0.5; here only the double matters
r = pet(spd=20, atk=4, crit=0.5); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=100, spd=10)], random.Random(2), 1)
M.MAX_CRIT = mc
s = next(x for x in steps if x["who"] == "pet"); assert s["crit"] and s["dmg"] >= 3 * 3     # (4±1) * 1.5 * 2
# without the double and with crit 0, it never crits
r = pet(spd=19, atk=4); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=100, spd=10)], random.Random(2), 1)
assert not any(x["who"] == "pet" and x["crit"] for x in steps)
# an enemy with double speed also gains it (crit 0.5 + 0.5)
r = pet(spd=5); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=100, spd=10, crit=0.0, atk=2)], random.Random(3), 1)
assert any(x["who"] == 0 and x["crit"] for x in steps)
# burn (chance at the 0.6 cap): damage per turn at the start of the round, 3 turns, then it stops
r = pet(burn=1.0); assert M.stats(r)["burn"] == M.MAX_ELEM_CHANCE
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=0, spd=1)], random.Random(4), 10)
dots = [x for x in steps if x["dot"] and x["target"] == 0]
assert dots and all(x["dmg"] == round(2 + 0.3 * 10) and x["status"] == "burn" for x in dots)
f0 = foe(hp=1000, atk=0, spd=1); f0["status"]["burn"] = M.BURN_TURNS
r = pet(); won, steps, _, _ = M.combat(r, M.stats(r), [f0], random.Random(4), 10)
assert sum(1 for x in steps if x["dot"]) == M.BURN_TURNS        # without renewing, it stops after 3
# poison grows: 1, 2, 3 ...
r = pet(poison=0.6); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=0, spd=1)], random.Random(5), 1)
v = [x["dmg"] for x in steps if x["dot"] and x["target"] == 0][:3]
assert len(v) == 3 and v == sorted(v) and v[-1] > v[0] and v[0] == 1
# freeze: loses the turn and wears off
r = pet(freeze=0.6); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(6), 1)
assert any(x["who"] == 0 and x["skip"] for x in steps)
f0 = foe(hp=1000, atk=1, spd=1); f0["status"]["freeze"] = M.FREEZE_TURNS
r = pet(); won, steps, _, _ = M.combat(r, M.stats(r), [f0], random.Random(6), 1)
assert sum(1 for x in steps if x["skip"]) == 1 and not f0["status"]["freeze"]   # lost one turn and wore off
# no luck with ice: the 2 turns pass without skipping a turn and the freeze ends by itself
f0 = foe(hp=1000, atk=1, spd=1); f0["status"]["freeze"] = M.FREEZE_TURNS
r = pet(); won, steps, _, _ = M.combat(r, M.stats(r), [f0], random.Random(4), 1)
assert not any(x["skip"] for x in steps) and f0["status"]["freeze"] == 0
# shock: may skip a turn
r = pet(shock=0.6); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(11), 1)
assert any(x["who"] == 0 and x["skip"] for x in steps)
# a regular monster never applies a status; a boss applies its element to the pet
r = pet(); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=40, atk=1)], random.Random(7), 1)
assert not any(x["who"] == 0 and x["status"] for x in steps)
r = pet(); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=200, atk=1, boss=True, element="fire")], random.Random(8), 5)
assert any(x["who"] == 0 and x["status"] == "burn" for x in steps)
assert any(x["dot"] and x["target"] == "pet" for x in steps)
# death by a boss status has the killer "Burn" or "Poison"
r = pet(); r["hp"] = 3
won, steps, killer, _ = M.combat(r, M.stats(r), [foe(hp=999, atk=0, spd=99, boss=True, element="fire")], random.Random(9), 20)
assert not won and killer in ("Burn", "Rat") and r["hp"] == 0
# the shield holds the hits, but not status damage: the boss's poison kills
r = pet(); r["hp"] = 1; r["shield"] = 10**6
won, steps, killer, _ = M.combat(r, M.stats(r), [foe(hp=999, atk=0, spd=1, boss=True, element="poison")], random.Random(9), 1)
assert not won and killer == "Poison" and steps[-1]["dot"] and steps[-1]["target"] == "pet"
# area hits everyone; without area, the target is the one with the lowest HP
r = pet(atk=50, area=True); fs = [foe(hp=40), foe(hp=40), foe(hp=40)]
won, steps, _, _ = M.combat(r, M.stats(r), fs, random.Random(12), 1)
assert won and all(x["hp"] <= 0 for x in fs) and sum(1 for x in steps if x["who"] == "pet") == 3
r = pet(atk=50); fs = [foe(hp=40), foe(hp=5), foe(hp=40)]
won, steps, _, _ = M.combat(r, M.stats(r), fs, random.Random(12), 1)
assert won and next(x for x in steps if x["who"] == "pet")["target"] == 1
# shield blocks the hit (0 damage to the pet); dodge marks dodge
r = pet(); r["shield"] = 1000; won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=30)], random.Random(13), 1)
assert won and r["hp"] == 30 and all(x["dmg"] == 0 for x in steps if x["target"] == "pet")
r = pet(dodge=0.5); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=60)], random.Random(14), 1)
assert any(x["dodge"] for x in steps)
# an impossible fight ends at the 60-round limit as a tie (pet alive, no reward)
r = pet(atk=0); r["shield"] = 10**6
won, steps, _, tie = M.combat(r, M.stats(r), [foe(hp=10**6, atk=0, spd=1)], random.Random(10), 1)
assert won and tie and sum(1 for x in steps if x["who"] == "pet") == M.MAX_ROUNDS
r = pet(atk=50); won, steps, _, tie = M.combat(r, M.stats(r), [foe(hp=5)], random.Random(10), 1)
assert won and not tie
M.ITEMS.pop("_t", None)
# enter_room: ev["foes"] and steps as dicts
meta = M.new_meta(); r = M.new_run("slime", {"hp": 30, "atk": 3}, 1); rng = random.Random(15)
seen_n = 0
for _ in range(200):
    if r["dead"]:
        break
    r["energy"] = M.ROOM_COST * 2
    ev = M.enter_room(r, meta, rng)
    if ev["kind"] in ("monster", "boss", "mimic", "horde"):
        seen_n += 1
        assert set(ev["foes"][0]) == {"sprite", "name", "boss", "element", "hp_max"}
        assert all(set(x) == KEYS for x in ev["hits"])
    else:
        assert "foes" not in ev
assert seen_n and not hasattr(M, "fight") and M.RULES_REV == 8
# tie via enter_room (boss): clears the room, but without gold, kills, boss bonus or item
rounds = M.MAX_ROUNDS; M.MAX_ROUNDS = 1
meta = M.new_meta(); r = M.new_run("slime", {"hp": 999, "atk": 1}, 1)
r["floor"], r["room"], r["energy"], r["shield"] = 5, M.ROOMS_PER_FLOOR - 1, 1e9, 10**6
maxhp = r["base"]["maxhp"]
ev = M.enter_room(r, meta, random.Random(1), mode="interactive")
M.MAX_ROUNDS = rounds
assert ev["kind"] == "boss" and ev.get("tie") and not ev["won"] and not ev["died"] and not r["dead"]
assert r["gold"] == 0 and r["kills"] == 0 and r["bosses"] == 0 and r["base"]["maxhp"] == maxhp
assert not ev.get("gold") and not r.get("pending") and not r["items"] and r["room"] == M.ROOMS_PER_FLOOR
# --- Task 3: hordes ---
assert M.HORDE_MIN_FLOOR == 3 and M.HORDE_MULT == {2: 0.75, 3: 0.6, 4: 0.5} and M.HORDE_GOLD_MULT == 1.25
assert ("horde", 9) in M.ROOM_WEIGHTS
assert [M.horde_max(f) for f in (3, 4, 5, 7, 8, 20)] == [2, 2, 3, 3, 4, 4]
assert M.make_foe(bat, 6, mult=M.HORDE_MULT[4])["hp"] < M.make_foe(bat, 6)["hp"]
assert M.make_foe(bat, 6, mult=M.HORDE_MULT[4])["atk"] == max(1, round((M.MON_ATK[0] + M.MON_ATK[1] * 6) * bat[3] * 0.5))
# lowest-HP target; with area it hits everyone (format: one step per target, never "all")
r = pet(atk=3); fs = [foe(hp=50), foe(hp=4), foe(hp=30)]
won, steps, _, _ = M.combat(r, M.stats(r), fs, random.Random(1), 3)
assert next(x for x in steps if x["who"] == "pet")["target"] == 1
r = pet(atk=3, area=True); fs = [foe(hp=50), foe(hp=4), foe(hp=30)]
won, steps, _, _ = M.combat(r, M.stats(r), fs, random.Random(1), 3)
first = [x for x in steps if x["who"] == "pet"][:3]; assert {x["target"] for x in first} >= {0, 1, 2} or first[0]["target"] == "all"
# the pet dies mid-round: the following enemies do not act after the death
r = pet(); r["hp"] = 1
fs = [foe(hp=99, atk=5, spd=20, name="Rato A"), foe(hp=99, atk=5, spd=19, name="Rato B")]
won, steps, killer, _ = M.combat(r, M.stats(r), fs, random.Random(2), 3)
assert not won and steps[-1]["target"] == "pet" and killer == fs[steps[-1]["who"]]["name"] == "Rato A"
# horde via enter_room: never before floor 3; kills and more gold
rng = random.Random(3); meta = M.new_meta(); seen = False; gold = {"horde": [], "monster": []}
for _ in range(400):
    run = M.new_run("slime", {"hp": 999, "atk": 50}, 1); run["floor"] = rng.choice([1, 2, 6]); run["energy"] = 1e9
    ev = M.enter_room(run, meta, rng)
    if ev.get("kind") == "horde":
        seen = True; assert run["floor"] >= 3 and 2 <= len(ev["foes"]) <= M.horde_max(run["floor"])
        assert run["kills"] == len(ev["foes"]) and ev["gold"] > 0
        assert ev["name"] == f"Horde ({len(ev['foes'])})" and not any(x["boss"] for x in ev["foes"])
    if ev.get("kind") in gold and run["floor"] == 6:
        gold[ev["kind"]].append(ev["gold"])
assert seen and gold["horde"] and gold["monster"] and min(gold["horde"]) > max(gold["monster"])
# --- Task 4: block, thorns, heals, attack cost and fury ---
# block 2: exactly the first 2 hits that would land become 0 damage
r = pet(atk=1, block=2); r["shield"] = 0
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=5, spd=15)], random.Random(1), 1)
blows = [x for x in steps if x["who"] == 0 and not x["dodge"]]
assert [x["locked"] for x in blows[:3]] == [True, True, False]
assert blows[0]["dmg"] == blows[1]["dmg"] == 0 and blows[2]["dmg"] > 0
assert sum(x["locked"] for x in steps) == 2
assert M.stats(pet(block=5))["block"] == M.MAX_BLOCK == 2 and M.stats(pet())["block"] == 0
# block with dodge: the dodge comes first and does not spend a charge
r = pet(atk=1, block=1, dodge=0.5)
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=5, spd=15)], random.Random(3), 1)
attacks = [x for x in steps if x["who"] == 0]
assert any(x["dodge"] for x in attacks) and sum(x["locked"] for x in attacks) == 1
assert not any(x["dodge"] and x["locked"] for x in attacks)
# thorns 0.5: returns half the damage (before the shield) and can kill the last enemy
assert M.stats(pet(thorns=0.9))["thorns"] == 0.5
r = pet(atk=1, thorns=0.5)
won, steps, _, tie = M.combat(r, M.stats(r), [foe(hp=3, atk=10, spd=15)], random.Random(4), 1)
assert won and not tie and steps[-1]["thorns"] and steps[-1]["who"] == "pet" and steps[-1]["target"] == 0
assert steps[-1]["dmg"] == round(steps[-2]["dmg"] * 0.5) and not any(x["thorns"] for x in steps[:-1])
r = pet(atk=1, thorns=0.5); r["shield"] = 1000
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=3, atk=10, spd=15)], random.Random(4), 1)
assert won and steps[-2]["dmg"] == 0 and steps[-1]["thorns"] and steps[-1]["dmg"] >= 4
r = pet(atk=50); won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=60, atk=3)], random.Random(4), 1)
assert not any(x["thorns"] or x["locked"] for x in steps)
# attack_cost: takes HP on each pet attack, but never below 1 (it never kills)
assert M._scale({"attack_cost": 2, "atk": 2}, "legendary")["attack_cost"] == 2   # the cost does not scale
r = pet(atk=1, attack_cost=50); r["hp"] = 1; r["shield"] = 10**6
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=20, atk=1, spd=1)], random.Random(5), 1)
assert won and r["hp"] == 1
r = pet(atk=50, attack_cost=2); r["shield"] = 10**6
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=40, atk=1, spd=1)], random.Random(5), 1)
assert won and r["hp"] == 30 - 2 * sum(1 for x in steps if x["who"] == "pet")
# fury: more damage with the pet at 20% HP than at 100%
def first_hit(hp):
    r = pet(atk=3, fury=1); r["hp"] = hp; r["shield"] = 10**6
    _, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(6), 1)
    return next(x["dmg"] for x in steps if x["who"] == "pet")
assert first_hit(30) <= 4 and first_hit(6) >= 3 + 8 - 1
# heal_room when entering a room (together with REGEN_PER_ROOM) and heal_floor on the stairs, up to max HP
weights = M.ROOM_WEIGHTS; M.ROOM_WEIGHTS = [("shop", 1)]                 # shop without gold: room with no effect on HP
r = pet(heal_room=5); r["hp"], r["energy"] = 10, 1e9
ev = M.enter_room(r, M.new_meta(), random.Random(7)); assert ev["kind"] == "shop" and r["hp"] == 10 + M.REGEN_PER_ROOM + 5
assert ev["item_heal"] == 5                                            # the GUI shows "+5 ♥" (only the item's part)
r = pet(heal_room=50); r["hp"], r["energy"] = 10, 1e9
ev = M.enter_room(r, M.new_meta(), random.Random(7)); assert r["hp"] == M.stats(r)["maxhp"]
assert ev["item_heal"] == r["hp"] - 10 - M.REGEN_PER_ROOM                # only what was actually healed
r = pet(); r["hp"], r["energy"] = 10, 1e9
assert "item_heal" not in M.enter_room(r, M.new_meta(), random.Random(7))   # no healing item: no floater
M.ROOM_WEIGHTS = weights
r = pet(heal_floor=5); r["hp"], r["energy"], r["room"] = 10, 1e9, M.ROOMS_PER_FLOOR
ev = M.enter_room(r, M.new_meta(), random.Random(7)); assert ev["kind"] == "stairs" and r["hp"] == 10 + M.FLOOR_BONUS_HP + 5
assert ev["item_heal"] == 5
r = pet(heal_floor=99); r["hp"], r["energy"], r["room"] = 10, 1e9, M.ROOMS_PER_FLOOR
M.enter_room(r, M.new_meta(), random.Random(7)); assert r["hp"] == M.stats(r)["maxhp"]
# fx_text: every item has text and the new fields show up
M.ITEMS.pop("_t", None)
assert all(M.fx_text(it["fx"]) for it in M.ITEMS.values())
assert M.fx_text({"block": 2}) == "bloqueia 2 golpes" and M.fx_text({"thorns": 0.3}) == "devolve 30% do dano"
assert M.fx_text({"heal_room": 3, "heal_floor": 5}) == "+3 HP por sala, +5 HP por andar"
assert M.fx_text({"attack_cost": 2, "fury": 1}) == "-2 HP por ataque, fúria +1 ATK/10% HP perdido"
assert M.fx_text({"burn": 0.2, "area": True}) == "ataque em área, 20% queimadura"
assert M.fx_text({"freeze": 0.29}) == "29% congelamento"
# --- Task 6: double hit and helpers ---
assert M.stats(pet(double=1.0))["double"] == M.MAX_DOUBLE and M.stats(pet())["double"] == 0 and M.stats(pet())["helper"] == 0
assert M.stats(pet(helper=2))["helper"] == 2
# double: second hit on the same target, right after the first; attack_cost charged once per turn
r = pet(atk=2, double=1.0, attack_cost=1); r["shield"] = 10**6
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=200, atk=1, spd=1)], random.Random(8), 1)
dup = [k for k, x in enumerate(steps) if x["double"]]
assert dup and all(steps[k]["who"] == "pet" and steps[k - 1]["who"] == "pet" and not steps[k - 1]["double"]
                   and steps[k]["target"] == steps[k - 1]["target"] for k in dup)
assert all(set(x) == KEYS for x in steps)
turns = sum(1 for x in steps if x["who"] == "pet" and not x["double"])
assert r["hp"] == max(1, 30 - turns) and 0 < len(dup) < turns
# double without the double-speed bonus: with crit 0 it never crits, even with double speed (the 1st hit crits)
r = pet(spd=20, atk=2, double=1.0); r["shield"] = 10**6
won, steps, _, _ = M.combat(r, M.stats(r), [foe(hp=500, atk=1, spd=5)], random.Random(9), 1)
assert any(x["double"] for x in steps) and not any(x["double"] and x["crit"] for x in steps)
# helper: once per round, right after the pet on a tie, never a target, no crit or status
r = pet(atk=1, helper=1, burn=1.0, crit=0.5); r["shield"] = 10**6
won, steps, _, tie = M.combat(r, M.stats(r), [foe(hp=10**6, atk=0, spd=10)], random.Random(10), 1)
aj = [k for k, x in enumerate(steps) if x["who"] == "helper"]
assert tie and len(aj) == M.MAX_ROUNDS
assert all(steps[k - 1]["who"] == "pet" and steps[k + 1]["who"] == 0 for k in aj if not steps[k - 1]["dot"])
assert all(not steps[k]["crit"] and steps[k]["status"] is None and steps[k]["dmg"] == 1 for k in aj)
assert not any(x["target"] == "helper" for x in steps)
# the helper kills the horde alone (pet with atk 1 and a strong helper); the win counts every enemy
r = pet(atk=1, helper=50); r["shield"] = 10**6
fs = [foe(hp=40, atk=1, spd=1) for _ in range(3)]
won, steps, _, tie = M.combat(r, M.stats(r), fs, random.Random(11), 1)
assert won and not tie and steps[-1]["who"] == "helper" and all(x["hp"] <= 0 for x in fs)
assert sum(1 for x in steps if x["who"] == "helper") == 3
M.ITEMS.pop("_t", None)
assert M.fx_text({"double": 0.2, "helper": 3}) == "20% golpe duplo, ajudante 3 de dano"
# Task 2: achievement counters (dodges, blocks, death by status, horde of 4)
def total_(evs, k): return sum(1 for ev in evs for h in ev.get("hits", []) if h[k])
r = pet(dodge=0.5, block=2); r["shield"] = 10**6; r["hp"] = 10**6
r["base"]["maxhp"] = 10**6; r["base"]["atk"] = 1
meta = M.new_meta(); rng = random.Random(21); evs = []
for _ in range(15):
    r["energy"] = 10**6; evs.append(M.enter_room(r, meta, rng))
assert r["counters"]["dodges"] == total_(evs, "dodge") > 0 and r["counters"]["blocks"] == total_(evs, "locked") > 0
# death by poison and by burn: an enemy with 1 HP and an active status dies on the tick
for nm, key in (("poison", "poison_kills"), ("burn", "burn_kills")):
    r = pet(); x = foe(hp=1, atk=0, spd=1); x["status"] = {nm: [0] if nm == "poison" else 2}
    won, steps, _, _ = M.combat(r, M.stats(r), [x], random.Random(1), 1)
    M._count(r, steps, [x], False)
    assert won and r["counters"][key] == 1 and sum(r["counters"].values()) == 1, (nm, r["counters"])
# a won horde of 4 counts; an old save gets the zeros
r = pet(); M._count(r, [], [foe()], True); assert r["counters"]["horde4"] == 1
stale = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0}}
assert M.migrate_run(stale)["counters"] == M.COUNTERS_ZERO and stale["counters"] is not M.COUNTERS_ZERO
# a tied horde of 4 (round limit) does not count horde4; a won one does
_cb, _rw, _hm = M.combat, M.ROOM_WEIGHTS, M.horde_max
M.ROOM_WEIGHTS = [("horde", 1)]; M.horde_max = lambda f: 4
for tie, expected in ((True, 0), (False, 1)):
    M.combat = lambda run, st, foes, rng, f, e=tie: (True, [], "", e)
    r = pet(); r["floor"] = max(M.HORDE_MIN_FLOOR, 2); rng = random.Random(5); meta = M.new_meta()
    for _ in range(300):
        r["energy"] = 10**6; ev = M.enter_room(r, meta, rng)
        if ev["name"] == "Horde (4)":
            break
    assert ev["name"] == "Horde (4)" and r["counters"]["horde4"] == expected, (tie, r["counters"])
M.combat, M.ROOM_WEIGHTS, M.horde_max = _cb, _rw, _hm
print("ok: combat")
