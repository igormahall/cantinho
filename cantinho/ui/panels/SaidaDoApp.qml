import QtQuick
import theme

// Fechar a janela deixa o app na bandeja, o que é o comportamento certo mas não
// dá jeito de encerrar de verdade sem ir até o ícone. A confirmação existe
// porque a diferença entre "esconder" e "encerrar" não é óbvia: quem clica em
// sair esperando o primeiro fecha o app inteiro.
//
// A sessão aberta, essa, é guardada de qualquer jeito — a ligação é no
// `aboutToQuit` da aplicação e não neste botão, porque há três caminhos para
// fora e só um passa por aqui. Ver `endOpenSession` no backend.
Item {
    id: saida

    anchors.fill: parent
    property bool aberta: false

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: saida.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        MouseArea {
            anchors.fill: parent
            onClicked: saida.aberta = false
        }
    }

    Painel {
        id: painel

        width: 380
        height: coluna.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        y: saida.aberta ? parent.height / 3 : parent.height / 3 - 16
        opacity: saida.aberta ? 1 : 0
        visible: opacity > 0.01

        Behavior on y { NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        Column {
            id: coluna
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            Text {
                text: "fechar o cantinho?"
                color: Theme.texto
                font.pixelSize: Theme.titulo
            }

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
                text: backend.timerRunning
                      ? "Tem uma sessão correndo. Ela é guardada no diário antes de sair."
                      : "Nada se perde. Fechar a janela sozinha deixa o app na bandeja."
            }

            Row {
                spacing: 4
                anchors.right: parent.right

                BotaoSuave {
                    text: "ficar"
                    onClicked: saida.aberta = false
                }

                BotaoSuave {
                    text: "sair"
                    destacado: true
                    corAtiva: Theme.terracota
                    tamanho: Theme.corpo
                    onClicked: backend.requestQuit()
                }
            }
        }

        Keys.onEscapePressed: saida.aberta = false
    }
}
