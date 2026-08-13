"""Geometria e renderização das camadas do cenário.

Estes testes tocam PySide6, que é permitido em `services/`. O que não pode é o
`core` depender de Qt — isso continua valendo e é verificado em outro lugar.
"""

from __future__ import annotations

import pytest

from cantinho.core.projections import SHELF_OBJECT_TYPES
from cantinho.services import scene

pytest.importorskip("PySide6.QtSvg")


# ------------------------------------------------------------------- assets


def test_os_dois_temas_existem() -> None:
    for tema in scene.THEMES:
        assert scene.scene_path(tema).is_file(), tema


def test_os_cinco_estagios_de_planta_existem() -> None:
    for estagio in range(scene.PLANT_STAGES):
        assert scene.plant_path(estagio).is_file(), estagio


def test_estagio_fora_da_faixa_e_grampeado() -> None:
    assert scene.plant_path(-3) == scene.plant_path(0)
    assert scene.plant_path(99) == scene.plant_path(scene.PLANT_STAGES - 1)


# ---------------------------------------------------------------- prateleira


def test_estante_vazia_nao_tem_posicao() -> None:
    assert scene.shelf_slots(0) == []


@pytest.mark.parametrize("quantidade", range(1, scene.SHELF_CAPACITY + 1))
def test_uma_posicao_por_objeto(quantidade: int) -> None:
    posicoes = scene.shelf_slots(quantidade)
    assert len(posicoes) == quantidade


def test_posicoes_ficam_dentro_da_prateleira() -> None:
    for centro_x, base_y in scene.shelf_slots(scene.SHELF_CAPACITY):
        assert scene.SHELF_X_MIN <= centro_x <= scene.SHELF_X_MAX
        assert base_y in scene.SHELF_LEDGES


def test_primeiros_tres_ficam_na_prateleira_de_cima() -> None:
    assert all(y == scene.SHELF_LEDGES[0] for _, y in scene.shelf_slots(3))


def test_a_de_cima_enche_antes_da_de_baixo() -> None:
    alturas = [y for _, y in scene.shelf_slots(scene.SHELF_PER_LEDGE + 2)]
    assert alturas.count(scene.SHELF_LEDGES[0]) == scene.SHELF_PER_LEDGE
    assert alturas.count(scene.SHELF_LEDGES[1]) == 2


def test_objeto_ja_posto_nao_muda_de_lugar() -> None:
    """A invariante da estante, e a razão de os slots serem fixos.

    A primeira versão repartia a largura pelo número de objetos, então entregar
    uma tarefa recolocava todas as outras: a prateleira inteira pulava, sem
    transição, no instante em que a atenção estava nela.
    """
    for quantidade in range(1, scene.SHELF_CAPACITY):
        antes = scene.shelf_slots(quantidade)
        depois = scene.shelf_slots(quantidade + 1)
        assert depois[:quantidade] == antes


def test_lotacao_nao_e_ultrapassada() -> None:
    assert len(scene.shelf_slots(scene.SHELF_CAPACITY + 40)) == scene.SHELF_CAPACITY


def test_posicoes_nao_se_repetem() -> None:
    posicoes = scene.shelf_slots(scene.SHELF_CAPACITY)
    assert len(set(posicoes)) == len(posicoes)


def test_shelf_slots_e_deterministico() -> None:
    assert scene.shelf_slots(7) == scene.shelf_slots(7)


# ------------------------------------------------------------- renderização


@pytest.fixture(scope="module")
def app():
    from PySide6.QtGui import QGuiApplication

    instancia = QGuiApplication.instance() or QGuiApplication([])
    return instancia


def _tem_pixel_visivel(imagem) -> bool:
    for y in range(0, imagem.height(), 4):
        for x in range(0, imagem.width(), 4):
            if imagem.pixelColor(x, y).alpha() > 8:
                return True
    return False


@pytest.mark.parametrize("tema", scene.THEMES)
def test_cenario_estatico_desenha_alguma_coisa(app, tema: str) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_static(tema, QSize(550, 350))
    assert (imagem.width(), imagem.height()) == (550, 350)
    assert _tem_pixel_visivel(imagem)


def test_todas_as_camadas_estaticas_existem_nos_dois_svgs(app) -> None:
    """Ids idênticos nos dois arquivos é o que permite o crossfade."""
    from PySide6.QtSvg import QSvgRenderer

    for tema in scene.THEMES:
        renderer = QSvgRenderer(str(scene.scene_path(tema)))
        assert renderer.isValid(), tema
        for camada in scene.STATIC_LAYERS:
            assert renderer.elementExists(camada), f"{tema}/{camada}"


