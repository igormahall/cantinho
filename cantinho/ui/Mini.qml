import QtQuick
import theme
import "panels"

// Mini janela: o lembrete, e só.
//
// Frameless não tem barra de título, então o arrasto é manual. `Qt.Tool` a
// mantém fora da barra de tarefas — ela é um objeto na mesa, não uma janela
// que se gerencia.
//
// ## O que ela é
//
// Três coisas, nesta ordem de importância: **em que você está**, **há quanto
// tempo**, e **um botão para encerrar isso**. Nada mais. Tudo que é ajuste —
// o ciclo de três estados do som, o tema, o humor — mora na janela grande,
// porque configurar não é coisa que se faça num retângulo enquanto se trabalha
// em outra tela.
//
// ## Por que ela encolheu, e por que ela se abre
//
// Eram 300x112 com cinco controles à mostra: o principal no alto à direita e
// mais quatro numa fileira embaixo, também à direita. Duas bordas direitas
// desalinhadas, e **o quadrante inferior esquerdo completamente vazio** — não
// como respiro, mas porque a fileira era ancorada num canto de uma faixa de
// largura inteira. Muita janela para pouca informação, que é o oposto do que um
// lembrete deve ser.
//
// Agora ela tem dois estados. Em repouso são 264x82: o relógio, o nome do que
// está correndo e o botão que fecha aquilo. É isso que fica na frente do
// trabalho de outra pessoa o dia inteiro, e é tudo o que um lembrete precisa
// dizer. Quando o mouse chega — ou seja, quando alguém *vai* mexer — ela se
// abre e mostra o resto: parar, som, abrir, fechar.
//
// A escolha é essa: o custo de um clique a mais nos controles secundários, em
// troca de 36% menos janela ocupando a tela durante todas as horas em que
// ninguém vai tocar neles. Os secundários são secundários de fato — parar sem
// entregar é o fim menos comum, e som, abrir e fechar são decisões de momento,
// não coisas que se consultem com o olho.
Window {
    id: mini

    // Em repouso e aberta. A diferença é exatamente a fileira de controles.
    readonly property int alturaEmRepouso: 82
    readonly property bool aberta: sobre.hovered

    width: 264
    height: alturaEmRepouso + (aberta ? 36 : 0)

    // A janela cresce para baixo, com o conteúdo ancorado no topo: nada do que
    // já estava na tela muda de lugar quando ela se abre.
    Behavior on height {
        NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
    }

    visible: backend.miniVisible
    color: "transparent"
    title: "Cantinho"

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool

    onVisibleChanged: if (!visible) backend.setMiniVisible(false)

    Painel {
        id: corpo
        objectName: "corpoDaMini"
        anchors.fill: parent
        anchors.margins: 6

        // A mini fica por cima do trabalho de outra pessoa o dia inteiro. Opaca
        // ela é um retângulo colado na tela; translúcida, o que está embaixo
        // continua legível e ela vira um objeto apoiado ali.
        //
        // Firma quando o mouse chega, que é quando alguém vai de fato ler o
        // relógio ou apertar um botão.
        opacidadeFundo: sobre.hovered
                        ? Theme.opacidadePainel : Theme.opacidadeMini

        // Canto mais redondo que o dos painéis: numa janela sem moldura, o
        // raio é a única coisa que separa "objeto apoiado na tela" de
        // "retângulo colado nela".
        radius: 16

        // Sombra, como nos painéis que cobrem alguma coisa — e aqui ela cobre a
        // tela inteira de outra pessoa. É o que separa "janela flutuando" de
        // "retângulo pintado por cima do trabalho".
        sombra: true

        HoverHandler { id: sobre }

        // Frameless exige drag manual.
        DragHandler {
            target: null
            grabPermissions: PointerHandler.CanTakeOverFromAnything
            onActiveChanged: if (active) mini.startSystemMove()
        }

        // ------------------------------------------- relógio e ação principal
        //
        // O relógio à esquerda e o botão que encerra à direita, na mesma linha
        // e alinhados pelo meio. É a linha que responde "há quanto tempo" e
        // "como eu paro isto" de uma olhada só.

        Item {
            id: topo
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 8
            anchors.leftMargin: Theme.espaco
            anchors.rightMargin: 8
            height: 36

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: backend.elapsedText
                // Algarismos de largura fixa. Sem isto o relógio treme: na
                // Inter o "1" é mais estreito que o "0", então 00:00 e 11:11
                // não medem igual e o texto se mexe a cada segundo.
                font.features: Theme.digitos
                color: backend.timerRunning ? Theme.ambar : Theme.textoSuave
                font.pixelSize: Theme.destaque
                font.letterSpacing: 1
                Behavior on color { ColorAnimation { duration: Theme.gesto } }
            }

            // Um botão principal por vez, e ele diz o que vai acontecer com a
            // tarefa. "Entreguei" fecha a tarefa e põe o objeto na estante;
            // parar sem entregar mora na fileira que aparece no hover.
            BotaoSuave {
                objectName: "acaoDaMini"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: !backend.timerRunning ? "começar"
                      : backend.currentTaskId !== "" ? "entreguei" : "parar"
                destacado: true
                corAtiva: backend.timerRunning ? Theme.musgo : Theme.ambar
                tamanho: Theme.corpo
                onClicked: {
                    if (!backend.timerRunning)
                        backend.startFocused()
                    else if (backend.currentTaskId !== "")
                        backend.endSessionAndComplete()
                    else
                        backend.endSession(false, "")
                }
            }
        }

        // ---------------------------------------------------------- a tarefa
        //
        // A linha que responde "em que eu estou". É a razão de a mini existir:
        // sem ela, o relógio conta um tempo que não se sabe de quê.

        Item {
            id: linha
            anchors.top: topo.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 1
            anchors.leftMargin: Theme.espaco
            anchors.rightMargin: Theme.espaco
            height: 20

            // Trocar de tarefa aqui é avançar de uma em uma, e não abrir uma
            // lista: numa janela deste tamanho a lista cobriria o relógio, que
            // é a razão de a mini existir. Avançar resolve o caso real — pular
            // do item de cima para o de baixo sem chamar a janela grande.
            readonly property bool trocavel: !backend.timerRunning
                                             && backend.today.length > 1

            // O toque do quarto, aqui, não é painel: não há onde pôr um.
            //
            // Ele toma emprestada a faixa do nome da tarefa por alguns
            // segundos e devolve. Sem botões — os fins de sessão estão a um
            // centímetro dali, na própria mini.
            property string toque: ""

            Connections {
                target: backend
                function onNudged(frase) {
                    linha.toque = frase
                    relogioDoToque.restart()
                }
            }

            Timer {
                id: relogioDoToque
                interval: 12000
                onTriggered: linha.toque = ""
            }

            Text {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: linha.toque
                color: Theme.ambar
                font.pixelSize: Theme.miudo
                elide: Text.ElideRight
                opacity: linha.toque !== "" && backend.timerRunning ? 1 : 0
                visible: opacity > 0.01
                Behavior on opacity { NumberAnimation { duration: Theme.chegada } }
            }

            Text {
                id: nome
                objectName: "nomeNaMini"
                anchors.left: parent.left
                anchors.right: dica.left
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                // Sai de cena enquanto o quarto fala, e volta depois.
                opacity: linha.toque !== "" && backend.timerRunning ? 0 : 1
                visible: opacity > 0.01
                Behavior on opacity { NumberAnimation { duration: Theme.chegada } }
                text: backend.timerRunning
                      ? (backend.currentTaskLabel !== ""
                         ? backend.currentTaskLabel : "sessão livre")
                      : backend.freeSessionChosen
                        ? "sessão livre"
                        : backend.focusedTaskLabel !== ""
                          ? backend.focusedTaskLabel
                          : "nada no hoje"
                color: backend.timerRunning ? Theme.ambar
                       : (trocar.containsMouse ? Theme.ambar : Theme.textoSuave)
                font.pixelSize: Theme.miudo
                elide: Text.ElideRight
                Behavior on color { ColorAnimation { duration: Theme.reacao } }
            }

            Text {
                id: dica
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: "trocar"
                font.pixelSize: Theme.nano
                color: Theme.textoSuave
                opacity: linha.trocavel && trocar.containsMouse ? 0.9 : 0
                Behavior on opacity { NumberAnimation { duration: Theme.gesto } }
            }

            MouseArea {
                id: trocar
                anchors.fill: parent
                anchors.margins: -3
                hoverEnabled: true
                enabled: linha.trocavel
                cursorShape: Qt.PointingHandCursor
                onEntered: backend.sfx("toque")
                onClicked: {
                    backend.sfx("clique")
                    backend.focusNext()
                }
            }
        }

        // ------------------------------------------------- o resto, no hover
        //
        // Os quatro controles secundários. Só existem quando o mouse está na
        // janela — em repouso a mini é um lembrete, e lembrete com quatro
        // botões é um painel.
        //
        // Ocupam a largura inteira, distribuídos, e não amontoados num canto:
        // era a fileira ancorada à direita que deixava metade da faixa vazia.

        Item {
            id: controles
            anchors.top: linha.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            height: 34
            opacity: mini.aberta ? 1 : 0
            visible: opacity > 0.01
            Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                height: 1
                color: Theme.borda
                opacity: 0.5
            }

            Row {
                id: fileira
                anchors.centerIn: parent
                width: parent.width - 12
                spacing: 0

                // "Parar" só existe quando há o que parar sem entregar — ou
                // seja, com uma sessão correndo **e** presa a uma tarefa. Numa
                // sessão livre o botão principal já é "parar", e repeti-lo aqui
                // seria o mesmo gesto duas vezes na mesma janela.
                readonly property bool pararCabe: backend.timerRunning
                                                  && backend.currentTaskId !== ""

                // Cada um com a mesma fatia, o que os espalha de ponta a ponta
                // e acaba com o canto vazio de antes. A conta é sobre quantos
                // estão à mostra: com três, os três ocupam a largura inteira em
                // vez de deixarem um buraco onde o quarto estaria.
                readonly property int quantos: pararCabe ? 4 : 3
                readonly property real fatia: width / quantos

                // Parar sem entregar: o fim menos comum, porque quase toda
                // sessão que acaba, acaba porque a tarefa acabou.
                Item {
                    visible: fileira.pararCabe
                    width: visible ? fileira.fatia : 0
                    height: 26
                    BotaoSuave {
                        anchors.centerIn: parent
                        objectName: "pararNaMini"
                        text: "parar"
                        corAtiva: Theme.texto
                        onClicked: backend.endSession(false, "")
                    }
                }

                // Interruptor de duas posições, e não o ciclo de três do menu.
                //
                // Aqui não se configura o ambiente: cala-se o som porque
                // alguém entrou na sala, e devolve-se ele exatamente como
                // estava. Escolher entre "ambiente e toques" e "só os toques" é
                // decisão de quem está sentado no quarto, e o quarto é a janela
                // grande.
                Item {
                    width: fileira.fatia
                    height: 26
                    BotaoSuave {
                        anchors.centerIn: parent
                        text: backend.muted ? "mudo" : "som"
                        destacado: !backend.muted
                        corAtiva: Theme.musgo
                        onClicked: backend.toggleMute()
                    }
                }

                // Mostrar a principal já esconde a mini: as duas nunca ficam na
                // tela juntas. Ver os comentários em backend.py.
                Item {
                    width: fileira.fatia
                    height: 26
                    BotaoSuave {
                        anchors.centerIn: parent
                        objectName: "abrirNaMini"
                        text: "abrir"
                        onClicked: backend.showMain()
                    }
                }

                // O × some com tudo, não só com a mini — daqui não dá para
                // voltar para a janela grande sem passar pela bandeja, então
                // "fechar" tem que significar fechar.
                Item {
                    width: fileira.fatia
                    height: 26
                    BotaoSuave {
                        anchors.centerIn: parent
                        text: "×"
                        corAtiva: Theme.terracota
                        onClicked: backend.hideAll()
                    }
                }
            }
        }
    }
}
