# -*- coding: utf-8 -*-
"""
Regras da Masmorra de Tokens (sem interface: dá para testar e simular).

Tokens viram ENERGIA. Cada sala custa ROOM_COST de energia. A cada 5 salas
o herói desce uma escada; a cada 5 andares a última sala é um chefe.
Morreu em combate ou em armadilha -> lápide no cemitério e run nova.
"""
from __future__ import annotations

import math
import random
from datetime import date

ROOM_COST = 100_000          # XP de tokens por sala
ROOMS_PER_FLOOR = 5
MAX_STORED_ROOMS = 20        # a "mochila" de energia guarda no máximo 20 salas
BOSS_EVERY = 5

# balanceamento (vida/ataque = base + por_andar * andar)
MON_HP = (4, 2.2)
MON_ATK = (1, 0.6)
BOSS_HP = (20, 5)
BOSS_ATK = (2, 0.9)
REGEN_PER_ROOM = 2
FLOOR_BONUS_HP = 2           # HP máx ganho a cada andar

ACHIEVEMENTS = {
    "andar5": "Chegar ao andar 5",
    "chefe1": "Derrotar um chefe",
    "mimico": "Derrotar um mímico",
    "rico": "Juntar 100 de ouro numa run",
    "colecionador": "Equipar 3 itens ao mesmo tempo",
    "andar10": "Chegar ao andar 10",
    "andar20": "Chegar ao andar 20",
}

SLOTS = ("mao", "escudo", "cabeca")
SLOT_NAMES = {"mao": "Mão", "escudo": "Escudo", "cabeca": "Cabeça"}

# fx: atk, def, maxhp, dodge, gold (+% ouro), trap (multiplicador de dano de
#     armadilha), energy (+% energia => salas mais baratas), lifesteal (cura por vitória)
ITEMS = {
    "adaga":        {"name": "Adaga Enferrujada",  "slot": "mao",    "tier": 1, "fx": {"atk": 2}},
    "espada_osso":  {"name": "Espada de Osso",     "slot": "mao",    "tier": 2, "fx": {"atk": 4}},
    "cajado":       {"name": "Cajado Espectral",   "slot": "mao",    "tier": 3, "fx": {"atk": 4, "lifesteal": 2}, "req": "andar5"},
    "foice":        {"name": "Foice Sombria",      "slot": "mao",    "tier": 4, "fx": {"atk": 8, "maxhp": -4}, "req": "chefe1"},
    "tampa":        {"name": "Tampa de Panela",    "slot": "escudo", "tier": 1, "fx": {"def": 1}},
    "escudo_ferro": {"name": "Escudo de Ferro",    "slot": "escudo", "tier": 2, "fx": {"def": 2}},
    "lanterna":     {"name": "Lanterna Pálida",    "slot": "escudo", "tier": 2, "fx": {"def": 1, "trap": 0.5}},
    "grimorio":     {"name": "Grimório Proibido",  "slot": "escudo", "tier": 3, "fx": {"atk": 2, "def": 2}, "req": "andar10"},
    "chapeu":       {"name": "Chapéu de Bruxa",    "slot": "cabeca", "tier": 1, "fx": {"gold": 0.5}},
    "gorro":        {"name": "Gorro de Ladrão",    "slot": "cabeca", "tier": 2, "fx": {"dodge": 0.15}},
    "chifres":      {"name": "Chifres de Demônio", "slot": "cabeca", "tier": 3, "fx": {"atk": 3, "maxhp": -3}, "req": "chefe1"},
    "aureola":      {"name": "Auréola Rachada",    "slot": "cabeca", "tier": 3, "fx": {"maxhp": 10}, "req": "andar10"},
    "vela":         {"name": "Vela Amaldiçoada",   "slot": "cabeca", "tier": 3, "fx": {"energy": 0.5, "trap": 2.0}, "req": "mimico"},
}

# sprite, nome, mult. de vida, mult. de ataque, andar mínimo
MONSTERS = [
    ("morcego", "Morcego", 0.8, 0.9, 1),
    ("rato", "Rato", 1.0, 0.8, 1),
    ("aranha", "Aranha", 0.9, 1.2, 2),
    ("esqueleto", "Esqueleto", 1.3, 1.0, 3),
    ("olho", "Olho Flutuante", 1.0, 1.4, 5),
]
BOSS_NAMES = {"morcego": "Morcego Vampiro", "rato": "Rei Rato", "aranha": "Aranha Mãe",
              "esqueleto": "Lorde Esqueleto", "olho": "Olho Abissal"}

