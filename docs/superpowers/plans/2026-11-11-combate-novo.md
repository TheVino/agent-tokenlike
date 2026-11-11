# Combate novo — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Combate por rodadas com velocidade, crítico, 4 status elementais, chefes elementais e hordas de 2–4 inimigos, rebalanceado de volta às `METAS`.

**Architecture:** Toda regra fica em `masmorra.py`: atributos novos em `stats()`, inimigos como dicts (`make_foe`), uma função `combate()` que substitui `fight()` e devolve passos (dicts) para a GUI animar. As hordas são um tipo de sala novo. `tokenlike.py` só anima: grid de até 4 inimigos, crítico, tingido de status. As estatísticas ganham a categoria de quem matou.

**Tech Stack:** Python 3.9+, só biblioteca padrão. Testes são scripts com `assert` (`python tests/<arquivo>.py`).

**Spec:** `docs/superpowers/specs/2026-11-11-combate-novo-design.md`

## Global Constraints

- Ler `CLAUDE.md`. Só biblioteca padrão; arte 100% original; texto na tela sobre `PANEL_BG`; pt-BR.
- Inatividade nunca pune. Status só existe dentro de uma luta e acaba com ela.
- Monstros comuns e mímico nunca aplicam status. Só chefes aplicam no pet, e só o próprio elemento.
- Ordem por `spd` decrescente; empate: pet antes; inimigos empatados na ordem da lista.
- Dobro da velocidade do alvo: `crit` +0,5 e o multiplicador de crítico dobra (`critdmg × 2`). Vale para os dois lados. Continua 1 ação por rodada.
- Status iniciais: queimadura `2 + 0,3 × andar` por turno durante 3 turnos (renova); eletricidade 30% de perder o turno, durante 2 turnos; veneno começa em 1 e soma +1 por round, durante 4 turnos, até 3 pilhas; congelamento 60% de perder o turno, sai depois de perder um turno ou depois de 2 turnos.
- Hordas: tipo `"horde"` a partir do andar 3; tamanho máximo 2 (andares 3–4), 3 (andares 5–7), 4 (andar 8+); HP e ATK × 0,75 / 0,6 / 0,5 para 2 / 3 / 4; `spd` sem redução; ouro = soma × 1,25; cada inimigo morto conta em `kills`; chefes nunca em horda; mímico continua sozinho.
- Limite de 60 rodadas: a luta acaba como vitória do pet, sem ouro extra.
- Tetos: `crit` ≤ 0,6 antes do bônus de velocidade; chance de cada elemento ≤ 0,6; `spd` ≥ 1.
- `REGRAS_REV` sobe para 2 (Task 2).
- Saves antigos e heróis sem `spd` funcionam com os padrões.
- Depois de cada task passam todos os testes: `tests/test_combate.py` (novo), `test_estatisticas`, `test_registro`, `test_visual`, `test_itens`, `test_gui`, `test_reader`, `test_migracao`, `test_limites`. A partir da Task 2, a saída do `tools/simular.py` pode mudar; o rebalanceamento final é na Task 6.

## Review Focus

1. **Luta em que ninguém consegue agir** (pet e inimigo congelados ou eletrizados por rodadas seguidas, ou dano 0 para os dois lados): termina pelo limite de 60 rodadas, sem laço infinito. Teste na Task 2.
2. **Save antigo no meio de uma run** (`base` sem `spd`/`crit`/`critdmg`): carrega e luta com os padrões. Teste na Task 1.
3. **Horda em que o pet morre no meio da rodada:** os inimigos seguintes não agem, a morte é registrada uma vez e o assassino é o inimigo que deu o golpe (ou o status). Teste na Task 3.
4. **Pet morre por status de chefe** (queimadura ou veneno no começo da rodada): a morte conta, com assassino "Queimadura" ou "Veneno". Teste na Task 2.
5. **Herói em PNG sem `spd` no `character.json`** e heróis com `spd` muito diferente: a ordem e o bônus de crítico funcionam sem exceção. Teste na Task 1.

---

### Task 1: Atributos novos e inimigos como dicts

