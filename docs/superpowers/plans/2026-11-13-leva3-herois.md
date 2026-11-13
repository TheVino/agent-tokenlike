# Leva 3: Cavaleiro Oco, Corvo Mensageiro, Alquimista e Freira das Cinzas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Os 4 últimos heróis autorais (14 no total), cada um com traço passivo e conquista temática; balanceamento final e docs.

**Architecture:** Igual às Levas 1 e 2. Cada herói = `herois/<chave>.py` + `characters/<chave>/character.json` + `folha1..3.png` (`tools/gerar_folhas.py`, lista `HEROIS`). Conquistas em `masmorra.ACHIEVEMENTS` + `_check_achievements`.

**Tech Stack:** Python 3 stdlib.

**Spec:** `docs/superpowers/specs/2026-11-12-doze-herois-design.md`

## Global Constraints

- Só biblioteca padrão no app; arte 100% original (arquétipos; nada reconhecível de jogo/filme/anime).
- Textos pt-BR. Estilo sombrio e fofo.
- Quadros 32×32, 4–6 por estado, 8 estados desenhados (`run_l` gerado). Gestos **grandes** (braços/objetos ≈5–9 px, contorno escuro); "z"/"?" de `herois/comum.py`. Objeto-símbolo no `running` e, quando der, no `idle`/`waving`.
- 3 estágios, andares `[1, 4, 10]`; acréscimo desenhado uma vez, colado em **todos** os quadros via `ANCORA` (inclusive `failed`: escolher acréscimo que faça sentido caído). Acréscimo inteiro dentro do quadro mesmo quando o corpo desloca; folga no topo no quadro mais alto do pulo; sem detalhe trocando de lado entre quadros.
- Peças repetidas vão para `herois/comum.py`; um herói nunca importa de outro.
- Stats base 20/3/0 salvo a tabela; traço só com campos aditivos de `stats()` (sem `crescer`).
- Balanceamento: cada herói passa do 1º chefe em **30–50%** (1.500 runs só dele); ajustar só números do `character.json`.

## Tabela da leva (spec)

| Chave | Nome | Estágios (título) | Traço | Stats | Conquista (chave → regra) |
|---|---|---|---|---|---|
| `cavaleiro` | Cavaleiro Oco | Armadura Vazia / Cavaleiro Oco (elmo com pluma) / Paladino Oco (estandarte nas costas) | `{"bloqueio": 1}` | 20/3/0, `spd` 8 | `bloqueio10` "Bloquear 10 golpes numa run" → `cont["bloqueios"] >= 10` |
| `corvo` | Corvo Mensageiro | Filhote de Corvo / Corvo Mensageiro (bolsa de cartas) / Corvo Arauto (capuz de pena) | `{"duplo": 0.08}` | 20/3/0, `spd` 12 | `chefes3` "Vencer 3 chefes no total" → `meta["chefes"] >= 3` (contador novo, soma em toda vitória sobre chefe; save antigo sem a chave = 0) |
| `alquimista` | Alquimista | Aprendiz de Alquimia / Alquimista (cinto de frascos) / Mestre Alquimista (óculos de lente dupla no chapéu) | `{"desconto": 0.2, "cura_andar": 3}` | 20/3/0 | `consumir10` "Consumir 10 itens numa run" → `len(run["consumed"]) >= 10` |
| `freira` | Freira das Cinzas | Noviça das Cinzas / Freira das Cinzas (terço de ossinhos) / Abadessa das Cinzas (véu longo com brasas) | `{"lifesteal": 1, "congelar": 0.06}` | 20/3/0 | `morrer10` "Morrer 10 vezes" → `meta["runs"] >= 10` (conferido também logo depois de `die`) |

Títulos e acréscimos são sugestão; o construtor pode trocar dentro do tema.

## Review Focus

- `chefes3` e `morrer10` são meta: valem entre runs; save antigo sem `meta["chefes"]` não quebra. → Task 1.
- `morrer10` dispara na sala em que o pet morre pela 10ª vez (o `_check_achievements` roda depois de `die`). → Task 1.
- Conquista não repete em `ev["unlocks"]`. → Task 1.
- `spd` base do herói (8 e 12) chega em `stats()` e no combate. → Tasks 2 e 3.
- Acréscimo e `failed` legível (≥ 40 pixels no último quadro), como nas levas anteriores. → cada task de herói.

---

### Task 1: Conquistas dos 4 heróis

**Files:** Modify `masmorra.py` (`ACHIEVEMENTS`, `_check_achievements`, contador `meta["chefes"]` onde `run["bosses"] += 1`), `tests/test_itens.py`.

- [ ] **Step 1: testes falhando:** cada conquista abaixo/no limite/não repete (molde `_ach` da Leva 2); meta sem a chave `chefes` funciona; vencer chefe soma em `meta["chefes"]`; 10ª morte numa run de verdade concede `morrer10` no `ev` da sala da morte.
- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar. **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: conquistas dos heróis da leva 3`.

### Tasks 2–5: um herói por task (`cavaleiro`, `corvo`, `alquimista`, `freira`, nesta ordem)

Mesmo molde da Leva 2; a Task N usa a linha N−1 da tabela.

**Files:** Create `herois/<chave>.py`, `characters/<chave>/character.json`, `folha1..3.png` (gerados). Modify `tools/gerar_folhas.py` (`HEROIS`), `tests/test_folha.py`.

- [ ] **Step 1: teste** `test_heroi_<chave>` igual ao `test_heroi_boneca` (+ `spd` em `stats()` para cavaleiro e corvo).
- [ ] **Step 2:** desenhar. Gestos: idle mexe o símbolo (olhinho espia pelo visor; carta balança no bico; frasco borbulha; terço balança); failed no tema (armadura desaba em peças e o olhinho foge; corvo cai e a carta voa; frasco quebra e fumaça; freira vira montinho de cinza com o véu por cima); waiting cochila com "z"; running golpe com o símbolo (espada/escudo, bicada com a carta, arremesso de frasco, terço/brasa); review com "?". `python tools/gerar_folhas.py` e conferir a prévia com zoom.
- [ ] **Step 3:** taxa de passar do 1º chefe (1.500 runs) dentro de 30–50%; senão ajustar números.
- [ ] **Step 4:** todos os testes → PASS. **Step 5:** commit `feat: herói <Nome>`.

### Task 6: Balanceamento final e docs

**Files:** `CLAUDE.md`, `README.md`, `LEIA-ME.md` (lista dos 14 heróis e como liberar), `characters/*/character.json` (só se preciso).

- [ ] **Step 1:** `python tools/estatisticas.py --sem-abrir` e `python tools/simular.py`: METAS da calibração dentro; taxa dos 14 heróis em 30–50%.
- [ ] **Step 2:** docs; todos os testes → PASS.
- [ ] **Step 3:** commit `chore: balanceamento final e docs dos 14 heróis`.
- [ ] **Step 4:** prévia ao dono (portão final).
