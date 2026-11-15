"""Escreve PNGs de verdade (zlib + struct) para os testes exercitarem o decodificador."""
import struct
import zlib


def _chunk(name, data):
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))


def _filter(f, lin, ant, bpp):
    if f == 0:
        return bytes(lin)
    out = bytearray(len(lin))
    for x in range(len(lin)):
        a = lin[x - bpp] if x >= bpp else 0
        b = ant[x]
        c = ant[x - bpp] if x >= bpp else 0
        if f == 1:
            p = a
        elif f == 2:
            p = b
        elif f == 3:
            p = (a + b) >> 1
        else:
            pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
            p = a if pa <= pb and pa <= pc else b if pb <= pc else c
        out[x] = (lin[x] - p) & 255
    return bytes(out)


def write_png(path, w, h, lines, kind=6, filters=(0,), plte=b"", trns=b""):
    """`linhas`: h linhas de bytes já no formato do tipo de cor (8 bits). Filtro da linha y = filtros[y % len]."""
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[kind]
    raw, ant = bytearray(), bytes(w * bpp)
    for y, lin in enumerate(lines):
        f = filters[y % len(filters)]
        raw += bytes([f]) + _filter(f, lin, ant, bpp)
        ant = lin
    d = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, kind, 0, 0, 0))
    if plte:
        d += _chunk(b"PLTE", plte)
    if trns:
        d += _chunk(b"tRNS", trns)
    d += _chunk(b"IDAT", zlib.compress(bytes(raw), 1)) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(d)


def sheet_png(path, w, h, lines=9, noise=8, rises=None, empties=None):
    """Folha 8 x `linhas`: corpo opaco no meio de cada célula, resto com alfa `ruido` (quase transparente).
    `sobe` = {linha: px}: o corpo daquela linha fica px mais alto (quadro de pulo)."""
    rises, empties = rises or {}, empties or {}   # vazias = {linha: n}: as n últimas células da linha ficam sem corpo
    cw, ch = w // 8, h // lines
    backdrop = bytes([10, 20, 30, noise])
    body = bytes([200, 100, 50, 255])
    def full(r):
        return b"".join(body if cw // 4 <= x % cw < 3 * cw // 4 and x // cw < 8 - empties.get(r, 0) else backdrop
                        for x in range(w))
    empty = backdrop * w
    write_png(path, w, h, [full(y // ch) if ch // 4 <= y % ch + rises.get(y // ch, 0) < ch - 2 else empty
                              for y in range(h)])
