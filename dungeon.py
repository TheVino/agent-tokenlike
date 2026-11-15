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
    "andar5": "Chegar ao andar 5",
    "chefe1": "Derrotar um chefe",
    "mimico": "Derrotar um mímico",
    "rico": "Juntar 100 de ouro numa run",
    "colecionador": "Pegar 10 itens numa run",
    "andar10": "Chegar ao andar 10",
    "andar20": "Chegar ao andar 20",
    "veneno1": "Matar um inimigo com veneno",
    "elementos3": "Pegar 3 itens elementais numa run",
    "ouro300": "Juntar 300 de ouro numa run",
    "horda4": "Vencer uma horda de 4 inimigos",
    "queima1": "Matar um inimigo com queimadura",
    "andar8cheio": "Chegar ao andar 8 com o HP cheio",
    "andar15": "Chegar ao andar 15",
    "esquiva10": "Esquivar 10 golpes numa run",
    "bloqueio10": "Bloquear 10 golpes numa run",
    "chefes3": "Vencer 3 chefes no total",
    "consumir10": "Consumir 10 itens numa run",
    "morrer10": "Morrer 10 vezes",
    "ajudantes3": "Pegar 3 itens de ajudante numa run",
    "sem_consumir10": "Chegar ao andar 10 sem consumir nenhum item",
    "lendarios3": "Pegar 3 itens lendários numa run",
    "veneno3": "Matar 3 inimigos com veneno numa run",
    "andar13": "Morrer no andar 13",
    "chefes3run": "Vencer 3 chefes numa mesma run",
}

RARITIES = ("comum", "raro", "epico", "lendario")
RAR_MULT = {"comum": 1, "raro": 1.2, "epico": 1.4, "lendario": 1.6}
RAR_NAMES = {"comum": "Comum", "raro": "Raro", "epico": "Épico", "lendario": "Lendário"}
RAR_COLOR = {"comum": None, "raro": "#6fd6ff", "epico": "#b48cff", "lendario": "#ffd23f"}
CHOICE_WINDOW_S = 30         # choice window in interactive mode (the GUI keeps the time)
MAX_ENERGY_BONUS = 1.0       # summed "energy" capped at +100%
TRAP_LIMITS = (0.25, 3.0)    # floor and cap of the summed trap multiplier
MAX_DODGE = 0.5              # cap of the summed dodge

_C = ["comum", "raro", "epico"]
_R = ["raro", "epico", "lendario"]

