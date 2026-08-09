# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Cantinho

App desktop pessoal de acompanhamento de atividades diárias, estética cozy lo-fi.
Um cômodo ilustrado onde o timer alimenta um diário, e as entregas viram objetos
na estante.

## Princípio de design (leia antes de sugerir qualquer feature)

"Acompanhamento de atividades" puxa para métricas e cobrança; "cozy lo-fi" puxa
para ambiente e ritmo lento. **Quando os dois brigarem, cozy vence.**

- O tracking é subproduto do uso, nunca o objetivo declarado na tela.
- Nada de streaks, barras de progresso, percentuais ou linguagem de desempenho.
- Falhar não destrói nada. Só não cresce.
- Nenhum gráfico ou dashboard na tela principal.

## Stack

- Python 3.10+ / PySide6 6.11.1
- QML para toda a UI (não QtWidgets, não QSS)
- SQLite via `sqlite3` da stdlib (não DuckDB, não ORM)
- pytest para testes
- PyInstaller (onedir, portable) para distribuição

Sem dependências além de PySide6 e pytest sem discussão prévia.

## Comandos

Sempre a partir da raiz do repositório, **e sempre com o Python do venv** — o
`python` do PATH é o do sistema e não tem PySide6.

Não há `pyproject.toml`/`setup.py`, de propósito. Como o Python põe no
`sys.path` o diretório do *script* e não o diretório atual, cada ferramenta de
`tools/` que importa `cantinho.*` insere a raiz do repositório no `sys.path`
por conta própria. Sem isso, `python tools/x.py` falha com
`ModuleNotFoundError: No module named 'cantinho'` mesmo rodando da raiz — que
é justamente o que estas instruções mandam fazer.

Windows (PowerShell), venv em `.venv/`:

```powershell
.venv\Scripts\Activate.ps1        # ou prefixar tudo com .venv\Scripts\python.exe
pip install -r requirements-dev.txt   # runtime + pytest + pyinstaller

python -m cantinho.main           # rodar o app
python -m cantinho.main --db .\teste.db --log DEBUG   # banco descartável
python -m pytest                  # suíte completa
python -m pytest tests/test_projections.py::test_planta_decai_ao_avancar_14_dias
python -m pytest -k planta -x     # por nome, parando no primeiro erro
python tools/check_svg.py         # validar SVGs -> build/svg_check/*.png
python tools/simular_uso.py       # percorre a UI com mouse e teclado sintéticos
python tools/semear.py            # banco de demonstração em build/demo.db
python tools/semear.py --de-novo  # refaz um banco já semeado
python tools/gerar_audio.py       # regera assets/audio/*.wav
python tools/gerar_icone.py       # regera assets/icon/cantinho.{ico,png}
python tools/gerar_capturas.py    # regera docs/quarto-*.png do README
pyinstaller cantinho.spec --noconfirm   # portable em dist/Cantinho/
python tools/empacotar_portatil.py      # pacote sobre o Python oficial
```

`tools/semear.py` existe porque um banco vazio não mostra quase nada: sem ele,
avaliar estante, planta, mural ou bilhete exige usar o app por duas semanas.
Ele escreve pelos construtores de evento, com o relógio deslocado para trás, e
imprime as projeções resultantes — o log que sai é legítimo, não um fixture.

Ele se recusa a semear um banco que já tem eventos: os uuids são novos a cada
execução, então o `INSERT OR IGNORE` do store não protege, e semear duas vezes
empilha duas semanas sobre outras duas — a estante passa da lotação do desenho
e a planta trava no estágio 4. `--de-novo` apaga e refaz, mas só se **tudo** no
log tiver saído desta ferramenta; se houver evento de outro `device_id`, ele
recusa mesmo com a flag, porque aí é banco de uso real.

