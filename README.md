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

## Rodando

Precisa de Python 3.10+. A única dependência de execução é o PySide6.

**Windows** — `cantinho.bat` faz tudo. Duplo clique abre um menu; da linha de
comando aceita `instalar`, `rodar`, `empacotar`, `atualizar`, `portatil`,
`testar` e `refazer`. É o mesmo script para a primeira instalação e para
atualizar depois.

**Linux** — o caminho manual:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m cantinho.main
```

Rode sempre com o Python do venv; o `python` do PATH não tem PySide6. Numa
Ubuntu limpa faltam algumas bibliotecas de sistema antes disso.

O banco fica em `%APPDATA%\Cantinho` no Windows e `~/.local/share/cantinho` no
Linux. Um banco por vez: abrir o mesmo duas vezes traz para a frente a janela
que já existe.

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

- **[docs/windows.md](docs/windows.md)** — empacotar para Windows, as duas
  formas, e o que fazer quando o antivírus implica com o executável.
- **[docs/linux.md](docs/linux.md)** — as bibliotecas de sistema que faltam
  numa Ubuntu limpa, o Anaconda desligando o OpenGL, e o atalho na grade.
- **[docs/desenvolvimento.md](docs/desenvolvimento.md)** — rodar a suíte,
  as ferramentas, e como o log de eventos funciona por dentro.
- **[CLAUDE.md](CLAUDE.md)** — as regras de arquitetura em detalhe, incluindo
  o que deliberadamente não se faz aqui e por quê.
