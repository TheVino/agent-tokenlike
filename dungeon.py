# -*- coding: utf-8 -*-
"""
Token Dungeon rules (no interface: can be tested and simulated).

Tokens become ENERGY. Each room costs ROOM_COST energy. Every 5 rooms
the hero goes down a staircase; every 5 floors the last room is a boss.
Died in combat or in a trap -> tombstone in the graveyard and a new run.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import date

from i18n import t

ROOM_COST = 100_000          # token XP per room
ROOMS_PER_FLOOR = 5
MAX_STORED_ROOMS = 20        # the energy "backpack" holds at most 20 rooms
BOSS_EVERY = 5

# balance (health/attack = base + per_floor * floor)
MON_HP = (4, 2.2)
MON_ATK = (1.5, 1.2)
# bosses: (value at the 1st boss, per floor) = v + per_floor * (floor - BOSS_EVERY); they grow faster than items
BOSS_HP = (55, 18)
BOSS_ATK = (7.5, 3.1)
# extra boss ramp after floor BOSS_RAMP_FROM: HP and ATK x (1 + BOSS_RAMP * (floor - BOSS_RAMP_FROM));
# cuts the tail of runs with many stacked items without touching the 1st and 2nd bosses
BOSS_RAMP, BOSS_RAMP_FROM = 0.07, 10
REGEN_PER_ROOM = 2
FLOOR_BONUS_HP = 2           # max HP gained each floor
CHEST_ITEM_CHANCE = 1.0      # chance that a chest holds an item (otherwise, gold)
SHOP_PRICE = (8, 2)          # shop item price = base + per_floor * floor

ACHIEVEMENTS = {
    "floor5": "Reach floor 5",
    "boss1": "Defeat a boss",
    "mimic": "Defeat a mimic",
    "rich": "Gather 100 gold in a run",
    "collector": "Take 10 items in a run",
    "floor10": "Reach floor 10",
    "floor20": "Reach floor 20",
    "poison1": "Kill an enemy with poison",
    "elements3": "Take 3 elemental items in a run",
    "gold300": "Gather 300 gold in a run",
    "horde4": "Beat a horde of 4 enemies",
    "burn1": "Kill an enemy with a burn",
    "floor8full": "Reach floor 8 at full HP",
    "floor15": "Reach floor 15",
    "dodge10": "Dodge 10 hits in a run",
    "block10": "Block 10 hits in a run",
    "bosses3": "Beat 3 bosses in total",
    "consume10": "Consume 10 items in a run",
    "die10": "Die 10 times",
    "helpers3": "Take 3 helper items in a run",
    "no_consume10": "Reach floor 10 consuming nothing",
    "legendaries3": "Take 3 legendary items in a run",
    "synergy5": "Discover 5 synergies",
    "reactions_all": "Discover all 6 reactions",
    "synergies3run": "Activate 3 synergies in a run",
    "poison3": "Kill 3 enemies with poison in a run",
    "floor13": "Die on floor 13",
    "bosses3run": "Beat 3 bosses in a single run",
}

RARITIES = ("common", "rare", "epic", "legendary")
RAR_MULT = {"common": 1, "rare": 1.2, "epic": 1.4, "legendary": 1.6}
RAR_NAMES = {"common": "Common", "rare": "Rare", "epic": "Epic", "legendary": "Legendary"}
RAR_COLOR = {"common": None, "rare": "#6fd6ff", "epic": "#b48cff", "legendary": "#ffd23f"}
CHOICE_WINDOW_S = 30         # choice window in interactive mode (the GUI keeps the time)
MAX_ENERGY_BONUS = 1.0       # summed "energy" capped at +100%
TRAP_LIMITS = (0.25, 3.0)    # floor and cap of the summed trap multiplier
MAX_DODGE = 0.5              # cap of the summed dodge

_C = ["common", "rare", "epic"]
_R = ["rare", "epic", "legendary"]

# fx: atk, def, maxhp, dodge, gold (+% gold), trap (trap damage
#     multiplier), energy (+% energy => cheaper rooms), lifesteal (heal per win)
# consume: what happens if the hero consumes the item instead of taking it (heal or shield)
ITEMS = {
    "dagger":        {"name": "Rusty Dagger",  "rarities": _C, "fx": {"atk": 2}, "consume": {"heal": 6},
                     "look": {"type": "obj", "anchor": "right", "art": "dagger"}},
    "bone_sword":  {"name": "Bone Sword",     "rarities": _C, "fx": {"atk": 4}, "consume": {"heal": 8},
                     "look": {"type": "obj", "anchor": "right", "art": "bone_sword"}},
    "staff":       {"name": "Spectral Staff",   "rarities": _R, "fx": {"atk": 3, "lifesteal": 2},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "right", "art": "staff"},
                     "req": "floor5"},
    "scythe":        {"name": "Shadow Scythe",      "rarities": ["epic", "legendary"], "fx": {"atk": 8, "maxhp": -4},
                     "consume": {"heal": 12}, "look": {"type": "obj", "anchor": "right", "art": "scythe"},
                     "req": "boss1"},
    "pot_lid":        {"name": "Pot Lid",    "rarities": _C, "fx": {"def": 1}, "consume": {"shield": 5},
                     "look": {"type": "obj", "anchor": "left", "art": "pot_lid"}},
    "iron_shield": {"name": "Iron Shield",    "rarities": _C, "fx": {"def": 2}, "consume": {"shield": 7},
                     "look": {"type": "obj", "anchor": "left", "art": "iron_shield"}},
    "lantern":     {"name": "Pale Lantern",    "rarities": _C, "fx": {"def": 1, "trap": 0.5},
                     "consume": {"shield": 7}, "look": {"type": "obj", "anchor": "left", "art": "lantern"}},
    "grimoire":     {"name": "Forbidden Grimoire",  "rarities": _R, "fx": {"atk": 2, "def": 2},
                     "consume": {"shield": 9}, "look": {"type": "obj", "anchor": "left", "art": "grimoire"},
                     "req": "floor10"},
    "hat":       {"name": "Witch Hat",    "rarities": _C, "fx": {"gold": 0.5, "maxhp": 3}, "consume": {"heal": 6},
                     "look": {"type": "obj", "anchor": "top", "art": "hat"}},
    "beanie":        {"name": "Thief's Cap",    "rarities": _C, "fx": {"dodge": 0.15}, "consume": {"heal": 8},
                     "look": {"type": "obj", "anchor": "top", "art": "beanie"}},
    "horns":      {"name": "Demon Horns", "rarities": _R, "fx": {"atk": 3, "maxhp": -3},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "top", "art": "horns"},
                     "req": "boss1"},
    "halo":      {"name": "Cracked Halo",    "rarities": _R, "fx": {"maxhp": 10},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "top", "art": "halo"},
                     "req": "floor10"},
    "candle":         {"name": "Cursed Candle",   "rarities": _R, "fx": {"energy": 0.5, "trap": 2.0},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "top", "art": "candle"},
                     "req": "mimic"},
    "carapace":     {"name": "Spiky Carapace", "rarities": _C, "fx": {"def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "thorns", "color": "#8a94a8"}},
    "slobber":         {"name": "Sticky Drool",      "rarities": _C, "fx": {"lifesteal": 1, "maxhp": 4},
                     "consume": {"heal": 8}, "look": {"type": "drops", "color": "#4fbf5a"}},
    "aura":         {"name": "Dark Aura",       "rarities": _R, "fx": {"dodge": 0.1, "atk": 1},
                     "consume": {"shield": 8}, "look": {"type": "outline", "color": "#b48cff"},
                     "req": "floor5"},
    "poison":       {"name": "Crimson Flask",    "rarities": _C, "fx": {"atk": 3, "maxhp": -2},
                     "consume": {"heal": 10}, "look": {"type": "tint", "color": "#e2384d", "amount": 0.4}},
    "third_eye": {"name": "Third Eye",     "rarities": _R, "fx": {"dodge": 0.1, "trap": 0.5},
                     "consume": {"shield": 7},
                     "look": {"type": "sticker", "art": "third_eye", "at": [0.5, 0.3]},
                     "req": "boss1"},
    "orb":         {"name": "Firefly Orb",     "rarities": _C, "fx": {"gold": 0.3, "def": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "float", "art": "orb"}},
    "ash_crown": {"name": "Crown of Ashes",    "rarities": ["legendary"], "fx": {"atk": 2, "maxhp": 5},
                     "consume": {"heal": 15}, "look": {"type": "obj", "anchor": "top", "art": "ash_crown"},
                     "req": "floor10"},
    # batch A: elementals (fire, lightning, poison, ice); fx = chance per hit to apply the status
    "ember":        {"name": "Live Ember",         "rarities": _C, "fx": {"burn": 0.12, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "flames"}},
    "singed_fur": {"name": "Singed Fur", "rarities": _R, "fx": {"burn": 0.1, "atk": 2},
                     "consume": {"heal": 8}, "look": {"type": "flames", "color": "#ff6b3d"}, "req": "floor5"},
    "torch":        {"name": "Tallow Torch",      "rarities": _C, "fx": {"burn": 0.1, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "torch"}},
    "wisp":   {"name": "Red Wisp",   "rarities": ["rare", "epic"], "fx": {"burn": 0.15, "atk": 1},
                     "consume": {"shield": 7}, "look": {"type": "obj", "anchor": "float", "art": "wisp"}},
    "magma_heart": {"name": "Magma Heart",  "rarities": ["legendary"], "fx": {"burn": 0.2, "atk": 3},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "front", "art": "magma_heart"},
                     "req": "boss1"},
    "static_fur": {"name": "Static Fur",     "rarities": _C, "fx": {"shock": 0.08, "atk": 1},
                     "consume": {"shield": 5}, "look": {"type": "sparks"}},
    "electric_lemon": {"name": "Electric Lemon",   "rarities": _C, "fx": {"shock": 0.1, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "left", "art": "electric_lemon"}},
    "lightning_rod":   {"name": "Crooked Lightning Rod",   "rarities": _C, "fx": {"shock": 0.08, "def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "top", "art": "lightning_rod"}},
    "angry_cloud": {"name": "Angry Little Cloud", "rarities": ["rare", "epic"], "fx": {"shock": 0.12, "atk": 1},
                     "consume": {"shield": 7}, "look": {"type": "sparks", "color": "#9fd8ff"}, "req": "floor5"},
    "antenna":       {"name": "Storm Antenna", "rarities": _R, "fx": {"shock": 0.1, "atk": 1},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "top", "art": "antenna"},
                     "req": "floor10"},
    "moss":        {"name": "Toxic Moss",       "rarities": _C, "fx": {"poison": 0.12, "maxhp": 3, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "poison_drops"}},
    "frog_tooth":   {"name": "Mudfrog Tooth", "rarities": _C, "fx": {"poison": 0.12, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "frog_tooth"}},
    "mushroom":     {"name": "Suspicious Mushroom",  "rarities": _C, "fx": {"poison": 0.1, "lifesteal": 1, "atk": 1},
                     "consume": {"heal": 8}, "look": {"type": "obj", "anchor": "top", "art": "mushroom"}},
    "sludge":         {"name": "Boiling Sludge",      "rarities": ["rare", "epic"], "fx": {"poison": 0.15, "atk": 1},
                     "consume": {"heal": 9}, "look": {"type": "poison_drops", "color": "#7be36b"}, "req": "floor5"},
    "censer":   {"name": "Plague Censer", "rarities": ["legendary"], "fx": {"poison": 0.15, "area": True},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "float", "art": "censer"},
                     "req": "boss1"},
    "icy_breath":  {"name": "Frosty Breath",        "rarities": _C, "fx": {"freeze": 0.06, "def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "frost"}},
    "ice_shard":    {"name": "Ice Shard",  "rarities": _C, "fx": {"freeze": 0.06, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "ice_shard"}},
    "scarf":     {"name": "Snow Scarf",   "rarities": _C, "fx": {"freeze": 0.06, "def": 1, "maxhp": 3, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "front", "art": "scarf"}},
    "frost_bark":  {"name": "Frost Rind",     "rarities": _R, "fx": {"freeze": 0.08, "def": 1, "atk": 1},
                     "consume": {"shield": 9}, "look": {"type": "frost", "color": "#c8f4ff"}, "req": "floor10"},
    "eternal_flake": {"name": "Eternal Snowflake",       "rarities": ["epic", "legendary"], "fx": {"freeze": 0.12, "maxhp": 4, "atk": 1},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "float", "art": "eternal_flake"},
                     "req": "boss1"},
    # batch B: defense (block, thorns), regeneration (heal per room/floor) and blood (attack cost, fury)
    "buckler":      {"name": "Bark Buckler",   "rarities": _C, "fx": {"block": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "left", "art": "buckler"}},
    "turtle_shell": {"name": "Old Tortoise Shell", "rarities": _R, "fx": {"block": 1, "spd": -2},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "left", "art": "turtle_shell"},
                     "req": "floor5"},
    "riveted_gauntlet": {"name": "Riveted Gauntlet", "rarities": _C, "fx": {"block": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "right", "art": "riveted_gauntlet"}},
    "guard_bell":  {"name": "Warning Bell",  "rarities": _C, "fx": {"block": 1, "maxhp": -3},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "front", "art": "guard_bell"}},
    "living_wall": {"name": "Living Stone Wall", "rarities": ["legendary"], "fx": {"block": 1, "maxhp": 2},
                     "consume": {"shield": 14}, "look": {"type": "obj", "anchor": "left", "art": "living_wall"},
                     "req": "boss1"},
    "burr":       {"name": "Chestnut Husk",  "rarities": _C, "fx": {"thorns": 0.15, "def": 1},
                     "consume": {"shield": 6}, "look": {"type": "thorns", "color": "#b0763f"}},
    "grumpy_cactus":    {"name": "Grumpy Cactus", "rarities": _C, "fx": {"thorns": 0.2, "maxhp": 3},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "top", "art": "grumpy_cactus"}},
    "barbed_armor": {"name": "Barbed Doublet", "rarities": _R, "fx": {"thorns": 0.15, "def": 1, "atk": 1},
                     "consume": {"shield": 8}, "look": {"type": "thorns", "color": "#c99a00"},
                     "req": "floor5"},
    "fang_necklace": {"name": "Fang Necklace",    "rarities": _C, "fx": {"thorns": 0.1, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "front", "art": "fang_necklace"}},
    "cracked_mirror": {"name": "Cracked Mirror", "rarities": ["legendary"], "fx": {"thorns": 0.2, "dodge": 0.05, "atk": 1},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "float", "art": "cracked_mirror"},
                     "req": "boss1"},
    "little_tea":     {"name": "Lukewarm Teapot",         "rarities": _C, "fx": {"heal_room": 1, "maxhp": 3},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "left", "art": "little_tea"}},
    "stubborn_root": {"name": "Stubborn Root",       "rarities": _C, "fx": {"heal_floor": 8, "maxhp": 3},
                     "consume": {"heal": 8}, "look": {"type": "obj", "anchor": "top", "art": "stubborn_root"}},
    "hearth_lamp": {"name": "Pocket Hearth", "rarities": _C, "fx": {"heal_floor": 5, "def": 1},
                     "consume": {"heal": 8}, "look": {"type": "obj", "anchor": "front", "art": "hearth_lamp"}},
    "pocket_spring":  {"name": "Bottled Spring Drop", "rarities": ["rare", "epic"], "fx": {"heal_room": 2, "maxhp": 5},
                     "consume": {"heal": 12}, "look": {"type": "obj", "anchor": "float", "art": "pocket_spring"},
                     "req": "floor5"},
    "ancient_sap": {"name": "Ancestral Sap",    "rarities": ["epic", "legendary"], "fx": {"heal_room": 1, "heal_floor": 8, "maxhp": 4},
                     "consume": {"heal": 14}, "look": {"type": "tint", "color": "#e0a030", "amount": 0.3},
                     "req": "floor10"},
    "bleeding_dagger": {"name": "Thirsty Blade",    "rarities": _C, "fx": {"attack_cost": 1, "atk": 3},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "bleeding_dagger"}},
    "stitched_heart": {"name": "Patched Heart", "rarities": _C, "fx": {"fury": 1, "maxhp": 2},
                     "consume": {"heal": 9}, "look": {"type": "sticker", "art": "stitched_heart", "at": [0.5, 0.6]}},
    "fury_mask": {"name": "Gnashing Mask",  "rarities": _R, "fx": {"fury": 1, "attack_cost": 1, "atk": 2},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "front", "art": "fury_mask"},
                     "req": "boss1"},
    "ruby_chalice": {"name": "Ruby Chalice",       "rarities": ["rare", "epic"], "fx": {"attack_cost": 1, "atk": 2, "lifesteal": 3},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "float", "art": "ruby_chalice"},
                     "req": "floor5"},
    "crimson_pact": {"name": "Seal of the Red Drop", "rarities": ["epic", "legendary"], "fx": {"attack_cost": 2, "fury": 1, "atk": 2},
                     "consume": {"heal": 12}, "look": {"type": "obj", "anchor": "float", "art": "crimson_pact"},
                     "req": "boss1"},
    # batch C: blows (double), area, helpers (always a floating obj) and crit
    "swift_glove": {"name": "Nimble Glove", "rarities": _C, "fx": {"double": 0.15, "crit": 0.05},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "swift_glove"}},
    "twin_stinger": {"name": "Twin Stinger",       "rarities": _C, "fx": {"double": 0.1, "poison": 0.1, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "twin_stinger"}},
    "pigtail":      {"name": "Snapping Tail",  "rarities": _C, "fx": {"double": 0.1, "dodge": 0.08},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "left", "art": "pigtail"}},
    "echo_bracelet": {"name": "Echo Bracelet",    "rarities": ["rare", "epic"], "fx": {"double": 0.12, "crit": 0.05, "maxhp": 3},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "front", "art": "echo_bracelet"},
                     "req": "floor5"},
    "twin_claws": {"name": "Twin Moon Claws", "rarities": ["legendary"], "fx": {"double": 0.15, "crit": 0.1, "atk": 3},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "right", "art": "twin_claws"},
                     "req": "boss1"},
    "blade_top": {"name": "Blade Top",    "rarities": _C, "fx": {"area": True, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "front", "art": "blade_top"}},
    "bent_chain": {"name": "Crooked Link Chain", "rarities": _C, "fx": {"area": True, "def": 1, "maxhp": 3},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "left", "art": "bent_chain"}},
    "bottled_howl": {"name": "Bottled Howl",   "rarities": _C, "fx": {"area": True, "maxhp": 5},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "top", "art": "bottled_howl"}},
    "feather_fan":  {"name": "Black Feather Fan", "rarities": _R, "fx": {"area": True, "dodge": 0.08},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "left", "art": "feather_fan"},
                     "req": "floor5"},
    "whirlwind":   {"name": "Pocket Whirlwind", "rarities": ["rare", "epic"], "fx": {"area": True, "dodge": 0.05, "def": 1},
                     "consume": {"heal": 9}, "look": {"type": "tint", "color": "#9fd8ff", "amount": 0.25},
                     "req": "floor5"},
    "beetle":   {"name": "Guard Beetle", "rarities": _C, "fx": {"helper": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "float", "art": "beetle"}},
    "little_bat":  {"name": "Cloth Bat", "rarities": _C, "fx": {"helper": 1, "maxhp": 5},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "float", "art": "little_bat"}},
    "little_skull":   {"name": "Hopping Skull", "rarities": _C, "fx": {"helper": 3, "maxhp": -3},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "float", "art": "little_skull"}},
    "puppet":     {"name": "Sock Puppet",   "rarities": ["rare", "epic"], "fx": {"helper": 2, "def": 1},
                     "consume": {"shield": 9}, "look": {"type": "obj", "anchor": "float", "art": "puppet"},
                     "req": "floor5"},
    "grey_crow":  {"name": "Ash Crow",     "rarities": ["legendary"], "fx": {"helper": 3, "maxhp": 4},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "float", "art": "grey_crow"},
                     "req": "boss1"},
    "monocle":     {"name": "Cracked Monocle",  "rarities": _C, "fx": {"crit": 0.1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "sticker", "art": "monocle", "at": [0.3, 0.4]}},
    "whetstone": {"name": "Whetstone",    "rarities": _C, "fx": {"critdmg": 0.25, "atk": 1, "maxhp": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "left", "art": "whetstone"}},
    "wilted_clover": {"name": "Wilted Clover",       "rarities": _C, "fx": {"crit": 0.15, "atk": 1, "maxhp": 3},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "top", "art": "wilted_clover"}},
    "wolf_fang":   {"name": "Shadow Wolf Fang", "rarities": _R, "fx": {"crit": 0.1, "critdmg": 0.15, "atk": 1},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "right", "art": "wolf_fang"},
                     "req": "floor5"},
    "cat_eye":    {"name": "Onyx Cat's Eye",  "rarities": ["epic", "legendary"], "fx": {"crit": 0.12, "dodge": 0.08},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "top", "art": "cat_eye"},
                     "req": "boss1"},
    # batch D: growth (grow = kills per +1 ATK), luck (rarity), gold and shop discount
    "milk_tooth":  {"name": "Sharp Baby Tooth", "rarities": _C, "fx": {"grow": 8, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "milk_tooth"}},
    "cocoon":       {"name": "Restless Cocoon",    "rarities": _C, "fx": {"grow": 10, "maxhp": 6, "def": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "left", "art": "cocoon"}},
    "trophy_collar": {"name": "Trophy Collar", "rarities": _C, "fx": {"grow": 9, "def": 1, "atk": 1},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "front", "art": "trophy_collar"}},
    "hungry_seed": {"name": "Hungry Seed", "rarities": ["rare", "epic"], "fx": {"grow": 8, "maxhp": 4, "atk": 1},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "top", "art": "hungry_seed"},
                     "req": "floor5"},
    "ringed_horn": {"name": "Ringed Horn",    "rarities": ["legendary"], "fx": {"grow": 5, "atk": 3},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "top", "art": "ringed_horn"},
                     "req": "boss1"},
    "hunter_buckle": {"name": "Hunter's Buckle", "rarities": ["rare", "epic"], "fx": {"grow": 8, "crit": 0.05, "atk": 1},
                     "consume": {"shield": 9}, "look": {"type": "outline", "color": "#c99a00"}, "req": "floor10"},
    "bone_grinder": {"name": "Bone Grinder",    "rarities": _R, "fx": {"grow": 6, "atk": 2, "maxhp": -2},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "right", "art": "bone_grinder"},
                     "req": "boss1"},
    "bone_die":    {"name": "Bone Die",       "rarities": _C, "fx": {"luck": 0.3, "crit": 0.05, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "right", "art": "bone_die"}},
    "crown_coin": {"name": "Two-Crowned Coin", "rarities": _C, "fx": {"luck": 0.25, "gold": 0.15, "atk": 1, "maxhp": 3},
                     "consume": {"shield": 5}, "look": {"type": "obj", "anchor": "left", "art": "crown_coin"}},
    "horseshoe":    {"name": "Rusty Horseshoe", "rarities": _C, "fx": {"luck": 0.25, "def": 2},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "front", "art": "horseshoe"}},
    "scribbled_map": {"name": "Scribbled Map",   "rarities": _C, "fx": {"luck": 0.2, "energy": 0.2, "maxhp": 5},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "left", "art": "scribbled_map"}},
    "thread_talisman": {"name": "Three-Thread Talisman", "rarities": _C, "fx": {"luck": 0.2, "heal_floor": 4, "maxhp": 3},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "top", "art": "thread_talisman"}},
    "shooting_star": {"name": "Shooting Star Shard", "rarities": ["rare", "epic"], "fx": {"luck": 0.35, "maxhp": 5},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "float", "art": "shooting_star"},
                     "req": "floor5"},
    "cat_whiskers":  {"name": "Black Cat Whisker", "rarities": ["legendary"], "fx": {"luck": 0.5, "dodge": 0.1},
                     "consume": {"shield": 12}, "look": {"type": "sticker", "art": "cat_whiskers", "at": [0.5, 0.65]},
                     "req": "boss1"},
    "frog_pouch":   {"name": "Frogskin Pouch", "rarities": _C, "fx": {"gold": 0.3, "discount": 0.1, "def": 1, "maxhp": 3},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "left", "art": "frog_pouch"}},
    "coupon":        {"name": "Bargain Ticket", "rarities": _C, "fx": {"discount": 0.2, "maxhp": 5},
                     "consume": {"shield": 5}, "look": {"type": "sticker", "art": "coupon", "at": [0.7, 0.5]}},
    "scale":      {"name": "Crooked Scales",      "rarities": _C, "fx": {"discount": 0.15, "def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "right", "art": "scale"}},
    "gold_tooth":   {"name": "Gold Tooth",      "rarities": _R, "fx": {"gold": 0.4, "atk": 2},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "front", "art": "gold_tooth"},
                     "req": "floor5"},
    "piggy_bank":     {"name": "Coin Jug",  "rarities": ["legendary"], "fx": {"gold": 0.5, "discount": 0.2, "maxhp": 8},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "float", "art": "piggy_bank"},
                     "req": "rich"},
    "leech":  {"name": "Tame Leech",  "rarities": _C, "fx": {"lifesteal": 2, "maxhp": 4, "atk": 1},
                     "consume": {"heal": 7}, "look": {"type": "sticker", "art": "leech", "at": [0.25, 0.7]}},
}


# item families (first fx field found in this order; none: "Basic"); sets count items by this single family
FAMILIES = (("Elemental", ("burn", "shock", "poison", "freeze")), ("Helper", ("helper",)),
            ("Growth", ("grow",)), ("Area", ("area",)), ("Blood", ("attack_cost", "fury")),
            ("Strikes", ("crit", "critdmg", "double")), ("Defense", ("block", "thorns", "dodge")),
            ("Regeneration", ("heal_room", "heal_floor", "lifesteal")), ("Luck & gold", ("luck", "gold", "discount")))


def item_family(key: str) -> str:
    fx = ITEMS[key]["fx"]
    return next((name for name, fields in FAMILIES if any(fx.get(c) for c in fields)), "Basic")


# Synergies: kind set (2 / 4 items of a family), pair (two named items), reaction (added later).
# fx of sets and pairs is summed in stats() with no rarity scaling, like the hero trait.
# family -> (key slug, [(name, fx) for 2 items, (name, fx) for 4 items])
_SETS = {
    "Elemental": ("elemental", ("Elemental Whispers", {"elem_boost": 0.02}), ("Lingering Elements", {"status_turns": 1})),
    "Defense": ("defense", ("Sturdy Habit", {"thorns": 0.05}), ("Thorny Fortress", {"thorns": 0.1})),
    "Regeneration": ("regeneration", ("Slow Mending", {"heal_floor": 2}), ("Living Warmth", {"heal_room": 1})),
    "Blood": ("blood", ("Thrifty Pain", {"attack_cost": -1}), ("Cornered Rage", {"fury": 1})),
    "Strikes": ("strikes", ("Steady Hand", {"crit": 0.02}), ("Rhythm of Blows", {"double": 0.05})),
    "Area": ("area", ("Wide Stance", {"atk": 1}), ("Sweeping Might", {"atk": 1, "critdmg": 0.25})),
    "Helper": ("helper", ("Small Company", {"helper": 1}), ("Loyal Crowd", {"helper": 2})),
    "Growth": ("growth", ("Sprouting", {"maxhp": 4}), ("Full Bloom", {"atk": 2})),
    "Luck & gold": ("luck", ("Pocket Charm", {"luck": 0.05}), ("Merchant's Grin", {"gold": 0.25, "discount": 0.1})),
}
SYNERGIES = {
    f"{slug}{n}": {"name": name, "kind": "set", "req": {"family": fam, "n": n}, "fx": fx,
                   "secret": False, "hint": f"Have {n} {fam} items"}
    for fam, (slug, *steps) in _SETS.items() for n, (name, fx) in zip((2, 4), steps)
}
_PAIRS = (
    ("hearthfire", "Hearthfire", "torch", "hearth_lamp", {"heal_room": 1}, False),
    ("winter_carapace", "Winter Carapace", "frost_bark", "turtle_shell", {"thorns": 0.05}, False),
    ("night_prowler", "Night Prowler", "cat_eye", "cat_whiskers", {"dodge": 0.05}, True),
    ("pack_instinct", "Pack Instinct", "beetle", "ringed_horn", {"helper": 1}, False),
    ("blood_debt", "Blood Debt", "ruby_chalice", "leech", {"lifesteal": 1}, True),
    ("loaded_dice", "Loaded Dice", "crown_coin", "bone_die", {"crit": 0.03}, False),
    ("miasma", "Miasma", "censer", "whirlwind", {"poison": 0.04}, False),
    ("shattered_gaze", "Shattered Gaze", "cracked_mirror", "monocle", {"atk": 1}, True),
)
for _k, _name, _a, _b, _fx, _sec in _PAIRS:
    SYNERGIES[_k] = {"name": _name, "kind": "pair", "req": {"items": [_a, _b]}, "fx": _fx, "secret": _sec,
                     "hint": f"Have {ITEMS[_a]['name']} and {ITEMS[_b]['name']}"}

# Reactions: the pet applies a status to an enemy that already has another one (effects live in combat()).
for _k, _name, _a, _b, _hint in (
        ("shatter", "Shatter", "burn", "freeze", "Burn and freeze the same enemy"),
        ("toxic_fumes", "Toxic Fumes", "burn", "poison", "Burn and poison the same enemy"),
        ("overload", "Overload", "burn", "shock", "Burn and shock the same enemy"),
        ("conductor", "Conductor", "shock", "freeze", "Shock and freeze the same enemy"),
        ("jolt_venom", "Jolt Venom", "shock", "poison", "Shock and poison the same enemy"),
        ("frostbite", "Frostbite", "poison", "freeze", "Poison and freeze the same enemy")):
    SYNERGIES[_k] = {"name": _name, "kind": "reaction", "req": {"status": [_a, _b]}, "fx": {}, "secret": False,
                     "hint": _hint}

# sprite, name, health mult., attack mult., min floor, speed mult.
MONSTERS = [
    ("bat", "Bat", 0.8, 0.9, 1, 1.4),
    ("rat", "Rat", 1.0, 0.8, 1, 1.1),
    ("spider", "Spider", 0.9, 1.2, 2, 1.0),
    ("skeleton", "Skeleton", 1.3, 1.0, 3, 0.6),
    ("eye", "Floating Eye", 1.0, 1.4, 5, 0.9),
]
BOSS_NAMES = {"bat": "Vampire Bat", "rat": "Rat King", "spider": "Mother Spider",
              "skeleton": "Skeleton Lord", "eye": "Abyssal Eye"}

# combat: speed, crit and elements
MON_SPD = (6, 0.1)            # (base, per floor)
BOSS_SPD_BONUS = 1.1
MON_CRIT, BOSS_CRIT, FOE_CRITDMG = 0.02, 0.03, 1.5
PET_SPD, PET_CRIT, PET_CRITDMG = 10, 0.10, 1.5
MAX_CRIT = 0.35             # 0.6 made long runs endless with batch C (crit x double)
MAX_ELEM_CHANCE = 0.3
MAX_BLOCK, MAX_THORNS = 2, 0.5   # block 3 made bosses harmless (batch B)
MAX_LUCK, MAX_DISCOUNT = 1.0, 0.6   # caps for luck (rarity) and shop discount
MAX_DOUBLE = 0.25             # cap of the summed double-hit chance (0.5 stretched the tail too much)
ELEMENTS = {"fire": "burn", "lightning": "shock", "poison": "poison", "ice": "freeze"}
BOSS_ELEMENT = {"bat": "lightning", "rat": "poison", "spider": "poison", "skeleton": "ice", "eye": "fire"}
BOSS_STATUS_CHANCE = 0.15
DOUBLE_CRIT = 0.5              # crit bonus for whoever has twice the target's speed (and critdmg x2)
STATUS_NAME = {"burn": "burn", "shock": "shock", "poison": "poison", "freeze": "freeze"}
BURN = (2, 0.3)             # damage per turn: base + per floor
BURN_TURNS = 3
SHOCK_CHANCE, SHOCK_TURNS = 0.3, 2
POISON_TURNS, POISON_MAX_STACKS = 4, 2
FREEZE_CHANCE, FREEZE_TURNS = 0.6, 2
MAX_ROUNDS = 60


def make_foe(m: tuple, f: int, boss: bool = False, mult: float = 1.0) -> dict:
    """Builds the enemy (monster or boss) for floor f; mult scales HP and ATK before rounding."""
    if boss:
        hp = BOSS_HP[0] + BOSS_HP[1] * (f - BOSS_EVERY)
        atk = BOSS_ATK[0] + BOSS_ATK[1] * (f - BOSS_EVERY)
        ramp = 1 + BOSS_RAMP * max(0, f - BOSS_RAMP_FROM)
        hp, atk = hp * ramp, atk * ramp
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
    return {"sprite": "mimic", "name": "Mimic", "boss": False, "element": None,
            "hp": hp, "hp_max": hp, "atk": max(1, round((MON_ATK[0] + MON_ATK[1] * f) * 1.1)),
            "spd": MON_SPD[0] + MON_SPD[1] * f, "crit": MON_CRIT, "critdmg": FOE_CRITDMG, "status": {}}


ROOM_WEIGHTS = [("monster", 46), ("chest", 16), ("trap", 12), ("fountain", 11),
                ("shop", 8), ("altar", 7), ("horde", 9)]
# hordes: 2 to 4 weaker enemies (HP and ATK x HORDE_MULT[n]); only from floor HORDE_MIN_FLOOR on
HORDE_MIN_FLOOR = 3
HORDE_MULT = {2: 0.75, 3: 0.6, 4: 0.5}
HORDE_GOLD_MULT = 1.25


def horde_max(f: int) -> int:
    """Max horde size on floor f."""
    return 2 if f < 5 else 3 if f < 8 else 4

DEFAULT_STAGE_FLOORS = [1, 3, 8, 15, 25, 40]


def fx_text(fx: dict) -> str:
    """Effects text in the current language (i18n.t); the rules do not depend on it."""
    parts = []
    for k, label in (("atk", "ATK"), ("def", "DEF"), ("maxhp", "HP")):
        if fx.get(k):
            parts.append(f"{fx[k]:+d} {label}")
    if fx.get("dodge"):
        parts.append(t("{v}% dodge", v=int(fx['dodge'] * 100)))
    if fx.get("gold"):
        parts.append(t("+{v}% gold", v=int(fx['gold'] * 100)))
    if fx.get("energy"):
        parts.append(t("+{v}% energy", v=int(fx['energy'] * 100)))
    if fx.get("lifesteal"):
        parts.append(t("+{v} HP per win", v=fx['lifesteal']))
    if fx.get("trap"):
        parts.append(t("traps x{v}", v=f"{fx['trap']:g}"))
    if fx.get("spd"):
        parts.append(t("{v} speed", v=f"{fx['spd']:+g}"))
    if fx.get("crit"):
        parts.append(t("{v}% crit", v=f"{fx['crit'] * 100:+.0f}"))
    if fx.get("critdmg"):
        parts.append(t("{v}x crit damage", v=f"{fx['critdmg']:+g}"))
    if fx.get("area"):
        parts.append(t("area attack"))
    for el, name in STATUS_NAME.items():
        if fx.get(el):
            parts.append(f"{round(fx[el] * 100)}% {t(name)}")
    if fx.get("block"):
        parts.append(t("blocks {v} hit" if fx["block"] == 1 else "blocks {v} hits", v=fx['block']))
    if fx.get("thorns"):
        parts.append(t("returns {v}% of damage", v=round(fx['thorns'] * 100)))
    if fx.get("heal_room"):
        parts.append(t("+{v} HP per room", v=fx['heal_room']))
    if fx.get("heal_floor"):
        parts.append(t("+{v} HP per floor", v=fx['heal_floor']))
    if fx.get("attack_cost"):
        parts.append(t("-{v} HP per attack", v=fx['attack_cost']))
    if fx.get("fury"):
        parts.append(t("fury +{v} ATK/10% HP lost", v=f"{fx['fury']:g}"))
    if fx.get("double"):
        parts.append(t("{v}% double hit", v=round(fx['double'] * 100)))
    if fx.get("helper"):
        parts.append(t("helper {v} damage", v=f"{fx['helper']:g}"))
    if fx.get("grow"):
        parts.append(t("+1 ATK every {v} kills", v=fx['grow']))
    if fx.get("luck"):
        parts.append(t("+{v}% luck", v=round(fx['luck'] * 100)))
    if fx.get("discount"):
        parts.append(t("-{v}% shop price", v=round(fx['discount'] * 100)))
    if fx.get("elem_boost"):
        parts.append(t("+{v}% chance to each element", v=round(fx['elem_boost'] * 100)))
    if fx.get("status_turns"):
        parts.append(t("statuses last +{v} turn", v=fx['status_turns']))
    return ", ".join(parts)


def new_meta() -> dict:
    return {"achievements": [], "graveyard": [], "runs": 0,
            "best": {"floor": 0, "room": 0}, "next_char": "slime", "bosses": 0,
            "synergies": {}}


COUNTERS_ZERO = {"dodges": 0, "blocks": 0, "poison_kills": 0, "burn_kills": 0, "horde4": 0}


def new_run(char_key: str, base_stats: dict, run_id: int, trait: dict | None = None) -> dict:
    hp = int(base_stats.get("hp", 20))
    return {
        "id": run_id, "char": char_key, "floor": 1, "room": 0, "stage": 0,
        "hp": hp,
        "base": {"maxhp": hp, "atk": int(base_stats.get("atk", 3)),
                 "def": int(base_stats.get("def", 0)), "dodge": float(base_stats.get("dodge", 0)),
                 "spd": float(base_stats.get("spd", PET_SPD)),
                 # crit/critdmg only if the hero defines them; without them, stats() uses the current PET_CRIT/PET_CRITDMG
                 **{k: float(base_stats[k]) for k in ("crit", "critdmg") if k in base_stats}},
        "trait": dict(trait or {}),
        "counters": dict(COUNTERS_ZERO),
        "items": [], "consumed": [], "shield": 0, "pending": None, "synergies": [],
        "temp": [], "rooms": {},
        "gold": 0, "energy": 0.0, "kills": 0, "bosses": 0,
        "started": date.today().isoformat(), "dead": False,
    }


def _scale(fx: dict, rar: str) -> dict:
    """Multiplies the positive values by the rarity; negatives, trap, area and attack_cost stay the same."""
    m = RAR_MULT[rar]
    out = {}
    for k, v in fx.items():
        if k in ("trap", "area", "attack_cost") or v <= 0:
            out[k] = v
        elif k == "grow":                          # fewer kills per point = better: scales down, floor of 3
            out[k] = max(3, math.ceil(v / m))
        elif isinstance(v, int):
            out[k] = math.floor(v * m + 0.5)      # round .5 up
        else:
            out[k] = v * m
    return out


def item_fx(key: str, rar: str) -> dict:
    return _scale(ITEMS[key]["fx"], rar)


def consume_fx(key: str, rar: str) -> dict:
    return _scale(ITEMS[key]["consume"], rar)


def migrate_run(run: dict) -> dict:
    """Old save (3 slots) -> list of common items; items and pending offers with keys that no longer exist are dropped."""
    items = run.get("items")
    if isinstance(items, dict):
        run["items"] = [{"key": items[s], "rar": "common"} for s in ("mao", "shield", "cabeca")
                        if items.get(s) in ITEMS]
    else:
        run["items"] = [i for i in (items or []) if isinstance(i, dict) and i.get("key") in ITEMS]
    for i in run["items"]:
        i.setdefault("floor", None)
        i.setdefault("kills0", 0)
    run.setdefault("consumed", [])
    run.setdefault("shield", 0)
    run.setdefault("synergies", [])
    run.setdefault("trait", {})
    cont = run.setdefault("counters", {})
    for k, v in COUNTERS_ZERO.items():
        cont.setdefault(k, v)
    b = run.setdefault("base", {})
    b.setdefault("spd", PET_SPD)
    # old saves froze the pet defaults (0.10 and 1.5) in the base: without them, the current constants apply
    if b.get("crit") == 0.10:
        del b["crit"]
    if b.get("critdmg") == 1.5:
        del b["critdmg"]
    run.setdefault("temp", [])
    run.setdefault("rooms", {})
    p = run.get("pending")
    if isinstance(p, dict):
        p.setdefault("kind", "offer")              # saves from before typed pendings
    if not isinstance(p, dict) or p["kind"] not in CHOICES or not CHOICES[p["kind"]][2](p):
        run["pending"] = None
    return run


def active_synergies(run: dict) -> list[str]:
    """Keys of the sets and pairs whose condition holds now, in SYNERGIES order (pure)."""
    keys = [i["key"] for i in run["items"]]
    count = {}
    for k in keys:
        fam = item_family(k)
        count[fam] = count.get(fam, 0) + 1
    return [k for k, s in SYNERGIES.items()
            if (s["kind"] == "set" and count.get(s["req"]["family"], 0) >= s["req"]["n"])
            or (s["kind"] == "pair" and all(i in keys for i in s["req"]["items"]))]


def note_synergies(run: dict, meta: dict, ev: dict, extra=()) -> None:
    """Records the synergies active now (+ `extra`, e.g. reactions seen in combat) in the run and in the meta;
    new ones for this run go to ev["synergies"] and ev["lines"]."""
    for k in [*active_synergies(run), *extra]:
        if k in run["synergies"]:
            continue
        run["synergies"].append(k)
        seen = meta.setdefault("synergies", {})
        new = k not in seen
        if new:
            seen[k] = {"runs": 0, "first_run": run["id"]}
        seen[k]["runs"] += 1
        ev.setdefault("synergies", []).append({"key": k, "new": new})
        ev.setdefault("lines", []).append(f"{'New synergy' if new else 'Synergy'}: {SYNERGIES[k]['name']}!")


def stats(run: dict) -> dict:
    b = run["base"]
    st = {"maxhp": b["maxhp"], "atk": b["atk"], "def": b["def"], "dodge": b["dodge"],
          "gold": 0.0, "trap": 1.0, "energy": 0.0, "lifesteal": 0,
          "spd": b.get("spd", PET_SPD), "crit": b.get("crit", PET_CRIT), "critdmg": b.get("critdmg", PET_CRITDMG),
          "area": False, "burn": 0.0, "shock": 0.0, "poison": 0.0, "freeze": 0.0,
          "block": 0, "thorns": 0.0, "heal_room": 0, "heal_floor": 0, "attack_cost": 0, "fury": 0,
          "double": 0.0, "helper": 0, "luck": 0.0, "discount": 0.0, "status_turns": 0}
    # the hero trait and the active synergies add up like an item, but without rarity scaling
    boost = 0.0
    for kills0, fx in ([(0, run.get("trait", {}))] + [(0, t["fx"]) for t in run.get("temp", [])]
                       + [(it.get("kills0", 0), item_fx(it["key"], it["rar"]))
                                                       for it in run["items"]]
                       + [(0, SYNERGIES[k]["fx"]) for k in active_synergies(run)]):
        for k, v in fx.items():
            if k == "elem_boost":                  # not an output field: added to each element already above 0
                boost += v
                continue
            if k == "grow":                        # +1 ATK every v kills made after taking the item
                st["atk"] += max(0, run["kills"] - kills0) // v
            elif k == "trap":
                st["trap"] *= v
            elif k == "area":
                st["area"] = st["area"] or bool(v)
            else:
                st[k] += v
    for el in ELEMENTS.values():
        if st[el] > 0:
            st[el] += boost
    st["attack_cost"] = max(0, st["attack_cost"])
    st["maxhp"] = max(5, st["maxhp"])
    st["atk"] = max(1, st["atk"])
    st["dodge"] = min(MAX_DODGE, st["dodge"])
    st["energy"] = min(MAX_ENERGY_BONUS, st["energy"])
    st["spd"] = max(1, st["spd"])
    st["crit"] = min(MAX_CRIT, st["crit"])
    for el in ELEMENTS.values():
        st[el] = min(MAX_ELEM_CHANCE, st[el])
    st["trap"] = min(TRAP_LIMITS[1], max(TRAP_LIMITS[0], st["trap"]))
    st["block"] = min(MAX_BLOCK, int(st["block"]))
    st["thorns"] = min(MAX_THORNS, st["thorns"])
    st["double"] = min(MAX_DOUBLE, st["double"])
    st["luck"] = min(MAX_LUCK, st["luck"])
    st["discount"] = min(MAX_DISCOUNT, st["discount"])
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
    """Rolls rarity and item (each item once per run). None when no unlocked item is left."""
    taken = {i["key"] for i in run["items"]}
    if (run.get("pending") or {}).get("kind") == "offer":
        taken.add(run["pending"]["key"])
    pool = [k for k in unlocked_items(meta) if k not in taken]
    if not pool:
        return None
    lo = 1 if best else 0
    w = _rarity_weights(run["floor"])
    luck = 1 + stats(run)["luck"]
    w = [w[0]] + [x * luck for x in w[1:]]            # luck pulls rare, epic and legendary
    idx = max(lo, rng.choices(range(len(RARITIES)), w)[0])
    # goes down one rarity at a time, then up; below the floor only as a last resort
    order = list(range(idx, lo - 1, -1)) + list(range(idx + 1, len(RARITIES))) + list(range(lo - 1, -1, -1))
    for i in order:
        rar = RARITIES[i]
        cands = [k for k in pool if rar in ITEMS[k]["rarities"]]
        if cands:
            return {"key": rng.choice(cands), "rar": rar}
    return None


def shop_price(run: dict, f: int) -> int:
    """Shop price of the item on floor f, with the items' discount (minimum 1)."""
    return max(1, round((SHOP_PRICE[0] + SHOP_PRICE[1] * f) * (1 - stats(run)["discount"])))


