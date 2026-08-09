import QtQuick
import theme

// Uma linha do menu do quarto: o nome do ajuste à esquerda, o estado atual à
// direita. Clicar em qualquer ponto da linha avança para o próximo estado.
//
// Sem caixa de seleção e sem interruptor: os ajustes daqui têm dois ou três
// estados e valor por extenso ("só os toques", "pelo relógio") diz mais do que
// um botão ligado ou desligado, sem precisar de rótulo explicando.
Item {
    id: linha

    property string rotulo: ""
    property string valor: ""
    property color cor: Theme.texto

    signal clicado()

    implicitHeight: 26

    Rectangle {
        anchors.fill: parent
        anchors.leftMargin: -8
        anchors.rightMargin: -8
        radius: Theme.raio
        color: area.pressed
               ? Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.16)
               : (area.containsMouse
                  ? Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.08)
                  : "transparent")
        Behavior on color { ColorAnimation { duration: Theme.reacao } }
    }

    Text {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        text: linha.rotulo
        color: area.containsMouse ? linha.cor : Theme.textoSuave
        font.pixelSize: Theme.miudo
        Behavior on color { ColorAnimation { duration: Theme.reacao } }
    }

    Text {
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: linha.valor
        color: linha.cor
        opacity: area.containsMouse ? 1.0 : 0.75
        font.pixelSize: Theme.miudo
        Behavior on opacity { NumberAnimation { duration: Theme.reacao } }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        anchors.margins: -4
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: backend.sfx("toque")
        onClicked: {
            backend.sfx("clique")
            linha.clicado()
        }
    }
}
