"""Balance metrics from the run lines (dungeon.run_record format)."""
import sys, json, html, statistics, collections, itertools, base64, struct, zlib, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dungeon as M
import art, visual

# Balance targets: (minimum, maximum); None = no limit.
TARGETS = {"passed_boss1": (0.35, 0.45), "p90": (13, 16), "max": (None, 50)}


def check_targets(res: dict) -> dict:
    """For each target, True if the number in `res` is inside the range (None without runs)."""
    if res.get("n") == 0:
        return {k: None for k in TARGETS}
    out = {}
    for k, (lo, hi) in TARGETS.items():
        v = res.get(k)
        out[k] = v is not None and (lo is None or v >= lo) and (hi is None or v <= hi)
    return out


def load_real(folder: Path, all_versions: bool = False):
    """Reads <folder>/runs.jsonl (never runs-demo.jsonl). Returns (lines, info)."""
    info = {"other_versions": 0, "ignored": 0, "gave_ups": 0, "modes": {}}
    arq = Path(folder) / "runs.jsonl"
    if not arq.exists():
        return [], info
    recs = []
    for txt in arq.read_text(encoding="utf-8", errors="replace").splitlines():
        if not txt.strip():
            continue
        try:
            rec = json.loads(txt)
        except ValueError:
            rec = None
        if not _line_ok(rec):
            info["ignored"] += 1
            continue
        if rec.get("version") != M.BALANCE_VERSION:
            info["other_versions"] += 1
            if not all_versions:
                continue
        recs.append(rec)
        if rec.get("gave_up"):
            info["gave_ups"] += 1
        mode = rec.get("mode", "?")
        info["modes"][mode] = info["modes"].get(mode, 0) + 1
    return recs, info


def valid(recs) -> list:
    """Removes the give-ups (run cut short, not finished)."""
    return [r for r in recs if not r.get("gave_up")]


def _p90(xs):
    # same method as simulate.py, but never above the maximum on small samples
    return min(statistics.quantiles(xs, n=10)[-1], max(xs)) if len(xs) >= 2 else xs[0]


def _line_ok(rec) -> bool:
    """Line with an integer floor, a text char and items {text key, floor None or from 1 up to the run's floor}."""
    def whole(x):
        return isinstance(x, int) and not isinstance(x, bool)
    if not isinstance(rec, dict) or not whole(rec.get("floor")) or not isinstance(rec.get("char"), str):
        return False
    its, cons = rec.get("items"), rec.get("consumed", [])  # consumed is missing in old lines
    if not isinstance(its, list) or not isinstance(cons, list):
        return False
    return all(isinstance(i, dict) and isinstance(i.get("key"), str) and "floor" in i
               and (i["floor"] is None or (whole(i["floor"]) and 1 <= i["floor"] <= rec["floor"]))
               for i in its + cons)


def summary(recs) -> dict:
    recs = valid(recs)
    if not recs:
        return {"n": 0, "median": None, "p90": None, "max": None, "passed_boss1": None, "items_median": None}
    floors = [r["floor"] for r in recs]
    return {"n": len(recs), "median": statistics.median(floors), "p90": _p90(floors), "max": max(floors),
            "passed_boss1": sum(f > M.BOSS_EVERY for f in floors) / len(floors),
            "items_median": statistics.median(len(r["items"]) for r in recs)}


def expected(recs) -> dict:
    """For each floor f: mean of the remaining floors (final − f) of the runs alive on floor f."""
    floors = [r["floor"] for r in valid(recs)]
    return {f: statistics.mean(x - f for x in floors if x >= f) for f in range(1, max(floors, default=0) + 1)}


def _taken(rec) -> dict:
    """Key -> floor where it was taken (the first one), ignoring items without floor (old saves)."""
    out = {}
    for i in rec["items"]:
        if i.get("floor") is not None:
            out[i["key"]] = min(out.get(i["key"], i["floor"]), i["floor"])
    return out


