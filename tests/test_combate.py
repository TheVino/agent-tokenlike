import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import masmorra as M

run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
st = M.stats(run)
assert st["spd"] == 10 and st["crit"] == M.PET_CRIT and st["critdmg"] == 1.5 and st["area"] is False
assert st["queimar"] == 0 and st["congelar"] == 0
assert M.new_run("x", {"spd": 14}, 2)["base"]["spd"] == 14
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0}}
M.migrate_run(old); assert old["base"]["spd"] == 10 and M.stats(old)["spd"] == 10
# crit/critdmg: só os do herói vão para a base; sem eles, stats() usa as constantes (e o save antigo também)
assert "crit" not in run["base"] and "critdmg" not in run["base"]
assert M.stats(M.new_run("x", {"crit": 0.3, "critdmg": 2}, 2))["crit"] == 0.3
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0, "spd": 10, "crit": 0.1, "critdmg": 1.5}}
M.migrate_run(old); crit0 = M.PET_CRIT; M.PET_CRIT = 0.2
assert M.stats(old)["crit"] == 0.2 and M.stats(run)["crit"] == 0.2; M.PET_CRIT = crit0
M.ITEMS["_t"] = {"name": "t", "fx": {"crit": 0.9, "queimar": 0.9, "spd": -50, "area": True},
                 "rarities": ["comum"], "consume": {"heal": 1}, "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
run["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
st = M.stats(run)
assert st["crit"] == M.MAX_CRIT and st["queimar"] == M.MAX_ELEM_CHANCE and st["spd"] == 1 and st["area"] is True
del M.ITEMS["_t"]
bat = next(m for m in M.MONSTERS if m[0] == "morcego"); ske = next(m for m in M.MONSTERS if m[0] == "esqueleto")
assert M.make_foe(bat, 5)["spd"] > M.make_foe(ske, 5)["spd"]
assert M.make_foe(bat, 5)["element"] is None and M.make_foe(bat, 5, boss=True)["element"] == "raio"
# mult é aplicado ANTES do arredondamento (um round só)
assert M.make_foe(bat, 5, mult=0.5)["hp"] == max(1, round((M.MON_HP[0] + M.MON_HP[1] * 5) * bat[2] * 0.5))
assert M.make_mimic(3)["element"] is None and M.make_mimic(3)["hp"] == M.make_mimic(3)["hp_max"]
# --- Task 2: combate por rodadas ---
import random
assert isinstance(M.new_run("x", {"spd": 14}, 2)["base"]["spd"], float)
M.ITEMS["_a"] = {"name": "a", "fx": {"area": True, "atk": 1}, "rarities": ["lendario"], "consume": {"heal": 1},
                 "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
assert M.item_fx("_a", "lendario")["area"] is True and M.item_fx("_a", "lendario")["atk"] > 1   # area não escala
del M.ITEMS["_a"]


def foe(hp=10, atk=1, spd=5, boss=False, element=None, crit=0.0, name="Rato"):
    return {"sprite": "rato", "name": name, "boss": boss, "element": element, "hp": hp, "hp_max": hp,
            "atk": atk, "spd": spd, "crit": crit, "critdmg": 1.5, "status": {}}


def pet(spd=10, atk=3, crit=0.0, **fx):
    r = M.new_run("slime", {"hp": 30, "atk": atk, "spd": spd}, 1); r["base"]["crit"] = crit
    if fx:
        M.ITEMS["_t"] = {"name": "t", "fx": fx, "rarities": ["comum"], "consume": {"heal": 1},
                         "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
        r["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
    return r


CHAVES = {"who", "target", "dmg", "crit", "status", "skip", "dot", "dodge", "bloqueado", "espinhos"}
# ordem: inimigo mais rápido age antes; empate -> pet antes
r = pet(spd=5); won, steps, _, _ = M.combate(r, M.stats(r), [foe(spd=9)], random.Random(1), 1)
assert steps[0]["who"] == 0 and all(set(x) == CHAVES for x in steps)
r = pet(spd=9); won, steps, _, _ = M.combate(r, M.stats(r), [foe(spd=9)], random.Random(1), 1)
assert steps[0]["who"] == "pet"
# dobro da velocidade: crítico com dano x (critdmg*2); com crit base 0.5 + 0.5 = 1.0 sempre crita
r = pet(spd=20, atk=4, crit=0.5); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=100, spd=10)], random.Random(2), 1)
s = next(x for x in steps if x["who"] == "pet"); assert s["crit"] and s["dmg"] >= 3 * 3     # (4±1) * 1.5 * 2
# sem o dobro e com crit 0, nunca crita
r = pet(spd=19, atk=4); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=100, spd=10)], random.Random(2), 1)
assert not any(x["who"] == "pet" and x["crit"] for x in steps)
# inimigo com o dobro também ganha (crit 0.5 + 0.5)
r = pet(spd=5); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=100, spd=10, crit=0.0, atk=2)], random.Random(3), 1)
assert any(x["who"] == 0 and x["crit"] for x in steps)
# queimadura (chance no teto de 0.6): dano por turno no começo da rodada, 3 turnos, depois para
r = pet(queimar=1.0); assert M.stats(r)["queimar"] == M.MAX_ELEM_CHANCE
won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=0, spd=1)], random.Random(4), 10)
dots = [x for x in steps if x["dot"] and x["target"] == 0]
assert dots and all(x["dmg"] == round(2 + 0.3 * 10) and x["status"] == "queimadura" for x in dots)
f0 = foe(hp=1000, atk=0, spd=1); f0["status"]["queimadura"] = M.QUEIMA_TURNOS
r = pet(); won, steps, _, _ = M.combate(r, M.stats(r), [f0], random.Random(4), 10)
assert sum(1 for x in steps if x["dot"]) == M.QUEIMA_TURNOS        # sem renovar, para depois de 3
# veneno cresce: 1, 2, 3 ...
r = pet(envenenar=0.6); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=0, spd=1)], random.Random(5), 1)
v = [x["dmg"] for x in steps if x["dot"] and x["target"] == 0][:3]
assert len(v) == 3 and v == sorted(v) and v[-1] > v[0] and v[0] == 1
# congelamento: perde o turno e sai
r = pet(congelar=0.6); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(6), 1)
assert any(x["who"] == 0 and x["skip"] for x in steps)
f0 = foe(hp=1000, atk=1, spd=1); f0["status"]["congelamento"] = M.GELO_TURNOS
r = pet(); won, steps, _, _ = M.combate(r, M.stats(r), [f0], random.Random(6), 1)
assert sum(1 for x in steps if x["skip"]) == 1 and not f0["status"]["congelamento"]   # perdeu um turno e saiu
# sem sorte no gelo: os 2 turnos passam sem perder a vez e o congelamento acaba sozinho
f0 = foe(hp=1000, atk=1, spd=1); f0["status"]["congelamento"] = M.GELO_TURNOS
r = pet(); won, steps, _, _ = M.combate(r, M.stats(r), [f0], random.Random(4), 1)
assert not any(x["skip"] for x in steps) and f0["status"]["congelamento"] == 0
# eletricidade: pode perder a vez
r = pet(eletrizar=0.6); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(11), 1)
assert any(x["who"] == 0 and x["skip"] for x in steps)
# monstro comum nunca aplica status; chefe aplica o seu elemento no pet
r = pet(); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=40, atk=1)], random.Random(7), 1)
assert not any(x["who"] == 0 and x["status"] for x in steps)
r = pet(); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=200, atk=1, boss=True, element="fogo")], random.Random(8), 5)
assert any(x["who"] == 0 and x["status"] == "queimadura" for x in steps)
assert any(x["dot"] and x["target"] == "pet" for x in steps)
# morte por status de chefe tem assassino "Queimadura" ou "Veneno"
r = pet(); r["hp"] = 3
won, steps, killer, _ = M.combate(r, M.stats(r), [foe(hp=999, atk=0, spd=99, boss=True, element="fogo")], random.Random(9), 20)
assert not won and killer in ("Queimadura", "Rato") and r["hp"] == 0
# o escudo segura os golpes, mas não o dano de status: o veneno do chefe mata
r = pet(); r["hp"] = 1; r["shield"] = 10**6
won, steps, killer, _ = M.combate(r, M.stats(r), [foe(hp=999, atk=0, spd=1, boss=True, element="veneno")], random.Random(9), 1)
assert not won and killer == "Veneno" and steps[-1]["dot"] and steps[-1]["target"] == "pet"
# área acerta todos; sem área, o alvo é o de menor HP
r = pet(atk=50, area=True); fs = [foe(hp=40), foe(hp=40), foe(hp=40)]
won, steps, _, _ = M.combate(r, M.stats(r), fs, random.Random(12), 1)
assert won and all(x["hp"] <= 0 for x in fs) and sum(1 for x in steps if x["who"] == "pet") == 3
r = pet(atk=50); fs = [foe(hp=40), foe(hp=5), foe(hp=40)]
won, steps, _, _ = M.combate(r, M.stats(r), fs, random.Random(12), 1)
assert won and next(x for x in steps if x["who"] == "pet")["target"] == 1
# escudo bloqueia o golpe (dano 0 no pet); esquiva marca dodge
r = pet(); r["shield"] = 1000; won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=30)], random.Random(13), 1)
assert won and r["hp"] == 30 and all(x["dmg"] == 0 for x in steps if x["target"] == "pet")
r = pet(dodge=0.5); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=60)], random.Random(14), 1)
assert any(x["dodge"] for x in steps)
# luta impossível termina no limite de 60 rodadas como empate (pet vivo, sem prêmio)
r = pet(atk=0); r["shield"] = 10**6
won, steps, _, empate = M.combate(r, M.stats(r), [foe(hp=10**6, atk=0, spd=1)], random.Random(10), 1)
assert won and empate and sum(1 for x in steps if x["who"] == "pet") == M.MAX_ROUNDS
r = pet(atk=50); won, steps, _, empate = M.combate(r, M.stats(r), [foe(hp=5)], random.Random(10), 1)
assert won and not empate
M.ITEMS.pop("_t", None)
# enter_room: ev["foes"] e passos em dict
meta = M.new_meta(); r = M.new_run("slime", {"hp": 30, "atk": 3}, 1); rng = random.Random(15)
vistos = 0
for _ in range(200):
    if r["dead"]:
        break
    r["energy"] = M.ROOM_COST * 2
    ev = M.enter_room(r, meta, rng)
    if ev["kind"] in ("monster", "boss", "mimic", "horde"):
        vistos += 1
        assert set(ev["foes"][0]) == {"sprite", "name", "boss", "element", "hp_max"}
        assert all(set(x) == CHAVES for x in ev["hits"])
    else:
        assert "foes" not in ev
