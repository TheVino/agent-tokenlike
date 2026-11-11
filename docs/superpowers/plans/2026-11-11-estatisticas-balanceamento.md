# Estatísticas de balanceamento — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Registrar cada run real, gerar os mesmos registros no simulador e transformar tudo numa página HTML de desenvolvimento (simulado × real) mais uma skill `/balancear`.

**Architecture:** `masmorra.py` ganha o andar em que cada item é pego, a lista de consumidos, `BALANCE_VERSION` e `run_record()` (a única função que monta a linha). `tokenlike.py` só acrescenta essa linha em `~/.tokenlike/runs.jsonl` (ou `runs-demo.jsonl`). `tools/simular.py` produz as mesmas linhas. `tools/estatisticas.py` calcula as métricas (funções puras) e gera HTML + JSON em `tools/saida/`.

**Tech Stack:** Python 3.9+, só biblioteca padrão. Testes são scripts com `assert` (`python tests/<arquivo>.py`), sem pytest.

**Spec:** `docs/superpowers/specs/2026-11-11-estatisticas-balanceamento-design.md`

## Global Constraints

- Ler `CLAUDE.md`. Só biblioteca padrão no app e em `tools/estatisticas.py`; sem rede; textos em pt-BR.
- Nada novo para o jogador: nenhum item de menu, nenhuma tela.
- Registro só com dados do jogo; nada do Claude Code.
- Demo grava em `runs-demo.jsonl`, que a página ignora.
- Desistências (`gave_up: true`) ficam no arquivo mas não entram em durou, esperado, mortes rápidas, onde morrem e quem mata; só contam no resumo.
- Rótulos da página: "sim" e "real".
- Verde: durou vs esperado > +1 andar; vermelho: < −1 andar. Mortes rápidas: morreu até 2 andares depois de pegar. Pares: mínimo de 30 runs simuladas juntas; mostrar os 10 maiores e os 5 menores. Real com menos de 10 runs num item: esmaecido com aviso.
- `METAS = {"passou_chefe1": (0.35, 0.45), "p90": (13, 16), "max": (None, 25)}`. "Passou do 1º chefe" = `floor > M.BOSS_EVERY`.
- Coluna "sim" = runs simuladas com todas as conquistas, heróis em partes iguais. O resumo mostra também "sim sem conquistas". `esperado(f)` é calculado separado por fonte.
- Consumido = consumidos ÷ (pegos + consumidos); real mostrado separado por modo.
- `BALANCE_VERSION` = `sha1(json.dumps(estrutura, sort_keys=True))[:8]` só com números de balanceamento (ver Task 1).
- Depois de cada task, passam: `tests/test_visual.py`, `tests/test_itens.py`, `tests/test_gui.py`, `tests/test_reader.py`, `tests/test_migracao.py`, `tests/test_limites.py` e os testes novos. Mexeu em `masmorra.py` → `python tools/simular.py` com a saída idêntica à de antes (este projeto só mede, não muda balanceamento).

## Review Focus

1. **Usuário sem nenhuma run real** (sem `runs.jsonl`): a página é gerada com "sem runs reais ainda" nas colunas reais, sem exceção. Teste na Task 4.
2. **Linha corrompida ou de outro formato no `runs.jsonl`:** é pulada e contada como ignorada. Teste na Task 4.
3. **Save antigo com run em andamento** (itens sem `floor`, sem `consumed`, sem `ach_start`): a run termina e grava a linha sem erro; itens sem `floor` não entram nas métricas de item. Testes na Task 1 e na Task 2.
4. **Item que nunca saiu na simulação:** aparece com 0 e "—", sem divisão por zero. Teste na Task 4.
5. **Falha ao gravar o `runs.jsonl`** (pasta sem permissão): só loga, o app segue. Teste na Task 2.

---

### Task 1: Registro da run em `masmorra.py`

**Files:**
- Modify: `masmorra.py` (`new_run`, `migrate_run`, `resolve_offer`, constantes)
- Test: `tests/test_registro.py` (novo)

