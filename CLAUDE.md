# Agent Tokenlike: Masmorra de Tokens

Pet de pixel art que fica sobre a tela do Windows (overlay transparente, sempre por cima) e
desce uma masmorra roguelike usando como energia os tokens gastos no Claude Code.
Antes se chamava TokenPet. Projeto pessoal e não oficial (sem vínculo com a Anthropic); interface e textos em **português (pt-BR)**.

## Arquivos

- `tokenlike.py`: app (tkinter). Contém a leitura de tokens (`TokenReader`), o estado/salvamento,
  os personagens (Slime embutido + loader de PNG) e a GUI (`PetApp`). O `tkinter` é importado só em
  `run_gui()`, para o resto do módulo ser testável sem tela.
  O botão direito abre um menu próprio em pixel art (`on_menu`: `Toplevel` sem borda de `pixel_box`, moldura dourada
  com cantos recortados, ícones de `arte.py`, chips de Tamanho/Modo, caixinhas em `arte.MENU_ART`), não o `tk.Menu`;
  "Heróis…" abre a grade `show_heroes` (bloqueado = silhueta + cadeado + conquista; `hero_cards[key]` é None).
  Status, Conquistas e Cemitério também são janelas pixel (`janela(attr, título)` + `ao_lado`; atributos em `JANELAS`):
  `show_stats` (miniatura, barra de HP, uma linha por campo de `STAT_LINHAS`/`stat_linhas` com ícone de `arte.STAT_ART`
  e teto, itens com brilho da raridade e nome no hover, consumidos esmaecidos), `show_achievements` (cards de `CONQ_*`,
  ícone de `arte.CONQ_ART`, silhueta se não tem, mini-ícones do que libera) e `show_graveyard` (lápides num `Canvas`
  com rolagem). "Itens" abre `show_items`: cards num `Canvas` (`item_card`), cada raridade possível com `fx_text` e o
  `consume` na cor de `RAR_COLOR`, família por `item_familia`/`FAMILIAS`, filtro Todos/Liberados/Bloqueados; bloqueado
  (`item_liberado`, mesma regra do sorteio; demo libera tudo) = silhueta + cadeado + conquista, sem valores.
  Toda janela que rola usa `rolagem()` (barra pixel: arrastar, clicar na trilha, roda, setas). Ícones via `icon()` (cache `self.icons`); `map_img` monta um PNG e
  carrega numa chamada só (um `put` por pixel deixava a janela lenta).
- `masmorra.py`: regras do jogo, puras e sem GUI: energia, salas, combate, itens, conquistas, morte.
  `enter_room()` resolve uma sala e devolve um dicionário de evento, que a GUI só anima (`PetApp.play_room`).
- `arte.py`: toda a pixel art em grades de texto (`'.'` = transparente, letras = cores de `PAL`).
  Itens, monstros, salas, coroa de chefe, `STAT_ART` (um por campo de `stats()`, mais `crescer`) e `CONQ_ART`
  (um por conquista). `BOSS_PAL` recolore os monstros para os chefes.
- `visual.py`: efeitos puros sobre mapas de pixels `{(x, y): "#rrggbb"}` (sem tkinter): `espinhos`, `gotas`,
  `contorno`, `tingir`, `adesivo`, `objeto` e `compose()`, que monta o pet com os `look` dos itens empilhados
  (brilho na cor da raridade). `LOOK_BOX` limita a área: em cada âncora ficam só os objetos mais recentes que cabem
  inteiros nela (os mais antigos daquele ponto deixam de ser desenhados); a GUI só recompõe quando a lista de itens muda (`refresh_look`).
