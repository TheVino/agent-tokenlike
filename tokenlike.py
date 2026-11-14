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
import arte  # noqa: E402
from herois import montar as _montar, slime as _slime  # noqa: E402
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
MENU_HOVER = "#2e2a48"      # fundo da linha do menu com o mouse em cima
GOLD_HOVER = "#fff27a"      # polegar da barra de rolagem com o mouse em cima
CARD_BG = "#262338"         # miolo dos cartões (um pouco mais claro que o painel)
JANELA_R, CARTAO_R = 8, 4   # raio dos cantos em degraus: janelas/painel e cartões/chips
CARTAO_PAD = 6              # respiro mínimo entre a borda do cartão e o que vai dentro
HERO_COLS, HERO_CARD_W, HERO_CARD_H = 5, 128, 160   # grade de heróis (cards de tamanho fixo)
CONQ_COLS, CONQ_CARD_W, CONQ_CARD_H = 4, 150, 118   # grade de conquistas
CEMI_W, CEMI_H, CEMI_LAPIDE = 470, 420, 92           # cemitério: largura, altura visível, altura de cada lápide
ITENS_COLS, ITENS_CARD_W, ITENS_H = 2, 280, 440      # página de itens: colunas, largura do card, altura visível
JANELAS = ("menu_win", "heroes_win", "stats_win", "conq_win", "cemi_win", "itens_win", "perfil_win")
PERFIL_W, PERFIL_MEDALHAS, PERFIL_MEDALHA, PERFIL_BARRA = 312, 13, 24, "#8a5a2b"   # perfil: largura, medalhas/linha, célula, cor
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


# ------------------------------------------------------------- perfil (funções puras)
NIVEL_XP = 1_000_000                # nível de domador = floor(sqrt(energia na vida (xp_total) / 1M))


