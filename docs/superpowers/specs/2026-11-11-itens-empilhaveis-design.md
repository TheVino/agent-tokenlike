# Itens empilháveis, raridade e modo interativo (parte 1 de 3)

Data: 2026-11-11. Projeto: Agent Tokenlike. Leia o `CLAUDE.md` antes: as regras de lá
(privacidade, só biblioteca padrão, arte 100% original, inatividade nunca pune) valem para tudo aqui.

## Intenção

Hoje o pet tem 3 espaços de item (mão, escudo, cabeça). Um item novo substitui o anterior
ou é vendido. O dono quer o oposto: uma run em que o pet **acumula itens sem limite**
e vai ficando **cada vez mais montado e esquisito**. Cada item fica visível no pet, como
objeto pendurado ou como mutação do próprio corpo, e muda as regras. A referência de gênero
é o roguelike de itens empilháveis (só mecânica, nada de arte ou nomes de outro jogo).

Além disso, o dono quer poder **jogar** quando estiver olhando para o pet, sem perder o
lado "idle" de quando está trabalhando. Daí os dois modos: auto e interativo.

## Visão geral das 3 partes

1. **Este documento:** o sistema novo, com cerca de 20 itens.
2. **Depois:** mais itens em levas de ~20 até chegar a **100 itens individuais** (cada um com
   desenho próprio). Cada leva tem desenho, efeito e uma rodada do simulador.
3. **Depois:** pets da comunidade do Petdex como heróis. O app só **lê** pets já instalados
   pelo usuário em `~/.petdex/pets/` ou `~/.codex/pets/` (pasta com `pet.json` + spritesheet
   8×9 de quadros 192×208). Só `.png` funciona (o tkinter não lê WebP). Nunca distribuir esses
   pets no repositório: são fan art com licença de cada autor. Sem rede no app.

O design desta parte já precisa deixar a parte 3 possível (ver "Visual").

## Objetivos

- Itens se acumulam a run inteira. Nada de espaços, troca ou venda automática.
- Todo item aparece no pet. Com ~15 itens o pet fica claramente diferente do começo da run.
- Raridades visíveis: **comum, raro, épico, lendário**.
- Ao achar um item: escolher entre **Pegar** (fica na run e empilha) e **Consumir**
  (o item some e dá um efeito imediato, como cura ou escudo).
- **Modo auto** (o pet decide sozinho) e **modo interativo** (o jogador decide).
- Começar com ~20 itens: os 13 atuais convertidos e ~7 novos.

## Fora do escopo (agora)

- Os 80 itens restantes (parte 2) e o suporte ao Petdex (parte 3).
- Sinergias entre itens específicos, sons, novas salas, novos heróis.
- Escolhas em outras salas (altar, loja) além da escolha de item.

## Anti-objetivos (seria fracasso mesmo funcionando)

- **Uma escolha pendente travar a masmorra.** A espera tem um tempo máximo; depois dele a
  escolha se resolve sozinha e o jogo segue.
- **Perder energia por causa da espera.** Tokens que chegam durante a espera vão para a mochila
  de energia normalmente.
- **Ficar sem usar punir.** Sem tokens, a escolha espera para sempre e nada se perde.
- **Mutação que só funciona num herói.** Todo efeito visual tem que funcionar em qualquer
  herói, inclusive num PNG qualquer (ver "Visual").
- Itens que somem visualmente por cima uns dos outros a ponto de o pet não parecer mudar.
- Quebrar o save de quem já joga.

## Decisões do dono

- Itens empilham sem limite. Opção visual **C (mistura)**: parte dos itens vira objeto
  no pet, parte muda o corpo.
- **Regra do contorno:** só entram efeitos visuais calculáveis a partir do contorno do
  desenho (onde há pixel e onde não há). Nada que dependa de saber onde fica a boca, o olho etc.
  Os 6 tipos aceitos:
  1. **Objeto** encaixado num ponto (topo, lados, frente, base, flutuando).
  2. **Espinhos** na borda de cima.
  3. **Gotas** escorrendo da borda de baixo.
  4. **Contorno** colorido em volta do corpo.
  5. **Recolorir** o corpo (mistura de cor, sem tocar no contorno escuro).
  6. **Adesivo** colado numa posição relativa da caixa (ex.: terceiro olho no meio do topo).
