# Leva 0: ferramentas 32 px + Slime e Fantasma expressivos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Infra para heróis de 32 px (gerador de folha com espelho e acréscimo de estágio, traço passivo, contadores de conquista, prévia) e Slime + Fantasma redesenhados em 32 px com gestos por estado.

**Architecture:** Arte em grades de texto 32×32 num pacote novo `herois/` (um módulo por herói, mesmo formato). `herois/montar.py` (puro) transforma um módulo de herói nos 9 estados por estágio. `tools/gerar_folhas.py` escreve os PNGs a partir disso. O Slime embutido continua no app via `herois.slime`; o Fantasma vira só PNG. Traço e contadores entram em `masmorra.py`.

**Tech Stack:** Python 3 stdlib (app), Pillow não usado (gerador já escreve PNG com `escrever_png`).

**Spec:** `docs/superpowers/specs/2026-11-12-doze-herois-design.md` (Levas 1–3 terão planos próprios após a prévia desta).

## Global Constraints

- Só biblioteca padrão no app; Pillow só em `tools/` (não necessário aqui).
- Arte 100% original; nada reconhecível de outro jogo.
- Textos e nomes em pt-BR.
- Quadro de arte 32×32; `'.'` = transparente; letras = cores da paleta do herói.
- 9 estados `folha.ESTADOS`; idle, run_r, waving, jumping, failed, waiting, running, review desenhados (4–6 quadros); `run_l` = espelho de `run_r`, gerado.
- Cada estado tem um gesto próprio (anti-objetivo: só subir/achatar o corpo inteiro).
- 3 estágios visuais (padrão `[1, 4, 10]`) = mesmos quadros + acréscimo desenhado uma vez.
- Mudar fórmula em `masmorra.py` → subir `REGRAS_REV` (7 → 8). Rodar `tools/simular.py` no fim.
- Rodar todos os testes (`tests/*.py`) depois de cada task.

## Review Focus

- Herói com `"traço"` contendo chave fora de `stats()` (ex.: `"voar"`): herói ignorado com log, app não cai. → teste na Task 1.
- Save antigo sem `run["traco"]`/contadores: carrega e joga normal. → teste na Task 1 e Task 2 (`migrate_run`).
- Acréscimo de estágio saindo da grade 32×32 num quadro de pulo: é cortado, não dá IndexError. → teste na Task 3.
- Herói 32 px na GUI fica do mesmo tamanho do de 16 px (k=2, `px_heroi = px/2`). → teste na Task 4.
- Estado com menos de 8 quadros na folha (5 quadros): a grade 8×9 repete ciclicamente e o leitor não vê célula vazia. → teste na Task 3.

---

### Task 1: Traço passivo

**Files:**
- Modify: `masmorra.py` (`new_run`, `migrate_run`, `stats`, `REGRAS_REV`)
- Modify: `tokenlike.py` (`CharacterDef`, loader de `character.json`, onde chama `M.new_run`, menu de heróis e tela de Status)
- Test: `tests/test_itens.py`, `tests/test_gui.py`

**Interfaces:**
- Produces: `M.new_run(char_key, base_stats, run_id, traco: dict | None = None)` grava `run["traco"]` (dict, padrão `{}`); `stats(run)` soma `run.get("traco", {})` como item **sem** `_scale`, antes dos tetos. `CharacterDef.traco: dict`. `M.fx_text(fx)` já existe e serve para mostrar o traço.

- [ ] **Step 1: testes falhando** em `tests/test_itens.py`:
  - `test_traco_soma_sem_escalar`: `run = M.new_run("x", {"hp": 20}, 1, traco={"envenenar": 0.1, "maxhp": -4})`; `st = M.stats(run)`; `st["envenenar"] == 0.1` e `st["maxhp"] == 16`; com item lendário que tem `envenenar`, a parte do traço continua 0.1 (total = 0.1 + valor escalado do item, respeitando `MAX_ELEM_CHANCE`).
  - `test_traco_save_antigo`: run sem a chave `"traco"` → `M.stats(M.migrate_run(run))` igual a antes.
  - `test_traco_chave_invalida_ignora_heroi` (em `test_gui.py`, junto dos testes de `character.json`): `"traço": {"voar": 1}` → herói fora de `all_characters()` e linha no log sem quebrar.
