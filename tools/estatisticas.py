"""Métricas de balanceamento a partir das linhas de run (formato de masmorra.run_record)."""
import sys, json, html, statistics, collections, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import masmorra as M

# Metas de balanceamento: (mínimo, máximo); None = sem limite.
METAS = {"passou_chefe1": (0.35, 0.45), "p90": (13, 16), "max": (None, 25)}


def checar_metas(res: dict) -> dict:
    """Para cada meta, True se o número de `res` está dentro da faixa."""
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
    for txt in arq.read_text(encoding="utf-8").splitlines():
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
    """Linha com andar inteiro e itens com floor inteiro ou None."""
    def inteiro(x):
        return isinstance(x, int) and not isinstance(x, bool)
    if not isinstance(rec, dict) or not inteiro(rec.get("floor")):
        return False
    for i in rec.get("items", []) + rec.get("consumed", []):
        if not isinstance(i, dict) or "floor" not in i or not (i["floor"] is None or inteiro(i["floor"])):
            return False
    return True


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
    return {"melhores": lista[:10], "piores": lista[::-1][:5]}


def mortes(recs) -> dict:
    recs = validas(recs)
    por_andar = collections.Counter(r["floor"] for r in recs)
    matadores = collections.Counter(r["killer"] for r in recs if r.get("killer") not in (None, "—"))
    return {"por_andar": dict(sorted(por_andar.items())), "matadores": matadores.most_common(6)}


def herois(recs) -> dict:
    grupos = collections.defaultdict(list)
    for r in validas(recs):
        grupos[r["char"]].append(r["floor"])
    return {c: {"n": len(fs), "mediana": statistics.median(fs), "p90": _p90(fs)} for c, fs in grupos.items()}


# ---------- coleta, página e linha de comando ----------

def _tudo(recs) -> dict:
    return resumo(recs)


def coletar(n_sim: int, pasta_real: Path, todas_versoes: bool, seed: int = 1) -> dict:
    """Roda a simulação (com e sem conquistas), lê as runs reais e calcula tudo."""
    from datetime import datetime
    import simular as S
    heroes = S.todos_os_herois()
    sim_recs = S.simular(n_sim, achs=list(M.ACHIEVEMENTS), seed=seed, heroes=heroes)[0]
    sem_recs = S.simular(n_sim, achs=(), seed=seed, heroes=heroes)[0]
    real_recs, info = carregar_reais(pasta_real, todas_versoes)
    pi_s, pi_r = por_item(sim_recs), por_item(real_recs)
    res = {"sim": _tudo(sim_recs), "sim_sem_conquistas": _tudo(sem_recs), "real": _tudo(real_recs)}
    return {
        "versao": M.BALANCE_VERSION, "gerado_em": datetime.now().isoformat(timespec="seconds"),
        **res, "info_real": info,
        "metas": {k: checar_metas(v) for k, v in res.items()},
        "itens": {k: {"nome": M.ITEMS[k]["name"], "raridades": M.ITEMS[k].get("rarities"),
                      "sim": pi_s[k], "real": pi_r[k]} for k in M.ITEMS},
        "pares": {"sim": pares(sim_recs), "real": pares(real_recs)},
        "mortes": {"sim": mortes(sim_recs), "real": mortes(real_recs)},
        "herois": {"sim": herois(sim_recs), "real": herois(real_recs)},
    }


