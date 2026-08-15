import QtQuick
import QtQuick.Effects
import theme

// Superfície translúcida. O quarto continua visível por trás — o painel é uma
// folha apoiada no ambiente, não uma tela que cobre o ambiente.
Rectangle {
    id: painel

    // Quanto o painel cobre o quarto. Quem tem texto para ler sobe; quem é só
    // controle desce. Ver os três níveis em Theme.qml.
    property real opacidadeFundo: Theme.opacidadePainel

    // A sombra que faz a folha ficar *apoiada* em vez de colada.
    //
    // É o detalhe mais barato que separa "painel na frente do quarto" de
    // "retângulo pintado por cima da ilustração" — sem ela o olho não tem como
    // saber que existem duas camadas, e a cena inteira lê como colagem.
    //
    // Larga, difusa e quase transparente de propósito: sombra dura viraria
    // caixa de diálogo de sistema, que é justamente o que este app não é. E
    // desligável, porque a barra de baixo e a mini não a querem — flutuar é
    // papel de quem cobre alguma coisa.
    property bool sombra: false

    layer.enabled: painel.sombra
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowBlur: 1.0
        shadowVerticalOffset: 6
        shadowHorizontalOffset: 0
        shadowOpacity: Theme.noite ? 0.5 : 0.22
    }

    color: Qt.rgba(Theme.superficie.r, Theme.superficie.g, Theme.superficie.b,
                   painel.opacidadeFundo)
    radius: Theme.raio
    border.color: Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b,
                          0.35 + 0.65 * painel.opacidadeFundo)
    border.width: 1

    Behavior on opacidadeFundo {
        NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
    }
}
