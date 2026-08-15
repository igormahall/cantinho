"""O ícone do app.

O ícone é gerado a partir da planta do quarto e versionado pronto. Estes testes
seguram o que quebra em silêncio: um `.ico` malformado só aparece na barra de
tarefas do usuário, e um ícone ilegível em 16 px ninguém percebe rodando em
1440p.

**Cada quadro é desenhado e medido uma vez.** Antes cada teste redesenhava os
cinco estágios e varria a imagem com `pixelColor` em laço aninhado — meio milhão
de chamadas Python→C++ para responder duas perguntas. Agora o desenho fica em
cache e a varredura é uma só, em `imagens.py`, que devolve de uma vez a silhueta
inteira: quantos pixels, onde eles começam e terminam, e onde está o pé do
desenho. Os testes leem da medida.

A troca não foi só de custo. A varredura antiga pulava de dois em dois pixels
para caber no tempo, e uma delas media a coisa errada por causa disso — ver
`test_o_pe_do_desenho_nao_anda_entre_estagios`.
"""

from __future__ import annotations

import struct
from functools import lru_cache
from pathlib import Path

import pytest

from cantinho.services import scene

pytest.importorskip("PySide6.QtSvg")

# Depois do `importorskip`: sem PySide6 não há o que medir.
from imagens import Medida, medir, tons, verdes

ICONE = scene.assets_dir() / "icon" / "cantinho.ico"
PNG = scene.assets_dir() / "icon" / "cantinho.png"

# Os sete tamanhos que o `.ico` carrega, e o corte do ladrilho no meio deles.
LADOS = (16, 24, 32, 48, 64, 128, 256)
LADOS_SEM_LADRILHO = tuple(lado for lado in LADOS if lado < scene.ICON_TILE_MIN)
LADOS_COM_LADRILHO = tuple(lado for lado in LADOS if lado >= scene.ICON_TILE_MIN)

ESTAGIOS = tuple(range(scene.PLANT_STAGES))

# O alfa a partir do qual o pixel conta como parte da silhueta. Abaixo disto é
# a franja de antisserrilhado, que num ícone de 16 px é quase tudo.
SILHUETA = 40


@pytest.fixture(scope="module")
def app():
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication([])


@lru_cache(maxsize=None)
def desenho(estagio: int, lado: int):
    """O quadro do ícone, desenhado uma vez por (estágio, tamanho)."""
    return scene.render_icon(estagio, lado)


@lru_cache(maxsize=None)
def medida(estagio: int, lado: int, limiar: int = SILHUETA) -> Medida:
    return medir(desenho(estagio, lado), limiar)


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
    assert quantidade == len(LADOS)

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

    assert lados == list(LADOS)


def _quadro_de(caminho: Path, lado: int):
    """Lê do `.ico` o quadro exatamente deste tamanho.

    `QIcon.pixmap(64, 64)` seria mais curto e está errado: ele devolve o
    pixmap já escalado para a densidade da tela. Num monitor a 125% isso vira
    uma imagem de 80x80 com `devicePixelRatio` 1,25, que nunca vai bater com os
    64x64 do gerador — e o teste passa ou falha conforme o monitor de quem
    roda, que é a pior espécie de teste.

    `QImageReader` percorre os quadros do contêiner e devolve o pixel como ele
    está gravado no arquivo, que é o que este teste quer comparar.
    """
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QImageReader

    leitor = QImageReader(str(caminho))
    for indice in range(leitor.imageCount()):
        leitor.jumpToImage(indice)
        if leitor.size() == QSize(lado, lado):
            return leitor.read()
    return None


def _estagio_do_gerador() -> int:
    """Lê `ESTAGIO_IDENTIDADE` do texto de `tools/gerar_icone.py`.

    Lê em vez de importar de propósito. Importar por caminho passa pelo cache
    de bytecode, e trocar um dígito da constante mantém o tamanho do arquivo:
    se as duas edições caírem no mesmo segundo, o Python valida um `.pyc`
    velho e o teste compara contra o estágio errado — foi o que aconteceu aqui.
    """
    import re

    fonte = (
        Path(__file__).resolve().parents[1] / "tools" / "gerar_icone.py"
    ).read_text(encoding="utf-8")
    achado = re.search(r"^ESTAGIO_IDENTIDADE\s*=\s*(\d+)", fonte, re.MULTILINE)
    assert achado, "não achei ESTAGIO_IDENTIDADE em tools/gerar_icone.py"
    return int(achado.group(1))


IDENTIDADE = _estagio_do_gerador()


def test_o_arquivo_versionado_bate_com_o_gerador(app) -> None:
    """O `.ico` no repositório tem que ser o que o gerador produz hoje.

    Mudar `ESTAGIO_IDENTIDADE` e esquecer de rodar `tools/gerar_icone.py`
    deixaria o arquivo versionado descrevendo outra coisa — e ninguém percebe,
    porque o ícone só aparece na barra de tarefas depois do build.
    """
    esperado = desenho(IDENTIDADE, 64)
    gravado = _quadro_de(ICONE, 64)
    assert gravado is not None, "o .ico não tem quadro de 64 px"

    assert gravado.convertToFormat(esperado.format()) == esperado, (
        f"o .ico versionado não corresponde ao estágio {IDENTIDADE}; "
        "rode tools/gerar_icone.py"
    )


def test_o_qt_rele_todos_os_tamanhos(app) -> None:
    from PySide6.QtGui import QIcon

    icone = QIcon(str(ICONE))
    assert not icone.isNull()
    lados = sorted(tamanho.width() for tamanho in icone.availableSizes())
    assert lados == list(LADOS)


# ------------------------------------------------------------- composição


