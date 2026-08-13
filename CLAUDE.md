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

Há um `pytest.ini`, e ele existe por uma linha só: `testpaths = tests`. Sem ela
o pytest coleta a partir da raiz e desce em `portatil/`, que carrega um Python
embeddable inteiro com o PySide6 dentro — a coleta morre lá antes de rodar um
teste sequer. O `norecursedirs` cobre quem passa caminho na mão. Ele **não** é o
`pyproject.toml` que não existe: não declara pacote nem mexe no `sys.path`, e
quem põe a raiz no `sys.path` continua sendo o `python -m` rodado da raiz.

No Windows há um atalho para tudo isto, e é o caminho de instalação da máquina
do trabalho — onde não há git, e o repositório chega como zip baixado à mão:

```bat
cantinho.bat                 :: menu, que é o que o duplo clique abre
cantinho.bat instalar        :: cria o venv e instala as dependências
cantinho.bat rodar           :: abre o app a partir do código
cantinho.bat empacotar       :: pyinstaller -> dist\Cantinho\
cantinho.bat atualizar       :: dependências + build com o cache limpo
cantinho.bat portatil        :: o zip que roda sobre o Python oficial
cantinho.bat testar          :: a suíte
cantinho.bat refazer         :: apaga o venv e começa de novo
cantinho.bat atalho          :: põe o Cantinho na Área de Trabalho
```

Ele é idempotente de propósito: o mesmo comando serve para instalar pela
primeira vez e para atualizar depois de sobrescrever os arquivos. `atualizar`
se distingue de `empacotar` por uma coisa só — apaga `build/cantinho` antes,
porque o cache de análise do PyInstaller é confiável quase sempre, e "quase"
é pouco quando os fontes foram trocados por baixo dele.

O `.bat` é **ASCII puro e CRLF**, e o `.gitattributes` tem exceção para isso.
O cmd.exe é o único leitor deste repositório que não aceita LF: com quebra de
linha do Unix ele erra em `goto` para rótulo no fim do arquivo e em bloco entre
parênteses, o que dá falha de sintaxe em script que parece certo — no sistema
onde ele é justamente o caminho de instalação.

Windows (PowerShell), venv em `.venv/`, para quem prefere na mão:

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
python tools/instalar_atalho.py   # atalho .desktop (Linux); --de-novo, --remover
python tools/atalho_windows.py    # atalho na Área de Trabalho (Windows); --remover
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
tarefa, escolhe o que vem agora, roda sessão, conclui, arrasta, corrige texto,
captura ideia, abre a semana e fecha o dia clicando de verdade; depois reabre o
banco e confere o log evento por evento. Rode depois de mexer em qualquer
`.qml`. Passe uma pasta como argumento para guardar as
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

No Windows a suíte dá **390 passados e 3 pulados**, e esse é o resultado certo,
não uma suíte incompleta. Os três são de `test_desktop_entry.py` e dependem de
semântica POSIX: barra `/` no `Exec=` e bit de execução no `.desktop`. A fixture
finge o `sys.platform`, mas o `pathlib` já escolheu `WindowsPath` na importação
e o `chmod` do Windows não tem bit para ligar — eles falhariam com o código
certo, que é o pior tipo de teste vermelho. No Ubuntu os 393 rodam.

**Não rode nada disto num terminal elevado.** Com token de administrador o
Windows põe `BUILTIN\Administradores` como dono de todo diretório criado, no
lugar do usuário; o pytest 9 endurece o próprio temp com ACL sem herança, onde o
acesso do usuário vem de "direitos do proprietário" — que deixou de ser você. O
sintoma chega atrasado, e é isso que o torna caro: a execução elevada passa, e a
**seguinte**, normal, é que morre. A suíte com `PermissionError: [WinError 5]`
na limpeza do temp, depois de todos os testes terem passado; e o `portatil` no
`shutil.rmtree` que refaz a pasta antes de montar o pacote. O `cantinho.bat`
avisa em toda ação. Se já aconteceu, apague a pasta envenenada — e se ela
resistir, `takeown /f <pasta> /r /d S` e `icacls <pasta> /reset /t`.

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

