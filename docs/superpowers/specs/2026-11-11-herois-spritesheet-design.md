# Heróis por spritesheet e pets da comunidade (projeto 4 do roadmap)

Data: 2026-11-11. Projeto: Agent Tokenlike. Ler o `CLAUDE.md` antes. As regras de lá valem: só
biblioteca padrão no app, sem rede, arte do repositório 100% original, texto sobre `PANEL_BG`.

## Intenção

Qualquer pessoa deve conseguir trazer o próprio herói. Hoje isso exige vários PNGs e um
`character.json`. O dono quer aceitar o formato que a comunidade do AgentPet e do Petdex já usa: um
spritesheet só, com **9 linhas de animação** (o mesmo prompt que o AgentPet publica). Assim, quem
gerar um pet com aquele prompt, ou já tiver pets do Petdex instalados, joga com ele na masmorra,
e os itens aparecem por cima, como em qualquer herói.

## Decisões do dono

- O app usa pets da comunidade **só lendo o que o usuário já instalou ou colocou** na pasta. Nunca
  baixa nada e nunca distribui esses pets no repositório. Eles são fan art com licença de cada autor.
- Só `.png` (o tkinter não lê WebP).
- O formato é o do prompt do AgentPet: 9 linhas, uma animação por linha, de 4 a 8 quadros, com fundo
  transparente e espaço transparente entre quadros e entre linhas.
- O LEIA-ME e o README trazem esse prompt adaptado, para a pessoa gerar o próprio herói.
- **Pastas lidas:**
  - `characters/<pasta>/`, com `spritesheet.png` e, se quiser, um `character.json` com stats e unlock;
  - `~/.petdex/pets/<slug>/` e `~/.codex/pets/<slug>/` (Petdex), com `pet.json` + spritesheet.

## Objetivos

- Ler um spritesheet de 9 linhas e cortar os quadros automaticamente pelas faixas transparentes.
- As animações da folha viram os estados do pet no jogo (tabela abaixo).
- Os itens se encaixam em heróis grandes, numa escala proporcional ao tamanho do herói. É a
  pendência "escala dos itens" das partes 1 e 3.
- O desempenho continua bom: compor as imagens ao pegar um item leva menos de 1 s mesmo com herói
  grande e muitos itens.
- Um pet com defeito (PNG ruim, folha sem linhas detectáveis) é ignorado e o motivo vai para o log,
  sem derrubar o app (o loader de hoje já faz isso).

## Fora do escopo

- Ler WebP.
- Baixar pets ou abrir a galeria do Petdex.
- Editor de herói.
- Stats específicos por pet da comunidade (todos usam stats padrão).

## Animações da folha → estados do jogo

| Linha | Nome no prompt | Uso no jogo |
|---|---|---|
| 1 | Idle | pet parado (os quadros normais) |
| 2 | Run Right | pet andando entre salas (opcional; se faltar, usa Idle) |
| 3 | Run Left | não usado |
| 4 | Waving | carinho (clique no pet) |
| 5 | Jumping | evolução e vitória contra chefe |
| 6 | Failed | morte, antes da lápide aparecer |
| 7 | Waiting | descansando e dormindo (no lugar de `sleep`) |
| 8 | Running | luta (enquanto a sala de combate anima) |
| 9 | Review | escolha pendente no modo interativo |

- Se uma linha estiver faltando ou vazia, o jogo usa Idle no lugar dela.
- Piscar: não existe na folha. Esses heróis não piscam.
- **Evolução:** cada estágio de evolução usa a mesma folha. Num `characters/<pasta>/character.json`,
  `stages` pode apontar uma folha diferente por estágio (`"sheet": "estagio2.png"`). O formato antigo
  (PNGs soltos) continua funcionando.

## Corte automático

- Uma linha de pixels sem nenhum pixel opaco separa as linhas da folha; uma coluna sem nenhum pixel
  opaco, dentro da faixa de uma linha, separa os quadros.
- Se o Petdex informar no `pet.json` o tamanho do quadro e o número de linhas e colunas, a grade
  informada tem prioridade sobre a detecção automática (*decisão minha*).
- Cada quadro é alinhado pela base: ponto de apoio no centro de baixo. Todos os quadros de uma folha
  usam a mesma caixa (a maior entre eles), para o pet não "pular" entre quadros.
- A leitura de pixels é feita **uma vez**, ao carregar o herói, e fica em cache em memória.

## Escala

- O herói é reduzido para uma altura de arte de **no máximo 48 px**, por amostragem inteira
  (pega 1 a cada N pixels, sem suavizar). Assim vale a regra da pixel art e o custo fica limitado.
