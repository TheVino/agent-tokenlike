# Itens empilháveis — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar os 3 espaços de item por itens que empilham a run inteira, com raridade, escolha pegar/consumir, modos auto/interativo e visual calculado pelo contorno do pet.

**Architecture:** Regras puras em `masmorra.py` (modelo de item, raridade, ofertas, escudo, migração de save). Efeitos visuais puros num módulo novo `visual.py`, sobre mapas de pixels `{(x, y): "#rrggbb"}`, sem tkinter. `tokenlike.py` só converte quadros em mapas, compõe uma vez quando os itens mudam, renderiza, e cuida do painel de escolha.

**Tech Stack:** Python 3.9+, só biblioteca padrão (tkinter). Testes são scripts com `assert` rodados com `python tests/<arquivo>.py` (sem pytest).

**Spec:** `docs/superpowers/specs/2026-11-11-itens-empilhaveis-design.md`

## Global Constraints

- Ler `CLAUDE.md`. Valem as regras de lá: só `message.usage` dos logs, sem rede, sem hooks; só biblioteca padrão no app (Pillow só em `tools/`); arte 100% original; inatividade nunca pune.
- Texto na tela sempre sobre retângulo sólido `PANEL_BG` (contorno rosa no Windows com `-transparentcolor #ff00fe`).
- Interface e textos em pt-BR.
- Raridades: `comum`, `raro`, `epico`, `lendario`. Multiplicadores: ×1, ×1,5, ×2, ×3. Efeitos negativos e `trap` não escalam.
- Cores de raridade: comum sem brilho, raro `#6fd6ff`, épico `#b48cff`, lendário `#ffd23f`.
- Cada item sai no máximo uma vez por run. Pool vazio → ouro (valor do baú de ouro: `round((5 + 2 * f) * (1 + st["gold"]))`).
- Regra automática: consome se `consume` tem `heal` e `hp < 0.4 * maxhp`; senão pega.
- `CHOICE_WINDOW_S = 30`. Com pendência aberta o pet não entra em salas antes da janela acabar; depois dela, resolve só quando houver energia para a próxima sala.
- Tetos: `energy` somado ≤ 1.0; `trap` somado entre 0.25 e 3. Limites atuais continuam (`maxhp >= 5`, `atk >= 1`, `dodge <= 0.5`).
- `colecionador` = 10 itens pegos numa run.
- Depois de cada task: `python tests/test_reader.py`, `python tests/test_gui.py`, `python tests/test_migracao.py` e os testes novos passam. Mexeu em `masmorra.py` → `python tools/simular.py`. Mexeu em `arte.py` → `arte.validate()` (já roda no `test_reader.py`).

## Review Focus

1. **Save antigo com run em andamento** (`run["items"]` como dict de espaços, sem `shield`) carrega sem erro, e os itens viram lista `comum` na ordem mão, escudo, cabeça. Teste na Task 2.
2. **App reaberto com pendência no save:** no modo interativo a janela recomeça com 30 s; no modo auto resolve no primeiro `tick`. Teste na Task 5.
3. **Pet composto maior que a área reservada** (muitos objetos no mesmo ponto): recorta na margem, e o ponto de apoio (centro da base) não se mexe. Teste na Task 1 e na Task 3.
4. **Trocar tamanho, evoluir, recarregar personagens, desistir com itens empilhados:** o visual é recomposto, e a lápide esconde tudo. Teste na Task 3.
5. **Pool esgotado e chefe sem item raro+ disponível:** dá ouro sem exceção; chefe cai para a melhor raridade disponível. Teste na Task 2.

---

### Task 1: `visual.py`, efeitos puros sobre mapas de pixels

**Files:**
- Create: `visual.py`
- Test: `tests/test_visual.py`

