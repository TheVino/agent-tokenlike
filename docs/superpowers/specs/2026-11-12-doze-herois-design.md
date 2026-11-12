# 12 heróis autorais e animações expressivas

Data: 2026-11-12. Projeto: Agent Tokenlike. Ler o `CLAUDE.md` antes. Valem a arte 100% original, só
biblioteca padrão no app (o Pillow só em `tools/`), pt-BR, o texto sobre `PANEL_BG` e a medição do
balanceamento com `/balancear`.

## Intenção

Hoje existem 2 heróis (Slime e Fantasma), com animações de 16 px que ficaram sutis demais. O dono quer:

- animações **expressivas** (gestos, rostos e golpes que se leem bem na tela);
- **12 heróis autorais novos**, em temas sombrios e simbólicos, no estilo fofo do jogo;
- cada herói liberado por uma **conquista temática**;
- **sem mímico** como herói.

## Decisões do dono

- **Arte em 32×32 px** por quadro. Na tela, o pet continua do mesmo tamanho (a regra de escala que já
  existe para heróis grandes cuida disso), com 4× mais detalhe.
- **Os 12 heróis e seus símbolos:**

  | # | Herói | Símbolos |
  |---|---|---|
  | 1 | Médico da Peste | máscara de bico, lanterna de ervas |
  | 2 | Bruxa do Pântano | caldeirão, chapéu torto |
  | 3 | Coveiro | pá, lampião |
  | 4 | Ceifeirinho | foice pequena, manto com capuz |
  | 5 | Vela Viva | chama na cabeça, cera que derrete |
  | 6 | Cogumelo de Caverna | esporos que brilham |
  | 7 | Inquisidor | livro trancado, sino |
  | 8 | Boneca de Pano | botões nos olhos, costuras |
  | 9 | Cavaleiro Oco | armadura vazia com um olhinho dentro |
  | 10 | Corvo Mensageiro | carta lacrada |
  | 11 | Alquimista | frascos, monóculo |
  | 12 | Freira das Cinzas | véu, terço de ossinhos |

- **Cada herói tem um traço passivo pequeno**, feito com os campos de `fx` que já existem (sem mecânica
  nova).
- **Liberação por conquista temática.** Cada herói tem a sua conquista própria e nova, ligada ao tema
  dele.
- O Slime e o Fantasma continuam e também ganham as animações expressivas (redesenhados em 32 px).

## Objetivos

- 14 heróis jogáveis: Slime, Fantasma e os 12 novos.
- Os 9 estados (`folha.ESTADOS`) desenhados de verdade, de 4 a 6 quadros cada, com um gesto
  reconhecível por estado:
  - **idle:** respira ou mexe algo do símbolo (a chama da vela, o lampião balançando);
  - **run_r:** corre de lado (pernas, manto, quique), com olhar na direção do movimento;
  - **waving:** acena com a mão ou com o objeto do símbolo;
  - **jumping:** agacha, salta e cai;
  - **failed:** cai ou se desfaz (a vela apaga, a boneca desmonta, o cavaleiro desaba);
  - **waiting:** cochila ou espera (cabeça pende, zZ);
  - **running:** golpe de luta com o objeto do símbolo (pá, foice, frasco, livro);
  - **review:** pensa (mão no queixo, "?", olha em volta).

  O `run_l` sai espelhado do `run_r`, gerado pela ferramenta.
- **Evolução em 3 estágios por herói** (andares do `stage_floors`, padrão `[1, 4, 10]`). Cada estágio
  usa os mesmos quadros base com um acréscimo visual desenhado uma vez e aplicado pela ferramenta em
  todos os quadros, sempre no ponto certo. Exemplos:
  - Médico da Peste: chapéu, depois capa;
  - Vela Viva: chama maior, depois castiçal;
  - Cavaleiro Oco: elmo, depois estandarte.

  Assim são 3 visuais por herói sem triplicar o desenho.
- Itens e efeitos continuam se encaixando por contorno, como em qualquer herói.

## Fora do escopo

- Mecânicas exclusivas por herói (habilidades ativas). Só o traço passivo, com `fx`.
- Novos monstros, salas ou itens.
- Sons.

## Anti-objetivos

- Personagem reconhecível de outro jogo, filme ou anime. Médico da peste, bruxa, ceifador e as outras
  figuras são arquétipos históricos ou de folclore, e o desenho precisa ser nosso.
- Um herói muito mais forte que os outros: o traço passivo não pode dominar.
- Animações que só mexem o corpo inteiro (sobe, desce, achata), como a versão atual. Cada estado
  precisa de um gesto próprio.
- Cada herói ser um mímico ou um item vivo de baú (o dono vetou o mímico).

## Formato e ferramenta

- Cada herói fica em `characters/<chave>/`, com `character.json` (`name`, `stats`, `unlock`, `stages`
  com `floor`, `title` e `sheet`) e uma folha PNG por estágio, gerada pela ferramenta.
