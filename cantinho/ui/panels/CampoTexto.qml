import QtQuick
import theme

// Campo de texto próprio em vez de QtQuick.Controls: o TextField estilizado
// puxa um tema de Controls inteiro, e aqui só se quer uma linha com sublinhado.
Item {
    id: campo

    property alias text: entrada.text
    property string placeholder: ""
    property alias entradaAtiva: entrada.activeFocus

    // Quanto o campo aceita, e não quanto ele mostra. O log é append-only: o
    // que entra fica para sempre e é relido em toda abertura, então o texto
    // colado por engano não é um erro que se conserta depois. Recusar aqui é o
    // jeito silencioso de impedir isso — o campo simplesmente para de crescer,
    // sem aviso, sem diálogo. O backend ainda corta por conta própria, porque
    // nem todo texto chega por um campo. Ver `LABEL_LIMIT` e `TEXT_LIMIT`.
    property alias limite: entrada.maximumLength

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
        Behavior on color { ColorAnimation { duration: Theme.gesto } }
    }
}