**Interfaces:**
- Produces (todas puras, nunca alteram a entrada, devolvem mapa novo):
  - `PixelMap = dict[tuple[int, int], str]`
  - `grid_to_map(grid: list[str], pal: dict) -> PixelMap` (pula `'.'` e letras sem cor na paleta)
  - `bbox(pm: PixelMap) -> tuple[int, int, int, int]` → `(x0, y0, x1, y1)`, `x1`/`y1` exclusivos
  - `espinhos(pm, color: str, nivel: int = 1) -> PixelMap`
  - `gotas(pm, color: str, nivel: int = 1) -> PixelMap`
  - `contorno(pm, color: str) -> PixelMap`
  - `tingir(pm, color: str, amount: float) -> PixelMap`
  - `adesivo(pm, art: PixelMap, at: tuple[float, float], glow: str | None = None) -> PixelMap`
  - `objeto(pm, art: PixelMap, anchor: str, ordem: int, glow: str | None = None) -> PixelMap`, `anchor` em `"topo" | "esq" | "dir" | "frente" | "base" | "flutua"`
  - `compose(base: PixelMap, looks: list[tuple[dict, str | None]], arts: dict[str, PixelMap]) -> PixelMap`: `looks` é `[(look, glow_color), ...]` na ordem em que os itens foram pegos.
  - `crop(pm, box: tuple[int, int, int, int]) -> PixelMap`
  - Constante `LOOK_BOX = (-8, -10, 24, 20)`: área máxima em pixels de arte, relativa a um quadro 16×16 em (0, 0).

- [ ] **Step 1: Escrever `tests/test_visual.py`** (estilo dos testes atuais: `sys.path` para a raiz, `tkinter` falso via `sys.modules.setdefault`, `assert` e `print("ok: visual")` no fim). Usar dois mapas: o Slime (`tokenlike.SLIME` + `SLIME_PALETTE`) e um mapa "qualquer" montado à mão (ex.: um retângulo 6×10 com cores arbitrárias), que representa um PNG da comunidade. Asserts:

```python
for pm in (slime, outro):
    x0, y0, x1, y1 = V.bbox(pm)
    e = V.espinhos(pm, "#e2384d"); assert V.bbox(e)[1] < y0 and len(e) > len(pm)
    g = V.gotas(pm, "#4fbf5a"); assert V.bbox(g)[3] > y1
    c = V.contorno(pm, "#ffd23f"); assert all(p in c for p in pm) and len(c) > len(pm)
    assert all(c[p] == "#ffd23f" for p in c if p not in pm)
    t = V.tingir(pm, "#9b6ad6", 0.5); assert t.keys() == pm.keys()
    assert all(t[p] == pm[p] for p in pm if pm[p] == "#1b1b2f")      # contorno escuro intacto
    assert any(t[p] != pm[p] for p in pm)
    assert V.espinhos(pm, "#e2384d", 2) != e                          # nível maior reforça
    assert pm == dict(pm_original)                                   # entrada não muda
# objetos no mesmo ponto não se sobrepõem por completo
arte_obj = V.grid_to_map(arte.ITEM_ART["chifres"], arte.PAL)
a = V.objeto(slime, arte_obj, "topo", 0); b = V.objeto(a, arte_obj, "topo", 1)
assert V.bbox(b)[1] < V.bbox(a)[1]
# glow: pixels vizinhos ao objeto na cor da raridade
gl = V.objeto(slime, arte_obj, "dir", 0, glow="#6fd6ff"); assert "#6fd6ff" in gl.values()
# compose + crop: pivô (centro da base do quadro 16x16) não muda com muitos objetos
looks = [({"type": "obj", "anchor": "topo", "art": "chifres"}, None)] * 12
pm2 = V.crop(V.compose(slime, looks, {"chifres": arte_obj}), V.LOOK_BOX)
bx0, by0, bx1, by1 = V.bbox(pm2)
assert bx0 >= V.LOOK_BOX[0] and by0 >= V.LOOK_BOX[1] and bx1 <= V.LOOK_BOX[2] and by1 <= V.LOOK_BOX[3]
assert V.compose(slime, [], {}) == slime
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `python tests/test_visual.py`. Expected: `ModuleNotFoundError: No module named 'visual'`.

- [ ] **Step 3: Implementar `visual.py`.** Regras que os testes não fixam sozinhos:
  - `espinhos`: para cada coluna `x` com pixel, de 3 em 3 colunas a partir de `x0 + 1`, pegar o `y` mínimo daquela coluna e pôr `color` em `y-1` e `#1b1b2f` em `y-2`. Com `nivel >= 2`, usar passo 2 e ponta de 3 pixels.
  - `gotas`: mesma ideia na borda de baixo, de 3 em 3 colunas, comprimento `1 + (i % 3) + (nivel - 1)`.
  - `contorno`: vizinhos ortogonais fora do mapa recebem `color`.
  - `tingir`: mistura linear RGB `cor*(1-amount) + alvo*amount`, pulando pixels com luminância < 40 (`0.299r + 0.587g + 0.114b`).
  - `adesivo`: centro do adesivo em `x0 + at[0]*(x1-x0)`, `y0 + at[1]*(y1-y0)`; com `glow`, aplicar `contorno` só no adesivo antes de colar.
  - `objeto`: âncoras relativas à caixa do mapa base: `topo` = centrado acima de `y0` (+2 de sobreposição); `esq`/`dir` = colado fora de `x0`/`x1`, base no `y1 - 1`; `frente` = centro; `base` = abaixo de `y1`; `flutua` = posições fixas em volta da caixa (cima-esq, cima-dir, esq, dir). `ordem` desloca para fora: `topo` sobe a altura do objeto - 2, `esq`/`dir` se afastam a largura - 2, `flutua` usa a próxima posição da lista (e repete mais longe ao acabar).
  - `compose`: mutações (`espinhos`, `gotas`, `contorno`, `tingir`, `adesivo`) aplicadas primeiro, na ordem da lista; `nivel` de espinhos/gotas = quantos looks daquele tipo existem; depois os `obj`, contando `ordem` por âncora. Os objetos usam a caixa do corpo já mutado.
  - `crop`: mantém só pixels dentro de `box`.

