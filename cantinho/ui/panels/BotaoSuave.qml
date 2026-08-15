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

    // Navegável pelo teclado.
    //
    // O app tinha bons atalhos — Espaço começa e para, Escape fecha em cascata,
    // Ctrl+Shift+I captura — e nenhum jeito de andar entre os controles sem o
    // mouse: só o campo de texto aceitava foco, e nada na tela mostrava onde o
    // foco estava. Tab agora percorre os botões, e o anel diz qual deles o
    // Enter vai acionar.
    //
    // `activeFocusOnTab` só nos que estão à mostra: um botão de largura zero na
    // fila do Tab é um passo em que a atenção some da tela.
    activeFocusOnTab: mostrando && enabled
    Keys.onReturnPressed: botao.aciona()
    Keys.onEnterPressed: botao.aciona()
    Keys.onSpacePressed: botao.aciona()

    // E anunciável por leitor de tela.
    //
    // Vai aqui e não em cada chamada porque assim os quase quarenta botões do
    // app são cobertos de uma vez, e um botão novo nasce coberto — a mesma razão
    // pela qual a fonte padrão é definida em `services/fonts.py` em vez de em
    // cada `Text`.
    //
    // Sem isto o Narrator e o Orca leem "painel, painel, painel" ao andar pela
    // barra: o `Item` do QML não tem papel nem nome, e o texto do rótulo está
    // num filho que a árvore de acessibilidade não associa a nada. O `onPress`
    // deixa o leitor acionar o botão pelo caminho dele em vez de simular tecla.
    //
    // É um app de um usuário só, e por isso isto é barato e não urgente — mas o
    // anel de foco e a fila do Tab já existem, e teclado sem nome é meio
    // caminho: quem navega sem ver a tela chega no botão e não sabe qual é.
    Accessible.role: Accessible.Button
    Accessible.name: rotulo.text
    Accessible.onPressAction: botao.aciona()

    function aciona() {
        backend.sfx("clique")
        botao.clicked()
    }

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
    // O teclado recebe a mesma reação do mouse: quem chega pelo Tab vê o botão
    // responder do mesmo jeito que quem chega apontando.
    scale: area.pressed ? 0.96
           : ((area.containsMouse || activeFocus) ? 1.04 : 1.0)

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
                       area.pressed ? 0.20
                       : ((area.containsMouse || botao.activeFocus) ? 0.10 : 0.0))
        Behavior on color { ColorAnimation { duration: Theme.reacao } }

        // O anel do foco. Fino, âmbar e por fora do fundo aceso — é a mesma
        // cor que o campo de texto já usa para dizer "a digitação vai para
        // aqui", e usar outra faria o app ter duas linguagens de foco.
        border.width: botao.activeFocus ? 1 : 0
        border.color: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b,
                              botao.activeFocus ? 0.75 : 0)
        Behavior on border.color { ColorAnimation { duration: Theme.reacao } }
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
            // O clique também dá o foco, senão Tab depois de clicar recomeça do
            // início da tela em vez de seguir de onde a mão estava.
            botao.forceActiveFocus()
            botao.aciona()
        }
    }
}
