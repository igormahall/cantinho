import QtQuick
import theme
import "room"
import "panels"

// Janela principal: o quarto ocupa tudo, e as listas entram por cima quando
// chamadas. O padrão da tela é o ambiente, não a lista de pendências.
Window {
    id: janela

    width: 1100
    height: 700
    minimumWidth: 900
    minimumHeight: 600
    visible: backend.mainVisible
    color: Theme.fundo
    title: "Cantinho"

    // O tema é do backend; o Theme só o reflete. Amarrado aqui porque
    // singleton QML não deve depender de context property para existir.
    Component.onCompleted: {
        Theme.noite = Qt.binding(function () { return backend.isNight })
    }

    onVisibleChanged: if (!visible) backend.setMainVisible(false)

    // "aba" vazia significa só o quarto à mostra.
    property string aba: ""
    function alternar(nome) { aba = (aba === nome) ? "" : nome }

    Room {
        id: quarto
        anchors.fill: parent
        plantStage: backend.plantStage
        shelf: backend.shelf

        // O bilhete da parede é a única parte do cenário que responde a clique.
        onAbrirHoje: janela.aba = "backlog"
    }

    // Clicar no vazio do quarto fecha o painel aberto.
    MouseArea {
        anchors.fill: parent
        enabled: janela.aba !== ""
        onClicked: janela.aba = ""
    }

    // ----------------------------------------------------- painel lateral

    // O painel fica no meio, por cima da janela do quarto — nunca por cima da
    // estante nem do vaso. Esses dois são o retorno que o app dá; escondê-los
    // para mostrar a lista de pendências inverteria a prioridade da tela.
    Painel {
        id: gaveta
        // Nomeado para `tools/simular_uso.py` conseguir procurar só aqui
        // dentro: o bilhete da parede repete os rótulos das tarefas, e uma
        // busca pela tela inteira acha o papel antes da linha da lista.
        objectName: "gaveta"
        width: 410
        x: 330
        anchors.top: parent.top
        anchors.topMargin: janela.aba === "" ? 44 : 24
        anchors.bottom: barra.top
        anchors.bottomMargin: 16

        opacity: janela.aba === "" ? 0 : 1
        visible: opacity > 0.01

        Behavior on anchors.topMargin {
            NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: 240 } }

        Column {
            anchors.fill: parent
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            Text {
                text: janela.aba === "backlog" ? "hoje"
                      : janela.aba === "ideias" ? "mural de ideias"
                      : janela.aba === "dia" ? "fechar o dia" : ""
                color: Theme.texto
                font.pixelSize: Theme.titulo
            }

            // ------------------------------------------------- backlog

            Item {
                width: parent.width
                height: parent.height - 90
                visible: janela.aba === "backlog"

                Backlog {
                    id: listaBacklog
                    anchors.fill: parent
                    anchors.bottomMargin: 48
                    tarefas: backend.backlog
                    limiteHoje: backend.todayLimit
                    tarefaAtual: backend.currentTaskId

                    onIniciar: function (taskId) { backend.startSession(taskId) }
                    onConcluir: function (taskId) { backend.completeTask(taskId) }
                    onArquivar: function (taskId) { backend.archiveTask(taskId) }
                    onReordenar: function (ids) { backend.reorderBacklog(ids) }
                }

                CampoTexto {
                    id: novaTarefa
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    placeholder: "o que você quer fazer?"
                    onAceito: function (texto) {
                        backend.addTask(texto)
                        limpar()
                    }
                }
            }

            // -------------------------------------------------- ideias

            Item {
                width: parent.width
                height: parent.height - 90
                visible: janela.aba === "ideias"

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 30
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: backend.ideas.length === 0
                    text: "O mural está vazio.\nCtrl+Shift+C funciona de qualquer lugar."
                    color: Theme.textoSuave
                    font.pixelSize: Theme.corpo
                    lineHeight: 1.4
                }

                // O mural.
                //
                // Uma ideia aproveitada não sai daqui: ela fica riscada, com a
                // data em que virou tarefa. É o único lugar do app onde dá para
                // ver de onde as coisas vieram — e uma ideia riscada é bem mais
                // barata de manter do que uma lista que se esvazia e não conta
                // mais nada.
                //
                // Some do mural só o que for descartado à mão, e mesmo isso é
                // um evento novo no log, não um apagamento.
                ListView {
                    anchors.fill: parent
                    anchors.bottomMargin: 48
                    spacing: 10
                    clip: true
                    model: backend.ideas

                    delegate: Item {
                        id: cartaz
                        width: ListView.view.width
                        height: linha.height + 10

                        readonly property bool usada: modelData.used

                        HoverHandler { id: sobre }

                        // Pino: sobra da metáfora do mural, e serve para o olho
                        // achar o começo de cada ideia.
                        Rectangle {
                            width: 5; height: 5; radius: 3
                            y: 6
                            color: cartaz.usada ? Theme.musgo : Theme.ambar
                            opacity: cartaz.usada ? 0.45 : 0.8
                        }

                        Column {
                            id: linha
                            x: 14
                            width: parent.width - 84
                            spacing: 2

                            Text {
                                width: parent.width
                                text: modelData.text
                                color: Theme.texto
                                opacity: cartaz.usada ? 0.45 : 1.0
                                font.pixelSize: Theme.corpo
                                font.strikeout: cartaz.usada
                                wrapMode: Text.WordWrap
                                Behavior on opacity { NumberAnimation { duration: 300 } }
                            }
                            Text {
                                text: cartaz.usada
                                      ? modelData.when + " · virou tarefa"
                                      : modelData.when
                                color: Theme.textoSuave
                                opacity: cartaz.usada ? 0.6 : 1.0
                                font.pixelSize: 11
                            }
                        }

                        Row {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            spacing: 0
                            opacity: sobre.hovered ? 1 : 0
                            visible: opacity > 0.01
                            Behavior on opacity { NumberAnimation { duration: 180 } }

                            BotaoSuave {
                                text: "virar tarefa"
                                visible: !cartaz.usada
                                onClicked: backend.ideaToTask(modelData.id)
                            }

                            BotaoSuave {
                                text: "×"
                                corAtiva: Theme.terracota
                                onClicked: backend.archiveIdea(modelData.id)
                            }
                        }
                    }
                }

                CampoTexto {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    placeholder: "o que passou pela cabeça?"
                    onAceito: function (texto) {
                        backend.captureIdea(texto)
                        limpar()
                    }
                }
            }

            // ------------------------------------------- retrospectiva

            Retrospectiva {
                width: parent.width
                height: parent.height - 90
                visible: janela.aba === "dia"
                sessoes: backend.todaySessions
                concluidas: backend.todayCompleted
                revisao: backend.todayReview
                onSalvar: function (humor, energia, nota) {
                    backend.saveReview(humor, energia, nota)
                    janela.aba = ""
                }
            }
        }
    }

    // ------------------------------------------------------- barra de baixo

    Painel {
        id: barra
        height: 76
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24

        // Bem mais translúcida que a gaveta: a barra não tem texto para ler, só
        // controles. Opaca, ela vira rodapé de aplicativo e corta o chão do
        // quarto em dois. Fica um pouco mais firme com o mouse por perto.
        opacidadeFundo: sobreBarra.hovered
                        ? Theme.opacidadePainel : Theme.opacidadeBarra

        HoverHandler { id: sobreBarra }

        Row {
            anchors.left: parent.left
            anchors.leftMargin: Theme.espacoGrande
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.espacoGrande

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                Text {
                    text: backend.elapsedText
                    color: backend.timerRunning ? Theme.ambar : Theme.textoSuave
                    font.pixelSize: 30
                    font.letterSpacing: 1
                    Behavior on color { ColorAnimation { duration: 300 } }
                }

                Text {
                    text: backend.timerRunning
                          ? (backend.currentTaskLabel !== ""
                             ? backend.currentTaskLabel : "sessão livre")
                          : "o tempo começa quando você quiser"
                    color: Theme.textoSuave
                    font.pixelSize: Theme.miudo
                    width: 320
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: Theme.espacoGrande
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: backend.timerRunning ? "encerrar" : "começar"
                destacado: true
                corAtiva: backend.timerRunning ? Theme.musgo : Theme.ambar
                tamanho: Theme.corpo
                onClicked: backend.timerRunning
                           ? backend.endSession(false, "")
                           : backend.startSession("")
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "fui interrompido"
                visible: backend.timerRunning
                corAtiva: Theme.terracota
                onClicked: backend.endSession(true, "")
            }

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 1; height: 26; color: Theme.borda
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "hoje"
                destacado: janela.aba === "backlog"
                onClicked: janela.alternar("backlog")
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "ideias"
                destacado: janela.aba === "ideias"
                onClicked: janela.alternar("ideias")
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "fechar o dia"
                destacado: janela.aba === "dia"
                onClicked: janela.alternar("dia")
            }

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 1; height: 26; color: Theme.borda
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: backend.themeMode === "auto" ? "relógio"
                      : backend.themeMode === "noite" ? "noite" : "tarde"
                onClicked: backend.cycleThemeMode()
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: backend.soundOn ? "som" : "mudo"
                destacado: backend.soundOn
                corAtiva: Theme.musgo
                onClicked: backend.toggleSound()
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "mini"
                destacado: backend.miniVisible
                onClicked: backend.toggleMini()
            }
        }
    }

    // ------------------------------------------------- captura de ideia

    Rectangle {
        id: veu
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: captura.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: 200 } }

        MouseArea {
            anchors.fill: parent
            onClicked: captura.aberta = false
        }
    }

    Painel {
        id: captura
        property bool aberta: false

        width: 520
        height: 120
        anchors.horizontalCenter: parent.horizontalCenter
        y: captura.aberta ? parent.height / 3 : -height
        opacity: captura.aberta ? 1 : 0
        visible: opacity > 0.01

        Behavior on y { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: 200 } }

        onAbertaChanged: {
            if (aberta) {
                entradaIdeia.limpar()
                entradaIdeia.focar()
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            Text {
                text: "guardar uma ideia"
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
            }

            CampoTexto {
                id: entradaIdeia
                width: parent.width
                placeholder: "escreva e aperte Enter"
                onAceito: function (texto) {
                    backend.captureIdea(texto)
                    captura.aberta = false
                }
            }
        }

        Keys.onEscapePressed: captura.aberta = false
    }

    Connections {
        target: backend
        function onCaptureRequested() {
            janela.raise()
            janela.requestActivate()
            captura.aberta = true
        }
    }

    // Ctrl+Shift+C também funciona com a janela em foco, sem depender do
    // atalho global do sistema.
    Shortcut {
        sequences: ["Ctrl+Shift+C"]
        onActivated: captura.aberta = true
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (captura.aberta) captura.aberta = false
            else janela.aba = ""
        }
    }
}
