"""Renderização das camadas do cenário.

Os dois SVGs de cena têm `<g>` de primeiro nível com ids idênticos. É isso que
permite montar o quarto camada por camada em vez de estampar o arquivo inteiro:
a planta e os objetos da estante precisam mudar sem que o resto mude junto.

Tudo aqui devolve imagens do tamanho da cena inteira, com cada elemento no lugar
que ele ocupa no SVG. Assim o QML só empilha `Image` de mesmo tamanho, sem
nenhuma conta de posição do lado da UI.
"""

from __future__ import annotations

import logging
import math
import threading
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)

# viewBox dos dois arquivos de cena.
SCENE_WIDTH = 1100
SCENE_HEIGHT = 700

# Camadas que não dependem de nenhum evento. Vão numa imagem só, e a troca de
# tema é um crossfade entre as duas versões dessa imagem.
STATIC_LAYERS: tuple[str, ...] = (
    "parede",
    "janela",
    "chao",
    "estante",
    "mesa_esquerda",
    "mesa_direita",
    # Depois das duas mesas, não entre elas: o brilho do abajur cai sobre a
    # mesa da esquerda e era apagado pela da direita, que é opaca e vinha por
    # cima. Isso deixava uma borda dura exatamente em x=560.
    "abajur",
    "vaso",
)

THEMES: tuple[str, ...] = ("tarde", "noite")

# Deslocamento que leva as coordenadas de planta_N.svg para as da cena.
#
# Não é chute: a camada `planta` da cena tem exatamente as mesmas medidas da
# folhagem de planta_4.svg, então os dois arquivos foram desenhados no mesmo
# sistema. A diferença entre as origens é esta.
PLANT_OFFSET_X = 843.96
PLANT_OFFSET_Y = 335.0

PLANT_STAGES = 5

# Prateleiras: y da superfície onde os objetos apoiam, e faixa de x utilizável.
SHELF_LEDGES: tuple[float, ...] = (392.0, 478.0)
SHELF_X_MIN = 82.0
SHELF_X_MAX = 248.0
SHELF_PER_LEDGE = 6

# Quantos objetos a arte atual comporta. A projeção guarda todos para sempre;
# esta é só a lotação do desenho.
SHELF_CAPACITY = len(SHELF_LEDGES) * SHELF_PER_LEDGE


def assets_dir() -> Path:
    """Raiz de `assets/`, tanto rodando do repositório quanto empacotado."""
    import sys

    empacotado = getattr(sys, "_MEIPASS", None)
    if empacotado:
        return Path(empacotado) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def scene_path(theme: str) -> Path:
    return assets_dir() / "scenes" / f"cena_{theme}.svg"


def plant_path(stage: int) -> Path:
    stage = max(0, min(stage, PLANT_STAGES - 1))
    return assets_dir() / "plant" / f"planta_{stage}.svg"


