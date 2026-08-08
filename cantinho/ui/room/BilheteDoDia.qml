import QtQuick
import theme

// A lista do dia, num papel pregado na parede.
//
// A lista precisava aparecer sem virar tela de lista. A saída foi tirá-la da
// interface e pôr no cenário: um bilhete escrito à mão, do tamanho de um
// bilhete, na parede acima da mesa. Ele não pede nada, não cobra nada e não
// tem botão — quem quiser mexer clica e a gaveta abre.
//
// O que foi feito hoje fica na folha, riscado, até o dia virar. Riscar à mão é
// o gesto que a barra de progresso substituiu por um número; aqui ele volta a
// ser o gesto.
FolhaDeParede {
    id: bilhete

    readonly property real larguraBase: 276
    readonly property real alturaBase: 168
    readonly property real margem: 16

    // Linhas prontas, vindas do backend: abertas primeiro, concluídas de hoje
    // riscadas no fim.
    property var linhas: []
    property string tarefaAtual: ""

    signal aberto()

    width: larguraBase * unidade
    height: alturaBase * unidade
    inclinacao: 1.4
    destaque: area.containsMouse ? 1.0 : 0.0

    Column {
        x: bilhete.margem * bilhete.unidade
        y: bilhete.margem * bilhete.unidade
        width: parent.width - 2 * x
        spacing: 2 * bilhete.unidade

        Text {
            bottomPadding: 4 * bilhete.unidade
            text: "hoje"
            color: Theme.textoSuave
            opacity: 0.7
            font.pixelSize: Math.round(10 * bilhete.unidade)
            font.letterSpacing: 1.6 * bilhete.unidade
        }

        Text {
            width: parent.width
            visible: bilhete.linhas.length === 0
            text: "o dia ainda está em branco"
            color: Theme.textoSuave
            opacity: 0.5
            font.pixelSize: Math.round(11 * bilhete.unidade)
            font.italic: true
        }

        Repeater {
            model: bilhete.linhas

            Row {
                required property var modelData

                readonly property bool feita: modelData.done
                readonly property bool emCurso: !feita
                                                && modelData.id === bilhete.tarefaAtual

                width: parent.width
                height: 16 * bilhete.unidade
                spacing: 7 * bilhete.unidade

                // Marca de item: círculo vazio enquanto está aberto, cheio
                // depois. É o mesmo círculo do backlog, reduzido.
                Item {
                    width: 7 * bilhete.unidade
                    height: parent.height

                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width
                        height: width
                        radius: width / 2
                        color: feita ? Theme.musgo
                               : (emCurso ? Theme.ambar : "transparent")
                        border.width: Math.max(1, 1.2 * bilhete.unidade)
                        border.color: feita ? Theme.musgo
                                      : (emCurso ? Theme.ambar : Theme.textoSuave)
                        opacity: feita ? 0.55 : 0.8
                        Behavior on color { ColorAnimation { duration: 400 } }
                    }
                }

                Text {
                    width: parent.width - 14 * bilhete.unidade
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: emCurso ? Theme.ambar : Theme.texto
                    opacity: feita ? 0.42 : (emCurso ? 1.0 : 0.78)
                    font.pixelSize: Math.round(12 * bilhete.unidade)
                    font.strikeout: feita
                    elide: Text.ElideRight
                    Behavior on opacity { NumberAnimation { duration: 400 } }
                }
            }
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: backend.sfx("toque")
        onClicked: {
            backend.sfx("clique")
            bilhete.aberto()
        }
    }
}