ROOM_WEIGHTS = [("monster", 46), ("chest", 16), ("trap", 12), ("fountain", 11),
                ("shop", 8), ("altar", 7)]

DEFAULT_STAGE_FLOORS = [1, 3, 8, 15, 25, 40]


def fx_text(fx: dict) -> str:
    parts = []
    for k, label in (("atk", "ATK"), ("def", "DEF"), ("maxhp", "HP")):
        if fx.get(k):
            parts.append(f"{fx[k]:+d} {label}")
    if fx.get("dodge"):
        parts.append(f"{int(fx['dodge'] * 100)}% esquiva")
    if fx.get("gold"):
        parts.append(f"+{int(fx['gold'] * 100)}% ouro")
    if fx.get("energy"):
        parts.append(f"+{int(fx['energy'] * 100)}% energia")
    if fx.get("lifesteal"):
        parts.append(f"+{fx['lifesteal']} HP por vitória")
    if fx.get("trap"):
        parts.append("armadilhas x" + (f"{fx['trap']:g}"))
    return ", ".join(parts)


def new_meta() -> dict:
    return {"achievements": [], "graveyard": [], "runs": 0,
            "best": {"floor": 0, "room": 0}, "next_char": "slime"}


def new_run(char_key: str, base_stats: dict, run_id: int) -> dict:
    hp = int(base_stats.get("hp", 20))
    return {
        "id": run_id, "char": char_key, "floor": 1, "room": 0, "stage": 0,
        "hp": hp,
        "base": {"maxhp": hp, "atk": int(base_stats.get("atk", 3)),
                 "def": int(base_stats.get("def", 0)), "dodge": float(base_stats.get("dodge", 0))},
        "items": {s: None for s in SLOTS},
        "gold": 0, "energy": 0.0, "kills": 0, "bosses": 0,
        "started": date.today().isoformat(), "dead": False,
    }


def stats(run: dict) -> dict:
    b = run["base"]
    st = {"maxhp": b["maxhp"], "atk": b["atk"], "def": b["def"], "dodge": b["dodge"],
          "gold": 0.0, "trap": 1.0, "energy": 0.0, "lifesteal": 0}
    for key in run["items"].values():
        if not key:
            continue
        for k, v in ITEMS[key]["fx"].items():
            if k == "trap":
                st["trap"] *= v
            else:
                st[k] += v
    st["maxhp"] = max(5, st["maxhp"])
    st["atk"] = max(1, st["atk"])
    st["dodge"] = min(0.5, st["dodge"])
    run["hp"] = min(run["hp"], st["maxhp"])
    return st


def room_cost(run: dict) -> float:
    return ROOM_COST / (1 + stats(run)["energy"])


def add_energy(run: dict, xp: float) -> None:
    run["energy"] = min(run["energy"] + xp, MAX_STORED_ROOMS * ROOM_COST)


def can_enter(run: dict) -> bool:
    return not run["dead"] and run["energy"] >= room_cost(run)


def stage_for_floor(floor: int, stage_floors: list[int]) -> int:
    idx = 0
    for i, f in enumerate(stage_floors):
        if floor >= f:
            idx = i
    return idx


def unlocked_items(meta: dict) -> list[str]:
    have = set(meta["achievements"])
    return [k for k, it in ITEMS.items() if not it.get("req") or it["req"] in have]


def roll_item(run: dict, meta: dict, rng: random.Random, best: bool = False) -> str:
    pool = unlocked_items(meta)
    max_tier = 1 + run["floor"] // 3
    pool_ok = [k for k in pool if ITEMS[k]["tier"] <= max_tier] or pool
    if best:
        top = max(ITEMS[k]["tier"] for k in pool_ok)
        pool_ok = [k for k in pool_ok if ITEMS[k]["tier"] == top]
    return rng.choice(pool_ok)


def give_item(run: dict, key: str, ev: dict) -> None:
    """Equipa se o espaço estiver vazio ou o item for igual/melhor; senão vende."""
    it = ITEMS[key]
    cur = run["items"][it["slot"]]
    if cur is None or it["tier"] >= ITEMS[cur]["tier"]:
        run["items"][it["slot"]] = key
        if "maxhp" in it["fx"] and it["fx"]["maxhp"] > 0:
            run["hp"] += it["fx"]["maxhp"]
        ev["item"] = key
        stats(run)
    else:
        price = 3 * it["tier"]
        run["gold"] += price
        ev["gold"] = ev.get("gold", 0) + price
        ev["lines"].append(f"Vendeu {it['name']} (+{price} ouro)")