**Files:**
- Modify: `masmorra.py` (constantes, `new_run`, `migrate_run`, `stats`, `MONSTERS`)
- Create: `tests/test_combate.py`

**Interfaces:**
- Produces:
  - `MONSTERS` ganha o 6º campo `spd_mult`: `(sprite, nome, hp_mult, atk_mult, andar_min, spd_mult)`. Valores iniciais: morcego 1.4, rato 1.1, aranha 1.0, esqueleto 0.7, olho 0.9.
  - Constantes: `MON_SPD = (8, 0.3)`, `BOSS_SPD_BONUS = 1.2`, `MON_CRIT = 0.03`, `BOSS_CRIT = 0.05`, `FOE_CRITDMG = 1.5`, `PET_SPD = 10`, `PET_CRIT = 0.05`, `PET_CRITDMG = 1.5`, `MAX_CRIT = 0.6`, `MAX_ELEM_CHANCE = 0.6`, `ELEMENTOS = {"fogo": "queimar", "raio": "eletrizar", "veneno": "envenenar", "gelo": "congelar"}`, `BOSS_ELEMENT = {"morcego": "raio", "rato": "veneno", "aranha": "veneno", "esqueleto": "gelo", "olho": "fogo"}`, `BOSS_STATUS_CHANCE = 0.35`.
  - `new_run`: `base` ganha `spd` (de `base_stats.get("spd", PET_SPD)`), `crit` (`PET_CRIT`), `critdmg` (`PET_CRITDMG`). `migrate_run`: `base.setdefault` dos três.
  - `stats(run)` devolve também `spd` (≥ 1), `crit` (≤ `MAX_CRIT`), `critdmg`, `area` (bool: algum item com `fx["area"]`), `queimar`, `eletrizar`, `envenenar`, `congelar` (cada ≤ `MAX_ELEM_CHANCE`). `item_fx`: valores positivos desses campos escalam com a raridade, menos `area`.
  - `make_foe(m: tuple, f: int, boss: bool = False, mult: float = 1.0) -> dict` com `{"sprite", "name", "boss", "element", "hp", "hp_max", "atk", "spd", "crit", "critdmg", "status": {}}`. HP e ATK usam as fórmulas atuais (monstro: `MON_HP`/`MON_ATK` × mults; chefe: `BOSS_HP`/`BOSS_ATK` com o nome de `BOSS_NAMES`) e depois `× mult`, com mínimo 1. `spd = (MON_SPD[0] + MON_SPD[1] × f) × spd_mult × (BOSS_SPD_BONUS se chefe)`. `element` = `BOSS_ELEMENT[sprite]` só se chefe, senão `None`.
  - Mímico: `make_mimic(f: int) -> dict` com as fórmulas atuais de mímico, `spd_mult` 1.0, sem elemento.

- [ ] **Step 1: Escrever `tests/test_combate.py`** (estilo de `tests/test_itens.py`):

```python
run = M.new_run("slime", {"hp": 20, "atk": 3}, 1)
st = M.stats(run)
assert st["spd"] == 10 and st["crit"] == 0.05 and st["critdmg"] == 1.5 and st["area"] is False
assert st["queimar"] == 0 and st["congelar"] == 0
assert M.new_run("x", {"spd": 14}, 2)["base"]["spd"] == 14
old = {"items": [], "hp": 10, "base": {"maxhp": 20, "atk": 3, "def": 0, "dodge": 0}}
M.migrate_run(old); assert old["base"]["spd"] == 10 and M.stats(old)["spd"] == 10
M.ITEMS["_t"] = {"name": "t", "fx": {"crit": 0.9, "queimar": 0.9, "spd": -50, "area": True},
                 "rarities": ["comum"], "consume": {"heal": 1}, "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
run["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
st = M.stats(run)
assert st["crit"] == M.MAX_CRIT and st["queimar"] == M.MAX_ELEM_CHANCE and st["spd"] == 1 and st["area"] is True
del M.ITEMS["_t"]
bat = next(m for m in M.MONSTERS if m[0] == "morcego"); ske = next(m for m in M.MONSTERS if m[0] == "esqueleto")
assert M.make_foe(bat, 5)["spd"] > M.make_foe(ske, 5)["spd"]
assert M.make_foe(bat, 5)["element"] is None and M.make_foe(bat, 5, boss=True)["element"] == "raio"
assert M.make_foe(bat, 5, mult=0.5)["hp"] == max(1, round(M.make_foe(bat, 5)["hp"] * 0.5))   # mesma regra de arredondamento
print("ok: combate")
```

