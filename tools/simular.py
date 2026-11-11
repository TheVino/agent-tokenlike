"""Simula milhares de runs para checar o balanceamento (masmorra.py)."""
import sys, random, statistics, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import masmorra as M

def todos_os_herois():
    import tokenlike  # importar não abre janela (tkinter só em run_gui)
    return [(c.key, c.stats) for c in tokenlike.all_characters().values()]

def simular(n=2000, achs=(), seed=1, heroes=None):
    """Devolve (registros no formato das runs reais, salas jogadas por run)."""
    stage = {}
    if heroes is None:
        heroes = [("slime", {"hp": 20, "atk": 3})]  # caminho padrão: sem stage_floors
    else:
        import tokenlike
        stage = {k: c.stage_floors for k, c in tokenlike.all_characters().items()}
    rng = random.Random(seed); recs = []; rooms = []
    for i in range(n):
        key, stats = heroes[i % len(heroes)]
        meta = M.new_meta(); meta["achievements"] = list(achs)
        run = M.new_run(key, stats, i); r = 0
        while not run["dead"] and r < 2000:
            run["energy"] = 1e9; M.enter_room(run, meta, rng, stage_floors=stage.get(key), mode="auto"); r += 1
        g = meta["graveyard"][-1] if run["dead"] else {"killer": "—", "kind": ""}
        recs.append(M.run_record(run, g["killer"], False, "auto", list(achs), g["kind"])); rooms.append(r)
    return recs, rooms

def sim(n=2000, achs=(), seed=1):
    recs, rooms = simular(n, achs, seed)
    floors = [r["floor"] for r in recs]
    killers = collections.Counter(r["killer"] for r in recs if r["killer"] != "—")
    nitems = [len(r["items"]) for r in recs]
    q = statistics.quantiles(floors, n=10)
    print(f"achs={len(achs)} mediana andar={statistics.median(floors)} p10={q[0]} p90={q[-1]} max={max(floors)} salas med={statistics.median(rooms)} itens med={statistics.median(nitems)}")
    print("  passou do 1º chefe:", sum(f>5 for f in floors)/n, " andar10+:", sum(f>=10 for f in floors)/n)
    print("  matadores:", killers.most_common(6))
    print("  mortes por tipo:", dict(collections.Counter(r["killer_kind"] for r in recs if r["killer"] != "—").most_common()))

def main():
    sim(); sim(achs=list(M.ACHIEVEMENTS))

if __name__ == "__main__":
    main()
