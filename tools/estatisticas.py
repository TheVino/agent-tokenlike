"""Métricas de balanceamento a partir das linhas de run (formato de masmorra.run_record)."""
import sys, json, html, statistics, collections, itertools, base64, struct, zlib, importlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import masmorra as M
import arte, visual

# Metas de balanceamento: (mínimo, máximo); None = sem limite.
METAS = {"passou_chefe1": (0.35, 0.45), "p90": (13, 16), "max": (None, 50)}


def checar_metas(res: dict) -> dict:
    """Para cada meta, True se o número de `res` está dentro da faixa (None sem runs)."""
    if res.get("n") == 0:
        return {k: None for k in METAS}
    out = {}
    for k, (lo, hi) in METAS.items():
        v = res.get(k)
        out[k] = v is not None and (lo is None or v >= lo) and (hi is None or v <= hi)
    return out


def carregar_reais(pasta: Path, todas_versoes: bool = False):
    """Lê <pasta>/runs.jsonl (nunca o runs-demo.jsonl). Devolve (linhas, info)."""
    info = {"outras_versoes": 0, "ignoradas": 0, "desistencias": 0, "modos": {}}
    arq = Path(pasta) / "runs.jsonl"
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
        if not _linha_ok(rec):
            info["ignoradas"] += 1
            continue
        if rec.get("version") != M.BALANCE_VERSION:
            info["outras_versoes"] += 1
            if not todas_versoes:
                continue
        recs.append(rec)
        if rec.get("gave_up"):
            info["desistencias"] += 1
        modo = rec.get("mode", "?")
        info["modos"][modo] = info["modos"].get(modo, 0) + 1
    return recs, info


def validas(recs) -> list:
    """Tira as desistências (run cortada, não terminou)."""
    return [r for r in recs if not r.get("gave_up")]


def _p90(xs):
    # mesmo método do simular.py, mas sem passar do máximo em amostras pequenas
    return min(statistics.quantiles(xs, n=10)[-1], max(xs)) if len(xs) >= 2 else xs[0]


def _linha_ok(rec) -> bool:
    """Linha com andar inteiro, char texto e itens {key texto, floor None ou de 1 até o andar da run}."""
    def inteiro(x):
        return isinstance(x, int) and not isinstance(x, bool)
    if not isinstance(rec, dict) or not inteiro(rec.get("floor")) or not isinstance(rec.get("char"), str):
        return False
    its, cons = rec.get("items"), rec.get("consumed", [])  # consumed falta em linhas antigas
    if not isinstance(its, list) or not isinstance(cons, list):
        return False
    return all(isinstance(i, dict) and isinstance(i.get("key"), str) and "floor" in i
               and (i["floor"] is None or (inteiro(i["floor"]) and 1 <= i["floor"] <= rec["floor"]))
               for i in its + cons)


def resumo(recs) -> dict:
    recs = validas(recs)
    if not recs:
        return {"n": 0, "mediana": None, "p90": None, "max": None, "passou_chefe1": None, "itens_med": None}
    floors = [r["floor"] for r in recs]
    return {"n": len(recs), "mediana": statistics.median(floors), "p90": _p90(floors), "max": max(floors),
            "passou_chefe1": sum(f > M.BOSS_EVERY for f in floors) / len(floors),
            "itens_med": statistics.median(len(r["items"]) for r in recs)}


def esperado(recs) -> dict:
    """Para cada andar f: média de andares restantes (final − f) das runs vivas no andar f."""
    floors = [r["floor"] for r in validas(recs)]
    return {f: statistics.mean(x - f for x in floors if x >= f) for f in range(1, max(floors, default=0) + 1)}


def _pegos(rec) -> dict:
    """Chave -> andar em que foi pego (o primeiro), ignorando itens sem floor (saves antigos)."""
    out = {}
    for i in rec["items"]:
        if i.get("floor") is not None:
            out[i["key"]] = min(out.get(i["key"], i["floor"]), i["floor"])
    return out


