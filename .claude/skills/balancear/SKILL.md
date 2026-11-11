---
name: balancear
description: Analisa a saúde do balanceamento do jogo (metas, itens verdes e vermelhos, pares, onde morrem, simulado x real) e propõe mudanças de números em masmorra.py. Use quando o dono pedir "balancear", "balanceamento", "saúde do jogo" ou "estatísticas dos itens".
---

# Balancear

Nunca edite arquivo sem a aprovação explícita do dono. Primeiro relate, depois proponha.

## Passos

1. Rode `python tools/estatisticas.py --sem-abrir` (opções: `--runs N`, `--real-dir DIR`, `--todas-versoes`).
2. Leia `tools/saida/estatisticas.json`. Chaves: `sim`, `sim_sem_conquistas`, `real` (cada um com `n`, `mediana`, `p90`, `max`, `passou_chefe1`, `itens_med`), `metas` (✓/✗ por bloco, valores-alvo em `METAS` de `tools/estatisticas.py`), `itens` (por item: `sim` e `real` com `n`, `durou`, `vs_esperado`, `mortes_rapidas`, `consumido_por_modo`), `pares` (`melhores`/`piores` com `ganho`), `mortes` (`por_andar`, `matadores`), `herois`, `info_real`.
3. Relate, curto:
   - metas ✓/✗ (sim, sim sem conquistas, real);
   - itens verdes (`vs_esperado` > +1) e vermelhos (< −1). Ignore sim com `n` pequeno; real com `n` < 10 é baixa confiança, diga isso;
   - pares fortes demais (`ganho` > +1,5) e anti-sinergias (ganho muito negativo). Par só conta com `n` >= 30;
   - onde morrem (andar e matadores);
   - diferença sim x real, só se o real tiver 10 runs ou mais. Runs `gave_up` já ficam fora.
   "durou" = andares que a run durou depois de pegar o item. "vs esperado" = durou menos a média restante das runs vivas naquele andar.
4. Proponha mudanças de números em `masmorra.py`, cada uma com o motivo e o efeito esperado. Ordem das alavancas (a de `CLAUDE.md`): raridade (`RAR_MULT`, pesos) -> `consume` -> baú/mímico/loja (`SHOP_PRICE`) -> só então `MON_*`/`BOSS_*`. Mude pouco por vez.
5. Espere a aprovação do dono. Sem "sim" explícito, não edite nada.
6. Depois de editar: rode todos os testes de `tests/`, `python tools/simular.py` e `python tools/estatisticas.py --sem-abrir` de novo. Mostre antes e depois.
7. Avise que a `BALANCE_VERSION` mudou: o histórico real (`~/.tokenlike/runs.jsonl`) recomeça na versão nova; as runs antigas só aparecem com `--todas-versoes`.