@pytest.mark.parametrize("lado", LADOS)
def test_render_devolve_o_tamanho_pedido(app, lado: int) -> None:
    quadro = medida(IDENTIDADE, lado)
    assert (quadro.largura, quadro.altura) == (lado, lado)


@pytest.mark.parametrize("estagio", ESTAGIOS)
def test_todo_estagio_desenha_alguma_coisa(app, estagio: int) -> None:
    quadro = medida(estagio, 64)
    assert quadro.cobertura > 0.06, f"estágio {estagio} saiu quase vazio"


def test_os_estagios_nao_sao_iguais(app) -> None:
    """Se saírem idênticos, a bandeja para de contar a história do crescimento."""
    vistos = [desenho(estagio, 64) for estagio in ESTAGIOS]
    for anterior in range(len(vistos) - 1):
        assert vistos[anterior] != vistos[anterior + 1], (
            f"estágio {anterior} igual ao seguinte"
        )


@pytest.mark.parametrize("lado", LADOS_SEM_LADRILHO)
def test_o_pe_do_desenho_nao_anda_entre_estagios(app, lado: int) -> None:
    """A moldura é fixa: o vaso não pode subir nem descer entre um estágio e
    outro, senão o ícone da bandeja pula a cada mudança.

    **A medição é nos tamanhos sem ladrilho, e isso é a correção.** A versão
    anterior procurava o pixel opaco mais baixo em 128 px — mas em 128 px o
    ladrilho é opaco e ocupa o quadro inteiro, então a resposta era "a última
    linha da imagem" para os cinco estágios, sempre. O teste passava sem olhar
    para o vaso: passaria também se o vaso andasse meio quadro.

    Abaixo de 32 px o ladrilho sai e a silhueta é a planta, então o pé da
    silhueta é o pé do vaso. Aqui ele tem que ser exatamente o mesmo em todos os
    estágios — e o topo só pode subir, porque o que cresce é a folhagem.
    """
    caixas = [medida(estagio, lado).caixa for estagio in ESTAGIOS]
    assert all(caixa is not None for caixa in caixas)

    pes = {caixa[3] for caixa in caixas}  # type: ignore[index]
    assert len(pes) == 1, f"o pé do desenho anda entre estágios: {sorted(pes)}"

    topos = [caixa[1] for caixa in caixas]  # type: ignore[index]
    assert topos == sorted(topos, reverse=True), f"a folhagem não sobe: {topos}"
    assert topos[0] > topos[-1], "o estágio 4 não é mais alto que o 0"


def test_verde_aumenta_com_o_estagio(app) -> None:
    """A folhagem é o que cresce, então o verde tem que crescer junto."""
    contagens = [verdes(desenho(estagio, 128)) for estagio in ESTAGIOS]
    assert contagens == sorted(contagens), f"o verde não cresce: {contagens}"
    assert contagens[-1] > contagens[0] * 3


# --------------------------------------------------------- tamanhos pequenos


@pytest.mark.parametrize("lado", LADOS_SEM_LADRILHO)
def test_o_pequeno_larga_o_ladrilho(app, lado: int) -> None:
    """Em 16 px o ladrilho engoliria o vaso: as bordas têm que ficar livres.

    A versão anterior olhava os quatro cantos. Esta olha as colunas e a linha
    inteiras — o topo fica de fora porque a folhagem dos estágios altos encosta
    lá de propósito.
    """
    caixa = medida(IDENTIDADE, lado).caixa
    assert caixa is not None
    assert caixa[0] > 0 and caixa[2] < lado - 1, f"o desenho encosta na lateral: {caixa}"
    assert caixa[3] < lado - 1, f"o desenho encosta no pé do quadro: {caixa}"


@pytest.mark.parametrize("lado", LADOS_COM_LADRILHO)
def test_o_grande_tem_ladrilho(app, lado: int) -> None:
    """Do tamanho de identidade para cima o ladrilho é o quarto, e ele precisa
    estar lá — é o que faz o ícone ser um cômodo reduzido a um quadrado."""
    quadro = medida(IDENTIDADE, lado, 200)
    assert quadro.caixa == (0, 0, lado - 1, lado - 1), "o ladrilho não cobre o quadro"
    assert quadro.cobertura > 0.9


@pytest.mark.parametrize("lado", LADOS_SEM_LADRILHO)
def test_o_pequeno_preenche_o_quadro(app, lado: int) -> None:
    """Sem ladrilho, a planta tem que ocupar quase todo o espaço.

    Os limiares vêm de medição no desenho atual (largura 56%, altura 88%,
    cobertura 29%), com folga. Não são alvo estético: existem para pegar
    regressão. Se alguém encolher a planta, reinstalar o ladrilho no tamanho
    pequeno ou voltar a moldura cheia — que deixava o vaso com sete pixels de
    largura — isto quebra.
    """
    quadro = medida(IDENTIDADE, lado)
    assert quadro.desenhou, "não desenhou nada"
    assert quadro.fracao_da_largura() > 0.45, f"largura de só {quadro.fracao_da_largura():.0%}"
    assert quadro.fracao_da_altura() > 0.75, f"altura de só {quadro.fracao_da_altura():.0%}"
    assert quadro.cobertura > 0.20, f"cobertura de só {quadro.cobertura:.0%}"


@pytest.mark.parametrize("lado", LADOS_SEM_LADRILHO)
def test_o_pequeno_aparece_em_fundo_claro_e_escuro(app, lado: int) -> None:
    """A bandeja pode ser clara ou escura. O vaso tem que aparecer nas duas."""
    claros, escuros = tons(desenho(IDENTIDADE, lado))
    assert claros or escuros, "nada opaco: o ícone some em qualquer fundo"
    assert claros > 0, "nada claro o bastante para aparecer em barra escura"
    assert escuros > 0 or claros > 4, "contraste insuficiente em barra clara"