def shelf_slots(quantidade: int) -> list[tuple[float, float]]:
    """Posições `(centro_x, base_y)` para `quantidade` objetos.

    As duas prateleiras se enchem de forma equilibrada: os três primeiros vão
    para a de cima, os três seguintes para a de baixo, e daí em diante os
    objetos se dividem entre as duas e vão se aproximando.
    """
    quantidade = max(0, min(quantidade, SHELF_CAPACITY))
    if quantidade == 0:
        return []

    if quantidade <= 3:
        por_prateleira = [quantidade, 0]
    elif quantidade <= 6:
        por_prateleira = [3, quantidade - 3]
    else:
        por_prateleira = [math.ceil(quantidade / 2), quantidade // 2]

    posicoes: list[tuple[float, float]] = []
    largura = SHELF_X_MAX - SHELF_X_MIN
    for base_y, total in zip(SHELF_LEDGES, por_prateleira):
        if total <= 0:
            continue
        passo = largura / total
        for indice in range(total):
            posicoes.append((SHELF_X_MIN + (indice + 0.5) * passo, base_y))
    return posicoes


class _RendererCache:
    """QSvgRenderer é caro de construir e os arquivos nunca mudam em runtime."""

    def __init__(self) -> None:
        self._cache: dict[Path, QSvgRenderer] = {}

    def get(self, path: Path) -> QSvgRenderer | None:
        renderer = self._cache.get(path)
        if renderer is None:
            renderer = QSvgRenderer(str(path))
            if not renderer.isValid():
                logger.error("SVG inválido: %s", path)
                return None
            self._cache[path] = renderer
        return renderer


_renderers = _RendererCache()

# Toda renderização passa por aqui, uma de cada vez.
#
# `QQuickImageProvider` do tipo Image é chamado numa thread de trabalho sempre
# que o `Image` do QML é assíncrono — e as cinco camadas do quarto são. Um
# `QSvgRenderer` não é reentrante, e as camadas compartilham o renderer do
# arquivo de cena, que fica em cache.
#
# O sintoma é traiçoeiro: no tamanho inicial dá certo, porque as imagens já
# estão em cache do QML e ninguém pede duas ao mesmo tempo. Ao redimensionar a
# janela, as cinco pedem um tamanho novo no mesmo instante, as chamadas se
# atropelam dentro do mesmo renderer e o quarto inteiro sai em branco — sem
# erro, sem aviso, só a parede vazia.
#
# Serializar custa pouco: a cena inteira rasteriza em ~10 ms.
_desenho = threading.Lock()


def _blank(size: QSize) -> QImage:
    imagem = QImage(size, QImage.Format_ARGB32_Premultiplied)
    imagem.fill(Qt.transparent)
    return imagem


def _target_size(requested: QSize) -> QSize:
    """Respeita o tamanho pedido pelo QML, preservando a proporção da cena."""
    if requested.width() > 0:
        largura = requested.width()
        return QSize(largura, round(largura * SCENE_HEIGHT / SCENE_WIDTH))
    if requested.height() > 0:
        altura = requested.height()
        return QSize(round(altura * SCENE_WIDTH / SCENE_HEIGHT), altura)
    return QSize(SCENE_WIDTH, SCENE_HEIGHT)


def _painter_for(imagem: QImage) -> QPainter:
    painter = QPainter(imagem)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    # Desenha sempre em coordenadas de viewBox; a escala para o tamanho pedido
    # é do painter, não das contas de cada elemento.
    painter.scale(imagem.width() / SCENE_WIDTH, imagem.height() / SCENE_HEIGHT)
    return painter


def render_static(theme: str, size: QSize) -> QImage:
    """Todas as camadas que não dependem de evento, numa imagem só."""
    imagem = _blank(size)
    with _desenho:
        renderer = _renderers.get(scene_path(theme))
        if renderer is None:
            return imagem
        painter = _painter_for(imagem)
        for layer in STATIC_LAYERS:
            if renderer.elementExists(layer):
                renderer.render(painter, layer, renderer.boundsOnElement(layer))
        painter.end()
    return imagem


def render_plant(stage: int, size: QSize) -> QImage:
    """Só a folhagem do estágio, posicionada sobre o vaso da cena.

    O vaso vem da cena, não do arquivo da planta: os dois desenham um vaso, e o
    da cena é o que combina com a mesa.
    """
    imagem = _blank(size)
    with _desenho:
        renderer = _renderers.get(plant_path(stage))
        if renderer is None or not renderer.elementExists("planta"):
            return imagem
        painter = _painter_for(imagem)
        bounds = renderer.boundsOnElement("planta")
        renderer.render(
            painter,
            "planta",
            QRectF(
                bounds.x() + PLANT_OFFSET_X,
                bounds.y() + PLANT_OFFSET_Y,
                bounds.width(),
                bounds.height(),
            ),
        )
        painter.end()
    return imagem


def render_shelf(theme: str, object_types: list[str], size: QSize) -> QImage:
    """Objetos da estante, na ordem em que foram conquistados.

    A arte de cada objeto vem do seu `obj_N` no SVG, mas a posição é calculada:
    o desenho traz seis objetos em seis lugares fixos, e a estante precisa
    acomodar mais que isso sem que o tipo do objeto dependa do lugar.
    """
    imagem = _blank(size)
    visiveis = object_types[:SHELF_CAPACITY]
    posicoes = shelf_slots(len(visiveis))
    with _desenho:
        renderer = _renderers.get(scene_path(theme))
        if renderer is None:
            return imagem
        painter = _painter_for(imagem)
        for object_type, (centro_x, base_y) in zip(visiveis, posicoes):
            if not renderer.elementExists(object_type):
                continue
            natural = renderer.boundsOnElement(object_type)
            renderer.render(
                painter,
                object_type,
                QRectF(
                    centro_x - natural.width() / 2,
                    base_y - natural.height(),
                    natural.width(),
                    natural.height(),
                ),
            )
        painter.end()
    return imagem


# ------------------------------------------------------------------- ícone
#
# O ícone não é arte nova: é o mesmo vaso que fica no canto do quarto, sobre um
# ladrilho quente com a luz do abajur atrás. O app inteiro é um cômodo, e o
# ícone é esse cômodo reduzido ao que cabe em 16 pixels — uma luz acesa e uma
# planta.
#
# Desenhar um relógio, um check ou uma lista seria a linguagem de produtividade
# que o projeto recusa na tela; não faz sentido colocá-la na barra de tarefas.

# Moldura fixa em coordenadas de planta_N.svg: o vaso (que não muda) unido à
# folhagem do estágio 4 (a maior). Fixa de propósito — assim o vaso fica do
# mesmo tamanho em todos os estágios e o que se vê crescendo é só a planta,
# preenchendo um quadro que não se mexe.
ICON_FRAME_X = 16.0
ICON_FRAME_Y = 25.0
ICON_FRAME_W = 160.0
ICON_FRAME_H = 236.0

# Tudo é composto neste tamanho e depois reduzido. Rasterizar SVG direto em
# 16 px sai empastado; reduzir de 256 com filtro suave sai limpo.
ICON_BASE = 256

# Abaixo deste tamanho o ladrilho sai e a planta ocupa o quadro inteiro.
#
# Não é preguiça, é o motivo de um `.ico` ter várias resoluções: cada tamanho é
# um desenho. Em 16 px o ladrilho come quase toda a área, sobra um vaso de
# quatro pixels e o ícone vira um quadrado escuro indistinguível de qualquer
# outro. Sem ladrilho, o mesmo vaso ocupa a largura toda e se enxerga tanto em
# barra escura quanto clara.
ICON_TILE_MIN = 32

# Quanto da altura o vaso e a folhagem ocupam, com e sem ladrilho.
_ICON_PLANT_HEIGHT = 0.84
_ICON_PLANT_BOTTOM = 0.07
_ICON_PLANT_HEIGHT_SOLTO = 0.96

# Sem ladrilho, a moldura começa mais embaixo. A moldura cheia é retrato
# (160x236), e encaixá-la pela altura deixa o vaso com sete pixels de largura
# num ícone de dezesseis. Cortando as pontas mais esparsas da folhagem a
# moldura fica quase quadrada e tudo cresce junto. Só o estágio 4 perde as
# pontas, que em 16 px são sub-pixel de qualquer jeito.
ICON_FRAME_Y_SOLTO = 55.0


def _desenhar_planta(
    painter: QPainter,
    stage: int,
    altura: float,
    base_y: float,
    topo: float = ICON_FRAME_Y,
) -> None:
    """Vaso e folhagem encaixados na moldura fixa.

    Os dois vêm do mesmo arquivo e são desenhados sob a mesma transformação,
    senão a folhagem descola do vaso.
    """
    moldura_h = ICON_FRAME_Y + ICON_FRAME_H - topo
    escala = altura / moldura_h
    largura = ICON_FRAME_W * escala
    destino_x = (ICON_BASE - largura) / 2
    destino_y = base_y - altura

    # A bandeja redesenha o ícone a cada evento, na thread da UI, enquanto o
    # provedor pode estar rasterizando a cena numa worker — e os dois passam
    # pelo mesmo cache de renderer.
    with _desenho:
        renderer = _renderers.get(plant_path(stage))
        if renderer is None:
            return
        painter.save()
        painter.translate(destino_x - ICON_FRAME_X * escala, destino_y - topo * escala)
        painter.scale(escala, escala)
        for elemento in ("vaso", "planta"):
            if renderer.elementExists(elemento):
                renderer.render(painter, elemento, renderer.boundsOnElement(elemento))
        painter.restore()


def render_icon(stage: int, size: int = ICON_BASE) -> QImage:
    """Ícone do app, com a planta no estágio pedido.

    Sempre nas cores da noite, independente do tema em uso: o ícone é
    identidade, não estado da tela. Um ícone que trocasse de cor ao entardecer
    viraria outro ícone na barra de tarefas.
    """
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QBrush, QLinearGradient, QPainterPath, QRadialGradient

    base = _blank(QSize(ICON_BASE, ICON_BASE))
    painter = QPainter(base)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    if size < ICON_TILE_MIN:
        _desenhar_planta(
            painter,
            stage,
            ICON_BASE * _ICON_PLANT_HEIGHT_SOLTO,
            ICON_BASE * (1.0 + _ICON_PLANT_HEIGHT_SOLTO) / 2,
            topo=ICON_FRAME_Y_SOLTO,
        )
    else:
        # Ladrilho: cantos arredondados e um gradiente vertical discreto, para
        # não ficar um bloco chapado.
        moldura = QPainterPath()
        moldura.addRoundedRect(
            0, 0, ICON_BASE, ICON_BASE, ICON_BASE * 0.22, ICON_BASE * 0.22
        )
        parede = QLinearGradient(0, 0, 0, ICON_BASE)
        parede.setColorAt(0.0, QColor("#332B26"))
        parede.setColorAt(1.0, QColor("#1A1614"))
        painter.fillPath(moldura, QBrush(parede))

        painter.save()
        painter.setClipPath(moldura)
        # Um pouco à esquerda e acima do centro, como na cena — mas perto o
        # bastante da planta para funcionar como contraluz. É esse halo que
        # separa a silhueta do fundo quando o ícone encolhe.
        brilho = QRadialGradient(
            QPointF(ICON_BASE * 0.42, ICON_BASE * 0.46), ICON_BASE * 0.58
        )
        brilho.setColorAt(0.0, QColor(224, 164, 88, 130))
        brilho.setColorAt(0.45, QColor(224, 164, 88, 52))
        brilho.setColorAt(1.0, QColor(224, 164, 88, 0))
        painter.fillPath(moldura, QBrush(brilho))

        _desenhar_planta(
            painter,
            stage,
            ICON_BASE * _ICON_PLANT_HEIGHT,
            ICON_BASE * (1.0 - _ICON_PLANT_BOTTOM),
        )
        painter.restore()

        # Fio de luz na borda: separa o ladrilho de uma barra escura.
        caneta = QPen(QColor(237, 224, 208, 38))
        caneta.setWidthF(ICON_BASE * 0.012)
        painter.setPen(caneta)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(moldura)

    painter.end()

    if size == ICON_BASE:
        return base
    # Compõe grande e reduz: rasterizar SVG direto em 16 px sai empastado.
    return base.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


GRAIN_TILE = 128


def render_grain(seed: int) -> QImage:
    """Ladrilho de ruído monocromático para o grão de filme.

    O CLAUDE.md pede um `ShaderEffect`, mas shader no Qt6 precisa ser compilado
    para `.qsb` por uma ferramenta externa — dependência de build que o projeto
    não tem. Um ladrilho de ruído repetido com opacidade baixa dá o mesmo
    resultado na tela e não acrescenta etapa de build nenhuma.
    """
    import random

    rng = random.Random(seed)
    imagem = QImage(GRAIN_TILE, GRAIN_TILE, QImage.Format_ARGB32_Premultiplied)
    for y in range(GRAIN_TILE):
        for x in range(GRAIN_TILE):
            valor = rng.randint(0, 255)
            imagem.setPixel(x, y, (255 << 24) | (valor << 16) | (valor << 8) | valor)
    return imagem


class SceneImageProvider(QQuickImageProvider):
    """Ponte entre as URLs `image://cena/...` do QML e os renderizadores acima.

    Formato do id:
        `estatico/<tema>`
        `planta/<estagio>`
        `estante/<tema>/<obj_a,obj_b,...>`

    O QML cacheia por URL, então mudar o estágio da planta ou a lista de
    objetos já invalida a imagem sozinho.
    """

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:
        partes = id.split("/")
        if partes[0] == "grao":
            imagem = render_grain(int(partes[1]) if len(partes) > 1 else 0)
            if size is not None:
                size.setWidth(imagem.width())
                size.setHeight(imagem.height())
            return imagem

        alvo = _target_size(requestedSize)
        try:
            if partes[0] == "estatico":
                imagem = render_static(partes[1], alvo)
            elif partes[0] == "planta":
                imagem = render_plant(int(partes[1]), alvo)
            elif partes[0] == "estante":
                tipos = [t for t in partes[2].split(",") if t] if len(partes) > 2 else []
                imagem = render_shelf(partes[1], tipos, alvo)
            else:
                logger.warning("pedido de imagem desconhecido: %s", id)
                imagem = _blank(alvo)
        except (IndexError, ValueError):
            logger.exception("pedido de imagem malformado: %s", id)
            imagem = _blank(alvo)

        if size is not None:
            size.setWidth(imagem.width())
            size.setHeight(imagem.height())
        return imagem