**Rode `tools/simular_uso.py` com a tela ligada.** Com o monitor apagado ou a
sessão bloqueada, o Windows para de apresentar quadros; o render loop threaded
do Qt congela junto e **toda animação para**. Os cliques continuam funcionando e
as propriedades mudam, mas os `Behavior` não avançam: `aba` vira "backlog" e a
gaveta fica com opacidade zero, então o roteiro não acha nada lá dentro e falha
em cascata como se a interface estivesse quebrada. A ferramenta já força
`QSG_RENDER_LOOP=basic` para contornar a parte das animações, mas o clique que
dá foco a um campo de texto continua não funcionando nesse estado.

`tools/simular_uso.py` é o que cobre o QML — o pytest não cobre. Ele cria
tarefa, roda sessão, conclui, arrasta, captura ideia e fecha o dia clicando de
verdade; depois reabre o banco e confere o log evento por evento. Rode depois
de mexer em qualquer `.qml`. Passe uma pasta como argumento para guardar as
capturas de cada etapa.

Linux (casa) é o mesmo com `source .venv/bin/activate`.

`--db` e `--device-id` existem para teste: sem eles o banco vai para a pasta de
dados do sistema, e é fácil sujar o banco real ao experimentar. `--db` expande
`~` por conta própria — o PowerShell não expande til em argumento de executável
nativo, e sem isso `--db ~/x/t.db` cria uma pasta chamada `~` no diretório atual
e o app abre num banco vazio sem dar erro nenhum.

Cada banco aceita **uma instância**. Abrir de novo o mesmo banco traz a janela
que já existe para a frente e sai; bancos diferentes abrem em paralelo.

Para rodar a suíte sem abrir janela: `$env:QT_QPA_PLATFORM="offscreen"`. Cuidado
que nesse modo o Qt fica **sem nenhuma família de fonte** — texto vira tofu em
screenshot. Para avaliar a UI de verdade, rode com a plataforma normal.

`tools/gerar_capturas.py` semeia um banco temporário e fotografa os dois temas
em `docs/`. As imagens do README são versionadas, e capturar à mão significa
que elas envelhecem em silêncio — a primeira leva delas ficou mostrando um
quarto sem calendário, sem relógio e sem bilhete.

`tools/check_svg.py` varre `assets/**/*.svg`, rasteriza cada um e sai com código
1 se algum falhar. Não basta olhar o exit code: **abra os PNGs em
`build/svg_check/`**, porque um SVG com feature não suportada renderiza vazio ou
parcial sem que `isValid()` reclame.

## Duas máquinas, um log de commits

O repositório é público em `github.com/igormahall/cantinho` e é editado de dois
lugares: Windows e Ubuntu, na mesma máquina dual-boot. O código sincroniza pelo
GitHub; **os bancos de evento não sincronizam nunca** e não estão no repositório.

O `.gitattributes` fixa LF para todo texto (`* text=auto eol=lf`). Sem isso,
quem decide a quebra de linha é o `core.autocrlf` de cada sistema — que é
configuração local, não viaja no clone — e trocar de sistema faz o `git status`
acusar o repositório inteiro como modificado sem uma linha de diferença real.
Se isso acontecer, o conserto é `git add --renormalize .`, não commitar o ruído.

O `.venv/` é por máquina e não é versionado. Depois de trocar de sistema ou de
puxar mudança em `requirements*.txt`, refaça: `pip install -r requirements-dev.txt`.

Antes de trocar de sistema, empurre o que está pendente — o pior conflito neste
projeto é um `.qml` editado nos dois lados. Fluxo normal:

```bash
git pull --rebase     # antes de começar
git push              # antes de desligar
```

## Distribuição

São dois empacotadores, para dois problemas diferentes.

- `cantinho.spec` (PyInstaller) → `dist/Cantinho/`, ~198 MB. É o build de casa.
- `tools/empacotar_portatil.py` → `Cantinho-portatil-windows.zip`, ~235 MB
  descompactado. É o build da fábrica.

O segundo existe porque o antivírus corporativo (AhnLab V3) apaga o executável
do PyInstaller, e lá não há administrador do antivírus para criar exceção. O
bootloader do PyInstaller é o mesmo binário em todo programa empacotado com
ele, inclusive nos maliciosos, e sem assinatura de editor não tem como se
distinguir. Em vez de tentar contornar o efeito, o empacotador portátil remove
a causa: monta o app sobre o `python.exe` oficial da PSF, que já vem assinado,
e não constrói binário nenhum.