assert vistos and not hasattr(M, "fight") and M.REGRAS_REV == 4
# empate via enter_room (chefe): passa a sala, mas sem ouro, kills, bônus de chefe nem item
rounds = M.MAX_ROUNDS; M.MAX_ROUNDS = 1
meta = M.new_meta(); r = M.new_run("slime", {"hp": 999, "atk": 1}, 1)
r["floor"], r["room"], r["energy"], r["shield"] = 5, M.ROOMS_PER_FLOOR - 1, 1e9, 10**6
maxhp = r["base"]["maxhp"]
ev = M.enter_room(r, meta, random.Random(1), mode="interativo")
M.MAX_ROUNDS = rounds
assert ev["kind"] == "boss" and ev.get("empate") and not ev["won"] and not ev["died"] and not r["dead"]
assert r["gold"] == 0 and r["kills"] == 0 and r["bosses"] == 0 and r["base"]["maxhp"] == maxhp
assert not ev.get("gold") and not r.get("pending") and not r["items"] and r["room"] == M.ROOMS_PER_FLOOR
# --- Task 3: hordas ---
assert M.HORDE_MIN_FLOOR == 3 and M.HORDE_MULT == {2: 0.75, 3: 0.6, 4: 0.5} and M.HORDE_GOLD_MULT == 1.25
assert ("horde", 9) in M.ROOM_WEIGHTS
assert [M.horde_max(f) for f in (3, 4, 5, 7, 8, 20)] == [2, 2, 3, 3, 4, 4]
assert M.make_foe(bat, 6, mult=M.HORDE_MULT[4])["hp"] < M.make_foe(bat, 6)["hp"]
assert M.make_foe(bat, 6, mult=M.HORDE_MULT[4])["atk"] == max(1, round((M.MON_ATK[0] + M.MON_ATK[1] * 6) * bat[3] * 0.5))
# alvo de menor HP; com área acerta todos (formato: um passo por alvo, nunca "todos")
r = pet(atk=3); fs = [foe(hp=50), foe(hp=4), foe(hp=30)]
won, steps, _, _ = M.combate(r, M.stats(r), fs, random.Random(1), 3)
assert next(x for x in steps if x["who"] == "pet")["target"] == 1
r = pet(atk=3, area=True); fs = [foe(hp=50), foe(hp=4), foe(hp=30)]
won, steps, _, _ = M.combate(r, M.stats(r), fs, random.Random(1), 3)
first = [x for x in steps if x["who"] == "pet"][:3]; assert {x["target"] for x in first} >= {0, 1, 2} or first[0]["target"] == "todos"
# pet morre no meio da rodada: inimigos seguintes não agem depois da morte
r = pet(); r["hp"] = 1
fs = [foe(hp=99, atk=5, spd=20, name="Rato A"), foe(hp=99, atk=5, spd=19, name="Rato B")]
won, steps, killer, _ = M.combate(r, M.stats(r), fs, random.Random(2), 3)
assert not won and steps[-1]["target"] == "pet" and killer == fs[steps[-1]["who"]]["name"] == "Rato A"
# horda via enter_room: nunca antes do andar 3; kills e ouro maior
rng = random.Random(3); meta = M.new_meta(); seen = False; ouro = {"horde": [], "monster": []}
for _ in range(400):
    run = M.new_run("slime", {"hp": 999, "atk": 50}, 1); run["floor"] = rng.choice([1, 2, 6]); run["energy"] = 1e9
    ev = M.enter_room(run, meta, rng)
    if ev.get("kind") == "horde":
        seen = True; assert run["floor"] >= 3 and 2 <= len(ev["foes"]) <= M.horde_max(run["floor"])
        assert run["kills"] == len(ev["foes"]) and ev["gold"] > 0
        assert ev["name"] == f"Horda ({len(ev['foes'])})" and not any(x["boss"] for x in ev["foes"])
    if ev.get("kind") in ouro and run["floor"] == 6:
        ouro[ev["kind"]].append(ev["gold"])
