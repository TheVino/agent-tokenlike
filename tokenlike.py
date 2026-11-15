#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Tokenlike - Masmorra de Tokens

Um bichinho de pixel que fica na sua tela e desce uma masmorra usando como
energia os tokens que você gasta no Claude Code. Salas aleatórias, itens que
aparecem no visual, chefes, desbloqueios e permadeath.

Privacidade:
  * Lê os arquivos de log que o Claude Code já salva no seu PC
    (%USERPROFILE%\\.claude\\projects\\*.jsonl) e usa SÓ os números de tokens.
  * Não guarda nem mostra prompts/respostas, não usa internet, não instala
    hooks e não mexe em nenhuma configuração do Claude Code.
  * O progresso fica em %USERPROFILE%\\.tokenlike\\

Uso:
  python tokenlike.py                   abre o pet
  python tokenlike.py --demo            modo teste (tokens falsos, progresso separado)
  python tokenlike.py --import-history  no 1º uso, já começa com a energia do histórico
  python tokenlike.py --reset           apaga todo o progresso (runs, cemitério, conquistas)
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import random
import shutil
import struct
import sys
import threading
import time
import traceback
import zlib
from collections import Counter, deque
from functools import lru_cache
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import art  # noqa: E402
from heroes import assemble as _assemble, slime as _slime  # noqa: E402
import sheet  # noqa: E402
import dungeon as M  # noqa: E402
import i18n  # noqa: E402
_t = i18n.t   # texto no idioma atual (todo texto visível passa por aqui)
import visual  # noqa: E402

tk = None  # o tkinter é importado só quando a janela abre (run_gui)

APP_NAME = "Agent Tokenlike"
DATA_DIR = Path.home() / ".tokenlike"
OLD_DATA_DIR = Path.home() / ".tokenpet"  # nome antigo (TokenPet)
CHARACTERS_DIR = SCRIPT_DIR / "characters"
LOG_FILE = DATA_DIR / "tokenlike.log"

# ----------------------------------------------------------------- ajustes
CACHE_READ_WEIGHT = 0.1     # tokens lidos do cache valem 10% (são baratos e muitos)
POLL_MS = 2500              # de quanto em quanto tempo olha os logs
REST_AFTER_S = 5 * 60       # parado há 5 min -> descansa e recupera 1 HP a cada 2 min
SLEEP_AFTER_S = 10 * 60     # parado há 10 min -> dorme (Zzz). Nunca morre por ficar parado.
HIDE_S = 5 * 60         # "Aparecer só com uso": some depois disso sem tokens novos (continua rodando escondido)
SAVE_EVERY_S = 30
RESPAWN_S = 12              # tempo mostrando a lápide antes da run nova
SIZES = {"Pequeno": 4, "Médio": 6, "Grande": 8}  # px de tela por pixel da arte
MODES = {"auto": "Auto", "interativo": "Interativo"}
CHOICE_BAR_W = 150          # largura da barrinha de tempo do painel de escolha
TRANSPARENT = "#ff00fe"     # cor "chave" que o Windows deixa invisível

PANEL_BG = "#1d1b2b"
PANEL_EDGE = "#4b4680"
TEXT = "#f2f0ff"
MUTED = "#a9a4d6"
BAR_BG = "#35315a"
ENERGY = "#5fd3c6"
ENERGY_SHIMMER = "#c8f5ef"     # brilho que corre pela barra de energia
SHIMMER_S = 2.4                # segundos por passada do brilho
PEAK_COLOR = "#8f88d6"          # barra de limite sem % oficial: uso da janela / seu pico (neutra, não é alerta)
GOOD = "#7ee081"
HURT = "#ff6b81"
GOLD = "#ffd23f"
CYAN = "#6fd6ff"
STATUS_COLOR = {"queimadura": "#ff9f43", "eletricidade": "#fff27a", "veneno": "#4fbf5a", "congelamento": "#9fe8ff"}
MENU_HOVER = "#2e2a48"      # fundo da linha do menu com o mouse em cima
GOLD_HOVER = "#fff27a"      # polegar da barra de rolagem com o mouse em cima
CARD_BG = "#262338"         # miolo dos cartões (um pouco mais claro que o painel)
WINDOW_R, CARD_R = 8, 4   # raio dos cantos em degraus: janelas/painel e cartões/chips
CARD_PAD = 6              # respiro mínimo entre a borda do cartão e o que vai dentro
HERO_COLS, HERO_CARD_W, HERO_CARD_H = 5, 128, 160   # grade de heróis (cards de tamanho fixo)
ACH_COLS, ACH_CARD_W, ACH_CARD_H = 4, 150, 118   # grade de conquistas
GRAVE_W, GRAVE_H, GRAVE_TOMB = 470, 420, 92           # cemitério: largura, altura visível, altura de cada lápide
ITEMS_COLS, ITEMS_CARD_W, ITEMS_H = 2, 280, 440      # página de itens: colunas, largura do card, altura visível
WINDOW_ATTRS = ("menu_win", "heroes_win", "stats_win", "ach_win", "grave_win", "items_win", "profile_win")
REOPEN = {"heroes_win": "show_heroes", "stats_win": "show_stats", "ach_win": "show_achievements",
          "grave_win": "show_graveyard", "items_win": "show_items", "profile_win": "show_perfil"}   # troca de idioma

PROFILE_W, PROFILE_MEDALS, PROFILE_MEDAL, PROFILE_BAR = 312, 13, 24, "#8a5a2b"   # perfil: largura, medalhas/linha, célula, cor
FX_MS = 200   # ms por fase da animação dos looks elementais (relógio próprio, separado do frame_ms do herói)


def fmt(n: float) -> str:
    n = float(n)
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            s = f"{n / div:.1f}"
            return (s[:-2] if s.endswith(".0") else s) + unit
    return str(int(n))