**Interfaces:**
- Produces:
  - Itens em `run["items"]`: `{"key", "rar", "floor": int | None}`. `run["consumed"]: list[{"key", "rar", "floor"}]`.
  - `BALANCE_VERSION: str` (8 caracteres hex), calculado no import por `_balance_version() -> str`.
  - `run_record(run: dict, killer: str, gave_up: bool, mode: str, achievements: list[str]) -> dict` com exatamente estas chaves: `run, char, floor, room, killer, gave_up, items, consumed, gold, kills, bosses, date, mode, version, achievements`.

- [ ] **Step 1: Escrever `tests/test_registro.py`**

```python
run = M.new_run("slime", {"hp": 20, "atk": 3}, 1); run["floor"] = 4
assert run["consumed"] == []
M.resolve_offer(run, {"key": "adaga", "rar": "raro"}, "pegar", {"lines": []})
M.resolve_offer(run, {"key": "tampa", "rar": "comum"}, "consumir", {"lines": []})
assert run["items"] == [{"key": "adaga", "rar": "raro", "floor": 4}]
assert run["consumed"] == [{"key": "tampa", "rar": "comum", "floor": 4}]
old = {"items": [{"key": "adaga", "rar": "comum"}], "hp": 5}
M.migrate_run(old); assert old["items"][0]["floor"] is None and old["consumed"] == []
rec = M.run_record(run, "Rei Rato", False, "auto", ["andar5"])
assert set(rec) == {"run", "char", "floor", "room", "killer", "gave_up", "items", "consumed", "gold",
                    "kills", "bosses", "date", "mode", "version", "achievements"}
assert rec["version"] == M.BALANCE_VERSION and len(M.BALANCE_VERSION) == 8
assert json.loads(json.dumps(rec)) == rec                       # serializável
v0 = M.BALANCE_VERSION
M.ITEMS["adaga"]["look"] = {"type": "obj", "anchor": "esq", "art": "adaga"}
assert M._balance_version() == v0                              # visual não muda a versão
M.ITEMS["adaga"]["fx"] = {"atk": 99}
assert M._balance_version() != v0                              # número muda a versão
print("ok: registro")
```

- [ ] **Step 2: Rodar e ver falhar.** `python tests/test_registro.py` → `AssertionError` ou `KeyError: 'consumed'`.

- [ ] **Step 3: Implementar.** `resolve_offer` grava `floor = run["floor"]` no item pego e no consumido. `new_run` cria `consumed: []`. `migrate_run` faz `setdefault("floor", None)` em cada item e `setdefault("consumed", [])`. `_balance_version()` serializa: por item `{fx, consume, rarities, req}`; `MONSTERS`; `ROOM_COST`, `ROOMS_PER_FLOOR`, `MAX_STORED_ROOMS`, `BOSS_EVERY`, `MON_HP`, `MON_ATK`, `BOSS_HP`, `BOSS_ATK`, `REGEN_PER_ROOM`, `FLOOR_BONUS_HP`, `ROOM_WEIGHTS`, `RAR_MULT`, `[_rarity_weights(f) for f in range(1, 41)]`, `MAX_ENERGY_BONUS`, `TRAP_LIMITS`, `MAX_DODGE`, `CHEST_ITEM_CHANCE`, `SHOP_PRICE`. `BALANCE_VERSION = _balance_version()` no fim do módulo. `run_record` copia listas (não referências) e usa `date.today().isoformat()`.

- [ ] **Step 4: Rodar tudo.** Todos os testes + `python tools/simular.py` com saída idêntica à de antes. Expected: tudo `ok`.

- [ ] **Step 5: Commit.** `git add masmorra.py tests/test_registro.py` → `git commit -m "feat: registro de run (andar do item, consumidos, BALANCE_VERSION)"`

---

### Task 2: Gravar as runs reais

**Files:**
- Modify: `tokenlike.py` (`new_run`, `on_death`, `give_up`, função nova)
- Modify: `tests/test_gui.py`

