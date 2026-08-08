import QtQuick
import theme

// Cinco pontos em vez de slider com número. Humor não tem unidade.
Item {
    id: escala

    property string rotulo: ""
    property int valor: 3
    property int total: 5

    signal escolhido(int valor)

    implicitHeight: 26

    Text {
        id: nome
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        text: escala.rotulo
        color: Theme.textoSuave
        font.pixelSize: Theme.miudo
        width: 60
    }

    Row {
        anchors.left: nome.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        Repeater {
            model: escala.total

            Rectangle {
                width: 14
                height: 14
                radius: 7
                color: (index + 1) <= escala.valor ? Theme.ambar : "transparent"
                border.width: 1.5
                border.color: (index + 1) <= escala.valor ? Theme.ambar : Theme.textoSuave
                opacity: ponto.containsMouse ? 1 : 0.85
                Behavior on color { ColorAnimation { duration: 160 } }

                MouseArea {
                    id: ponto
                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: escala.escolhido(index + 1)
                }
            }
        }
    }
}
