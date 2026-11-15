#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statusline OPCIONAL do Claude Code para o Agent Tokenlike.

O Claude Code roda este script e manda um JSON pelo stdin. Daqui só se aproveita
`rate_limits` (porcentagem oficial da sessão de 5h e da semana, com o horário de reset),
gravado em %USERPROFILE%\\.tokenlike\\limites.json para o pet desenhar as barras.
Nada mais do JSON (pasta, modelo, transcript...) é guardado. Sem rede.

Você liga no seu ~/.claude/settings.json (o pet nunca mexe nisso):
  "statusLine": {"type": "command", "command": "python \"C:/caminho/para/statusline.py\""}
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
    """resets_at vem em segundos (número) ou ISO-8601; devolve segundos UTC."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def extract(payload: dict) -> dict | None:
    """Só os limites. None se o Claude Code ainda não mandou (antes da 1ª resposta)."""
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
            pass                      # a statusline nunca pode quebrar o Claude Code
    stdout.write(format_line(lim) + "\n")


if __name__ == "__main__":
    # no Windows o pipe usaria cp1252; o Claude Code fala UTF-8
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    main()
