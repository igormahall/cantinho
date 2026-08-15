pragma Singleton
import QtQuick

// Único arquivo do projeto com cor escrita à mão. Qualquer hex fora daqui é bug.
//
// As cores são propriedades ligadas a `noite`, não constantes: quando o tema
// vira, o Behavior anima a mudança em vez de cortar seco.
QtObject {
    id: tema

    // Quem manda aqui é o backend. Main.qml amarra os dois no startup.
    property bool noite: true

    // O quarto respira ou fica quieto.
    //
    // Cinco coisas se mexem sozinhas para sempre: a luz do abajur, as folhas,
    // a chuva, a poeira e o grão. São o ambiente, e é por isso que existem —
    // mas ambiente que nunca para custa duas coisas que só aparecem depois de
    // horas: bateria, porque o grão repinta a janela a cada 900 ms mesmo com
    // ninguém olhando; e sossego, para quem não quer movimento na visão
    // periférica enquanto lê outra coisa.
    //
    // Isto **não** desliga a reação ao mouse: `reacao` continua valendo. Um
    // botão que não responde ao toque não é um quarto quieto, é um app
    // quebrado. O que para é o que se mexe sem ninguém pedir.
    property bool movimento: true

    // Crossfade de cenário e de painel andam juntos, no mesmo tempo. Com o
    // quarto quieto a troca de tema é imediata: são três segundos de gradiente
    // atravessando a tela inteira, exatamente o que alguém que pediu sossego
    // não quer ver.
    readonly property int transicao: movimento ? 3000 : 0

    property color fundo:      noite ? "#221D1A" : "#F2E8DA"
    property color superficie: noite ? "#2E2723" : "#FBF4E9"
    property color borda:      noite ? "#3D342E" : "#DCCBB6"
    property color texto:      noite ? "#EDE0D0" : "#3A3129"
    property color textoSuave: noite ? "#A9968A" : "#7C6B5C"
    property color ambar:      noite ? "#E0A458" : "#C77D2E"
    property color musgo:      noite ? "#7A8B6F" : "#6E7F62"
    property color terracota:  noite ? "#C4704F" : "#B05F3F"

    readonly property int raio: 10
    readonly property int espaco: 14
    readonly property int espacoGrande: 22

    // ------------------------------------------------------------ tipografia
    //
    // As duas famílias são asset, como os SVGs e os WAVs — não são dependência
    // nova, e o `FontLoader` é do próprio Qt.
    //
    // **Antes disto o projeto não definia fonte em lugar nenhum.** O app usava
    // o padrão do sistema, o que quer dizer Segoe UI no Windows e Cantarell ou
    // DejaVu no Ubuntu — e as duas máquinas são os dois contextos de uso deste
    // projeto. Ou seja: era outro programa em cada uma, com outro desenho de
    // letra, outra métrica e outras larguras de botão. Um repositório que fixa
    // cor em hex num arquivo só e proíbe hardcode em qualquer outro estava
    // deixando metade do que se vê na tela por conta do sistema operacional.
    //
    // São duas porque têm papéis diferentes, e é essa divisão que faz o efeito:
    //
    //   `fonte`  — Inter. A interface: painéis, barra, botões, campos. Sans
    //              humanista de contraste baixo, que acompanha a ilustração sem
    //              disputar com ela.
    //   `fontePapel` — EB Garamond. As superfícies de papel do quarto: o
    //              bilhete e o calendário. É o que faz o bilhete parecer papel
    //              pregado na parede em vez de um retângulo com texto.
    //
    // Ambas SIL OFL 1.1 — a licença vai junto em `assets/fonts/`.
    readonly property FontLoader _interLoader: FontLoader {
        source: "../../../assets/fonts/Inter.ttf"
    }
    readonly property FontLoader _papelLoader: FontLoader {
        source: "../../../assets/fonts/EBGaramond.ttf"
    }

    // O nome da família, com recuo para a fonte do sistema se o arquivo faltar
    // — num build mal empacotado, texto que some é pior que texto na fonte
    // errada.
    readonly property string fonte: _interLoader.status === FontLoader.Ready
                                    ? _interLoader.name : "sans-serif"
    readonly property string fontePapel: _papelLoader.status === FontLoader.Ready
                                         ? _papelLoader.name : "serif"

    // Algarismos de largura fixa, para o cronômetro.
    //
    // O `tnum` da Inter, e ele é obrigatório aqui: por padrão os algarismos dela
    // são proporcionais — o "1" tem 6,95 px onde o "0" tem 9,6 —, então
    // `00:00` e `11:11` têm larguras diferentes e o relógio **treme a cada
    // segundo**. Com `tnum` os dez algarismos ficam com a mesma largura e as
    // duas cadeias medem igual. Medido.
    readonly property var digitos: ({ "tnum": 1 })

    // A escala de tamanhos, pela mesma regra das cores e dos tempos: número de
    // corpo escrito à mão fora daqui é bug.
    //
    // Havia 9, 10, 11, 13, 15, 16, 18 e 30 espalhados, com o 11 sozinho em oito
    // lugares — a mesma doença que os quatro eixos de tempo curaram nas
    // durações, cada valor escolhido no dia em que aquela tela foi escrita. São
    // cinco degraus agora, em razão aproximada de 1,25, que é o que dá
    // hierarquia visível sem parecer salto.
    //
    // Os corpos dos objetos de parede (bilhete, calendário) **não** vêm daqui:
    // eles escalam com o desenho, por `unidade`, porque são parte da
    // ilustração e não da interface.
    readonly property int nano: 11      // legenda, data, metadado
    readonly property int miudo: 13     // texto secundário
    readonly property int corpo: 15     // texto normal
    readonly property int titulo: 19    // título de painel
    readonly property int destaque: 30  // o cronômetro, e só ele

    // Painel translúcido: o quarto continua aparecendo por trás.
    //
    // Três níveis, e a diferença entre eles é quanto texto cada superfície
    // carrega. A gaveta tem listas para ler e precisa de fundo. A barra é uma
    // fileira de botões: opaca, ela vira um rodapé de aplicativo e corta o
    // chão do quarto em dois. A mini é um objeto na mesa de outra pessoa, e
    // quanto menos ela parecer janela, melhor.
    readonly property real opacidadePainel: 0.93
    readonly property real opacidadeBarra: 0.62
    readonly property real opacidadeMini: 0.55

    // Papel pregado na parede: calendário, relógio e bilhete. Bem baixa — é
    // decoração do cômodo, não widget por cima dele.
    readonly property real opacidadeParede: 0.16

    // Os quatro tempos do app, e a mesma regra das cores vale para eles: número
    // de duração escrito à mão fora daqui é bug.
    //
    // Espalhados pelos arquivos havia 150, 160, 180, 200, 220, 240, 260 e 300 —
    // oito valores para três intenções, cada um escolhido no dia em que aquela
    // animação foi escrita. Ninguém percebe a diferença entre 150 e 160 numa
    // tela; percebe, sim, quando dois painéis irmãos abrem em ritmos que não
    // combinam.
    //
    //   reacao   — o mouse tocou em algo. Resposta, não animação.
    //   gesto    — o usuário pediu: painel abrindo, foco mudando, escolha feita.
    //   chegada  — algo entrou no quarto. O objeto na estante, a ideia no mural.
    //   transicao — o cômodo inteiro mudando de hora.
    //
    // Os dois do meio não obedecem a `movimento`, e é de propósito: são
    // consequência de um gesto, como a reação ao mouse. O que o quarto quieto
    // desliga é o que se mexe sozinho.
    readonly property int reacao: 140
    readonly property int gesto: 200
    readonly property int chegada: 460

    Behavior on fundo      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on superficie { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on borda      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on texto      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on textoSuave { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on ambar      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on musgo      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on terracota  { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
}
