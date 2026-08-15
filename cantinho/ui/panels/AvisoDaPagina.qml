import QtQuick
import theme

// Confirmação de que a página foi escrita, com o caminho e o jeito de chegar
// nela.
//
// Uma exportação sem retorno na tela é indistinguível de uma exportação que não
// aconteceu — e como o arquivo vai para uma pasta ao lado do banco, sem esta
// tira ninguém saberia onde procurar. É por isso que ela existe, e é por isso
// que "abrir a pasta" está aqui: o caminho não é para ser decorado.
//
// Some sozinha. Não pede resposta porque não há decisão nenhuma a tomar: o
// arquivo já está no disco.
Painel {
    id: aviso

    // A quem se encostar por baixo. É a ilha do rodapé, para a tira nascer de
    // trás dela em vez de flutuar no meio do quarto.
    property Item rodape: null

    property bool aberta: false
    property bool falhou: false
    property string caminho: ""

    Connections {
        target: backend

        function onExported(caminho) {
            aviso.caminho = caminho
            aviso.falhou = false
            aviso.aberta = true
            relogio.restart()
        }

        function onExportFailed() {
            aviso.caminho = ""
            aviso.falhou = true
            aviso.aberta = true
            relogio.restart()
        }
    }

    Timer {
        id: relogio
        interval: 9000
        onTriggered: aviso.aberta = false
    }

    sombra: true
    width: Math.min(480, parent.width - 48)
    height: coluna.height + 2 * Theme.espacoGrande
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: rodape ? rodape.top : parent.bottom
    anchors.bottomMargin: aberta ? 14 : -10

    opacity: aberta ? 1 : 0
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
        spacing: 6

        Text {
            width: parent.width
            wrapMode: Text.WordWrap
            lineHeight: 1.3
            text: aviso.falhou
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
            visible: !aviso.falhou
            text: aviso.caminho
            color: Theme.textoSuave
            font.pixelSize: Theme.nano
        }

        Row {
            anchors.right: parent.right
            spacing: 4

            BotaoSuave {
                text: "ok"
                onClicked: aviso.aberta = false
            }

            BotaoSuave {
                text: "abrir a pasta"
                mostrando: !aviso.falhou
                destacado: true
                corAtiva: Theme.musgo
                tamanho: Theme.corpo
                onClicked: {
                    aviso.aberta = false
                    backend.openExportFolder()
                }
            }
        }
    }
}
