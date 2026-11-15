"""Simulates thousands of runs to check the balance (dungeon.py)."""
import sys, random, statistics, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dungeon as M

def all_heroes():
    import tokenlike  # importing does not open a window (tkinter only in run_gui)
    return [(c.key, c.stats, c.trait) for c in tokenlike.all_characters().values()]

def simulate(n=2000, achs=(), seed=1, heroes=None):
    """Returns (records in the same format as the real runs, rooms played per run)."""
    stage = {}
    if heroes is None:
        heroes = [("slime", {"hp": 20, "atk": 3}, {})]  # default path: no stage_floors
    else:
        import tokenlike
        stage = {k: c.stage_floors for k, c in tokenlike.all_characters().items()}
    rng = random.Random(seed); recs = []; rooms = []
    for i in range(n):
        key, stats, trait = heroes[i % len(heroes)]
        meta = M.new_meta(); meta["achievements"] = list(achs)
        run = M.new_run(key, stats, i, trait); r = 0
        while not run["dead"] and r < 2000:
            run["energy"] = 1e9; M.enter_room(run, meta, rng, stage_floors=stage.get(key), mode="auto"); r += 1
        g = meta["graveyard"][-1] if run["dead"] else {"killer": "—", "kind": ""}
        recs.append(M.run_record(run, g["killer"], False, "auto", list(achs), g["kind"])); rooms.append(r)
    return recs, rooms

def sim(n=2000, achs=(), seed=1):
    recs, rooms = simulate(n, achs, seed)
    floors = [r["floor"] for r in recs]
    killers = collections.Counter(r["killer"] for r in recs if r["killer"] != "—")
    nitems = [len(r["items"]) for r in recs]
    q = statistics.quantiles(floors, n=10)
    print(f"achs={len(achs)} median floor={statistics.median(floors)} p10={q[0]} p90={q[-1]} max={max(floors)} rooms med={statistics.median(rooms)} items med={statistics.median(nitems)}")
    print("  passed the 1st boss:", sum(f>5 for f in floors)/n, " floor10+:", sum(f>=10 for f in floors)/n)
    print("  killers:", killers.most_common(6))
    sy = collections.Counter(k for r in recs for k in r.get("synergies", []))
    print("  synergies (% of runs):", {k: round(100 * sy[k] / n) for k in M.SYNERGIES}, "unused:", [k for k in M.SYNERGIES if not sy[k]])
    print("  deaths by kind:", dict(collections.Counter(r["killer_kind"] for r in recs if r["killer"] != "—").most_common()))

def main():
    sim(); sim(achs=list(M.ACHIEVEMENTS))

if __name__ == "__main__":
    main()
