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
import json
import math
import os
import random
import shutil
import sys
import time
import traceback
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import arte  # noqa: E402
import folha  # noqa: E402
import masmorra as M  # noqa: E402
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
GOOD = "#7ee081"
HURT = "#ff6b81"
GOLD = "#ffd23f"
CYAN = "#6fd6ff"
STATUS_COR = {"queimadura": "#ff9f43", "eletricidade": "#fff27a", "veneno": "#4fbf5a", "congelamento": "#9fe8ff"}
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


def limit_view(key: str, limits: dict | None, state: dict, now: float):
    """(pct|None, reset|None, estimado, tokens|None) para a linha da janela `key`."""
    win = WINDOWS[key]
    pct, reset = (limits or {}).get(key, (None, None))
    upd = (limits or {}).get("updated") or 0
    if pct is not None and now - upd < OFFICIAL_FRESH_S:
        return pct, reset, False, None
    cal = (state.get("calib") or {}).get(key)
    if cal:
        reset = cal["reset"]
    if reset and reset <= now:              # o reset passou: avança a janela em múltiplos dela
        reset += ((now - reset) // win + 1) * win
    start = reset - win if reset else now - win
    tok = usage_between(state, start, now)
    if cal:
        return tok * cal["f"], reset, True, None
    return None, reset, False, tok


# ------------------------------------------------------------- progresso
DEFAULT_STATE = {
    "tokens_total": 0,
    "xp_total": 0.0,
    "daily": {},
    "size": "Médio",
    "mode": "auto",              # "auto" ou "interativo" (o jogador escolhe pegar/consumir)
    "pos": None,
    "topmost": True,
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


DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


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
    return f"{DIAS[t.weekday()]} {t.strftime('%H:%M')}"


def save_state(path: Path, state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    daily = state.get("daily", {})
    for k in sorted(daily)[:-60]:
        del daily[k]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


# ----------------------------------------------------------- personagens
SLIME_PALETTE = {
    "K": "#1b1b2f", "G": "#57d36b", "L": "#b4f5a8", "D": "#2f9a4a",
    "W": "#ffffff", "B": "#1b1b2f", "P": "#ff8fb1",
    "S": "#d7dde9", "s": "#8a94a8", "R": "#e2384d", "Y": "#ffd23f", "y": "#c99a00",
}

SLIME_GOTINHA = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    ".......KK.......",
    "......KLGK......",
    ".....KLGGGK.....",
    "....KGGGGGGK....",
    "....KGWBGWBK....",
    "...KGGGGGGGGK...",
    "...KPGGKKGGPK...",
    "...KDGGGGGGDK...",
    "....KKKKKKKK....",
]

SLIME = [
    "................",
    "................",
    "................",
    "......KKKK......",
    "....KKLLGGKK....",
    "...KLLGGGGGGK...",
    "..KLGGGGGGGGGK..",
    "..KLGGGGGGGGGK..",
    ".KGGGWWGGWWGGGK.",
    ".KGGGWBGGWBGGGK.",
    ".KGPPGGGGGGPPGK.",
    ".KGGGGGKKGGGGGK.",
    ".KGGGGGGGGGGGGK.",
    ".KDGGGGGGGGGGDK.",
    "..KDDDDDDDDDDK..",
    "...KKKKKKKKKK...",
]

SLIME_CAVALEIRO = [
    "........RR......",
    ".......RRK......",
    ".....KKKKKK.....",
    "....KSSSSSSK....",
    "...KSLSSSSSsK...",
    "..KSLSSSSSSSsK..",
    "..KssssssssssK..",
    ".KGGGGGGGGGGGGK.",
    ".KGGGWWGGWWGGGK.",
    ".KGGGWBGGWBGGGK.",
    ".KGPPGGGGGGPPGK.",
    ".KGGGGGKKGGGGGK.",
    ".KGGGGGGGGGGGGK.",
    ".KDGGGGGGGGGGDK.",
    "..KDDDDDDDDDDK..",
    "...KKKKKKKKKK...",
]

REI_SLIME = [
    "....Y..YY..Y....",
    "....YY.YY.YY....",
    "....YYYYYYYY....",
    "....YRYYYYRY....",
    "...KyyyyyyyyK...",
    "..KLGGGGGGGGGK..",
    ".KLGGGGGGGGGGGK.",
    "KLGGGGGGGGGGGGGK",
    "KGGGGWWGGWWGGGGK",
    "KGGGGWBGGWBGGGGK",
    "KGGPPGGGGGGPPGGK",
    "KGGGGKGGGGKGGGGK",
    "KGGGGGKKKKGGGGGK",
    "KDGGGGGGGGGGGGDK",
    ".KDDDDDDDDDDDDK.",
    "..KKKKKKKKKKKK..",
]


def blink_grid(grid: list[str], eye_chars: str, body_char: str) -> list[str]:
    """Fecha os olhos: a última linha do olho vira traço, as de cima viram corpo."""
    eyes = [(y, x) for y, row in enumerate(grid) for x, ch in enumerate(row) if ch in eye_chars]
    bottom = {}
    for y, x in eyes:
        bottom[x] = max(bottom.get(x, y), y)
    rows = [list(r) for r in grid]
    for y, x in eyes:
        rows[y][x] = "K" if y == bottom[x] else body_char
    return ["".join(r) for r in rows]


class CharacterDef:
    def __init__(self, key, name, stages, frame_ms=600, stats=None, unlock=None, comunidade=False):
        self.key, self.name, self.frame_ms = key, name, frame_ms
        self.stats = stats or {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
        self.unlock, self.comunidade = unlock, comunidade
        # cada estágio: {"floor", "title", "frames": [spec], "blink": spec|None, "sleep": spec|None}
        # e, se vier de spritesheet, "estados": {estado: [spec]} (spec ("sheet", path, box, N))
        self.stages = sorted(stages, key=lambda s: s["floor"])

    @property
    def stage_floors(self) -> list[int]:
        return [s["floor"] for s in self.stages]


def builtin_characters() -> list[CharacterDef]:
    stages = []
    for floor, title, grid in ((1, "Gotinha", SLIME_GOTINHA), (3, "Slime", SLIME),
                               (8, "Slime Cavaleiro", SLIME_CAVALEIRO), (15, "Rei Slime", REI_SLIME)):
        closed = ("grid", blink_grid(grid, "WB", "G"), SLIME_PALETTE)
        stages.append({"floor": floor, "title": title, "frames": [("grid", grid, SLIME_PALETTE)],
                       "blink": closed, "sleep": closed})
    return [CharacterDef("slime", "Slime", stages, stats={"hp": 20, "atk": 3, "def": 0, "dodge": 0})]


DEFAULT_STATS = {"hp": 20, "atk": 3, "def": 0, "dodge": 0, "spd": 10.0}
_FOLHAS = {}  # (caminho, mtime) -> (linhas de caixas, N): cada folha é cortada uma vez
_IMGS = {}    # ponytail: nunca esvaziado (poucas folhas por sessão); limpar ao trocar de herói se crescer
# caminho -> (mtime, PhotoImage): spec_to_map não reabre o PNG a cada quadro


def _img_folha(path: Path):
    mt = path.stat().st_mtime
    if _IMGS.get(str(path), (None,))[0] != mt:
        _IMGS[str(path)] = (mt, tk.PhotoImage(file=str(path)))
    return _IMGS[str(path)][1]


def ler_folha(path: Path):
    """Linhas de caixas da folha e o fator N de redução. Grade fixa quando o tamanho bate; senão corte
    automático numa grade de opacidade amostrada (1 a cada N px), porque a máscara completa é lenta."""
    ck = (str(path), path.stat().st_mtime)
    if ck not in _FOLHAS:
        src = _img_folha(path)
        w, h = src.width(), src.height()
        grade = folha.detectar_grade(w, h)
        if grade:
            cols, lins = grade
            cw, ch = w // cols, h // lins
            a = folha.fator_reducao(ch)   # varredura amostrada: transparency_get do Tk é lento
            ocup = [[(ox, oy) for ox in range(0, cw, a) for oy in range(0, ch, a)
                     if not src.transparency_get(c * cw + ox, r * ch + oy)]
                    for r in range(lins) for c in range(cols)]
            pts = [p for cel in ocup for p in cel]
            if not pts:
                raise ValueError(f"folha sem quadros: {path.name}")
            # uma caixa só (união do opaco de todas as células) para os quadros não tremerem
            ox0, oy0 = min(x for x, _ in pts), min(y for _, y in pts)
            ox1, oy1 = min(cw, max(x for x, _ in pts) + a), min(ch, max(y for _, y in pts) + a)
            linhas = [[(c * cw + ox0, r * ch + oy0, c * cw + ox1, r * ch + oy1) for c in range(cols)]
                      if any(ocup[r * cols + c] for c in range(cols)) else [] for r in range(lins)]
            n = folha.fator_reducao(oy1 - oy0)
        else:
            # ponytail: caixas com precisão de N px (amostra); corte exato custa ~5 s em folha grande
            n = folha.fator_reducao(h // 9)
            ws, hs = -(-w // n), -(-h // n)
            op = [[not src.transparency_get(x * n, y * n) for x in range(ws)] for y in range(hs)]
            linhas = [[(x0 * n, y0 * n, min(w, x1 * n), min(h, y1 * n)) for x0, y0, x1, y1 in lin]
                      for lin in folha.cortar(ws, hs, lambda x, y: op[y][x])]
            if any(linhas):  # N pela altura real das linhas, não pela suposição de 9 linhas
                n = folha.fator_reducao(max(c[3] - c[1] for lin in linhas for c in lin))
        if not any(linhas):
            raise ValueError(f"folha sem quadros: {path.name}")
        _FOLHAS[ck] = linhas, n
    return _FOLHAS[ck]


def stage_da_folha(path: Path, floor: int, title: str) -> dict:
    """Estágio de herói de spritesheet: estados na ordem das linhas; linha vazia ou ausente usa o Idle."""
    linhas, n = ler_folha(path)
    specs = [[("sheet", path, c, n) for c in lin] for lin in linhas]
    idle = next(l for l in specs if l)
    estados = {e: (specs[i] if i < len(specs) and specs[i] else idle) for i, e in enumerate(folha.ESTADOS)}
    return {"floor": floor, "title": title, "frames": estados["idle"], "blink": None, "sleep": None,
            "estados": estados}


def load_png_characters(folder: Path = CHARACTERS_DIR) -> list[CharacterDef]:
    out = []
    if not folder.is_dir():
        return out
    for d in sorted(folder.iterdir()):
        cfg = d / "character.json"
        if not cfg.is_file():
            if (d / "spritesheet.png").is_file():   # folha sem character.json: um estágio, stats padrão
                try:
                    out.append(CharacterDef(d.name, d.name, [stage_da_folha(d / "spritesheet.png", 1, d.name)],
                                            stats=dict(DEFAULT_STATS)))
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
                    stages.append(stage_da_folha(spec(st["sheet"])[1], int(st.get("floor", default_floor)),
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
            out.append(CharacterDef(d.name, data.get("name", d.name), stages,
                                    int(data.get("frame_ms", 600)), stats, unlock))
        except Exception as e:  # personagem com defeito não derruba o app
            log(f"personagem '{d.name}' ignorado: {e}")
    return out


def petdex_dirs() -> list[Path]:
    """Pastas de pets do Petdex (só lidas, nunca escritas). Lidas na hora para o teste trocar o HOME."""
    return [Path.home() / ".petdex" / "pets", Path.home() / ".codex" / "pets"]


def load_petdex_characters() -> list[CharacterDef]:
    """Pets da comunidade: o .png da pasta (de preferência spritesheet.png) e só o `name` do pet.json."""
    out = []
    for base in petdex_dirs():
        if not base.is_dir():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            pngs = sorted(d.glob("*.png"), key=lambda p: (p.name != "spritesheet.png", p.name))
            if not pngs:
                if any(d.glob("*.webp")):
                    log(f"pet '{d.name}' ignorado: só tem WebP; converta para PNG para usar este pet")
                continue
            name = d.name
            try:
                name = str(json.loads((d / "pet.json").read_text(encoding="utf-8")).get("name") or d.name)
            except (OSError, ValueError, AttributeError):
                pass   # pet.json ausente ou inválido: fica o nome da pasta
            try:
                out.append(CharacterDef("petdex:" + d.name, name, [stage_da_folha(pngs[0], 1, name)],
                                        stats=dict(DEFAULT_STATS), comunidade=True))
            except Exception as e:
                log(f"pet '{d.name}' ignorado: {e}")
    return out


def all_characters() -> dict[str, CharacterDef]:
    chars = {c.key: c for c in builtin_characters()}
    for c in load_png_characters() + load_petdex_characters():
        chars.setdefault(c.key, c)
    return chars


# ------------------------------------------------------------------- GUI
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


def spec_to_map(spec):
    """Spec do herói -> PixelMap com o quadro em (0..16, 0..16), centrado na horizontal e base em y = 16."""
    if spec[0] == "sheet":
        _, path, (x0, y0, x1, y1), n = spec
        src = _img_folha(path)
        pm = {((x - x0) // n, (y - y0) // n): _hex(src.get(x, y))
              for y in range(y0, y1, n) for x in range(x0, x1, n) if not src.transparency_get(x, y)}
        if not pm:
            return {}
        w, lado = -(-(x1 - x0) // n), 16 * spec_k(spec)
        dx, dy = (lado - w) // 2, lado - 1 - max(y for _, y in pm)   # base do desenho na base do quadro
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
    dx, dy = (16 - w) // 2, 16 - h
    return {(x + dx, y + dy): c for (x, y), c in pm.items()}


def spec_altura(spec) -> int:
    """Altura final (já reduzida) do quadro; grid e PNG solto ficam em 16."""
    if spec[0] == "sheet":
        return -(-(spec[2][3] - spec[2][1]) // spec[3])
    return 16


def spec_k(spec) -> int:
    return max(1, round(spec_altura(spec) / 16))


def render_map(pm, s: int, k: int = 1):
    """Imagem com origem em look_box(k) (tamanho sempre fixo) e quantos px de tela ela desce abaixo da base.
    `s` = px de tela por pixel do mapa (herói de altura H: s = px_heroi); k = H/16 arredondado (escala dos looks)."""
    box = visual.look_box(k)
    x0, y0, x1, y1 = box
    img = tk.PhotoImage(width=(x1 - x0) * s, height=(y1 - y0) * s)
    for (x, y), c in visual.crop(pm, box).items():
        img.put(c, to=((x - x0) * s, (y - y0) * s, (x - x0 + 1) * s, (y - y0 + 1) * s))
    return img, (y1 - 16 * k) * s


_ITEM_ARTS = {}


ELEMENTO_LOOK = {"queimar": "chamas", "eletrizar": "faiscas", "envenenar": "gotas_veneno", "congelar": "geada"}


def pet_looks(run):
    """Looks dos itens [(look, brilho)] + um look animado por elemento que o pet aplica e ainda não aparece."""
    looks = [(M.ITEMS[it["key"]]["look"], M.RAR_COLOR.get(it["rar"]))
             for it in run["items"] if it["key"] in M.ITEMS]
    tipos = {l["type"] for l, _ in looks}
    st = M.stats(run)
    return looks + [({"type": t}, None) for k, t in ELEMENTO_LOOK.items() if st[k] > 0 and t not in tipos]


def item_arts():
    """Arte dos itens como PixelMap (em cache: nunca muda)."""
    if not _ITEM_ARTS:
        _ITEM_ARTS.update({k: visual.grid_to_map(g, arte.PAL) for k, g in arte.ITEM_ART.items()})
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
                ["Bem-vindo à Masmorra de Tokens!",
                 "Seus tokens do Claude Code viram energia",
                 "e eu desço a masmorra sozinho.",
                 "Arraste para me mover · botão direito = menu",
                 "Duplo clique = status"], 10000))
        if self.demo:
            self.root.after(500, lambda: self.floater("MODO DEMO", GOLD))
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
        return not c.unlock or c.unlock in self.meta["achievements"]

    def new_run(self, announce=True):
        key = self.meta.get("next_char", "slime")
        c = self.chars.get(key)
        if c is None or not self.is_unlocked(c):
            key, c = "slime", self.chars["slime"]
        # a energia que sobrou passa para a run nova (tokens não se perdem)
        energy = self.state["run"]["energy"] if self.state.get("run") else 0.0
        self.state["run"] = M.new_run(key, c.stats, self.meta["runs"] + 1)
        self.state["run"]["energy"] = energy
        self.state["run"]["ach_start"] = list(self.meta["achievements"])
        self.respawn_at = None
        self.pet_status = None
        if announce:
            self.build()
            self.popup([f"Run #{self.run['id']} começou!", f"{c.name} entra na masmorra..."], 5000)

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
        c.create_rectangle(6, py, self.W - 6, py + 52 + self.limit_h, fill=PANEL_BG,
                           outline=PANEL_EDGE, width=2)
        self.title_txt = c.create_text(14, py + 11, anchor="w", fill=TEXT, font=self.font)
        self.hp_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=HURT, font=self.font)
        self.status_y = py + 11
        self.status_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=MUTED, font=self.font_small)
        self.info_txt = c.create_text(14, py + 26, anchor="w", fill=MUTED, font=self.font_small)
        self.bar_x0, self.bar_x1, self.bar_y = 14, self.W - 14, py + 38
        c.create_rectangle(self.bar_x0, self.bar_y, self.bar_x1, self.bar_y + 6, fill=BAR_BG, outline="")
        self.bar = c.create_rectangle(self.bar_x0, self.bar_y, self.bar_x0, self.bar_y + 6,
                                      fill=ENERGY, outline="")
        self.limit_rows = {}
        # colunas fixas medidas com o texto mais largo: rótulo | barra | reset
        y = py + 56
        probe = c.create_text(14, y, anchor="w", text="Semana  ~100%", font=self.font_small)
        lx0 = c.bbox(probe)[2] + 8
        c.itemconfigure(probe, anchor="e", text="reseta sáb 00:00")
        c.coords(probe, self.W - 14, y)
        lx1 = max(lx0 + 4, c.bbox(probe)[0] - 8)
        c.delete(probe)
        for i, (key, label) in enumerate((("sessao", "Sessão"), ("semana", "Semana"))):
            y = py + 52 + 4 + i * 13
            back = c.create_rectangle(lx0, y - 3, lx1, y + 3, fill=BAR_BG, outline="")
            self.limit_rows[key] = (
                label,
                c.create_text(14, y, anchor="w", fill=MUTED, font=self.font_small),
                c.create_rectangle(lx0, y - 3, lx0, y + 3, fill=GOOD, outline=""),
                c.create_text(self.W - 14, y, anchor="e", fill=MUTED, font=self.font_small),
                lx0, lx1, y, back)
        self.refresh_look()
        self.update_panel()

    def art_img(self, key, boss=False, status=None):
        """Imagem (em cache) de um desenho do arte.py; com status, tingida na cor dele."""
        ck = (key, boss, status)
        if ck not in self.art:
            pal = arte.BOSS_PAL if boss else arte.PAL
            if status:      # tingir a paleta = tingir cada pixel (o contorno escuro fica intacto)
                pal = visual.tingir(pal, STATUS_COR[status], 0.5)
            self.art[ck] = render_grid(arte.all_art()[key], pal, self.bpx if boss else self.px)
        return self.art[ck]

    def load_images(self):
        stage = self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)]
        try:
            # só os mapas de pixels; as imagens saem de refresh_look (com os itens por cima)
            self.frame_maps = [spec_to_map(s) for s in stage["frames"]]
            self.blink_map = spec_to_map(stage["blink"]) if stage["blink"] else None
            self.sleep_map = spec_to_map(stage["sleep"]) if stage["sleep"] else None
        except Exception as e:
            if self.char.key == "slime":
                raise
            log(f"erro carregando imagens de '{self.char.key}': {e}; voltando para o Slime")
            self.run["char"] = "slime"
            return self.load_images()
        # herói de spritesheet: os mapas de cada estado (os antigos não têm "estados")
        self.estado_maps = {e: [spec_to_map(sp) for sp in specs]
                            for e, specs in stage.get("estados", {}).items()}
        self.stage_title = stage["title"]
        h = spec_altura(stage["frames"][0])
        self.hero_k, self.hero_px = spec_k(stage["frames"][0]), max(1, round(self.px * 16 / h))

    def refresh_look(self, k: int = None, px_heroi: int = None):
        """Recompõe as imagens do pet com os looks dos itens. Só quando a lista muda, nunca no tick.
        Herói de altura H: k = H/16 e px_heroi = max(1, round(px*16/H)) (padrão: 16 px, k=1, px)."""
        k = k or getattr(self, "hero_k", 1)
        px_heroi = px_heroi or getattr(self, "hero_px", None) or self.px
        looks = pet_looks(self.run)
        arts = item_arts()
        cor = STATUS_COR.get(self.pet_status)

        # looks elementais animam em FASES quadros; sem eles, uma fase só (nenhuma imagem a mais)
        fases = range(visual.FASES if visual.tem_animacao(looks) else 1)

        def mapa(pm, fase):
            m = visual.compose(pm, looks, arts, fase, k)
            return visual.tingir(m, cor, 0.5) if cor else m   # com status, o pet fica na cor dele (todas as fases)

        def img(m):
            im, self.below = render_map(m, px_heroi, k)
            return im

        mapas = [[mapa(pm, j) for j in fases] for pm in self.frame_maps]
        self.look_maps = [q[0] for q in mapas]                    # fase 0 de cada quadro
        # imagens indexadas [quadro_do_heroi][fase]; o tick só escolhe qual mostrar
        self.frames_fx = [[img(m) for m in q] for q in mapas]
        self.blink_fx = [img(mapa(self.blink_map, j)) for j in fases] if self.blink_map else None
        self.sleep_fx = ([img(mapa(self.sleep_map, j)) for j in fases] if self.sleep_map
                         else (self.blink_fx or self.frames_fx[0]))
        # estados da folha: [quadro][fase], compostos uma vez aqui (o idle reaproveita frames_fx)
        self.estados_fx = {e: (self.frames_fx if e == "idle" else [[img(mapa(pm, j)) for j in fases] for pm in pms])
                           for e, pms in getattr(self, "estado_maps", {}).items()}
        self.canvas.itemconfigure(self.sprite, image=self.frames_fx[0][0])
        self.place_pet(0, 0)

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
        self.canvas.itemconfigure(self.title_txt, text=f"{self.stage_title}  ·  Run #{run['id']}")
        self.canvas.itemconfigure(self.hp_txt, text=f"♥ {run['hp']}/{st['maxhp']}")
        x0 = self.canvas.bbox(self.hp_txt)[0] - 8
        self.canvas.coords(self.status_txt, x0, self.status_y)
        self.canvas.itemconfigure(self.status_txt, text=self.pet_status or "",
                                  fill=STATUS_COR.get(self.pet_status, MUTED))
        self.canvas.itemconfigure(
            self.info_txt,
            text=f"Andar {run['floor']}-{run['room']}   ATK {st['atk']}  DEF {st['def']}   $ {run['gold']}")
        cost = M.room_cost(run)
        frac = min(1.0, run["energy"] / cost) if cost else 0
        x1 = self.bar_x0 + (self.bar_x1 - self.bar_x0) * frac
        self.canvas.coords(self.bar, self.bar_x0, self.bar_y, x1, self.bar_y + 6)
        self.update_limits()

    def update_limits(self):
        now = time.time()
        for key, (label, txt, fill, rtxt, lx0, lx1, y, back) in self.limit_rows.items():
            pct, reset, est, tok = limit_view(key, self.limits, self.state, now)
            self.canvas.itemconfigure(rtxt, text=f"reseta {fmt_reset(reset, now)}" if reset else "")
            if pct is None:                 # sem fator: só os tokens da janela, sem barra de %
                self.canvas.itemconfigure(txt, text=f"{label}  {fmt(tok)}" if tok else f"{label}  —")
                self.canvas.coords(fill, lx0, y - 3, lx0, y + 3)
                self.canvas.itemconfigure(back, state="hidden")
                continue
            self.canvas.itemconfigure(back, state="normal")
            self.canvas.itemconfigure(txt, text=f"{label}  {'~' if est else ''}{round(pct)}%")
            frac = max(0.0, min(1.0, pct / 100))
            self.canvas.coords(fill, lx0, y - 3, lx0 + (lx1 - lx0) * frac, y + 3)
            self.canvas.itemconfigure(fill, fill=limit_color(pct))

    def refresh_limits(self):
        """Relê limites.json (opcional), calibra a estimativa com leitura oficial nova e redesenha."""
        now = time.time()
        self.limits = read_limits(DATA_DIR / "limites.json", now)
        calibrate(self.state, self.limits, now)
        self.update_limits()

    def build_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Status", command=self.show_stats)
        self.menu.add_command(label="Cemitério", command=self.show_graveyard)
        self.menu.add_command(label="Conquistas", command=self.show_achievements)
        self.char_menu = tk.Menu(self.menu, tearoff=0)
        self.char_var = tk.StringVar(value=self.meta.get("next_char", "slime"))
        self.menu.add_cascade(label="Herói da próxima run", menu=self.char_menu)
        self.fill_char_menu()
        size_menu = tk.Menu(self.menu, tearoff=0)
        self.size_var = tk.StringVar(value=self.state["size"])
        for name in SIZES:
            size_menu.add_radiobutton(label=name, value=name, variable=self.size_var,
                                      command=self.change_size)
        self.menu.add_cascade(label="Tamanho", menu=size_menu)
        mode_menu = tk.Menu(self.menu, tearoff=0)
        self.mode_var = tk.StringVar(value=self.state["mode"])
        for key, label in MODES.items():
            mode_menu.add_radiobutton(label=label, value=key, variable=self.mode_var,
                                      command=self.change_mode)
        self.menu.add_cascade(label="Modo", menu=mode_menu)
        self.top_var = tk.BooleanVar(value=bool(self.state["topmost"]))
        self.menu.add_checkbutton(label="Sempre por cima", variable=self.top_var,
                                  command=self.toggle_top)
        self.menu.add_separator()
        self.menu.add_command(label="Desistir da run (começa outra)", command=self.give_up)
        self.menu.add_separator()
        self.menu.add_command(label="Abrir pasta de personagens", command=self.open_chars)
        self.menu.add_command(label="Recarregar personagens", command=self.reload_chars)
        self.menu.add_separator()
        self.menu.add_command(label="Sair", command=self.quit)

    def fill_char_menu(self):
        self.char_menu.delete(0, "end")
        proprios = [(k, c) for k, c in self.chars.items() if not c.comunidade]
        comunidade = [(k, c) for k, c in self.chars.items() if c.comunidade]
        for key, c in proprios:
            if self.is_unlocked(c):
                self.char_menu.add_radiobutton(label=c.name, value=key, variable=self.char_var,
                                               command=self.change_character)
            else:
                self.char_menu.add_command(
                    label=f"{c.name}  [bloqueado: {M.ACHIEVEMENTS[c.unlock]}]", state="disabled")
        if comunidade:
            self.char_menu.add_separator()
            self.char_menu.add_command(label="Comunidade", state="disabled")
            for key, c in comunidade:
                self.char_menu.add_radiobutton(label=c.name, value=key, variable=self.char_var,
                                               command=self.change_character)

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
            self.estado_tmp = ("waving", time.time() + 1.0)
        self._drag = None

    def on_menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def change_character(self):
        key = self.char_var.get()
        self.meta["next_char"] = key
        name = self.chars[key].name
        run = self.run
        if run["floor"] == 1 and run["room"] == 0 and not run["dead"]:
            self.new_run()      # run nem começou: troca na hora
        else:
            self.popup([f"{name} entra na próxima run."], 4000)

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

    def toggle_top(self):
        self.state["topmost"] = bool(self.top_var.get())
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
        self.floater(f"{len(self.chars)} personagens", MUTED)

    def quit(self):
        self.save()
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

        self._ultimo_kind = [ev["kind"]]               # só para o teste
        kind = ev["kind"]
        foes = ev.get("foes") or []
        name_color = {"boss": HURT, "monster": TEXT, "horde": TEXT, "mimic": HURT, "stairs": CYAN}.get(kind, GOLD)

        def nova_sala():
            self.set_pet_status(None)                  # status do pet não passa de uma sala para outra
            self.update_panel()
        at(0, nova_sala)
        if foes:
            at(0, lambda: self.show_foes(foes))
        else:
            at(0, lambda: self.show_foe(ev.get("sprite"), ev.get("boss", False)))
        at(0, lambda: self.floater(ev["name"], name_color, x=self.fcx, life=22, top=True))
        if ev.get("cura_item"):                        # cura_sala / cura_andar dos itens
            at(250, lambda: self.floater(f"+{ev['cura_item']} ♥", GOOD))
        t = 500

        if kind in ("monster", "boss", "mimic", "horde"):
            hits = ev["hits"]
            # quem já morreu depois de cada passo (contando a lista inteira, mesmo os passos não mostrados)
            hp = [f["hp_max"] for f in foes]
            mortos_ate, status_ate, s = [], [], None
            for h in hits:
                if h["target"] != "pet" and not h["skip"]:
                    hp[h["target"]] -= h["dmg"]
                if h["target"] == "pet" and h["status"] and not h["skip"]:
                    s = h["status"]                    # último status do pet até aqui (vale p/ passos pulados)
                mortos_ate.append([i for i, v in enumerate(hp) if v <= 0])
                status_ate.append(s)
            idx = list(range(len(hits)))
            if len(idx) > 12:                          # lutas longas: os 11 primeiros passos e o último
                idx = idx[:11] + [idx[-1]]
            for k in idx:
                at(t, lambda h=hits[k], mortos=mortos_ate[k], s=status_ate[k]: self.anim_hit(h, mortos, s))
                t += 380
            if ev["won"]:
                at(t, lambda: self.hide_foe(burst=True))
                t += 300
                at(t, lambda: self.floater(f"+{ev.get('gold', 0)} $", GOLD, x=self.fcx))
                t += 450
            elif ev.get("empate"):
                at(t, lambda: (self.floater("empate", MUTED, x=self.fcx), self.hide_foe()))
                t += 450
            at(t, lambda: self.set_pet_status(None))  # o status do pet acaba com a luta
        elif kind == "trap":
            if ev.get("dodged"):
                at(t, lambda: self.floater("esquivou!", CYAN))
            elif ev["dmg"] == 0:                       # o escudo absorveu tudo
                at(t, lambda: self.floater("bloqueou!", CYAN))
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
            at(t, lambda: self.floater(M.ITEMS[key]["name"], M.RAR_COLOR.get(rar) or GOLD,
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
        self.luta_until = self.busy_until if kind in ("monster", "boss", "mimic", "horde") else 0

    def _offer_steps(self, ev, at, t):
        """Animação das linhas e da oferta resolvida (item pego ou consumido); devolve o novo t."""
        for line in ev["lines"]:
            at(t, lambda line=line: self.floater(line, TEXT, life=24))
            t += 600
        if ev.get("item"):
            key, rar = ev["item"]["key"], ev["item"]["rar"]
            it = M.ITEMS[key]
            at(t, lambda: self.show_foe(key, False))
            at(t, lambda: self.floater(it["name"], GOLD, x=self.fcx, life=24))
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
                at(t, lambda: self.floater("HP já cheio", MUTED))
            else:
                at(t, lambda: self.floater(f"+{c['shield']} escudo", CYAN))
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

    def anim_hit(self, h, mortos, status):
        """Um passo da luta: floaters, bote, tinta de status e some com quem morreu até aqui."""
        tgt, who = h["target"], h["who"]

        def fx(i):
            return self.foe_xy[i][0] if i in self.foe_on else self.fcx
        x = None if tgt == "pet" else fx(tgt)
        txt = f"-{h['dmg']}" + ("!" if h["crit"] else "") + (" x2" if h.get("duplo") else "")
        if h["skip"]:
            self.floater("perdeu a vez", MUTED, x=None if who == "pet" else fx(who), life=10)
        elif h["dot"]:
            self.floater(str(h["dmg"]), STATUS_COR.get(h["status"], HURT), x=x, life=8)
        elif h["dodge"]:
            self.floater("esquivou!", CYAN, life=10)
        elif h.get("bloqueado"):
            self.foe_attack(who)
            self.floater("bloqueou!", CYAN, life=10)
        elif h.get("espinhos"):                           # espinhos: o dano volta para o atacante, sem bote
            self.floater(f"-{h['dmg']}", GOOD, x=x, life=10)
        elif who == "ajudante":                           # ajudante: o número sai de cima do pet, sem bote
            self.floater(txt, GOOD, life=10)
        elif who == "pet":
            self.lunge = [5, 10, 5, 0]
            self.floater(txt, GOLD if h["crit"] else TEXT, x=x, life=10)
            if h["status"] and tgt in self.foe_on:        # ataque elemental: clarão na cor do elemento
                self.burst(x, self.foe_xy[tgt][1] - 4 * self.px, colors=(STATUS_COR[h["status"]], "#ffffff"))
                # ponytail: a tinta fica até o inimigo morrer (a GUI não sabe quando o status acaba)
                self.draw_foe(tgt, h["status"])
        else:
            self.foe_attack(who)
            if h["dmg"]:
                self.floater(txt, GOLD if h["crit"] else HURT, life=10)
            else:
                self.floater("bloqueou!", CYAN, life=10)
        self.set_pet_status(status)
        for i in mortos:
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
        self.estado_tmp = ("jumping", time.time() + 1.2)
        self.floater("EVOLUIU!", GOLD, life=22)
        self.popup([f"{old} evoluiu para {self.stage_title}!", "+4 HP máx, +1 ATK"], 5000)

    def log_run(self, killer, gave_up):
        rec = M.run_record(self.run, killer, gave_up, self.state["mode"],
                           self.run.get("ach_start", self.meta["achievements"]),
                           killer_kind=self.meta["graveyard"][-1].get("kind", ""))
        append_run_record(rec, self.demo)

    def on_death(self):
        g = self.meta["graveyard"][-1]
        self.log_run(g["killer"], False)
        self.save()
        if getattr(self, "estados_fx", None):       # herói de folha: quadros "failed" antes da lápide
            self.estado_tmp = ("failed", time.time() + 1.2)
            self.root.after(1200, lambda: self.run["dead"] and self.show_tomb())
        else:
            self.show_tomb()
        self.burst(self.pcx, self.base_y - self.T // 3, colors=("#8a94a8", "#d7dde9", HURT))
        best = self.meta["best"]
        self.popup([f"{self.stage_title} morreu no andar {g['floor']}-{g['room']}",
                    f"Derrotado por: {g['killer']}",
                    f"Monstros vencidos: {g['kills']}   Ouro: {g['gold']}",
                    f"Recorde: andar {best['floor']}-{best['room']}",
                    "Uma nova run começa em instantes..."], RESPAWN_S * 1000)
        self.respawn_at = time.time() + RESPAWN_S

    def show_tomb(self):
        self.canvas.itemconfigure(self.sprite, image=self.art_img("lapide"))
        self.canvas.coords(self.sprite, self.pcx, self.base_y)
        self.hide_foe()

    def announce_unlocks(self, keys):
        lines = ["CONQUISTA!"]
        for k in keys:
            lines.append(M.ACHIEVEMENTS[k])
            gains = self.unlock_rewards(k)
            if gains:
                lines.append("  libera: " + ", ".join(gains))
        self.fill_char_menu()
        self.popup(lines, 9000)

    def unlock_rewards(self, ach):
        items = [it["name"] for it in M.ITEMS.values() if it.get("req") == ach]
        chars = [f"herói {c.name}" for c in self.chars.values() if c.unlock == ach]
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
        vivos = [c.bbox(f[0][0]) for f in self.floaters]
        opcoes = []
        for dy in (0, -16, 16, -32, 32, -48):
            for dx in (0, -34, 34):
                c.coords(t, bx + dx, by + dy)
                x0, y0, x1, y1 = c.bbox(t)
                shift = max(0, 4 - (x0 - 5)) - max(0, (x1 + 5) - (self.W - 4))
                box = (x0 + shift - 5, y0 - 2, x1 + shift + 5, y1 + 2)
                if box[1] >= 0 and box[3] < self.panel_y:      # nunca por cima do painel
                    opcoes.append((bx + dx + shift, by + dy, box))
        livres = [o for o in opcoes if not any(
            v and o[2][0] < v[2] and v[0] < o[2][2] and o[2][1] < v[3] and v[1] < o[2][3] for v in vivos)]
        if livres or opcoes:
            fx, fy, box = (livres or opcoes)[0]
        else:
            fx, fy = bx, by
            x0, y0, x1, y1 = c.bbox(t)
            box = (x0 - 5, y0 - 2, x1 + 5, y1 + 2)
        c.coords(t, fx, fy)
        r = c.create_rectangle(*box, fill=PANEL_BG, outline=PANEL_EDGE, tags=tags)
        c.tag_raise(t)
        c.tag_raise("nome")
        self.floaters.append([(r, t), life])

    def burst(self, x, y, colors=(GOLD, "#ffffff", GOOD)):
        for i in range(16):
            a = i * math.pi / 8
            r = self.canvas.create_rectangle(x - 3, y - 3, x + 3, y + 3,
                                             fill=self.rng.choice(colors), outline="")
            self.particles.append([r, math.cos(a) * 6, math.sin(a) * 6, 12])

    def estado_atual(self, now, descansando):
        """Estado da folha a mostrar (None para heróis sem estados): escolha > luta > morte > descanso > idle;
        waving/jumping valem pelo tempo marcado."""
        if not getattr(self, "estados_fx", None):
            return None
        tmp, ate = getattr(self, "estado_tmp", (None, 0))
        if self.run["dead"]:
            return "failed" if tmp == "failed" and now < ate else None
        if self.run["pending"]:
            return "review"
        if now < getattr(self, "luta_until", 0):
            return "running"
        if tmp in ("waving", "jumping") and now < ate:
            return tmp
        return "waiting" if descansando else "idle"

    def quadro_estado(self, estado, now):
        qs = self.estados_fx[estado]
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
                if self.estado_atual(now, False) == "failed":
                    self.canvas.itemconfigure(self.sprite, image=self.quadro_estado("failed", now))
            else:
                sleeping = idle > SLEEP_AFTER_S and not busy
                fase = int(now * 1000 / FX_MS)       # relógio dos efeitos, separado do herói
                estado = self.estado_atual(now, idle > REST_AFTER_S and not busy)
                if estado:
                    img = self.quadro_estado(estado, now)
                    bob = 0
                elif sleeping:
                    img = self.sleep_fx[fase % len(self.sleep_fx)]
                    bob = -2 if int(now / 1.4) % 2 else 0
                    if now > self.next_zzz:
                        self.floater("z Z", MUTED, life=20)
                        self.next_zzz = now + 3
                else:
                    if self.blink_fx is not None and now > self.next_blink:
                        self.blink_until = now + 0.16
                        self.next_blink = now + self.rng.uniform(2.5, 6)
                    if self.blink_fx is not None and now < self.blink_until:
                        img = self.blink_fx[fase % len(self.blink_fx)]
                    else:
                        q = self.frames_fx[int(now * 1000 / self.char.frame_ms) % len(self.frames_fx)]
                        img = q[fase % len(q)]
                    bob = -2 if int(now / 0.6) % 2 else 0
                dy = self.hop.pop(0) if self.hop else bob
                dx = self.lunge.pop(0) if self.lunge else 0
                self.canvas.itemconfigure(self.sprite, image=img)
                self.place_pet(dx, dy)
            if self.foe_lunge and self.lunge_foe < len(self.foe_xy):
                x, y = self.foe_xy[self.lunge_foe]
                self.canvas.coords(self.foe_items[self.lunge_foe][0], x + self.foe_lunge.pop(0), y)

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
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=PANEL_BG, highlightbackground=PANEL_EDGE, highlightthickness=2)
        tk.Label(w, text="\n".join(lines), justify="left", bg=PANEL_BG, fg=TEXT,
                 font=self.font, padx=10, pady=8).pack()
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
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=PANEL_BG, highlightbackground=PANEL_EDGE, highlightthickness=2)
        self.choice_img = self.art_img(key)       # referência: o tk não guarda a imagem sozinho
        tk.Label(w, image=self.choice_img, bg=PANEL_BG).pack(pady=(8, 2))
        tk.Label(w, text=f"{it['name']}  ·  {M.RAR_NAMES[rar]}", bg=PANEL_BG,
                 fg=M.RAR_COLOR.get(rar) or TEXT, font=self.font).pack(padx=10)
        cf = M.consume_fx(key, rar)
        cons = f"+{cf['heal']} ♥" if "heal" in cf else f"+{cf['shield']} escudo"
        tk.Label(w, text=f"Pegar: {M.fx_text(M.item_fx(key, rar))}\nConsumir: {cons}",
                 justify="left", bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(padx=10)
        row = tk.Frame(w, bg=PANEL_BG)
        row.pack(pady=4)
        for label, choice in (("Pegar", "pegar"), ("Consumir", "consumir")):
            tk.Button(row, text=label, command=lambda c=choice: self.choose(c), bg=PANEL_EDGE,
                      fg=TEXT, activebackground=PANEL_EDGE, activeforeground=TEXT, relief="flat",
                      bd=0, font=self.font_small, padx=8, pady=2).pack(side="left", padx=4)
        self.choice_cv = tk.Canvas(w, width=CHOICE_BAR_W, height=6, bg=BAR_BG,
                                   highlightthickness=0, bd=0)
        self.choice_cv.pack(pady=(2, 2))
        self.choice_bar = self.choice_cv.create_rectangle(0, 0, CHOICE_BAR_W, 6, fill=ENERGY,
                                                          outline="")
        self.choice_wait = tk.Label(w, text="", bg=PANEL_BG, fg=MUTED, font=self.font_small)
        self.choice_wait.pack(pady=(0, 6))
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
        self.choice_cv.coords(self.choice_bar, 0, 0, CHOICE_BAR_W * left, 6)
        rooms = int(self.run["energy"] // M.room_cost(self.run))
        wait = "" if rooms < 1 else ("1 sala esperando" if rooms == 1 else f"{rooms} salas esperando")
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
        lines = [f"Run #{run['id']}  -  {self.char.name} ({self.stage_title})"
                 f"    Modo: {MODES[self.state['mode']]}",
                 f"Andar {run['floor']}-{run['room']}    ♥ {run['hp']}/{st['maxhp']}",
                 f"ATK {st['atk']}   DEF {st['def']}   Esquiva {int(st['dodge'] * 100)}%"
                 f"   Ouro {run['gold']}",
                 f"Velocidade {round(st['spd'])}   Crítico {round(st['crit'] * 100)}%"
                 f"   Dano crítico ×{st['critdmg']:g}",
                 "Itens:"]
        for i in run["items"]:
            lines.append(f"  {M.ITEMS[i['key']]['name']} ({M.RAR_NAMES[i['rar']]}):"
                         f" {M.fx_text(M.item_fx(i['key'], i['rar']))}")
        if not run["items"]:
            lines.append("  -")
        if run["shield"] > 0:
            lines.append(f"Escudo: {run['shield']}")
        if run["pending"]:
            lines.append(f"Esperando escolha: {M.ITEMS[run['pending']['key']]['name']}")
        stored = int(run["energy"] // M.room_cost(run))
        best = meta["best"]
        today = self.state["daily"].get(date.today().isoformat(), 0)
        lines += [f"Energia guardada: {stored} sala(s)",
                  f"Recorde: andar {best['floor']}-{best['room']}    Runs: {meta['runs']}",
                  f"Tokens hoje: {fmt(today)}    Total: {fmt(self.state['tokens_total'])}"]
        if self.demo:
            lines.append("(modo demo)")
        self.popup(lines, 14000)

    def show_graveyard(self):
        g = self.meta["graveyard"]
        best = self.meta["best"]
        lines = [f"Cemitério  (recorde: andar {best['floor']}-{best['room']})"]
        if not g:
            lines.append("Ninguém morreu ainda...")
        for d in reversed(g[-10:]):
            name = self.chars[d["char"]].name if d["char"] in self.chars else d["char"]
            lines.append(f"#{d['run']} {name}: andar {d['floor']}-{d['room']}, {d['killer']}"
                         f" ({len(d['items'])} itens)")
        self.popup(lines, 14000)

    def show_achievements(self):
        have = set(self.meta["achievements"])
        lines = ["Conquistas"]
        for k, desc in M.ACHIEVEMENTS.items():
            mark = "[x]" if k in have else "[  ]"
            gains = self.unlock_rewards(k)
            lines.append(f"{mark} {desc}" + (f"  ->  {', '.join(gains)}" if gains else ""))
        self.popup(lines, 14000)

    def save(self):
        try:
            self.reader.export()
            save_state(self.state_path, self.state)
            self.last_save = time.time()
        except OSError as e:
            log(f"erro salvando: {e}")


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
    tk = _tk
    lock = acquire_lock("demo.lock" if args.demo else "tokenlike.lock")
    if lock is None:
        print("O Agent Tokenlike já está aberto.")
        return
    app = PetApp(args)
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