No Windows os dois saem por `cantinho.bat` (`empacotar` e `portatil`). São dois
empacotadores, para dois problemas diferentes.

- `cantinho.spec` (PyInstaller) → `dist/Cantinho/`, ~198 MB. É o build para a
  máquina onde se pode instalar o que quiser.
- `tools/empacotar_portatil.py` → `Cantinho-portatil-windows.zip`, ~235 MB
  descompactado. É o build para máquina restrita.

O segundo existe porque antivírus gerenciado por política apaga o executável do
PyInstaller, e nesse tipo de máquina não há como criar exceção. O bootloader do
PyInstaller é o mesmo binário em todo programa empacotado com ele, inclusive
nos maliciosos, e sem assinatura de editor não tem como se distinguir. Em vez
de tentar contornar o efeito, o empacotador portátil remove a causa: monta o
app sobre o `python.exe` oficial da PSF, que já vem assinado, e não constrói
binário nenhum. O pacote fica auditável — que é o argumento para pedir
liberação a quem administra, se ela for necessária.

A poda do Qt no portátil compara nomes **em minúsculas**. A primeira versão
comparava sensível a maiúsculas e deixou 83 MB de recurso do WebEngine para
trás, porque o Qt escreve `Qt6WebEngine` na DLL e `qtwebengine` no `.pak`.

Detalhes, instruções de instalação e o que fazer se mesmo assim for bloqueado:
`docs/windows.md`.

## Contexto de uso (restrições reais)

- **Windows**: máquina restrita, sem internet externa confiável. Roda portable,
  sem instalação e sem admin. Uso diurno.
- **Linux**: Ubuntu 22.04 (X11), uso noturno para doutorado e projetos paralelos.
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

1. `events` é a **única** tabela persistida. Nada mais vai a disco. Duas
   exceções, ambas arquivos ao lado do banco e nenhuma delas estado: o
   `device_id` e a marca de vida (`services/heartbeat.py`). Projeção continua
   sendo função pura de `events`; a marca só decide *qual evento escrever* na
   recuperação de queda, e é apagada assim que serve.
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
task.renamed      {id, label}
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

`task.renamed` é a exceção que confirma a regra 2: corrigir o texto de uma
tarefa não edita o `task.created`, que continua no log como foi escrito. Na
projeção ele é o único caso em que **o último evento vence** — renomear é
correção, e corrigir duas vezes tem que valer a segunda. O id não muda, então o
objeto que a tarefa deixa na estante continua sendo o mesmo desenho: ele vem do
hash do id, nunca do rótulo.

## Regras de gamificação

- `foco_14d` = minutos de sessão concluída na janela móvel de 14 dias.
- Estágios da planta por `foco_14d`: 0h / 3h / 8h / 16h / 30h -> planta_0..4
- A janela móvel já produz o decaimento natural. **Não adicione penalidade
  explícita.** Some sozinho e volta rápido.
- Estante: 1 objeto por `task.completed`. Tipo escolhido por hash determinístico
  do uuid da tarefa, para o quarto ser sempre o mesmo. Objetos são permanentes.
- A posição também é permanente: o objeto k fica no slot k, seis por prateleira,
  a de cima primeiro. Ver `shelf_slots`.
- `mood` e `energy` valem de 1 a 5 (`MOOD_SCALE`), e a faixa é do contrato de
  evento, não só do controle da tela.

## Camadas de UI

1. **Backlog leve** — sem projetos aninhados, sem prazos. Lista arrastável.
   "Hoje" limitado a 5 itens. Clique escolhe a tarefa do próximo "começar";
   duplo clique corrige o texto ali mesmo.
2. **Vitrine de entregas** — concluir uma tarefa coloca um objeto na estante.
   Esse é o feedback de progresso imediato.