A poda do Qt no portátil compara nomes **em minúsculas**. A primeira versão
comparava sensível a maiúsculas e deixou 83 MB de recurso do WebEngine para
trás, porque o Qt escreve `Qt6WebEngine` na DLL e `qtwebengine` no `.pak`.

Detalhes, instruções de instalação na máquina do trabalho e o que fazer se
mesmo assim for bloqueado: `docs/fabrica.md`.

## Contexto de uso (restrições reais)

- **Trabalho**: Windows, rede corporativa restrita, sem internet externa
  confiável. Roda `.exe` portable, sem instalação e sem admin. Uso diurno.
- **Casa**: Ubuntu 22.04 (X11), uso noturno para doutorado e projetos paralelos.
- **Os dois ambientes NUNCA sincronizam dados.** Bancos independentes.
- Build é feito em cada plataforma separadamente (máquina dual-boot).
- **Windows é a prioridade atual.** Linux vem depois.
- Todo código específico de plataforma fica em `services/` atrás de interface.
  Se Win32 vazar para `core/` ou `ui/`, o port para Linux vira reescrita.

## Arquitetura: event log append-only

Esta é a decisão central do projeto. Não a contorne.

```sql
CREATE TABLE events (
  uuid        TEXT PRIMARY KEY,
  device_id   TEXT NOT NULL,
  occurred_at TEXT NOT NULL,   -- ISO8601 UTC
  kind        TEXT NOT NULL,
  payload     TEXT NOT NULL    -- JSON
);
CREATE INDEX idx_events_time ON events(occurred_at);
```

Regras invioláveis:

1. `events` é a **única** tabela persistida. Nada mais vai a disco.
2. Eventos são imutáveis. Só `INSERT`. Nunca `UPDATE`, nunca `DELETE`.
   Correção é um novo evento (ex.: `task.archived`), não uma edição.
3. Backlog, sessões, estante, planta e histórico são **projeções** calculadas
   em memória a partir do log, no startup e a cada novo evento.
4. Projeção é função pura: `events -> estado`. Idempotente e determinística.
5. Desbloqueios e recompensas **não** são eventos. Se virarem, perde-se a
   idempotência. Derive sempre do histórico.
6. `device_id` existe mesmo sem sync. Custa um campo e preserva a opção de
   merge futuro (que seria `INSERT OR IGNORE`, sem conflito).

### Kinds

```
task.created      {id, label, project?}
task.completed    {id}
task.archived     {id}
session.started   {id, task_id?}
session.ended     {id, interrupted: bool, note?}
idea.captured     {id, text}
idea.promoted     {id, task_id}
idea.archived     {id}
day.checkin       {date, intents: [str]}
day.review        {date, mood: int, energy: int, note?}
```

Novos kinds são aditivos. Nunca renomeie ou remova um kind existente.

## Regras de gamificação

- `foco_14d` = minutos de sessão concluída na janela móvel de 14 dias.
- Estágios da planta por `foco_14d`: 0h / 3h / 8h / 16h / 30h -> planta_0..4
- A janela móvel já produz o decaimento natural. **Não adicione penalidade
  explícita.** Some sozinho e volta rápido.
- Estante: 1 objeto por `task.completed`. Tipo escolhido por hash determinístico
  do uuid da tarefa, para o quarto ser sempre o mesmo. Objetos são permanentes.

## Camadas de UI

1. **Backlog leve** — sem projetos aninhados, sem prazos. Lista arrastável.
   "Hoje" limitado a 5 itens.
2. **Vitrine de entregas** — concluir uma tarefa coloca um objeto na estante.
   Esse é o feedback de progresso. Não existe outro.
3. **Mural de ideias** — atalho global, campo de texto, Enter, some. Zero
   categorização no momento da captura. Ideia aproveitada não sai do mural:
   fica riscada, com a data. Sai só o que for descartado à mão.