(Se o arredondamento escolhido aplicar `mult` antes do `round`, ajuste a última linha para refletir a ordem implementada e diga isso no relatório.)

- [ ] **Step 2: Rodar e ver falhar.** `python tests/test_combate.py` → `AssertionError`/`KeyError: 'spd'`.

- [ ] **Step 3: Implementar** conforme Interfaces. `enter_room` passa a usar `make_foe`/`make_mimic` para montar o inimigo, mas continua chamando `fight()` com `foe["hp"]`/`foe["atk"]` (troca de motor é a Task 2). `tools/simular.py` deve imprimir exatamente o mesmo de antes nesta task (o RNG não pode ser consumido a mais).

- [ ] **Step 4: Rodar tudo** + `python tools/simular.py` idêntico ao de antes.

- [ ] **Step 5: Commit.** `git commit -am "feat: velocidade, crítico e elementos como atributos; inimigos como dicts"` (incluir `tests/test_combate.py` com `git add`).

---

### Task 2: Motor de combate por rodadas

**Files:**
- Modify: `masmorra.py` (`combate` novo, `fight` sai, `enter_room`, `REGRAS_REV`)
- Modify: `tokenlike.py` (`play_room` lê os passos novos, ainda com 1 inimigo na tela)
- Test: `tests/test_combate.py`

**Interfaces:**
- Consumes: `make_foe`, `make_mimic`, `stats` (Task 1).
- Produces:
  - Constantes: `QUEIMA = (2, 0.3)`, `QUEIMA_TURNOS = 3`, `ELETRO_CHANCE = 0.3`, `ELETRO_TURNOS = 2`, `VENENO_TURNOS = 4`, `VENENO_MAX_PILHAS = 3`, `GELO_CHANCE = 0.6`, `GELO_TURNOS = 2`, `MAX_ROUNDS = 60`, `REGRAS_REV = 2`.
  - `combate(run: dict, st: dict, foes: list[dict], rng, f: int) -> tuple[bool, list[dict], str]`: devolve (venceu, passos, assassino). Muta `run["hp"]` (via `apply_damage`, que já usa o escudo) e o `hp`/`status` de cada inimigo. O status do pet fica numa variável local (nunca no `run`).
  - Cada passo é um dict com **todas** estas chaves: `who` (`"pet"` ou índice do inimigo), `target` (`"pet"`, índice ou `"todos"`), `dmg` (int, 0 se nada), `crit` (bool), `status` (nome aplicado ou `None`: `"queimadura"`, `"eletricidade"`, `"veneno"`, `"congelamento"`), `skip` (bool, perdeu o turno), `dot` (bool, dano de status no começo da rodada), `dodge` (bool).
  - Assassino: o `name` do inimigo que deu o golpe final, ou `"Queimadura"`/`"Veneno"` se o pet morreu por status.
  - `enter_room`: luta = `combate(...)`; `ev["foes"] = [{"sprite", "name", "boss", "element", "hp_max"} ...]`, `ev["hits"] = passos`; morte usa o assassino. Remover `fight()`.

- [ ] **Step 1: Testes** (acrescentar em `tests/test_combate.py`). Usar `random.Random` com semente e inimigos montados à mão (`make_foe` + ajustes de `spd`/`hp`/`atk`):