3. **Mural de ideias** — atalho global, campo de texto, Enter, some. Zero
   categorização no momento da captura. Ideia aproveitada não sai do mural:
   fica riscada, com a data. Sai só o que for descartado à mão.
4. **Timer** — vinculado a um item do backlog. É o motor de tudo. A tarefa em
   foco é derivada do backlog e escolhida na barra; o botão nunca abre sessão
   sem dono por omissão.
5. **Retrospectiva noturna** — montada automaticamente das sessões do dia. O
   usuário só confirma e adiciona humor/energia. "Encerrar o dia" fecha junto a
   sessão que estiver correndo.
5b. **A semana** — as entregas dia a dia, com navegação para trás. É o retorno
   de médio prazo entre a estante (tudo, sem data) e o bilhete (hoje, some à
   meia-noite). Sem barra, sem percentual, sem comparação entre dias.
6. **Objetos de parede** — calendário do mês à esquerda, relógio analógico à
   direita, bilhete com a lista do dia embaixo dele. São cenário, não widget:
   ficam atrás da luz do abajur, em opacidade baixa, retos. Dois respondem a
   clique, cada um abrindo a sua leitura literal: o bilhete abre o "hoje", o
   calendário abre a semana. O relógio não abre nada. O bilhete leva o tempo de
   cada tarefa e o total do dia.
7. **Menu do quarto** — luz, som, movimento, humor/energia e a saída do app.
   Não é gosto por menu: com "entreguei" na barra, a fileira de botões passava
   da largura da janela, e esses são ajustes do ambiente, não ações do dia.

## Janelas

Uma `QQmlApplicationEngine`, dois `Window` QML ligados ao **mesmo** backend
Python exposto como context property. Sem IPC, sem estado duplicado.

- `Main.qml` — 1100x700, cena completa.
- `Mini.qml` — 300x112, `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
  Qt.Tool`. Frameless exige drag manual via `DragHandler`.

As duas são a mesma coisa em dois tamanhos e **nunca ficam visíveis juntas**.
`setMainVisible(True)` esconde a mini e vice-versa; as duas escondidas é o app na
bandeja. Ter as duas na tela era dois relógios contando o mesmo tempo, com a
mini competindo com a janela que ela existe para substituir.

**Minimizar minimiza, e só.** A versão anterior trocava a janela pela mini, com
o argumento de que o timer continuava visível num canto. Na prática o gesto
quer dizer "sai da frente agora", e o app respondia pondo outra janela na
frente — sempre por cima de tudo. Para chamar a mini existe o botão "mini". Ao
reaparecer, `Main.qml` desfaz o estado minimizado — sem isso a janela volta
minimizada e "abrir" pela bandeja parece não ter funcionado.

A mini é o app reduzido ao gesto: ver o relógio, trocar de tarefa, encerrar.
Três faixas empilhadas, e nenhuma sobrepondo a outra — antes o nome da tarefa
ocupava a largura inteira com os botões ancorados por cima, e uma tarefa de nome
comprido passava por baixo do botão. Ajuste não mora ali: o som tem duas
posições (`toggleMute`, que devolve o estado anterior), e o ciclo de três
estados, o tema e o humor ficam na janela grande.

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

Os cinco obedecem a `Theme.movimento` — ver o ajuste **o quarto → movimento**
nas divergências. Chuva e poeira **saem de cena** em vez de congelar: gota
parada no ar não é chuva discreta, é desenho com defeito. O grão continua na
tela, porque ele é textura de filme; o que para é o sorteio da semente.

A chuva pintada dentro de `cena_noite.svg` não é essas partículas e não some:
a janela continua sendo uma noite de chuva, ela só para de se mexer.

## Estrutura

