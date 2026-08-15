import QtQuick
import theme

// O campo que guarda uma ideia e some.
//
// Zero categorização no momento da captura: escreve e aperta Enter. O que ele
// não faz é perguntar em qual projeto, para quando, ou se vira tarefa — isso é
// decisão de outro dia, e o mural é onde ela acontece.
//
// Quem abre isto costuma estar no meio de outra coisa: ou pelo atalho global,
// com o app escondido, ou por Ctrl+Shift+I com a janela à vista. Por isso o
// campo já vem limpo e com o cursor dentro.
Item {
    id: captura

    anchors.fill: parent
    property bool aberta: false

    onAbertaChanged: {
        if (aberta) {
            entrada.limpar()
            entrada.focar()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: captura.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        MouseArea {
            anchors.fill: parent
            onClicked: captura.aberta = false
        }
    }

    Painel {
        id: painel

        width: 520
        height: 120
        anchors.horizontalCenter: parent.horizontalCenter
        y: captura.aberta ? parent.height / 3 : -height
        opacity: captura.aberta ? 1 : 0
        visible: opacity > 0.01

        Behavior on y { NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        Column {
            anchors.fill: parent
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            Text {
                text: "guardar uma ideia"
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
            }

            CampoTexto {
                id: entrada
                width: parent.width
                limite: backend.textLimit
                placeholder: "escreva e aperte Enter"
                onAceito: function (texto) {
                    backend.captureIdea(texto)
                    captura.aberta = false
                }
            }
        }

        Keys.onEscapePressed: captura.aberta = false
    }
}
