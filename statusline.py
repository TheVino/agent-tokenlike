#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPTIONAL Claude Code statusline for Agent Tokenlike.

Claude Code runs this script and sends a JSON on stdin. Only `rate_limits` is used
(official percentage of the 5h session and of the week, with the reset time),
written to %USERPROFILE%\\.tokenlike\\limits.json so the pet can draw the bars.
Nothing else from the JSON (folder, model, transcript...) is kept. No network.

You turn it on in your ~/.claude/settings.json (the pet never touches it):
  "statusLine": {"type": "command", "command": "python \"C:/path/to/statusline.py\""}
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".tokenlike"
WINDOW_ATTRS = ("five_hour", "seven_day")


def _epoch(v) -> float | None:
    """resets_at comes in seconds (number) or ISO-8601; returns UTC seconds."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def extract(payload: dict) -> dict | None:
    """Only the limits. None if Claude Code has not sent them yet (before the 1st response)."""
    rl = payload.get("rate_limits") if isinstance(payload, dict) else None
    if not isinstance(rl, dict):
        return None
    out = {}
    for k in WINDOW_ATTRS:
        w = rl.get(k)
        if not isinstance(w, dict):
            continue
        pct = w.get("used_percentage")
        if not isinstance(pct, (int, float)) or isinstance(pct, bool):
            continue
        out[k] = {"used_percentage": pct, "resets_at": _epoch(w.get("resets_at"))}
    if not out:
        return None
    out["updated"] = time.time()
    return out


def format_line(lim: dict | None) -> str:
    if not lim:
        return ""
    parts = []
    for k, name in (("five_hour", "sessão"), ("seven_day", "semana")):
        if k in lim:
            parts.append(f"{name} {round(lim[k]['used_percentage'])}%")
    return " · ".join(parts)


def main(stdin=sys.stdin, stdout=sys.stdout, data_dir: Path = DATA_DIR) -> None:
    try:
        lim = extract(json.loads(stdin.read() or "{}"))
    except ValueError:
        lim = None
    if lim:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            tmp = data_dir / "limites.json.tmp"
            tmp.write_text(json.dumps(lim), encoding="utf-8")
            os.replace(tmp, data_dir / "limites.json")
        except OSError:
            pass                      # the statusline must never break Claude Code
    stdout.write(format_line(lim) + "\n")


if __name__ == "__main__":
    # on Windows the pipe would use cp1252; Claude Code speaks UTF-8
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    main()
