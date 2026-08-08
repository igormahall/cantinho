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
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QPainter
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
    renderer = _renderers.get(scene_path(theme))
    if renderer is None:
        return imagem

    visiveis = object_types[:SHELF_CAPACITY]
    posicoes = shelf_slots(len(visiveis))
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