- [ ] **Step 4: Rodar e ver passar.** Run: `python tests/test_visual.py`. Expected: `ok: visual`.

- [ ] **Step 5: Commit.** `git add visual.py tests/test_visual.py` → `git commit -m "feat: efeitos visuais por contorno (visual.py)"`

---

### Task 2: Regras novas de itens em `masmorra.py`

**Files:**
- Modify: `masmorra.py` (ITEMS, `stats`, `roll_item`→`roll_offer`, `give_item` sai, `fight`, armadilha, `die`, `_check_achievements`, `enter_room`, `new_run`, `ACHIEVEMENTS`)
- Modify: `tokenlike.py` (`load_state` chama `M.migrate_run`; `show_stats` lista a lista de itens; `refresh_equipment` passa a só esconder os acessórios até a Task 3; `play_room` lê `ev["item"]` como `{"key","rar"}` e mostra `ev["consumed"]`)
- Modify: `tools/simular.py` (usar modo auto; imprimir média de itens por run)
- Test: `tests/test_itens.py`

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces:
  - `RARITIES = ("comum", "raro", "epico", "lendario")`, `RAR_MULT = {"comum": 1, "raro": 1.5, "epico": 2, "lendario": 3}`, `RAR_NAMES = {"comum": "Comum", "raro": "Raro", "epico": "Épico", "lendario": "Lendário"}`, `RAR_COLOR = {"comum": None, "raro": "#6fd6ff", "epico": "#b48cff", "lendario": "#ffd23f"}`
  - Entrada de `ITEMS`: `{"name", "fx", "rarities": [...], "consume": {"heal": n} | {"shield": n}, "look": {...}, "req"?: str}`. Sem `slot` e sem `tier`. `look` no formato da Task 1 (`{"type": "obj", "anchor": ..., "art": <chave de arte.ITEM_ART>}` etc.).
  - `item_fx(key: str, rar: str) -> dict` e `consume_fx(key: str, rar: str) -> dict`: valores positivos × `RAR_MULT` (inteiros arredondados para `atk`, `def`, `maxhp`, `lifesteal`, `heal`, `shield`; floats para `dodge`, `gold`, `energy`); negativos e `trap` sem escala.
  - `run["items"]: list[{"key": str, "rar": str}]`, `run["shield"]: int`, `run["pending"]: {"key", "rar", "source"} | None`.
  - `roll_offer(run, meta, rng, best: bool = False) -> dict | None`
  - `auto_choice(run: dict, offer: dict) -> str` → `"pegar" | "consumir"`
  - `resolve_offer(run: dict, offer: dict, choice: str, ev: dict) -> None`: pegar → `run["items"].append`, `ev["item"] = offer`; maxhp positivo também soma ao `hp` (como hoje). Consumir → `heal` (limitado ao máximo) ou soma em `run["shield"]`, `ev["consumed"] = {"key", "rar", "heal"|"shield": n}`. Sempre `_check_achievements`.
  - `resolve_pending(run, meta) -> dict`: resolve `run["pending"]` pela regra automática e devolve o `ev` (com `lines`).
  - `choose_pending(run, meta, choice: str) -> dict`: igual, com a escolha do jogador.
  - `enter_room(run, meta, rng, stage_floors=None, mode: str = "auto") -> dict`: no lugar de `give_item`, cria oferta; `mode == "auto"` → `resolve_offer(..., auto_choice(...))`; `mode == "interativo"` → `run["pending"] = {**offer, "source": kind}` e `ev["pending"] = offer`. Se `roll_offer` devolve `None`, dá o ouro do baú.
  - `apply_damage(run: dict, d: int) -> int`: escudo absorve primeiro; devolve o dano que chegou ao HP. Usado em `fight` (golpe do monstro) e na armadilha.
  - `migrate_run(run: dict) -> dict`: `items` dict → lista `comum` na ordem `mao`, `escudo`, `cabeca`, pulando vazios e chaves que não existem mais em `ITEMS`; `setdefault("shield", 0)`; `setdefault("pending", None)`.
  - `CHOICE_WINDOW_S = 30` (constante aqui, usada pela GUI).

