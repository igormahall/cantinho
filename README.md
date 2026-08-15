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

Precisa de **Python 3.10 ou mais novo**, e só. A única dependência de execução é
o PySide6, que a instalação baixa sozinha.

### Windows

Tudo passa por um arquivo, o `cantinho.bat`. Duplo clique nele abre um menu de
quatro opções, e é o mesmo menu para quem está começando e para quem mexe no
código:

```
 1  instalar    montar o quarto do zero, atalho incluído
 2  atualizar   trocar o que mudou; o que você anotou fica
 3  dev         a oficina: código, testes, ferramentas
 4  remover     desmontar, e escolher o que fica
```

**A opção 1 termina com o Cantinho funcionando** — venv, dependências e o atalho
na Área de Trabalho. Não há um segundo comando depois dela.

Escolha como o código chega até a sua máquina. As duas formas dão no mesmo
`cantinho.bat`; a diferença aparece só na hora de atualizar.

**Com git** (recomendado, se você já usa) — atualizar depois é uma opção só:

```bat
cd /d "%USERPROFILE%\Documents"
git clone https://github.com/igormahall/cantinho.git
cd cantinho
cantinho.bat instalar
```

**Com o ZIP**, sem instalar git nem saber o que é: em
**github.com/igormahall/cantinho**, botão verde **`<> Code`** → **Download ZIP**.
Descompacte dentro de `Documentos` — fica `C:\Users\voce\Documents\cantinho-main\`
— e dê **duplo clique no `cantinho.bat`** de dentro dela, opção **1**.

De qualquer um dos dois jeitos leva de 5 a 10 minutos, quase tudo esperando o
`pip`. No fim o atalho **Cantinho** está na Área de Trabalho e abre o app.

> **Nunca fez isso antes?**
> **[docs/instalar-no-windows.md](docs/instalar-no-windows.md)** é o mesmo
> roteiro explicado do zero, sem supor nada: desde instalar o Python até o ícone
> aparecer na Área de Trabalho, com o que fazer em cada erro comum.

**Nenhum executável é gerado, e isso é de propósito.** O atalho aponta para o
`pythonw.exe` do próprio ambiente virtual, que é uma cópia do binário oficial da
Python Software Foundation e carrega a assinatura dela. Um `.exe` construído aqui
nasceria sem assinatura, e é isso que o Smart App Control do Windows 11 e os
antivírus gerenciados recusam — sem aviso, sem mensagem, o duplo clique
simplesmente não faz nada. Ver [docs/plataformas.md](docs/plataformas.md).

Uma consequência prática: **o atalho aponta para dentro desta pasta.** Se você
mudá-la de lugar, rode a opção **2** de lá — ela refaz o atalho no caminho novo.

#### Atualizar

**Não precisa fechar o app antes**: se ele estiver aberto, a atualização o fecha,
inclusive o ícone perto do relógio. E as suas anotações não são tocadas — elas
ficam em `%APPDATA%\Cantinho`, fora da pasta do programa.

- **Instalou com git?** É só a opção **2**. Ela mesma oferece buscar as novidades
  no GitHub antes de atualizar.
- **Instalou pelo ZIP?** Baixe o ZIP novo, descompacte por cima da pasta antiga
  substituindo os arquivos, e então a opção **2**. Ali não aparece pergunta de
  git nenhuma: numa pasta que não veio de `git clone`, `git pull` responderia
  *"not a git repository"*.

Para trocar do ZIP para o git e ganhar a atualização de uma opção só, instale
[Git para Windows](https://git-scm.com/download/win) e refaça a instalação com
`git clone`. Suas anotações ficam onde estão — elas não moram na pasta do
programa.

A opção **1** também serve como conserto: apaga o ambiente e refaz do zero, que é
o caminho quando algo ficou em estado duvidoso. Continua sem tocar no diário.

#### Remover

A opção **4** desmonta o que foi montado — o ambiente, as pastas de trabalho e o
atalho — e deixa o código da pasta, que você apaga na mão se quiser.

O seu diário é uma pergunta **separada**, feita depois, e só sai se você escrever
a palavra `apagar`. É a única coisa aqui que não se refaz: não existe cópia em
lugar nenhum, e o banco inteiro é um arquivo só (`cantinho.db`), fácil de guardar
antes.

### Ubuntu

Aqui não há instalador: é o venv e o código. O atalho na grade de aplicativos o
próprio app cria na primeira abertura.

```bash
sudo apt install python3-venv python3-dev libxcb-cursor0

git clone https://github.com/igormahall/cantinho.git
cd cantinho
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

python -m cantinho.main
```

Para atualizar, `git pull --rebase` e o `pip install` de novo — o `.venv/` é por
máquina e não é versionado, então é por ele que uma dependência trocada no outro
sistema chega aqui.

Numa Ubuntu recém-instalada faltam mais bibliotecas que o PySide6 carrega em
runtime, e o sintoma é sempre o plugin `xcb` não carregar. A lista completa, o
Anaconda desligando o OpenGL e o atalho na grade estão em
**[docs/plataformas.md](docs/plataformas.md)**.

### Onde ficam os seus dados

`%APPDATA%\Cantinho` no Windows, `~/.local/share/cantinho` no Linux. Um banco por
vez: abrir o mesmo duas vezes traz para a frente a janela que já existe. **Os
bancos das duas máquinas nunca se falam** — não há sincronização de nenhum tipo.

### Mexer no código

**[docs/desenvolvimento.md](docs/desenvolvimento.md)** tem os comandos, as
ferramentas e a suíte. No Windows, a opção **3** do menu embrulha tudo isso já
com o Python do venv.

Três coisas que economizam tempo depois:

- **Rode sempre com o Python do venv.** O `python` do PATH não tem PySide6.
- **`python tools/semear.py`** cria um banco de demonstração com duas semanas de
  uso. Sem ele, avaliar estante, planta ou bilhete exige usar o app por duas
  semanas de verdade.
- **`python tools/simular_uso.py` é o que cobre o QML** — o pytest não cobre.
  Rode depois de mexer em qualquer `.qml`, com a tela ligada e nos dois temas.

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

Quatro arquivos, cada um para um leitor diferente:

- **[docs/instalar-no-windows.md](docs/instalar-no-windows.md)** — instalar do
  zero no Windows, escrito para quem nunca abriu um terminal.
- **[docs/plataformas.md](docs/plataformas.md)** — o que é específico de cada
  sistema: por que não se gera executável, como confirmar que foi o Smart App
  Control que bloqueou, o pacote portátil, as bibliotecas que faltam numa Ubuntu
  limpa, o Anaconda desligando o OpenGL e os atalhos.
- **[docs/desenvolvimento.md](docs/desenvolvimento.md)** — os comandos, as
  ferramentas, a suíte, e como o log de eventos funciona por dentro.
- **[CLAUDE.md](CLAUDE.md)** — as regras de arquitetura em detalhe, incluindo o
  que deliberadamente não se faz aqui e por quê.

E **[docs/auditoria.md](docs/auditoria.md)**, que não é documentação de uso: são
as direções que sobraram da auditoria de 14/08/2026, algumas das quais não devem
ser feitas.
