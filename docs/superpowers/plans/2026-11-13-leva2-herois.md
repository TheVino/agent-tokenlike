# Leva 2: Vela Viva, Cogumelo de Caverna, Inquisidor e Boneca de Pano — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 heróis autorais novos em 32 px, cada um com traço passivo e conquista temática que o libera.

**Architecture:** Igual à Leva 1. Cada herói = `herois/<chave>.py` (`PAL`, `QUADROS`, `ESTAGIOS`, `ANCORA`, validado por `herois.montar.validar`) + `characters/<chave>/character.json` + `folha1..3.png` gerados por `tools/gerar_folhas.py` (lista `HEROIS`). Conquistas em `masmorra.ACHIEVEMENTS` + `_check_achievements`, usando `run["cont"]`.

**Tech Stack:** Python 3 stdlib.

**Spec:** `docs/superpowers/specs/2026-11-12-doze-herois-design.md`

## Global Constraints

- Só biblioteca padrão no app; arte 100% original (vela viva, cogumelo, inquisidor e boneca de pano são arquétipos; nada de personagem reconhecível de jogo/filme/anime).
- Textos pt-BR. Estilo sombrio e fofo, como os heróis já feitos.
- Quadros 32×32, 4–6 por estado, 8 estados desenhados (`run_l` gerado). Gestos **grandes**: braços/objetos ≈5–9 px com contorno escuro; "z"/"?" de `herois/comum.py`. Cada estado com gesto próprio; o objeto-símbolo aparece no `running` e, quando der, no `idle`/`waving`.
- 3 estágios, andares `[1, 4, 10]`; acréscimo desenhado uma vez, acompanha o corpo via `ANCORA`.
- Peças repetidas vão para `herois/comum.py`; um herói nunca importa de outro herói.
- Referência: `herois/slime.py`, `herois/fantasma.py`, `herois/medico.py`. Acessório de topo precisa de folga no quadro mais alto do pulo; quadros finais do `failed` legíveis.
- Stats base 20/3/0 salvo o que a tabela diz; traço só com campos aditivos de `stats()` (sem `crescer`).
- Balanceamento (regra nova, aprovada pelo dono em 2026-11-13): taxa de passar do 1º chefe de cada herói entre **30% e 50%** (1.500 runs por herói); ajustar só números do `character.json`.

## Tabela da leva (spec)

| Chave | Nome | Estágios (título) | Traço | Stats | Conquista (chave → regra) |
|---|---|---|---|---|---|
| `vela` | Vela Viva | Tôco de Vela / Vela Viva (chama maior) / Círio Antigo (castiçal) | `{"queimar": 0.12, "maxhp": -4}` | 20/3/0 | `queima1` "Matar um inimigo com queimadura" → `cont["mortes_queima"] >= 1` |
| `cogumelo` | Cogumelo de Caverna | Esporinho / Cogumelo de Caverna (esporos brilhando em volta) / Ancião do Micélio (chapéu com cogumelinhos) | `{"cura_sala": 1}` | 20/3/0 | `andar8cheio` "Chegar ao andar 8 com o HP cheio" → `run["floor"] >= 8` e `run["hp"] >= stats(run)` HP máx |
| `inquisidor` | Inquisidor | Noviço / Inquisidor (sino na cintura) / Grão-Inquisidor (mitra alta) | `{"def": 1, "espinhos": 0.1}` | 20/3/0 | `andar15` "Chegar ao andar 15" → `run["floor"] >= 15` |
| `boneca` | Boneca de Pano | Retalho / Boneca de Pano (laço de fita) / Boneca Remendada (agulha com linha nas costas) | `{"dodge": 0.1}` | 20/3/0 | `esquiva10` "Esquivar 10 golpes numa run" → `cont["esquivas"] >= 10` |

Títulos e acréscimos são sugestão; o construtor pode trocar dentro do tema. Se `maxhp` não for o nome do campo de HP máx em `stats()`, usar o nome real.

## Review Focus