```python
def foe(hp=10, atk=1, spd=5, boss=False, element=None, crit=0.0):
    return {"sprite": "rato", "name": "Rato", "boss": boss, "element": element, "hp": hp, "hp_max": hp,
            "atk": atk, "spd": spd, "crit": crit, "critdmg": 1.5, "status": {}}
def pet(spd=10, atk=3, crit=0.0, **fx):
    r = M.new_run("slime", {"hp": 30, "atk": atk, "spd": spd}, 1); r["base"]["crit"] = crit
    if fx:
        M.ITEMS["_t"] = {"name": "t", "fx": fx, "rarities": ["comum"], "consume": {"heal": 1},
                         "look": {"type": "obj", "anchor": "topo", "art": "adaga"}}
        r["items"] = [{"key": "_t", "rar": "comum", "floor": 1}]
    return r
# ordem: inimigo mais rápido age antes; empate -> pet antes
r = pet(spd=5); won, steps, _ = M.combate(r, M.stats(r), [foe(spd=9)], random.Random(1), 1)
assert steps[0]["who"] == 0
r = pet(spd=9); won, steps, _ = M.combate(r, M.stats(r), [foe(spd=9)], random.Random(1), 1)
assert steps[0]["who"] == "pet"
# dobro da velocidade: crítico com dano x (critdmg*2); com crit base 0.5 + 0.5 = 1.0 sempre crita
r = pet(spd=20, atk=4, crit=0.5); won, steps, _ = M.combate(r, M.stats(r), [foe(hp=100, spd=10)], random.Random(2), 1)
s = next(x for x in steps if x["who"] == "pet"); assert s["crit"] and s["dmg"] >= 3 * 3     # (4±1) * 1.5 * 2
# inimigo com o dobro também ganha (crit 0.5 + 0.5)
r = pet(spd=5); won, steps, _ = M.combate(r, M.stats(r), [foe(hp=100, spd=10, crit=0.5, atk=2)], random.Random(3), 1)
assert any(x["who"] == 0 and x["crit"] for x in steps)
# queimadura: dano por turno no começo da rodada, 3 turnos, depois para
r = pet(queimar=1.0); M.ITEMS["_t"]["fx"]["queimar"] = 1.0
won, steps, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=0, spd=1)], random.Random(4), 10)
dots = [x for x in steps if x["dot"] and x["target"] == 0]; assert dots and all(x["dmg"] == round(2 + 0.3 * 10) for x in dots)
# veneno cresce: 1, 2, 3 ...
r = pet(envenenar=0.6); won, steps, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=0, spd=1)], random.Random(5), 1)
v = [x["dmg"] for x in steps if x["dot"] and x["target"] == 0][:3]; assert v == sorted(v) and v[-1] > v[0]
# congelamento: perde o turno e sai
r = pet(congelar=0.6); won, steps, _ = M.combate(r, M.stats(r), [foe(hp=1000, atk=1, spd=1)], random.Random(6), 1)
assert any(x["who"] == 0 and x["skip"] for x in steps)
# monstro comum nunca aplica status; chefe aplica o seu elemento no pet
r = pet(); won, steps, _ = M.combate(r, M.stats(r), [foe(hp=40, atk=1)], random.Random(7), 1)
assert not any(x["who"] == 0 and x["status"] for x in steps)
r = pet(); won, steps, _ = M.combate(r, M.stats(r), [foe(hp=200, atk=1, boss=True, element="fogo")], random.Random(8), 5)
assert any(x["who"] == 0 and x["status"] == "queimadura" for x in steps)
# morte por status de chefe tem assassino "Queimadura" ou "Veneno"
r = pet(); r["hp"] = 3
won, steps, killer = M.combate(r, M.stats(r), [foe(hp=999, atk=0, spd=99, boss=True, element="fogo")], random.Random(9), 20)
assert not won and killer in ("Queimadura", "Rato")
# luta impossível termina no limite de 60 rodadas como vitória
r = pet(atk=0); r["base"]["atk"] = 0
won, steps, _ = M.combate(r, M.stats(r), [foe(hp=10**6, atk=0, spd=1)], random.Random(10), 1)
assert won and sum(1 for x in steps if x["who"] == "pet") <= M.MAX_ROUNDS
M.ITEMS.pop("_t", None)
```

Ajustar os números de semente se algum caso for sorte demais, mas mantendo o que cada assert prova. No último caso, `atk` mínimo do pet é 1 (`stats` garante `atk >= 1`); usar HP enorme no inimigo.

- [ ] **Step 2: Rodar e ver falhar.** `AttributeError: module 'masmorra' has no attribute 'combate'`.

