"""Geometria e renderização das camadas do cenário.

Estes testes tocam PySide6, que é permitido em `services/`. O que não pode é o
`core` depender de Qt — isso continua valendo e é verificado em outro lugar.
"""

from __future__ import annotations

import pytest

from cantinho.core.projections import SHELF_OBJECT_TYPES
from cantinho.services import scene

pytest.importorskip("PySide6.QtSvg")

# Depois do `importorskip`: sem PySide6 não há o que medir.
from imagens import medir


# ------------------------------------------------------------------- assets
#
# O inventário dos arquivos desenhados. Era um teste por pergunta — "os dois
# temas existem", "os cinco estágios existem", "as camadas existem nos dois",
# "todo tipo de objeto tem arte" —, cada um reabrindo os mesmos SVGs. Agora é
# uma leitura por arquivo, e ela responde tudo o que se quer saber daquele
# arquivo de uma vez, inclusive o que ninguém estava perguntando: o `viewBox`.


def _inventario(caminho, ids: tuple[str, ...]) -> dict:
    """Abre um SVG uma vez e devolve o que os testes perguntam dele."""
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(caminho))
    caixa = renderer.viewBoxF()
    return {
        "existe": caminho.is_file(),
        "valido": renderer.isValid(),
        "viewbox": (caixa.width(), caixa.height()),
        "falta": tuple(nome for nome in ids if not renderer.elementExists(nome)),
        "tamanhos": {
            nome: (
                renderer.boundsOnElement(nome).width(),
                renderer.boundsOnElement(nome).height(),
            )
            for nome in ids
            if renderer.elementExists(nome)
        },
    }


@pytest.mark.parametrize("tema", scene.THEMES)
def test_a_cena_do_tema_esta_inteira(app, tema: str) -> None:
    """As camadas e os objetos, com os mesmos ids nos dois arquivos.

    Ids idênticos é o que permite o crossfade entre os temas: as duas cenas são
    a mesma geometria em duas paletas, e `services/scene.py` monta a imagem
    pedindo elemento por elemento. Um id que existe num arquivo e não no outro
    não aparece como erro — aparece como um pedaço do quarto que some ao
    escurecer.
    """
    esperados = tuple(scene.STATIC_LAYERS) + tuple(SHELF_OBJECT_TYPES)
    achado = _inventario(scene.scene_path(tema), esperados)

    assert achado["existe"], tema
    assert achado["valido"], f"{tema}: o Qt não renderiza este SVG"
    assert achado["falta"] == (), f"{tema}: faltam {achado['falta']}"
    # O viewBox é o que faz as camadas se sobreporem: duas cenas com caixas
    # diferentes desalinhariam o quarto inteiro no crossfade, e nenhuma
    # validação de SVG reclamaria disso.
    assert achado["viewbox"] == (scene.SCENE_WIDTH, scene.SCENE_HEIGHT)


@pytest.mark.parametrize("estagio", range(scene.PLANT_STAGES))
def test_a_planta_do_estagio_esta_inteira(app, estagio: int) -> None:
    """Mesma caixa em todos os estágios: é o que mantém o vaso parado.

    `services/scene.py` desenha a planta por cima da cena com um deslocamento
    fixo (`PLANT_OFFSET_X/Y`). Se um estágio tivesse outro `viewBox`, ele
    entraria em outra escala e a planta pularia ao crescer.
    """
    achado = _inventario(scene.plant_path(estagio), ("planta",))

    assert achado["existe"], estagio
    assert achado["valido"], f"estágio {estagio}: o Qt não renderiza"
    assert achado["falta"] == (), f"estágio {estagio}: sem o elemento 'planta'"
    assert achado["viewbox"] == (200.0, 260.0)


def test_a_folhagem_cresce_a_cada_estagio(app) -> None:
    """Cada estágio tem que desenhar mais folha que o anterior.

    Numa leitura por arquivo, comparando os cinco de uma vez — a versão
    anterior reabria o estágio anterior a cada caso para comparar dois a dois.
    """
    tamanhos = [
        _inventario(scene.plant_path(estagio), ("planta",))["tamanhos"]["planta"]
        for estagio in range(scene.PLANT_STAGES)
    ]
    larguras = [largura for largura, _ in tamanhos]
    alturas = [altura for _, altura in tamanhos]

    assert larguras == sorted(larguras) and len(set(larguras)) == len(larguras), (
        f"a folhagem não alarga a cada estágio: {larguras}"
    )
    assert alturas == sorted(alturas) and len(set(alturas)) == len(alturas), (
        f"a folhagem não sobe a cada estágio: {alturas}"
    )


def test_estagio_fora_da_faixa_e_grampeado() -> None:
    assert scene.plant_path(-3) == scene.plant_path(0)
    assert scene.plant_path(99) == scene.plant_path(scene.PLANT_STAGES - 1)


# ---------------------------------------------------------------- prateleira
#
# Eram nove testes sobre `shelf_slots`, cada um chamando a função com uma
# quantidade escolhida a dedo: dentro da prateleira em 12, a de cima cheia em
# 8, sem repetição em 12. O que eles descreviam eram invariantes — coisas que
# valem para **toda** quantidade —, e conferi-las num ponto só deixava o resto
# da faixa sem prova nenhuma. A varredura abaixo passa por todas as
# quantidades possíveis, da estante vazia à lotada com sobra.


