import QtQuick
import theme

// A marca de que a lista continua.
//
// As listas do app rolam desde sempre e não diziam isso: `clip: true` e nenhum
// indicador. Com sete tarefas no backlog, a oitava simplesmente não existia
// para quem olhava — não havia como saber que faltava alguma coisa nem que
// havia para onde arrastar.
//
// A resposta não é barra de rolagem: uma barra é cromo de aplicativo, ocupa
// espaço fixo e fica lá parada dizendo "isto é um widget". O que se usa aqui é
// **o desvanecimento das bordas**: onde a lista continua, o conteúdo dissolve
// no fundo do painel em vez de ser cortado numa reta. É a mesma pista que uma
// folha dobrada dá, e ela aparece só quando há conteúdo do outro lado.
//
// Uso: coloque por cima de um Flickable/ListView, ancorado nos mesmos limites.
//
//     Rolagem { lista: minhaListView; anchors.fill: minhaListView }
Item {
    id: raiz

    // O Flickable ou ListView observado.
    property Flickable lista: null

    // A cor em que o conteúdo dissolve: a do painel que está por trás.
    property color corDoFundo: Theme.superficie

    // Altura da faixa que desvanece.
    readonly property int faixa: 22

    // `anchors.fill` no alvo é o uso normal, mas o toque tem que atravessar:
    // isto é uma pista visual, não um controle.
    z: 5

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: raiz.faixa

        // Só quando há coisa acima. `contentY` maior que o topo do conteúdo
        // significa que a lista foi arrastada para baixo.
        opacity: (raiz.lista && raiz.lista.contentY > 2) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        gradient: Gradient {
            GradientStop { position: 0.0; color: raiz.corDoFundo }
            GradientStop {
                position: 1.0
                color: Qt.rgba(raiz.corDoFundo.r, raiz.corDoFundo.g,
                               raiz.corDoFundo.b, 0)
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: raiz.faixa

        // Só quando ainda falta conteúdo embaixo.
        opacity: (raiz.lista
                  && raiz.lista.contentHeight > raiz.lista.height + 2
                  && raiz.lista.contentY < raiz.lista.contentHeight
                                           - raiz.lista.height - 2) ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        gradient: Gradient {
            GradientStop {
                position: 0.0
                color: Qt.rgba(raiz.corDoFundo.r, raiz.corDoFundo.g,
                               raiz.corDoFundo.b, 0)
            }
            GradientStop { position: 1.0; color: raiz.corDoFundo }
        }
    }
}