- [ ] **Step 1: Escrever `tests/test_itens.py`** com `random.Random(seed)` e asserts:

```python
assert M.item_fx("adaga", "raro")["atk"] == 3 and M.item_fx("adaga", "lendario")["atk"] == 6
assert M.item_fx("foice", "epico")["maxhp"] == -4                     # negativo não escala
assert M.item_fx("vela", "lendario")["trap"] == 2.0                    # trap não escala
run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); meta = M.new_meta()
assert run["items"] == [] and run["shield"] == 0 and run["pending"] is None
# empilha e soma
for k in ("adaga", "espada_osso"): M.resolve_offer(run, {"key": k, "rar": "comum"}, "pegar", {"lines": []})
assert M.stats(run)["atk"] == 3 + 2 + 4
# tetos
run2 = M.new_run("slime", {}, 2); run2["items"] = [{"key": "vela", "rar": "lendario"}] * 1
assert M.stats(run2)["energy"] <= 1.0 and 0.25 <= M.stats(run2)["trap"] <= 3
# escudo absorve antes do HP
run["shield"] = 5; hp = run["hp"]; assert M.apply_damage(run, 3) == 0 and run["shield"] == 2 and run["hp"] == hp
assert M.apply_damage(run, 4) == 2 and run["shield"] == 0 and run["hp"] == hp - 2
# regra automática
r = M.new_run("slime", {"hp": 20}, 3); r["hp"] = 7
heal_item = next(k for k, it in M.ITEMS.items() if "heal" in it["consume"])
assert M.auto_choice(r, {"key": heal_item, "rar": "comum"}) == "consumir"
r["hp"] = 20; assert M.auto_choice(r, {"key": heal_item, "rar": "comum"}) == "pegar"
# um de cada por run e pool vazio -> None
meta_all = M.new_meta(); meta_all["achievements"] = list(M.ACHIEVEMENTS)
r = M.new_run("slime", {}, 4); r["floor"] = 30; rng = random.Random(1); seen = set()
while (o := M.roll_offer(r, meta_all, rng)) is not None:
    assert o["key"] not in seen and o["rar"] in M.ITEMS[o["key"]]["rarities"]; seen.add(o["key"])
    r["items"].append(o)
assert seen == set(M.ITEMS)
assert M.roll_offer(r, meta_all, rng, best=True) is None
# chefe: raro+ quando existe
r = M.new_run("slime", {}, 5)
assert all(M.roll_offer(r, meta_all, random.Random(s), best=True)["rar"] != "comum" for s in range(50))
# modo interativo cria pendência; enter_room não entra com pendência (responsabilidade da GUI) mas resolve_pending funciona
# migração de save antigo
old = {"items": {"mao": "adaga", "escudo": None, "cabeca": "chapeu"}, "hp": 10}
M.migrate_run(old); assert old["items"] == [{"key": "adaga", "rar": "comum"}, {"key": "chapeu", "rar": "comum"}]
assert old["shield"] == 0 and old["pending"] is None
# colecionador
r = M.new_run("slime", {}, 6); r["items"] = [{"key": k, "rar": "comum"} for k in list(M.ITEMS)[:10]]
ev = {"lines": []}; M._check_achievements(r, meta, ev); assert "colecionador" in meta["achievements"]
# muitas salas nos dois modos, sem exceção; pendência resolvida antes de cada sala
for mode in ("auto", "interativo"):
    rng = random.Random(7); meta = M.new_meta(); run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
    for _ in range(400):
        if run["dead"]: run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
        if run["pending"]: M.resolve_pending(run, meta)
        run["energy"] = 1e9; M.enter_room(run, meta, rng, mode=mode)
        assert len({i["key"] for i in run["items"]}) == len(run["items"])
print("ok: itens")
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `python tests/test_itens.py`. Expected: `AttributeError` (ex.: `item_fx`).

- [ ] **Step 3: Converter os 13 itens.** Cada um: `look` = `{"type": "obj", "anchor": "topo"}` para os antigos `cabeca`, `"dir"` para `mao`, `"esq"` para `escudo`, `"art"` = a própria chave. `rarities`: o antigo `tier` 1 → `["comum", "raro", "epico"]`, 2 → `["comum", "raro", "epico"]`, 3 → `["raro", "epico", "lendario"]`, 4 → `["epico", "lendario"]`. `consume`: armas e cabeça → `{"heal": 4 + 2 * tier}`, escudos → `{"shield": 3 + 2 * tier}`. Manter `req`.

- [ ] **Step 4: Implementar as funções do bloco Interfaces.** Sorteio de raridade em `roll_offer`: pesos por andar `f` = comum `max(10, 70 - 4f)`, raro `25 + f`, épico `4 + 1.5f`, lendário `0.5 + 0.5f` (ponto de partida; a Task 6 ajusta). Sorteia a raridade, depois o item entre os liberados, não possuídos e não pendentes que têm essa raridade; se não houver nenhum, desce uma raridade (e sobe se for preciso); `best=True` começa no mínimo em `raro`. Loja: paga o preço só se houver oferta. `die()` grava `"items": [i["key"] for i in run["items"]]`. Texto de `colecionador`: `"Pegar 10 itens numa run"`. Remover `SLOTS`, `SLOT_NAMES`, `give_item`.

- [ ] **Step 5: Adaptar `tokenlike.py` o mínimo** (os itens não aparecem no pet até a Task 3): `load_state` chama `M.migrate_run(state["run"])` quando há run; `show_stats` lista `nome (Raridade): fx` de cada item, mais `Escudo: n` se > 0 e `Esperando escolha: nome` se houver pendência; `refresh_equipment` esconde os 3 acessórios; `play_room` usa `M.ITEMS[ev["item"]["key"]]` e `M.item_fx(...)`, e para `ev["consumed"]` mostra `+n ♥` (verde, `GOOD`) ou `+n escudo` (`CYAN`). `play_room` ainda chama `enter_room` com `mode="auto"`.

- [ ] **Step 6: `tools/simular.py`:** passar `mode="auto"` e imprimir `itens med=<mediana de len(run["items"]) ao morrer>`.

- [ ] **Step 7: Rodar tudo.** Run: `python tests/test_itens.py && python tests/test_reader.py && python tests/test_gui.py && python tests/test_migracao.py && python tools/simular.py`. Expected: todos imprimem `ok`; o simulador roda (números fora do alvo são esperados até a Task 6).

- [ ] **Step 8: Commit.** `git add masmorra.py tokenlike.py tools/simular.py tests/test_itens.py` → `git commit -m "feat: itens empilháveis com raridade, pegar/consumir e escudo"`

---

### Task 3: Pet composto na GUI

**Files:**
- Modify: `tokenlike.py` (`render_spec`, `load_images`, `build`, `refresh_equipment`→`refresh_look`, `place_pet`, `evolve`, `show_tomb`, `play_room`)
- Modify: `tests/test_gui.py` (fake `PhotoImage.get`)

**Interfaces:**
- Consumes: `visual.grid_to_map`, `visual.compose`, `visual.crop`, `visual.LOOK_BOX` (Task 1); `M.ITEMS[...]["look"]`, `M.RAR_COLOR`, `run["items"]` (Task 2).
- Produces:
  - `spec_to_map(spec) -> visual.PixelMap`: grade → `grid_to_map`; PNG → lê `PhotoImage.get(x, y)` dos pixels não transparentes (`transparency_get`). PNG maior que 24 px é reduzido pegando 1 a cada `ceil(lado / 16)` pixels (a escala de verdade para pets grandes é da parte 3). O mapa sempre é deslocado para que o quadro ocupe (0..16, 0..16), centrado na horizontal e com a base em y = 16.
  - `render_map(pm, s: int) -> tuple[PhotoImage, int]`: imagem com origem em `LOOK_BOX` e quanto (em px de tela) ela desce abaixo da base.
  - `PetApp.refresh_look()`: recompõe `self.frames`, `self.blink_img`, `self.sleep_img` com os looks de `run["items"]` e guarda `self.below` (px abaixo da base). Chamado em `build`, `evolve`, depois de pegar item, `new_run`, `reload_chars`, `change_size`. Nunca no `tick`.

- [ ] **Step 1: Teste em `tests/test_gui.py`.** No fake, `PhotoImage.get = lambda self, x, y: (200, 100, 50)`. Depois do `pump` do modo real, adicionar:

```python
app.run["items"] = [{"key": k, "rar": "lendario"} for k in list(M.ITEMS)[:12]]
app.refresh_look(); w_full = app.frames[0].width()
app.run["items"] = []; app.refresh_look(); w_empty = app.frames[0].width()
assert w_full == w_empty                       # imagem sempre do tamanho de LOOK_BOX: pivô fixo
app.run["items"] = [{"key": "chifres", "rar": "raro"}]; app.refresh_look()
for size in ("Pequeno", "Grande"): app.size_var.set(size); app.change_size()
app.evolve(); app.reload_chars(); app.give_up()
assert not hasattr(app, "acc_items")
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `python tests/test_gui.py`. Expected: `AttributeError: ... 'refresh_look'`.