4. **Timer** — vinculado a um item do backlog. É o motor de tudo.
5. **Retrospectiva noturna** — montada automaticamente das sessões do dia. O
   usuário só confirma e adiciona humor/energia.
6. **Objetos de parede** — calendário do mês à esquerda, relógio analógico à
   direita, bilhete com a lista do dia embaixo dele. São cenário, não widget:
   ficam atrás da luz do abajur, em opacidade baixa, retos, e o único que
   responde a clique é o bilhete (abre a gaveta do "hoje"). O bilhete leva o
   tempo de cada tarefa e o total do dia.
7. **Menu do quarto** — luz, som, humor/energia e a saída do app. Não é gosto
   por menu: com "terminei" na barra, a fileira de botões passava da largura da
   janela, e esses são ajustes do ambiente, não ações do dia.

## Janelas

Uma `QQmlApplicationEngine`, dois `Window` QML ligados ao **mesmo** backend
Python exposto como context property. Sem IPC, sem estado duplicado.

- `Main.qml` — 1100x700, cena completa.
- `Mini.qml` — ~340x120, `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
  Qt.Tool`. Frameless exige drag manual via `DragHandler`.

As duas são a mesma coisa em dois tamanhos e **nunca ficam visíveis juntas**.
`setMainVisible(True)` esconde a mini e vice-versa; as duas escondidas é o app na
bandeja. Ter as duas na tela era dois relógios contando o mesmo tempo, com a
mini competindo com a janela que ela existe para substituir.

Minimizar a principal traz a mini no lugar. Ao reaparecer, `Main.qml` desfaz o
estado minimizado — sem isso a janela volta minimizada e "abrir" parece não ter
funcionado.

## Temas

Dois temas completos, mesma geometria de cena, só cores mudam.

Os ids internos são `noite` e `tarde` — são os nomes dos arquivos de cena e de
áudio, e não mudam. Na tela o tema claro se chama **dia**: a paleta foi
desenhada pensando em luz baixa de fim de tarde e o nome vazou do desenho para
a interface, mas quem abre o app às sete da manhã lê "fim de tarde" e o app
está errado sobre o próprio momento do dia.

O modo `auto` segue o expediente (`core/schedule.py`), não uma hora fixa: em dia
útil o quarto acende quando o turno começa e vira noite quando ele termina.
Fora de dia útil vale a regra do relógio, 6h às 18h.

**Noite** (abajur aceso, chuva na janela)
```
fundo #221D1A · superficie #2E2723 · borda #3D342E
texto #EDE0D0 · texto suave #A9968A
ambar #E0A458 · musgo #7A8B6F · terracota #C4704F
```

**Fim de tarde** (luz da janela, abajur apagado)
```
fundo #F2E8DA · superficie #FBF4E9 · borda #DCCBB6
texto #3A3129 · texto suave #7C6B5C
ambar #C77D2E · musgo #6E7F62 · terracota #B05F3F
```

Troca por relógio local, com padrão inicial vindo do `device_id` (trabalho abre
claro, casa abre escuro) e override manual. **Transição nunca é corte seco:**
crossfade de ~3s entre camadas de cenário + `ColorAnimation` nos painéis.

Cores vivem só em `ui/theme/Theme.qml`. Nenhum hex hardcoded em outro arquivo.

## Assets

`assets/scenes/cena_noite.svg` e `cena_tarde.svg` — viewBox 0 0 1100 700,
camadas em `<g>` de primeiro nível com ids idênticos nos dois arquivos:

```
parede, janela, chao, estante, mesa_esquerda, abajur,
mesa_direita, vaso, planta, objetos_estante
```

`assets/plant/planta_0.svg` a `planta_4.svg` — viewBox 0 0 200 260, vaso na
mesma posição e escala em todos.

SVG Tiny 1.2 apenas. Sem `<filter>`, sem `<foreignObject>`, sem CSS externo.
Qt não renderiza. Validar com `tools/check_svg.py`, que rasteriza em
`build/svg_check/` — `isValid()` sozinho mente.

### Coordenadas dentro do quarto