def per_item(recs) -> dict:
    recs = valid(recs)
    esp = expected(recs)
    taken_ones = [(r, _taken(r)) for r in recs]
    out = {}
    for key in M.ITEMS:
        rs = [(r["floor"], p[key]) for r, p in taken_ones if key in p]
        # resolved offers: each take or consume counts once, per mode
        offers = collections.defaultdict(lambda: [0, 0])  # mode -> [taken, consumed]
        for r in recs:
            mode = r.get("mode", "?")
            offers[mode][0] += sum(i["key"] == key and i.get("floor") is not None for i in r["items"])
            offers[mode][1] += sum(i["key"] == key and i.get("floor") is not None for i in r.get("consumed", []))
        per_mode = {m: c / (p + c) for m, (p, c) in offers.items() if p + c}
        tp, tc = sum(p for p, _ in offers.values()), sum(c for _, c in offers.values())
        d = {"n": len(rs), "taken": None, "taken_floor": None, "lasted": None, "vs_expected": None,
             "final_floor": None, "quick_deaths": None,
             "consumed_pct": tc / (tp + tc) if tp + tc else None, "consumed_by_mode": per_mode}
        if rs:
            d.update(taken=len(rs) / len(recs), taken_floor=statistics.median(f for _, f in rs),
                     lasted=statistics.mean(fin - f for fin, f in rs),
                     vs_expected=statistics.mean(fin - f - esp[f] for fin, f in rs),
                     final_floor=statistics.mean(fin for fin, _ in rs),
                     quick_deaths=sum(fin - f <= 2 for fin, f in rs) / len(rs))
        out[key] = d
    # vs_mean: vs_expected minus the (n-weighted) mean of the items, because taking an item already helps
    com = [d for d in out.values() if d["n"]]
    mean = sum(d["n"] * d["vs_expected"] for d in com) / sum(d["n"] for d in com) if com else 0
    for d in out.values():
        d["vs_mean"] = None if d["vs_expected"] is None else d["vs_expected"] - mean
    return out


def pairs(recs, minimum: int = 30) -> dict:
    """Item pairs with at least `minimum` runs together, counted from the floor of the 2nd item."""
    recs = valid(recs)
    esp = expected(recs)
    vs = {k: d["vs_expected"] for k, d in per_item(recs).items()}
    groups = collections.defaultdict(list)
    # ponytail: O(items² per run), fine for thousands of runs with ~5 items each
    for r in recs:
        for (a, fa), (b, fb) in itertools.combinations(sorted(_taken(r).items()), 2):
            f2 = max(fa, fb)
            groups[a, b].append(r["floor"] - f2 - esp[f2])
    lst = []
    for (a, b), xs in groups.items():
        if len(xs) >= minimum and a in vs and b in vs:  # an item that left the game is skipped
            m = statistics.mean(xs)
            lst.append({"a": a, "b": b, "n": len(xs), "vs_expected": m, "gain": m - max(vs[a], vs[b])})
    lst.sort(key=lambda p: p["gain"], reverse=True)
    return {"best_items": lst[:10], "worst_items": lst[10:][::-1][:5]}  # the worst ones do not repeat the best ones


def deaths(recs) -> dict:
    recs = valid(recs)
    per_floor = collections.Counter(r["floor"] for r in recs)
    killers = collections.Counter(r["killer"] for r in recs if r.get("killer") not in (None, "—"))
    per_kind = collections.Counter(r.get("killer_kind") or "?" for r in recs)   # old line: "?"
    return {"per_floor": dict(sorted(per_floor.items())), "killers": killers.most_common(6),
            "per_kind": dict(per_kind.most_common())}


def heroes(recs) -> dict:
    groups = collections.defaultdict(list)
    for r in valid(recs):
        groups[r["char"]].append(r["floor"])
    return {c: {"n": len(fs), "median": statistics.median(fs), "p90": _p90(fs)} for c, fs in groups.items()}


def synergies(recs) -> dict:
    """Per synergy key: runs that had it and the median final floor with / without it."""
    v = valid(recs)
    out = {}
    for k in M.SYNERGIES:
        w = [r["floor"] for r in v if k in (r.get("synergies") or [])]
        wo = [r["floor"] for r in v if k not in (r.get("synergies") or [])]
        out[k] = {"n": len(w), "median_with": statistics.median(w) if w else None,
                  "median_without": statistics.median(wo) if wo else None}
    return out


def rooms(recs) -> dict:
    """Share of each room kind among the rooms played, and the idol's accept (per idol room) and win (per accept) rates."""
    tot = collections.Counter()
    acc = win = 0
    for r in valid(recs):
        tot.update({k: v for k, v in (r.get("rooms") or {}).items() if isinstance(v, int)})
        c = r.get("counters") or {}
        acc += c.get("idol_accept", 0)
        win += c.get("idol_win", 0)
    n = sum(tot.values())
    return {"share": {k: v / n for k, v in tot.most_common()},
            "idol_accept": acc / tot["idol"] if tot["idol"] else None, "idol_win": win / acc if acc else None}