def nivel(total: float) -> tuple[int, float, float]:
    """(nível, fração até o próximo, energia que falta). Nível n começa em n² milhões de energia."""
    n = math.isqrt(int(total // NIVEL_XP))
    base, prox = n * n * NIVEL_XP, (n + 1) ** 2 * NIVEL_XP
    return n, (total - base) / (prox - base), prox - total


def uso_por_dia(state: dict, now: float, dias: int = 7) -> list[tuple[date, float]]:
    """XP de `usage_hist` somado por dia local, do mais antigo até hoje."""
    hoje = datetime.fromtimestamp(now).date()
    out = {hoje - timedelta(days=i): 0.0 for i in range(dias)}
    for k, v in (state.get("usage_hist") or {}).items():
        d = datetime.fromtimestamp(int(k)).date()
        if d in out:
            out[d] += v
    return sorted(out.items())


def dias_seguidos(state: dict, now: float) -> int:
    """Dias seguidos com uso até hoje (hoje ainda sem uso não quebra a sequência).
    Usa `usage_hist` (8 dias, por horário) e `daily` (60 dias, contado com o app aberto)."""
    usados = {datetime.fromtimestamp(int(k)).date() for k, v in (state.get("usage_hist") or {}).items() if v > 0}
    usados |= {date.fromisoformat(k) for k, v in (state.get("daily") or {}).items() if v > 0}
    d = datetime.fromtimestamp(now).date()
    if d not in usados:
        d -= timedelta(days=1)
    n = 0
    while d in usados:
        n, d = n + 1, d - timedelta(days=1)
    return n


def ultimo_uso(state: dict) -> float | None:
    """Fim do último balde de 5 min com tokens."""
    ks = [int(k) for k, v in (state.get("usage_hist") or {}).items() if v > 0]
    return max(ks) + BUCKET_S if ks else None


def fmt_ha(dt: float) -> str:
    if dt < 60:
        return "agora"
    if dt < 3600:
        return f"há {int(dt // 60)} min"
    if dt < 86400:
        return f"há {int(dt // 3600)} h"
    return f"há {int(dt // 86400)} d"


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
class CharacterDef:
    def __init__(self, key, name, stages, frame_ms=600, stats=None, unlock=None, comunidade=False, traco=None):
        self.key, self.name, self.frame_ms = key, name, frame_ms
        self.stats = stats or {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
        self.unlock, self.comunidade = unlock, comunidade
        self.traco = traco or {}
        # cada estágio: {"floor", "title", "frames": [spec], "blink": spec|None, "sleep": spec|None}
        # e, se vier de spritesheet, "estados": {estado: [spec]} (spec ("sheet", path, box, N))
        self.stages = sorted(stages, key=lambda s: s["floor"])

    @property
    def stage_floors(self) -> list[int]:
        return [s["floor"] for s in self.stages]


def builtin_characters() -> list[CharacterDef]:
    stages = []
    for i, st in enumerate(_slime.ESTAGIOS):
        estados = {e: [("grid", g, _slime.PAL) for g in gs] for e, gs in _montar.estados(_slime, i).items()}
        piscar = _montar.sobrepor(_slime.BLINK, st["extra"], *_slime.ANCORA["idle"][2]) if st["extra"] else _slime.BLINK
        closed = ("grid", piscar, _slime.PAL)
        stages.append({"floor": st["floor"], "title": st["title"], "frames": estados["idle"],
                       "blink": closed, "sleep": closed, "estados": estados})
    return [CharacterDef("slime", "Slime", stages, stats={"hp": 20, "atk": 3, "def": 0, "dodge": 0})]


DEFAULT_STATS = {"hp": 20, "atk": 3, "def": 0, "dodge": 0, "spd": 10.0}
_FOLHAS = {}  # (caminho, mtime) -> (linhas de caixas, N, {caixa: PixelMap reduzido}); o PNG decodificado é descartado


def ler_folha(path: Path):
    """Linhas de caixas da folha, o fator N de redução e o mapa reduzido de cada caixa. Puro (roda na thread).
    Opaco = alfa > 128; a máscara é amostrada (1 a cada `a` px) e perde as ilhas de até 2 px."""
    ck = (str(path), path.stat().st_mtime)
    if ck not in _FOLHAS:
        w, h, rgba = folha.ler_png(path)
        op = rgba[3::4].translate(folha.OPACO)
        grade = folha.detectar_grade(w, h)
        if grade:
            cols, lins = grade
            cw, ch = w // cols, h // lins
            a = folha.fator_reducao(ch)
        else:
            a = folha.fator_reducao(h // 9)
        ws, hs = -(-w // a), -(-h // a)
        m = folha._mascara(ws, hs, lambda x, y: op[y * a * w + x * a])
        if grade:
            ocup = {}   # célula -> pontos opacos (offset dentro da célula)
            for ys, lin in enumerate(m):
                for xs in range(ws):
                    if lin[xs]:
                        X, Y = xs * a, ys * a
                        ocup.setdefault((Y // ch, X // cw), []).append((X % cw, Y % ch))
            pts = [p for cel in ocup.values() for p in cel]
            if not pts:
                raise ValueError(f"folha sem quadros: {path.name}")
            # uma caixa só (união do opaco de todas as células) para os quadros não tremerem
            ox0, oy0 = min(x for x, _ in pts), min(y for _, y in pts)
            ox1, oy1 = min(cw, max(x for x, _ in pts) + a), min(ch, max(y for _, y in pts) + a)
            # célula sem pixel opaco (linha com menos de 8 quadros) fica de fora: nunca vira quadro piscando
            linhas = [[(c * cw + ox0, r * ch + oy0, c * cw + ox1, r * ch + oy1) for c in range(cols) if (r, c) in ocup]
                      for r in range(lins)]
            n = folha.fator_reducao(oy1 - oy0)
        else:
            # ponytail: caixas com precisão de `a` px (amostra); corte exato custa ~5 s em folha grande
            linhas = [[(x0 * a, y0 * a, min(w, x1 * a), min(h, y1 * a)) for x0, y0, x1, y1 in lin]
                      for lin in folha.cortar(ws, hs, lambda x, y: m[y][x])]
            n = folha.fator_reducao(max((c[3] - c[1] for lin in linhas for c in lin), default=1))
        if not any(linhas):
            raise ValueError(f"folha sem quadros: {path.name}")
        mapas = {}
        for lin in linhas:
            for (x0, y0, x1, y1) in lin:
                mapas[(x0, y0, x1, y1)] = {
                    ((x - x0) // n, (y - y0) // n): "#%02x%02x%02x" % tuple(rgba[4 * (y * w + x):4 * (y * w + x) + 3])
                    for y in range(y0, y1, n) for x in range(x0, x1, n) if op[y * w + x]}
        _FOLHAS[ck] = linhas, n, mapas
    return _FOLHAS[ck]


def stage_da_folha(path: Path, floor: int, title: str) -> dict:
    """Estágio de spritesheet ainda não cortado: a descoberta só lê o cabeçalho do PNG (barato).
    `completar_estagio` (na thread, ao ativar o herói) preenche "frames" e "estados"."""
    with open(path, "rb") as f:
        folha.info_png(f.read(29))
    return {"floor": floor, "title": title, "sheet": path, "frames": None, "blink": None, "sleep": None}


def completar_estagio(stage: dict) -> dict:
    """Corta a folha do estágio: estados na ordem das linhas; linha vazia ou ausente usa o Idle.
    Erro vira stage["erro"] (a GUI volta para o Slime). Puro: pode rodar fora da thread do Tk."""
    try:
        linhas, n, _ = ler_folha(stage["sheet"])
        specs = [[("sheet", stage["sheet"], c, n) for c in lin] for lin in linhas]
        idle = next(l for l in specs if l)
        estados = {e: (specs[i] if i < len(specs) and specs[i] else idle) for i, e in enumerate(folha.ESTADOS)}
        stage["frames"] = estados["idle"]
        stage["estados"] = estados      # por último: quem vê "estados" já vê "frames"
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
                    out.append(CharacterDef(d.name, name, [stage_da_folha(png, 1, name)], stats=dict(DEFAULT_STATS)))
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
            traco = data.get("traço") or data.get("traco") or {}
            if not isinstance(traco, dict):
                raise ValueError("'traço' precisa ser um objeto")
            validas = M.stats(M.new_run("x", {}, 0))
            for k, v in traco.items():
                if k not in validas or isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise ValueError(f"'traço' inválido: {k}")
            out.append(CharacterDef(d.name, data.get("name", d.name), stages,
                                    int(data.get("frame_ms", 600)), stats, unlock, traco=traco))
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
                out.append(CharacterDef("petdex:" + d.name, name, [stage_da_folha(png, 1, name)],
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
class _EstadosFx(dict):
    """estado -> imagens [quadro][fase]; compõe na primeira leitura e guarda em app.fx_cache."""
    def __init__(self, app, nomes):
        super().__init__((e, None) for e in nomes)
        self.app = app

    def __getitem__(self, e):
        ck = (e, self.app.fx_sig)
        if ck not in self.app.fx_cache:
            dict.__getitem__(self, e)           # KeyError para estado que a folha não tem
            self.app.fx_cache[ck] = self.app.fx_compor(e)
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
        pm = ler_folha(path)[2][box]
        w, h, lado = -(-(box[2] - box[0]) // n), -(-(box[3] - box[1]) // n), 16 * (k or spec_k(spec))
        dx, dy = (lado - w) // 2, lado - h
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
    lado = 16 * (k or max(1, -(-h // 16)))      # grade 32 px: quadro de 32 (k = 2)
    dx, dy = (lado - w) // 2, lado - h
    return {(x + dx, y + dy): c for (x, y), c in pm.items()}


def spec_altura(spec) -> int:
    """Altura final (já reduzida) do quadro; grid = altura da grade; PNG solto fica em 16."""
    if spec[0] == "sheet":
        return -(-(spec[2][3] - spec[2][1]) // spec[3])
    return len(spec[1]) if spec[0] == "grid" else 16


def spec_k(spec) -> int:
    return max(1, -(-spec_altura(spec) // 16))   # para cima: o quadro nunca corta o herói


def render_map(pm, s: int, k: int = 1):
    """Imagem com origem em look_box(k) (tamanho sempre fixo) e quantos px de tela ela desce abaixo da base.
    `s` = px de tela por pixel do mapa (herói de altura H: s = px_heroi); k = H/16 arredondado (escala dos looks)."""
    box = visual.look_box(k)
    x0, y0, x1, y1 = box
    img = tk.PhotoImage(width=(x1 - x0) * s, height=(y1 - y0) * s)
    for (x, y), c in visual.crop(pm, box).items():
        img.put(c, to=((x - x0) * s, (y - y0) * s, (x - x0 + 1) * s, (y - y0 + 1) * s))
    return img, (y1 - 16 * k) * s


def degraus(r: int) -> list[int]:
    """Recuo de cada uma das r linhas de um canto de raio r, de fora para dentro (degraus de 1 px, sem antialias)."""
    return [r - round(math.sqrt(r * r - (r - i - 0.5) ** 2)) for i in range(r)]


def _forma(cv, x0, y0, x1, y1, r, cor, tags):
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    if x1 <= x0 or y1 <= y0:
        return
    ins, kw, i = degraus(r), dict(fill=cor, outline="", width=0, tags=tags), 0
    while i < len(ins):                     # linhas de mesmo recuo viram um retângulo só
        j = i
        while j < len(ins) and ins[j] == ins[i]:
            j += 1
        cv.create_rectangle(x0 + ins[i], y0 + i, x1 - ins[i], y0 + j, **kw)
        cv.create_rectangle(x0 + ins[i], y1 - j, x1 - ins[i], y1 - i, **kw)
        i = j
    if y1 - r > y0 + r:
        cv.create_rectangle(x0, y0 + r, x1, y1 - r, **kw)


def retangulo_arredondado(cv, x0, y0, x1, y1, r, fill, outline=None, larg=1, tag="arred", extra=()):
    """Retângulo de cantos em degraus de pixel no Canvas `cv`, só com retângulos retos (sem antialias: a cor-chave
    #ff00fe não ganha contorno rosa). Tags: `tag` em tudo, `tag`_f no miolo (troca de cor no hover), mais `extra`."""
    if outline:
        _forma(cv, x0, y0, x1, y1, r, outline, (tag, tag + "_b", *extra))
        x0, y0, x1, y1, r = x0 + larg, y0 + larg, x1 - larg, y1 - larg, max(0, r - larg)
    _forma(cv, x0, y0, x1, y1, r, fill, (tag, tag + "_f", *extra))


def map_img(pm, lado):
    """Mapa de pixels aparado e ampliado por um inteiro até caber em `lado` px."""
    if not pm:
        return tk.PhotoImage(width=1, height=1)
    x0, y0, x1, y1 = visual.bbox(pm)
    s = max(1, lado // max(1, x1 - x0, y1 - y0))
    w, h =(x1 - x0) * s, (y1 - y0) * s
    # um PNG montado aqui e lido numa chamada só (um put por pixel levava ~0,4 s para abrir o cemitério)
    raw = b"".join((b"\0" + b"".join((bytes.fromhex(pm[(x, y)][1:]) + b"\xff" if (x, y) in pm else b"\0" * 4) * s
                                     for x in range(x0, x1))) * s for y in range(y0, y1))

    def bloco(tipo, d):
        return struct.pack(">I", len(d)) + tipo + d + struct.pack(">I", zlib.crc32(tipo + d))
    png = (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + bloco(b"IDAT", zlib.compress(raw, 1)) + bloco(b"IEND", b""))
    return tk.PhotoImage(data=base64.b64encode(png).decode(), format="png", width=w, height=h)


def heroi_idle(key):
    """1º quadro idle do 1º estágio direto do módulo herois/<key>.py (sem cortar a folha PNG, que leva segundos).
    None se não houver módulo (herói externo/Petdex: a grade espera a thread de corte)."""
    import importlib
    try:
        mod = importlib.import_module(f"herois.{key}")
    except ImportError:
        return None
    return visual.grid_to_map(_montar.estados(mod, 0)["idle"][0], mod.PAL)


def heroi_proprio(key):
    """Herói feito aqui (tem módulo herois/<key>.py); os outros (pasta em characters/, Petdex/Codex) são importados."""
    import importlib.util
    try:
        return importlib.util.find_spec(f"herois.{key}") is not None
    except (ImportError, ValueError):
        return False


_ITEM_ARTS = {}


ELEMENTO_LOOK = {"queimar": "chamas", "eletrizar": "faiscas", "envenenar": "gotas_veneno", "congelar": "geada"}


def pet_looks(run):
    """Looks dos itens [(look, brilho)] + um look animado por elemento que o pet aplica e ainda não aparece."""
    looks = [(M.ITEMS[it["key"]]["look"], M.RAR_COLOR.get(it["rar"]))
             for it in run["items"] if it["key"] in M.ITEMS]
    tipos = {l["type"] for l, _ in looks}
    st = M.stats(run)
    return looks + [({"type": t}, None) for k, t in ELEMENTO_LOOK.items() if st[k] > 0 and t not in tipos]


def _pct(v):
    return f"{round(v * 100)}%"


# janela de Status: (campo de stats(), nome, formato, teto ou None, mostra mesmo zerado)
STAT_LINHAS = (
    ("maxhp", "HP máx", str, None, True),
    ("atk", "Ataque", str, None, True),
    ("def", "Defesa", str, None, True),
    ("spd", "Velocidade", lambda v: f"{round(v)}", None, True),
    ("crit", "Crítico", _pct, M.MAX_CRIT, True),
    ("critdmg", "Dano crítico", lambda v: f"×{v:g}", None, True),
    ("dodge", "Esquiva", _pct, M.MAX_DODGE, False),
    ("lifesteal", "Roubo de vida", lambda v: f"+{v} por vitória", None, False),
    ("duplo", "Golpe duplo", _pct, M.MAX_DUPLO, False),
    ("area", "Ataque em área", lambda v: "sim", None, False),
    ("queimar", "Queimar", _pct, M.MAX_ELEM_CHANCE, False),
    ("eletrizar", "Eletrizar", _pct, M.MAX_ELEM_CHANCE, False),
    ("envenenar", "Envenenar", _pct, M.MAX_ELEM_CHANCE, False),
    ("congelar", "Congelar", _pct, M.MAX_ELEM_CHANCE, False),
    ("bloqueio", "Bloqueios por luta", str, M.MAX_BLOQUEIO, False),
    ("espinhos", "Espinhos", _pct, M.MAX_ESPINHOS, False),
    ("cura_sala", "Cura por sala", lambda v: f"+{v} HP", None, False),
    ("cura_andar", "Cura por andar", lambda v: f"+{v} HP", None, False),
    ("custo_ataque", "Custo de ataque", lambda v: f"-{v} HP", None, False),
    ("furia", "Fúria", lambda v: f"+{v} ATK a cada 10%", None, False),
    ("ajudante", "Ajudante", lambda v: f"{v} de dano", None, False),
    ("crescer", "Crescer", lambda v: f"+1 ATK / {v} kills", None, False),
    ("gold", "Ouro", lambda v: f"+{_pct(v)}", None, False),
    ("energy", "Energia", lambda v: f"+{_pct(v)}", M.MAX_ENERGY_BONUS, False),
    ("trap", "Armadilhas", lambda v: f"×{v:g}", None, False),
    ("sorte", "Sorte", lambda v: f"+{_pct(v)}", M.MAX_SORTE, False),
    ("desconto", "Desconto", _pct, M.MAX_DESCONTO, False),
)


def stat_linhas(run, st):
    """[(campo, nome, valor)] da janela de Status: os fixos sempre, os outros só quando mudam algo."""
    st = dict(st, crescer=min([M.item_fx(i["key"], i["rar"]).get("crescer", 0) for i in run["items"]
                               if "crescer" in M.ITEMS.get(i["key"], {}).get("fx", {})] or [0]))
    out = []
    for k, nome, fmt_, teto, sempre in STAT_LINHAS:
        v = st[k]
        if sempre or (v != 1 if k == "trap" else v):
            out.append((k, nome, fmt_(v) + (f" / {fmt_(teto)}" if teto is not None else "")))
    return out


# página de itens: família pelo 1º campo de fx que aparece nesta ordem (sem nenhum: "Básico")
FAMILIAS = (("Elemental", ("queimar", "eletrizar", "envenenar", "congelar")), ("Ajudante", ("ajudante",)),
            ("Crescimento", ("crescer",)), ("Área", ("area",)), ("Sangue", ("custo_ataque", "furia")),
            ("Golpes", ("crit", "critdmg", "duplo")), ("Defesa", ("bloqueio", "espinhos", "dodge")),
            ("Regeneração", ("cura_sala", "cura_andar", "lifesteal")), ("Sorte e ouro", ("sorte", "gold", "desconto")))


def item_familia(key):
    fx = M.ITEMS[key]["fx"]
    return next((nome for nome, campos in FAMILIAS if any(fx.get(c) for c in campos)), "Básico")


@lru_cache(maxsize=None)
def boss_grid(sprite):
    """Monstro com a coroa de chefe em cima (grade única por sprite: o cache de ícones usa o id)."""
    foe = arte.FOE_ART[sprite]
    w = max(len(foe[0]), len(arte.CROWN[0]))
    pad = lambda r: r.center(w, ".")
    return tuple(pad(r) for r in arte.CROWN + foe)


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
        return self.demo or not c.unlock or c.unlock in self.meta["achievements"]   # demo: todos liberados para testar

    def new_run(self, announce=True):
        key = self.meta.get("next_char", "slime")
        c = self.chars.get(key)
        if c is None or not self.is_unlocked(c):
            key, c = "slime", self.chars["slime"]
        # a energia que sobrou passa para a run nova (tokens não se perdem)
        energy = self.state["run"]["energy"] if self.state.get("run") else 0.0
        self.state["run"] = M.new_run(key, c.stats, self.meta["runs"] + 1, c.traco)
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
        if stage.get("sheet") and "estados" not in stage and "erro" not in stage:
            self.preparar_folha(stage)          # na thread; até lá fica o visual anterior (ou o do Slime)
            if getattr(self, "frame_maps", None) is not None:
                return
            stage = builtin_characters()[0].stages[0]
        try:
            if stage.get("erro"):
                raise ValueError(stage["erro"])
            # herói de spritesheet: um k só no estágio (mesma escala e mesmo pivô em todos os estados)
            todos = [sp for specs in stage.get("estados", {}).values() for sp in specs] or stage["frames"]
            h = max(spec_altura(sp) for sp in todos)
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
        self.estado_maps = {e: [spec_to_map(sp, k) for sp in specs]   # os heróis antigos não têm "estados"
                            for e, specs in stage.get("estados", {}).items()}
        self.fx_cache = {}         # estados compostos: (estado, assinatura) -> [quadro][fase]
        self.stage_title = stage["title"]

    def preparar_folha(self, stage):
        """Decodifica e corta a folha numa thread (só Python puro); o Tk volta na thread principal pelo after."""
        if stage.get("thread") is None:
            stage["thread"] = threading.Thread(target=completar_estagio, args=(stage,), daemon=True)
            stage["thread"].start()
            self.root.after(0, lambda: self.floater("preparando herói…", MUTED))
            self.root.after(100, lambda: self.esperar_folha(stage))

    def esperar_folha(self, stage):
        if stage["thread"].is_alive():
            self.root.after(100, lambda: self.esperar_folha(stage))
            return
        if self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)] is stage:
            self.load_images()
            self.refresh_look()

    def refresh_look(self, k: int = None, px_heroi: int = None):
        """Recompõe as imagens do pet com os looks dos itens. Só quando a lista muda, nunca no tick.
        Herói de altura H: k = H/16 e px_heroi = max(1, round(px*16/H)) (padrão: 16 px, k=1, px)."""
        k = k or getattr(self, "hero_k", 1)
        px_heroi = px_heroi or getattr(self, "hero_px", None) or self.px
        looks = pet_looks(self.run)
        arts = item_arts()
        cor = STATUS_COR.get(self.pet_status)
        virar = self.virar
        if hasattr(self, "virar_var"):
            self.virar_var.set(virar)

        # looks elementais animam em FASES quadros; sem eles, uma fase só (nenhuma imagem a mais)
        fases = range(visual.FASES if visual.tem_animacao(looks) else 1)

        def mapa(pm, fase):
            m = visual.compose(pm, looks, arts, fase, k)
            m = visual.tingir(m, cor, 0.5) if cor else m
            return {(16 * k - 1 - x, y): c for (x, y), c in m.items()} if virar else m   # espelha o mapa final   # com status, o pet fica na cor dele (todas as fases)

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
        # estados da folha: [quadro][fase], compostos na 1ª vez que aparecem (só idle e o atual saem aqui);
        # cache por (estado, itens, status, escala), então tirar e pôr o mesmo status não recompõe
        sig = (tuple((i["key"], i.get("rar")) for i in self.run["items"]), self.pet_status, k, px_heroi, virar)
        self.fx_cache = {ck: v for ck, v in getattr(self, "fx_cache", {}).items() if ck[1][0] == sig[0] and ck[1][4] == virar}
        self.fx_cache[("idle", sig)] = self.frames_fx
        troca = {"run_r": "run_l", "run_l": "run_r"} if virar else {}
        self.fx_compor = lambda e: [[img(mapa(pm, j)) for j in fases] for pm in self.estado_maps[troca.get(e, e)]]
        self.fx_sig = sig
        self.estados_fx = _EstadosFx(self, getattr(self, "estado_maps", {}))
        if getattr(self, "estado_visto", None) in self.estados_fx:
            self.estados_fx[self.estado_visto]
        self.canvas.itemconfigure(self.sprite, image=self.frames_fx[0][0])
        self.place_pet(0, 0)

    @property
    def virar(self):
        return bool(self.state.get("virar", {}).get(self.run["char"]))

    def toggle_virar(self):
        self.state.setdefault("virar", {})[self.run["char"]] = bool(self.virar_var.get())
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
        """Só as variáveis; o menu (pixel art, `on_menu`) e a grade de heróis (`show_heroes`) nascem ao abrir."""
        self.char_var = tk.StringVar(value=self.meta.get("next_char", "slime"))
        self.size_var = tk.StringVar(value=self.state["size"])
        self.mode_var = tk.StringVar(value=self.state["mode"])
        self.top_var = tk.BooleanVar(value=bool(self.state["topmost"]))
        self.virar_var = tk.BooleanVar(value=self.virar)
        for attr in JANELAS:
            setattr(self, attr, None)
        self.thumb_thread = None
        self.hero_cards, self.hero_thumb_lbl, self.thumbs, self.icons, self.fontes = {}, {}, {}, {}, {}

    def fill_char_menu(self):
        """Conquista nova ou personagens recarregados: refaz a grade de heróis se estiver aberta."""
        if self.heroes_win is not None:
            self.show_heroes()

    # ------------------------------------------------------- menu em pixel art
    def pixel_box(self, x, y, fecha=True):
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
        fundo = tk.Canvas(w, bg=corte, highlightthickness=0, bd=0)
        fundo.place(x=0, y=0, relwidth=1, relheight=1)      # criado antes do miolo: fica por baixo dele

        def desenha(e):
            fundo.delete("all")
            retangulo_arredondado(fundo, 0, 0, e.width, e.height, JANELA_R, PANEL_EDGE, GOLD, 2)
            retangulo_arredondado(fundo, 3, 3, e.width - 3, e.height - 3, JANELA_R - 3, PANEL_BG)
        fundo.bind("<Configure>", desenha)
        miolo = tk.Frame(w, bg=PANEL_BG, padx=4, pady=4)
        miolo.pack(padx=5, pady=5)          # fora da área dos cantos
        if fecha:
            w.bind("<Escape>", lambda e: self.close_win(w))
            w.bind("<FocusOut>", lambda e: self.close_win(w) if e.widget is w else None)
        w.geometry(f"+{x}+{y}")
        return w, miolo

    def place_win(self, w, x, y):
        """Põe a janela em (x, y) sem sair da tela (sem espaço embaixo, abre para cima) e pega o foco."""
        w.update_idletasks()
        vx0, vy0, vx1, vy1 = self.tela()
        ww, wh = w.winfo_width(), w.winfo_height()
        x = max(vx0, min(x, vx1 - ww))
        y = max(vy0, y if y + wh <= vy1 else y - wh)
        w.geometry(f"+{x}+{y}")
        w.focus_force()

    def tela(self):
        """Retângulo da tela virtual (todos os monitores; x negativo = monitor à esquerda do principal)."""
        r = self.root
        x, y = r.winfo_vrootx(), r.winfo_vrooty()
        return x, y, x + r.winfo_vrootwidth(), y + r.winfo_vrootheight()

    def close_win(self, w):
        if w is None:
            return
        for attr in JANELAS:
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
            self.art[ck] = render_grid(arte.all_art()[key], arte.PAL, 2)
        return self.art[ck]

    def hover(self, widgets, texto, fg, on_click):
        """Hover: fundo mais claro e texto dourado; clique em qualquer parte. Cartão (`cartao`) troca só o miolo."""
        base = {wd: None if hasattr(wd, "fundo") else wd.cget("bg") for wd in widgets}

        def pintar(on):
            for wd in widgets:
                if base[wd] is None:
                    wd.fundo(MENU_HOVER if on else CARD_BG)
                else:
                    wd.configure(bg=MENU_HOVER if on else base[wd])
            texto.configure(fg=GOLD if on else fg)
        for wd in widgets:
            wd.configure(cursor="hand2")
            wd.bind("<Enter>", lambda e: pintar(True))
            wd.bind("<Leave>", lambda e: pintar(False))
            wd.bind("<Button-1>", lambda e: on_click())

    def menu_row(self, parent, icon, text, cmd, fg=TEXT):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x")
        ico = tk.Label(row, image=self.menu_icon(icon), bg=PANEL_BG, width=22, height=20)
        ico.pack(side="left")
        t = tk.Label(row, text=text, bg=PANEL_BG, fg=fg, font=self.font, anchor="w", padx=4)
        t.pack(side="left", fill="x", expand=True)
        self.hover((row, ico, t), t, fg, lambda: self.menu_do(cmd))

    def menu_chips(self, parent, label, opcoes, var, cmd):
        """Botões segmentados no próprio menu (sem submenu); o escolhido fica dourado."""
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=PANEL_BG, fg=MUTED, font=self.font_small, width=8, anchor="w").pack(side="left")
        for value, text in opcoes.items():
            self.chip(row, text, var.get() == value, lambda v=value: (var.set(v), self.menu_do(cmd))).pack(
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

        def pintar(sel=None, quente=False):
            if sel is not None:
                st["sel"] = sel
            cv.delete("chip")
            fundo = GOLD if st["sel"] else MENU_HOVER if quente else BAR_BG
            retangulo_arredondado(cv, 0, 0, larg, alto, CARTAO_R, fundo, tag="chip")
            cv.tag_raise(t)
            cv.itemconfigure(t, fill=PANEL_BG if st["sel"] else GOLD if quente else TEXT)
        pintar()
        if cmd:
            cv.bind("<Button-1>", lambda e: cmd())
            cv.bind("<Enter>", lambda e: pintar(quente=True))
            cv.bind("<Leave>", lambda e: pintar())
        cv.pintar = pintar
        return cv

    def cartao(self, parent, borda=PANEL_EDGE, larg=None, alto=None, espessura=2):
        """Cartão arredondado: Canvas com o fundo desenhado (CARD_BG). Os filhos usam bg=CARD_BG e ficam a
        CARTAO_PAD da borda. Com larg/alto, tamanho fixo. `cv.fundo(cor)` troca a cor do miolo (hover)."""
        cv = tk.Canvas(parent, bg=PANEL_BG, highlightthickness=0, bd=0, width=larg or 1, height=alto or 1)
        if larg:
            cv.pack_propagate(False)
        st = {"cor": CARD_BG}

        def desenha(e):
            cv.delete("cartao")
            retangulo_arredondado(cv, 0, 0, e.width, e.height, CARTAO_R, st["cor"], borda, espessura, tag="cartao")
            cv.tag_lower("cartao")

        def fundo(cor):
            st["cor"] = cor
            cv.itemconfigure("cartao_f", fill=cor)
        cv.bind("<Configure>", desenha)
        cv.fundo = fundo
        return cv

    def medir(self, texto, font):
        """Largura do texto em px (tkinter falso dos testes: 6 px por letra)."""
        tkf = getattr(tk, "font", None)
        if tkf is None:
            return 6 * len(texto)
        if font not in self.fontes:
            self.fontes[font] = tkf.Font(root=self.root, font=font)
        return self.fontes[font].measure(texto)

    def encurtar(self, texto, font, larg):
        """O texto se couber em `larg` px; senão cortado com "…" (mostre o inteiro com `dica`)."""
        if self.medir(texto, font) <= larg:
            return texto
        while texto and self.medir(texto + "…", font) > larg:
            texto = texto[:-1]
        return texto.rstrip() + "…"

    def dica(self, wd, texto):
        """Balão pixel com o texto inteiro enquanto o mouse está em cima de `wd` (para o que foi encurtado)."""
        st = {}

        def abre(e):
            fecha(e)
            w, f = self.pixel_box(e.x_root + 12, e.y_root + 14, fecha=False)
            tk.Label(f, text=texto, bg=PANEL_BG, fg=TEXT, font=self.font_small).pack()
            st["w"] = w

        def fecha(e):
            if st.get("w") is not None:
                st.pop("w").destroy()
        wd.bind("<Enter>", abre, add="+")
        wd.bind("<Leave>", fecha, add="+")

    def barra(self, parent, larg, alto, frac=0.0, cor=GOLD):
        """Barra de progresso arredondada (Canvas); `cv.set(frac, cor)` redesenha o preenchimento."""
        cv = tk.Canvas(parent, width=larg, height=alto, bg=PANEL_BG, highlightthickness=0, bd=0)
        retangulo_arredondado(cv, 0, 0, larg, alto, alto // 2, BAR_BG, tag="trilha")

        def set_(frac, cor=cor):
            cv.delete("cheio")
            retangulo_arredondado(cv, 0, 0, round(larg * max(0.0, min(1.0, frac))), alto, alto // 2, cor, tag="cheio")
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
        tk.Label(head, text=f"{self.char.name}  ·  {self.stage_title}", bg=PANEL_BG, fg=GOLD,
                 font=self.font, anchor="w").pack(fill="x")
        tk.Label(head, text=f"Andar {run['floor']}-{run['room']}    ♥ {run['hp']}/{st['maxhp']}",
                 bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        self.menu_sep(f)
        for icon, text, cmd in (("estrela_cadente", "Perfil", self.show_perfil),
                                ("grimorio", "Status", self.show_stats),
                                ("lapide", "Cemitério", self.show_graveyard),
                                ("coroa", "Conquistas", self.show_achievements),
                                ("pocao", "Itens", self.show_items),
                                ("espada_osso", "Heróis…", self.show_heroes)):
            self.menu_row(f, icon, text, cmd)
        self.menu_sep(f)
        self.menu_chips(f, "Tamanho", {n: n for n in SIZES}, self.size_var, self.change_size)
        self.menu_chips(f, "Modo", MODES, self.mode_var, self.change_mode)
        for text, var, fn in (("Sempre por cima", self.top_var, self.toggle_top),
                              ("Virar herói", self.virar_var, self.toggle_virar)):
            self.menu_row(f, "caixa_ok" if var.get() else "caixa", text,
                          lambda v=var, fn=fn: (v.set(not v.get()), fn()))
        self.menu_sep(f)
        self.menu_row(f, "caveirinha", "Desistir da run", self.give_up, fg=HURT)
        self.menu_sep(f)
        self.menu_row(f, "bau", "Abrir pasta de personagens", self.open_chars)
        self.menu_row(f, "redemoinho", "Recarregar personagens", self.reload_chars)
        self.menu_row(f, "escada", "Sair", self.quit)
        self.place_win(w, e.x_root, e.y_root)

    def menu_do(self, cmd):
        self.close_win(self.menu_win)
        cmd()

    # ------------------------------------------------------- grade de heróis
    def hero_thumb(self, c, ok, lado=64):
        """Idle do 1º estágio ampliado (bloqueado: silhueta). None enquanto a folha ainda é cortada na thread."""
        stage = c.stages[0]
        ck = (id(stage), ok) if lado == 64 else (id(stage), ok, lado)
        if ck not in self.thumbs:
            pm = heroi_idle(c.key) if not stage.get("frames") else spec_to_map(stage["frames"][0])
            if pm is None:
                return None
            self.thumbs[ck] = map_img(pm if ok else {p: "#0b0b14" for p in pm}, lado)
        return self.thumbs[ck]

    def cortar_folhas(self):
        """Corta numa thread as folhas que a grade ainda não tem; depois só troca as miniaturas."""
        pend = [c.stages[0] for c in self.chars.values()
                if not c.stages[0].get("frames") and "erro" not in c.stages[0]
                and (id(c.stages[0]), True) not in self.thumbs and (id(c.stages[0]), False) not in self.thumbs]
        if not pend or self.thumb_thread is not None:
            return
        self.thumb_thread = threading.Thread(target=lambda: [completar_estagio(s) for s in pend], daemon=True)
        self.thumb_thread.start()

        def esperar():
            if self.thumb_thread.is_alive():
                self.root.after(150, esperar)
                return
            self.thumb_thread = None
            for key, lbl in list(self.hero_thumb_lbl.items()):
                c = self.chars.get(key)
                img = c and self.hero_thumb(c, self.is_unlocked(c))
                if img:
                    lbl.configure(image=img, text="", height=72)
        self.root.after(150, esperar)

    def janela(self, attr, titulo):
        """Janela pixel (fecha a anterior do mesmo tipo) com título dourado e um x; devolve (janela, miolo)."""
        self.close_win(getattr(self, attr))
        w, f = self.pixel_box(self.root.winfo_x(), self.root.winfo_y())
        setattr(self, attr, w)
        top = tk.Frame(f, bg=PANEL_BG)
        top.pack(fill="x")
        nome = tk.Label(top, text=titulo, bg=PANEL_BG, fg=GOLD, font=self.font)
        nome.pack(side="left")
        self.arrastavel(w, attr, top, nome)
        fechar = tk.Label(top, text=" x ", bg=PANEL_BG, fg=MUTED, font=self.font)
        fechar.pack(side="right")
        self.hover((fechar,), fechar, MUTED, lambda: self.close_win(w))
        return w, f

    def arrastavel(self, w, attr, *alcas):
        """Arrasta a janela segurando a barra de título (`alcas`) e lembra a posição em state["janelas"][attr]."""
        pega = {}

        def aperta(e):
            pega["d"] = (e.x_root - w.winfo_x(), e.y_root - w.winfo_y())

        def move(e):
            if "d" in pega:
                x, y = e.x_root - pega["d"][0], e.y_root - pega["d"][1]
                w.geometry(f"+{x}+{y}")
                self.state.setdefault("janelas", {})[attr] = [x, y]
        for a in alcas:
            a.configure(cursor="fleur")
            a.bind("<Button-1>", aperta)
            a.bind("<B1-Motion>", move)
        w.barra = alcas[0]          # para os testes

    def ao_lado(self, w):
        """Na posição lembrada (arrastada antes), se ainda estiver na tela; senão ao lado do pet:
        à esquerda, ou à direita se não couber."""
        w.update_idletasks()
        attr = next((a for a in JANELAS if getattr(self, a) is w), None)
        pos = (self.state.get("janelas") or {}).get(attr)
        vx0, vy0, vx1, vy1 = self.tela()
        if pos and vx0 <= pos[0] < vx1 and vy0 <= pos[1] < vy1:   # ponytail: retângulo da tela virtual, não por monitor
            self.place_win(w, pos[0], min(pos[1], max(vy0, vy1 - w.winfo_height())))
            return
        x, y = self.root.winfo_x(), self.root.winfo_y()
        left = x - w.winfo_width() - 6
        self.place_win(w, left if left >= vx0 else x + self.W + 6, y)

    def icon(self, grid, s=2, pal=None, glow=None, dark=False, dim=False, lado=None):
        """Grade de arte em escala s (cache): brilho de raridade, silhueta (bloqueado) ou esmaecida (consumido).
        Com `lado`, a escala é a maior inteira que cabe num quadrado de `lado` px (ícones do mesmo tamanho)."""
        ck = (id(grid), s, id(pal), glow, dark, dim, lado)
        if ck not in self.icons:
            pm = visual.grid_to_map(grid, pal or arte.PAL)
            if glow:
                pm = visual.contorno(pm, glow)
            if dark:
                pm = {p: "#0b0b14" for p in pm}
            if dim:
                pm = visual.tingir(pm, PANEL_BG, 0.55)
            x0, y0, x1, y1 = visual.bbox(pm)
            self.icons[ck] = map_img(pm, lado or s * max(x1 - x0, y1 - y0))
        return self.icons[ck]

    def show_heroes(self):
        w, f = self.janela("heroes_win", "Herói da próxima run")
        secoes = [("Heróis", [(k, c) for k, c in self.chars.items() if heroi_proprio(k)]),
                  ("Comunidade", [(k, c) for k, c in self.chars.items() if not heroi_proprio(k)])]
        for n, (titulo, lista) in enumerate(s for s in secoes if s[1]):
            if n:
                self.menu_sep(f)
            tk.Label(f, text=titulo, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x", pady=(4, 0))
            grade = tk.Frame(f, bg=PANEL_BG)
            grade.pack(pady=(4, 0))
            for i, (key, c) in enumerate(lista):
                self.hero_card(grade, key, c).grid(row=i // HERO_COLS, column=i % HERO_COLS, padx=3, pady=3)
        self.cortar_folhas()
        self.ao_lado(w)

    def hero_card(self, parent, key, c):
        ok, sel = self.is_unlocked(c), key == self.char_var.get()
        card = self.cartao(parent, GOLD if sel else PANEL_EDGE, HERO_CARD_W, HERO_CARD_H)
        img = self.hero_thumb(c, ok)
        pic = tk.Label(card, image=img or "", text="" if img else "…", bg=CARD_BG, fg=MUTED,
                       font=self.font, height=72 if img else 4)
        pic.pack(pady=(CARTAO_PAD, 0))
        self.hero_thumb_lbl[key] = pic
        curto = self.encurtar(c.name, self.font, HERO_CARD_W - 2 * CARTAO_PAD)
        nome = tk.Label(card, text=curto, bg=CARD_BG, fg=GOLD if sel else TEXT if ok else MUTED, font=self.font)
        nome.pack()
        if ok:
            info = tk.Label(card, text=M.fx_text(c.traco) if c.traco else "sem traço", bg=CARD_BG,
                            fg=MUTED, font=self.font_small, wraplength=HERO_CARD_W - 2 * CARTAO_PAD)
            info.pack()

            def pick():
                self.close_win(self.heroes_win)
                self.char_var.set(key)
                self.change_character()
            self.hover((card, pic, nome, info), nome, GOLD if sel else TEXT, pick)
            if curto != c.name:
                self.dica(nome, c.name)
        else:
            pick = None             # bloqueado: nada clicável
            tk.Label(card, text=M.ACHIEVEMENTS[c.unlock], image=self.menu_icon("cadeado"), compound="left",
                     bg=CARD_BG, fg=MUTED, font=self.font_small, wraplength=HERO_CARD_W - 24 - 2 * CARTAO_PAD).pack()
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
            self.estado_tmp = ("waving", time.time() + 1.0)
        self._drag = None

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
        self.estado_visto = estado
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
                    if estado == "idle" and self.blink_fx is not None:   # herói de grade ainda pisca
                        if now > self.next_blink:
                            self.blink_until = now + 0.16
                            self.next_blink = now + self.rng.uniform(2.5, 6)
                        if now < self.blink_until:
                            img = self.blink_fx[fase % len(self.blink_fx)]
                    if sleeping and now > self.next_zzz:
                        self.floater("z Z", MUTED, life=20)
                        self.next_zzz = now + 3
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
        w, f = self.pixel_box(0, 0, fecha=False)
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
        w, f = self.pixel_box(0, 0, fecha=False)   # a escolha não fecha sozinha ao perder o foco
        self.choice_img = self.art_img(key)       # referência: o tk não guarda a imagem sozinho
        tk.Label(f, image=self.choice_img, bg=PANEL_BG).pack(pady=(4, 2))
        tk.Label(f, text=f"{it['name']}  ·  {M.RAR_NAMES[rar]}", bg=PANEL_BG,
                 fg=M.RAR_COLOR.get(rar) or TEXT, font=self.font).pack(padx=6)
        cf = M.consume_fx(key, rar)
        cons = f"+{cf['heal']} ♥" if "heal" in cf else f"+{cf['shield']} escudo"
        tk.Label(f, text=f"Pegar: {M.fx_text(M.item_fx(key, rar))}\nConsumir: {cons}",
                 justify="left", bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(padx=6)
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=4)
        for label, choice in (("Pegar", "pegar"), ("Consumir", "consumir")):
            self.chip(row, label, False, lambda c=choice: self.choose(c)).pack(side="left", padx=4)
        self.choice_cv = self.barra(f, CHOICE_BAR_W, 6, 1.0, ENERGY)
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
        w, f = self.janela("stats_win", f"Status  ·  Run #{run['id']}")
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x", pady=(4, 0))
        self.stats_thumb = map_img(self.look_maps[0], 56)    # referência: o tk não guarda a imagem sozinho
        tk.Label(head, image=self.stats_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 8))
        col = tk.Frame(head, bg=PANEL_BG)
        col.pack(side="left", fill="x")
        tk.Label(col, text=f"{self.char.name}  ·  {self.stage_title}", bg=PANEL_BG, fg=GOLD, font=self.font,
                 anchor="w").pack(fill="x")
        tk.Label(col, text=f"Andar {run['floor']}-{run['room']}   ·   Modo {MODES[self.state['mode']]}",
                 bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        self.barra(col, 170, 8, run["hp"] / st["maxhp"], HURT).pack(anchor="w", pady=3)
        escudo = f"   ·   escudo {run['shield']}" if run["shield"] > 0 else ""
        tk.Label(col, text=f"♥ {run['hp']}/{st['maxhp']}{escudo}   ·   $ {run['gold']}   ·   {run['kills']} kills"
                 f"   ·   {run['bosses']} chefe{'s' if run['bosses'] != 1 else ''}", bg=PANEL_BG, fg=TEXT, font=self.font_small,
                 anchor="w").pack(fill="x")
        if run.get("traco"):
            tk.Label(f, text=f"Traço: {M.fx_text(run['traco'])}", bg=PANEL_BG, fg=MUTED, font=self.font_small,
                     anchor="w").pack(fill="x", pady=(4, 0))
        self.menu_sep(f)
        grade = tk.Frame(f, bg=PANEL_BG)
        grade.pack(fill="x")
        for n, (k, nome, valor) in enumerate(stat_linhas(run, st)):
            r, c = n // 2, (n % 2) * 3
            tk.Label(grade, image=self.icon(arte.STAT_ART[k], 2), bg=PANEL_BG, width=20, height=18).grid(
                row=r, column=c)
            tk.Label(grade, text=nome, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").grid(
                row=r, column=c + 1, sticky="w", padx=(2, 6))
            tk.Label(grade, text=valor, bg=PANEL_BG, fg=TEXT, font=self.font_small, anchor="e").grid(
                row=r, column=c + 2, sticky="e", padx=(0, 14 if c == 0 else 0))
        self.menu_sep(f)
        dica = "passe o mouse num item" if run["items"] or run["consumed"] else ""
        info = tk.Label(f, text=dica, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w", justify="left",
                        wraplength=330)
        for titulo, lista, s, dim in ((f"Itens ({len(run['items'])})", run["items"], 3, False),
                                      (f"Consumidos ({len(run['consumed'])})", run["consumed"], 2, True)):
            if not lista and dim:
                continue
            tk.Label(f, text=titulo, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
            box = tk.Frame(f, bg=PANEL_BG)
            box.pack(fill="x", pady=(2, 4))
            if not lista:
                tk.Label(box, text="nenhum ainda", bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(anchor="w")
            for n, it in enumerate(i for i in lista if i["key"] in M.ITEMS):
                rar = it.get("rar", "comum")
                lbl = tk.Label(box, image=self.icon(arte.ITEM_ART[it["key"]], s, glow=M.RAR_COLOR.get(rar), dim=dim),
                               bg=PANEL_BG, width=s * 9 + 4, height=s * 9 + 4)
                lbl.grid(row=n // 12, column=n % 12)
                txt = (f"{M.ITEMS[it['key']]['name']} ({M.RAR_NAMES.get(rar, rar)})"
                       + ("" if dim else f": {M.fx_text(M.item_fx(it['key'], rar))}"))
                lbl.bind("<Enter>", lambda e, t=txt: info.configure(text=t, fg=TEXT))
                lbl.bind("<Leave>", lambda e: info.configure(text=dica, fg=MUTED))
        info.pack(fill="x")
        self.menu_sep(f)
        best = meta["best"]
        rodape = [f"Energia guardada: {int(run['energy'] // M.room_cost(run))} sala(s)",
                  f"Recorde: andar {best['floor']}-{best['room']}   ·   Runs: {meta['runs']}",
                  f"Tokens hoje: {fmt(self.state['daily'].get(date.today().isoformat(), 0))}"
                  f"   ·   Total: {fmt(self.state['tokens_total'])}"]
        if run["pending"]:
            rodape.append(f"Esperando escolha: {M.ITEMS[run['pending']['key']]['name']}")
        if self.demo:
            rodape.append("(modo demo)")
        tk.Label(f, text="\n".join(rodape), bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w",
                 justify="left").pack(fill="x")
        self.ao_lado(w)

    def killer_icon(self, d):
        """Ícone de quem matou: monstro, chefe com coroa, mímico, status, armadilha ou desistência."""
        k = d.get("killer", "")
        boss = next((s for s, n in M.BOSS_NAMES.items() if n == k), None)
        if boss:
            return self.icon(boss_grid(boss), 2, pal=arte.BOSS_PAL)
        spr = "mimico" if k == "Mímico" else next((m[0] for m in M.MONSTERS if m[1] == k), None)
        if spr:
            return self.icon(arte.FOE_ART[spr], 2)
        grid = {"Queimadura": arte.STAT_ART["queimar"], "Veneno": arte.STAT_ART["envenenar"],
                "Armadilha": arte.ROOM_ART["armadilha"], "Desistiu": arte.ROOM_ART["escada"]}.get(k)
        return self.icon(grid or arte.ROOM_ART["lapide"], 2)

    def lapide(self, cv, y, d):
        """Uma lápide do cemitério desenhada no canvas a partir de y."""
        L, f, fs = CEMI_LAPIDE, self.font, self.font_small
        retangulo_arredondado(cv, 1, y + 1, CEMI_W - 1, y + L - 3, CARTAO_R, CARD_BG, PANEL_EDGE, 2, tag="cartao",
                              extra=(f"card:{y}",))
        c = self.chars.get(d.get("char"))
        img = (c and self.hero_thumb(c, True, 40)) or self.icon(arte.ROOM_ART["lapide"], 4)
        cv.create_image(30, y + L // 2 - 1, image=img)
        cv.create_text(60, y + 15, anchor="w", text=f"#{d.get('run', '?')}  {c.name if c else d.get('char', '?')}",
                       fill=GOLD, font=f)
        cv.create_text(CEMI_W - 12, y + 15, anchor="e", text=f"andar {d['floor']}-{d['room']}", fill=TEXT, font=f)
        kimg = self.killer_icon(d)
        cv.create_image(60, y + 37, anchor="w", image=kimg)
        quem = "desistiu" if d.get("kind") == "desistiu" else f"morto por {d.get('killer', '?')}"
        cv.create_text(66 + kimg.width(), y + 37, anchor="w", text=quem, fill=HURT, font=fs)
        cv.create_text(CEMI_W - 12, y + 37, anchor="e", fill=MUTED, font=fs,
                       text=f"$ {d.get('gold', 0)}   ·   {d.get('kills', 0)} kills   ·   {d.get('date', '')}")
        x = 60
        itens = [(it, None) if isinstance(it, str) else (it["key"], it.get("rar")) for it in d.get("items", [])]
        itens = [(k, r) for k, r in itens if k in arte.ITEM_ART]
        for n, (key, rar) in enumerate(itens):
            im = self.icon(arte.ITEM_ART[key], 2, glow=M.RAR_COLOR.get(rar))
            if x + im.width() > CEMI_W - 34 and n < len(itens) - 1:
                cv.create_text(x + 2, y + 64, anchor="w", text=f"+{len(itens) - n}", fill=MUTED, font=fs)
                break
            cv.create_image(x, y + 64, anchor="w", image=im)
            x += im.width() + 3
        if not itens:
            cv.create_text(60, y + 64, anchor="w", text="sem itens", fill=MUTED, font=fs)

    def show_graveyard(self):
        g, meta = self.meta["graveyard"], self.meta
        w, f = self.janela("cemi_win", "Cemitério")
        best = meta["best"]
        resumo = f"{meta['runs']} runs   ·   recorde: andar {best['floor']}-{best['room']}"
        mortes = Counter(d.get("killer") for d in g if d.get("kind") != "desistiu")
        if mortes:
            resumo += f"   ·   quem mais matou: {mortes.most_common(1)[0][0]}"
        tk.Label(f, text=resumo, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        if not g:
            tk.Label(f, image=self.icon(arte.ROOM_ART["lapide"], 4), text="Nenhuma lápide ainda...\no herói segue firme!",
                     compound="left", bg=PANEL_BG, fg=TEXT, font=self.font, padx=10, pady=12,
                     justify="left").pack()
            self.ao_lado(w)
            return
        alto, vis = len(g) * CEMI_LAPIDE, min(len(g) * CEMI_LAPIDE, CEMI_H)
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=(4, 0))
        cv = tk.Canvas(row, width=CEMI_W, height=vis, bg=PANEL_BG, highlightthickness=0,
                       scrollregion=(0, 0, CEMI_W, alto), yscrollincrement=CEMI_LAPIDE // 3)
        cv.pack(side="left")
        for n, d in enumerate(reversed(g)):
            self.lapide(cv, n * CEMI_LAPIDE, d)
        if alto > vis:
            self.rolagem(row, w, cv, vis)
        self.ao_lado(w)

    def rolagem(self, parent, w, cv, vis):
        """Barra de rolagem em pixel (a nativa não pega as cores) ao lado do Canvas `cv` (com scrollregion):
        arrastar o polegar rola junto, clicar na trilha centraliza o polegar ali, roda do mouse e setas.
        O polegar some quando tudo cabe (ex.: depois de um filtro). Devolve a trilha."""
        tr = tk.Canvas(parent, width=8, height=vis, bg=PANEL_BG, highlightthickness=0, cursor="hand2")
        tr.pack(side="left", padx=(4, 0))
        retangulo_arredondado(tr, 0, 0, 8, vis, 4, BAR_BG, tag="trilha")
        vista = {"a": 0.0, "b": 1.0, "pega": None, "cor": GOLD}   # fração visível, onde o polegar foi pego, cor

        def mostra(a, b):
            vista["a"], vista["b"] = float(a), float(b)
            tr.delete("dedo")
            if vista["b"] - vista["a"] < 0.999:
                retangulo_arredondado(tr, 0, round(vista["a"] * vis), 8, round(vista["b"] * vis), 4, vista["cor"],
                                      tag="dedo")

        def vai(y):
            tam = vista["b"] - vista["a"]
            cv.yview_moveto(max(0.0, min(1.0 - tam, (y - vista["pega"]) / vis)))

        def aperta(e):
            y0, y1 = vista["a"] * vis, vista["b"] * vis
            vista["pega"] = e.y - y0 if y0 <= e.y <= y1 else (y1 - y0) / 2   # fora do polegar: pula para lá
            vai(e.y)

        def solta(e):
            vista["pega"] = None
        cv.configure(yscrollcommand=mostra)
        tr.bind("<Button-1>", aperta)
        tr.bind("<B1-Motion>", lambda e: vista["pega"] is not None and vai(e.y))
        tr.bind("<ButtonRelease-1>", solta)
        def cor(c):
            vista["cor"] = c
            tr.itemconfigure("dedo", fill=c)
        tr.tag_bind("dedo", "<Enter>", lambda e: cor(GOLD_HOVER))
        tr.tag_bind("dedo", "<Leave>", lambda e: cor(GOLD))
        w.bind("<MouseWheel>", lambda e: cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        w.bind("<Up>", lambda e: cv.yview_scroll(-1, "units"))
        w.bind("<Down>", lambda e: cv.yview_scroll(1, "units"))
        return tr

    def item_liberado(self, key):
        """Mesma regra do sorteio (M.unlocked_items); no demo tudo liberado, como os heróis."""
        req = M.ITEMS[key].get("req")
        return self.demo or not req or req in self.meta["achievements"]

    def item_card(self, cv, x, y, key):
        """Card de um item no canvas a partir de (x, y); devolve a altura. Bloqueado: silhueta, cadeado, sem valores."""
        it, ok, fs = M.ITEMS[key], self.item_liberado(key), self.font_small
        top = next((M.RAR_COLOR[r] for r in reversed(it["rarities"]) if M.RAR_COLOR[r]), None)
        cv.create_image(x + 26, y + 26, image=self.icon(arte.ITEM_ART[key], 4, glow=ok and top or None, dark=not ok))
        cv.create_text(x + 54, y + 16, anchor="w", text=it["name"], fill=TEXT if ok else MUTED, font=self.font)
        cv.create_text(x + 54, y + 33, anchor="w", font=fs, fill=MUTED,
                       text=item_familia(key) + (f"  ·  consumir: {'cura' if 'heal' in it['consume'] else 'escudo'}" if ok else ""))
        ty, larg = y + 54, ITENS_CARD_W - 20
        if not ok:
            cv.create_image(x + 10, ty + 7, anchor="w", image=self.menu_icon("cadeado"))
            t = cv.create_text(x + 26, ty, anchor="nw", text=M.ACHIEVEMENTS.get(it["req"], it["req"]), fill=MUTED,
                               font=fs, width=larg - 16)
            ty = cv.bbox(t)[3] + 4
        for r in [] if not ok else it["rarities"]:
            c = M.consume_fx(key, r)
            comer = f"cura {c['heal']}" if "heal" in c else f"escudo {c.get('shield', 0)}"
            t = cv.create_text(x + 10, ty, anchor="nw", fill=M.RAR_COLOR[r] or TEXT, font=fs, width=larg,
                               text=f"{M.RAR_NAMES[r]}: {M.fx_text(M.item_fx(key, r))}  ·  {comer}")
            ty = cv.bbox(t)[3] + 3
        alto = max(ty - y + 6, 60)
        retangulo_arredondado(cv, x, y, x + ITENS_CARD_W, y + alto, CARTAO_R, CARD_BG, PANEL_EDGE, 2, tag="cartao",
                              extra=(f"card:{x}_{y}",))
        cv.tag_lower("cartao")
        return alto

    def show_items(self):
        livres = [k for k in M.ITEMS if self.item_liberado(k)]
        w, f = self.janela("itens_win", f"Itens  ·  {len(livres)} de {len(M.ITEMS)} liberados")
        self.itens_filtro = getattr(self, "itens_filtro", "todos")
        chips = tk.Frame(f, bg=PANEL_BG)
        chips.pack(fill="x", pady=(4, 0))
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=(4, 0))
        cv = tk.Canvas(row, width=ITENS_COLS * (ITENS_CARD_W + 6), height=ITENS_H, bg=PANEL_BG,
                       highlightthickness=0, yscrollincrement=40)
        cv.pack(side="left")
        self.itens_cv = cv
        self.rolagem(row, w, cv, ITENS_H)
        botoes = {}

        def desenha(filtro):
            self.itens_filtro = filtro
            for nome, b in botoes.items():
                b.pintar(nome == filtro)
            cv.delete("all")
            keys = [k for k in M.ITEMS if filtro == "todos" or (k in livres) == (filtro == "liberados")]
            y = 0
            for i in range(0, len(keys), ITENS_COLS):
                y += 6 + max(self.item_card(cv, c * (ITENS_CARD_W + 6), y, k)
                             for c, k in enumerate(keys[i:i + ITENS_COLS]))
            if not keys:
                cv.create_text(10, 20, anchor="w", text="Nenhum item aqui.", fill=MUTED, font=self.font)
            cv.configure(scrollregion=(0, 0, ITENS_COLS * (ITENS_CARD_W + 6), max(y, ITENS_H)))
            cv.yview_moveto(0)
        for nome, texto in (("todos", "Todos"), ("liberados", "Liberados"), ("bloqueados", "Bloqueados")):
            b = self.chip(chips, texto, False, lambda n=nome: desenha(n))
            b.pack(side="left", padx=(0, 3))
            botoes[nome] = b
        desenha(self.itens_filtro)
        self.ao_lado(w)

    def show_achievements(self):
        have = set(self.meta["achievements"]) & set(M.ACHIEVEMENTS)
        w, f = self.janela("conq_win", f"Conquistas  ·  {len(have)} de {len(M.ACHIEVEMENTS)}")
        grade = tk.Frame(f, bg=PANEL_BG)
        grade.pack(pady=(4, 0))
        for n, (k, desc) in enumerate(M.ACHIEVEMENTS.items()):
            ok = k in have
            card = self.cartao(grade, GOLD if ok else PANEL_EDGE, CONQ_CARD_W, CONQ_CARD_H)
            card.grid(row=n // CONQ_COLS, column=n % CONQ_COLS, padx=3, pady=3)
            tk.Label(card, image=self.icon(arte.CONQ_ART[k], 3, dark=not ok), bg=CARD_BG, height=36).pack(
                pady=(CARTAO_PAD, 2))
            tk.Label(card, text=desc, bg=CARD_BG, fg=TEXT if ok else MUTED, font=self.font_small,
                     wraplength=CONQ_CARD_W - 2 * CARTAO_PAD).pack()
            premios = [self.icon(arte.ITEM_ART[ik], 2, dark=not ok) for ik, it in M.ITEMS.items()
                       if it.get("req") == k and ik in arte.ITEM_ART]
            premios += [im for c in self.chars.values() if c.unlock == k for im in [self.hero_thumb(c, ok, 24)] if im]
            if premios:
                linha = tk.Frame(card, bg=CARD_BG)
                linha.pack(side="bottom", pady=(0, CARTAO_PAD))
                tk.Label(linha, text="libera", bg=CARD_BG, fg=MUTED, font=self.font_small).pack(side="left", padx=2)
                for im in premios[:3]:
                    tk.Label(linha, image=im, bg=CARD_BG).pack(side="left", padx=1)
                if len(premios) > 3:
                    tk.Label(linha, text=f"+{len(premios) - 3}", bg=CARD_BG, fg=MUTED, font=self.font_small).pack(side="left")
        self.ao_lado(w)

    def show_perfil(self):
        """Perfil (só dados que já existem: state, meta, usage_hist): herói, nível de domador, medalhas,
        números, gráfico dos últimos 7 dias, limites e atalhos. Textos novos do perfil ficam todos aqui."""
        run, meta, state, now = self.run, self.meta, self.state, time.time()
        st, fs, L = M.stats(run), self.font_small, PERFIL_W
        w, f = self.janela("perfil_win", "Perfil")

        def barra(parent, frac, cor, larg=L, alto=6):
            return self.barra(parent, larg, alto, frac, cor)

        def rotulo(parent, txt, fg=MUTED, font=fs):
            tk.Label(parent, text=txt, bg=PANEL_BG, fg=fg, font=font, anchor="w").pack(fill="x")

        def topo(esq, dir_, fg_dir=TEXT, font=fs):
            fr = tk.Frame(f, bg=PANEL_BG)
            fr.pack(fill="x")
            tk.Label(fr, text=esq, bg=PANEL_BG, fg=GOLD if font == self.font else MUTED, font=font).pack(side="left")
            tk.Label(fr, text=dir_, bg=PANEL_BG, fg=fg_dir, font=fs).pack(side="right")
        # cabeçalho: herói, run, HP
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x", pady=(4, 0))
        self.perfil_thumb = map_img(self.look_maps[0], 48)    # referência: o tk não guarda a imagem sozinho
        tk.Label(head, image=self.perfil_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 8))
        col = tk.Frame(head, bg=PANEL_BG)
        col.pack(side="left", fill="x")
        rotulo(col, f"{self.char.name}  ·  {self.stage_title}", GOLD, self.font)
        rotulo(col, f"Run #{run['id']}   ·   Andar {run['floor']}-{run['room']}   ·   ♥ {run['hp']}/{st['maxhp']}")
        barra(col, run["hp"] / st["maxhp"], HURT, L - 56).pack(anchor="w", pady=(3, 0))
        # nível de domador (energia na vida: mesma unidade do gráfico)
        n, frac, falta = nivel(state["xp_total"])
        self.menu_sep(f)
        topo(f"Domador  Nv {n}", f"{round(frac * 100)}%", GOLD, self.font)
        barra(f, frac, GOLD).pack(anchor="w", pady=2)
        rotulo(f, f"faltam ~{fmt(falta)} de energia para o Nv {n + 1}")
        # medalhas
        have = set(meta["achievements"]) & set(M.ACHIEVEMENTS)
        self.menu_sep(f)
        topo("Conquistas", f"{len(have)} / {len(M.ACHIEVEMENTS)}")
        med = tk.Frame(f, bg=PANEL_BG)
        med.pack(anchor="w", pady=2)
        dica = "passe o mouse numa medalha"
        info = tk.Label(f, text=dica, bg=PANEL_BG, fg=MUTED, font=fs, anchor="w", justify="left", wraplength=L)
        for i, (k, desc) in enumerate(M.ACHIEVEMENTS.items()):
            lb = tk.Label(med, image=self.icon(arte.CONQ_ART[k], dark=k not in have, lado=PERFIL_MEDALHA - 2),
                          bg=PANEL_BG, width=PERFIL_MEDALHA, height=PERFIL_MEDALHA, bd=0, padx=0, pady=0)
            lb.grid(row=i // PERFIL_MEDALHAS, column=i % PERFIL_MEDALHAS)
            txt = desc + ("" if k in have else "  (bloqueada)")
            lb.bind("<Enter>", lambda e, t=txt: info.configure(text=t, fg=TEXT))
            lb.bind("<Leave>", lambda e: info.configure(text=dica, fg=MUTED))
        info.pack(fill="x")
        # cartões de números
        proprios = [c for k, c in self.chars.items() if heroi_proprio(k)]
        best, dias = meta["best"], uso_por_dia(state, now)
        cartoes = (("HOJE", fmt(dias[-1][1]), "de energia"), ("SEQUÊNCIA", str(dias_seguidos(state, now)), "dias seguidos"),
                   ("NA VIDA", fmt(state["xp_total"]), "de energia"), ("RUNS", str(meta["runs"]), "jogadas"),
                   ("RECORDE", f"{best['floor']}-{best['room']}", "andar-sala"),
                   ("HERÓIS", f"{sum(self.is_unlocked(c) for c in proprios)}/{len(proprios)}",
                    f"{meta.get('chefes', 0)} chefes"))
        self.menu_sep(f)
        grade = tk.Frame(f, bg=PANEL_BG)
        grade.pack(fill="x")
        for c in range(3):
            grade.columnconfigure(c, weight=1, uniform="cartao")
        for i, (tit, val, sub) in enumerate(cartoes):
            card = self.cartao(grade, espessura=1)
            card.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="nsew")
            for j, (txt, fg, font) in enumerate(((tit, MUTED, fs), (val, TEXT, self.font), (sub, MUTED, fs))):
                tk.Label(card, text=txt, bg=CARD_BG, fg=fg, font=font, anchor="w", padx=0, pady=0).pack(
                    fill="x", padx=CARTAO_PAD, pady=(CARTAO_PAD if j == 0 else 0, CARTAO_PAD if j == 2 else 0))
        # gráfico dos últimos 7 dias (energia por dia, de usage_hist)
        self.menu_sep(f)
        topo("Últimos 7 dias  (energia)", fmt(sum(v for _, v in dias)), GOLD)
        alto, maior = 58, max(v for _, v in dias) or 1
        cv = tk.Canvas(f, width=L, height=alto + 16, bg=PANEL_BG, highlightthickness=0)
        cv.pack(pady=(2, 0))
        bw = L // 7
        for i, (d, v) in enumerate(dias):
            x0, hoje_ = i * bw + 4, i == len(dias) - 1
            h = max(2, round(alto * v / maior / 2) * 2)      # degraus de 2 px: cara de pixel
            cv.create_rectangle(x0, alto - h, x0 + bw - 8, alto, width=0,
                                fill=(GOLD if hoje_ else PERFIL_BARRA) if v else BAR_BG)
            cv.create_text(x0 + (bw - 8) / 2, alto + 9, text=DIAS[d.weekday()], fill=GOLD if hoje_ else MUTED, font=fs)
        # limites (iguais aos do painel)
        self.menu_sep(f)
        rotulo(f, "Limites")
        for key, nome in (("sessao", "Sessão"), ("semana", "Semana")):
            pct, reset, est, tok = limit_view(key, self.limits, state, now)
            val = f"{'~' if est else ''}{round(pct)}%" if pct is not None else (fmt(tok) if tok else "—")
            topo(f"{nome}  {val}", f"reseta {fmt_reset(reset, now)}" if reset else "", MUTED)
            if pct is not None:
                barra(f, pct / 100, limit_color(pct)).pack(anchor="w", pady=(1, 3))
        # rodapé: último uso e atalhos
        self.menu_sep(f)
        ult = ultimo_uso(state)
        rotulo(f, f"último uso: {fmt_ha(now - ult) if ult else 'nenhum ainda'}" + ("   ·   (modo demo)" if self.demo else ""))
        bot = tk.Frame(f, bg=PANEL_BG)
        bot.pack(fill="x", pady=(4, 0))
        for txt, fn in (("Conquistas", self.show_achievements), ("Cemitério", self.show_graveyard),
                        ("Itens", self.show_items)):
            self.chip(bot, txt, False, fn).pack(side="left", padx=(0, 4))
        self.ao_lado(w)

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
    import tkinter.font  # noqa: F401  (tk.font: medir texto para encurtar com "…")
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