```
cantinho/
  assets/       scenes/ plant/ audio/ icon/  (gerados ou desenhados, versionados)
  docs/         quarto-{noite,tarde}.png     (capturas do README)
                instalar-no-windows.md      (o passo a passo para leigos)
                windows.md linux.md desenvolvimento.md
  build/        saída de ferramenta e cache, nada versionado
  cantinho.bat  instalação e build no Windows (ASCII, CRLF)
  cantinho/
    main.py
    core/      events.py store.py projections.py clock.py schedule.py
    services/  timer.py audio.py hotkey.py tray.py scene.py single_instance.py
               graphics.py desktop_entry.py heartbeat.py
    ui/        Main.qml Mini.qml theme/ room/ panels/
  tests/
  tools/     check_svg.py simular_uso.py semear.py gerar_{audio,icone,capturas}.py
             instalar_atalho.py atalho_windows.py empacotar_portatil.py
```

Painéis: `Backlog`, `Retrospectiva`, `Semana`, `SeletorTarefa`, `Passeio` e os quatro
elementos de base (`Painel`, `BotaoSuave`, `CampoTexto`, `EscalaPontos`,
`LinhaMenu`).

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
  fato do histórico. **O padrão de abertura é `sussurro`**
  (`DEFAULT_SOUND_MODE`): o ambiente é a única coisa aqui que ocupa a sala sem
  ninguém ter pedido, e quem abre o app numa mesa compartilhada levaria chuva
  tocando até achar onde desligar. A música é escolha de quem quer companhia.
- **Os três fins de sessão têm nomes que não se confundem.** Eram "terminei" e
  "encerrar" lado a lado — a mesma palavra dita de dois jeitos, e ninguém sabia
  qual fechava a tarefa. Cada botão diz agora o que acontece com ela:
  `entreguei` (vai para a estante), `parar` (continua na lista) e
  `fui interrompido` (idem, marcado assim no diário). "Entreguei" é o verbo da
  estante, que é a vitrine de entregas.
- **A tarefa em foco** (`focusedTaskId`) é o que o botão "começar" pega. Antes
  ele abria sempre sessão livre: o tempo era gravado sem dono, o "entreguei" nem
  aparecia, e prender o timer a uma tarefa exigia mirar a palavra "começar"
  dentro da linha certa do painel "hoje" — um gesto escondido dentro de outro.
  O foco **não é estado persistido**: é derivado do backlog, vazio significa "a
  primeira do hoje", e sessão livre continua disponível como escolha explícita
  na lista do seletor. Se o app fechar, o foco volta a ser o topo da lista, que
  é o que a lista já diz.
- **"Encerrar o dia" fecha a sessão aberta junto.** O botão só gravava a
  revisão e deixava o relógio correndo; quem fechava o app em seguida perdia o
  tempo aberto, e quem esquecia o timer ligado voltava no dia seguinte com uma
  sessão de catorze horas — o limite conhecido do MVP aparecendo justamente
  onde havia um botão para evitá-lo.
- **O calendário da parede abre a semana.** Ele continua sem marcar os dias
  trabalhados — isso viraria mapa de assiduidade —, mas ganhou um clique, que é
  a leitura literal do objeto: um calendário de parede é onde se olha para saber
  onde a semana está. A folha inteira responde; nenhuma célula é clicável
  sozinha, porque escolher um dia seria seleção de data.
- **`o quarto → movimento` para os cinco laços contínuos.** A luz respirando,
  as folhas, a chuva, a poeira e o grão rodam para sempre — são o ambiente, e
  são também a única coisa do app que gasta máquina sem ninguém ter pedido
  nada. O grão sozinho repinta a janela inteira a cada 900 ms, a tarde toda,
  com o app parado. Desligar serve a dois casos que não se resolvem sozinhos:
  bateria na máquina do trabalho, e sossego para quem não quer movimento na
  visão periférica enquanto lê outra coisa. O ajuste **não** desliga a reação
  ao mouse (`Theme.reacao` continua valendo): botão que não responde ao toque
  não é quarto quieto, é app quebrado. Ele desliga, sim, o crossfade de tema —
  `Theme.transicao` vira 0 —, porque três segundos de gradiente atravessando a
  tela é exatamente o que quem pediu sossego não quer ver.
  É **o mais perto que dá de `prefers-reduced-motion`**: o Qt não expõe a
  preferência do sistema (`QStyleHints` só tem `useHoverEffects`), e ler o
  registro do Windows ou o gsetting do GNOME seria código de plataforma novo em
  `services/` para um app de um usuário só, que sabe se quer movimento.
