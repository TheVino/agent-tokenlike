"""Writes real PNGs (zlib + struct) so the tests exercise the decoder."""
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
    """`lines`: h rows of bytes already in the color type's format (8 bits). Filter of row y = filters[y % len]."""
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
    """8 x `lines` sheet: opaque body in the middle of each cell, the rest with alpha `noise` (almost transparent).
    `rises` = {row: px}: that row's body sits px higher (jump frame)."""
    rises, empties = rises or {}, empties or {}   # empties = {row: n}: the last n cells of the row have no body
    cw, ch = w // 8, h // lines
    backdrop = bytes([10, 20, 30, noise])
    body = bytes([200, 100, 50, 255])
    def full(r):
        return b"".join(body if cw // 4 <= x % cw < 3 * cw // 4 and x // cw < 8 - empties.get(r, 0) else backdrop
                        for x in range(w))
    empty = backdrop * w
    write_png(path, w, h, [full(y // ch) if ch // 4 <= y % ch + rises.get(y // ch, 0) < ch - 2 else empty
                              for y in range(h)])