- Pegar ou consumir; o efeito de consumir depende do item (ex.: escudo ou cura).
- Raridade visível. Muitos itens têm versões em várias raridades; alguns só existem como lendários.
- Modo auto e modo interativo. No interativo, a escolha **fica esperando** por uma janela de
  tempo (30 s, ajustável); enquanto isso o pet não entra em salas e a mochila de energia serve de
  buffer. O painel mostra o tempo restante e quantas salas já estão esperando.
- **Cada item sai no máximo uma vez por run.**
- Total de 100 itens individuais no fim da parte 2.

## Regras do jogo

### Item (definição)

Cada entrada de `masmorra.ITEMS` passa a ter:

- `name`, `fx` (como hoje: `atk`, `def`, `maxhp`, `dodge`, `gold`, `trap`, `energy`, `lifesteal`).
- `rarities`: lista das raridades em que o item existe, ex. `["comum", "raro", "epico"]`,
  ou só `["lendario"]`.
- `consume`: efeito ao consumir, ex. `{"heal": 8}` ou `{"shield": 6}`.
- `look`: o visual (ver "Visual").
- `req` opcional (conquista que libera), como hoje. Some o campo `slot`. O campo `tier` vira
  a raridade mínima do item.

### Raridade

- Quatro raridades: `comum`, `raro`, `epico`, `lendario`.
- Os valores numéricos de `fx` e `consume` são multiplicados pela raridade, com arredondamento:
  comum ×1, raro ×1,5, épico ×2, lendário ×3 (*decisão minha, ajustar no simulador*).
  Efeitos negativos (ex.: `maxhp: -4` da foice) **não** escalam: a raridade só melhora o lado bom.
  `trap` (multiplicador) também não escala.
- A chance de cada raridade sobe com o andar, no lugar do atual `max_tier = 1 + floor // 3`.
  Chefe sempre dá raro ou melhor. A curva exata fica para o simulador.
- Visual da raridade: um brilho em volta do objeto (ou do adesivo) na cor da raridade:
  comum sem brilho, raro azul, épico roxo, lendário dourado (*decisão minha*). Mutações de
  corpo mostram a raridade só no nome e no texto de status.

### Estado da run

- `run["items"]` vira uma **lista** na ordem em que foram pegos: `[{"key": "adaga", "rar": "raro"}, ...]`.
- `run["shield"]`: pontos de escudo temporário. Absorvem dano de combate e armadilha antes do HP.
  Não têm teto, não regeneram e somem ao fim da run.
- `run["pending"]`: item esperando escolha, `{"key", "rar", "source"}` ou ausente.
- `stats(run)` soma `fx` de todos os itens com o multiplicador de raridade. Os limites atuais
  continuam (`maxhp >= 5`, `atk >= 1`, `dodge <= 0.5`).

### Achar um item

Baú, mímico, chefe e loja continuam dando itens, mas em vez de `give_item` criam uma **oferta**:

1. `enter_room` sorteia o item e a raridade e põe em `ev["offer"]`. O sorteio exclui itens que
   já estão em `run["items"]` ou em `run["pending"]` (um de cada por run). Se não sobrar nenhum
   item liberado, a sala dá ouro no lugar (valor do baú de ouro atual).
2. Modo auto: a regra automática decide na hora e aplica.
3. Modo interativo: grava em `run["pending"]` e a GUI mostra a escolha.

**Regra automática** (usada no modo auto e ao resolver uma pendência): consome se o efeito de
consumir for cura e o HP estiver abaixo de 40% do máximo. Nos outros casos, pega.
(*decisão minha, simples de propósito*)

**Janela de escolha (modo interativo):**

- Com `run["pending"]` aberto, o pet **não entra em salas**, mesmo com energia na mochila.
  Os tokens que chegam continuam indo para a mochila (`add_energy`, até `MAX_STORED_ROOMS`).
- A pendência guarda quando foi aberta. Ela se resolve quando o jogador clica ou quando passam
  `CHOICE_WINDOW_S` (30 s, constante ajustável) **e** há energia para a próxima sala. Aí a regra
  automática decide, a GUI anima o resultado curto e o pet segue pelas salas guardadas no ritmo
  normal. Se uma dessas salas gerar outra oferta, abre uma nova janela de 30 s.
