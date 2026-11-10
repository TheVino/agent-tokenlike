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
| Botão direito | Menu: Cemitério, Conquistas, herói da próxima run, tamanho, desistir da run, sair |

## Como a masmorra funciona

- **Energia:** cada token do Claude Code vira energia (os tokens lidos do cache valem 10%).
  A barra azul do painel enche, e cada **100 mil** de energia = **1 sala**. A mochila guarda no máximo 20 salas.
- **Andares:** 5 salas por andar, depois a escada. A cada **5 andares** a última sala é um **chefe** (com coroa).
- **Salas aleatórias:** monstro, baú (que às vezes é um **mímico**), armadilha, fonte de cura, lojinha e altar sombrio
  (pactos com preço: perde HP máximo e ganha ATK, troca ouro por cura...).
- **Itens:** 3 espaços (mão, escudo, cabeça). Cada item aparece **desenhado no pet** e muda as regras,
  por exemplo a Vela Amaldiçoada dá +50% de energia, mas as armadilhas doem o dobro.
  Se o item novo for pior que o atual, ele é vendido automaticamente.
- **Evolução dentro da run:** o Slime evolui ao chegar nos andares 3, 8 e 15 (+4 HP máx, +1 ATK).
- **Permadeath:** se morrer em combate ou numa armadilha, vira lápide no **Cemitério** (andar, assassino, itens)
  e uma nova run começa. A energia guardada passa para a run nova.
- **Descanso:** ficar sem usar o Claude Code **nunca mata o pet**. Depois de 5 minutos parado ele descansa
  e recupera HP; depois de 10, dorme (Zzz).
- **Conquistas e desbloqueios:** chegar ao andar 5 ou 10, derrotar um chefe, derrotar um mímico... cada conquista libera
  itens novos no sorteio e **heróis novos**. O Fantasma é liberado ao derrotar o primeiro chefe.

Em simulação, cerca de 40% das runs passam do primeiro chefe, e as melhores chegam ao andar 15–20.
Os números ficam no topo do `masmorra.py` (`MON_HP`, `BOSS_HP`, `ROOM_COST`...) e podem ser ajustados.

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

- `stats`: HP, ataque, defesa e esquiva (0.2 = 20%) iniciais.
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

## Outras opções

- `python tokenlike.py --import-history`: no primeiro uso, já começa com a mochila cheia de energia vinda do seu histórico.
- `python tokenlike.py --reset`: apaga tudo (runs, cemitério, conquistas) e começa do zero.
- **Abrir junto com o Windows:** `Win + R` → `shell:startup` → crie ali um atalho para o `iniciar.bat`.
- **Desinstalar:** feche o pet (botão direito → Sair) e apague esta pasta e a `%USERPROFILE%\.tokenlike` (e a antiga `.tokenpet`, se existir).

> Só o uso do **Claude Code** alimenta o pet. Conversas no app/site do Claude não ficam salvas no seu PC.

Projeto pessoal e **não oficial**, sem vínculo com a Anthropic. Licença MIT (veja `LICENSE`). README em inglês: `README.md`.