**Interfaces:**
- Consumes: `M.run_record`, `M.BALANCE_VERSION` (Task 1).
- Produces:
  - `append_run_record(rec: dict, demo: bool) -> None`: acrescenta `json.dumps(rec, ensure_ascii=False) + "\n"` em `DATA_DIR / ("runs-demo.jsonl" if demo else "runs.jsonl")`. Usa `DATA_DIR` lido na hora (o teste troca `tp.DATA_DIR`). Qualquer `OSError` vira `log(...)`. O texto do log não pode conter a palavra "erro" (o `test_gui` falha com ela), então usar algo como `"não gravou runs.jsonl: ..."`.
  - `run["ach_start"]`: lista de conquistas no começo da run, gravada no `PetApp.new_run`. Na gravação, usa `run.get("ach_start", meta["achievements"])`.
  - Morte (`on_death`): `killer = meta["graveyard"][-1]["killer"]`, `gave_up=False`. Desistência (`give_up`): `killer="Desistiu"`, `gave_up=True`. `mode = state["mode"]`.

- [ ] **Step 1: Teste em `tests/test_gui.py`**, depois do bloco das barras de limite (`app4`):

```python
runs_file = tp.DATA_DIR / "runs.jsonl"; demo_file = tp.DATA_DIR / "runs-demo.jsonl"
lines = [json.loads(l) for l in runs_file.read_text(encoding="utf-8").splitlines()]
assert lines and all(l["version"] == M.BALANCE_VERSION for l in lines)
assert any(l["gave_up"] for l in lines) and any(not l["gave_up"] for l in lines)
assert demo_file.exists()                                        # o demo grava separado
assert all(isinstance(l["achievements"], list) for l in lines)
# falha ao gravar só loga
real_dir = tp.DATA_DIR; tp.DATA_DIR = runs_file / "sub"          # "pasta" dentro de um arquivo: mkdir falha
tp.append_run_record({"x": 1}, False); tp.DATA_DIR = real_dir
# save antigo: run sem ach_start/consumed/floor termina sem exceção
app5 = tp.PetApp(Args()); PENDING.clear(); app5.rng = random.Random(SEED)
app5.run.pop("ach_start", None); app5.run.pop("consumed", None)
app5.run["items"] = [{"key": "adaga", "rar": "comum"}]; M.migrate_run(app5.run)
app5.give_up(); app5.quit()
```

- [ ] **Step 2: Rodar e ver falhar.** `python tests/test_gui.py` → `FileNotFoundError` para `runs.jsonl`.

- [ ] **Step 3: Implementar** conforme o bloco Interfaces. `DATA_DIR.mkdir(parents=True, exist_ok=True)` fica dentro do `try`, assim o caminho "dentro de um arquivo" do teste cai no `except OSError`.

- [ ] **Step 4: Rodar tudo.** Expected: todos `ok`, sem "erro" no log.

- [ ] **Step 5: Commit.** `git commit -am "feat: grava cada run real em runs.jsonl (demo separado)"`

---

### Task 3: Simulador gera registros

**Files:**
- Modify: `tools/simular.py`
- Test: `tests/test_registro.py` (acrescentar)

**Interfaces:**
- Consumes: `M.run_record` (Task 1); `tokenlike.all_characters()` para heróis e stats (importar `tokenlike` não abre janela).
- Produces:
  - `simular(n: int = 2000, achs=(), seed: int = 1, heroes: list[tuple[str, dict]] | None = None) -> tuple[list[dict], list[int]]`: devolve os registros (via `run_record`, `mode="auto"`, `killer` do cemitério ou `"—"` se bater o limite de salas, `achievements=list(achs)`) e a lista de salas jogadas. `heroes=None` → `[("slime", {"hp": 20, "atk": 3})]`, exatamente como hoje. Com vários heróis, as runs se dividem em partes iguais (run `i` usa `heroes[i % len(heroes)]`).
  - `todos_os_herois() -> list[tuple[str, dict]]`: `[(c.key, c.stats) for c in tokenlike.all_characters().values()]`.
  - O `__main__` imprime exatamente as mesmas linhas de hoje (slime, sem e com conquistas, semente 1).

- [ ] **Step 1: Teste** (em `tests/test_registro.py`):

```python
sys.path.insert(0, str(ROOT / "tools")); import simular as S
recs, salas = S.simular(n=40, achs=list(M.ACHIEVEMENTS), seed=3, heroes=S.todos_os_herois())
assert len(recs) == 40 and len(salas) == 40
assert {r["char"] for r in recs} == {k for k, _ in S.todos_os_herois()}
assert all(set(r) == set(M.run_record(M.new_run("slime", {}, 0), "x", False, "auto", [])) for r in recs)
assert all(i["floor"] is not None for r in recs for i in r["items"])
a, _ = S.simular(n=20, seed=5); b, _ = S.simular(n=20, seed=5)
assert [r["floor"] for r in a] == [r["floor"] for r in b]       # determinístico
```