- Sem energia para sala nenhuma, a pendência espera para sempre (fica no save), mesmo depois dos
  30 s, e se resolve na primeira sala que puder ser paga. Inatividade nunca resolve contra o jogador.
- O relógio da janela é de tempo real (`time.time()`); ao reabrir o app com pendência antiga no
  save, a janela recomeça com 30 s.
- Morte não acontece com pendência aberta: só uma sala pode matar e a pendência é resolvida antes.
- No modo auto não existe pendência: a regra automática decide na hora.
- Trocar de interativo para auto com pendência aberta resolve ela na hora pela regra automática.

### Conquistas

- `colecionador` deixa de ser "3 itens equipados" e vira "**ter 10 itens pegos numa run**"
  (consumidos não contam) (*decisão minha*).
- As outras continuam iguais.

### Saves antigos

Ao carregar um `run["items"]` no formato antigo (dict de espaços), converter para lista com
raridade `comum`, mantendo a ordem mão, escudo, cabeça. Sem `shield` ou `pending`, usar 0 e
ausente. Lápides antigas no cemitério continuam como estão (lista de chaves).

## Visual

### Princípio

Todo efeito trabalha sobre uma **imagem como mapa de pixels**: `{(x, y): "#rrggbb"}`, só com os
pixels opacos. As funções de efeito são **puras** (sem tkinter), recebem o mapa e devolvem um
novo mapa. Isso permite testar sem tela e funciona igual para a arte em grade e para PNG.

- Herói em grade (Slime): o mapa vem direto da grade + paleta.
- Herói em PNG: o mapa vem do `PhotoImage` (`get`/`transparency_get`) uma vez, ao carregar.

### Composição

Para cada quadro do herói (normal, piscando, dormindo), o pet visível é:

`quadro base → mutações na ordem em que os itens foram pegos → objetos → render`

- O resultado é renderizado **uma vez** quando a lista de itens muda (pegar item, nova run,
  evolução, troca de herói, recarregar personagens) e guardado. Nada é recalculado por quadro.
- Os objetos entram no mesmo mapa (uma imagem só), no lugar dos 3 itens de canvas separados de
  hoje (`acc_items`, `refresh_equipment`).
- A imagem final cresce para caber o que sair da caixa original (espinhos, chifres, espada).
  O ponto de apoio do pet na tela (centro da base) não pode mudar, senão o pet "pula".
- Escala: itens são desenhados em pixels de arte do herói. Num herói de 16 px os itens de
  arte já servem na escala 1:1. Herói maior (Petdex, parte 3) precisa ampliar os itens pelo fator
  `altura_do_herói / 16`; deixar a escala como parâmetro desde já.

### Os 6 tipos (`look`)

- `{"type": "obj", "anchor": "topo|esq|dir|frente|base|flutua", "art": "<chave em arte.ITEM_ART>"}`
- `{"type": "espinhos", "color": "#..."}`: um espinho a cada N colunas na borda de cima do contorno.
- `{"type": "gotas", "color": "#..."}`: gotas de comprimento variado saindo da borda de baixo.
- `{"type": "contorno", "color": "#..."}`: pixels vizinhos ao contorno, do lado de fora.
- `{"type": "tingir", "color": "#...", "amount": 0.4}`: mistura de cor nos pixels do corpo,
  **sem** tocar os pixels escuros de contorno (luminância baixa). Dois tingimentos se somam.
- `{"type": "adesivo", "art": "<chave>", "at": [fx, fy]}`: arte colada na posição relativa
  (0..1) da caixa do contorno.

Um protótipo dessas funções sobre mapas de pixels está em
`.superpowers/brainstorm/*/content/contorno-exemplos.html` (gerado durante o brainstorm);
serve só de referência visual.

### Empilhar no mesmo ponto

Como cada item sai uma vez só por run, nunca há dois iguais; mas itens diferentes podem
dividir o mesmo ponto. Dois objetos no mesmo `anchor` não se escondem: o segundo é deslocado para fora (topo sobe,
lados se afastam, `flutua` ocupa a próxima posição em volta do pet). Se faltar espaço, vale
mostrar os mais recentes daquele ponto, com um limite que o construtor define pelo que fica
legível. Itens diferentes com a mesma mutação (ex.: dois itens de espinhos) reforçam o efeito
(mais espinhos, gotas mais longas).

