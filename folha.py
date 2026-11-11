"""Corte e redução de spritesheets (puro, sem tkinter).

Trabalha só com um callback `opaco(x, y) -> bool`; quem chama decide o limiar de opacidade.
`ler_png` decodifica o PNG com zlib + struct (o Tk não dá o alfa, só "transparente ou não").
"""
import struct
import zlib

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
        faixas = _faixas([any(m[y][x] for y in range(y0, y1)) for x in range(w)])
        cols = _juntar(list(faixas))
        if cols is None:  # ponytail: células iguais, sem tentar adivinhar o quadro certo
            x0, x1 = faixas[0][0], faixas[-1][1]
            cols = [[x0 + (x1 - x0) * i // MAX_QUADROS, x0 + (x1 - x0) * (i + 1) // MAX_QUADROS]
                    for i in range(MAX_QUADROS)]
        saida.append([(a, y0, b, y1) for a, b in cols])
    return saida


# ------------------------------------------------------------------ PNG
_ASSINATURA = b"\x89PNG\r\n\x1a\n"
_BPP = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}   # tipo de cor -> bytes por pixel (sempre 8 bits por canal)
OPACO = bytes(1 if a > 128 else 0 for a in range(256))   # tabela para bytes.translate: alfa > 128 é opaco


def info_png(cabeca: bytes):
    """(w, h, tipo) do IHDR; ValueError se não for um PNG que ler_png entende."""
    if cabeca[:8] != _ASSINATURA or cabeca[12:16] != b"IHDR":
        raise ValueError("não é um PNG")
    w, h, prof, tipo, _, _, entrel = struct.unpack(">IIBBBBB", cabeca[16:29])
    if prof != 8 or tipo not in _BPP or entrel:
        raise ValueError(f"formato de PNG não suportado (bits {prof}, tipo {tipo}, entrelaçado {entrel})")
    return w, h, tipo


def _somar(a, b, m7, m8):
    """Soma byte a byte (mod 256) de duas linhas inteiras de uma vez, via inteiros grandes."""
    A, B = int.from_bytes(a, "big"), int.from_bytes(b, "big")
    return bytearray((((A & m7) + (B & m7)) ^ ((A ^ B) & m8)).to_bytes(len(a), "big"))


def ler_png(path):
    """(w, h, rgba) de um PNG de 8 bits: RGBA, RGB, cinza, cinza+alfa ou paleta (com tRNS)."""
    d = open(path, "rb").read()
    w, h, tipo = info_png(d[:29])
    idat, plte, trns, i = [], b"", b"", 8
    while i + 8 <= len(d):
        n, nome = struct.unpack(">I4s", d[i:i + 8])
        corpo = d[i + 8:i + 8 + n]
        if nome == b"IDAT":
            idat.append(corpo)
        elif nome == b"PLTE":
            plte = corpo
        elif nome == b"tRNS":
            trns = corpo
        elif nome == b"IEND":
            break
        i += 12 + n
    raw = zlib.decompress(b"".join(idat))
    bpp = _BPP[tipo]
    lado = w * bpp
    m7 = int.from_bytes(b"\x7f" * lado, "big")
    m8 = int.from_bytes(b"\x80" * lado, "big")
    dados, ant, p = bytearray(), bytearray(lado), 0
    for _ in range(h):
        f, lin = raw[p], bytearray(raw[p + 1:p + 1 + lado])
        p += 1 + lado
        if f == 1:
            for x in range(bpp, lado):
                lin[x] = (lin[x] + lin[x - bpp]) & 255
        elif f == 2:
            lin = _somar(lin, ant, m7, m8)
        elif f == 3:
            for x in range(bpp):
                lin[x] = (lin[x] + (ant[x] >> 1)) & 255
            for x in range(bpp, lado):
                lin[x] = (lin[x] + ((lin[x - bpp] + ant[x]) >> 1)) & 255
        elif f == 4:
            for x in range(bpp):
                lin[x] = (lin[x] + ant[x]) & 255
            for x in range(bpp, lado):
                a, b, c = lin[x - bpp], ant[x], ant[x - bpp]
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                lin[x] = (lin[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif f:
            raise ValueError(f"filtro de PNG inválido: {f}")
        dados += lin
        ant = lin
    if tipo == 6:
        return w, h, bytes(dados)
    out = bytearray(w * h * 4)
    if tipo == 2:
        out[0::4], out[1::4], out[2::4] = dados[0::3], dados[1::3], dados[2::3]
        out[3::4] = b"\xff" * (w * h)
    elif tipo in (0, 4):
        g = dados[0::bpp]
        out[0::4] = out[1::4] = out[2::4] = g
        out[3::4] = dados[1::2] if tipo == 4 else b"\xff" * (w * h)
    else:
        plte = plte.ljust(768, b"\0")
        alfa = trns.ljust(256, b"\xff")[:256]
        for c in range(3):
            out[c::4] = dados.translate(plte[c::3])
        out[3::4] = dados.translate(alfa)
    return w, h, bytes(out)
