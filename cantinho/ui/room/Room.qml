import QtQuick
import QtQuick.Particles
import QtQuick.Shapes
import theme

// O quarto. Empilha camadas do mesmo tamanho, todas vindas do provedor de
// imagem em `services/scene.py`, que já entrega cada elemento na posição certa
// do viewBox. Nenhuma conta de posição acontece aqui.
Item {
    id: quarto

    property int plantStage: 0
    property var shelf: []

    // Coordenadas do viewBox dos SVGs. Serve para posicionar os efeitos por
    // cima do desenho quando a janela não está em 1:1.
    readonly property real escala: Math.min(width / 1100, height / 700)
    function px(v) { return v * escala }

    // --------------------------------------------------------- cenário fixo

    Image {
        anchors.fill: parent
        source: "image://cena/estatico/tarde"
        sourceSize.width: Math.round(quarto.width)
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        smooth: true
    }

    Image {
        anchors.fill: parent
        source: "image://cena/estatico/noite"
        sourceSize.width: Math.round(quarto.width)
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        smooth: true
        opacity: Theme.noite ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.transicao; easing.type: Easing.InOutQuad } }
    }

    // ------------------------------------------------------------- estante

    Image {
        anchors.fill: parent
        source: "image://cena/estante/tarde/" + quarto.shelf.join(",")
        sourceSize.width: Math.round(quarto.width)
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        smooth: true
        visible: quarto.shelf.length > 0
    }

    Image {
        anchors.fill: parent
        source: "image://cena/estante/noite/" + quarto.shelf.join(",")
        sourceSize.width: Math.round(quarto.width)
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        smooth: true
        visible: quarto.shelf.length > 0
        opacity: Theme.noite ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.transicao; easing.type: Easing.InOutQuad } }
    }

    // -------------------------------------------------------------- planta
    //
    // Troca de estágio nunca é corte seco: a folhagem nova entra por cima da
    // antiga com um fade longo. Crescer devagar é o ponto.

    Image {
        id: planta
        anchors.fill: parent
        source: "image://cena/planta/" + quarto.plantStage
        sourceSize.width: Math.round(quarto.width)
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        smooth: true

        // Folhas balançando: ±1,5°, em torno do próprio vaso.
        transform: Rotation {
            origin.x: quarto.px(944)
            origin.y: quarto.px(560)
            angle: 0
            RotationAnimation on angle {
                running: true
                loops: Animation.Infinite
                from: -1.5
                to: 1.5
                duration: 5200
                easing.type: Easing.InOutSine
                onStopped: {}
            }
        }

        Behavior on source {
            SequentialAnimation {
                NumberAnimation { target: planta; property: "opacity"; to: 0; duration: 700 }
                PropertyAction {}
                NumberAnimation { target: planta; property: "opacity"; to: 1; duration: 1400 }
            }
        }
    }

    // ------------------------------------------------------- luz do abajur
    //
    // Só no tema noite, quando o abajur está aceso. O raio respira ±3% num
    // ciclo de uns seis segundos.

    Shape {
        id: luz
        anchors.fill: parent
        opacity: Theme.noite ? 0.5 : 0
        visible: opacity > 0.01
        preferredRendererType: Shape.CurveRenderer
        Behavior on opacity { NumberAnimation { duration: Theme.transicao } }

        property real raio: quarto.px(230)
        SequentialAnimation on raio {
            running: true
            loops: Animation.Infinite
            NumberAnimation { to: quarto.px(237); duration: 3100; easing.type: Easing.InOutSine }
            NumberAnimation { to: quarto.px(223); duration: 3100; easing.type: Easing.InOutSine }
        }

        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: quarto.px(334); centerY: quarto.px(392)
                focalX: centerX; focalY: centerY
                centerRadius: luz.raio
                GradientStop { position: 0.0; color: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.30) }
                GradientStop { position: 0.45; color: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.12) }
                GradientStop { position: 1.0; color: Qt.rgba(Theme.ambar.r, Theme.ambar.g, Theme.ambar.b, 0.0) }
            }
            PathRectangle { x: 0; y: 0; width: quarto.width; height: quarto.height }
        }
    }

    // ----------------------------------------------------- chuva na janela
    //
    // Recortada na moldura da janela. Partículas são Rectangle e não imagem:
    // o projeto não versiona textura de partícula.

    // Recortada no vidro, não na moldura: chuva escorrendo pela cortina seria
    // chuva dentro do quarto.
    Item {
        id: janela
        x: quarto.px(424); y: quarto.px(94)
        width: quarto.px(252); height: quarto.px(212)
        clip: true
        opacity: Theme.noite ? 1 : 0
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.transicao } }

        ParticleSystem {
            id: sistemaChuva
            running: janela.visible
        }

        Emitter {
            system: sistemaChuva
            anchors.top: parent.top
            width: parent.width
            height: 1
            emitRate: 34
            lifeSpan: 2600
            size: 1
            velocity: PointDirection { x: 14; xVariation: 6; y: 260; yVariation: 60 }
        }

        ItemParticle {
            system: sistemaChuva
            delegate: Rectangle {
                width: 1.4
                height: 11
                radius: 1
                color: Theme.textoSuave
                opacity: 0.35
            }
        }
    }

    // ------------------------------------------------- poeira no feixe (dia)

    // No feixe que entra pela janela, alargando conforme desce até o chão.
    Item {
        id: feixe
        x: quarto.px(400); y: quarto.px(94)
        width: quarto.px(330); height: quarto.px(400)
        clip: true
        opacity: Theme.noite ? 0 : 1
        visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: Theme.transicao } }

        ParticleSystem {
            id: sistemaPoeira
            running: feixe.visible
        }

        Emitter {
            system: sistemaPoeira
            anchors.fill: parent
            emitRate: 3
            lifeSpan: 14000
            size: 1
            // Deriva quase nula: a poeira flutua, não cai.
            velocity: PointDirection { x: 3; xVariation: 5; y: 2; yVariation: 5 }
        }

        ItemParticle {
            system: sistemaPoeira
            delegate: Rectangle {
                width: 2; height: 2; radius: 1
                color: Theme.ambar
                opacity: 0.30
            }
        }
    }

    // ---------------------------------------------------------------- grão
    //
    // Ruído ladrilhado por cima de tudo. O seed troca devagar para o grão não
    // ficar congelado na tela.

    Image {
        id: grao
        anchors.fill: parent
        source: "image://cena/grao/1"
        fillMode: Image.Tile
        opacity: 0.04
        smooth: false

        property int seed: 1
        Timer {
            interval: 900
            running: true
            repeat: true
            onTriggered: {
                grao.seed = grao.seed % 6 + 1
                grao.source = "image://cena/grao/" + grao.seed
            }
        }
    }
}
