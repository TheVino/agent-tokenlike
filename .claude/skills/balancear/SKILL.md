---
name: balancear
description: Analisa a saúde do balanceamento do jogo (metas, itens verdes e vermelhos, pares, onde morrem, simulado x real) e propõe mudanças de números em masmorra.py. Use quando o dono pedir "balancear", "balanceamento", "saúde do jogo" ou "estatísticas dos itens".
---

# Balancear

Nunca edite arquivo sem a aprovação explícita do dono. Primeiro relate, depois proponha.

## Passos

1. Rode `python tools/estatisticas.py --sem-abrir` (opções: `--runs N`, `--real-dir DIR`, `--todas-versoes`).
2. Leia `tools/saida/estatisticas.json`. Chaves:
   - `calibracao.sem_conquistas` e `calibracao.com_conquistas`: só slime, igual ao `tools/simular.py`. As metas são julgadas aqui.
   - `sim`, `sim_sem_conquistas` (todos os heróis misturados, só informativo) e `real`. Cada um tem `n`, `mediana`, `p90`, `max`, `passou_chefe1`, `itens_med`.
   - `metas`: `sem_conquistas`, `com_conquistas` e `real`, com True/False por meta (`null` no real sem runs). Valores-alvo em `METAS` de `tools/estatisticas.py`.
   - `itens.<chave>.sim` / `.real`: `n`, `durou`, `vs_esperado` (bruto), `vs_media` (vs_esperado menos a média ponderada dos itens daquela fonte), `mortes_rapidas`, `consumido_por_modo`.
   - `pares.sim.melhores` / `pares.sim.piores` (e `pares.real.*`): `a`, `b`, `n`, `vs_esperado`, `ganho`. Os piores nunca repetem os melhores.
   - `mortes.sim` / `mortes.real`: `por_andar`, `matadores`, `por_tipo` (monster, horde, boss, mimic, trap, status; "?" em linha antiga). `herois.sim` / `herois.real`: `n`, `mediana`, `p90` por herói.
   - `info_real`: `modos`, `desistencias`, `ignoradas`, `outras_versoes`.
3. Relate, curto:
   - metas ✓/✗ da calibração (sem e com conquistas) e do real;
   - itens verdes (`vs_media` > +1) e vermelhos (`vs_media` < −1). Use `vs_media`, não `vs_esperado`: pegar qualquer item já ajuda, então o bruto sai quase todo positivo. Ignore sim com `n` pequeno; real com `n` < 10 é baixa confiança, diga isso;
   - pares fortes demais (`ganho` > +1,5) e anti-sinergias (`ganho` < −1,5). Par só conta com `n` >= 30;
   - onde morrem (andar, matadores e tipo). Hordas devem ficar entre 5% e 35% das mortes; status acima de 0 e sem ser a maioria;
   - diferença sim x real, só se o real tiver 10 runs ou mais. Runs `gave_up` já ficam fora.
   "durou" = andares que a run durou depois de pegar o item. "vs esperado" = durou menos a média restante das runs vivas naquele andar.
4. Proponha mudanças de números em `masmorra.py`, cada uma com o motivo e o efeito esperado. Ordem das alavancas (a de `CLAUDE.md`): raridade (`RAR_MULT`, pesos) -> `consume` -> baú/mímico/loja (`SHOP_PRICE`); no combate: status e crítico -> velocidades -> horda (peso em `ROOM_WEIGHTS`, `horde_max`, `HORDE_GOLD_MULT`; `HORDE_MULT` é do dono) -> só então as curvas de monstro/chefe (`MON_*`/`BOSS_*`). Para a cauda (máx e runs muito longas), a alavanca é `BOSS_RAMP` (rampa extra dos chefes depois do andar `BOSS_RAMP_FROM`), que não mexe no 1º e no 2º chefe. Mude pouco por vez.
   - **Item verde ou vermelho:** mexa primeiro no `fx` do próprio item, não nas curvas. Além de `atk`/`def`/`maxhp`/`dodge`/`gold`/`lifesteal`/`energy`/`trap`, cada item pode usar os campos das famílias: `spd`, `crit`, `critdmg`, `area`, `queimar`/`eletrizar`/`envenenar`/`congelar`, `bloqueio`, `espinhos`, `cura_sala`, `cura_andar`, `custo_ataque`, `furia`, `duplo`, `ajudante`, `crescer` (menor = mais forte), `sorte` e `desconto`. Os tetos (`MAX_CRIT`, `MAX_ELEM_CHANCE`, `MAX_BLOQUEIO`, `MAX_ESPINHOS`, `MAX_DUPLO`, `MAX_SORTE`, `MAX_DESCONTO`, `MAX_DODGE`) valem sobre a soma e só pesam em builds empilhadas. `atk` e `critdmg` sem teto alongam a cauda; prefira atributos com teto. Itens só lendários costumam ter `n` < 100: trate como amostra pequena. A `vela` e itens de `energy`/`sorte`/`gold`/`desconto` puros saem fracos no sim por natureza (o sim não usa energia; ouro só vale na loja).
5. Espere a aprovação do dono. Sem "sim" explícito, não edite nada.
6. Depois de editar: rode todos os testes de `tests/`, `python tools/simular.py` e `python tools/estatisticas.py --sem-abrir` de novo. Mostre antes e depois.
7. Avise que a `BALANCE_VERSION` mudou (se mudou fórmula ou número escrito no código, suba `REGRAS_REV` em `masmorra.py`, hoje 7): o histórico real (`~/.tokenlike/runs.jsonl`) recomeça na versão nova; as runs antigas só aparecem com `--todas-versoes`.
