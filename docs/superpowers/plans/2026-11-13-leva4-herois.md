# Leva 4: mais 6 heróis (20 no total) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 6 heróis autorais novos (20 nossos no total), cada um com traço passivo, conquista temática e ícone de conquista.

**Architecture:** Igual às Levas 1–3. Herói = `herois/<chave>.py` + `characters/<chave>/character.json` + `folha1..3.png` (`tools/gerar_folhas.py`, `HEROIS`). Conquista em `masmorra.ACHIEVEMENTS` + `_check_achievements` + ícone em `arte.CONQ_ART` (a janela de Conquistas exige ícone para toda conquista).

**Tech Stack:** Python 3 stdlib.

**Spec:** `docs/superpowers/specs/2026-11-12-doze-herois-design.md` (mesmas regras; o dono pediu 20 heróis e aprovou esta tabela em 2026-11-13).

## Global Constraints

- Só biblioteca padrão no app; arte 100% original (arquétipos; nada reconhecível de jogo/filme/anime). Sem mímico.
- Textos pt-BR. Estilo sombrio e fofo.
- Quadros 32×32, 4–6 por estado, 8 estados desenhados (`run_l` gerado). Gestos **grandes** (braços/objetos ≈5–9 px, contorno escuro); "z"/"?" de `herois/comum.py`. Objeto-símbolo no `running` e, quando der, no `idle`/`waving`.
- 3 estágios, andares `[1, 4, 10]`; acréscimo colado em **todos** os quadros via `ANCORA` (inclusive `failed`); acréscimo inteiro dentro do quadro (usar `extra_dentro` de `tests/test_folha.py`); folga no topo no pulo; nada trocando de lado entre quadros; sem buracos transparentes no meio do corpo; acréscimo não cobre o braço que gesticula; bom contraste em fundo escuro.
- Peças repetidas vão para `herois/comum.py`; um herói nunca importa de outro.
- Stats base 20/3/0 salvo a tabela; traço só com campos aditivos de `stats()` (sem `crescer`).
- Balanceamento: cada herói passa do 1º chefe em **30–50%** (1.500 runs só dele); ajustar só números do `character.json` (traço primeiro).

## Tabela da leva

| Chave | Nome | Símbolos | Estágios (sugestão) | Traço | Stats | Conquista (chave → regra) |
|---|---|---|---|---|---|---|
| `espantalho` | Espantalho | chapéu de palha, remendos | Espantalhinho / Espantalho (corvinho de palha no ombro) / Guardião da Lavoura (lanterna de abóbora) | `{"ajudante": 2}` | 20/3/0 | `ajudantes3` "Pegar 3 itens de ajudante numa run" → itens de `run["items"]` com `ajudante` no `fx` ≥ 3 |
| `golem` | Golem de Musgo | pedra, musgo, florzinha | Pedrinha / Golem de Musgo (flor maior) / Golem Ancião (cogumelos e ninho) | `{"def": 1, "maxhp": 6}` | 20/3/0, `spd` 8 | `sem_consumir10` "Chegar ao andar 10 sem consumir nenhum item" → `run["floor"] >= 10` e `run["consumed"] == []` |
| `mariposa` | Mariposa Lunar | asas com olhos, pó brilhante | Lagartinha Lunar / Mariposa Lunar (antenas maiores) / Mariposa Eclipse (lua crescente) | `{"dodge": 0.05, "eletrizar": 0.06}` | 20/3/0 | `lendarios3` "Pegar 3 itens lendários numa run" → itens com `rar == "lendario"` ≥ 3 |
| `sapo` | Sapo Xamã | máscara de folha, cajado | Girino Xamã / Sapo Xamã (colar de dentes) / Ancião do Brejo (cocar de folhas) | `{"envenenar": 0.06, "cura_sala": 1}` | 20/3/0 | `veneno3` "Matar 3 inimigos com veneno numa run" → `cont["mortes_veneno"] >= 3` |
| `gato` | Gato Preto de Cemitério | olhos amarelos, coleira com sino | Gatinho Preto / Gato de Cemitério (lenço) / Gato das Sete Vidas (sete velinhas flutuando) | `{"sorte": 0.3, "crit": 0.05}` | 20/3/0 | `andar13` "Morrer no andar 13" → `run["dead"]` e `run["floor"] == 13` (checado em `die`) |
| `polvo` | Polvo do Poço | tentáculos, balde velho | Polvinho / Polvo do Poço (balde na cabeça) / Senhor do Poço (corrente com âncora) | `{"duplo": 0.06, "congelar": 0.04}` | 20/3/0 | `chefes3run` "Vencer 3 chefes numa mesma run" → `run["bosses"] >= 3` |

## Review Focus

- Cada conquista dispara uma vez só e tem ícone em `arte.CONQ_ART`. → Task 1.
- `andar13` só na morte (passar pelo 13 vivo não concede); `sem_consumir10` falha com 1 consumido. → Task 1.
- `spd` 8 do Golem e `maxhp` +6 chegam em `stats()`. → Task 3.
- Acréscimo dentro do quadro e `failed` legível. → cada task de herói.
- Os 6 aparecem na seção "Heróis" (não em "Comunidade") da grade. → cada task de herói.

---

### Task 1: Conquistas e ícones

**Files:** `masmorra.py`, `arte.py` (`CONQ_ART`), `tests/test_itens.py`.

- [ ] Testes (molde `_ach`): limite abaixo/no limite/não repete para as 6; casos do Review Focus. Ícone para as 6 (o teste de `CONQ_ART` já existe).
- [ ] Implementar; `python tools/preview_arte.py`; todos os testes; `python tools/simular.py`.
- [ ] Commit `feat: conquistas dos heróis da leva 4`.

### Tasks 2–7: um herói por task (`espantalho`, `golem`, `mariposa`, `sapo`, `gato`, `polvo`)

Mesmo molde da Leva 3; a Task N usa a linha N−1 da tabela.

**Files:** Create `herois/<chave>.py`, `characters/<chave>/character.json`, `folha1..3.png`. Modify `tools/gerar_folhas.py` (`HEROIS`), `tests/test_folha.py`.

- [ ] Teste `test_heroi_<chave>` igual ao `test_heroi_freira` (+ `spd`/`maxhp` no Golem; `extra_dentro`).
- [ ] Desenhar. failed no tema (espantalho desmonta em palha; golem racha em pedrinhas; mariposa cai e o pó apaga; sapo afunda na poça e a máscara boia; gato se enrola e o sino toca uma última vez; polvo volta para dentro do balde). running com o símbolo (corvinho/foice de palha, soco de pedra, rajada de pó, cajado, patada/arranhão, chicotada de tentáculo).
- [ ] Taxa de passar do 1º chefe (1.500 runs) em 30–50%.
- [ ] Todos os testes; commit `feat: herói <Nome>`.

### Task 8: Fechamento

- [ ] `python tools/estatisticas.py --sem-abrir`: METAS dentro; os 20 em 30–50%.
- [ ] Docs: `CLAUDE.md`, `README.md` (nomes em inglês sem colidir com jogos conhecidos), `LEIA-ME.md` (tabela de como liberar).
- [ ] Commit `chore: documenta os 20 heróis`; prévia ao dono.