def auto_choice(run: dict, offer: dict) -> str:
    """Automatic rule: consumes if it is a heal and HP is below 40%; otherwise takes it."""
    if "heal" in ITEMS[offer["key"]]["consume"] and run["hp"] < 0.4 * stats(run)["maxhp"]:
        return "consume"
    return "take"


def resolve_offer(run: dict, offer: dict, choice: str, ev: dict) -> None:
    """Applies the choice. Achievements are left to the caller (enter_room / *_pending)."""
    item = {"key": offer["key"], "rar": offer["rar"]}      # without the floor: this is what the event (GUI) receives
    if choice == "take":
        run["items"].append({**item, "floor": run["floor"], "kills0": run["kills"]})
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


def add_temp(run: dict, fx: dict, rooms: int) -> None:
    """Temporary effect: active for the next `rooms` non-stairs rooms (see enter_room)."""
    run["temp"].append({"fx": dict(fx), "rooms": rooms})


# Per-kind pending choices: (auto(run, p) -> str, apply(run, meta, p, choice, ev, mode) -> None, valid(p) -> bool).
# mode is "interactive" or "auto" (later rooms resolving inline may chain another offer).
CHOICES: dict = {
    "offer": (auto_choice,
              lambda run, meta, p, choice, ev, mode="interactive": resolve_offer(run, p, choice, ev),
              lambda p: p.get("key") in ITEMS and p.get("rar") in RARITIES),
}