assert seen and ouro["horde"] and ouro["monster"] and min(ouro["horde"]) > max(ouro["monster"])
# --- Task 4: bloqueio, espinhos, curas, custo de ataque e fúria ---
# bloqueio 2: exatamente os 2 primeiros golpes que acertariam viram dano 0
r = pet(atk=1, bloqueio=2); r["shield"] = 0
won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=5, spd=15)], random.Random(1), 1)
golpes = [x for x in steps if x["who"] == 0 and not x["dodge"]]
assert [x["bloqueado"] for x in golpes[:3]] == [True, True, False]
assert golpes[0]["dmg"] == golpes[1]["dmg"] == 0 and golpes[2]["dmg"] > 0
assert sum(x["bloqueado"] for x in steps) == 2
assert M.stats(pet(bloqueio=5))["bloqueio"] == 3 and M.stats(pet())["bloqueio"] == 0
# bloqueio com esquiva: a esquiva vem antes e não gasta carga
r = pet(atk=1, bloqueio=1, dodge=0.5)
won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=5, spd=15)], random.Random(3), 1)
ataques = [x for x in steps if x["who"] == 0]
assert any(x["dodge"] for x in ataques) and sum(x["bloqueado"] for x in ataques) == 1
assert not any(x["dodge"] and x["bloqueado"] for x in ataques)
# espinhos 0,5: devolve metade do dano (antes do escudo) e pode matar o último inimigo
assert M.stats(pet(espinhos=0.9))["espinhos"] == 0.5
r = pet(atk=1, espinhos=0.5)
won, steps, _, empate = M.combate(r, M.stats(r), [foe(hp=3, atk=10, spd=15)], random.Random(4), 1)
assert won and not empate and steps[-1]["espinhos"] and steps[-1]["who"] == "pet" and steps[-1]["target"] == 0
assert steps[-1]["dmg"] == round(steps[-2]["dmg"] * 0.5) and not any(x["espinhos"] for x in steps[:-1])
r = pet(atk=1, espinhos=0.5); r["shield"] = 1000
won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=3, atk=10, spd=15)], random.Random(4), 1)
assert won and steps[-2]["dmg"] == 0 and steps[-1]["espinhos"] and steps[-1]["dmg"] >= 4
r = pet(atk=50); won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=60, atk=3)], random.Random(4), 1)
assert not any(x["espinhos"] or x["bloqueado"] for x in steps)
# custo_ataque: tira HP a cada ataque do pet, mas nunca abaixo de 1 (nem mata)
assert M._scale({"custo_ataque": 2, "atk": 2}, "lendario")["custo_ataque"] == 2   # custo não escala
r = pet(atk=1, custo_ataque=50); r["hp"] = 1; r["shield"] = 10**6
won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=20, atk=1, spd=1)], random.Random(5), 1)
assert won and r["hp"] == 1
r = pet(atk=50, custo_ataque=2); r["shield"] = 10**6
won, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=40, atk=1, spd=1)], random.Random(5), 1)
assert won and r["hp"] == 30 - 2 * sum(1 for x in steps if x["who"] == "pet")
# fúria: mais dano com o pet a 20% do HP do que a 100%
def primeiro_golpe(hp):
    r = pet(atk=3, furia=1); r["hp"] = hp; r["shield"] = 10**6
    _, steps, _, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(6), 1)
    return next(x["dmg"] for x in steps if x["who"] == "pet")