- [ ] **Step 2: Rodar e ver falhar.** `AttributeError: module 'simular' has no attribute 'simular'`.

- [ ] **Step 3: Implementar.** Mover o laço atual para `simular()`; o `print` fica num `main()` chamado sob `if __name__ == "__main__":`. O import de `simular` não pode rodar nada.

- [ ] **Step 4: Rodar tudo.** `python tools/simular.py` com saída idêntica à de antes. Expected: todos `ok`.

- [ ] **Step 5: Commit.** `git commit -am "feat: simular() devolve registros no formato das runs reais"`

---

### Task 4: Métricas em `tools/estatisticas.py`

**Files:**
- Create: `tools/estatisticas.py` (só funções puras nesta task)
- Test: `tests/test_estatisticas.py`

**Interfaces:**
- Consumes: formato de linha da Task 1; `M.BALANCE_VERSION`, `M.BOSS_EVERY`, `M.ITEMS`.
- Produces (todas puras):
  - `METAS` (valores em Global Constraints); `checar_metas(res: dict) -> dict[str, bool]`.
  - `carregar_reais(pasta: Path, todas_versoes: bool = False) -> tuple[list[dict], dict]`: lê `runs.jsonl` (nunca `runs-demo.jsonl`). Devolve as linhas da versão atual (ou todas) e `info = {"outras_versoes": int, "ignoradas": int, "desistencias": int, "modos": dict[str, int]}`. Arquivo inexistente → `([], info zerado)`.
  - `validas(recs) -> list[dict]`: tira `gave_up`.
  - `resumo(recs) -> dict`: `{"n", "mediana", "p90", "max", "passou_chefe1", "itens_med"}` (com `recs` vazio → `n=0` e o resto `None`).
  - `esperado(recs) -> dict[int, float]`: para cada andar f, média de `floor_final − f` entre as runs com `floor_final ≥ f`.
  - `por_item(recs) -> dict[str, dict]`: para **toda** chave de `M.ITEMS`: `n`, `pego` (fração das runs), `andar_pego` (mediana), `durou`, `vs_esperado`, `andar_final`, `mortes_rapidas` (fração), `consumido` (fração), `consumido_por_modo: dict[str, float]`. Sem dados → `n=0` e os outros `None`. Itens com `floor None` são ignorados.
  - `pares(recs, minimo: int = 30) -> dict`: `{"melhores": [...10], "piores": [...5]}`, cada um `{"a", "b", "n", "vs_esperado", "ganho"}`. `ganho = vs_esperado_do_par − max(vs_esperado(a), vs_esperado(b))`, e o par conta a partir do andar em que o segundo item foi pego.
  - `mortes(recs) -> dict`: `{"por_andar": dict[int, int], "matadores": list[tuple[str, int]]}` (top 6).
  - `herois(recs) -> dict[str, dict]`: `{"n", "mediana", "p90"}` por herói.

- [ ] **Step 1: Escrever `tests/test_estatisticas.py`** com linhas montadas à mão (função auxiliar `linha(char, floor, items, killer="Rato", gave_up=False, mode="auto", consumed=())`):

