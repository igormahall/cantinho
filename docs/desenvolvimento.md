# Desenvolvimento

Tudo a partir da raiz do repositório, e **sempre com o Python do venv** — o
`python` do PATH não tem PySide6.

```bash
pip install -r requirements-dev.txt        # produção + pytest + ruff
```

**Duas categorias e mais nenhuma.** `requirements.txt` é produção — o que o app
carrega para rodar, e é o que a máquina restrita instala.
`requirements-dev.txt` é desenvolvimento, traz o de produção junto e é o comando
único de quem vai mexer no código. Havia um terceiro arquivo só com o ruff, e
ele existia porque o `requirements-dev.txt` era o que a instalação normal rodava:
cada pacote ali era risco no passo que precisa funcionar sem internet confiável.
Com produção separada, essa razão acabou.

No Windows a opção **3** (dev) do `cantinho.bat` embrulha o que está abaixo, já
com o Python certo — e o item da suíte pergunta antes se pode instalar esta
categoria, porque a instalação normal de propósito não a traz. No Linux é na
mão, com o venv ativado.

## Comandos

```bash
python -m cantinho.main                    # abre o app a partir do código
python -m cantinho.main --db ./teste.db --log DEBUG   # banco descartável

python -m pytest                           # a suíte
python -m pytest -k planta -x              # por nome, parando no primeiro erro
python -m ruff check cantinho tests tools  # estilo do Python
python tools/check_qml.py                  # qmllint com o import path certo

python tools/simular_uso.py --tema tarde   # percorre a UI clicando de verdade
python tools/simular_uso.py --tema noite
python tools/semear.py                     # banco de demonstração em build/
python tools/check_svg.py                  # rasteriza os SVGs em build/svg_check/
python tools/gerar_audio.py                # regera os sons
python tools/gerar_icone.py                # regera o ícone
python tools/gerar_capturas.py             # regera as imagens do README
python tools/empacotar_portatil.py         # pacote para máquina sem Python
```

Não há `pyproject.toml` nem `setup.py`, de propósito. Como o Python põe no
`sys.path` o diretório do *script* e não o diretório atual, cada ferramenta de
`tools/` que importa `cantinho.*` insere a raiz do repositório no `sys.path` por
conta própria. O `pytest.ini` só delimita a coleta: `testpaths = tests`, sem o
qual o pytest desce em `portatil/` — um Python embeddable inteiro com o PySide6
dentro, onde a coleta morre antes de rodar um teste sequer — e as duas marcas de
sistema, que a seção seguinte explica.

## A suíte

**A suíte escolhe o checklist do sistema em que está rodando.** No Windows: 472
passados, nenhum pulado. No Ubuntu: 475. A diferença são quatro testes de
semântica POSIX de verdade — barra `/` no `Exec=` e bit de execução no
`.desktop` —, que no Windows **não são coletados**. A fixture finge o
`sys.platform`, mas o `pathlib` já escolheu `WindowsPath` na importação e o
`chmod` do Windows não tem bit para ligar: lá eles falhariam com o código certo,
que é o pior tipo de teste vermelho.

Antes eles ficavam como pulados, e "3 pulados" no fim de toda execução é uma
pergunta que nunca tem resposta nova — quem lê sem o comentário ao lado conclui
que a suíte está incompleta. Agora ficam fora da coleta, e o cabeçalho conta o
que aconteceu:

```
checklist: posix — 475 testes dos 476 coletados; fora: 1 exclusivo de windows
```

Quem decide é `tests/checklist.py`, que é função pura e tem teste próprio; o
`conftest.py` só liga isso ao pytest. Um teste que só existe num sistema leva
`@pytest.mark.posix` ou `@pytest.mark.windows` — as duas marcas estão declaradas
no `pytest.ini`, e `--strict-markers` faz um nome inventado (`@pytest.mark.linux`)
parar a suíte na hora, em vez de virar um teste que roda em todo lugar sem
ninguém notar. Quase nada precisa de marca: o `core` não sabe onde está rodando,
e o que é de plataforma finge o `sys.platform` e é conferido nos dois sistemas de
dentro de um só.