def test_todo_tipo_de_objeto_tem_arte_nos_dois_temas(app) -> None:
    """O catálogo da projeção e o desenho não podem divergir."""
    from PySide6.QtSvg import QSvgRenderer

    for tema in scene.THEMES:
        renderer = QSvgRenderer(str(scene.scene_path(tema)))
        for tipo in SHELF_OBJECT_TYPES:
            assert renderer.elementExists(tipo), f"{tema}/{tipo}"


@pytest.mark.parametrize("estagio", range(scene.PLANT_STAGES))
def test_planta_cresce_a_cada_estagio(app, estagio: int) -> None:
    """Cada estágio tem que desenhar mais folha que o anterior."""
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(scene.plant_path(estagio)))
    assert renderer.isValid()
    assert renderer.elementExists("planta")

    if estagio > 0:
        anterior = QSvgRenderer(str(scene.plant_path(estagio - 1)))
        atual = renderer.boundsOnElement("planta")
        antes = anterior.boundsOnElement("planta")
        assert atual.width() > antes.width()
        assert atual.height() > antes.height()


def test_planta_desenha_na_area_do_vaso(app) -> None:
    """Folhagem fora do vaso é sinal de deslocamento errado entre os arquivos."""
    from PySide6.QtCore import QSize

    imagem = scene.render_plant(4, QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT))
    xs, ys = [], []
    for y in range(0, imagem.height(), 2):
        for x in range(0, imagem.width(), 2):
            if imagem.pixelColor(x, y).alpha() > 30:
                xs.append(x)
                ys.append(y)

    assert xs, "a planta não desenhou nada"
    # O vaso da cena fica em x 890..998, y 486..581.
    assert 820 < min(xs) and max(xs) < 1060
    assert 340 < min(ys) and max(ys) < 520


def test_estante_vazia_nao_desenha_nada(app) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_shelf("noite", [], QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT))
    assert not _tem_pixel_visivel(imagem)


def test_estante_desenha_na_area_da_estante(app) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_shelf(
        "noite", ["obj_0", "obj_3", "obj_5"], QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT)
    )
    xs, ys = [], []
    for y in range(0, imagem.height(), 2):
        for x in range(0, imagem.width(), 2):
            if imagem.pixelColor(x, y).alpha() > 30:
                xs.append(x)
                ys.append(y)

    assert xs, "a estante não desenhou nada"
    assert scene.SHELF_X_MIN - 30 < min(xs) and max(xs) < scene.SHELF_X_MAX + 30
    assert max(ys) <= max(scene.SHELF_LEDGES) + 2


def test_tipo_desconhecido_nao_derruba_a_estante(app) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_shelf(
        "noite", ["obj_0", "nao_existe"], QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT)
    )
    assert _tem_pixel_visivel(imagem)


@pytest.mark.parametrize("tema", scene.THEMES)
def test_a_mesa_nao_tem_emenda(app, tema: str) -> None:
    """Regressão: as duas metades da mesa têm que virar uma superfície só.

    Com `abajur` desenhado entre `mesa_esquerda` e `mesa_direita`, o brilho do
    abajur caía sobre a mesa da esquerda e era apagado pela da direita, que é
    opaca e vinha por cima. Sobrava um degrau duro de 24 níveis exatamente em
    x=560, na emenda das duas.

    A varredura fica abaixo dos objetos apoiados na mesa, senão a caneca e os
    livros contam como salto — e eles são borda de verdade.
    """
    from PySide6.QtCore import QSize

    imagem = scene.render_static(tema, QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT))

    pior, onde = 0, (0, 0)
    for y in range(478, 489):
        for x in range(270, 830):
            atual = imagem.pixelColor(x, y)
            proximo = imagem.pixelColor(x + 1, y)
            salto = max(
                abs(atual.red() - proximo.red()),
                abs(atual.green() - proximo.green()),
                abs(atual.blue() - proximo.blue()),
            )
            if salto > pior:
                pior, onde = salto, (x, y)

    assert pior <= 10, f"degrau de {pior} níveis em x={onde[0]} y={onde[1]}"


def test_abajur_vem_depois_das_duas_mesas(app) -> None:
    """A ordem é o que corrige a emenda; trocar de novo traria o degrau."""
    ordem = list(scene.STATIC_LAYERS)
    assert ordem.index("abajur") > ordem.index("mesa_esquerda")
    assert ordem.index("abajur") > ordem.index("mesa_direita")


def test_grao_e_reprodutivel_por_seed(app) -> None:
    a = scene.render_grain(3)
    b = scene.render_grain(3)
    c = scene.render_grain(4)
    assert a == b
    assert a != c