def fight(run: dict, st: dict, foe_hp: int, foe_atk: int, rng: random.Random):
    """Combate automático. Retorna (venceu, golpes) — golpes servem para a animação."""
    hits = []
    while True:
        dmg = max(1, st["atk"] + rng.randint(-1, 1))
        foe_hp -= dmg
        hits.append(("pet", dmg))
        if foe_hp <= 0:
            return True, hits
        if rng.random() < st["dodge"]:
            hits.append(("dodge", 0))
            continue
        d = max(1, foe_atk - st["def"] + rng.randint(-1, 1))
        run["hp"] -= d
        hits.append(("foe", d))
        if run["hp"] <= 0:
            run["hp"] = 0
            return False, hits


def die(run: dict, meta: dict, ev: dict, killer: str) -> None:
    run["dead"] = True
    ev["died"] = True
    ev["killed_by"] = killer
    meta["runs"] += 1
    meta["graveyard"].append({
        "run": run["id"], "char": run["char"], "floor": run["floor"], "room": run["room"],
        "killer": killer, "items": [k for k in run["items"].values() if k],
        "gold": run["gold"], "kills": run["kills"], "date": date.today().isoformat(),
    })
    meta["graveyard"] = meta["graveyard"][-50:]


def _check_achievements(run: dict, meta: dict, ev: dict) -> None:
    have = set(meta["achievements"])
    new = []

    def grant(key, cond):
        if cond and key not in have:
            new.append(key)
            have.add(key)

    grant("andar5", run["floor"] >= 5)
    grant("andar10", run["floor"] >= 10)
    grant("andar20", run["floor"] >= 20)
    grant("chefe1", run["bosses"] >= 1)
    grant("mimico", ev.get("kind") == "mimic" and ev.get("won"))
    grant("rico", run["gold"] >= 100)
    grant("colecionador", all(run["items"].values()))
    if new:
        meta["achievements"].extend(new)
        ev["unlocks"] = new
    b = meta["best"]
    if (run["floor"], run["room"]) > (b["floor"], b["room"]):
        meta["best"] = {"floor": run["floor"], "room": run["room"]}


