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
            menu.aberto = false
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
        menu.aberto = false
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

        // Os papéis da parede que respondem a clique, cada um abrindo a sua
        // leitura literal: o bilhete abre o "hoje", o calendário abre a semana,
        // os papeizinhos abrem o mural. O relógio não abre nada — não há painel
        // nenhum que seja "as horas".
        onAbrirHoje: janela.aba = "backlog"
        onAbrirSemana: janela.aba = "semana"
        onAbrirIdeias: janela.aba = "ideias"
    }

    // Clicar no vazio do quarto fecha o painel aberto.
    MouseArea {
        anchors.fill: parent
        enabled: janela.aba !== ""
        onClicked: janela.recolher()
    }

    // ------------------------------------------------- sessão que ficou aberta

    AvisoDeQueda {}

    // ------------------------------------------ o que mais se fechou junto

    PerguntaDoExtra {}

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
                    destacado: menu.aberto
                    onClicked: {
                        seletor.aberto = false
                        menu.aberto = !menu.aberto
                    }
                }
            }
        }
    }

    // ------------------------------------------------------ o toque do quarto

    ToqueDoQuarto {
        rodape: barra
        onEncerrarODia: janela.aba = "dia"
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

    MenuDoQuarto {
        id: menu
        rodape: barra
        onSair: saida.aberta = true
    }

    // ------------------------------------------------------ a página saiu

    AvisoDaPagina { rodape: barra }

    // ------------------------------------------------------ sair do app

    SaidaDoApp { id: saida }

    // ------------------------------------------------- captura de ideia

    CapturaDeIdeia { id: captura }

    // Trazer a janela para a frente é assunto da janela e não do painel: o
    // atalho global chega com o app escondido na bandeja, e um campo de texto
    // com foco atrás de outra aplicação não recebe o que se digita.
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
            else if (menu.aberto) menu.aberto = false
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
