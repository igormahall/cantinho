import QtQuick
import theme

// Superfície translúcida. O quarto continua visível por trás — o painel é uma
// folha apoiada no ambiente, não uma tela que cobre o ambiente.
Rectangle {
    id: painel

    // Quanto o painel cobre o quarto. Quem tem texto para ler sobe; quem é só
    // controle desce. Ver os três níveis em Theme.qml.
    property real opacidadeFundo: Theme.opacidadePainel

    color: Qt.rgba(Theme.superficie.r, Theme.superficie.g, Theme.superficie.b,
                   painel.opacidadeFundo)
    radius: Theme.raio
    border.color: Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b,
                          0.35 + 0.65 * painel.opacidadeFundo)
    border.width: 1

    Behavior on opacidadeFundo {
        NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
    }
}