- `herois/`: heróis embutidos 32 px, um módulo por herói (`slime.py`, `fantasma.py`, `medico.py`, `bruxa.py`, `coveiro.py`, `ceifeirinho.py`, `vela.py`, `cogumelo.py`, `inquisidor.py`, `boneca.py`, `cavaleiro.py`, `corvo.py`, `alquimista.py`, `freira.py`) com: `PAL` (letra -> cor), `QUADROS`
  (8 estados desenhados: idle, run_r, waving, jumping, failed, waiting, running, review; 4 a 6 quadros 32x32 cada),
  `ESTAGIOS` (exatamente 3: `title`, `floor`, `extra`; o 1º com `extra=None`; o Slime evolui nos andares 1/4/10: Gotinha,
  Slime, Rei Slime) e `ANCORA` (por estado e quadro, `(x, y)` inteiros onde o `extra` do estágio é colado).
  `herois/comum.py`: peças repartidas (`z`, `?`, lágrima, `carimbar`, `linha`, `contornar`, `traco`).
  Desbloqueio por conquista: Fantasma `chefe1`, Médico `veneno1`, Bruxa `elementos3`, Coveiro `ouro300`, Ceifeirinho `horda4`,
  Vela Viva `queima1`, Cogumelo `andar8cheio`, Inquisidor `andar15` (HP base 16), Boneca `esquiva10`,
  Cavaleiro Oco `bloqueio10` (ATK base 2, spd 8), Corvo `chefes3` (meta, `meta["chefes"]`, spd 12), Alquimista `consumir10`,
  Freira `morrer10` (meta, `meta["runs"]`). `die()` chama `_check_achievements`. No `--demo` todos os heróis vêm liberados.
  Regra de balanceamento dos heróis: cada um passa do 1º chefe em 30-50% (1.500 runs só dele).
  `herois/montar.py`: `estados()` monta os 9 estados (`run_l` = `run_r` espelhado, não se desenha) e `validar()` confere
  tudo (4-6 quadros, âncoras, 32x32, 3 estágios). `tools/gerar_folhas.py` gera `characters/fantasma/folha1..3.png`
  (grade 8x9, células de 40 px, 4-6 quadros por estado, células vazias onde faltam quadros) e a prévia
  `tools/saida/preview_herois.png`. Os PNGs antigos do Fantasma ficam no repo.
- **Traço do herói** (`"traço"` no `character.json`, objeto com campos de `fx`): vai para `run["traco"]` em `new_run` e soma
  em `stats()` como um item, mas **sem escalar por raridade**. Chave inválida ou valor não numérico invalida o herói.
  `run["cont"]` guarda contadores da run (`esquivas`, `bloqueios`, `mortes_veneno`, `mortes_queima`, `horda4`; horda de 4
  empatada não conta), para conquistas e traços futuros.
- `characters/<pasta>/character.json` + PNGs: heróis extras (ex.: `fantasma`). O formato está no `LEIA-ME.md`.
- `folha.py`: corte de spritesheet (9 linhas, `ESTADOS`: idle, run_r, run_l, waving, jumping, failed, waiting,
  running, review). Herói = `characters/<pasta>/spritesheet.png` (+ `character.json` opcional) ou pet do Petdex
  (`~/.petdex/pets/<slug>/`, `~/.codex/pets/<slug>/`, só PNG, `comunidade=True`, menu "Comunidade"; só lidos, nunca copiados).
  Na GUI, `estado_atual` escolhe: escolha pendente `review` > luta `running` > morte `failed` (antes da lápide) >
  descanso/sono `waiting` > `idle`; `waving` ~1 s após o carinho, `jumping` na evolução e ao vencer chefe.
  O PNG é decodificado por `folha.ler_png` (zlib + struct, 8 bits; opaco = alfa > 128), não pelo Tk. A descoberta
  (`all_characters`) só lê o cabeçalho; o corte (`completar_estagio`/`ler_folha`, cache por caminho+mtime, guarda só os
  mapas reduzidos) roda numa thread quando o herói fica ativo, e o `after` troca o visual ("preparando herói…").
  `refresh_look` compõe na hora só o idle e o estado na tela; os outros de `estados_fx` saem na 1ª leitura
  (cache `fx_cache` por estado + itens + status). Todos os estados usam o mesmo k e o pivô na base da caixa aparada.
  O Slime embutido também tem `estados` (grade) e continua piscando no idle; heróis PNG soltos seguem sem estados.
  Uma pasta `characters/slime` não substitui mais o Slime embutido (chaves repetidas ficam com o primeiro).
