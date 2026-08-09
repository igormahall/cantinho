import QtQuick
import theme
import "panels"

// Mini janela: o timer e nada mais, sempre por cima.
//
// Frameless não tem barra de título, então o arrasto é manual. `Qt.Tool` a
// mantém fora da barra de tarefas — ela é um objeto na mesa, não uma janela
// que se gerencia.
Window {
    id: mini

    width: 340
    height: 120
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

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: Theme.espaco
            anchors.rightMargin: Theme.espaco
            spacing: 2

            Text {
                text: backend.elapsedText
                color: backend.timerRunning ? Theme.ambar : Theme.textoSuave
                font.pixelSize: 32
                font.letterSpacing: 1
                Behavior on color { ColorAnimation { duration: 300 } }
            }

            Text {
                width: parent.width
                text: backend.timerRunning
                      ? (backend.currentTaskLabel !== ""
                         ? backend.currentTaskLabel : "sessão livre")
                      : "parado"
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
                elide: Text.ElideRight
            }
        }

        Row {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 8
            spacing: 2

            // Mesma dupla da barra grande: concluir a tarefa tem que caber no
            // mesmo lugar onde se encerra a sessão, senão a mini vira só um
            // relógio e obriga a abrir a janela para fechar o que se acabou de
            // fazer.
            BotaoSuave {
                text: "terminei"
                visible: backend.timerRunning && backend.currentTaskId !== ""
                destacado: true
                corAtiva: Theme.musgo
                onClicked: backend.endSessionAndComplete()
            }

            BotaoSuave {
                text: backend.timerRunning ? "encerrar" : "começar"
                destacado: !backend.timerRunning
                corAtiva: backend.timerRunning ? Theme.musgo : Theme.ambar
                onClicked: backend.timerRunning
                           ? backend.endSession(false, "")
                           : backend.startSession("")
            }

            BotaoSuave {
                text: backend.soundMode === "tudo" ? "som"
                      : backend.soundMode === "sussurro" ? "sussurro" : "mudo"
                destacado: backend.soundMode !== "mudo"
                corAtiva: Theme.musgo
                onClicked: backend.cycleSoundMode()
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
