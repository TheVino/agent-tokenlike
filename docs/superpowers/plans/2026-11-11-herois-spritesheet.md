# Heróis por spritesheet — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Heróis a partir de um spritesheet de 9 linhas (formato do prompt do AgentPet/Petdex), com corte automático, estados animados, itens escalados e pets do Petdex instalados.

**Architecture:** Módulo puro novo `folha.py` (corte e redução sobre uma grade de opacidade, sem tkinter). `visual.py` ganha escala `k`. `tokenlike.py` lê os PNGs (PhotoImage), monta `CharacterDef` com estados, procura pastas do Petdex e usa os estados na GUI, mantendo o pet do mesmo tamanho na tela.

**Tech Stack:** Python 3.9+, só biblioteca padrão. Testes com `assert` em scripts.

**Spec:** `docs/superpowers/specs/2026-11-11-herois-spritesheet-design.md`

## Global Constraints

- Ler `CLAUDE.md`. Sem rede; nunca copiar/distribuir pets da comunidade; só `.png`; texto sobre `PANEL_BG`; pt-BR.
- Linhas da folha: 1 Idle, 2 Run Right, 3 Run Left, 4 Waving, 5 Jumping, 6 Failed, 7 Waiting, 8 Running, 9 Review; linha ausente/vazia → Idle.
- Corte: grade fixa 8 colunas × 9 (ou 11) linhas quando o tamanho da folha bate; senão faixas transparentes; > 8 quadros numa linha → juntar pedaços estreitos ao vizinho, ainda > 8 → 8 células iguais; alinhamento pela base, caixa comum por folha.
- Redução: menor inteiro N com `altura/N ≤ 48`; `k = max(1, round(altura_final / 16))`; na tela o herói ocupa o mesmo espaço do Slime (`px_heroi = px × 16 / altura_final`, com piso 1).
- Pet sem `character.json`: 1 estágio, andar 1, título = nome, stats padrão (`hp` 20, `atk` 3, `spd` 10), liberado; menu "Comunidade". Pastas Petdex: `~/.petdex/pets/<slug>/`, `~/.codex/pets/<slug>/`; nome do `pet.json` (`name`) ou da pasta; WebP-only → log "converta para PNG".
- Composição: só ao mudar itens/estado-chave; tick só troca imagens; composição < 3 s no `test_gui`.
- Todos os testes atuais passam; `test_gui` com `SEED` 1..5 na última task.

## Review Focus

1. **Folha gerada por IA "suja"** (pixels semitransparentes quase invisíveis entre quadros, ruído no fundo): o corte usa limiar de opacidade (alpha > 128) e ignora ilhas de 1–2 pixels. Teste na Task 1.
2. **Herói enorme (ex.: 1536×1872)**: carrega em tempo razoável (leitura de pixels uma vez, com cache), sem travar a GUI por segundos. Teste na Task 3 (folha sintética grande no `test_gui`, tempo < 3 s com tkinter falso).
3. **Pasta da comunidade quebrada** (PNG corrompido, só WebP, `pet.json` inválido): ignorada com log, sem "erro" que derrube o app. Teste na Task 3.
4. **Herói pequeno (16 px)**: `k = 1`, composição idêntica à de hoje. Teste na Task 2.
5. **Estados simultâneos** (escolha pendente enquanto descansa): prioridade definida e testada (escolha > luta > morte > descanso > parado). Teste na Task 4.

---

### Task 1: `folha.py` — corte e redução puros

**Files:** Create `folha.py`; Test `tests/test_folha.py`

**Interfaces (produz):**
- `cortar(w: int, h: int, opaco, grade: tuple[int, int] | None = None) -> list[list[tuple[int,int,int,int]]]`: `opaco(x, y) -> bool`; devolve, por linha (até 11), a lista de caixas `(x0, y0, x1, y1)` (exclusivas) de cada quadro, já com as regras de junção/8 células e ilhas ≤ 2 px ignoradas. `grade` = (colunas, linhas) força grade fixa.
- `detectar_grade(w, h) -> tuple[int,int] | None`: (8, 9) ou (8, 11) se `w % 8 == 0` e `h % 9` ou `h % 11 == 0` com células quase quadradas (razão 0,7–1,4); senão `None`.
- `caixa_comum(caixas) -> tuple[int,int]`: largura e altura máximas.
- `fator_reducao(altura: int, maximo: int = 48) -> int`.
- `ESTADOS = ("idle", "run_r", "run_l", "waving", "jumping", "failed", "waiting", "running", "review")`.

