# Agent Tokenlike: Masmorra de Tokens

Pet de pixel art que fica sobre a tela do Windows (overlay transparente, sempre por cima) e
desce uma masmorra roguelike usando como energia os tokens gastos no Claude Code.
Antes se chamava TokenPet. Projeto pessoal e não oficial (sem vínculo com a Anthropic); interface e textos em **português (pt-BR)**.

## Arquivos

- `tokenlike.py`: app (tkinter). Contém a leitura de tokens (`TokenReader`), o estado/salvamento,
  os personagens (Slime embutido + loader de PNG) e a GUI (`PetApp`). O `tkinter` é importado só em
  `run_gui()`, para o resto do módulo ser testável sem tela.
- `masmorra.py`: regras do jogo, puras e sem GUI: energia, salas, combate, itens, conquistas, morte.
  `enter_room()` resolve uma sala e devolve um dicionário de evento, que a GUI só anima (`PetApp.play_room`).
- `arte.py`: toda a pixel art em grades de texto (`'.'` = transparente, letras = cores de `PAL`).
  Itens, monstros, salas, coroa de chefe. `BOSS_PAL` recolore os monstros para os chefes.
- `visual.py`: efeitos puros sobre mapas de pixels `{(x, y): "#rrggbb"}` (sem tkinter): `espinhos`, `gotas`,
  `contorno`, `tingir`, `adesivo`, `objeto` e `compose()`, que monta o pet com os `look` dos itens empilhados
  (brilho na cor da raridade). `LOOK_BOX` limita a área: em cada âncora ficam só os objetos mais recentes que cabem
  inteiros nela (os mais antigos daquele ponto deixam de ser desenhados); a GUI só recompõe quando a lista de itens muda (`refresh_look`).
- `characters/<pasta>/character.json` + PNGs: heróis extras (ex.: `fantasma`). O formato está no `LEIA-ME.md`.
- `tests/`: `test_limites.py` (statusline grava só os limites; leitura, dado velho, cores, fuso), `test_migracao.py` (cópia de `~/.tokenpet` para `~/.tokenlike`), `test_reader.py` (leitura de logs, deduplicação, arte),
  `test_itens.py` (raridade, empilhar, pegar/consumir, escudo, tetos, pendência, migração do save de 3 espaços),
  `test_registro.py` (`run_record`, `runs.jsonl`), `test_estatisticas.py` (métricas e página),
  `test_visual.py` (efeitos de `visual.py` e composição do pet) e `test_gui.py` (tkinter falso
  que executa os callbacks `after`, joga centenas de salas, morre, renasce, troca de herói e testa o modo interativo;
  usa `random.Random(SEED)` para ser determinístico).
- `tools/simular.py`: simula 2.000 runs e mostra a distribuição de andares, a taxa de passar do 1º chefe e quem mais mata.
  `tools/estatisticas.py`: gera `tools/saida/estatisticas.html` e `.json` (gitignored) com simulado x real, itens, pares, mortes e heróis; `METAS` (metas de balanceamento) mora aí.
  `tools/preview_arte.py`: gera um PNG com todos os desenhos (precisa do Pillow, só para desenvolvimento).
- `README.md` (inglês, para o GitHub) e `LEIA-ME.md` (pt-BR). Licença MIT.
- `statusline.py`: statusline opcional do Claude Code (o usuário liga). Lê o JSON do stdin e grava só os limites oficiais
  de sessão (5h) e semana em `~/.tokenlike/limites.json`. O pet lê com `read_limits` a cada poll e desenha as barras
  Sessão/Semana no painel (verde ≤50%, amarelo ≤80%, vermelho acima; `—` quando o reset já passou). Sem o arquivo,
  as barras não aparecem e a janela fica do tamanho de antes.
- `.claude/skills/balancear/`: skill `/balancear` (lê as estatísticas e propõe mudanças de números, só edita com aprovação do dono).
- `iniciar.bat` (pythonw, sem console), `testar-demo.bat` (`--demo`: tokens falsos, estado separado).

## Comandos