As camadas usam `PreserveAspectFit`, então o desenho é centralizado e sobra
faixa vazia no eixo mais folgado. Qualquer coisa posicionada à mão sobre a cena
**precisa somar essa folga**: `Room.qml` expõe `px(v)` para comprimento e
`cx(v)`/`cy(v)` para posição. Usar `px` onde deveria ser `cx` funciona em
1100x700, onde a folga é zero, e só quebra quando a janela é maximizada — que é
como a chuva e a poeira já saíram da cena uma vez.

### Efeitos que ficam em QML, não no SVG

- Luz do abajur: `RadialGradient` com `SequentialAnimation` de ±3% no raio (~6s)
- Chuva (noite): `QtQuick.Particles`
- Poeira no feixe (dia): `ParticleSystem`, partículas mínimas, deriva quase nula
- Folhas: `RotationAnimator` ±1,5°, fases dessincronizadas
- Grão: `ShaderEffect` de ruído, ~4% de opacidade, sobre tudo

## Estrutura

```
cantinho/
  assets/    scenes/ plant/ audio/ icon/     (gerados ou desenhados, versionados)
  docs/      quarto-noite.png quarto-tarde.png   (capturas do README)
  build/     saída de ferramenta e cache, nada versionado
  cantinho/
    main.py
    core/      events.py store.py projections.py clock.py
    services/  timer.py audio.py hotkey.py tray.py scene.py single_instance.py
    ui/        Main.qml Mini.qml theme/ room/ panels/
  tests/
  tools/     check_svg.py simular_uso.py semear.py gerar_{audio,icone,capturas}.py
```

`core/clock.py` é injetável. Sem isso, nada que dependa da janela de 14 dias é
testável.

### Divergências em relação ao desenho original

Todas deliberadas, todas com motivo:

- **`cantinho/backend.py`** não estava na estrutura. É a fronteira entre o log e
  o QML, o único objeto exposto como context property. Não cabia em `core/`
  (importa Qt) nem em `services/` (não é plataforma).
- **`cantinho/services/scene.py`** monta a cena camada a camada e serve as
  imagens ao QML. É o que permite planta e estante mudarem sem redesenhar o
  resto — e é a razão de os ids serem idênticos nos dois SVGs.
- **`QSystemTrayIcon` é QtWidgets**, e não existe equivalente em QtQuick. A
  exceção está confinada em `services/tray.py`, nenhum widget é mostrado, e é
  por causa dela que `main.py` usa `QApplication` e não `QGuiApplication`.
- **O grão é ruído ladrilhado, não `ShaderEffect`.** Shader no Qt6 precisa ser
  compilado para `.qsb` por ferramenta externa, o que seria uma etapa de build
  nova. O resultado na tela é o mesmo.
- **Kind novo `backlog.reordered {order: [id]}`.** A lista é arrastável e a
  ordem é decisão do usuário, não estado derivado. Aditivo, como a regra pede.
- **Tema `auto` decide pelo relógio local** (18h–6h é noite). O padrão vindo do
  `device_id` não foi implementado: o `device_id` é um uuid opaco, não sabe
  dizer se é trabalho ou casa. Como os dois ambientes são usados em horários
  diferentes, a regra do relógio já entrega o efeito descrito.
- **Sessão interrompida conta no `foco_14d`.** O tempo foi gasto, e zerá-lo
  seria a penalidade explícita que o decaimento da janela dispensa.
- **Uma instância por banco, não por máquina** (`services/single_instance.py`).
  Duas cópias sobre o mesmo log carregam as projeções separadas e divergem na
  tela. Travar por máquina proibiria abrir o app de teste com o de verdade na
  bandeja, que é o fluxo de quem mexe no projeto. A trava é um `QLocalServer`,
  que além de detectar serve de campainha: a segunda cópia avisa a primeira e
  sai, e a janela da primeira aparece.
- **O som tem três estados num controle só** (`SOUND_MODES`): `tudo`,
  `sussurro` — ambiente calado, reações de clique ativas — e `mudo`. O do meio
  existe porque as duas pontas não davam conta: quem está numa chamada não quer
  chuva tocando, mas continua querendo o retorno do clique. A preferência vive
  só na sessão: `events` é a única tabela persistida, e "liguei o som" não é
  fato do histórico.