# fx: atk, def, maxhp, dodge, gold (+% gold), trap (trap damage
#     multiplier), energy (+% energy => cheaper rooms), lifesteal (heal per win)
# consume: what happens if the hero consumes the item instead of taking it (heal or shield)
ITEMS = {
    "adaga":        {"name": "Adaga Enferrujada",  "rarities": _C, "fx": {"atk": 2}, "consume": {"heal": 6},
                     "look": {"type": "obj", "anchor": "dir", "art": "adaga"}},
    "espada_osso":  {"name": "Espada de Osso",     "rarities": _C, "fx": {"atk": 4}, "consume": {"heal": 8},
                     "look": {"type": "obj", "anchor": "dir", "art": "espada_osso"}},
    "cajado":       {"name": "Cajado Espectral",   "rarities": _R, "fx": {"atk": 3, "lifesteal": 2},
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
    "chapeu":       {"name": "Chapéu de Bruxa",    "rarities": _C, "fx": {"gold": 0.5, "maxhp": 3}, "consume": {"heal": 6},
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
    # batch A: elementals (fire, lightning, poison, ice); fx = chance per hit to apply the status
    "brasa":        {"name": "Brasa Viva",         "rarities": _C, "fx": {"queimar": 0.12, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "chamas"}},
    "pelagem_chamuscada": {"name": "Pelagem Chamuscada", "rarities": _R, "fx": {"queimar": 0.1, "atk": 2},
                     "consume": {"heal": 8}, "look": {"type": "chamas", "color": "#ff6b3d"}, "req": "andar5"},
    "tocha":        {"name": "Tocha de Sebo",      "rarities": _C, "fx": {"queimar": 0.1, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "tocha"}},
    "fogo_fatuo":   {"name": "Fogo-fátuo Rubro",   "rarities": ["raro", "epico"], "fx": {"queimar": 0.15, "atk": 1},
                     "consume": {"shield": 7}, "look": {"type": "obj", "anchor": "flutua", "art": "fogo_fatuo"}},
    "coracao_magma": {"name": "Coração de Magma",  "rarities": ["lendario"], "fx": {"queimar": 0.2, "atk": 3},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "frente", "art": "coracao_magma"},
                     "req": "chefe1"},
    "pelo_estatico": {"name": "Pelo Estático",     "rarities": _C, "fx": {"eletrizar": 0.08, "atk": 1},
                     "consume": {"shield": 5}, "look": {"type": "faiscas"}},
    "limao_eletrico": {"name": "Limão Elétrico",   "rarities": _C, "fx": {"eletrizar": 0.1, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "esq", "art": "limao_eletrico"}},
    "para_raios":   {"name": "Para-raios Torto",   "rarities": _C, "fx": {"eletrizar": 0.08, "def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "topo", "art": "para_raios"}},
    "nuvem_raivosa": {"name": "Nuvenzinha Raivosa", "rarities": ["raro", "epico"], "fx": {"eletrizar": 0.12, "atk": 1},
                     "consume": {"shield": 7}, "look": {"type": "faiscas", "color": "#9fd8ff"}, "req": "andar5"},
    "antena":       {"name": "Antena de Tempestade", "rarities": _R, "fx": {"eletrizar": 0.1, "atk": 1},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "topo", "art": "antena"},
                     "req": "andar10"},
    "musgo":        {"name": "Musgo Tóxico",       "rarities": _C, "fx": {"envenenar": 0.12, "maxhp": 3, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "gotas_veneno"}},
    "dente_sapo":   {"name": "Dente de Sapo-lodo", "rarities": _C, "fx": {"envenenar": 0.12, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "dente_sapo"}},
    "cogumelo":     {"name": "Cogumelo Suspeito",  "rarities": _C, "fx": {"envenenar": 0.1, "lifesteal": 1, "atk": 1},
                     "consume": {"heal": 8}, "look": {"type": "obj", "anchor": "topo", "art": "cogumelo"}},
    "lodo":         {"name": "Lodo Fervente",      "rarities": ["raro", "epico"], "fx": {"envenenar": 0.15, "atk": 1},
                     "consume": {"heal": 9}, "look": {"type": "gotas_veneno", "color": "#7be36b"}, "req": "andar5"},
    "incensario":   {"name": "Incensário da Peste", "rarities": ["lendario"], "fx": {"envenenar": 0.15, "area": True},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "flutua", "art": "incensario"},
                     "req": "chefe1"},
    "bafo_gelido":  {"name": "Bafo Gélido",        "rarities": _C, "fx": {"congelar": 0.06, "def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "geada"}},
    "estilhaco":    {"name": "Estilhaço de Gelo",  "rarities": _C, "fx": {"congelar": 0.06, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "estilhaco"}},
    "cachecol":     {"name": "Cachecol de Neve",   "rarities": _C, "fx": {"congelar": 0.06, "def": 1, "maxhp": 3, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "frente", "art": "cachecol"}},
    "casca_geada":  {"name": "Casca de Geada",     "rarities": _R, "fx": {"congelar": 0.08, "def": 1, "atk": 1},
                     "consume": {"shield": 9}, "look": {"type": "geada", "color": "#c8f4ff"}, "req": "andar10"},
    "floco_eterno": {"name": "Floco Eterno",       "rarities": ["epico", "lendario"], "fx": {"congelar": 0.12, "maxhp": 4, "atk": 1},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "flutua", "art": "floco_eterno"},
                     "req": "chefe1"},
    # batch B: defense (block, thorns), regeneration (heal per room/floor) and blood (attack cost, fury)
    "broquel":      {"name": "Broquel de Casca",   "rarities": _C, "fx": {"bloqueio": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "esq", "art": "broquel"}},
    "casco_tartaruga": {"name": "Casco de Jabuti Velho", "rarities": _R, "fx": {"bloqueio": 1, "spd": -2},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "esq", "art": "casco_tartaruga"},
                     "req": "andar5"},
    "manopla_rebite": {"name": "Manopla Rebitada", "rarities": _C, "fx": {"bloqueio": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "dir", "art": "manopla_rebite"}},
    "sino_guarda":  {"name": "Sininho de Alerta",  "rarities": _C, "fx": {"bloqueio": 1, "maxhp": -3},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "frente", "art": "sino_guarda"}},
    "muralha_viva": {"name": "Muralha de Pedra Viva", "rarities": ["lendario"], "fx": {"bloqueio": 1, "maxhp": 2},
                     "consume": {"shield": 14}, "look": {"type": "obj", "anchor": "esq", "art": "muralha_viva"},
                     "req": "chefe1"},
    "ourico":       {"name": "Casca de Castanha",  "rarities": _C, "fx": {"espinhos": 0.15, "def": 1},
                     "consume": {"shield": 6}, "look": {"type": "espinhos", "color": "#b0763f"}},
    "cacto_mal":    {"name": "Cacto Mal-humorado", "rarities": _C, "fx": {"espinhos": 0.2, "maxhp": 3},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "topo", "art": "cacto_mal"}},
    "armadura_farpas": {"name": "Gibão de Farpas", "rarities": _R, "fx": {"espinhos": 0.15, "def": 1, "atk": 1},
                     "consume": {"shield": 8}, "look": {"type": "espinhos", "color": "#c99a00"},
                     "req": "andar5"},
    "colar_presas": {"name": "Colar de Presas",    "rarities": _C, "fx": {"espinhos": 0.1, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "frente", "art": "colar_presas"}},
    "espelho_rachado": {"name": "Espelho Rachado", "rarities": ["lendario"], "fx": {"espinhos": 0.2, "dodge": 0.05, "atk": 1},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "flutua", "art": "espelho_rachado"},
                     "req": "chefe1"},
    "chazinho":     {"name": "Bule Morno",         "rarities": _C, "fx": {"cura_sala": 1, "maxhp": 3},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "esq", "art": "chazinho"}},
    "raiz_teimosa": {"name": "Raiz Teimosa",       "rarities": _C, "fx": {"cura_andar": 8, "maxhp": 3},
                     "consume": {"heal": 8}, "look": {"type": "obj", "anchor": "topo", "art": "raiz_teimosa"}},
    "lamparina_lar": {"name": "Lareirinha de Bolso", "rarities": _C, "fx": {"cura_andar": 5, "def": 1},
                     "consume": {"heal": 8}, "look": {"type": "obj", "anchor": "frente", "art": "lamparina_lar"}},
    "fonte_bolso":  {"name": "Gota de Fonte Presa", "rarities": ["raro", "epico"], "fx": {"cura_sala": 2, "maxhp": 5},
                     "consume": {"heal": 12}, "look": {"type": "obj", "anchor": "flutua", "art": "fonte_bolso"},
                     "req": "andar5"},
    "seiva_antiga": {"name": "Seiva Ancestral",    "rarities": ["epico", "lendario"], "fx": {"cura_sala": 1, "cura_andar": 8, "maxhp": 4},
                     "consume": {"heal": 14}, "look": {"type": "tingir", "color": "#e0a030", "amount": 0.3},
                     "req": "andar10"},
    "adaga_sangria": {"name": "Lâmina Sedenta",    "rarities": _C, "fx": {"custo_ataque": 1, "atk": 3},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "adaga_sangria"}},
    "coracao_costurado": {"name": "Coração Remendado", "rarities": _C, "fx": {"furia": 1, "maxhp": 2},
                     "consume": {"heal": 9}, "look": {"type": "adesivo", "art": "coracao_costurado", "at": [0.5, 0.6]}},
    "mascara_furia": {"name": "Máscara Rangente",  "rarities": _R, "fx": {"furia": 1, "custo_ataque": 1, "atk": 2},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "frente", "art": "mascara_furia"},
                     "req": "chefe1"},
    "calice_rubro": {"name": "Cálice Rubro",       "rarities": ["raro", "epico"], "fx": {"custo_ataque": 1, "atk": 2, "lifesteal": 3},
                     "consume": {"heal": 10}, "look": {"type": "obj", "anchor": "flutua", "art": "calice_rubro"},
                     "req": "andar5"},
    "pacto_carmesim": {"name": "Selo da Gota Rubra", "rarities": ["epico", "lendario"], "fx": {"custo_ataque": 2, "furia": 1, "atk": 2},
                     "consume": {"heal": 12}, "look": {"type": "obj", "anchor": "flutua", "art": "pacto_carmesim"},
                     "req": "chefe1"},
    # batch C: blows (double), area, helpers (always a floating obj) and crit
    "luvinha_ligeira": {"name": "Luvinha Ligeira", "rarities": _C, "fx": {"duplo": 0.15, "crit": 0.05},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "luvinha_ligeira"}},
    "ferrao_gemeo": {"name": "Ferrão Gêmeo",       "rarities": _C, "fx": {"duplo": 0.1, "envenenar": 0.1, "atk": 1},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "ferrao_gemeo"}},
    "rabicho":      {"name": "Rabicho Estalante",  "rarities": _C, "fx": {"duplo": 0.1, "dodge": 0.08},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "esq", "art": "rabicho"}},
    "pulseira_eco": {"name": "Pulseira do Eco",    "rarities": ["raro", "epico"], "fx": {"duplo": 0.12, "crit": 0.05, "maxhp": 3},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "frente", "art": "pulseira_eco"},
                     "req": "andar5"},
    "garras_gemeas": {"name": "Garras Gêmeas da Lua", "rarities": ["lendario"], "fx": {"duplo": 0.15, "crit": 0.1, "atk": 3},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "dir", "art": "garras_gemeas"},
                     "req": "chefe1"},
    "piao_laminas": {"name": "Pião de Lâminas",    "rarities": _C, "fx": {"area": True, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "frente", "art": "piao_laminas"}},
    "corrente_torta": {"name": "Corrente de Elos Tortos", "rarities": _C, "fx": {"area": True, "def": 1, "maxhp": 3},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "esq", "art": "corrente_torta"}},
    "uivo_garrafa": {"name": "Uivo Engarrafado",   "rarities": _C, "fx": {"area": True, "maxhp": 5},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "topo", "art": "uivo_garrafa"}},
    "leque_penas":  {"name": "Leque de Penas Negras", "rarities": _R, "fx": {"area": True, "dodge": 0.08},
                     "consume": {"shield": 8}, "look": {"type": "obj", "anchor": "esq", "art": "leque_penas"},
                     "req": "andar5"},
    "redemoinho":   {"name": "Redemoinho de Bolso", "rarities": ["raro", "epico"], "fx": {"area": True, "dodge": 0.05, "def": 1},
                     "consume": {"heal": 9}, "look": {"type": "tingir", "color": "#9fd8ff", "amount": 0.25},
                     "req": "andar5"},
    "besourinho":   {"name": "Besourinho de Guarda", "rarities": _C, "fx": {"ajudante": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "flutua", "art": "besourinho"}},
    "morceguinho":  {"name": "Morceguinho de Pano", "rarities": _C, "fx": {"ajudante": 1, "maxhp": 5},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "flutua", "art": "morceguinho"}},
    "caveirinha":   {"name": "Caveirinha Saltitante", "rarities": _C, "fx": {"ajudante": 3, "maxhp": -3},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "flutua", "art": "caveirinha"}},
    "fantoche":     {"name": "Fantoche de Meia",   "rarities": ["raro", "epico"], "fx": {"ajudante": 2, "def": 1},
                     "consume": {"shield": 9}, "look": {"type": "obj", "anchor": "flutua", "art": "fantoche"},
                     "req": "andar5"},
    "corvo_cinza":  {"name": "Corvo de Cinza",     "rarities": ["lendario"], "fx": {"ajudante": 3, "maxhp": 4},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "flutua", "art": "corvo_cinza"},
                     "req": "chefe1"},
    "monoculo":     {"name": "Monóculo Trincado",  "rarities": _C, "fx": {"crit": 0.1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "adesivo", "art": "monoculo", "at": [0.3, 0.4]}},
    "pedra_amolar": {"name": "Pedra de Amolar",    "rarities": _C, "fx": {"critdmg": 0.25, "atk": 1, "maxhp": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "esq", "art": "pedra_amolar"}},
    "trevo_murcho": {"name": "Trevo Murcho",       "rarities": _C, "fx": {"crit": 0.15, "atk": 1, "maxhp": 3},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "topo", "art": "trevo_murcho"}},
    "presa_lobo":   {"name": "Presa de Lobo-sombra", "rarities": _R, "fx": {"crit": 0.1, "critdmg": 0.15, "atk": 1},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "dir", "art": "presa_lobo"},
                     "req": "andar5"},
    "olho_gato":    {"name": "Olho de Gato Ônix",  "rarities": ["epico", "lendario"], "fx": {"crit": 0.12, "dodge": 0.08},
                     "consume": {"shield": 12}, "look": {"type": "obj", "anchor": "topo", "art": "olho_gato"},
                     "req": "chefe1"},
    # batch D: growth (grow = kills per +1 ATK), luck (rarity), gold and shop discount
    "dente_leite":  {"name": "Dente de Leite Afiado", "rarities": _C, "fx": {"crescer": 8, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "dente_leite"}},
    "casulo":       {"name": "Casulo Inquieto",    "rarities": _C, "fx": {"crescer": 10, "maxhp": 6, "def": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "esq", "art": "casulo"}},
    "coleira_trofeus": {"name": "Coleira de Troféus", "rarities": _C, "fx": {"crescer": 9, "def": 1, "atk": 1},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "frente", "art": "coleira_trofeus"}},
    "semente_faminta": {"name": "Semente Faminta", "rarities": ["raro", "epico"], "fx": {"crescer": 8, "maxhp": 4, "atk": 1},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "topo", "art": "semente_faminta"},
                     "req": "andar5"},
    "chifre_aneis": {"name": "Chifre de Anéis",    "rarities": ["lendario"], "fx": {"crescer": 5, "atk": 3},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "topo", "art": "chifre_aneis"},
                     "req": "chefe1"},
    "fivela_cacador": {"name": "Fivela do Caçador", "rarities": ["raro", "epico"], "fx": {"crescer": 8, "crit": 0.05, "atk": 1},
                     "consume": {"shield": 9}, "look": {"type": "contorno", "color": "#c99a00"}, "req": "andar10"},
    "moedor_ossos": {"name": "Moedor de Ossos",    "rarities": _R, "fx": {"crescer": 6, "atk": 2, "maxhp": -2},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "dir", "art": "moedor_ossos"},
                     "req": "chefe1"},
    "dado_osso":    {"name": "Dado de Osso",       "rarities": _C, "fx": {"sorte": 0.3, "crit": 0.05, "atk": 2},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "dir", "art": "dado_osso"}},
    "moeda_coroas": {"name": "Moeda de Duas Coroas", "rarities": _C, "fx": {"sorte": 0.25, "gold": 0.15, "atk": 1, "maxhp": 3},
                     "consume": {"shield": 5}, "look": {"type": "obj", "anchor": "esq", "art": "moeda_coroas"}},
    "ferradura":    {"name": "Ferradura Enferrujada", "rarities": _C, "fx": {"sorte": 0.25, "def": 2},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "frente", "art": "ferradura"}},
    "mapa_rabiscado": {"name": "Mapa Rabiscado",   "rarities": _C, "fx": {"sorte": 0.2, "energy": 0.2, "maxhp": 5},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "esq", "art": "mapa_rabiscado"}},
    "talisma_fios": {"name": "Talismã de Três Fios", "rarities": _C, "fx": {"sorte": 0.2, "cura_andar": 4, "maxhp": 3},
                     "consume": {"heal": 7}, "look": {"type": "obj", "anchor": "topo", "art": "talisma_fios"}},
    "estrela_cadente": {"name": "Caco de Estrela Cadente", "rarities": ["raro", "epico"], "fx": {"sorte": 0.35, "maxhp": 5},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "flutua", "art": "estrela_cadente"},
                     "req": "andar5"},
    "bigode_gato":  {"name": "Bigode de Gato Preto", "rarities": ["lendario"], "fx": {"sorte": 0.5, "dodge": 0.1},
                     "consume": {"shield": 12}, "look": {"type": "adesivo", "art": "bigode_gato", "at": [0.5, 0.65]},
                     "req": "chefe1"},
    "bolsa_sapo":   {"name": "Bolsa de Couro de Sapo", "rarities": _C, "fx": {"gold": 0.3, "desconto": 0.1, "def": 1, "maxhp": 3},
                     "consume": {"heal": 6}, "look": {"type": "obj", "anchor": "esq", "art": "bolsa_sapo"}},
    "cupom":        {"name": "Bilhete de Barganha", "rarities": _C, "fx": {"desconto": 0.2, "maxhp": 5},
                     "consume": {"shield": 5}, "look": {"type": "adesivo", "art": "cupom", "at": [0.7, 0.5]}},
    "balanca":      {"name": "Balança Torta",      "rarities": _C, "fx": {"desconto": 0.15, "def": 1, "atk": 1},
                     "consume": {"shield": 6}, "look": {"type": "obj", "anchor": "dir", "art": "balanca"}},
    "dente_ouro":   {"name": "Dente de Ouro",      "rarities": _R, "fx": {"gold": 0.4, "atk": 2},
                     "consume": {"heal": 9}, "look": {"type": "obj", "anchor": "frente", "art": "dente_ouro"},
                     "req": "andar5"},
    "cofrinho":     {"name": "Moringa de Moedas",  "rarities": ["lendario"], "fx": {"gold": 0.5, "desconto": 0.2, "maxhp": 8},
                     "consume": {"heal": 14}, "look": {"type": "obj", "anchor": "flutua", "art": "cofrinho"},
                     "req": "rico"},
    "sanguessuga":  {"name": "Sanguessuga Mansa",  "rarities": _C, "fx": {"lifesteal": 2, "maxhp": 4, "atk": 1},
                     "consume": {"heal": 7}, "look": {"type": "adesivo", "art": "sanguessuga", "at": [0.25, 0.7]}},
}

