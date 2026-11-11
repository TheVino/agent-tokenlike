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
    "colecionador": "Pegar 10 itens numa run",
    "andar10": "Chegar ao andar 10",
    "andar20": "Chegar ao andar 20",
}

RARITIES = ("comum", "raro", "epico", "lendario")
RAR_MULT = {"comum": 1, "raro": 1.5, "epico": 2, "lendario": 3}
RAR_NAMES = {"comum": "Comum", "raro": "Raro", "epico": "Épico", "lendario": "Lendário"}
RAR_COLOR = {"comum": None, "raro": "#6fd6ff", "epico": "#b48cff", "lendario": "#ffd23f"}
CHOICE_WINDOW_S = 30         # janela de escolha do modo interativo (a GUI conta o tempo)
MAX_ENERGY_BONUS = 1.0       # soma de "energy" limitada a +100%
TRAP_LIMITS = (0.25, 3.0)    # piso e teto do multiplicador de armadilha somado

_C = ["comum", "raro", "epico"]
_R = ["raro", "epico", "lendario"]

# fx: atk, def, maxhp, dodge, gold (+% ouro), trap (multiplicador de dano de
#     armadilha), energy (+% energia => salas mais baratas), lifesteal (cura por vitória)
# consume: o que acontece se o herói consumir o item em vez de pegar (heal ou shield)
ITEMS = {
    "adaga":        {"name": "Adaga Enferrujada",  "rarities": _C, "fx": {"atk": 2}, "consume": {"heal": 6},
                     "look": {"type": "obj", "anchor": "dir", "art": "adaga"}},
    "espada_osso":  {"name": "Espada de Osso",     "rarities": _C, "fx": {"atk": 4}, "consume": {"heal": 8},
                     "look": {"type": "obj", "anchor": "dir", "art": "espada_osso"}},
    "cajado":       {"name": "Cajado Espectral",   "rarities": _R, "fx": {"atk": 4, "lifesteal": 2},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "dir", "art": "cajado"},
                     "req": "andar5"},
    "foice":        {"name": "Foice Sombria",      "rarities": ["epico", "lendario"], "fx": {"atk": 8, "maxhp": -4},
                     "consume": {"heal": 12}, "look": {"type": "obj", "anchor": "dir", "art": "foice"},
                     "req": "chefe1"},
    "tampa":        {"name": "Tampa de Panela",    "rarities": _C, "fx": {"def": 1}, "consume": {"shield": 5},
                     "look": {"type": "obj", "anchor": "esq", "art": "tampa"}},
    "escudo_ferro": {"name": "Escudo de Ferro",    "rarities": _C, "fx": {"def": 2}, "consume": {"shield": 7},
                     "look": {"type": "obj", "anchor": "esq", "art": "escudo_ferro"}},
    "lanterna":     {"name": "Lanterna Pálida",    "rarities": _C, "fx": {"def": 1, "trap": 0.5},
                     "consume": {"shield": 7}, "look": {"type": "obj", "anchor": "esq", "art": "lanterna"}},
    "grimorio":     {"name": "Grimório Proibido",  "rarities": _R, "fx": {"atk": 2, "def": 2},
                     "consume": {"shield": 9}, "look": {"type": "obj", "anchor": "esq", "art": "grimorio"},
                     "req": "andar10"},
    "chapeu":       {"name": "Chapéu de Bruxa",    "rarities": _C, "fx": {"gold": 0.5}, "consume": {"heal": 6},
                     "look": {"type": "obj", "anchor": "topo", "art": "chapeu"}},
    "gorro":        {"name": "Gorro de Ladrão",    "rarities": _C, "fx": {"dodge": 0.15}, "consume": {"heal": 8},
                     "look": {"type": "obj", "anchor": "topo", "art": "gorro"}},
    "chifres":      {"name": "Chifres de Demônio", "rarities": _R, "fx": {"atk": 3, "maxhp": -3},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "topo", "art": "chifres"},
                     "req": "chefe1"},
    "aureola":      {"name": "Auréola Rachada",    "rarities": _R, "fx": {"maxhp": 10},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "topo", "art": "aureola"},
                     "req": "andar10"},
    "vela":         {"name": "Vela Amaldiçoada",   "rarities": _R, "fx": {"energy": 0.5, "trap": 2.0},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "topo", "art": "vela"},
                     "req": "mimico"},
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
        "items": [], "shield": 0, "pending": None,
        "gold": 0, "energy": 0.0, "kills": 0, "bosses": 0,
        "started": date.today().isoformat(), "dead": False,
    }