def por_item(recs) -> dict:
    recs = validas(recs)
    esp = esperado(recs)
    pegos = [(r, _pegos(r)) for r in recs]
    out = {}
    for key in M.ITEMS:
        rs = [(r["floor"], p[key]) for r, p in pegos if key in p]
        # ofertas resolvidas: cada pegar ou consumir conta uma vez, por modo
        ofertas = collections.defaultdict(lambda: [0, 0])  # modo -> [pegos, consumidos]
        for r in recs:
            modo = r.get("mode", "?")
            ofertas[modo][0] += sum(i["key"] == key and i.get("floor") is not None for i in r["items"])
            ofertas[modo][1] += sum(i["key"] == key and i.get("floor") is not None for i in r.get("consumed", []))
        por_modo = {m: c / (p + c) for m, (p, c) in ofertas.items() if p + c}
        tp, tc = sum(p for p, _ in ofertas.values()), sum(c for _, c in ofertas.values())
        d = {"n": len(rs), "pego": None, "andar_pego": None, "durou": None, "vs_esperado": None,
             "andar_final": None, "mortes_rapidas": None,
             "consumido": tc / (tp + tc) if tp + tc else None, "consumido_por_modo": por_modo}
        if rs:
            d.update(pego=len(rs) / len(recs), andar_pego=statistics.median(f for _, f in rs),
                     durou=statistics.mean(fin - f for fin, f in rs),
                     vs_esperado=statistics.mean(fin - f - esp[f] for fin, f in rs),
                     andar_final=statistics.mean(fin for fin, _ in rs),
                     mortes_rapidas=sum(fin - f <= 2 for fin, f in rs) / len(rs))
        out[key] = d
    # vs_media: vs_esperado menos a média (ponderada por n) dos itens, porque pegar item já ajuda
    com = [d for d in out.values() if d["n"]]
    media = sum(d["n"] * d["vs_esperado"] for d in com) / sum(d["n"] for d in com) if com else 0
    for d in out.values():
        d["vs_media"] = None if d["vs_esperado"] is None else d["vs_esperado"] - media
    return out


def pares(recs, minimo: int = 30) -> dict:
    """Pares de itens com pelo menos `minimo` runs juntos, contados do andar do 2º item."""
    recs = validas(recs)
    esp = esperado(recs)
    vs = {k: d["vs_esperado"] for k, d in por_item(recs).items()}
    grupos = collections.defaultdict(list)
    # ponytail: O(itens² por run), ok para milhares de runs com ~5 itens cada
    for r in recs:
        for (a, fa), (b, fb) in itertools.combinations(sorted(_pegos(r).items()), 2):
            f2 = max(fa, fb)
            grupos[a, b].append(r["floor"] - f2 - esp[f2])
    lista = []
    for (a, b), xs in grupos.items():
        if len(xs) >= minimo and a in vs and b in vs:  # item que saiu do jogo não entra
            m = statistics.mean(xs)
            lista.append({"a": a, "b": b, "n": len(xs), "vs_esperado": m, "ganho": m - max(vs[a], vs[b])})
    lista.sort(key=lambda p: p["ganho"], reverse=True)
    return {"melhores": lista[:10], "piores": lista[10:][::-1][:5]}  # piores não repetem os melhores


def mortes(recs) -> dict:
    recs = validas(recs)
    por_andar = collections.Counter(r["floor"] for r in recs)
    matadores = collections.Counter(r["killer"] for r in recs if r.get("killer") not in (None, "—"))
    por_tipo = collections.Counter(r.get("killer_kind") or "?" for r in recs)   # linha antiga: "?"
    return {"por_andar": dict(sorted(por_andar.items())), "matadores": matadores.most_common(6),
            "por_tipo": dict(por_tipo.most_common())}


def herois(recs) -> dict:
    grupos = collections.defaultdict(list)
    for r in validas(recs):
        grupos[r["char"]].append(r["floor"])
    return {c: {"n": len(fs), "mediana": statistics.median(fs), "p90": _p90(fs)} for c, fs in grupos.items()}


# ---------- coleta, página e linha de comando ----------