- [ ] **Step 2:** rodar `python tests/test_itens.py` → FAIL.
- [ ] **Step 3:** implementar. Loader lê `data.get("traço") or data.get("traco") or {}`, valida chaves contra as de `stats()` (`ValueError` → herói ignorado). `REGRAS_REV = 8`. Menu de heróis: `f"{c.name} — {M.fx_text(c.traco)}"` quando houver traço; tela de Status mostra linha "Traço: …".
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: traço passivo do herói (character.json)`.

### Task 2: Contadores de conquista na run

**Files:**
- Modify: `masmorra.py` (`new_run`, `migrate_run`, `enter_room`)
- Test: `tests/test_combate.py`

**Interfaces:**
- Produces: `run["cont"]` = `{"esquivas": int, "bloqueios": int, "mortes_veneno": int, "mortes_queima": int, "horda4": int}`; `migrate_run` faz `setdefault` com zeros. `enter_room` soma a partir dos `passos` de `combate`: passo do inimigo no pet com `dodge=True` → esquivas; `bloqueado=True` → bloqueios; inimigo que chega a hp ≤ 0 num passo `dot=True` com `status` "Veneno"/"Queimadura" → mortes_*; horda de 4 vencida → horda4. Nenhuma conquista nova nesta task (vêm nas levas dos heróis).

- [ ] **Step 1: testes falhando** em `tests/test_combate.py`, com run montada à mão e `random.Random(SEED)`:
  - `test_conta_esquivas_e_bloqueios`: base `dodge` 0.5, item com `bloqueio` 2; após N salas de monstro, `run["cont"]["esquivas"]` = nº de passos com `dodge` e `bloqueios` = nº com `bloqueado` (somar os passos de cada `ev` e comparar).
  - `test_conta_morte_por_status`: inimigo com hp 1 e status veneno aplicado; matar no dano de status → `mortes_veneno == 1`.
  - `test_cont_save_antigo`: `migrate_run` em run sem `"cont"` cria os zeros.
- [ ] **Step 2:** rodar `python tests/test_combate.py` → FAIL.
- [ ] **Step 3:** implementar (se `ev` não expõe os passos, guardar a contagem dentro de `enter_room` logo após cada `combate`).
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: contadores de esquiva, bloqueio, morte por status e horda de 4`.

### Task 3: Montagem 32 px e gerador de folha

**Files:**
- Create: `herois/__init__.py` (vazio), `herois/montar.py`
- Modify: `tools/gerar_folhas.py` (quadro 32, `CEL = 40`, prévia nova)
- Test: `tests/test_folha.py`

**Interfaces:**
- Formato de um módulo de herói (`herois/<chave>.py`), usado pelas Tasks 4–5 e pelas Levas 1–3:
  - `PAL: dict[str, str]` (letra → `#rrggbb`)
  - `QUADROS: dict[str, list[list[str]]]` com os 8 estados desenhados (sem `run_l`), cada quadro 32 linhas de 32 chars.
  - `ESTAGIOS: list[dict]`: `[{"title": str, "floor": int, "extra": list[str] | None}, ...]` (3 itens; o 1º com `extra=None`).
  - `ANCORA: dict[str, list[tuple[int, int]]]`: ponto (x, y) onde o canto superior-esquerdo do `extra` vai em cada quadro de cada estado desenhado (mesmo comprimento de `QUADROS[e]`).
- Produces: `montar.estados(heroi, estagio: int) -> dict[str, list[list[str]]]` com os 9 estados; `montar.validar(heroi) -> None` (`AssertionError` com estado/quadro no texto). `gerar_folhas.gerar_folha(path, est, pal)` aceita quadros 32×32 (cel 40, base alinhada ao fundo da célula, 8 colunas repetindo ciclicamente).

- [ ] **Step 1: testes falhando** em `tests/test_folha.py`, com um herói falso de 2 cores criado no teste (`types.SimpleNamespace`):
  - `test_run_l_espelha_run_r`: `est["run_l"][i] == [l[::-1] for l in est["run_r"][i]]`.
  - `test_extra_na_ancora`: estágio 1 com `extra=["X"]` → em todo quadro de todo estado, pixel `(ax, ay)` da âncora é `"X"` (no `run_l`, em `31 - ax`).
  - `test_extra_fora_corta`: âncora `(31, -1)` com extra 2×2 → sem exceção, grade continua 32×32.
  - `test_validar`: quadro com 31 linhas, quadro todo `'.'`, estado faltando ou com 3 quadros → `AssertionError`.
  - `test_folha_32_le_de_volta`: `gerar_folha` num tmp com 5 quadros por estado → `folha.ler_folha`/corte devolve 9 estados, nenhum quadro vazio, altura aparada ≤ 32.