def _scale(fx: dict, rar: str) -> dict:
    """Multiplica os valores positivos pela raridade; negativos e trap ficam iguais."""
    m = RAR_MULT[rar]
    out = {}
    for k, v in fx.items():
        if k == "trap" or v <= 0:
            out[k] = v
        elif isinstance(v, int):
            out[k] = math.floor(v * m + 0.5)      # arredonda .5 para cima
        else:
            out[k] = v * m
    return out


def item_fx(key: str, rar: str) -> dict:
    return _scale(ITEMS[key]["fx"], rar)


def consume_fx(key: str, rar: str) -> dict:
    return _scale(ITEMS[key]["consume"], rar)


def migrate_run(run: dict) -> dict:
    """Save antigo (3 espaços) -> lista de itens comuns; chaves que sumiram são puladas."""
    items = run.get("items")
    if isinstance(items, dict):
        run["items"] = [{"key": items[s], "rar": "comum"} for s in ("mao", "escudo", "cabeca")
                        if items.get(s) in ITEMS]
    run.setdefault("shield", 0)
    run.setdefault("pending", None)
    return run


def stats(run: dict) -> dict:
    b = run["base"]
    st = {"maxhp": b["maxhp"], "atk": b["atk"], "def": b["def"], "dodge": b["dodge"],
          "gold": 0.0, "trap": 1.0, "energy": 0.0, "lifesteal": 0}
    for it in run["items"]:
        for k, v in item_fx(it["key"], it["rar"]).items():
            if k == "trap":
                st["trap"] *= v
            else:
                st[k] += v
    st["maxhp"] = max(5, st["maxhp"])
    st["atk"] = max(1, st["atk"])
    st["dodge"] = min(0.5, st["dodge"])
    st["energy"] = min(MAX_ENERGY_BONUS, st["energy"])
    st["trap"] = min(TRAP_LIMITS[1], max(TRAP_LIMITS[0], st["trap"]))
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


def _rarity_weights(f: int) -> list[float]:
    # ponto de partida; a Task 6 ajusta no simulador
    return [max(10, 70 - 4 * f), 25 + f, 4 + 1.5 * f, 0.5 + 0.5 * f]


def roll_offer(run: dict, meta: dict, rng: random.Random, best: bool = False) -> dict | None:
    """Sorteia raridade e item (um de cada por run). None quando não sobra item liberado."""
    taken = {i["key"] for i in run["items"]}
    if run.get("pending"):
        taken.add(run["pending"]["key"])
    pool = [k for k in unlocked_items(meta) if k not in taken]
    if not pool:
        return None
    lo = 1 if best else 0
    idx = max(lo, rng.choices(range(len(RARITIES)), _rarity_weights(run["floor"]))[0])
    # desce uma raridade por vez, depois sobe; abaixo do piso só em último caso
    order = list(range(idx, lo - 1, -1)) + list(range(idx + 1, len(RARITIES))) + list(range(lo - 1, -1, -1))
    for i in order:
        rar = RARITIES[i]
        cands = [k for k in pool if rar in ITEMS[k]["rarities"]]
        if cands:
            return {"key": rng.choice(cands), "rar": rar}
    return None


def auto_choice(run: dict, offer: dict) -> str:
    """Regra automática: consome se for cura e o HP estiver abaixo de 40%; senão pega."""
    if "heal" in ITEMS[offer["key"]]["consume"] and run["hp"] < 0.4 * stats(run)["maxhp"]:
        return "consumir"
    return "pegar"


