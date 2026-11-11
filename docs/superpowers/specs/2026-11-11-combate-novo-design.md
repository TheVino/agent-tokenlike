# Combate novo (projeto 2 do roadmap)

Data: 2026-11-11. Projeto: Agent Tokenlike. Ler o `CLAUDE.md` antes; as regras de lá valem
(privacidade, só biblioteca padrão, arte 100% original, inatividade nunca pune, texto sobre `PANEL_BG`).

## Intenção

O combate de hoje é um duelo simples: o pet sempre ataca primeiro, um contra um, e só ataque,
defesa e esquiva importam. O dono quer uma luta com mais decisões dentro dos números: quem é mais
rápido age antes, golpes críticos, status elementais (queimar, eletrizar, envenenar, congelar) e
salas com grupos de inimigos (hordas). Isso prepara o projeto 3, que traz itens até 100, muitos
deles elementais, de área e de velocidade.

Tudo continua automático. O jogador só assiste, como hoje. As únicas escolhas continuam sendo pegar
ou consumir itens.

## Roadmap (contexto)

1. Estatísticas de balanceamento: **pronto** (`tools/estatisticas.py`, skill `/balancear`).
2. **Este documento:** combate novo.
3. Itens até 100, em levas de ~20, com os visuais elementais no pet.
4. Pets do Petdex.

## Objetivos

- Velocidade decide a ordem de ação a cada rodada.
- Crítico como atributo, com o bônus por ter o dobro da velocidade do adversário.
- 4 status elementais, aplicados por chance a cada golpe.
- Chefes com um elemento fixo que aplicam o status no pet.
- Hordas de 2 a 4 inimigos, com ataque em área disponível para itens.
- Os atributos e efeitos novos ficam prontos para os itens do projeto 3 usarem pelo `fx`.
- O balanceamento volta para as `METAS` depois das mudanças, medido com as estatísticas.

## Fora do escopo

- Itens novos. Este projeto só cria os campos de `fx` que eles vão usar.
  - Exceção: o construtor pode dar um elemento a 1 ou 2 itens existentes, se isso ajudar a testar e
    balancear. É decisão dele, e precisa ser anotada.
- Visual elemental no corpo do pet (chamas, faíscas e cristais animados): fica no projeto 3, junto
  dos itens elementais.
- Combinações entre elementos (fogo derrete gelo etc.).
- Monstros comuns aplicando status.
- Escolhas do jogador durante a luta.

## Anti-objetivos

- Lutas que travam ou nunca acabam (status que impede todo mundo de agir para sempre).
- Lutas longas demais para a animação: a animação de uma sala tem que continuar curta (resumir golpes
  como hoje).
- Quebrar saves antigos ou runs em andamento.
- O pet morrer de status fora da masmorra. Status só existe durante uma luta e termina com ela.
- Status que deixa o jogo injusto contra o jogador sem ele poder ver (todo status no pet aparece).

## Decisões do dono

- **Velocidade (`spd`):** atributo do pet (no herói, `character.json` `stats.spd`), de cada tipo de
  monstro e de chefe; itens podem somar ou tirar. A cada rodada quem tem mais velocidade age antes.
- **Ter o dobro da velocidade do adversário** não dá ataque extra (continua 1 ataque por rodada), mas
  **dobra o dano crítico** e dá **+50% de chance de crítico**. Vale para os dois lados.
- **Crítico:** atributos novos `crit` (chance) e `critdmg` (multiplicador do golpe crítico).
- **Status elementais (no alvo):**
  - **Fogo → queimadura:** dano a cada turno.
  - **Raio → eletricidade:** chance de o alvo perder o turno.
  - **Veneno:** dano a cada turno, que cresce a cada round.
  - **Gelo → congelamento:** chance maior que a do raio de perder o turno; depois de perder um
    turno, o congelamento sai.
- **Quem aplica:** os elementos vêm do pet (por itens) e dos **chefes**, que aplicam no pet.
  **Monstros comuns não aplicam.**
