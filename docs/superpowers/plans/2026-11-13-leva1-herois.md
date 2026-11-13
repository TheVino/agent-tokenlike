# Leva 1: Médico da Peste, Bruxa do Pântano, Coveiro e Ceifeirinho — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 heróis autorais novos em 32 px, cada um com traço passivo e conquista temática que o libera.

**Architecture:** Cada herói = `herois/<chave>.py` (formato da Leva 0: `PAL`, `QUADROS`, `ESTAGIOS`, `ANCORA`, validado por `herois.montar.validar`) + `characters/<chave>/character.json` + `folha1..3.png` gerados por `tools/gerar_folhas.py` (lista `HEROIS`). Conquistas em `masmorra.ACHIEVEMENTS` + `_check_achievements`, usando `run["cont"]` da Leva 0.

**Tech Stack:** Python 3 stdlib.

**Spec:** `docs/superpowers/specs/2026-11-12-doze-herois-design.md`

## Global Constraints

- Só biblioteca padrão no app; arte 100% original (médico da peste, bruxa, coveiro e ceifador são arquétipos; nada de personagem reconhecível de jogo/filme/anime).
- Textos pt-BR. Estilo: sombrio e fofo, como Slime e Fantasma.
- Quadros 32×32, 4–6 por estado, 8 estados desenhados (`run_l` gerado). Gestos **grandes**: braços/objetos ≈5–9 px com contorno escuro; "z"/"?" ≈5×7+ com contorno. Cada estado com gesto próprio (spec, "Objetivos"); o objeto-símbolo aparece no `running` (golpe) e, quando der, no `idle`/`waving`.
- 3 estágios, andares `[1, 4, 10]`; o acréscimo é desenhado uma vez e acompanha o corpo via `ANCORA` (o dono aprovou esse efeito na Leva 0).
- Referência de estilo e de técnica: `herois/slime.py` e `herois/fantasma.py`. Lições da Leva 0: acessório de topo precisa de folga no quadro mais alto do pulo; quadros finais do `failed` não podem ficar quase invisíveis.
- Stats base (`hp`, `atk`, `def`) iguais aos do Slime (20/3/0) salvo o que a tabela diz; traço só com campos aditivos de `stats()` (não usar `crescer`).
- Balanceamento: mediana de andar de cada herói a ±2 da do Slime (seção "Heróis" de `python tools/estatisticas.py --sem-abrir`); ajustar só números do `character.json`.

## Tabela da leva (spec)

| Chave | Nome | Estágios (título) | Traço | Stats | Conquista (chave → regra) |
|---|---|---|---|---|---|
| `medico` | Médico da Peste | Aprendiz da Peste / Médico da Peste (chapéu de aba larga) / Doutor da Praga (capa) | `{"envenenar": 0.10}` | 20/3/0 | `veneno1` "Matar um inimigo com veneno" → `run["cont"]["mortes_veneno"] >= 1` |
| `bruxa` | Bruxa do Pântano | Bruxinha / Bruxa do Pântano (caldeirãozinho flutuando ao lado) / Matriarca do Brejo (corvo/vagalumes no chapéu) | `{"queimar": 0.08, "sorte": 0.2}` | 20/3/0 | `elementos3` "Pegar 3 itens elementais numa run" → itens em `run["items"]` cujo `fx` tem alguma chave de `ELEMENTOS.values()` ≥ 3 |
| `coveiro` | Coveiro | Ajudante de Coveiro / Coveiro (lampião) / Guardião do Cemitério (chapéu alto) | `{"gold": 0.4}` | 20/3/0 | `ouro300` "Juntar 300 de ouro numa run" → `run["gold"] >= 300` |
| `ceifeirinho` | Ceifeirinho | Ceifeirinho / Ceifador (capuz maior) / Ceifador Ancião (lanterna de almas) | `{"crit": 0.08}` | 16/3/0 | `horda4` "Vencer uma horda de 4 inimigos" → `run["cont"]["horda4"] >= 1` |

Títulos de estágio e acréscimos são sugestão; o construtor pode trocar dentro do tema.

## Review Focus

