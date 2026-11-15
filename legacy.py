# -*- coding: utf-8 -*-
"""Saves from the Portuguese-named versions (before the English rename) -> current keys.

`migrate_state` converts state.json once (keys and values: items, heroes, achievements, rarities, modes,
window names...); texts that were saved for display (graveyard killer names, hero names, sizes) go through
`i18n.legacy_en`. `migrate_runs` rewrites runs.jsonl the same way. A copy of the old file is kept (.pt.bak)."""
import json
import shutil
from pathlib import Path

import i18n

DATA_VERSION = 2          # 1 = Portuguese keys (no "data_version" in the save)

KEYS = {
    "virar": "flip",
    "aberta": "open", "adaga": "dagger", "adaga_sangria": "bleeding_dagger", "adesivo": "sticker",
    "ajudante": "helper", "ajudantes3": "helpers3", "alquimista": "alchemist", "andar10": "floor10",
    "andar13": "floor13", "andar15": "floor15", "andar20": "floor20", "andar5": "floor5",
    "andar8cheio": "floor8full", "andar_final": "final_floor", "andar_pego": "taken_floor", "antena": "antenna",
    "apagado": "unlit", "aranha": "spider", "armadilha": "trap", "armadura_farpas": "barbed_armor", "aura": "aura",
    "aureola": "halo", "baba": "slobber", "bafo_gelido": "icy_breath", "baixo": "down", "balanca": "scale",
    "bau": "chest", "besourinho": "beetle", "bico": "beak", "bigode_gato": "cat_whiskers", "bloqueado": "locked",
    "bloqueados": "locked", "bloqueio": "block", "bloqueio10": "block10", "bloqueios": "blocks",
    "bolsa_sapo": "frog_pouch", "boneca": "doll", "brasa": "ember", "bravo": "angry", "broquel": "buckler",
    "bruxa": "witch", "buu": "boo", "buu_g": "boo_l", "cachecol": "scarf", "cacto_mal": "grumpy_cactus",
    "cadeado": "padlock", "caixa": "box", "caixa_ok": "box_ok", "cajado": "staff", "calibracao": "calibration",
    "calice_rubro": "ruby_chalice", "carapaca": "carapace", "casca_geada": "frost_bark",
    "casco_tartaruga": "turtle_shell", "casulo": "cocoon", "cavaleiro": "knight", "caveirinha": "little_skull",
    "ceifeirinho": "reaper", "cemi_win": "grave_win", "chamas": "flames", "chao": "ground", "chapeu": "hat",
    "chazinho": "little_tea", "chefe1": "boss1", "chefes": "bosses", "chefes3": "bosses3",
    "chefes3run": "bosses3run", "chifre_aneis": "ringed_horn", "chifres": "horns", "cima": "up",
    "cofrinho": "piggy_bank", "cogumelo": "mushroom", "colar_presas": "fang_necklace", "colecionador": "collector",
    "coleira_trofeus": "trophy_collar", "com_conquistas": "with_achievements", "comum": "common",
    "congelamento": "freeze", "congelar": "freeze", "conq_win": "ach_win", "consumido": "consumed_pct",
    "consumido_por_modo": "consumed_by_mode", "consumir": "consume", "consumir10": "consume10", "cont": "counters",
    "contorno": "outline", "coracao_costurado": "stitched_heart", "coracao_magma": "magma_heart",
    "coroa_cinzas": "ash_crown", "corrente_torta": "bent_chain", "corvo": "crow", "corvo_cinza": "grey_crow",
    "coveiro": "gravedigger", "crescer": "grow", "cupom": "coupon", "cura_andar": "heal_floor",
    "cura_item": "item_heal", "cura_sala": "heal_room", "custo_ataque": "attack_cost", "dado_osso": "bone_die",
    "dedo": "finger", "dente_leite": "milk_tooth", "dente_ouro": "gold_tooth", "dente_sapo": "frog_tooth",
    "dentes": "teeth", "desconto": "discount", "desistencias": "gave_ups", "desistiu": "gave_up", "dir": "right",
    "duplo": "double", "durou": "lasted", "elementos3": "elements3", "eletricidade": "shock", "eletrizar": "shock",
    "empate": "tie", "envenenar": "poison", "epico": "epic", "erro": "error", "escada": "stairs",
    "escudo_ferro": "iron_shield", "espada_osso": "bone_sword", "espantalho": "scarecrow",
    "espelho_rachado": "cracked_mirror", "espinhos": "thorns", "esq": "left", "esqueleto": "skeleton",
    "esquiva10": "dodge10", "esquivas": "dodges", "estado": "state", "estados": "states", "estilhaco": "ice_shard",
    "estrela_cadente": "shooting_star", "faiscas": "sparks", "fantasma": "ghost", "fantoche": "puppet",
    "fechada": "closed", "fechado": "closed", "feliz": "happy", "ferradura": "horseshoe",
    "ferrao_gemeo": "twin_stinger", "fivela_cacador": "hunter_buckle", "floco_eterno": "eternal_flake",
    "flutua": "float", "fogo": "fire", "fogo_fatuo": "wisp", "foice": "scythe", "fonte": "fountain",
    "fonte_bolso": "pocket_spring", "fora": "out", "freira": "nun", "frente": "front", "fumaca": "smoke",
    "fumaca2": "smoke2", "furia": "fury", "ganho": "gain", "garras_gemeas": "twin_claws", "gato": "cat",
    "geada": "frost", "gelo": "ice", "gerado_em": "generated_at", "gorro": "beanie", "gotas": "drops",
    "gotas_veneno": "poison_drops", "grimorio": "grimoire", "grito": "scream", "herois": "heroes",
    "horda4": "horde4", "ignoradas": "ignored", "incensario": "censer", "info_real": "real_info",
    "inquisidor": "inquisitor", "interativo": "interactive", "itens": "items", "itens_med": "items_median",
    "itens_win": "items_win", "janelas": "windows", "jogadas": "played", "lamparina_lar": "hearth_lamp",
    "lanterna": "lantern", "lapide": "tombstone", "lendario": "legendary", "lendarios3": "legendaries3",
    "leque_penas": "feather_fan", "liberados": "unlocked", "limao_eletrico": "electric_lemon", "lodo": "sludge",
    "loja": "shop", "luvinha_ligeira": "swift_glove", "manopla_rebite": "riveted_gauntlet",
    "mapa_rabiscado": "scribbled_map", "mariposa": "moth", "mascara_furia": "fury_mask", "matadores": "killers",
    "mediana": "median", "medico": "doctor", "meio": "middle", "melhores": "best_items", "metas": "targets",
    "mimico": "mimic", "modos": "modes", "moeda_coroas": "crown_coin", "moedor_ossos": "bone_grinder",
    "monoculo": "monocle", "morcego": "bat", "morceguinho": "little_bat", "morrer10": "die10", "mortes": "deaths",
    "mortes_queima": "burn_kills", "mortes_rapidas": "quick_deaths", "mortes_veneno": "poison_kills",
    "muralha_viva": "living_wall", "musgo": "moss", "nuvem_raivosa": "angry_cloud", "olho": "eye",
    "olho_gato": "cat_eye", "orbe": "orb", "ourico": "burr", "ouro300": "gold300",
    "outras_versoes": "other_versions", "pacto_carmesim": "crimson_pact", "para_raios": "lightning_rod",
    "pares": "pairs", "passou_chefe1": "passed_boss1", "pedra_amolar": "whetstone", "pegar": "take", "pego": "taken",
    "pelagem_chamuscada": "singed_fur", "pelo_estatico": "static_fur", "perfil_win": "profile_win",
    "piao_laminas": "blade_top", "pico": "peak", "piores": "worst_items", "pocao": "potion", "polvo": "octopus",
    "por_andar": "per_floor", "por_tipo": "per_kind", "presa_lobo": "wolf_fang", "pulseira_eco": "echo_bracelet",
    "queima1": "burn1", "queimadura": "burn", "queimar": "burn", "rabicho": "pigtail", "raio": "lightning",
    "raiz_teimosa": "stubborn_root", "raridades": "rarities", "raro": "rare", "rato": "rat",
    "redemoinho": "whirlwind", "reta": "straight", "rico": "rich", "sanguessuga": "leech", "sapo": "frog",
    "seiva_antiga": "ancient_sap", "sem_conquistas": "without_achievements", "sem_consumir10": "no_consume10",
    "semana": "week", "semente_faminta": "hungry_seed", "sessao": "session",
    "sim_sem_conquistas": "sim_without_achievements", "sino_guarda": "guard_bell", "so_com_uso": "only_when_used",
    "sorriso": "smile", "sorte": "luck", "talisma_fios": "thread_talisman", "tampa": "pot_lid",
    "terceiro_olho": "third_eye", "tingir": "tint", "tocha": "torch", "todos": "all", "topo": "top",
    "torta": "crooked", "traco": "trait", "trevo_murcho": "wilted_clover", "triste": "sad",
    "uivo_garrafa": "bottled_howl", "usage_hist_desde": "usage_hist_since", "vela": "candle", "veneno": "poison",
    "veneno1": "poison1", "veneno3": "poison3", "versao": "version", "voar": "fly", "volta": "back",
    "vs_esperado": "vs_expected", "vs_media": "vs_mean",
}


