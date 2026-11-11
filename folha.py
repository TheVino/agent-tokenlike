"""Corte e redução de spritesheets (puro, sem tkinter).

Trabalha só com um callback `opaco(x, y) -> bool`; quem chama decide o limiar de opacidade.
"""

ESTADOS = ("idle", "run_r", "run_l", "waving", "jumping", "failed", "waiting", "running", "review")
MAX_LINHAS = 11
MAX_QUADROS = 8
ILHA_MAX = 2  # ilhas de até 2 px (mão solta, poeira) são ignoradas


def detectar_grade(w, h):
    """(8, 9) ou (8, 11) se a folha tem células quase quadradas; senão None."""
    if w % 8:
        return None
    for linhas in (9, 11):
        if h % linhas == 0 and 0.7 <= (w // 8) / (h // linhas) <= 1.4:
            return (8, linhas)
    return None


def caixa_comum(caixas):
    """Largura e altura máximas entre as caixas."""
    return (max(c[2] - c[0] for c in caixas), max(c[3] - c[1] for c in caixas))


def fator_reducao(altura, maximo=48):
    """Menor inteiro N tal que altura / N <= maximo."""
    return max(1, -(-altura // maximo))


def _mascara(w, h, opaco):
    """Matriz de opacos sem as ilhas pequenas (componentes 8-conexos de até ILHA_MAX px)."""
    m = [bytearray(1 if opaco(x, y) else 0 for x in range(w)) for y in range(h)]
    for y in range(h):
        for x in range(w):
            if m[y][x] != 1:
                continue
            comp, pilha = [(x, y)], [(x, y)]
            m[y][x] = 2
            while pilha:
                cx, cy = pilha.pop()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and m[ny][nx] == 1:
                            m[ny][nx] = 2
                            comp.append((nx, ny))
                            pilha.append((nx, ny))
            if len(comp) <= ILHA_MAX:
                for cx, cy in comp:
                    m[cy][cx] = 0
    return m


def _faixas(tem):
    """Intervalos [a, b) de índices consecutivos com tem[i] verdadeiro."""
    saida, ini = [], None
    for i, v in enumerate(list(tem) + [False]):
        if v and ini is None:
            ini = i
        elif not v and ini is not None:
            saida.append([ini, i])
            ini = None
    return saida


def _juntar(cols):
    """Mais de 8 pedaços: junta o mais estreito ao vizinho mais próximo (só se for bem
    mais estreito que o maior). Se ainda passar de 8, devolve None."""
    while len(cols) > MAX_QUADROS:
        i = min(range(len(cols)), key=lambda k: cols[k][1] - cols[k][0])
        if (cols[i][1] - cols[i][0]) * 2 > max(c[1] - c[0] for c in cols):
            return None
        if i == 0:
            j = 1
        elif i == len(cols) - 1:
            j = i - 1
        else:
            j = i - 1 if cols[i][0] - cols[i - 1][1] <= cols[i + 1][0] - cols[i][1] else i + 1
        a, b = sorted((i, j))
        cols[a] = [cols[a][0], cols[b][1]]
        del cols[b]
    return cols


def cortar(w, h, opaco, grade=None):
    """Caixas (x0, y0, x1, y1), exclusivas, de cada quadro, por linha da folha (até 11).
    Linha sem nenhum pixel opaco vira []. `grade` = (colunas, linhas) força grade fixa."""
    if grade:
        cols, lins = grade
        cw, ch = w // cols, h // lins
        saida = []
        for r in range(lins):
            caixas = [(c * cw, r * ch, (c + 1) * cw, (r + 1) * ch) for c in range(cols)]
            tem = any(opaco(x, y) for x in range(caixas[0][0], caixas[-1][2]) for y in range(r * ch, (r + 1) * ch))
            saida.append(caixas if tem else [])
        return saida
    m = _mascara(w, h, opaco)
    saida = []
    for y0, y1 in _faixas([any(l) for l in m])[:MAX_LINHAS]:
        cols = _faixas([any(m[y][x] for y in range(y0, y1)) for x in range(w)])
        cols = _juntar(cols)
        if cols is None:  # ponytail: células iguais, sem tentar adivinhar o quadro certo
            x0, x1 = _faixas([any(m[y][x] for y in range(y0, y1)) for x in range(w)])[0][0], \
                max(m_x for m_x in range(w) if any(m[y][m_x] for y in range(y0, y1))) + 1
            cols = [[x0 + (x1 - x0) * i // MAX_QUADROS, x0 + (x1 - x0) * (i + 1) // MAX_QUADROS]
                    for i in range(MAX_QUADROS)]
        saida.append([(a, y0, b, y1) for a, b in cols])
    return saida
