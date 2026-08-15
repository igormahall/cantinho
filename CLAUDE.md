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
- Nenhum empacotador de binário: o app roda sobre o `python.exe` assinado da
  PSF, no venv aqui e no pacote portátil na máquina que não tem Python

Sem dependências além de PySide6, pytest e ruff sem discussão prévia.

### As duas categorias de dependência

**Produção e desenvolvimento, e mais nenhuma.** A pergunta que decide onde um
pacote entra é uma só: *o app carrega isto para rodar?*

| arquivo | categoria | o que tem | quem instala |
|---|---|---|---|
| `requirements.txt` | produção | PySide6 | `cantinho.bat instalar`, o pacote portátil, quem só usa o app |
| `requirements-dev.txt` | desenvolvimento | produção + pytest + ruff | quem mexe no código |

O de desenvolvimento faz `-r requirements.txt`, então na máquina de quem
desenvolve o comando continua sendo um só. Nenhum arquivo repete o que o outro
já declara.

O que essa divisão resolve é concreto: o passo de instalação da máquina do
trabalho — restrita, sem internet externa confiável, sem administrador — passou
a instalar **um** pacote. Cada dependência a mais ali é uma chance a mais de a
instalação falhar justamente onde ela mais importa, e nem o pytest nem o ruff
fazem o app rodar.

Havia um terceiro arquivo, `requirements-lint.txt`, só com o ruff, e ele existia
por uma razão que deixou de valer: enquanto `requirements-dev.txt` era o que a
instalação normal rodava, tirar o ruff de lá era a única forma de mantê-lo fora
da máquina restrita. Com produção separada, a máquina restrita não chega mais
nesse arquivo — e lint e teste voltam a ser a mesma categoria de ferramenta,
porque quem instala uma instala a outra.

Duas consequências no `cantinho.bat`:

- `instalar` e `atualizar` instalam **produção**. É a mudança de comportamento:
  antes traziam o pytest junto para toda máquina.
- A oficina pergunta antes de baixar as ferramentas, e só no item da suíte — o
  único que não roda sem elas. Rodar o app, simular a interface, semear e
  empacotar continuam funcionando sem nada instalado a mais; recusar volta ao
  menu, não derruba a oficina.

## Comandos

Sempre a partir da raiz do repositório, **e sempre com o Python do venv** — o
`python` do PATH é o do sistema e não tem PySide6.

Não há `pyproject.toml`/`setup.py`, de propósito. Como o Python põe no
`sys.path` o diretório do *script* e não o diretório atual, cada ferramenta de
`tools/` que importa `cantinho.*` insere a raiz do repositório no `sys.path`
por conta própria. Sem isso, `python tools/x.py` falha com
`ModuleNotFoundError: No module named 'cantinho'` mesmo rodando da raiz — que
é justamente o que estas instruções mandam fazer.

Há um `pytest.ini`, e o que ele faz é delimitar a coleta. `testpaths = tests`:
sem essa linha o pytest coleta a partir da raiz e desce em `portatil/`, que
carrega um Python embeddable inteiro com o PySide6 dentro — a coleta morre lá
antes de rodar um teste sequer. O `norecursedirs` cobre quem passa caminho na
mão, e as marcas `posix`/`windows` mais `--strict-markers` são o checklist do
sistema (ver **O checklist do sistema**). Ele **não** é o `pyproject.toml` que
não existe: não declara pacote nem mexe no `sys.path`, e quem põe a raiz no
`sys.path` continua sendo o `python -m` rodado da raiz.

No Windows há um atalho para tudo isto, e é o caminho de instalação das duas
máquinas — inclusive a do trabalho, onde não há git e o repositório chega como
zip baixado à mão:

```bat
cantinho.bat                 :: o menu, que é o que o duplo clique abre
cantinho.bat instalar        :: apaga o venv, refaz do zero e cria o atalho
cantinho.bat atualizar       :: fecha o app, atualiza as deps e refaz o atalho
cantinho.bat dev             :: a oficina: rodar, testar, lint, semear, portátil
cantinho.bat remover         :: desmonta, e pergunta pelo diário em separado
```

São **quatro verbos e mais nenhum**, e o arquivo é **só do Windows** — o roteiro
do Ubuntu vive no `README.md`, que é onde alguém de lá vai procurar. O que antes
era ação de primeiro nível (`rodar`, `testar`, `lint`, `portatil`, `empacotar`)
virou item da oficina, porque nada disso é passo de instalação — e o menu de
instalação é lido por quem não sabe qual das nove opções escolher.

`instalar` e `atualizar` **terminam com o app funcionando**: as duas fecham
chamando `tools/atalho_windows.py`, e não há segundo comando depois de nenhuma
delas. A diferença é só o ponto de partida — `instalar` apaga o `.venv` e
recomeça (é também o conserto para ambiente em estado duvidoso), `atualizar`
aproveita o que existe, oferece o `git pull --rebase` quando a pasta veio de
`git clone`, e **fecha o app se ele estiver aberto**, porque as DLLs do Qt
ficam em uso e o pip não consegue substituí-las.

O fechamento é por linha de comando e não por nome de processo — `pythonw.exe`
sozinho pegaria qualquer outro programa em Python aberto na máquina, e são dois
processos por app aberto (o lançador do venv e o Python de base que ele chama),
os dois com `cantinho.main` na linha. É `TerminateProcess`, então cai na mesma
rede da queda de energia: a sessão aberta é fechada na última marca de vida na
abertura seguinte.

**`remover` faz duas perguntas, e elas são separadas de propósito.** A primeira
tira o ambiente, as pastas de trabalho e o atalho — tudo refazível com a opção 1.
A segunda é o diário em `%APPDATA%\Cantinho`, e ela **exige que se escreva a
palavra `apagar`**: é a única coisa do projeto que não se refaz com nada, não há
cópia em lugar nenhum, e um `(s/N)` compartilhado com a primeira pergunta seria
pedir que a pressa apagasse anos de log. O atalho sai antes do venv, e por isso
`:remover_atalho` aceita qualquer Python do PATH como reserva — `atalho_windows`
não importa PySide6, então não precisa do venv que acabou de ir embora.

O `.bat` é **ASCII puro e CRLF**, e o `.gitattributes` tem exceção para isso.
O cmd.exe é o único leitor deste repositório que não aceita LF: com quebra de
linha do Unix ele erra em `goto` para rótulo no fim do arquivo e em bloco entre
parênteses, o que dá falha de sintaxe em script que parece certo — no sistema
onde ele é justamente o caminho de instalação.

Windows (PowerShell), venv em `.venv/`, para quem prefere na mão:

