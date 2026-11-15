"""Builds the 9 states of a 32 px hero from the `heroes/<key>.py` module (PAL, FRAMES, STAGES, ANCHOR)."""

N = 32
DRAWN = ("idle", "run_r", "waving", "jumping", "failed", "waiting", "running", "review")


def overlap(frame, extra, ax, ay):
    g = [list(l) for l in frame]
    for dy, lin in enumerate(extra):
        for dx, ch in enumerate(lin):
            if ch != "." and 0 <= ax + dx < N and 0 <= ay + dy < N:
                g[ay + dy][ax + dx] = ch
    return ["".join(l) for l in g]


def states(hero, stage):
    """The 9 states (run_l = run_r mirrored) with the stage's `extra` at each frame's anchor."""
    extra = hero.STAGES[stage]["extra"]
    est = {}
    for e in DRAWN:
        qs = hero.FRAMES[e]
        est[e] = [overlap(q, extra, *hero.ANCHOR[e][i]) if extra else list(q) for i, q in enumerate(qs)]
    est["run_l"] = [[l[::-1] for l in q] for q in est["run_r"]]
    return {e: est[e] for e in ("idle", "run_r", "run_l") + DRAWN[2:]}


def validate(hero):
    est = hero.STAGES
    assert len(est) == 3, f"ESTAGIOS: {len(est)} itens (esperado 3)"
    assert est[0]["extra"] is None, "ESTAGIOS[0]: extra deve ser None"
    assert all("title" in s and "floor" in s for s in est), "ESTAGIOS: falta title/floor"
    for e in DRAWN:
        assert e in hero.FRAMES, f"estado faltando: {e}"
        qs = hero.FRAMES[e]
        assert 4 <= len(qs) <= 6, f"{e}: {len(qs)} quadros (esperado 4 a 6)"
        anc = hero.ANCHOR.get(e, [])
        assert len(anc) == len(qs), f"{e}: âncoras != quadros"
        assert all(len(a) == 2 and all(type(v) is int for v in a) for a in anc), f"{e}: âncora não é (int, int)"
        for i, q in enumerate(qs):
            assert len(q) == N and all(len(l) == N for l in q), f"{e} quadro {i}: não é {N}x{N}"
            assert any(c != "." for l in q for c in l), f"{e} quadro {i}: vazio"
            used = {c for l in q for c in l} - {"."}
            assert used <= set(hero.PAL), f"{e} quadro {i}: cor fora da PAL {used - set(hero.PAL)}"