Para rodar sem abrir janela, `QT_QPA_PLATFORM=offscreen`. Nesse modo o Qt fica
**sem nenhuma família de fonte** e texto vira tofu em screenshot — para avaliar
a UI de verdade, rode com a plataforma normal.

## Coisas que só se aprende errando

- **O `pytest` não cobre o QML.** Quem faz isso é o `simular_uso.py`: ele abre as
  janelas, cria tarefa, escolhe, roda sessão, conclui, arrasta, corrige texto,
  captura ideia, abre a semana, guarda a página e fecha o dia com mouse e teclado
  sintéticos; depois reabre o banco do zero e confere o log evento por evento.
  **Rode depois de mexer em qualquer `.qml`.**
- **Rode o `simular_uso.py` com a tela ligada.** Com o monitor apagado ou a
  sessão bloqueada, o Qt para de apresentar quadros e toda animação congela. O
  roteiro não acha os painéis e falha em cascata, como se a interface estivesse
  quebrada.
- **Rode os dois temas.** Sem `--tema` ele herda o modo `auto`, que decide pelo
  relógio — e como o desenvolvimento acontece à noite, na prática o tema claro
  nunca era exercitado. Não é diferença cosmética: são dois SVGs de cena, quatro
  camadas de estante e uma paleta com contraste próprio.
- **O `check_qml.py` existe pelo import path.** Sem `-I cantinho/ui` o `theme`
  não resolve, o `Theme` vira tipo desconhecido e o relatório enche de avisos que
  só existem porque a ferramenta foi mal chamada — 569 numa auditoria, contra 313
  com o caminho certo, e 2 defeitos de verdade depois de desligar a categoria que
  não se aplica. Ferramenta mal chamada não é rigorosa, é inútil.
- **Não basta o exit code do `check_svg.py`.** Abra os PNGs em
  `build/svg_check/`: um SVG com feature não suportada renderiza vazio ou parcial
  sem que o Qt reclame.
- **Áudio, ícone e capturas são versionados prontos**, e os geradores são
  determinísticos. Uma mudança no `git status` depois de rodá-los significa que o
  código mudou, não que o resultado variou.
- **`--db` e `--device-id` são de teste.** Sem eles o banco vai para a pasta de
  dados do sistema, e é fácil sujar o log real ao experimentar. `--db` expande
  `~` por conta própria: o PowerShell não expande til em argumento de executável
  nativo, e sem isso `--db ~/x/t.db` cria uma pasta chamada `~` e o app abre num
  banco vazio sem dar erro nenhum.
- **`tools/semear.py` recusa semear um banco que já tem eventos.** Os uuids são
  novos a cada execução, então o `INSERT OR IGNORE` não protege, e semear duas
  vezes empilha duas semanas sobre outras duas — a estante passa da lotação do
  desenho e a planta trava no estágio 4. `--de-novo` refaz, mas só se todo o log
  tiver saído da ferramenta.

## O que não tem teste automático

Dois comportamentos dependem do tempo real passando, e o roteiro de cada um está
registrado porque é a única forma de exercitá-los.

**Os limiares de sessão.** O `simular_uso.py` emite `nudged` e `extraAsked` na
mão, então o que fica sem exercício é o tique de um minuto decidindo sozinho.
Baixe `LONG_SESSION_MINUTES`, `NUDGE_AFTER_MINUTES` e `NUDGE_REPEAT_MINUTES` em
`backend.py` (1, 2 e 1 servem) e deixe o app aberto uns cinco minutos, com o laço
de eventos vivo. **Devolva as constantes quando terminar** — `git checkout
cantinho/backend.py`.

**A queda.** Abra uma sessão, espere alguns minutos e mate o processo pelo
Gerenciador de Tarefas ("Finalizar tarefa", que é `TerminateProcess`, o único
jeito de o `aboutToQuit` não rodar). Na reabertura o aviso traz os minutos até a
última marca de vida — medido, 3 min para 3,8 reais, que é a perda de até um
tique que o desenho aceita.

## Ruff