def choose_pending(run: dict, meta: dict, choice: str) -> dict:
    """Resolves the pending choice with the player's choice (offers: "take" or "consume")."""
    ev: dict = {"lines": []}
    p, run["pending"] = run.get("pending"), None
    if p:
        CHOICES[p.get("kind", "offer")][1](run, meta, p, choice, ev)
        note_synergies(run, meta, ev)
        _check_achievements(run, meta, ev)
    return ev


def resolve_pending(run: dict, meta: dict) -> dict:
    """Resolves the pending offer with the automatic rule."""
    if not run.get("pending"):
        return {"lines": []}
    p = run["pending"]
    return choose_pending(run, meta, CHOICES[p.get("kind", "offer")][0](run, p))


def apply_damage(run: dict, d: int) -> int:
    """The shield absorbs first; returns the damage that reached HP."""
    absorbed = min(run["shield"], d)
    run["shield"] -= absorbed
    run["hp"] -= d - absorbed
    return d - absorbed


def _apply_status(s: dict, name: str, turns_bonus: int = 0) -> None:
    """Puts the status on s. Burn renews; poison gains a stack (at the cap, renews the oldest).
    turns_bonus: extra turns on burn/shock/freeze (the Elemental 4 set)."""
    if name == "poison":
        v = s.setdefault("poison", [])
        if len(v) < POISON_MAX_STACKS:
            v.append(0)
        else:
            v[v.index(max(v))] = 0
    else:
        s[name] = {"burn": BURN_TURNS, "shock": SHOCK_TURNS, "freeze": FREEZE_TURNS}[name] + turns_bonus