def test_as_invariantes_da_prateleira_valem_em_toda_quantidade() -> None:
    """Uma varredura, cinco invariantes, todas as quantidades.

    Elas andam juntas de propósito: é a mesma passada que mostra que o slot 3
    não mudou de lugar quando chegou o quarto objeto, e que ele continua dentro
    da prateleira. Separadas, cada uma escolheria um número diferente e
    nenhuma cobriria a faixa inteira.
    """
    anterior: list[tuple[float, float]] = []

    for quantidade in range(0, scene.SHELF_CAPACITY + 41):
        posicoes = scene.shelf_slots(quantidade)
        cabem = min(quantidade, scene.SHELF_CAPACITY)

        # 1. Uma posição por objeto, até a lotação — e a lotação não é
        #    ultrapassada: é o desenho que lota, não a projeção.
        assert len(posicoes) == cabem, quantidade

        # 2. Determinística: a mesma pergunta, a mesma resposta.
        assert posicoes == scene.shelf_slots(quantidade)

        # 3. Objeto já posto não muda de lugar. **A invariante da estante**: a
        #    primeira versão repartia a largura pelo número de objetos, então
        #    entregar uma tarefa recolocava todas as outras e a prateleira
        #    inteira pulava, sem transição, no instante em que a atenção
        #    estava nela.
        assert posicoes[: len(anterior)] == anterior, quantidade

        # 4. Nenhuma posição se repete: dois objetos no mesmo lugar são um
        #    objeto sumido.
        assert len(set(posicoes)) == len(posicoes), quantidade

        # 5. Tudo dentro da prateleira desenhada.
        for centro_x, base_y in posicoes:
            assert scene.SHELF_X_MIN <= centro_x <= scene.SHELF_X_MAX
            assert base_y in scene.SHELF_LEDGES

        anterior = posicoes[:cabem]


def test_a_de_cima_enche_antes_da_de_baixo() -> None:
    """A ordem de preenchimento é a leitura: a prateleira de cima primeiro."""
    for quantidade in range(1, scene.SHELF_CAPACITY + 1):
        alturas = [y for _, y in scene.shelf_slots(quantidade)]
        em_cima = min(quantidade, scene.SHELF_PER_LEDGE)
        assert alturas.count(scene.SHELF_LEDGES[0]) == em_cima, quantidade
        assert alturas.count(scene.SHELF_LEDGES[1]) == quantidade - em_cima, quantidade


# ------------------------------------------------------------- renderização


@pytest.fixture(scope="module")
def app():
    from PySide6.QtGui import QGuiApplication

    instancia = QGuiApplication.instance() or QGuiApplication([])
    return instancia


# As três leituras de SVG que havia aqui — camadas nos dois temas, arte de todo
# objeto, folhagem crescendo — subiram para o inventário lá em cima, onde cada
# arquivo é aberto uma vez e responde tudo. O que fica nesta seção é o que só a
# imagem rasterizada responde: onde a tinta caiu.


def _desenhado(imagem, limiar: int = 30):
    """A silhueta do que foi desenhado, medida de uma passada (`imagens.py`).

    A varredura antiga pulava de dois em dois pixels para caber no tempo, o que
    tornava "não desenhou nada" uma afirmação sobre os pixels pares. Esta olha
    todos e ainda é mais rápida, porque as contas rodam em C.
    """
    return medir(imagem, limiar)


@pytest.mark.parametrize("tema", scene.THEMES)
def test_cenario_estatico_desenha_alguma_coisa(app, tema: str) -> None:
    from PySide6.QtCore import QSize

    quadro = _desenhado(scene.render_static(tema, QSize(550, 350)), 8)
    assert (quadro.largura, quadro.altura) == (550, 350)
    assert quadro.desenhou


def test_planta_desenha_na_area_do_vaso(app) -> None:
    """Folhagem fora do vaso é sinal de deslocamento errado entre os arquivos."""
    from PySide6.QtCore import QSize

    quadro = _desenhado(scene.render_plant(4, QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT)))
    assert quadro.caixa is not None, "a planta não desenhou nada"
    x_min, y_min, x_max, y_max = quadro.caixa

    # O vaso da cena fica em x 890..998, y 486..581.
    assert 820 < x_min and x_max < 1060
    assert 340 < y_min and y_max < 520


def test_estante_vazia_nao_desenha_nada(app) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_shelf("noite", [], QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT))
    assert not _desenhado(imagem, 8).desenhou


def test_estante_desenha_na_area_da_estante(app) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_shelf(
        "noite", ["obj_0", "obj_3", "obj_5"], QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT)
    )
    quadro = _desenhado(imagem)
    assert quadro.caixa is not None, "a estante não desenhou nada"
    x_min, _, x_max, y_max = quadro.caixa

    assert scene.SHELF_X_MIN - 30 < x_min and x_max < scene.SHELF_X_MAX + 30
    assert y_max <= max(scene.SHELF_LEDGES) + 2


def test_tipo_desconhecido_nao_derruba_a_estante(app) -> None:
    from PySide6.QtCore import QSize

    imagem = scene.render_shelf(
        "noite", ["obj_0", "nao_existe"], QSize(scene.SCENE_WIDTH, scene.SCENE_HEIGHT)
    )
    assert _desenhado(imagem, 8).desenhou


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