```powershell
.venv\Scripts\Activate.ps1        # ou prefixar tudo com .venv\Scripts\python.exe
pip install -r requirements.txt       # produção: só o que o app carrega
pip install -r requirements-dev.txt   # desenvolvimento: produção + pytest + ruff

python -m cantinho.main           # rodar o app
python -m cantinho.main --db .\teste.db --log DEBUG   # banco descartável
python -m pytest                  # suíte completa
python -m pytest tests/test_projections.py::test_planta_decai_ao_avancar_14_dias
python -m pytest -k planta -x     # por nome, parando no primeiro erro
python tools/check_svg.py         # validar SVGs -> build/svg_check/*.png
python tools/check_qml.py         # qmllint com o import path certo
python tools/simular_uso.py --tema tarde   # percorre a UI clicando de verdade
python tools/simular_uso.py --tema noite   # e de novo no outro tema
python tools/semear.py            # banco de demonstração em build/demo.db
python tools/semear.py --de-novo  # refaz um banco já semeado
python tools/gerar_audio.py       # regera assets/audio/*.wav
python tools/gerar_icone.py       # regera assets/icon/cantinho.{ico,png}
python tools/gerar_capturas.py    # regera docs/quarto-*.png do README
python tools/instalar_atalho.py   # atalho .desktop (Linux); --de-novo, --remover
python tools/atalho_windows.py    # atalho na Área de Trabalho (Windows); --remover
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
captura ideia, abre a semana, guarda a página, abre e usa a mini e fecha o dia
clicando de verdade; depois reabre o banco e confere o log evento por evento — e
abre a página escrita para conferir que ela traz o que foi entregue e nenhuma
palavra de desempenho. Rode depois de mexer em qualquer `.qml`. Passe uma pasta
como argumento para guardar as capturas de cada etapa.

No fim ele varre as mensagens do Qt atrás de erro de QML, e a lista do que
conta (`ERROS_DE_QML`) tem cinco marcas: `TypeError` e `is not defined` pegam
expressão quebrada; `Cannot anchor`, `Unable to assign` e `Binding loop` pegam
**montagem** quebrada. As três últimas entraram depois de uma delas passar
batido por uma execução inteira — uma âncora ilegal pôs um painel no topo da
janela, o Qt avisou, e o roteiro deu tudo certo porque só olhava `TypeError`.
Aviso que ninguém lê é aviso que não existe.

**Rode os dois temas.** Sem `--tema` ele herda o modo `auto`, que decide pelo
relógio — e como o desenvolvimento acontece à noite, na prática **o tema claro
nunca era exercitado**. Não é diferença cosmética: são dois SVGs de cena
distintos, quatro camadas de estante (duas listas × dois temas) e uma paleta com
contraste e opacidades próprios. Uma regressão que só aparecesse de dia passaria
batido indefinidamente. Com a pasta de capturas, cada tema grava com o nome
sufixado, para não sobrescrever o outro.

O que ele **não** cobre são os limiares de tempo: ele emite `nudged` e
`extraAsked` na mão, então o que fica sem exercício é justamente o tique de um
minuto decidindo sozinho. Para conferir isso é preciso baixar
`LONG_SESSION_MINUTES`, `NUDGE_AFTER_MINUTES` e `NUDGE_REPEAT_MINUTES` em
`backend.py` (1, 2 e 1 servem) e deixar o app aberto de verdade uns cinco
minutos — com o laço de eventos vivo, porque é dele que o tique depende. Testado
assim: o toque sai sozinho, repete, chega pela bandeja com as duas janelas
escondidas, e a pergunta do fim de sessão traz a janela grande de volta estando
só a mini na tela. **Devolva as constantes quando terminar** — `git checkout
cantinho/backend.py`. Como não há mais executável a gerar, o que ficaria com os
números de teste é o próprio código que o atalho abre.

A queda também não tem teste automático, e o roteiro é curto: abra uma sessão,
espere alguns minutos e mate o processo pelo Gerenciador de Tarefas ("Finalizar
tarefa", que é `TerminateProcess`, o único jeito de o `aboutToQuit` não rodar).
Na reabertura o aviso traz os minutos até a última marca de vida — medido, 3 min
para 3,8 reais, que é a perda de até um tique que o desenho aceita.

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

### O checklist do sistema

**A suíte descobre em que sistema está e coleta só o checklist dele.** No
Windows dá **550 passados e nenhum pulado**; no Ubuntu, 553. A diferença são
quatro testes de semântica POSIX de verdade — barra `/` no `Exec=` e bit de
execução no `.desktop` —, que no Windows não são coletados: a fixture finge o
`sys.platform`, mas o `pathlib` já escolheu `WindowsPath` na importação e o
`chmod` do Windows não tem bit para ligar, então lá eles falhariam com o código
certo, que é o pior tipo de teste vermelho.

Antes eles eram `skipif`, e a suíte do Windows terminava com "3 pulados" para
sempre. **Pulado é uma pergunta em aberto** — "isto deveria ter rodado?" — que
reaparece em toda execução e nunca tem resposta nova; quem lesse aquilo sem o
comentário ao lado concluiria que a suíte estava incompleta. Fora da coleta,
cada sistema termina com o seu checklist inteiro e nada pendurado, e o cabeçalho
reconcilia os números:

```
checklist: posix — 553 testes dos 554 coletados; fora: 1 exclusivo de windows
```

As peças:

- **`tests/checklist.py`** — a decisão, em função pura, com teste próprio
  (`test_checklist.py`). Ela lê `os.name` e **não** `sys.platform`, de
  propósito: `sys.platform` é justamente o que meia dúzia de testes finge com
  `monkeypatch`, e a coleta acontece antes de qualquer fixture — ler dali faria
  um teste mudar o checklist da suíte inteira.
- **`tests/conftest.py`** — o encanamento: filtra em `pytest_collection_modifyitems`
  e escreve a linha do cabeçalho. Não chama o hook de "deselected", porque estes
  testes não foram descartados por escolha de quem rodou; no sistema errado eles
  não existem.
- **`@pytest.mark.posix` / `@pytest.mark.windows`** — as duas marcas, declaradas
  no `pytest.ini`. Quase nada precisa de uma: o `core` não sabe onde está
  rodando, e o que é de plataforma finge o `sys.platform` e é conferido nas duas
  pontas de dentro de um sistema só. A marca é para o que **não** dá para fingir.
- **`--strict-markers`** no `pytest.ini`, e ele é o que segura o resto: sem isso
  um `@pytest.mark.linux` distraído viraria um teste rodando em todo lugar sem
  ninguém notar, que é o mesmo defeito silencioso que a filtragem existe para
  evitar.

Há um teste exclusivo de Windows em `test_checklist.py` e ele existe para isto:
a filtragem tem duas direções, e a direção que ninguém exercita é a que apodrece.

### O banco de provas das projeções

**`tests/projecoes.py` é o registro de todas as projeções públicas**, cada uma
reduzida a `eventos -> resultado`, mais um log de prova que passa por todos os
kinds. Não é utilitário de conveniência: é o que faz as propriedades do
`CLAUDE.md` valerem para o módulo inteiro em vez de para uma amostra.

O problema que ele resolve é o de listas escritas à mão. As propriedades que
valem para toda projeção — log vazio não quebra, a entrada não é consumida, a
ordem de chegada não importa, o `device_id` não é olhado, o lote repetido não
muda nada — estavam conferidas cada uma sobre a sua própria seleção: seis
projeções aqui, cinco ali, duas acolá, de treze. **O cadeado do merge, que este
documento descreve como "nenhuma projeção olha o `device_id`", provava isso de
cinco.** As outras oito não estavam certas nem erradas: estavam sem cadeado.

Agora cada propriedade roda sobre as treze, e
`test_o_registro_cobre_toda_projecao_publica` sai de `projections.__all__` e
falha enquanto uma projeção nova não for registrada. Quem escreve uma projeção
nova ganha as seis provas de graça e é avisado se esquecer.

Duas peças completam o mesmo raciocínio para o resto da suíte:

- **`tests/imagens.py`** mede uma imagem numa passada, com operações de bytes.
  A varredura anterior era `pixelColor` em laço aninhado, repetida em seis
  testes, e pulava pixels para caber no tempo — **e uma delas media a coisa
  errada por causa disso**: procurava o pé do vaso no ícone de 128 px, onde o
  ladrilho opaco ocupa o quadro inteiro, então a resposta era a borda da imagem
  para todos os estágios e o teste passaria com o vaso andando meio quadro.
- **A superfície do backend** (`test_backend.py`) é varrida pelo
  `staticMetaObject`: as 52 propriedades que o QML lê são lidas todas, no log
  vazio e depois de um dia de uso. Uma que estourasse na primeira abertura não
  daria teste vermelho — daria um app que não abre.

**Não rode nada disto num terminal elevado.** Com token de administrador o
Windows põe `BUILTIN\Administradores` como dono de todo diretório criado, no
lugar do usuário; o pytest 9 endurece o próprio temp com ACL sem herança, onde o
acesso do usuário vem de "direitos do proprietário" — que deixou de ser você. O
sintoma chega atrasado, e é isso que o torna caro: a execução elevada passa, e a
**seguinte**, normal, é que morre. A suíte com `PermissionError: [WinError 5]`
na limpeza do temp, depois de todos os testes terem passado; e o `portatil` no
`shutil.rmtree` que refaz a pasta antes de montar o pacote. O `cantinho.bat`
avisa em toda ação. Se já aconteceu, apague a pasta envenenada — e se ela
resistir, devolva o dono e refaça as permissões:

```powershell
icacls "<pasta>" /setowner "$env:COMPUTERNAME\$env:USERNAME" /t /c /q
icacls "<pasta>" /reset /t
```

**Não use `takeown /f <pasta> /r /d S` neste Windows.** A letra de confirmação
do `/d` é traduzida, e em português ele responde
`O valor 'S' não é permitido para a opção '/d'` — trocar por `/d N` também não
serve, porque aí a resposta é "não". O `icacls /setowner` faz a mesma coisa sem
depender do idioma.

`tools/gerar_capturas.py` semeia um banco temporário e fotografa os dois temas
em `docs/`. As imagens do README são versionadas, e capturar à mão significa
que elas envelhecem em silêncio — a primeira leva delas ficou mostrando um
quarto sem calendário, sem relógio e sem bilhete.

Ele **grava sempre em 1100x700**, e a redução é obrigatória: `grabWindow()`
devolve pixels físicos, então numa tela a 225% ele entrega 2475x1575 onde a
janela mede 1100x700. Como as imagens são versionadas, o mesmo código produzia
arquivos diferentes em cada máquina — 948 KB no Ubuntu a 100%, 2,3 MB no
Windows a 225% — e rodar o gerador virava um diff de dois megabytes que ninguém
pediu, do lado de quem tem a tela melhor. É a mesma doença que o
`.gitattributes` cura nas quebras de linha e que a semente fixa cura no gerador
de áudio: **artefato versionado tem que ser função só do código.**

`tools/check_svg.py` varre `assets/**/*.svg`, rasteriza cada um e sai com código
1 se algum falhar. Não basta olhar o exit code: **abra os PNGs em
`build/svg_check/`**, porque um SVG com feature não suportada renderiza vazio ou
parcial sem que `isValid()` reclame.

`tools/check_qml.py` roda o `qmllint` sobre `cantinho/ui/`. Ele existe pelo
import path, e isso não é detalhe: **sem `-I cantinho/ui` o `theme` não resolve**,
o `Theme` vira tipo desconhecido e o relatório enche de "Unqualified access" que
só existem porque a ferramenta foi mal chamada. Uma auditoria deste projeto
reportou 569 avisos assim; com o caminho certo eram 313, todos do `backend`, que
é context property e o `qmllint` nunca vai conhecer — não tem tipo declarado em
lugar nenhum, por construção. Chamar errado não deixa a análise rigorosa, deixa
ela inútil.

O `.qmllint.ini` desliga `UnqualifiedAccess` e `ContextProperties` por essa
razão, e é isso que faz sobrar sinal: depois de desligadas restaram **2** avisos,
e os 2 eram defeito de verdade — `Passeio.qml` chamava `cx`/`cy` numa
`property Item`, e `Item` não tem nenhum dos dois. A correção foi tipar como
`Room`, que é de quem os métodos são.

O preço de desligar é conhecido: erro de digitação em nome de propriedade do
backend não é pego aqui. Quem pega é `tools/simular_uso.py`. Acabar com o preço
exigiria expor o backend como singleton QML em vez de context property — mexeria
nos 18 arquivos `.qml`, e em troca o `qmlcachegen` passaria a compilar os
bindings em vez de interpretá-los. A decisão não foi tomada.

Os dois se completam e nenhum substitui o outro: `check_qml.py` é estático e
pega propriedade que não existe no tipo, `simular_uso.py` clica de verdade e
pega comportamento.

`docs/auditoria.md` é o que sobrou da auditoria de 14/08/2026: **as direções**,
que não são pendências e algumas das quais não devem ser feitas. Os achados de
bug, de usabilidade e o plano estético saíram de lá quando foram implementados —
o raciocínio de cada um foi para onde ele serve, que é junto do código que o
tomou, aqui e nos comentários. O que um arquivo separado guarda bem é decisão
sobre o futuro; o porquê de uma linha de código envelhece longe dela.

### Ruff

`ruff==0.16.3`, configurado em `ruff.toml`, e em `requirements-dev.txt` junto
com o pytest — ver **As duas categorias de dependência**. Lint e teste são a
mesma categoria de ferramenta: quem instala uma instala a outra, e a máquina que
só roda o app não instala nenhuma das duas. A falta dele continua sendo aviso e
não erro — o item de lint no menu de dev pula a parte Python e roda o qmllint
assim mesmo, que é o caso de quem recusou a instalação das ferramentas.

```powershell
pip install -r requirements-dev.txt
python -m ruff check cantinho tests tools
```

O conjunto de regras é escolhido a dedo (`E4 E7 E9 E402 F B DTZ RUF100`) e
fixado em vez de herdado do padrão do ruff, que muda entre versões — e as duas
máquinas deste projeto não atualizam juntas. O critério de inclusão é um só:
**lint que reclama de código certo é lint que se aprende a ignorar.** Cada
família ligada pega defeito; as de fora saíram porque reclamavam de decisões
deliberadas — a ordem dos `__all__` segue o ciclo de vida do domínio e não o
alfabeto, `int(mood)` é a fronteira do número vindo do QML, os
`subprocess.run` sem `check` são melhor-esforço de propósito.

Duas coisas não óbvias:

- **`E402` é a regra que faz o resto funcionar.** Toda ferramenta de `tools/`
  importa `cantinho.*` depois de mexer no `sys.path`, e cada uma vinha marcada
  com `# noqa: E402`. Com a regra desligada esses noqa não serviam para nada, e
  o `RUF100` denunciava dezenove de uma vez. Ligada, cada um volta a significar
  o que significa. O ruff, aliás, **tolera `sys.path.insert` antes de import
  sozinho** — o que dispara E402 mesmo é chamada de função antes do import, que
  é o caso do `ensure_gl_integration()` em `simular_uso.py`.
