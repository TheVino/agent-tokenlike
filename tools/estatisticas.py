"""Métricas de balanceamento a partir das linhas de run (formato de masmorra.run_record)."""
import sys, json, statistics, collections, itertools
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
