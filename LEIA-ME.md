# Agent Tokenlike: Masmorra de Tokens 🕯️

Um bichinho de pixel que fica flutuando na sua tela e **desce uma masmorra usando como energia
os tokens que você gasta no Claude Code**. Salas aleatórias, itens que aparecem no visual dele,
chefes, desbloqueios e **permadeath**.

## Privacidade (o que ele faz e o que NÃO faz)

- Lê os logs que o próprio Claude Code já grava no seu PC (`%USERPROFILE%\.claude\projects\*.jsonl`)
  e aproveita **só os números de tokens** de cada resposta.
- **Não** guarda nem mostra prompts ou respostas.
- **Não** usa internet, **não** tem login e **não** instala hooks nem mexe nas configurações do Claude Code.
- O progresso fica em `%USERPROFILE%\.tokenlike\state.json`, que você pode abrir e conferir.
  Quem usava a versão antiga (TokenPet): na primeira execução o progresso de `.tokenpet` é **copiado**
  para `.tokenlike` (o antigo não é apagado).
- Opcional, e só se **você** ligar: o `statusline.py` (veja "Barras de sessão e semana") guarda só as suas
  porcentagens oficiais de uso para o pet desenhar. Nada mais do Claude Code é guardado.
- Usa só a biblioteca padrão do Python, em três arquivos: `tokenlike.py` (tela), `masmorra.py` (regras) e `arte.py` (desenhos).

## Como usar

1. Tenha o Python 3.9+ instalado (python.org; marque "Add to PATH" na instalação).
2. **`testar-demo.bat`**: modo demo, com tokens falsos para ver salas, lutas, mortes e desbloqueios acontecendo rápido.
   O progresso do demo fica separado do real.
3. **`iniciar.bat`**: modo real. O pet aparece no canto inferior direito da tela.

| Ação | O que faz |
|---|---|
| Arrastar | Move o pet |
| Clique | Carinho ❤ |
| Duplo clique | Status: HP, ATK, DEF, itens, energia guardada, recorde |
| Botão direito | Menu: Cemitério, Conquistas, herói da próxima run, tamanho, Modo (Auto ou Interativo), desistir da run, sair |

## Como a masmorra funciona

- **Energia:** cada token do Claude Code vira energia (os tokens lidos do cache valem 10%).
  A barra azul do painel enche, e cada **100 mil** de energia = **1 sala**. A mochila guarda no máximo 20 salas.
- **Andares:** 5 salas por andar, depois a escada. A cada **5 andares** a última sala é um **chefe** (com coroa).
- **Salas aleatórias:** monstro, **horda** (2 a 4 inimigos mais fracos, a partir do andar 3), baú (que às vezes é um
  **mímico**), armadilha, fonte de cura, lojinha e altar sombrio (pactos com preço: perde HP máximo e ganha ATK,
  troca ouro por cura...).
- **Combate por rodadas:** a cada rodada age primeiro quem tem mais **velocidade** (no empate, o pet). Todo golpe pode
  ser **crítico**; quem tem o dobro da velocidade do alvo ganha chance extra de crítico, com dano dobrado. Cada chefe
  tem um elemento e pode deixar o pet com um **status**: queimadura e veneno tiram HP no começo da rodada,
  eletricidade e congelamento podem fazer perder a vez. Na horda o pet bate no inimigo com menos vida. Uma luta
  que passa de 60 rodadas termina empatada: o pet segue, mas sem prêmio.
- **Itens:** não há limite de espaços, os itens **se empilham** (cada um aparece no máximo uma vez por run) e todos
  aparecem **no pet**: objetos na mão, na cabeça ou flutuando, espinhos, gotas, contorno, cor. Cada item muda as regras,
  por exemplo a Vela Amaldiçoada dá +50% de energia, mas as armadilhas doem o dobro.
  Cada item vem com uma **raridade**: comum, **raro** (azul), **épico** (roxo) ou **lendário** (dourado); quanto mais raro,
  mais forte o bônus (os efeitos ruins não aumentam). Ao achar um item dá para **pegar** (entra na pilha) ou **consumir**
  (cura na hora ou vira **escudo**, que absorve dano antes do HP).
- **Modos:** no **Auto** o pet decide sozinho (consome se estiver com pouca vida, senão pega). No **Interativo** abre uma
  janelinha com Pegar/Consumir e o pet espera; se ninguém escolher em **30 segundos**, a regra automática decide
  assim que a próxima sala estiver pronta.
- **Evolução dentro da run:** o Slime evolui ao chegar nos andares 3, 8 e 15 (+4 HP máx, +1 ATK).
- **Permadeath:** se morrer em combate ou numa armadilha, vira lápide no **Cemitério** (andar, assassino, itens)
  e uma nova run começa. A energia guardada passa para a run nova.