def _status_damage(s: dict, f: int) -> list[tuple[str, int]]:
    """Start-of-round tick: [(name, damage)] and already decrements the duration."""
    out = []
    if s.get("burn"):
        s["burn"] -= 1
        out.append(("burn", round(BURN[0] + BURN[1] * f)))
    if s.get("poison"):
        v = [t + 1 for t in s["poison"]]                # each stack deals 1, 2, 3, 4 damage
        out.append(("poison", sum(v)))
        s["poison"] = [t for t in v if t < POISON_TURNS]
    return out


_REACTIONS = {frozenset(r["req"]["status"]): k for k, r in SYNERGIES.items() if r["kind"] == "reaction"}


def _react(key, i, atk, f, foes, x, step):
    """Effect of reaction `key` on foe i (x). Uses _apply_status directly, so effects never chain."""
    if x["hp"] <= 0:                  # an earlier reaction of the same hit already killed it
        return
    others = [j for j, y in enumerate(foes) if j != i and y["hp"] > 0]
    d = 0
    if key == "shatter":
        d, x["status"]["freeze"] = atk, 0
    elif key == "toxic_fumes":
        for j in others:
            _apply_status(foes[j]["status"], "poison")
    elif key == "overload":
        d = round(BURN[0] + BURN[1] * f)
    elif key == "conductor":
        if others:
            _apply_status(foes[others[0]]["status"], "shock")
    elif key == "jolt_venom":
        if len(x["status"].get("poison", [])) < POISON_MAX_STACKS:
            _apply_status(x["status"], "poison")
    elif key == "frostbite":
        x["status"]["freeze"] = x["status"].get("freeze", 0) + 1
    x["hp"] -= d
    step("pet", i, d, status="burn" if key == "overload" else None, dot=key == "overload", reaction=key)