- **O quarto acende em vez de aparecer** (`Room.aceso`). As cinco camadas são
  SVG rasterizado fora da thread da UI e levavam uns 300 ms entrando de estalo,
  uma a uma, sobre o fundo vazio — a única coisa do app que aparecia sem
  transição, e logo a tela inteira. A trava é de uma vez só: ligar a opacidade
  direto em `status` faria o quarto apagar e reacender a cada mudança de
  `larguraFonte`, ou seja, sempre que a janela muda de tamanho — e ali não há o
  que esconder, porque o Qt continua mostrando a imagem antiga enquanto
  rasteriza a nova.
- **`BotaoSuave.mostrando`, e não `visible`.** Botão de barra que some por
  `visible` é troca seca no controle mais usado do app: a cada sessão que
  começava, dois botões surgiam do nada e empurravam os vizinhos. A largura
  anda junto com a opacidade — sem ela o buraco continua lá quando o botão sai,
  e é a largura que faz o gesto ler como "o botão chegou" em vez de "algo
  apareceu por cima". A fileira de ações do backlog já fazia certo desde
  sempre; era a barra que destoava.
- **Os quatro painéis da gaveta se cruzam por opacidade.** Eram irmãos de uma
  `Column` alternando por `visible`, o que passava despercebido enquanto a
  gaveta só abria e fechava — e ficou evidente quando "o dia" e "a semana"
  viraram abas do mesmo painel: clicar de uma para a outra trocava a tela num
  quadro. Empilhados dentro de um `Item`, a `Column` deixa de decidir a altura
  deles, e é por isso que a conta dos 90 px mudou de lugar em vez de sumir.
- **A semana lista entregas, não minutos por dia.** Sete números em coluna são
  um gráfico de barras disfarçado, e comparar ontem com hoje é exatamente o que
  o projeto recusa. O único número é a soma no rodapé — a mesma conta que o
  bilhete da parede já faz para um dia. Somar não cobra; comparar cobraria.
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
- **`cantinho/services/desktop_entry.py` é a única coisa que escreve fora da
  pasta de dados.** Um `.desktop` em `~/.local/share/applications` mais o ícone
  em `icons/hicolor/256x256/apps` — só no Linux, no-op nos outros sistemas como
  em `hotkey.py`. A regra que sustenta o resto é **criar uma vez e nunca
  sobrescrever**: revalidar o `Exec=` a cada abertura sobreviveria a mover o
  repositório sozinho, mas daria a qualquer clone de teste o poder de roubar o
  atalho do menu apontando para si. Para mudar de ideia existe `--de-novo`.
  Execução com `--db` não cria atalho: é a flag de teste, e um atalho
  permanente apontando para banco descartável seria a pior herança de um
  experimento. **O `Exec=` não resolve o symlink do `sys.executable`** —
  `.venv/bin/python` aponta para o Python do sistema, sem PySide6, e seguir
  esse link produz um atalho que aparece na grade, abre e morre com
  `ModuleNotFoundError` sem terminal onde reclamar. Há teste para isso.
  Instalar e remover chamam **`update-desktop-database`** em melhor-esforço:
  sem isso o GNOME Shell segue servindo o atalho que tem em memória, e um
  `Exec=` corrigido em disco continua abrindo pela linha antiga — com
  `gtk-launch` funcionando, o que manda procurar o defeito onde ele não está.