- `tests/`: `test_limites.py` (statusline grava só os limites; leitura, dado velho, cores, fuso), `test_migracao.py` (cópia de `~/.tokenpet` para `~/.tokenlike`), `test_reader.py` (leitura de logs, deduplicação, arte),
  `test_itens.py` (raridade, empilhar, pegar/consumir, escudo, tetos, pendência, migração do save de 3 espaços),
  `test_registro.py` (`run_record`, `runs.jsonl`), `test_estatisticas.py` (métricas e página),
  `test_folha.py` (corte e decodificador de PNG; `tests/_png.py` escreve PNGs de verdade), `test_visual.py` (efeitos de `visual.py` e composição do pet) e `test_gui.py` (tkinter falso
  que executa os callbacks `after`, joga centenas de salas, morre, renasce, troca de herói e testa o modo interativo;
  usa `random.Random(SEED)` para ser determinístico).
- `tools/simular.py`: simula 2.000 runs e mostra a distribuição de andares, a taxa de passar do 1º chefe e quem mais mata.
  `tools/estatisticas.py`: gera `tools/saida/estatisticas.html` e `.json` (gitignored) com simulado x real, itens, pares, mortes e heróis; `METAS` (metas de balanceamento) mora aí.
  `tools/preview_arte.py`: gera um PNG com todos os desenhos (precisa do Pillow, só para desenvolvimento).
- `README.md` (inglês, para o GitHub) e `LEIA-ME.md` (pt-BR). Licença MIT.
- `statusline.py`: statusline opcional do Claude Code (o usuário liga). Lê o JSON do stdin e grava só os limites oficiais
  de sessão (5h) e semana em `~/.tokenlike/limites.json`. O pet lê com `read_limits` a cada poll e desenha as barras
  Sessão/Semana no painel (verde ≤50%, amarelo ≤80%, vermelho acima). Leitura oficial nova calibra um fator por janela
  (`calibrate`, `state["calib"]`); sem leitura recente (<10 min) mostra `~N%` estimado (`limit_view`); sem fator, só os tokens
  da janela. As barras aparecem sempre.
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
   `message.usage` e o `timestamp` de cada resposta (histórico em baldes de 5 min, 8 dias, em `state["usage_hist"]`). Nunca guardar, mostrar ou logar conteúdo de prompts e respostas. Sem rede, sem telemetria,
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
  (negativos, `trap`, `area` e `custo_ataque` não escalam; `crescer` escala para baixo: `ceil(N / RAR_MULT)`, piso 3);
  `_rarity_weights(andar)` sorteia a raridade (a `sorte` dos itens multiplica os pesos de raro, épico e lendário) e
  cada item lista as `rarities` possíveis. São 100 itens: ~74 em 3 raridades, ~16 em 2 e 10 só lendários.
  Cores (`RAR_COLOR`): raro azul, épico roxo, lendário dourado.
- **Pegar ou consumir:** cada oferta (baú, mímico, chefe, loja) pode ser pega (entra na lista) ou consumida
  (`consume`: `heal` cura na hora, `shield` vira escudo, que absorve dano antes do HP em `apply_damage`).
  Modo `auto` (`state["mode"]`): `auto_choice` consome cura se o HP < 40%, senão pega. Modo `interativo`: a oferta
  fica em `run["pending"]` (salva no state) e a GUI abre a janela de escolha; sem resposta em `CHOICE_WINDOW_S` (30 s),
  a regra automática decide quando a próxima sala estiver pronta. Nunca entra em sala com pendência aberta.