def combat(run: dict, st: dict, foes: list[dict], rng: random.Random, f: int):
    """Round-based fight. Returns (won, steps, killer, tie); mutates run["hp"] and the enemies' hp/status.

    Without `area` the pet hits the living enemy with the lowest HP; with `area`, one step per living target.
    `double`: chance of a 2nd hit on the same target (step with double=True). With `helper` > 0, the "helper"
    participant acts once per round (pet's spd, right after it) on the living enemy with the lowest HP; it is never a target.
    tie: the fight hit the MAX_ROUNDS limit (the pet survives, but the room gives no reward).
    """
    steps = []
    pst: dict = {}                                       # pet status (only during the fight)

    charges = st["block"]                              # enemy hits the pet cancels in this fight

    def step(who, target, dmg=0, crit=False, status=None, skip=False, dot=False, dodge=False,
              locked=False, thorns=False, double=False, reaction=None):
        steps.append({"who": who, "target": target, "dmg": dmg, "crit": crit, "status": status, "skip": skip,
                       "dot": dot, "dodge": dodge, "locked": locked, "thorns": thorns, "double": double,
                       "reaction": reaction})

    def alive():
        return [i for i, x in enumerate(foes) if x["hp"] > 0]

    def skips_turn(s):
        lost = False
        if s.get("freeze"):
            s["freeze"] -= 1
            if rng.random() < FREEZE_CHANCE:
                lost, s["freeze"] = True, 0
        if s.get("shock"):
            s["shock"] -= 1
            lost = rng.random() < SHOCK_CHANCE or lost
        return lost

    def critical(crit, critdmg, spd, target_spd):
        """(is crit, multiplier); twice the speed gives +DOUBLE_CRIT and critdmg x2."""
        double = spd >= 2 * target_spd
        e_crit = rng.random() < crit + (DOUBLE_CRIT if double else 0)
        return e_crit, (critdmg * (2 if double else 1) if e_crit else 1)

    for _ in range(MAX_ROUNDS):
        # 1. status damage at the start of the round (ignores the shield)
        for name, d in _status_damage(pst, f):
            run["hp"] -= d
            step("pet", "pet", d, status=name, dot=True)
            if run["hp"] <= 0:
                run["hp"] = 0
                return False, steps, name.capitalize(), False
        for i in alive():
            for name, d in _status_damage(foes[i]["status"], f):
                foes[i]["hp"] -= d
                step(i, i, d, status=name, dot=True)
        if not alive():
            return True, steps, "", False
        # 2. order by speed; tie: pet first, then list order (stable sort)
        # the helper comes right after the pet (same spd, stable sort)
        ajud = [("helper", st["spd"])] if st["helper"] > 0 else []
        order = sorted([("pet", st["spd"])] + ajud + [(i, foes[i]["spd"]) for i in alive()], key=lambda x: -x[1])
        for who, _spd in order:
            if who not in ("pet", "helper") and foes[who]["hp"] <= 0:
                continue
            if who == "helper":                          # no status, crit or skipped turn
                i = min(alive(), key=lambda i: foes[i]["hp"])
                d = max(1, round(st["helper"]))      # never 0 damage
                foes[i]["hp"] -= d
                step("helper", i, d)
                if not alive():
                    return True, steps, "", False
                continue
            if skips_turn(pst if who == "pet" else foes[who]["status"]):
                step(who, who, skip=True)
                continue
            if who == "pet":
                vs = alive()
                targets = vs if st["area"] else [min(vs, key=lambda i: foes[i]["hp"])]
                # fury: +fury ATK for every 10% of missing HP (integer math, no float error)
                atk = st["atk"] + st["fury"] * ((st["maxhp"] - run["hp"]) * 10 // st["maxhp"])
                if st["attack_cost"]:                     # blood: attacking costs HP, but never below 1
                    run["hp"] = max(1, run["hp"] - st["attack_cost"])
                for i in targets:
                    x = foes[i]
                    # 2nd hit (double): rolled per target, only if the target survived; no double-speed bonus
                    for dup in (False, True):
                        if dup and (x["hp"] <= 0 or not st["double"] or rng.random() >= st["double"]):
                            break
                        e_crit, mult = critical(st["crit"], st["critdmg"], 0 if dup else st["spd"], x["spd"])
                        d = round(max(1, atk + rng.randint(-1, 1)) * mult)
                        x["hp"] -= d
                        applied, reacts = None, []
                        if x["hp"] > 0:
                            had = [n for n in STATUS_NAME if x["status"].get(n)]    # before this hit's elements
                            for el, name in STATUS_NAME.items():      # each element rolls separately
                                if st[el] and rng.random() < st[el]:
                                    _apply_status(x["status"], name, st["status_turns"])
                                    applied = applied or name
                                    if name not in had and had:       # a new status next to another one
                                        reacts.append(_REACTIONS[frozenset((name, had[0]))])
                        step("pet", i, d, e_crit, applied, double=dup)
                        for key in reacts:
                            _react(key, i, atk, f, foes, x, step)
                if not alive():
                    return True, steps, "", False
            else:
                x = foes[who]
                if rng.random() < st["dodge"]:
                    step(who, "pet", dodge=True)
                    continue
                if charges:                                 # block: after the dodge, spends one charge
                    charges -= 1
                    step(who, "pet", locked=True)
                    continue
                e_crit, mult = critical(x["crit"], x["critdmg"], x["spd"], st["spd"])
                raw = round(max(1, x["atk"] - st["def"] + rng.randint(-1, 1)) * mult)
                d = apply_damage(run, raw)
                applied = None
                if x["boss"] and x.get("element") and rng.random() < BOSS_STATUS_CHANCE:
                    applied = STATUS_NAME[ELEMENTS[x["element"]]]
                    _apply_status(pst, applied)
                step(who, "pet", d, e_crit, applied)
                if run["hp"] <= 0:
                    run["hp"] = 0
                    return False, steps, x["name"], False
                returns = round(raw * st["thorns"])      # thorns: fraction of the damage before the shield
                if returns:
                    x["hp"] -= returns
                    step("pet", who, returns, thorns=True)
                    if not alive():
                        return True, steps, "", False
    return True, steps, "", True                        # safety limit: tie, no reward


def _count(run: dict, steps: list[dict], foes: list[dict], horde4: bool) -> None:
    """Achievement counters from the fight steps. Death by status: the enemy crosses hp 0 on a dot step."""
    c = run.setdefault("counters", dict(COUNTERS_ZERO))
    hp = [x["hp_max"] for x in foes]
    for p in steps:
        if p["dodge"]:
            c["dodges"] += 1
        if p["locked"]:
            c["blocks"] += 1
        i = p["target"]
        if isinstance(i, int) and (p["who"] in ("pet", "helper") or p["dot"]):
            before, hp[i] = hp[i], hp[i] - p["dmg"]
            if p["dot"] and before > 0 >= hp[i]:
                c["poison_kills" if p["status"] == "poison" else "burn_kills"] += 1
    if horde4:
        c["horde4"] += 1


def die(run: dict, meta: dict, ev: dict, killer: str, kind: str = "monster") -> None:
    """kind: monster|horde|boss|mimic|trap|gave_up; death by Burn/Poison becomes "status"."""
    if killer in ("Burn", "Poison"):
        kind = "status"
    run["dead"] = True
    ev["died"] = True
    ev["killed_by"] = killer
    meta["runs"] += 1
    meta["graveyard"].append({
        "run": run["id"], "char": run["char"], "floor": run["floor"], "room": run["room"],
        "killer": killer, "kind": kind, "items": [{"key": i["key"], "rar": i["rar"]} for i in run["items"]],
        "gold": run["gold"], "kills": run["kills"], "date": date.today().isoformat(),
    })
    meta["graveyard"] = meta["graveyard"][-50:]
    _check_achievements(run, meta, ev)


def _check_achievements(run: dict, meta: dict, ev: dict) -> None:
    # every room outcome (and death) passes here: record synergies first so their achievements see them
    note_synergies(run, meta, ev, [h["reaction"] for h in ev.get("hits", ()) if h.get("reaction")])
    have = set(meta["achievements"])
    new = []

    def grant(key, cond):
        if cond and key not in have:
            new.append(key)
            have.add(key)

    grant("floor5", run["floor"] >= 5)
    grant("floor10", run["floor"] >= 10)
    grant("floor20", run["floor"] >= 20)
    grant("boss1", run["bosses"] >= 1)
    grant("mimic", ev.get("kind") == "mimic" and ev.get("won"))
    grant("rich", run["gold"] >= 100)
    grant("collector", len(run["items"]) >= 10)
    cont = run.get("counters", {})
    grant("poison1", cont.get("poison_kills", 0) >= 1)
    grant("gold300", run["gold"] >= 300)
    grant("horde4", cont.get("horde4", 0) >= 1)
    grant("burn1", cont.get("burn_kills", 0) >= 1)
    grant("dodge10", cont.get("dodges", 0) >= 10)
    grant("floor15", run["floor"] >= 15)
    grant("block10", cont.get("blocks", 0) >= 10)
    grant("bosses3", meta.get("bosses", 0) >= 3)
    grant("consume10", len(run.get("consumed", [])) >= 10)
    grant("die10", meta["runs"] >= 10)
    grant("no_consume10", run["floor"] >= 10 and not run.get("consumed"))
    grant("legendaries3", sum(1 for it in run["items"] if it["rar"] == "legendary") >= 3)
    grant("helpers3", sum(1 for it in run["items"] if "helper" in ITEMS[it["key"]]["fx"]) >= 3)
    grant("poison3", cont.get("poison_kills", 0) >= 3)
    grant("bosses3run", run["bosses"] >= 3)
    grant("synergy5", len(meta.get("synergies", {})) >= 5)
    grant("reactions_all", all(k in meta.get("synergies", {}) for k, s in SYNERGIES.items() if s["kind"] == "reaction"))
    grant("synergies3run", len(run.get("synergies", ())) >= 3)
    grant("floor13", run.get("dead") and run["floor"] == 13)
    if run["floor"] >= 8 and "floor8full" not in have:
        grant("floor8full", run["hp"] >= stats(run)["maxhp"])
    if "elements3" not in have:
        elem = set(ELEMENTS.values())
        grant("elements3", sum(1 for it in run["items"] if elem & set(ITEMS[it["key"]]["fx"])) >= 3)
    if new:
        meta["achievements"].extend(new)
        ev["unlocks"] = new
    b = meta["best"]
    if (run["floor"], run["room"]) > (b["floor"], b["room"]):
        meta["best"] = {"floor": run["floor"], "room": run["room"]}


def _heal_by_item(run, ev, maxhp, hp, heal):
    """HP = hp + heal (up to maxhp); what the item heal actually added goes into ev["item_heal"] (floater in the GUI)."""
    run["hp"] = min(maxhp, hp + heal)
    if run["hp"] > hp:
        ev["item_heal"] = run["hp"] - hp


def enter_room(run: dict, meta: dict, rng: random.Random,
               stage_floors: list[int] | None = None, mode: str = "auto") -> dict:
    """Spends energy, resolves the next room and returns what happened.

    mode "auto": the automatic rule decides offers right away.
    mode "interactive": the offer goes to run["pending"] and ev["pending"] (the GUI resolves it).
    """
    stage_floors = stage_floors or DEFAULT_STAGE_FLOORS
    run["energy"] -= room_cost(run)
    st = stats(run)
    ev: dict = {"lines": [], "won": False, "died": False}
    f = run["floor"]

    # stairs to the next floor
    if run["room"] >= ROOMS_PER_FLOOR:
        run["floor"] += 1
        run["room"] = 0
        ev.update(kind="stairs", name=f"Floor {run['floor']}", sprite="stairs")
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
        st = stats(run)
        _heal_by_item(run, ev, st["maxhp"], run["hp"], st["heal_floor"])
        return ev

    run["room"] += 1
    run["temp"] = [{**t, "rooms": t["rooms"] - 1} for t in run["temp"] if t["rooms"] > 0]
    st = stats(run)
    # regenerates every room (+ heal_room)
    _heal_by_item(run, ev, st["maxhp"], min(st["maxhp"], run["hp"] + REGEN_PER_ROOM), st["heal_room"])

    if run["room"] == ROOMS_PER_FLOOR and f % BOSS_EVERY == 0:
        kind = "boss"
    else:
        weights = [(k, w) for k, w in ROOM_WEIGHTS if k != "horde" or f >= HORDE_MIN_FLOOR]
        kind = rng.choices([k for k, _ in weights], [w for _, w in weights])[0]
        if kind == "chest" and f >= 2 and rng.random() < 0.12:
            kind = "mimic"
    ev["kind"] = kind
    run["rooms"][kind] = run["rooms"].get(kind, 0) + 1

    def deliver(offer):
        if mode == "auto":
            resolve_offer(run, offer, auto_choice(run, offer), ev)
        else:
            run["pending"] = {"kind": "offer", **offer, "source": kind}
            ev["pending"] = offer

    def give(best=False):
        offer = roll_offer(run, meta, rng, best)
        if offer:
            deliver(offer)
        else:                                  # out of items: chest gold
            gold = round((5 + 2 * f) * (1 + st["gold"]))
            run["gold"] += gold
            ev["gold"] = ev.get("gold", 0) + gold

    if kind in ("monster", "boss", "mimic", "horde"):
        pool = [m for m in MONSTERS if m[4] <= f]
        if kind == "mimic":
            foes = [make_mimic(f)]
        elif kind == "horde":                 # a boss never comes in a horde
            n = rng.randint(2, horde_max(f))
            foes = [make_foe(rng.choice(pool), f, mult=HORDE_MULT[n]) for _ in range(n)]
        else:
            foes = [make_foe(rng.choice(pool), f, boss=(kind == "boss"))]
        ev["name"] = f"Horde ({len(foes)})" if kind == "horde" else foes[0]["name"]
        ev["foes"] = [{k: x[k] for k in ("sprite", "name", "boss", "element", "hp_max")} for x in foes]
        hp_before = run["hp"]
        won, ev["hits"], killer, tie = combat(run, st, foes, rng, f)
        ev["dmg"] = hp_before - run["hp"]
        _count(run, ev["hits"], foes, kind == "horde" and len(foes) == 4 and won and not tie)
        if not won:
            die(run, meta, ev, killer, kind)
            return ev
        if tie:                            # cleared the room, but without gold, kills, boss bonus or item
            ev["tie"] = True
            _check_achievements(run, meta, ev)
            return ev
        ev["won"] = True
        run["kills"] += len(foes)

        def monster_gold():
            return round((rng.randint(1, 3) + f // 2) * (1 + st["gold"]))
        gold = round(sum(monster_gold() for _ in foes) * HORDE_GOLD_MULT) if kind == "horde" else monster_gold()
        if st["lifesteal"]:
            run["hp"] = min(st["maxhp"], run["hp"] + st["lifesteal"])
        if kind == "boss":
            run["bosses"] += 1
            meta["bosses"] = meta.get("bosses", 0) + 1
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
        ev.update(name="Chest", sprite="chest")
        if rng.random() < CHEST_ITEM_CHANCE:
            give()
        else:                                  # only happens if CHEST_ITEM_CHANCE < 1
            gold = round((5 + 2 * f) * (1 + st["gold"]))
            run["gold"] += gold
            ev["gold"] = gold

    elif kind == "trap":
        ev.update(name="Trap", sprite="trap")
        if rng.random() < st["dodge"]:
            ev["dodged"] = True
        else:
            dmg = apply_damage(run, max(1, round((2 + 0.6 * f) * st["trap"])))
            ev["dmg"] = dmg
            if run["hp"] <= 0:
                run["hp"] = 0
                die(run, meta, ev, "Trap", "trap")
                return ev

    elif kind == "fountain":
        ev.update(name="Fountain", sprite="fountain")
        heal = max(1, round(st["maxhp"] * 0.35))
        heal = min(heal, st["maxhp"] - run["hp"])
        run["hp"] += heal
        ev["heal"] = heal

    elif kind == "shop":
        ev.update(name="Little Shop", sprite="shop")
        potion, item_price = 6 + f, shop_price(run, f)
        if run["hp"] < st["maxhp"] * 0.5 and run["gold"] >= potion:
            run["gold"] -= potion
            heal = min(st["maxhp"] - run["hp"], round(st["maxhp"] * 0.5))
            run["hp"] += heal
            ev["heal"] = heal
            ev["lines"].append(f"Bought a potion (-{potion} gold)")
        elif run["gold"] >= item_price:
            offer = roll_offer(run, meta, rng, best=True)
            if offer:
                run["gold"] -= item_price
                ev["lines"].append(f"Paid {item_price} gold")
                deliver(offer)
            else:
                ev["lines"].append("The shop has nothing new...")
        else:
            ev["lines"].append("No gold to buy...")

    elif kind == "altar":
        ev.update(name="Dark Altar", sprite="altar")
        pact = rng.choice(["sangue", "pedra", "bencao", "ouro"])
        b = run["base"]
        if pact == "sangue":
            loss = max(2, round(b["maxhp"] * 0.2))
            b["maxhp"] -= loss
            b["atk"] += 2
            ev["lines"].append(f"Blood pact: -{loss} max HP, +2 ATK")
        elif pact == "pedra":
            if b["atk"] > 2:
                b["atk"] -= 1
                b["def"] += 1
                ev["lines"].append("Stone skin: -1 ATK, +1 DEF")
            else:
                ev["lines"].append("The altar ignores you...")
        elif pact == "bencao":
            b["maxhp"] += 4
            run["hp"] += 4
            ev["lines"].append("Dark blessing: +4 max HP")
        else:
            if run["gold"] >= 10:
                run["gold"] -= 10
                run["hp"] = stats(run)["maxhp"]
                ev["lines"].append("Traded 10 gold for a full heal")
            else:
                run["gold"] += 5
                ev["gold"] = 5
                ev["lines"].append("Found 5 coins on the altar")
        stats(run)

    _check_achievements(run, meta, ev)
    return ev


# Bump when a combat formula/rule or a number written straight in the code changes (the hash below does not see that).
RULES_REV = 10


def _balance_version() -> str:
    """Hash of the balance numbers (not the visuals): identifies the rules version in the records."""
    its = {k: {f: v.get(f) for f in ("fx", "consume", "rarities", "req")} for k, v in sorted(ITEMS.items())}
    mons = [(m[0],) + tuple(m[2:]) for m in MONSTERS]  # without the display name
    blob = [RULES_REV, its, mons, ROOM_COST, ROOMS_PER_FLOOR, MAX_STORED_ROOMS, BOSS_EVERY, MON_HP, MON_ATK,
            BOSS_HP, BOSS_ATK, BOSS_RAMP, BOSS_RAMP_FROM, REGEN_PER_ROOM, FLOOR_BONUS_HP, ROOM_WEIGHTS, RAR_MULT,
            [_rarity_weights(f) for f in range(1, 41)], MAX_ENERGY_BONUS, TRAP_LIMITS, MAX_DODGE,
            CHEST_ITEM_CHANCE, SHOP_PRICE, MON_SPD, BOSS_SPD_BONUS, MON_CRIT, BOSS_CRIT, FOE_CRITDMG, PET_SPD,
            PET_CRIT, PET_CRITDMG, MAX_CRIT, MAX_ELEM_CHANCE, MAX_BLOCK, MAX_THORNS, MAX_DOUBLE, MAX_LUCK, MAX_DISCOUNT, BOSS_ELEMENT, BOSS_STATUS_CHANCE, DOUBLE_CRIT, BURN,
            BURN_TURNS, SHOCK_CHANCE, SHOCK_TURNS, POISON_TURNS, POISON_MAX_STACKS, FREEZE_CHANCE, FREEZE_TURNS,
            MAX_ROUNDS, HORDE_MIN_FLOOR, HORDE_MULT, HORDE_GOLD_MULT,
            {k: {f: v[f] for f in ("kind", "req", "fx")} for k, v in sorted(SYNERGIES.items())}]
    return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()[:8]


BALANCE_VERSION = _balance_version()


def run_record(run: dict, killer: str, gave_up: bool, mode: str, achievements: list,
               killer_kind: str = "") -> dict:
    """Record line of a finished run (same format in the game and in the simulator)."""
    return {
        "run": run["id"], "char": run["char"], "floor": run["floor"], "room": run["room"],
        "killer": killer, "killer_kind": killer_kind, "gave_up": gave_up,
        "items": [dict(i) for i in run["items"]], "consumed": [dict(i) for i in run["consumed"]],
        "gold": run["gold"], "kills": run["kills"], "bosses": run["bosses"],
        "date": date.today().isoformat(), "mode": mode, "version": BALANCE_VERSION,
        "achievements": list(achievements), "synergies": list(run.get("synergies", [])), "rooms": dict(run.get("rooms", {})),
    }