- [ ] **Step 3: Implementar `combate`** seguindo a seção "A rodada" do spec. Pontos que o spec não fixa: o dano base de um golpe continua `max(1, atk + rng.randint(-1, 1))` (pet) e `max(1, atk − def + rng.randint(-1, 1))` (inimigo, contra o pet); a esquiva do pet continua valendo contra cada golpe inimigo; o crítico multiplica e arredonda (`round`); cada elemento do pet rola separado por alvo acertado. **GUI:** `play_room` passa a ler `ev["hits"]` como dicts (só o inimigo 0 aparece na tela por enquanto; `skip` mostra "perdeu a vez", `dot` mostra o número pequeno, `crit` mostra o número com "!"), e `ev["foes"][0]` substitui `ev["sprite"]`/`ev["boss"]`.

- [ ] **Step 4: Rodar tudo** (o `simular.py` agora muda; só precisa rodar). `test_gui` 3× seguidas.

- [ ] **Step 5: Commit.** `git commit -am "feat: combate por rodadas (velocidade, crítico, status, chefes elementais)"`

---

### Task 3: Hordas

**Files:**
- Modify: `masmorra.py` (`ROOM_WEIGHTS`, `enter_room`)
- Test: `tests/test_combate.py`

**Interfaces:**
- Consumes: `make_foe`, `combate` (Tasks 1-2).
- Produces:
  - Constantes: `HORDE_MIN_FLOOR = 3`, `HORDE_MULT = {2: 0.75, 3: 0.6, 4: 0.5}`, `HORDE_GOLD_MULT = 1.25`, `ROOM_WEIGHTS` com `("horde", 12)`.
  - `horde_max(f: int) -> int`: 2 se f < 5, 3 se f < 8, senão 4.
  - Sala `"horde"`: abaixo do andar 3 o sorteio nunca escolhe horda (re-sorteia sem ela). Tamanho `rng.randint(2, horde_max(f))`, monstros sorteados da lista do andar, `make_foe(m, f, mult=HORDE_MULT[n])`. `ev["kind"] = "horde"`, `ev["name"] = f"Horda ({n})"`. Ouro: soma do ouro de um monstro comum por inimigo × `HORDE_GOLD_MULT`. `run["kills"] += n` só na vitória. Na derrota, o assassino vem de `combate`.
  - No `combate`, sem `area` o pet ataca o inimigo vivo de menor `hp` (empate: menor índice); com `area`, `target = "todos"` e cada inimigo vivo toma um golpe (um rolar de dano e crítico por alvo).

- [ ] **Step 1: Testes:**

```python
bat = next(m for m in M.MONSTERS if m[0] == "morcego")
assert [M.horde_max(f) for f in (3, 4, 5, 7, 8, 20)] == [2, 2, 3, 3, 4, 4]
assert M.make_foe(bat, 6, mult=M.HORDE_MULT[4])["hp"] < M.make_foe(bat, 6)["hp"]
# alvo de menor HP; com área acerta todos
r = pet(atk=3); fs = [foe(hp=50), foe(hp=4), foe(hp=30)]
won, steps, _ = M.combate(r, M.stats(r), fs, random.Random(1), 3)
assert next(x for x in steps if x["who"] == "pet")["target"] == 1
r = pet(atk=3, area=True); fs = [foe(hp=50), foe(hp=4), foe(hp=30)]
won, steps, _ = M.combate(r, M.stats(r), fs, random.Random(1), 3)
first = [x for x in steps if x["who"] == "pet"][:3]; assert {x["target"] for x in first} >= {0, 1, 2} or first[0]["target"] == "todos"
# pet morre no meio da rodada: inimigos seguintes não agem depois da morte
r = pet(); r["hp"] = 1
won, steps, killer = M.combate(r, M.stats(r), [foe(hp=99, atk=5, spd=20), foe(hp=99, atk=5, spd=19)], random.Random(2), 3)
assert not won and steps[-1]["target"] == "pet" and killer == "Rato"
# horda via enter_room: nunca antes do andar 3; kills e ouro maior
rng = random.Random(3); meta = M.new_meta(); seen = False
for _ in range(400):
    run = M.new_run("slime", {"hp": 999, "atk": 50}, 1); run["floor"] = rng.choice([1, 2, 6]); run["energy"] = 1e9
    ev = M.enter_room(run, meta, rng)
    if ev.get("kind") == "horde":
        seen = True; assert run["floor"] >= 3 and 2 <= len(ev["foes"]) <= M.horde_max(run["floor"])
        assert run["kills"] == len(ev["foes"]) and ev["gold"] > 0
assert seen
M.ITEMS.pop("_t", None)
```

