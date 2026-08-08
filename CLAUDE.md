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

Sempre a partir da raiz do repositório. Não há `pyproject.toml`/`setup.py`: os
imports de `cantinho.*` e os caminhos relativos de `tools/` dependem do cwd.

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
python tools/gerar_audio.py       # regera assets/audio/*.wav
python tools/gerar_icone.py       # regera assets/icon/cantinho.{ico,png}
pyinstaller cantinho.spec --noconfirm   # portable em dist/Cantinho/
```

`tools/simular_uso.py` é o que cobre o QML — o pytest não cobre. Ele cria
tarefa, roda sessão, conclui, arrasta, captura ideia e fecha o dia clicando de
verdade; depois reabre o banco e confere o log evento por evento. Rode depois
de mexer em qualquer `.qml`. Passe uma pasta como argumento para guardar as
capturas de cada etapa.

Linux (casa) é o mesmo com `source .venv/bin/activate`.

`--db` e `--device-id` existem para teste: sem eles o banco vai para a pasta de
dados do sistema, e é fácil sujar o banco real ao experimentar.

Para rodar a suíte sem abrir janela: `$env:QT_QPA_PLATFORM="offscreen"`. Cuidado
que nesse modo o Qt fica **sem nenhuma família de fonte** — texto vira tofu em
screenshot. Para avaliar a UI de verdade, rode com a plataforma normal.

`tools/check_svg.py` varre `assets/**/*.svg`, rasteriza cada um e sai com código
1 se algum falhar. Não basta olhar o exit code: **abra os PNGs em
`build/svg_check/`**, porque um SVG com feature não suportada renderiza vazio ou
parcial sem que `isValid()` reclame.

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
3. **Inbox de ideias** — atalho global, campo de texto, Enter, some. Zero
   categorização no momento da captura.
4. **Timer** — vinculado a um item do backlog. É o motor de tudo.
5. **Retrospectiva noturna** — montada automaticamente das sessões do dia. O
   usuário só confirma e adiciona humor/energia.

## Janelas

Uma `QQmlApplicationEngine`, dois `Window` QML ligados ao **mesmo** backend
Python exposto como context property. Sem IPC, sem estado duplicado.

- `Main.qml` — 1100x700, cena completa.
- `Mini.qml` — ~320x120, `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
  Qt.Tool`. Frameless exige drag manual via `DragHandler`.

## Temas

Dois temas completos, mesma geometria de cena, só cores mudam.

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

### Efeitos que ficam em QML, não no SVG

- Luz do abajur: `RadialGradient` com `SequentialAnimation` de ±3% no raio (~6s)
- Chuva (noite): `QtQuick.Particles`
- Poeira no feixe (dia): `ParticleSystem`, partículas mínimas, deriva quase nula
- Folhas: `RotationAnimator` ±1,5°, fases dessincronizadas
- Grão: `ShaderEffect` de ruído, ~4% de opacidade, sobre tudo

## Estrutura

Estrutura-alvo (a maior parte ainda não existe — ver "Estado atual" abaixo):

```
cantinho/
  assets/scenes/  assets/plant/
  build/
  cantinho/
    main.py
    core/      events.py store.py projections.py clock.py
    services/  timer.py audio.py hotkey.py tray.py
    ui/        Main.qml Mini.qml theme/Theme.qml room/
  tests/
  tools/check_svg.py
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

### Limites conhecidos do MVP

- A estante comporta **12 objetos** (duas prateleiras, seis cada). A projeção
  guarda todos para sempre; é o desenho que lota. Passar disso pede arte nova.
- Sessão é atribuída inteira ao instante em que terminou, sem teto. Timer
  esquecido a noite toda vira oito horas de foco.
- Atalho global só no Windows. No Linux `create_hotkey()` devolve um no-op.
- O som é sintetizado, não gravado, e é curto: 24 s em loop. Não tem melodia,
  é textura. Trocar por faixa de verdade é só pôr outro arquivo com o mesmo
  nome em `assets/audio/`.

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

`assets/audio/ambiente_noite.wav` e `ambiente_tarde.wav` são gerados por
`tools/gerar_audio.py` e versionados prontos, para que um clone limpo já tenha
som sem etapa extra de build.

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
| F6 | PyInstaller portable | feito, ~207 MB em `dist/Cantinho/` |

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
