import QtQuick
import theme

// Fechar o dia. O texto já vem montado das sessões; o usuário só confirma e
// diz como estava. Nenhum número de desempenho, nenhuma comparação com ontem.
Item {
    id: raiz

    property var sessoes: []
    property var concluidas: []
    property var revisao: null

    signal salvar(int humor, int energia, string nota)

    property int humor: revisao ? revisao.mood : 3
    property int energia: revisao ? revisao.energy : 3

    onRevisaoChanged: {
        if (revisao) {
            humor = revisao.mood
            energia = revisao.energy
            nota.text = revisao.note
        }
    }

    function duracao(minutos) {
        if (minutos < 60) return minutos + " min"
        var h = Math.floor(minutos / 60)
        var m = minutos % 60
        return m === 0 ? h + "h" : h + "h" + (m < 10 ? "0" : "") + m
    }

    Flickable {
        anchors.fill: parent
        contentHeight: coluna.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: coluna
            width: parent.width
            spacing: Theme.espaco

            Text {
                text: raiz.sessoes.length === 0 && raiz.concluidas.length === 0
                      ? "O dia ainda não tem nada guardado."
                      : "Hoje o cantinho registrou:"
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
            }

            Column {
                width: parent.width
                spacing: 5
                visible: raiz.sessoes.length > 0

                Repeater {
                    model: raiz.sessoes
                    Row {
                        width: coluna.width
                        spacing: 8

                        Text {
                            text: modelData.at
                            color: Theme.textoSuave
                            font.pixelSize: Theme.miudo
                            width: 42
                        }
                        Text {
                            text: modelData.label
                            color: Theme.texto
                            font.pixelSize: Theme.miudo
                            width: coluna.width - 140
                            elide: Text.ElideRight
                        }
                        Text {
                            text: raiz.duracao(modelData.minutes)
                                  + (modelData.interrupted ? " ·" : "")
                            color: modelData.interrupted ? Theme.terracota : Theme.musgo
                            font.pixelSize: Theme.miudo
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 5
                visible: raiz.concluidas.length > 0

                Text {
                    text: "Foi para a estante:"
                    color: Theme.textoSuave
                    font.pixelSize: Theme.miudo
                    topPadding: 6
                }

                Repeater {
                    model: raiz.concluidas
                    Text {
                        text: "· " + modelData
                        color: Theme.musgo
                        font.pixelSize: Theme.miudo
                        width: coluna.width
                        elide: Text.ElideRight
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: Theme.borda }

            EscalaPontos {
                width: parent.width
                rotulo: "humor"
                valor: raiz.humor
                onEscolhido: function (v) { raiz.humor = v }
            }

            EscalaPontos {
                width: parent.width
                rotulo: "energia"
                valor: raiz.energia
                onEscolhido: function (v) { raiz.energia = v }
            }

            CampoTexto {
                id: nota
                width: parent.width
                placeholder: "alguma coisa que valha lembrar (opcional)"
            }

            BotaoSuave {
                text: raiz.revisao ? "guardar de novo" : "guardar o dia"
                destacado: true
                corAtiva: Theme.musgo
                onClicked: raiz.salvar(raiz.humor, raiz.energia, nota.text)
            }
        }
    }
}