def enter_room(run: dict, meta: dict, rng: random.Random,
               stage_floors: list[int] | None = None) -> dict:
    """Gasta energia, resolve a próxima sala e devolve o que aconteceu."""
    stage_floors = stage_floors or DEFAULT_STAGE_FLOORS
    run["energy"] -= room_cost(run)
    st = stats(run)
    ev: dict = {"lines": [], "won": False, "died": False}
    f = run["floor"]

    # escada para o próximo andar
    if run["room"] >= ROOMS_PER_FLOOR:
        run["floor"] += 1
        run["room"] = 0
        ev.update(kind="stairs", name=f"Andar {run['floor']}", sprite="escada")
        if FLOOR_BONUS_HP:
            run["base"]["maxhp"] += FLOOR_BONUS_HP
            run["hp"] += FLOOR_BONUS_HP
        new_stage = stage_for_floor(run["floor"], stage_floors)
        if new_stage > run["stage"]:
            run["stage"] = new_stage
            run["base"]["maxhp"] += 4
            run["base"]["atk"] += 1
            run["hp"] += 4
            ev["evolved"] = True
        _check_achievements(run, meta, ev)
        stats(run)
        return ev

    run["room"] += 1
    run["hp"] = min(st["maxhp"], run["hp"] + REGEN_PER_ROOM)   # regenera um pouquinho a cada sala

    if run["room"] == ROOMS_PER_FLOOR and f % BOSS_EVERY == 0:
        kind = "boss"
    else:
        kind = rng.choices([k for k, _ in ROOM_WEIGHTS], [w for _, w in ROOM_WEIGHTS])[0]
        if kind == "chest" and f >= 2 and rng.random() < 0.12:
            kind = "mimic"
    ev["kind"] = kind

    if kind in ("monster", "boss", "mimic"):
        if kind == "boss":
            m = rng.choice([m for m in MONSTERS if m[4] <= f])
            sprite, name = m[0], BOSS_NAMES[m[0]]
            hp, atk = round(BOSS_HP[0] + BOSS_HP[1] * f), round(BOSS_ATK[0] + BOSS_ATK[1] * f)
        elif kind == "mimic":
            sprite, name = "mimico", "Mímico"
            hp, atk = round((MON_HP[0] + MON_HP[1] * f) * 1.4), round((MON_ATK[0] + MON_ATK[1] * f) * 1.1)
        else:
            m = rng.choice([m for m in MONSTERS if m[4] <= f])
            sprite, name = m[0], m[1]
            hp, atk = round((MON_HP[0] + MON_HP[1] * f) * m[2]), max(1, round((MON_ATK[0] + MON_ATK[1] * f) * m[3]))
        ev.update(name=name, sprite=sprite, boss=(kind == "boss"))
        hp_before = run["hp"]
        won, hits = fight(run, st, hp, atk, rng)
        ev["hits"] = hits
        ev["dmg"] = hp_before - run["hp"]
        if not won:
            die(run, meta, ev, name)
            return ev
        ev["won"] = True
        run["kills"] += 1
        gold = round((rng.randint(1, 3) + f // 2) * (1 + st["gold"]))
        if st["lifesteal"]:
            run["hp"] = min(st["maxhp"], run["hp"] + st["lifesteal"])
        if kind == "boss":
            run["bosses"] += 1
            run["base"]["maxhp"] += 5
            gold += 15 + f
            stats(run)
            run["hp"] = stats(run)["maxhp"]
            give_item(run, roll_item(run, meta, rng, best=True), ev)
        elif kind == "mimic":
            gold += 5 + f
            give_item(run, roll_item(run, meta, rng), ev)
        run["gold"] += gold
        ev["gold"] = ev.get("gold", 0) + gold

    elif kind == "chest":
        ev.update(name="Baú", sprite="bau")
        if rng.random() < 0.75:
            give_item(run, roll_item(run, meta, rng), ev)
        else:
            gold = round((5 + 2 * f) * (1 + st["gold"]))
            run["gold"] += gold
            ev["gold"] = gold

    elif kind == "trap":
        ev.update(name="Armadilha", sprite="armadilha")
        if rng.random() < st["dodge"]:
            ev["dodged"] = True
        else:
            dmg = max(1, round((2 + 0.6 * f) * st["trap"]))
            run["hp"] -= dmg
            ev["dmg"] = dmg
            if run["hp"] <= 0:
                run["hp"] = 0
                die(run, meta, ev, "Armadilha")
                return ev

    elif kind == "fountain":
        ev.update(name="Fonte", sprite="fonte")
        heal = max(1, round(st["maxhp"] * 0.35))
        heal = min(heal, st["maxhp"] - run["hp"])
        run["hp"] += heal
        ev["heal"] = heal

    elif kind == "shop":
        ev.update(name="Lojinha", sprite="loja")
        potion, item_price = 6 + f, 12 + 3 * f
        if run["hp"] < st["maxhp"] * 0.5 and run["gold"] >= potion:
            run["gold"] -= potion
            heal = min(st["maxhp"] - run["hp"], round(st["maxhp"] * 0.5))
            run["hp"] += heal
            ev["heal"] = heal
            ev["lines"].append(f"Comprou poção (-{potion} ouro)")
        elif run["gold"] >= item_price:
            run["gold"] -= item_price
            ev["lines"].append(f"Pagou {item_price} ouro")
            give_item(run, roll_item(run, meta, rng, best=True), ev)
        else:
            ev["lines"].append("Sem ouro pra comprar...")

    elif kind == "altar":
        ev.update(name="Altar Sombrio", sprite="altar")
        pact = rng.choice(["sangue", "pedra", "bencao", "ouro"])
        b = run["base"]
        if pact == "sangue":
            loss = max(2, round(b["maxhp"] * 0.2))
            b["maxhp"] -= loss
            b["atk"] += 2
            ev["lines"].append(f"Pacto de sangue: -{loss} HP máx, +2 ATK")
        elif pact == "pedra":
            if b["atk"] > 2:
                b["atk"] -= 1
                b["def"] += 1
                ev["lines"].append("Pele de pedra: -1 ATK, +1 DEF")
            else:
                ev["lines"].append("O altar te ignora...")
        elif pact == "bencao":
            b["maxhp"] += 4
            run["hp"] += 4
            ev["lines"].append("Bênção sombria: +4 HP máx")
        else:
            if run["gold"] >= 10:
                run["gold"] -= 10
                run["hp"] = stats(run)["maxhp"]
                ev["lines"].append("Trocou 10 ouro por cura total")
            else:
                run["gold"] += 5
                ev["gold"] = 5
                ev["lines"].append("Achou 5 moedas no altar")
        stats(run)

    _check_achievements(run, meta, ev)
    return ev
