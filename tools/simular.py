"""Simula milhares de runs para checar o balanceamento (masmorra.py)."""
import sys, random, statistics, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib, masmorra as M
def sim(n=2000, achs=(), seed=1):
    rng=random.Random(seed); floors=[]; killers=collections.Counter(); rooms=[]; nitems=[]
    for i in range(n):
        meta=M.new_meta(); meta["achievements"]=list(achs)
        run=M.new_run("slime",{"hp":20,"atk":3},i); r=0
        while not run["dead"] and r<2000:
            run["energy"]=1e9; M.enter_room(run,meta,rng,mode="auto"); r+=1
        floors.append(run["floor"]); rooms.append(r); nitems.append(len(run["items"]))
        if run["dead"]: killers[meta["graveyard"][-1]["killer"]]+=1
    q=statistics.quantiles(floors,n=10)
    print(f"achs={len(achs)} mediana andar={statistics.median(floors)} p10={q[0]} p90={q[-1]} max={max(floors)} salas med={statistics.median(rooms)} itens med={statistics.median(nitems)}")
    print("  passou do 1º chefe:", sum(f>5 for f in floors)/n, " andar10+:", sum(f>=10 for f in floors)/n)
    print("  matadores:", killers.most_common(6))
sim(); sim(achs=list(M.ACHIEVEMENTS))