- Os itens e os efeitos usam um **fator de escala** `k = round(altura_do_herói / 16)`, mínimo 1:
  - objetos e adesivos são ampliados por `k`;
  - os efeitos de contorno (espinhos, gotas, chamas etc.) continuam calculados no próprio contorno
    do herói, que já está maior.
- `visual.compose` e o `LOOK_BOX` ganham o parâmetro de escala. Com `k = 1`, tudo fica idêntico a
  hoje.
- A janela do pet se ajusta ao tamanho final.

## Detalhes decididos (*decisões minhas*, depois da revisão)

- **Tamanho na tela:** o pet ocupa na tela o mesmo espaço do Slime de hoje (16 px de arte × `px`).
  O herói grande é desenhado com menos pixels de tela por pixel de arte (`px_heroi = px × 16 / altura`)
  e os itens, ampliados por `k`, seguem a mesma escala. A janela, o painel e os números flutuantes
  ficam como estão.
- **Petdex:**
  - a folha é o `.png` da pasta (de preferência `spritesheet.png`);
  - se o tamanho da folha bater com uma grade de 8 colunas × 9 linhas (ou × 11, formato v2), usa essa
    grade fixa;
  - senão, faz o corte automático;
  - campos desconhecidos do `pet.json` são ignorados; dele, só se usa `name`;
  - pasta só com WebP: o log diz "converta para PNG para usar este pet".
- **Corte automático com segurança:** se uma linha der mais de 8 quadros (provavelmente uma mão ou
  efeito solto partiu um quadro), o jogo junta pedaços estreitos ao vizinho. Se ainda passar de 8, a
  linha vira 8 células de largura igual. Linha com 0 quadros: usa Idle.
- **Redução:** usa o menor inteiro N tal que `altura / N ≤ 48` (1 a cada N pixels). O resultado fica
  entre ~25 e 48 px. Um quadro de 64 px vira 32 px.
- **Pet sem `character.json`:** um estágio só, no andar 1, com o nome do pet como título. Por isso
  não evolui. Num `character.json`, cada estágio pode ter `frames` (PNGs soltos) **ou** `sheet`.
- **Evolução com outra folha:** o fator `k` e a escala na tela são recalculados ao evoluir. Como o
  tamanho na tela é normalizado, a janela não muda.

## Stats e desbloqueio

- Herói da comunidade sem `character.json`: stats padrão (`hp` 20, `atk` 3, `spd` 10), liberado desde
  o começo.
- O nome vem do `pet.json` (`name`) ou do nome da pasta.
- No menu "Herói da próxima run", os pets da comunidade aparecem numa seção separada "Comunidade".

## Privacidade e licença

- Nada é copiado para o repositório nem para `~/.tokenlike`. O app só lê as pastas.
- O README explica que pets do Petdex são de quem os criou e que o Agent Tokenlike só os exibe
  localmente.

## Prompt para a pessoa criar o próprio herói (vai no LEIA-ME e no README)

Mesmo prompt do AgentPet, com estes acréscimos:

- personagem pequeno, com quadros de **no máximo 64×64 px**, em pixel art de verdade;
- contorno escuro de 1 px;
- sem nada além do personagem (sem chão, sem sombra).

E as instruções de onde colocar o arquivo: `characters/<nome>/spritesheet.png`.

## Testes

- Corte:
  - uma folha sintética de 9 linhas com tamanhos de quadro diferentes é cortada certo (número de
    quadros por linha e alinhamento pela base);
  - uma folha com linhas faltando cai no Idle;
  - uma folha sem separação é recusada com mensagem no log.
- Escala: herói de 192 px reduzido para no máximo 48 px; `k` certo; composição com `k = 1` idêntica a
  hoje; com `k = 3`, os objetos ficam 3× maiores e o ponto de apoio não muda.
- Petdex: uma pasta falsa em `~/.petdex/pets/x/` (num HOME temporário) com `pet.json` e PNG aparece
  como herói; o mesmo em WebP é ignorado com log.
- GUI: centenas de salas com um herói de folha; os estados usam as linhas certas (morte com Failed,
  descanso com Waiting, escolha com Review); o tempo de composição fica abaixo de 3 s com o tkinter
  falso.
- Todos os testes atuais continuam passando.

## Fica a critério do construtor

- Como guardar os quadros em cache.
- A posição exata da seção "Comunidade" no menu.
- A ordem de aplicação dos estados quando dois coincidem (por exemplo, escolha pendente enquanto
  dorme).