- **`ruff format` não é usado, e não é esquecimento.** Reflui a base inteira, e
  o pior conflito deste projeto é um arquivo editado nas duas máquinas —
  reformatar tudo de uma vez é fabricar esse conflito. Está desligado no
  `ruff.toml` com o motivo escrito.

A primeira passada achou 64 avisos e sobraram 20 depois do conjunto escolhido.
Desses, os que eram defeito de verdade: `not x is None` em `simular_uso.py`,
dois `zip()` sem `strict=` sobre listas que têm o mesmo tamanho por construção
(um deles em `services/scene.py`, na estante), e um
`pytest.raises(Exception)` que aceitaria `AttributeError` por nome de campo
errado como se fosse a prova de imutabilidade.

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

**No Windows não se constrói binário.** Nem para desenvolver, nem para
instalar. O que o atalho da Área de Trabalho abre é
`.venv\Scripts\pythonw.exe -m cantinho.main`, e o `pythonw.exe` do venv é cópia
do binário oficial da PSF, com a assinatura dela intacta
(`Get-AuthenticodeSignature` responde `Valid`, `CN=Python Software
Foundation`).

Isto foi uma correção, não um desenho de origem, e a causa merece ficar escrita
porque ela vai voltar: o `Cantinho.exe` do PyInstaller **não abre nesta
máquina**. O **Smart App Control** do Windows 11 recusa carregá-lo —
`VerifiedAndReputablePolicyState` = 1 em
`HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy`, e os eventos 3033 e 3077 em
`Microsoft-Windows-CodeIntegrity/Operational` nomeando o arquivo, disparados
pelo `explorer.exe`, ou seja, pelo duplo clique. O sintoma engana e é isso que
custa caro: o arquivo continua em `dist/`, o duplo clique não diz nada, e a
conclusão natural é defeito do build — então se rebuilda, e o binário novo
nasce igualmente sem assinatura e sem reputação. Nenhuma quantidade de rebuild
resolve.

