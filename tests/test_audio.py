"""O som: os loops de ambiente e as reações de interface.

Os arquivos são sintetizados por `tools/gerar_audio.py` e versionados prontos,
para que o app funcione num clone limpo sem etapa extra de build. Estes testes
seguram o contrato entre o gerador e `services/audio.py` — se o gerador mudar
um nome ou um formato, o app fica mudo em silêncio, que é a pior forma de
quebrar.

**Cada arquivo é lido e medido uma vez só.** Antes cada teste reabria o `.wav` e
reconstruía a lista de amostras: os dois arquivos de ambiente têm 24 segundos a
22 kHz, então eram meio milhão de amostras convertidas em float oito vezes, para
responder cinco perguntas. `medir()` faz uma passada e devolve todas as
respostas de uma vez; os testes leem da medida. É o mesmo rigor com um oitavo do
trabalho — e, de quebra, as perguntas de formato passaram a valer para os cinco
arquivos em vez de para dois grupos separados.
"""

from __future__ import annotations

import array
import math
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

from cantinho.services import audio, scene

TEMAS = ("noite", "tarde")
REACOES = tuple(audio.SFX_VOLUMES)

# A janela usada para ouvir as pontas do loop, em amostras.
PONTA = 2000


def caminho(tema: str) -> Path:
    return scene.assets_dir() / "audio" / f"ambiente_{tema}.wav"


def caminho_reacao(nome: str) -> Path:
    return scene.assets_dir() / "audio" / f"ui_{nome}.wav"


# Os cinco arquivos que o app toca, com o nome que aparece numa falha.
ARQUIVOS: tuple[tuple[str, Path], ...] = (
    *((f"ambiente_{tema}", caminho(tema)) for tema in TEMAS),
    *((f"ui_{nome}", caminho_reacao(nome)) for nome in REACOES),
)


@dataclass(frozen=True)
class Medida:
    """Tudo o que se quer saber de um `.wav`, de uma passada só.

    Os campos são as perguntas que os testes fazem: o formato que o
    `QSoundEffect` exige, o nível, a emenda do loop, o silêncio nas pontas e o
    brilho — que é o que separa a chuva no vidro do ar da sala.
    """

    canais: int
    largura: int
    taxa: int
    quadros: int
    duracao: float
    pico: float
    rms: float
    degrau_do_loop: float
    rms_do_comeco: float
    rms_do_fim: float
    primeira: float
    ultima: float
    energia_aguda: float


@lru_cache(maxsize=None)
def medir(caminho_do_arquivo: Path) -> Medida:
    """Lê o arquivo uma vez e mede tudo numa passada.

    A parte cara é o filtro passa-altas: ele é recursivo, então não há como
    escapar de percorrer amostra por amostra em Python. O que dá para não fazer
    é percorrer cinco vezes — daí ele dividir o laço com as somas de energia, e
    daí o resultado ficar em cache.
    """
    with wave.open(str(caminho_do_arquivo)) as arquivo:
        canais = arquivo.getnchannels()
        largura = arquivo.getsampwidth()
        taxa = arquivo.getframerate()
        quadros = arquivo.getnframes()
        bruto = array.array("h")
        bruto.frombytes(arquivo.readframes(quadros))

    escala = 1.0 / 32768.0
    # Constantes do passa-altas de 1500 Hz, o corte que separa o chiado da
    # chuva do ronco do ambiente de tarde.
    rc = 1.0 / (2 * math.pi * 1500.0)
    dt = 1.0 / taxa
    coeficiente = dt / (rc + dt)

    pico = 0.0
    soma_quadrados = 0.0
    soma_agudos = 0.0
    soma_comeco = 0.0
    soma_fim = 0.0
    baixo = 0.0
    total = len(bruto)
    inicio_do_fim = total - PONTA

    for indice, cru in enumerate(bruto):
        amostra = cru * escala
        quadrado = amostra * amostra
        soma_quadrados += quadrado

        modulo = -amostra if amostra < 0.0 else amostra
        if modulo > pico:
            pico = modulo

        baixo += coeficiente * (amostra - baixo)
        agudo = amostra - baixo
        soma_agudos += agudo * agudo

        if indice < PONTA:
            soma_comeco += quadrado
        elif indice >= inicio_do_fim:
            soma_fim += quadrado

    primeira = bruto[0] * escala
    ultima = bruto[-1] * escala

    return Medida(
        canais=canais,
        largura=largura,
        taxa=taxa,
        quadros=quadros,
        duracao=quadros / taxa,
        pico=pico,
        rms=math.sqrt(soma_quadrados / total),
        degrau_do_loop=abs(ultima - primeira),
        rms_do_comeco=math.sqrt(soma_comeco / min(PONTA, total)),
        rms_do_fim=math.sqrt(soma_fim / min(PONTA, total)),
        primeira=primeira,
        ultima=ultima,
        energia_aguda=soma_agudos / (soma_quadrados or 1.0),
    )


# --------------------------------------------------------- os cinco arquivos
#
# O que vale para todo som que o app toca. Antes eram dois blocos parecidos, um
# para o ambiente e outro para as reações, e a diferença entre eles não era
# decisão: era o que cada um tinha lembrado de conferir.


@pytest.mark.parametrize("nome,arquivo", ARQUIVOS, ids=[nome for nome, _ in ARQUIVOS])
def test_o_arquivo_esta_versionado(nome: str, arquivo: Path) -> None:
    """Um clone limpo tem que ter som sem rodar o gerador."""
    assert arquivo.is_file(), nome