# ---------- collection, page and command line ----------

def collect(n_sim: int, real_folder: Path, all_versions: bool, seed: int = 1) -> dict:
    """Runs the calibration (slime only, same as simulate.py), the simulation with all heroes and reads the real runs."""
    from datetime import datetime
    import simulate as S
    hero_keys = S.all_heroes()
    sim_recs = S.simulate(n_sim, achs=list(M.ACHIEVEMENTS), seed=seed, heroes=hero_keys)[0]
    no_recs = S.simulate(n_sim, achs=(), seed=seed, heroes=hero_keys)[0]
    real_recs, info = load_real(real_folder, all_versions)
    pi_s, pi_r = per_item(sim_recs), per_item(real_recs)
    cal = {"without_achievements": summary(S.simulate(n_sim, achs=(), seed=seed)[0]),
           "with_achievements": summary(S.simulate(n_sim, achs=list(M.ACHIEVEMENTS), seed=seed)[0])}
    real = summary(real_recs)
    return {
        "version": M.BALANCE_VERSION, "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sim": summary(sim_recs), "sim_without_achievements": summary(no_recs), "real": real, "calibration": cal,
        "real_info": info,
        "targets": {**{k: check_targets(v) for k, v in cal.items()}, "real": check_targets(real)},
        "items": {k: {"name": M.ITEMS[k]["name"], "rarities": M.ITEMS[k].get("rarities"),
                      "sim": pi_s[k], "real": pi_r[k]} for k in M.ITEMS},
        "pairs": {"sim": pairs(sim_recs), "real": pairs(real_recs)},
        "deaths": {"sim": deaths(sim_recs), "real": deaths(real_recs)},
        "heroes": {"sim": heroes(sim_recs), "real": heroes(real_recs)},
        "synergies": {"sim": synergies(sim_recs), "real": synergies(real_recs)},
        "rooms": {"sim": rooms(sim_recs), "real": rooms(real_recs)},
    }


CSS = """
:root{--bg:#1d1b2b;--cx:#25223a;--zb:#2b2844;--bd:#3d3866;--tx:#f2f0ff;--mu:#a9a4d6;--ok:#7ee081;--bad:#ff6b81;
--gold:#ffd23f;--purple:#7a73d6;--purple2:#b48cff}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--tx);font:14px/1.5 "Segoe UI",system-ui,sans-serif;padding:24px 16px;max-width:1200px;margin:auto}
td{font-family:Consolas,"Cascadia Mono","Courier New",monospace;font-size:13px}
header{border:2px solid var(--purple);background:linear-gradient(135deg,#2a2545,#1d1b2b);padding:16px 20px;border-radius:6px;
box-shadow:4px 4px 0 #0b0b14}
h1{font-size:22px;margin:0 0 4px;color:var(--gold);letter-spacing:.04em;text-shadow:2px 2px 0 #6a3fb5}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--gold);margin:32px 0 10px;padding-left:10px;
border-left:4px solid var(--purple2)}
.mu{color:var(--mu)}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--gold)}.weak{opacity:.5}
.scroll{overflow-x:auto;border:1px solid var(--bd);border-radius:6px}
table{border-collapse:collapse;width:100%;background:var(--cx)}
th,td{padding:6px 10px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--bd)}
tbody tr:nth-child(even){background:var(--zb)}tbody tr:hover{background:#363159}
th:first-child,td:first-child{text-align:left}
th{color:var(--mu);font-weight:600;font-size:12px;background:#221f36}
th.ord{cursor:pointer}th.ord:hover{color:var(--gold)}
.cols{display:flex;gap:16px;flex-wrap:wrap}.cols>div{flex:1 1 320px;min-width:0}
.card{background:var(--cx);border:1px solid var(--bd);border-radius:6px;padding:12px 14px}
.source{color:var(--purple2);font-weight:600;text-transform:uppercase;letter-spacing:.06em;font-size:12px;margin:0 0 6px}
.badge{display:inline-block;padding:0 6px;border-radius:9px;font-size:11px;font-weight:700;margin-left:4px}
.badge.ok{background:#1f3d2a;border:1px solid #3d7a4f}.badge.bad{background:#4a1f2a;border:1px solid #8f3a4d}
.ic{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;margin-right:8px;
background:#14121f;border:2px solid #4b4680;border-radius:4px;flex:none}
.ic img{image-rendering:pixelated}
.ic.big{width:72px;height:72px}
.name{display:inline-flex;align-items:center;font-family:"Segoe UI",system-ui,sans-serif;font-size:14px;vertical-align:middle}
.bars{list-style:none;padding:0;margin:0 0 12px}
.bars li{display:grid;grid-template-columns:minmax(90px,40%) 1fr 48px;gap:8px;align-items:center;margin:3px 0}
.bars .b{background:#14121f;height:12px;border-radius:2px;overflow:hidden}.bars .b span{display:block;height:100%;background:var(--purple)}
.bars .v{text-align:right;font-family:Consolas,monospace;font-size:12px;color:var(--mu)}
svg{max-width:100%;height:auto}
"""