- [ ] **Step 3: Implementar.** `build` reserva espaço para `LOOK_BOX`: margem esquerda e direita de 8 px de arte e topo de 10 px de arte além do quadro 16×16 (ajustar `left`, `self.top`, `self.W`, `self.H`, `self.fcx`). O sprite continua com `anchor="s"` em `(self.pcx, self.base_y + self.below)`. Remover `acc_items`, `acc_rel` e o desenho por espaço. `show_tomb` só troca o sprite pela lápide. Ao pegar item em `play_room`: `refresh_look()` e `burst` no pet.

- [ ] **Step 4: Rodar tudo.** Run: `python tests/test_visual.py && python tests/test_itens.py && python tests/test_gui.py && python tests/test_reader.py && python tests/test_migracao.py`. Expected: todos `ok`.

- [ ] **Step 5: Ver na tela.** Run: `python tokenlike.py --demo` por ~1 min. Expected: o pet ganha objetos e mutações ao pegar itens, não pula de lugar, nada cortado na janela. (O dono confere se der; registrar no commit se não deu para ver.)

- [ ] **Step 6: Commit.** `git commit -am "feat: pet composto com os itens empilhados"`

---

### Task 4: 7 itens novos com arte

**Files:**
- Modify: `arte.py` (`ITEM_ART`)
- Modify: `masmorra.py` (`ITEMS`)
- Modify: `tools/preview_arte.py` só se precisar mostrar os novos

