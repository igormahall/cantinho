import QtQuick
import theme
import "panels"

// Mini janela: o timer e nada mais, sempre por cima.
//
// Frameless não tem barra de título, então o arrasto é manual. `Qt.Tool` a
// mantém fora da barra de tarefas — ela é um objeto na mesa, não uma janela
// que se gerencia.
//
// O conceito é "o app reduzido ao gesto": ver o relógio, trocar de tarefa,
// encerrar. Tudo o que é ajuste — o ciclo de três estados do som, o tema, o
// humor — mora na janela grande, porque configurar não é coisa que se faça num
// retângulo de 300 pixels enquanto se trabalha em outra tela.
//
// A largura caiu de 340 para 300 e o conteúdo virou três faixas empilhadas. Na
// versão anterior o nome da tarefa ocupava a largura inteira e os botões
// ficavam ancorados por cima dele — com uma tarefa de nome comprido, o texto
// passava por baixo de "terminei" e os dois viravam um borrão.
Window {
    id: mini

    width: 300
    height: 112
    visible: backend.miniVisible
    color: "transparent"
    title: "Cantinho"

    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool

    onVisibleChanged: if (!visible) backend.setMiniVisible(false)

    Painel {
        id: corpo
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

        HoverHandler { id: sobre }

        // Frameless exige drag manual.
        DragHandler {
            target: null
            grabPermissions: PointerHandler.CanTakeOverFromAnything
            onActiveChanged: if (active) mini.startSystemMove()
        }

        // ------------------------------------------- relógio e ação principal

        Item {
            id: topo
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 10
            anchors.leftMargin: Theme.espaco
            anchors.rightMargin: 8
            height: 34

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: backend.elapsedText
                color: backend.timerRunning ? Theme.ambar : Theme.textoSuave
                font.pixelSize: 30
                font.letterSpacing: 1
                Behavior on color { ColorAnimation { duration: 300 } }
            }

            // Um botão principal por vez, e ele diz o que vai acontecer com a
            // tarefa. "Entreguei" fecha a tarefa e põe o objeto na estante;
            // parar sem entregar é o botão discreto do rodapé.
            BotaoSuave {
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

        Item {
            id: linha
            anchors.top: topo.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 2
            anchors.leftMargin: Theme.espaco
            anchors.rightMargin: Theme.espaco
            height: 20

            // Trocar de tarefa aqui é avançar de uma em uma, e não abrir uma
            // lista: numa janela deste tamanho a lista cobriria o relógio, que
            // é a razão de a mini existir. Avançar resolve o caso real — pular
            // do item de cima para o de baixo sem chamar a janela grande.
            readonly property bool trocavel: !backend.timerRunning
                                             && backend.today.length > 1

            Text {
                id: nome
                anchors.left: parent.left
                anchors.right: dica.left
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
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
                font.pixelSize: 10
                color: Theme.textoSuave
                opacity: linha.trocavel && trocar.containsMouse ? 0.9 : 0
                Behavior on opacity { NumberAnimation { duration: 160 } }
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

        // ---------------------------------------------------------- o rodapé

        Row {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 8
            anchors.bottomMargin: 6
            spacing: 0

            // Parar sem entregar. Fica aqui, pequeno, porque é o fim menos
            // comum: quase toda sessão que acaba, acaba porque a tarefa acabou.
            BotaoSuave {
                text: "parar"
                visible: backend.timerRunning && backend.currentTaskId !== ""
                corAtiva: Theme.texto
                onClicked: backend.endSession(false, "")
            }

            // Interruptor de duas posições, e não o ciclo de três do menu.
            //
            // Aqui não se configura o ambiente: cala-se o som porque alguém
            // entrou na sala, e devolve-se ele exatamente como estava. Escolher
            // entre "ambiente e toques" e "só os toques" é decisão de quem está
            // sentado no quarto, e o quarto é a janela grande.
            BotaoSuave {
                text: backend.muted ? "mudo" : "som"
                destacado: !backend.muted
                corAtiva: Theme.musgo
                onClicked: backend.toggleMute()
            }

            // Mostrar a principal já esconde a mini: as duas nunca ficam na
            // tela juntas. Ver os comentários em backend.py.
            BotaoSuave {
                text: "abrir"
                onClicked: backend.showMain()
            }

            // O × some com tudo, não só com a mini — daqui não dá para voltar
            // para a janela grande sem passar pela bandeja, então "fechar" tem
            // que significar fechar.
            BotaoSuave {
                text: "×"
                corAtiva: Theme.terracota
                onClicked: backend.hideAll()
            }
        }
    }
}