- [ ] **Step 2:** rodar `python tests/test_folha.py` → FAIL.
- [ ] **Step 3:** implementar `herois/montar.py` (sobrepor `extra` com corte nas bordas; `'.'` do extra não apaga). `gerar_folhas.py`: `CEL = 40`; `preview(path, herois, esc=4)` com uma faixa por estágio, até 6 quadros por estado; `main()` percorre `HEROIS = ["slime", "fantasma"]` via `importlib.import_module("herois." + k)`, chama `validar`, gera `characters/<k>/folha{1..3}.png` (exceto `slime`, que é embutido) e a prévia `tools/saida/preview_herois.png`.
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: montagem de heróis 32 px e gerador de folha`.

### Task 4: Slime 32 px expressivo (embutido)

**Files:**
- Create: `herois/slime.py`
- Modify: `tokenlike.py` (`builtin_characters` usa `herois.slime` + `montar.estados`; piscar)
- Modify: `arte_herois.py` (remover as grades e funções de 16 px que ficarem sem uso)
- Test: `tests/test_gui.py`, `tests/test_reader.py` (se testa a arte do slime)

**Interfaces:**
- Consumes: formato de herói e `montar.estados` (Task 3).
- `ESTAGIOS` do Slime: 3 estágios, títulos "Gotinha" (1), "Slime" (4), "Rei Slime" (10); o acréscimo do 2º é um elmo pequeno, do 3º uma coroa. (Hoje são 4 estágios em 1/3/8/15; passam a 3 como os outros heróis.)

- [ ] **Step 1: testes falhando** em `tests/test_gui.py`:
  - `test_slime_32`: `builtin_characters()[0]` tem 3 estágios, cada um com os 9 `estados`, quadros 32×32.
  - `test_heroi32_mesmo_tamanho`: após `refresh_look` com o Slime, `k == 2` e a altura do pet desenhado em px de tela fica a ±2 px de `16 * app.px`.
- [ ] **Step 2:** rodar `python tests/test_gui.py` → FAIL.
- [ ] **Step 3:** desenhar `herois/slime.py`. Gestos obrigatórios: idle (respira + olhos piscam num quadro); run_r (estica para frente, gotinha ficando para trás, olhos na direção); waving (bracinho de gosma sai do lado e balança); jumping (agacha, estica no ar, achata ao cair); failed (derrete numa poça, olhos em X no último); waiting (cabeça pende, "z" subindo); running (morde/investe com boca aberta e olhos bravos); review (olha para cima, "?" aparece). `blink` = quadro do idle com os olhos fechados. Remover código de 16 px morto.
- [ ] **Step 4:** `python tools/gerar_folhas.py --so-preview`; abrir `tools/saida/preview_herois.png` e conferir cada gesto. Todos os testes → PASS.
- [ ] **Step 5:** commit `feat: Slime redesenhado em 32 px com gestos por estado`.

### Task 5: Fantasma 32 px expressivo

**Files:**
- Create: `herois/fantasma.py`
- Modify: `tools/gerar_folhas.py` (remover as grades de 16 px do Fantasma)
- Modify: `characters/fantasma/folha1.png..folha3.png` (regenerados), `characters/fantasma/character.json` (títulos/andares se mudarem)
- Test: `tests/test_folha.py`

**Interfaces:**
- Consumes: Task 3. Estágios: Fantasminha (1), Fantasma (4, acréscimo: correntinha), Fantasma Mago (10, acréscimo: chapéu de mago). Stats e `unlock` do JSON ficam iguais.

- [ ] **Step 1: teste falhando** `test_fantasma_folhas`: as 3 folhas existem, `ler_folha` dá 9 estados com ≥ 4 quadros e altura aparada > 16 (prova que é 32 px).
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** desenhar. Gestos: idle (cauda ondula); run_r (inclina e deixa rastro); waving (mãozinha de lençol); jumping (encolhe e dispara para cima); failed (some aos poucos, buracos no lençol); waiting (cochila flutuando, z); running (avança com boca "Buu" aberta); review (coça a cabeça, "?"). Rodar `python tools/gerar_folhas.py`.
- [ ] **Step 4:** conferir a prévia; todos os testes → PASS.
- [ ] **Step 5:** commit `feat: Fantasma redesenhado em 32 px com gestos por estado`.

### Task 6: Fechamento da leva

**Files:**
- Modify: `CLAUDE.md` (pacote `herois/`, formato do módulo de herói, `traço`, `run["cont"]`, `REGRAS_REV` 8, gerador 32 px), `LEIA-ME.md` e `README.md` (campo `traço` no `character.json`)

- [ ] **Step 1:** rodar todos os `tests/*.py` → PASS; `python tools/simular.py` → METAS continuam dentro (Slime sem traço, só muda `REGRAS_REV`).
- [ ] **Step 2:** atualizar docs.
- [ ] **Step 3:** commit `docs: heróis 32 px, traço e contadores`.
- [ ] **Step 4:** mostrar a prévia ao dono (portão da leva) antes de planejar a Leva 1.
