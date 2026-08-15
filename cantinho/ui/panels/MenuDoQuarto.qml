import QtQuick
import theme

// O menu do quarto: luz, som, movimento, humor/energia, a página e a saída.
//
// Não é gosto por menu. Com "entreguei" na barra, a fileira de botões passava da
// largura da janela — e o que está aqui dentro são ajustes do ambiente e coisas
// que se fazem uma vez, não ações do dia. A barra ficou com o que se usa toda
// hora; o resto mora atrás de uma porta.
//
// `aberto` é a fonte da verdade e mora aqui, não na janela: quem fecha o menu é
// quase sempre o próprio menu — o clique fora, a linha que dispara uma ação —, e
// uma propriedade da janela amarrada por binding se romperia na primeira dessas
// atribuições, deixando os dois lados discordando em silêncio.
Item {
    id: menu

    anchors.fill: parent

    // A quem o painel se encosta por baixo: a ilha do rodapé.
    property Item rodape: null

    property bool aberto: false

    // Quem fecha o app é a janela, que tem a confirmação. Daqui sai o pedido.
    signal sair()

    MouseArea {
        anchors.fill: parent
        enabled: menu.aberto
        onClicked: menu.aberto = false
    }

    Painel {
        id: painel
        width: 268
        height: coluna.height + 2 * Theme.espacoGrande
        anchors.right: parent.right
        anchors.rightMargin: 24

        // Encostado por cima do rodapé, e por posição em vez de âncora.
        //
        // O rodapé é irmão **deste componente**, não deste painel: âncora só
        // atravessa entre pai e irmão, e `anchors.bottom: rodape.top` daqui de
        // dentro deixa o Qt reclamar em runtime e o painel parado no topo. Foi
        // o preço de embrulhar o menu num Item para trazer junto o clique de
        // fora — e como as duas coisas ficam no mesmo contentItem da janela, a
        // conta em `y` dá exatamente o mesmo lugar.
        y: (menu.rodape ? menu.rodape.y : parent.height)
           - height - (menu.aberto ? 10 : -6)

        opacity: menu.aberto ? 1 : 0
        visible: opacity > 0.01

        Behavior on y {
            NumberAnimation { duration: Theme.gesto; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: Theme.gesto } }

        Column {
            id: coluna
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.espacoGrande
            spacing: Theme.espaco

            // O humor e a energia saíram de dentro da retrospectiva para cá.
            //
            // Lá eles só apareciam depois de rolar a lista de sessões, no
            // painel chamado "fechar o dia" — ou seja, na prática só existiam
            // no fim da noite. Aqui dá para dizer como se está às três da
            // tarde, que é quando a resposta é verdadeira.
            //
            // Grava na hora, sem botão de confirmar, e preserva a nota que já
            // estiver guardada: é o mesmo `day.review` do painel do dia, e a
            // última do dia vence.
            Text {
                text: "como está o dia"
                color: Theme.textoSuave
                font.pixelSize: Theme.miudo
            }

            EscalaPontos {
                width: parent.width
                rotulo: "humor"
                valor: backend.todayReview ? backend.todayReview.mood : 3
                onEscolhido: function (v) {
                    backend.saveReview(
                        v,
                        backend.todayReview ? backend.todayReview.energy : 3,
                        backend.todayReview ? backend.todayReview.note : "")
                }
            }

            EscalaPontos {
                width: parent.width
                rotulo: "energia"
                valor: backend.todayReview ? backend.todayReview.energy : 3
                onEscolhido: function (v) {
                    backend.saveReview(
                        backend.todayReview ? backend.todayReview.mood : 3,
                        v,
                        backend.todayReview ? backend.todayReview.note : "")
                }
            }

            Rectangle {
                width: parent.width; height: 1; color: Theme.borda
            }

            // "dia" e não "fim de tarde".
            //
            // A paleta clara foi desenhada pensando em luz baixa de fim de
            // tarde, e o nome vazou do desenho para a tela. Só que quem abre o
            // app às sete da manhã lê "fim de tarde" e o app está errado sobre
            // o próprio momento do dia. O id interno continua `tarde`, que é o
            // nome dos arquivos de cena e de áudio.
            LinhaMenu {
                width: parent.width
                rotulo: "luz"
                valor: backend.themeMode === "auto" ? "pelo seu dia"
                       : backend.themeMode === "noite" ? "noite" : "dia"
                onClicado: backend.cycleThemeMode()
            }

            // Três estados, um botão. "Sussurro" é o do meio: o quarto cala a
            // chuva e o acorde, mas o clique continua respondendo — para quem
            // está numa chamada e não quer perder o retorno da interface.
            LinhaMenu {
                width: parent.width
                rotulo: "som"
                valor: backend.soundMode === "tudo" ? "ambiente e toques"
                       : backend.soundMode === "sussurro" ? "só os toques"
                       : "nenhum"
                onClicado: backend.cycleSoundMode()
            }

            // O irmão do som, e pelo mesmo motivo.
            //
            // Cinco coisas se mexem sozinhas aqui dentro para sempre. São o
            // ambiente, e ao mesmo tempo a única coisa do app que gasta
            // máquina sem ninguém pedir — o grão repinta a janela a cada
            // 900 ms a tarde inteira. Quem precisa de sossego na visão
            // periférica, ou de bateria, desliga aqui. A reação ao mouse
            // continua: o quarto fica quieto, não morto.
            LinhaMenu {
                width: parent.width
                rotulo: "movimento"
                valor: backend.motionOn ? "o quarto respira" : "o quarto quieto"
                onClicado: backend.toggleMotion()
            }

            Rectangle {
                width: parent.width; height: 1; color: Theme.borda
            }

            // O passeio da primeira abertura não some para sempre.
            //
            // Ele aparece sozinho enquanto o log está vazio, e some assim que
            // a primeira coisa é escrita — o que é certo, mas deixaria quem
            // dispensou cedo demais sem caminho de volta. Aqui está o caminho.
            LinhaMenu {
                width: parent.width
                rotulo: "o passeio"
                valor: "ver de novo"
                onClicado: {
                    menu.aberto = false
                    backend.startTour()
                }
            }

            // Levar o quarto embora.
            //
            // Um log de anos sem saída é um refém: o banco é SQLite e o esquema
            // é simples, mas "abra o sqlite3 e escreva um SELECT" não é uma
            // saída, é a ausência de uma. Aqui a estante, o diário e o mural
            // viram uma página de texto que se lê sem o Cantinho instalado.
            //
            // Fica ao lado do passeio e não perto de "sair" de propósito: não é
            // um gesto de despedida. É a mesma natureza do passeio — as duas
            // linhas que falam sobre o app em vez de ajustarem o ambiente.
            LinhaMenu {
                width: parent.width
                rotulo: "a página"
                valor: "guardar uma cópia"
                onClicado: {
                    menu.aberto = false
                    backend.exportEverything()
                }
            }

            Rectangle {
                width: parent.width; height: 1; color: Theme.borda
            }

            LinhaMenu {
                width: parent.width
                rotulo: "sair"
                valor: "fechar o cantinho"
                cor: Theme.terracota
                onClicado: {
                    menu.aberto = false
                    menu.sair()
                }
            }
        }
    }
}