JS = """
document.querySelectorAll('th.ord').forEach(function(th,i){th.addEventListener('click',function(){
var b=th.closest('table').tBodies[0],asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
Array.prototype.slice.call(b.rows).sort(function(x,y){
var a=x.cells[i].dataset.v,c=y.cells[i].dataset.v;
if(i===0)return asc?a.localeCompare(c):c.localeCompare(a);
a=a===''?-1e9:parseFloat(a);c=c===''?-1e9:parseFloat(c);return asc?a-c:c-a;
}).forEach(function(r){b.appendChild(r)});});});
"""


def _e(x) -> str:
    return html.escape(str(x))


def _n(x, dec=1) -> str:
    return "—" if x is None else f"{x:.{dec}f}"


def _pct(x) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def _img(pm, side=28) -> str:
    """Pixel map {(x, y): "#rrggbb"} -> <img> RGBA PNG (trimmed to its box) as a data URI, scaled by an integer."""
    x0, y0, x1, y1 = visual.bbox(pm)
    raw = bytearray()
    for y in range(y0, y1):
        raw.append(0)  # filter 0 on the line
        for x in range(x0, x1):
            c = pm.get((x, y))
            raw += bytes.fromhex(c[1:]) + b"\xff" if c else b"\0\0\0\0"
    def chunk(n, d):
        return struct.pack(">I", len(d)) + n + d + struct.pack(">I", zlib.crc32(n + d))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", x1 - x0, y1 - y0, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    k = max(1, side // max(x1 - x0, y1 - y0))
    return (f'<img alt="" width="{(x1 - x0) * k}" height="{(y1 - y0) * k}" '
            f'src="data:image/png;base64,{base64.b64encode(png).decode()}">')


def _item_icon(key) -> str:
    """Item icon, with the border in the color of the highest rarity it can have."""
    g = art.ITEM_ART.get(key)
    if not g:
        return ""
    rars = M.ITEMS[key].get("rarities") or []
    color = next((M.RAR_COLOR[r] for r in reversed(list(M.RAR_COLOR)) if r in rars and M.RAR_COLOR[r]), None)
    edge = f' style="border-color:{color}"' if color else ""
    return f'<span class="ic"{edge}>{_img(visual.grid_to_map(g, art.PAL))}</span>'


def _hero_icon(key) -> str:
    """Idle frame of the 1st stage (heroes/<key>.py); a hero without a module (e.g. Petdex) has no icon."""
    try:
        mod = importlib.import_module("heroes." + key)
        from heroes import assemble
        pm = visual.grid_to_map(assemble.states(mod, 0)["idle"][0], mod.PAL)
    except (ImportError, AttributeError, KeyError):
        return ""
    return f'<span class="ic big">{_img(pm, 64)}</span>'


def _syn_icon(key) -> str:
    """Pair: its two items; set: first item of the family; reaction: none."""
    req = M.SYNERGIES[key]["req"]
    if "items" in req:
        return "".join(_item_icon(i) for i in req["items"])
    if "family" in req:
        return next((_item_icon(i) for i in M.ITEMS if M.item_family(i) == req["family"]), "")
    return ""


