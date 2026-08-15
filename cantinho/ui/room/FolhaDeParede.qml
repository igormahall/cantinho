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

    // A escrita sobe junto com o papel.
    //
    // Por muito tempo só o fundo e a borda reagiam ao mouse, e os textos de
    // dentro tinham opacidade fixa: o papel acendia e o que estava escrito nele
    // continuava igual, o que entrega metade do ganho de leitura. À noite é onde
    // mais falta — a parede é escura, a vinheta puxa os cantos para baixo, e
    // estes são os objetos do cenário que **carregam informação**: a lista do
    // dia com o tempo de cada tarefa, e os números do mês.
    //
    // Em repouso nada muda, que é a regra dos objetos de parede: eles são
    // decoração do cômodo até alguém se aproximar. Quem chega com o mouse chegou
    // para ler.
    //
    // Quem escreve na folha chama isto em vez de pôr número solto em `opacity`.
    // O teto é 1: base alta somada ao realce estouraria, e opacidade acima de 1
    // não dá erro no Qt — só desperdiça o realce em silêncio, justamente nas
    // linhas que já estavam legíveis.
    function lido(base) {
        return Math.min(1, base + 0.22 * folha.destaque)
    }

    property bool prego: true

    // Sem inclinação, de propósito.
    //
    // A primeira versão pendurava tudo torto, um grau e pouco cada, pela ideia
    // de papel preso por um prego só. Na tela não leu como espontâneo: leu como
    // desalinhado — três retângulos de texto fora de esquadro num quarto onde
    // todo o resto é reto. O prego continua, a inclinação não: o cantinho é
    // organizado, não bagunçado.

    color: Qt.rgba(Theme.superficie.r, Theme.superficie.g, Theme.superficie.b,
                   Theme.opacidadeParede + 0.20 * destaque)
    radius: 3 * unidade
    border.width: 1
    border.color: Qt.rgba(Theme.borda.r, Theme.borda.g, Theme.borda.b,
                          0.40 + 0.45 * destaque)

    // Papel de parede responde ao mouse como qualquer controle responde: é a
    // mesma pergunta ("isto reage?") feita a um objeto do cenário.
    Behavior on destaque {
        NumberAnimation { duration: Theme.reacao; easing.type: Easing.OutCubic }
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