def coletar(n_sim: int, pasta_real: Path, todas_versoes: bool, seed: int = 1) -> dict:
    """Roda a calibração (só slime, igual ao simular.py), a simulação com todos os heróis e lê as runs reais."""
    from datetime import datetime
    import simular as S
    heroes = S.todos_os_herois()
    sim_recs = S.simular(n_sim, achs=list(M.ACHIEVEMENTS), seed=seed, heroes=heroes)[0]
    sem_recs = S.simular(n_sim, achs=(), seed=seed, heroes=heroes)[0]
    real_recs, info = carregar_reais(pasta_real, todas_versoes)
    pi_s, pi_r = por_item(sim_recs), por_item(real_recs)
    cal = {"sem_conquistas": resumo(S.simular(n_sim, achs=(), seed=seed)[0]),
           "com_conquistas": resumo(S.simular(n_sim, achs=list(M.ACHIEVEMENTS), seed=seed)[0])}
    real = resumo(real_recs)
    return {
        "versao": M.BALANCE_VERSION, "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "sim": resumo(sim_recs), "sim_sem_conquistas": resumo(sem_recs), "real": real, "calibracao": cal,
        "info_real": info,
        "metas": {**{k: checar_metas(v) for k, v in cal.items()}, "real": checar_metas(real)},
        "itens": {k: {"nome": M.ITEMS[k]["name"], "raridades": M.ITEMS[k].get("rarities"),
                      "sim": pi_s[k], "real": pi_r[k]} for k in M.ITEMS},
        "pares": {"sim": pares(sim_recs), "real": pares(real_recs)},
        "mortes": {"sim": mortes(sim_recs), "real": mortes(real_recs)},
        "herois": {"sim": herois(sim_recs), "real": herois(real_recs)},
    }