A mesma causa, em outra roupa, é o antivírus gerenciado da máquina do trabalho
apagando o executável: o bootloader do PyInstaller é o mesmo binário em todo
programa empacotado com ele, inclusive nos maliciosos, e sem assinatura de
editor não tem como se distinguir. Nos dois casos a saída não é contornar o
efeito — é **remover a causa**, não produzindo binário nenhum.

Sobra um empacotador, e ele tem um caso de uso só:

- `tools/empacotar_portatil.py` → `Cantinho-portatil-windows.zip`, ~235 MB
  descompactado. É para levar o app a uma máquina **que não tem Python** e onde
  não se pode instalar. Ele baixa o embeddable oficial do python.org e monta o
  app sobre ele — a mesma estratégia do atalho, com o runtime vindo de fora em
  vez de já estar no venv. O pacote fica auditável, que é o argumento para
  pedir liberação a quem administra, se ela for necessária.

A poda do Qt no portátil compara nomes **em minúsculas**. A primeira versão
comparava sensível a maiúsculas e deixou 83 MB de recurso do WebEngine para
trás, porque o Qt escreve `Qt6WebEngine` na DLL e `qtwebengine` no `.pak`.

**O `cantinho.spec` e o `pyinstaller` saíram do repositório em 14/08/2026**, e a
remoção é parte da correção, não faxina. Um caminho de build documentado como
"não funciona nesta máquina" é convite a tentar de novo — e cada tentativa custa
o mesmo diagnóstico caro, porque o sintoma não diz nada. Além disso o
`pyinstaller` puxava cinco pacotes (`altgraph`, `pefile`,
`pyinstaller-hooks-contrib`, `pywin32-ctypes`, `setuptools`) para dentro das
dependências, e nada no repositório o chamava.

Quem segura a regressão é `tests/test_atalho_windows.py`: ele exige que o atalho
aponte para um `pythonw.exe` e **proíbe `Cantinho.exe`** no script gerado.

Detalhes, o roteiro de diagnóstico e o que fazer se mesmo assim for bloqueado:
`docs/plataformas.md`.

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

   **A opção tem cadeado** (`tests/test_merge.py`). Sync continua proibido e não
   deve ser implementado; o que os testes garantem é que a porta não se feche
   sozinha. Opção preservada por acidente é opção que se perde por acidente:
   bastaria uma projeção passar a filtrar por `device_id`, ou a ordem do log
   passar a depender de quem escreveu, e ela sumiria sem ninguém perceber — para
   se descobrir no dia em que alguém precisasse dela, que é o pior dia possível.

   O cadeado prova quatro coisas: que juntar dois logs é **comutativo** (a ordem
   do encontro não muda o resultado, então não há conflito a resolver), que é
   **idempotente**, que **nenhuma projeção olha o `device_id`** — trocar o
   dispositivo de todo evento não pode mudar nada na tela —, e que o desempate
   do log é por uuid e não por dispositivo.

   As três primeiras comparam o **estado inteiro**, e não uma amostra dele: a
   comparação passa pelo banco de provas (`tests/projecoes.py`), que chama todas
   as projeções públicas de uma vez. Antes eram cinco escolhidas à mão, de
   treze — ver **O banco de provas das projeções**.

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

### Limites de texto, e por que eles só valem na construção

Todo campo de texto livre tem teto: `LABEL_LIMIT` (200) para rótulo, projeto e
intenção do dia; `TEXT_LIMIT` (4000) para ideia e nota. Por cima dos dois há
`PAYLOAD_LIMIT` (64 000 bytes no JSON serializado), que é rede para o que os
limites por campo não cobrem — uma lista que cresceu, um kind futuro que
ninguém lembrou de limitar.

Existem porque o log não tem `UPDATE` nem `DELETE`: o e-mail inteiro colado por
engano no campo de ideia fica no banco para sempre, é relido em toda abertura e
reprojetado a cada evento. É a imutabilidade que torna o limite barato agora e
impossível depois.

**A regra que sustenta tudo isto: o limite vale na construção, nunca na
leitura.** `check_limits` é chamado de `make_event`, e de propósito não está
dentro de `validate_payload` — aquela roda também em `Event.from_row`, então um
limite novo lá tornaria ilegível todo evento antigo acima dele, e um banco que
abria ontem pararia de abrir hoje. Há teste para isso.

São três camadas, e cada uma existe por um motivo diferente:

1. `CampoTexto.limite` (`maximumLength`) — a tela para de aceitar. Silenciosa:
   sem diálogo, sem aviso, o campo só não cresce. É o caminho normal, e nele
   nada é cortado nem recusado.
2. `_texto()` em `backend.py` — corta antes de montar o evento. É o que garante
   que um slot nunca levante exceção: exceção em slot morre dentro do laço de
   eventos do Qt, e perder o app por ter colado texto grande é pior do que
   perder o excedente do texto.
3. `check_limits` em `core/events.py` — a garantia do contrato, para quem não
   passa por tela nenhuma (`tools/`, atalho global, código futuro).

Um caso não é texto e por isso escapa das duas primeiras: **limitar cada item de
uma lista não limita a lista.** Com itens no tamanho máximo, algumas centenas
deles passam do `PAYLOAD_LIMIT` — e aí o evento se recusa a nascer dentro de um
slot, que é onde exceção derruba o app. Daí `CHECKIN_LIMIT` (50) em
`backend.py`, cortando `day.checkin` na mesma divisão de trabalho. O outro kind
de lista, `backlog.reordered`, não é cortado de propósito: são uuids que o app
gera do próprio backlog, e caberiam cerca de mil e seiscentos antes de o teto
chegar perto. Cortar ali seria perder ordem de tarefa real para prevenir o que
não acontece.

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

   **As últimas três soltas ficam pregadas na parede** (`WALL_IDEAS_LIMIT`,
   `ui/room/MuralDeParede.qml`). Era a única das cinco camadas sem corpo no
   quarto: o calendário abre a semana, o bilhete abre o dia, a estante guarda o
   entregue, a planta guarda o foco — e as ideias existiam só como uma palavra
   na barra. Cada uma é o seu papelzinho, com o seu prego, na largura que o
   texto pediu; um bilhete grande repetiria o desenho da folha da direita. Com
   o mural vazio **não há objeto nenhum**, e isso dá de graça o retorno que
   faltava à captura: o papel aparecer é a confirmação de que a ideia foi
   guardada. As aproveitadas não vão para a parede — na parede, papel resolvido
   é papel que se tira.
4. **Timer** — vinculado a um item do backlog. É o motor de tudo. A tarefa em
   foco é derivada do backlog e escolhida na barra; o botão nunca abre sessão
   sem dono por omissão.
5. **Retrospectiva noturna** — montada automaticamente das sessões do dia. O
   usuário só confirma e adiciona humor/energia. "Encerrar o dia" fecha junto a
   sessão que estiver correndo.
5b. **A semana** — as entregas dia a dia, com navegação para trás. É o retorno
   de médio prazo entre a estante (tudo, sem data) e o bilhete (hoje, some à
   meia-noite). Sem barra, sem percentual, sem comparação entre dias. Para
   horizonte mais longo que isso, o rodapé oferece **a página** — ver abaixo.