- **`endSessionAndComplete` grava dois eventos, não um.** `session.ended` e
  `task.completed` continuam sendo fatos distintos no log; o que o botão
  "terminei" junta é o gesto. Antes eram dois movimentos em telas diferentes, e
  só o segundo punha o objeto na estante — ou seja, o retorno do app dependia
  de lembrar da metade que não estava à vista.
- **O bilhete mostra o tempo de cada tarefa.** Nasceu de layout (metade da folha
  ficava vazia) e resolveu uso: o tempo por tarefa só existia dentro da
  retrospectiva, no fim do dia. Continua sendo diário e não placar — minutos de
  hoje, sem meta, sem comparação com ontem, nada somando além da meia-noite.
- **Humor e energia também ficam no menu do quarto**, gravando na hora e
  preservando a nota existente. No painel do dia eles só apareciam depois de
  rolar a lista de sessões, o que na prática os deixava para as dez da noite.
- **`core/schedule.py` é o único módulo do core que trabalha em horário local.**
  Os demais são UTC, porque timestamp de evento não tem fuso. Expediente tem:
  ninguém trabalha "das 10h UTC". A jornada é constante e não configuração — é
  um app pessoal de uma pessoa com horário fixo, e um painel de preferências
  para editar isto seria mais código do que a informação que guarda.
- **O relógio de parede marca a próxima virada do turno**, não o fim dele.
  Saber que faltam duas horas para ir embora não ajuda às oito da manhã; saber
  onde termina o trecho em que se está, ajuda. É marca de bezel de relógio, não
  contagem regressiva: o olho lê a distância sem que apareça número nenhum.
- **Objetos de parede não têm inclinação.** A primeira versão pendurava tudo
  torto pela ideia de papel preso por um prego só; na tela leu como
  desalinhado, não como espontâneo. O prego ficou, a inclinação não.
- **Todo desenho de SVG passa por uma trava** (`_desenho`, em `services/scene.py`).
  `QQuickImageProvider` do tipo Image roda em thread de trabalho quando o
  `Image` do QML é assíncrono, e as camadas do quarto compartilham um
  `QSvgRenderer` em cache, que não é reentrante.

### Limites conhecidos do MVP

- A estante comporta **12 objetos** (duas prateleiras, seis cada). A projeção
  guarda todos para sempre; é o desenho que lota. Passar disso pede arte nova.
- Sessão é atribuída inteira ao instante em que terminou, sem teto. Timer
  esquecido a noite toda vira oito horas de foco.
- Atalho global só no Windows. No Linux `create_hotkey()` devolve um no-op.
- O som é sintetizado, não gravado, e é curto: 24 s em loop. Não tem melodia,
  é textura. Trocar por faixa de verdade é só pôr outro arquivo com o mesmo
  nome em `assets/audio/`.
- O bilhete da parede comporta **seis linhas** (`BOARD_LIMIT`). É a folha que
  limita, não a projeção: uma lista que rola na parede deixa de ser bilhete.
- Os objetos de parede vivem nas duas áreas que a arte deixou livres (acima da
  estante à esquerda, e a coluna à direita entre o teto e a folhagem do vaso).
  Mexer nos SVGs de cena pode invalidar essas posições.

### Ícone

O ícone não é arte nova: é o mesmo vaso da cena, renderizado por
`scene.render_icon()` a partir de `planta_N.svg`. Um relógio, um check ou uma
lista seriam a linguagem de produtividade que o projeto recusa na tela — não
faz sentido colocá-la na barra de tarefas.

Três decisões que não são arbitrárias:

- **O desenho muda com o tamanho.** De 32 px para cima é a planta sobre um
  ladrilho quente com a luz do abajur atrás — o cômodo reduzido a um quadrado.
  Abaixo disso o ladrilho sai e a planta ocupa o quadro: em 16 px o ladrilho
  engolia tudo e sobrava um vaso de quatro pixels. É para isso que `.ico` tem
  várias resoluções.
