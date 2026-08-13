import QtQuick
import theme

// Botão sem moldura pesada: só texto que reage ao passar o mouse.
//
// A reação tem três camadas que entram juntas: o fundo acende, o rótulo muda de
// cor e o conjunto cresce um fio. Nenhuma delas sozinha se nota; as três juntas
// dão a impressão de que o botão percebeu o mouse.
//
// Os números são pequenos de propósito. 4% de escala é o limite entre "isso
// respondeu" e "isso pulou": passando disso, uma fileira de botões vira um
// teclado de piano quando o mouse atravessa a barra.
Item {
    id: botao

    property alias text: rotulo.text
    property color cor: Theme.textoSuave
    property color corAtiva: Theme.ambar
    property bool destacado: false
    property int tamanho: Theme.miudo

    // Entra e sai em vez de piscar.
    //
    // `visible: false` num botão de barra é troca seca no controle mais usado
    // do app: a cada sessão que começa, dois botões apareciam do nada e
    // empurravam os vizinhos de lado. A fileira de ações do backlog já fazia
    // certo, com opacidade; a barra não fazia.
    //
    // A largura anda junto com a opacidade, senão o buraco continua lá quando
    // o botão some — e é a largura que faz o gesto ler como "o botão chegou"
    // em vez de "algo apareceu por cima".
    property bool mostrando: true

    signal clicked()

    implicitWidth: rotulo.implicitWidth + 20
    implicitHeight: rotulo.implicitHeight + 12

    width: mostrando ? implicitWidth : 0
    opacity: mostrando ? 1 : 0
    // Some da conta do Row quando fecha de vez, senão sobra o espaçamento.
    visible: width > 0.5
    clip: width < implicitWidth

    Behavior on width {
        NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
    }
    Behavior on opacity {
        NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
    }

    // Cresce a partir do meio, senão o botão anda para o lado ao ser apontado.
    transformOrigin: Item.Center
    scale: area.pressed ? 0.96 : (area.containsMouse ? 1.04 : 1.0)

    // Curvas diferentes na ida e na volta: entra com um respiro (OutBack dá o
    // leve exagero no fim), sai reto. Reação carinhosa é assimétrica.
    Behavior on scale {
        NumberAnimation {
            duration: Theme.reacao
            easing.type: area.containsMouse ? Easing.OutBack : Easing.OutCubic
            easing.overshoot: 1.6
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.raio
        color: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b,
                       area.pressed ? 0.20 : (area.containsMouse ? 0.10 : 0.0))
        Behavior on color { ColorAnimation { duration: Theme.reacao } }
    }

    Text {
        id: rotulo
        anchors.centerIn: parent
        font.pixelSize: botao.tamanho
        color: (botao.destacado || area.containsMouse) ? botao.corAtiva : botao.cor
        Behavior on color { ColorAnimation { duration: Theme.reacao } }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: backend.sfx("toque")
        onClicked: {
            backend.sfx("clique")
            botao.clicked()
        }
    }
}