```python
recs = [linha("slime", 10, [("adaga", 2)]), linha("slime", 4, [("adaga", 3)]),
        linha("slime", 8, []), linha("slime", 3, [("vela", 2)], gave_up=True)]
v = E.validas(recs); assert len(v) == 3
esp = E.esperado(v); assert esp[2] == ((10 - 2) + (4 - 2) + (8 - 2)) / 3
it = E.por_item(v)
assert it["adaga"]["n"] == 2 and it["adaga"]["durou"] == ((10 - 2) + (4 - 3)) / 2
assert it["adaga"]["mortes_rapidas"] == 0.5                        # 4 - 3 <= 2
assert it["vela"]["n"] == 0 and it["vela"]["durou"] is None         # só aparecia na desistência
assert set(it) == set(M.ITEMS)
assert E.resumo([])["n"] == 0
assert E.checar_metas({"passou_chefe1": 0.4, "p90": 15, "max": 25}) == {"passou_chefe1": True, "p90": True, "max": True}
assert E.checar_metas({"passou_chefe1": 0.5, "p90": 10, "max": 26}) == {"passou_chefe1": False, "p90": False, "max": False}
# arquivo: versão, demo, linha quebrada, pasta vazia
d = Path(tempfile.mkdtemp())
assert E.carregar_reais(d) == ([], {"outras_versoes": 0, "ignoradas": 0, "desistencias": 0, "modos": {}})
(d / "runs.jsonl").write_text(json.dumps(recs[0]) + "\n{quebrada\n" + json.dumps(dict(recs[1], version="x")) + "\n")
(d / "runs-demo.jsonl").write_text(json.dumps(recs[2]) + "\n")
reais, info = E.carregar_reais(d)
assert len(reais) == 1 and info["ignoradas"] == 1 and info["outras_versoes"] == 1
assert len(E.carregar_reais(d, todas_versoes=True)[0]) == 2
# pares: mínimo de amostra
many = [linha("slime", 12, [("adaga", 2), ("tampa", 3)]) for _ in range(30)]
assert E.pares(many, minimo=30)["melhores"][0]["n"] == 30 and E.pares(many, minimo=31)["melhores"] == []
print("ok: estatisticas")
```

- [ ] **Step 2: Rodar e ver falhar.** `ModuleNotFoundError: No module named 'estatisticas'`.

- [ ] **Step 3: Implementar** as funções do bloco Interfaces em `tools/estatisticas.py` (importa `masmorra` pelo `sys.path` da raiz, como o `simular.py`). Nenhum código roda no import.

- [ ] **Step 4: Rodar tudo.** Expected: todos `ok`.

- [ ] **Step 5: Commit.** `git add tools/estatisticas.py tests/test_estatisticas.py` → `git commit -m "feat: métricas de balanceamento (durou vs esperado, pares, mortes)"`

---

### Task 5: Página HTML, JSON e linha de comando

**Files:**
- Modify: `tools/estatisticas.py`
- Modify: `tests/test_estatisticas.py`
- Modify: `.gitignore` (`tools/saida/`)

**Interfaces:**
- Consumes: funções da Task 4; `simular.simular`, `simular.todos_os_herois` (Task 3).
- Produces:
  - `coletar(n_sim: int, pasta_real: Path, todas_versoes: bool, seed: int = 1) -> dict`: roda `simular(n_sim, achs=todas, heroes=todos)` (coluna "sim") e `simular(n_sim, achs=(), heroes=todos)` (linha "sim sem conquistas" do resumo), carrega o real, calcula tudo. Chaves do resultado: `versao, gerado_em, sim, sim_sem_conquistas, real, info_real, metas, itens, pares, mortes, herois`, onde `itens[key] = {"nome", "raridades", "sim": {...}, "real": {...}}` e `mortes`/`herois` têm `sim` e `real`.
  - `gerar_html(dados: dict) -> str`: uma página completa, sem recurso externo (CSS e SVG embutidos), fundo escuro do jogo (`#1d1b2b`, borda `#4b4680`, texto `#f2f0ff`). Seções, nesta ordem: Resumo (sim, sim sem conquistas, real, com ✓/✗ das metas e aviso se o real tiver menos de 10 runs), Itens (tabela ordenável por clique no cabeçalho, com JS embutido curto; colunas "Pego", "Andar em que é pego", "Durou", "vs esperado", "Andar final", "Em mortes rápidas", "Consumido", cada uma "sim / real"; verde/vermelho pela regra de Global Constraints; real esmaecido abaixo de 10 runs), Melhores pares e Piores pares, Onde as runs morrem (histograma SVG sim e real, e quem mais mata), Heróis. Escapar textos com `html.escape`.
  - `main(argv=None)`: `--runs N` (padrão 2000), `--sem-abrir`, `--real-dir` (padrão `~/.tokenlike`), `--todas-versoes`. Grava `tools/saida/estatisticas.html` e `tools/saida/estatisticas.json` (UTF-8) e, sem `--sem-abrir`, abre com `webbrowser.open(path.as_uri())`. Imprime os dois caminhos.

- [ ] **Step 1: Teste** (acrescentar):

