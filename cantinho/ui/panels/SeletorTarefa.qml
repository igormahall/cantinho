import QtQuick
import theme

// "O que vem agora": a lista curta que abre acima da barra.
//
// Existe porque o botão "começar" precisava saber o que começar. Antes ele
// abria sempre uma sessão livre, e prender o timer a uma tarefa só era possível
// mirando a palavra "começar" dentro da linha certa do painel "hoje" — um gesto
// escondido dentro de outro. Quem apertava o botão grande, que é o óbvio,
// gravava tempo solto que nem podia ser concluído.
//
// A lista é a do "hoje", no máximo cinco linhas, mais a sessão livre no fim.
// Ela continua sendo um uso legítimo: às vezes o trabalho não estava na lista.
Painel {
    id: seletor

    property var tarefas: []
    property string escolhida: ""
    property bool livre: false
    property bool aberto: false

    signal escolher(string taskId)

    width: 300
    height: coluna.height + 2 * Theme.espaco

    opacity: aberto ? 1 : 0
    visible: opacity > 0.01
    Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

    // Uma linha da escolha. Marca à esquerda, rótulo, nada mais.
    component Escolha: Item {
        id: linha

        property string rotulo: ""
        property bool marcada: false
        property bool discreta: false

        signal ativada()

        width: parent.width
        height: 28

        Rectangle {
            anchors.fill: parent
            anchors.leftMargin: -6
            anchors.rightMargin: -6
            radius: Theme.raio
            color: area.containsMouse
                   ? Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.10)
                   : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.reacao } }
        }

        Rectangle {
            id: marca
            anchors.verticalCenter: parent.verticalCenter
            width: 7; height: 7; radius: 4
            color: linha.marcada ? Theme.ambar : "transparent"
            border.width: 1.2
            border.color: linha.marcada ? Theme.ambar : Theme.textoSuave
            opacity: linha.marcada ? 1.0 : 0.55
            Behavior on color { ColorAnimation { duration: Theme.gesto } }
        }

        Text {
            anchors.left: marca.right
            anchors.leftMargin: 10
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: linha.rotulo
            color: linha.marcada ? Theme.ambar : Theme.texto
            opacity: linha.discreta && !linha.marcada ? 0.6 : 1.0
            font.pixelSize: Theme.miudo
            font.italic: linha.discreta
            elide: Text.ElideRight
        }

        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onEntered: backend.sfx("toque")
            onClicked: {
                backend.sfx("clique")
                linha.ativada()
            }
        }
    }

    Column {
        id: coluna
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.espaco
        spacing: 1

        Text {
            text: "o que vem agora"
            color: Theme.textoSuave
            font.pixelSize: 11
            bottomPadding: 4
        }

        Text {
            width: parent.width
            visible: seletor.tarefas.length === 0
            text: "o hoje está vazio"
            color: Theme.textoSuave
            opacity: 0.7
            font.pixelSize: Theme.miudo
            font.italic: true
            bottomPadding: 4
        }

        Repeater {
            model: seletor.tarefas

            Escolha {
                required property var modelData
                rotulo: modelData.label
                marcada: modelData.id === seletor.escolhida && !seletor.livre
                onAtivada: seletor.escolher(modelData.id)
            }
        }

        Item { width: 1; height: 4 }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.borda
        }

        Item { width: 1; height: 4 }

        Escolha {
            rotulo: "sessão livre"
            discreta: true
            marcada: seletor.livre
            onAtivada: seletor.escolher("")
        }
    }
}