def resolve_offer(run: dict, offer: dict, choice: str, ev: dict) -> None:
    """Aplica a escolha. As conquistas ficam com quem chama (enter_room / *_pending)."""
    item = {"key": offer["key"], "rar": offer["rar"]}
    if choice == "pegar":
        run["items"].append(item)
        hp_bonus = item_fx(item["key"], item["rar"]).get("maxhp", 0)
        if hp_bonus > 0:
            run["hp"] += hp_bonus
        ev["item"] = item
        stats(run)
        return
    cf = consume_fx(item["key"], item["rar"])
    if "heal" in cf:
        n = max(0, min(cf["heal"], stats(run)["maxhp"] - run["hp"]))
        run["hp"] += n
        ev["consumed"] = {**item, "heal": n}
    else:
        run["shield"] += cf["shield"]
        ev["consumed"] = {**item, "shield": cf["shield"]}


def choose_pending(run: dict, meta: dict, choice: str) -> dict:
    """Resolve a oferta pendente com a escolha do jogador ("pegar" ou "consumir")."""
    ev: dict = {"lines": []}
    offer, run["pending"] = run.get("pending"), None
    if offer:
        resolve_offer(run, offer, choice, ev)
        _check_achievements(run, meta, ev)
    return ev


def resolve_pending(run: dict, meta: dict) -> dict:
    """Resolve a oferta pendente pela regra automática."""
    if not run.get("pending"):
        return {"lines": []}
    return choose_pending(run, meta, auto_choice(run, run["pending"]))


def apply_damage(run: dict, d: int) -> int:
    """O escudo absorve primeiro; devolve o dano que chegou ao HP."""
    absorbed = min(run["shield"], d)
    run["shield"] -= absorbed
    run["hp"] -= d - absorbed
    return d - absorbed


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
        d = apply_damage(run, max(1, foe_atk - st["def"] + rng.randint(-1, 1)))
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
        "killer": killer, "items": [i["key"] for i in run["items"]],
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
    grant("colecionador", len(run["items"]) >= 10)
    if new:
        meta["achievements"].extend(new)
        ev["unlocks"] = new
    b = meta["best"]
    if (run["floor"], run["room"]) > (b["floor"], b["room"]):
        meta["best"] = {"floor": run["floor"], "room": run["room"]}


def enter_room(run: dict, meta: dict, rng: random.Random,
               stage_floors: list[int] | None = None, mode: str = "auto") -> dict:
    """Gasta energia, resolve a próxima sala e devolve o que aconteceu.

    mode "auto": a regra automática decide as ofertas na hora.
    mode "interativo": a oferta vai para run["pending"] e ev["pending"] (a GUI resolve).
    """
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

    def deliver(offer):
        if mode == "auto":
            resolve_offer(run, offer, auto_choice(run, offer), ev)
        else:
            run["pending"] = {**offer, "source": kind}
            ev["pending"] = offer

    def give(best=False):
        offer = roll_offer(run, meta, rng, best)
        if offer:
            deliver(offer)
        else:                                  # acabaram os itens: ouro do baú
            gold = round((5 + 2 * f) * (1 + st["gold"]))
            run["gold"] += gold
            ev["gold"] = ev.get("gold", 0) + gold

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
            give(best=True)
        elif kind == "mimic":
            gold += 5 + f
            give()
        run["gold"] += gold
        ev["gold"] = ev.get("gold", 0) + gold

    elif kind == "chest":
        ev.update(name="Baú", sprite="bau")
        if rng.random() < 0.75:
            give()
        else:
            gold = round((5 + 2 * f) * (1 + st["gold"]))
            run["gold"] += gold
            ev["gold"] = gold

    elif kind == "trap":
        ev.update(name="Armadilha", sprite="armadilha")
        if rng.random() < st["dodge"]:
            ev["dodged"] = True
        else:
            dmg = apply_damage(run, max(1, round((2 + 0.6 * f) * st["trap"])))
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
            offer = roll_offer(run, meta, rng, best=True)
            if offer:
                run["gold"] -= item_price
                ev["lines"].append(f"Pagou {item_price} ouro")
                deliver(offer)
            else:
                ev["lines"].append("A loja não tem nada novo...")
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