6. **Objetos de parede** — calendário do mês à esquerda com o mural de ideias
   embaixo dele, relógio analógico à direita com o bilhete do dia embaixo. São
   cenário, não widget: ficam atrás da luz do abajur, em opacidade baixa,
   retos. Três respondem a clique, cada um abrindo a sua leitura literal: o
   bilhete abre o "hoje", o calendário abre a semana, os papeizinhos abrem o
   mural. O relógio não abre nada — não há painel que seja "as horas". O
   bilhete leva o tempo de cada tarefa e o total do dia.

   **A escrita acende junto com o papel** (`FolhaDeParede.lido`). Por muito
   tempo só o fundo e a borda reagiam ao mouse e os textos tinham opacidade
   fixa: o papel acendia e o que estava escrito nele continuava igual, o que
   entrega metade do ganho de leitura. À noite é onde mais falta — a parede é
   escura, a vinheta puxa os cantos, e estes são os objetos do cenário que
   carregam informação. Em repouso nada muda; quem chega com o mouse chegou
   para ler.
7. **Menu do quarto** — luz, som, movimento, humor/energia, a página e a
   saída do app.
   Não é gosto por menu: com "entreguei" na barra, a fileira de botões passava
   da largura da janela, e esses são ajustes do ambiente, não ações do dia.

## A página, e a regra que ela carrega

`core/export.py` transforma o log em Markdown: a estante, o diário dia a dia e
o mural. Função pura, `events -> str`, sem I/O e sem Qt — quem escreve em disco
é o backend.

Existe por dois motivos, e o segundo é o que importa para decisões futuras.

**Um: um log pessoal de anos sem exportação é um refém.** O banco é SQLite e o
esquema é simples, mas "abra o sqlite3 e escreva um SELECT" não é uma saída, é
a ausência de uma.