- [ ] Testes: folha sintética (grade de booleanos) com 9 linhas de 4–8 quadros de larguras diferentes → contagens certas; linha vazia → `[]`; um quadro com mão solta (2 ilhas) não vira 2 quadros; linha com 12 pedaços → 8; ilha de 1 px ignorada; `detectar_grade(1536, 1872) == (8, 9)`; `fator_reducao(208) == 5`, `fator_reducao(64) == 2`, `fator_reducao(16) == 1`. Ver falhar, implementar, passar, commit `feat: folha.py corta spritesheets de 9 linhas`.

### Task 2: Escala `k` em `visual.py` e na renderização

**Files:** Modify `visual.py` (`compose(..., k: int = 1)`, `LOOK_BOX` escalado via `look_box(k)`), `tokenlike.py` (`render_map(pm, s)` usado com `px_heroi`); Test `tests/test_visual.py`

**Interfaces:** `visual.look_box(k) -> tuple` (= `LOOK_BOX` × k); `compose(base, looks, arts, fase=0, k=1)`: objetos e adesivos ampliados por `k` (cada pixel vira k×k), posições/âncoras na caixa do corpo; efeitos de contorno inalterados (já no contorno do herói grande); espessuras de chamas/gotas etc. escaladas por `k` quando fizer sentido (decisão do implementador, documentada).

- [ ] Testes: `compose(slime, looks, arts, k=1) ==` resultado antigo (todos os testes atuais de visual seguem passando); com um corpo 48×48 e `k=3`, o objeto `topo` tem 3× a largura do de `k=1` num corpo 16×16; o ponto de apoio (centro da base) é o mesmo entre fases e entre k. Commit `feat: escala k nos looks para heróis grandes`.

### Task 3: Carregar heróis por folha e do Petdex

**Files:** Modify `tokenlike.py` (`CharacterDef`, `load_png_characters`, novo `load_petdex_characters`, `all_characters`, `spec_to_map` para recortes), `tests/test_gui.py`, `tests/test_reader.py`

**Interfaces:** `CharacterDef` ganha `estados: dict[str, list[spec]]` por estágio (`spec` de recorte `("sheet", path, box, N)`), `comunidade: bool`; `petdex_dirs() -> list[Path]` (`~/.petdex/pets`, `~/.codex/pets`, lidos na hora para o teste trocar HOME); leitura de pixels da folha **uma vez por arquivo** (cache em módulo, chave = caminho + mtime) com `PhotoImage.transparency_get` → grade de opacidade → `folha.cortar` → mapas reduzidos por N. `character.json` aceita `stages[].sheet`.

- [ ] Testes (HOME temporário, PNGs sintéticos gerados pelo próprio teste com o tkinter falso ou com dados embutidos): herói `characters/x/spritesheet.png` aparece com 9 estados; pasta `~/.petdex/pets/y/` com `pet.json {"name": "Yzinho"}` + PNG aparece como "Yzinho" (comunidade, liberado, stats padrão); pasta só com `.webp` é ignorada e o log contém "converta para PNG" (sem a palavra "erro"); `pet.json` inválido não derruba; folha 1536×1872 carrega em < 3 s com o fake. Commit `feat: heróis por spritesheet e pets do Petdex`.

### Task 4: Estados na GUI, menu Comunidade, docs

**Files:** Modify `tokenlike.py` (`tick`, `play_room`, `on_release` carinho, `on_death`, `evolve`, painel de escolha, `fill_char_menu`), `README.md`, `LEIA-ME.md`, `CLAUDE.md`; Test `tests/test_gui.py`

**Interfaces:** o tick escolhe a lista de quadros pelo estado atual com prioridade escolha pendente (`review`) > luta (`running`, enquanto a sala de combate anima) > morte (`failed`, antes da lápide) > descanso/sono (`waiting`) > parado (`idle`); `waving` por ~1 s após o carinho; `jumping` na evolução e ao vencer chefe; heróis sem estados (Slime, PNG antigo) seguem como hoje. Menu "Herói da próxima run" com separador e seção "Comunidade". Docs: formato da folha, onde colocar, pastas Petdex lidas, aviso de licença dos pets da comunidade, e o prompt adaptado (quadros ≤ 64×64, contorno de 1 px, sem chão/sombra).

- [ ] Testes: com um herói de folha, centenas de salas sem exceção; morte mostra quadros `failed`; descanso `waiting`; pendência `review` tem prioridade sobre descanso; carinho `waving`; Slime inalterado; `test_gui` com `SEED` 1..5. Commit `feat: estados do spritesheet na GUI e docs do prompt`.
