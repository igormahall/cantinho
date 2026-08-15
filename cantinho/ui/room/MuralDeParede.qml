import QtQuick
import theme

// As ideias que ainda esperam, pregadas na parede.
//
// Das cinco camadas da interface, o mural era a única sem corpo no quarto. O
// calendário abre a semana, o bilhete abre o dia, a estante guarda o que foi
// entregue e a planta guarda o foco das duas semanas — as ideias existiam só
// como uma palavra na barra de baixo. Quem não clicasse ali não tinha como
// saber que havia alguma coisa esperando.
//
// São papeizinhos, e não mais um bilhete: a folha da direita é uma lista, e
// repetir aquele desenho aqui faria a parede ter dois avisos iguais. Aqui cada
// ideia é o seu próprio pedaço de papel, com o seu próprio prego, na largura
// que o texto pediu — que é como um mural de verdade se parece.
//
// **Sem inclinação**, pela mesma razão que o calendário e o bilhete não têm: na
// tela, papel torto lê como desalinhado e não como espontâneo. O que varia é a
// largura, e ela varia porque o texto varia — não por enfeite.
//
// Com o mural vazio não há objeto nenhum: a parede fica lisa. É o inverso de
// mostrar um quadro vazio dizendo "nada aqui ainda", que seria cobrança
// silenciosa por não ter tido ideia. E dá de graça o retorno que faltava à
// captura — o papel **aparecer** na parede é a confirmação de que a ideia foi
// guardada.
//
// Só as soltas ficam aqui. A ideia aproveitada continua no painel, riscada e
// com a data, porque é lá que ela conta que virou tarefa; na parede um papel já
// resolvido é um papel que se tira.
Item {
    id: mural

    // Escala da cena. Vem do Room, como nos outros objetos de parede.
    property real unidade: 1.0

    // Vem pronta do backend: só as ideias soltas, da mais recente para a mais
    // antiga, já cortadas em WALL_IDEAS_LIMIT.
    property var ideias: []

    signal aberto()

    // Medidas em unidades do viewBox da cena.
    readonly property real larguraMax: 196
    readonly property real larguraMin: 76
    readonly property real alturaPapel: 27
    readonly property real espaco: 8
    readonly property real margem: 8

    visible: ideias.length > 0
    width: larguraMax * unidade
    height: coluna.height

    Column {
        id: coluna
        width: parent.width
        spacing: mural.espaco * mural.unidade

        Repeater {
            model: mural.ideias

            // A chegada não é animada aqui, e é decisão e não esquecimento: o
            // Repeater recria os delegates a cada mudança do modelo, então uma
            // entrada animada faria os três papéis piscarem juntos sempre que
            // um deles mudasse. É o mesmo defeito que os slots fixos da estante
            // existem para evitar — o objeto que chega não pode mexer nos que
            // já estavam.
            FolhaDeParede {
                id: papel
                required property var modelData

                unidade: mural.unidade
                destaque: area.containsMouse ? 1.0 : 0.0

                // A largura é a do texto, entre um mínimo e um máximo. Uma
                // ideia de quatro mil caracteres não faz um papel gigante: ela
                // encosta no teto e o resto é elidido, como num bilhete escrito
                // com a letra apertada no fim.
                width: Math.min(mural.larguraMax * mural.unidade,
                                Math.max(mural.larguraMin * mural.unidade,
                                         escrito.implicitWidth
                                         + 2 * mural.margem * mural.unidade))
                height: mural.alturaPapel * mural.unidade

                Text {
                    id: escrito
                    anchors.fill: parent
                    anchors.margins: mural.margem * mural.unidade
                    verticalAlignment: Text.AlignVCenter
                    text: papel.modelData.text
                    color: Theme.texto
                    opacity: papel.lido(0.72)
                    font.pixelSize: Math.round(11 * mural.unidade)
                    font.family: Theme.fontePapel
                    elide: Text.ElideRight
                }

                // O alvo é o papel, e não a coluna inteira: os papéis têm
                // larguras diferentes, e uma área única cobriria a parede nua à
                // direita dos mais curtos — clicar no vazio do quarto fecharia
                // painel numa metade da tela e abriria o mural na outra, sem
                // nada na tela explicando a diferença.
                //
                // Como consequência, acende só o papel sob o cursor, que é o
                // que aconteceria se a mão passasse por eles.
                //
                // Clicar em qualquer um abre o mural inteiro. Escolher uma
                // ideia daqui seria transformar a parede em lista, e a lista já
                // existe no painel — com o riscado, a data e o que fazer com
                // ela.
                MouseArea {
                    id: area
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: backend.sfx("toque")
                    onClicked: {
                        backend.sfx("clique")
                        mural.aberto()
                    }
                }
            }
        }
    }
}