(A asserção da área aceita o formato escolhido: um passo com `"todos"` ou um passo por alvo; documentar qual foi usado.)

- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.** A GUI ainda mostra só o inimigo 0 (Task 4 faz o grid), mas não pode quebrar com `kind == "horde"`.
- [ ] **Step 4: Rodar tudo**, `test_gui` 3×.
- [ ] **Step 5: Commit.** `git commit -am "feat: hordas de 2 a 4 inimigos e ataque em área"`

---

### Task 4: GUI do combate

**Files:**
- Modify: `tokenlike.py` (`build`, `show_foe`/`hide_foe`, `play_room`, painel, `show_stats`)
- Modify: `tests/test_gui.py`

**Interfaces:**
- Consumes: `ev["foes"]`, `ev["hits"]` (Tasks 2-3); passos com `who/target/dmg/crit/status/skip/dot/dodge`.
- Produces:
  - Até 4 inimigos na tela num grid 2×2 no lado direito; com 1 inimigo, igual a hoje (centralizado, tamanho atual). Com 2–4, cada um desenhado em escala menor (`self.px`, não `self.bpx`). A janela pode alargar o mínimo necessário; `self.W` continua estável ao trocar o tamanho do pet (`change_size`).
  - Cores de status: `STATUS_COR = {"queimadura": "#ff9f43", "eletricidade": "#fff27a", "veneno": "#4fbf5a", "congelamento": "#9fe8ff"}`. Inimigo com status: imagem tingida (recolorir via `visual.tingir` sobre `visual.grid_to_map` da arte, cache por `(sprite, boss, status)`). Pet com status: o painel mostra o nome do status ao lado do HP, na cor do status (o tingido do pet é opcional nesta task).
  - Crítico: floater dourado (`GOLD`) com `"!"`. Ataque elemental do pet: `burst` no alvo com a cor do elemento. `skip`: floater "perdeu a vez" (`MUTED`). `dot`: floater pequeno na cor do status.
  - No máximo 12 passos animados por sala (os primeiros 11 e o último), como hoje com 8.
  - Status (duplo clique): linha `Velocidade N   Crítico X%   Dano crítico ×Y`.

- [ ] **Step 1: Teste em `tests/test_gui.py`** (depois dos blocos existentes; cada `PetApp` com `rng = random.Random(SEED)`):

```python
app6 = tp.PetApp(Args()); PENDING.clear(); app6.rng = random.Random(SEED)
w0 = app6.W
for size in ("Pequeno", "Grande", "Médio"): app6.size_var.set(size); app6.change_size()
assert app6.W == w0
seen_horde = False
for _ in range(600):
    app6.busy_until = 0
    if app6.run["dead"]:
        app6.respawn_at = 1
    app6.run["energy"] = 10 * M.ROOM_COST
    app6.run["floor"] = max(app6.run["floor"], 3)
    app6.tick()
    fns = PENDING[:]; PENDING.clear()
    for fn in fns:
        if fn is None or getattr(fn, "__name__", "") in ("tick", "poll"): continue
        fn()
    seen_horde = seen_horde or any(k == "horde" for k in getattr(app6, "_ultimo_kind", [""]))
app6.show_stats(); app6.quit()
```

e, em `PetApp.play_room`, guardar `self._ultimo_kind = [ev["kind"]]` (só para o teste). Acrescentar `assert seen_horde`.

