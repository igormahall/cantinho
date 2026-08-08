"""O ícone do app.

O ícone é gerado a partir da planta do quarto e versionado pronto. Estes testes
seguram o que quebra em silêncio: um `.ico` malformado só aparece na barra de
tarefas do usuário, e um ícone ilegível em 16 px ninguém percebe rodando em
1440p.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from cantinho.services import scene

pytest.importorskip("PySide6.QtSvg")

ICONE = scene.assets_dir() / "icon" / "cantinho.ico"
PNG = scene.assets_dir() / "icon" / "cantinho.png"


@pytest.fixture(scope="module")
def app():
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication([])


# --------------------------------------------------------------- arquivos


def test_os_arquivos_existem() -> None:
    assert ICONE.is_file()
    assert PNG.is_file()


def test_o_ico_declara_os_tamanhos_esperados() -> None:
    """Lê o diretório do .ico sem depender do Qt, para conferir o que gravei."""
    dados = ICONE.read_bytes()
    reservado, tipo, quantidade = struct.unpack("<HHH", dados[:6])
    assert reservado == 0
    assert tipo == 1, "tipo 1 é ícone; 2 seria cursor"
    assert quantidade == 7

    lados = []
    for indice in range(quantidade):
        base = 6 + 16 * indice
        largura, altura, _, _, planos, bits, tamanho, deslocamento = struct.unpack(
            "<BBBBHHII", dados[base : base + 16]
        )
        lados.append(largura or 256)
        assert altura == largura, "quadro não quadrado"
        assert planos == 1
        assert bits == 32
        # O deslocamento e o tamanho têm que cair dentro do arquivo, senão o
        # Windows mostra o ícone genérico e não diz por quê.
        assert deslocamento + tamanho <= len(dados)
        assert dados[deslocamento : deslocamento + 8] == b"\x89PNG\r\n\x1a\n"

    assert lados == [16, 24, 32, 48, 64, 128, 256]


def test_o_qt_rele_todos_os_tamanhos(app) -> None:
    from PySide6.QtGui import QIcon

    icone = QIcon(str(ICONE))
    assert not icone.isNull()
    lados = sorted(tamanho.width() for tamanho in icone.availableSizes())
    assert lados == [16, 24, 32, 48, 64, 128, 256]


# ------------------------------------------------------------- composição


@pytest.mark.parametrize("lado", [16, 24, 32, 48, 64, 128, 256])
def test_render_devolve_o_tamanho_pedido(app, lado: int) -> None:
    imagem = scene.render_icon(2, lado)
    assert imagem.width() == lado
    assert imagem.height() == lado


@pytest.mark.parametrize("estagio", range(scene.PLANT_STAGES))
def test_todo_estagio_desenha_alguma_coisa(app, estagio: int) -> None:
    imagem = scene.render_icon(estagio, 64)
    visiveis = sum(
        1
        for y in range(0, 64, 2)
        for x in range(0, 64, 2)
        if imagem.pixelColor(x, y).alpha() > 16
    )
    assert visiveis > 60, f"estágio {estagio} saiu quase vazio"


def test_os_estagios_nao_sao_iguais(app) -> None:
    """Se saírem idênticos, a bandeja para de contar a história do crescimento."""
    vistos = [scene.render_icon(estagio, 64) for estagio in range(scene.PLANT_STAGES)]
    for anterior in range(len(vistos) - 1):
        assert vistos[anterior] != vistos[anterior + 1], f"estágio {anterior} igual ao seguinte"


def test_a_planta_cresce_dentro_do_quadro_fixo(app) -> None:
    """A moldura é fixa: o vaso não pode andar entre um estágio e outro.

    O que muda de tamanho é a folhagem. Se o vaso subisse ou encolhesse junto,
    o ícone da bandeja pularia a cada mudança de estágio.
    """
    def base_do_vaso(estagio: int) -> int:
        imagem = scene.render_icon(estagio, 128)
        for y in range(127, -1, -1):
            for x in range(128):
                if imagem.pixelColor(x, y).alpha() > 200:
                    return y
        return -1

    bases = [base_do_vaso(estagio) for estagio in range(scene.PLANT_STAGES)]
    assert max(bases) - min(bases) <= 2, f"o vaso se move entre estágios: {bases}"


def test_verde_aumenta_com_o_estagio(app) -> None:
    """A folhagem é o que cresce, então o verde tem que crescer junto."""
    def pixels_verdes(estagio: int) -> int:
        imagem = scene.render_icon(estagio, 128)
        total = 0
        for y in range(128):
            for x in range(128):
                cor = imagem.pixelColor(x, y)
                if cor.alpha() > 128 and cor.green() > cor.red() and cor.green() > cor.blue():
                    total += 1
        return total

    verdes = [pixels_verdes(estagio) for estagio in range(scene.PLANT_STAGES)]
    assert verdes == sorted(verdes), f"o verde não cresce monotonicamente: {verdes}"
    assert verdes[-1] > verdes[0] * 3


# --------------------------------------------------------- tamanhos pequenos


def test_o_pequeno_larga_o_ladrilho(app) -> None:
    """Em 16 px o ladrilho engoliria o vaso. Os cantos têm que ficar vazios."""
    imagem = scene.render_icon(2, 16)
    cantos = [(0, 0), (15, 0), (0, 15), (15, 15)]
    assert all(imagem.pixelColor(x, y).alpha() < 40 for x, y in cantos)


def test_o_grande_tem_ladrilho(app) -> None:
    """No tamanho de identidade o ladrilho é o quarto, e ele precisa estar lá."""
    imagem = scene.render_icon(2, 128)
    assert imagem.pixelColor(64, 8).alpha() > 200
    assert imagem.pixelColor(8, 64).alpha() > 200


@pytest.mark.parametrize("lado", [16, 24])
def test_o_pequeno_preenche_o_quadro(app, lado: int) -> None:
    """Sem ladrilho, a planta tem que ocupar quase todo o espaço.

    Os limiares vêm de medição no desenho atual (largura 56%, altura 88%,
    cobertura 29%), com folga. Não são alvo estético: existem para pegar
    regressão. Se alguém encolher a planta, reinstalar o ladrilho no tamanho
    pequeno ou voltar a moldura cheia — que deixava o vaso com sete pixels de
    largura — isto quebra.
    """
    imagem = scene.render_icon(2, lado)
    pontos = [
        (x, y)
        for y in range(lado)
        for x in range(lado)
        if imagem.pixelColor(x, y).alpha() > 40
    ]
    assert pontos, "não desenhou nada"

    xs = [x for x, _ in pontos]
    ys = [y for _, y in pontos]
    largura = (max(xs) - min(xs) + 1) / lado
    altura = (max(ys) - min(ys) + 1) / lado
    cobertura = len(pontos) / (lado * lado)

    assert largura > 0.45, f"largura de só {largura:.0%}"
    assert altura > 0.75, f"altura de só {altura:.0%}"
    assert cobertura > 0.20, f"cobertura de só {cobertura:.0%}"


def test_o_pequeno_aparece_em_fundo_claro_e_escuro(app) -> None:
    """A bandeja pode ser clara ou escura. O vaso tem que aparecer nas duas."""
    imagem = scene.render_icon(2, 16)
    opacos = [
        imagem.pixelColor(x, y)
        for y in range(16)
        for x in range(16)
        if imagem.pixelColor(x, y).alpha() > 200
    ]
    assert opacos, "nada opaco: o ícone some em qualquer fundo"

    claros = sum(1 for cor in opacos if cor.lightness() > 140)
    escuros = sum(1 for cor in opacos if cor.lightness() < 90)
    assert claros > 0, "nada claro o bastante para aparecer em barra escura"
    assert escuros > 0 or claros > 4, "contraste insuficiente em barra clara"