`ruff==0.16.3`, configurado em `ruff.toml`, e dentro de `requirements-dev.txt`
com o pytest: lint e teste são a mesma categoria de ferramenta, e quem instala
uma instala a outra. A falta dele continua sendo aviso e não erro — o item de
lint no menu pula a parte Python e roda o qmllint assim mesmo, que é o caso de
quem recusou a instalação das ferramentas.

O conjunto de regras é escolhido a dedo (`E4 E7 E9 E402 F B DTZ RUF100`) e
fixado em vez de herdado do padrão, que muda entre versões — e as duas máquinas
deste projeto não atualizam juntas. O critério de inclusão é um só: **lint que
reclama de código certo é lint que se aprende a ignorar.**

Duas coisas não óbvias:

- **`E402` é a regra que faz o resto funcionar.** Toda ferramenta de `tools/`
  importa `cantinho.*` depois de mexer no `sys.path`, com `# noqa: E402`. Com a
  regra desligada esses noqa não serviam para nada e o `RUF100` denunciava
  dezenove de uma vez.
- **`ruff format` não é usado, e não é esquecimento.** Reflui a base inteira, e o
  pior conflito deste projeto é um arquivo editado nas duas máquinas —
  reformatar tudo de uma vez é fabricar esse conflito.

## Duas máquinas, um repositório

O código sincroniza pelo GitHub; **os bancos de evento não sincronizam nunca** e
não estão no repositório. Antes de trocar de sistema, empurre o que está
pendente: o pior conflito aqui é um `.qml` editado nos dois lados.

```bash
git pull --rebase     # antes de começar
git push              # antes de desligar
```

O `.venv/` é por máquina e não é versionado, então depois de trocar de sistema ou
de puxar mudança em `requirements*.txt`, refaça o `pip install`. Ele é
idempotente — sem mudança, não faz nada.

Se o `git status` acusar o repositório inteiro como modificado sem diferença
real, foi a quebra de linha: o `.gitattributes` fixa LF para todo texto, e o
conserto é `git add --renormalize .`, não commitar o ruído. A exceção é o
`cantinho.bat`, que é **ASCII puro e CRLF** — o cmd.exe é o único leitor deste
repositório que não aceita LF.

---

## Por dentro

Só existe uma tabela, `events`, e ela só recebe `INSERT`. Backlog, sessões,
estante, planta, mural e histórico não são guardados: são recalculados a partir
do log toda vez, por funções puras. Corrigir alguma coisa é acrescentar um
evento novo — inclusive renomear uma tarefa, que é um `task.renamed` e não uma
edição do que já passou.

Isso significa que o estado da tela nunca pode divergir do que está em disco, e
que apagar o arquivo de banco é a única forma de perder alguma coisa. É também o
que dá o mural de graça: "essa ideia virou tarefa" não é um campo que muda, é um
evento posterior apontando para a tarefa que nasceu.

```
cantinho/
  core/       events.py store.py projections.py clock.py schedule.py export.py
              (sem Qt, testável sem instanciar aplicação)
  services/   scene.py timer.py audio.py hotkey.py tray.py graphics.py fonts.py
              single_instance.py desktop_entry.py heartbeat.py   (plataforma)
  backend.py  a fronteira entre o log e a interface
  ui/         Main.qml Mini.qml theme/ room/ panels/
```

O ícone é o próprio vaso do quarto, e na bandeja ele acompanha o crescimento da
planta. O som é sintetizado pela biblioteca padrão do Python, não gravado. Os
SVGs de cena têm camadas com os mesmos ids nos dois temas, o que deixa a planta e
a estante mudarem sem redesenhar o quarto.

---

- **[plataformas.md](plataformas.md)** — assinatura de binário, antivírus,
  bibliotecas de sistema, atalhos: o que é específico de Windows e de Linux.
- **[auditoria.md](auditoria.md)** — as direções que sobraram da auditoria de
  14/08/2026, algumas das quais não devem ser feitas.
- **[../CLAUDE.md](../CLAUDE.md)** — as regras de arquitetura em detalhe,
  incluindo o que deliberadamente não se faz aqui e por quê.
