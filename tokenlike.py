#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Tokenlike - Token Dungeon

A little pixel pet that lives on your screen and descends a dungeon using the
tokens you spend in Claude Code as energy. Random rooms, items that show up
on its look, bosses, unlocks and permadeath.

Privacy:
  * Reads the log files Claude Code already saves on your PC
    (%USERPROFILE%\\.claude\\projects\\*.jsonl) and uses ONLY the token counts.
  * Does not store or show prompts/responses, does not use the internet, does not
    install hooks and does not touch any Claude Code setting.
  * Progress is kept in %USERPROFILE%\\.tokenlike\\

Usage:
  python tokenlike.py                   opens the pet
  python tokenlike.py --demo            test mode (fake tokens, separate progress)
  python tokenlike.py --import-history  on first use, starts with the energy from your history
  python tokenlike.py --reset           erases all progress (runs, graveyard, achievements)
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
import types
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
import legacy  # noqa: E402
_t = i18n.t   # text in the current language (every visible text goes through here)
import visual  # noqa: E402

tk = None  # tkinter is imported only when the window opens (run_gui)

APP_NAME = "Agent Tokenlike"
DATA_DIR = Path.home() / ".tokenlike"
OLD_DATA_DIR = Path.home() / ".tokenpet"  # old name (TokenPet)
CHARACTERS_DIR = SCRIPT_DIR / "characters"
LOG_FILE = DATA_DIR / "tokenlike.log"

# ----------------------------------------------------------------- settings
CACHE_READ_WEIGHT = 0.1     # tokens read from cache count 10% (they are cheap and plentiful)
POLL_MS = 2500              # how often the logs are checked
REST_AFTER_S = 5 * 60       # idle for 5 min -> rests and recovers 1 HP every 2 min
SLEEP_AFTER_S = 10 * 60     # idle for 10 min -> sleeps (Zzz). Never dies from being idle.
HIDE_S = 5 * 60         # "Show only when in use": hides after this long without new tokens (keeps running hidden)
SAVE_EVERY_S = 30
RESPAWN_S = 12              # how long the tombstone shows before the new run
SIZES = {"Small": 4, "Medium": 6, "Large": 8}  # screen px per art pixel
MODES = {"auto": "Auto", "interactive": "Interactive"}
CHOICE_TEXT_W = 220         # wrap width of the idol/campfire texts
CHOICE_BAR_W = 150          # width of the timer bar in the choice panel
TRANSPARENT = "#ff00fe"     # "key" color that Windows makes invisible

PANEL_BG = "#1d1b2b"
PANEL_EDGE = "#4b4680"
TEXT = "#f2f0ff"
MUTED = "#a9a4d6"
BAR_BG = "#35315a"
ENERGY = "#5fd3c6"
ENERGY_SHIMMER = "#c8f5ef"     # shimmer that runs along the energy bar
SHIMMER_S = 2.4                # seconds per shimmer pass
LIM_HALF = 5                   # half height of the Session/Week bars (10 px)
PEAK_COLOR = "#8f88d6"          # limit bar without an official %: window usage / your peak (neutral, not a warning)
GOOD = "#7ee081"
HURT = "#ff6b81"
GOLD = "#ffd23f"
CYAN = "#6fd6ff"
# soft pastel tints for the HUD info line: only to tell the fields apart, never to draw attention
INFO_COLOR = {"atk": "#e3a6a6", "def": "#a6bfe3", "gold": "#e3d3a0"}
STATUS_COLOR = {"burn": "#ff9f43", "shock": "#fff27a", "poison": "#4fbf5a", "freeze": "#9fe8ff"}
MENU_HOVER = "#2e2a48"      # menu row background on mouse hover
GOLD_HOVER = "#fff27a"      # scrollbar thumb on mouse hover
CARD_BG = "#262338"         # card inner color (a bit lighter than the panel)
WINDOW_R, CARD_R = 8, 4   # stepped corner radius: windows/panel and cards/chips
CARD_PAD = 6              # minimum padding between the card border and its content
HERO_COLS, HERO_CARD_W, HERO_CARD_H = 5, 128, 160   # hero grid (fixed-size cards)
ACH_COLS, ACH_CARD_W, ACH_CARD_H = 4, 150, 118   # achievements grid
GRAVE_W, GRAVE_H, GRAVE_TOMB = 470, 420, 92           # graveyard: width, visible height, height of each tombstone
JOURNAL_W, JOURNAL_H = 420, 420                      # journal: card width, visible height
ITEMS_COLS, ITEMS_CARD_W, ITEMS_H = 2, 280, 440      # items page: columns, card width, visible height
WINDOW_ATTRS = ("menu_win", "heroes_win", "stats_win", "ach_win", "grave_win", "items_win", "profile_win", "journal_win")
REOPEN = {"heroes_win": "show_heroes", "stats_win": "show_stats", "ach_win": "show_achievements",
          "grave_win": "show_graveyard", "items_win": "show_items", "profile_win": "show_profile", "journal_win": "show_journal"}   # language switch

PROFILE_W, PROFILE_MEDALS, PROFILE_MEDAL, PROFILE_BAR = 312, 13, 24, "#8a5a2b"   # profile: width, medals per row, cell, color
FX_MS = 200   # ms per phase of the elemental look animation (own clock, separate from the hero's frame_ms)


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
    """Appends a finished run to runs.jsonl (game data only; a failure is only logged)."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / ("runs-demo.jsonl" if demo else "runs.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        log(f"could not write runs.jsonl: {e}")


# ------------------------------------------------------- token reading
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
    """Reads only the new lines of Claude Code's .jsonl files and adds up the token usage."""

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
        """Marks everything that already exists as read (the pet starts from scratch)."""
        self._files_at = 0
        for f in self.files():
            try:
                self.offsets[str(f)] = f.stat().st_size
            except OSError:
                pass

    def poll(self) -> tuple[float, int]:
        """Returns (xp_gained, raw_tokens) since the last read."""
        xp, raw = 0.0, 0
        for f in self.files():
            key = str(f)
            try:
                size = f.stat().st_size
            except OSError:
                continue
            off = self.offsets.get(key, 0)
            if size < off:          # file was recreated/truncated
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
            if end < 0:             # line still being written
                continue
            self.offsets[key] = off + end + 1
            for line in data[:end].splitlines():
                got = self.parse_line(line)
                if got:
                    xp += got[0]
                    raw += got[1]
                    if got[2] is not None:      # no timestamp: counts as energy, but not in the bars
                        add_usage(self.state, got[2], got[0])
        prune_usage(self.state, time.time())
        return xp, raw

    def backfill(self) -> None:
        """Once: fills the per-time history with what was already read (up to each file's offset,
        from the last 8 days). Gives no energy and does not touch `seen`."""
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
        self.state["usage_hist_since"] = cutoff         # the history covers the last 8 days
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
        # Claude Code writes the same response on several lines: count it once
        if msg.get("id") and seen is not None:      # backfill: local dedup, without touching `seen`
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
    """ISO (UTC) timestamp of the response -> epoch. Only the time, no content."""
    if not isinstance(v, str):
        return None
    try:
        t = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.timestamp()


# ------------------------------------------------- history and limit estimate
BUCKET_S = 300                      # 5-min buckets with the weighted XP
HIST_KEEP_S = 8 * 86400             # keeps only the last 8 days
WINDOWS = {"session": 5 * 3600, "week": 7 * 86400}
OFFICIAL_FRESH_S = 600              # an official reading is valid for ~10 min without "~"
MIN_CALIB_XP = 1000                 # with almost no local tokens, the factor is useless