# sprite, name, health mult., attack mult., min floor, speed mult.
MONSTERS = [
    ("morcego", "Morcego", 0.8, 0.9, 1, 1.4),
    ("rato", "Rato", 1.0, 0.8, 1, 1.1),
    ("aranha", "Aranha", 0.9, 1.2, 2, 1.0),
    ("esqueleto", "Esqueleto", 1.3, 1.0, 3, 0.6),
    ("olho", "Olho Flutuante", 1.0, 1.4, 5, 0.9),
]
BOSS_NAMES = {"morcego": "Morcego Vampiro", "rato": "Rei Rato", "aranha": "Aranha Mãe",
              "esqueleto": "Lorde Esqueleto", "olho": "Olho Abissal"}

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
ELEMENTS = {"fogo": "queimar", "raio": "eletrizar", "veneno": "envenenar", "gelo": "congelar"}
BOSS_ELEMENT = {"morcego": "raio", "rato": "veneno", "aranha": "veneno", "esqueleto": "gelo", "olho": "fogo"}
BOSS_STATUS_CHANCE = 0.15
DOUBLE_CRIT = 0.5              # crit bonus for whoever has twice the target's speed (and critdmg x2)
STATUS_NAME = {"queimar": "queimadura", "eletrizar": "eletricidade", "envenenar": "veneno", "congelar": "congelamento"}
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
    return {"sprite": "mimico", "name": "Mímico", "boss": False, "element": None,
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
        parts.append(t("{v}% esquiva", v=int(fx['dodge'] * 100)))
    if fx.get("gold"):
        parts.append(t("+{v}% ouro", v=int(fx['gold'] * 100)))
    if fx.get("energy"):
        parts.append(t("+{v}% energia", v=int(fx['energy'] * 100)))
    if fx.get("lifesteal"):
        parts.append(t("+{v} HP por vitória", v=fx['lifesteal']))
    if fx.get("trap"):
        parts.append(t("armadilhas x{v}", v=f"{fx['trap']:g}"))
    if fx.get("spd"):
        parts.append(t("{v} velocidade", v=f"{fx['spd']:+g}"))
    if fx.get("crit"):
        parts.append(t("{v}% crítico", v=f"{fx['crit'] * 100:+.0f}"))
    if fx.get("critdmg"):
        parts.append(t("{v}x dano crítico", v=f"{fx['critdmg']:+g}"))
    if fx.get("area"):
        parts.append(t("ataque em área"))
    for el, name in STATUS_NAME.items():
        if fx.get(el):
            parts.append(f"{round(fx[el] * 100)}% {t(name)}")
    if fx.get("bloqueio"):
        parts.append(t("bloqueia {v} golpe" if fx["bloqueio"] == 1 else "bloqueia {v} golpes", v=fx['bloqueio']))
    if fx.get("espinhos"):
        parts.append(t("devolve {v}% do dano", v=round(fx['espinhos'] * 100)))
    if fx.get("cura_sala"):
        parts.append(t("+{v} HP por sala", v=fx['cura_sala']))
    if fx.get("cura_andar"):
        parts.append(t("+{v} HP por andar", v=fx['cura_andar']))
    if fx.get("custo_ataque"):
        parts.append(t("-{v} HP por ataque", v=fx['custo_ataque']))
    if fx.get("furia"):
        parts.append(t("fúria +{v} ATK/10% HP perdido", v=f"{fx['furia']:g}"))
    if fx.get("duplo"):
        parts.append(t("{v}% golpe duplo", v=round(fx['duplo'] * 100)))
    if fx.get("ajudante"):
        parts.append(t("ajudante {v} de dano", v=f"{fx['ajudante']:g}"))
    if fx.get("crescer"):
        parts.append(t("+1 ATK a cada {v} kills", v=fx['crescer']))
    if fx.get("sorte"):
        parts.append(t("+{v}% sorte", v=round(fx['sorte'] * 100)))
    if fx.get("desconto"):
        parts.append(t("-{v}% preço na loja", v=round(fx['desconto'] * 100)))
    return ", ".join(parts)


def new_meta() -> dict:
    return {"achievements": [], "graveyard": [], "runs": 0,
            "best": {"floor": 0, "room": 0}, "next_char": "slime", "chefes": 0}


COUNTERS_ZERO = {"esquivas": 0, "bloqueios": 0, "mortes_veneno": 0, "mortes_queima": 0, "horda4": 0}


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
        "traco": dict(trait or {}),
        "cont": dict(COUNTERS_ZERO),
        "items": [], "consumed": [], "shield": 0, "pending": None,
        "gold": 0, "energy": 0.0, "kills": 0, "bosses": 0,
        "started": date.today().isoformat(), "dead": False,
    }


