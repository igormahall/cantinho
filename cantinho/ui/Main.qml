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

    // A janela e o backend precisam concordar nos dois sentidos: o usuário
    // fecha pelo X do sistema, e o app esconde por conta própria quando a mini
    // entra em cena.
    onVisibleChanged: {
        if (visible) {
            // Reaparecer minimizada é o que acontece se alguém minimizou a
            // janela antes de ela ser escondida: o estado fica guardado e
            // volta junto. Aqui ela é devolvida ao tamanho normal e trazida
            // para a frente, senão "abrir" pela mini ou pela bandeja parece
            // não ter feito nada.
            if (visibility === Window.Minimized)
                visibility = Window.Windowed
            raise()
            requestActivate()
        } else {
            janela.menuAberto = false
            saida.aberta = false
            backend.setMainVisible(false)
        }
    }

    // Minimizar minimiza, e só.
    //
    // Antes trocava a janela pela mini, com o argumento de que o timer
    // continuava visível num canto. Na prática o gesto de minimizar quer dizer
    // "sai da frente agora", e o app respondia colocando outra janela na
    // frente — sempre por cima de tudo, ainda por cima. Para chamar a mini
    // existe o botão "mini", que é onde alguém que a queira vai procurá-la.

    // "aba" vazia significa só o quarto à mostra.
    property string aba: ""
    function alternar(nome) { aba = (aba === nome) ? "" : nome }

    // Fechar o que estiver aberto por cima do quarto, em um lugar só.
    function recolher() {
        aba = ""
        menuAberto = false
        seletor.aberto = false
    }

    Room {
        id: quarto
        anchors.fill: parent
        plantStage: backend.plantStage
        shelf: backend.shelf

        // Os dois papéis da parede que respondem a clique: o bilhete abre o
        // "hoje", o calendário abre a semana. É a leitura literal de cada um —
        // a lista do dia e o mês passando.
        onAbrirHoje: janela.aba = "backlog"
        onAbrirSemana: janela.aba = "semana"
    }

    // Clicar no vazio do quarto fecha o painel aberto.
    MouseArea {
        anchors.fill: parent
        enabled: janela.aba !== ""
        onClicked: janela.recolher()
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

            // O título e, no diário, as duas abas.
            //
            // "O dia" e "a semana" são a mesma coisa em duas distâncias, então
            // dividem o painel em vez de disputarem espaço na barra de baixo —
            // que já estava cheia. Quem abre um chega no outro em um clique.
            Item {
                width: parent.width
                height: 28

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: janela.aba === "backlog" ? "hoje"
                          : janela.aba === "ideias" ? "mural de ideias"
                          : janela.aba === "dia" ? "o dia"
                          : janela.aba === "semana" ? "a semana" : ""
                    color: Theme.texto
                    font.pixelSize: Theme.titulo
                }

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 0
                    visible: janela.aba === "dia" || janela.aba === "semana"

                    BotaoSuave {
                        text: "o dia"
                        destacado: janela.aba === "dia"
                        onClicked: janela.aba = "dia"
                    }

                    BotaoSuave {
                        text: "a semana"
                        destacado: janela.aba === "semana"
                        onClicked: janela.aba = "semana"
                    }
                }
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
                    tarefaFoco: backend.timerRunning ? "" : backend.focusedTaskId

                    onIniciar: function (taskId) { backend.startSession(taskId) }
                    onConcluir: function (taskId) { backend.completeTask(taskId) }
                    onArquivar: function (taskId) { backend.archiveTask(taskId) }
                    onReordenar: function (ids) { backend.reorderBacklog(ids) }
                    onFocar: function (taskId) { backend.setFocusedTask(taskId) }
                    onRenomear: function (taskId, texto) {
                        backend.renameTask(taskId, texto)
                    }
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
                    text: "O mural está vazio.\nCtrl+Shift+I funciona de qualquer lugar."
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
                minutosDoDia: backend.todayMinutes
                sessaoCorrendo: backend.timerRunning
                onEncerrar: function (humor, energia, nota) {
                    backend.endDay(humor, energia, nota)
                    janela.aba = ""
                }
            }

            // ------------------------------------------------- a semana

            Semana {
                width: parent.width
                height: parent.height - 90
                visible: janela.aba === "semana"
                dias: backend.weekDays
                titulo: backend.weekTitle
                periodo: backend.weekRange
                entregas: backend.weekDelivered
                minutos: backend.weekMinutes
                recuo: backend.weekOffset
                onAnterior: backend.previousWeek()
                onSeguinte: backend.nextWeek()
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

        // O relógio e, debaixo dele, o que o "começar" vai pegar.
        //
        // A segunda linha não é legenda: é um controle. Enquanto o timer está
        // parado ela mostra a tarefa escolhida e abre a lista de escolha; com o
        // timer correndo ela vira o nome do que está sendo feito e para de
        // responder, porque trocar de tarefa no meio da sessão seria trocar o
        // que o log já está gravando.
        Column {
            id: relogio
            anchors.left: parent.left
            anchors.leftMargin: Theme.espacoGrande
            anchors.verticalCenter: parent.verticalCenter
            width: 330
            spacing: 2

            Text {
                text: backend.elapsedText
                color: backend.timerRunning ? Theme.ambar : Theme.textoSuave
                font.pixelSize: 30
                font.letterSpacing: 1
                Behavior on color { ColorAnimation { duration: 300 } }
            }

            Item {
                width: parent.width
                height: 20

                readonly property bool escolhivel: !backend.timerRunning

                Text {
                    id: aoLado
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(implicitWidth, parent.width - 20)
                    elide: Text.ElideRight
                    font.pixelSize: Theme.miudo
                    text: backend.timerRunning
                          ? (backend.currentTaskLabel !== ""
                             ? backend.currentTaskLabel : "sessão livre")
                          : backend.freeSessionChosen
                            ? "sessão livre"
                            : backend.focusedTaskLabel !== ""
                              ? backend.focusedTaskLabel
                              : "escreva no hoje o que fazer"
                    color: backend.timerRunning ? Theme.ambar
                           : (escolher.containsMouse ? Theme.ambar : Theme.textoSuave)
                    Behavior on color { ColorAnimation { duration: Theme.reacao } }
                }

                // Marca de "isto abre": some junto com a possibilidade de
                // escolher, para não prometer um clique que não acontece.
                Text {
                    anchors.left: aoLado.right
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: "▾"
                    font.pixelSize: 9
                    color: escolher.containsMouse ? Theme.ambar : Theme.textoSuave
                    opacity: parent.escolhivel ? 0.8 : 0
                    Behavior on opacity { NumberAnimation { duration: 160 } }
                }

                MouseArea {
                    id: escolher
                    anchors.fill: parent
                    anchors.margins: -4
                    hoverEnabled: true
                    enabled: parent.escolhivel
                    cursorShape: Qt.PointingHandCursor
                    onEntered: backend.sfx("toque")
                    onClicked: {
                        backend.sfx("clique")
                        seletor.aberto = !seletor.aberto
                    }
                }
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: Theme.espacoGrande
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            // Os três fins possíveis de uma sessão, e eles precisavam de nomes
            // que não se confundissem.
            //
            // "Terminei" e "encerrar" eram a mesma palavra dita de dois jeitos,
            // e ficavam lado a lado: ninguém sabia qual dos dois fechava a
            // tarefa. Agora cada botão diz o que acontece com a tarefa, que é a
            // única diferença entre eles:
            //
            //   entreguei        — a tarefa acabou e vira objeto na estante
            //   parar            — o relógio para, a tarefa continua na lista
            //   fui interrompido — igual, mas fica marcado assim no diário
            //
            // "Entreguei" é o mesmo verbo da estante, que é a vitrine de
            // entregas: quem lê a palavra já sabe onde a tarefa vai parar. Só
            // aparece com tarefa presa ao timer — numa sessão livre não há o
            // que concluir.
            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "entreguei"
                mostrando: backend.timerRunning && backend.currentTaskId !== ""
                destacado: true
                corAtiva: Theme.musgo
                tamanho: Theme.corpo
                onClicked: backend.endSessionAndComplete()
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: backend.timerRunning ? "parar" : "começar"
                // Deixa de ser o botão principal quando "entreguei" está do
                // lado: dois destaques lado a lado não destacam nada.
                destacado: !backend.timerRunning
                corAtiva: backend.timerRunning ? Theme.texto : Theme.ambar
                tamanho: backend.timerRunning ? Theme.miudo : Theme.corpo
                onClicked: backend.timerRunning
                           ? backend.endSession(false, "")
                           : backend.startFocused()
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "fui interrompido"
                mostrando: backend.timerRunning
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

            // "o dia" e não "fechar o dia": o painel sempre pôde ser aberto a
            // qualquer hora, mas o nome dizia que era coisa de fim de
            // expediente, e por isso ninguém entrava nele antes das dez da
            // noite. É onde estão as sessões, o humor e a nota.
            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "o dia"
                destacado: janela.aba === "dia" || janela.aba === "semana"
                // Dia já encerrado esverdeia o rótulo. É o mesmo verde da
                // estante, e é tudo o que se pode dizer sobre isso sem virar
                // marca de tarefa cumprida: não conta dias seguidos, não some
                // amanhã como conquista perdida.
                cor: backend.dayClosed ? Theme.musgo : Theme.textoSuave
                onClicked: janela.alternar("dia")
            }

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 1; height: 26; color: Theme.borda
            }

            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "mini"
                onClicked: backend.showMini()
            }

            // Tema, som, humor e a saída moram aqui.
            //
            // Não é gosto por menu: com "entreguei" a mais, a fileira de botões
            // passava da largura da janela. E são todos ajustes do ambiente, não
            // ações do dia — separá-los deixa na barra só o que se usa o tempo
            // todo.
            BotaoSuave {
                anchors.verticalCenter: parent.verticalCenter
                text: "o quarto"
                destacado: janela.menuAberto
                onClicked: {
                    seletor.aberto = false
                    janela.menuAberto = !janela.menuAberto
                }
            }
        }
    }

    // --------------------------------------------- o que vem agora (seletor)

    // Fecha ao clicar fora, como o menu do quarto.
    MouseArea {
        anchors.fill: parent
        enabled: seletor.aberto
        onClicked: seletor.aberto = false
    }

    SeletorTarefa {
        id: seletor
        // Nomeado para `tools/simular_uso.py` procurar só aqui dentro: os
        // rótulos das tarefas aparecem em três lugares na tela ao mesmo tempo.
        objectName: "seletor"
        anchors.left: parent.left
        anchors.leftMargin: 24
        anchors.bottom: barra.top
        anchors.bottomMargin: aberto ? 10 : -6

        tarefas: backend.today
        escolhida: backend.focusedTaskId
        livre: backend.freeSessionChosen

        Behavior on anchors.bottomMargin {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }

        onEscolher: function (taskId) {
            backend.setFocusedTask(taskId)
            aberto = false
        }
    }

    // Uma sessão que começa fecha a escolha: ela já foi feita.
    Connections {
        target: backend
        function onTimerChanged() {
            if (backend.timerRunning) seletor.aberto = false
        }
    }

    // ------------------------------------------------------- menu do quarto

    property bool menuAberto: false

    MouseArea {
        anchors.fill: parent
        enabled: janela.menuAberto
        onClicked: janela.menuAberto = false
    }

    Painel {
        id: menu
        width: 268
        height: colunaMenu.height + 2 * Theme.espacoGrande
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.bottom: barra.top
        anchors.bottomMargin: janela.menuAberto ? 10 : -6

        opacity: janela.menuAberto ? 1 : 0
        visible: opacity > 0.01

        Behavior on anchors.bottomMargin {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: 180 } }

        Column {
            id: colunaMenu
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            // O humor e a energia saíram de dentro da retrospectiva para cá.
            //
            // Lá eles só apareciam depois de rolar a lista de sessões, no
            // painel chamado "fechar o dia" — ou seja, na prática só existiam
            // no fim da noite. Aqui dá para dizer como se está às três da
            // tarde, que é quando a resposta é verdadeira.
            //
            // Grava na hora, sem botão de confirmar, e preserva a nota que já
            // estiver guardada: é o mesmo `day.review` do painel do dia, e a
            // última do dia vence.
            Text {
                text: "como está o dia"
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
            }

            EscalaPontos {
                width: parent.width
                rotulo: "humor"
                valor: backend.todayReview ? backend.todayReview.mood : 3
                onEscolhido: function (v) {
                    backend.saveReview(
                        v,
                        backend.todayReview ? backend.todayReview.energy : 3,
                        backend.todayReview ? backend.todayReview.note : "")
                }
            }

            EscalaPontos {
                width: parent.width
                rotulo: "energia"
                valor: backend.todayReview ? backend.todayReview.energy : 3
                onEscolhido: function (v) {
                    backend.saveReview(
                        backend.todayReview ? backend.todayReview.mood : 3,
                        v,
                        backend.todayReview ? backend.todayReview.note : "")
                }
            }

            Rectangle {
                width: parent.width; height: 1; color: Theme.borda
            }

            // "dia" e não "fim de tarde".
            //
            // A paleta clara foi desenhada pensando em luz baixa de fim de
            // tarde, e o nome vazou do desenho para a tela. Só que quem abre o
            // app às sete da manhã lê "fim de tarde" e o app está errado sobre
            // o próprio momento do dia. O id interno continua `tarde`, que é o
            // nome dos arquivos de cena e de áudio.
            LinhaMenu {
                width: parent.width
                rotulo: "luz"
                valor: backend.themeMode === "auto" ? "pelo seu dia"
                       : backend.themeMode === "noite" ? "noite" : "dia"
                onClicado: backend.cycleThemeMode()
            }

            // Três estados, um botão. "Sussurro" é o do meio: o quarto cala a
            // chuva e o acorde, mas o clique continua respondendo — para quem
            // está numa chamada e não quer perder o retorno da interface.
            LinhaMenu {
                width: parent.width
                rotulo: "som"
                valor: backend.soundMode === "tudo" ? "ambiente e toques"
                       : backend.soundMode === "sussurro" ? "só os toques"
                       : "nenhum"
                onClicado: backend.cycleSoundMode()
            }

            Rectangle {
                width: parent.width; height: 1; color: Theme.borda
            }

            LinhaMenu {
                width: parent.width
                rotulo: "sair"
                valor: "fechar o cantinho"
                cor: Theme.terracota
                onClicado: {
                    janela.menuAberto = false
                    saida.aberta = true
                }
            }
        }
    }

    // ------------------------------------------------------ sair do app

    // Fechar a janela deixa o app na bandeja, o que é o comportamento certo mas
    // não dá jeito de encerrar de verdade sem ir até o ícone. A confirmação
    // existe porque a diferença entre "esconder" e "encerrar" não é óbvia: quem
    // clica em sair esperando o primeiro perde a sessão que estiver correndo.
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: saida.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: 200 } }

        MouseArea {
            anchors.fill: parent
            onClicked: saida.aberta = false
        }
    }

    Painel {
        id: saida
        property bool aberta: false

        width: 380
        height: colunaSaida.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        y: saida.aberta ? parent.height / 3 : parent.height / 3 - 16
        opacity: saida.aberta ? 1 : 0
        visible: opacity > 0.01

        Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: 180 } }

        Column {
            id: colunaSaida
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            Text {
                text: "fechar o cantinho?"
                color: Theme.texto
                font.pixelSize: Theme.titulo
            }

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
                text: backend.timerRunning
                      ? "Tem uma sessão correndo. Sair agora não a guarda no diário."
                      : "Nada se perde. Fechar a janela sozinha deixa o app na bandeja."
            }

            Row {
                spacing: 4
                anchors.right: parent.right

                BotaoSuave {
                    text: "ficar"
                    onClicked: saida.aberta = false
                }

                BotaoSuave {
                    text: "sair"
                    destacado: true
                    corAtiva: Theme.terracota
                    tamanho: Theme.corpo
                    onClicked: backend.requestQuit()
                }
            }
        }

        Keys.onEscapePressed: saida.aberta = false
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

    // Ctrl+Shift+I também funciona com a janela em foco, sem depender do
    // atalho global do sistema. "I" de ideia.
    Shortcut {
        sequences: ["Ctrl+Shift+I"]
        onActivated: captura.aberta = true
    }

    // Espaço começa e para a sessão sem tirar a mão do teclado.
    //
    // Só com o quarto limpo, e a condição é essa mesma e não "o campo de texto
    // não está em foco": todo painel deste app tem um campo de escrita dentro,
    // e um atalho que às vezes come a barra de espaço no meio de uma frase é
    // pior do que não existir.
    Shortcut {
        sequence: "Space"
        enabled: janela.aba === "" && !captura.aberta && !saida.aberta
        onActivated: backend.timerRunning
                     ? backend.endSession(false, "")
                     : backend.startFocused()
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (captura.aberta) captura.aberta = false
            else if (saida.aberta) saida.aberta = false
            else if (seletor.aberto) seletor.aberto = false
            else if (janela.menuAberto) janela.menuAberto = false
            else janela.aba = ""
        }
    }
}
