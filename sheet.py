"""Corte e redução de spritesheets (puro, sem tkinter).

Trabalha só com um callback `opaco(x, y) -> bool`; quem chama decide o limiar de opacidade.
`ler_png` decodifica o PNG com zlib + struct (o Tk não dá o alfa, só "transparente ou não").
"""
import struct
import zlib

STATES = ("idle", "run_r", "run_l", "waving", "jumping", "failed", "waiting", "running", "review")
MAX_LINES = 11
MAX_FRAMES = 8
ISLAND_MAX = 2  # ilhas de até 2 px (mão solta, poeira) são ignoradas


def detect_grid(w, h):
    """(8, 9) ou (8, 11) se a folha tem células quase quadradas; senão None."""
    if w % 8:
        return None
    for lines in (9, 11):
        if h % lines == 0 and 0.7 <= (w // 8) / (h // lines) <= 1.4:
            return (8, lines)
    return None


def shared_box(boxes):
    """Largura e altura máximas entre as caixas."""
    return (max(c[2] - c[0] for c in boxes), max(c[3] - c[1] for c in boxes))


def reduction_factor(height_px, maximum=48):
    """Menor inteiro N tal que altura / N <= maximo."""
    return max(1, -(-height_px // maximum))


def _mask(w, h, opaque):
    """Matriz de opacos sem as ilhas pequenas (componentes 8-conexos de até ILHA_MAX px)."""
    m = [bytearray(1 if opaque(x, y) else 0 for x in range(w)) for y in range(h)]
    for y in range(h):
        for x in range(w):
            if m[y][x] != 1:
                continue
            comp, stack = [(x, y)], [(x, y)]
            m[y][x] = 2
            while stack:
                cx, cy = stack.pop()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and m[ny][nx] == 1:
                            m[ny][nx] = 2
                            comp.append((nx, ny))
                            stack.append((nx, ny))
            if len(comp) <= ISLAND_MAX:
                for cx, cy in comp:
                    m[cy][cx] = 0
    return m


def _bands(has):
    """Intervalos [a, b) de índices consecutivos com tem[i] verdadeiro."""
    out, ini = [], None
    for i, v in enumerate(list(has) + [False]):
        if v and ini is None:
            ini = i
        elif not v and ini is not None:
            out.append([ini, i])
            ini = None
    return out


def _merge(cols):
    """Mais de 8 pedaços: junta o mais estreito ao vizinho mais próximo (só se for bem
    mais estreito que o maior). Se ainda passar de 8, devolve None."""
    while len(cols) > MAX_FRAMES:
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


def cut(w, h, opaque, grid=None):
    """Caixas (x0, y0, x1, y1), exclusivas, de cada quadro, por linha da folha (até 11).
    Linha sem nenhum pixel opaco vira []. `grade` = (colunas, linhas) força grade fixa."""
    if grid:
        cols, lins = grid
        cw, ch = w // cols, h // lins
        out = []
        for r in range(lins):
            boxes = [(c * cw, r * ch, (c + 1) * cw, (r + 1) * ch) for c in range(cols)]
            has = any(opaque(x, y) for x in range(boxes[0][0], boxes[-1][2]) for y in range(r * ch, (r + 1) * ch))
            out.append(boxes if has else [])
        return out
    m = _mask(w, h, opaque)
    out = []
    for y0, y1 in _bands([any(l) for l in m])[:MAX_LINES]:
        bands = _bands([any(m[y][x] for y in range(y0, y1)) for x in range(w)])
        cols = _merge(list(bands))
        if cols is None:  # ponytail: células iguais, sem tentar adivinhar o quadro certo
            x0, x1 = bands[0][0], bands[-1][1]
            cols = [[x0 + (x1 - x0) * i // MAX_FRAMES, x0 + (x1 - x0) * (i + 1) // MAX_FRAMES]
                    for i in range(MAX_FRAMES)]
        out.append([(a, y0, b, y1) for a, b in cols])
    return out


# ------------------------------------------------------------------ PNG
_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_BPP = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}   # tipo de cor -> bytes por pixel (sempre 8 bits por canal)
OPAQUE = bytes(1 if a > 128 else 0 for a in range(256))   # tabela para bytes.translate: alfa > 128 é opaco


def info_png(head: bytes):
    """(w, h, tipo) do IHDR; ValueError se não for um PNG que ler_png entende."""
    if head[:8] != _SIGNATURE or head[12:16] != b"IHDR":
        raise ValueError("não é um PNG")
    w, h, prof, kind, _, _, entrel = struct.unpack(">IIBBBBB", head[16:29])
    if prof != 8 or kind not in _BPP or entrel:
        raise ValueError(f"formato de PNG não suportado (bits {prof}, tipo {kind}, entrelaçado {entrel})")
    return w, h, kind


def _sum(a, b, m7, m8):
    """Soma byte a byte (mod 256) de duas linhas inteiras de uma vez, via inteiros grandes."""
    A, B = int.from_bytes(a, "big"), int.from_bytes(b, "big")
    return bytearray((((A & m7) + (B & m7)) ^ ((A ^ B) & m8)).to_bytes(len(a), "big"))


def read_png(path):
    """(w, h, rgba) de um PNG de 8 bits: RGBA, RGB, cinza, cinza+alfa ou paleta (com tRNS)."""
    d = open(path, "rb").read()
    w, h, kind = info_png(d[:29])
    idat, plte, trns, i = [], b"", b"", 8
    while i + 8 <= len(d):
        n, name = struct.unpack(">I4s", d[i:i + 8])
        body = d[i + 8:i + 8 + n]
        if name == b"IDAT":
            idat.append(body)
        elif name == b"PLTE":
            plte = body
        elif name == b"tRNS":
            trns = body
        elif name == b"IEND":
            break
        i += 12 + n
    raw = zlib.decompress(b"".join(idat))
    bpp = _BPP[kind]
    side = w * bpp
    m7 = int.from_bytes(b"\x7f" * side, "big")
    m8 = int.from_bytes(b"\x80" * side, "big")
    data, ant, p = bytearray(), bytearray(side), 0
    for _ in range(h):
        f, lin = raw[p], bytearray(raw[p + 1:p + 1 + side])
        p += 1 + side
        if f == 1:
            for x in range(bpp, side):
                lin[x] = (lin[x] + lin[x - bpp]) & 255
        elif f == 2:
            lin = _sum(lin, ant, m7, m8)
        elif f == 3:
            for x in range(bpp):
                lin[x] = (lin[x] + (ant[x] >> 1)) & 255
            for x in range(bpp, side):
                lin[x] = (lin[x] + ((lin[x - bpp] + ant[x]) >> 1)) & 255
        elif f == 4:
            for x in range(bpp):
                lin[x] = (lin[x] + ant[x]) & 255
            for x in range(bpp, side):
                a, b, c = lin[x - bpp], ant[x], ant[x - bpp]
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                lin[x] = (lin[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif f:
            raise ValueError(f"filtro de PNG inválido: {f}")
        data += lin
        ant = lin
    if kind == 6:
        return w, h, bytes(data)
    out = bytearray(w * h * 4)
    if kind == 2:
        out[0::4], out[1::4], out[2::4] = data[0::3], data[1::3], data[2::3]
        out[3::4] = b"\xff" * (w * h)
    elif kind in (0, 4):
        g = data[0::bpp]
        out[0::4] = out[1::4] = out[2::4] = g
        out[3::4] = data[1::2] if kind == 4 else b"\xff" * (w * h)
    else:
        plte = plte.ljust(768, b"\0")
        alpha = trns.ljust(256, b"\xff")[:256]
        for c in range(3):
            out[c::4] = data.translate(plte[c::3])
        out[3::4] = data.translate(alpha)
    return w, h, bytes(out)
