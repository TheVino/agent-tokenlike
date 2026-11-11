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
  (brilho na cor da raridade). `LOOK_BOX` limita a área; a GUI só recompõe quando a lista de itens muda (`refresh_look`).
- `characters/<pasta>/character.json` + PNGs: heróis extras (ex.: `fantasma`). O formato está no `LEIA-ME.md`.
- `tests/`: `test_migracao.py` (cópia de `~/.tokenpet` para `~/.tokenlike`), `test_reader.py` (leitura de logs, deduplicação, arte),
  `test_itens.py` (raridade, empilhar, pegar/consumir, escudo, tetos, pendência, migração do save de 3 espaços),
  `test_visual.py` (efeitos de `visual.py` e composição do pet) e `test_gui.py` (tkinter falso
  que executa os callbacks `after`, joga centenas de salas, morre, renasce, troca de herói e testa o modo interativo;
  usa `random.Random(SEED)` para ser determinístico).
- `tools/simular.py`: simula 2.000 runs e mostra a distribuição de andares, a taxa de passar do 1º chefe e quem mais mata.
  `tools/preview_arte.py`: gera um PNG com todos os desenhos (precisa do Pillow, só para desenvolvimento).
- `README.md` (inglês, para o GitHub) e `LEIA-ME.md` (pt-BR). Licença MIT.
- `iniciar.bat` (pythonw, sem console), `testar-demo.bat` (`--demo`: tokens falsos, estado separado).

## Comandos

```
python tests/test_reader.py
python tests/test_itens.py
python tests/test_visual.py
python tests/test_gui.py
python tests/test_migracao.py
python tools/simular.py          # depois de mexer em balanceamento/itens/salas
python tools/preview_arte.py     # depois de mexer em arte.py
python tokenlike.py --demo        # ver na tela de verdade
```

Rode os testes depois de qualquer mudança. Quando mexer em `masmorra.py`, rode também o simulador.
O `test_gui.py` falha se aparecer "erro" em `~/.tokenlike/tokenlike.log` (num HOME temporário).

## Regras do projeto (não quebrar)

1. **Privacidade:** dos `.jsonl` do Claude Code (`~/.claude/projects/**`, ou `CLAUDE_CONFIG_DIR`) só se usa
   `message.usage`. Nunca guardar, mostrar ou logar conteúdo de prompts e respostas. Sem rede, sem telemetria,
   sem hooks, sem alterar configs do Claude Code.
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
- Meta-progressão em `state["meta"]`: `achievements`, `graveyard` (últimas 50), `best`, `runs`, `next_char`.
  Itens com `req` e heróis com `unlock` só entram depois da conquista.
- Estado em `~/.tokenlike/state.json` (ou `state-demo.json`). Na 1ª execução, se `~/.tokenlike` não existe e
  `~/.tokenpet` (nome antigo) existe, `migrate_old_data()` copia os `state*.json` sem apagar o antigo. Gravação atômica (tmp + replace).
  Um arquivo de lock impede duas instâncias abertas.
- Balanceamento atual (via `tools/simular.py`, as duas linhas: 0 e todas as conquistas): 38–41% das runs passam do
  1º chefe, p90 = andar 15, máx = 25. Como os itens empilham, o herói fica forte rápido (baú sempre traz item,
  `CHEST_ITEM_CHANCE` = 1.0, `RAR_MULT` baixo: 1 / 1.2 / 1.4 / 1.6), e quem segura as runs são os chefes, com base
  negativa e inclinação alta (`BOSS_HP` = (-35, 18), `BOSS_ATK` = (-9.5, 3.4)): fracos no andar 5, paredões nos 15–20.
  Quase toda morte acontece na sala do chefe. Ordem das alavancas: raridade, `consume`, baú/mímico/loja (`SHOP_PRICE`),
  só então `MON_*`/`BOSS_*`.

## Para adicionar coisas

- **Item novo:** desenho em `arte.ITEM_ART[chave]` (se o `look` usar arte) e entrada em `masmorra.ITEMS` com `name`,
  `rarities` (lista das raridades possíveis), `fx`, `consume` (`{"heal": n}` ou `{"shield": n}`), `look` e `req` opcional.
  Não existe mais `slot` nem `tier`. `look` é um dos efeitos de `visual.py`: `{"type": "obj", "anchor": "dir|esq|topo|flutua", "art": ...}`,
  `espinhos`/`gotas`/`contorno` (`color`), `tingir` (`color`, `amount`) ou `adesivo` (`art`, `at`). Rode `tools/simular.py` depois.
- **Monstro novo:** desenho em `arte.FOE_ART`, entrada em `masmorra.MONSTERS` (+ nome de chefe em `BOSS_NAMES`).
- **Tipo de sala novo:** `ROOM_WEIGHTS` + um ramo em `enter_room` + a animação em `PetApp.play_room`.
- **Conquista nova:** `masmorra.ACHIEVEMENTS` + regra em `_check_achievements`.
- **Herói novo:** de preferência uma pasta em `characters/` com PNGs e `character.json` (`stats`, `unlock`, `stages[].floor`).

## Ideias em aberto

- Heróis desbloqueáveis: velinha viva, cogumelo de caverna, baú mímico (cada um com stats e uma mecânica própria).
- Mais salas (evento raro, sala secreta), mais chefes com sprite próprio, sinergias entre itens.
- Mais escolhas do jogador (hoje só pegar/consumir no modo interativo), sons, estatísticas de runs.
