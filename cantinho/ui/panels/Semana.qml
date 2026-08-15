import QtQuick
import theme

// A semana: o que foi entregue, dia a dia.
//
// É o retorno de médio prazo que faltava. A estante mostra tudo o que já foi
// feito, sem data; o bilhete mostra hoje e some à meia-noite. Entre os dois não
// havia nada, e "a semana passou e eu não sei no quê" é uma sensação ruim que o
// app tinha como responder e não respondia.
//
// O que ela não é, de propósito: não tem barra, não tem percentual, não compara
// um dia com o outro e não diz nada sobre os dias em branco além de que estão em
// branco. Dia vazio é dia vazio — descanso conta como dia.
//
// O único número é a soma do rodapé, que é a mesma conta que o bilhete da parede
// já faz para um dia. Somar não cobra nada; comparar cobraria, e é por isso que
// os minutos não aparecem linha a linha.
Item {
    id: raiz

    property var dias: []
    property string titulo: ""
    property string periodo: ""
    property int entregas: 0
    property int minutos: 0
    property int recuo: 0
    // O passado tem fim, e ele é o primeiro evento do log. A seta apaga lá
    // pelo mesmo motivo que a outra apaga em "esta semana": adiante e atrás do
    // log não há o que mostrar, só sete dias vazios repetidos para sempre.
    property bool temAnterior: true

    signal anterior()
    signal seguinte()
    signal guardarPagina()

    function duracao(m) {
        if (m < 60) return m + " min"
        var h = Math.floor(m / 60)
        var r = m % 60
        return r === 0 ? h + "h" : h + "h" + (r < 10 ? "0" : "") + r
    }

    // ------------------------------------------------------- navegação

    Item {
        id: cabecalho
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 30

        Column {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1

            // O período em cima e o "esta semana" embaixo, e não o contrário:
            // o título do painel já diz "a semana", então repeti-lo em corpo
            // maior seria dizer a mesma coisa duas vezes. O que muda quando se
            // navega para trás são as datas.
            Text {
                text: raiz.periodo
                color: Theme.texto
                font.pixelSize: Theme.corpo
            }
            Text {
                text: raiz.titulo
                color: raiz.recuo === 0 ? Theme.textoSuave : Theme.ambar
                font.pixelSize: Theme.nano
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            BotaoSuave {
                text: "‹"
                tamanho: Theme.corpo
                opacity: raiz.temAnterior ? 1 : 0.25
                enabled: raiz.temAnterior
                onClicked: raiz.anterior()
            }

            BotaoSuave {
                text: "›"
                tamanho: Theme.corpo
                // Não passa desta semana: o cantinho não tem nada a dizer do
                // que ainda não aconteceu.
                opacity: raiz.recuo > 0 ? 1 : 0.25
                enabled: raiz.recuo > 0
                onClicked: raiz.seguinte()
            }
        }
    }

    Rectangle {
        id: risco
        anchors.top: cabecalho.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.borda
    }

    // ------------------------------------------------------------ os dias

    Flickable {
        id: rolo
        anchors.top: risco.bottom
        anchors.topMargin: Theme.espaco
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: rodape.top
        anchors.bottomMargin: Theme.espaco
        contentHeight: coluna.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: coluna
            width: parent.width
            spacing: 10

            Repeater {
                model: raiz.dias

                Item {
                    required property var modelData

                    readonly property bool vazio: modelData.delivered.length === 0

                    width: coluna.width
                    height: Math.max(20, entregues.height)
                    opacity: modelData.ahead ? 0.28 : 1.0

                    // A data. Hoje ganha cor, como no calendário da parede —
                    // é a mesma marca de lápis, não um item selecionado.
                    Column {
                        id: data
                        width: 54
                        spacing: 0

                        Text {
                            text: modelData.weekday
                            color: modelData.today ? Theme.ambar : Theme.textoSuave
                            font.pixelSize: Theme.nano
                        }
                        Text {
                            text: modelData.day
                            color: modelData.today ? Theme.ambar : Theme.texto
                            opacity: modelData.today ? 1.0 : 0.7
                            font.pixelSize: Theme.miudo
                        }
                    }

                    Column {
                        id: entregues
                        anchors.left: data.right
                        anchors.right: humor.left
                        anchors.rightMargin: 8
                        anchors.top: parent.top
                        spacing: 3

                        Text {
                            width: parent.width
                            visible: vazio
                            text: modelData.ahead ? "" : "—"
                            color: Theme.textoSuave
                            opacity: 0.45
                            font.pixelSize: Theme.miudo
                        }

                        Repeater {
                            model: modelData.delivered

                            Row {
                                required property string modelData
                                width: entregues.width
                                spacing: 8

                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 6; height: 6; radius: 3
                                    color: Theme.musgo
                                    opacity: 0.75
                                }

                                Text {
                                    width: parent.width - 14
                                    text: modelData
                                    color: Theme.texto
                                    opacity: 0.85
                                    font.pixelSize: Theme.miudo
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Text {
                            width: parent.width
                            visible: modelData.note !== ""
                            text: modelData.note
                            color: Theme.textoSuave
                            font.pixelSize: Theme.nano
                            font.italic: true
                            wrapMode: Text.WordWrap
                        }
                    }

                    // Humor do dia, se houve. Pontinhos, os mesmos da escala —
                    // nunca uma nota, nunca uma média.
                    Row {
                        id: humor
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: 5
                        spacing: 3
                        visible: modelData.mood > 0

                        Repeater {
                            model: modelData.mood
                            Rectangle {
                                width: 4; height: 4; radius: 2
                                color: Theme.ambar
                                opacity: 0.55
                            }
                        }
                    }
                }
            }
        }
    }

    // --------------------------------------------------------------- rodapé

    Column {
        id: rodape
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 4

        Rectangle { width: parent.width; height: 1; color: Theme.borda }

        Item { width: 1; height: 2 }

        Text {
            width: parent.width
            text: raiz.entregas === 0
                  ? "nada foi para a estante nesta semana"
                  : raiz.entregas === 1
                    ? "uma coisa foi para a estante"
                    : raiz.entregas + " coisas foram para a estante"
            color: Theme.musgo
            font.pixelSize: Theme.miudo
        }

        Text {
            width: parent.width
            visible: raiz.minutos > 0
            text: "e " + raiz.duracao(raiz.minutos) + " de cantinho"
            color: Theme.textoSuave
            font.pixelSize: Theme.miudo
        }

        // **A resposta deste projeto ao horizonte mais longo.**
        //
        // A semana é a costura por onde o Cantinho poderia virar planilha: é o
        // único painel com um número somado e navegação temporal, e daqui todo
        // pedido natural — "e o mês?", "e o ano?", "e comparado com a semana
        // passada?" — é um passo em direção ao dashboard que o projeto recusa.
        //
        // A saída não é um painel maior: é uma **página**. Ver mais que uma
        // semana é gerar o diário daquele período e lê-lo como texto, fora do
        // app. A diferença não é de formato, é de natureza: um painel de mês
        // seria mais tela no mesmo lugar, com a mesma pressão de virar
        // comparação; a página é um artefato que se lê, se guarda e se fecha.
        //
        // Por isso o botão está aqui, no rodapé da semana, e não escondido num
        // menu: é neste painel que a pergunta aparece.
        Item { width: 1; height: 4 }

        BotaoSuave {
            anchors.right: parent.right
            text: "guardar esta página"
            tamanho: Theme.miudo
            onClicked: raiz.guardarPagina()
        }
    }

    Rolagem {
        anchors.fill: rolo
        lista: rolo
    }
}