```
python tests/test_reader.py
python tests/test_itens.py
python tests/test_visual.py
python tests/test_gui.py
python tests/test_migracao.py
python tests/test_limites.py
python tests/test_registro.py
python tests/test_estatisticas.py
python tools/estatisticas.py    # página de estatísticas (sim x real); --sem-abrir não abre o navegador
python tools/simular.py          # depois de mexer em balanceamento/itens/salas
python tools/preview_arte.py     # depois de mexer em arte.py
python tokenlike.py --demo        # ver na tela de verdade
```

Rode os testes depois de qualquer mudança. Quando mexer em `masmorra.py`, rode também o simulador.
O `test_gui.py` falha se aparecer "erro" em `~/.tokenlike/tokenlike.log` (num HOME temporário).

## Regras do projeto (não quebrar)

1. **Privacidade:** dos `.jsonl` do Claude Code (`~/.claude/projects/**`, ou `CLAUDE_CONFIG_DIR`) só se usa
   `message.usage`. Nunca guardar, mostrar ou logar conteúdo de prompts e respostas. Sem rede, sem telemetria,
   sem hooks, sem alterar configs do Claude Code. Exceção opcional e manual: `statusline.py` é uma statusline que o
   **próprio usuário** liga no `settings.json` dele; ela grava só `rate_limits` (porcentagem e reset de 5h/semana) em
   `~/.tokenlike/limites.json`. O app só lê esse arquivo e nunca instala nem edita a statusline.
2. **Só biblioteca padrão** no app (tkinter, json etc.). O Pillow só é aceito em `tools/`.
3. **Windows primeiro:** a transparência usa `-transparentcolor` com a cor chave `#ff00fe`. Texto sempre sobre
   um retângulo sólido (`PANEL_BG`); se ficar direto sobre a cor chave, o antialiasing deixa um contorno rosa.
   Em outros sistemas o app cai num fundo escuro.
4. **Arte 100% original.** Nada de personagens, sprites ou nomes de jogos existentes (ex.: The Binding of Isaac).
   O clima é roguelike sombrio e fofo, mas com identidade própria.
5. **Ficar sem usar não pune:** inatividade nunca mata o pet nem tira progresso, ele só descansa (recupera HP) e dorme.
   O perigo fica dentro da masmorra.
6. Deduplicar o uso por `message.id:requestId`, porque o Claude Code grava a mesma resposta em várias linhas.
   Ler só linhas completas (terminadas em `\n`) e guardar o offset de cada arquivo.

## Como as peças se encaixam

- XP de tokens = entrada + saída + criação de cache + 10% da leitura de cache (`CACHE_READ_WEIGHT`). Vira `run["energy"]`.
- `ROOM_COST` = 100 mil por sala, com no máximo 20 salas guardadas. São 5 salas por andar e depois a escada;
  o chefe vem na sala 5 dos andares múltiplos de 5.
- Evolução dentro da run por **andar** (`stage_floors` do herói), com +4 HP máx e +1 ATK.
- **Itens empilham:** `run["items"]` é uma lista de `{"key", "rar"}` sem limite (cada item no máximo uma vez por run).
  Raridade `comum|raro|epico|lendario` multiplica os valores positivos de `fx` e de `consume` por `RAR_MULT`
  (negativos e `trap` não escalam); `_rarity_weights(andar)` sorteia a raridade e cada item lista as `rarities` possíveis.
  Cores (`RAR_COLOR`): raro azul, épico roxo, lendário dourado.
- **Pegar ou consumir:** cada oferta (baú, mímico, chefe, loja) pode ser pega (entra na lista) ou consumida
  (`consume`: `heal` cura na hora, `shield` vira escudo, que absorve dano antes do HP em `apply_damage`).
  Modo `auto` (`state["mode"]`): `auto_choice` consome cura se o HP < 40%, senão pega. Modo `interativo`: a oferta
  fica em `run["pending"]` (salva no state) e a GUI abre a janela de escolha; sem resposta em `CHOICE_WINDOW_S` (30 s),
  a regra automática decide quando a próxima sala estiver pronta. Nunca entra em sala com pendência aberta.
- **Tetos:** `energy` somada ≤ +100% (`MAX_ENERGY_BONUS`), multiplicador de armadilha em `TRAP_LIMITS` (0,25 a 3),
  esquiva ≤ `MAX_DODGE`. Saves antigos de 3 espaços viram itens comuns em `migrate_run`.