def _scale(fx: dict, rar: str) -> dict:
    """Multiplies the positive values by the rarity; negatives, trap, area and attack_cost stay the same."""
    m = RAR_MULT[rar]
    out = {}
    for k, v in fx.items():
        if k in ("trap", "area", "custo_ataque") or v <= 0:
            out[k] = v
        elif k == "crescer":                          # fewer kills per point = better: scales down, floor of 3
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
        run["items"] = [{"key": items[s], "rar": "comum"} for s in ("mao", "escudo", "cabeca")
                        if items.get(s) in ITEMS]
    else:
        run["items"] = [i for i in (items or []) if isinstance(i, dict) and i.get("key") in ITEMS]
    for i in run["items"]:
        i.setdefault("floor", None)
        i.setdefault("kills0", 0)
    run.setdefault("consumed", [])
    run.setdefault("shield", 0)
    run.setdefault("traco", {})
    cont = run.setdefault("cont", {})
    for k, v in COUNTERS_ZERO.items():
        cont.setdefault(k, v)
    b = run.setdefault("base", {})
    b.setdefault("spd", PET_SPD)
    # old saves froze the pet defaults (0.10 and 1.5) in the base: without them, the current constants apply
    if b.get("crit") == 0.10:
        del b["crit"]
    if b.get("critdmg") == 1.5:
        del b["critdmg"]
    if (run.get("pending") or {}).get("key") not in ITEMS:
        run["pending"] = None
    return run