- Conquista dispara na sala certa e uma vez só. → testes na Task 1.
- `andar8cheio`: HP 1 abaixo do máx no andar 8 não concede; andar 7 com HP cheio não concede. → Task 1.
- Vela com `maxhp` negativo: HP máx nunca fica < 1 e o herói passa por centenas de salas no `test_gui`. → Task 2.
- Acessório de topo não é cortado no pulo (pixel do acréscimo em todos os quadros de `estados(h, 1)` e `estados(h, 2)`). → cada task de herói.
- `failed` legível: último quadro ≥ 40 pixels opacos. → cada task de herói.

---

### Task 1: Conquistas dos 4 heróis

**Files:** Modify `masmorra.py` (`ACHIEVEMENTS`, `_check_achievements`), `tests/test_itens.py`.

**Interfaces:** Produces as chaves `queima1`, `andar8cheio`, `andar15`, `esquiva10` (texto da tabela), usadas no `"unlock"` das Tasks 2–5.

- [ ] **Step 1: testes falhando:** para cada conquista, run montada à mão logo abaixo do limite → não concede; no limite → concede e aparece em `ev["unlocks"]`; de novo → não repete. Casos de `andar8cheio` do Review Focus.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: conquistas dos heróis da leva 2`.

### Tasks 2–5: um herói por task (`vela`, `cogumelo`, `inquisidor`, `boneca`, nesta ordem)

Mesmo molde da Leva 1; a Task N usa a linha N−1 da tabela.

**Files:** Create `herois/<chave>.py`, `characters/<chave>/character.json`, `characters/<chave>/folha1..3.png` (gerados). Modify `tools/gerar_folhas.py` (`HEROIS` += chave), `tests/test_folha.py`.

**Interfaces:** `character.json`: `{"name", "unlock", "stats", "traço", "frame_ms": 600, "stages": [{"title", "floor", "sheet": "folhaN.png"}]}` com os valores da tabela.

- [ ] **Step 1: teste falhando** `test_heroi_<chave>` em `tests/test_folha.py`, igual aos da Leva 1: `validar` passa; 3 folhas com 9 estados ≥ 4 quadros e altura aparada > 16; carregador devolve `traco` e `unlock` da tabela; acréscimo em todos os quadros; último `failed` ≥ 40 pixels. Vela: também `stats()` com o traço dá HP máx 16.
- [ ] **Step 2:** rodar → FAIL.
- [ ] **Step 3:** desenhar. Gestos: idle mexe o símbolo (chama tremula; esporos sobem; sino balança; botão-olho pisca/costura mexe); run_r corre de lado; waving acena; jumping agacha/salta/cai; failed no tema (vela: chama apaga e a cera escorre; cogumelo: murcha e solta esporos; inquisidor: cai e o livro trancado tomba; boneca: desmonta, enchimento escapa); waiting cochila com "z"; running golpe com o símbolo (gota de cera/chama, nuvem de esporos, sino/livro, agulha); review com "?". `python tools/gerar_folhas.py` e conferir `tools/saida/preview_herois.png` com zoom.
- [ ] **Step 4:** todos os testes → PASS.
- [ ] **Step 5:** commit `feat: herói <Nome>`.

### Task 6: Balanceamento e fechamento

**Files:** Modify `characters/<chave>/character.json` (só números), `CLAUDE.md` (lista de heróis e conquistas), `docs/superpowers/specs/2026-11-12-doze-herois-design.md` (seção Balanceamento: trocar a regra da mediana ±2 pela taxa 30–50%).

- [ ] **Step 1:** `python tools/estatisticas.py --sem-abrir` e `python tools/simular.py`; medir a taxa de passar do 1º chefe por herói (1.500 runs cada). METAS da calibração continuam dentro.
- [ ] **Step 2:** herói fora de 30–50% → ajustar traço/stats e repetir; anotar antes/depois no report.
- [ ] **Step 3:** atualizar docs; todos os testes → PASS.
- [ ] **Step 4:** commit `chore: balanceia e documenta os heróis da leva 2`.
- [ ] **Step 5:** mostrar a prévia ao dono (portão da leva).