- **Combate por rodadas** (`masmorra.combate`, inimigos são dicts de `make_foe`/`make_mimic`): a cada rodada,
  1) dano de status (queimadura e veneno, ignoram escudo); 2) todos agem por `spd`, do maior para o menor (empate: pet
  primeiro, depois a ordem da lista). Pet: `PET_SPD` 10 (ou `stats.spd` do herói), `PET_CRIT`, `PET_CRITDMG`.
  Monstro: `spd` = `MON_SPD` (base + por andar) x `spd_mult` do monstro (x `BOSS_SPD_BONUS` no chefe), crítico fixo
  (`MON_CRIT`/`BOSS_CRIT`, dano `FOE_CRITDMG`). Quem tem o **dobro da velocidade** do alvo ganha `DOBRO_CRIT` de
  chance e `critdmg` x2 (vale dos dois lados; o esqueleto lento apanha muito crítico).
- **Status:** chefes têm elemento (`BOSS_ELEMENT`) e aplicam o status com `BOSS_STATUS_CHANCE` por golpe; itens com
  `queimar|eletrizar|envenenar|congelar` aplicam nos inimigos. Queimadura (`QUEIMA`, `QUEIMA_TURNOS`) e veneno
  (pilhas de 1,2,3,4 de dano, até `VENENO_MAX_PILHAS`) tiram HP; eletricidade (`ELETRO_CHANCE`) e congelamento
  (`GELO_CHANCE`) fazem perder a vez. Morte por Queimadura/Veneno vira `kind` "status" no cemitério.
- **Hordas** (`"horde"` em `ROOM_WEIGHTS`, a partir de `HORDE_MIN_FLOOR`): 2 a `horde_max(andar)` inimigos com HP/ATK
  x `HORDE_MULT[n]`, ouro x `HORDE_GOLD_MULT`, nunca chefe. Sem `area` o pet bate no de menor HP; com `area`, em todos.
- **Empate:** a luta para em `MAX_ROUNDS` (60); o pet passa da sala, mas sem ouro, kill, item ou bônus de chefe.
- Meta-progressão em `state["meta"]`: `achievements`, `graveyard` (últimas 50), `best`, `runs`, `next_char`.
  Itens com `req` e heróis com `unlock` só entram depois da conquista.
- Estado em `~/.tokenlike/state.json` (ou `state-demo.json`). Na 1ª execução, se `~/.tokenlike` não existe e
  `~/.tokenpet` (nome antigo) existe, `migrate_old_data()` copia os `state*.json` sem apagar o antigo. Gravação atômica (tmp + replace).
  Um arquivo de lock impede duas instâncias abertas.
- Registro de runs: toda run encerrada vira uma linha em `~/.tokenlike/runs.jsonl` (demo: `runs-demo.jsonl`) via
  `masmorra.run_record`, com `masmorra.BALANCE_VERSION` (hash de 8 caracteres só dos números de balanceamento).
  Mudou número, mudou a versão e o histórico real recomeça (`--todas-versoes` mostra tudo).
  O hash não vê fórmulas nem números escritos no código: ao mudar regra/fórmula de combate, suba `masmorra.REGRAS_REV`
  (hoje 3). Mudar só constante já muda a versão sozinho.
- Metas de balanceamento: em `METAS` de `tools/estatisticas.py` (passar do 1º chefe 35-45%, p90 13-16, máx <= 25).
  São julgadas na **calibração** (só slime, igual ao `simular.py`, sem e com conquistas); o "sim" com todos os
  heróis misturados é só informativo. Item verde/vermelho usa `vs_media` (vs esperado menos a média dos itens).
  Rode `python tools/estatisticas.py`, não decore números aqui.
