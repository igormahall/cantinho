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

    readonly property int corpo: 15
    readonly property int miudo: 13
    readonly property int titulo: 18

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