- [ ] **Step 2: Rodar e ver falhar** (`AttributeError` ou `assert seen_horde`).
- [ ] **Step 3: Implementar.** Testar também `python -c` gerando um `render_grid` tingido para cada status sem exceção.
- [ ] **Step 4: Rodar tudo**, `test_gui` 3×, nenhuma "erro" no log.
- [ ] **Step 5: Ver na tela** não é possível sem monitor: registrar no relatório.
- [ ] **Step 6: Commit.** `git commit -am "feat: tela do combate novo (grid de inimigos, crítico, status)"`

---

### Task 5: Estatísticas por categoria de morte

**Files:**
- Modify: `masmorra.py` (`die`, `run_record`), `tokenlike.py` (`log_run`), `tools/simular.py`, `tools/estatisticas.py`
- Test: `tests/test_registro.py`, `tests/test_estatisticas.py`

**Interfaces:**
- Produces:
  - `die(run, meta, ev, killer, kind="monster")`: o cemitério guarda `"kind"`. Categorias: `"monster"`, `"horde"`, `"boss"`, `"mimic"`, `"trap"`, `"status"` (quando o assassino é "Queimadura"/"Veneno"), `"desistiu"`.
  - `run_record(run, killer, gave_up, mode, achievements, killer_kind="")`: a linha ganha `killer_kind` (entra no conjunto de chaves do teste de formato).
  - `tools/estatisticas.py`: `mortes(recs)` ganha `"por_tipo": dict[str, int]`; a página mostra essa contagem em "Onde as runs morrem" (sim e real). `_linha_ok` aceita linhas antigas sem `killer_kind` (contam como `"?"`).
  - `tools/simular.py`: o `main()` imprime também uma linha `  mortes por tipo: {...}` depois de "matadores".

- [ ] **Step 1: Testes:** `run_record` tem `killer_kind`; morte em horda gera `kind == "horde"` no cemitério; `E.mortes([...])["por_tipo"]` conta certo com linhas montadas à mão (inclusive uma linha antiga sem a chave → `"?"`); `coletar` + `gerar_html` contêm "horde"/"Horda".
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Implementar.** Todos os chamadores de `die` passam o `kind` certo (o mímico usa `"mimic"`, armadilha `"trap"`, desistência `"desistiu"`).
- [ ] **Step 4: Rodar tudo.**
- [ ] **Step 5: Commit.** `git commit -am "feat: estatísticas separam mortes por tipo (horda, chefe, status...)"`

---

### Task 6: Rebalanceamento e documentação

**Files:**
- Modify: `masmorra.py` (só números), `CLAUDE.md`, `LEIA-ME.md`, `README.md`, `characters/fantasma/character.json` (se o Fantasma ganhar `spd`)

**Interfaces:**
- Consumes: tudo. Referência guardada antes do projeto: `docs/balanceamento/baseline-pre-combate.json`.

- [ ] **Step 1: Medir.** `python tools/estatisticas.py --sem-abrir` e `python tools/simular.py`; comparar com a referência.
- [ ] **Step 2: Ajustar** até a calibração (Slime, sem e com conquistas) ficar dentro das `METAS` de `tools/estatisticas.py`. Ordem de alavancas: números de status e crítico; velocidades; peso e multiplicadores da horda; só então as curvas de monstro/chefe. Conferir que hordas e status de chefe aparecem nas mortes (não podem ser 0% nem a maioria absoluta: hordas entre 5% e 35% das mortes, *decisão minha*).
- [ ] **Step 3: Rodar tudo** + `test_gui` com `SEED` 1..5 (sem commitar as trocas de semente); todas passam.
- [ ] **Step 4: Documentação.** `CLAUDE.md`: "Como as peças se encaixam" (rodada, velocidade, crítico, status, hordas, `REGRAS_REV = 2`, números novos do simulador) e "Para adicionar coisas" (monstro novo tem `spd_mult`; chefe novo precisa de `BOSS_ELEMENT`; campos de `fx` novos). `LEIA-ME.md`/`README.md`: o item de combate em "Como a masmorra funciona" (velocidade, crítico, status, hordas) e `spd` no formato do `character.json`.
- [ ] **Step 5: Commit.** `git commit -am "chore: rebalanceia o combate novo e atualiza docs"`