- **Hordas:** de 2 a 4 inimigos. HP e ataque de cada um caem para 75% com 2, 60% com 3 e 50%
  com 4. O prêmio tem que ser maior que o de um inimigo sozinho.
- **Turno com horda:** o pet age, depois todos os inimigos vivos atacam em sequência, e então o pet
  age de novo. Com a velocidade, a ordem passa a vir da velocidade de cada um.
- **Ataque em área:** itens podem fazer o golpe do pet acertar todos os inimigos.
- **Balanceamento sempre medido** com as estatísticas, antes e depois.

## Regras

### Atributos

`stats(run)` passa a devolver também `spd`, `crit`, `critdmg` e os efeitos elementais. Valores
iniciais (*decisão minha*, o construtor ajusta pelo simulador):

- **Pet:**
  - `spd` vem do herói: Slime 10; heróis em PNG sem `spd` no `character.json` também ficam com 10
    (o Fantasma pode ganhar um valor próprio).
  - `crit` 0,05 e `critdmg` 1,5 de base.
- **Monstros:** cada entrada de `MONSTERS` ganha um multiplicador de velocidade. O morcego é rápido,
  o esqueleto é lento. A velocidade cresce um pouco por andar. Crítico fica pequeno e fixo.
- **Chefes:** recebem um elemento fixo por tipo (`BOSS_ELEMENT`, palpite: morcego raio, rato veneno,
  aranha veneno, esqueleto gelo, olho fogo). O chefe usa a velocidade do tipo, com bônus de chefe.
- **Campos novos em `fx`:**
  - `spd`, `crit`, `critdmg`, `area` (bool);
  - um por elemento com a chance de aplicar por golpe: `queimar`, `eletrizar`, `envenenar`,
    `congelar` (0..1);
  - os já existentes continuam.
  - Raridade escala os valores positivos, como hoje. `area` não escala.
- **Tetos** (*decisão minha*): `crit` ≤ 0,6 antes do bônus de velocidade; chance de cada elemento
  ≤ 0,6; `spd` ≥ 1.

### A rodada

1. No começo de cada rodada, os status de dano (queimadura, veneno) causam dano em quem os tem.
   Quem morre por status sai da luta.
2. A ordem é por `spd`, do maior para o menor. No empate o pet age primeiro; entre inimigos empatados
   vale a ordem da lista.
3. Cada combatente vivo age uma vez:
   - se estiver eletrizado ou congelado, rola a chance de perder o turno. Congelado que perde o turno
     sai do congelamento;
   - **ataque do pet:** escolhe o alvo de menor HP; com `area`, acerta todos. Para cada alvo acertado:
     - se tiver o dobro da velocidade do alvo, ganha o bônus de crítico;
     - se for crítico, multiplica o dano por `critdmg`, que dobra com o bônus;
     - rola cada elemento que tiver.
   - **ataque do inimigo:** a esquiva e a defesa do pet funcionam como hoje, e o escudo absorve como
     hoje. Os chefes rolam o seu elemento.
4. A luta acaba quando todos os inimigos morrem (vitória) ou o pet morre.
5. **Limite de segurança:** 60 rodadas. Se passar disso, a luta termina como vitória do pet, sem
   prêmio extra (*decisão minha*). Assim nenhuma luta trava.

### Status: números iniciais (*decisão minha*, o simulador ajusta)

- **Queimadura:** 2 + 0,3 × andar de dano por turno, durante 3 turnos. Se pegar de novo, renova a
  duração.
- **Eletricidade:** 30% de chance de perder o turno, durante 2 turnos.
- **Veneno:** começa em 1 de dano e soma +1 a cada round, durante 4 turnos. Se pegar de novo, soma
  pilha (com teto de 3 pilhas).
- **Congelamento:** 60% de chance de perder o turno; sai depois de perder um turno ou depois de
  2 turnos.
- No pet, os status de chefe usam os mesmos números.

### Hordas

- Tipo de sala novo, `"horde"`, em `ROOM_WEIGHTS` a partir do andar 3, com peso parecido com o da
  armadilha (*decisão minha*).
