"""Monta os 9 estados de um herói 32 px a partir do módulo `herois/<chave>.py` (PAL, QUADROS, ESTAGIOS, ANCORA)."""

N = 32
DESENHADOS = ("idle", "run_r", "waving", "jumping", "failed", "waiting", "running", "review")


def _sobrepor(quadro, extra, ax, ay):
    g = [list(l) for l in quadro]
    for dy, lin in enumerate(extra):
        for dx, ch in enumerate(lin):
            if ch != "." and 0 <= ax + dx < N and 0 <= ay + dy < N:
                g[ay + dy][ax + dx] = ch
    return ["".join(l) for l in g]


def estados(heroi, estagio):
    """Os 9 estados (run_l = run_r espelhado) com o `extra` do estágio na âncora de cada quadro."""
    extra = heroi.ESTAGIOS[estagio]["extra"]
    est = {}
    for e in DESENHADOS:
        qs = heroi.QUADROS[e]
        est[e] = [_sobrepor(q, extra, *heroi.ANCORA[e][i]) if extra else list(q) for i, q in enumerate(qs)]
    est["run_l"] = [[l[::-1] for l in q] for q in est["run_r"]]
    return {e: est[e] for e in ("idle", "run_r", "run_l") + DESENHADOS[2:]}


def validar(heroi):
    est = heroi.ESTAGIOS
    assert len(est) == 3, f"ESTAGIOS: {len(est)} itens (esperado 3)"
    assert est[0]["extra"] is None, "ESTAGIOS[0]: extra deve ser None"
    assert all("title" in s and "floor" in s for s in est), "ESTAGIOS: falta title/floor"
    for e in DESENHADOS:
        assert e in heroi.QUADROS, f"estado faltando: {e}"
        qs = heroi.QUADROS[e]
        assert 4 <= len(qs) <= 6, f"{e}: {len(qs)} quadros (esperado 4 a 6)"
        anc = heroi.ANCORA.get(e, [])
        assert len(anc) == len(qs), f"{e}: âncoras != quadros"
        assert all(len(a) == 2 and all(type(v) is int for v in a) for a in anc), f"{e}: âncora não é (int, int)"
        for i, q in enumerate(qs):
            assert len(q) == N and all(len(l) == N for l in q), f"{e} quadro {i}: não é {N}x{N}"
            assert any(c != "." for l in q for c in l), f"{e} quadro {i}: vazio"
            usadas = {c for l in q for c in l} - {"."}
            assert usadas <= set(heroi.PAL), f"{e} quadro {i}: cor fora da PAL {usadas - set(heroi.PAL)}"