- **`cantinho/services/graphics.py` limpa o ambiente antes de o Qt subir.** Com
  o `base` do Anaconda ativo, o `qt-main` do conda exporta
  `QT_XCB_GL_INTEGRATION=none` em todo shell, e o Qt Quick não sobe — o app
  morre logo depois de abrir. É o único módulo que mexe no `os.environ` de
  quem roda o app, e a licença para isso é estreita: `none` não tem leitura
  válida aqui, porque não existe modo degradado sem integração GL. `xcb_glx` e
  `xcb_egl` passam intactos, e a remoção sai no log. **Não importa PySide6**,
  de propósito: o Qt lê a variável ao construir a aplicação, então a limpeza
  tem de acontecer antes. Chamam `ensure_gl_integration()` o `main.py` e as
  duas ferramentas que sobem Qt Quick (`simular_uso.py`, `gerar_capturas.py`);
  `check_svg.py` e `gerar_icone.py` não precisam, porque só usam
  `QPainter`/`QImage`.
- **Sair guarda a sessão aberta**, e a ligação é no `aboutToQuit` da aplicação
  (`endOpenSession`), não em cada botão. Há três caminhos para fora — o menu do
  quarto, o menu da bandeja e fechar a última janela quando não há bandeja — e
  dois nunca passavam pelo backend: o `session.started` ficava órfão, e sessão
  sem fim não conta em projeção nenhuma. O tempo sumia inteiro numa saída
  normal. É a mesma decisão que `endDay` já tomava.
- **Nenhuma sessão fica aberta, nem depois de uma queda.** Falta de energia e
  processo morto não avisam ninguém, e o `session.started` órfão não conta em
  projeção nenhuma. Na abertura seguinte ele é fechado na **última marca de
  vida** (`services/heartbeat.py`), que é o último instante em que o app
  comprovadamente estava rodando — a única hora de término que não é chute.
  Fechar "agora" daria catorze horas de foco a uma máquina que passou a noite
  desligada; sem marca legível, a sessão fecha no próprio começo, porque zero
  minuto é uma perda honesta e o contrário não é. Vai como `interrupted`, que é
  o que aconteceu. O aviso na tela é informativo, não uma pergunta: o que havia
  para gravar já foi gravado, e o que sobra é decidir se você volta àquilo
  agora ("continuar isso" abre uma sessão nova, não retoma a velha).
- **Começar pelo "hoje" troca a janela grande pela mini.** Escolher a tarefa na
  lista é o último gesto antes de trabalhar; ficar com o quarto inteiro na
  frente depois disso obriga a fechá-lo à mão toda vez. O botão grande da barra
  **não** faz isso — lá o quarto já está à vista e a escolha foi feita na
  própria barra.
- **Sessão acima de `LONG_SESSION_MINUTES` (60) pergunta o que mais se fechou
  junto.** Uma hora raramente é uma coisa só: no meio dela chega o pedido
  urgente, resolve-se o e-mail que travava outra pessoa. Nada disso vira
  entrega, porque o gesto de registrar acontece no fim e a essa altura já se
  esqueceu. A pergunta aceita item da lista **e** texto livre
  (`addAndCompleteTask`, que grava `task.created` + `task.completed` no mesmo
  lote — criar para marcar em seguida faria a linha piscar no "hoje"). Não é
  cobrança, e a diferença está na direção: ela oferece crédito por trabalho já
  feito, e "só isso" fecha sem custo. Traz a janela grande de volta se preciso,
  porque quem começou pelo "hoje" está na mini.
- **`NUDGE_AFTER_MINUTES` (120), repetindo a cada 30.** Duas horas é mais do que
  qualquer sessão conduzida de propósito; daí para cima o caso comum é timer
  esquecido, e quem esqueceu não vai olhar o relógio sozinho. Insiste porque
  quem saiu da mesa às 19h50 não estava lá para ver o primeiro aviso. As frases
  (`NUDGES`) são observações do quarto, não avisos de sistema, e **nenhuma passa
  de 36 caracteres** — na mini o toque ocupa a faixa do nome da tarefa, em 300
  px, e elidir come justamente o fim, que é onde a frase diz alguma coisa. Há
  teste. Os botões do toque são a razão de ele existir: não é para informar, é
  para dar onde clicar.
