import QtQuick
import theme

// Duas horas correndo, e o quarto comenta.
//
// Daí para cima o caso comum não é foco, é timer esquecido — e quem esqueceu não
// vai olhar o relógio por conta própria, que é justamente o problema. Volta de
// meia em meia hora, com outra frase, porque quem saiu da mesa às 19h50 não
// estava lá para ver o primeiro.
//
// O tom é o do resto do app: observação do quarto, não aviso de sistema. Nenhuma
// frase diz quanto tempo passou nem sugere que se devia estar trabalhando — o
// relógio da barra já mostra o número para quem quiser.
//
// Os três botões são as três saídas que fazem sentido a essa altura, e a razão
// de o toque existir: não é para informar, é para dar onde clicar.
Painel {
    id: toque

    // A quem se encostar por baixo: a ilha do rodapé.
    property Item rodape: null

    property bool aberto: false
    property string frase: ""

    signal encerrarODia()

    Connections {
        target: backend
        function onNudged(frase) {
            toque.frase = frase
            toque.aberto = true
            relogio.restart()
        }
    }

    Timer {
        id: relogio
        interval: 12000
        onTriggered: toque.aberto = false
    }

    width: Math.min(430, parent.width - 48)
    height: coluna.height + 2 * Theme.espacoGrande
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: rodape ? rodape.top : parent.bottom
    anchors.bottomMargin: aberto ? 14 : -10

    // Some junto com a sessão: um lembrete sobre um relógio que já parou é o app
    // falando sozinho.
    opacity: aberto && backend.timerRunning ? 1 : 0
    visible: opacity > 0.01

    Behavior on anchors.bottomMargin {
        NumberAnimation { duration: Theme.chegada; easing.type: Easing.OutCubic }
    }
    Behavior on opacity { NumberAnimation { duration: Theme.chegada } }

    Column {
        id: coluna
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.espacoGrande
        spacing: Theme.espaco

        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            lineHeight: 1.3
            text: toque.frase
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
                    toque.encerrarODia()
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
