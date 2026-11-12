"""Escreve PNGs de verdade (zlib + struct) para os testes exercitarem o decodificador."""
import struct
import zlib


def _bloco(nome, dados):
    return struct.pack(">I", len(dados)) + nome + dados + struct.pack(">I", zlib.crc32(nome + dados))


def _filtrar(f, lin, ant, bpp):
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


def escrever_png(path, w, h, linhas, tipo=6, filtros=(0,), plte=b"", trns=b""):
    """`linhas`: h linhas de bytes já no formato do tipo de cor (8 bits). Filtro da linha y = filtros[y % len]."""
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[tipo]
    raw, ant = bytearray(), bytes(w * bpp)
    for y, lin in enumerate(linhas):
        f = filtros[y % len(filtros)]
        raw += bytes([f]) + _filtrar(f, lin, ant, bpp)
        ant = lin
    d = b"\x89PNG\r\n\x1a\n" + _bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, tipo, 0, 0, 0))
    if plte:
        d += _bloco(b"PLTE", plte)
    if trns:
        d += _bloco(b"tRNS", trns)
    d += _bloco(b"IDAT", zlib.compress(bytes(raw), 1)) + _bloco(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(d)


def folha_png(path, w, h, linhas=9, ruido=8, sobe=None, vazias=None):
    """Folha 8 x `linhas`: corpo opaco no meio de cada célula, resto com alfa `ruido` (quase transparente).
    `sobe` = {linha: px}: o corpo daquela linha fica px mais alto (quadro de pulo)."""
    sobe, vazias = sobe or {}, vazias or {}   # vazias = {linha: n}: as n últimas células da linha ficam sem corpo
    cw, ch = w // 8, h // linhas
    fundo = bytes([10, 20, 30, ruido])
    corpo = bytes([200, 100, 50, 255])
    def cheia(r):
        return b"".join(corpo if cw // 4 <= x % cw < 3 * cw // 4 and x // cw < 8 - vazias.get(r, 0) else fundo
                        for x in range(w))
    vazia = fundo * w
    escrever_png(path, w, h, [cheia(y // ch) if ch // 4 <= y % ch + sobe.get(y // ch, 0) < ch - 2 else vazia
                              for y in range(h)])
