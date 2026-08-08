import QtQuick
import theme

// Botão sem moldura pesada: só texto que reage ao passar o mouse.
Item {
    id: botao

    property alias text: rotulo.text
    property color cor: Theme.textoSuave
    property color corAtiva: Theme.ambar
    property bool destacado: false
    property int tamanho: Theme.miudo

    signal clicked()

    implicitWidth: rotulo.implicitWidth + 20
    implicitHeight: rotulo.implicitHeight + 12

    Rectangle {
        anchors.fill: parent
        radius: Theme.raio
        color: area.containsMouse
               ? Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.10)
               : "transparent"
        Behavior on color { ColorAnimation { duration: 180 } }
    }

    Text {
        id: rotulo
        anchors.centerIn: parent
        font.pixelSize: botao.tamanho
        color: (botao.destacado || area.containsMouse) ? botao.corAtiva : botao.cor
        Behavior on color { ColorAnimation { duration: 180 } }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: botao.clicked()
    }
}
