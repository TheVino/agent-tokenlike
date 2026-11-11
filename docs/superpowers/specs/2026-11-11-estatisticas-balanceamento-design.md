# Estatísticas de balanceamento (projeto 1 de 3 do roadmap)

Data: 2026-11-11. Projeto: Agent Tokenlike. Ler o `CLAUDE.md` antes; as regras de lá valem
(privacidade, só biblioteca padrão no app, Pillow só em `tools/`, inatividade nunca pune).

## Intenção

O jogo vai crescer muito (combate novo com velocidade, crítico, status e hordas; itens de 20
para 100). O dono quer cuidar da "saúde do jogo": a cada mudança, medir se algum item ficou forte
ou fraco demais, quais combinam bem e onde as runs morrem. Isso vem **antes** do combate novo,
para termos uma base do jogo atual e podermos comparar cada mudança com ela.

As estatísticas são **só para quem desenvolve**. O jogador final não vê nada novo.

## Roadmap (contexto)

1. **Este documento:** estatísticas.
2. Combate novo (velocidade, crítico, 4 status elementais, hordas de 2 a 4, chefes com elemento).
3. Itens até 100, em levas de ~20.
4. Pets do Petdex.

Antes do lançamento público, fica pendente (não faz parte deste projeto, mas precisa ser anotado
no `CLAUDE.md`): visual caprichado e ícones de itens e heróis na página de estatísticas; screenshot
e GIF do README; teste na tela de verdade do modo interativo e das barras de sessão e semana.

## Objetivos

- Toda run real terminada fica registrada localmente com o que importa para o balanceamento.
- O simulador produz os mesmos registros, no mesmo formato, para milhares de runs.
- Um comando gera uma página HTML com as estatísticas, comparando simulado e real lado a lado.
- Uma skill do Claude Code no repositório (`/balancear`) roda tudo e sugere ajustes.

## Fora do escopo

- Qualquer tela nova para o jogador. Nada no menu do pet.
- Compartilhar estatísticas pela internet, ranking ou média da comunidade (fica para depois).
- Ícones e capricho visual da página (pré-lançamento).
- Mudar o balanceamento atual. Este projeto só mede.

## Anti-objetivos

- O app ficar mais lento ou o save crescer sem controle.
- Gravar qualquer coisa do Claude Code além do que já se usa. O registro é só de dados do jogo.
- Misturar runs do modo demo com runs reais.
- Comparar runs reais de versões diferentes do balanceamento como se fossem iguais.

## Decisões do dono

- A régua de um item bom é **quantos andares a run durou depois de pegar o item**, mais o andar
  final.
- Fontes: o **simulado** roda a cada mudança no jogo; o **real** serve para conferir se a
  simulação bate com o jogo de verdade.
- Formato: página **HTML** que abre no navegador. É ferramenta de desenvolvimento, não do jogador.
- A **skill** fica integrada ao Claude Code, dentro do repositório.
- Na página, o rótulo das colunas é **"sim / real"**.
- Seções aprovadas no rascunho:
  - resumo simulado × real;
  - tabela de itens: quantas vezes é pego, andar em que é pego, quanto durou, andar final,
    presença em mortes rápidas, quantas vezes foi consumido;
  - melhores pares (sinergia);
  - onde as runs morrem (andar e quem matou);
  - heróis.

## Dados

### Registro de cada item pego

Cada entrada de `run["items"]` passa a guardar também o andar em que foi pega:
`{"key", "rar", "floor"}`. Saves antigos: `migrate_run` preenche `floor` com `None`.
`run["consumed"]` (lista nova, `{"key", "rar", "floor"}`) guarda os itens consumidos.
O código que hoje lê `run["items"]` continua funcionando, porque só ganha um campo.

### Registro das runs reais

- Arquivo `~/.tokenlike/runs.jsonl`, uma linha JSON por run terminada (morte ou desistência).
  Só acrescenta linhas, sem reescrever o arquivo.
- O modo demo grava em `~/.tokenlike/runs-demo.jsonl`, que a página ignora.
- Conteúdo de cada linha:
  `run`, `char`, `floor`, `room`, `killer`, `gave_up` (bool), `items` (lista com key, rar, floor),
  `consumed`, `gold`, `kills`, `bosses`, `date`, `mode` (auto ou interativo), `version`.
