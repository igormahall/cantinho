# Cantinho

Um cômodo ilustrado que fica aberto enquanto você trabalha.

O timer é o motor de tudo. Ele alimenta um diário que se escreve sozinho, cada
tarefa concluída deixa um objeto na estante, e a planta do canto cresce com as
horas de foco das últimas duas semanas — murchando sozinha se você sumir, sem
drama e sem cobrança.

![O cantinho à noite](docs/quarto-noite.png)

## O que ele não faz

Sem streak, sem barra de progresso, sem percentual, sem XP, sem ranking. Sem
gráfico na tela principal e sem notificação lembrando que você não abriu ontem.
Falhar não destrói nada: só não faz crescer.

Sem conta, sem nuvem, sem sincronização. O banco é um arquivo na sua máquina e
nada sai dela.

## Rodando

Precisa de Python 3.10+. A única dependência de execução é o PySide6.

**Windows** — `cantinho.bat` faz tudo: cria o ambiente, instala as
dependências e gera o executável. Duplo clique abre um menu; da linha de
comando ele aceita `instalar`, `rodar`, `empacotar`, `atualizar`, `portatil`,
`testar` e `refazer`. É o mesmo script para a primeira instalação e para
atualizar depois de sobrescrever os arquivos com uma versão nova.

**Linux** — o caminho manual:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m cantinho.main
```

Rode sempre com o Python do venv; o `python` do PATH não tem PySide6. Numa
Ubuntu limpa faltam algumas bibliotecas de sistema antes disso —
**[docs/linux.md](docs/linux.md)** tem a lista e o resto do que é específico
daqui.

O banco fica em `%APPDATA%\Cantinho` no Windows e `~/.local/share/cantinho` no
Linux. Um banco por vez: abrir o mesmo duas vezes traz para a frente a janela
que já existe. Para experimentar sem sujar seus dados:

```bash
python -m cantinho.main --db ./teste.db --log DEBUG
```

## Como se usa

| | |
|---|---|
| **começar** | prende o timer à tarefa escolhida. Clique no nome dela, ao lado do relógio, para trocar. |
| **entreguei** | encerra a sessão e conclui a tarefa. É o que põe um objeto na estante. |
| **parar** | para o relógio; a tarefa continua na lista. |
| **hoje** | escreva embaixo e aperte Enter. Arraste para reordenar, clique para escolher, duplo clique para corrigir o texto. |
| **o círculo** | conclui a tarefa sem passar pelo timer. |
| **o dia** | as sessões, o humor, a nota — e **encerrar o dia**, que guarda a sessão aberta junto. |
| **a semana** | o que foi entregue, dia a dia. Também abre clicando no calendário da parede. |
| **ideias** | o mural. A ideia que virar tarefa continua lá, riscada. |
| **Ctrl+Shift+I** | guarda uma ideia de qualquer lugar, mesmo com o app escondido. |
| **mini** | troca a janela por uma janelinha só com o timer, sempre por cima. Arrasta pelo corpo. |
| **o quarto** | luz, som, movimento, como está o dia e a saída do app. |

As duas janelas nunca ficam na tela juntas: a mini substitui a grande e
vice-versa. Fechar a janela não encerra o app — ele continua na bandeja. Para
encerrar de verdade, **o quarto → sair**.

O som abre em **só os toques**: o quarto calado, a interface respondendo ao
clique. O ambiente — chuva à noite, acorde de tarde — é uma escolha em **o
quarto → som**, que gira entre os três estados.

Cinco coisas se mexem sozinhas no cenário: a luz do abajur respirando, as
folhas, a chuva, a poeira no feixe e o grão. Em **o quarto → movimento** elas
param todas. Serve para bateria — o grão repinta a janela a cada 900 ms, o dia
inteiro — e para quem não quer movimento no canto do olho enquanto lê outra
coisa. Os botões continuam respondendo ao toque: o quarto fica quieto, não
morto.

![O cantinho de tarde, com o backlog aberto](docs/quarto-tarde.png)

## Os dois momentos

Em dia de semana o quarto segue o seu expediente: acende quando o turno começa,
vira noite quando ele termina, com uma travessia de três segundos entre um e
outro. Fora disso vale o relógio. A jornada fica em `cantinho/core/schedule.py`,
e dá para fixar o tema à mão em **o quarto → luz**.

O relógio de parede ganha um traço âmbar onde o trecho atual termina — de manhã
o almoço, à tarde a hora de ir embora. Não é contagem regressiva: é uma marca no
mostrador, que se lê de relance e não mostra número nenhum.

## Executável portátil

```bash
pip install -r requirements-dev.txt
pyinstaller cantinho.spec --noconfirm
```

Sai uma pasta `dist/Cantinho/` de uns 200 MB que roda sem instalação e sem
admin. O build é por plataforma.

Quando o antivírus apaga o executável — e acontece, porque o bootloader do
PyInstaller é o mesmo binário em todo programa empacotado com ele —, existe um
segundo empacotador, que não gera binário nenhum e monta o app sobre o
`python.exe` oficial da PSF:

```powershell
python tools/empacotar_portatil.py     # Cantinho-portatil-windows.zip
```

O passo a passo em máquina corporativa está em
**[docs/fabrica.md](docs/fabrica.md)**.

## Desenvolvimento

Com o venv ativado:

```bash
pip install -r requirements-dev.txt

python -m pytest                # 333 testes, sem abrir janela
python tools/simular_uso.py     # percorre a interface clicando de verdade
python tools/check_svg.py       # rasteriza os SVGs em build/svg_check/
python tools/semear.py          # banco descartável com duas semanas de uso
python tools/gerar_audio.py     # regera os sons
python tools/gerar_icone.py     # regera o ícone do app
python tools/gerar_capturas.py  # regera as imagens deste README
```

O `pytest` não cobre o QML. Quem faz isso é o `simular_uso.py`: ele abre as
janelas, cria tarefa, escolhe, roda sessão, conclui, arrasta, corrige texto,
captura ideia, abre a semana e fecha o dia com mouse e teclado sintéticos;
depois reabre o banco do zero e confere o log evento por evento. Rode depois de
mexer em qualquer `.qml`.

Áudio, ícone e capturas são gerados e versionados prontos, e os geradores são
determinísticos: uma mudança no `git status` depois de rodá-los significa que o
código mudou, não que o resultado variou.

### Por dentro

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
  core/       events.py store.py projections.py clock.py schedule.py   (sem Qt)
  services/   scene.py timer.py audio.py hotkey.py tray.py graphics.py
              single_instance.py desktop_entry.py            (plataforma)
  backend.py  a fronteira entre o log e a interface
  ui/         Main.qml Mini.qml theme/ room/ panels/
```

O ícone é o próprio vaso do quarto, e na bandeja ele acompanha o crescimento da
planta. O som é sintetizado pela biblioteca padrão do Python, não gravado. Os
SVGs de cena têm camadas com os mesmos ids nos dois temas, o que deixa a planta
e a estante mudarem sem redesenhar o quarto.

`CLAUDE.md` tem as regras de arquitetura em detalhe, incluindo o que
deliberadamente não se faz aqui e por quê.
