import QtQuick
import theme

// Papel pregado na parede. Base do calendário e do bilhete do dia.
//
// A opacidade é bem mais baixa que a dos painéis porque estes objetos não são
// interface por cima do quarto: são coisas penduradas dentro dele. Um retângulo
// sólido na parede lê como caixa de diálogo esquecida aberta; um papel
// translúcido, com a parede aparecendo através, lê como papel.
//
// Tudo é medido em unidades do viewBox da cena e multiplicado por `unidade`,
// para o quarto inteiro crescer junto quando a janela cresce.
Rectangle {
    id: folha

    // Escala da cena. Vem do Room.
    property real unidade: 1.0

    // 0 quando ninguém está olhando, 1 com o mouse em cima. Sobe o contraste
    // do papel sem mudar nada de lugar.
    property real destaque: 0.0

    // Inclinação de papel pregado por um prego só. Um grau e pouco: o
    // suficiente para não parecer alinhado por régua.
    property real inclinacao: -1.1

    property bool prego: true

    rotation: inclinacao
    transformOrigin: Item.Top

    color: Qt.rgba(Theme.superficie.r, Theme.superficie.g, Theme.superficie.b,
                   Theme.opacidadeParede + 0.20 * destaque)
    radius: 3 * unidade
    border.width: 1
    border.color: Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b,
                          0.40 + 0.45 * destaque)

    Behavior on destaque {
        NumberAnimation { duration: 260; easing.type: Easing.OutCubic }
    }

    // O prego. Justifica a inclinação e é o que faz o retângulo virar objeto.
    Rectangle {
        visible: folha.prego
        width: 5 * folha.unidade
        height: width
        radius: width / 2
        anchors.horizontalCenter: parent.horizontalCenter
        y: -height / 2
        color: Theme.textoSuave
        opacity: 0.5 + 0.3 * folha.destaque
    }
}
