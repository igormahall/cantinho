import QtQuick
import theme

// O que sobra de uma queda: o app morreu sem gravar o fim de uma sessão.
//
// Sair pelo menu, pela bandeja ou fechando a janela já guarda o que estava
// correndo, então isto só aparece depois de falta de energia, sessão do sistema
// derrubada ou processo morto — raro, e por isso discreto: uma tira no alto, que
// não cobre nada e não pede resposta para o app funcionar.
//
// O aviso é informativo, não uma pergunta: a sessão **já foi guardada** na
// última marca de vida do app, que é o último instante em que ele estava
// comprovadamente rodando. Ver a recuperação em `backend.py`. O que sobra para
// decidir é só se você volta a trabalhar naquilo agora — e por isso "continuar
// isso" abre uma sessão nova, não retoma a velha.
Painel {
    id: aviso

    width: Math.min(520, parent.width - 48)
    height: coluna.height + 2 * Theme.espacoGrande
    anchors.horizontalCenter: parent.horizontalCenter
    y: backend.hasRecoveredSession ? 24 : -height

    opacity: backend.hasRecoveredSession ? 1 : 0
    visible: opacity > 0.01

    Behavior on y { NumberAnimation { duration: Theme.chegada; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

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
