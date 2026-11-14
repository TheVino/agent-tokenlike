"""Checagem de textos numa janela Tk de verdade (reutilizável: a rodada de idioma roda de novo em inglês).

`checar(janela)` devolve uma lista de problemas (vazia = tudo certo):
- widget com tamanho pedido maior que o que recebeu (texto ou imagem cortados);
- widget fora do pai, ou a menos de MARGEM px da borda de um cartão (`cartao` do tokenlike: Canvas com `fundo`);
- irmãos (pack/grid) que se sobrepõem;
- texto com quebra automática (wraplength / width) que precisaria partir uma palavra no meio;
- no Canvas: texto fora da largura, texto sobre texto e texto encostado na borda do cartão desenhado
  (itens com uma tag "card:<id>", ver `retangulo_arredondado(extra=...)`).
"""
import tkinter.font as tkfont

MARGEM = 3      # borda do cartão (até 2 px) + 1 px de respiro


def _fonte(w, spec, cache={}):
    k = str(spec)
    if k not in cache:
        cache[k] = tkfont.Font(root=w, font=spec)
    return cache[k]


def _nome(w):
    t = ""
    try:
        t = w.cget("text")
    except Exception:
        pass
    return f"{w.winfo_class()} {str(w)[-40:]}" + (f" {t[:40]!r}" if t else "")


def _cruza(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _palavras(w, texto, fonte, larg, onde, out):
    if not texto or not larg:
        return
    f = _fonte(w, fonte)
    for p in texto.split():
        if f.measure(p) > larg:
            out.append(f"{onde}: a palavra {p!r} ({f.measure(p)} px) não cabe na quebra de {larg} px")


def _canvas(cv, out):
    largura = cv.winfo_width()
    sr = cv.cget("scrollregion")
    if sr:
        largura = max(largura, float(sr.split()[2]))
    cards = {}
    for i in cv.find_all():
        for t in cv.gettags(i):
            if t.startswith("card:"):
                b = cv.bbox(i)
                c = cards.get(t)
                cards[t] = b if c is None else (min(c[0], b[0]), min(c[1], b[1]), max(c[2], b[2]), max(c[3], b[3]))
    textos = [i for i in cv.find_all() if cv.type(i) == "text" and cv.itemcget(i, "state") != "hidden"
              and cv.itemcget(i, "text").strip()]
    caixas = {i: cv.bbox(i) for i in textos}
    for i in textos:
        b, txt = caixas[i], cv.itemcget(i, "text")
        onde = f"{_nome(cv)} texto {txt[:40]!r}"
        if b[0] < 0 or b[2] > largura:
            out.append(f"{onde}: sai da largura do canvas ({b[0]}..{b[2]} de {largura})")
        _palavras(cv, txt, cv.itemcget(i, "font"), float(cv.itemcget(i, "width") or 0), onde, out)
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        for k, c in cards.items():
            if c[0] <= cx <= c[2] and c[1] <= cy <= c[3]:
                if b[0] < c[0] + MARGEM or b[2] > c[2] - MARGEM or b[1] < c[1] + MARGEM or b[3] > c[3] - MARGEM:
                    out.append(f"{onde}: encosta/passa da borda do cartão {k} ({b} em {c})")
    for n, i in enumerate(textos):
        for j in textos[n + 1:]:
            if _cruza(caixas[i], caixas[j]):
                out.append(f"{_nome(cv)}: textos sobrepostos {cv.itemcget(i, 'text')[:30]!r} e "
                           f"{cv.itemcget(j, 'text')[:30]!r}")


def checar(janela):
    """Lista de problemas de texto/layout em `janela` e em todos os filhos visíveis."""
    janela.update()                  # mapeia a janela (winfo_ismapped/tamanhos de verdade)
    out = []

    def anda(w):
        filhos = [c for c in w.winfo_children() if c.winfo_ismapped()]
        cartao = hasattr(w, "fundo")
        pw, ph = w.winfo_width(), w.winfo_height()
        m = MARGEM if cartao else 0
        geo = {}
        for c in filhos:
            x, y, cw, ch = c.winfo_x(), c.winfo_y(), c.winfo_width(), c.winfo_height()
            geo[c] = (x, y, x + cw, y + ch)
            if c.winfo_manager() not in ("pack", "grid"):
                continue                     # place: fundo desenhado, fica por baixo de propósito
            if c.winfo_class() != "Canvas" and (cw < c.winfo_reqwidth() or ch < c.winfo_reqheight()):
                out.append(f"{_nome(c)}: cortado ({cw}x{ch} de {c.winfo_reqwidth()}x{c.winfo_reqheight()})")
            if x < m or y < m or x + cw > pw - m or y + ch > ph - m:
                out.append(f"{_nome(c)}: {'encosta na borda do cartão' if cartao else 'sai do pai'} "
                           f"({geo[c]} em {pw}x{ph})")
            if c.winfo_class() == "Label" and str(c.cget("image")):
                iw, ih = (int(c.tk.call("image", d, c.cget("image"))) for d in ("width", "height"))
                if iw > cw or ih > ch:
                    out.append(f"{_nome(c)}: imagem {iw}x{ih} cortada em {cw}x{ch}")
            if c.winfo_class() == "Label":
                wl = int(float(str(c.cget("wraplength")) or 0))
                _palavras(c, c.cget("text"), c.cget("font"), wl, _nome(c), out)
        gerenciados = [c for c in filhos if c.winfo_manager() in ("pack", "grid")]
        for n, a in enumerate(gerenciados):
            for b in gerenciados[n + 1:]:
                if _cruza(geo[a], geo[b]):
                    out.append(f"{_nome(a)} sobrepõe {_nome(b)}")
        if w.winfo_class() == "Canvas":
            _canvas(w, out)
        for c in filhos:
            anda(c)
    anda(janela)
    return out