def _conv(x):
    if isinstance(x, dict):
        return {KEYS.get(k, k) if isinstance(k, str) else k: _conv(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_conv(v) for v in x]
    if isinstance(x, str):
        return KEYS.get(x) or i18n.legacy_en(x)
    return x


def migrate_state(state: dict) -> dict:
    """Old save (no data_version) -> current keys. Saves already migrated come back unchanged."""
    if state.get("data_version", 1) >= DATA_VERSION:
        return state
    new = _conv(state)
    new["data_version"] = DATA_VERSION
    return new


def migrate_file(path: Path, lines: bool = False) -> bool:
    """Converts state.json (or runs.jsonl with lines=True) in place, keeping <name>.pt.bak. True if it changed."""
    bak = path.with_name(path.name + ".pt.bak")
    if not path.exists() or bak.exists():
        return False
    txt = path.read_text(encoding="utf-8")
    try:
        if lines:
            recs = [json.loads(l) for l in txt.splitlines() if l.strip()]
            if all(r.get("data_version", 1) >= DATA_VERSION for r in recs):
                return False
            out = "".join(json.dumps(dict(_conv(r), data_version=DATA_VERSION), ensure_ascii=False) + "\n" for r in recs)
        else:
            st = json.loads(txt)
            if st.get("data_version", 1) >= DATA_VERSION:
                return False
            out = json.dumps(migrate_state(st), ensure_ascii=False)
    except (ValueError, AttributeError):
        return False
    shutil.copy2(path, bak)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(out, encoding="utf-8")
    tmp.replace(path)
    return True


def migrate_all(data_dir: Path) -> list[str]:
    """Once, when state.json (or state-demo.json) is from a Portuguese-named version: converts it and its runs file."""
    done = []
    for state, runs in (("state.json", "runs.jsonl"), ("state-demo.json", "runs-demo.jsonl")):
        p = Path(data_dir) / state
        try:
            old = p.exists() and json.loads(p.read_text(encoding="utf-8")).get("data_version", 1) < DATA_VERSION
        except (OSError, ValueError, AttributeError):
            old = False
        if old:
            done += [n for n, lines in ((state, False), (runs, True)) if migrate_file(Path(data_dir) / n, lines)]
    return done
