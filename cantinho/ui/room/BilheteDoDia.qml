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
//
// A segunda coluna é o tempo que cada tarefa recebeu hoje. Ela nasceu de um
// problema de layout — metade da folha ficava vazia e nunca ia encher — e
// resolveu um problema de uso: o tempo por tarefa só existia dentro da
// retrospectiva, no fim do dia, que é tarde demais para ele informar alguma
// coisa. Aqui ele fica à vista o tempo todo, sem ninguém abrir nada.
//
// Continua sendo um diário, não um placar: são minutos do dia de hoje, sem
// meta, sem comparação com ontem e sem nada somando para além da meia-noite.
FolhaDeParede {
    id: bilhete

    // A folha tem tamanho fixo: seis linhas, o rodapé e as margens cabem
    // exatamente. Ver BOARD_LIMIT no backend — é a folha que limita a lista,
    // não a projeção.
    readonly property real larguraBase: 300
    readonly property real alturaBase: 172
    readonly property real margem: 16

    // Largura reservada ao tempo, no fim de cada linha.
    readonly property real colunaTempo: 52

    // Linhas prontas, vindas do backend: abertas primeiro, concluídas de hoje
    // riscadas no fim.
    property var linhas: []
    property int minutosDoDia: 0
    property string tarefaAtual: ""

    signal aberto()

    width: larguraBase * unidade
    height: alturaBase * unidade
    destaque: area.containsMouse ? 1.0 : 0.0

    // "1h35" e não "95 min": em horas o número para de crescer e volta a ser
    // legível de relance, que é como um bilhete na parede é lido.
    function duracao(minutos) {
        if (minutos <= 0) return ""
        if (minutos < 60) return minutos + "min"
        var h = Math.floor(minutos / 60)
        var m = minutos % 60
        return m === 0 ? h + "h" : h + "h" + (m < 10 ? "0" : "") + m
    }

    Column {
        id: conteudo
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

            Item {
                required property var modelData

                readonly property bool feita: modelData.done
                readonly property bool emCurso: !feita
                                                && modelData.id === bilhete.tarefaAtual

                width: parent.width
                height: 15 * bilhete.unidade

                // Marca de item: círculo vazio enquanto está aberto, cheio
                // depois. É o mesmo círculo do backlog, reduzido.
                Rectangle {
                    id: marca
                    anchors.verticalCenter: parent.verticalCenter
                    width: 7 * bilhete.unidade
                    height: width
                    radius: width / 2
                    color: feita ? Theme.musgo : (emCurso ? Theme.ambar : "transparent")
                    border.width: Math.max(1, 1.2 * bilhete.unidade)
                    border.color: feita ? Theme.musgo
                                  : (emCurso ? Theme.ambar : Theme.textoSuave)
                    opacity: feita ? 0.55 : 0.8
                    Behavior on color { ColorAnimation { duration: Theme.chegada } }
                }

                Text {
                    anchors.left: marca.right
                    anchors.leftMargin: 7 * bilhete.unidade
                    anchors.right: tempo.left
                    anchors.rightMargin: 6 * bilhete.unidade
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.label
                    color: emCurso ? Theme.ambar : Theme.texto
                    opacity: feita ? 0.42 : (emCurso ? 1.0 : 0.78)
                    font.pixelSize: Math.round(12 * bilhete.unidade)
                    font.strikeout: feita
                    elide: Text.ElideRight
                    Behavior on opacity { NumberAnimation { duration: Theme.chegada } }
                }

                // Alinhado à direita, para os números formarem uma coluna. Sem
                // tempo o espaço fica vazio em vez de mostrar "0min": tarefa
                // que ainda não recebeu nada não precisa dizer isso.
                Text {
                    id: tempo
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: bilhete.colunaTempo * bilhete.unidade
                    horizontalAlignment: Text.AlignRight
                    text: bilhete.duracao(modelData.minutes)
                    color: emCurso ? Theme.ambar : Theme.musgo
                    opacity: feita ? 0.5 : 0.75
                    font.pixelSize: Math.round(11 * bilhete.unidade)
                }
            }
        }
    }

    // Rodapé: o total do dia, encostado na base da folha. Fica longe da lista
    // de propósito — é o resumo, não mais uma linha dela.
    Item {
        anchors.left: conteudo.left
        anchors.right: conteudo.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: bilhete.margem * bilhete.unidade * 0.7
        height: 14 * bilhete.unidade
        visible: bilhete.minutosDoDia > 0

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.borda
            opacity: 0.7
        }

        Text {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            text: "no dia"
            color: Theme.textoSuave
            opacity: 0.6
            font.pixelSize: Math.round(10 * bilhete.unidade)
        }

        Text {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: bilhete.colunaTempo * bilhete.unidade
            horizontalAlignment: Text.AlignRight
            text: bilhete.duracao(bilhete.minutosDoDia)
            color: Theme.musgo
            opacity: 0.85
            font.pixelSize: Math.round(11 * bilhete.unidade)
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