- **A moldura da planta é fixa**, então o vaso fica do mesmo tamanho em todos
  os estágios e só a folhagem cresce. Sem isso o ícone da bandeja pularia a
  cada mudança de estágio. Nos tamanhos pequenos a moldura começa mais embaixo
  (`ICON_FRAME_Y_SOLTO`), cortando as pontas esparsas para tudo crescer junto.
- **Só o da bandeja é vivo.** Ele acompanha `plant_stage`. O do executável e o
  da janela são fixos no estágio 2: identidade não pode mudar sozinha.

`escrever_ico()` monta o contêiner na mão porque o Qt não tem gravador de ICO.
São 16 bytes de diretório por quadro e um PNG por tamanho; há teste lendo o
arquivo byte a byte, porque `.ico` malformado só aparece na barra de tarefas
do usuário.

### Áudio

`assets/audio/ambiente_noite.wav`, `ambiente_tarde.wav` e os três `ui_*.wav`
(toque, clique, entrega) são gerados por `tools/gerar_audio.py` e versionados
prontos, para que um clone limpo já tenha som sem etapa extra de build.

O ambiente toca por `QMediaPlayer`; as reações de mouse por `QSoundEffect`, que
mantém o efeito decodificado em memória — o player de mídia leva dezenas de
milissegundos para começar, o que num retorno de clique é atraso audível. Em
compensação, `QSoundEffect` só aceita PCM sem compressão, e é isso que fixa o
formato dos `ui_*.wav`.

As reações têm rampa nas duas pontas e um intervalo mínimo entre disparos.
Sem a rampa, o começo e o fim do arquivo são degraus na saída de áudio — o
mesmo estalo da emenda do loop, do outro lado. Sem o intervalo, arrastar o
mouse pela barra dispara uma metralhadora de cliques.

A síntese é determinística (semente fixa), então regerar produz o mesmo arquivo
byte a byte — se o `git status` acusar mudança depois de rodar o gerador, foi o
código do gerador que mudou, não ruído aleatório.

Duas coisas seguram a qualidade do loop e têm teste: as frequências dos senos
são ajustadas para caber um número inteiro de ciclos na duração, e o fim do
arquivo é misturado por crossfade sobre o começo. Sem as duas, a volta do loop
estala — e num som que fica horas tocando isso é insuportável.

## Fases

| Fase | Entrega | |
|------|---------|---|
| F0 | Event store + timer + janela | feito |
| F1 | Mini window, tray, always-on-top | feito |
| F2 | Backlog e "Hoje" (máx. 5) | feito |
| F3 | Cena, planta, estante | feito |
| F4 | Retrospectiva, humor, inbox de ideias | feito |
| F5 | Áudio local, ambiente, ciclo dia/noite | feito |
| F6 | PyInstaller portable | feito, ~198 MB em `dist/Cantinho/` |
| F7 | Parede viva, mural, reação de mouse | feito |

Não pule fase. Não adiante arte. Se o modelo de eventos estiver errado,
descobrir na F3 custa caro.

## Convenções

- Português do Brasil em UI, commits e comentários. Código e identificadores em
  inglês.
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`).
- Type hints em todo o `core/`.
- `core/` não importa PySide6 exceto `QObject`/`Signal` na fronteira. Deve ser
  testável sem instanciar aplicação Qt.
- Timestamps sempre UTC no banco; conversão para local só na apresentação.
- Nada de `print()` em `cantinho/` — use `logging`. Scripts de `tools/` são CLI
  e podem imprimir.
- `.gitattributes` força `eol=lf` nos SVGs. Editar asset no Windows não deve
  trocar a quebra de linha.

## Não fazer

- Não adicionar dependências sem perguntar.
- Não persistir estado derivado.
- Não criar tabelas além de `events`.
- Não sugerir sync, nuvem, conta de usuário ou telemetria.
- Não usar QtWidgets nem QSS.
- Não introduzir streak, XP, ranking ou notificação de cobrança.
- Não mexer nos SVGs de `assets/` sem pedido explícito.