CSS = """
:root{--bg:#1d1b2b;--cx:#25223a;--zb:#2b2844;--bd:#3d3866;--tx:#f2f0ff;--mu:#a9a4d6;--ok:#7ee081;--ruim:#ff6b81;
--ouro:#ffd23f;--roxo:#7a73d6;--roxo2:#b48cff}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--tx);font:14px/1.5 "Segoe UI",system-ui,sans-serif;padding:24px 16px;max-width:1200px;margin:auto}
td{font-family:Consolas,"Cascadia Mono","Courier New",monospace;font-size:13px}
header{border:2px solid var(--roxo);background:linear-gradient(135deg,#2a2545,#1d1b2b);padding:16px 20px;border-radius:6px;
box-shadow:4px 4px 0 #0b0b14}
h1{font-size:22px;margin:0 0 4px;color:var(--ouro);letter-spacing:.04em;text-shadow:2px 2px 0 #6a3fb5}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--ouro);margin:32px 0 10px;padding-left:10px;
border-left:4px solid var(--roxo2)}
.mu{color:var(--mu)}.ok{color:var(--ok)}.ruim{color:var(--ruim)}.aviso{color:var(--ouro)}.fraco{opacity:.5}
.rolar{overflow-x:auto;border:1px solid var(--bd);border-radius:6px}
table{border-collapse:collapse;width:100%;background:var(--cx)}
th,td{padding:6px 10px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--bd)}
tbody tr:nth-child(even){background:var(--zb)}tbody tr:hover{background:#363159}
th:first-child,td:first-child{text-align:left}
th{color:var(--mu);font-weight:600;font-size:12px;background:#221f36}
th.ord{cursor:pointer}th.ord:hover{color:var(--ouro)}
.cols{display:flex;gap:16px;flex-wrap:wrap}.cols>div{flex:1 1 320px;min-width:0}
.cartao{background:var(--cx);border:1px solid var(--bd);border-radius:6px;padding:12px 14px}
.fonte{color:var(--roxo2);font-weight:600;text-transform:uppercase;letter-spacing:.06em;font-size:12px;margin:0 0 6px}
.badge{display:inline-block;padding:0 6px;border-radius:9px;font-size:11px;font-weight:700;margin-left:4px}
.badge.ok{background:#1f3d2a;border:1px solid #3d7a4f}.badge.ruim{background:#4a1f2a;border:1px solid #8f3a4d}
.ic{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;margin-right:8px;
background:#14121f;border:2px solid #4b4680;border-radius:4px;flex:none}
.ic img{image-rendering:pixelated}
.nome{display:inline-flex;align-items:center;font-family:"Segoe UI",system-ui,sans-serif;font-size:14px;vertical-align:middle}
.barras{list-style:none;padding:0;margin:0 0 12px}
.barras li{display:grid;grid-template-columns:minmax(90px,40%) 1fr 48px;gap:8px;align-items:center;margin:3px 0}
.barras .b{background:#14121f;height:12px;border-radius:2px;overflow:hidden}.barras .b span{display:block;height:100%;background:var(--roxo)}
.barras .v{text-align:right;font-family:Consolas,monospace;font-size:12px;color:var(--mu)}
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


def _img(pm, lado=28) -> str:
    """Mapa de pixels {(x, y): "#rrggbb"} -> <img> PNG RGBA (aparado na caixa) em data URI, ampliado por inteiro."""
    x0, y0, x1, y1 = visual.bbox(pm)
    raw = bytearray()
    for y in range(y0, y1):
        raw.append(0)  # filtro 0 na linha
        for x in range(x0, x1):
            c = pm.get((x, y))
            raw += bytes.fromhex(c[1:]) + b"\xff" if c else b"\0\0\0\0"
    def bloco(n, d):
        return struct.pack(">I", len(d)) + n + d + struct.pack(">I", zlib.crc32(n + d))
    png = (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", x1 - x0, y1 - y0, 8, 6, 0, 0, 0))
           + bloco(b"IDAT", zlib.compress(bytes(raw), 9)) + bloco(b"IEND", b""))
    k = max(1, lado // max(x1 - x0, y1 - y0))
    return (f'<img alt="" width="{(x1 - x0) * k}" height="{(y1 - y0) * k}" '
            f'src="data:image/png;base64,{base64.b64encode(png).decode()}">')


def _icone_item(key) -> str:
    """Ícone do item, com a borda na cor da raridade mais alta que ele pode ter."""
    art = arte.ITEM_ART.get(key)
    if not art:
        return ""
    rars = M.ITEMS[key].get("rarities") or []
    cor = next((M.RAR_COLOR[r] for r in reversed(list(M.RAR_COLOR)) if r in rars and M.RAR_COLOR[r]), None)
    borda = f' style="border-color:{cor}"' if cor else ""
    return f'<span class="ic"{borda}>{_img(visual.grid_to_map(art, arte.PAL))}</span>'


def _icone_heroi(key) -> str:
    """Quadro idle do 1º estágio (herois/<chave>.py); herói sem módulo (ex.: Petdex) fica sem ícone."""
    try:
        mod = importlib.import_module("herois." + key)
        from herois import montar
        pm = visual.grid_to_map(montar.estados(mod, 0)["idle"][0], mod.PAL)
    except (ImportError, AttributeError, KeyError):
        return ""
    return f'<span class="ic">{_img(pm)}</span>'


def _nome_item(key, itens) -> str:
    nome = itens[key]["nome"] if key in itens else key
    return f'<span class="nome">{_icone_item(key) if key in M.ITEMS else ""}{_e(nome)}</span>'


def _resumo_linha(nome, r, metas=None) -> str:
    """Linha da tabela Resumo; sem `metas` (ou meta None) não mostra ✓/✗."""
    def cel(k, txt):
        m = (metas or {}).get(k)
        sinal = "" if m is None else (' <span class="badge ok">✓</span>' if m else ' <span class="badge ruim">✗</span>')
        return f"<td>{txt}{sinal}</td>"
    aviso = ' <span class="aviso">(menos de 10 runs, pouco confiável)</span>' if 0 < r["n"] < 10 else ""
    return (f"<tr><td>{_e(nome)}{aviso}</td><td>{r['n']}</td><td>{_n(r['mediana'])}</td>"
            + cel("p90", _n(r["p90"])) + cel("max", _n(r["max"], 0)) + cel("passou_chefe1", _pct(r["passou_chefe1"]))
            + f"<td>{_n(r['itens_med'])}</td></tr>")


def _par_sr(sim, real, fmt, vs=False, fraco=False, fmt_real=None) -> str:
    """Célula 'sim / real'. Cor pela regra vs_media; real esmaecido quando fraco."""
    def un(v, f, dim):
        txt = f(v)
        if vs and v is not None and abs(v) > 1:
            txt = f'<span class="{"ok" if v > 0 else "ruim"}">{txt}</span>'
        return f'<span class="fraco">{txt}</span>' if dim else txt
    return f"{un(sim, fmt, False)} / {un(real, fmt_real or fmt, fraco)}"


def _tabela_itens(itens) -> str:
    cab = [("Item", None), ("Pego", "pego"), ("Andar em que é pego", "andar_pego"), ("Durou", "durou"),
           ("vs média", "vs_media"), ("Andar final", "andar_final"),
           ("Em mortes rápidas", "mortes_rapidas"), ("Consumido", "consumido")]
    fmts = {"pego": _pct, "andar_pego": _n, "durou": _n, "vs_media": lambda v: _n(v, 2),
            "andar_final": _n, "mortes_rapidas": _pct, "consumido": _pct}
    out = ['<div class="rolar"><table id="itens"><thead><tr>']
    out += [f'<th class="ord">{_e(t)}{"<br>sim / real" if k else ""}</th>' for t, k in cab]
    out.append("</tr></thead><tbody>")
    for key, it in sorted(itens.items(), key=lambda x: x[1]["nome"]):
        s, r = it["sim"], it["real"]
        fraco = r["n"] < 10
        raros = ", ".join(f'<span style="color:{M.RAR_COLOR[x]}">{_e(M.RAR_NAMES[x])}</span>' if M.RAR_COLOR.get(x)
                          else _e(M.RAR_NAMES[x]) for x in (it["raridades"] or []) if x in M.RAR_NAMES)
        aviso = f' <span class="aviso" title="menos de 10 runs reais">⚠ n={r["n"]}</span>' if fraco and r["n"] else ""
        out.append(f'<tr><td data-v="{_e(it["nome"])}"><span class="nome">{_icone_item(key)}<span>{_e(it["nome"])}'
                   f'<br><small class="mu">{raros}</small>{aviso}</span></span></td>')
        for _, k in cab[1:]:
            ordem = "" if s[k] is None else s[k]
            modos, fr = "", None
            if k == "pego":  # real: quantas runs e a fração
                fr = lambda v, n=r["n"]: "—" if v is None else f"{n} ({_pct(v)})"
            if k == "vs_media":  # valor bruto, sem centrar na média
                modos = f'<br><small class="mu">bruto {_n(s["vs_esperado"], 2)} / {_n(r["vs_esperado"], 2)}</small>'
            if k == "consumido" and r["consumido_por_modo"]:  # real separado por modo de jogo
                modos = "<br><small class=\"mu\">" + " · ".join(
                    f"{_e(m)} {_pct(v)}" for m, v in sorted(r["consumido_por_modo"].items())) + "</small>"
            out.append(f'<td data-v="{ordem}">{_par_sr(s[k], r[k], fmts[k], vs=(k == "vs_media"), fraco=fraco, fmt_real=fr)}{modos}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _tabela_pares(lista, itens) -> str:
    if not lista:
        return '<p class="mu">Poucos pares com amostra suficiente.</p>'
    cor = lambda g: "ok" if g > 1 else "ruim" if g < -1 else ""
    linhas = "".join(f'<tr><td>{_nome_item(p["a"], itens)} <span class="mu">+</span> {_nome_item(p["b"], itens)}</td><td>{p["n"]}</td>'
                     f'<td>{_n(p["vs_esperado"], 2)}</td><td class="{cor(p["ganho"])}">{_n(p["ganho"], 2)}</td></tr>'
                     for p in lista)
    return ('<div class="rolar">' "<table><thead><tr><th>Par</th><th>n</th><th>vs esperado</th><th>Ganho do par</th></tr></thead>"
            f"<tbody>{linhas}</tbody></table></div>")


def _histograma(por_andar, titulo) -> str:
    if not por_andar:
        return f'<p class="mu">{_e(titulo)}: sem runs.</p>'
    ate, total, maxv = max(int(a) for a in por_andar), sum(por_andar.values()), max(por_andar.values())
    larg, alt, esp = 22, 120, 14
    barras = []
    for a in range(1, ate + 1):
        v = por_andar.get(a, por_andar.get(str(a), 0))  # chave int (memória) ou str (JSON)
        h, x = alt * v / maxv, (a - 1) * larg
        barras.append(f'<rect x="{x + 2}" y="{alt - h:.1f}" width="{larg - 4}" height="{h:.1f}" fill="{"#ffd23f" if a % M.BOSS_EVERY == 0 else "#7a73d6"}" rx="2">'
                      f'<title>andar {a}: {v} ({v / total * 100:.0f}%)</title></rect>'
                      f'<text x="{x + larg / 2}" y="{alt + esp}" fill="#a9a4d6" font-size="10" text-anchor="middle">{a}</text>')
    return (f'<p class="mu">Andar em que morreram ({total} runs; dourado = andar de chefe)</p>'
            f'<svg viewBox="0 0 {ate * larg} {alt + esp + 2}" width="{ate * larg}" role="img" aria-label="{_e(titulo)}">'
            + "".join(barras) + "</svg>")


def _barras(pares) -> str:
    """Barras horizontais em CSS: rótulo, barra proporcional ao maior e valor."""
    pares = list(pares)
    topo = max(c for _, c in pares) or 1
    return '<ul class="barras">' + "".join(
        f'<li><span>{_e(n)}</span><span class="b"><span style="width:{c / topo * 100:.0f}%"></span></span>'
        f'<span class="v">{c}</span></li>' for n, c in pares) + "</ul>"


def _matadores(lista) -> str:
    if not lista:
        return '<p class="mu">sem dados</p>'
    return _barras(lista)


TIPOS = {"monster": "Monstro", "horde": "Horda", "boss": "Chefe", "mimic": "Mímico", "trap": "Armadilha",
         "status": "Status", "desistiu": "Desistiu", "?": "Antigo"}


def _tipos(d) -> str:
    if not d:
        return '<p class="mu">sem dados</p>'
    return _barras((TIPOS.get(k, k), c) for k, c in d.items())


def gerar_html(dados: dict) -> str:
    itens, info = dados["itens"], dados["info_real"]
    real_vazio = dados["real"]["n"] == 0
    p = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>Estatísticas da masmorra</title><style>{CSS}</style></head><body>",
         f'<header><h1>Masmorra de Tokens · estatísticas de balanceamento</h1><p class="mu">Versão {_e(dados["versao"])} · '
         f'gerado em {_e(dados["gerado_em"])} · ferramenta de desenvolvimento</p></header>',
         "<h2>Resumo</h2>"]
    if real_vazio:
        p.append('<p class="aviso">sem runs reais: a coluna real fica vazia até acabarem runs (runs.jsonl em ~/.tokenlike).</p>')
    modos = ", ".join(f"{m}: {c}" for m, c in sorted(info["modos"].items())) or "nenhuma"
    p.append(f'<p class="mu">Runs reais por modo: {_e(modos)} · {info["desistencias"]} desistências fora das contas · '
             f'{info["ignoradas"]} linhas ignoradas · {info["outras_versoes"]} linhas de outras versões.</p>')
    p.append(f'<div class="rolar"><table><thead><tr><th>Fonte</th><th>Runs</th><th>Mediana</th><th>p90 ({METAS["p90"][0]}–{METAS["p90"][1]})</th>'
             f'<th>Máx (até {METAS["max"][1]})</th><th>Passou do 1º chefe '
             f'({METAS["passou_chefe1"][0] * 100:.0f}–{METAS["passou_chefe1"][1] * 100:.0f}%)</th><th>Itens (mediana)</th></tr></thead><tbody>')
    cal, metas = dados["calibracao"], dados["metas"]
    for chave, nome in (("sem_conquistas", "calibração (slime) sem conquistas"),
                        ("com_conquistas", "calibração (slime) com conquistas")):
        p.append(_resumo_linha(nome, cal[chave], metas[chave]))
    # todos os heróis misturados: informativo, as metas são julgadas na calibração
    p.append(_resumo_linha("sim (todos os heróis)", dados["sim"]))
    p.append(_resumo_linha("sim sem conquistas (todos os heróis)", dados["sim_sem_conquistas"]))
    p.append(_resumo_linha("real", dados["real"], metas["real"]))
    p.append("</tbody></table></div>")
    p.append('<h2>Itens</h2><p class="mu">Cada célula: sim / real. Clique no cabeçalho para ordenar. '
             "vs média: vs esperado menos a média dos itens (pegar item já ajuda). Verde: acima de +1; vermelho: abaixo de −1. "
             "Embaixo, o vs esperado bruto. Real esmaecido: menos de 10 runs reais com o item.</p>")
    p.append(_tabela_itens(itens))
    for rot, chave in (("Melhores pares", "melhores"), ("Piores pares", "piores")):
        p.append(f'<h2>{rot}</h2><div>')  # empilhado: os nomes com ícone não cabem lado a lado
        for fonte in ("sim", "real"):
            lista = dados["pares"][fonte][chave]
            corpo = '<p class="mu">sem runs reais</p>' if fonte == "real" and real_vazio else _tabela_pares(lista, itens)
            p.append(f'<div><p class="fonte">{fonte}</p>{corpo}</div>')
        p.append("</div>")
    p.append('<h2>Onde as runs morrem</h2><div class="cols">')
    for fonte in ("sim", "real"):
        m = dados["mortes"][fonte]
        p.append(f'<div class="cartao"><p class="fonte">{fonte}</p>{_histograma(m["por_andar"], fonte)}<p class="mu">Quem mais mata</p>{_matadores(m["matadores"])}<p class="mu">Por tipo de morte</p>{_tipos(m["por_tipo"])}</div>')
    p.append('</div><h2>Heróis</h2><div class="rolar"><table><thead><tr><th>Herói</th><th>Runs sim / real</th>'
             "<th>Mediana sim / real</th><th>p90 sim / real</th></tr></thead><tbody>")
    hs, hr = dados["herois"]["sim"], dados["herois"]["real"]
    g = lambda d, k, f=_n: f(d[k]) if d else "—"
    try:
        import tokenlike
        nomes = {k: c.name for k, c in tokenlike.all_characters().items()}
    except Exception:  # só o nome bonito; a chave serve
        nomes = {}
    for c in sorted(set(hs) | set(hr)):
        s, r = hs.get(c), hr.get(c)
        nome = f'<span class="nome">{_icone_heroi(c)}{_e(nomes.get(c, c))}</span>'
        p.append(f"<tr><td>{nome}</td><td>{g(s, 'n', str)} / {g(r, 'n', str)}</td>"
                 f"<td>{g(s, 'mediana')} / {g(r, 'mediana')}</td><td>{g(s, 'p90')} / {g(r, 'p90')}</td></tr>")
    p.append(f"</tbody></table></div><script>{JS}</script></body></html>")
    return "".join(p)


def main(argv=None):
    import argparse, webbrowser
    ap = argparse.ArgumentParser(description="Página de estatísticas de balanceamento (sim x real).")
    ap.add_argument("--runs", type=int, default=2000)
    ap.add_argument("--sem-abrir", action="store_true")
    ap.add_argument("--real-dir", default=str(Path.home() / ".tokenlike"))
    ap.add_argument("--todas-versoes", action="store_true")
    ap.add_argument("--saida", default=str(Path(__file__).resolve().parent / "saida"))  # só para teste
    a = ap.parse_args(argv)
    dados = coletar(a.runs, Path(a.real_dir), a.todas_versoes)
    saida = Path(a.saida); saida.mkdir(parents=True, exist_ok=True)
    h, j = saida / "estatisticas.html", saida / "estatisticas.json"
    h.write_text(gerar_html(dados), encoding="utf-8")
    j.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(h); print(j)
    if not a.sem_abrir:
        webbrowser.open(h.as_uri())


if __name__ == "__main__":
    main()