- **Com as duas janelas escondidas, o toque sai pela bandeja** (`Tray.notify`,
  ligado em `main.py` e só nesse caso — com janela na tela quem mostra a frase é
  o QML, e notificar junto seria a mesma frase duas vezes). É a exceção ao "não
  introduzir notificação de cobrança", e ela se justifica pela direção: o aviso
  pede para **parar**, não para trabalhar, e app na bandeja com o relógio
  correndo é exatamente o retrato do timer esquecido — o estado onde não existe
  nenhuma superfície do app para pôr um aviso.
- **No Linux a notificação não passa pelo Qt.** `QSystemTrayIcon.showMessage`
  entrega a mensagem ao GNOME — ela entra na lista, o ponto acende ao lado do
  relógio — mas **não abre banner nenhum**. Medido nas duas pontas com a fila
  vazia. Como o aviso existe para alcançar quem não está olhando para o app,
  chegar só na lista é o mesmo que não chegar, então `Tray.notify` fala com
  `org.freedesktop.Notifications` por `gdbus`, em melhor-esforço, e só cai no
  caminho do Qt se isso falhar — que é o caminho certo no Windows, onde vira
  torrada da Central de Ações. Por `QtDBus` não dá: `Notify` pede `replaces_id`
  como uint32 e o PySide6 converte todo `int` para int32, sem como marcar o
  tipo. A dica `desktop-entry` põe a planta no balão e faz o clique ativar o
  atalho, que cai na trava de instância única e traz a janela para a frente.
- **O que depende da data se atualiza sozinho** (`_reavaliar_relogio`, de minuto
  em minuto, no mesmo timer que já reavaliava o tema). O app fica aberto a noite
  toda e a meia-noite não gera evento: o bilhete amanhecia com as tarefas de
  ontem riscadas e o diário dizia que o dia estava fechado. A planta anda no
  mesmo tick, porque a janela de 14 dias desliza a qualquer hora, não à
  meia-noite. Emite só quando algo mudou — um `stateChanged` por minuto
  reavaliaria a tela inteira a troco de nada. É por isso que `_hoje()` passou a
  vir do clock injetado: sem isso nada disso é testável.
- **`_registrar_lote` existe pelo estado final único, não por atomicidade.** O
  log é append-only justamente para que cada evento seja um fato independente, e
  um lote pela metade é um estado legítimo. O que ele evita é o quadro
  intermediário: "entreguei" reprojetava duas vezes, e havia um instante em que
  a sessão já tinha acabado e a tarefa ainda não estava na estante.
- **Slots fixos na estante.** A primeira versão repartia a largura da prateleira
  pelo número de objetos, para eles ficarem sempre espalhados de ponta a ponta.
  Bonito parado e errado em movimento: entregar não punha um objeto, punha e
  **recolocava todos** — de 10 para 11 a prateleira inteira dava um pulo, sem
  transição, no instante em que a atenção estava nela. Com o objeto k no slot k,
  a chegada pode ser um crossfade entre a estante de antes e a de agora: as duas
  imagens são idênticas em tudo que já estava lá, então só o objeto novo tem
  para onde ir. O preço é uma estante agrupada à esquerda quando há poucas
  coisas, que é o que acontece com uma estante de verdade.
- **Os quatro tempos vivem no `Theme.qml`**, pela mesma regra das cores:
  `reacao` (o mouse tocou), `gesto` (o usuário pediu), `chegada` (algo entrou no
  quarto) e `transicao` (o cômodo mudando de hora). Havia oito valores
  espalhados — 150, 160, 180, 200, 220, 240, 260, 300 — para três intenções,
  cada um escolhido no dia em que aquela animação foi escrita. Ninguém percebe
  a diferença entre 150 e 160; percebe quando dois painéis irmãos abrem em
  ritmos que não combinam. `gesto` e `chegada` **não** obedecem a `movimento`,
  como `reacao`: são consequência de um gesto, e o quarto quieto desliga o que
  se mexe sozinho.