- Último resultado do simulador (`tools/simular.py`, só como referência, pode estar defasado): 37-40% passam do
  1º chefe, p90 = andar 15, máx = 25. Mortes (sem conquistas): chefe ~59%, monstro ~22%, horda ~10%, status ~5%,
  mímico ~3%, armadilha ~1%. Itens empilham, o herói fica forte rápido (`CHEST_ITEM_CHANCE` = 1.0, `RAR_MULT` baixo)
  e quem segura as runs são os chefes (`BOSS_HP` = (55, 18), `BOSS_ATK` = (7.5, 3.1), ou seja
  `valor + por_andar * (andar - BOSS_EVERY)`, mínimo 1); o 2º chefe (andar 10) é o muro. `MON_ATK` = (1.5, 1.2).
  Combate: `MON_SPD` = (6, 0.1), `BOSS_SPD_BONUS` = 1.1, `PET_CRIT` = 0.10, `BOSS_STATUS_CHANCE` = 0.15.
  Hordas: `HORDE_MULT` = {2: 0.75, 3: 0.6, 4: 0.5} é decisão do dono (não mexer); quem ajusta é o peso "horde"
  (hoje 9 em `ROOM_WEIGHTS`), `horde_max` e `HORDE_GOLD_MULT`. Crítico do pet: a base só guarda `crit`/`critdmg`
  se o herói definir; senão `stats()` usa `PET_CRIT`/`PET_CRITDMG`.
  Ordem das alavancas: raridade, `consume`, baú/mímico/loja (`SHOP_PRICE`); no combate: status e crítico,
  velocidades, horda (peso, `horde_max`, `HORDE_GOLD_MULT`); só então `MON_*`/`BOSS_*`. Hordas devem ficar entre 5% e 35% das mortes
  e status acima de 0 (sem ser a maioria).

## Para adicionar coisas

- **Item novo:** desenho em `arte.ITEM_ART[chave]` (se o `look` usar arte) e entrada em `masmorra.ITEMS` com `name`,
  `rarities` (lista das raridades possíveis), `fx`, `consume` (`{"heal": n}` ou `{"shield": n}`), `look` e `req` opcional.
  Não existe mais `slot` nem `tier`. `look` é um dos efeitos de `visual.py`: `{"type": "obj", "anchor": "dir|esq|topo|flutua", "art": ...}`,
  `espinhos`/`gotas`/`contorno` (`color`), `tingir` (`color`, `amount`) ou `adesivo` (`art`, `at`). Rode `tools/simular.py` depois.
- **Monstro novo:** desenho em `arte.FOE_ART`, entrada em `masmorra.MONSTERS`
  `(sprite, nome, mult_hp, mult_atk, andar_min, spd_mult)` (+ nome de chefe em `BOSS_NAMES` e elemento em
  `BOSS_ELEMENT`: `fogo|raio|veneno|gelo`; sem elemento o chefe quebra `make_foe`).
- **Campos de `fx` do combate:** `spd`, `crit`, `critdmg`, `area` (bool, não escala com raridade) e a chance por golpe
  de cada elemento: `queimar`, `eletrizar`, `envenenar`, `congelar` (0..1, teto `MAX_ELEM_CHANCE`; `crit` teto `MAX_CRIT`).
- **Tipo de sala novo:** `ROOM_WEIGHTS` + um ramo em `enter_room` + a animação em `PetApp.play_room`.
- **Conquista nova:** `masmorra.ACHIEVEMENTS` + regra em `_check_achievements`.
- **Herói novo:** de preferência uma pasta em `characters/` com PNGs e `character.json` (`stats` com `spd` opcional, `unlock`, `stages[].floor`).

## Antes do lançamento

- Capricho visual da página de estatísticas e ícones de itens e heróis nela.
- Screenshot e GIF do README (`docs/screenshot.png`, `docs/demo.gif`).
- Testar na tela de verdade o modo interativo e as barras de sessão e semana.

## Ideias em aberto

- Heróis desbloqueáveis: velinha viva, cogumelo de caverna, baú mímico (cada um com stats e uma mecânica própria).
- Mais salas (evento raro, sala secreta), mais chefes com sprite próprio, sinergias entre itens.
- Mais escolhas do jogador (hoje só pegar/consumir no modo interativo), sons, estatísticas de runs.
- Escala dos itens para heróis maiores que 16 px (fator altura_do_herói/16) fica para a parte 3 (Petdex);
  `visual.compose` ainda não tem parâmetro de escala.