- Conquista dispara na sala certa e uma vez só (já desbloqueada não repete em `ev["unlocks"]`). → testes na Task 1.
- Herói bloqueado aparece no menu com o texto da conquista e não pode ser escolhido; `next_char` apontando para herói bloqueado cai no Slime. → teste na Task 1.
- Traço do herói aparece no menu/Status (`fx_text`) com texto não vazio. → teste na Task 1.
- Acessório de topo não é cortado no quadro mais alto do pulo. → assert em cada task de herói (pixel do acréscimo presente em todos os quadros de `estados(h, 1)` e `estados(h, 2)`).
- `failed` legível: último quadro com ≥ 40 pixels opacos. → assert em cada task de herói.

---

### Task 1: Conquistas e cadastro dos 4 heróis

**Files:**
- Modify: `masmorra.py` (`ACHIEVEMENTS`, `_check_achievements`), `tests/test_itens.py` ou `tests/test_combate.py`, `tests/test_gui.py`

**Interfaces:**
- Produces: chaves `veneno1`, `elementos3`, `ouro300`, `horda4` em `M.ACHIEVEMENTS` (texto da tabela). As Tasks 2–5 usam essas chaves no `"unlock"`.

- [ ] **Step 1: testes falhando:** para cada conquista, run montada à mão com o contador/condição logo abaixo do limite → `_check_achievements` não concede; no limite → concede e aparece em `ev["unlocks"]`; chamar de novo → não repete. `elementos3`: 2 itens elementais + 1 não elemental não concede; 3 elementais concede. Em `test_gui.py`: herói falso com `"unlock": "ouro300"` aparece desabilitado com o texto da conquista; com `next_char` nele e conquista ausente, a run começa com o Slime.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: conquistas dos heróis da leva 1`.

### Tasks 2–5: um herói por task (`medico`, `bruxa`, `coveiro`, `ceifeirinho`, nesta ordem)

Mesmo molde para as quatro; a Task N usa a linha N−1 da tabela.

**Files:**
- Create: `herois/<chave>.py`, `characters/<chave>/character.json`, `characters/<chave>/folha1.png..folha3.png` (gerados)
- Modify: `tools/gerar_folhas.py` (`HEROIS` += chave), `tests/test_folha.py`

**Interfaces:**
- Consumes: formato de herói e `herois.montar` (Leva 0); chave de conquista da Task 1.
- `character.json`: `{"name", "unlock", "stats", "traço", "frame_ms": 600, "stages": [{"title", "floor", "sheet": "folhaN.png"}]}` com os valores da tabela.

- [ ] **Step 1: teste falhando** `test_heroi_<chave>` em `tests/test_folha.py`: `validar(herois.<chave>)` passa; as 3 folhas leem 9 estados com ≥ 4 quadros e altura aparada > 16; o carregador de `tokenlike` devolve o herói com `traco` e `unlock` da tabela; o acréscimo de cada estágio > 0 aparece em todos os quadros; último quadro do `failed` com ≥ 40 pixels opacos.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** desenhar `herois/<chave>.py`. Gestos por estado (spec): idle mexe o símbolo; run_r corre de lado olhando para a frente; waving acena com mão ou símbolo; jumping agacha/salta/cai; failed cai ou se desfaz no tema (médico: máscara cai; bruxa: derrete em poça de brejo; coveiro: cai na própria cova/lampião apaga; ceifeirinho: manto desaba vazio); waiting cochila com "z"; running golpe com o símbolo (frasco de ervas, colherada do caldeirão/feitiço, pá, foice); review pensa com "?". Rodar `python tools/gerar_folhas.py` e inspecionar `tools/saida/preview_herois.png` com zoom até cada gesto ler de relance.
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: herói <Nome>`.

### Task 6: Balanceamento e fechamento

**Files:**
- Modify: `characters/<chave>/character.json` (só números, se preciso), `CLAUDE.md` (lista de heróis e conquistas novas)

- [ ] **Step 1:** `python tools/estatisticas.py --sem-abrir` e `python tools/simular.py`; ler a seção "Heróis" no JSON gerado em `tools/saida/`. METAS da calibração continuam dentro.
- [ ] **Step 2:** herói com mediana fora de ±2 da do Slime → ajustar o traço/stats no `character.json` e repetir. Anotar no report os números antes/depois.
- [ ] **Step 3:** atualizar `CLAUDE.md`; todos os testes → PASS.
- [ ] **Step 4:** commit `chore: balanceia e documenta os heróis da leva 1`.
- [ ] **Step 5:** mostrar a prévia ao dono (portão da leva) antes da Leva 2.