**Interfaces:**
- Consumes: formato de `ITEMS` e `look` (Tasks 1 e 2).
- Produces: 7 chaves novas em `ITEMS` e em `ITEM_ART` (ícone de cada uma, inclusive das mutações).

- [ ] **Step 1: Teste em `tests/test_itens.py`.**

```python
tipos = {it["look"]["type"] for it in M.ITEMS.values()}
assert {"obj", "espinhos", "gotas", "contorno", "tingir", "adesivo"} <= tipos
assert len(M.ITEMS) >= 20
assert any(it["rarities"] == ["lendario"] for it in M.ITEMS.values())
assert all(k in arte.ITEM_ART for k in M.ITEMS)                       # todo item tem ícone
assert all(it["look"]["art"] in arte.ITEM_ART for it in M.ITEMS.values() if "art" in it["look"])
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `python tests/test_itens.py`. Expected: `AssertionError` no conjunto de tipos.

- [ ] **Step 3: Criar os 7 itens.** Um para cada tipo de mutação (espinhos, gotas, contorno, tingir, adesivo), um objeto `flutua` e um objeto só `["lendario"]`. Nomes, efeitos, cores e desenhos ficam com o implementador, no clima sombrio e fofo, 100% originais, em grade de texto com cores de `arte.PAL` (ícones até ~9×9). O adesivo pode ser um terceiro olho (`at` perto de `(0.5, 0.3)`).

- [ ] **Step 4: Rodar.** Run: `python tests/test_itens.py && python tests/test_reader.py && python tests/test_gui.py && python tests/test_visual.py`. Expected: todos `ok`. Se o Pillow estiver instalado: `python tools/preview_arte.py` e olhar o PNG.

- [ ] **Step 5: Commit.** `git add arte.py masmorra.py tests/test_itens.py` → `git commit -m "feat: 7 itens novos cobrindo as mutações"`

---

### Task 5: Modo auto/interativo e painel de escolha

**Files:**
- Modify: `tokenlike.py` (`DEFAULT_STATE`, `build_menu`, `tick`, `play_room`, `show_stats`, novos `show_choice`, `update_choice`, `close_choice`, `choose`, `change_mode`)
- Modify: `tests/test_gui.py` (fake `tk.Button`, `tk.Frame` = `Noop`)

**Interfaces:**
- Consumes: `M.enter_room(..., mode=...)`, `run["pending"]`, `M.resolve_pending`, `M.choose_pending`, `M.CHOICE_WINDOW_S`, `M.consume_fx`, `M.item_fx`, `M.RAR_NAMES`, `M.RAR_COLOR` (Task 2).
- Produces:
  - `state["mode"]`: `"auto"` (padrão) ou `"interativo"`.
  - `PetApp.pending_since: float | None` (só em memória; ao abrir o app com pendência no save, vira `time.time()` no primeiro `tick`).
  - `PetApp.choose(choice: str) -> None` (botões), `PetApp.change_mode() -> None` (menu).

- [ ] **Step 1: Teste em `tests/test_gui.py`.**

```python
if app.run["dead"]: app.new_run(announce=False)
app.state["mode"] = "interativo"; app.run["pending"] = None
app.run["energy"] = 5 * M.ROOM_COST; app.busy_until = 0
offer = {"key": "adaga", "rar": "raro", "source": "chest"}; app.run["pending"] = dict(offer)
app.pending_since = time.time(); room_before = (app.run["floor"], app.run["room"])
app.tick(); assert (app.run["floor"], app.run["room"]) == room_before   # espera a janela
app.feed(300_000, 300_000); app.tick(); assert app.run["pending"]         # tokens vão para a mochila
app.pending_since = time.time() - M.CHOICE_WINDOW_S - 1; app.tick()
assert app.run["pending"] is None                                       # resolveu sozinho e seguiu
app.run["pending"] = dict(offer, key="tampa"); app.pending_since = time.time(); app.choose("consumir")
assert app.run["pending"] is None and not any(i["key"] == "tampa" for i in app.run["items"])
app.run["pending"] = dict(offer, key="gorro"); app.pending_since = time.time() - 999
app.run["energy"] = 0; app.busy_until = 0; app.tick(); assert app.run["pending"]   # sem energia: espera
app.state["mode"] = "auto"; app.change_mode(); assert app.run["pending"] is None  # trocar p/ auto resolve
# reabrir com pendência no save
app.state["mode"] = "interativo"; app.run["pending"] = dict(offer, key="chapeu"); app.quit()
app3 = tp.PetApp(Args(demo=demo)); PENDING.clear(); app3.busy_until = 0; app3.run["energy"] = 5 * M.ROOM_COST
app3.tick(); assert app3.run["pending"] and app3.pending_since is not None
# pump nos dois modos
app3.state["mode"] = "interativo"; pump(app3, 300)
```

No `pump`, antes de `app.tick()`, envelhecer a pendência (`app.pending_since = 0` se houver) para o teste não travar. Rodar o bloco para `demo=False` (o laço atual já cobre os dois).

- [ ] **Step 2: Rodar e ver falhar.** Run: `python tests/test_gui.py`. Expected: `AttributeError: ... 'choose'`.

- [ ] **Step 3: Implementar.**
  - `DEFAULT_STATE["mode"] = "auto"`. Menu: cascata `"Modo"` com radiobuttons `"Auto"` e `"Interativo"` → `change_mode`. Ao trocar para auto com pendência: `resolve_pending` e animar.
  - `tick`: se `run["pending"]`: `pending_since` vazio → `now`, e `show_choice()`; se `mode == "auto"`, ou se `now - pending_since >= CHOICE_WINDOW_S` e `M.can_enter(run)` → `resolve_pending`, animar, `close_choice()`; senão `update_choice()` e **não** chamar `play_room`.
  - `play_room` passa `mode=self.state["mode"]`; com `ev["pending"]` mostra o ícone do item e abre o painel.
  - Painel: `tk.Toplevel` sem borda, `bg=PANEL_BG` e borda `PANEL_EDGE`, posicionado como `popup` (ao lado da janela do pet). Conteúdo: ícone (`art_img`), nome na cor da raridade (`RAR_COLOR` ou `TEXT` se comum) + nome da raridade, `"Pegar: " + fx_text(item_fx)`, `"Consumir: +n ♥"` ou `"+n escudo"`, botões **Pegar** e **Consumir** (`bg=PANEL_EDGE`, `fg=TEXT`), barrinha (`tk.Canvas`) do tempo restante e o texto `"N salas esperando"` quando `int(energy // room_cost) >= 1`. `update_choice` só mexe na barrinha e no texto. `close_choice` destrói o painel (tolerando `TclError`).
  - `choose(choice)`: `M.choose_pending(run, meta, choice)`, animar (pegar → `refresh_look()` + `burst`; consumir → floater verde ou azul), `close_choice()`, `pending_since = None`, `save()`.
  - `show_stats` mostra o modo atual.

- [ ] **Step 4: Rodar tudo.** Run: os 5 testes. Expected: todos `ok`, sem `erro` no log.

- [ ] **Step 5: Ver na tela.** `python tokenlike.py --demo`, trocar para Interativo no menu, esperar um baú: o painel aparece, a barrinha esvazia, os botões funcionam, "N salas esperando" aparece.

- [ ] **Step 6: Commit.** `git commit -am "feat: modo interativo com janela de escolha"`

---

### Task 6: Balanceamento e documentação

**Files:**
- Modify: `masmorra.py` (só números)
- Modify: `CLAUDE.md`, `LEIA-ME.md`, `README.md`

- [ ] **Step 1: Ajustar.** Rodar `python tools/simular.py` e mexer nos números até: passou do 1º chefe ≈ 0.40 (0.35–0.45), p90 ≈ 14 (13–16), max ≈ 20 (18–24). Ordem das alavancas: pesos de raridade e `RAR_MULT`; `consume`; chance de item no baú (hoje 75%) e preço da loja; só então `MON_HP`/`MON_ATK`/`BOSS_HP`/`BOSS_ATK`.

- [ ] **Step 2: Rodar tudo.** Run: os 5 testes + simulador. Expected: todos `ok`; números do simulador dentro das faixas.

- [ ] **Step 3: Documentação.**
  - `CLAUDE.md`: em "Arquivos", adicionar `visual.py` e os dois testes novos. Atualizar "Comandos", "Como as peças se encaixam" (itens em lista, raridade, pendência e janela, escudo, tetos, números novos do simulador) e "Para adicionar coisas" (item novo = `ITEM_ART` + `ITEMS` com `rarities`, `consume`, `look`; sem `slot`).
  - `LEIA-ME.md` e `README.md`: reescrever o item "Itens" de "Como a masmorra funciona" (empilham, raridade com cores, pegar/consumir, modos) e o menu (opção Modo).

- [ ] **Step 4: Commit.** `git commit -am "chore: rebalanceia itens empilháveis e atualiza docs"`
