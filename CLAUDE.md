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

python -m cantinho.main           # rodar o app
python -m pytest                  # suíte completa
python -m pytest tests/test_projections.py::test_foco_14d   # um teste só
python -m pytest -k foco -x       # por nome, parando no primeiro erro
python tools/check_svg.py         # validar SVGs -> build/svg_check/*.png
```

Linux (casa) é o mesmo com `source .venv/bin/activate`.

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

### Estado atual

O código ainda não começou. Existem só os SVGs de `assets/`,
`tools/check_svg.py` e os `__init__.py` vazios de `cantinho/`, `cantinho/core/`
e `cantinho/services/`. `tests/` está vazio, `cantinho/ui/` não existe.
`requirements.txt` tem apenas PySide6 — pytest ainda precisa entrar lá (e ser
instalado) antes do primeiro teste.

Ou seja: F0 é greenfield. O primeiro arquivo a existir deve ser `core/store.py`
+ `core/events.py`, com teste, antes de qualquer coisa de Qt.

## Fases

| Fase | Entrega |
|------|---------|
| F0 | Event store + timer + janela sem estilo. **Atual.** |
| F1 | Mini window, tray, always-on-top |
| F2 | Backlog e "Hoje" (máx. 5) |
| F3 | Cena, planta, estante |
| F4 | Retrospectiva, humor, inbox de ideias |
| F5 | Áudio local, ambiente, ciclo dia/noite |
| F6 | PyInstaller portable |

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