def stats(run: dict) -> dict:
    b = run["base"]
    st = {"maxhp": b["maxhp"], "atk": b["atk"], "def": b["def"], "dodge": b["dodge"],
          "gold": 0.0, "trap": 1.0, "energy": 0.0, "lifesteal": 0,
          "spd": b.get("spd", PET_SPD), "crit": b.get("crit", PET_CRIT), "critdmg": b.get("critdmg", PET_CRITDMG),
          "area": False, "queimar": 0.0, "eletrizar": 0.0, "envenenar": 0.0, "congelar": 0.0,
          "bloqueio": 0, "espinhos": 0.0, "cura_sala": 0, "cura_andar": 0, "custo_ataque": 0, "furia": 0,
          "duplo": 0.0, "ajudante": 0, "sorte": 0.0, "desconto": 0.0}
    # the hero trait adds up like an item, but without rarity scaling
    for kills0, fx in [(0, run.get("traco", {}))] + [(it.get("kills0", 0), item_fx(it["key"], it["rar"]))
                                                      for it in run["items"]]:
        for k, v in fx.items():
            if k == "crescer":                        # +1 ATK every v kills made after taking the item
                st["atk"] += max(0, run["kills"] - kills0) // v
            elif k == "trap":
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
    for el in ELEMENTS.values():
        st[el] = min(MAX_ELEM_CHANCE, st[el])
    st["trap"] = min(TRAP_LIMITS[1], max(TRAP_LIMITS[0], st["trap"]))
    st["bloqueio"] = min(MAX_BLOCK, int(st["bloqueio"]))
    st["espinhos"] = min(MAX_THORNS, st["espinhos"])
    st["duplo"] = min(MAX_DOUBLE, st["duplo"])
    st["sorte"] = min(MAX_LUCK, st["sorte"])
    st["desconto"] = min(MAX_DISCOUNT, st["desconto"])
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
    if run.get("pending"):
        taken.add(run["pending"]["key"])
    pool = [k for k in unlocked_items(meta) if k not in taken]
    if not pool:
        return None
    lo = 1 if best else 0
    w = _rarity_weights(run["floor"])
    luck = 1 + stats(run)["sorte"]
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
    return max(1, round((SHOP_PRICE[0] + SHOP_PRICE[1] * f) * (1 - stats(run)["desconto"])))


