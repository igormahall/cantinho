pragma Singleton
import QtQuick

// Único arquivo do projeto com cor escrita à mão. Qualquer hex fora daqui é bug.
//
// As cores são propriedades ligadas a `noite`, não constantes: quando o tema
// vira, o Behavior anima a mudança em vez de cortar seco.
QtObject {
    id: tema

    // Quem manda aqui é o backend. Main.qml amarra isto no startup.
    property bool noite: true

    // Crossfade de cenário e de painel andam juntos, no mesmo tempo.
    readonly property int transicao: 3000

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

    // Reação ao mouse. Curta o bastante para parecer resposta e não animação.
    readonly property int reacao: 140

    Behavior on fundo      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on superficie { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on borda      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on texto      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on textoSuave { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on ambar      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on musgo      { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
    Behavior on terracota  { ColorAnimation { duration: tema.transicao; easing.type: Easing.InOutQuad } }
}