- O tamanho é sorteado entre 2 e 4. O número máximo de inimigos cresce com o andar: 2 no andar 3,
  até 4 a partir do andar 8 (*decisão minha*).
- Os monstros são sorteados da lista do andar. HP e ATK de cada um saem com o multiplicador
  (0,75 / 0,6 / 0,5). Velocidade não cai.
- O prêmio é a soma do ouro de cada inimigo × 1,25, e cada inimigo morto conta como uma vitória
  (`kills`).
- Chefes nunca vêm em horda. O mímico continua sendo um inimigo só.

### Evento para a GUI

`enter_room` continua devolvendo um `ev`. O combate passa a registrar a luta como uma lista de passos:

- `ev["foes"]`: um item por inimigo, com `{"sprite", "name", "boss", "element", "hp_max"}`;
- `ev["hits"]`: lista de passos, cada um
  `{"who": "pet"|int, "target": "pet"|int|"todos", "dmg", "crit", "status", "skip", "dot"}`.

Isso substitui as tuplas atuais.

## Interface

- **Até 4 inimigos na tela:** o lado direito mostra os inimigos menores, num grid 2×2. A janela pode
  crescer um pouco na largura. Cada inimigo tem o seu número de dano flutuando.
- **Crítico:** o número sai maior e dourado, com um "!" no fim.
- **Status no inimigo:** o inimigo fica tingido na cor do elemento enquanto o status dura (fogo
  laranja, raio amarelo, veneno verde, gelo azul-claro), mais um floater pequeno com o dano a cada
  turno.
- **Status no pet:** o pet fica tingido na cor do status, e o painel mostra o nome do status ao lado
  do HP.
- **Ataque elemental do pet:** um clarão ou faíscas na cor do elemento no alvo.
- **Animação curta:** como hoje, lutas longas mostram só parte dos passos. O número total de passos
  animados fica limitado (hoje 8; com hordas, até ~12).
- **Status:** a tela de Status (duplo clique) mostra velocidade, crítico e o dano crítico.

## Saves e versões

- `migrate_run` não precisa de nada novo: `stats` calcula os atributos novos com padrões.
- `REGRAS_REV` sobe para 2, porque as fórmulas de combate mudam.
- Heróis em `characters/` sem `spd` funcionam com o padrão.

## Balanceamento

- Antes de mudar qualquer coisa, gerar e guardar uma cópia do JSON de estatísticas como referência.
- Depois, `tools/simular.py` e `tools/estatisticas.py` precisam voltar para dentro das `METAS` na
  calibração (Slime).
- O resumo novo do simulador mostra também as mortes em horda e as mortes por status. O formato atual
  das linhas impressas pode mudar neste projeto, porque as regras mudam.
- As estatísticas ganham, no "Onde as runs morrem", a separação entre monstro sozinho, horda, chefe e
  armadilha.

## Testes

- Ordem por velocidade: um inimigo mais rápido age antes do pet; no empate, o pet age primeiro.
- O bônus do dobro de velocidade aparece dos dois lados (crítico com dano dobrado).
- Cada status:
  - queimadura e veneno causam o dano certo por turno, e o veneno cresce;
  - eletricidade e congelamento fazem perder o turno, e o congelamento sai depois de perder um.
- Monstro comum nunca aplica status; chefe aplica o elemento dele.
- Horda: os multiplicadores de 75/60/50%, o pet escolhe o alvo de menor HP, a área acerta todos,
  o prêmio é maior e cada inimigo conta em `kills`.
- O limite de 60 rodadas encerra a luta.
- GUI (`test_gui`): centenas de salas com hordas e chefes elementais sem exceção; o painel mostra
  status; o tamanho da janela continua estável ao trocar o tamanho do pet.
- Estatísticas: o arquivo e a página continuam funcionando com os campos novos.

## Fica a critério do construtor

- Os números exatos (velocidades, chances, durações) guiados pelo simulador, desde que as regras
  acima valham.
- O layout exato do grid de inimigos e das cores de status.
- Dar ou não um elemento a 1 ou 2 itens existentes para testar.