- **Tetos:** `energy` somada ≤ +100% (`MAX_ENERGY_BONUS`), multiplicador de armadilha em `TRAP_LIMITS` (0,25 a 3),
  esquiva ≤ `MAX_DODGE`, crítico ≤ `MAX_CRIT` (0,35), chance de cada elemento ≤ `MAX_ELEM_CHANCE` (0,3),
  `bloqueio` ≤ `MAX_BLOQUEIO` (2), `espinhos` ≤ `MAX_ESPINHOS` (0,5), `duplo` ≤ `MAX_DUPLO` (0,25),
  `sorte` ≤ `MAX_SORTE` (1,0), `desconto` ≤ `MAX_DESCONTO` (0,6). Os tetos valem sobre o total somado em `stats()`.
  Saves antigos de 3 espaços viram itens comuns em `migrate_run`.
- **Campos de `fx` das famílias** (todos somam em `stats()`): `bloqueio` (golpes anulados no começo de cada luta),
  `espinhos` (fração do dano recebido devolvida), `cura_sala`/`cura_andar` (HP ao entrar numa sala/descer a escada),
  `custo_ataque` (HP perdido por ataque do pet, nunca mata), `furia` (+ATK a cada 10% de HP que falta), `duplo`
  (chance de segundo golpe), `ajudante` (dano de um ajudante que ataca uma vez por rodada no inimigo de menor HP e
  não pode ser alvo), `crescer` (+1 ATK a cada N kills feitos depois de pegar o item: `kills0` guardado na pegada),
  `sorte` (raridade) e `desconto` (loja, `shop_price`). `fx_text` mostra todos; todo item precisa de texto.
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
  (hoje 8). Mudar só constante já muda a versão sozinho.
- Metas de balanceamento: em `METAS` de `tools/estatisticas.py` (passar do 1º chefe 35-45%, p90 13-16, máx <= 50).
  São julgadas na **calibração** (só slime, igual ao `simular.py`, sem e com conquistas); o "sim" com todos os
  heróis misturados é só informativo. Item verde/vermelho usa `vs_media` (vs esperado menos a média dos itens).
  Rode `python tools/estatisticas.py`, não decore números aqui.
- Último resultado do simulador (`tools/simular.py`, só como referência, pode estar defasado): 40-43% passam do
  1º chefe, p90 = andar 15, p99 = 20, máx = 35-45. Mortes (sem conquistas): chefe ~62%, monstro ~19%, horda ~9%,
  status ~5%, mímico ~3%, armadilha ~1%. Itens empilham, o herói fica forte rápido (`CHEST_ITEM_CHANCE` = 1.0,
  `RAR_MULT` baixo) e quem segura as runs são os chefes (`BOSS_HP` = (55, 18), `BOSS_ATK` = (7.5, 3.1), ou seja
  `valor + por_andar * (andar - BOSS_EVERY)`, mínimo 1); o 2º chefe (andar 10) é o muro. `MON_ATK` = (1.5, 1.2).
  **Rampa dos chefes:** depois do andar `BOSS_RAMP_FROM` (10), HP e ATK do chefe ainda são multiplicados por
  `1 + BOSS_RAMP * (andar - 10)` (`BOSS_RAMP` = 0.07). Não mexe no 1º e no 2º chefe; é ela que corta a cauda das runs
  com muitos itens (sem ela, com 100 itens, o máx passava de 200). Para alongar ou encurtar as runs longas, mexa nela.
  Combate: `MON_SPD` = (6, 0.1), `BOSS_SPD_BONUS` = 1.1, `PET_CRIT` = 0.10, `BOSS_STATUS_CHANCE` = 0.15.
  Hordas: `HORDE_MULT` = {2: 0.75, 3: 0.6, 4: 0.5} é decisão do dono (não mexer); quem ajusta é o peso "horde"
  (hoje 9 em `ROOM_WEIGHTS`), `horde_max` e `HORDE_GOLD_MULT`. Crítico do pet: a base só guarda `crit`/`critdmg`
  se o herói definir; senão `stats()` usa `PET_CRIT`/`PET_CRITDMG`.
  Ordem das alavancas: raridade, `consume`, baú/mímico/loja (`SHOP_PRICE`); no combate: status e crítico,
  velocidades, horda (peso, `horde_max`, `HORDE_GOLD_MULT`); só então `MON_*`/`BOSS_*`; para a cauda (máx), `BOSS_RAMP`. Hordas devem ficar entre 5% e 35% das mortes
  e status acima de 0 (sem ser a maioria).

