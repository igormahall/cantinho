import QtQuick
import theme

// Depois de uma sessão longa, o app pergunta uma coisa só.
//
// Uma hora raramente é uma coisa só: no meio dela chega o pedido urgente,
// resolve-se o e-mail que travava outra pessoa, termina-se o que já estava quase
// pronto. Nada disso vira entrega, porque o gesto de registrar acontece no fim
// da sessão e a essa altura já se esqueceu.
//
// A pergunta oferece crédito por trabalho já feito, e é isso que a separa de
// cobrança: "só isso" fecha sem custo nenhum, e é a resposta que o Escape e o
// clique fora também dão.
//
// Aceita mais de uma resposta de propósito — em duas horas cabe mais de uma
// coisa —, então o painel fica aberto e a lista vai encurtando.
Item {
    id: pergunta

    anchors.fill: parent
    property bool aberta: false

    Connections {
        target: backend

        // Os minutos chegam no sinal e não são usados, e isso é decisão.
        //
        // O texto do painel não traz número nenhum de propósito: "foi um bom
        // tempo por aqui" convida, "você ficou 75 minutos" mede. O tempo da
        // sessão já está no bilhete da parede e no painel do dia, para quem
        // quiser olhar — aqui ele viraria a cobrança que a pergunta existe para
        // não ser.
        function onExtraAsked(minutos) { pergunta.aberta = true }
    }

    // O véu. Escurece o quarto inteiro, e clicar nele é a mesma resposta que
    // "só isso" — fechar sem custo.
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: pergunta.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        MouseArea {
            anchors.fill: parent
            onClicked: pergunta.aberta = false
        }
    }

    Painel {
        id: painel
        // Nomeado para `tools/simular_uso.py` procurar só aqui dentro: os
        // rótulos das tarefas aparecem no bilhete da parede ao mesmo tempo, e
        // um clique que erra o painel acerta o véu e o fecha.
        objectName: "extra"

        width: 460
        height: coluna.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        y: pergunta.aberta ? parent.height / 5 : parent.height / 5 - 16
        opacity: pergunta.aberta ? 1 : 0
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
                width: parent.width
                wrapMode: Text.WordWrap
                color: Theme.texto
                font.pixelSize: Theme.titulo
                text: "foi um bom tempo por aqui"
            }

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
                text: "Fechou mais alguma coisa nesse meio-tempo? Vale o que não estava "
                      + "na lista — o que apareceu no caminho conta igual."
            }

            // As tarefas abertas, para marcar as que também acabaram. Cada uma
            // que se marca sai da lista, e o painel continua aberto.
            Column {
                width: parent.width
                spacing: 2
                visible: backend.today.length > 0

                Repeater {
                    model: backend.today

                    delegate: Item {
                        width: parent.width
                        height: 30

                        HoverHandler { id: sobre }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: -2
                            radius: Theme.raio
                            color: sobre.hovered
                                   ? Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b, 0.45)
                                   : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.reacao } }
                        }

                        Rectangle {
                            id: circulo
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            width: 14; height: 14; radius: 7
                            color: "transparent"
                            border.width: 1.5
                            border.color: sobre.hovered ? Theme.musgo : Theme.textoSuave
                            Behavior on border.color { ColorAnimation { duration: Theme.reacao } }
                        }

                        Text {
                            anchors.left: circulo.right
                            anchors.leftMargin: 10
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.label
                            color: Theme.texto
                            font.pixelSize: Theme.corpo
                            elide: Text.ElideRight
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: backend.sfx("toque")
                            onClicked: {
                                backend.sfx("entrega")
                                backend.completeTask(modelData.id)
                            }
                        }
                    }
                }
            }

            // E o que nunca esteve na lista. Nasce e é concluída no mesmo
            // gesto: criar a tarefa para marcá-la em seguida faria a linha
            // piscar no "hoje" no meio do caminho.
            CampoTexto {
                width: parent.width
                limite: backend.labelLimit
                placeholder: "ou escreva o que apareceu no caminho"
                onAceito: function (texto) {
                    backend.addAndCompleteTask(texto)
                    limpar()
                }
            }

            Row {
                anchors.right: parent.right
                spacing: 4

                BotaoSuave {
                    text: "só isso"
                    destacado: true
                    tamanho: Theme.corpo
                    onClicked: pergunta.aberta = false
                }
            }
        }

        Keys.onEscapePressed: pergunta.aberta = false
    }
}