@pytest.mark.parametrize("nome,arquivo", ARQUIVOS, ids=[nome for nome, _ in ARQUIVOS])
def test_o_formato_e_o_que_o_qsoundeffect_toca(nome: str, arquivo: Path) -> None:
    """PCM sem compressão, mono, 22 kHz.

    O `QSoundEffect` — que é quem toca as reações, porque mantém o som
    decodificado em memória — só aceita isso. O ambiente vai por `QMediaPlayer`
    e aceitaria mais, mas manter um formato só é o que faz o gerador ter uma
    saída só.
    """
    medida = medir(arquivo)
    assert medida.canais == 1
    assert medida.largura == 2
    assert medida.taxa == 22050


@pytest.mark.parametrize("nome,arquivo", ARQUIVOS, ids=[nome for nome, _ in ARQUIVOS])
def test_tem_som_e_nao_estoura(nome: str, arquivo: Path) -> None:
    medida = medir(arquivo)
    assert medida.pico < 0.95, f"{nome} está clipando"
    assert medida.pico > 0.2, f"{nome} está quase mudo"


# ---------------------------------------------------------------- o ambiente


@pytest.mark.parametrize("tema", TEMAS)
def test_o_ambiente_dura_o_loop_inteiro(tema: str) -> None:
    assert medir(caminho(tema)).duracao == pytest.approx(24.0, abs=0.1)


@pytest.mark.parametrize("tema", TEMAS)
def test_o_ambiente_fica_num_nivel_de_fundo(tema: str) -> None:
    """Alto demais deixa de ser ambiente; baixo demais é o mesmo que mudo."""
    rms = medir(caminho(tema)).rms
    assert 0.02 < rms < 0.3, f"nível estranho: rms={rms}"


@pytest.mark.parametrize("tema", TEMAS)
def test_a_volta_do_loop_nao_estala(tema: str) -> None:
    """O fim tem que desembocar no começo.

    Um degrau grande entre o último e o primeiro quadro vira um clique audível
    a cada volta, que num som que fica horas tocando é insuportável.
    """
    medida = medir(caminho(tema))
    assert medida.degrau_do_loop < 6 * medida.rms, (
        f"degrau de {medida.degrau_do_loop:.4f} contra rms {medida.rms:.4f}"
    )


@pytest.mark.parametrize("tema", TEMAS)
def test_nao_comeca_nem_termina_em_silencio(tema: str) -> None:
    """Silêncio nas pontas viraria um buraco a cada volta do loop."""
    medida = medir(caminho(tema))
    assert medida.rms_do_comeco > 0.01, f"começo silencioso demais: {medida.rms_do_comeco}"
    assert medida.rms_do_fim > 0.01, f"fim silencioso demais: {medida.rms_do_fim}"


def test_a_chuva_tem_mais_agudo_que_a_tarde() -> None:
    """A noite é chuva no vidro; a tarde é o ar da sala. Não podem se parecer."""
    noite = medir(caminho("noite")).energia_aguda
    tarde = medir(caminho("tarde")).energia_aguda
    assert noite > tarde * 1.5


def test_temas_diferentes_dao_arquivos_diferentes() -> None:
    assert caminho("noite").read_bytes() != caminho("tarde").read_bytes()


# ------------------------------------------------------- reações de interface


@pytest.mark.parametrize("nome", REACOES)
def test_reacao_e_curta(nome: str) -> None:
    """Som de UI que dura é som que atrapalha o que a pessoa está fazendo."""
    duracao = medir(caminho_reacao(nome)).duracao
    assert 0.02 < duracao < 1.2, f"{nome} dura {duracao:.2f}s"


@pytest.mark.parametrize("nome", REACOES)
def test_reacao_entra_e_sai_no_zero(nome: str) -> None:
    """Rampa nas duas pontas.

    Começar ou terminar com amplitude é um degrau na saída de áudio, e degrau
    é estalo. Num som que dispara a cada clique, isso apareceria o dia inteiro.
    """
    medida = medir(caminho_reacao(nome))
    assert abs(medida.primeira) < 0.02, "ataque seco no começo"
    assert abs(medida.ultima) < 0.02, "corte seco no fim"


# ------------------------------------------------------- o contrato do nome


@pytest.mark.parametrize("tema", TEMAS)
def test_o_servico_encontra_o_arquivo_do_tema(tema: str) -> None:
    """Se o gerador mudar de nome, o app fica mudo em silêncio. Não pode."""
    achado = audio._find((f"ambiente_{tema}", "ambiente"))
    assert achado is not None
    assert achado.name == f"ambiente_{tema}.wav"


@pytest.mark.parametrize("nome", REACOES)
def test_o_servico_encontra_a_reacao(nome: str) -> None:
    """Mesmo contrato do ambiente: nome errado deixa a UI muda sem avisar."""
    achado = audio._find((f"ui_{nome}",))
    assert achado is not None
    assert achado.name == f"ui_{nome}.wav"


def test_o_toque_e_mais_discreto_que_o_clique() -> None:
    """Passar o mouse tem que ficar abaixo de clicar, senão vira barulho."""
    assert audio.SFX_VOLUMES["toque"] < audio.SFX_VOLUMES["clique"]
    assert audio.SFX_VOLUMES["clique"] < audio.SFX_VOLUMES["entrega"]
