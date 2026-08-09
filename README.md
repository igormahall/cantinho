# Cantinho

Um cômodo ilustrado que fica aberto enquanto você trabalha.

O timer é o motor de tudo. Ele alimenta um diário que se escreve sozinho, e
cada tarefa que você conclui deixa um objeto na estante. A planta no canto
cresce com as horas de foco das últimas duas semanas — e murcha sozinha se
você sumir, sem drama e sem cobrança.

![O cantinho à noite](docs/quarto-noite.png)

## O que ele não faz

Isso é metade do projeto, então vale dizer antes.

Não tem streak. Não tem barra de progresso, percentual, XP nem ranking. Não
tem gráfico na tela principal, nem notificação lembrando que você não abriu
ontem. Falhar não destrói nada — só não faz crescer.

Não tem conta, não tem nuvem, não tem sincronização e não manda nada para
lugar nenhum. O banco é um arquivo na sua máquina.

## O que fica na parede

O calendário do mês, um relógio de parede e um bilhete com a lista do dia. São
cenário, não painel: ficam atrás da luz do abajur, em opacidade baixa, e o
único que responde a clique é o bilhete — que abre a gaveta do "hoje".

O relógio não tem ponteiro de segundos, e o calendário não marca os dias em que
você trabalhou. Os dois seriam fáceis de fazer e os dois puxariam a tela para o
lugar errado: um vira cronômetro, o outro vira mapa de assiduidade.

No bilhete, o que você concluiu hoje fica na folha, riscado, até o dia virar.

## Os dois momentos

Em dia de semana o quarto segue o seu expediente: acende quando o turno começa
e vira noite quando ele termina, com uma travessia de três segundos entre um e
outro. Nunca corta seco. Fora disso vale o relógio — claro de dia, escuro à
noite. A jornada fica em `cantinho/core/schedule.py`, e dá para fixar o tema à
mão em **o quarto → luz**.

O relógio de parede ganha um traço âmbar onde o trecho atual termina: de manhã
é o almoço, à tarde é a hora de ir embora. Não é contagem regressiva — é uma
marca no mostrador, do tipo que se lê de relance e não mostra número nenhum.

![O cantinho de tarde, com o backlog aberto](docs/quarto-tarde.png)

## Rodando

Precisa de Python 3.10 ou mais novo. A única dependência de execução é o
PySide6.

```bash
git clone https://github.com/igormahall/cantinho.git
cd cantinho

python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
source .venv/bin/activate         # Linux

pip install -r requirements.txt
python -m cantinho.main
```

O `.venv/` não é versionado e não atravessa sistema: cada máquina cria o seu.
Rode sempre com o Python do venv — o `python` do PATH é o do sistema e não tem
PySide6.

### No Linux, antes do venv

O PySide6 vem do PyPI com o Qt inteiro dentro, mas não traz as bibliotecas de
sistema de que o Qt depende para falar com o X11 e com o áudio. Numa Ubuntu
22.04 recém-instalada faltam algumas, e a falha é sempre a mesma linha:

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though
it was found.
```

Não é erro do app — é biblioteca faltando. O conjunto que resolve:

```bash
sudo apt install python3-venv python3-dev \
     libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
     libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
     libxkbcommon-x11-0 libegl1 libgl1 libdbus-1-3