def log(msg: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def append_run_record(rec: dict, demo: bool) -> None:
    """Acrescenta uma run terminada em runs.jsonl (só dados do jogo; falha só loga)."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / ("runs-demo.jsonl" if demo else "runs.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        log(f"não gravou runs.jsonl: {e}")


# ------------------------------------------------------- leitura de tokens
def claude_project_dirs() -> list[Path]:
    cands: list[Path] = []
    for part in os.environ.get("CLAUDE_CONFIG_DIR", "").split(","):
        if part.strip():
            cands.append(Path(part.strip()).expanduser() / "projects")
    cands.append(Path.home() / ".claude" / "projects")
    cands.append(Path.home() / ".config" / "claude" / "projects")
    out, seen = [], set()
    for c in cands:
        try:
            key = str(c.resolve())
        except OSError:
            continue
        if key not in seen and c.is_dir():
            seen.add(key)
            out.append(c)
    return out


class TokenReader:
    """Lê só as linhas novas dos .jsonl do Claude Code e soma o uso de tokens."""

    FILE_LIST_REFRESH_S = 10

    def __init__(self, state: dict, dirs: list[Path] | None = None):
        self.state = state
        self.dirs = dirs
        self.offsets: dict = state.setdefault("offsets", {})
        self.seen = deque(state.get("seen", []), maxlen=6000)
        self.seen_set = set(self.seen)
        self._files: list[Path] = []
        self._files_at = 0.0

    def files(self) -> list[Path]:
        now = time.time()
        if now - self._files_at > self.FILE_LIST_REFRESH_S:
            found = []
            for d in (self.dirs if self.dirs is not None else claude_project_dirs()):
                try:
                    found.extend(p for p in d.rglob("*.jsonl") if p.is_file())
                except OSError:
                    pass
            self._files, self._files_at = found, now
        return self._files

    def skip_existing(self) -> None:
        """Marca tudo que já existe como lido (o pet nasce do zero)."""
        self._files_at = 0
        for f in self.files():
            try:
                self.offsets[str(f)] = f.stat().st_size
            except OSError:
                pass

    def poll(self) -> tuple[float, int]:
        """Retorna (xp_ganho, tokens_brutos) desde a última leitura."""
        xp, raw = 0.0, 0
        for f in self.files():
            key = str(f)
            try:
                size = f.stat().st_size
            except OSError:
                continue
            off = self.offsets.get(key, 0)
            if size < off:          # arquivo foi recriado/encurtado
                off = 0
            if size == off:
                continue
            try:
                with open(f, "rb") as fh:
                    fh.seek(off)
                    data = fh.read(size - off)
            except OSError:
                continue
            end = data.rfind(b"\n")
            if end < 0:             # linha ainda sendo escrita
                continue
            self.offsets[key] = off + end + 1
            for line in data[:end].splitlines():
                got = self.parse_line(line)
                if got:
                    xp += got[0]
                    raw += got[1]
                    if got[2] is not None:      # sem horário: conta como energia, mas não nas barras
                        add_usage(self.state, got[2], got[0])
        prune_usage(self.state, time.time())
        return xp, raw

    def backfill(self) -> None:
        """Uma vez: preenche o histórico por horário com o que já foi lido (até o offset de cada arquivo,
        dos últimos 8 dias). Não dá energia nem mexe no `seen`."""
        hist = self.state.setdefault("usage_hist", {})
        seen = set()
        self._files_at = 0
        cutoff = time.time() - HIST_KEEP_S
        for f in self.files():
            off = self.offsets.get(str(f), 0)
            try:
                if not off or f.stat().st_mtime < cutoff:
                    continue
                with open(f, "rb") as fh:
                    data = fh.read(off)
            except OSError:
                continue
            for line in data.splitlines():
                got = self.parse_line(line, seen)
                if got and got[2] is not None:
                    add_usage(self.state, got[2], got[0])
        self.state["usage_hist"] = hist
        self.state["usage_hist_desde"] = cutoff         # o histórico cobre os últimos 8 dias
        prune_usage(self.state, time.time())

    def parse_line(self, line: bytes, seen: set | None = None):
        if b'"usage"' not in line:
            return None
        try:
            obj = json.loads(line)
        except ValueError:
            return None
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            return None
        msg = obj.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
            return None
        # o Claude Code grava a mesma resposta em várias linhas: conta só uma vez
        if msg.get("id") and seen is not None:      # backfill: dedup local, sem tocar no `seen`
            key = f'{msg.get("id")}:{obj.get("requestId")}'
            if key in seen:
                return None
            seen.add(key)
        elif msg.get("id"):
            key = f'{msg.get("id")}:{obj.get("requestId")}'
            if key in self.seen_set:
                return None
            if len(self.seen) == self.seen.maxlen:
                self.seen_set.discard(self.seen[0])
            self.seen.append(key)
            self.seen_set.add(key)
        usage = msg["usage"]

        def num(k):
            v = usage.get(k) or 0
            return v if isinstance(v, (int, float)) else 0

        inp, out = num("input_tokens"), num("output_tokens")
        cc, cr = num("cache_creation_input_tokens"), num("cache_read_input_tokens")
        raw = int(inp + out + cc + cr)
        if raw <= 0:
            return None
        return inp + out + cc + cr * CACHE_READ_WEIGHT, raw, parse_ts(obj.get("timestamp"))

    def export(self) -> None:
        self.state["seen"] = list(self.seen)


def parse_ts(v) -> float | None:
    """Horário ISO (UTC) da resposta -> epoch. Só o horário, nada de conteúdo."""
    if not isinstance(v, str):
        return None
    try:
        t = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.timestamp()


# ------------------------------------------------- histórico e estimativa dos limites
BUCKET_S = 300                      # baldes de 5 min com o XP ponderado
HIST_KEEP_S = 8 * 86400             # guarda só os últimos 8 dias
WINDOWS = {"sessao": 5 * 3600, "semana": 7 * 86400}
OFFICIAL_FRESH_S = 600              # leitura oficial vale por ~10 min sem "~"
MIN_CALIB_XP = 1000                 # com quase nada de tokens locais, o fator não presta


def add_usage(state: dict, ts: float, xp: float) -> None:
    hist = state.setdefault("usage_hist", {})
    k = str(int(ts // BUCKET_S * BUCKET_S))
    hist[k] = hist.get(k, 0) + xp


def prune_usage(state: dict, now: float) -> None:
    hist = state.get("usage_hist") or {}
    if "usage_hist_desde" in state:
        state["usage_hist_desde"] = max(state["usage_hist_desde"], now - HIST_KEEP_S)
    for k in [k for k in hist if int(k) < now - HIST_KEEP_S]:
        del hist[k]


def usage_between(state: dict, start: float, end: float) -> float:
    return sum(v for k, v in (state.get("usage_hist") or {}).items() if int(k) + BUCKET_S > start and int(k) < end)


def calibrate(state: dict, limits: dict | None, now: float) -> None:
    """Leitura oficial nova -> fator = % oficial / tokens locais na janela, por janela."""
    upd = (limits or {}).get("updated")
    cal = state.setdefault("calib", {})
    if not upd or upd == cal.get("updated"):
        return
    cal["updated"] = upd
    for key, win in WINDOWS.items():
        pct, reset = limits.get(key, (None, None))
        if pct is None or not reset:
            continue
        if state.get("usage_hist_desde", math.inf) > reset - win:
            continue                        # histórico não cobre a janela toda: mantém o fator anterior
        tok = usage_between(state, reset - win, now)
        if tok >= MIN_CALIB_XP:
            cal[key] = {"f": pct / tok, "reset": reset}


def sessions(state: dict) -> list[list[float]]:
    """Janelas de 5h refeitas do histórico, [início, tokens]: uma começa no 1º uso depois que a anterior acabou."""
    out = []
    for k, v in sorted((int(k), v) for k, v in (state.get("usage_hist") or {}).items() if v > 0):
        if not out or k >= out[-1][0] + WINDOWS["sessao"]:
            out.append([k, 0.0])
        out[-1][1] += v
    return out


def peak(state: dict, key: str, tok: float) -> float:
    """Maior uso já visto numa janela `key` (guardado em state["pico"], vale além dos 8 dias do histórico).
    É a régua da barra quando não há % oficial nem fator: "quanto do seu pico", não do limite real."""
    p = state.setdefault("pico", {})
    hist = max((t for _, t in sessions(state)), default=0) if key == "sessao" else 0
    p[key] = max(p.get(key, 0), hist, tok or 0)
    return p[key]


def limit_view(key: str, limits: dict | None, state: dict, now: float):
    """(pct|None, reset|None, estimado, tokens|None) para a linha da janela `key`."""
    win = WINDOWS[key]
    pct, reset = (limits or {}).get(key, (None, None))
    upd = (limits or {}).get("updated") or 0
    if pct is not None and now - upd < OFFICIAL_FRESH_S:
        return pct, reset, False, None
    cal = (state.get("calib") or {}).get(key)
    if not cal and key == "sessao":         # sem fator: a sessão vem do histórico (começa no 1º uso)
        s = sessions(state)
        if s and now < s[-1][0] + win:
            return None, s[-1][0] + win, False, s[-1][1]
        return None, None, False, 0.0
    if cal:
        reset = cal["reset"]
    if reset and reset <= now:              # o reset passou: avança a janela em múltiplos dela
        reset += ((now - reset) // win + 1) * win
    start = reset - win if reset else now - win
    tok = usage_between(state, start, now)
    if cal:
        return tok * cal["f"], reset, True, None
    return None, reset, False, tok


# ------------------------------------------------------------- perfil (funções puras)
LEVEL_XP = 1_000_000                # nível de domador = floor(sqrt(energia na vida (xp_total) / 1M))


def level(total: float) -> tuple[int, float, float]:
    """(nível, fração até o próximo, energia que falta). Nível n começa em n² milhões de energia."""
    n = math.isqrt(int(total // LEVEL_XP))
    base, next_ = n * n * LEVEL_XP, (n + 1) ** 2 * LEVEL_XP
    return n, (total - base) / (next_ - base), next_ - total


def usage_per_day(state: dict, now: float, dias: int = 7) -> list[tuple[date, float]]:
    """XP de `usage_hist` somado por dia local, do mais antigo até hoje."""
    today = datetime.fromtimestamp(now).date()
    out = {today - timedelta(days=i): 0.0 for i in range(dias)}
    for k, v in (state.get("usage_hist") or {}).items():
        d = datetime.fromtimestamp(int(k)).date()
        if d in out:
            out[d] += v
    return sorted(out.items())


def streak_days(state: dict, now: float) -> int:
    """Dias seguidos com uso até hoje (hoje ainda sem uso não quebra a sequência).
    Usa `usage_hist` (8 dias, por horário) e `daily` (60 dias, contado com o app aberto)."""
    used = {datetime.fromtimestamp(int(k)).date() for k, v in (state.get("usage_hist") or {}).items() if v > 0}
    used |= {date.fromisoformat(k) for k, v in (state.get("daily") or {}).items() if v > 0}
    d = datetime.fromtimestamp(now).date()
    if d not in used:
        d -= timedelta(days=1)
    n = 0
    while d in used:
        n, d = n + 1, d - timedelta(days=1)
    return n


def last_use(state: dict) -> float | None:
    """Fim do último balde de 5 min com tokens."""
    ks = [int(k) for k, v in (state.get("usage_hist") or {}).items() if v > 0]
    return max(ks) + BUCKET_S if ks else None


def fmt_ago(dt: float) -> str:
    if dt < 60:
        return _t("agora")
    if dt < 3600:
        return _t("há {n} min", n=int(dt // 60))
    if dt < 86400:
        return _t("há {n} h", n=int(dt // 3600))
    return _t("há {n} d", n=int(dt // 86400))


# ------------------------------------------------------------- progresso
DEFAULT_STATE = {
    "tokens_total": 0,
    "xp_total": 0.0,
    "daily": {},
    "size": "Médio",
    "mode": "auto",              # "auto" ou "interativo" (o jogador escolhe pegar/consumir)
    "lang": "pt",                # idioma da interface: "pt" ou "en" (idioma.py)
    "pos": None,
    "topmost": True,
    "so_com_uso": False,         # some depois de ESCONDER_S sem tokens e volta quando houver uso
    "last_fed": 0.0,
    "run": None,
    "meta": None,
}


def load_state(path: Path) -> tuple[dict, bool]:
    state = json.loads(json.dumps(DEFAULT_STATE))
    is_new = True
    if path.exists():
        try:
            state.update(json.loads(path.read_text(encoding="utf-8")))
            is_new = False
        except (OSError, ValueError) as e:
            log(f"estado ilegível ({e}); começando do zero")
    meta = M.new_meta()
    meta.update(state.get("meta") or {})
    state["meta"] = meta
    if state.get("run"):
        M.migrate_run(state["run"])
    return state, is_new


DAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def read_limits(path: Path, now: float) -> dict | None:
    """{"sessao": (pct|None, resets_at), "semana": ...}; pct None = dado velho (reset já passou)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    out = {}
    for key, name in (("five_hour", "sessao"), ("seven_day", "semana")):
        w = data.get(key) if isinstance(data, dict) else None
        if not isinstance(w, dict):
            continue
        reset = w.get("resets_at")
        pct = w.get("used_percentage")
        if not isinstance(pct, (int, float)) or (isinstance(reset, (int, float)) and reset <= now):
            pct = None
        out[name] = (pct, reset if isinstance(reset, (int, float)) else None)
    if out and isinstance(data.get("updated"), (int, float)):
        out["updated"] = data["updated"]
    return out or None


def limit_color(pct: float) -> str:
    return GOOD if pct <= 50 else GOLD if pct <= 80 else HURT


def fmt_reset(reset: float, now: float) -> str:
    """Horário do reset no fuso do PC: "14:30" se for hoje, senão "sex 09:00"."""
    t = datetime.fromtimestamp(reset)
    if t.date() == datetime.fromtimestamp(now).date():
        return t.strftime("%H:%M")
    return f"{_t(DAYS[t.weekday()])} {t.strftime('%H:%M')}"


def save_state(path: Path, state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    daily = state.get("daily", {})
    for k in sorted(daily)[:-60]:
        del daily[k]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


# ----------------------------------------------------------- personagens
class CharacterDef:
    def __init__(self, key, name, stages, frame_ms=600, stats=None, unlock=None, community=False, trait=None):
        self.key, self.name, self.frame_ms = key, name, frame_ms
        self.stats = stats or {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
        self.unlock, self.community = unlock, community
        self.trait = trait or {}
        # cada estágio: {"floor", "title", "frames": [spec], "blink": spec|None, "sleep": spec|None}
        # e, se vier de spritesheet, "estados": {estado: [spec]} (spec ("sheet", path, box, N))
        self.stages = sorted(stages, key=lambda s: s["floor"])

    @property
    def stage_floors(self) -> list[int]:
        return [s["floor"] for s in self.stages]


def builtin_characters() -> list[CharacterDef]:
    stages = []
    for i, st in enumerate(_slime.STAGES):
        states = {e: [("grid", g, _slime.PAL) for g in gs] for e, gs in _assemble.states(_slime, i).items()}
        blink = _assemble.overlap(_slime.BLINK, st["extra"], *_slime.ANCHOR["idle"][2]) if st["extra"] else _slime.BLINK
        closed = ("grid", blink, _slime.PAL)
        stages.append({"floor": st["floor"], "title": st["title"], "frames": states["idle"],
                       "blink": closed, "sleep": closed, "estados": states})
    return [CharacterDef("slime", "Slime", stages, stats={"hp": 20, "atk": 3, "def": 0, "dodge": 0})]


DEFAULT_STATS = {"hp": 20, "atk": 3, "def": 0, "dodge": 0, "spd": 10.0}
_LEAVES = {}  # (caminho, mtime) -> (linhas de caixas, N, {caixa: PixelMap reduzido}); o PNG decodificado é descartado


def read_sheet(path: Path):
    """Linhas de caixas da folha, o fator N de redução e o mapa reduzido de cada caixa. Puro (roda na thread).
    Opaco = alfa > 128; a máscara é amostrada (1 a cada `a` px) e perde as ilhas de até 2 px."""
    ck = (str(path), path.stat().st_mtime)
    if ck not in _LEAVES:
        w, h, rgba = sheet.read_png(path)
        op = rgba[3::4].translate(sheet.OPAQUE)
        grid = sheet.detect_grid(w, h)
        if grid:
            cols, lins = grid
            cw, ch = w // cols, h // lins
            a = sheet.reduction_factor(ch)
        else:
            a = sheet.reduction_factor(h // 9)
        ws, hs = -(-w // a), -(-h // a)
        m = sheet._mask(ws, hs, lambda x, y: op[y * a * w + x * a])
        if grid:
            occupied = {}   # célula -> pontos opacos (offset dentro da célula)
            for ys, lin in enumerate(m):
                for xs in range(ws):
                    if lin[xs]:
                        X, Y = xs * a, ys * a
                        occupied.setdefault((Y // ch, X // cw), []).append((X % cw, Y % ch))
            pts = [p for cel in occupied.values() for p in cel]
            if not pts:
                raise ValueError(f"folha sem quadros: {path.name}")
            # uma caixa só (união do opaco de todas as células) para os quadros não tremerem
            ox0, oy0 = min(x for x, _ in pts), min(y for _, y in pts)
            ox1, oy1 = min(cw, max(x for x, _ in pts) + a), min(ch, max(y for _, y in pts) + a)
            # célula sem pixel opaco (linha com menos de 8 quadros) fica de fora: nunca vira quadro piscando
            lines = [[(c * cw + ox0, r * ch + oy0, c * cw + ox1, r * ch + oy1) for c in range(cols) if (r, c) in occupied]
                      for r in range(lins)]
            n = sheet.reduction_factor(oy1 - oy0)
        else:
            # ponytail: caixas com precisão de `a` px (amostra); corte exato custa ~5 s em folha grande
            lines = [[(x0 * a, y0 * a, min(w, x1 * a), min(h, y1 * a)) for x0, y0, x1, y1 in lin]
                      for lin in sheet.cut(ws, hs, lambda x, y: m[y][x])]
            n = sheet.reduction_factor(max((c[3] - c[1] for lin in lines for c in lin), default=1))
        if not any(lines):
            raise ValueError(f"folha sem quadros: {path.name}")
        maps = {}
        for lin in lines:
            for (x0, y0, x1, y1) in lin:
                maps[(x0, y0, x1, y1)] = {
                    ((x - x0) // n, (y - y0) // n): "#%02x%02x%02x" % tuple(rgba[4 * (y * w + x):4 * (y * w + x) + 3])
                    for y in range(y0, y1, n) for x in range(x0, x1, n) if op[y * w + x]}
        _LEAVES[ck] = lines, n, maps
    return _LEAVES[ck]


def stage_of_sheet(path: Path, floor: int, title: str) -> dict:
    """Estágio de spritesheet ainda não cortado: a descoberta só lê o cabeçalho do PNG (barato).
    `completar_estagio` (na thread, ao ativar o herói) preenche "frames" e "estados"."""
    with open(path, "rb") as f:
        sheet.info_png(f.read(29))
    return {"floor": floor, "title": title, "sheet": path, "frames": None, "blink": None, "sleep": None}


def complete_stage(stage: dict) -> dict:
    """Corta a folha do estágio: estados na ordem das linhas; linha vazia ou ausente usa o Idle.
    Erro vira stage["erro"] (a GUI volta para o Slime). Puro: pode rodar fora da thread do Tk."""
    try:
        lines, n, _ = read_sheet(stage["sheet"])
        specs = [[("sheet", stage["sheet"], c, n) for c in lin] for lin in lines]
        idle = next(l for l in specs if l)
        states = {e: (specs[i] if i < len(specs) and specs[i] else idle) for i, e in enumerate(sheet.STATES)}
        stage["frames"] = states["idle"]
        stage["estados"] = states      # por último: quem vê "estados" já vê "frames"
    except Exception as e:
        stage["erro"] = str(e)
    return stage


def pet_openpets(d: Path):
    """Formato OpenPets (pet.json): (png, nome) da pasta. `spritesheetPath` .webp usa o .png de mesmo nome;
    sem pet.json: spritesheet.png ou o 1º .png. png None = nada usável (webp-only loga o aviso)."""
    name, rel = d.name, None
    try:
        j = json.loads((d / "pet.json").read_text(encoding="utf-8"))
        name = str(j.get("displayName") or j.get("name") or d.name)
        rel = j.get("spritesheetPath")
    except (OSError, ValueError, AttributeError):
        pass   # pet.json ausente ou inválido: fica o nome da pasta
    cands = []
    if isinstance(rel, str) and rel:
        p = d / rel
        cands.append(p.with_suffix(".png") if p.suffix.lower() == ".webp" else p)
    cands.append(d / "spritesheet.png")
    cands += sorted(d.glob("*.png"))
    png = next((c for c in cands if c.suffix.lower() == ".png" and c.is_file()), None)
    if not png and any(d.glob("*.webp")):
        log(f"pet '{d.name}' ignorado: só tem WebP; converta para PNG (python tools/converter_webp.py {d})")
    return png, name


def load_png_characters(folder: Path = CHARACTERS_DIR) -> list[CharacterDef]:
    out = []
    if not folder.is_dir():
        return out
    for d in sorted(folder.iterdir()):
        cfg = d / "character.json"
        if not cfg.is_file():
            png, name = pet_openpets(d)   # folha sem character.json: um estágio, stats padrão
            if png:
                try:
                    out.append(CharacterDef(d.name, name, [stage_of_sheet(png, 1, name)], stats=dict(DEFAULT_STATS)))
                except Exception as e:
                    log(f"personagem '{d.name}' ignorado: {e}")
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))

            def spec(name):
                p = d / name
                if not p.is_file():
                    raise FileNotFoundError(f"imagem não encontrada: {p.name}")
                return ("png", p)

            stages = []
            for i, st in enumerate(data["stages"]):
                default_floor = M.DEFAULT_STAGE_FLOORS[min(i, len(M.DEFAULT_STAGE_FLOORS) - 1)]
                if st.get("sheet"):
                    stages.append(stage_of_sheet(spec(st["sheet"])[1], int(st.get("floor", default_floor)),
                                                 st.get("title", data.get("name", d.name))))
                    continue
                frames = [spec(f) for f in st["frames"]]
                if not frames:
                    raise ValueError("estágio sem 'frames'")
                stages.append({
                    "floor": int(st.get("floor", default_floor)),
                    "title": st.get("title", data.get("name", d.name)),
                    "frames": frames,
                    "blink": spec(st["blink"]) if st.get("blink") else None,
                    "sleep": spec(st["sleep"]) if st.get("sleep") else None,
                })
            if not stages:
                raise ValueError("nenhum estágio em 'stages'")
            stats = {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
            stats.update(data.get("stats") or {})
            for k in ("hp", "atk", "def"):          # tipo errado: herói ignorado aqui, não erro a cada tick
                stats[k] = int(stats[k])
            for k in ("dodge", "spd", "crit", "critdmg"):
                if k in stats:
                    stats[k] = float(stats[k])
            unlock = data.get("unlock")
            if unlock and unlock not in M.ACHIEVEMENTS:
                raise ValueError(f"'unlock' desconhecido: {unlock}")
            trait = data.get("traço") or data.get("traco") or {}
            if not isinstance(trait, dict):
                raise ValueError("'traço' precisa ser um objeto")
            valid = M.stats(M.new_run("x", {}, 0))
            for k, v in trait.items():
                if k not in valid or isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise ValueError(f"'traço' inválido: {k}")
            out.append(CharacterDef(d.name, data.get("name", d.name), stages,
                                    int(data.get("frame_ms", 600)), stats, unlock, trait=trait))
        except Exception as e:  # personagem com defeito não derruba o app
            log(f"personagem '{d.name}' ignorado: {e}")
    return out


def petdex_dirs() -> list[Path]:
    """Pastas de pets do Petdex (só lidas, nunca escritas). Lidas na hora para o teste trocar o HOME."""
    return [Path.home() / ".petdex" / "pets", Path.home() / ".codex" / "pets"]


def load_petdex_characters() -> list[CharacterDef]:
    """Pets da comunidade: via `pet_openpets` (só leitura)."""
    out = []
    for base in petdex_dirs():
        if not base.is_dir():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            png, name = pet_openpets(d)
            if not png:
                continue
            try:
                out.append(CharacterDef("petdex:" + d.name, name, [stage_of_sheet(png, 1, name)],
                                        stats=dict(DEFAULT_STATS), community=True))
            except Exception as e:
                log(f"pet '{d.name}' ignorado: {e}")
    return out


def all_characters() -> dict[str, CharacterDef]:
    chars = {c.key: c for c in builtin_characters()}
    for c in load_png_characters() + load_petdex_characters():
        chars.setdefault(c.key, c)
    return chars


# ------------------------------------------------------------------- GUI
class _StatesFx(dict):
    """estado -> imagens [quadro][fase]; compõe na primeira leitura e guarda em app.fx_cache."""
    def __init__(self, app, names):
        super().__init__((e, None) for e in names)
        self.app = app

    def __getitem__(self, e):
        ck = (e, self.app.fx_sig)
        if ck not in self.app.fx_cache:
            dict.__getitem__(self, e)           # KeyError para estado que a folha não tem
            self.app.fx_cache[ck] = self.app.fx_compose(e)
        return self.app.fx_cache[ck]


def render_grid(grid, pal, s):
    h, w = len(grid), max(len(r) for r in grid)
    img = tk.PhotoImage(width=w * s, height=h * s)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            color = pal.get(ch)
            if color:
                img.put(color, to=(x * s, y * s, (x + 1) * s, (y + 1) * s))
    return img


def _hex(v):
    """Cor de PhotoImage.get: tupla (r, g, b) no Tk 8.6, texto "r g b" em alguns builds."""
    if isinstance(v, str):
        v = v.split()
    return "#%02x%02x%02x" % tuple(int(c) for c in v[:3])


def spec_to_map(spec, k: int = None):
    """Spec do herói -> PixelMap com o quadro em (0..16, 0..16), centrado na horizontal e base em y = 16.
    Folha: quadro de 16k (k do estágio, igual para todos os estados), base da caixa aparada na base do quadro,
    então um quadro de pulo sai do chão."""
    if spec[0] == "sheet":
        _, path, box, n = spec
        pm = read_sheet(path)[2][box]
        w, h, side = -(-(box[2] - box[0]) // n), -(-(box[3] - box[1]) // n), 16 * (k or spec_k(spec))
        dx, dy = (side - w) // 2, side - h
        return {(x + dx, y + dy): c for (x, y), c in pm.items()}
    if spec[0] == "grid":
        grid = spec[1]
        w, h = max(len(r) for r in grid), len(grid)
        pm = visual.grid_to_map(grid, spec[2])
    else:
        src = tk.PhotoImage(file=str(spec[1]))
        sw, sh = src.width(), src.height()
        # ponytail: PNG grande só é amostrado (1 a cada `step` px); a escala de verdade fica para a parte 3
        step = math.ceil(max(sw, sh) / 16) if max(sw, sh) > 24 else 1
        pm = {(x // step, y // step): _hex(src.get(x, y))
              for y in range(0, sh, step) for x in range(0, sw, step) if not src.transparency_get(x, y)}
        w, h = math.ceil(sw / step), math.ceil(sh / step)
    side = 16 * (k or max(1, -(-h // 16)))      # grade 32 px: quadro de 32 (k = 2)
    dx, dy = (side - w) // 2, side - h
    return {(x + dx, y + dy): c for (x, y), c in pm.items()}


def spec_height(spec) -> int:
    """Altura final (já reduzida) do quadro; grid = altura da grade; PNG solto fica em 16."""
    if spec[0] == "sheet":
        return -(-(spec[2][3] - spec[2][1]) // spec[3])
    return len(spec[1]) if spec[0] == "grid" else 16


def spec_k(spec) -> int:
    return max(1, -(-spec_height(spec) // 16))   # para cima: o quadro nunca corta o herói


def render_map(pm, s: int, k: int = 1):
    """Imagem com origem em look_box(k) (tamanho sempre fixo) e quantos px de tela ela desce abaixo da base.
    `s` = px de tela por pixel do mapa (herói de altura H: s = px_heroi); k = H/16 arredondado (escala dos looks)."""
    box = visual.look_box(k)
    x0, y0, x1, y1 = box
    img = tk.PhotoImage(width=(x1 - x0) * s, height=(y1 - y0) * s)
    for (x, y), c in visual.crop(pm, box).items():
        img.put(c, to=((x - x0) * s, (y - y0) * s, (x - x0 + 1) * s, (y - y0 + 1) * s))
    return img, (y1 - 16 * k) * s


def steps(r: int) -> list[int]:
    """Recuo de cada uma das r linhas de um canto de raio r, de fora para dentro (degraus de 1 px, sem antialias)."""
    return [r - round(math.sqrt(r * r - (r - i - 0.5) ** 2)) for i in range(r)]


def _shape(cv, x0, y0, x1, y1, r, color, tags):
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    if x1 <= x0 or y1 <= y0:
        return
    ins, kw, i = steps(r), dict(fill=color, outline="", width=0, tags=tags), 0
    while i < len(ins):                     # linhas de mesmo recuo viram um retângulo só
        j = i
        while j < len(ins) and ins[j] == ins[i]:
            j += 1
        cv.create_rectangle(x0 + ins[i], y0 + i, x1 - ins[i], y0 + j, **kw)
        cv.create_rectangle(x0 + ins[i], y1 - j, x1 - ins[i], y1 - i, **kw)
        i = j
    if y1 - r > y0 + r:
        cv.create_rectangle(x0, y0 + r, x1, y1 - r, **kw)


def rounded_rect(cv, x0, y0, x1, y1, r, fill, outline=None, larg=1, tag="arred", extra=()):
    """Retângulo de cantos em degraus de pixel no Canvas `cv`, só com retângulos retos (sem antialias: a cor-chave
    #ff00fe não ganha contorno rosa). Tags: `tag` em tudo, `tag`_f no miolo (troca de cor no hover), mais `extra`."""
    if outline:
        _shape(cv, x0, y0, x1, y1, r, outline, (tag, tag + "_b", *extra))
        x0, y0, x1, y1, r = x0 + larg, y0 + larg, x1 - larg, y1 - larg, max(0, r - larg)
    _shape(cv, x0, y0, x1, y1, r, fill, (tag, tag + "_f", *extra))


def png_bytes(pm, side, square=False):
    """PNG do mapa de pixels aparado e ampliado por um inteiro até caber em `lado` px -> (png, w, h).
    `quadrado`: centraliza numa tela lado x lado (ícone da bandeja)."""
    x0, y0, x1, y1 = visual.bbox(pm)
    s = max(1, side // max(1, x1 - x0, y1 - y0))
    if square:
        n = side // s
        x0 -= (n - (x1 - x0)) // 2
        y0 -= (n - (y1 - y0)) // 2
        x1, y1 = x0 + n, y0 + n
    w, h = (x1 - x0) * s, (y1 - y0) * s
    raw = b"".join((b"\0" + b"".join((bytes.fromhex(pm[(x, y)][1:]) + b"\xff" if (x, y) in pm else b"\0" * 4) * s
                                     for x in range(x0, x1))) * s for y in range(y0, y1))

    def bloco(kind, d):
        return struct.pack(">I", len(d)) + kind + d + struct.pack(">I", zlib.crc32(kind + d))
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(raw, 1)) + bloco(b"IEND", b"")), w, h


def map_img(pm, side):
    """Mapa de pixels aparado e ampliado por um inteiro até caber em `lado` px."""
    if not pm:
        return tk.PhotoImage(width=1, height=1)
    # um PNG montado aqui e lido numa chamada só (um put por pixel levava ~0,4 s para abrir o cemitério)
    png, w, h = png_bytes(pm, side)
    return tk.PhotoImage(data=base64.b64encode(png).decode(), format="png", width=w, height=h)


def start_tray():
    """Ícone na bandeja (só Windows): o Slime em .ico em DATA_DIR. Falhou? Segue sem (o menu tem "Sair")."""
    if os.name != "nt":
        return None
    try:
        import tray
        p = DATA_DIR / "icone.ico"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        p.write_bytes(tray.ico(png_bytes(hero_idle("slime"), 32, square=True)[0], 32))
        return tray.Bandeja(str(p), APP_NAME, lambda: [_t("Mostrar o pet"), _t("Sair")])
    except Exception:
        log("erro no ícone da bandeja: " + traceback.format_exc())
        return None


def hero_idle(key):
    """1º quadro idle do 1º estágio direto do módulo herois/<key>.py (sem cortar a folha PNG, que leva segundos).
    None se não houver módulo (herói externo/Petdex: a grade espera a thread de corte)."""
    import importlib
    try:
        mod = importlib.import_module(f"heroes.{key}")
    except ImportError:
        return None
    return visual.grid_to_map(_assemble.states(mod, 0)["idle"][0], mod.PAL)


def own_hero(key):
    """Herói feito aqui (tem módulo herois/<key>.py); os outros (pasta em characters/, Petdex/Codex) são importados."""
    import importlib.util
    try:
        return importlib.util.find_spec(f"heroes.{key}") is not None
    except (ImportError, ValueError):
        return False


_ITEM_ARTS = {}


ELEMENT_LOOK = {"queimar": "chamas", "eletrizar": "faiscas", "envenenar": "gotas_veneno", "congelar": "geada"}


def pet_looks(run):
    """Looks dos itens [(look, brilho)] + um look animado por elemento que o pet aplica e ainda não aparece."""
    looks = [(M.ITEMS[it["key"]]["look"], M.RAR_COLOR.get(it["rar"]))
             for it in run["items"] if it["key"] in M.ITEMS]
    kinds = {l["type"] for l, _ in looks}
    st = M.stats(run)
    return looks + [({"type": t}, None) for k, t in ELEMENT_LOOK.items() if st[k] > 0 and t not in kinds]


def depth(run):
    """"Andar 3-2" no idioma atual."""
    return _t("Andar {n}", n=f"{run['floor']}-{run['room']}")


def _pct(v):

    return f"{round(v * 100)}%"


# janela de Status: (campo de stats(), nome, formato, teto ou None, mostra mesmo zerado)
STAT_LINES = (
    ("maxhp", "HP máx", str, None, True),
    ("atk", "Ataque", str, None, True),
    ("def", "Defesa", str, None, True),
    ("spd", "Velocidade", lambda v: f"{round(v)}", None, True),
    ("crit", "Crítico", _pct, M.MAX_CRIT, True),
    ("critdmg", "Dano crítico", lambda v: f"×{v:g}", None, True),
    ("dodge", "Esquiva", _pct, M.MAX_DODGE, False),
    ("lifesteal", "Roubo de vida", lambda v: _t("+{v} por vitória", v=v), None, False),
    ("duplo", "Golpe duplo", _pct, M.MAX_DOUBLE, False),
    ("area", "Ataque em área", lambda v: _t("sim"), None, False),
    ("queimar", "Queimar", _pct, M.MAX_ELEM_CHANCE, False),
    ("eletrizar", "Eletrizar", _pct, M.MAX_ELEM_CHANCE, False),
    ("envenenar", "Envenenar", _pct, M.MAX_ELEM_CHANCE, False),
    ("congelar", "Congelar", _pct, M.MAX_ELEM_CHANCE, False),
    ("bloqueio", "Bloqueios por luta", str, M.MAX_BLOCK, False),
    ("espinhos", "Espinhos", _pct, M.MAX_THORNS, False),
    ("cura_sala", "Cura por sala", lambda v: f"+{v} HP", None, False),
    ("cura_andar", "Cura por andar", lambda v: f"+{v} HP", None, False),
    ("custo_ataque", "Custo de ataque", lambda v: f"-{v} HP", None, False),
    ("furia", "Fúria", lambda v: _t("+{v} ATK a cada 10%", v=v), None, False),
    ("ajudante", "Ajudante", lambda v: _t("{v} de dano", v=v), None, False),
    ("crescer", "Crescer", lambda v: f"+1 ATK / {v} kills", None, False),
    ("gold", "Ouro", lambda v: f"+{_pct(v)}", None, False),
    ("energy", "Energia", lambda v: f"+{_pct(v)}", M.MAX_ENERGY_BONUS, False),
    ("trap", "Armadilhas", lambda v: f"×{v:g}", None, False),
    ("sorte", "Sorte", lambda v: f"+{_pct(v)}", M.MAX_LUCK, False),
    ("desconto", "Desconto", _pct, M.MAX_DISCOUNT, False),
)


def stat_lines(run, st):
    """[(campo, nome, valor)] da janela de Status: os fixos sempre, os outros só quando mudam algo."""
    st = dict(st, crescer=min([M.item_fx(i["key"], i["rar"]).get("crescer", 0) for i in run["items"]
                               if "crescer" in M.ITEMS.get(i["key"], {}).get("fx", {})] or [0]))
    out = []
    for k, name, fmt_, cap, always in STAT_LINES:
        v = st[k]
        if always or (v != 1 if k == "trap" else v):
            out.append((k, _t(name), fmt_(v) + (f" / {fmt_(cap)}" if cap is not None else "")))
    return out


# página de itens: família pelo 1º campo de fx que aparece nesta ordem (sem nenhum: "Básico")
FAMILIES = (("Elemental", ("queimar", "eletrizar", "envenenar", "congelar")), ("Ajudante", ("ajudante",)),
            ("Crescimento", ("crescer",)), ("Área", ("area",)), ("Sangue", ("custo_ataque", "furia")),
            ("Golpes", ("crit", "critdmg", "duplo")), ("Defesa", ("bloqueio", "espinhos", "dodge")),
            ("Regeneração", ("cura_sala", "cura_andar", "lifesteal")), ("Sorte e ouro", ("sorte", "gold", "desconto")))


def item_family(key):
    fx = M.ITEMS[key]["fx"]
    return next((name for name, fields in FAMILIES if any(fx.get(c) for c in fields)), "Básico")


@lru_cache(maxsize=None)
def boss_grid(sprite):
    """Monstro com a coroa de chefe em cima (grade única por sprite: o cache de ícones usa o id)."""
    foe = art.FOE_ART[sprite]
    w = max(len(foe[0]), len(art.CROWN[0]))
    pad = lambda r: r.center(w, ".")
    return tuple(pad(r) for r in art.CROWN + foe)


def item_arts():
    """Arte dos itens como PixelMap (em cache: nunca muda)."""
    if not _ITEM_ARTS:
        _ITEM_ARTS.update({k: visual.grid_to_map(g, art.PAL) for k, g in art.ITEM_ART.items()})
    return _ITEM_ARTS


class PetApp:
    def __init__(self, args):
        self.demo = args.demo
        self.rng = random.Random()
        self.state_path = DATA_DIR / ("state-demo.json" if self.demo else "state.json")
        if args.reset and self.state_path.exists():
            self.state_path.unlink()
        self.state, is_new = load_state(self.state_path)
        self.meta = self.state["meta"]
        self.reader = TokenReader(self.state)
        if is_new:
            self.state["last_fed"] = time.time()
            if not self.demo and not args.import_history:
                self.reader.skip_existing()
        if not self.demo and "usage_hist" not in self.state:
            self.reader.backfill()
        self.state.setdefault("usage_hist_desde", time.time())   # sem backfill: cobre só daqui em diante
        self.chars = all_characters()
        if self.state["size"] not in SIZES:
            self.state["size"] = "Médio"
        if self.state["mode"] not in MODES:
            self.state["mode"] = "auto"
        i18n.set_lang(self.state.get("lang"))
        self.state["lang"] = i18n.LANG
        run = self.state.get("run")
        if not run or run.get("dead") or run.get("char") not in self.chars:
            self.new_run(announce=False)

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", bool(self.state["topmost"]))
        self.root.report_callback_exception = self._on_error
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT)
            bg = TRANSPARENT
        except tk.TclError:          # fora do Windows: fundo escuro em vez de transparente
            bg = PANEL_BG
        self.canvas = tk.Canvas(self.root, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.font = ("Segoe UI", 9, "bold")
        self.font_small = ("Segoe UI", 8, "bold")

        self.floaters: list = []
        self.n_floater = 0
        self.particles: list = []
        self.hop: list[int] = []
        self.lunge: list[int] = []
        self.foe_lunge: list[int] = []
        self.lunge_foe = 0            # qual inimigo está dando o bote
        self.foe_xy: list = []        # posição de cada inimigo na tela
        self.pet_status = None        # status do pet visto na animação da luta (só para o painel)
        self.blink_until = 0.0
        self.next_blink = time.time() + 3
        self.next_zzz = 0.0
        self.last_rest_heal = time.time()
        self.opened_at = time.time()        # aberto à mão: aparece por ESCONDER_S mesmo sem uso
        self.escondido = False
        self.tray = None                 # ícone na bandeja (run_gui liga; os testes não)
        self.last_save = time.time()
        self.busy_until = time.time() + 1.5
        self.respawn_at = None
        self.popup_win = None
        self.choice_win = None
        self.pending_since = None     # quando a janela de escolha começou (só em memória)
        self._drag = None
        self._moved = False

        self.limits = read_limits(DATA_DIR / "limites.json", time.time())   # statusline opcional
        self.build(first=True)
        self.build_menu()
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", lambda e: self.show_stats())
        self.canvas.bind("<Button-3>", self.on_menu)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        if is_new:
            self.root.after(800, lambda: self.popup(
                [_t(s) for s in ("Bem-vindo à Masmorra de Tokens!",
                                 "Seus tokens do Claude Code viram energia",
                                 "e eu desço a masmorra sozinho.",
                                 "Arraste para me mover · botão direito = menu",
                                 "Duplo clique = status")], 10000))
        if self.demo:
            self.root.after(500, lambda: self.floater(_t("MODO DEMO"), GOLD))
        self.root.after(300, self.poll)
        self.root.after(100, self.tick)

    # ----------------------------------------------------------- run/meta
    @property
    def run(self) -> dict:
        return self.state["run"]

    @property
    def char(self) -> CharacterDef:
        return self.chars.get(self.run["char"]) or self.chars["slime"]

    def is_unlocked(self, c: CharacterDef) -> bool:
        return self.demo or not c.unlock or c.unlock in self.meta["achievements"]   # demo: todos liberados para testar

    def new_run(self, announce=True):
        key = self.meta.get("next_char", "slime")
        c = self.chars.get(key)
        if c is None or not self.is_unlocked(c):
            key, c = "slime", self.chars["slime"]
        # a energia que sobrou passa para a run nova (tokens não se perdem)
        energy = self.state["run"]["energy"] if self.state.get("run") else 0.0
        self.state["run"] = M.new_run(key, c.stats, self.meta["runs"] + 1, c.trait)
        self.state["run"]["energy"] = energy
        self.state["run"]["ach_start"] = list(self.meta["achievements"])
        self.respawn_at = None
        self.pet_status = None
        if announce:
            self.build()
            self.popup([_t("Run #{n} começou!", n=self.run['id']), _t("{nome} entra na masmorra...", nome=_t(c.name))],
                       5000)

    # --------------------------------------------------------------- layout
    def build(self, first=False):
        px = SIZES[self.state["size"]]
        self.px = px
        self.bpx = round(px * 1.5)
        self.T = 16 * px
        bx0, by0, bx1, by1 = visual.LOOK_BOX
        left = 6 - bx0 * px                 # margem para os itens que saem à esquerda do quadro
        self.pcx = left + self.T // 2
        # à direita: 1 inimigo grande ou um grid 2x2 de inimigos pequenos (colunas de 11 px + 1 de folga)
        fx0 = left + self.T + (bx1 - 16) * px
        self.foe_area = max(11 * self.bpx, 23 * px)
        self.fcx = fx0 + self.foe_area // 2
        self.foe_cols = (fx0 + 11 * px // 2, fx0 + 12 * px + 11 * px // 2)
        self.W = fx0 + self.foe_area + 10
        self.top = 52 - by0 * px            # espaço para o que sai acima do quadro
        self.base_y = self.top + self.T
        self.below = (by1 - 16) * px        # o que pode descer abaixo da base (gotas)
        # barras de sessão/semana: oficial (statusline), estimada (~) ou só tokens
        self.limit_h = 30
        self.H = self.base_y + self.below + 64 + self.limit_h

        self.art = {}
        self.load_images()

        if first:
            pos = self.state.get("pos")
            if pos:
                x, y = pos
            else:
                x = self.root.winfo_screenwidth() - self.W - 40
                y = self.root.winfo_screenheight() - self.H - 80
        else:
            x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{self.W}x{self.H}+{int(x)}+{int(y)}")

        c = self.canvas
        c.delete("all")
        self.floaters.clear()
        self.particles.clear()
        self.sprite = c.create_image(self.pcx, self.base_y + self.below, anchor="s")
        self.foe_items = [(c.create_image(self.fcx, self.base_y, anchor="s", state="hidden"),
                           c.create_image(self.fcx, self.base_y, anchor="s", state="hidden"))
                          for _ in range(4)]
        self.foe_xy = []
        self.foe_on = set()           # inimigos visíveis
        self.foe_look = []

        py = self.base_y + self.below + 6
        self.panel_y = py
        rounded_rect(c, 5, py - 1, self.W - 5, py + 53 + self.limit_h, WINDOW_R, PANEL_BG, PANEL_EDGE, 2,
                              tag="painel", extra=("card:painel",))
        self.title_txt = c.create_text(14, py + 11, anchor="w", fill=TEXT, font=self.font)
        self.hp_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=HURT, font=self.font)
        self.status_y = py + 11
        self.status_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=MUTED, font=self.font_small)
        self.info_txt = c.create_text(14, py + 26, anchor="w", fill=MUTED, font=self.font_small)
        self.bar_x0, self.bar_x1, self.bar_y = 14, self.W - 14, py + 38
        rounded_rect(c, self.bar_x0, self.bar_y, self.bar_x1, self.bar_y + 6, 3, BAR_BG, tag="barra_t")
        self.bar = "barra_e"            # tag do preenchimento (redesenhado em update_panel)
        self.limit_rows = {}
        # colunas fixas medidas com o texto mais largo: rótulo | barra | reset
        y = py + 56
        probe = c.create_text(14, y, anchor="w", text=max((_t("Sessão"), _t("Semana")), key=len) + "  ~100%",
                              font=self.font_small)
        lx0 = c.bbox(probe)[2] + 8
        c.itemconfigure(probe, anchor="e", text=_t("reseta {h}", h=max((_t(d) for d in DAYS), key=len) + " 00:00"))
        c.coords(probe, self.W - 14, y)
        lx1 = max(lx0 + 4, c.bbox(probe)[0] - 8)
        c.delete(probe)
        for i, (key, label) in enumerate((("sessao", _t("Sessão")), ("semana", _t("Semana")))):
            y = py + 52 + 4 + i * 13
            back = f"lim_t_{key}"       # tags: trilha e preenchimento (redesenhado em update_limits)
            rounded_rect(c, lx0, y - 3, lx1, y + 3, 3, BAR_BG, tag=back)
            self.limit_rows[key] = (
                label,
                c.create_text(14, y, anchor="w", fill=MUTED, font=self.font_small),
                f"lim_{key}",
                c.create_text(self.W - 14, y, anchor="e", fill=MUTED, font=self.font_small),
                lx0, lx1, y, back)
        self.refresh_look()
        self.update_panel()

    def art_img(self, key, boss=False, status=None):
        """Imagem (em cache) de um desenho do arte.py; com status, tingida na cor dele."""
        ck = (key, boss, status)
        if ck not in self.art:
            pal = art.BOSS_PAL if boss else art.PAL
            if status:      # tingir a paleta = tingir cada pixel (o contorno escuro fica intacto)
                pal = visual.tint(pal, STATUS_COLOR[status], 0.5)
            self.art[ck] = render_grid(art.all_art()[key], pal, self.bpx if boss else self.px)
        return self.art[ck]

    def load_images(self):
        stage = self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)]
        if stage.get("sheet") and "estados" not in stage and "erro" not in stage:
            self.prepare_sheet(stage)          # na thread; até lá fica o visual anterior (ou o do Slime)
            if getattr(self, "frame_maps", None) is not None:
                return
            stage = builtin_characters()[0].stages[0]
        try:
            if stage.get("erro"):
                raise ValueError(stage["erro"])
            # herói de spritesheet: um k só no estágio (mesma escala e mesmo pivô em todos os estados)
            all_ = [sp for specs in stage.get("estados", {}).values() for sp in specs] or stage["frames"]
            h = max(spec_height(sp) for sp in all_)
            k = max(1, -(-h // 16))
            # só os mapas de pixels; as imagens saem de refresh_look (com os itens por cima)
            self.frame_maps = [spec_to_map(s, k) for s in stage["frames"]]
            self.blink_map = spec_to_map(stage["blink"]) if stage["blink"] else None
            self.sleep_map = spec_to_map(stage["sleep"]) if stage["sleep"] else None
        except Exception as e:
            if self.char.key == "slime":
                raise
            log(f"erro carregando imagens de '{self.char.key}': {e}; voltando para o Slime")
            self.run["char"] = "slime"
            return self.load_images()
        self.hero_k, self.hero_px = k, max(1, round(self.px * 16 / h))
        self.state_maps = {e: [spec_to_map(sp, k) for sp in specs]   # os heróis antigos não têm "estados"
                            for e, specs in stage.get("estados", {}).items()}
        self.fx_cache = {}         # estados compostos: (estado, assinatura) -> [quadro][fase]
        self.stage_title = stage["title"]

    def prepare_sheet(self, stage):
        """Decodifica e corta a folha numa thread (só Python puro); o Tk volta na thread principal pelo after."""
        if stage.get("thread") is None:
            stage["thread"] = threading.Thread(target=complete_stage, args=(stage,), daemon=True)
            stage["thread"].start()
            self.root.after(0, lambda: self.floater(_t("preparando herói…"), MUTED))
            self.root.after(100, lambda: self.wait_sheet(stage))

    def wait_sheet(self, stage):
        if stage["thread"].is_alive():
            self.root.after(100, lambda: self.wait_sheet(stage))
            return
        if self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)] is stage:
            self.load_images()
            self.refresh_look()

    def refresh_look(self, k: int = None, hero_pixels: int = None):
        """Recompõe as imagens do pet com os looks dos itens. Só quando a lista muda, nunca no tick.
        Herói de altura H: k = H/16 e px_heroi = max(1, round(px*16/H)) (padrão: 16 px, k=1, px)."""
        k = k or getattr(self, "hero_k", 1)
        hero_pixels = hero_pixels or getattr(self, "hero_px", None) or self.px
        looks = pet_looks(self.run)
        arts = item_arts()
        color = STATUS_COLOR.get(self.pet_status)
        flip = self.flip
        if hasattr(self, "flip_var"):
            self.flip_var.set(flip)

        # looks elementais animam em FASES quadros; sem eles, uma fase só (nenhuma imagem a mais)
        phases = range(visual.PHASES if visual.has_anim(looks) else 1)

        def pmap(pm, phase):
            m = visual.compose(pm, looks, arts, phase, k)
            m = visual.tint(m, color, 0.5) if color else m
            return {(16 * k - 1 - x, y): c for (x, y), c in m.items()} if flip else m   # espelha o mapa final   # com status, o pet fica na cor dele (todas as fases)

        def img(m):
            im, self.below = render_map(m, hero_pixels, k)
            return im

        maps = [[pmap(pm, j) for j in phases] for pm in self.frame_maps]
        self.look_maps = [q[0] for q in maps]                    # fase 0 de cada quadro
        # imagens indexadas [quadro_do_heroi][fase]; o tick só escolhe qual mostrar
        self.frames_fx = [[img(m) for m in q] for q in maps]
        self.blink_fx = [img(pmap(self.blink_map, j)) for j in phases] if self.blink_map else None
        self.sleep_fx = ([img(pmap(self.sleep_map, j)) for j in phases] if self.sleep_map
                         else (self.blink_fx or self.frames_fx[0]))
        # estados da folha: [quadro][fase], compostos na 1ª vez que aparecem (só idle e o atual saem aqui);
        # cache por (estado, itens, status, escala), então tirar e pôr o mesmo status não recompõe
        sig = (tuple((i["key"], i.get("rar")) for i in self.run["items"]), self.pet_status, k, hero_pixels, flip)
        self.fx_cache = {ck: v for ck, v in getattr(self, "fx_cache", {}).items() if ck[1][0] == sig[0] and ck[1][4] == flip}
        self.fx_cache[("idle", sig)] = self.frames_fx
        swap = {"run_r": "run_l", "run_l": "run_r"} if flip else {}
        self.fx_compose = lambda e: [[img(pmap(pm, j)) for j in phases] for pm in self.state_maps[swap.get(e, e)]]
        self.fx_sig = sig
        self.states_fx = _StatesFx(self, getattr(self, "state_maps", {}))
        if getattr(self, "state_seen", None) in self.states_fx:
            self.states_fx[self.state_seen]
        self.canvas.itemconfigure(self.sprite, image=self.frames_fx[0][0])
        self.place_pet(0, 0)

    @property
    def flip(self):
        return bool(self.state.get("virar", {}).get(self.run["char"]))

    def toggle_flip(self):
        self.state.setdefault("virar", {})[self.run["char"]] = bool(self.flip_var.get())
        self.refresh_look()
        self.save()

    def set_pet_status(self, s):
        """Status do pet no painel e na tinta; só recompõe as imagens quando muda (nunca no tick)."""
        if s != self.pet_status:
            self.pet_status = s
            self.refresh_look()
            self.update_panel()

    def place_pet(self, dx, dy):
        self.canvas.coords(self.sprite, self.pcx + dx, self.base_y + self.below + dy)

    def update_panel(self):
        run = self.run
        st = M.stats(run)
        self.canvas.itemconfigure(self.title_txt, text=f"{_t(self.stage_title)}  ·  Run #{run['id']}")
        self.canvas.itemconfigure(self.hp_txt, text=f"♥ {run['hp']}/{st['maxhp']}")
        x0 = self.canvas.bbox(self.hp_txt)[0] - 8
        self.canvas.coords(self.status_txt, x0, self.status_y)
        self.canvas.itemconfigure(self.status_txt, text=_t(self.pet_status) if self.pet_status else "",
                                  fill=STATUS_COLOR.get(self.pet_status, MUTED))
        self.canvas.itemconfigure(
            self.info_txt,
            text=f"{depth(run)}   ATK {st['atk']}  DEF {st['def']}   $ {run['gold']}")
        cost = M.room_cost(run)
        self.bar_target = min(1.0, run["energy"] / cost) if cost else 0
        if getattr(self, "bar_frac", None) is None:     # 1º desenho: já no valor, sem deslizar
            self.bar_frac = self.bar_target
        self.draw_energy(time.time())
        self.update_limits()

    def draw_energy(self, now):
        """Barra de energia: o preenchimento desliza até o alvo (tick) e um brilho corre pela parte cheia."""
        c = self.canvas
        x0, y = self.bar_x0, self.bar_y
        x1 = round(x0 + (self.bar_x1 - x0) * self.bar_frac)
        c.delete(self.bar)
        rounded_rect(c, x0, y, x1, y + 6, 3, ENERGY, tag=self.bar)
        if x1 - x0 > 14:                                 # brilho de 4 px, uma passada a cada BRILHO_S
            bx = x0 + 3 + (now % SHIMMER_S) / SHIMMER_S * (x1 - x0 - 10)
            c.create_rectangle(round(bx), y + 1, round(bx) + 4, y + 5, fill=ENERGY_SHIMMER, width=0, tags=self.bar)

    def update_limits(self):
        now = time.time()
        for key, (label, txt, fill, rtxt, lx0, lx1, y, back) in self.limit_rows.items():
            pct, reset, est, tok = limit_view(key, self.limits, self.state, now)
            self.canvas.itemconfigure(rtxt, text=_t("reseta {h}", h=fmt_reset(reset, now)) if reset else "")
            self.canvas.delete(fill)
            if pct is None:                 # sem fator: tokens da janela, barra = fração do seu pico
                self.canvas.itemconfigure(txt, text=f"{label}  {fmt(tok)}" if tok else f"{label}  —")
                p = peak(self.state, key, tok)
                if tok and p:
                    rounded_rect(self.canvas, lx0, y - 3, round(lx0 + (lx1 - lx0) * tok / p), y + 3, 3,
                                          PEAK_COLOR, tag=fill)
                continue
            self.canvas.itemconfigure(txt, text=f"{label}  {'~' if est else ''}{round(pct)}%")
            frac = max(0.0, min(1.0, pct / 100))
            rounded_rect(self.canvas, lx0, y - 3, round(lx0 + (lx1 - lx0) * frac), y + 3, 3, limit_color(pct),
                                  tag=fill)

    def refresh_limits(self):
        """Relê limites.json (opcional), calibra a estimativa com leitura oficial nova e redesenha."""
        now = time.time()
        self.limits = read_limits(DATA_DIR / "limites.json", now)
        calibrate(self.state, self.limits, now)
        self.update_limits()

    def build_menu(self):
        """Só as variáveis; o menu (pixel art, `on_menu`) e a grade de heróis (`show_heroes`) nascem ao abrir."""
        self.char_var = tk.StringVar(value=self.meta.get("next_char", "slime"))
        self.size_var = tk.StringVar(value=self.state["size"])
        self.mode_var = tk.StringVar(value=self.state["mode"])
        self.lang_var = tk.StringVar(value=self.state["lang"])
        self.top_var = tk.BooleanVar(value=bool(self.state["topmost"]))
        self.usage_var = tk.BooleanVar(value=bool(self.state.get("so_com_uso")))
        self.startup_var = tk.BooleanVar(value=startup_shortcut().exists())
        self.flip_var = tk.BooleanVar(value=self.flip)
        for attr in WINDOW_ATTRS:
            setattr(self, attr, None)
        self.thumb_thread = None
        self.hero_cards, self.hero_thumb_lbl, self.thumbs, self.icons, self.fonts = {}, {}, {}, {}, {}

    def fill_char_menu(self):
        """Conquista nova ou personagens recarregados: refaz a grade de heróis se estiver aberta."""
        if self.heroes_win is not None:
            self.show_heroes()

    # ------------------------------------------------------- menu em pixel art
    def pixel_box(self, x, y, closes=True):
        """Janela sem borda, moldura dourada de 2 px com cantos arredondados em degraus; devolve (janela, miolo).
        Com `fecha`, fecha com Esc ou ao perder o foco (clique fora). Quem chama posiciona de novo se crescer."""
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        try:
            w.attributes("-transparentcolor", TRANSPARENT)
            corte = TRANSPARENT
        except tk.TclError:
            corte = PANEL_BG                # fora do Windows: cantos no fundo escuro
        w.configure(bg=corte)
        backdrop = tk.Canvas(w, bg=corte, highlightthickness=0, bd=0)
        backdrop.place(x=0, y=0, relwidth=1, relheight=1)      # criado antes do miolo: fica por baixo dele

        def draw(e):
            backdrop.delete("all")
            rounded_rect(backdrop, 0, 0, e.width, e.height, WINDOW_R, PANEL_EDGE, GOLD, 2)
            rounded_rect(backdrop, 3, 3, e.width - 3, e.height - 3, WINDOW_R - 3, PANEL_BG)
        backdrop.bind("<Configure>", draw)
        inner = tk.Frame(w, bg=PANEL_BG, padx=4, pady=4)
        inner.pack(padx=5, pady=5)          # fora da área dos cantos
        if closes:
            w.bind("<Escape>", lambda e: self.close_win(w))
            w.bind("<FocusOut>", lambda e: self.close_win(w) if e.widget is w else None)
        w.geometry(f"+{x}+{y}")
        return w, inner

    def place_win(self, w, x, y):
        """Põe a janela em (x, y) sem sair da tela (sem espaço embaixo, abre para cima) e pega o foco."""
        w.update_idletasks()
        vx0, vy0, vx1, vy1 = self.screen()
        ww, wh = w.winfo_width(), w.winfo_height()
        x = max(vx0, min(x, vx1 - ww))
        y = max(vy0, y if y + wh <= vy1 else y - wh)
        w.geometry(f"+{x}+{y}")
        w.focus_force()

    def screen(self):
        """Retângulo da tela virtual (todos os monitores; x negativo = monitor à esquerda do principal)."""
        r = self.root
        x, y = r.winfo_vrootx(), r.winfo_vrooty()
        return x, y, x + r.winfo_vrootwidth(), y + r.winfo_vrootheight()

    def close_win(self, w):
        if w is None:
            return
        for attr in WINDOW_ATTRS:
            if getattr(self, attr) is w:
                setattr(self, attr, None)
        if self.heroes_win is None:
            self.hero_cards, self.hero_thumb_lbl = {}, {}
        try:
            w.destroy()
        except tk.TclError:
            pass

    def menu_icon(self, key):
        ck = ("menu", key)
        if ck not in self.art:
            self.art[ck] = render_grid(art.all_art()[key], art.PAL, 2)
        return self.art[ck]

    def hover(self, widgets, text, fg, on_click):
        """Hover: fundo mais claro e texto dourado; clique em qualquer parte. Cartão (`cartao`) troca só o miolo."""
        base = {wd: None if hasattr(wd, "backdrop") else wd.cget("bg") for wd in widgets}

        def paint(on):
            for wd in widgets:
                if base[wd] is None:
                    wd.backdrop(MENU_HOVER if on else CARD_BG)
                else:
                    wd.configure(bg=MENU_HOVER if on else base[wd])
            text.configure(fg=GOLD if on else fg)
        for wd in widgets:
            wd.configure(cursor="hand2")
            wd.bind("<Enter>", lambda e: paint(True))
            wd.bind("<Leave>", lambda e: paint(False))
            wd.bind("<Button-1>", lambda e: on_click())

    def menu_row(self, parent, icon, text, cmd, fg=TEXT):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x")
        ico = tk.Label(row, image=self.menu_icon(icon), bg=PANEL_BG, width=22, height=20)
        ico.pack(side="left")
        t = tk.Label(row, text=text, bg=PANEL_BG, fg=fg, font=self.font, anchor="w", padx=4)
        t.pack(side="left", fill="x", expand=True)
        self.hover((row, ico, t), t, fg, lambda: self.menu_do(cmd))

    def menu_chips(self, parent, label, options, var, cmd):
        """Botões segmentados no próprio menu (sem submenu); o escolhido fica dourado."""
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=_t(label), bg=PANEL_BG, fg=MUTED, font=self.font_small, width=8, anchor="w").pack(side="left")
        for value, text in options.items():
            self.chip(row, _t(text), var.get() == value, lambda v=value: (var.set(v), self.menu_do(cmd))).pack(
                side="left", padx=(0, 3))

    def chip(self, parent, text, sel=False, cmd=None):
        """Botão pílula arredondado (Canvas): dourado se escolhido, hover mais claro. `cv.pintar(sel)` troca o estado."""
        cv = tk.Canvas(parent, bg=PANEL_BG, highlightthickness=0, bd=0, cursor="hand2" if cmd else "")
        t = cv.create_text(0, 0, anchor="nw", text=text, font=self.font_small)
        x0, y0, x1, y1 = cv.bbox(t)
        larg, alto = x1 - x0 + 12, y1 - y0 + 4
        cv.configure(width=larg, height=alto)
        cv.coords(t, 6, 2)
        st = {"sel": sel}

        def paint(sel=None, hot=False):
            if sel is not None:
                st["sel"] = sel
            cv.delete("chip")
            backdrop = GOLD if st["sel"] else MENU_HOVER if hot else BAR_BG
            rounded_rect(cv, 0, 0, larg, alto, CARD_R, backdrop, tag="chip")
            cv.tag_raise(t)
            cv.itemconfigure(t, fill=PANEL_BG if st["sel"] else GOLD if hot else TEXT)
        paint()
        if cmd:
            cv.bind("<Button-1>", lambda e: cmd())
            cv.bind("<Enter>", lambda e: paint(hot=True))
            cv.bind("<Leave>", lambda e: paint())
        cv.paint = paint
        return cv

    def card_box(self, parent, edge=PANEL_EDGE, larg=None, alto=None, thickness=2):
        """Cartão arredondado: Canvas com o fundo desenhado (CARD_BG). Os filhos usam bg=CARD_BG e ficam a
        CARTAO_PAD da borda. Com larg/alto, tamanho fixo. `cv.fundo(cor)` troca a cor do miolo (hover)."""
        cv = tk.Canvas(parent, bg=PANEL_BG, highlightthickness=0, bd=0, width=larg or 1, height=alto or 1)
        if larg:
            cv.pack_propagate(False)
        st = {"cor": CARD_BG}

        def draw(e):
            cv.delete("cartao")
            rounded_rect(cv, 0, 0, e.width, e.height, CARD_R, st["cor"], edge, thickness, tag="cartao")
            cv.tag_lower("cartao")

        def backdrop(color):
            st["cor"] = color
            cv.itemconfigure("cartao_f", fill=color)
        cv.bind("<Configure>", draw)
        cv.backdrop = backdrop
        return cv

    def text_width(self, text, font):
        """Largura do texto em px (tkinter falso dos testes: 6 px por letra)."""
        tkf = getattr(tk, "font", None)
        if tkf is None:
            return 6 * len(text)
        if font not in self.fonts:
            self.fonts[font] = tkf.Font(root=self.root, font=font)
        return self.fonts[font].measure(text)

    def shorten(self, text, font, larg):
        """O texto se couber em `larg` px; senão cortado com "…" (mostre o inteiro com `dica`)."""
        if self.text_width(text, font) <= larg:
            return text
        while text and self.text_width(text + "…", font) > larg:
            text = text[:-1]
        return text.rstrip() + "…"

    def tooltip(self, wd, text):
        """Balão pixel com o texto inteiro enquanto o mouse está em cima de `wd` (para o que foi encurtado)."""
        st = {}

        def opens(e):
            closes(e)
            w, f = self.pixel_box(e.x_root + 12, e.y_root + 14, closes=False)
            tk.Label(f, text=text, bg=PANEL_BG, fg=TEXT, font=self.font_small).pack()
            st["w"] = w

        def closes(e):
            if st.get("w") is not None:
                st.pop("w").destroy()
        wd.bind("<Enter>", opens, add="+")
        wd.bind("<Leave>", closes, add="+")

    def progress_bar(self, parent, larg, alto, frac=0.0, color=GOLD):
        """Barra de progresso arredondada (Canvas); `cv.set(frac, cor)` redesenha o preenchimento."""
        cv = tk.Canvas(parent, width=larg, height=alto, bg=PANEL_BG, highlightthickness=0, bd=0)
        rounded_rect(cv, 0, 0, larg, alto, alto // 2, BAR_BG, tag="trilha")

        def set_(frac, color=color):
            cv.delete("cheio")
            rounded_rect(cv, 0, 0, round(larg * max(0.0, min(1.0, frac))), alto, alto // 2, color, tag="cheio")
        set_(frac)
        cv.set = set_
        return cv

    def menu_sep(self, parent):
        tk.Frame(parent, bg=PANEL_EDGE, height=2).pack(fill="x", pady=4)

    def on_menu(self, e):
        self.close_win(self.menu_win)
        w, f = self.pixel_box(e.x_root, e.y_root)
        self.menu_win = w
        run, st = self.run, M.stats(self.run)
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x")
        self.menu_thumb = map_img(self.look_maps[0], 36)     # referência: o tk não guarda a imagem sozinho
        tk.Label(head, image=self.menu_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 6))
        tk.Label(head, text=f"{_t(self.char.name)}  ·  {_t(self.stage_title)}", bg=PANEL_BG, fg=GOLD,
                 font=self.font, anchor="w").pack(fill="x")
        tk.Label(head, text=f"{depth(run)}    ♥ {run['hp']}/{st['maxhp']}",
                 bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        self.menu_sep(f)
        for icon, text, cmd in (("estrela_cadente", "Perfil", self.show_perfil),
                                ("grimorio", "Status", self.show_stats),
                                ("lapide", "Cemitério", self.show_graveyard),
                                ("coroa", "Conquistas", self.show_achievements),
                                ("pocao", "Itens", self.show_items),
                                ("espada_osso", "Heróis…", self.show_heroes)):
            self.menu_row(f, icon, _t(text), cmd)
        self.menu_sep(f)
        self.menu_chips(f, "Tamanho", {n: n for n in SIZES}, self.size_var, self.change_size)
        self.menu_chips(f, "Modo", MODES, self.mode_var, self.change_mode)
        self.menu_chips(f, "Idioma", i18n.LANGS, self.lang_var, self.change_lang)
        options = [("Sempre por cima", self.top_var, self.toggle_top),
                  ("Virar herói", self.flip_var, self.toggle_flip),
                  ("Aparecer só com uso", self.usage_var, self.toggle_usage)]
        if os.name == "nt":
            options.append(("Abrir com o Windows", self.startup_var, self.toggle_startup))
        for text, var, fn in options:
            self.menu_row(f, "caixa_ok" if var.get() else "caixa", _t(text),
                          lambda v=var, fn=fn: (v.set(not v.get()), fn()))
        self.menu_sep(f)
        self.menu_row(f, "caveirinha", _t("Desistir da run"), self.give_up, fg=HURT)
        self.menu_sep(f)
        self.menu_row(f, "bau", _t("Abrir pasta de personagens"), self.open_chars)
        self.menu_row(f, "redemoinho", _t("Recarregar personagens"), self.reload_chars)
        self.menu_row(f, "escada", _t("Sair"), self.quit)
        self.place_win(w, e.x_root, e.y_root)

    def menu_do(self, cmd):
        self.close_win(self.menu_win)
        cmd()

    # ------------------------------------------------------- grade de heróis
    def hero_thumb(self, c, ok, side=64):
        """Idle do 1º estágio ampliado (bloqueado: silhueta). None enquanto a folha ainda é cortada na thread."""
        stage = c.stages[0]
        ck = (id(stage), ok) if side == 64 else (id(stage), ok, side)
        if ck not in self.thumbs:
            pm = hero_idle(c.key) if not stage.get("frames") else spec_to_map(stage["frames"][0])
            if pm is None:
                return None
            self.thumbs[ck] = map_img(pm if ok else {p: "#0b0b14" for p in pm}, side)
        return self.thumbs[ck]

    def cut_sheets(self):
        """Corta numa thread as folhas que a grade ainda não tem; depois só troca as miniaturas."""
        pend = [c.stages[0] for c in self.chars.values()
                if not c.stages[0].get("frames") and "erro" not in c.stages[0]
                and (id(c.stages[0]), True) not in self.thumbs and (id(c.stages[0]), False) not in self.thumbs]
        if not pend or self.thumb_thread is not None:
            return
        self.thumb_thread = threading.Thread(target=lambda: [complete_stage(s) for s in pend], daemon=True)
        self.thumb_thread.start()

        def wait():
            if self.thumb_thread.is_alive():
                self.root.after(150, wait)
                return
            self.thumb_thread = None
            for key, lbl in list(self.hero_thumb_lbl.items()):
                c = self.chars.get(key)
                img = c and self.hero_thumb(c, self.is_unlocked(c))
                if img:
                    lbl.configure(image=img, text="", height=72)
        self.root.after(150, wait)

    def window(self, attr, title):
        """Janela pixel (fecha a anterior do mesmo tipo) com título dourado e um x; devolve (janela, miolo)."""
        self.close_win(getattr(self, attr))
        w, f = self.pixel_box(self.root.winfo_x(), self.root.winfo_y())
        setattr(self, attr, w)
        top = tk.Frame(f, bg=PANEL_BG)
        top.pack(fill="x")
        name = tk.Label(top, text=title, bg=PANEL_BG, fg=GOLD, font=self.font)
        name.pack(side="left")
        self.make_draggable(w, attr, top, name)
        shutdown = tk.Label(top, text=" x ", bg=PANEL_BG, fg=MUTED, font=self.font)
        shutdown.pack(side="right")
        self.hover((shutdown,), shutdown, MUTED, lambda: self.close_win(w))
        return w, f

    def make_draggable(self, w, attr, *straps):
        """Arrasta a janela segurando a barra de título (`alcas`) e lembra a posição em state["janelas"][attr]."""
        takes = {}

        def squeeze(e):
            takes["d"] = (e.x_root - w.winfo_x(), e.y_root - w.winfo_y())

        def move(e):
            if "d" in takes:
                x, y = e.x_root - takes["d"][0], e.y_root - takes["d"][1]
                w.geometry(f"+{x}+{y}")
                self.state.setdefault("janelas", {})[attr] = [x, y]
        for a in straps:
            a.configure(cursor="fleur")
            a.bind("<Button-1>", squeeze)
            a.bind("<B1-Motion>", move)
        w.progress_bar = straps[0]          # para os testes

    def beside(self, w):
        """Na posição lembrada (arrastada antes), se ainda estiver na tela; senão ao lado do pet:
        à esquerda, ou à direita se não couber."""
        w.update_idletasks()
        attr = next((a for a in WINDOW_ATTRS if getattr(self, a) is w), None)
        pos = (self.state.get("janelas") or {}).get(attr)
        vx0, vy0, vx1, vy1 = self.screen()
        if pos and vx0 <= pos[0] < vx1 and vy0 <= pos[1] < vy1:   # ponytail: retângulo da tela virtual, não por monitor
            self.place_win(w, pos[0], min(pos[1], max(vy0, vy1 - w.winfo_height())))
            return
        x, y = self.root.winfo_x(), self.root.winfo_y()
        left = x - w.winfo_width() - 6
        self.place_win(w, left if left >= vx0 else x + self.W + 6, y)

    def icon(self, grid, s=2, pal=None, glow=None, dark=False, dim=False, side=None):
        """Grade de arte em escala s (cache): brilho de raridade, silhueta (bloqueado) ou esmaecida (consumido).
        Com `lado`, a escala é a maior inteira que cabe num quadrado de `lado` px (ícones do mesmo tamanho)."""
        ck = (id(grid), s, id(pal), glow, dark, dim, side)
        if ck not in self.icons:
            pm = visual.grid_to_map(grid, pal or art.PAL)
            if glow:
                pm = visual.contour(pm, glow)
            if dark:
                pm = {p: "#0b0b14" for p in pm}
            if dim:
                pm = visual.tint(pm, PANEL_BG, 0.55)
            x0, y0, x1, y1 = visual.bbox(pm)
            self.icons[ck] = map_img(pm, side or s * max(x1 - x0, y1 - y0))
        return self.icons[ck]

    def show_heroes(self):
        w, f = self.window("heroes_win", _t("Herói da próxima run"))
        sections = [("Heróis", [(k, c) for k, c in self.chars.items() if own_hero(k)]),
                  ("Comunidade", [(k, c) for k, c in self.chars.items() if not own_hero(k)])]
        for n, (title, lst) in enumerate(s for s in sections if s[1]):
            if n:
                self.menu_sep(f)
            tk.Label(f, text=_t(title), bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x", pady=(4, 0))
            grid = tk.Frame(f, bg=PANEL_BG)
            grid.pack(pady=(4, 0))
            for i, (key, c) in enumerate(lst):
                self.hero_card(grid, key, c).grid(row=i // HERO_COLS, column=i % HERO_COLS, padx=3, pady=3)
        self.cut_sheets()
        self.beside(w)

    def hero_card(self, parent, key, c):
        ok, sel = self.is_unlocked(c), key == self.char_var.get()
        card = self.card_box(parent, GOLD if sel else PANEL_EDGE, HERO_CARD_W, HERO_CARD_H)
        img = self.hero_thumb(c, ok)
        pic = tk.Label(card, image=img or "", text="" if img else "…", bg=CARD_BG, fg=MUTED,
                       font=self.font, height=72 if img else 4)
        pic.pack(pady=(CARD_PAD, 0))
        self.hero_thumb_lbl[key] = pic
        name_ = _t(c.name)
        short = self.shorten(name_, self.font, HERO_CARD_W - 2 * CARD_PAD)
        name = tk.Label(card, text=short, bg=CARD_BG, fg=GOLD if sel else TEXT if ok else MUTED, font=self.font)
        name.pack()
        if ok:
            info = tk.Label(card, text=M.fx_text(c.trait) if c.trait else _t("sem traço"), bg=CARD_BG,
                            fg=MUTED, font=self.font_small, wraplength=HERO_CARD_W - 2 * CARD_PAD)
            info.pack()

            def pick():
                self.close_win(self.heroes_win)
                self.char_var.set(key)
                self.change_character()
            self.hover((card, pic, name, info), name, GOLD if sel else TEXT, pick)
            if short != name_:
                self.tooltip(name, name_)
        else:
            pick = None             # bloqueado: nada clicável
            tk.Label(card, text=_t(M.ACHIEVEMENTS[c.unlock]), image=self.menu_icon("cadeado"), compound="left",
                     bg=CARD_BG, fg=MUTED, font=self.font_small, wraplength=HERO_CARD_W - 24 - 2 * CARD_PAD).pack()
        self.hero_cards[key] = pick
        return card

    # -------------------------------------------------------------- eventos
    def on_press(self, e):
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())
        self._moved = False

    def on_drag(self, e):
        if self._drag:
            self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")
            self._moved = True

    def on_release(self, e):
        if self._moved:
            self.state["pos"] = [self.root.winfo_x(), self.root.winfo_y()]
        elif (abs(e.x - self.pcx) < self.T / 2 and self.base_y - self.T <= e.y <= self.base_y
              and not self.run["dead"]):
            self.hop = [-3, -6, -8, -6, -3, 0]
            self.floater("<3", "#ff8fb1")
            self.state_tmp = ("waving", time.time() + 1.0)
        self._drag = None

    def change_character(self):
        key = self.char_var.get()
        self.meta["next_char"] = key
        name = _t(self.chars[key].name)
        run = self.run
        if run["floor"] == 1 and run["room"] == 0 and not run["dead"]:
            self.new_run()      # run nem começou: troca na hora
        else:
            self.popup([_t("{nome} entra na próxima run.", nome=name)], 4000)

    def change_size(self):
        self.state["size"] = self.size_var.get()
        self.build()
        if self.run["dead"]:
            self.show_tomb()

    def change_mode(self):
        self.state["mode"] = self.mode_var.get()
        if self.state["mode"] == "auto" and self.run["pending"] and not self.run["dead"]:
            self.finish_pending(M.resolve_pending(self.run, self.meta))
        self.save()

    def change_lang(self):
        """Troca o idioma: redesenha o HUD e reabre as janelas que estavam abertas (o menu fecha)."""
        self.state["lang"] = self.lang_var.get()
        i18n.set_lang(self.state["lang"])
        opened = [a for a in WINDOW_ATTRS if a != "menu_win" and getattr(self, a) is not None]
        self.build()
        if self.run["dead"]:
            self.show_tomb()
        for a in opened:
            getattr(self, REOPEN[a])()
        if self.choice_win is not None:
            since = self.pending_since
            self.close_choice()
            self.pending_since = since
            self.show_choice()
        self.save()

    def toggle_top(self):
        self.state["topmost"] = bool(self.top_var.get())
        self.root.attributes("-topmost", self.state["topmost"])

    def toggle_usage(self):
        self.state["so_com_uso"] = bool(self.usage_var.get())
        self.opened_at = time.time()            # ligou agora: não some na hora
        self.save()

    def toggle_startup(self):
        try:
            startup_shortcut(create=bool(self.startup_var.get()))
        except OSError as e:
            log(f"erro no atalho de inicialização: {e}")
        self.startup_var.set(startup_shortcut().exists())

    def adjust_visibility(self, now):
        """"Aparecer só com uso": esconde depois de ESCONDER_S sem tokens (nunca no meio de uma sala ou com
        escolha aberta) e mostra de novo no 1º token. Escondido o jogo continua; nada se perde."""
        stopped = now - max(self.state["last_fed"], self.opened_at) > HIDE_S
        esconder = bool(self.state.get("so_com_uso")) and stopped and now >= self.busy_until and not self.run["pending"]
        if esconder == self.escondido:
            return
        self.escondido = esconder
        if esconder:
            for attr in WINDOW_ATTRS:
                self.close_win(getattr(self, attr))
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.attributes("-topmost", self.state["topmost"])

    def give_up(self):
        if self.run["dead"]:
            return
        self.run["pending"] = None             # a oferta morre junto com a run
        self.close_choice()
        ev = {"lines": []}
        M.die(self.run, self.meta, ev, "Desistiu", "desistiu")
        self.log_run("Desistiu", True)
        self.save()
        self.new_run()

    def open_chars(self):
        CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(CHARACTERS_DIR))  # type: ignore[attr-defined]
            else:
                self.popup([str(CHARACTERS_DIR)], 6000)
        except OSError as e:
            log(f"não abriu a pasta: {e}")

    def reload_chars(self):
        self.chars = all_characters()
        if self.run["char"] not in self.chars:
            self.run["char"] = "slime"
        self.fill_char_menu()
        self.build()
        if self.run["dead"]:
            self.show_tomb()
        self.floater(_t("{n} personagens", n=len(self.chars)), MUTED)


    def show(self):
        """Pela bandeja: aparece (mesmo com "Aparecer só com uso", conta ESCONDER_S de novo) e vem para a frente."""
        self.opened_at = time.time()
        self.adjust_visibility(self.opened_at)
        self.root.lift()

    def listen_tray(self):
        """Cliques da bandeja chegam por fila (a thread dela não pode mexer no Tk). 0 = mostrar, 1 = sair."""
        if not self.tray:
            return
        while not self.tray.events.empty():
            if self.tray.events.get():
                return self.quit()
            self.show()
        self.root.after(150, self.listen_tray)

    def quit(self):
        self.save()
        if self.tray:
            self.tray.shutdown()
            self.tray = None
        self.root.destroy()

    def _on_error(self, *exc):
        log("erro: " + "".join(traceback.format_exception(*exc)))

    # ------------------------------------------------------- tokens/energia
    def fake_tokens(self):
        if self.rng.random() < 0.6:
            raw = self.rng.randint(100_000, 1_500_000)
            add_usage(self.state, time.time(), raw * 0.35)
            return raw * 0.35, raw
        return 0.0, 0

    def poll(self):
        try:
            xp, raw = self.fake_tokens() if self.demo else self.reader.poll()
            now = time.time()
            if raw > 0:
                self.feed(xp, raw)
            elif (now - self.state["last_fed"] > REST_AFTER_S and not self.run["dead"]
                  and now - self.last_rest_heal > 120):
                st = M.stats(self.run)
                if self.run["hp"] < st["maxhp"]:
                    self.run["hp"] += 1
                    self.update_panel()
                self.last_rest_heal = now
            if now - self.last_save > SAVE_EVERY_S:
                self.save()
            self.refresh_limits()
            self.adjust_visibility(now)
        except Exception:
            log("erro lendo tokens: " + traceback.format_exc())
        self.root.after(1000 if self.demo else POLL_MS, self.poll)

    def feed(self, xp: float, raw: int):
        self.state["tokens_total"] += raw
        self.state["xp_total"] += xp
        today = date.today().isoformat()
        self.state["daily"][today] = self.state["daily"].get(today, 0) + raw
        self.state["last_fed"] = time.time()
        M.add_energy(self.run, xp)
        if time.time() >= self.busy_until and not self.run["dead"]:
            self.floater(f"+{fmt(raw)}", ENERGY)
        self.update_panel()

    # -------------------------------------------------------------- salas
    def play_room(self):
        ev = M.enter_room(self.run, self.meta, self.rng, self.char.stage_floors,
                          mode=self.state["mode"])
        steps = []
        t = 0

        def at(ms, fn):
            steps.append((ms, fn))

        self._last_kind = [ev["kind"]]               # só para o teste
        kind = ev["kind"]
        foes = ev.get("foes") or []
        name_color = {"boss": HURT, "monster": TEXT, "horde": TEXT, "mimic": HURT, "stairs": CYAN}.get(kind, GOLD)

        def new_room():
            self.set_pet_status(None)                  # status do pet não passa de uma sala para outra
            self.update_panel()
        at(0, new_room)
        if foes:
            at(0, lambda: self.show_foes(foes))
        else:
            at(0, lambda: self.show_foe(ev.get("sprite"), ev.get("boss", False)))
        at(0, lambda: self.floater(_t(ev["name"]), name_color, x=self.fcx, life=22, top=True))
        if ev.get("cura_item"):                        # cura_sala / cura_andar dos itens
            at(250, lambda: self.floater(f"+{ev['cura_item']} ♥", GOOD))
        t = 500

        if kind in ("monster", "boss", "mimic", "horde"):
            hits = ev["hits"]
            # quem já morreu depois de cada passo (contando a lista inteira, mesmo os passos não mostrados)
            hp = [f["hp_max"] for f in foes]
            dead_until, status_until, s = [], [], None
            for h in hits:
                if h["target"] != "pet" and not h["skip"]:
                    hp[h["target"]] -= h["dmg"]
                if h["target"] == "pet" and h["status"] and not h["skip"]:
                    s = h["status"]                    # último status do pet até aqui (vale p/ passos pulados)
                dead_until.append([i for i, v in enumerate(hp) if v <= 0])
                status_until.append(s)
            idx = list(range(len(hits)))
            if len(idx) > 12:                          # lutas longas: os 11 primeiros passos e o último
                idx = idx[:11] + [idx[-1]]
            for k in idx:
                at(t, lambda h=hits[k], dead=dead_until[k], s=status_until[k]: self.anim_hit(h, dead, s))
                t += 380
            if ev["won"]:
                at(t, lambda: self.hide_foe(burst=True))
                t += 300
                at(t, lambda: self.floater(f"+{ev.get('gold', 0)} $", GOLD, x=self.fcx))
                t += 450
            elif ev.get("empate"):
                at(t, lambda: (self.floater(_t("empate"), MUTED, x=self.fcx), self.hide_foe()))
                t += 450
            at(t, lambda: self.set_pet_status(None))  # o status do pet acaba com a luta
        elif kind == "trap":
            if ev.get("dodged"):
                at(t, lambda: self.floater(_t("esquivou!"), CYAN))
            elif ev["dmg"] == 0:                       # o escudo absorveu tudo
                at(t, lambda: self.floater(_t("bloqueou!"), CYAN))
            else:
                at(t, lambda: (self._set("hop", [-4, -8, -4, 0]),
                               self.floater(f"-{ev['dmg']}", HURT)))
            t += 600
        elif kind == "fountain":
            at(t, lambda: self.floater(f"+{ev.get('heal', 0)} ♥", GOOD))
            t += 600
        elif kind == "stairs":
            at(t, lambda: self._set("hop", [-4, -8, -10, -8, -4, 0]))
            t += 600
            if ev.get("evolved"):
                at(t, self.evolve)
                t += 1200
        if ev.get("gold") and kind not in ("monster", "boss", "mimic", "horde"):
            at(t, lambda: self.floater(f"+{ev['gold']} $", GOLD, x=self.fcx))
            t += 450
        t = self._offer_steps(ev, at, t)
        if ev.get("pending"):
            key, rar = ev["pending"]["key"], ev["pending"]["rar"]
            at(t, lambda: self.show_foe(key, False))
            at(t, lambda: self.floater(_t(M.ITEMS[key]["name"]), M.RAR_COLOR.get(rar) or GOLD,
                                       x=self.fcx, life=24))
            at(t, self.show_choice)
            t += 700
        if kind == "boss" and not ev["died"] and not ev.get("empate"):
            at(t, lambda: self._set("estado_tmp", ("jumping", time.time() + 1.2)))
        if ev["died"]:
            at(t, self.on_death)
            t += 400
        else:
            at(t, self.hide_foe)
        if ev.get("unlocks"):
            at(t, lambda: self.announce_unlocks(ev["unlocks"]))
        at(t, self.update_panel)

        for ms, fn in steps:
            self.root.after(ms, fn)
        self.busy_until = time.time() + t / 1000 + 0.8
        self.fight_until = self.busy_until if kind in ("monster", "boss", "mimic", "horde") else 0

    def _offer_steps(self, ev, at, t):
        """Animação das linhas e da oferta resolvida (item pego ou consumido); devolve o novo t."""
        for line in ev["lines"]:
            at(t, lambda line=line: self.floater(_t(line), TEXT, life=24))
            t += 600
        if ev.get("item"):
            key, rar = ev["item"]["key"], ev["item"]["rar"]
            it = M.ITEMS[key]
            at(t, lambda: self.show_foe(key, False))
            at(t, lambda: self.floater(_t(it["name"]), GOLD, x=self.fcx, life=24))
            t += 700
            at(t, lambda: (self.hide_foe(), self.refresh_look(),
                           self.burst(self.pcx, self.base_y - self.T // 2),
                           self.floater(M.fx_text(M.item_fx(key, rar)), GOOD, life=24)))
            t += 700
        if ev.get("consumed"):
            c = ev["consumed"]
            if c.get("heal"):
                at(t, lambda: self.floater(f"+{c['heal']} ♥", GOOD))
            elif "heal" in c:                          # curou 0: o HP já estava cheio
                at(t, lambda: self.floater(_t("HP já cheio"), MUTED))
            else:
                at(t, lambda: self.floater(_t("+{n} escudo", n=c['shield']), CYAN))
            t += 600
        return t

    def finish_pending(self, ev):
        """Fecha o painel e anima a oferta resolvida (escolha, janela vencida ou troca p/ auto)."""
        self.close_choice()
        steps = []
        t = self._offer_steps(ev, lambda ms, fn: steps.append((ms, fn)), 0)
        if ev.get("unlocks"):
            steps.append((t, lambda: self.announce_unlocks(ev["unlocks"])))
        steps.append((t, self.update_panel))
        for ms, fn in steps:
            self.root.after(ms, fn)
        self.busy_until = time.time() + t / 1000 + 0.8
        self.save()

    def choose(self, choice):
        if self.run["pending"] and not self.run["dead"]:
            self.finish_pending(M.choose_pending(self.run, self.meta, choice))

    def _set(self, attr, value):
        setattr(self, attr, list(value))

    def anim_hit(self, h, dead, status):
        """Um passo da luta: floaters, bote, tinta de status e some com quem morreu até aqui."""
        tgt, who = h["target"], h["who"]

        def fx(i):
            return self.foe_xy[i][0] if i in self.foe_on else self.fcx
        x = None if tgt == "pet" else fx(tgt)
        txt = f"-{h['dmg']}" + ("!" if h["crit"] else "") + (" x2" if h.get("duplo") else "")
        if h["skip"]:
            self.floater(_t("perdeu a vez"), MUTED, x=None if who == "pet" else fx(who), life=10)
        elif h["dot"]:
            self.floater(str(h["dmg"]), STATUS_COLOR.get(h["status"], HURT), x=x, life=8)
        elif h["dodge"]:
            self.floater(_t("esquivou!"), CYAN, life=10)
        elif h.get("bloqueado"):
            self.foe_attack(who)
            self.floater(_t("bloqueou!"), CYAN, life=10)
        elif h.get("espinhos"):                           # espinhos: o dano volta para o atacante, sem bote
            self.floater(f"-{h['dmg']}", GOOD, x=x, life=10)
        elif who == "ajudante":                           # ajudante: o número sai de cima do pet, sem bote
            self.floater(txt, GOOD, life=10)
        elif who == "pet":
            self.lunge = [5, 10, 5, 0]
            self.floater(txt, GOLD if h["crit"] else TEXT, x=x, life=10)
            if h["status"] and tgt in self.foe_on:        # ataque elemental: clarão na cor do elemento
                self.burst(x, self.foe_xy[tgt][1] - 4 * self.px, colors=(STATUS_COLOR[h["status"]], "#ffffff"))
                # ponytail: a tinta fica até o inimigo morrer (a GUI não sabe quando o status acaba)
                self.draw_foe(tgt, h["status"])
        else:
            self.foe_attack(who)
            if h["dmg"]:
                self.floater(txt, GOLD if h["crit"] else HURT, life=10)
            else:
                self.floater(_t("bloqueou!"), CYAN, life=10)
        self.set_pet_status(status)
        for i in dead:
            self.hide_foe(i, burst=True)

    def foe_slots(self, n):
        """(centro, base) de cada inimigo: 1 no meio; 2-4 num grid 2x2 (com 3, o 3º fica em cima, no meio)."""
        if n <= 1:
            return [(self.fcx, self.base_y)]
        up = self.base_y - 9 * self.px              # a arte dos monstros tem até 8 px de altura
        xy = [(self.foe_cols[0], self.base_y), (self.foe_cols[1], self.base_y)]
        if n == 3:
            xy.append((self.fcx, up))
        elif n >= 4:
            xy += [(self.foe_cols[0], up), (self.foe_cols[1], up)]
        return xy

    def show_foes(self, foes):
        self.hide_foe()
        foes = foes[:4]
        self.foe_xy = self.foe_slots(len(foes))
        self.foe_look = [(f.get("sprite"), f.get("boss", False)) for f in foes]
        for i in range(len(foes)):
            self.draw_foe(i)

    def show_foe(self, sprite, boss=False):
        if sprite:
            self.show_foes([{"sprite": sprite, "boss": boss}])

    def draw_foe(self, i, status=None):
        sprite, boss = self.foe_look[i]
        if not sprite:
            return
        img_i, crown = self.foe_items[i]
        x, y = self.foe_xy[i]
        img = self.art_img(sprite, boss, status)
        self.canvas.itemconfigure(img_i, image=img, state="normal")
        self.canvas.coords(img_i, x, y)
        if boss:
            self.canvas.itemconfigure(crown, image=self.art_img("coroa"), state="normal")
            self.canvas.coords(crown, x, y - img.height() + self.px)
        else:
            self.canvas.itemconfigure(crown, state="hidden")
        self.foe_on.add(i)

    def foe_attack(self, i):
        """Bote do inimigo i (o anterior volta para o lugar se ainda estava no meio do bote)."""
        j = self.lunge_foe
        if j != i and j < len(self.foe_xy):
            self.canvas.coords(self.foe_items[j][0], *self.foe_xy[j])
        self.lunge_foe = i
        self.foe_lunge = [-5, -10, -5, 0]

    def hide_foe(self, i=None, burst=False):
        """Esconde um inimigo (ou todos); com burst, explode quem ainda estava na tela."""
        for j in (range(len(self.foe_items)) if i is None else [i]):
            if burst and j in self.foe_on:
                self.burst(self.foe_xy[j][0], self.foe_xy[j][1] - 4 * self.px)
            self.foe_on.discard(j)
            img_i, crown = self.foe_items[j]
            self.canvas.itemconfigure(img_i, state="hidden")
            self.canvas.itemconfigure(crown, state="hidden")

    def evolve(self):
        old = self.stage_title
        self.load_images()
        self.refresh_look()
        self.burst(self.pcx, self.base_y - self.T // 2)
        self.hop = [-6, -12, -16, -12, -6, 0]
        self.state_tmp = ("jumping", time.time() + 1.2)
        self.floater(_t("EVOLUIU!"), GOLD, life=22)
        self.popup([_t("{a} evoluiu para {b}!", a=_t(old), b=_t(self.stage_title)), _t("+4 HP máx, +1 ATK")], 5000)

    def log_run(self, killer, gave_up):
        rec = M.run_record(self.run, killer, gave_up, self.state["mode"],
                           self.run.get("ach_start", self.meta["achievements"]),
                           killer_kind=self.meta["graveyard"][-1].get("kind", ""))
        append_run_record(rec, self.demo)

    def on_death(self):
        g = self.meta["graveyard"][-1]
        self.log_run(g["killer"], False)
        self.save()
        if getattr(self, "states_fx", None):       # herói de folha: quadros "failed" antes da lápide
            self.state_tmp = ("failed", time.time() + 1.2)
            self.root.after(1200, lambda: self.run["dead"] and self.show_tomb())
        else:
            self.show_tomb()
        self.burst(self.pcx, self.base_y - self.T // 3, colors=("#8a94a8", "#d7dde9", HURT))
        best = self.meta["best"]
        self.popup([_t("{nome} morreu no andar {n}", nome=_t(self.stage_title), n=f"{g['floor']}-{g['room']}"),
                    _t("Derrotado por: {k}", k=_t(g['killer'])),
                    _t("Monstros vencidos: {k}   Ouro: {o}", k=g['kills'], o=g['gold']),
                    _t("Recorde: andar {n}", n=f"{best['floor']}-{best['room']}"),
                    _t("Uma nova run começa em instantes...")], RESPAWN_S * 1000)
        self.respawn_at = time.time() + RESPAWN_S

    def show_tomb(self):
        self.canvas.itemconfigure(self.sprite, image=self.art_img("lapide"))
        self.canvas.coords(self.sprite, self.pcx, self.base_y)
        self.hide_foe()

    def announce_unlocks(self, keys):
        lines = [_t("CONQUISTA!")]
        for k in keys:
            lines.append(_t(M.ACHIEVEMENTS[k]))
            gains = self.unlock_rewards(k)
            if gains:
                lines.append(_t("  libera: {x}", x=", ".join(gains)))
        self.fill_char_menu()
        self.popup(lines, 9000)

    def unlock_rewards(self, ach):
        items = [_t(it["name"]) for it in M.ITEMS.values() if it.get("req") == ach]
        chars = [_t("herói {nome}", nome=_t(c.name)) for c in self.chars.values() if c.unlock == ach]
        return items + chars

    # ------------------------------------------------------------- animação
    def floater(self, text, color=TEXT, life=16, x=None, top=False):
        """Texto que sobe. Escolhe um lugar livre (sem cobrir floaters vivos nem o painel);
        com top=True (nome do monstro) fica sempre por cima."""
        c = self.canvas
        bx = (self.pcx if x is None else x) + self.rng.randint(-10, 10)
        by = self.base_y - self.T + 10
        tags = ("nome",) if top else ()
        t = c.create_text(bx, by, text=text, fill=color, font=self.font_small, tags=tags)
        alive = [c.bbox(f[0][0]) for f in self.floaters]
        options = []
        for dy in (0, -16, 16, -32, 32, -48):
            for dx in (0, -34, 34):
                c.coords(t, bx + dx, by + dy)
                x0, y0, x1, y1 = c.bbox(t)
                shift = max(0, 4 - (x0 - 5)) - max(0, (x1 + 5) - (self.W - 4))
                box = (x0 + shift - 5, y0 - 2, x1 + shift + 5, y1 + 2)
                if box[1] >= 0 and box[3] < self.panel_y:      # nunca por cima do painel
                    options.append((bx + dx + shift, by + dy, box))
        free = [o for o in options if not any(
            v and o[2][0] < v[2] and v[0] < o[2][2] and o[2][1] < v[3] and v[1] < o[2][3] for v in alive)]
        if free or options:
            fx, fy, box = (free or options)[0]
        else:
            fx, fy = bx, by
            x0, y0, x1, y1 = c.bbox(t)
            box = (x0 - 5, y0 - 2, x1 + 5, y1 + 2)
        c.coords(t, fx, fy)
        self.n_floater += 1
        r = f"flt{self.n_floater}"      # tag do balão arredondado (vários retângulos)
        rounded_rect(c, *box, CARD_R, PANEL_BG, PANEL_EDGE, 1, tag=r, extra=tags)
        c.tag_raise(t)
        c.tag_raise("nome")
        self.floaters.append([(r, t), life])

    def burst(self, x, y, colors=(GOLD, "#ffffff", GOOD)):
        for i in range(16):
            a = i * math.pi / 8
            r = self.canvas.create_rectangle(x - 3, y - 3, x + 3, y + 3,
                                             fill=self.rng.choice(colors), outline="")
            self.particles.append([r, math.cos(a) * 6, math.sin(a) * 6, 12])

    def current_state(self, now, resting):
        """Estado da folha a mostrar (None para heróis sem estados): escolha > luta > morte > descanso > idle;
        waving/jumping valem pelo tempo marcado."""
        if not getattr(self, "states_fx", None):
            return None
        tmp, until = getattr(self, "state_tmp", (None, 0))
        if self.run["dead"]:
            return "failed" if tmp == "failed" and now < until else None
        if self.run["pending"]:
            return "review"
        if now < getattr(self, "fight_until", 0):
            return "running"
        if tmp in ("waving", "jumping") and now < until:
            return tmp
        return "waiting" if resting else "idle"

    def state_frame(self, state, now):
        qs = self.states_fx[state]
        self.state_seen = state
        q = qs[int(now * 1000 / self.char.frame_ms) % len(qs)]
        return q[int(now * 1000 / FX_MS) % len(q)]

    def tick(self):
        now = time.time()
        run = self.run
        try:
            if self.choice_win is not None and (not run["pending"] or run["dead"]):
                self.close_choice()                # a pendência sumiu (run nova, desistiu...)
            if run["dead"]:
                if self.respawn_at and now >= self.respawn_at:
                    self.new_run()
            elif now >= self.busy_until and run["pending"]:
                # nunca entra em sala com escolha aberta; os tokens continuam enchendo a energia
                if self.pending_since is None:
                    self.pending_since = now       # também ao abrir o app com pendência no save
                if self.state["mode"] == "auto" or (
                        now - self.pending_since >= M.CHOICE_WINDOW_S and M.can_enter(run)):
                    self.finish_pending(M.resolve_pending(run, self.meta))
                else:
                    self.show_choice()
                    self.update_choice()
            elif now >= self.busy_until and M.can_enter(run):
                self.play_room()

            idle = now - self.state["last_fed"]
            busy = now < self.busy_until
            if run["dead"]:
                if self.current_state(now, False) == "failed":
                    self.canvas.itemconfigure(self.sprite, image=self.state_frame("failed", now))
            else:
                sleeping = idle > SLEEP_AFTER_S and not busy
                phase = int(now * 1000 / FX_MS)       # relógio dos efeitos, separado do herói
                state = self.current_state(now, idle > REST_AFTER_S and not busy)
                if state:
                    img = self.state_frame(state, now)
                    bob = 0
                    if state == "idle" and self.blink_fx is not None:   # herói de grade ainda pisca
                        if now > self.next_blink:
                            self.blink_until = now + 0.16
                            self.next_blink = now + self.rng.uniform(2.5, 6)
                        if now < self.blink_until:
                            img = self.blink_fx[phase % len(self.blink_fx)]
                    if sleeping and now > self.next_zzz:
                        self.floater("z Z", MUTED, life=20)
                        self.next_zzz = now + 3
                elif sleeping:
                    img = self.sleep_fx[phase % len(self.sleep_fx)]
                    bob = -2 if int(now / 1.4) % 2 else 0
                    if now > self.next_zzz:
                        self.floater("z Z", MUTED, life=20)
                        self.next_zzz = now + 3
                else:
                    if self.blink_fx is not None and now > self.next_blink:
                        self.blink_until = now + 0.16
                        self.next_blink = now + self.rng.uniform(2.5, 6)
                    if self.blink_fx is not None and now < self.blink_until:
                        img = self.blink_fx[phase % len(self.blink_fx)]
                    else:
                        q = self.frames_fx[int(now * 1000 / self.char.frame_ms) % len(self.frames_fx)]
                        img = q[phase % len(q)]
                    bob = -2 if int(now / 0.6) % 2 else 0
                dy = self.hop.pop(0) if self.hop else bob
                dx = self.lunge.pop(0) if self.lunge else 0
                self.canvas.itemconfigure(self.sprite, image=img)
                self.place_pet(dx, dy)
            if self.foe_lunge and self.lunge_foe < len(self.foe_xy):
                x, y = self.foe_xy[self.lunge_foe]
                self.canvas.coords(self.foe_items[self.lunge_foe][0], x + self.foe_lunge.pop(0), y)

            d = self.bar_target - self.bar_frac             # barra de energia desliza até o alvo
            self.bar_frac = self.bar_target if abs(d) < 0.004 else self.bar_frac + d * 0.3
            self.draw_energy(now)

            for f in self.floaters[:]:
                for item in f[0]:
                    self.canvas.move(item, 0, -2)
                f[1] -= 1
                if f[1] <= 0:
                    for item in f[0]:
                        self.canvas.delete(item)
                    self.floaters.remove(f)
            for p in self.particles[:]:
                self.canvas.move(p[0], p[1], p[2])
                p[3] -= 1
                if p[3] <= 0:
                    self.canvas.delete(p[0])
                    self.particles.remove(p)
        except Exception:
            log("erro na animação: " + traceback.format_exc())
        self.root.after(100, self.tick)

    # --------------------------------------------------------------- janelas
    def popup(self, lines, ms=8000):
        if self.popup_win is not None:
            try:
                self.popup_win.destroy()
            except tk.TclError:
                pass
        w, f = self.pixel_box(0, 0, closes=False)
        tk.Label(f, text="\n".join(lines), justify="left", bg=PANEL_BG, fg=TEXT,
                 font=self.font, padx=6, pady=4).pack()
        w.update_idletasks()
        x = self.root.winfo_x() - w.winfo_width() - 6
        if x < 0:
            x = self.root.winfo_x() + self.W + 6
        y = max(0, self.root.winfo_y() + self.top)
        w.geometry(f"+{x}+{y}")
        w.bind("<Button-1>", lambda e: self.close_popup(w))
        w.after(ms, lambda: self.close_popup(w))
        self.popup_win = w

    def close_popup(self, w):
        if self.popup_win is w:
            self.popup_win = None
        try:
            w.destroy()
        except tk.TclError:
            pass

    def show_choice(self):
        """Painel Pegar/Consumir ao lado do pet (um só por vez)."""
        p = self.run["pending"]
        if self.choice_win is not None or not p:
            return
        key, rar = p["key"], p["rar"]
        it = M.ITEMS[key]
        w, f = self.pixel_box(0, 0, closes=False)   # a escolha não fecha sozinha ao perder o foco
        self.choice_img = self.art_img(key)       # referência: o tk não guarda a imagem sozinho
        tk.Label(f, image=self.choice_img, bg=PANEL_BG).pack(pady=(4, 2))
        tk.Label(f, text=f"{_t(it['name'])}  ·  {_t(M.RAR_NAMES[rar])}", bg=PANEL_BG,
                 fg=M.RAR_COLOR.get(rar) or TEXT, font=self.font).pack(padx=6)
        cf = M.consume_fx(key, rar)
        cons = f"+{cf['heal']} ♥" if "heal" in cf else _t("+{n} escudo", n=cf['shield'])
        tk.Label(f, text=_t("Pegar: {x}", x=M.fx_text(M.item_fx(key, rar))) + "\n" + _t("Consumir: {x}", x=cons),
                 justify="left", bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(padx=6)
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=4)
        for label, choice in (("Pegar", "pegar"), ("Consumir", "consumir")):
            self.chip(row, _t(label), False, lambda c=choice: self.choose(c)).pack(side="left", padx=4)
        self.choice_cv = self.progress_bar(f, CHOICE_BAR_W, 6, 1.0, ENERGY)
        self.choice_cv.pack(pady=(2, 2))
        self.choice_wait = tk.Label(f, text="", bg=PANEL_BG, fg=MUTED, font=self.font_small)
        self.choice_wait.pack(pady=(0, 2))
        w.update_idletasks()
        x = self.root.winfo_x() - w.winfo_width() - 6
        if x < 0:
            x = self.root.winfo_x() + self.W + 6
        # alinhado por baixo com o pet, para não cobrir o popup (que cresce a partir do topo)
        y = max(0, self.root.winfo_y() + self.H - w.winfo_height())
        w.geometry(f"+{x}+{y}")
        self.choice_win = w
        self.update_choice()

    def update_choice(self):
        """Só mexe na barrinha do tempo e no texto das salas esperando."""
        if self.choice_win is None:
            return
        since = time.time() if self.pending_since is None else self.pending_since
        left = max(0.0, 1 - (time.time() - since) / M.CHOICE_WINDOW_S)
        self.choice_cv.set(left)
        rooms = int(self.run["energy"] // M.room_cost(self.run))
        wait = "" if rooms < 1 else (_t("1 sala esperando") if rooms == 1 else _t("{n} salas esperando", n=rooms))

        self.choice_wait.config(text=wait)

    def close_choice(self):
        w, self.choice_win, self.pending_since = self.choice_win, None, None
        if w is not None:
            try:
                w.destroy()
            except tk.TclError:
                pass

    def show_stats(self):
        run, meta = self.run, self.meta
        st = M.stats(run)
        w, f = self.window("stats_win", _t("Status  ·  Run #{n}", n=run['id']))
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x", pady=(4, 0))
        self.stats_thumb = map_img(self.look_maps[0], 56)    # referência: o tk não guarda a imagem sozinho
        tk.Label(head, image=self.stats_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 8))
        col = tk.Frame(head, bg=PANEL_BG)
        col.pack(side="left", fill="x")
        tk.Label(col, text=f"{_t(self.char.name)}  ·  {_t(self.stage_title)}", bg=PANEL_BG, fg=GOLD, font=self.font,
                 anchor="w").pack(fill="x")
        tk.Label(col, text=f"{depth(run)}   ·   " + _t("Modo {m}", m=_t(MODES[self.state['mode']])),
                 bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        self.progress_bar(col, 170, 8, run["hp"] / st["maxhp"], HURT).pack(anchor="w", pady=3)
        shield = "   ·   " + _t("escudo {n}", n=run['shield']) if run["shield"] > 0 else ""
        bosses = _t("{n} chefe" if run['bosses'] == 1 else "{n} chefes", n=run['bosses'])
        tk.Label(col, text=f"♥ {run['hp']}/{st['maxhp']}{shield}   ·   $ {run['gold']}   ·   {run['kills']} kills"
                 f"   ·   {bosses}", bg=PANEL_BG, fg=TEXT, font=self.font_small,
                 anchor="w").pack(fill="x")
        if run.get("traco"):
            tk.Label(f, text=_t("Traço: {x}", x=M.fx_text(run['traco'])), bg=PANEL_BG, fg=MUTED, font=self.font_small,
                     anchor="w").pack(fill="x", pady=(4, 0))
        self.menu_sep(f)
        grid = tk.Frame(f, bg=PANEL_BG)
        grid.pack(fill="x")
        for n, (k, name, value) in enumerate(stat_lines(run, st)):
            r, c = n // 2, (n % 2) * 3
            tk.Label(grid, image=self.icon(art.STAT_ART[k], 2), bg=PANEL_BG, width=20, height=18).grid(
                row=r, column=c)
            tk.Label(grid, text=name, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").grid(
                row=r, column=c + 1, sticky="w", padx=(2, 6))
            tk.Label(grid, text=value, bg=PANEL_BG, fg=TEXT, font=self.font_small, anchor="e").grid(
                row=r, column=c + 2, sticky="e", padx=(0, 14 if c == 0 else 0))
        self.menu_sep(f)
        tooltip = _t("passe o mouse num item") if run["items"] or run["consumed"] else ""
        info = tk.Label(f, text=tooltip, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w", justify="left",
                        wraplength=330)
        for title, lst, s, dim in ((_t("Itens ({n})", n=len(run['items'])), run["items"], 3, False),
                                      (_t("Consumidos ({n})", n=len(run['consumed'])), run["consumed"], 2, True)):
            if not lst and dim:
                continue
            tk.Label(f, text=title, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
            box = tk.Frame(f, bg=PANEL_BG)
            box.pack(fill="x", pady=(2, 4))
            if not lst:
                tk.Label(box, text=_t("nenhum ainda"), bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(anchor="w")
            for n, it in enumerate(i for i in lst if i["key"] in M.ITEMS):
                rar = it.get("rar", "comum")
                side, cols = s * 12, 10 if s == 3 else 14     # célula fixa: itens largos (chapéus) cabem sem cobrir o vizinho
                lbl = tk.Label(box, image=self.icon(art.ITEM_ART[it["key"]], s, glow=M.RAR_COLOR.get(rar), dim=dim,
                                                    side=side), bg=PANEL_BG, width=side + 2, height=side + 2)
                lbl.grid(row=n // cols, column=n % cols)
                txt = (f"{_t(M.ITEMS[it['key']]['name'])} ({_t(M.RAR_NAMES.get(rar, rar))})"
                       + ("" if dim else f": {M.fx_text(M.item_fx(it['key'], rar))}"))
                lbl.bind("<Enter>", lambda e, t=txt: info.configure(text=t, fg=TEXT))
                lbl.bind("<Leave>", lambda e: info.configure(text=tooltip, fg=MUTED))
        info.pack(fill="x")
        self.menu_sep(f)
        best = meta["best"]
        footer = [_t("Energia guardada: {n} sala(s)", n=int(run['energy'] // M.room_cost(run))),
                  _t("Recorde: andar {n}", n=f"{best['floor']}-{best['room']}") + f"   ·   Runs: {meta['runs']}",
                  _t("Tokens hoje: {n}", n=fmt(self.state['daily'].get(date.today().isoformat(), 0)))
                  + f"   ·   Total: {fmt(self.state['tokens_total'])}"]
        if run["pending"]:
            footer.append(_t("Esperando escolha: {x}", x=_t(M.ITEMS[run['pending']['key']]['name'])))
        if self.demo:
            footer.append(_t("(modo demo)"))
        tk.Label(f, text="\n".join(footer), bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w",
                 justify="left").pack(fill="x")
        self.beside(w)

    def killer_icon(self, d):
        """Ícone de quem matou: monstro, chefe com coroa, mímico, status, armadilha ou desistência."""
        k = d.get("killer", "")
        boss = next((s for s, n in M.BOSS_NAMES.items() if n == k), None)
        if boss:
            return self.icon(boss_grid(boss), 2, pal=art.BOSS_PAL)
        spr = "mimico" if k == "Mímico" else next((m[0] for m in M.MONSTERS if m[1] == k), None)
        if spr:
            return self.icon(art.FOE_ART[spr], 2)
        grid = {"Queimadura": art.STAT_ART["queimar"], "Veneno": art.STAT_ART["envenenar"],
                "Armadilha": art.ROOM_ART["armadilha"], "Desistiu": art.ROOM_ART["escada"]}.get(k)
        return self.icon(grid or art.ROOM_ART["lapide"], 2)

    def tombstone(self, cv, y, d):
        """Uma lápide do cemitério desenhada no canvas a partir de y."""
        L, f, fs = GRAVE_TOMB, self.font, self.font_small
        rounded_rect(cv, 1, y + 1, GRAVE_W - 1, y + L - 3, CARD_R, CARD_BG, PANEL_EDGE, 2, tag="cartao",
                              extra=(f"card:{y}",))
        c = self.chars.get(d.get("char"))
        img = (c and self.hero_thumb(c, True, 40)) or self.icon(art.ROOM_ART["lapide"], 4)
        cv.create_image(30, y + L // 2 - 1, image=img)
        cv.create_text(60, y + 15, anchor="w", text=f"#{d.get('run', '?')}  {_t(c.name) if c else d.get('char', '?')}",
                       fill=GOLD, font=f)
        cv.create_text(GRAVE_W - 12, y + 15, anchor="e", text=_t("andar {n}", n=f"{d['floor']}-{d['room']}"), fill=TEXT,
                       font=f)
        kimg = self.killer_icon(d)
        cv.create_image(60, y + 37, anchor="w", image=kimg)
        who = _t("desistiu") if d.get("kind") == "desistiu" else _t("morto por {k}", k=_t(d.get('killer', '?')))
        cv.create_text(66 + kimg.width(), y + 37, anchor="w", text=who, fill=HURT, font=fs)
        cv.create_text(GRAVE_W - 12, y + 37, anchor="e", fill=MUTED, font=fs,
                       text=f"$ {d.get('gold', 0)}   ·   {d.get('kills', 0)} kills   ·   {d.get('date', '')}")
        x = 60
        items = [(it, None) if isinstance(it, str) else (it["key"], it.get("rar")) for it in d.get("items", [])]
        items = [(k, r) for k, r in items if k in art.ITEM_ART]
        for n, (key, rar) in enumerate(items):
            im = self.icon(art.ITEM_ART[key], 2, glow=M.RAR_COLOR.get(rar))
            if x + im.width() > GRAVE_W - 34 and n < len(items) - 1:
                cv.create_text(x + 2, y + 64, anchor="w", text=f"+{len(items) - n}", fill=MUTED, font=fs)
                break
            cv.create_image(x, y + 64, anchor="w", image=im)
            x += im.width() + 3
        if not items:
            cv.create_text(60, y + 64, anchor="w", text=_t("sem itens"), fill=MUTED, font=fs)

    def show_graveyard(self):
        g, meta = self.meta["graveyard"], self.meta
        w, f = self.window("grave_win", _t("Cemitério"))
        best = meta["best"]
        summary = _t("{n} runs   ·   recorde: andar {a}", n=meta['runs'], a=f"{best['floor']}-{best['room']}")
        deaths = Counter(d.get("killer") for d in g if d.get("kind") != "desistiu")
        if deaths:
            summary += _t("   ·   quem mais matou: {k}", k=_t(deaths.most_common(1)[0][0]))
        tk.Label(f, text=summary, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        if not g:
            tk.Label(f, image=self.icon(art.ROOM_ART["lapide"], 4), text=_t("Nenhuma lápide ainda...\no herói segue firme!"),
                     compound="left", bg=PANEL_BG, fg=TEXT, font=self.font, padx=10, pady=12,
                     justify="left").pack()
            self.beside(w)
            return
        alto, vis = len(g) * GRAVE_TOMB, min(len(g) * GRAVE_TOMB, GRAVE_H)
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=(4, 0))
        cv = tk.Canvas(row, width=GRAVE_W, height=vis, bg=PANEL_BG, highlightthickness=0,
                       scrollregion=(0, 0, GRAVE_W, alto), yscrollincrement=GRAVE_TOMB // 3)
        cv.pack(side="left")
        for n, d in enumerate(reversed(g)):
            self.tombstone(cv, n * GRAVE_TOMB, d)
        if alto > vis:
            self.scrollbar(row, w, cv, vis)
        self.beside(w)

    def scrollbar(self, parent, w, cv, vis):
        """Barra de rolagem em pixel (a nativa não pega as cores) ao lado do Canvas `cv` (com scrollregion):
        arrastar o polegar rola junto, clicar na trilha centraliza o polegar ali, roda do mouse e setas.
        O polegar some quando tudo cabe (ex.: depois de um filtro). Devolve a trilha."""
        tr = tk.Canvas(parent, width=8, height=vis, bg=PANEL_BG, highlightthickness=0, cursor="hand2")
        tr.pack(side="left", padx=(4, 0))
        rounded_rect(tr, 0, 0, 8, vis, 4, BAR_BG, tag="trilha")
        view = {"a": 0.0, "b": 1.0, "pega": None, "cor": GOLD}   # fração visível, onde o polegar foi pego, cor

        def shows(a, b):
            view["a"], view["b"] = float(a), float(b)
            tr.delete("dedo")
            if view["b"] - view["a"] < 0.999:
                rounded_rect(tr, 0, round(view["a"] * vis), 8, round(view["b"] * vis), 4, view["cor"],
                                      tag="dedo")

        def vai(y):
            tam = view["b"] - view["a"]
            cv.yview_moveto(max(0.0, min(1.0 - tam, (y - view["pega"]) / vis)))

        def squeeze(e):
            y0, y1 = view["a"] * vis, view["b"] * vis
            view["pega"] = e.y - y0 if y0 <= e.y <= y1 else (y1 - y0) / 2   # fora do polegar: pula para lá
            vai(e.y)

        def releases(e):
            view["pega"] = None
        cv.configure(yscrollcommand=shows)
        tr.bind("<Button-1>", squeeze)
        tr.bind("<B1-Motion>", lambda e: view["pega"] is not None and vai(e.y))
        tr.bind("<ButtonRelease-1>", releases)
        def color(c):
            view["cor"] = c
            tr.itemconfigure("dedo", fill=c)
        tr.tag_bind("dedo", "<Enter>", lambda e: color(GOLD_HOVER))
        tr.tag_bind("dedo", "<Leave>", lambda e: color(GOLD))
        w.bind("<MouseWheel>", lambda e: cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        w.bind("<Up>", lambda e: cv.yview_scroll(-1, "units"))
        w.bind("<Down>", lambda e: cv.yview_scroll(1, "units"))
        return tr

    def item_unlocked(self, key):
        """Mesma regra do sorteio (M.unlocked_items); no demo tudo liberado, como os heróis."""
        req = M.ITEMS[key].get("req")
        return self.demo or not req or req in self.meta["achievements"]

    def item_card(self, cv, x, y, key):
        """Card de um item no canvas a partir de (x, y); devolve a altura. Bloqueado: silhueta, cadeado, sem valores."""
        it, ok, fs = M.ITEMS[key], self.item_unlocked(key), self.font_small
        top = next((M.RAR_COLOR[r] for r in reversed(it["rarities"]) if M.RAR_COLOR[r]), None)
        cv.create_image(x + 26, y + 26, image=self.icon(art.ITEM_ART[key], 4, glow=ok and top or None, dark=not ok))
        cv.create_text(x + 54, y + 16, anchor="w", text=_t(it["name"]), fill=TEXT if ok else MUTED, font=self.font)
        eat = _t("cura" if "heal" in it["consume"] else "escudo")
        cv.create_text(x + 54, y + 33, anchor="w", font=fs, fill=MUTED,
                       text=_t(item_family(key)) + ("  ·  " + _t("consumir: {x}", x=eat) if ok else ""))
        ty, larg = y + 54, ITEMS_CARD_W - 20
        if not ok:
            cv.create_image(x + 10, ty + 7, anchor="w", image=self.menu_icon("cadeado"))
            t = cv.create_text(x + 26, ty, anchor="nw", text=_t(M.ACHIEVEMENTS.get(it["req"], it["req"])), fill=MUTED,
                               font=fs, width=larg - 16)
            ty = cv.bbox(t)[3] + 4
        for r in [] if not ok else it["rarities"]:
            c = M.consume_fx(key, r)
            eat = _t("cura {n}", n=c['heal']) if "heal" in c else _t("escudo {n}", n=c.get('shield', 0))
            t = cv.create_text(x + 10, ty, anchor="nw", fill=M.RAR_COLOR[r] or TEXT, font=fs, width=larg,
                               text=f"{_t(M.RAR_NAMES[r])}: {M.fx_text(M.item_fx(key, r))}  ·  {eat}")
            ty = cv.bbox(t)[3] + 3
        alto = max(ty - y + 6, 60)
        rounded_rect(cv, x, y, x + ITEMS_CARD_W, y + alto, CARD_R, CARD_BG, PANEL_EDGE, 2, tag="cartao",
                              extra=(f"card:{x}_{y}",))
        cv.tag_lower("cartao")
        return alto

    def show_items(self):
        free = [k for k in M.ITEMS if self.item_unlocked(k)]
        w, f = self.window("items_win", _t("Itens  ·  {a} de {b} liberados", a=len(free), b=len(M.ITEMS)))
        self.items_filter = getattr(self, "items_filter", "todos")
        chips = tk.Frame(f, bg=PANEL_BG)
        chips.pack(fill="x", pady=(4, 0))
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=(4, 0))
        cv = tk.Canvas(row, width=ITEMS_COLS * (ITEMS_CARD_W + 6), height=ITEMS_H, bg=PANEL_BG,
                       highlightthickness=0, yscrollincrement=40)
        cv.pack(side="left")
        self.items_cv = cv
        self.scrollbar(row, w, cv, ITEMS_H)
        buttons = {}

        def draw(filter_by):
            self.items_filter = filter_by
            for name, b in buttons.items():
                b.paint(name == filter_by)
            cv.delete("all")
            keys = [k for k in M.ITEMS if filter_by == "todos" or (k in free) == (filter_by == "liberados")]
            y = 0
            for i in range(0, len(keys), ITEMS_COLS):
                y += 6 + max(self.item_card(cv, c * (ITEMS_CARD_W + 6), y, k)
                             for c, k in enumerate(keys[i:i + ITEMS_COLS]))
            if not keys:
                cv.create_text(10, 20, anchor="w", text=_t("Nenhum item aqui."), fill=MUTED, font=self.font)
            cv.configure(scrollregion=(0, 0, ITEMS_COLS * (ITEMS_CARD_W + 6), max(y, ITEMS_H)))
            cv.yview_moveto(0)
        for name, text in (("todos", "Todos"), ("liberados", "Liberados"), ("bloqueados", "Bloqueados")):
            b = self.chip(chips, _t(text), False, lambda n=name: draw(n))
            b.pack(side="left", padx=(0, 3))
            buttons[name] = b
        draw(self.items_filter)
        self.beside(w)

    def show_achievements(self):
        have = set(self.meta["achievements"]) & set(M.ACHIEVEMENTS)
        w, f = self.window("ach_win", _t("Conquistas  ·  {a} de {b}", a=len(have), b=len(M.ACHIEVEMENTS)))
        grid = tk.Frame(f, bg=PANEL_BG)
        grid.pack(pady=(4, 0))
        for n, (k, desc) in enumerate(M.ACHIEVEMENTS.items()):
            ok = k in have
            card = self.card_box(grid, GOLD if ok else PANEL_EDGE, ACH_CARD_W, ACH_CARD_H)
            card.grid(row=n // ACH_COLS, column=n % ACH_COLS, padx=3, pady=3)
            tk.Label(card, image=self.icon(art.ACH_ART[k], 3, dark=not ok), bg=CARD_BG, height=36).pack(
                pady=(CARD_PAD, 2))
            tk.Label(card, text=_t(desc), bg=CARD_BG, fg=TEXT if ok else MUTED, font=self.font_small,
                     wraplength=ACH_CARD_W - 2 * CARD_PAD).pack()
            rewards = [self.icon(art.ITEM_ART[ik], 2, dark=not ok) for ik, it in M.ITEMS.items()
                       if it.get("req") == k and ik in art.ITEM_ART]
            rewards += [im for c in self.chars.values() if c.unlock == k for im in [self.hero_thumb(c, ok, 24)] if im]
            if rewards:
                line = tk.Frame(card, bg=CARD_BG)
                line.pack(side="bottom", pady=(0, CARD_PAD))
                tk.Label(line, text=_t("libera"), bg=CARD_BG, fg=MUTED, font=self.font_small).pack(side="left", padx=2)
                for im in rewards[:3]:
                    tk.Label(line, image=im, bg=CARD_BG).pack(side="left", padx=1)
                if len(rewards) > 3:
                    tk.Label(line, text=f"+{len(rewards) - 3}", bg=CARD_BG, fg=MUTED, font=self.font_small).pack(side="left")
        self.beside(w)

    def show_perfil(self):
        """Perfil (só dados que já existem: state, meta, usage_hist): herói, nível de domador, medalhas,
        números, gráfico dos últimos 7 dias, limites e atalhos. Textos novos do perfil ficam todos aqui."""
        run, meta, state, now = self.run, self.meta, self.state, time.time()
        st, fs, L = M.stats(run), self.font_small, PROFILE_W
        w, f = self.window("profile_win", _t("Perfil"))

        def progress_bar(parent, frac, color, larg=L, alto=6):
            return self.progress_bar(parent, larg, alto, frac, color)

        def label(parent, txt, fg=MUTED, font=fs):
            tk.Label(parent, text=txt, bg=PANEL_BG, fg=fg, font=font, anchor="w").pack(fill="x")

        def top(left, dir_, fg_dir=TEXT, font=fs):
            fr = tk.Frame(f, bg=PANEL_BG)
            fr.pack(fill="x")
            tk.Label(fr, text=left, bg=PANEL_BG, fg=GOLD if font == self.font else MUTED, font=font).pack(side="left")
            tk.Label(fr, text=dir_, bg=PANEL_BG, fg=fg_dir, font=fs).pack(side="right")
        # cabeçalho: herói, run, HP
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x", pady=(4, 0))
        self.profile_thumb = map_img(self.look_maps[0], 48)    # referência: o tk não guarda a imagem sozinho
        tk.Label(head, image=self.profile_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 8))
        col = tk.Frame(head, bg=PANEL_BG)
        col.pack(side="left", fill="x")
        label(col, f"{_t(self.char.name)}  ·  {_t(self.stage_title)}", GOLD, self.font)
        label(col, f"Run #{run['id']}   ·   {depth(run)}   ·   ♥ {run['hp']}/{st['maxhp']}")
        progress_bar(col, run["hp"] / st["maxhp"], HURT, L - 56).pack(anchor="w", pady=(3, 0))
        # nível de domador (energia na vida: mesma unidade do gráfico)
        n, frac, missing = level(state["xp_total"])
        self.menu_sep(f)
        top(_t("Domador  Nv {n}", n=n), f"{round(frac * 100)}%", GOLD, self.font)
        progress_bar(f, frac, GOLD).pack(anchor="w", pady=2)
        label(f, _t("faltam ~{x} de energia para o Nv {n}", x=fmt(missing), n=n + 1))
        # medalhas
        have = set(meta["achievements"]) & set(M.ACHIEVEMENTS)
        self.menu_sep(f)
        top(_t("Conquistas"), f"{len(have)} / {len(M.ACHIEVEMENTS)}")
        med = tk.Frame(f, bg=PANEL_BG)
        med.pack(anchor="w", pady=2)
        tooltip = _t("passe o mouse numa medalha")
        info = tk.Label(f, text=tooltip, bg=PANEL_BG, fg=MUTED, font=fs, anchor="w", justify="left", wraplength=L)
        for i, (k, desc) in enumerate(M.ACHIEVEMENTS.items()):
            lb = tk.Label(med, image=self.icon(art.ACH_ART[k], dark=k not in have, side=PROFILE_MEDAL - 2),
                          bg=PANEL_BG, width=PROFILE_MEDAL, height=PROFILE_MEDAL, bd=0, padx=0, pady=0)
            lb.grid(row=i // PROFILE_MEDALS, column=i % PROFILE_MEDALS)
            txt = _t(desc) + ("" if k in have else _t("  (bloqueada)"))
            lb.bind("<Enter>", lambda e, t=txt: info.configure(text=t, fg=TEXT))
            lb.bind("<Leave>", lambda e: info.configure(text=tooltip, fg=MUTED))
        info.pack(fill="x")
        # cartões de números
        own = [c for k, c in self.chars.items() if own_hero(k)]
        best, dias = meta["best"], usage_per_day(state, now)
        cards = (("HOJE", fmt(dias[-1][1]), "de energia"), ("SEQUÊNCIA", str(streak_days(state, now)), "dias seguidos"),
                   ("NA VIDA", fmt(state["xp_total"]), "de energia"), ("RUNS", str(meta["runs"]), "jogadas"),
                   ("RECORDE", f"{best['floor']}-{best['room']}", "andar-sala"),
                   ("HERÓIS", f"{sum(self.is_unlocked(c) for c in own)}/{len(own)}",
                    _t("{n} chefe" if meta.get('chefes', 0) == 1 else "{n} chefes", n=meta.get('chefes', 0))))
        cards = [(_t(a), b, _t(c)) for a, b, c in cards]
        self.menu_sep(f)
        grid = tk.Frame(f, bg=PANEL_BG)
        grid.pack(fill="x")
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="cartao")
        for i, (tit, val, sub) in enumerate(cards):
            card = self.card_box(grid, thickness=1)
            card.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="nsew")
            for j, (txt, fg, font) in enumerate(((tit, MUTED, fs), (val, TEXT, self.font), (sub, MUTED, fs))):
                tk.Label(card, text=txt, bg=CARD_BG, fg=fg, font=font, anchor="w", padx=0, pady=0).pack(
                    fill="x", padx=CARD_PAD, pady=(CARD_PAD if j == 0 else 0, CARD_PAD if j == 2 else 0))
        # gráfico dos últimos 7 dias (energia por dia, de usage_hist)
        self.menu_sep(f)
        top(_t("Últimos 7 dias  (energia)"), fmt(sum(v for _, v in dias)), GOLD)
        alto, larger = 58, max(v for _, v in dias) or 1
        cv = tk.Canvas(f, width=L, height=alto + 16, bg=PANEL_BG, highlightthickness=0)
        cv.pack(pady=(2, 0))
        bw = L // 7
        for i, (d, v) in enumerate(dias):
            x0, today_ = i * bw + 4, i == len(dias) - 1
            h = max(2, round(alto * v / larger / 2) * 2)      # degraus de 2 px: cara de pixel
            cv.create_rectangle(x0, alto - h, x0 + bw - 8, alto, width=0,
                                fill=(GOLD if today_ else PROFILE_BAR) if v else BAR_BG)
            cv.create_text(x0 + (bw - 8) / 2, alto + 9, text=_t(DAYS[d.weekday()]), fill=GOLD if today_ else MUTED, font=fs)
        # limites (iguais aos do painel)
        self.menu_sep(f)
        label(f, _t("Limites"))
        for key, name in (("sessao", "Sessão"), ("semana", "Semana")):
            pct, reset, est, tok = limit_view(key, self.limits, state, now)
            if pct is not None:
                val = f"{'~' if est else ''}{round(pct)}%"
            else:                       # sem % oficial nem fator: tokens e quanto isso é do seu pico
                p = peak(state, key, tok)
                val = _t("{n} · {p}% do seu pico", n=fmt(tok), p=round(100 * tok / p)) if tok and p else "—"
            top(f"{_t(name)}  {val}", _t("reseta {h}", h=fmt_reset(reset, now)) if reset else "", MUTED)
            if pct is not None:
                progress_bar(f, pct / 100, limit_color(pct)).pack(anchor="w", pady=(1, 3))
            else:
                progress_bar(f, tok / p if tok and p else 0, PEAK_COLOR).pack(anchor="w", pady=(1, 3))
        # rodapé: último uso e atalhos
        self.menu_sep(f)
        ult = last_use(state)
        label(f, _t("último uso: {x}", x=fmt_ago(now - ult) if ult else _t("nenhum ainda"))
               + ("   ·   " + _t("(modo demo)") if self.demo else ""))
        bot = tk.Frame(f, bg=PANEL_BG)
        bot.pack(fill="x", pady=(4, 0))
        for txt, fn in (("Conquistas", self.show_achievements), ("Cemitério", self.show_graveyard),
                        ("Itens", self.show_items)):
            self.chip(bot, _t(txt), False, fn).pack(side="left", padx=(0, 4))
        self.beside(w)

    def save(self):
        try:
            self.reader.export()
            save_state(self.state_path, self.state)
            self.last_save = time.time()
        except OSError as e:
            log(f"erro salvando: {e}")


def startup_shortcut(create: bool | None = None) -> Path:
    """Atalho na pasta Inicializar do Windows que abre o pet sem console (pythonw). Só o usuário liga, pelo menu.
    criar=True grava, False apaga, None só devolve o caminho."""
    p = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/Agent Tokenlike.cmd"
    if create:
        pyw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pyw) if pyw.exists() else "pythonw"
        p.write_text(f'@start "" "{exe}" "{Path(__file__).resolve()}"\r\n', encoding="utf-8")
    elif create is False:
        p.unlink(missing_ok=True)
    return p


def acquire_lock(name: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fh = open(DATA_DIR / name, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def migrate_old_data(old: Path = OLD_DATA_DIR, new: Path = DATA_DIR) -> bool:
    """1ª execução após o rename: copia o progresso de ~/.tokenpet sem apagar o antigo."""
    if new.exists() or not old.is_dir():
        return False
    new.mkdir(parents=True)
    for name in ("state.json", "state-demo.json"):
        if (old / name).is_file():
            shutil.copy2(old / name, new / name)
    log(f"progresso copiado de {old}")
    return True


def run_gui(args):
    global tk
    migrate_old_data()
    import tkinter as _tk
    import tkinter.font  # noqa: F401  (tk.font: medir texto para encurtar com "…")
    tk = _tk
    lock = acquire_lock("demo.lock" if args.demo else "tokenlike.lock")
    if lock is None:
        print("O Agent Tokenlike já está aberto.")
        return
    app = PetApp(args)
    app.tray = start_tray()
    app.listen_tray()
    app.root.mainloop()


def main(argv=None):
    p = argparse.ArgumentParser(description="Agent Tokenlike - Masmorra de Tokens")
    p.add_argument("--demo", action="store_true", help="tokens falsos para testar (progresso separado)")
    p.add_argument("--import-history", action="store_true",
                   help="no primeiro uso, já começa com a energia do histórico do Claude Code")
    p.add_argument("--reset", action="store_true", help="apaga todo o progresso e começa do zero")
    args = p.parse_args(argv)
    try:
        run_gui(args)
    except Exception:
        log("erro fatal: " + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