- `version` é `M.BALANCE_VERSION`: um hash curto (8 caracteres) calculado no import a partir de
  `ITEMS`, `MONSTERS` e das constantes de balanceamento de `masmorra.py`. Muda sozinho quando um
  número de balanceamento muda, sem ninguém lembrar de atualizar.
- Erro de escrita nunca derruba o app: é só logado.

### Simulado

- `tools/simular.py` passa a gerar os mesmos registros (mesmo formato de linha), em memória e
  opcionalmente num arquivo.
- Continua imprimindo o resumo de hoje, para não quebrar o hábito nem o `CLAUDE.md`.
- Roda os dois heróis embutidos e os de `characters/` (com os stats deles), com e sem todas as
  conquistas, no modo auto e com semente fixa.

## Métricas

Com N = runs que pegaram o item:

- **Pego:** % das runs em que o item foi pego (real: contagem absoluta e %).
- **Andar em que é pego:** mediana.
- **Durou:** média de `andar_final − andar_pego`.
- **Durou vs esperado:** `durou − esperado(andar_pego)`, onde `esperado(f)` é a média de andares
  restantes de todas as runs que estavam vivas no andar f.
  - É o número que decide verde ou vermelho, porque um item pego tarde naturalmente "dura" menos.
  - Verde: acima de +1 andar. Vermelho: abaixo de −1 andar.
- **Andar final:** média.
- **Em mortes rápidas:** % das runs com o item que morreram até 2 andares depois de pegá-lo.
- **Consumido:** % das vezes que o item foi oferecido e acabou consumido.
- **Pares:** para cada par de itens com pelo menos 30 runs simuladas juntas:
  - ganho do par = (durou vs esperado, contado do andar em que o segundo item foi pego) − o
    maior "durou vs esperado" dos dois itens sozinhos;
  - mostrar os 10 maiores e os 5 menores (anti-sinergia).
- **Resumo:** número de runs, mediana, p90 e máximo do andar, % que passou do 1º chefe, itens por
  run. As metas atuais (do `CLAUDE.md`) aparecem junto de cada número, com ✓ ou ✗.
- **Onde morrem:** histograma do andar da morte (sim e real) e os 6 que mais matam.
- **Heróis:** mediana e p90 por herói.
- **Real com pouca amostra:** item com menos de 10 runs reais mostra o número esmaecido e com
  aviso.
- **Versões:** por padrão, o real usa só as runs da `BALANCE_VERSION` atual. A página mostra
  quantas runs de outras versões existem e aceita `--todas-versoes`.

## Ferramentas

- `tools/estatisticas.py`:
  - roda a simulação (2.000 runs por padrão, `--runs N`), lê o `runs.jsonl` real, calcula tudo e
    grava duas saídas em `tools/saida/` (pasta no `.gitignore`):
    - `estatisticas.html`: uma página só, sem internet e sem dependência, com CSS e SVG embutidos,
      no visual escuro do jogo;
    - `estatisticas.json`: os mesmos números, para a skill ler.
  - abre a página no navegador (`webbrowser`), a não ser com `--sem-abrir`.
  - `--real-dir` permite apontar para outra pasta de dados (padrão `~/.tokenlike`).
  - só biblioteca padrão, como o resto de `tools/` que não precisa de Pillow.
- Skill `.claude/skills/balancear/SKILL.md` (em pt-BR):
  - roda `python tools/estatisticas.py --sem-abrir`;
  - lê o JSON e compara com as metas;
  - aponta os itens fora da curva (verde ou vermelho com amostra suficiente), os pares fortes
    demais, onde as runs morrem e a diferença entre simulado e real;
  - propõe ajustes de números explicando o porquê;
  - **só altera arquivos com a aprovação do dono**;
  - depois de aplicar, roda de novo e mostra o antes e o depois.

## Metas de balanceamento

As metas ficam num lugar só, numa constante `METAS` em `tools/estatisticas.py`, e o `CLAUDE.md`
aponta para lá. Valores atuais:

- passou do 1º chefe entre 0,35 e 0,45;
- p90 do andar entre 13 e 16;
- máximo até 25 (aceito pelo dono depois do rebalanceamento da parte 1).

## Detalhes decididos (*decisões minhas*, depois da revisão)

- **Uma função só monta a linha:** `M.run_record(run, meta, gave_up, mode, achievements) -> dict`,
  em `masmorra.py`. A GUI grava o arquivo (real ou demo) quando a run termina, tanto na morte
  (`on_death`) quanto em `give_up`; o simulador chama a mesma função. Formato garantido igual.
- **Conquistas na linha:** a linha guarda `achievements`, a lista de conquistas que o jogador tinha
  **no começo da run** (a GUI guarda isso em `run["ach_start"]` no `new_run`). O pool de itens
  depende delas.
- **Qual é a coluna "sim":**
  - por padrão, as runs simuladas com **todas as conquistas**, com os heróis em partes iguais;
  - o resumo mostra também a linha "sim sem conquistas";
  - `esperado(f)` é calculado separado para cada fonte (sim e real), cada um com as próprias runs;
  - as metas ✓/✗ são julgadas no "sim com todas as conquistas" e no "sim sem conquistas", como o
    simulador já imprime hoje.
- **Desistências:** ficam no arquivo (`gave_up: true`), mas **não entram** em durou, esperado,
  mortes rápidas, onde morrem e quem mata, porque a run foi cortada e não terminou. O resumo mostra
  quantas foram. Runs em andamento não estão no arquivo e não entram.
- **Modo:** a linha grava o modo do momento em que a run terminou. O real usa as runs dos dois
  modos juntas e o resumo mostra quantas são de cada. A coluna "Consumido" mostra o real separado
  por modo, porque no interativo quem escolhe é o jogador.
- **`BALANCE_VERSION`:** hash só dos números de balanceamento.
  - Entram: `fx`, `consume`, `rarities` e `req` de cada item; `MONSTERS`; `ROOM_COST`, `ROOMS_PER_FLOOR`, `MAX_STORED_ROOMS`, `BOSS_EVERY`, `MON_HP`,
    `MON_ATK`, `BOSS_HP`, `BOSS_ATK`, `REGEN_PER_ROOM`, `FLOOR_BONUS_HP`, `ROOM_WEIGHTS`,
    `RAR_MULT`, os pesos de raridade (como tabela de números, ou os coeficientes da função) e os
    tetos (`energy`, `trap`, `dodge`), além de `CHEST_ITEM_CHANCE` e `SHOP_PRICE`.
  - Não entram: nomes (inclusive `BOSS_NAMES`), `look` e qualquer coisa visual.
  - Stats de heróis não entram, porque cada linha já guarda `char`.
  - O construtor junta tudo numa estrutura ordenada, faz `json.dumps(..., sort_keys=True)` e tira
    `sha1[:8]`.
- **Denominador do "Consumido":** cada oferta resolvida conta uma vez, seja pegar ou consumir.
  Consumido = consumidos ÷ (pegos + consumidos). Um item consumido pode voltar a ser oferecido na
  mesma run, e cada oferta conta. Uma oferta pendente quando a run termina não conta.
- **Metas:** as faixas acima são **metas**, não um retrato. O `CLAUDE.md` passa a apontar para
  `METAS` e a mostrar o último resultado do simulador separado delas.

## Testes

- `tests/test_estatisticas.py`:
  - as métricas em dados pequenos montados à mão (durou, esperado, mortes rápidas, pares com
    amostra mínima, versão filtrada, demo ignorado);
  - o HTML é gerado e contém as seções;
  - o JSON tem as chaves que a skill usa.
- Um item pego grava `floor`; `migrate_run` lida com item sem `floor`; morte e desistência
  acrescentam uma linha ao `runs.jsonl` certo (real ou demo); `BALANCE_VERSION` muda quando um
  número de `ITEMS` muda.
- Todos os testes atuais continuam passando.

## Fica a critério do construtor

- O layout exato do HTML (seguindo o rascunho aprovado, com o visual escuro do jogo).
- Como a skill formata a sugestão.
- Se o simulador grava arquivo por padrão ou só sob demanda.
