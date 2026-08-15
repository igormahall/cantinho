import QtQuick
import QtQuick.Effects
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
        Theme.movimento = Qt.binding(function () { return backend.motionOn })
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

    // Quanto o quarto está "atrás". Zero com a gaveta fechada.
    //
    // É o que liga o desfoque do cenário à abertura do painel, num valor só,
    // para que a profundidade e o painel andem no mesmo ritmo. Não obedece a
    // `Theme.movimento`: é consequência de um gesto, como `gesto` e `chegada`.
    property real profundidade: aba === "" ? 0 : 1
    Behavior on profundidade {
        NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
    }

    Room {
        id: quarto
        anchors.fill: parent
        plantStage: backend.plantStage
        shelf: backend.shelf
        focoNoQuarto: janela.aba === ""

        // O quarto sai de foco quando um painel abre — e isto é a correção do
        // problema de composição mais visível que a auditoria achou.
        //
        // A gaveta era uma laje clara pousada sobre a ilustração, cobrindo a
        // janela **e** o abajur, e lia como caixa de diálogo colada por cima do
        // desenho: o quarto sumia justamente na hora de usar o app. Com o fundo
        // desfocado e um pouco mais escuro, a mesma laje passa a ler como
        // "à frente" — a cena continua lá, reconhecível, e o olho sabe para
        // onde olhar sem que nada precise ser escondido.
        //
        // `layer.effect` cuida de esconder a fonte sozinho, e com
        // `layer.enabled` falso o custo é exatamente zero: nada disto roda com
        // a gaveta fechada, que é o estado padrão do app.
        layer.enabled: janela.profundidade > 0.01
        layer.effect: MultiEffect {
            blurEnabled: true
            // **Fraco de propósito, e o número foi calibrado olhando.** Com
            // `blurMax: 40` o quarto virava mancha: dava profundidade e custava
            // a cena inteira, que é o contrário do que este app é. O alvo é
            // ainda reconhecer os objetos da estante e as folhas do vaso, só
            // fora de foco — o quarto continua sendo um quarto, apenas atrás.
            blurMax: 14
            blur: janela.profundidade
            // Escurecer e dessaturar junto, de leve. Só o desfoque deixaria a
            // cena com a mesma luminosidade do painel, e aí as duas camadas
            // voltariam a brigar por atenção.
            brightness: -0.10 * janela.profundidade
            saturation: -0.12 * janela.profundidade
        }

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

    // ------------------------------------------------- sessão que ficou aberta

    // O que sobra de uma queda: o app morreu sem gravar o fim de uma sessão.
    //
    // Sair pelo menu, pela bandeja ou fechando a janela já guarda o que estava
    // correndo, então isto só aparece depois de falta de energia, sessão do
    // sistema derrubada ou processo morto — raro, e por isso discreto: uma tira
    // no alto, que não cobre nada e não pede resposta para o app funcionar.
    //
    // O aviso é informativo, não uma pergunta: a sessão **já foi guardada** na
    // última marca de vida do app, que é o último instante em que ele estava
    // comprovadamente rodando. Ver a recuperação em `backend.py`. O que sobra
    // para decidir é só se você volta a trabalhar naquilo agora.
    Painel {
        id: recuperada

        width: Math.min(520, parent.width - 48)
        height: colunaRecuperada.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        y: backend.hasRecoveredSession ? 24 : -height

        opacity: backend.hasRecoveredSession ? 1 : 0
        visible: opacity > 0.01

        Behavior on y { NumberAnimation { duration: Theme.chegada; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        Column {
            id: colunaRecuperada
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: 6

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                color: Theme.texto
                font.pixelSize: Theme.corpo
                text: backend.recoveredLabel !== ""
                      ? "O cantinho fechou sozinho com “" + backend.recoveredLabel
                        + "” em andamento."
                      : "O cantinho fechou sozinho com uma sessão em andamento."
            }

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
                text: backend.recoveredMinutes > 0
                      ? "Guardei até " + backend.recoveredUntil + ", que foi a última "
                        + "vez que o app deu sinal — " + backend.recoveredMinutes
                        + " min. Depois disso não dá para saber."
                      : "Não deu tempo de guardar nada dessa sessão: o app não chegou "
                        + "a dar sinal nenhum antes de fechar."
            }

            Row {
                anchors.right: parent.right
                spacing: 4

                BotaoSuave {
                    text: "ok"
                    onClicked: backend.dismissRecovered()
                }

                BotaoSuave {
                    text: "continuar isso"
                    mostrando: backend.recoveredTaskId !== ""
                    destacado: true
                    corAtiva: Theme.ambar
                    tamanho: Theme.corpo
                    onClicked: backend.continueRecovered()
                }
            }
        }
    }

    // ------------------------------------------ o que mais se fechou junto

    // Depois de uma sessão longa, o app pergunta uma coisa só.
    //
    // Uma hora raramente é uma coisa só: no meio dela chega o pedido urgente,
    // resolve-se o e-mail que travava outra pessoa, termina-se o que já estava
    // quase pronto. Nada disso vira entrega, porque o gesto de registrar
    // acontece no fim da sessão e a essa altura já se esqueceu.
    //
    // A pergunta oferece crédito por trabalho já feito, e é isso que a separa
    // de cobrança: "só isso" fecha sem custo nenhum, e é a resposta que o
    // Escape e o clique fora também dão.
    //
    // Aceita mais de uma resposta de propósito — em duas horas cabe mais de uma
    // coisa —, então o painel fica aberto e a lista vai encurtando.
    property int extraMinutos: 0

    Connections {
        target: backend
        function onExtraAsked(minutos) {
            janela.extraMinutos = minutos
            extra.aberta = true
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: extra.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        MouseArea {
            anchors.fill: parent
            onClicked: extra.aberta = false
        }
    }

    Painel {
        id: extra
        // Nomeado para `tools/simular_uso.py` procurar só aqui dentro: os
        // rótulos das tarefas aparecem no bilhete da parede ao mesmo tempo, e
        // um clique que erra o painel acerta o véu e o fecha.
        objectName: "extra"
        property bool aberta: false

        width: 460
        height: colunaExtra.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        y: extra.aberta ? parent.height / 5 : parent.height / 5 - 16
        opacity: extra.aberta ? 1 : 0
        visible: opacity > 0.01

        Behavior on y { NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        Column {
            id: colunaExtra
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

                        HoverHandler { id: sobreExtra }

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: -2
                            radius: Theme.raio
                            color: sobreExtra.hovered
                                   ? Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b, 0.45)
                                   : "transparent"
                            Behavior on color { ColorAnimation { duration: Theme.reacao } }
                        }

                        Rectangle {
                            id: circuloExtra
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            width: 14; height: 14; radius: 7
                            color: "transparent"
                            border.width: 1.5
                            border.color: sobreExtra.hovered ? Theme.musgo : Theme.textoSuave
                            Behavior on border.color { ColorAnimation { duration: Theme.reacao } }
                        }

                        Text {
                            anchors.left: circuloExtra.right
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
                id: entradaExtra
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
                    onClicked: extra.aberta = false
                }
            }
        }

        Keys.onEscapePressed: extra.aberta = false
    }

    // ----------------------------------------------------- painel lateral

    // O painel cobre a janela do quarto, e nada além dela.
    //
    // A estante e o vaso são o retorno que o app dá; escondê-los para mostrar a
    // lista de pendências inverteria a prioridade da tela. O abajur entrou
    // nessa lista depois: em x=330 o painel cortava a cúpula no meio, o que
    // não escondia a luz e também não a deixava aparecer — o pior dos dois. Em
    // 400 ele começa depois do abajur e termina antes do vaso, e o que fica
    // debaixo dele é a janela, que é cenário puro.
    //
    // **Posição em coordenada de cena, não da janela.** Era `x: 330` em pixel
    // de janela, o que coincide com a cena só em 1100x700: com a janela
    // maximizada, o desenho é centralizado e escalado e o painel ficava parado
    // no lugar antigo, descolando do abajur que ele existe para não cobrir. É a
    // mesma armadilha que já tirou a chuva e a poeira de cena, e que o balão do
    // passeio corrigiu — `cx` para posição, nunca fração da janela.
    Painel {
        id: gaveta
        // Nomeado para `tools/simular_uso.py` conseguir procurar só aqui
        // dentro: o bilhete da parede repete os rótulos das tarefas, e uma
        // busca pela tela inteira acha o papel antes da linha da lista.
        objectName: "gaveta"
        sombra: true
        width: quarto.px(410)
        x: quarto.cx(400)
        anchors.top: parent.top
        anchors.topMargin: janela.aba === "" ? 44 : 24
        anchors.bottom: barra.top
        anchors.bottomMargin: 16

        opacity: janela.aba === "" ? 0 : 1
        visible: opacity > 0.01

        Behavior on anchors.topMargin {
            NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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
                    opacity: janela.aba === "dia" || janela.aba === "semana" ? 1 : 0
                    visible: opacity > 0.01
                    Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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

            // Os quatro painéis ocupam o mesmo lugar e atravessam um pelo
            // outro.
            //
            // Antes eram irmãos de uma Column, cada um aparecendo por `visible`
            // — troca seca. Passava despercebido enquanto a gaveta só abria e
            // fechava, e ficou evidente quando "o dia" e "a semana" viraram
            // duas abas do mesmo painel: clicar de uma para a outra trocava a
            // tela inteira num quadro.
            //
            // Empilhados e anexados por opacidade, a Column deixa de decidir a
            // altura deles, que é por isso que a conta dos 90 pixels mudou de
            // lugar em vez de sumir.
            Item {
                id: conteudo
                width: parent.width
                height: parent.height - 90

                // ------------------------------------------------- backlog

                Item {
                    anchors.fill: parent
                    opacity: janela.aba === "backlog" ? 1 : 0
                    visible: opacity > 0.01
                    // A entrada é a mesma para os quatro de propósito: eles
                    // são o mesmo lugar da tela mostrando coisas diferentes,
                    // e uma curva por painel leria como quatro telas soltas.
                    Behavior on opacity {
                        NumberAnimation { duration: Theme.gesto }
                    }

                    Backlog {
                        id: listaBacklog
                        anchors.fill: parent
                        anchors.bottomMargin: 48
                        tarefas: backend.backlog
                        limiteHoje: backend.todayLimit
                        tarefaAtual: backend.currentTaskId
                        tarefaFoco: backend.timerRunning ? "" : backend.focusedTaskId

                        // Começar pelo "hoje" manda a janela grande embora e
                        // deixa a mini.
                        //
                        // O gesto de escolher uma tarefa na lista é o último
                        // que se faz antes de trabalhar; ficar com o quarto
                        // inteiro na frente depois disso é ter que fechá-lo à
                        // mão toda vez. A mini é o app reduzido ao relógio, que
                        // é exatamente o que sobra de útil a partir daqui.
                        //
                        // O botão grande da barra não faz isto: lá o quarto já
                        // está à vista e a escolha foi feita na própria barra.
                        onIniciar: function (taskId) {
                            backend.startSession(taskId)
                            backend.showMini()
                        }
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
                        limite: backend.labelLimit
                        placeholder: "o que você quer fazer?"
                        onAceito: function (texto) {
                            backend.addTask(texto)
                            limpar()
                        }
                    }
                }

                // -------------------------------------------------- ideias

                Item {
                    anchors.fill: parent
                    opacity: janela.aba === "ideias" ? 1 : 0
                    visible: opacity > 0.01
                    Behavior on opacity {
                        NumberAnimation { duration: Theme.gesto }
                    }

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
                        id: mural
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
                                    // Quatro linhas, e o resto vira reticência.
                                    //
                                    // Uma ideia aceita até `TEXT_LIMIT` (4000)
                                    // caracteres, o que é folgado de propósito
                                    // — mas sem teto de linhas um texto colado
                                    // empurrava o resto do mural para fora da
                                    // tela, e as outras ideias sumiam. O mural
                                    // é uma parede de bilhetes: bilhete que
                                    // ocupa a parede inteira deixou de ser um.
                                    maximumLineCount: 4
                                    elide: Text.ElideRight
                                    Behavior on opacity { NumberAnimation { duration: Theme.gesto } }
                                }
                                Text {
                                    text: cartaz.usada
                                          ? modelData.when + " · virou tarefa"
                                          : modelData.when
                                    color: Theme.textoSuave
                                    opacity: cartaz.usada ? 0.6 : 1.0
                                    font.pixelSize: Theme.nano
                                }
                            }

                            Row {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                spacing: 0
                                opacity: sobre.hovered ? 1 : 0
                                visible: opacity > 0.01
                                Behavior on opacity { NumberAnimation { duration: Theme.reacao } }

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

                    Rolagem {
                        anchors.fill: mural
                        lista: mural
                    }

                    CampoTexto {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        limite: backend.textLimit
                        placeholder: "o que passou pela cabeça?"
                        onAceito: function (texto) {
                            backend.captureIdea(texto)
                            limpar()
                        }
                    }
                }

                // ------------------------------------------- retrospectiva

                Retrospectiva {
                    anchors.fill: parent
                    opacity: janela.aba === "dia" ? 1 : 0
                    visible: opacity > 0.01
                    Behavior on opacity {
                        NumberAnimation { duration: Theme.gesto }
                    }
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

                // Dentro de um Loader, e é o único painel que precisa disso.
                //
                // Os quatro painéis se cruzam por opacidade, então todos ficam
                // instanciados o tempo todo — o que é barato para os outros
                // três e não era para este. `weekDays`, `weekDelivered` e
                // `weekMinutes` são notificados por `weekChanged`, que o
                // `_recomputar` emite a **cada evento gravado**: com os
                // bindings vivos, toda tarefa concluída pagava a semana inteira
                // com o painel fechado. Medido em 95 ms por clique com um ano
                // de log, e 301 ms com três anos — justamente no gesto em que a
                // estante deveria animar suave.
                //
                // `active` só liga quando a aba é a semana; o fade continua
                // sendo do Loader, então a transição não muda.
                Loader {
                    anchors.fill: parent
                    active: janela.aba === "semana" || opacity > 0.01
                    opacity: janela.aba === "semana" ? 1 : 0
                    visible: opacity > 0.01
                    Behavior on opacity {
                        NumberAnimation { duration: Theme.gesto }
                    }
                    sourceComponent: Semana {
                        dias: backend.weekDays
                        titulo: backend.weekTitle
                        periodo: backend.weekRange
                        entregas: backend.weekDelivered
                        minutos: backend.weekMinutes
                        recuo: backend.weekOffset
                        temAnterior: backend.hasPreviousWeek
                        onAnterior: backend.previousWeek()
                        onSeguinte: backend.nextWeek()
                        onGuardarPagina: backend.exportCurrentWeek()
                    }
                }
            }
        }
    }

    // ------------------------------------------------------- barra de baixo

    // Duas ilhas, e não uma faixa de ponta a ponta.
    //
    // A barra era uma laje que atravessava a tela inteira com o cronômetro numa
    // ponta, os botões na outra e um vazio enorme no meio — a peça mais
    // "aplicativo" da tela, e a que cortava o chão do quarto em dois. O vazio
    // não era espaço de respiro: era superfície pintada sobre a ilustração para
    // não ligar nada a nada.
    //
    // Agora são dois agrupamentos flutuando sobre o chão, e o chão aparece
    // entre eles. Nada se perde: os controles continuam exatamente onde a mão
    // já procurava, cada um ancorado no seu canto. O que sai é a ponte de
    // pixels que só existia porque a barra tinha que ser um retângulo.
    //
    // `barra` continua existindo como guia de layout — é a ela que a gaveta se
    // ancora por cima —, mas não desenha mais nada.
    Item {
        id: barra
        height: 76
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 24

        // A ilha do tempo: o relógio e, debaixo dele, o que o "começar" pega.
        //
        // A segunda linha não é legenda: é um controle. Enquanto o timer está
        // parado ela mostra a tarefa escolhida e abre a lista de escolha; com o
        // timer correndo ela vira o nome do que está sendo feito e para de
        // responder, porque trocar de tarefa no meio da sessão seria trocar o
        // que o log já está gravando.
        Painel {
            id: ilhaTempo
            sombra: true
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            // A largura acompanha o conteúdo em vez de ser fatia da janela: é o que
            // faz a ilha ser do tamanho do que ela carrega, em qualquer resolução.
            width: relogio.width + 2 * Theme.espacoGrande

            // Bem mais translúcida que a gaveta: aqui não há texto para ler, só
            // controle. Opaca, vira rodapé de aplicativo. Firma um pouco com o
            // mouse por perto.
            opacidadeFundo: sobreTempo.hovered
                            ? Theme.opacidadePainel : Theme.opacidadeBarra
            HoverHandler { id: sobreTempo }

            Column {
                id: relogio
                anchors.left: parent.left
                anchors.leftMargin: Theme.espacoGrande
                anchors.verticalCenter: parent.verticalCenter
                width: 300
                spacing: 2

                Text {
                    text: backend.elapsedText
                    // Algarismos de largura fixa. Sem isto o relógio
                    // treme: na Inter o "1" é mais estreito que o
                    // "0", então 00:00 e 11:11 não medem igual e o
                    // texto se mexe a cada segundo.
                    font.features: Theme.digitos
                    color: backend.timerRunning ? Theme.ambar : Theme.textoSuave
                    font.pixelSize: Theme.destaque
                    font.letterSpacing: 1
                    Behavior on color { ColorAnimation { duration: Theme.gesto } }
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
                        font.pixelSize: Theme.nano
                        color: escolher.containsMouse ? Theme.ambar : Theme.textoSuave
                        opacity: parent.escolhivel ? 0.8 : 0
                        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }
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

        }

        // A ilha das ações. A largura anda com o conteúdo, então quando
        // "entreguei" e "fui interrompido" chegam a ilha cresce junto com eles
        // — o mesmo gesto de `BotaoSuave.mostrando`, agora com a borda do
        // painel acompanhando em vez de um buraco aparecendo dentro dele.
        Painel {
            id: ilhaAcoes
            sombra: true
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: acoes.width + 2 * Theme.espacoGrande
            opacidadeFundo: sobreAcoes.hovered
                            ? Theme.opacidadePainel : Theme.opacidadeBarra
            HoverHandler { id: sobreAcoes }

            Row {
                id: acoes
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
    }

    // ------------------------------------------------------ o toque do quarto

    // Duas horas correndo, e o quarto comenta.
    //
    // Daí para cima o caso comum não é foco, é timer esquecido — e quem
    // esqueceu não vai olhar o relógio por conta própria, que é justamente o
    // problema. Volta de meia em meia hora, com outra frase, porque quem saiu
    // da mesa às 19h50 não estava lá para ver o primeiro.
    //
    // O tom é o do resto do app: observação do quarto, não aviso de sistema.
    // Nenhuma frase diz quanto tempo passou nem sugere que se devia estar
    // trabalhando — o relógio da barra já mostra o número para quem quiser.
    //
    // Os três botões são as três saídas que fazem sentido a essa altura, e a
    // razão de o toque existir: não é para informar, é para dar onde clicar.
    property string toqueTexto: ""

    Connections {
        target: backend
        function onNudged(frase) {
            janela.toqueTexto = frase
            toque.aberto = true
            relogioDoToque.restart()
        }
    }

    Timer {
        id: relogioDoToque
        interval: 12000
        onTriggered: toque.aberto = false
    }

    Painel {
        id: toque
        property bool aberto: false

        width: Math.min(430, parent.width - 48)
        height: colunaToque.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: barra.top
        anchors.bottomMargin: aberto ? 14 : -10

        // Some junto com a sessão: um lembrete sobre um relógio que já parou
        // é o app falando sozinho.
        opacity: aberto && backend.timerRunning ? 1 : 0
        visible: opacity > 0.01

        Behavior on anchors.bottomMargin {
            NumberAnimation { duration: Theme.chegada; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: Theme.chegada } }

        Column {
            id: colunaToque
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                text: janela.toqueTexto
                color: Theme.texto
                font.pixelSize: Theme.corpo
            }

            Row {
                anchors.right: parent.right
                spacing: 4

                BotaoSuave {
                    text: "deixa correr"
                    onClicked: toque.aberto = false
                }

                BotaoSuave {
                    text: "encerrar o dia"
                    corAtiva: Theme.terracota
                    onClicked: {
                        toque.aberto = false
                        janela.aba = "dia"
                    }
                }

                BotaoSuave {
                    text: "parar"
                    onClicked: {
                        toque.aberto = false
                        backend.endSession(false, "")
                    }
                }

                BotaoSuave {
                    text: "entreguei"
                    mostrando: backend.currentTaskId !== ""
                    destacado: true
                    corAtiva: Theme.musgo
                    tamanho: Theme.corpo
                    onClicked: {
                        toque.aberto = false
                        backend.endSessionAndComplete()
                    }
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
            NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
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
            NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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

            // O irmão do som, e pelo mesmo motivo.
            //
            // Cinco coisas se mexem sozinhas aqui dentro para sempre. São o
            // ambiente, e ao mesmo tempo a única coisa do app que gasta
            // máquina sem ninguém pedir — o grão repinta a janela a cada
            // 900 ms a tarde inteira. Quem precisa de sossego na visão
            // periférica, ou de bateria, desliga aqui. A reação ao mouse
            // continua: o quarto fica quieto, não morto.
            LinhaMenu {
                width: parent.width
                rotulo: "movimento"
                valor: backend.motionOn ? "o quarto respira" : "o quarto quieto"
                onClicado: backend.toggleMotion()
            }

            Rectangle {
                width: parent.width; height: 1; color: Theme.borda
            }

            // O passeio da primeira abertura não some para sempre.
            //
            // Ele aparece sozinho enquanto o log está vazio, e some assim que
            // a primeira coisa é escrita — o que é certo, mas deixaria quem
            // dispensou cedo demais sem caminho de volta. Aqui está o caminho.
            LinhaMenu {
                width: parent.width
                rotulo: "o passeio"
                valor: "ver de novo"
                onClicado: {
                    janela.menuAberto = false
                    backend.startTour()
                }
            }

            // Levar o quarto embora.
            //
            // Um log de anos sem saída é um refém: o banco é SQLite e o esquema
            // é simples, mas "abra o sqlite3 e escreva um SELECT" não é uma
            // saída, é a ausência de uma. Aqui a estante, o diário e o mural
            // viram uma página de texto que se lê sem o Cantinho instalado.
            //
            // Fica ao lado do passeio e não perto de "sair" de propósito: não é
            // um gesto de despedida. É a mesma natureza do passeio — as duas
            // linhas que falam sobre o app em vez de ajustarem o ambiente.
            LinhaMenu {
                width: parent.width
                rotulo: "a página"
                valor: "guardar uma cópia"
                onClicado: {
                    janela.menuAberto = false
                    backend.exportEverything()
                }
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

    // ------------------------------------------------------ a página saiu

    // Confirmação de que a página foi escrita, com o caminho e o jeito de
    // chegar nela.
    //
    // Uma exportação sem retorno na tela é indistinguível de uma exportação que
    // não aconteceu — e como o arquivo vai para uma pasta ao lado do banco, sem
    // esta tira ninguém saberia onde procurar. É por isso que ela existe, e é
    // por isso que "abrir a pasta" está aqui: o caminho não é para ser decorado.
    //
    // Some sozinha. Não pede resposta porque não há decisão nenhuma a tomar: o
    // arquivo já está no disco.
    property string paginaEscrita: ""

    Connections {
        target: backend
        function onExported(caminho) {
            janela.paginaEscrita = caminho
            pagina.aberta = true
            relogioDaPagina.restart()
        }
        function onExportFailed() {
            janela.paginaEscrita = ""
            pagina.falhou = true
            pagina.aberta = true
            relogioDaPagina.restart()
        }
    }

    Timer {
        id: relogioDaPagina
        interval: 9000
        onTriggered: pagina.aberta = false
    }

    Painel {
        id: pagina
        property bool aberta: false
        property bool falhou: false

        sombra: true
        width: Math.min(480, parent.width - 48)
        height: colunaPagina.height + 2 * Theme.espacoGrande
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: barra.top
        anchors.bottomMargin: aberta ? 14 : -10

        opacity: aberta ? 1 : 0
        visible: opacity > 0.01

        Behavior on anchors.bottomMargin {
            NumberAnimation { duration: Theme.chegada; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: Theme.chegada } }

        Column {
            id: colunaPagina
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: 6

            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.3
                text: pagina.falhou
                      ? "Não deu para escrever a página aqui."
                      : "A página está guardada."
                color: Theme.texto
                font.pixelSize: Theme.corpo
            }

            Text {
                width: parent.width
                wrapMode: Text.WrapAnywhere
                maximumLineCount: 2
                elide: Text.ElideMiddle
                visible: !pagina.falhou
                text: janela.paginaEscrita
                color: Theme.textoSuave
                font.pixelSize: Theme.nano
            }

            Row {
                anchors.right: parent.right
                spacing: 4

                BotaoSuave {
                    text: "ok"
                    onClicked: pagina.aberta = false
                }

                BotaoSuave {
                    text: "abrir a pasta"
                    mostrando: !pagina.falhou
                    destacado: true
                    corAtiva: Theme.musgo
                    tamanho: Theme.corpo
                    onClicked: {
                        pagina.aberta = false
                        backend.openExportFolder()
                    }
                }
            }
        }
    }

    // ------------------------------------------------------ sair do app

    // Fechar a janela deixa o app na bandeja, o que é o comportamento certo mas
    // não dá jeito de encerrar de verdade sem ir até o ícone. A confirmação
    // existe porque a diferença entre "esconder" e "encerrar" não é óbvia: quem
    // clica em sair esperando o primeiro fecha o app inteiro. A sessão aberta,
    // essa, é guardada de qualquer jeito — ver `endOpenSession` no backend.
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.45)
        opacity: saida.aberta ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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

        Behavior on y { NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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
                      ? "Tem uma sessão correndo. Ela é guardada no diário antes de sair."
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
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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

        Behavior on y { NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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
                limite: backend.textLimit
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
            if (passeio.visible) backend.dismissTour()
            else if (captura.aberta) captura.aberta = false
            else if (saida.aberta) saida.aberta = false
            else if (seletor.aberto) seletor.aberto = false
            else if (janela.menuAberto) janela.menuAberto = false
            else janela.aba = ""
        }
    }

    // ------------------------------------------------------------- o passeio

    // Por cima de tudo, e por último no arquivo — que é o que garante isso sem
    // precisar mexer em `z`. Na primeira abertura ele é a única coisa da tela
    // que pede atenção; nas outras nem existe. Ver `showTour` no backend.
    Passeio {
        id: passeio
        objectName: "passeio"
        anchors.fill: parent

        // Os balões apontam para coisas desenhadas na cena, e a cena se desloca
        // dentro da janela. Sem o quarto aqui, eles se guiam pela janela e
        // acabam por cima do que estão explicando.
        cena: quarto

        opacity: backend.showTour ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.chegada } }

        // Recomeçar do primeiro passo a cada vez que ele é chamado: quem pede
        // "ver de novo" no menu quer o passeio, não o passo onde parou.
        onVisibleChanged: if (visible) recomecar()

        onFechar: backend.dismissTour()
    }
}
