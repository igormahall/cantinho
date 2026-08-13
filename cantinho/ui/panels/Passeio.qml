import QtQuick
import theme

// O passeio da primeira abertura.
//
// Nada neste app se anuncia: não há barra de menu, não há rótulo dizendo o que
// ele é, e a coisa mais importante da tela — a estante — parece decoração até
// alguém contar que não é. Quem abre pela primeira vez vê um quarto bonito e
// não sabe onde clicar.
//
// Quem conta é a planta, e ela é a mesma figura do ícone do app: quem aprende
// o cantinho por este rosto reconhece o programa na barra de tarefas depois.
//
// O passeio não ensina a interface botão por botão. Ele conta o ciclo, que é
// a única coisa que precisa ser entendida uma vez: escrever, começar,
// entregar, e o quarto guardar aquilo. O resto se descobre clicando.
Item {
    id: passeio

    // Onde cada balão fica. São regiões da janela, não coordenadas: a cena usa
    // `PreserveAspectFit` e o quarto se desloca quando a janela muda de forma,
    // então prender o balão a um pixel exato o descolaria do que ele aponta.
    readonly property var passos: [
        {
            "onde": "centro",
            "titulo": "oi. este é o seu cantinho.",
            "texto": "Um quarto que guarda o que você faz durante o dia. "
                     + "Levo meio minuto para mostrar como ele funciona."
        },
        {
            "onde": "barra",
            "titulo": "primeiro, escreva o que quer fazer",
            "texto": "O botão “hoje” abre a sua lista. Cabem cinco coisas por "
                     + "vez, e o limite é de propósito: lista que aceita tudo "
                     + "deixa de ser a lista de hoje."
        },
        {
            "onde": "barra",
            "titulo": "depois, aperte começar",
            "texto": "O relógio corre enquanto você trabalha. Não tem meta, "
                     + "não tem barra enchendo e ninguém está contando pontos "
                     + "— ele só marca o tempo que passou."
        },
        {
            "onde": "estante",
            "titulo": "terminou? “entreguei”",
            "texto": "Cada coisa que você termina vira um objeto nesta "
                     + "estante. Eles não somem nunca. É aqui que dá para ver "
                     + "o que você fez sem precisar de nenhum número."
        },
        {
            "onde": "vaso",
            "titulo": "a planta cresce com o seu tempo",
            "texto": "Ela olha as últimas duas semanas. Se você sumir uns "
                     + "dias ela encolhe devagar, e volta rápido quando você "
                     + "voltar. Falhar aqui não quebra nada."
        },
        {
            "onde": "parede",
            "titulo": "o papel e o calendário",
            "texto": "O papel na parede é a sua lista de hoje, com o tempo de "
                     + "cada coisa. O calendário do outro lado abre a semana. "
                     + "Os dois respondem a clique."
        },
        {
            "onde": "barra",
            "titulo": "e “o quarto” é seu",
            "texto": "Luz, som, movimento e a saída ficam ali. Este passeio "
                     + "também — se quiser rever, é por lá. Bom trabalho."
        }
    ]

    property int passo: 0
    readonly property var atual: passos[Math.min(passo, passos.length - 1)]
    readonly property bool ultimo: passo >= passos.length - 1

    signal fechar()

    function avancar() {
        if (ultimo)
            passeio.fechar()
        else
            passo += 1
    }

    function recomecar() { passo = 0 }

    // Enquanto o passeio corre, o quarto não recebe clique.
    //
    // Não é para prender ninguém — "pular" está sempre à vista, na mesma
    // altura do olho. É que o passeio aponta para botões, e um clique que
    // abrisse a gaveta por cima do balão faria a explicação sumir no meio da
    // frase, justamente para quem ainda não sabe como voltar.
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onClicked: passeio.avancar()
    }

    // O balão. Sai da posição anterior e entra na nova em vez de saltar: o
    // olho acompanha o movimento e chega junto no que está sendo apontado.
    Painel {
        id: balao

        readonly property string onde: passeio.atual.onde
        readonly property int margem: 28

        width: Math.min(360, passeio.width - 2 * margem)
        height: conteudo.height + 2 * Theme.espacoGrande

        // O balão fica **ao lado** do que explica, nunca por cima.
        //
        // A primeira versão punha o balão da estante encostado na borda
        // esquerda, que é exatamente onde a estante está: a frase dizia "esta
        // estante" tapando a estante inteira. O mesmo valia para o vaso, do
        // outro lado.
        //
        // Sem seta apontando, a proximidade é a única pista que sobra — então
        // ela precisa estar certa. As frações vêm do desenho da cena: a
        // estante ocupa a faixa esquerda até uns 25% da largura, o vaso e os
        // papéis a faixa direita a partir de uns 76%, e a barra é a tira de
        // baixo. O balão mora no meio que sobra.
        x: {
            switch (onde) {
            case "estante": return passeio.width * 0.28
            case "vaso":
            case "parede":  return Math.max(margem, passeio.width * 0.74 - width)
            default:        return (passeio.width - width) / 2
            }
        }
        y: {
            switch (onde) {
            case "parede":  return passeio.height * 0.22
            case "estante":
            case "vaso":    return passeio.height * 0.40
            case "barra":   return passeio.height - height - 104
            default:        return (passeio.height - height) / 2
            }
        }

        Behavior on x { NumberAnimation { duration: Theme.chegada; easing.type: Easing.InOutCubic } }
        Behavior on y { NumberAnimation { duration: Theme.chegada; easing.type: Easing.InOutCubic } }

        Item {
            id: conteudo
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            height: Math.max(retrato.height, coluna.height) + rodape.height + Theme.espaco

            // A planta, olhando de frente. Mesmo desenho do ícone do app.
            Image {
                id: retrato
                width: 56
                height: 56
                anchors.left: parent.left
                anchors.top: parent.top
                source: "image://cena/avatar/" + backend.tourAvatarStage
                sourceSize.width: 112
                sourceSize.height: 112
                asynchronous: true
                smooth: true
            }

            Column {
                id: coluna
                anchors.left: retrato.right
                anchors.leftMargin: Theme.espaco
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: 6

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: passeio.atual.titulo
                    color: Theme.texto
                    font.pixelSize: Theme.titulo
                }

                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.35
                    text: passeio.atual.texto
                    color: Theme.textoSuave
                    font.pixelSize: Theme.corpo
                }
            }

            Item {
                id: rodape
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 30

                // Onde se está, sem número: sete pontos, um aceso. Um "3 de 7"
                // seria a única barra de progresso do app, e ela apareceria
                // justamente na tela que promete que não existe nenhuma.
                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 2
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5

                    Repeater {
                        model: passeio.passos.length

                        delegate: Rectangle {
                            width: 5; height: 5; radius: 3
                            anchors.verticalCenter: parent.verticalCenter
                            color: index === passeio.passo ? Theme.ambar : Theme.textoSuave
                            opacity: index === passeio.passo ? 1 : 0.35
                            Behavior on color { ColorAnimation { duration: Theme.gesto } }
                            Behavior on opacity { NumberAnimation { duration: Theme.gesto } }
                        }
                    }
                }

                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    // Sempre à vista, inclusive no último passo: quem quer sair
                    // não devia ter que chegar ao fim para conseguir.
                    BotaoSuave {
                        text: "pular"
                        mostrando: !passeio.ultimo
                        onClicked: passeio.fechar()
                    }

                    BotaoSuave {
                        text: passeio.ultimo ? "entendi" : "próximo"
                        destacado: true
                        corAtiva: Theme.ambar
                        tamanho: Theme.corpo
                        onClicked: passeio.avancar()
                    }
                }
            }
        }
    }
}
