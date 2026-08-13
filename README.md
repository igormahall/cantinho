# Cantinho

Um cômodo ilustrado que fica aberto enquanto você trabalha.

O timer é o motor de tudo. Ele alimenta um diário que se escreve sozinho, cada
tarefa concluída deixa um objeto na estante, e a planta do canto cresce com as
horas de foco das últimas duas semanas — murchando sozinha se você sumir, sem
drama e sem cobrança.

![O cantinho à noite](docs/quarto-noite.png)

## O que ele não faz

- Sem streak, sem barra de progresso, sem percentual, sem XP, sem ranking.
- Sem gráfico na tela principal.
- Sem notificação lembrando que você não abriu ontem.
- Sem conta, sem nuvem, sem sincronização.

Falhar não destrói nada: só não faz crescer. O banco é um arquivo na sua
máquina, e nada sai dela.

## Instalando

Precisa de **Python 3.10 ou mais novo**, e só. A única dependência de execução
é o PySide6, que os comandos abaixo instalam sozinhos.

Escolha o seu caso:

| | |
|---|---|
| **Só quero usar o Cantinho** (Windows) | [instalar](#usar-no-windows) · [atualizar](#atualizar-o-cantinho-instalado) |
| **Quero mexer no código** (Windows ou Linux) | [ambiente de desenvolvimento](#desenvolver) |

---

### Usar no Windows

Não precisa de git nem de conhecimento técnico: baixar, descompactar e colar
três linhas.

**1. Baixe e descompacte**

Em **github.com/igormahall/cantinho**, botão verde **`<> Code`** →
**Download ZIP**. Descompacte dentro de `Documentos`, de forma a ficar assim:

```
C:\Users\voce\Documents\cantinho-main\
```

**2. Instale**

Abra o Prompt de Comando (<kbd>Windows</kbd>+<kbd>R</kbd>, escreva `cmd`,
Enter) e cole os comandos, um de cada vez:

```bat
cd /d "%USERPROFILE%\Documents\cantinho-main"
cantinho.bat instalar
cantinho.bat empacotar
```

O primeiro leva de 5 a 10 minutos, o segundo uns 2. No fim, o **atalho já está
na Área de Trabalho** e o executável em `dist\Cantinho\Cantinho.exe`.

> **Nunca fez isso antes?**
> **[docs/instalar-no-windows.md](docs/instalar-no-windows.md)** é o mesmo
> roteiro explicado do zero, sem supor nada: desde instalar o Python até o
> ícone aparecer na Área de Trabalho, com o que fazer em cada erro comum.

Se o antivírus da empresa apagar o `.exe`, troque o segundo comando por
`cantinho.bat portatil` — ver [docs/windows.md](docs/windows.md).

---

### Atualizar o Cantinho instalado

**As suas anotações não são tocadas.** Elas ficam em `%APPDATA%\Cantinho`, fora
da pasta do programa; atualizar troca só o código.

Antes de começar, **feche o Cantinho** — inclusive o ícone perto do relógio
(**o quarto → sair**). O executável não pode ser reescrito enquanto está
aberto.

Todos os comandos rodam **dentro da pasta do Cantinho**:

```bat
cd /d "%USERPROFILE%\Documents\cantinho-main"
```

**Se você instalou pelo ZIP** (o caminho acima), baixe o ZIP novo, descompacte
por cima da pasta antiga substituindo os arquivos, e depois:

```bat
cantinho.bat atualizar
```

**Se você instalou com git** (`git clone`), o comando de puxar as novidades vai
nessa mesma pasta, antes do `atualizar`:

```bat
cd /d "%USERPROFILE%\Documents\cantinho"
git pull
cantinho.bat atualizar
```

> `git pull` só funciona em pasta que veio de `git clone`. Numa pasta que veio
> do ZIP ele responde *"not a git repository"* — ali o caminho é baixar o ZIP
> de novo. Se você prefere atualizar com um comando só daqui para frente,
> instale [Git para Windows](https://git-scm.com/download/win) e refaça a
> instalação com `git clone https://github.com/igormahall/cantinho.git`.

`atualizar` e `empacotar` fazem quase a mesma coisa; a diferença é que
`atualizar` apaga o cache de build antes. Ele é confiável quase sempre, e
"quase" é pouco quando os arquivos foram trocados por baixo dele.

---

### Desenvolver

Aqui o git é o caminho, nos dois sistemas:

```bash
git clone https://github.com/igormahall/cantinho.git
cd cantinho
```

**Windows** — `cantinho.bat` faz tudo. Duplo clique abre um menu; da linha de
comando aceita `instalar`, `rodar`, `empacotar`, `atualizar`, `portatil`,
`testar`, `refazer` e `atalho`.

```bat
cantinho.bat instalar    :: venv + dependências (runtime, pytest, pyinstaller)
cantinho.bat rodar       :: abre o app a partir do código
cantinho.bat testar      :: a suíte
```

**Linux** — o mesmo, na mão:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

python -m cantinho.main          # rodar o app
python -m pytest                 # a suíte
python tools/simular_uso.py      # percorre a UI clicando de verdade
```

Numa Ubuntu limpa faltam bibliotecas de sistema que o PySide6 carrega em
runtime — o sintoma é o plugin `xcb` não carregar. A lista está em
[docs/linux.md](docs/linux.md).

Três coisas que economizam tempo depois:

- **Rode sempre com o Python do venv.** O `python` do PATH não tem PySide6.
- **`python tools/semear.py`** cria um banco de demonstração com duas semanas
  de uso, em `build/demo.db`. Sem ele, avaliar estante, planta ou bilhete exige
  usar o app por duas semanas de verdade.
- **`python tools/simular_uso.py` é o que cobre o QML** — o pytest não cobre.
  Rode depois de mexer em qualquer `.qml`, e **com a tela ligada**.

Mais detalhes em
**[docs/desenvolvimento.md](docs/desenvolvimento.md)**.

---

O banco fica em `%APPDATA%\Cantinho` no Windows e `~/.local/share/cantinho` no
Linux. Um banco por vez: abrir o mesmo duas vezes traz para a frente a janela
que já existe. **Os bancos das duas máquinas nunca se falam** — não há
sincronização de nenhum tipo.

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
| **Ctrl+Shift+I** | guarda uma ideia de qualquer lugar, mesmo com o app escondido. Só no Windows. |
| **mini** | troca a janela por uma janelinha só com o timer, sempre por cima. Arrasta pelo corpo. |
| **o quarto** | luz, som, movimento, como está o dia e a saída do app. |

Três coisas que surpreendem na primeira vez:

- **As duas janelas nunca ficam na tela juntas.** A mini substitui a grande, e
  vice-versa.
- **Fechar a janela não encerra o app** — ele continua na bandeja. Para
  encerrar de verdade, **o quarto → sair**.
- **O som abre em "só os toques"**: o quarto calado, a interface respondendo
  ao clique. O ambiente — chuva à noite, acorde de tarde — é uma escolha em
  **o quarto → som**, que gira entre os três estados.

![O cantinho de tarde, com o backlog aberto](docs/quarto-tarde.png)

## O quarto

Em dia de semana ele segue o seu expediente: acende quando o turno começa,
vira noite quando ele termina, com uma travessia de três segundos entre um e
outro. Fora disso vale o relógio. A jornada fica em
`cantinho/core/schedule.py`, e dá para fixar o tema à mão em **o quarto → luz**.

O relógio de parede ganha um traço âmbar onde o trecho atual termina — de
manhã o almoço, à tarde a hora de ir embora. Não é contagem regressiva: é uma
marca no mostrador, que se lê de relance e não mostra número nenhum.

Cinco coisas se mexem sozinhas: a luz do abajur respirando, as folhas, a
chuva, a poeira no feixe e o grão. Em **o quarto → movimento** elas param
todas. Serve para bateria — o grão repinta a janela a cada 900 ms, o dia
inteiro — e para quem não quer movimento no canto do olho enquanto lê outra
coisa. Os botões continuam respondendo ao toque: o quarto fica quieto, não
morto.

## Documentação

- **[docs/instalar-no-windows.md](docs/instalar-no-windows.md)** — instalar do
  zero no Windows, escrito para quem nunca abriu um terminal.
- **[docs/windows.md](docs/windows.md)** — empacotar para Windows, as duas
  formas, e o que fazer quando o antivírus implica com o executável.
- **[docs/linux.md](docs/linux.md)** — as bibliotecas de sistema que faltam
  numa Ubuntu limpa, o Anaconda desligando o OpenGL, e o atalho na grade.
- **[docs/desenvolvimento.md](docs/desenvolvimento.md)** — rodar a suíte,
  as ferramentas, e como o log de eventos funciona por dentro.
- **[CLAUDE.md](CLAUDE.md)** — as regras de arquitetura em detalhe, incluindo
  o que deliberadamente não se faz aqui e por quê.
