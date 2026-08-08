import QtQuick
import theme

// Relógio de parede, no alto à direita.
//
// Sem ponteiro de segundos, de propósito. Segundo ponteiro é o que transforma
// um relógio em cronômetro: ele se mexe o tempo todo, puxa o olho e conta.
// Hora e minuto dizem em que ponto do dia se está, que é a única pergunta que
// esta tela precisa responder.
//
// Também não há número no mostrador. A posição dos ponteiros já é a leitura, e
// doze algarismos pequenos na parede viram sujeira visual.
Item {
    id: relogio

    // Escala da cena. Vem do Room.
    property real unidade: 1.0

    readonly property real diametroBase: 128
    width: diametroBase * unidade
    height: width

    property date agora: new Date()

    // Dez segundos: o ponteiro dos minutos anda um grau por passo, o que é
    // menos de um pixel na ponta. O passo não se vê.
    Timer {
        interval: 10000
        running: true
        repeat: true
        onTriggered: relogio.agora = new Date()
    }

    readonly property real anguloMinuto: agora.getMinutes() * 6
    readonly property real anguloHora: (agora.getHours() % 12) * 30
                                       + agora.getMinutes() * 0.5

    // Prego, como no calendário: o relógio está pendurado, não flutuando.
    Rectangle {
        width: 5 * relogio.unidade
        height: width
        radius: width / 2
        anchors.horizontalCenter: parent.horizontalCenter
        y: -height
        color: Theme.textoSuave
        opacity: 0.5
    }

    // ------------------------------------------------------------ mostrador

    Rectangle {
        id: mostrador
        anchors.fill: parent
        radius: width / 2
        color: Qt.rgba(Theme.superficie.r, Theme.superficie.g, Theme.superficie.b,
                       Theme.opacidadeParede)
        border.width: Math.max(1, 2 * relogio.unidade)
        border.color: Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b, 0.75)
    }

    // ---------------------------------------------------------------- marcas
    //
    // Doze traços, com os quatro das horas cheias mais compridos. É o que dá a
    // leitura de relance sem escrever número nenhum.

    Repeater {
        model: 12

        Item {
            required property int index
            readonly property bool cheia: index % 3 === 0

            anchors.centerIn: parent
            width: 0
            height: 0
            rotation: index * 30

            Rectangle {
                width: (cheia ? 2.2 : 1.2) * relogio.unidade
                height: (cheia ? 9 : 5) * relogio.unidade
                radius: width / 2
                x: -width / 2
                y: -(relogio.width / 2 - 11 * relogio.unidade)
                color: Theme.textoSuave
                opacity: cheia ? 0.75 : 0.4
            }
        }
    }

    // -------------------------------------------------------------- ponteiros
    //
    // Cada ponteiro é um retângulo cuja base cai no centro do mostrador, com o
    // giro pivotando nessa base. Sem `transformOrigin: Item.Bottom` o ponteiro
    // giraria em torno do próprio meio e descreveria um círculo em vez de
    // apontar.

    Rectangle {
        id: ponteiroHora
        width: 3.4 * relogio.unidade
        height: relogio.width * 0.27
        radius: width / 2
        x: (relogio.width - width) / 2
        y: relogio.height / 2 - height
        transformOrigin: Item.Bottom
        rotation: relogio.anguloHora
        color: Theme.texto
        opacity: 0.8
    }

    Rectangle {
        id: ponteiroMinuto
        width: 2.2 * relogio.unidade
        height: relogio.width * 0.39
        radius: width / 2
        x: (relogio.width - width) / 2
        y: relogio.height / 2 - height
        transformOrigin: Item.Bottom
        rotation: relogio.anguloMinuto
        color: Theme.texto
        opacity: 0.65
    }

    // Miolo: o único ponto de cor do relógio.
    Rectangle {
        anchors.centerIn: parent
        width: 6 * relogio.unidade
        height: width
        radius: width / 2
        color: Theme.ambar
        opacity: 0.8
    }
}