- O desenho é feito em grades de texto 32×32 num módulo de arte (`arte_herois.py` ou um arquivo por
  herói em `arte_herois/`), com paleta por herói.
- `tools/gerar_folhas.py` gera as folhas no layout de 9 linhas, espelha o `run_l`, aplica o acréscimo
  de cada estágio e escreve os PNGs (só biblioteca padrão). As folhas geradas são commitadas.
- Uma prévia em `tools/saida/preview_herois.png` mostra todos os estados de todos os heróis em tamanho
  grande, para revisão a cada leva.

## Traços passivos (*decisão minha*, o simulador ajusta)

Usam `fx` que já existem, somados aos stats base do herói (`hp`, `atk`, `def`, `spd`):

| Herói | Traço |
|---|---|
| Médico da Peste | `envenenar` 0,10 |
| Bruxa do Pântano | `queimar` 0,08 e `sorte` 0,2 |
| Coveiro | `gold` 0,4 |
| Ceifeirinho | `crit` 0,08, `hp` menor |
| Vela Viva | `queimar` 0,12, `maxhp` −4 |
| Cogumelo de Caverna | `cura_sala` 1 |
| Inquisidor | `def` +1 e `espinhos` 0,1 |
| Boneca de Pano | `dodge` 0,1 |
| Cavaleiro Oco | `bloqueio` 1, `spd` menor |
| Corvo Mensageiro | `spd` maior e `duplo` 0,08 |
| Alquimista | `desconto` 0,2 e `cura_andar` 3 |
| Freira das Cinzas | `lifesteal` 1 e `congelar` 0,06 |

O traço fica no `character.json` (por exemplo `"traço": {"envenenar": 0.1}`), entra em `stats()` como um
item invisível que não escala com a raridade, e aparece na tela de Status e no menu de heróis.

## Conquistas temáticas (*decisão minha*)

Uma por herói, novas em `masmorra.ACHIEVEMENTS` com a regra em `_check_achievements`:

| Herói | Conquista |
|---|---|
| Médico da Peste | matar 1 inimigo com veneno |
| Bruxa do Pântano | pegar 3 itens elementais numa run |
| Coveiro | juntar 300 de ouro numa run |
| Ceifeirinho | vencer uma horda de 4 inimigos |
| Vela Viva | matar 1 inimigo com queimadura |
| Cogumelo de Caverna | chegar ao andar 8 com o HP cheio |
| Inquisidor | chegar ao andar 15 |
| Boneca de Pano | esquivar 10 golpes numa run |
| Cavaleiro Oco | bloquear 10 golpes numa run |
| Corvo Mensageiro | vencer 3 chefes no total (meta) |
| Alquimista | consumir 10 itens numa run |
| Freira das Cinzas | morrer 10 vezes (meta; consolo para quem perde muito) |

As que contam eventos de luta (golpes esquivados, bloqueados, mortes por status) precisam de contadores
na run. O `combate` já tem os passos com `dodge`, `bloqueado` e `status`, e `enter_room` soma esses
contadores.

## Levas

Cada leva tem arte, `character.json`, traço, conquista, testes e prévia. O balanceamento é medido no
fim de cada leva.

- **Leva 0:** as ferramentas (gerador de folha 32 px com espelho e acréscimos de estágio, traço
  passivo em `stats()`, contadores de conquista, prévia) e o Slime e o Fantasma redesenhados em 32 px,
  já com as animações expressivas.
- **Leva 1:** heróis 1 a 4.
- **Leva 2:** heróis 5 a 8.
- **Leva 3:** heróis 9 a 12, mais o balanceamento final e a documentação.

## Balanceamento

- A calibração das `METAS` continua só com o Slime, como hoje.
- A seção "Heróis" das estatísticas mostra cada herói. Nenhum herói pode ficar com mediana de andar fora
  de ±2 andares da mediana do Slime, a não ser por decisão anotada.
- Traços fortes demais são ajustados nos números do `character.json`.

## Testes

- A ferramenta gera folhas de 9 linhas com quadros de 32×32. O `run_l` é o espelho do `run_r`. Os
  acréscimos de estágio aparecem no mesmo ponto de todos os quadros.
- Cada herói tem os 9 estados, com pelo menos 4 quadros cada, e todo quadro tem pixels opacos.
- O traço passivo entra em `stats()` e não escala com a raridade.
- Cada conquista dispara no evento certo (testes em `masmorra`, com runs montadas à mão).
- `test_gui`: os 14 heróis passam por centenas de salas sem exceção. O menu mostra os bloqueados com a
  conquista que libera cada um.
- Todos os testes atuais continuam passando.

## Fica a critério do construtor

- A paleta e os detalhes do desenho de cada herói, dentro do tema e dos símbolos.
- Os números finais de stats e traços, guiados pelas estatísticas.
- O nome exato das chaves das conquistas.