def add_usage(state: dict, ts: float, xp: float) -> None:
    hist = state.setdefault("usage_hist", {})
    k = str(int(ts // BUCKET_S * BUCKET_S))
    hist[k] = hist.get(k, 0) + xp


def prune_usage(state: dict, now: float) -> None:
    hist = state.get("usage_hist") or {}
    if "usage_hist_since" in state:
        state["usage_hist_since"] = max(state["usage_hist_since"], now - HIST_KEEP_S)
    for k in [k for k in hist if int(k) < now - HIST_KEEP_S]:
        del hist[k]


def usage_between(state: dict, start: float, end: float) -> float:
    return sum(v for k, v in (state.get("usage_hist") or {}).items() if int(k) + BUCKET_S > start and int(k) < end)


def calibrate(state: dict, limits: dict | None, now: float) -> None:
    """New official reading -> factor = official % / local tokens in the window, per window."""
    upd = (limits or {}).get("updated")
    cal = state.setdefault("calib", {})
    if not upd or upd == cal.get("updated"):
        return
    cal["updated"] = upd
    for key, win in WINDOWS.items():
        pct, reset = limits.get(key, (None, None))
        if pct is None or not reset:
            continue
        if state.get("usage_hist_since", math.inf) > reset - win:
            continue                        # history does not cover the whole window: keep the previous factor
        tok = usage_between(state, reset - win, now)
        if tok >= MIN_CALIB_XP:
            cal[key] = {"f": pct / tok, "reset": reset}


def sessions(state: dict) -> list[list[float]]:
    """5h windows rebuilt from the history, [start, tokens]: one starts at the 1st use after the previous one ended."""
    out = []
    for k, v in sorted((int(k), v) for k, v in (state.get("usage_hist") or {}).items() if v > 0):
        if not out or k >= out[-1][0] + WINDOWS["session"]:
            out.append([k, 0.0])
        out[-1][1] += v
    return out


def peak(state: dict, key: str, tok: float) -> float:
    """Largest usage ever seen in window `key` (kept in state["peak"], survives the 8-day history).
    It is the bar's yardstick when there is no official % or factor: "how much of your peak", not of the real limit."""
    p = state.setdefault("peak", {})
    hist = max((t for _, t in sessions(state)), default=0) if key == "session" else 0
    p[key] = max(p.get(key, 0), hist, tok or 0)
    return p[key]


def limit_view(key: str, limits: dict | None, state: dict, now: float):
    """(pct|None, reset|None, estimated, tokens|None) for the line of window `key`."""
    win = WINDOWS[key]
    pct, reset = (limits or {}).get(key, (None, None))
    upd = (limits or {}).get("updated") or 0
    if pct is not None and now - upd < OFFICIAL_FRESH_S:
        return pct, reset, False, None
    cal = (state.get("calib") or {}).get(key)
    if not cal and key == "session":         # no factor: the session comes from the history (starts at the 1st use)
        s = sessions(state)
        if s and now < s[-1][0] + win:
            return None, s[-1][0] + win, False, s[-1][1]
        return None, None, False, 0.0
    if cal:
        reset = cal["reset"]
    if reset and reset <= now:              # the reset passed: move the window forward by multiples of its length
        reset += ((now - reset) // win + 1) * win
    start = reset - win if reset else now - win
    tok = usage_between(state, start, now)
    if cal:
        return tok * cal["f"], reset, True, None
    return None, reset, False, tok


# ------------------------------------------------------------- profile (pure functions)
LEVEL_XP = 1_000_000                # tamer level = floor(sqrt(lifetime energy (xp_total) / 1M))


def level(total: float) -> tuple[int, float, float]:
    """(level, fraction to the next one, energy still needed). Level n starts at n² million energy."""
    n = math.isqrt(int(total // LEVEL_XP))
    base, next_ = n * n * LEVEL_XP, (n + 1) ** 2 * LEVEL_XP
    return n, (total - base) / (next_ - base), next_ - total


def usage_per_day(state: dict, now: float, dias: int = 7) -> list[tuple[date, float]]:
    """XP from `usage_hist` summed per local day, from the oldest to today."""
    today = datetime.fromtimestamp(now).date()
    out = {today - timedelta(days=i): 0.0 for i in range(dias)}
    for k, v in (state.get("usage_hist") or {}).items():
        d = datetime.fromtimestamp(int(k)).date()
        if d in out:
            out[d] += v
    return sorted(out.items())


def streak_days(state: dict, now: float) -> int:
    """Consecutive days with usage up to today (today without usage yet does not break the streak).
    Uses `usage_hist` (8 days, by time) and `daily` (60 days, counted while the app is open)."""
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
    """End of the last 5-min bucket with tokens."""
    ks = [int(k) for k, v in (state.get("usage_hist") or {}).items() if v > 0]
    return max(ks) + BUCKET_S if ks else None


def fmt_ago(dt: float) -> str:
    if dt < 60:
        return _t("now")
    if dt < 3600:
        return _t("{n} min ago", n=int(dt // 60))
    if dt < 86400:
        return _t("{n} h ago", n=int(dt // 3600))
    return _t("{n} d ago", n=int(dt // 86400))


# ------------------------------------------------------------- progress
DEFAULT_STATE = {
    "data_version": legacy.DATA_VERSION,   # 2 = English keys (legacy.py converts older saves)
    "tokens_total": 0,
    "xp_total": 0.0,
    "daily": {},
    "size": "Medium",
    "mode": "auto",              # "auto" or "interactive" (the player chooses take/consume)
    "lang": "pt",                # interface language: "pt" or "en" (i18n.py)
    "pos": None,
    "topmost": True,
    "only_when_used": False,         # hides after HIDE_S without tokens and comes back when there is usage
    "last_fed": 0.0,
    "run": None,
    "meta": None,
}


def load_state(path: Path) -> tuple[dict, bool]:
    state = json.loads(json.dumps(DEFAULT_STATE))
    is_new = True
    if path.exists():
        try:
            state.update(legacy.migrate_state(json.loads(path.read_text(encoding="utf-8"))))
            is_new = False
        except (OSError, ValueError) as e:
            log(f"unreadable state ({e}); starting from scratch")
    meta = M.new_meta()
    meta.update(state.get("meta") or {})
    state["meta"] = meta
    if state.get("run"):
        M.migrate_run(state["run"])
    return state, is_new


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def read_limits(path: Path, now: float) -> dict | None:
    """{"session": (pct|None, resets_at), "week": ...}; pct None = stale data (the reset already passed)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    out = {}
    for key, name in (("five_hour", "session"), ("seven_day", "week")):
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
    """Reset time in the PC's time zone: "14:30" if it is today, otherwise "Fri 09:00"."""
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


# ----------------------------------------------------------- characters
class CharacterDef:
    def __init__(self, key, name, stages, frame_ms=600, stats=None, unlock=None, community=False, trait=None):
        self.key, self.name, self.frame_ms = key, name, frame_ms
        self.stats = stats or {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
        self.unlock, self.community = unlock, community
        self.trait = trait or {}
        # each stage: {"floor", "title", "frames": [spec], "blink": spec|None, "sleep": spec|None}
        # and, if it comes from a spritesheet, "states": {state: [spec]} (spec ("sheet", path, box, N))
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
                       "blink": closed, "sleep": closed, "states": states})
    return [CharacterDef("slime", "Slime", stages, stats={"hp": 20, "atk": 3, "def": 0, "dodge": 0})]


DEFAULT_STATS = {"hp": 20, "atk": 3, "def": 0, "dodge": 0, "spd": 10.0}
_LEAVES = {}  # (path, mtime) -> (box rows, N, {box: reduced PixelMap}); the decoded PNG is discarded


def read_sheet(path: Path):
    """Box rows of the sheet, the reduction factor N and the reduced map of each box. Pure (runs in the thread).
    Opaque = alpha > 128; the mask is sampled (1 every `a` px) and loses islands of up to 2 px."""
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
            occupied = {}   # cell -> opaque points (offset inside the cell)
            for ys, lin in enumerate(m):
                for xs in range(ws):
                    if lin[xs]:
                        X, Y = xs * a, ys * a
                        occupied.setdefault((Y // ch, X // cw), []).append((X % cw, Y % ch))
            pts = [p for cel in occupied.values() for p in cel]
            if not pts:
                raise ValueError(f"sheet without frames: {path.name}")
            # a single box (union of the opaque pixels of all cells) so the frames do not jitter
            ox0, oy0 = min(x for x, _ in pts), min(y for _, y in pts)
            ox1, oy1 = min(cw, max(x for x, _ in pts) + a), min(ch, max(y for _, y in pts) + a)
            # cell without opaque pixels (row with fewer than 8 frames) is left out: never becomes a blinking frame
            lines = [[(c * cw + ox0, r * ch + oy0, c * cw + ox1, r * ch + oy1) for c in range(cols) if (r, c) in occupied]
                      for r in range(lins)]
            n = sheet.reduction_factor(oy1 - oy0)
        else:
            # ponytail: boxes accurate to `a` px (sampled); an exact cut costs ~5 s on a big sheet
            lines = [[(x0 * a, y0 * a, min(w, x1 * a), min(h, y1 * a)) for x0, y0, x1, y1 in lin]
                      for lin in sheet.cut(ws, hs, lambda x, y: m[y][x])]
            n = sheet.reduction_factor(max((c[3] - c[1] for lin in lines for c in lin), default=1))
        if not any(lines):
            raise ValueError(f"sheet without frames: {path.name}")
        maps = {}
        for lin in lines:
            for (x0, y0, x1, y1) in lin:
                maps[(x0, y0, x1, y1)] = {
                    ((x - x0) // n, (y - y0) // n): "#%02x%02x%02x" % tuple(rgba[4 * (y * w + x):4 * (y * w + x) + 3])
                    for y in range(y0, y1, n) for x in range(x0, x1, n) if op[y * w + x]}
        _LEAVES[ck] = lines, n, maps
    return _LEAVES[ck]


def stage_of_sheet(path: Path, floor: int, title: str) -> dict:
    """Spritesheet stage not cut yet: discovery only reads the PNG header (cheap).
    `complete_stage` (in the thread, when the hero becomes active) fills "frames" and "states"."""
    with open(path, "rb") as f:
        sheet.info_png(f.read(29))
    return {"floor": floor, "title": title, "sheet": path, "frames": None, "blink": None, "sleep": None}


def complete_stage(stage: dict) -> dict:
    """Cuts the stage's sheet: states in row order; an empty or missing row uses Idle.
    An error becomes stage["error"] (the GUI falls back to the Slime). Pure: may run outside the Tk thread."""
    try:
        lines, n, _ = read_sheet(stage["sheet"])
        specs = [[("sheet", stage["sheet"], c, n) for c in lin] for lin in lines]
        idle = next(l for l in specs if l)
        states = {e: (specs[i] if i < len(specs) and specs[i] else idle) for i, e in enumerate(sheet.STATES)}
        stage["frames"] = states["idle"]
        stage["states"] = states      # last: whoever sees "states" already sees "frames"
    except Exception as e:
        stage["error"] = str(e)
    return stage


def pet_openpets(d: Path):
    """OpenPets format (pet.json): (png, name) of the folder. A .webp `spritesheetPath` uses the .png with the same name;
    without pet.json: spritesheet.png or the 1st .png. png None = nothing usable (webp-only logs a warning)."""
    name, rel = d.name, None
    try:
        j = json.loads((d / "pet.json").read_text(encoding="utf-8"))
        name = str(j.get("displayName") or j.get("name") or d.name)
        rel = j.get("spritesheetPath")
    except (OSError, ValueError, AttributeError):
        pass   # pet.json missing or invalid: the folder name is used
    cands = []
    if isinstance(rel, str) and rel:
        p = d / rel
        cands.append(p.with_suffix(".png") if p.suffix.lower() == ".webp" else p)
    cands.append(d / "spritesheet.png")
    cands += sorted(d.glob("*.png"))
    png = next((c for c in cands if c.suffix.lower() == ".png" and c.is_file()), None)
    if not png and any(d.glob("*.webp")):
        log(f"pet '{d.name}' ignored: only has WebP; convert it to PNG (python tools/convert_webp.py {d})")
    return png, name


def load_png_characters(folder: Path = CHARACTERS_DIR) -> list[CharacterDef]:
    out = []
    if not folder.is_dir():
        return out
    for d in sorted(folder.iterdir()):
        cfg = d / "character.json"
        if not cfg.is_file():
            png, name = pet_openpets(d)   # sheet without character.json: one stage, default stats
            if png:
                try:
                    out.append(CharacterDef(d.name, name, [stage_of_sheet(png, 1, name)], stats=dict(DEFAULT_STATS)))
                except Exception as e:
                    log(f"character '{d.name}' ignored: {e}")
            continue
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))

            def spec(name):
                p = d / name
                if not p.is_file():
                    raise FileNotFoundError(f"image not found: {p.name}")
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
                    raise ValueError("stage without 'frames'")
                stages.append({
                    "floor": int(st.get("floor", default_floor)),
                    "title": st.get("title", data.get("name", d.name)),
                    "frames": frames,
                    "blink": spec(st["blink"]) if st.get("blink") else None,
                    "sleep": spec(st["sleep"]) if st.get("sleep") else None,
                })
            if not stages:
                raise ValueError("no stage in 'stages'")
            stats = {"hp": 20, "atk": 3, "def": 0, "dodge": 0}
            stats.update(data.get("stats") or {})
            for k in ("hp", "atk", "def"):          # wrong type: hero ignored here, not an error on every tick
                stats[k] = int(stats[k])
            for k in ("dodge", "spd", "crit", "critdmg"):
                if k in stats:
                    stats[k] = float(stats[k])
            unlock = data.get("unlock")
            if unlock and unlock not in M.ACHIEVEMENTS:
                raise ValueError(f"unknown 'unlock': {unlock}")
            trait = data.get("traço") or data.get("trait") or {}
            if not isinstance(trait, dict):
                raise ValueError("'trait' must be an object")
            valid = M.stats(M.new_run("x", {}, 0))
            for k, v in trait.items():
                if k not in valid or isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise ValueError(f"invalid 'trait': {k}")
            out.append(CharacterDef(d.name, data.get("name", d.name), stages,
                                    int(data.get("frame_ms", 600)), stats, unlock, trait=trait))
        except Exception as e:  # a broken character does not bring the app down
            log(f"character '{d.name}' ignored: {e}")
    return out


def petdex_dirs() -> list[Path]:
    """Petdex pet folders (read only, never written). Read on each call so the test can swap HOME."""
    return [Path.home() / ".petdex" / "pets", Path.home() / ".codex" / "pets"]


def load_petdex_characters() -> list[CharacterDef]:
    """Community pets: via `pet_openpets` (read only)."""
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
                log(f"pet '{d.name}' ignored: {e}")
    return out


def all_characters() -> dict[str, CharacterDef]:
    chars = {c.key: c for c in builtin_characters()}
    for c in load_png_characters() + load_petdex_characters():
        chars.setdefault(c.key, c)
    return chars


# ------------------------------------------------------------------- GUI
class _StatesFx(dict):
    """state -> images [frame][phase]; composed on first read and kept in app.fx_cache."""
    def __init__(self, app, names):
        super().__init__((e, None) for e in names)
        self.app = app

    def __getitem__(self, e):
        ck = (e, self.app.fx_sig)
        if ck not in self.app.fx_cache:
            dict.__getitem__(self, e)           # KeyError for a state the sheet does not have
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
    """Color from PhotoImage.get: tuple (r, g, b) in Tk 8.6, text "r g b" in some builds."""
    if isinstance(v, str):
        v = v.split()
    return "#%02x%02x%02x" % tuple(int(c) for c in v[:3])


def spec_to_map(spec, k: int = None):
    """Hero spec -> PixelMap with the frame in (0..16, 0..16), centered horizontally and base at y = 16.
    Sheet: 16k frame (the stage's k, the same for every state), base of the trimmed box at the frame's base,
    so a jump frame leaves the ground."""
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
        # ponytail: a big PNG is only sampled (1 every `step` px); proper scaling is left for part 3
        step = math.ceil(max(sw, sh) / 16) if max(sw, sh) > 24 else 1
        pm = {(x // step, y // step): _hex(src.get(x, y))
              for y in range(0, sh, step) for x in range(0, sw, step) if not src.transparency_get(x, y)}
        w, h = math.ceil(sw / step), math.ceil(sh / step)
    side = 16 * (k or max(1, -(-h // 16)))      # 32 px grid: 32 px frame (k = 2)
    dx, dy = (side - w) // 2, side - h
    return {(x + dx, y + dy): c for (x, y), c in pm.items()}


def spec_height(spec) -> int:
    """Final (already reduced) frame height; grid = grid height; a loose PNG stays at 16."""
    if spec[0] == "sheet":
        return -(-(spec[2][3] - spec[2][1]) // spec[3])
    return len(spec[1]) if spec[0] == "grid" else 16


def spec_k(spec) -> int:
    return max(1, -(-spec_height(spec) // 16))   # round up: the frame never cuts the hero


def render_map(pm, s: int, k: int = 1):
    """Image with origin at look_box(k) (always the same size) and how many screen px it hangs below the base.
    `s` = screen px per map pixel (hero of height H: s = hero_pixels); k = H/16 rounded (scale of the looks)."""
    box = visual.look_box(k)
    x0, y0, x1, y1 = box
    img = tk.PhotoImage(width=(x1 - x0) * s, height=(y1 - y0) * s)
    for (x, y), c in visual.crop(pm, box).items():
        img.put(c, to=((x - x0) * s, (y - y0) * s, (x - x0 + 1) * s, (y - y0 + 1) * s))
    return img, (y1 - 16 * k) * s


def steps(r: int) -> list[int]:
    """Inset of each of the r rows of a corner of radius r, from the outside in (1 px steps, no antialias)."""
    return [r - round(math.sqrt(r * r - (r - i - 0.5) ** 2)) for i in range(r)]


def _shape(cv, x0, y0, x1, y1, r, color, tags):
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    if x1 <= x0 or y1 <= y0:
        return
    ins, kw, i = steps(r), dict(fill=color, outline="", width=0, tags=tags), 0
    while i < len(ins):                     # rows with the same inset become a single rectangle
        j = i
        while j < len(ins) and ins[j] == ins[i]:
            j += 1
        cv.create_rectangle(x0 + ins[i], y0 + i, x1 - ins[i], y0 + j, **kw)
        cv.create_rectangle(x0 + ins[i], y1 - j, x1 - ins[i], y1 - i, **kw)
        i = j
    if y1 - r > y0 + r:
        cv.create_rectangle(x0, y0 + r, x1, y1 - r, **kw)


def rounded_rect(cv, x0, y0, x1, y1, r, fill, outline=None, larg=1, tag="arred", extra=()):
    """Rectangle with stepped pixel corners on Canvas `cv`, using only straight rectangles (no antialias: the key
    color #ff00fe gets no pink fringe). Tags: `tag` on everything, `tag`_f on the inner area (color change on hover), plus `extra`."""
    if outline:
        _shape(cv, x0, y0, x1, y1, r, outline, (tag, tag + "_b", *extra))
        x0, y0, x1, y1, r = x0 + larg, y0 + larg, x1 - larg, y1 - larg, max(0, r - larg)
    _shape(cv, x0, y0, x1, y1, r, fill, (tag, tag + "_f", *extra))


def png_bytes(pm, side, square=False):
    """PNG of the pixel map, trimmed and scaled by an integer to fit in `side` px -> (png, w, h).
    `square`: centers it on a side x side canvas (tray icon)."""
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

    def chunk(kind, d):
        return struct.pack(">I", len(d)) + kind + d + struct.pack(">I", zlib.crc32(kind + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b"")), w, h


def map_img(pm, side):
    """Pixel map trimmed and scaled by an integer to fit in `side` px."""
    if not pm:
        return tk.PhotoImage(width=1, height=1)
    # a PNG built here and loaded in one call (one put per pixel took ~0.4 s to open the graveyard)
    png, w, h = png_bytes(pm, side)
    return tk.PhotoImage(data=base64.b64encode(png).decode(), format="png", width=w, height=h)


def start_tray():
    """Tray icon (Windows only): the Slime as an .ico in DATA_DIR. Failed? Carry on without it (the menu has "Quit")."""
    if os.name != "nt":
        return None
    try:
        import tray
        p = DATA_DIR / "icon.ico"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        p.write_bytes(tray.ico(png_bytes(hero_idle("slime"), 32, square=True)[0], 32))
        return tray.Bandeja(str(p), APP_NAME, lambda: [_t("Show the pet"), _t("Quit")])
    except Exception:
        log("tray icon error: " + traceback.format_exc())
        return None


def hero_idle(key):
    """1st idle frame of the 1st stage straight from the heroes/<key>.py module (without cutting the PNG sheet, which takes seconds).
    None if there is no module (external/Petdex hero: the grid waits for the cutting thread)."""
    import importlib
    try:
        mod = importlib.import_module(f"heroes.{key}")
    except ImportError:
        return None
    return visual.grid_to_map(_assemble.states(mod, 0)["idle"][0], mod.PAL)


def own_hero(key):
    """Hero made here (has a heroes/<key>.py module); the others (folder in characters/, Petdex/Codex) are imported."""
    import importlib.util
    try:
        return importlib.util.find_spec(f"heroes.{key}") is not None
    except (ImportError, ValueError):
        return False


_ITEM_ARTS = {}


ELEMENT_LOOK = {"burn": "flames", "shock": "sparks", "poison": "poison_drops", "freeze": "frost"}


def pet_looks(run):
    """Item looks [(look, glow)] + one animated look per element the pet applies that does not show yet."""
    looks = [(M.ITEMS[it["key"]]["look"], M.RAR_COLOR.get(it["rar"]))
             for it in run["items"] if it["key"] in M.ITEMS]
    kinds = {l["type"] for l, _ in looks}
    st = M.stats(run)
    return looks + [({"type": t}, None) for k, t in ELEMENT_LOOK.items() if st[k] > 0 and t not in kinds]


def depth(run):
    """"Floor 3-2" in the current language."""
    return _t("Floor {n}", n=f"{run['floor']}-{run['room']}")


def _pct(v):

    return f"{round(v * 100)}%"


# Status window: (stats() field, name, format, cap or None, show even when zero)
STAT_LINES = (
    ("maxhp", "Max HP", str, None, True),
    ("atk", "Attack", str, None, True),
    ("def", "Defense", str, None, True),
    ("spd", "Speed", lambda v: f"{round(v)}", None, True),
    ("crit", "Crit", _pct, M.MAX_CRIT, True),
    ("critdmg", "Crit damage", lambda v: f"×{v:g}", None, True),
    ("dodge", "Dodge", _pct, M.MAX_DODGE, False),
    ("lifesteal", "Lifesteal", lambda v: _t("+{v} per win", v=v), None, False),
    ("double", "Double hit", _pct, M.MAX_DOUBLE, False),
    ("area", "Area attack", lambda v: _t("yes"), None, False),
    ("burn", "Ignite", _pct, M.MAX_ELEM_CHANCE, False),
    ("shock", "Shock", _pct, M.MAX_ELEM_CHANCE, False),
    ("poison", "Envenom", _pct, M.MAX_ELEM_CHANCE, False),
    ("freeze", "Freeze", _pct, M.MAX_ELEM_CHANCE, False),
    ("block", "Blocks per fight", str, M.MAX_BLOCK, False),
    ("thorns", "Thorns", _pct, M.MAX_THORNS, False),
    ("heal_room", "Heal per room", lambda v: f"+{v} HP", None, False),
    ("heal_floor", "Heal per floor", lambda v: f"+{v} HP", None, False),
    ("attack_cost", "Attack cost", lambda v: f"-{v} HP", None, False),
    ("fury", "Fury", lambda v: _t("+{v} ATK per 10%", v=v), None, False),
    ("helper", "Helper", lambda v: _t("{v} damage", v=v), None, False),
    ("grow", "Grow", lambda v: f"+1 ATK / {v} kills", None, False),
    ("gold", "Gold", lambda v: f"+{_pct(v)}", None, False),
    ("energy", "Energy", lambda v: f"+{_pct(v)}", M.MAX_ENERGY_BONUS, False),
    ("trap", "Traps", lambda v: f"×{v:g}", None, False),
    ("luck", "Luck", lambda v: f"+{_pct(v)}", M.MAX_LUCK, False),
    ("discount", "Discount", _pct, M.MAX_DISCOUNT, False),
    ("status_turns", "Status duration", lambda v: _t("+{v} turn", v=v), None, False),
)


# Reactions have no `fx`: a short fixed text each (the rules live in dungeon.combat)
REACTION_TEXT = {
    "shatter": "Extra damage equal to your ATK; removes the freeze",
    "toxic_fumes": "1 poison stack spreads to every other enemy",
    "overload": "An extra burn tick right away",
    "conductor": "Shock jumps to another enemy",
    "jolt_venom": "+1 poison stack",
    "frostbite": "Freeze lasts +1 turn",
}


def stat_lines(run, st):
    """[(field, name, value)] for the Status window: the fixed ones always, the others only when they change something."""
    st = dict(st, grow=min([M.item_fx(i["key"], i["rar"]).get("grow", 0) for i in run["items"]
                               if "grow" in M.ITEMS.get(i["key"], {}).get("fx", {})] or [0]))
    out = []
    for k, name, fmt_, cap, always in STAT_LINES:
        v = st[k]
        if always or (v != 1 if k == "trap" else v):
            out.append((k, _t(name), fmt_(v) + (f" / {fmt_(cap)}" if cap is not None else "")))
    return out


@lru_cache(maxsize=None)
def boss_grid(sprite):
    """Monster with the boss crown on top (one grid per sprite: the icon cache uses the id)."""
    foe = art.FOE_ART[sprite]
    w = max(len(foe[0]), len(art.CROWN[0]))
    pad = lambda r: r.center(w, ".")
    return tuple(pad(r) for r in art.CROWN + foe)


def item_arts():
    """Item art as a PixelMap (cached: it never changes)."""
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
        self.state.setdefault("usage_hist_since", time.time())   # no backfill: covers only from now on
        self.chars = all_characters()
        if self.state["size"] not in SIZES:
            self.state["size"] = "Medium"
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
        except tk.TclError:          # outside Windows: dark background instead of transparent
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
        self.lunge_foe = 0            # which enemy is lunging
        self.foe_xy: list = []        # on-screen position of each enemy
        self.pet_status = None        # pet status seen in the fight animation (panel only)
        self.blink_until = 0.0
        self.next_blink = time.time() + 3
        self.next_zzz = 0.0
        self.last_rest_heal = time.time()
        self.opened_at = time.time()        # opened by hand: shows for HIDE_S even without usage
        self.escondido = False
        self.tray = None                 # tray icon (run_gui turns it on; tests do not)
        self.last_save = time.time()
        self.busy_until = time.time() + 1.5
        self.respawn_at = None
        self.popup_win = None
        self.choice_win = None
        self.pending_since = None     # when the choice window started (memory only)
        self._drag = None
        self._moved = False

        self.limits = read_limits(DATA_DIR / "limits.json", time.time())   # optional statusline
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
                [_t(s) for s in ("Welcome to the Token Dungeon!",
                                 "Your Claude Code tokens become energy",
                                 "and I go down the dungeon on my own.",
                                 "Drag to move me · right-click = menu",
                                 "Double-click = status")], 10000))
        if self.demo:
            self.root.after(500, lambda: self.floater(_t("DEMO MODE"), GOLD))
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
        return self.demo or not c.unlock or c.unlock in self.meta["achievements"]   # demo: everything unlocked for testing

    def new_run(self, announce=True):
        key = self.meta.get("next_char", "slime")
        c = self.chars.get(key)
        if c is None or not self.is_unlocked(c):
            key, c = "slime", self.chars["slime"]
        # leftover energy carries over to the new run (tokens are never lost)
        energy = self.state["run"]["energy"] if self.state.get("run") else 0.0
        self.state["run"] = M.new_run(key, c.stats, self.meta["runs"] + 1, c.trait)
        self.state["run"]["energy"] = energy
        self.state["run"]["ach_start"] = list(self.meta["achievements"])
        self.respawn_at = None
        self.pet_status = None
        if announce:
            self.build()
            self.popup([_t("Run #{n} started!", n=self.run['id']), _t("{nome} enters the dungeon...", nome=_t(c.name))],
                       5000)

    # --------------------------------------------------------------- layout
    def build(self, first=False):
        px = SIZES[self.state["size"]]
        self.px = px
        self.bpx = round(px * 1.5)
        self.T = 16 * px
        bx0, by0, bx1, by1 = visual.LOOK_BOX
        left = 6 - bx0 * px                 # margin for items that stick out to the left of the frame
        self.pcx = left + self.T // 2
        # on the right: 1 big enemy or a 2x2 grid of small enemies (11 px columns + 1 px gap)
        fx0 = left + self.T + (bx1 - 16) * px
        self.foe_area = max(11 * self.bpx, 23 * px)
        self.fcx = fx0 + self.foe_area // 2
        self.foe_cols = (fx0 + 11 * px // 2, fx0 + 12 * px + 11 * px // 2)
        self.W = fx0 + self.foe_area + 10
        self.top = 52 - by0 * px            # room for what sticks out above the frame
        self.base_y = self.top + self.T
        self.below = (by1 - 16) * px        # what can hang below the base (drops)
        # session/week bars: official (statusline), estimated (~) or tokens only
        self.limit_h = 38
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
        self.foe_on = set()           # visible enemies
        self.foe_look = []

        py = self.base_y + self.below + 6
        self.panel_y = py
        rounded_rect(c, 5, py - 1, self.W - 5, py + 53 + self.limit_h, WINDOW_R, PANEL_BG, PANEL_EDGE, 2,
                              tag="painel", extra=("card:painel",))
        self.title_txt = c.create_text(14, py + 11, anchor="w", fill=TEXT, font=self.font)
        self.hp_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=HURT, font=self.font)
        self.status_y = py + 11
        self.status_txt = c.create_text(self.W - 14, py + 11, anchor="e", fill=MUTED, font=self.font_small)
        self.info_y = py + 26
        self.info_txt = c.create_text(14, self.info_y, anchor="w", fill=MUTED, font=self.font_small)   # floor
        self.info_parts = [(k, c.create_text(14, self.info_y, anchor="w", fill=INFO_COLOR[k], font=self.font_small))
                           for k in ("atk", "def", "gold")]
        self.bar_x0, self.bar_x1, self.bar_y = 14, self.W - 14, py + 38
        rounded_rect(c, self.bar_x0, self.bar_y, self.bar_x1, self.bar_y + 6, 3, BAR_BG, tag="barra_t")
        self.bar = "barra_e"            # fill tag (redrawn in update_panel)
        self.limit_rows = {}
        # fixed columns measured with the widest text: label | bar | reset
        y = py + 56
        probe = c.create_text(14, y, anchor="w", text=max((_t("Session"), _t("Week")), key=len) + "  ~100%",
                              font=self.font_small)
        lx0 = c.bbox(probe)[2] + 8
        c.itemconfigure(probe, anchor="e", text=_t("resets {h}", h=max((_t(d) for d in DAYS), key=len) + " 00:00"))
        c.coords(probe, self.W - 14, y)
        lx1 = max(lx0 + 4, c.bbox(probe)[0] - 8)
        c.delete(probe)
        for i, (key, label) in enumerate((("session", _t("Session")), ("week", _t("Week")))):
            y = py + 52 + 7 + i * 17
            back = f"lim_t_{key}"       # tags: track and fill (redrawn in update_limits)
            rounded_rect(c, lx0, y - LIM_HALF, lx1, y + LIM_HALF, 3, BAR_BG, tag=back)
            self.limit_rows[key] = (
                label,
                c.create_text(14, y, anchor="w", fill=MUTED, font=self.font_small),
                f"lim_{key}",
                c.create_text(self.W - 14, y, anchor="e", fill=MUTED, font=self.font_small),
                lx0, lx1, y, back)
        self.refresh_look()
        self.update_panel()

    def art_img(self, key, boss=False, status=None):
        """Image (cached) of a drawing from art.py; with a status, tinted in its color."""
        ck = (key, boss, status)
        if ck not in self.art:
            pal = art.BOSS_PAL if boss else art.PAL
            if status:      # tinting the palette = tinting each pixel (the dark outline stays intact)
                pal = visual.tint(pal, STATUS_COLOR[status], 0.5)
            self.art[ck] = render_grid(art.all_art()[key], pal, self.bpx if boss else self.px)
        return self.art[ck]

    def load_images(self):
        stage = self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)]
        if stage.get("sheet") and "states" not in stage and "error" not in stage:
            self.prepare_sheet(stage)          # in the thread; until then the previous look stays (or the Slime's)
            if getattr(self, "frame_maps", None) is not None:
                return
            stage = builtin_characters()[0].stages[0]
        try:
            if stage.get("error"):
                raise ValueError(stage["error"])
            # spritesheet hero: a single k per stage (same scale and same pivot in every state)
            all_ = [sp for specs in stage.get("states", {}).values() for sp in specs] or stage["frames"]
            h = max(spec_height(sp) for sp in all_)
            k = max(1, -(-h // 16))
            # pixel maps only; the images come from refresh_look (with the items on top)
            self.frame_maps = [spec_to_map(s, k) for s in stage["frames"]]
            self.blink_map = spec_to_map(stage["blink"]) if stage["blink"] else None
            self.sleep_map = spec_to_map(stage["sleep"]) if stage["sleep"] else None
        except Exception as e:
            if self.char.key == "slime":
                raise
            log(f"error loading images of '{self.char.key}': {e}; falling back to the Slime")
            self.run["char"] = "slime"
            return self.load_images()
        self.hero_k, self.hero_px = k, max(1, round(self.px * 16 / h))
        self.state_maps = {e: [spec_to_map(sp, k) for sp in specs]   # old heroes have no "states"
                            for e, specs in stage.get("states", {}).items()}
        self.fx_cache = {}         # composed states: (state, signature) -> [frame][phase]
        self.stage_title = stage["title"]

    def prepare_sheet(self, stage):
        """Decodes and cuts the sheet in a thread (pure Python only); Tk comes back on the main thread via after."""
        if stage.get("thread") is None:
            stage["thread"] = threading.Thread(target=complete_stage, args=(stage,), daemon=True)
            stage["thread"].start()
            self.root.after(0, lambda: self.floater(_t("preparing hero…"), MUTED))
            self.root.after(100, lambda: self.wait_sheet(stage))

    def wait_sheet(self, stage):
        if stage["thread"].is_alive():
            self.root.after(100, lambda: self.wait_sheet(stage))
            return
        if self.char.stages[min(self.run["stage"], len(self.char.stages) - 1)] is stage:
            self.load_images()
            self.refresh_look()

    def refresh_look(self, k: int = None, hero_pixels: int = None):
        """Recomposes the pet images with the item looks. Only when the list changes, never in the tick.
        Hero of height H: k = H/16 and hero_pixels = max(1, round(px*16/H)) (default: 16 px, k=1, px)."""
        k = k or getattr(self, "hero_k", 1)
        hero_pixels = hero_pixels or getattr(self, "hero_px", None) or self.px
        looks = pet_looks(self.run)
        arts = item_arts()
        color = STATUS_COLOR.get(self.pet_status)
        flip = self.flip
        if hasattr(self, "flip_var"):
            self.flip_var.set(flip)

        # elemental looks animate over PHASES frames; without them, a single phase (no extra images)
        phases = range(visual.PHASES if visual.has_anim(looks) else 1)

        def pmap(pm, phase):
            m = visual.compose(pm, looks, arts, phase, k)
            m = visual.tint(m, color, 0.5) if color else m
            return {(16 * k - 1 - x, y): c for (x, y), c in m.items()} if flip else m   # mirror the final map   # with a status, the pet takes its color (all phases)

        def img(m):
            im, self.below = render_map(m, hero_pixels, k)
            return im

        maps = [[pmap(pm, j) for j in phases] for pm in self.frame_maps]
        self.look_maps = [q[0] for q in maps]                    # phase 0 of each frame
        # images indexed [hero_frame][phase]; the tick only picks which one to show
        self.frames_fx = [[img(m) for m in q] for q in maps]
        self.blink_fx = [img(pmap(self.blink_map, j)) for j in phases] if self.blink_map else None
        self.sleep_fx = ([img(pmap(self.sleep_map, j)) for j in phases] if self.sleep_map
                         else (self.blink_fx or self.frames_fx[0]))
        # sheet states: [frame][phase], composed the 1st time they appear (only idle and the current one here);
        # cache keyed by (state, items, status, scale), so removing and re-adding the same status does not recompose
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
        return bool(self.state.get("flip", {}).get(self.run["char"]))

    def toggle_flip(self):
        self.state.setdefault("flip", {})[self.run["char"]] = bool(self.flip_var.get())
        self.refresh_look()
        self.save()

    def set_pet_status(self, s):
        """Pet status in the panel and in the tint; only recomposes the images when it changes (never in the tick)."""
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
        self.canvas.itemconfigure(self.info_txt, text=depth(run))
        # each field in its own tint, laid out after the previous one (gap in px)
        x = self.canvas.bbox(self.info_txt)[2]
        for (k, item), (gap, txt) in zip(self.info_parts, ((10, f"ATK {st['atk']}"), (7, f"DEF {st['def']}"),
                                                           (10, f"$ {run['gold']}"))):
            self.canvas.itemconfigure(item, text=txt)
            self.canvas.coords(item, x + gap, self.info_y)
            x = self.canvas.bbox(item)[2]
        cost = M.room_cost(run)
        self.bar_target = min(1.0, run["energy"] / cost) if cost else 0
        if getattr(self, "bar_frac", None) is None:     # 1st draw: already at the value, no sliding
            self.bar_frac = self.bar_target
        self.draw_energy(time.time())
        self.update_limits()

    def draw_energy(self, now):
        """Energy bar: the fill slides to the target (tick) and a shimmer runs along the filled part."""
        c = self.canvas
        x0, y = self.bar_x0, self.bar_y
        x1 = round(x0 + (self.bar_x1 - x0) * self.bar_frac)
        c.delete(self.bar)
        rounded_rect(c, x0, y, x1, y + 6, 3, ENERGY, tag=self.bar)
        if x1 - x0 > 14:                                 # 4 px shimmer, one pass every SHIMMER_S
            bx = x0 + 3 + (now % SHIMMER_S) / SHIMMER_S * (x1 - x0 - 10)
            c.create_rectangle(round(bx), y + 1, round(bx) + 4, y + 5, fill=ENERGY_SHIMMER, width=0, tags=self.bar)

    def update_limits(self):
        now = time.time()
        for key, (label, txt, fill, rtxt, lx0, lx1, y, back) in self.limit_rows.items():
            pct, reset, est, tok = limit_view(key, self.limits, self.state, now)
            self.canvas.itemconfigure(rtxt, text=_t("resets {h}", h=fmt_reset(reset, now)) if reset else "")
            self.canvas.delete(fill)
            if pct is None:                 # no factor: window tokens, bar = fraction of your peak
                self.canvas.itemconfigure(txt, text=f"{label}  {fmt(tok)}" if tok else f"{label}  —")
                p = peak(self.state, key, tok)
                if tok and p:
                    rounded_rect(self.canvas, lx0, y - LIM_HALF, round(lx0 + (lx1 - lx0) * tok / p), y + LIM_HALF, 3,
                                          PEAK_COLOR, tag=fill)
                continue
            self.canvas.itemconfigure(txt, text=f"{label}  {'~' if est else ''}{round(pct)}%")
            frac = max(0.0, min(1.0, pct / 100))
            rounded_rect(self.canvas, lx0, y - LIM_HALF, round(lx0 + (lx1 - lx0) * frac), y + LIM_HALF, 3, limit_color(pct),
                                  tag=fill)

    def refresh_limits(self):
        """Rereads limits.json (optional), calibrates the estimate with a new official reading and redraws."""
        now = time.time()
        self.limits = read_limits(DATA_DIR / "limits.json", now)
        calibrate(self.state, self.limits, now)
        self.update_limits()

    def build_menu(self):
        """Only the variables; the menu (pixel art, `on_menu`) and the hero grid (`show_heroes`) are built when opened."""
        self.char_var = tk.StringVar(value=self.meta.get("next_char", "slime"))
        self.size_var = tk.StringVar(value=self.state["size"])
        self.mode_var = tk.StringVar(value=self.state["mode"])
        self.lang_var = tk.StringVar(value=self.state["lang"])
        self.top_var = tk.BooleanVar(value=bool(self.state["topmost"]))
        self.usage_var = tk.BooleanVar(value=bool(self.state.get("only_when_used")))
        self.startup_var = tk.BooleanVar(value=startup_shortcut().exists())
        self.flip_var = tk.BooleanVar(value=self.flip)
        for attr in WINDOW_ATTRS:
            setattr(self, attr, None)
        self.thumb_thread = None
        self.hero_cards, self.hero_thumb_lbl, self.thumbs, self.icons, self.fonts = {}, {}, {}, {}, {}

    def fill_char_menu(self):
        """New achievement or reloaded characters: rebuilds the hero grid if it is open."""
        if self.heroes_win is not None:
            self.show_heroes()

    # ------------------------------------------------------- pixel art menu
    def pixel_box(self, x, y, closes=True):
        """Borderless window, 2 px golden frame with stepped rounded corners; returns (window, inner).
        With `closes`, closes on Esc or when it loses focus (click outside). The caller repositions it if it grows."""
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        try:
            w.attributes("-transparentcolor", TRANSPARENT)
            corte = TRANSPARENT
        except tk.TclError:
            corte = PANEL_BG                # outside Windows: corners on the dark background
        w.configure(bg=corte)
        backdrop = tk.Canvas(w, bg=corte, highlightthickness=0, bd=0)
        backdrop.place(x=0, y=0, relwidth=1, relheight=1)      # created before the inner area: stays below it

        def draw(e):
            backdrop.delete("all")
            rounded_rect(backdrop, 0, 0, e.width, e.height, WINDOW_R, PANEL_EDGE, GOLD, 2)
            rounded_rect(backdrop, 3, 3, e.width - 3, e.height - 3, WINDOW_R - 3, PANEL_BG)
        backdrop.bind("<Configure>", draw)
        inner = tk.Frame(w, bg=PANEL_BG, padx=4, pady=4)
        inner.pack(padx=5, pady=5)          # outside the corner area
        if closes:
            w.bind("<Escape>", lambda e: self.close_win(w))
            w.bind("<FocusOut>", lambda e: self.close_win(w) if e.widget is w else None)
        w.geometry(f"+{x}+{y}")
        return w, inner

    def place_win(self, w, x, y):
        """Places the window at (x, y) without leaving the screen (no room below: opens upward) and takes focus."""
        w.update_idletasks()
        vx0, vy0, vx1, vy1 = self.screen()
        ww, wh = w.winfo_width(), w.winfo_height()
        x = max(vx0, min(x, vx1 - ww))
        y = max(vy0, y if y + wh <= vy1 else y - wh)
        w.geometry(f"+{x}+{y}")
        w.focus_force()

    def screen(self):
        """Rectangle of the virtual screen (all monitors; negative x = monitor to the left of the primary)."""
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
        """Hover: lighter background and golden text; click anywhere. A card (`card_box`) changes only its inner area."""
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
        """Segmented buttons inside the menu (no submenu); the selected one is golden."""
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=_t(label), bg=PANEL_BG, fg=MUTED, font=self.font_small, width=8, anchor="w").pack(side="left")
        for value, text in options.items():
            self.chip(row, _t(text), var.get() == value, lambda v=value: (var.set(v), self.menu_do(cmd))).pack(
                side="left", padx=(0, 3))

    def chip(self, parent, text, sel=False, cmd=None):
        """Rounded pill button (Canvas): golden if selected, lighter on hover. `cv.paint(sel)` changes the state."""
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
        """Rounded card: Canvas with the background drawn (CARD_BG). Children use bg=CARD_BG and sit
        CARD_PAD from the border. With width/height, fixed size. `cv.backdrop(color)` changes the inner color (hover)."""
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
        """Text width in px (fake tkinter in the tests: 6 px per letter)."""
        tkf = getattr(tk, "font", None)
        if tkf is None:
            return 6 * len(text)
        if font not in self.fonts:
            self.fonts[font] = tkf.Font(root=self.root, font=font)
        return self.fonts[font].measure(text)

    def shorten(self, text, font, larg):
        """The text if it fits in `lw` px; otherwise cut with "…" (show the full text with `tooltip`)."""
        if self.text_width(text, font) <= larg:
            return text
        while text and self.text_width(text + "…", font) > larg:
            text = text[:-1]
        return text.rstrip() + "…"

    def tooltip(self, wd, text):
        """Pixel bubble with the full text while the mouse is over `wd` (for what was shortened)."""
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
        """Rounded progress bar (Canvas); `cv.set(frac, color)` redraws the fill."""
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
        self.menu_thumb = map_img(self.look_maps[0], 36)     # keep a reference: tk does not hold the image by itself
        tk.Label(head, image=self.menu_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 6))
        tk.Label(head, text=f"{_t(self.char.name)}  ·  {_t(self.stage_title)}", bg=PANEL_BG, fg=GOLD,
                 font=self.font, anchor="w").pack(fill="x")
        tk.Label(head, text=f"{depth(run)}    ♥ {run['hp']}/{st['maxhp']}",
                 bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        self.menu_sep(f)
        for icon, text, cmd in (("shooting_star", "Profile", self.show_profile),
                                ("grimoire", "Status", self.show_stats),
                                ("tombstone", "Graveyard", self.show_graveyard),
                                ("campfire", "Journal", self.show_journal),
                                ("coroa", "Achievements", self.show_achievements),
                                ("potion", "Items", self.show_items),
                                ("bone_sword", "Heroes…", self.show_heroes)):
            self.menu_row(f, icon, _t(text), cmd)
        self.menu_sep(f)
        self.menu_chips(f, "Size", {n: n for n in SIZES}, self.size_var, self.change_size)
        self.menu_chips(f, "Mode", MODES, self.mode_var, self.change_mode)
        self.menu_chips(f, "Language", i18n.LANGS, self.lang_var, self.change_lang)
        options = [("Always on top", self.top_var, self.toggle_top),
                  ("Flip hero", self.flip_var, self.toggle_flip),
                  ("Show only when in use", self.usage_var, self.toggle_usage)]
        if os.name == "nt":
            options.append(("Start with Windows", self.startup_var, self.toggle_startup))
        for text, var, fn in options:
            self.menu_row(f, "box_ok" if var.get() else "box", _t(text),
                          lambda v=var, fn=fn: (v.set(not v.get()), fn()))
        self.menu_sep(f)
        self.menu_row(f, "little_skull", _t("Give up the run"), self.give_up, fg=HURT)
        self.menu_sep(f)
        self.menu_row(f, "chest", _t("Open characters folder"), self.open_chars)
        self.menu_row(f, "whirlwind", _t("Reload characters"), self.reload_chars)
        self.menu_row(f, "stairs", _t("Quit"), self.quit)
        self.place_win(w, e.x_root, e.y_root)

    def menu_do(self, cmd):
        self.close_win(self.menu_win)
        cmd()

    # ------------------------------------------------------- hero grid
    def hero_thumb(self, c, ok, side=64):
        """Idle of the 1st stage, scaled up (locked: silhouette). None while the sheet is still being cut in the thread."""
        stage = c.stages[0]
        ck = (id(stage), ok) if side == 64 else (id(stage), ok, side)
        if ck not in self.thumbs:
            pm = hero_idle(c.key) if not stage.get("frames") else spec_to_map(stage["frames"][0])
            if pm is None:
                return None
            self.thumbs[ck] = map_img(pm if ok else {p: "#0b0b14" for p in pm}, side)
        return self.thumbs[ck]

    def cut_sheets(self):
        """Cuts in a thread the sheets the grid does not have yet; then only swaps the thumbnails."""
        pend = [c.stages[0] for c in self.chars.values()
                if not c.stages[0].get("frames") and "error" not in c.stages[0]
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
        """Pixel window (closes the previous one of the same kind) with a golden title and an x; returns (window, inner)."""
        self.close_win(getattr(self, attr))
        w, f = self.pixel_box(self.root.winfo_x(), self.root.winfo_y())
        setattr(self, attr, w)
        top = tk.Frame(f, bg=PANEL_BG)
        top.pack(fill="x")
        name = tk.Label(top, text=title, bg=PANEL_BG, fg=GOLD, font=self.font)
        name.pack(side="left")
        w.title_label = name
        self.make_draggable(w, attr, top, name)
        shutdown = tk.Label(top, text=" x ", bg=PANEL_BG, fg=MUTED, font=self.font)
        shutdown.pack(side="right")
        self.hover((shutdown,), shutdown, MUTED, lambda: self.close_win(w))
        return w, f

    def make_draggable(self, w, attr, *straps):
        """Drags the window by its title bar (`straps`) and remembers the position in state["windows"][attr]."""
        takes = {}

        def squeeze(e):
            takes["d"] = (e.x_root - w.winfo_x(), e.y_root - w.winfo_y())

        def move(e):
            if "d" in takes:
                x, y = e.x_root - takes["d"][0], e.y_root - takes["d"][1]
                w.geometry(f"+{x}+{y}")
                self.state.setdefault("windows", {})[attr] = [x, y]
        for a in straps:
            a.configure(cursor="fleur")
            a.bind("<Button-1>", squeeze)
            a.bind("<B1-Motion>", move)
        w.progress_bar = straps[0]          # for the tests

    def beside(self, w):
        """At the remembered position (dragged before), if it is still on screen; otherwise beside the pet:
        on the left, or on the right if it does not fit."""
        w.update_idletasks()
        attr = next((a for a in WINDOW_ATTRS if getattr(self, a) is w), None)
        pos = (self.state.get("windows") or {}).get(attr)
        vx0, vy0, vx1, vy1 = self.screen()
        if pos and vx0 <= pos[0] < vx1 and vy0 <= pos[1] < vy1:   # ponytail: rectangle of the virtual screen, not per monitor
            self.place_win(w, pos[0], min(pos[1], max(vy0, vy1 - w.winfo_height())))
            return
        x, y = self.root.winfo_x(), self.root.winfo_y()
        left = x - w.winfo_width() - 6
        self.place_win(w, left if left >= vx0 else x + self.W + 6, y)

    def icon(self, grid, s=2, pal=None, glow=None, dark=False, dim=False, side=None):
        """Art grid at scale s (cached): rarity glow, silhouette (locked) or faded (consumed).
        With `side`, the scale is the largest integer that fits a `side` px square (icons of the same size)."""
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
        w, f = self.window("heroes_win", _t("Next run's hero"))
        sections = [("Heroes", [(k, c) for k, c in self.chars.items() if own_hero(k)]),
                  ("Community", [(k, c) for k, c in self.chars.items() if not own_hero(k)])]
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
            info = tk.Label(card, text=M.fx_text(c.trait) if c.trait else _t("no trait"), bg=CARD_BG,
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
            pick = None             # locked: nothing clickable
            tk.Label(card, text=_t(M.ACHIEVEMENTS[c.unlock]), image=self.menu_icon("padlock"), compound="left",
                     bg=CARD_BG, fg=MUTED, font=self.font_small, wraplength=HERO_CARD_W - 24 - 2 * CARD_PAD).pack()
        self.hero_cards[key] = pick
        return card

    # -------------------------------------------------------------- events
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
            self.new_run()      # run has not started yet: switch right away
        else:
            self.popup([_t("{nome} joins the next run.", nome=name)], 4000)

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
        """Switches the language: redraws the HUD and reopens the windows that were open (the menu closes)."""
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
        self.state["only_when_used"] = bool(self.usage_var.get())
        self.opened_at = time.time()            # just turned on: do not hide right away
        self.save()

    def toggle_startup(self):
        try:
            startup_shortcut(create=bool(self.startup_var.get()))
        except OSError as e:
            log(f"startup shortcut error: {e}")
        self.startup_var.set(startup_shortcut().exists())

    def adjust_visibility(self, now):
        """"Show only when in use": hides after HIDE_S without tokens (never in the middle of a room or with
        a choice open) and shows again on the 1st token. While hidden the game goes on; nothing is lost."""
        stopped = now - max(self.state["last_fed"], self.opened_at) > HIDE_S
        esconder = bool(self.state.get("only_when_used")) and stopped and now >= self.busy_until and not self.run["pending"]
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
        self.run["pending"] = None             # the offer dies with the run
        self.close_choice()
        ev = {"lines": []}
        M.die(self.run, self.meta, ev, "Gave up", "gave_up")
        self.log_run("Gave up", True)
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
            log(f"could not open the folder: {e}")

    def reload_chars(self):
        self.chars = all_characters()
        if self.run["char"] not in self.chars:
            self.run["char"] = "slime"
        self.fill_char_menu()
        self.build()
        if self.run["dead"]:
            self.show_tomb()
        self.floater(_t("{n} characters", n=len(self.chars)), MUTED)


    def show(self):
        """From the tray: shows the pet (even with "Show only when in use", HIDE_S counts again) and brings it to the front."""
        self.opened_at = time.time()
        self.adjust_visibility(self.opened_at)
        self.root.lift()

    def listen_tray(self):
        """Tray clicks arrive through a queue (its thread must not touch Tk). 0 = show, 1 = quit."""
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
        log("error: " + "".join(traceback.format_exception(*exc)))

    # ------------------------------------------------------- tokens/energy
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
            log("error reading tokens: " + traceback.format_exc())
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

    # -------------------------------------------------------------- rooms
    def play_room(self):
        ev = M.enter_room(self.run, self.meta, self.rng, self.char.stage_floors,
                          mode=self.state["mode"])
        steps = []
        t = 0

        def at(ms, fn):
            steps.append((ms, fn))

        self._last_kind = [ev["kind"]]               # for the test only
        kind = ev["kind"]
        foes = ev.get("foes") or []
        name_color = {"boss": HURT, "monster": TEXT, "horde": TEXT, "mimic": HURT, "stairs": CYAN}.get(kind, GOLD)

        def new_room():
            self.set_pet_status(None)                  # pet status does not carry over from one room to the next
            self.update_panel()
        at(0, new_room)
        if foes:
            at(0, lambda: self.show_foes(foes))
        else:
            at(0, lambda: self.show_foe(ev.get("sprite"), ev.get("boss", False)))
        at(0, lambda: self.floater(_t(ev["name"]), name_color, x=self.fcx, life=22, top=True))
        if ev.get("item_heal"):                        # heal_room / heal_floor from items
            at(250, lambda: self.floater(f"+{ev['item_heal']} ♥", GOOD))
        t = 500

        if kind in ("monster", "boss", "mimic", "horde"):
            hits = ev["hits"]
            # who has died after each step (counting the whole list, even steps that are not shown)
            hp = [f["hp_max"] for f in foes]
            dead_until, status_until, s = [], [], None
            for h in hits:
                if h["target"] != "pet" and not h["skip"]:
                    hp[h["target"]] -= h["dmg"]
                if h["target"] == "pet" and h["status"] and not h["skip"]:
                    s = h["status"]                    # latest pet status so far (also covers skipped steps)
                dead_until.append([i for i, v in enumerate(hp) if v <= 0])
                status_until.append(s)
            idx = list(range(len(hits)))
            if len(idx) > 12:                          # long fights: the first 11 steps and the last one
                idx = idx[:11] + [idx[-1]]
            for k in idx:
                at(t, lambda h=hits[k], dead=dead_until[k], s=status_until[k]: self.anim_hit(h, dead, s))
                t += 380
            if ev["won"]:
                at(t, lambda: self.hide_foe(burst=True))
                t += 300
                at(t, lambda: self.floater(f"+{ev.get('gold', 0)} $", GOLD, x=self.fcx))
                t += 450
            elif ev.get("tie"):
                at(t, lambda: (self.floater(_t("draw"), MUTED, x=self.fcx), self.hide_foe()))
                t += 450
            at(t, lambda: self.set_pet_status(None))  # the pet status ends with the fight
        elif kind == "trap":
            if ev.get("dodged"):
                at(t, lambda: self.floater(_t("dodged!"), CYAN))
            elif ev["dmg"] == 0:                       # the shield absorbed everything
                at(t, lambda: self.floater(_t("blocked!"), CYAN))
            else:
                at(t, lambda: (self._set("hop", [-4, -8, -4, 0]),
                               self.floater(f"-{ev['dmg']}", HURT)))
            t += 600
        elif kind == "fountain":
            at(t, lambda: self.floater(f"+{ev.get('heal', 0)} ♥", GOOD))
            t += 600
        elif kind == "secret":                         # like a chest, with a gold flash
            at(t, lambda: self.burst(self.fcx, self.base_y - self.T // 2))
            t += 400
        elif kind == "idol":                           # like the altar: the pet flinches when it pays
            if ev.get("lines") and not self.run["pending"]:
                at(t, lambda: self._set("hop", [-4, -8, -4, 0]))
                t += 400
        elif kind == "campfire":                       # like the fountain: a warm glow
            at(t, lambda: self.floater("♥", GOOD))
            t += 400
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
        if kind == "boss" and not ev["died"] and not ev.get("tie"):
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
        """Animation of the lines and of the resolved offer (item taken or consumed); returns the new t."""
        new_lines = {f"New synergy: {M.SYNERGIES[s['key']]['name']}!" for s in ev.get("synergies", []) if s["new"]}
        for line in ev["lines"]:
            at(t, lambda line=line: self.floater(_t(line), GOLD if line in new_lines else TEXT, life=24))
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
            elif "heal" in c:                          # healed 0: HP was already full
                at(t, lambda: self.floater(_t("HP already full"), MUTED))
            else:
                at(t, lambda: self.floater(_t("+{n} shield", n=c['shield']), CYAN))
            t += 600
        return t

    def finish_pending(self, ev):
        """Closes the panel and animates the resolved offer (choice, expired window or switch to auto)."""
        self.close_choice()
        steps = []
        t = self._offer_steps(ev, lambda ms, fn: steps.append((ms, fn)), 0)
        if ev.get("unlocks"):
            steps.append((t, lambda: self.announce_unlocks(ev["unlocks"])))
        if ev.get("pending") and self.run["pending"]:       # an idol win chains an offer
            steps.append((t, self.show_choice))
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
        """One fight step: floaters, lunge, status tint and removing whoever died so far."""
        tgt, who = h["target"], h["who"]

        def fx(i):
            return self.foe_xy[i][0] if i in self.foe_on else self.fcx
        x = None if tgt == "pet" else fx(tgt)
        txt = f"-{h['dmg']}" + ("!" if h["crit"] else "") + (" x2" if h.get("double") else "")
        if h["skip"]:
            self.floater(_t("lost a turn"), MUTED, x=None if who == "pet" else fx(who), life=10)
        elif h["dot"]:
            self.floater(str(h["dmg"]), STATUS_COLOR.get(h["status"], HURT), x=x, life=8)
        elif h["dodge"]:
            self.floater(_t("dodged!"), CYAN, life=10)
        elif h.get("locked"):
            self.foe_attack(who)
            self.floater(_t("blocked!"), CYAN, life=10)
        elif h.get("thorns"):                           # thorns: the damage goes back to the attacker, no lunge
            self.floater(f"-{h['dmg']}", GOOD, x=x, life=10)
        elif who == "helper":                           # helper: the number pops from above the pet, no lunge
            self.floater(txt, GOOD, life=10)
        elif who == "pet":
            self.lunge = [5, 10, 5, 0]
            self.floater(txt, GOLD if h["crit"] else TEXT, x=x, life=10)
            if h["status"] and tgt in self.foe_on:        # elemental attack: flash in the element's color
                self.burst(x, self.foe_xy[tgt][1] - 4 * self.px, colors=(STATUS_COLOR[h["status"]], "#ffffff"))
                # ponytail: the tint stays until the enemy dies (the GUI does not know when the status ends)
                self.draw_foe(tgt, h["status"])
        else:
            self.foe_attack(who)
            if h["dmg"]:
                self.floater(txt, GOLD if h["crit"] else HURT, life=10)
            else:
                self.floater(_t("blocked!"), CYAN, life=10)
        self.set_pet_status(status)
        for i in dead:
            self.hide_foe(i, burst=True)

    def foe_slots(self, n):
        """(center, base) of each enemy: 1 in the middle; 2-4 in a 2x2 grid (with 3, the 3rd is on top, in the middle)."""
        if n <= 1:
            return [(self.fcx, self.base_y)]
        up = self.base_y - 9 * self.px              # monster art is at most 8 px tall
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
        """Lunge of enemy i (the previous one goes back to its place if it was still mid-lunge)."""
        j = self.lunge_foe
        if j != i and j < len(self.foe_xy):
            self.canvas.coords(self.foe_items[j][0], *self.foe_xy[j])
        self.lunge_foe = i
        self.foe_lunge = [-5, -10, -5, 0]

    def hide_foe(self, i=None, burst=False):
        """Hides one enemy (or all of them); with burst, blows up whoever was still on screen."""
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
        self.floater(_t("EVOLVED!"), GOLD, life=22)
        self.popup([_t("{a} evolved into {b}!", a=_t(old), b=_t(self.stage_title)), _t("+4 max HP, +1 ATK")], 5000)

    def log_run(self, killer, gave_up):
        rec = M.run_record(self.run, killer, gave_up, self.state["mode"],
                           self.run.get("ach_start", self.meta["achievements"]),
                           killer_kind=self.meta["graveyard"][-1].get("kind", ""))
        append_run_record(rec, self.demo)

    def on_death(self):
        g = self.meta["graveyard"][-1]
        self.log_run(g["killer"], False)
        self.save()
        if getattr(self, "states_fx", None):       # sheet hero: "failed" frames before the tombstone
            self.state_tmp = ("failed", time.time() + 1.2)
            self.root.after(1200, lambda: self.run["dead"] and self.show_tomb())
        else:
            self.show_tomb()
        self.burst(self.pcx, self.base_y - self.T // 3, colors=("#8a94a8", "#d7dde9", HURT))
        best = self.meta["best"]
        self.popup([_t("{nome} died on floor {n}", nome=_t(self.stage_title), n=f"{g['floor']}-{g['room']}"),
                    _t("Defeated by: {k}", k=_t(g['killer'])),
                    _t("Monsters beaten: {k}   Gold: {o}", k=g['kills'], o=g['gold']),
                    _t("Best: floor {n}", n=f"{best['floor']}-{best['room']}"),
                    _t("A new run starts in a moment...")], RESPAWN_S * 1000)
        self.respawn_at = time.time() + RESPAWN_S

    def show_tomb(self):
        self.canvas.itemconfigure(self.sprite, image=self.art_img("tombstone"))
        self.canvas.coords(self.sprite, self.pcx, self.base_y)
        self.hide_foe()

    def announce_unlocks(self, keys):
        lines = [_t("ACHIEVEMENT!")]
        for k in keys:
            lines.append(_t(M.ACHIEVEMENTS[k]))
            gains = self.unlock_rewards(k)
            if gains:
                lines.append(_t("  unlocks: {x}", x=", ".join(gains)))
        self.fill_char_menu()
        self.popup(lines, 9000)

    def unlock_rewards(self, ach):
        items = [_t(it["name"]) for it in M.ITEMS.values() if it.get("req") == ach]
        chars = [_t("hero {nome}", nome=_t(c.name)) for c in self.chars.values() if c.unlock == ach]
        return items + chars

    # ------------------------------------------------------------- animation
    def floater(self, text, color=TEXT, life=16, x=None, top=False):
        """Rising text. Picks a free spot (not covering live floaters or the panel);
        with top=True (monster name) it always goes on top."""
        c = self.canvas
        bx = (self.pcx if x is None else x) + self.rng.randint(-10, 10)
        by = self.base_y - self.T + 10
        tags = ("name_tag",) if top else ()
        t = c.create_text(bx, by, text=text, fill=color, font=self.font_small, tags=tags)
        alive = [c.bbox(f[0][0]) for f in self.floaters]
        options = []
        for dy in (0, -16, 16, -32, 32, -48):
            for dx in (0, -34, 34):
                c.coords(t, bx + dx, by + dy)
                x0, y0, x1, y1 = c.bbox(t)
                shift = max(0, 4 - (x0 - 5)) - max(0, (x1 + 5) - (self.W - 4))
                box = (x0 + shift - 5, y0 - 2, x1 + shift + 5, y1 + 2)
                if box[1] >= 0 and box[3] < self.panel_y:      # never on top of the panel
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
        r = f"flt{self.n_floater}"      # tag of the rounded bubble (several rectangles)
        rounded_rect(c, *box, CARD_R, PANEL_BG, PANEL_EDGE, 1, tag=r, extra=tags)
        c.tag_raise(t)
        c.tag_raise("name_tag")
        self.floaters.append([(r, t), life])

    def burst(self, x, y, colors=(GOLD, "#ffffff", GOOD)):
        for i in range(16):
            a = i * math.pi / 8
            r = self.canvas.create_rectangle(x - 3, y - 3, x + 3, y + 3,
                                             fill=self.rng.choice(colors), outline="")
            self.particles.append([r, math.cos(a) * 6, math.sin(a) * 6, 12])

    def current_state(self, now, resting):
        """Sheet state to show (None for heroes without states): choice > fight > death > rest > idle;
        waving/jumping last for the scheduled time."""
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
                self.close_choice()                # the pending offer is gone (new run, gave up...)
            if run["dead"]:
                if self.respawn_at and now >= self.respawn_at:
                    self.new_run()
            elif now >= self.busy_until and run["pending"]:
                # never enters a room with an open choice; tokens keep filling the energy
                if self.pending_since is None:
                    self.pending_since = now       # also when the app opens with a pending offer in the save
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
                phase = int(now * 1000 / FX_MS)       # effects clock, separate from the hero
                state = self.current_state(now, idle > REST_AFTER_S and not busy)
                if state:
                    img = self.state_frame(state, now)
                    bob = 0
                    if state == "idle" and self.blink_fx is not None:   # grid hero still blinks
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

            d = self.bar_target - self.bar_frac             # energy bar slides to the target
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
            log("animation error: " + traceback.format_exc())
        self.root.after(100, self.tick)

    # --------------------------------------------------------------- windows
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

    def choice_title(self, p):
        """Name shown after "Waiting for a choice:" for any kind of pending."""
        kind = p.get("kind", "offer")
        if kind == "idol":
            return _t("Cracked Idol")
        if kind == "campfire":
            return _t("Campfire")
        return _t(M.ITEMS[p["key"]]["name"])

    def show_choice(self):
        """Choice panel beside the pet (only one at a time): offer, idol or campfire."""
        p = self.run["pending"]
        if self.choice_win is not None or not p:
            return
        kind = p.get("kind", "offer")
        w, f = self.pixel_box(0, 0, closes=False)   # the choice does not close by itself when it loses focus
        row = tk.Frame(f, bg=PANEL_BG)
        if kind == "idol":
            self.choice_img = self.art_img("idol")
            tk.Label(f, image=self.choice_img, bg=PANEL_BG).pack(pady=(4, 2))
            tk.Label(f, text=_t("Cracked Idol"), bg=PANEL_BG, fg=GOLD, font=self.font).pack(padx=6)
            tk.Label(f, text=_t("Pay {n} HP: {p}% epic item, or a curse", n=min(p["cost"], self.run["hp"] - 1), p=round(M.IDOL_WIN * 100)),
                     justify="center", bg=PANEL_BG, fg=MUTED, font=self.font_small, wraplength=CHOICE_TEXT_W).pack(padx=6)
            row.pack(pady=4)
            for c in M.idol_choices(self.run):
                self.chip(row, _t(c.capitalize()), False, lambda c=c: self.choose(c)).pack(side="left", padx=4)
        elif kind == "campfire":
            self.choice_img = self.art_img("tale_" + M.TALES[p["line"]]["who"])
            tk.Label(f, image=self.choice_img, bg=PANEL_BG).pack(pady=(4, 2))
            tk.Label(f, text=_t(M.TALES[p["line"]]["text"]), justify="center", bg=PANEL_BG, fg=TEXT,
                     font=self.font_small, wraplength=CHOICE_TEXT_W).pack(padx=6)
            row.pack(pady=4)
            for c in p["boons"]:
                full = M.boon_text(c, self.run)
                chip = self.chip(row, self.shorten(full, self.font_small, CHOICE_TEXT_W - 12), False,
                                 lambda c=c: self.choose(c))
                chip.pack(pady=2)
                self.tooltip(chip, full)
        else:
            key, rar = p["key"], p["rar"]
            it = M.ITEMS[key]
            self.choice_img = self.art_img(key)       # keep a reference: tk does not hold the image by itself
            tk.Label(f, image=self.choice_img, bg=PANEL_BG).pack(pady=(4, 2))
            tk.Label(f, text=f"{_t(it['name'])}  ·  {_t(M.RAR_NAMES[rar])}", bg=PANEL_BG,
                     fg=M.RAR_COLOR.get(rar) or TEXT, font=self.font).pack(padx=6)
            cf = M.consume_fx(key, rar)
            cons = f"+{cf['heal']} ♥" if "heal" in cf else _t("+{n} shield", n=cf['shield'])
            tk.Label(f, text=_t("Take: {x}", x=M.fx_text(M.item_fx(key, rar))) + "\n" + _t("Consume: {x}", x=cons),
                     justify="left", bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(padx=6)
            row.pack(pady=4)
            for label, choice in (("Take", "take"), ("Consume", "consume")):
                self.chip(row, _t(label), False, lambda c=choice: self.choose(c)).pack(side="left", padx=4)
        self.choice_cv = self.progress_bar(f, CHOICE_BAR_W, 6, 1.0, ENERGY)
        self.choice_cv.pack(pady=(2, 2))
        self.choice_wait = tk.Label(f, text="", bg=PANEL_BG, fg=MUTED, font=self.font_small)
        self.choice_wait.pack(pady=(0, 2))
        w.update_idletasks()
        x = self.root.winfo_x() - w.winfo_width() - 6
        if x < 0:
            x = self.root.winfo_x() + self.W + 6
        # aligned at the bottom with the pet, so it does not cover the popup (which grows from the top)
        y = max(0, self.root.winfo_y() + self.H - w.winfo_height())
        w.geometry(f"+{x}+{y}")
        self.choice_win = w
        self.update_choice()

    def update_choice(self):
        """Only updates the timer bar and the text of the waiting rooms."""
        if self.choice_win is None:
            return
        since = time.time() if self.pending_since is None else self.pending_since
        left = max(0.0, 1 - (time.time() - since) / M.CHOICE_WINDOW_S)
        self.choice_cv.set(left)
        rooms = int(self.run["energy"] // M.room_cost(self.run))
        wait = "" if rooms < 1 else (_t("1 room waiting") if rooms == 1 else _t("{n} rooms waiting", n=rooms))

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
        self.stats_thumb = map_img(self.look_maps[0], 56)    # keep a reference: tk does not hold the image by itself
        tk.Label(head, image=self.stats_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 8))
        col = tk.Frame(head, bg=PANEL_BG)
        col.pack(side="left", fill="x")
        tk.Label(col, text=f"{_t(self.char.name)}  ·  {_t(self.stage_title)}", bg=PANEL_BG, fg=GOLD, font=self.font,
                 anchor="w").pack(fill="x")
        tk.Label(col, text=f"{depth(run)}   ·   " + _t("Mode {m}", m=_t(MODES[self.state['mode']])),
                 bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        self.progress_bar(col, 170, 8, run["hp"] / st["maxhp"], HURT).pack(anchor="w", pady=3)
        shield = "   ·   " + _t("shield {n}", n=run['shield']) if run["shield"] > 0 else ""
        bosses = _t("{n} boss" if run['bosses'] == 1 else "{n} bosses", n=run['bosses'])
        tk.Label(col, text=f"♥ {run['hp']}/{st['maxhp']}{shield}   ·   $ {run['gold']}   ·   {run['kills']} kills"
                 f"   ·   {bosses}", bg=PANEL_BG, fg=TEXT, font=self.font_small,
                 anchor="w").pack(fill="x")
        if run.get("trait"):
            tk.Label(f, text=_t("Trait: {x}", x=M.fx_text(run['trait'])), bg=PANEL_BG, fg=MUTED, font=self.font_small,
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
        tooltip = _t("hover over an item") if run["items"] or run["consumed"] else ""
        info = tk.Label(f, text=tooltip, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w", justify="left",
                        wraplength=330)
        for title, lst, s, dim in ((_t("Items ({n})", n=len(run['items'])), run["items"], 3, False),
                                      (_t("Consumed ({n})", n=len(run['consumed'])), run["consumed"], 2, True)):
            if not lst and dim:
                continue
            tk.Label(f, text=title, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
            box = tk.Frame(f, bg=PANEL_BG)
            box.pack(fill="x", pady=(2, 4))
            if not lst:
                tk.Label(box, text=_t("none yet"), bg=PANEL_BG, fg=MUTED, font=self.font_small).pack(anchor="w")
            for n, it in enumerate(i for i in lst if i["key"] in M.ITEMS):
                rar = it.get("rar", "common")
                side, cols = s * 12, 10 if s == 3 else 14     # fixed cell: wide items (hats) fit without covering the neighbor
                lbl = tk.Label(box, image=self.icon(art.ITEM_ART[it["key"]], s, glow=M.RAR_COLOR.get(rar), dim=dim,
                                                    side=side), bg=PANEL_BG, width=side + 2, height=side + 2)
                lbl.grid(row=n // cols, column=n % cols)
                txt = (f"{_t(M.ITEMS[it['key']]['name'])} ({_t(M.RAR_NAMES.get(rar, rar))})"
                       + ("" if dim else f": {M.fx_text(M.item_fx(it['key'], rar))}"))
                lbl.bind("<Enter>", lambda e, t=txt: info.configure(text=t, fg=TEXT))
                lbl.bind("<Leave>", lambda e: info.configure(text=tooltip, fg=MUTED))
        info.pack(fill="x")
        if run.get("synergies"):
            tk.Label(f, text=_t("Synergies ({n})", n=len(run["synergies"])) + ": "
                     + ", ".join(_t(M.SYNERGIES[k]["name"]) for k in run["synergies"] if k in M.SYNERGIES),
                     bg=PANEL_BG, fg=GOLD, font=self.font_small, anchor="w", justify="left", wraplength=330).pack(fill="x")
        self.menu_sep(f)
        best = meta["best"]
        footer = [_t("Stored energy: {n} room(s)", n=int(run['energy'] // M.room_cost(run))),
                  _t("Best: floor {n}", n=f"{best['floor']}-{best['room']}") + f"   ·   Runs: {meta['runs']}",
                  _t("Tokens today: {n}", n=fmt(self.state['daily'].get(date.today().isoformat(), 0)))
                  + f"   ·   Total: {fmt(self.state['tokens_total'])}"]
        if run["pending"]:
            footer.append(_t("Waiting for a choice: {x}", x=self.choice_title(run["pending"])))
        if self.demo:
            footer.append(_t("(demo mode)"))
        tk.Label(f, text="\n".join(footer), bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w",
                 justify="left").pack(fill="x")
        self.beside(w)

    def killer_icon(self, d):
        """Icon of the killer: monster, crowned boss, mimic, status, trap or giving up."""
        k = d.get("killer", "")
        boss = next((s for s, n in M.BOSS_NAMES.items() if n == k), None)
        if boss:
            return self.icon(boss_grid(boss), 2, pal=art.BOSS_PAL)
        spr = "mimic" if k == "Mimic" else next((m[0] for m in M.MONSTERS if m[1] == k), None)
        if spr:
            return self.icon(art.FOE_ART[spr], 2)
        grid = {"Burn": art.STAT_ART["burn"], "Poison": art.STAT_ART["poison"],
                "Trap": art.ROOM_ART["trap"], "Gave up": art.ROOM_ART["stairs"]}.get(k)
        return self.icon(grid or art.ROOM_ART["tombstone"], 2)

    def tombstone(self, cv, y, d):
        """One graveyard tombstone drawn on the canvas starting at y."""
        L, f, fs = GRAVE_TOMB, self.font, self.font_small
        rounded_rect(cv, 1, y + 1, GRAVE_W - 1, y + L - 3, CARD_R, CARD_BG, PANEL_EDGE, 2, tag="cartao",
                              extra=(f"card:{y}",))
        c = self.chars.get(d.get("char"))
        img = (c and self.hero_thumb(c, True, 40)) or self.icon(art.ROOM_ART["tombstone"], 4)
        cv.create_image(30, y + L // 2 - 1, image=img)
        cv.create_text(60, y + 15, anchor="w", text=f"#{d.get('run', '?')}  {_t(c.name) if c else d.get('char', '?')}",
                       fill=GOLD, font=f)
        cv.create_text(GRAVE_W - 12, y + 15, anchor="e", text=_t("floor {n}", n=f"{d['floor']}-{d['room']}"), fill=TEXT,
                       font=f)
        kimg = self.killer_icon(d)
        cv.create_image(60, y + 37, anchor="w", image=kimg)
        who = _t("gave up") if d.get("kind") == "gave_up" else _t("killed by {k}", k=_t(d.get('killer', '?')))
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
            cv.create_text(60, y + 64, anchor="w", text=_t("no items"), fill=MUTED, font=fs)

    def show_graveyard(self):
        g, meta = self.meta["graveyard"], self.meta
        w, f = self.window("grave_win", _t("Graveyard"))
        best = meta["best"]
        summary = _t("{n} runs   ·   best: floor {a}", n=meta['runs'], a=f"{best['floor']}-{best['room']}")
        deaths = Counter(d.get("killer") for d in g if d.get("kind") != "gave_up")
        if deaths:
            summary += _t("   ·   top killer: {k}", k=_t(deaths.most_common(1)[0][0]))
        tk.Label(f, text=summary, bg=PANEL_BG, fg=MUTED, font=self.font_small, anchor="w").pack(fill="x")
        if not g:
            tk.Label(f, image=self.icon(art.ROOM_ART["tombstone"], 4), text=_t("No tombstones yet...\nthe hero stands strong!"),
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

    def show_journal(self):
        """Campfire tales heard so far (meta["journal"]); unheard ones are a silhouette and "???"."""
        heard, fs = self.meta.get("journal", {}), self.font_small
        w, f = self.window("journal_win", _t("Journal"))
        tk.Label(f, text=_t("{n}/{total}", n=len(set(heard) & set(M.TALES)), total=len(M.TALES)), bg=PANEL_BG,
                 fg=MUTED, font=fs, anchor="w").pack(fill="x")
        row = tk.Frame(f, bg=PANEL_BG)
        row.pack(pady=(4, 0))
        cv = tk.Canvas(row, width=JOURNAL_W + 6, height=JOURNAL_H, bg=PANEL_BG, highlightthickness=0,
                       yscrollincrement=40)
        cv.pack(side="left")
        y = 0
        for key, tale in M.TALES.items():
            h = heard.get(key)
            x, ty = 3, y + 10
            cv.create_image(x + 30, y + 30, image=self.icon(art.TALE_ART[tale["who"]], 3, dark=not h, side=44))
            if h:
                lines = [(_t(tale["who"].capitalize()), GOLD), (_t(tale["text"]), TEXT),
                         (_t("Run #{run}  ·  Floor {floor}", run=h["run"], floor=h["floor"]), MUTED)]
                for txt, color in lines:
                    t = cv.create_text(x + 62, ty, anchor="nw", text=txt, fill=color, font=fs, width=JOURNAL_W - 74)
                    ty = cv.bbox(t)[3] + 3
            else:
                cv.create_text(x + 62, y + 30, anchor="w", text="???", fill=MUTED, font=self.font)
                ty = y + 50
            alto = max(ty - y + 7, 60)
            rounded_rect(cv, x, y, x + JOURNAL_W, y + alto, CARD_R, CARD_BG, GOLD if h else PANEL_EDGE, 2,
                         tag="cartao", extra=(f"card:{key}",))
            cv.tag_lower("cartao")
            y += alto + 6
        vis = min(y, JOURNAL_H)
        cv.configure(height=vis, scrollregion=(0, 0, JOURNAL_W + 6, y))
        if y > vis:
            self.scrollbar(row, w, cv, vis)
        self.beside(w)

    def scrollbar(self, parent, w, cv, vis):
        """Pixel scrollbar (the native one ignores colors) beside Canvas `cv` (with scrollregion):
        dragging the thumb scrolls along, clicking the track centers the thumb there, mouse wheel and arrow keys.
        The thumb hides when everything fits (e.g. after a filter). Returns the track."""
        tr = tk.Canvas(parent, width=8, height=vis, bg=PANEL_BG, highlightthickness=0, cursor="hand2")
        tr.pack(side="left", padx=(4, 0))
        rounded_rect(tr, 0, 0, 8, vis, 4, BAR_BG, tag="trilha")
        view = {"a": 0.0, "b": 1.0, "pega": None, "cor": GOLD}   # visible fraction, where the thumb was grabbed, color

        def shows(a, b):
            view["a"], view["b"] = float(a), float(b)
            tr.delete("finger")
            if view["b"] - view["a"] < 0.999:
                rounded_rect(tr, 0, round(view["a"] * vis), 8, round(view["b"] * vis), 4, view["cor"],
                                      tag="finger")

        def vai(y):
            tam = view["b"] - view["a"]
            cv.yview_moveto(max(0.0, min(1.0 - tam, (y - view["pega"]) / vis)))

        def squeeze(e):
            y0, y1 = view["a"] * vis, view["b"] * vis
            view["pega"] = e.y - y0 if y0 <= e.y <= y1 else (y1 - y0) / 2   # outside the thumb: jump there
            vai(e.y)

        def releases(e):
            view["pega"] = None
        cv.configure(yscrollcommand=shows)
        tr.bind("<Button-1>", squeeze)
        tr.bind("<B1-Motion>", lambda e: view["pega"] is not None and vai(e.y))
        tr.bind("<ButtonRelease-1>", releases)
        def color(c):
            view["cor"] = c
            tr.itemconfigure("finger", fill=c)
        tr.tag_bind("finger", "<Enter>", lambda e: color(GOLD_HOVER))
        tr.tag_bind("finger", "<Leave>", lambda e: color(GOLD))
        w.bind("<MouseWheel>", lambda e: cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        w.bind("<Up>", lambda e: cv.yview_scroll(-1, "units"))
        w.bind("<Down>", lambda e: cv.yview_scroll(1, "units"))
        return tr

    def item_unlocked(self, key):
        """Same rule as the drop roll (M.unlocked_items); in the demo everything is unlocked, like the heroes."""
        req = M.ITEMS[key].get("req")
        return self.demo or not req or req in self.meta["achievements"]

    def item_card(self, cv, x, y, key):
        """Card of one item on the canvas starting at (x, y); returns its height. Locked: silhouette, padlock, no values."""
        it, ok, fs = M.ITEMS[key], self.item_unlocked(key), self.font_small
        top = next((M.RAR_COLOR[r] for r in reversed(it["rarities"]) if M.RAR_COLOR[r]), None)
        cv.create_image(x + 26, y + 26, image=self.icon(art.ITEM_ART[key], 4, glow=ok and top or None, dark=not ok))
        cv.create_text(x + 54, y + 16, anchor="w", text=_t(it["name"]), fill=TEXT if ok else MUTED, font=self.font)
        eat = _t("heal" if "heal" in it["consume"] else "shield")
        cv.create_text(x + 54, y + 33, anchor="w", font=fs, fill=MUTED,
                       text=_t(M.item_family(key)) + ("  ·  " + _t("consume: {x}", x=eat) if ok else ""))
        ty, larg = y + 54, ITEMS_CARD_W - 20
        if not ok:
            cv.create_image(x + 10, ty + 7, anchor="w", image=self.menu_icon("padlock"))
            t = cv.create_text(x + 26, ty, anchor="nw", text=_t(M.ACHIEVEMENTS.get(it["req"], it["req"])), fill=MUTED,
                               font=fs, width=larg - 16)
            ty = cv.bbox(t)[3] + 4
        for r in [] if not ok else it["rarities"]:
            c = M.consume_fx(key, r)
            eat = _t("heal {n}", n=c['heal']) if "heal" in c else _t("shield {n}", n=c.get('shield', 0))
            t = cv.create_text(x + 10, ty, anchor="nw", fill=M.RAR_COLOR[r] or TEXT, font=fs, width=larg,
                               text=f"{_t(M.RAR_NAMES[r])}: {M.fx_text(M.item_fx(key, r))}  ·  {eat}")
            ty = cv.bbox(t)[3] + 3
        alto = max(ty - y + 6, 60)
        rounded_rect(cv, x, y, x + ITEMS_CARD_W, y + alto, CARD_R, CARD_BG, PANEL_EDGE, 2, tag="cartao",
                              extra=(f"card:{x}_{y}",))
        cv.tag_lower("cartao")
        return alto

    def synergy_card(self, cv, x, y, key):
        """Card of one synergy on the canvas at (x, y); returns its height. Discovered: icons, effect, counters.
        Locked: silhouette plus the hint. Secret and not discovered: only "???" (no icons: they would give it away)."""
        sy, fs = M.SYNERGIES[key], self.font_small
        seen = self.meta.get("synergies", {}).get(key)
        hidden = sy["secret"] and not seen
        if sy["kind"] == "pair":
            grids = [art.ITEM_ART[i] for i in sy["req"]["items"]]
        elif sy["kind"] == "reaction":
            grids = [art.STAT_ART[s] for s in sy["req"]["status"]]
        else:
            fields = next(f for n, f in M.FAMILIES if n == sy["req"]["family"])
            grids = [art.STAT_ART[fields[0]]]
        larg, ty = ITEMS_CARD_W - 20, y + 54
        if hidden:
            cv.create_image(x + 26, y + 26, image=self.menu_icon("padlock"))
            cv.create_text(x + 54, y + 26, anchor="w", text="???", fill=MUTED, font=self.font)
        else:
            for n, g in enumerate(grids):
                cv.create_image(x + 20 + n * 34, y + 26, image=self.icon(g, 2, dark=not seen, side=30))
            nx = x + 10 + len(grids) * 34 + 6
            full = _t(sy["name"])
            short = self.shorten(full, self.font, x + ITEMS_CARD_W - 8 - nx)
            name_item = cv.create_text(nx, y + 18, anchor="w", text=short, fill=TEXT if seen else MUTED, font=self.font)
            if short != full:           # shortened: full name on hover (tooltip binds like a widget)
                self.tooltip(types.SimpleNamespace(
                    bind=lambda ev, f, add=None, it=name_item: cv.tag_bind(it, ev, f, add)), full)
            cv.create_text(nx, y + 35, anchor="w", font=fs, fill=MUTED,
                           text=_t({"set": "Set", "pair": "Pair", "reaction": "Reaction"}[sy["kind"]]))
            if seen:
                fx = M.fx_text(sy["fx"]) if sy["fx"] else _t(REACTION_TEXT[key])
                lines = [fx, _t("Active in {n} runs", n=seen["runs"]), _t("Discovered in run #{n}", n=seen["first_run"])]
            else:
                lines = [_t(sy["hint"])]
                cv.create_image(x + 10, ty + 7, anchor="w", image=self.menu_icon("padlock"))
            for i, line in enumerate(lines):
                t = cv.create_text(x + (26 if not seen else 10), ty, anchor="nw", text=line,
                                   fill=GOLD if seen and i == 0 else MUTED, font=fs, width=larg - (0 if seen else 16))
                ty = cv.bbox(t)[3] + 3
        alto = max(ty - y + 6, 60)
        rounded_rect(cv, x, y, x + ITEMS_CARD_W, y + alto, CARD_R, CARD_BG, GOLD if seen else PANEL_EDGE, 2, tag="cartao",
                     extra=(f"card:{key}",))
        cv.tag_lower("cartao")
        return alto

    def show_items(self):
        free = [k for k in M.ITEMS if self.item_unlocked(k)]
        w, f = self.window("items_win", _t("Items  ·  {a} of {b} unlocked", a=len(free), b=len(M.ITEMS)))
        self.items_filter = getattr(self, "items_filter", "all")
        self.items_tab = getattr(self, "items_tab", "items")
        tabs = tk.Frame(f, bg=PANEL_BG)
        tabs.pack(fill="x", pady=(4, 0))
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

        def draw(filter_by, tab=None):
            self.items_filter, self.items_tab = filter_by, tab or self.items_tab
            for name, b in buttons.items():
                b.paint(name == filter_by)
            for name, b in tab_buttons.items():
                b.paint(name == self.items_tab)
            cv.delete("all")
            syn = self.items_tab == "synergies"
            found = self.meta.get("synergies", {})
            w.title_label.configure(text=_t("Synergies  ·  {a} of {b} discovered", a=len(set(found) & set(M.SYNERGIES)),
                                            b=len(M.SYNERGIES)) if syn else
                                    _t("Items  ·  {a} of {b} unlocked", a=len(free), b=len(M.ITEMS)))
            if syn:
                keys = [k for k in M.SYNERGIES if filter_by == "all" or (k in found) == (filter_by == "unlocked")]
                card = self.synergy_card
            else:
                keys = [k for k in M.ITEMS if filter_by == "all" or (k in free) == (filter_by == "unlocked")]
                card = self.item_card
            y = 0
            for i in range(0, len(keys), ITEMS_COLS):
                y += 6 + max(card(cv, c * (ITEMS_CARD_W + 6), y, k)
                             for c, k in enumerate(keys[i:i + ITEMS_COLS]))
            if not keys:
                cv.create_text(10, 20, anchor="w", text=_t("No synergies here." if syn else "No items here."), fill=MUTED, font=self.font)
            cv.configure(scrollregion=(0, 0, ITEMS_COLS * (ITEMS_CARD_W + 6), max(y, ITEMS_H)))
            cv.yview_moveto(0)
        for name, text in (("all", "All"), ("unlocked", "Unlocked"), ("locked", "Locked")):
            b = self.chip(chips, _t(text), False, lambda n=name: draw(n))
            b.pack(side="left", padx=(0, 3))
            buttons[name] = b
        tab_buttons = {}
        for name, text in (("items", "Items"), ("synergies", "Synergies")):
            b = self.chip(tabs, _t(text), False, lambda n=name: draw(self.items_filter, n))
            b.pack(side="left", padx=(0, 3))
            tab_buttons[name] = b
        draw(self.items_filter)
        self.beside(w)

    def show_achievements(self):
        have = set(self.meta["achievements"]) & set(M.ACHIEVEMENTS)
        w, f = self.window("ach_win", _t("Achievements  ·  {a} of {b}", a=len(have), b=len(M.ACHIEVEMENTS)))
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
                tk.Label(line, text=_t("unlocks"), bg=CARD_BG, fg=MUTED, font=self.font_small).pack(side="left", padx=2)
                for im in rewards[:3]:
                    tk.Label(line, image=im, bg=CARD_BG).pack(side="left", padx=1)
                if len(rewards) > 3:
                    tk.Label(line, text=f"+{len(rewards) - 3}", bg=CARD_BG, fg=MUTED, font=self.font_small).pack(side="left")
        self.beside(w)

    def show_profile(self):
        """Profile (only data that already exists: state, meta, usage_hist): hero, tamer level, medals,
        numbers, last 7 days chart, limits and shortcuts. All new profile texts live here."""
        run, meta, state, now = self.run, self.meta, self.state, time.time()
        st, fs, L = M.stats(run), self.font_small, PROFILE_W
        w, f = self.window("profile_win", _t("Profile"))

        def progress_bar(parent, frac, color, larg=L, alto=6):
            return self.progress_bar(parent, larg, alto, frac, color)

        def label(parent, txt, fg=MUTED, font=fs):
            tk.Label(parent, text=txt, bg=PANEL_BG, fg=fg, font=font, anchor="w").pack(fill="x")

        def top(left, dir_, fg_dir=TEXT, font=fs):
            fr = tk.Frame(f, bg=PANEL_BG)
            fr.pack(fill="x")
            tk.Label(fr, text=left, bg=PANEL_BG, fg=GOLD if font == self.font else MUTED, font=font).pack(side="left")
            tk.Label(fr, text=dir_, bg=PANEL_BG, fg=fg_dir, font=fs).pack(side="right")
        # header: hero, run, HP
        head = tk.Frame(f, bg=PANEL_BG)
        head.pack(fill="x", pady=(4, 0))
        self.profile_thumb = map_img(self.look_maps[0], 48)    # keep a reference: tk does not hold the image by itself
        tk.Label(head, image=self.profile_thumb, bg=PANEL_BG).pack(side="left", padx=(0, 8))
        col = tk.Frame(head, bg=PANEL_BG)
        col.pack(side="left", fill="x")
        label(col, f"{_t(self.char.name)}  ·  {_t(self.stage_title)}", GOLD, self.font)
        label(col, f"Run #{run['id']}   ·   {depth(run)}   ·   ♥ {run['hp']}/{st['maxhp']}")
        progress_bar(col, run["hp"] / st["maxhp"], HURT, L - 56).pack(anchor="w", pady=(3, 0))
        # tamer level (lifetime energy: same unit as the chart)
        n, frac, missing = level(state["xp_total"])
        self.menu_sep(f)
        top(_t("Tamer  Lv {n}", n=n), f"{round(frac * 100)}%", GOLD, self.font)
        progress_bar(f, frac, GOLD).pack(anchor="w", pady=2)
        label(f, _t("~{x} energy left to Lv {n}", x=fmt(missing), n=n + 1))
        # medals
        have = set(meta["achievements"]) & set(M.ACHIEVEMENTS)
        self.menu_sep(f)
        top(_t("Achievements"), f"{len(have)} / {len(M.ACHIEVEMENTS)}")
        med = tk.Frame(f, bg=PANEL_BG)
        med.pack(anchor="w", pady=2)
        tooltip = _t("hover over a medal")
        info = tk.Label(f, text=tooltip, bg=PANEL_BG, fg=MUTED, font=fs, anchor="w", justify="left", wraplength=L)
        for i, (k, desc) in enumerate(M.ACHIEVEMENTS.items()):
            lb = tk.Label(med, image=self.icon(art.ACH_ART[k], dark=k not in have, side=PROFILE_MEDAL - 2),
                          bg=PANEL_BG, width=PROFILE_MEDAL, height=PROFILE_MEDAL, bd=0, padx=0, pady=0)
            lb.grid(row=i // PROFILE_MEDALS, column=i % PROFILE_MEDALS)
            txt = _t(desc) + ("" if k in have else _t("  (locked)"))
            lb.bind("<Enter>", lambda e, t=txt: info.configure(text=t, fg=TEXT))
            lb.bind("<Leave>", lambda e: info.configure(text=tooltip, fg=MUTED))
        info.pack(fill="x")
        label(f, _t("Synergies {n}/{total}", n=len(set(meta.get("synergies", {})) & set(M.SYNERGIES)), total=len(M.SYNERGIES)))
        # number cards
        own = [c for k, c in self.chars.items() if own_hero(k)]
        best, dias = meta["best"], usage_per_day(state, now)
        cards = (("TODAY", fmt(dias[-1][1]), "energy"), ("STREAK", str(streak_days(state, now)), "days in a row"),
                   ("LIFETIME", fmt(state["xp_total"]), "energy"), ("RUNS", str(meta["runs"]), "played"),
                   ("BEST", f"{best['floor']}-{best['room']}", "floor-room"),
                   ("HEROES", f"{sum(self.is_unlocked(c) for c in own)}/{len(own)}",
                    _t("{n} boss" if meta.get('bosses', 0) == 1 else "{n} bosses", n=meta.get('bosses', 0))))
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
        # last 7 days chart (energy per day, from usage_hist)
        self.menu_sep(f)
        top(_t("Last 7 days  (energy)"), fmt(sum(v for _, v in dias)), GOLD)
        alto, larger = 58, max(v for _, v in dias) or 1
        cv = tk.Canvas(f, width=L, height=alto + 16, bg=PANEL_BG, highlightthickness=0)
        cv.pack(pady=(2, 0))
        bw = L // 7
        for i, (d, v) in enumerate(dias):
            x0, today_ = i * bw + 4, i == len(dias) - 1
            h = max(2, round(alto * v / larger / 2) * 2)      # 2 px steps: pixel look
            cv.create_rectangle(x0, alto - h, x0 + bw - 8, alto, width=0,
                                fill=(GOLD if today_ else PROFILE_BAR) if v else BAR_BG)
            cv.create_text(x0 + (bw - 8) / 2, alto + 9, text=_t(DAYS[d.weekday()]), fill=GOLD if today_ else MUTED, font=fs)
        # limits (same as in the panel)
        self.menu_sep(f)
        label(f, _t("Limits"))
        for key, name in (("session", "Session"), ("week", "Week")):
            pct, reset, est, tok = limit_view(key, self.limits, state, now)
            if pct is not None:
                val = f"{'~' if est else ''}{round(pct)}%"
            else:                       # no official % and no factor: tokens and how much of your peak that is
                p = peak(state, key, tok)
                val = _t("{n} · {p}% of your peak", n=fmt(tok), p=round(100 * tok / p)) if tok and p else "—"
            top(f"{_t(name)}  {val}", _t("resets {h}", h=fmt_reset(reset, now)) if reset else "", MUTED)
            if pct is not None:
                progress_bar(f, pct / 100, limit_color(pct)).pack(anchor="w", pady=(1, 3))
            else:
                progress_bar(f, tok / p if tok and p else 0, PEAK_COLOR).pack(anchor="w", pady=(1, 3))
        # footer: last use and shortcuts
        self.menu_sep(f)
        ult = last_use(state)
        label(f, _t("last use: {x}", x=fmt_ago(now - ult) if ult else _t("none yet"))
               + ("   ·   " + _t("(demo mode)") if self.demo else ""))
        bot = tk.Frame(f, bg=PANEL_BG)
        bot.pack(fill="x", pady=(4, 0))
        for txt, fn in (("Achievements", self.show_achievements), ("Graveyard", self.show_graveyard),
                        ("Items", self.show_items)):
            self.chip(bot, _t(txt), False, fn).pack(side="left", padx=(0, 4))
        self.beside(w)

    def save(self):
        try:
            self.reader.export()
            save_state(self.state_path, self.state)
            self.last_save = time.time()
        except OSError as e:
            log(f"error saving: {e}")


def startup_shortcut(create: bool | None = None) -> Path:
    """Shortcut in the Windows Startup folder that opens the pet without a console (pythonw). Only the user turns it on, from the menu.
    create=True writes it, False deletes it, None only returns the path."""
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
    """1st run after the rename: copies the progress from ~/.tokenpet without deleting the old one."""
    if new.exists() or not old.is_dir():
        return False
    new.mkdir(parents=True)
    for name in ("state.json", "state-demo.json"):
        if (old / name).is_file():
            shutil.copy2(old / name, new / name)
    log(f"progress copied from {old}")
    return True


def run_gui(args):
    global tk
    migrate_old_data()
    for name in legacy.migrate_all(DATA_DIR):
        log(f"{name} converted to the English keys (copy in {name}.pt.bak)")
    import tkinter as _tk
    import tkinter.font  # noqa: F401  (tk.font: measure text to shorten it with "…")
    tk = _tk
    lock = acquire_lock("demo.lock" if args.demo else "tokenlike.lock")
    if lock is None:
        print("Agent Tokenlike is already open.")
        return
    app = PetApp(args)
    app.tray = start_tray()
    app.listen_tray()
    app.root.mainloop()


def main(argv=None):
    p = argparse.ArgumentParser(description="Agent Tokenlike - Token Dungeon")
    p.add_argument("--demo", action="store_true", help="fake tokens for testing (separate progress)")
    p.add_argument("--import-history", action="store_true",
                   help="on first use, starts with the energy from your Claude Code history")
    p.add_argument("--reset", action="store_true", help="erases all progress and starts from scratch")
    args = p.parse_args(argv)
    try:
        run_gui(args)
    except Exception:
        log("fatal error: " + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
