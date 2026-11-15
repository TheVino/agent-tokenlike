"""Spritesheet cutting and reduction (pure, no tkinter).

Works only with an `opaque(x, y) -> bool` callback; the caller decides the opacity threshold.
`read_png` decodes the PNG with zlib + struct (Tk does not expose alpha, only "transparent or not").
"""
import struct
import zlib

STATES = ("idle", "run_r", "run_l", "waving", "jumping", "failed", "waiting", "running", "review")
MAX_LINES = 11
MAX_FRAMES = 8
ISLAND_MAX = 2  # islands of up to 2 px (stray hand, dust) are ignored


def detect_grid(w, h):
    """(8, 9) or (8, 11) if the sheet has nearly square cells; otherwise None."""
    if w % 8:
        return None
    for lines in (9, 11):
        if h % lines == 0 and 0.7 <= (w // 8) / (h // lines) <= 1.4:
            return (8, lines)
    return None


def shared_box(boxes):
    """Max width and height among the boxes."""
    return (max(c[2] - c[0] for c in boxes), max(c[3] - c[1] for c in boxes))


def reduction_factor(height_px, maximum=48):
    """Smallest integer N such that height / N <= maximum."""
    return max(1, -(-height_px // maximum))


def _mask(w, h, opaque):
    """Opacity matrix without the small islands (8-connected components of up to ISLAND_MAX px)."""
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
    """Ranges [a, b) of consecutive indices where has[i] is true."""
    out, ini = [], None
    for i, v in enumerate(list(has) + [False]):
        if v and ini is None:
            ini = i
        elif not v and ini is not None:
            out.append([ini, i])
            ini = None
    return out


def _merge(cols):
    """More than 8 pieces: merges the narrowest into its nearest neighbor (only if it is much
    narrower than the widest). If there are still more than 8, returns None."""
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
    """Boxes (x0, y0, x1, y1), exclusive, of each frame, per sheet row (up to 11).
    A row without any opaque pixel becomes []. `grid` = (columns, rows) forces a fixed grid."""
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
        if cols is None:  # ponytail: equal cells, without trying to guess the right frame
            x0, x1 = bands[0][0], bands[-1][1]
            cols = [[x0 + (x1 - x0) * i // MAX_FRAMES, x0 + (x1 - x0) * (i + 1) // MAX_FRAMES]
                    for i in range(MAX_FRAMES)]
        out.append([(a, y0, b, y1) for a, b in cols])
    return out


# ------------------------------------------------------------------ PNG
_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_BPP = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}   # color type -> bytes per pixel (always 8 bits per channel)
OPAQUE = bytes(1 if a > 128 else 0 for a in range(256))   # table for bytes.translate: alpha > 128 is opaque


def info_png(head: bytes):
    """(w, h, type) from IHDR; ValueError if it is not a PNG that read_png understands."""
    if head[:8] != _SIGNATURE or head[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    w, h, prof, kind, _, _, entrel = struct.unpack(">IIBBBBB", head[16:29])
    if prof != 8 or kind not in _BPP or entrel:
        raise ValueError(f"unsupported PNG format (bits {prof}, type {kind}, interlaced {entrel})")
    return w, h, kind


def _sum(a, b, m7, m8):
    """Byte-by-byte sum (mod 256) of two whole rows at once, using big integers."""
    A, B = int.from_bytes(a, "big"), int.from_bytes(b, "big")
    return bytearray((((A & m7) + (B & m7)) ^ ((A ^ B) & m8)).to_bytes(len(a), "big"))


def read_png(path):
    """(w, h, rgba) of an 8-bit PNG: RGBA, RGB, grey, grey+alpha or palette (with tRNS)."""
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
            raise ValueError(f"invalid PNG filter: {f}")
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
