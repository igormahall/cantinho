import QtQuick
import theme

// Calendário do mês, pendurado na parede acima da estante.
//
// Ele não é seletor de data: não marca prazo, não sabe de tarefa nenhuma e
// **não marca os dias em que se trabalhou**. Isso viraria mapa de assiduidade,
// que é exatamente o tipo de placar que o projeto recusa. Os números são
// discretos e só o dia de hoje tem cor.
//
// O que ele ganhou foi um clique, que abre a semana. É a leitura literal do
// objeto: um calendário de parede é onde se olha para saber onde a semana está.
// A folha inteira responde, com o mesmo destaque de hover do bilhete — nenhuma
// célula é clicável sozinha, porque escolher um dia seria a tal seleção de data.
// Os números acendem junto com o papel, por `lido()`: de longe o mês é textura
// na parede, e de perto ele é legível.
FolhaDeParede {
    id: calendario

    signal aberto()

    destaque: area.containsMouse ? 1.0 : 0.0

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: backend.sfx("toque")
        onClicked: {
            backend.sfx("clique")
            calendario.aberto()
        }
    }

    // Medidas em unidades do viewBox da cena.
    readonly property real larguraBase: 212
    readonly property real alturaBase: 194
    readonly property real margem: 15

    width: larguraBase * unidade
    height: alturaBase * unidade

    property date agora: new Date()

    // Um minuto basta: o que muda aqui muda à meia-noite.
    Timer {
        interval: 60000
        running: true
        repeat: true
        onTriggered: calendario.agora = new Date()
    }

    readonly property int ano: agora.getFullYear()
    readonly property int mes: agora.getMonth()
    readonly property int hoje: agora.getDate()

    // Dia da semana em que o mês começa (0 = domingo) e quantos dias ele tem.
    // Dia 0 do mês seguinte é o último do atual — é assim que se pega fevereiro
    // bissexto sem escrever regra de bissexto.
    readonly property int primeiraColuna: new Date(ano, mes, 1).getDay()
    readonly property int diasNoMes: new Date(ano, mes + 1, 0).getDate()

    readonly property real celula: (larguraBase - 2 * margem) / 7

    Column {
        x: calendario.margem * calendario.unidade
        y: calendario.margem * calendario.unidade
        width: parent.width - 2 * x
        spacing: 5 * calendario.unidade

        // ------------------------------------------------------- cabeçalho

        Item {
            width: parent.width
            height: 18 * calendario.unidade

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: calendario.agora.toLocaleDateString(Qt.locale("pt_BR"), "MMMM")
                color: Theme.texto
                opacity: calendario.lido(0.85)
                font.pixelSize: Math.round(15 * calendario.unidade)
                font.family: Theme.fontePapel
                font.letterSpacing: 0.5 * calendario.unidade
            }

            Text {
                anchors.right: parent.right
                anchors.baseline: parent.verticalCenter
                anchors.baselineOffset: 5 * calendario.unidade
                text: calendario.ano
                color: Theme.textoSuave
                opacity: calendario.lido(0.7)
                font.pixelSize: Math.round(10 * calendario.unidade)
                font.family: Theme.fontePapel
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Theme.borda
            opacity: calendario.lido(0.6)
        }

        // ---------------------------------------------- iniciais da semana

        Row {
            Repeater {
                model: ["d", "s", "t", "q", "q", "s", "s"]
                Text {
                    width: calendario.celula * calendario.unidade
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData
                    color: Theme.textoSuave
                    opacity: calendario.lido(0.55)
                    font.pixelSize: Math.round(9 * calendario.unidade)
                    font.family: Theme.fontePapel
                }
            }
        }

        // ---------------------------------------------------- grade do mês
        //
        // Seis linhas fixas. Cinco bastam quase sempre e falham nos meses que
        // começam no sábado — e uma grade que muda de altura conforme o mês
        // faria o papel pular de tamanho na parede.

        Grid {
            columns: 7
            rows: 6

            Repeater {
                model: 42

                Item {
                    required property int index

                    readonly property int dia: index - calendario.primeiraColuna + 1
                    readonly property bool doMes: dia >= 1 && dia <= calendario.diasNoMes
                    readonly property bool ehHoje: doMes && dia === calendario.hoje
                    readonly property bool fimDeSemana: index % 7 === 0 || index % 7 === 6

                    width: calendario.celula * calendario.unidade
                    height: 19 * calendario.unidade

                    // Hoje: uma marca de lápis em volta do número, não um botão
                    // selecionado.
                    Rectangle {
                        anchors.centerIn: parent
                        width: 17 * calendario.unidade
                        height: width
                        radius: width / 2
                        visible: parent.ehHoje
                        color: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.18)
                        border.width: 1
                        border.color: Qt.rgba(Theme.ambar.r, Theme.ambar.g,
                                              Theme.ambar.b, 0.55)
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: parent.doMes
                        text: parent.dia
                        color: parent.ehHoje ? Theme.ambar : Theme.texto
                        opacity: calendario.lido(
                                     parent.ehHoje ? 1.0
                                     : (parent.fimDeSemana ? 0.38 : 0.62))
                        font.pixelSize: Math.round(11 * calendario.unidade)
                        font.family: Theme.fontePapel
                    }
                }
            }
        }
    }
}
