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
    // A escolhida para o próximo "começar". Vazia enquanto uma sessão corre —
    // aí quem manda é `tarefaAtual`.
    property string tarefaFoco: ""

    signal iniciar(string taskId)
    signal concluir(string taskId)
    signal arquivar(string taskId)
    signal reordenar(var ids)
    signal focar(string taskId)
    signal renomear(string taskId, string texto)

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
                Behavior on color { ColorAnimation { duration: Theme.reacao } }

                HoverHandler { id: hover }

                // Modo de correção do texto. Ver `abrirEdicao` mais abaixo.
                property bool editando: false

                function abrirEdicao() {
                    edicao.text = model.label
                    editando = true
                    edicao.forceActiveFocus()
                    edicao.selectAll()
                }

                function fecharEdicao(guardar) {
                    if (!editando)
                        return
                    editando = false
                    if (guardar)
                        raiz.renomear(model.taskId, edicao.text)
                }

                // Marca da escolhida: um traço na margem, do lado de fora do
                // texto. É a mesma informação que a barra de baixo mostra por
                // extenso, e aqui ela precisa caber num item de 42 pixels sem
                // virar botão nem caixa de seleção.
                Rectangle {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: 2
                    height: 22
                    radius: 1
                    color: Theme.ambar
                    opacity: model.taskId === raiz.tarefaAtual ? 1.0
                             : (model.taskId === raiz.tarefaFoco ? 0.55 : 0)
                    Behavior on opacity { NumberAnimation { duration: Theme.gesto } }
                }

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
                            Behavior on border.color { ColorAnimation { duration: Theme.reacao } }
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
                                Behavior on opacity { NumberAnimation { duration: Theme.reacao } }
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
                                        duration: Theme.chegada; easing.type: Easing.OutCubic
                                    }
                                    NumberAnimation {
                                        target: onda; property: "opacity"
                                        from: 0.7; to: 0
                                        duration: Theme.chegada; easing.type: Easing.OutCubic
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

                    // A linha abre espaço para os botões só quando eles
                    // aparecem.
                    //
                    // Com largura fixa, o espaço reservado às ações ficava
                    // roubado o tempo todo e quase toda tarefa aparecia
                    // cortada em "responder o e-mail do ...". Como as ações só
                    // existem com o mouse em cima, o texto pode ocupar a linha
                    // inteira enquanto ninguém está mirando nelas.
                    Column {
                        width: parent.width - (hover.hovered
                                               || model.taskId === raiz.tarefaAtual
                                               ? 170 : 40)
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 1

                        Behavior on width {
                            NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutQuad }
                        }

                        // O rótulo e a correção dele ocupam o mesmo lugar.
                        //
                        // Uma tarefa mal escrita não tinha conserto: dava para
                        // arquivá-la e escrever outra, o que enche o log de
                        // tarefa morta e perde o tempo já gasto nela. Corrigir
                        // aqui é um evento novo (`task.renamed`), o id continua
                        // o mesmo e o objeto que ela vai deixar na estante não
                        // muda de desenho.
                        Item {
                            width: parent.width
                            height: rotulo.implicitHeight + 2

                            Text {
                                id: rotulo
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                visible: !cartao.editando
                                text: model.label
                                color: model.taskId === raiz.tarefaAtual ? Theme.ambar : Theme.texto
                                font.pixelSize: Theme.corpo
                                elide: Text.ElideRight
                                Behavior on color { ColorAnimation { duration: Theme.gesto } }
                            }

                            TextInput {
                                id: edicao
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                visible: cartao.editando
                                color: Theme.texto
                                font.pixelSize: Theme.corpo
                                selectionColor: Qt.rgba(Theme.ambar.r, Theme.ambar.g,
                                                        Theme.ambar.b, 0.35)
                                selectedTextColor: Theme.texto
                                clip: true

                                onAccepted: cartao.fecharEdicao(true)
                                // Clicar em qualquer outro lugar guarda o que
                                // foi escrito. Perder a correção por ter
                                // clicado fora seria pior que não ter editor.
                                onActiveFocusChanged: if (!activeFocus) cartao.fecharEdicao(true)
                                Keys.onEscapePressed: cartao.fecharEdicao(false)
                            }

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                visible: cartao.editando
                                color: Theme.ambar
                            }
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
                    opacity: (hover.hovered || model.taskId === raiz.tarefaAtual)
                             && !cartao.editando ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Theme.reacao } }

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

                    Item { width: 10; height: 1 }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "editar"
                        font.pixelSize: 11
                        color: corrigir.containsMouse ? Theme.ambar : Theme.textoSuave
                        MouseArea {
                            id: corrigir
                            anchors.fill: parent
                            anchors.margins: -6
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: cartao.abrirEdicao()
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
                    anchors.rightMargin: 140
                    cursorShape: Qt.OpenHandCursor
                    drag.target: cartao
                    drag.axis: Drag.YAxis
                    // Enquanto o texto está sendo corrigido, o clique é do
                    // campo: esta área fica por cima dele e engoliria o cursor.
                    enabled: !cartao.editando

                    onPressed: raiz.arrastando = true

                    // Clique sem arrasto escolhe a tarefa para o próximo
                    // "começar". É o gesto mais barato da lista, e serve ao
                    // caso mais comum: decidir o que vem agora sem começar
                    // agora.
                    onClicked: raiz.focar(model.taskId)

                    // Duplo clique abre a correção do texto — o mesmo gesto de
                    // renomear arquivo, no lugar onde o texto está.
                    onDoubleClicked: cartao.abrirEdicao()

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
            NumberAnimation { properties: "y"; duration: Theme.gesto; easing.type: Easing.OutQuad }
        }
    }
}