def _synergies_table(sim, real, real_empty) -> str:
    rows = []
    for k, d in M.SYNERGIES.items():
        def cel(x):
            return "—" if not x["n"] else f'{x["n"]} · {_n(x["median_with"])} vs {_n(x["median_without"])}'
        r = "—" if real_empty else cel(real[k])
        rows.append(f'<tr><td><span class="name">{_syn_icon(k)}{_e(d["name"])}</span></td><td>{_e(d["kind"])}</td>'
                    f'<td>{cel(sim[k])}</td><td>{r}</td></tr>')
    return ('<div class="scroll"><table><thead><tr><th>Synergy</th><th>Kind</th><th>Sim: runs · median with vs without</th>'
            '<th>Real</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def _item_name(key, items) -> str:
    name = items[key]["name"] if key in items else key
    return f'<span class="name">{_item_icon(key) if key in M.ITEMS else ""}{_e(name)}</span>'


def _summary_line(name, r, metas=None) -> str:
    """Summary table row; without `targets` (or with a None target) it shows no ✓/✗."""
    def cel(k, txt):
        m = (metas or {}).get(k)
        sign = "" if m is None else (' <span class="badge ok">✓</span>' if m else ' <span class="badge bad">✗</span>')
        return f"<td>{txt}{sign}</td>"
    warning = ' <span class="warn">(fewer than 10 runs, unreliable)</span>' if 0 < r["n"] < 10 else ""
    return (f"<tr><td>{_e(name)}{warning}</td><td>{r['n']}</td><td>{_n(r['median'])}</td>"
            + cel("p90", _n(r["p90"])) + cel("max", _n(r["max"], 0)) + cel("passed_boss1", _pct(r["passed_boss1"]))
            + f"<td>{_n(r['items_median'])}</td></tr>")


def _pair_sr(sim, real, fmt, vs=False, weak=False, fmt_real=None) -> str:
    """'sim / real' cell. Color by the vs_mean rule; real is faded when weak."""
    def un(v, f, dim):
        txt = f(v)
        if vs and v is not None and abs(v) > 1:
            txt = f'<span class="{"ok" if v > 0 else "bad"}">{txt}</span>'
        return f'<span class="weak">{txt}</span>' if dim else txt
    return f"{un(sim, fmt, False)} / {un(real, fmt_real or fmt, weak)}"


def _items_table(items) -> str:
    cab = [("Item", None), ("Taken", "taken"), ("Floor when taken", "taken_floor"), ("Lasted", "lasted"),
           ("vs mean", "vs_mean"), ("Final floor", "final_floor"),
           ("In quick deaths", "quick_deaths"), ("Consumed", "consumed_pct")]
    fmts = {"taken": _pct, "taken_floor": _n, "lasted": _n, "vs_mean": lambda v: _n(v, 2),
            "final_floor": _n, "quick_deaths": _pct, "consumed_pct": _pct}
    out = ['<div class="scroll"><table id="items"><thead><tr>']
    out += [f'<th class="ord">{_e(t)}{"<br>sim / real" if k else ""}</th>' for t, k in cab]
    out.append("</tr></thead><tbody>")
    for key, it in sorted(items.items(), key=lambda x: x[1]["name"]):
        s, r = it["sim"], it["real"]
        weak = r["n"] < 10
        rares = ", ".join(f'<span style="color:{M.RAR_COLOR[x]}">{_e(M.RAR_NAMES[x])}</span>' if M.RAR_COLOR.get(x)
                          else _e(M.RAR_NAMES[x]) for x in (it["rarities"] or []) if x in M.RAR_NAMES)
        warning = f' <span class="warn" title="fewer than 10 real runs">⚠ n={r["n"]}</span>' if weak and r["n"] else ""
        out.append(f'<tr><td data-v="{_e(it["name"])}"><span class="name">{_item_icon(key)}<span>{_e(it["name"])}'
                   f'<br><small class="mu">{rares}</small>{warning}</span></span></td>')
        for _, k in cab[1:]:
            order = "" if s[k] is None else s[k]
            modes, fr = "", None
            if k == "taken":  # real: how many runs and the fraction
                fr = lambda v, n=r["n"]: "—" if v is None else f"{n} ({_pct(v)})"
            if k == "vs_mean":  # raw value, not centered on the mean
                modes = f'<br><small class="mu">raw {_n(s["vs_expected"], 2)} / {_n(r["vs_expected"], 2)}</small>'
            if k == "consumed_pct" and r["consumed_by_mode"]:  # real split by game mode
                modes = "<br><small class=\"mu\">" + " · ".join(
                    f"{_e(m)} {_pct(v)}" for m, v in sorted(r["consumed_by_mode"].items())) + "</small>"
            out.append(f'<td data-v="{order}">{_pair_sr(s[k], r[k], fmts[k], vs=(k == "vs_mean"), weak=weak, fmt_real=fr)}{modes}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _pairs_table(lst, items) -> str:
    if not lst:
        return '<p class="mu">Few pairs with a large enough sample.</p>'
    color = lambda g: "ok" if g > 1 else "bad" if g < -1 else ""
    lines = "".join(f'<tr><td>{_item_name(p["a"], items)} <span class="mu">+</span> {_item_name(p["b"], items)}</td><td>{p["n"]}</td>'
                     f'<td>{_n(p["vs_expected"], 2)}</td><td class="{color(p["gain"])}">{_n(p["gain"], 2)}</td></tr>'
                     for p in lst)
    return ('<div class="scroll">' "<table><thead><tr><th>Pair</th><th>n</th><th>vs expected</th><th>Pair gain</th></tr></thead>"
            f"<tbody>{lines}</tbody></table></div>")


def _histogram(per_floor, title) -> str:
    if not per_floor:
        return f'<p class="mu">{_e(title)}: no runs.</p>'
    until, total, maxv = max(int(a) for a in per_floor), sum(per_floor.values()), max(per_floor.values())
    larg, alt, esp = 22, 120, 14
    bars = []
    for a in range(1, until + 1):
        v = per_floor.get(a, per_floor.get(str(a), 0))  # int key (memory) or str (JSON)
        h, x = alt * v / maxv, (a - 1) * larg
        bars.append(f'<rect x="{x + 2}" y="{alt - h:.1f}" width="{larg - 4}" height="{h:.1f}" fill="{"#ffd23f" if a % M.BOSS_EVERY == 0 else "#7a73d6"}" rx="2">'
                      f'<title>floor {a}: {v} ({v / total * 100:.0f}%)</title></rect>'
                      f'<text x="{x + larg / 2}" y="{alt + esp}" fill="#a9a4d6" font-size="10" text-anchor="middle">{a}</text>')
    return (f'<p class="mu">Floor where they died ({total} runs; gold = boss floor)</p>'
            f'<svg viewBox="0 0 {until * larg} {alt + esp + 2}" width="{until * larg}" role="img" aria-label="{_e(title)}">'
            + "".join(bars) + "</svg>")


def _bars(pairs) -> str:
    """Horizontal CSS bars: label, bar proportional to the largest and value."""
    pairs = list(pairs)
    top = max(c for _, c in pairs) or 1
    return '<ul class="bars">' + "".join(
        f'<li><span>{_e(n)}</span><span class="b"><span style="width:{c / top * 100:.0f}%"></span></span>'
        f'<span class="v">{c}</span></li>' for n, c in pairs) + "</ul>"


def _killers(lst) -> str:
    if not lst:
        return '<p class="mu">no data</p>'
    return _bars(lst)


KINDS = {"monster": "Monster", "horde": "Horde", "boss": "Boss", "mimic": "Mimic", "trap": "Trap",
         "status": "Status", "gave_up": "Gave up", "?": "Old"}


def _kinds(d) -> str:
    if not d:
        return '<p class="mu">no data</p>'
    return _bars((KINDS.get(k, k), c) for k, c in d.items())


def make_html(data: dict) -> str:
    items, info = data["items"], data["real_info"]
    real_empty = data["real"]["n"] == 0
    p = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>Dungeon statistics</title><style>{CSS}</style></head><body>",
         f'<header><h1>Token Dungeon · balance statistics</h1><p class="mu">Version {_e(data["version"])} · '
         f'generated at {_e(data["generated_at"])} · development tool</p></header>',
         "<h2>Summary</h2>"]
    if real_empty:
        p.append('<p class="warn">no real runs: the real column stays empty until runs finish (runs.jsonl in ~/.tokenlike).</p>')
    modes = ", ".join(f"{m}: {c}" for m, c in sorted(info["modes"].items())) or "none"
    p.append(f'<p class="mu">Real runs per mode: {_e(modes)} · {info["gave_ups"]} give-ups left out · '
             f'{info["ignored"]} ignored lines · {info["other_versions"]} lines from other versions.</p>')
    p.append(f'<div class="scroll"><table><thead><tr><th>Source</th><th>Runs</th><th>Median</th><th>p90 ({TARGETS["p90"][0]}–{TARGETS["p90"][1]})</th>'
             f'<th>Max (up to {TARGETS["max"][1]})</th><th>Passed the 1st boss '
             f'({TARGETS["passed_boss1"][0] * 100:.0f}–{TARGETS["passed_boss1"][1] * 100:.0f}%)</th><th>Items (median)</th></tr></thead><tbody>')
    cal, metas = data["calibration"], data["targets"]
    for key, name in (("without_achievements", "calibration (slime) without achievements"),
                        ("with_achievements", "calibration (slime) with achievements")):
        p.append(_summary_line(name, cal[key], metas[key]))
    # all heroes mixed: informative only, the targets are judged in the calibration
    p.append(_summary_line("sim (all heroes)", data["sim"]))
    p.append(_summary_line("sim without achievements (all heroes)", data["sim_without_achievements"]))
    p.append(_summary_line("real", data["real"], metas["real"]))
    p.append("</tbody></table></div>")
    p.append('<h2>Items</h2><p class="mu">Each cell: sim / real. Click a header to sort. '
             "vs mean: vs expected minus the items' mean (taking an item already helps). Green: above +1; red: below −1. "
             "Below, the raw vs expected. Faded real: fewer than 10 real runs with the item.</p>")
    p.append(_items_table(items))
    for rot, key in (("Best pairs", "best_items"), ("Worst pairs", "worst_items")):
        p.append(f'<h2>{rot}</h2><div>')  # stacked: names with icons do not fit side by side
        for font in ("sim", "real"):
            lst = data["pairs"][font][key]
            body = '<p class="mu">no real runs</p>' if font == "real" and real_empty else _pairs_table(lst, items)
            p.append(f'<div><p class="source">{font}</p>{body}</div>')
        p.append("</div>")
    p.append("<h2>Synergies</h2>" + _synergies_table(data["synergies"]["sim"], data["synergies"]["real"], real_empty))
    p.append('<h2>Rooms</h2><div class="cols">')
    for font in ("sim", "real"):
        ro = data["rooms"][font]
        bars = _bars((k, round(100 * v)) for k, v in ro["share"].items()) if ro["share"] else '<p class="mu">no data</p>'
        p.append(f'<div class="card"><p class="source">{font}</p><p class="mu">Share of rooms (%)</p>{bars}'
                 f'<p class="mu">Idol accepted: {_pct(ro["idol_accept"])} · won: {_pct(ro["idol_win"])}</p></div>')
    p.append('</div><h2>Where runs die</h2><div class="cols">')
    for font in ("sim", "real"):
        m = data["deaths"][font]
        p.append(f'<div class="card"><p class="source">{font}</p>{_histogram(m["per_floor"], font)}<p class="mu">Top killers</p>{_killers(m["killers"])}<p class="mu">By kind of death</p>{_kinds(m["per_kind"])}</div>')
    p.append('</div><h2>Heroes</h2><div class="scroll"><table><thead><tr><th>Hero</th><th>Runs sim / real</th>'
             "<th>Median sim / real</th><th>p90 sim / real</th></tr></thead><tbody>")
    hs, hr = data["heroes"]["sim"], data["heroes"]["real"]
    g = lambda d, k, f=_n: f(d[k]) if d else "—"
    try:
        import tokenlike
        names = {k: c.name for k, c in tokenlike.all_characters().items()}
    except Exception:  # only the pretty name; the key will do
        names = {}
    for c in sorted(set(hs) | set(hr)):
        s, r = hs.get(c), hr.get(c)
        name = f'<span class="name">{_hero_icon(c)}{_e(names.get(c, c))}</span>'
        p.append(f"<tr><td>{name}</td><td>{g(s, 'n', str)} / {g(r, 'n', str)}</td>"
                 f"<td>{g(s, 'median')} / {g(r, 'median')}</td><td>{g(s, 'p90')} / {g(r, 'p90')}</td></tr>")
    p.append(f"</tbody></table></div><script>{JS}</script></body></html>")
    return "".join(p)


def main(argv=None):
    import argparse, webbrowser
    ap = argparse.ArgumentParser(description="Balance statistics page (sim x real).")
    ap.add_argument("--runs", type=int, default=2000)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--real-dir", default=str(Path.home() / ".tokenlike"))
    ap.add_argument("--all-versions", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))  # for tests only
    a = ap.parse_args(argv)
    data = collect(a.runs, Path(a.real_dir), a.all_versions)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    h, j = out / "balance_stats.html", out / "balance_stats.json"
    h.write_text(make_html(data), encoding="utf-8")
    j.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(h); print(j)
    if not a.no_open:
        webbrowser.open(h.as_uri())


if __name__ == "__main__":
    main()