def auto_choice(run: dict, offer: dict) -> str:
    """Automatic rule: consumes if it is a heal and HP is below 40%; otherwise takes it."""
    if "heal" in ITEMS[offer["key"]]["consume"] and run["hp"] < 0.4 * stats(run)["maxhp"]:
        return "consumir"
    return "pegar"


def resolve_offer(run: dict, offer: dict, choice: str, ev: dict) -> None:
    """Applies the choice. Achievements are left to the caller (enter_room / *_pending)."""
    item = {"key": offer["key"], "rar": offer["rar"]}      # without the floor: this is what the event (GUI) receives
    if choice == "pegar":
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


def choose_pending(run: dict, meta: dict, choice: str) -> dict:
    """Resolves the pending offer with the player's choice ("take" or "consume")."""
    ev: dict = {"lines": []}
    offer, run["pending"] = run.get("pending"), None
    if offer:
        resolve_offer(run, offer, choice, ev)
        _check_achievements(run, meta, ev)
    return ev


def resolve_pending(run: dict, meta: dict) -> dict:
    """Resolves the pending offer with the automatic rule."""
    if not run.get("pending"):
        return {"lines": []}
    return choose_pending(run, meta, auto_choice(run, run["pending"]))


def apply_damage(run: dict, d: int) -> int:
    """The shield absorbs first; returns the damage that reached HP."""
    absorbed = min(run["shield"], d)
    run["shield"] -= absorbed
    run["hp"] -= d - absorbed
    return d - absorbed