```python
d = Path(tempfile.mkdtemp())                                       # sem runs reais
dados = E.coletar(n_sim=60, pasta_real=d, todas_versoes=False)
assert dados["real"]["n"] == 0 and set(dados["itens"]) == set(M.ITEMS)
page = E.gerar_html(dados)
for sec in ("Resumo", "Itens", "Melhores pares", "Onde as runs morrem", "Heróis", "sem runs reais"):
    assert sec in page, sec
assert "http://" not in page and "https://" not in page          # nada externo
json.dumps(dados)                                                  # serializável
out = Path(tempfile.mkdtemp())
E.main(["--runs", "40", "--sem-abrir", "--real-dir", str(d), "--saida", str(out)])
assert (out / "estatisticas.html").exists() and json.loads((out / "estatisticas.json").read_text(encoding="utf-8"))["versao"] == M.BALANCE_VERSION
```

(`--saida` é uma opção extra só para teste, padrão `tools/saida/`.)

- [ ] **Step 2: Rodar e ver falhar.** `AttributeError: ... 'coletar'`.

- [ ] **Step 3: Implementar.** `.gitignore` ganha `tools/saida/`.

- [ ] **Step 4: Rodar tudo + manual.** `python tools/estatisticas.py --sem-abrir` imprime os caminhos; abrir o HTML gerado e conferir que as 5 seções aparecem e a tabela ordena. Expected: todos os testes `ok`.

- [ ] **Step 5: Commit.** `git commit -am "feat: página de estatísticas (sim × real) e JSON para a skill"`

---

### Task 6: Skill `/balancear` e documentação

**Files:**
- Create: `.claude/skills/balancear/SKILL.md`
- Modify: `CLAUDE.md`, `README.md` (seção Development)

**Interfaces:**
- Consumes: `python tools/estatisticas.py --sem-abrir` e `tools/saida/estatisticas.json` (chaves da Task 5).

- [ ] **Step 1: Escrever a skill** (pt-BR). Frontmatter: `name: balancear`, `description:` que dispara em "balancear", "balanceamento", "saúde do jogo", "estatísticas dos itens". Passos:
  1. rodar `python tools/estatisticas.py --sem-abrir`;
  2. ler `tools/saida/estatisticas.json`;
  3. relatar as metas ✓/✗, os itens verdes e vermelhos com amostra suficiente, os pares fortes demais (ganho > +1,5) e as anti-sinergias, onde morrem, e a diferença sim × real quando o real tiver 10 runs ou mais;
  4. propor mudanças de números em `masmorra.py` com o motivo de cada uma, seguindo a ordem de alavancas do `CLAUDE.md`;
  5. **só editar com a aprovação do dono**;
  6. depois de editar, rodar os testes, `python tools/simular.py` e de novo as estatísticas, e mostrar o antes e o depois;
  7. lembrar que a `BALANCE_VERSION` muda, então o histórico real recomeça na versão nova.

- [ ] **Step 2: `CLAUDE.md`:**
  - Arquivos: `tools/estatisticas.py`, `tests/test_registro.py`, `tests/test_estatisticas.py`, `.claude/skills/balancear/`.
  - Comandos: `python tests/test_registro.py`, `python tests/test_estatisticas.py`, `python tools/estatisticas.py`.
  - "Como as peças se encaixam": `runs.jsonl`, `run_record`, `BALANCE_VERSION`; as metas passam a apontar para `METAS` em `tools/estatisticas.py`, com o último resultado do simulador separado delas.
  - Nova seção **"Antes do lançamento"**: capricho visual e ícones de itens e heróis na página de estatísticas; screenshot e GIF do README (`docs/screenshot.png`, `docs/demo.gif`); teste na tela do modo interativo e das barras de sessão e semana.

- [ ] **Step 3: `README.md`**, seção Development: linhas para os dois testes novos e para `python tools/estatisticas.py`, mais uma frase sobre a skill `/balancear`.

- [ ] **Step 4: Rodar tudo.** Todos os testes + `python tools/estatisticas.py --sem-abrir --runs 200`. Expected: `ok` e os dois caminhos impressos.

- [ ] **Step 5: Commit.** `git add .claude/skills/balancear/SKILL.md CLAUDE.md README.md` → `git commit -m "docs: skill /balancear e notas de estatísticas/pré-lançamento"`