assert primeiro_golpe(30) <= 4 and primeiro_golpe(6) >= 3 + 8 - 1
# cura_sala ao entrar numa sala (junto com REGEN_PER_ROOM) e cura_andar na escada, até o HP máximo
pesos = M.ROOM_WEIGHTS; M.ROOM_WEIGHTS = [("shop", 1)]                 # loja sem ouro: sala sem efeito no HP
r = pet(cura_sala=5); r["hp"], r["energy"] = 10, 1e9
ev = M.enter_room(r, M.new_meta(), random.Random(7)); assert ev["kind"] == "shop" and r["hp"] == 10 + M.REGEN_PER_ROOM + 5
r = pet(cura_sala=50); r["hp"], r["energy"] = 10, 1e9
M.enter_room(r, M.new_meta(), random.Random(7)); assert r["hp"] == M.stats(r)["maxhp"]
M.ROOM_WEIGHTS = pesos
r = pet(cura_andar=5); r["hp"], r["energy"], r["room"] = 10, 1e9, M.ROOMS_PER_FLOOR
ev = M.enter_room(r, M.new_meta(), random.Random(7)); assert ev["kind"] == "stairs" and r["hp"] == 10 + M.FLOOR_BONUS_HP + 5
r = pet(cura_andar=99); r["hp"], r["energy"], r["room"] = 10, 1e9, M.ROOMS_PER_FLOOR
M.enter_room(r, M.new_meta(), random.Random(7)); assert r["hp"] == M.stats(r)["maxhp"]
# fx_text: todo item tem texto e os campos novos aparecem
M.ITEMS.pop("_t", None)
assert all(M.fx_text(it["fx"]) for it in M.ITEMS.values())
assert M.fx_text({"bloqueio": 2}) == "bloqueia 2 golpes" and M.fx_text({"espinhos": 0.3}) == "devolve 30% do dano"
assert M.fx_text({"cura_sala": 3, "cura_andar": 5}) == "+3 HP por sala, +5 HP por andar"
assert M.fx_text({"custo_ataque": 2, "furia": 1}) == "-2 HP por ataque, fúria +1 ATK/10% HP perdido"
assert M.fx_text({"queimar": 0.2, "area": True}) == "ataque em área, 20% queimadura"
assert M.fx_text({"congelar": 0.29}) == "29% congelamento"
print("ok: combate")