## Interface

- **Menu (botão direito):** opção "Modo: Auto / Interativo", salva em `state["mode"]`.
  Padrão: auto.
- **Escolha no modo interativo:** quando há `run["pending"]`, aparece perto do pet um painel
  com o desenho do item, nome com a cor da raridade, o texto do efeito ao pegar e ao consumir,
  e dois botões: **Pegar** e **Consumir**. Embaixo, uma barrinha do tempo restante da janela
  e, se a mochila tiver salas guardadas, o aviso "N salas esperando". Texto sempre sobre
  retângulo sólido (`PANEL_BG`), por causa do contorno rosa no Windows.
- **Status (duplo clique):** lista de itens com raridade, escudo atual e, se houver, o item pendente.
- **Animação ao pegar:** o desenho do pet muda na hora, com um efeito curto (o `burst` atual serve).
- **Animação ao consumir:** número de cura em verde ou de escudo em azul, como os floaters de hoje.
- O painel some quando a escolha se resolve (clique ou automático).

## Conteúdo da parte 1 (~20 itens)

- Os 13 itens atuais convertidos (`look` = objeto com a arte que já existe; os de cabeça vão para
  `topo`, os de mão para `dir`, os de escudo para `esq`). Raridades e `consume` definidos pelo construtor.
- ~7 novos, cobrindo os 5 tipos de mutação ao menos uma vez (espinhos, gotas, contorno, tingir,
  adesivo) e pelo menos 1 só lendário. Cada um precisa de um desenho de ícone (para aparecer na
  sala e no painel de escolha), mesmo os que são mutação.
- Arte nova em grade de texto em `arte.py`, 100% original, no clima sombrio e fofo do jogo.

## Balanceamento

Empilhar deixa as runs bem mais fortes. Rodar `tools/simular.py` (no modo auto) e ajustar até
voltar perto do alvo atual: cerca de 40% das runs passam do 1º chefe, p90 ≈ andar 14, máx ≈ 20.
O simulador passa a mostrar também a média de itens por run.

Alavancas permitidas (*decisão minha*): números de raridade e `consume`, curva de raridade por
andar, chance de item em baú/mímico/loja, preços, curvas de monstro e chefe (`MON_HP`, `BOSS_HP`
etc.) e limites de soma por atributo. Preferir mexer primeiro nos itens e nas chances; mexer nas
curvas de monstro só se não bastar, e anotar no `CLAUDE.md` os números novos.

O bônus de `energy` somado é limitado a **+100%** (*decisão minha*): o simulador não modela o
ritmo de tokens, e energia sem teto desvincularia o pet do uso real. O multiplicador `trap` somado
também ganha piso e teto (sugestão: entre 0,25 e 3).

## Testes

- Funções de efeito visual: testes puros sobre mapas de pixels (sem tkinter). Cada tipo
  funciona num mapa de Slime e num mapa qualquer (ex.: o PNG do Fantasma lido como mapa).
  O ponto de apoio da base não muda depois da composição.
- Regras: empilhamento e soma de `fx` com raridade; escudo absorvendo dano; regra automática;
  um item de cada por run (e ouro quando o pool acaba); tetos de `energy` e `trap`; migração do save antigo.
- Janela de escolha: o pet não entra em salas com pendência aberta antes dos 30 s; tokens
  chegando durante a espera vão para a mochila; depois dos 30 s com energia, resolve e segue;
  sem energia, espera indefinidamente.
- `tests/test_gui.py`: jogar centenas de salas nos dois modos, inclusive com pendência aberta
  quando chega energia.
- Todos os testes atuais continuam passando. Atualizar o `CLAUDE.md` e os dois READMEs
  (seção "Como a masmorra funciona" e "Para adicionar coisas").

## Fica a critério do construtor

- Números de raridade, `consume` de cada item e a curva de chance por andar (guiados pelo simulador).
- Os nomes, desenhos e efeitos dos ~7 itens novos.
- Onde morar as funções de efeito visual (sugestão: funções puras em `arte.py` ou um módulo
  pequeno novo, sem tkinter).
- Posição exata do painel de escolha e o limite de objetos por ponto de encaixe.
