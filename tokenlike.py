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
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import arte  # noqa: E402
import masmorra as M  # noqa: E402

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
        return xp, raw

    def parse_line(self, line: bytes):
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
        if msg.get("id"):
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
        return inp + out + cc + cr * CACHE_READ_WEIGHT, raw

    def export(self) -> None:
        self.state["seen"] = list(self.seen)


# ------------------------------------------------------------- progresso
DEFAULT_STATE = {
    "tokens_total": 0,
    "xp_total": 0.0,
    "daily": {},
    "size": "Médio",
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
    def __init__(self, key, name, stages, frame_ms=600, stats=None, unlock=None):
        self.key, self.name, self.frame_ms = key, name, frame_ms
        self.stats = stats or {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
        self.unlock = unlock
        # cada estágio: {"floor", "title", "frames": [spec], "blink": spec|None, "sleep": spec|None}
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


def load_png_characters(folder: Path = CHARACTERS_DIR) -> list[CharacterDef]:
    out = []
    if not folder.is_dir():
        return out
    for d in sorted(folder.iterdir()):
        cfg = d / "character.json"
        if not cfg.is_file():
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
                frames = [spec(f) for f in st["frames"]]
                if not frames:
                    raise ValueError("estágio sem 'frames'")
                default_floor = M.DEFAULT_STAGE_FLOORS[min(i, len(M.DEFAULT_STAGE_FLOORS) - 1)]
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
            unlock = data.get("unlock")
            if unlock and unlock not in M.ACHIEVEMENTS:
                raise ValueError(f"'unlock' desconhecido: {unlock}")
            out.append(CharacterDef(d.name, data.get("name", d.name), stages,
                                    int(data.get("frame_ms", 600)), stats, unlock))
        except Exception as e:  # personagem com defeito não derruba o app
            log(f"personagem '{d.name}' ignorado: {e}")
    return out


def all_characters() -> dict[str, CharacterDef]:
    chars = {c.key: c for c in builtin_characters()}
    for c in load_png_characters():
        chars[c.key] = c
    return chars


# ------------------------------------------------------------------- GUI
def grid_bbox(grid):
    pts = [(x, y) for y, r in enumerate(grid) for x, ch in enumerate(r) if ch != "."]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def render_grid(grid, pal, s):
    h, w = len(grid), max(len(r) for r in grid)
    img = tk.PhotoImage(width=w * s, height=h * s)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            color = pal.get(ch)
            if color:
                img.put(color, to=(x * s, y * s, (x + 1) * s, (y + 1) * s))
    return img


def render_spec(spec, target_px: int):
    """Devolve (imagem, caixa_da_arte) — a caixa ignora as bordas transparentes."""
    if spec[0] == "grid":
        grid, pal = spec[1], spec[2]
        s = max(1, round(target_px / max(len(grid), max(len(r) for r in grid))))
        x0, y0, x1, y1 = grid_bbox(grid)
        return render_grid(grid, pal, s), (x0 * s, y0 * s, x1 * s, y1 * s)
    src = tk.PhotoImage(file=str(spec[1]))
    w, h = src.width(), src.height()
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if not src.transparency_get(x, y):
                xs.append(x)
                ys.append(y)
    box = (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else (0, 0, w, h)
    m = max(w, h)
    if m < target_px:
        z = max(1, round(target_px / m))
        return src.zoom(z), tuple(v * z for v in box)
    if m > target_px * 1.5:
        sub = math.ceil(m / target_px)
        return src.subsample(sub), tuple(v // sub for v in box)
    return src, box


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
        self.chars = all_characters()
        if self.state["size"] not in SIZES:
            self.state["size"] = "Médio"
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
        self.blink_until = 0.0
        self.next_blink = time.time() + 3
        self.next_zzz = 0.0
        self.last_rest_heal = time.time()
        self.last_save = time.time()
        self.busy_until = time.time() + 1.5
        self.respawn_at = None
        self.popup_win = None
        self._drag = None
        self._moved = False

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
        self.respawn_at = None
        if announce:
            self.build()
            self.popup([f"Run #{self.run['id']} começou!", f"{c.name} entra na masmorra..."], 5000)

    # --------------------------------------------------------------- layout
    def build(self, first=False):
        px = SIZES[self.state["size"]]
        self.px = px
        self.bpx = round(px * 1.5)
        self.T = 16 * px
        left = 6 * px + 6
        self.pcx = left + self.T // 2
        foe_w = 11 * self.bpx
        self.fcx = left + self.T + 4 * px + foe_w // 2
        self.W = self.fcx + foe_w // 2 + 10
        self.top = 52
        self.base_y = self.top + self.T
        self.H = self.base_y + 64

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
        self.acc_items = {}
        self.acc_items["escudo"] = c.create_image(0, 0, anchor="s", state="hidden")
        self.sprite = c.create_image(self.pcx, self.base_y, anchor="s", image=self.frames[0])
        self.acc_items["mao"] = c.create_image(0, 0, anchor="s", state="hidden")
        self.acc_items["cabeca"] = c.create_image(0, 0, anchor="s", state="hidden")
        self.foe = c.create_image(self.fcx, self.base_y, anchor="s", state="hidden")
        self.foe_crown = c.create_image(self.fcx, self.base_y, anchor="s", state="hidden")

        py = self.base_y + 6
        c.create_rectangle(6, py, self.W - 6, py + 52, fill=PANEL_BG, outline=PANEL_EDGE, width=2)
        self.title_txt = c.create_text(14, py + 11, anchor="w", fill=TEXT, font=self.font)
        self.hp_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=HURT, font=self.font)
        self.info_txt = c.create_text(14, py + 26, anchor="w", fill=MUTED, font=self.font_small)
        self.bar_x0, self.bar_x1, self.bar_y = 14, self.W - 14, py + 38
        c.create_rectangle(self.bar_x0, self.bar_y, self.bar_x1, self.bar_y + 6, fill=BAR_BG, outline="")
        self.bar = c.create_rectangle(self.bar_x0, self.bar_y, self.bar_x0, self.bar_y + 6,
                                      fill=ENERGY, outline="")
        self.refresh_equipment()
        self.update_panel()

    def art_img(self, key, boss=False):
        """Imagem (em cache) de um desenho do arte.py."""
        ck = (key, boss)
        if ck not in self.art:
            pal = arte.BOSS_PAL if boss else arte.PAL
            self.art[ck] = render_grid(arte.all_art()[key], pal, self.bpx if boss else self.px)
        return self.art[ck]

    def load_images(self):
        stage = self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)]
        try:
            self.frames, boxes = zip(*[render_spec(s, self.T) for s in stage["frames"]])
            self.frames = list(self.frames)
            self.pet_box = boxes[0]
            self.blink_img = render_spec(stage["blink"], self.T)[0] if stage["blink"] else None
            self.sleep_img = (render_spec(stage["sleep"], self.T)[0] if stage["sleep"]
                              else self.blink_img or self.frames[0])
        except Exception as e:
            if self.char.key == "slime":
                raise
            log(f"erro carregando imagens de '{self.char.key}': {e}; voltando para o Slime")
            self.run["char"] = "slime"
            return self.load_images()
        self.stage_title = stage["title"]

    def refresh_equipment(self):
        """Por enquanto só esconde os acessórios; os itens voltam a aparecer no pet na Task 3."""
        self.acc_rel = {}
        for item_id in self.acc_items.values():
            self.canvas.itemconfigure(item_id, state="hidden")
        self.place_pet(0, 0)

    def place_pet(self, dx, dy):
        self.canvas.coords(self.sprite, self.pcx + dx, self.base_y + dy)
        for slot, (rx, ry) in self.acc_rel.items():
            self.canvas.coords(self.acc_items[slot], self.pcx + dx + rx, self.base_y + dy + ry)

    def update_panel(self):
        run = self.run
        st = M.stats(run)
        self.canvas.itemconfigure(self.title_txt, text=f"{self.stage_title}  ·  Run #{run['id']}")
        self.canvas.itemconfigure(self.hp_txt, text=f"♥ {run['hp']}/{st['maxhp']}")
        self.canvas.itemconfigure(
            self.info_txt,
            text=f"Andar {run['floor']}-{run['room']}   ATK {st['atk']}  DEF {st['def']}   $ {run['gold']}")
        cost = M.room_cost(run)
        frac = min(1.0, run["energy"] / cost) if cost else 0
        x1 = self.bar_x0 + (self.bar_x1 - self.bar_x0) * frac
        self.canvas.coords(self.bar, self.bar_x0, self.bar_y, x1, self.bar_y + 6)

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
        for key, c in self.chars.items():
            if self.is_unlocked(c):
                self.char_menu.add_radiobutton(label=c.name, value=key, variable=self.char_var,
                                               command=self.change_character)
            else:
                self.char_menu.add_command(
                    label=f"{c.name}  [bloqueado: {M.ACHIEVEMENTS[c.unlock]}]", state="disabled")

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

    def toggle_top(self):
        self.state["topmost"] = bool(self.top_var.get())
        self.root.attributes("-topmost", self.state["topmost"])

    def give_up(self):
        if self.run["dead"]:
            return
        ev = {"lines": []}
        M.die(self.run, self.meta, ev, "Desistiu")
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
        ev = M.enter_room(self.run, self.meta, self.rng, self.char.stage_floors, mode="auto")
        steps = []
        t = 0

        def at(ms, fn):
            steps.append((ms, fn))

        kind = ev["kind"]
        boss = ev.get("boss", False)
        sprite = ev.get("sprite")
        name_color = {"boss": HURT, "monster": TEXT, "mimic": HURT, "stairs": CYAN}.get(kind, GOLD)
        at(0, lambda: self.show_foe(sprite, boss))
        at(0, lambda: self.floater(ev["name"], name_color, x=self.fcx, life=22))
        t = 500

        if kind in ("monster", "boss", "mimic"):
            hits = ev["hits"]
            shown = hits if len(hits) <= 8 else hits[:7] + [hits[-1]]
            for who, d in shown:
                if who == "pet":
                    at(t, lambda d=d: (self._set("lunge", [5, 10, 5, 0]),
                                       self.floater(f"-{d}", TEXT, x=self.fcx, life=10)))
                elif who == "foe":
                    at(t, lambda d=d: (self._set("foe_lunge", [-5, -10, -5, 0]),
                                       self.floater(f"-{d}", HURT, life=10)))
                else:
                    at(t, lambda: self.floater("esquivou!", CYAN, life=10))
                t += 380
            if ev["won"]:
                at(t, lambda: (self.burst(self.fcx, self.base_y - 4 * self.px), self.hide_foe()))
                t += 300
                at(t, lambda: self.floater(f"+{ev.get('gold', 0)} $", GOLD, x=self.fcx))
                t += 450
        elif kind == "trap":
            if ev.get("dodged"):
                at(t, lambda: self.floater("esquivou!", CYAN))
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
        if ev.get("gold") and kind not in ("monster", "boss", "mimic"):
            at(t, lambda: self.floater(f"+{ev['gold']} $", GOLD, x=self.fcx))
            t += 450
        for line in ev["lines"]:
            at(t, lambda line=line: self.floater(line, TEXT, life=24))
            t += 600
        if ev.get("item"):
            key, rar = ev["item"]["key"], ev["item"]["rar"]
            it = M.ITEMS[key]
            at(t, lambda: self.show_foe(key, False))
            at(t, lambda: self.floater(it["name"], GOLD, x=self.fcx, life=24))
            t += 700
            at(t, lambda: (self.hide_foe(), self.refresh_equipment(),
                           self.floater(M.fx_text(M.item_fx(key, rar)), GOOD, life=24)))
            t += 700
        if ev.get("consumed"):
            c = ev["consumed"]
            if "heal" in c:
                at(t, lambda: self.floater(f"+{c['heal']} ♥", GOOD))
            else:
                at(t, lambda: self.floater(f"+{c['shield']} escudo", CYAN))
            t += 600
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

    def _set(self, attr, value):
        setattr(self, attr, list(value))

    def show_foe(self, sprite, boss=False):
        if not sprite:
            return
        self.canvas.itemconfigure(self.foe, image=self.art_img(sprite, boss), state="normal")
        self.canvas.coords(self.foe, self.fcx, self.base_y)
        if boss:
            img = self.art_img(sprite, True)
            self.canvas.itemconfigure(self.foe_crown, image=self.art_img("coroa"), state="normal")
            self.canvas.coords(self.foe_crown, self.fcx, self.base_y - img.height() + self.px)
        else:
            self.canvas.itemconfigure(self.foe_crown, state="hidden")

    def hide_foe(self):
        self.canvas.itemconfigure(self.foe, state="hidden")
        self.canvas.itemconfigure(self.foe_crown, state="hidden")

    def evolve(self):
        old = self.stage_title
        self.load_images()
        self.canvas.itemconfigure(self.sprite, image=self.frames[0])
        self.refresh_equipment()
        self.burst(self.pcx, self.base_y - self.T // 2)
        self.hop = [-6, -12, -16, -12, -6, 0]
        self.floater("EVOLUIU!", GOLD, life=22)
        self.popup([f"{old} evoluiu para {self.stage_title}!", "+4 HP máx, +1 ATK"], 5000)

    def on_death(self):
        g = self.meta["graveyard"][-1]
        self.save()
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
        for item_id in self.acc_items.values():
            self.canvas.itemconfigure(item_id, state="hidden")
        self.acc_rel = {}
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
    def floater(self, text, color=TEXT, life=16, x=None):
        c = self.canvas
        x = (self.pcx if x is None else x) + self.rng.randint(-10, 10)
        t = c.create_text(x, self.base_y - self.T + 10, text=text, fill=color, font=self.font_small)
        x0, y0, x1, y1 = c.bbox(t)
        shift = max(0, 4 - (x0 - 5)) - max(0, (x1 + 5) - (self.W - 4))
        if shift:
            c.move(t, shift, 0)
            x0, x1 = x0 + shift, x1 + shift
        r = c.create_rectangle(x0 - 5, y0 - 2, x1 + 5, y1 + 2, fill=PANEL_BG, outline=PANEL_EDGE)
        c.tag_raise(t)
        self.floaters.append([(r, t), life])

    def burst(self, x, y, colors=(GOLD, "#ffffff", GOOD)):
        for i in range(16):
            a = i * math.pi / 8
            r = self.canvas.create_rectangle(x - 3, y - 3, x + 3, y + 3,
                                             fill=self.rng.choice(colors), outline="")
            self.particles.append([r, math.cos(a) * 6, math.sin(a) * 6, 12])

    def tick(self):
        now = time.time()
        run = self.run
        try:
            if run["dead"]:
                if self.respawn_at and now >= self.respawn_at:
                    self.new_run()
            elif now >= self.busy_until and M.can_enter(run):
                self.play_room()

            idle = now - self.state["last_fed"]
            busy = now < self.busy_until
            if run["dead"]:
                dy = 0
            else:
                sleeping = idle > SLEEP_AFTER_S and not busy
                if sleeping:
                    img = self.sleep_img
                    bob = -2 if int(now / 1.4) % 2 else 0
                    if now > self.next_zzz:
                        self.floater("z Z", MUTED, life=20)
                        self.next_zzz = now + 3
                else:
                    if self.blink_img is not None and now > self.next_blink:
                        self.blink_until = now + 0.16
                        self.next_blink = now + self.rng.uniform(2.5, 6)
                    if self.blink_img is not None and now < self.blink_until:
                        img = self.blink_img
                    else:
                        i = int(now * 1000 / self.char.frame_ms) % len(self.frames)
                        img = self.frames[i]
                    bob = -2 if int(now / 0.6) % 2 else 0
                dy = self.hop.pop(0) if self.hop else bob
                dx = self.lunge.pop(0) if self.lunge else 0
                self.canvas.itemconfigure(self.sprite, image=img)
                self.place_pet(dx, dy)
            fdx = self.foe_lunge.pop(0) if self.foe_lunge else 0
            self.canvas.coords(self.foe, self.fcx + fdx, self.base_y)

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

    def show_stats(self):
        run, meta = self.run, self.meta
        st = M.stats(run)
        lines = [f"Run #{run['id']}  -  {self.char.name} ({self.stage_title})",
                 f"Andar {run['floor']}-{run['room']}    ♥ {run['hp']}/{st['maxhp']}",
                 f"ATK {st['atk']}   DEF {st['def']}   Esquiva {int(st['dodge'] * 100)}%"
                 f"   Ouro {run['gold']}",
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