```

`libxcb-cursor0` é a que mais falta: o Qt 6 passou a exigi-la e ela não vem no
desktop padrão do 22.04. Para descobrir o que ainda falta em vez de adivinhar:

```bash
QT_DEBUG_PLUGINS=1 python -m cantinho.main
```

Se o app abrir mas ficar mudo, falta o áudio: `sudo apt install libpulse0`.

O resto é igual ao Windows: `python -m venv .venv`, `pip install -r
requirements.txt`, `python -m cantinho.main`.

### Duas diferenças no Linux

**O atalho global não funciona.** `Ctrl+Shift+C` para capturar ideia é a única
parte específica de plataforma que não tem equivalente: no Linux
`create_hotkey()` devolve um no-op deliberado, e a captura de ideia continua
disponível pelo mural, com a janela à vista.

**A bandeja depende do seu desktop.** O GNOME não mostra ícone de bandeja sem
extensão — no Ubuntu é a *AppIndicator and KStatusNotifierItem Support*, que
vem instalada e às vezes desligada. Isso importa porque fechar a janela **não**
encerra o app: ele fica na bandeja. Sem bandeja visível, o jeito de trazê-lo de
volta é abrir de novo pelo terminal, que a trava de instância única detecta e
usa para mostrar a janela que já existe. Para encerrar de verdade, **o quarto →
sair**.

O banco fica em `%APPDATA%\Cantinho` no Windows e `~/.local/share/cantinho` no
Linux — bancos independentes, que nunca sincronizam entre os dois sistemas.
Para experimentar sem sujar seus dados de verdade:

```bash
python -m cantinho.main --db ./teste.db --log DEBUG
```

Um banco por vez: abrir o mesmo banco duas vezes traz para a frente a janela
que já existe, em vez de subir uma segunda cópia. Bancos diferentes convivem —
é o que deixa você abrir um app de teste com o de verdade na bandeja.

### Como se usa

| | |
|---|---|
| **hoje** | escreva no campo de baixo e aperte Enter. Arraste para reordenar. |
| **começar** | prende o timer a uma tarefa. Ou clique em "começar" na barra para uma sessão solta. |
| **terminei** | encerra a sessão e conclui a tarefa de uma vez. É o que põe um objeto na estante. |
| **o círculo** | conclui a tarefa sem passar pelo timer. |
| **Ctrl+Shift+C** | guarda uma ideia de qualquer lugar, mesmo com o app escondido. |
| **ideias** | o mural. A ideia que virar tarefa continua lá, riscada. |
| **o dia** | as sessões de hoje, o total, o humor e a nota. Aberto a qualquer hora. |
| **mini** | troca a janela por uma janelinha só com o timer, sempre por cima. Arrasta pelo corpo. |
| **o quarto** | luz, som, como está o dia e a saída do app. |

As duas janelas nunca ficam na tela juntas: a mini substitui a grande e vice-versa.
Minimizar a janela grande também traz a mini — o timer continua num canto em vez de
sumir na barra de tarefas.

Fechar a janela não encerra o app: ele continua na bandeja, ao lado do relógio.
Para encerrar de verdade, **o quarto → sair**, que pergunta antes.

O som tem três estados, girando no mesmo lugar: **ambiente e toques**,
**só os toques** — o quarto cala a chuva mas o clique continua respondendo, para
quando alguém está numa chamada — e **nenhum**.

### Um quarto para olhar

O app novo abre um quarto vazio, que é honesto mas não mostra grande coisa.
Para ver a estante ocupada e a planta crescida sem esperar duas semanas:

```bash
python tools/semear.py                          # escreve em build/demo.db
python tools/semear.py --de-novo                # refaz um já semeado
python -m cantinho.main --db build/demo.db
```

Semear duas vezes no mesmo banco empilharia duas semanas sobre outras duas, e a
ferramenta se recusa a fazer isso. Se o banco tiver eventos vindos do app de
verdade, ela recusa mesmo com `--de-novo`.

A semeadura escreve pelos construtores de evento de verdade, com o relógio
deslocado para trás. O banco que sai dali é um log legítimo, não um fixture.

## Executável portátil

Para o pendrive, para a máquina do trabalho, para onde não dá para instalar
nada:

```bash
pip install -r requirements-dev.txt
pyinstaller cantinho.spec --noconfirm
```

Sai uma pasta `dist/Cantinho/` de uns 200 MB que roda sem instalação e sem
admin. O build é por plataforma: o do Windows não serve no Linux e vice-versa.

```powershell
.\dist\Cantinho\Cantinho.exe                        # seu banco de verdade
.\dist\Cantinho\Cantinho.exe --db ~/cantinho/x.db   # um banco à parte
```

### Quando o antivírus apaga o executável

Acontece, e não é acaso: o executável do PyInstaller é um *bootloader* genérico
igual em todo programa empacotado com ele, e sem assinatura de editor não tem
como se distinguir do malware que usa o mesmo empacotador.

Para esse caso existe um segundo empacotador, que não gera binário nenhum — ele
monta o app sobre o `python.exe` oficial da Python Software Foundation, que já
vem assinado:

```powershell
python tools/empacotar_portatil.py     # Cantinho-portatil-windows.zip
```

O porquê, o passo a passo em máquina corporativa e o que fazer se ainda assim
for bloqueado estão em **[docs/fabrica.md](docs/fabrica.md)**.

## Desenvolvimento

Com o venv ativado — sem isso, `python` é o do sistema e não tem PySide6:

```bash
pip install -r requirements-dev.txt

python -m pytest                # 272 testes, sem abrir janela
python tools/simular_uso.py     # percorre a interface clicando de verdade
python tools/check_svg.py       # rasteriza os SVGs em build/svg_check/
python tools/semear.py          # banco descartável com duas semanas de uso
python tools/gerar_audio.py     # regera os sons
python tools/gerar_icone.py     # regera o ícone do app
python tools/gerar_capturas.py  # regera as imagens deste README
```

O `pytest` não cobre o QML. Quem faz isso é o `simular_uso.py`: ele abre as
janelas, cria tarefa, roda sessão, conclui, arrasta, captura ideia, transforma
ideia em tarefa, estica a janela e fecha o dia com mouse e teclado sintéticos,
depois reabre o banco do zero e confere o log evento por evento. Rode depois de
mexer em qualquer `.qml`.

Áudio, ícone e capturas são gerados e versionados prontos, para que um clone
limpo funcione sem etapa extra de build. Os três geradores são determinísticos
o bastante para que uma mudança no `git status` depois de rodá-los signifique
que o código mudou, não que o resultado variou.

### Por dentro

Só existe uma tabela, `events`, e ela só recebe `INSERT`. Backlog, sessões,
estante, planta, mural e histórico não são guardados: são recalculados a partir
do log toda vez, por funções puras. Corrigir alguma coisa é acrescentar um
evento novo, nunca editar o que já passou.

Isso significa que o estado da tela nunca pode divergir do que está em disco —
e que apagar o arquivo de banco é a única forma de perder alguma coisa.

É também o que dá o mural de graça: "essa ideia virou tarefa" não é um campo
que muda, é um evento posterior que aponta para a tarefa que nasceu.

```
cantinho/
  core/       events.py store.py projections.py clock.py    (sem Qt)
  services/   scene.py timer.py audio.py hotkey.py tray.py
              single_instance.py                            (plataforma)
  backend.py  a fronteira entre o log e a interface
  ui/         Main.qml Mini.qml theme/ room/ panels/
```

O ícone é o próprio vaso do quarto: nos tamanhos grandes ele aparece sobre um
ladrilho com a luz do abajur atrás, e nos pequenos o ladrilho sai para a planta
caber. Na bandeja ele é vivo — acompanha o crescimento da planta.

O som é sintetizado, não gravado: `tools/gerar_audio.py` monta chuva, acorde e
estalo de vinil com a biblioteca padrão do Python, mais os três estalos curtos
que respondem ao mouse. Os SVGs do cenário têm camadas com os mesmos ids nos
dois temas, o que deixa a planta e a estante mudarem sem redesenhar o quarto.

`CLAUDE.md` tem as regras de arquitetura em detalhe, incluindo o que
deliberadamente não se faz aqui e por quê.