def _apply_status(s: dict, name: str) -> None:
    """Puts the status on s. Burn renews; poison gains a stack (at the cap, renews the oldest)."""
    if name == "veneno":
        v = s.setdefault("veneno", [])
        if len(v) < POISON_MAX_STACKS:
            v.append(0)
        else:
            v[v.index(max(v))] = 0
    else:
        s[name] = {"queimadura": BURN_TURNS, "eletricidade": SHOCK_TURNS, "congelamento": FREEZE_TURNS}[name]


def _status_damage(s: dict, f: int) -> list[tuple[str, int]]:
    """Start-of-round tick: [(name, damage)] and already decrements the duration."""
    out = []
    if s.get("queimadura"):
        s["queimadura"] -= 1
        out.append(("queimadura", round(BURN[0] + BURN[1] * f)))
    if s.get("veneno"):
        v = [t + 1 for t in s["veneno"]]                # each stack deals 1, 2, 3, 4 damage
        out.append(("veneno", sum(v)))
        s["veneno"] = [t for t in v if t < POISON_TURNS]
    return out


def combate(run: dict, st: dict, foes: list[dict], rng: random.Random, f: int):
    """Round-based fight. Returns (won, steps, killer, tie); mutates run["hp"] and the enemies' hp/status.

    Without `area` the pet hits the living enemy with the lowest HP; with `area`, one step per living target.
    `double`: chance of a 2nd hit on the same target (step with double=True). With `helper` > 0, the "helper"
    participant acts once per round (pet's spd, right after it) on the living enemy with the lowest HP; it is never a target.
    tie: the fight hit the MAX_ROUNDS limit (the pet survives, but the room gives no reward).
    """
    steps = []
    pst: dict = {}                                       # pet status (only during the fight)

    charges = st["bloqueio"]                              # enemy hits the pet cancels in this fight

    def step(who, target, dmg=0, crit=False, status=None, skip=False, dot=False, dodge=False,
              locked=False, thorns=False, double=False):
        steps.append({"who": who, "target": target, "dmg": dmg, "crit": crit, "status": status, "skip": skip,
                       "dot": dot, "dodge": dodge, "bloqueado": locked, "espinhos": thorns, "duplo": double})

    def alive():
        return [i for i, x in enumerate(foes) if x["hp"] > 0]

    def skips_turn(s):
        lost = False
        if s.get("congelamento"):
            s["congelamento"] -= 1
            if rng.random() < FREEZE_CHANCE:
                lost, s["congelamento"] = True, 0
        if s.get("eletricidade"):
            s["eletricidade"] -= 1
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
        ajud = [("ajudante", st["spd"])] if st["ajudante"] > 0 else []
        order = sorted([("pet", st["spd"])] + ajud + [(i, foes[i]["spd"]) for i in alive()], key=lambda x: -x[1])
        for who, _spd in order:
            if who not in ("pet", "ajudante") and foes[who]["hp"] <= 0:
                continue
            if who == "ajudante":                          # no status, crit or skipped turn
                i = min(alive(), key=lambda i: foes[i]["hp"])
                d = max(1, round(st["ajudante"]))      # never 0 damage
                foes[i]["hp"] -= d
                step("ajudante", i, d)
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
                atk = st["atk"] + st["furia"] * ((st["maxhp"] - run["hp"]) * 10 // st["maxhp"])
                if st["custo_ataque"]:                     # blood: attacking costs HP, but never below 1
                    run["hp"] = max(1, run["hp"] - st["custo_ataque"])
                for i in targets:
                    x = foes[i]
                    # 2nd hit (double): rolled per target, only if the target survived; no double-speed bonus
                    for dup in (False, True):
                        if dup and (x["hp"] <= 0 or not st["duplo"] or rng.random() >= st["duplo"]):
                            break
                        e_crit, mult = critical(st["crit"], st["critdmg"], 0 if dup else st["spd"], x["spd"])
                        d = round(max(1, atk + rng.randint(-1, 1)) * mult)
                        x["hp"] -= d
                        applied = None
                        if x["hp"] > 0:
                            for el, name in STATUS_NAME.items():      # each element rolls separately
                                if st[el] and rng.random() < st[el]:
                                    _apply_status(x["status"], name)
                                    applied = applied or name
                        step("pet", i, d, e_crit, applied, double=dup)
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
                returns = round(raw * st["espinhos"])      # thorns: fraction of the damage before the shield
                if returns:
                    x["hp"] -= returns
                    step("pet", who, returns, thorns=True)
                    if not alive():
                        return True, steps, "", False
    return True, steps, "", True                        # safety limit: tie, no reward


def _count(run: dict, steps: list[dict], foes: list[dict], horde4: bool) -> None:
    """Achievement counters from the fight steps. Death by status: the enemy crosses hp 0 on a dot step."""
    c = run.setdefault("cont", dict(COUNTERS_ZERO))
    hp = [x["hp_max"] for x in foes]
    for p in steps:
        if p["dodge"]:
            c["esquivas"] += 1
        if p["bloqueado"]:
            c["bloqueios"] += 1
        i = p["target"]
        if isinstance(i, int) and (p["who"] in ("pet", "ajudante") or p["dot"]):
            before, hp[i] = hp[i], hp[i] - p["dmg"]
            if p["dot"] and before > 0 >= hp[i]:
                c["mortes_veneno" if p["status"] == "veneno" else "mortes_queima"] += 1
    if horde4:
        c["horda4"] += 1


def die(run: dict, meta: dict, ev: dict, killer: str, kind: str = "monster") -> None:
    """kind: monster|horde|boss|mimic|trap|gave_up; death by Burn/Poison becomes "status"."""
    if killer in ("Queimadura", "Veneno"):
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
    cont = run.get("cont", {})
    grant("veneno1", cont.get("mortes_veneno", 0) >= 1)
    grant("ouro300", run["gold"] >= 300)
    grant("horda4", cont.get("horda4", 0) >= 1)
    grant("queima1", cont.get("mortes_queima", 0) >= 1)
    grant("esquiva10", cont.get("esquivas", 0) >= 10)
    grant("andar15", run["floor"] >= 15)
    grant("bloqueio10", cont.get("bloqueios", 0) >= 10)
    grant("chefes3", meta.get("chefes", 0) >= 3)
    grant("consumir10", len(run.get("consumed", [])) >= 10)
    grant("morrer10", meta["runs"] >= 10)
    grant("sem_consumir10", run["floor"] >= 10 and not run.get("consumed"))
    grant("lendarios3", sum(1 for it in run["items"] if it["rar"] == "lendario") >= 3)
    grant("ajudantes3", sum(1 for it in run["items"] if "ajudante" in ITEMS[it["key"]]["fx"]) >= 3)
    grant("veneno3", cont.get("mortes_veneno", 0) >= 3)
    grant("chefes3run", run["bosses"] >= 3)
    grant("andar13", run.get("dead") and run["floor"] == 13)
    if run["floor"] >= 8 and "andar8cheio" not in have:
        grant("andar8cheio", run["hp"] >= stats(run)["maxhp"])
    if "elementos3" not in have:
        elem = set(ELEMENTS.values())
        grant("elementos3", sum(1 for it in run["items"] if elem & set(ITEMS[it["key"]]["fx"])) >= 3)
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
        ev["cura_item"] = run["hp"] - hp


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
        st = stats(run)
        _heal_by_item(run, ev, st["maxhp"], run["hp"], st["cura_andar"])
        return ev

    run["room"] += 1
    # regenerates every room (+ heal_room)
    _heal_by_item(run, ev, st["maxhp"], min(st["maxhp"], run["hp"] + REGEN_PER_ROOM), st["cura_sala"])

    if run["room"] == ROOMS_PER_FLOOR and f % BOSS_EVERY == 0:
        kind = "boss"
    else:
        weights = [(k, w) for k, w in ROOM_WEIGHTS if k != "horde" or f >= HORDE_MIN_FLOOR]
        kind = rng.choices([k for k, _ in weights], [w for _, w in weights])[0]
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
        ev["name"] = f"Horda ({len(foes)})" if kind == "horde" else foes[0]["name"]
        ev["foes"] = [{k: x[k] for k in ("sprite", "name", "boss", "element", "hp_max")} for x in foes]
        hp_before = run["hp"]
        won, ev["hits"], killer, tie = combate(run, st, foes, rng, f)
        ev["dmg"] = hp_before - run["hp"]
        _count(run, ev["hits"], foes, kind == "horde" and len(foes) == 4 and won and not tie)
        if not won:
            die(run, meta, ev, killer, kind)
            return ev
        if tie:                            # cleared the room, but without gold, kills, boss bonus or item
            ev["empate"] = True
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
            meta["chefes"] = meta.get("chefes", 0) + 1
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
        else:                                  # only happens if CHEST_ITEM_CHANCE < 1
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
        potion, item_price = 6 + f, shop_price(run, f)
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


# Bump when a combat formula/rule or a number written straight in the code changes (the hash below does not see that).
RULES_REV = 8


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
            MAX_ROUNDS, HORDE_MIN_FLOOR, HORDE_MULT, HORDE_GOLD_MULT]
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
        "achievements": list(achievements),
    }
