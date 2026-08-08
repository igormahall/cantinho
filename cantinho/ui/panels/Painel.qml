import QtQuick
import theme

// Superfície translúcida. O quarto continua visível por trás — o painel é uma
// folha apoiada no ambiente, não uma tela que cobre o ambiente.
Rectangle {
    id: painel
    color: Qt.rgba(Theme.superficie.r, Theme.superficie.g, Theme.superficie.b,
                   Theme.opacidadePainel)
    radius: Theme.raio
    border.color: Theme.borda
    border.width: 1
}
