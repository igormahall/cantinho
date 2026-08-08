import QtQuick
import theme

// Backlog leve: sem projeto aninhado, sem prazo, sem contagem.
//
// Os cinco primeiros são "Hoje". O limite não é enfeite: uma lista de hoje que
// aceita tudo deixa de ser uma lista de hoje. Passou de cinco, o resto fica
// visivelmente mais apagado, embaixo de uma linha.
Item {
    id: raiz

    property var tarefas: []
    property int limiteHoje: 5
    property string tarefaAtual: ""

    signal iniciar(string taskId)
    signal concluir(string taskId)
    signal arquivar(string taskId)
    signal reordenar(var ids)

    // O modelo é reconstruído a partir do backend, exceto durante um arrasto:
    // reconstruir no meio do gesto faria o item sumir da mão do usuário.
    property bool arrastando: false

    onTarefasChanged: if (!arrastando) recarregar()
    Component.onCompleted: recarregar()

    function recarregar() {
        modelo.clear()
        for (var i = 0; i < tarefas.length; i++) {
            modelo.append({
                "taskId": tarefas[i].id,
                "label": tarefas[i].label,
                "project": tarefas[i].project
            })
        }
    }

    function publicarOrdem() {
        var ids = []
        for (var i = 0; i < modelo.count; i++)
            ids.push(modelo.get(i).taskId)
        raiz.reordenar(ids)
    }

    ListModel { id: modelo }

    Text {
        id: vazio
        anchors.centerIn: parent
        width: parent.width - 40
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        visible: modelo.count === 0
        text: "Nada por aqui ainda.\nEscreva embaixo o que quiser fazer."
        color: Theme.textoSuave
        font.pixelSize: Theme.corpo
        lineHeight: 1.4
    }

    ListView {
        id: lista
        anchors.fill: parent
        spacing: 4
        model: modelo
        clip: true
        cacheBuffer: 400

        delegate: Item {
            id: envelope
            width: lista.width
            height: 46

            property int indiceVisual: index

            // Divisória entre "Hoje" e o resto do backlog.
            Rectangle {
                width: parent.width - 8
                height: 1
                color: Theme.borda
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                visible: index === raiz.limiteHoje
            }

            // Altura de uma linha, usada para converter o quanto o cartão
            // subiu ou desceu em quantas posições ele andou.
            readonly property int passo: envelope.height + lista.spacing

            function repousar() {
                cartao.y = Qt.binding(function () {
                    return index === raiz.limiteHoje ? 4 : 0
                })
            }

            Rectangle {
                id: cartao
                width: envelope.width
                height: 42
                y: index === raiz.limiteHoje ? 4 : 0
                z: arraste.drag.active ? 2 : 0
                radius: Theme.raio
                color: arraste.drag.active
                       ? Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.16)
                       : (hover.hovered
                          ? Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b, 0.45)
                          : "transparent")
                // Fora do "Hoje" o item existe, mas não pede atenção.
                opacity: index < raiz.limiteHoje ? 1.0 : 0.5
                Behavior on color { ColorAnimation { duration: 150 } }

                HoverHandler { id: hover }

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    spacing: 10

                    // Círculo de concluir. Clicar aqui é o que coloca um
                    // objeto na estante.
                    Item {
                        id: marcador
                        width: 20
                        height: parent.height

                        // Trava depois do primeiro clique: a conclusão é
                        // adiada para o anel aparecer, e sem isto um clique
                        // duplo gravaria dois `task.completed`.
                        property bool concluindo: false

                        // O anel precisa de um instante para se abrir, e a
                        // linha some no momento em que a tarefa é concluída.
                        // Duzentos milissegundos não se percebem como atraso e
                        // são o bastante para o gesto ter uma resposta.
                        Timer {
                            id: adiar
                            interval: 200
                            onTriggered: raiz.concluir(model.taskId)
                        }

                        Rectangle {
                            id: circulo
                            anchors.centerIn: parent
                            width: 15; height: 15; radius: 8
                            color: "transparent"
                            border.width: 1.5
                            border.color: marcar.containsMouse ? Theme.musgo : Theme.textoSuave
                            scale: marcar.containsMouse ? 1.15 : 1.0
                            Behavior on border.color { ColorAnimation { duration: 150 } }
                            Behavior on scale {
                                NumberAnimation {
                                    duration: Theme.reacao
                                    easing.type: Easing.OutBack
                                    easing.overshoot: 2.2
                                }
                            }

                            Rectangle {
                                anchors.centerIn: parent
                                width: 7; height: 7; radius: 4
                                color: Theme.musgo
                                opacity: marcar.containsMouse ? 1 : 0
                                Behavior on opacity { NumberAnimation { duration: 150 } }
                            }

                            // O anel que se abre ao concluir. Dura menos de meio
                            // segundo e some junto com a linha — é o adeus da
                            // tarefa, não uma comemoração.
                            Rectangle {
                                id: onda
                                anchors.centerIn: parent
                                width: 15; height: 15; radius: width / 2
                                color: "transparent"
                                border.width: 1.5
                                border.color: Theme.musgo
                                opacity: 0
                                scale: 1

                                ParallelAnimation {
                                    id: pulso
                                    NumberAnimation {
                                        target: onda; property: "scale"
                                        from: 1; to: 2.6
                                        duration: 460; easing.type: Easing.OutCubic
                                    }
                                    NumberAnimation {
                                        target: onda; property: "opacity"
                                        from: 0.7; to: 0
                                        duration: 460; easing.type: Easing.OutCubic
                                    }
                                }
                            }
                        }

                        MouseArea {
                            id: marcar
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            enabled: !marcador.concluindo
                            onEntered: backend.sfx("toque")
                            onClicked: {
                                marcador.concluindo = true
                                backend.sfx("entrega")
                                pulso.start()
                                adiar.start()
                            }
                        }
                    }

                    Column {
                        width: parent.width - 130
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1

                        Text {
                            width: parent.width
                            text: model.label
                            color: model.taskId === raiz.tarefaAtual ? Theme.ambar : Theme.texto
                            font.pixelSize: Theme.corpo
                            elide: Text.ElideRight
                            Behavior on color { ColorAnimation { duration: 200 } }
                        }

                        Text {
                            width: parent.width
                            text: model.project
                            visible: model.project !== ""
                            color: Theme.textoSuave
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                    }

                    Item { width: 1; height: 1 }
                }

                Row {
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    opacity: hover.hovered || model.taskId === raiz.tarefaAtual ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 180 } }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.taskId === raiz.tarefaAtual ? "em curso" : "começar"
                        font.pixelSize: 11
                        color: comecar.containsMouse ? Theme.ambar : Theme.textoSuave
                        MouseArea {
                            id: comecar
                            anchors.fill: parent
                            anchors.margins: -6
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            enabled: model.taskId !== raiz.tarefaAtual
                            onClicked: raiz.iniciar(model.taskId)
                        }
                    }

                    Item { width: 8; height: 1 }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "×"
                        font.pixelSize: 16
                        color: guardar.containsMouse ? Theme.terracota : Theme.textoSuave
                        MouseArea {
                            id: guardar
                            anchors.fill: parent
                            anchors.margins: -6
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: raiz.arquivar(model.taskId)
                        }
                    }
                }

                MouseArea {
                    id: arraste
                    anchors.fill: parent
                    anchors.leftMargin: 30
                    anchors.rightMargin: 96
                    cursorShape: Qt.OpenHandCursor
                    drag.target: cartao
                    drag.axis: Drag.YAxis

                    onPressed: raiz.arrastando = true

                    // A posição nova é calculada uma vez, ao soltar.
                    //
                    // A versão anterior trocava as linhas ao vivo, por DropArea:
                    // cada troca reposicionava as linhas debaixo do cursor, o
                    // que disparava a DropArea vizinha e desfazia a troca. O
                    // cartão ficava indo e voltando, e o resultado dependia de
                    // em que ponto da oscilação o usuário soltasse.
                    onReleased: {
                        var andou = Math.round(cartao.y / envelope.passo)
                        var destino = Math.max(
                            0, Math.min(modelo.count - 1, index + andou))
                        var de = index

                        envelope.repousar()
                        raiz.arrastando = false

                        if (destino !== de) {
                            modelo.move(de, destino, 1)
                            raiz.publicarOrdem()
                        }
                    }
                }
            }
        }

        displaced: Transition {
            NumberAnimation { properties: "y"; duration: 180; easing.type: Easing.OutQuad }
        }
    }
}