- **Descanso:** ficar sem usar o Claude Code **nunca mata o pet**. Depois de 5 minutos parado ele descansa
  e recupera HP; depois de 10, dorme (Zzz).
- **Conquistas e desbloqueios:** chegar ao andar 5 ou 10, derrotar um chefe, derrotar um mímico... cada conquista libera
  itens novos no sorteio e **heróis novos**. O Fantasma é liberado ao derrotar o primeiro chefe.

Em simulação, cerca de 40% das runs passam do primeiro chefe, e as melhores chegam ao andar 15–25.
Os números ficam no topo do `masmorra.py` (`MON_HP`, `BOSS_HP`, `RAR_MULT`, `ROOM_COST`...) e podem ser ajustados.

## Criando novos heróis

Cada herói é uma pasta dentro de `characters\`, com as imagens PNG e um `character.json`.
Veja o exemplo `characters\fantasma\`:

```json
{
  "name": "Fantasma",
  "unlock": "chefe1",
  "stats": { "hp": 16, "atk": 3, "def": 0, "dodge": 0.2 },
  "stages": [
    { "floor": 1,  "title": "Fantasminha",   "frames": ["estagio1.png"], "blink": "estagio1_piscando.png" },
    { "floor": 4,  "title": "Fantasma",      "frames": ["estagio2.png"], "blink": "estagio2_piscando.png" },
    { "floor": 10, "title": "Fantasma Mago", "frames": ["estagio3.png"], "blink": "estagio3_piscando.png" }
  ]
}
```

- `stats`: HP, ataque, defesa e esquiva (0.2 = 20%) iniciais. `spd` (velocidade) é opcional; sem ele, fica 10
  (a do Slime). Ex.: `"spd": 12`.
- `unlock` (opcional): conquista que libera o herói. Pode ser `andar5`, `chefe1`, `mimico`, `rico`,
  `colecionador`, `andar10` ou `andar20`. Sem esse campo, o herói já começa liberado.
- `stages`: as formas do herói e o **andar** em que ele evolui para cada uma.
- `frames`: uma ou mais imagens que se alternam a cada `frame_ms` milissegundos.
  `blink` (olhos fechados) e `sleep` (dormindo) são opcionais.
- **Imagens:** PNG com fundo transparente. Pixel art pequena (16×16 ou 32×32) é ampliada sozinha.
  Os itens se encaixam sozinhos em volta da parte desenhada. Evite bordas semitransparentes,
  porque podem aparecer com um contorno rosado no Windows.

Depois, use **botão direito → Recarregar personagens**. Se algo der errado, o motivo fica em
`%USERPROFILE%\.tokenlike\tokenlike.log`.

## Barras de sessão e semana (opcional)

O pet pode mostrar o seu uso **oficial** da sessão de 5 horas e da semana (os mesmos números do `/usage`), com o
horário em que cada um zera. O Claude Code só entrega esses números para um script de *statusline*, então é você
quem liga. O pet nunca mexe nas configurações do Claude Code.

Coloque isto no `%USERPROFILE%\.claude\settings.json` (com o caminho real desta pasta):

```json
"statusLine": { "type": "command", "command": "python \"C:/caminho/para/agent-tokenlike/statusline.py\"" }
```

A statusline do Claude Code passa a mostrar `sessão 42% · semana 18%` e o pet ganha duas barras embaixo da barra de
energia (verde até 50%, amarelo até 80%, vermelho acima). Os números atualizam quando o Claude Code atualiza a
statusline, depois da primeira resposta da sessão, e valem para a conta inteira (outros PCs e claude.ai incluídos).
Para desligar, apague a linha e o arquivo `%USERPROFILE%\.tokenlike\limites.json`. Precisa do Claude Code 2.1.80+.
O Claude Code só aceita uma statusline: se você já usa outra, escolha uma.

## Outras opções

- `python tokenlike.py --import-history`: no primeiro uso, já começa com a mochila cheia de energia vinda do seu histórico.
- `python tokenlike.py --reset`: apaga tudo (runs, cemitério, conquistas) e começa do zero.
- **Abrir junto com o Windows:** `Win + R` → `shell:startup` → crie ali um atalho para o `iniciar.bat`.
- **Desinstalar:** feche o pet (botão direito → Sair) e apague esta pasta e a `%USERPROFILE%\.tokenlike` (e a antiga `.tokenpet`, se existir).

> Só o uso do **Claude Code** alimenta o pet. Conversas no app/site do Claude não ficam salvas no seu PC.

Projeto pessoal e **não oficial**, sem vínculo com a Anthropic. Licença MIT (veja `LICENSE`). README em inglês: `README.md`.