## Para adicionar coisas

- **Item novo:** desenho em `arte.ITEM_ART[chave]` (se o `look` usar arte) e entrada em `masmorra.ITEMS` com `name`,
  `rarities` (lista das raridades possíveis), `fx`, `consume` (`{"heal": n}` ou `{"shield": n}`), `look` e `req` opcional.
  Não existe mais `slot` nem `tier`. `look` é um dos efeitos de `visual.py`: `{"type": "obj", "anchor": "dir|esq|topo|frente|flutua", "art": ...}`,
  `espinhos`/`gotas`/`contorno` (`color`), `tingir` (`color`, `amount`), `adesivo` (`art`, `at`) ou um dos **animados**
  dos elementais: `chamas`, `faiscas`, `gotas_veneno`, `geada` (`color` opcional; 3 fases calculadas uma vez em
  `refresh_look` e trocadas no tick pelo relógio `FX_MS`). Ajudantes usam sempre `obj` `flutua`.
  Famílias (cada uma com pelo menos 4 itens, conferido em `tests/test_itens.py`): elementais (5 por elemento, look
  animado), defesa (`bloqueio`, `espinhos`, `dodge`), regeneração (`cura_sala`, `cura_andar`, `lifesteal`), sangue
  (`custo_ataque` sempre com `atk` ou `furia`), golpes (`crit`, `critdmg`, `duplo`), área (`area`), ajudantes
  (`ajudante`), crescimento (`crescer`) e sorte/ouro (`sorte`, `gold`, `desconto`). Todo item precisa de ícone e de
  `fx_text` não vazio; nomes não se repetem. Rode `tools/simular.py` e `tools/estatisticas.py` depois.
- **Monstro novo:** desenho em `arte.FOE_ART`, entrada em `masmorra.MONSTERS`
  `(sprite, nome, mult_hp, mult_atk, andar_min, spd_mult)` (+ nome de chefe em `BOSS_NAMES` e elemento em
  `BOSS_ELEMENT`: `fogo|raio|veneno|gelo`; sem elemento o chefe quebra `make_foe`).
- **Campos de `fx` do combate:** `spd`, `crit`, `critdmg`, `area` (bool, não escala com raridade) e a chance por golpe
  de cada elemento: `queimar`, `eletrizar`, `envenenar`, `congelar` (0..1, teto `MAX_ELEM_CHANCE`; `crit` teto `MAX_CRIT`),
  mais os das famílias (`bloqueio`, `espinhos`, `cura_sala`, `cura_andar`, `custo_ataque`, `furia`, `duplo`,
  `ajudante`, `crescer`, `sorte`, `desconto`), descritos em "Como as peças se encaixam".
- **Tipo de sala novo:** `ROOM_WEIGHTS` + um ramo em `enter_room` + a animação em `PetApp.play_room`.
- **Conquista nova:** `masmorra.ACHIEVEMENTS` + regra em `_check_achievements` + ícone em `arte.CONQ_ART` (teste).
- **Campo de `fx`/`stats()` novo:** ícone em `arte.STAT_ART` e linha em `tokenlike.STAT_LINHAS` (teste).
- **Herói novo:** de preferência uma pasta em `characters/` com PNGs e `character.json` (`stats` com `spd` opcional, `unlock`, `stages[].floor`).

## Antes do lançamento

- Capricho visual da página de estatísticas e ícones de itens e heróis nela.
- Screenshot e GIF do README (`docs/screenshot.png`, `docs/demo.gif`).
- Testar na tela de verdade o modo interativo e as barras de sessão e semana.

## Ideias em aberto

- Heróis desbloqueáveis: velinha viva, cogumelo de caverna, baú mímico (cada um com stats e uma mecânica própria).
- Mais salas (evento raro, sala secreta), mais chefes com sprite próprio, sinergias entre itens.
- Mais escolhas do jogador (hoje só pegar/consumir no modo interativo), sons, estatísticas de runs.