**Dois: é a resposta ao horizonte longo.** A semana é a costura por onde este
projeto viraria planilha — é o único painel com número somado e navegação
temporal, e daqui todo pedido natural ("e o mês?", "e o ano?", "e comparado com
a semana passada?") é um passo em direção ao dashboard que o princípio de design
recusa. A regra que segura isso: **a resposta é uma página, não um painel
maior.** Ver mais que uma semana é gerar o diário daquele período e lê-lo como
texto, fora do app. **Não existe aba de mês, e não deve existir.**

A diferença não é de formato, é de natureza: um painel de mês seria mais tela no
mesmo lugar, com a mesma pressão de virar comparação; a página é um artefato que
se lê, se guarda e se fecha.

Decisões que não são arbitrárias:

- **Markdown, não HTML.** Por longevidade. O ponto de uma saída de emergência é
  ser legível sem ferramenta nenhuma, daqui a dez anos, por quem não tem o app
  instalado — e um `.md` continua sendo texto num bloco de notas. HTML seria
  mais bonito e menos útil exatamente onde importa, e converter Markdown em HTML
  é trivial enquanto o caminho inverso perde a legibilidade crua.
- **A página não é relatório.** Sem média, sem percentual, sem comparação de
  períodos. O único número é a soma dos minutos de um dia, a mesma conta que o
  bilhete da parede já faz. A regra vale mais forte aqui do que na tela: um
  arquivo dura mais, e número de cobrança impresso cobra por mais tempo. Há
  teste varrendo a página em busca dessas palavras.
- **Parte sem conteúdo não aparece**, em vez de aparecer vazia. Cabeçalho
  seguido de nada é cobrança silenciosa por não ter nada ali.
- **Vai para `<pasta de dados>/paginas/`**, e não para a Área de Trabalho ou os
  Documentos. Descobrir onde essas pastas ficam é código de plataforma — em
  português elas têm outro nome, e com OneDrive corporativo estão redirecionadas
  —, e `openExportFolder` abre a pasta em seguida por `QDesktopServices`, que é
  abstração do próprio Qt e não código de plataforma. Assim o caminho deixa de
  ser algo que alguém precise decorar, e continua de pé a regra de que o app só
  escreve na própria pasta de dados.
- **O nome do arquivo começa pela data em ISO**, que é o único formato que
  ordena alfabeticamente na mesma ordem em que ordena cronologicamente. Numa
  pasta com dois anos de páginas, é a diferença entre uma lista e uma bagunça. O
  nome vem do período, então exportar de novo o mesmo período reescreve a mesma
  página em vez de acumular cópias.
- **Escrita atômica**, pela mesma razão da marca de vida: uma queda no meio
  deixaria meia página no lugar de uma inteira, com a anterior — que estava
  certa — já truncada.
- **Dois caminhos, e eles dizem coisas diferentes.** `o quarto → a página` grava
  tudo; o rodapé da semana grava o período que está na tela. O segundo é o que
  torna a regra do horizonte longo utilizável, e é por isso que ele fica no
  painel onde a pergunta aparece, não escondido num menu.

## Janelas

Uma `QQmlApplicationEngine`, dois `Window` QML ligados ao **mesmo** backend
Python exposto como context property. Sem IPC, sem estado duplicado.

- `Main.qml` — 1100x700, cena completa.
- `Mini.qml` — **264x82 em repouso, 264x118 com o mouse em cima**,
  `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`. Frameless exige
  drag manual via `DragHandler`.

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

A mini é um **lembrete**, não um painel. Ela responde três coisas, nesta ordem:
em que você está, há quanto tempo, e como encerrar isso. Ajuste não mora ali — o
som tem duas posições (`toggleMute`, que devolve o estado anterior), e o ciclo de
três estados, o tema e o humor ficam na janela grande.

**Ela tem dois tamanhos, e é isso que a fez encolher.** Eram 300x112 com cinco
controles à mostra o tempo todo: o principal no alto à direita e mais quatro numa
fileira embaixo, também à direita — duas bordas direitas desalinhadas e **o
quadrante inferior esquerdo completamente vazio**, não como respiro mas porque a
fileira era ancorada num canto de uma faixa de largura inteira. Muita janela para
pouca informação, que é o oposto do que um lembrete deve ser.

Em repouso agora são 264x82: relógio, nome do que está correndo, e o botão que
encerra aquilo. Quando o mouse chega — ou seja, quando alguém *vai* mexer — a
janela cresce para baixo e mostra os secundários (parar, som, abrir, fechar),
distribuídos pela largura inteira em vez de amontoados num canto. O conteúdo é
ancorado no topo, então nada do que já estava na tela muda de lugar.

A troca é essa: um clique a mais nos controles secundários, em troca de **36%
menos janela** ocupando a tela durante todas as horas em que ninguém vai tocar
neles. E "parar" só aparece quando há o que parar sem entregar — numa sessão
livre o botão principal já é "parar", e a fileira se redistribui entre três em
vez de deixar um buraco.

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

## Tipografia

Duas famílias embutidas em `assets/fonts/`, carregadas de dois lugares que
fazem metades diferentes do trabalho.

**Antes disto o projeto não definia fonte em lugar nenhum.** O app herdava a do
sistema — Segoe UI no Windows, Cantarell ou DejaVu no Ubuntu —, e as duas
máquinas são os dois contextos de uso daqui: era outro programa em cada uma, com
outro desenho de letra, outra métrica e outras larguras de botão. Um repositório
que fixa cor em hex num arquivo só e proíbe hardcode em qualquer outro estava
deixando metade do que se vê na tela por conta do sistema operacional.

- **Inter** (`Theme.fonte`) — a interface: painéis, barra, botões, campos.
- **EB Garamond** (`Theme.fontePapel`) — as superfícies de papel do quarto: o
  bilhete e o calendário. É o que faz o bilhete parecer papel pregado na parede
  em vez de um retângulo com texto.

Ambas SIL OFL 1.1, com a licença ao lado do arquivo. **Não são dependência
nova**: são asset, como os SVGs e os WAVs, e o `FontLoader` é do próprio Qt.

Quem carrega:

- `services/fonts.py` define a **fonte padrão da aplicação**
  (`QApplication.setFont`). É o que faz cada `Text` herdar a família certa sem
  declarar nada — e faz código novo nascer certo em vez de depender de alguém
  lembrar de escrever `font.family`. Chamam-no `main.py` e as duas ferramentas
  que sobem Qt Quick, pelo mesmo padrão de `ensure_gl_integration()`.
- O `FontLoader` do `Theme.qml` garante a família para o QML mesmo sem passar
  pelo Python, e expõe o nome para os poucos lugares que trocam de propósito.

**Os algarismos do cronômetro precisam de `tnum`** (`Theme.digitos`). Por padrão
os da Inter são proporcionais — o "1" tem 6,95 px onde o "0" tem 9,6 —, então
`00:00` e `11:11` não medem igual e o relógio **treme a cada segundo**. Com o
recurso ligado os dez ficam com a mesma largura. Há teste, e ele prova as duas
pontas: que sem `tnum` os algarismos divergem mesmo, e que com ele param de
divergir.

A escala de corpos vive no `Theme`, pela mesma regra das cores e dos tempos:

```
nano 11 · miudo 13 · corpo 15 · titulo 19 · destaque 30
```

Havia 9, 10, 11, 13, 15, 16, 18 e 30 espalhados, o 11 sozinho em oito lugares —
a mesma doença que os quatro eixos de tempo curaram nas durações. Os corpos dos
objetos de parede **não** vêm daqui: eles escalam com o desenho, por `unidade`,
porque são parte da ilustração e não da interface.

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

Fração da largura da **janela** é a mesma armadilha com outra cara, e foi assim
que o balão do passeio acabou por cima do bilhete que explicava: 52 px em
1100x700, 114 px ao alargar. Quem aponta para algo desenhado na cena recebe o
`Room` e passa por `cx`/`cy` — é o que o `Passeio.qml` faz com a propriedade
`cena`. A conta em pixel de janela só vale para o que é ancorado na janela, como
a barra de baixo. E as frações têm de vir do desenho, não de estimativa: a
estante termina em x≈264 e o bilhete começa em x=762, não nos 76% que o
comentário antigo supunha.

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

**A luz do abajur sabe que tem alguém trabalhando.** Enquanto uma sessão corre
ela fica um pouco mais quente e um pouco mais larga, e volta sozinha quando o
relógio para. É o corpo que faltava ao timer dentro do quarto: o relógio de
parede marca o turno e não a sessão, e o cronômetro mora numa ilha apoiada no
chão — a informação mais importante do app não tinha presença nenhuma na
ilustração. É a frase mais própria que este cômodo tem: a luz está acesa porque
você está aqui. Sem número, sem contorno, sem widget, e derivada do log, então
não custa evento nenhum.

Três detalhes que não são arbitrários:

- **Existe nos dois temas.** Em repouso, de dia, a luz continua exatamente zero
  como sempre foi; o que a sessão acende ali é bem mais fraco — é a luminária
  que se liga sobre a mesa quando alguém senta, não um segundo sol. Importa
  porque a máquina de uso diurno é a do trabalho: um sinal só noturno não
  existiria justamente onde o app é mais usado.
- **O alargamento multiplica o respiro em vez de somar a ele.** A
  `SequentialAnimation` escreve direto em `raio`, então um valor ligado ali
  seria sobrescrito no primeiro quadro; quem recebe o fator é o `centerRadius`.
- **A `opacity` é conta pura sobre duas propriedades já animadas, sem
  `Behavior` própria.** Com uma ali, cada quadro da animação da sessão viraria
  alvo novo para a animação da opacidade e uma perseguiria a outra — atraso
  elástico que ninguém pediu, e que sumiria de vez com o quarto quieto, quando
  `transicao` vira 0.

## Estrutura

```
cantinho/
  assets/       scenes/ plant/ audio/ icon/ fonts/  (gerados ou desenhados,
                versionados)
  docs/         quarto-{noite,tarde}.png     (capturas do README)
                instalar-no-windows.md      (o passo a passo para leigos)
                plataformas.md              (Windows e Linux: o que difere)
                desenvolvimento.md          (comandos, ferramentas, a suíte)
                auditoria.md                (as direções de 14/08/2026)
  build/        saída de ferramenta e cache, nada versionado
  cantinho.bat  instalar, atualizar, dev e remover no Windows (ASCII, CRLF)
  cantinho/
    main.py
    core/      events.py store.py projections.py clock.py schedule.py
               export.py
    services/  timer.py audio.py hotkey.py tray.py scene.py single_instance.py
               graphics.py desktop_entry.py heartbeat.py fonts.py
    ui/        Main.qml Mini.qml theme/ room/ panels/
  tests/     conftest.py + os três módulos que não são teste, e sim montagem
             compartilhada: checklist.py (de qual sistema é cada teste),
             projecoes.py (o banco de provas), imagens.py (medir um desenho)
  tools/     check_svg.py check_qml.py simular_uso.py semear.py
             gerar_{audio,icone,capturas}.py
             instalar_atalho.py atalho_windows.py empacotar_portatil.py
```

Painéis: `Backlog`, `Retrospectiva`, `Semana`, `SeletorTarefa`, `Passeio`; as
sobreposições `AvisoDeQueda`, `PerguntaDoExtra`, `ToqueDoQuarto`,
`MenuDoQuarto`, `AvisoDaPagina`, `SaidaDoApp` e `CapturaDeIdeia`; e os
elementos de base (`Painel`, `BotaoSuave`, `CampoTexto`, `EscalaPontos`,
`LinhaMenu`, `Rolagem`).

Objetos do quarto: `Room`, `FolhaDeParede` e os três papéis que herdam dela —
`Calendario`, `BilheteDoDia`, `MuralDeParede` — mais o `RelogioParede`.

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
  em `icons/hicolor/<lado>x<lado>/apps` — só no Linux, no-op nos outros sistemas
  como em `hotkey.py`. A regra que sustenta o resto é **criar uma vez e nunca
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
  para dar onde clicar. O limiar é conferido no **tique de um minuto**, que é
  ancorado na abertura do app e não no começo da sessão: o toque sai no primeiro
  tique em ou depois do limiar, com até um minuto de atraso. Com 120 minutos
  isso não se percebe — mas quem baixar as constantes para testar tem de contar
  com a folga, ou vai concluir que o aviso não dispara.
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
  que falava dela. Ficar ao lado exige receber o `Room` (`cena`) e ler as
  posições por `cx`/`cy`: por fração da janela o balão só acerta em 1100x700, e
  foi assim que ele voltou a tapar, agora o bilhete da parede. Ver **coordenadas
  dentro do quarto**.
- **`tools/atalho_windows.py` é o irmão Windows do `.desktop`.** Mora em
  `tools/` e não em `services/` porque a diferença é *quando* cada um roda: o
  do Linux é criado pelo app na primeira abertura, e este é passo de
  instalação. `instalar` e `atualizar` no `cantinho.bat` chamam ele no fim,
  **ignorando o código de saída**: atalho que não deu certo é aviso, não
  instalação perdida — sem ele o app ainda abre pelo menu de dev. Vai por
  `powershell -Command` e não por arquivo `.ps1` porque máquina gerenciada
  costuma vir com a política de execução em `Restricted`, que bloqueia script
  em arquivo e deixa passar comando na linha. E pergunta ao Windows onde fica a
  Área de Trabalho em vez de montar `%USERPROFILE%\Desktop`: em português ela
  tem outro nome, e com OneDrive corporativo ela está redirecionada.

  **Ele aponta para `.venv\Scripts\pythonw.exe -m cantinho.main`**, com a raiz
  do repositório como diretório de trabalho — que com `-m` é também o
  `sys.path[0]` de onde o pacote é importado, a mesma armadilha que o `Exec=`
  do `.desktop` já tinha caído no Linux. O ícone vem do asset e não do alvo,
  senão o atalho é o logo do Python. Ver **Distribuição** para o porquê de não
  ser um `.exe`.

  E aqui **refazer é o certo**, ao contrário do Linux. Lá a regra é criar uma
  vez e nunca sobrescrever, porque qualquer clone de teste poderia sequestrar o
  atalho do menu apontando para si; aqui quem chama é a instalação, a pedido, e
  o alvo é o venv desta pasta — que é exatamente o que precisa ser corrigido
  quando a pasta muda de lugar ou o ambiente é refeito.
- **Todo desenho de SVG passa por uma trava** (`_desenho`, em `services/scene.py`).
  `QQuickImageProvider` do tipo Image roda em thread de trabalho quando o
  `Image` do QML é assíncrono, e as camadas do quarto compartilham um
  `QSvgRenderer` em cache, que não é reentrante.

- **O quarto sai de foco quando um painel abre** (`Main.qml`, `profundidade`).
  A gaveta era uma laje clara pousada sobre a ilustração, cobrindo a janela **e**
  o abajur, e lia como caixa de diálogo colada por cima do desenho: o quarto
  sumia justamente na hora de usar o app. Com o fundo desfocado e um pouco mais
  escuro (`MultiEffect`, que já vem no PySide6 — sem shader compilado e sem
  etapa de build nova), a mesma laje passa a ler como "à frente". O `blurMax` é
  **14 e não 40**: no primeiro ajuste o quarto virava mancha, o que dá
  profundidade e custa a cena inteira. O alvo é ainda reconhecer os objetos da
  estante e as folhas do vaso, só fora de foco. Com `layer.enabled` falso o
  custo é exatamente zero, e esse é o estado padrão do app.
- **A gaveta é posicionada em coordenada de cena** (`quarto.cx(400)`). Era
  `x: 330` em pixel de janela, que coincide com a cena só em 1100x700: ao
  maximizar, o desenho é centralizado e escalado e o painel ficava parado no
  lugar antigo, descolando do abajur que ele existe para não cobrir. É a mesma
  armadilha que já tirou a chuva e a poeira de cena, e que o balão do passeio
  corrigiu.
- **A barra de baixo são duas ilhas, não uma faixa.** Era uma laje que
  atravessava a tela com o cronômetro numa ponta, os botões na outra e um vazio
  enorme no meio — a peça mais "aplicativo" da tela, e a que cortava o chão do
  quarto em dois. O vazio não era respiro: era superfície pintada sobre a
  ilustração para não ligar nada a nada. Agora o chão aparece entre os dois
  agrupamentos, cada um do tamanho do que carrega. `barra` continua existindo
  como guia de layout — é a ela que a gaveta se ancora —, mas não desenha nada.
- **`Painel.sombra`**, ligada só em quem cobre alguma coisa. É o detalhe mais
  barato que separa "painel na frente do quarto" de "retângulo pintado por cima
  da ilustração": sem ela o olho não tem como saber que existem duas camadas.
  Larga, difusa e quase transparente — sombra dura viraria caixa de diálogo de
  sistema.
- **Vinheta e paralaxe, para o cômodo ter volume** (`Room.qml`). O desenho é
  iluminado de forma plana: a parede tem a mesma intensidade no centro e no
  canto, o que lê como ilustração chapada. A vinheta é mais forte à noite, e por
  um motivo físico — de dia a luz entra pela janela e chega aos cantos; à noite
  há uma lâmpada só. Ela **não** obedece a `movimento`, porque não se mexe: é
  iluminação. O paralaxe são **quatro pixels** e obedece, sim; a escala de 1,2%
  existe só para dar folga, senão deslocar descobriria faixa vazia na borda
  oposta. O `Behavior` sobre a ligação é o que dá o arrasto: grudado no cursor
  seria enjoativo e denunciaria o truque.
- **A estante tem presença, e diz de quem é cada objeto.** Ela é o retorno
  inteiro do app e era a coisa **menos visível** da tela: um borrão escuro no
  canto, menor que o ícone do calendário e longe da única luz do quarto. Ganhou
  luz própria, que sobe no instante da chegada e volta sozinha
  (`brilhoDaChegada`), e o rótulo da tarefa quando o mouse para em cima. A
  geometria do hover vem de `scene.shelf_slots`, **a mesma função que desenha a
  imagem** — se as duas contas divergissem, o nome apareceria ao lado do objeto
  errado, que é pior do que não aparecer. Só o rótulo: no instante em que
  mostrar data ou minutos, deixa de ser memória e vira registro. E não responde
  com painel aberto (`Room.focoNoQuarto`), porque ali o quarto é cenário — balão
  nítido sobre cena desfocada denunciaria que as duas camadas não são o mesmo
  lugar.
- **`Rolagem.qml` em vez de barra de rolagem.** As listas rolavam desde sempre e
  não diziam isso: `clip: true` e nenhum indicador, então com sete tarefas a
  oitava não existia para quem olhava. Barra de rolagem é cromo de aplicativo,
  ocupa espaço fixo e fica parada dizendo "isto é um widget"; o que se usa é o
  **desvanecimento das bordas** — onde a lista continua, o conteúdo dissolve no
  fundo do painel em vez de ser cortado numa reta. É a pista que uma folha
  dobrada dá, e ela só aparece quando há conteúdo do outro lado.
- **`BotaoSuave` aceita foco de teclado.** O app tinha bons atalhos e nenhum
  jeito de andar entre os controles sem o mouse. O anel é âmbar, a mesma cor que
  o `CampoTexto` já usava para dizer "a digitação vai para aqui" — outra cor
  daria ao app duas linguagens de foco. `activeFocusOnTab` só nos que estão à
  mostra: botão de largura zero na fila do Tab é um passo em que a atenção some
  da tela. E o clique também dá foco, senão Tab depois de clicar recomeça do
  início.

  **E anuncia o próprio nome** (`Accessible.role`, `.name`, `.onPressAction`,
  no componente e não em cada chamada — assim os quase quarenta botões do app
  são cobertos de uma vez e um botão novo nasce coberto, pela mesma lógica de
  `services/fonts.py` definir a fonte da aplicação em vez de cada `Text`
  declarar a família). Sem isso o Narrator e o Orca leem "painel, painel,
  painel" ao andar pela barra: o `Item` do QML não tem papel nem nome, e o
  rótulo está num filho que a árvore de acessibilidade não associa a nada. É um
  app de um usuário só, então isto é barato e não urgente — mas o anel de foco
  e a fila do Tab já existiam, e teclado sem nome é meio caminho.
- **As sobreposições vivem em `panels/`, uma por arquivo.** `Main.qml` tinha
  1.653 linhas e carregava dez coisas independentes — o aviso de queda, a
  pergunta do extra, o toque, o menu do quarto, o aviso da página, a saída, a
  captura de ideia — cada uma um painel autocontido que nada mais lê. Extraídas,
  a janela ficou com 897 linhas e passou a conter o que é de fato dela: o
  quarto, a gaveta, a barra, os atalhos e a cola entre eles. Nenhum pixel mudou.
  Duas regras saíram do processo e valem para a próxima:

  **Estado mora com quem o muda.** O menu virou dono do próprio `aberto` em vez
  de espelhar uma propriedade da janela: quem fecha o menu é quase sempre o
  próprio menu — o clique fora, a linha que dispara uma ação —, e um binding
  vindo de fora se romperia na primeira dessas atribuições, deixando os dois
  lados discordando em silêncio.

  **Âncora não atravessa fronteira de componente.** Embrulhar o menu num `Item`
  para trazer junto o clique de fora tornou o rodapé irmão do *componente* e não
  do painel, e `anchors.bottom: rodape.top` virou aviso em runtime com o painel
  parado no topo da janela. Onde o embrulho existe, a conta vai em `y`. Os
  painéis que são `Painel` na raiz continuam ancorando normalmente.
- **O cartão do mural corta em quatro linhas.** Uma ideia aceita até 4.000
  caracteres, e sem teto de linhas um texto colado empurrava o resto do mural
  para fora da tela. O mural é uma parede de bilhetes; bilhete que ocupa a
  parede inteira deixou de ser um.

- **O ícone do Linux sai do `.ico` do Windows, e nos sete tamanhos**
  (`install_icons`). Era só o 256 que ia para o `hicolor`, e o ambiente reduzia
  esse arquivo único para os 22-24 px da bandeja e os 48-64 do dock. Só que a
  arte do 256 é a planta **sobre um ladrilho escuro**: reduzida a 24 px ela vira
  um quadrado escuro com um borrão dentro, que na barra do Ubuntu lê como ícone
  genérico. No Windows nunca apareceu porque lá o `.ico` entrega os sete
  tamanhos e o sistema escolhe o certo — e é por isso que o desenho *muda* com
  o tamanho (ver "Ícone"): abaixo de 32 px o ladrilho sai e a planta ocupa o
  quadro. Instalar só o maior desfazia exatamente a decisão que o gerador do
  ícone tomou.

  A correção lê os quadros de dentro do `.ico` com `struct` — **sem Qt**, porque
  este módulo roda antes de a aplicação existir — e escreve cada um no tamanho
  correspondente. Os dois sistemas passam a mostrar literalmente os mesmos
  bytes, que é o que "igual ao do Windows" quer dizer.

  Duas coisas mais, que faltavam junto: **`gtk-update-icon-cache`** é chamado
  como irmão do `update-desktop-database` (sem ele, um tamanho novo fica em
  disco e o GTK continua servindo o índice antigo — ícone certo no disco,
  genérico na tela), e **o ícone é reparado mesmo com o `.desktop` já no
  lugar**. Esta última é o que faz a correção chegar em quem já tinha instalado:
  `install` sai cedo quando o atalho existe, e antes o ícone saía junto, então
  uma instalação antiga jamais ganharia os tamanhos que faltam. "Criar uma vez e
  nunca sobrescrever" protege o `Exec=` de ser sequestrado e respeita um atalho
  editado à mão; o ícone é asset do app e ninguém o edita.

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
- **Nada no app comprova que a notificação apareceu.** `Tray.notify` devolvendo
  `True` quer dizer que a chamada não falhou, não que subiu banner — e as duas
  coisas se separam de verdade: nesta máquina, com `isSystemTrayAvailable`,
  `supportsMessages` e `notify()` todos `True`, nenhum banner aparece. Não é do
  Qt: um balão de `NotifyIcon` do .NET e uma torrada WinRT com AUMID conhecido
  também não saem, sem "não perturbe" nem política no registro. É condição da
  máquina, e o único jeito de saber é olhar a tela. Vale para o Linux pelo mesmo
  motivo — foi para contornar um caso desses que existe o caminho por `gdbus`.
- O som é sintetizado, não gravado, e é curto: 24 s em loop. Não tem melodia,
  é textura. Trocar por faixa de verdade é só pôr outro arquivo com o mesmo
  nome em `assets/audio/`.
- O bilhete da parede comporta **seis linhas** (`BOARD_LIMIT`). É a folha que
  limita, não a projeção: uma lista que rola na parede deixa de ser bilhete.
- **`_recomputar` reprojeta o log inteiro a cada evento gravado**, não só na
  abertura. É o custo que cresce com o tempo, e o enquadramento importa: o
  `read_all` do startup roda uma vez e some, mas a reprojeção roda no clique.
  Medido no Ubuntu, com uso sintético pesado (3 tarefas + 4 sessões + ideia +
  revisão por dia):

  | período | eventos | `read_all` (abertura) | projeções (**por clique**) |
  |---|---|---|---|
  | 30 dias | 480 | 2,5 ms | 1,5 ms |
  | 1 ano | 5.840 | 30 ms | 17 ms |
  | 3 anos | 17.520 | 84 ms | 59 ms |
  | 10 anos | 58.400 | 328 ms | 213 ms |

  Não é problema hoje e não pede conserto. O que ele pede é que a saída, se um
  dia for preciso, **não seja tabela de snapshot** — isso quebraria "`events` é
  a única tabela persistida" e "não persistir estado derivado" de uma vez. A
  saída que preserva a arquitetura é memoização em memória, que continua sendo
  função pura do log.

  **O que já foi consertado ali é a semana**, que pagava cinco vezes esse custo
  sem ninguém ter aberto o painel. Três propriedades notificadas por
  `weekChanged` — que `_recomputar` emite a cada evento — e cada uma
  reprojetando o log várias vezes: `weekDays` chamava `completed_on` sete vezes,
  `weekMinutes` chamava `minutes_on` outras sete, e `weekDelivered` chamava
  `weekDays` inteiro só para contar. Com o painel **fechado**, porque os
  bindings ficam vivos de qualquer jeito: os quatro painéis se cruzam por
  opacidade, não por `Loader`. Media 95 ms por clique com um ano de log e 301 ms
  com três anos, justamente no gesto em que a estante deveria animar suave.

  Duas correções, e as duas valem lembrar porque a segunda quase sempre é
  esquecida: `_semana()` faz uma passada só e as três propriedades leem dela
  (301 ms → 82 ms aos três anos), **e** a `Semana` foi para dentro de um
  `Loader` com `active` ligado à aba — com o painel fechado o custo é zero, não
  "menor". É o único painel que precisa disso; para os outros três a instância
  permanente é barata.
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
| F6 | Distribuição sem binário próprio | feito, sobre o Python assinado |
| F7 | Parede viva, mural, reação de mouse | feito |
| F8 | Foco da sessão, correção de tarefa, a semana | feito |

Não pule fase. Não adiante arte. Se o modelo de eventos estiver errado,
descobrir na F3 custa caro.

## Convenções

- Português do Brasil em UI, commits e comentários.
- **Idioma de identificador é regra de fronteira, não de arquivo.** O que
  atravessa para o QML é inglês; o que é interno acompanha os comentários, que
  são todos em português. Em detalhe:
  - **Inglês, sem exceção:** tudo que o QML enxerga — `@Property`, `@Slot`,
    `Signal` e os kinds do log. `addTask`, `focusedTaskId`, `weekDelivered`,
    `task.completed`. É API, e API que muda de idioma no meio obriga a
    adivinhar de que lado cada nome está.
  - **Inglês também:** constantes públicas de módulo (`TODAY_LIMIT`,
    `SHELF_OBJECT_TYPES`, `LABEL_LIMIT`) e nomes de arquivo e função de
    `core/`, `services/` e `tools/`.
  - **Português:** locais, atributos privados e o vocabulário do quarto —
    `_estante`, `_concluidas`, `eventos`, `posicoes`, e no QML `Theme.noite`,
    `movimento`, `chegada`. Nesses lugares o nome está cercado de comentário em
    português, e traduzir só o identificador quebra a frase.

  A regra escrita antes era "identificadores em inglês", que o código nunca
  seguiu e não deveria seguir: renomear os internos daria um diff enorme, risco
  puro e nenhum ganho. O que estava errado era a documentação, não o código.
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