- **O passeio da primeira abertura, guiado pela planta** (`ui/panels/Passeio.qml`).
  Nada neste app se anuncia: não há barra de menu, não há rótulo dizendo o que
  ele é, e a estante — a razão de tudo — parece decoração até alguém contar que
  não é. Sete balões contam o ciclo (escrever, começar, entregar, o quarto
  guardar) e param aí; o resto se descobre clicando. **Nenhuma flag de "já
  viu" vai a disco**: o sinal de primeira abertura já existe e é exato — o log
  está vazio. Guardar um booleano ao lado seria uma segunda fonte de verdade
  sobre a mesma pergunta. A consequência é deliberada: quem dispensa e fecha o
  app sem fazer nada vê o passeio de novo, porque de fato ainda não começou.
  Uma tarefa, uma ideia ou uma sessão o encerram para sempre, e **o quarto → o
  passeio** traz de volta. O rosto é `avatar/<estágio>` no provedor de cena —
  o mesmo desenho do ícone, num estágio fixo (2, como o ícone da janela):
  numa primeira abertura `plantStage` é 0, e a figura que apresenta o app não
  pode ser a versão mais murcha dele. Os balões ficam **ao lado** do que
  explicam e nunca por cima — a primeira versão tapava a estante com a frase
  que falava dela.
- **`tools/atalho_windows.py` é o irmão Windows do `.desktop`.** Mora em
  `tools/` e não em `services/` porque a diferença é *quando* cada um roda: o
  do Linux é criado pelo app na primeira abertura, e este é passo de
  instalação — só existe o que apontar depois que o executável saiu. `:construir`
  no `cantinho.bat` chama ele no fim, **ignorando o código de saída**: atalho
  que não deu certo é aviso, não build perdido. Vai por `powershell -Command` e
  não por arquivo `.ps1` porque máquina gerenciada costuma vir com a política
  de execução em `Restricted`, que bloqueia script em arquivo e deixa passar
  comando na linha. E pergunta ao Windows onde fica a Área de Trabalho em vez
  de montar `%USERPROFILE%\Desktop`: em português ela tem outro nome, e com
  OneDrive corporativo ela está redirecionada.
- **Todo desenho de SVG passa por uma trava** (`_desenho`, em `services/scene.py`).
  `QQuickImageProvider` do tipo Image roda em thread de trabalho quando o
  `Image` do QML é assíncrono, e as camadas do quarto compartilham um
  `QSvgRenderer` em cache, que não é reentrante.

### Limites conhecidos do MVP

- A estante comporta **12 objetos** (duas prateleiras, seis cada). A projeção
  guarda todos para sempre; é o desenho que lota. Passar disso pede arte nova.
- Sessão é atribuída inteira ao instante em que terminou, sem teto. Timer
  esquecido a noite toda vira oito horas de foco. "Encerrar o dia" reduz o caso
  comum, mas não é teto: quem não encerra continua exposto.
- Atalho global só no Windows, em `Ctrl+Shift+I` ("I" de ideia). No Linux
  `create_hotkey()` devolve um no-op.
- No Linux o PySide6 do PyPI traz o Qt mas não as bibliotecas de sistema que
  ele carrega em runtime. Numa Ubuntu 22.04 limpa falta pelo menos
  `libxcb-cursor0`, e o sintoma é o plugin `xcb` não carregar. A lista está no
  README; `QT_DEBUG_PLUGINS=1` diz qual está faltando.
- A bandeja no GNOME depende da extensão AppIndicator. Sem ela o ícone não
  aparece — e como fechar a janela não encerra o app, some o caminho de volta.
  Reabrir pelo terminal resolve: a trava de instância única mostra a janela que
  já existe em vez de subir uma segunda. O toque do quarto continua chegando
  nesse caso, porque ele vai por `gdbus` e não pelo ícone.
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
| F8 | Foco da sessão, correção de tarefa, a semana | feito |

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