CSS = """
:root{--bg:#1d1b2b;--bd:#4b4680;--tx:#f2f0ff;--mu:#a9a4d6;--ok:#7ee081;--ruim:#ff6b81;--ouro:#ffd23f}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--tx);font:14px/1.45 Consolas,"Courier New",monospace;padding:16px;max-width:1200px;margin:auto}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;color:var(--ouro);margin:28px 0 8px;border-bottom:1px solid var(--bd);padding-bottom:4px}
.mu{color:var(--mu)}.ok{color:var(--ok)}.ruim{color:var(--ruim)}.aviso{color:var(--ouro)}.fraco{opacity:.5}
.rolar{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{border:1px solid var(--bd);padding:4px 8px;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--mu);font-weight:normal}
th.ord{cursor:pointer}th.ord:hover{color:var(--tx)}
.cols{display:flex;gap:16px;flex-wrap:wrap}.cols>div{flex:1 1 320px}
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


def _resumo_linha(nome, r, metas) -> str:
    def cel(k, txt):
        sinal = "" if r["n"] == 0 else (' <span class="ok">✓</span>' if metas.get(k) else ' <span class="ruim">✗</span>')
        return f"<td>{txt}{sinal}</td>"
    aviso = ' <span class="aviso">(menos de 10 runs, pouco confiável)</span>' if 0 < r["n"] < 10 else ""
    return (f"<tr><td>{_e(nome)}{aviso}</td><td>{r['n']}</td><td>{_n(r['mediana'])}</td>"
            + cel("p90", _n(r["p90"])) + cel("max", _n(r["max"], 0)) + cel("passou_chefe1", _pct(r["passou_chefe1"]))
            + f"<td>{_n(r['itens_med'])}</td></tr>")


def _par_sr(sim, real, fmt, vs=False, fraco=False) -> str:
    """Célula 'sim / real'. Cor pela regra vs_esperado; real esmaecido quando fraco."""
    def un(v, dim):
        txt = fmt(v)
        if vs and v is not None and abs(v) > 1:
            txt = f'<span class="{"ok" if v > 0 else "ruim"}">{txt}</span>'
        return f'<span class="fraco">{txt}</span>' if dim else txt
    return f"{un(sim, False)} / {un(real, fraco)}"


def _tabela_itens(itens) -> str:
    cab = [("Item", None), ("Pego", "pego"), ("Andar em que é pego", "andar_pego"), ("Durou", "durou"),
           ("vs esperado", "vs_esperado"), ("Andar final", "andar_final"),
           ("Em mortes rápidas", "mortes_rapidas"), ("Consumido", "consumido")]
    fmts = {"pego": _pct, "andar_pego": _n, "durou": _n, "vs_esperado": lambda v: _n(v, 2),
            "andar_final": _n, "mortes_rapidas": _pct, "consumido": _pct}
    out = ['<div class="rolar"><table id="itens"><thead><tr>']
    out += [f'<th class="ord">{_e(t)}{"<br>sim / real" if k else ""}</th>' for t, k in cab]
    out.append("</tr></thead><tbody>")
    for it in sorted(itens.values(), key=lambda x: x["nome"]):
        s, r = it["sim"], it["real"]
        fraco = r["n"] < 10
        raros = ", ".join(f'<span style="color:{M.RAR_COLOR[x]}">{_e(M.RAR_NAMES[x])}</span>' if M.RAR_COLOR.get(x)
                          else _e(M.RAR_NAMES[x]) for x in (it["raridades"] or []) if x in M.RAR_NAMES)
        aviso = f' <span class="aviso" title="menos de 10 runs reais">⚠ n={r["n"]}</span>' if fraco and r["n"] else ""
        out.append(f'<tr><td data-v="{_e(it["nome"])}">{_e(it["nome"])}<br><small class="mu">{raros}</small>{aviso}</td>')
        for _, k in cab[1:]:
            ordem = "" if s[k] is None else s[k]
            out.append(f'<td data-v="{ordem}">{_par_sr(s[k], r[k], fmts[k], vs=(k == "vs_esperado"), fraco=fraco)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _tabela_pares(lista, itens) -> str:
    if not lista:
        return '<p class="mu">Poucos pares com amostra suficiente.</p>'
    nome = lambda k: itens[k]["nome"] if k in itens else k
    cor = lambda g: "ok" if g > 1 else "ruim" if g < -1 else ""
    linhas = "".join(f'<tr><td>{_e(nome(p["a"]))} + {_e(nome(p["b"]))}</td><td>{p["n"]}</td>'
                     f'<td>{_n(p["vs_esperado"], 2)}</td><td class="{cor(p["ganho"])}">{_n(p["ganho"], 2)}</td></tr>'
                     for p in lista)
    return ("<table><thead><tr><th>Par</th><th>n</th><th>vs esperado</th><th>Ganho do par</th></tr></thead>"
            f"<tbody>{linhas}</tbody></table>")


def _histograma(por_andar, titulo) -> str:
    if not por_andar:
        return f'<p class="mu">{_e(titulo)}: sem runs.</p>'
    ate, total, maxv = max(int(a) for a in por_andar), sum(por_andar.values()), max(por_andar.values())
    larg, alt, esp = 22, 120, 14
    barras = []
    for a in range(1, ate + 1):
        v = por_andar.get(a, por_andar.get(str(a), 0))  # chave int (memória) ou str (JSON)
        h, x = alt * v / maxv, (a - 1) * larg
        barras.append(f'<rect x="{x + 2}" y="{alt - h:.1f}" width="{larg - 4}" height="{h:.1f}" fill="#7a73d6">'
                      f'<title>andar {a}: {v} ({v / total * 100:.0f}%)</title></rect>'
                      f'<text x="{x + larg / 2}" y="{alt + esp}" fill="#a9a4d6" font-size="10" text-anchor="middle">{a}</text>')
    return (f'<p class="mu">{_e(titulo)}: andar em que morreram ({total} runs)</p>'
            f'<svg viewBox="0 0 {ate * larg} {alt + esp + 2}" width="{ate * larg}" role="img" aria-label="{_e(titulo)}">'
            + "".join(barras) + "</svg>")


def _matadores(lista) -> str:
    if not lista:
        return '<p class="mu">sem dados</p>'
    return "<ul>" + "".join(f"<li>{_e(n)}: {c}</li>" for n, c in lista) + "</ul>"


def gerar_html(dados: dict) -> str:
    itens, info = dados["itens"], dados["info_real"]
    real_vazio = dados["real"]["n"] == 0
    p = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>Estatísticas da masmorra</title><style>{CSS}</style></head><body>",
         f'<h1>Estatísticas de balanceamento</h1><p class="mu">Versão {_e(dados["versao"])} · '
         f'gerado em {_e(dados["gerado_em"])} · ferramenta de desenvolvimento</p>',
         "<h2>Resumo</h2>"]
    if real_vazio:
        p.append('<p class="aviso">sem runs reais: a coluna real fica vazia até acabarem runs (runs.jsonl em ~/.tokenlike).</p>')
    extra = [f"{info[k]} {t}" for k, t in (("outras_versoes", "linhas de outras versões"), ("ignoradas", "linhas ignoradas"),
                                           ("desistencias", "desistências fora das contas")) if info[k]]
    if extra:
        p.append(f'<p class="mu">Runs reais: {_e(", ".join(extra))}.</p>')
    p.append('<div class="rolar"><table><thead><tr><th>Fonte</th><th>Runs</th><th>Mediana</th><th>p90 (13–16)</th>'
             '<th>Máx (até 25)</th><th>Passou do 1º chefe (35–45%)</th><th>Itens (mediana)</th></tr></thead><tbody>')
    for chave, nome in (("sim", "sim"), ("sim_sem_conquistas", "sim sem conquistas"), ("real", "real")):
        p.append(_resumo_linha(nome, dados[chave], dados["metas"][chave]))
    p.append("</tbody></table></div>")
    p.append('<h2>Itens</h2><p class="mu">Cada célula: sim / real. Clique no cabeçalho para ordenar. '
             "Verde: vs esperado acima de +1; vermelho: abaixo de −1. Real esmaecido: menos de 10 runs reais com o item.</p>")
    p.append(_tabela_itens(itens))
    for rot, chave in (("Melhores pares", "melhores"), ("Piores pares", "piores")):
        p.append(f'<h2>{rot}</h2><div class="cols">')
        for fonte in ("sim", "real"):
            lista = dados["pares"][fonte][chave]
            if chave == "piores":  # com poucos pares, os piores repetem os melhores
                vistos = {(x["a"], x["b"]) for x in dados["pares"][fonte]["melhores"]}
                lista = [x for x in lista if (x["a"], x["b"]) not in vistos]
            corpo = '<p class="mu">sem runs reais</p>' if fonte == "real" and real_vazio else _tabela_pares(lista, itens)
            p.append(f'<div><p class="mu">{fonte}</p>{corpo}</div>')
        p.append("</div>")
    p.append('<h2>Onde as runs morrem</h2><div class="cols">')
    for fonte in ("sim", "real"):
        m = dados["mortes"][fonte]
        p.append(f'<div>{_histograma(m["por_andar"], fonte)}<p class="mu">Quem mais mata</p>{_matadores(m["matadores"])}</div>')
    p.append('</div><h2>Heróis</h2><div class="rolar"><table><thead><tr><th>Herói</th><th>Runs sim / real</th>'
             "<th>Mediana sim / real</th><th>p90 sim / real</th></tr></thead><tbody>")
    hs, hr = dados["herois"]["sim"], dados["herois"]["real"]
    g = lambda d, k, f=_n: f(d[k]) if d else "—"
    for c in sorted(set(hs) | set(hr)):
        s, r = hs.get(c), hr.get(c)
        p.append(f"<tr><td>{_e(c)}</td><td>{g(s, 'n', str)} / {g(r, 'n', str)}</td>"
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
