import QtQuick
import theme

// Campo de texto próprio em vez de QtQuick.Controls: o TextField estilizado
// puxa um tema de Controls inteiro, e aqui só se quer uma linha com sublinhado.
Item {
    id: campo

    property alias text: entrada.text
    property string placeholder: ""
    property alias entradaAtiva: entrada.activeFocus

    signal aceito(string texto)

    implicitHeight: 34

    function limpar() { entrada.text = "" }
    function focar() { entrada.forceActiveFocus() }

    TextInput {
        id: entrada
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.bottomMargin: 6
        color: Theme.texto
        font.pixelSize: Theme.corpo
        selectionColor: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.35)
        selectedTextColor: Theme.texto
        clip: true

        onAccepted: {
            var limpo = text.trim()
            if (limpo.length > 0)
                campo.aceito(limpo)
        }
    }

    Text {
        anchors.fill: entrada
        verticalAlignment: Text.AlignVCenter
        text: campo.placeholder
        color: Theme.textoSuave
        font.pixelSize: Theme.corpo
        visible: entrada.text.length === 0
        opacity: 0.75
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: entrada.activeFocus ? Theme.ambar : Theme.borda
        Behavior on color { ColorAnimation { duration: 200 } }
    }
}
