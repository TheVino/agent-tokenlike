"""Text checks on a real Tk window (reusable: the language round runs again in English).

`check(window)` returns a list of problems (empty = all good):
- widget whose requested size is larger than what it got (text or image cut off);
- widget outside its parent, or less than MARGIN px from the edge of a card (tokenlike's `card_box`: Canvas with `backdrop`);
- siblings (pack/grid) that overlap;
- text with automatic wrapping (wraplength / width) that would have to break a word in the middle;
- on a Canvas: text wider than the width, text over text and text touching the edge of the drawn card
  (items with a "card:<id>" tag, see `rounded_rect(extra=...)`).
"""
import tkinter.font as tkfont

MARGIN = 3      # card border (up to 2 px) + 1 px of padding


def _font(w, spec, cache={}):
    k = str(spec)
    if k not in cache:
        cache[k] = tkfont.Font(root=w, font=spec)
    return cache[k]


def _name(w):
    t = ""
    try:
        t = w.cget("text")
    except Exception:
        pass
    return f"{w.winfo_class()} {str(w)[-40:]}" + (f" {t[:40]!r}" if t else "")


def _crosses(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _words(w, text, font, larg, where, out):
    if not text or not larg:
        return
    f = _font(w, font)
    for p in text.split():
        if f.measure(p) > larg:
            out.append(f"{where}: the word {p!r} ({f.measure(p)} px) does not fit the wrap of {larg} px")


def _canvas(cv, out):
    width = cv.winfo_width()
    sr = cv.cget("scrollregion")
    if sr:
        width = max(width, float(sr.split()[2]))
    cards = {}
    for i in cv.find_all():
        for t in cv.gettags(i):
            if t.startswith("card:"):
                b = cv.bbox(i)
                c = cards.get(t)
                cards[t] = b if c is None else (min(c[0], b[0]), min(c[1], b[1]), max(c[2], b[2]), max(c[3], b[3]))
    texts = [i for i in cv.find_all() if cv.type(i) == "text" and cv.itemcget(i, "state") != "hidden"
              and cv.itemcget(i, "text").strip()]
    boxes = {i: cv.bbox(i) for i in texts}
    for i in texts:
        b, txt = boxes[i], cv.itemcget(i, "text")
        where = f"{_name(cv)} text {txt[:40]!r}"
        if b[0] < 0 or b[2] > width:
            out.append(f"{where}: leaves the canvas width ({b[0]}..{b[2]} of {width})")
        _words(cv, txt, cv.itemcget(i, "font"), float(cv.itemcget(i, "width") or 0), where, out)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        for k, c in cards.items():
            if c[0] <= cx <= c[2] and c[1] <= cy <= c[3]:
                if b[0] < c[0] + MARGIN or b[2] > c[2] - MARGIN or b[1] < c[1] + MARGIN or b[3] > c[3] - MARGIN:
                    out.append(f"{where}: touches/crosses the card border {k} ({b} in {c})")
    for n, i in enumerate(texts):
        for j in texts[n + 1:]:
            if _crosses(boxes[i], boxes[j]):
                out.append(f"{_name(cv)}: overlapping texts {cv.itemcget(i, 'text')[:30]!r} and "
                           f"{cv.itemcget(j, 'text')[:30]!r}")


def check(window):
    """List of text/layout problems in `window` and in all its visible children."""
    window.update()                  # maps the window (real winfo_ismapped/sizes)
    out = []

    def anda(w):
        children = [c for c in w.winfo_children() if c.winfo_ismapped()]
        card_box = hasattr(w, "backdrop")
        pw, ph = w.winfo_width(), w.winfo_height()
        m = MARGIN if card_box else 0
        geo = {}
        for c in children:
            x, y, cw, ch = c.winfo_x(), c.winfo_y(), c.winfo_width(), c.winfo_height()
            geo[c] = (x, y, x + cw, y + ch)
            if c.winfo_manager() not in ("pack", "grid"):
                continue                     # place: drawn background, stays below on purpose
            if c.winfo_class() != "Canvas" and (cw < c.winfo_reqwidth() or ch < c.winfo_reqheight()):
                out.append(f"{_name(c)}: cut off ({cw}x{ch} of {c.winfo_reqwidth()}x{c.winfo_reqheight()})")
            if x < m or y < m or x + cw > pw - m or y + ch > ph - m:
                out.append(f"{_name(c)}: {'touches the card border' if card_box else 'leaves the parent'} "
                           f"({geo[c]} in {pw}x{ph})")
            if c.winfo_class() == "Label" and str(c.cget("image")):
                iw, ih = (int(c.tk.call("image", d, c.cget("image"))) for d in ("width", "height"))
                if iw > cw or ih > ch:
                    out.append(f"{_name(c)}: image {iw}x{ih} cut to {cw}x{ch}")
            if c.winfo_class() == "Label":
                wl = int(float(str(c.cget("wraplength")) or 0))
                _words(c, c.cget("text"), c.cget("font"), wl, _name(c), out)
        managed = [c for c in children if c.winfo_manager() in ("pack", "grid")]
        for n, a in enumerate(managed):
            for b in managed[n + 1:]:
                if _crosses(geo[a], geo[b]):
                    out.append(f"{_name(a)} overlaps {_name(b)}")
        if w.winfo_class() == "Canvas":
            _canvas(w, out)
        for c in children:
            anda(c)
    anda(window)
    return out
