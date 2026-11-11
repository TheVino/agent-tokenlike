# -*- coding: utf-8 -*-
"""
Regras da Masmorra de Tokens (sem interface: dá para testar e simular).

Tokens viram ENERGIA. Cada sala custa ROOM_COST de energia. A cada 5 salas
o herói desce uma escada; a cada 5 andares a última sala é um chefe.
Morreu em combate ou em armadilha -> lápide no cemitério e run nova.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import date

ROOM_COST = 100_000          # XP de tokens por sala
ROOMS_PER_FLOOR = 5
MAX_STORED_ROOMS = 20        # a "mochila" de energia guarda no máximo 20 salas
BOSS_EVERY = 5

# balanceamento (vida/ataque = base + por_andar * andar)
MON_HP = (4, 2.2)
MON_ATK = (1.5, 1.2)
# chefes: (valor no 1º chefe, por andar) = v + por_andar * (andar - BOSS_EVERY); crescem mais rápido que os itens
BOSS_HP = (55, 18)
BOSS_ATK = (7.5, 3.4)
REGEN_PER_ROOM = 2
FLOOR_BONUS_HP = 2           # HP máx ganho a cada andar
CHEST_ITEM_CHANCE = 1.0      # chance de o baú trazer item (senão, ouro)
SHOP_PRICE = (8, 2)          # preço do item na loja = base + por_andar * andar

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
RAR_MULT = {"comum": 1, "raro": 1.2, "epico": 1.4, "lendario": 1.6}
RAR_NAMES = {"comum": "Comum", "raro": "Raro", "epico": "Épico", "lendario": "Lendário"}
RAR_COLOR = {"comum": None, "raro": "#6fd6ff", "epico": "#b48cff", "lendario": "#ffd23f"}
CHOICE_WINDOW_S = 30         # janela de escolha do modo interativo (a GUI conta o tempo)
MAX_ENERGY_BONUS = 1.0       # soma de "energy" limitada a +100%
TRAP_LIMITS = (0.25, 3.0)    # piso e teto do multiplicador de armadilha somado
MAX_DODGE = 0.5              # teto da esquiva somada

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
    "carapaca":     {"name": "Carapaça Espinhosa", "rarities": _C, "fx": {"def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "espinhos", "color": "#8a94a8"}},
    "baba":         {"name": "Baba Pegajosa",      "rarities": _C, "fx": {"lifesteal": 1, "maxhp": 4},
                     "consume": {"heal": 8}, "look": {"type": "gotas", "color": "#4fbf5a"}},
    "aura":         {"name": "Aura Sombria",       "rarities": _R, "fx": {"dodge": 0.1, "atk": 1},
                     "consume": {"shield": 8}, "look": {"type": "contorno", "color": "#b48cff"},
                     "req": "andar5"},
    "veneno":       {"name": "Frasco Carmesim",    "rarities": _C, "fx": {"atk": 3, "maxhp": -2},
                     "consume": {"heal": 10}, "look": {"type": "tingir", "color": "#e2384d", "amount": 0.4}},
    "terceiro_olho": {"name": "Terceiro Olho",     "rarities": _R, "fx": {"dodge": 0.1, "trap": 0.5},
                     "consume": {"shield": 7},
                     "look": {"type": "adesivo", "art": "terceiro_olho", "at": [0.5, 0.3]},
                     "req": "chefe1"},
    "orbe":         {"name": "Orbe Vaga-lume",     "rarities": _C, "fx": {"gold": 0.3, "def": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "flutua", "art": "orbe"}},
    "coroa_cinzas": {"name": "Coroa de Cinzas",    "rarities": ["lendario"], "fx": {"atk": 2, "maxhp": 5},
                     "consume": {"heal": 15}, "look": {"type": "obj", "anchor": "topo", "art": "coroa_cinzas"},
                     "req": "andar10"},
}

# sprite, nome, mult. de vida, mult. de ataque, andar mínimo, mult. de velocidade
MONSTERS = [
    ("morcego", "Morcego", 0.8, 0.9, 1, 1.4),
    ("rato", "Rato", 1.0, 0.8, 1, 1.1),
    ("aranha", "Aranha", 0.9, 1.2, 2, 1.0),
    ("esqueleto", "Esqueleto", 1.3, 1.0, 3, 0.7),
    ("olho", "Olho Flutuante", 1.0, 1.4, 5, 0.9),
]
BOSS_NAMES = {"morcego": "Morcego Vampiro", "rato": "Rei Rato", "aranha": "Aranha Mãe",
              "esqueleto": "Lorde Esqueleto", "olho": "Olho Abissal"}

# combate: velocidade, crítico e elementos
MON_SPD = (8, 0.3)            # (base, por andar)
BOSS_SPD_BONUS = 1.2
MON_CRIT, BOSS_CRIT, FOE_CRITDMG = 0.03, 0.05, 1.5
PET_SPD, PET_CRIT, PET_CRITDMG = 10, 0.05, 1.5
MAX_CRIT = 0.6
MAX_ELEM_CHANCE = 0.6
ELEMENTOS = {"fogo": "queimar", "raio": "eletrizar", "veneno": "envenenar", "gelo": "congelar"}
BOSS_ELEMENT = {"morcego": "raio", "rato": "veneno", "aranha": "veneno", "esqueleto": "gelo", "olho": "fogo"}
BOSS_STATUS_CHANCE = 0.35
DOBRO_CRIT = 0.5              # bônus de crítico de quem tem o dobro da velocidade do alvo (e critdmg x2)
STATUS_NOME = {"queimar": "queimadura", "eletrizar": "eletricidade", "envenenar": "veneno", "congelar": "congelamento"}
QUEIMA = (2, 0.3)             # dano por turno: base + por andar
QUEIMA_TURNOS = 3
ELETRO_CHANCE, ELETRO_TURNOS = 0.3, 2
VENENO_TURNOS, VENENO_MAX_PILHAS = 4, 3
GELO_CHANCE, GELO_TURNOS = 0.6, 2
MAX_ROUNDS = 60


def make_foe(m: tuple, f: int, boss: bool = False, mult: float = 1.0) -> dict:
    """Monta o inimigo (monstro ou chefe) do andar f; mult escala HP e ATK antes de arredondar."""
    if boss:
        hp = BOSS_HP[0] + BOSS_HP[1] * (f - BOSS_EVERY)
        atk = BOSS_ATK[0] + BOSS_ATK[1] * (f - BOSS_EVERY)
    else:
        hp = (MON_HP[0] + MON_HP[1] * f) * m[2]
        atk = (MON_ATK[0] + MON_ATK[1] * f) * m[3]
    hp = max(1, round(hp * mult))
    return {"sprite": m[0], "name": BOSS_NAMES[m[0]] if boss else m[1], "boss": boss,
            "element": BOSS_ELEMENT[m[0]] if boss else None,
            "hp": hp, "hp_max": hp, "atk": max(1, round(atk * mult)),
            "spd": (MON_SPD[0] + MON_SPD[1] * f) * m[5] * (BOSS_SPD_BONUS if boss else 1),
            "crit": BOSS_CRIT if boss else MON_CRIT, "critdmg": FOE_CRITDMG, "status": {}}


def make_mimic(f: int) -> dict:
    hp = max(1, round((MON_HP[0] + MON_HP[1] * f) * 1.4))
    return {"sprite": "mimico", "name": "Mímico", "boss": False, "element": None,
            "hp": hp, "hp_max": hp, "atk": max(1, round((MON_ATK[0] + MON_ATK[1] * f) * 1.1)),
            "spd": MON_SPD[0] + MON_SPD[1] * f, "crit": MON_CRIT, "critdmg": FOE_CRITDMG, "status": {}}


ROOM_WEIGHTS = [("monster", 46), ("chest", 16), ("trap", 12), ("fountain", 11),
                ("shop", 8), ("altar", 7), ("horde", 12)]
# hordas: 2 a 4 inimigos mais fracos (HP e ATK x HORDE_MULT[n]); só a partir do andar HORDE_MIN_FLOOR
HORDE_MIN_FLOOR = 3
HORDE_MULT = {2: 0.75, 3: 0.6, 4: 0.5}
HORDE_GOLD_MULT = 1.25


def horde_max(f: int) -> int:
    """Tamanho máximo da horda no andar f."""
    return 2 if f < 5 else 3 if f < 8 else 4

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
                 "def": int(base_stats.get("def", 0)), "dodge": float(base_stats.get("dodge", 0)),
                 "spd": float(base_stats.get("spd", PET_SPD)), "crit": PET_CRIT, "critdmg": PET_CRITDMG},
        "items": [], "consumed": [], "shield": 0, "pending": None,
        "gold": 0, "energy": 0.0, "kills": 0, "bosses": 0,
        "started": date.today().isoformat(), "dead": False,
    }


def _scale(fx: dict, rar: str) -> dict:
    """Multiplica os valores positivos pela raridade; negativos e trap ficam iguais."""
    m = RAR_MULT[rar]
    out = {}
    for k, v in fx.items():
        if k in ("trap", "area") or v <= 0:
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
    """Save antigo (3 espaços) -> lista de itens comuns; itens e pendência com chaves que sumiram são descartados."""
    items = run.get("items")
    if isinstance(items, dict):
        run["items"] = [{"key": items[s], "rar": "comum"} for s in ("mao", "escudo", "cabeca")
                        if items.get(s) in ITEMS]
    else:
        run["items"] = [i for i in (items or []) if isinstance(i, dict) and i.get("key") in ITEMS]
    for i in run["items"]:
        i.setdefault("floor", None)
    run.setdefault("consumed", [])
    run.setdefault("shield", 0)
    b = run.setdefault("base", {})
    b.setdefault("spd", PET_SPD); b.setdefault("crit", PET_CRIT); b.setdefault("critdmg", PET_CRITDMG)
    if (run.get("pending") or {}).get("key") not in ITEMS:
        run["pending"] = None
    return run


def stats(run: dict) -> dict:
    b = run["base"]
    st = {"maxhp": b["maxhp"], "atk": b["atk"], "def": b["def"], "dodge": b["dodge"],
          "gold": 0.0, "trap": 1.0, "energy": 0.0, "lifesteal": 0,
          "spd": b.get("spd", PET_SPD), "crit": b.get("crit", PET_CRIT), "critdmg": b.get("critdmg", PET_CRITDMG),
          "area": False, "queimar": 0.0, "eletrizar": 0.0, "envenenar": 0.0, "congelar": 0.0}
    for it in run["items"]:
        for k, v in item_fx(it["key"], it["rar"]).items():
            if k == "trap":
                st["trap"] *= v
            elif k == "area":
                st["area"] = st["area"] or bool(v)
            else:
                st[k] += v
    st["maxhp"] = max(5, st["maxhp"])
    st["atk"] = max(1, st["atk"])
    st["dodge"] = min(MAX_DODGE, st["dodge"])
    st["energy"] = min(MAX_ENERGY_BONUS, st["energy"])
    st["spd"] = max(1, st["spd"])
    st["crit"] = min(MAX_CRIT, st["crit"])
    for el in ELEMENTOS.values():
        st[el] = min(MAX_ELEM_CHANCE, st[el])
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
    item = {"key": offer["key"], "rar": offer["rar"]}      # sem andar: é o que o evento (GUI) recebe
    if choice == "pegar":
        run["items"].append({**item, "floor": run["floor"]})
        hp_bonus = item_fx(item["key"], item["rar"]).get("maxhp", 0)
        if hp_bonus > 0:
            run["hp"] += hp_bonus
        ev["item"] = item
        stats(run)
        return
    run["consumed"].append({**item, "floor": run["floor"]})
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


def _aplicar_status(s: dict, nome: str) -> None:
    """Coloca o status em s. Queimadura renova; veneno ganha uma pilha (no teto, renova a mais velha)."""
    if nome == "veneno":
        v = s.setdefault("veneno", [])
        if len(v) < VENENO_MAX_PILHAS:
            v.append(0)
        else:
            v[v.index(max(v))] = 0
    else:
        s[nome] = {"queimadura": QUEIMA_TURNOS, "eletricidade": ELETRO_TURNOS, "congelamento": GELO_TURNOS}[nome]


def _dano_status(s: dict, f: int) -> list[tuple[str, int]]:
    """Tique do começo da rodada: [(nome, dano)] e já desconta a duração."""
    out = []
    if s.get("queimadura"):
        s["queimadura"] -= 1
        out.append(("queimadura", round(QUEIMA[0] + QUEIMA[1] * f)))
    if s.get("veneno"):
        v = [t + 1 for t in s["veneno"]]                # cada pilha dá 1, 2, 3, 4 de dano
        out.append(("veneno", sum(v)))
        s["veneno"] = [t for t in v if t < VENENO_TURNOS]
    return out


def combate(run: dict, st: dict, foes: list[dict], rng: random.Random, f: int):
    """Luta por rodadas. Devolve (venceu, passos, assassino, empate); muta run["hp"] e hp/status dos inimigos.

    Sem `area` o pet bate no inimigo vivo de menor HP; com `area`, um passo por alvo vivo.
    empate: a luta bateu no limite de MAX_ROUNDS (o pet sobrevive, mas a sala não dá prêmio).
    """
    passos = []
    pst: dict = {}                                       # status do pet (só durante a luta)

    def passo(who, target, dmg=0, crit=False, status=None, skip=False, dot=False, dodge=False):
        passos.append({"who": who, "target": target, "dmg": dmg, "crit": crit, "status": status,
                       "skip": skip, "dot": dot, "dodge": dodge})

    def vivos():
        return [i for i, x in enumerate(foes) if x["hp"] > 0]

    def perde_vez(s):
        perdeu = False
        if s.get("congelamento"):
            s["congelamento"] -= 1
            if rng.random() < GELO_CHANCE:
                perdeu, s["congelamento"] = True, 0
        if s.get("eletricidade"):
            s["eletricidade"] -= 1
            perdeu = rng.random() < ELETRO_CHANCE or perdeu
        return perdeu

    def critico(crit, critdmg, spd, spd_alvo):
        """(é crítico, multiplicador); o dobro da velocidade dá +DOBRO_CRIT e critdmg x2."""
        dobro = spd >= 2 * spd_alvo
        e_crit = rng.random() < crit + (DOBRO_CRIT if dobro else 0)
        return e_crit, (critdmg * (2 if dobro else 1) if e_crit else 1)

    for _ in range(MAX_ROUNDS):
        # 1. dano de status no começo da rodada (ignora o escudo)
        for nome, d in _dano_status(pst, f):
            run["hp"] -= d
            passo("pet", "pet", d, status=nome, dot=True)
            if run["hp"] <= 0:
                run["hp"] = 0
                return False, passos, nome.capitalize(), False
        for i in vivos():
            for nome, d in _dano_status(foes[i]["status"], f):
                foes[i]["hp"] -= d
                passo(i, i, d, status=nome, dot=True)
        if not vivos():
            return True, passos, "", False
        # 2. ordem por velocidade; empate: pet primeiro, depois a ordem da lista (sort estável)
        ordem = sorted([("pet", st["spd"])] + [(i, foes[i]["spd"]) for i in vivos()], key=lambda x: -x[1])
        for who, _spd in ordem:
            if who != "pet" and foes[who]["hp"] <= 0:
                continue
            if perde_vez(pst if who == "pet" else foes[who]["status"]):
                passo(who, who, skip=True)
                continue
            if who == "pet":
                vs = vivos()
                alvos = vs if st["area"] else [min(vs, key=lambda i: foes[i]["hp"])]
                for i in alvos:
                    x = foes[i]
                    e_crit, mult = critico(st["crit"], st["critdmg"], st["spd"], x["spd"])
                    d = round(max(1, st["atk"] + rng.randint(-1, 1)) * mult)
                    x["hp"] -= d
                    aplicado = None
                    if x["hp"] > 0:
                        for el, nome in STATUS_NOME.items():      # cada elemento rola separado
                            if st[el] and rng.random() < st[el]:
                                _aplicar_status(x["status"], nome)
                                aplicado = aplicado or nome
                    passo("pet", i, d, e_crit, aplicado)
                if not vivos():
                    return True, passos, "", False
            else:
                x = foes[who]
                if rng.random() < st["dodge"]:
                    passo(who, "pet", dodge=True)
                    continue
                e_crit, mult = critico(x["crit"], x["critdmg"], x["spd"], st["spd"])
                d = apply_damage(run, round(max(1, x["atk"] - st["def"] + rng.randint(-1, 1)) * mult))
                aplicado = None
                if x["boss"] and x.get("element") and rng.random() < BOSS_STATUS_CHANCE:
                    aplicado = STATUS_NOME[ELEMENTOS[x["element"]]]
                    _aplicar_status(pst, aplicado)
                passo(who, "pet", d, e_crit, aplicado)
                if run["hp"] <= 0:
                    run["hp"] = 0
                    return False, passos, x["name"], False
    return True, passos, "", True                        # limite de segurança: empate, sem prêmio


def die(run: dict, meta: dict, ev: dict, killer: str, kind: str = "monster") -> None:
    """kind: monster|horde|boss|mimic|trap|desistiu; morte por Queimadura/Veneno vira "status"."""
    if killer in ("Queimadura", "Veneno"):
        kind = "status"
    run["dead"] = True
    ev["died"] = True
    ev["killed_by"] = killer
    meta["runs"] += 1
    meta["graveyard"].append({
        "run": run["id"], "char": run["char"], "floor": run["floor"], "room": run["room"],
        "killer": killer, "kind": kind, "items": [i["key"] for i in run["items"]],
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
        pesos = [(k, w) for k, w in ROOM_WEIGHTS if k != "horde" or f >= HORDE_MIN_FLOOR]
        kind = rng.choices([k for k, _ in pesos], [w for _, w in pesos])[0]
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

    if kind in ("monster", "boss", "mimic", "horde"):
        pool = [m for m in MONSTERS if m[4] <= f]
        if kind == "mimic":
            foes = [make_mimic(f)]
        elif kind == "horde":                 # chefe nunca vem em horda
            n = rng.randint(2, horde_max(f))
            foes = [make_foe(rng.choice(pool), f, mult=HORDE_MULT[n]) for _ in range(n)]
        else:
            foes = [make_foe(rng.choice(pool), f, boss=(kind == "boss"))]
        ev["name"] = f"Horda ({len(foes)})" if kind == "horde" else foes[0]["name"]
        ev["foes"] = [{k: x[k] for k in ("sprite", "name", "boss", "element", "hp_max")} for x in foes]
        hp_before = run["hp"]
        won, ev["hits"], killer, empate = combate(run, st, foes, rng, f)
        ev["dmg"] = hp_before - run["hp"]
        if not won:
            die(run, meta, ev, killer, kind)
            return ev
        if empate:                            # passou da sala, mas sem ouro, kills, bônus de chefe ou item
            ev["empate"] = True
            _check_achievements(run, meta, ev)
            return ev
        ev["won"] = True
        run["kills"] += len(foes)

        def gold_monstro():
            return round((rng.randint(1, 3) + f // 2) * (1 + st["gold"]))
        gold = round(sum(gold_monstro() for _ in foes) * HORDE_GOLD_MULT) if kind == "horde" else gold_monstro()
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
        if rng.random() < CHEST_ITEM_CHANCE:
            give()
        else:                                  # só acontece se CHEST_ITEM_CHANCE < 1
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
                die(run, meta, ev, "Armadilha", "trap")
                return ev

    elif kind == "fountain":
        ev.update(name="Fonte", sprite="fonte")
        heal = max(1, round(st["maxhp"] * 0.35))
        heal = min(heal, st["maxhp"] - run["hp"])
        run["hp"] += heal
        ev["heal"] = heal

    elif kind == "shop":
        ev.update(name="Lojinha", sprite="loja")
        potion, item_price = 6 + f, SHOP_PRICE[0] + SHOP_PRICE[1] * f
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


# Suba quando mudar fórmula de combate/regra ou número escrito direto no código (o hash abaixo não vê isso).
REGRAS_REV = 3


def _balance_version() -> str:
    """Hash dos números de balanceamento (não do visual): identifica a versão das regras nos registros."""
    its = {k: {f: v.get(f) for f in ("fx", "consume", "rarities", "req")} for k, v in sorted(ITEMS.items())}
    mons = [(m[0],) + tuple(m[2:]) for m in MONSTERS]  # sem o nome de exibição
    blob = [REGRAS_REV, its, mons, ROOM_COST, ROOMS_PER_FLOOR, MAX_STORED_ROOMS, BOSS_EVERY, MON_HP, MON_ATK,
            BOSS_HP, BOSS_ATK, REGEN_PER_ROOM, FLOOR_BONUS_HP, ROOM_WEIGHTS, RAR_MULT,
            [_rarity_weights(f) for f in range(1, 41)], MAX_ENERGY_BONUS, TRAP_LIMITS, MAX_DODGE,
            CHEST_ITEM_CHANCE, SHOP_PRICE, MON_SPD, BOSS_SPD_BONUS, MON_CRIT, BOSS_CRIT, FOE_CRITDMG, PET_SPD,
            PET_CRIT, PET_CRITDMG, MAX_CRIT, MAX_ELEM_CHANCE, BOSS_ELEMENT, BOSS_STATUS_CHANCE, DOBRO_CRIT, QUEIMA,
            QUEIMA_TURNOS, ELETRO_CHANCE, ELETRO_TURNOS, VENENO_TURNOS, VENENO_MAX_PILHAS, GELO_CHANCE, GELO_TURNOS,
            MAX_ROUNDS, HORDE_MIN_FLOOR, HORDE_MULT, HORDE_GOLD_MULT]
    return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()[:8]


BALANCE_VERSION = _balance_version()


def run_record(run: dict, killer: str, gave_up: bool, mode: str, achievements: list,
               killer_kind: str = "") -> dict:
    """Linha de registro de uma run terminada (mesmo formato no jogo e no simulador)."""
    return {
        "run": run["id"], "char": run["char"], "floor": run["floor"], "room": run["room"],
        "killer": killer, "killer_kind": killer_kind, "gave_up": gave_up,
        "items": [dict(i) for i in run["items"]], "consumed": [dict(i) for i in run["consumed"]],
        "gold": run["gold"], "kills": run["kills"], "bosses": run["bosses"],
        "date": date.today().isoformat(), "mode": mode, "version": BALANCE_VERSION,
        "achievements": list(achievements),
    }
