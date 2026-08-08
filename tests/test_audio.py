"""Os loops de ambiente.

Os arquivos são sintetizados por `tools/gerar_audio.py` e versionados prontos,
para que o app funcione num clone limpo sem etapa extra de build. Estes testes
seguram o contrato entre o gerador e `services/audio.py`.
"""

from __future__ import annotations

import array
import math
import wave
from pathlib import Path

import pytest

from cantinho.services import audio, scene

TEMAS = ("noite", "tarde")


def caminho(tema: str) -> Path:
    return scene.assets_dir() / "audio" / f"ambiente_{tema}.wav"


def amostras(tema: str) -> tuple[int, list[float]]:
    with wave.open(str(caminho(tema))) as arquivo:
        taxa = arquivo.getframerate()
        dados = array.array("h")
        dados.frombytes(arquivo.readframes(arquivo.getnframes()))
    return taxa, [v / 32768.0 for v in dados]


@pytest.mark.parametrize("tema", TEMAS)
def test_o_arquivo_do_tema_existe(tema: str) -> None:
    assert caminho(tema).is_file()


@pytest.mark.parametrize("tema", TEMAS)
def test_formato_esperado(tema: str) -> None:
    with wave.open(str(caminho(tema))) as arquivo:
        assert arquivo.getnchannels() == 1
        assert arquivo.getsampwidth() == 2
        assert arquivo.getframerate() == 22050
        assert arquivo.getnframes() / arquivo.getframerate() == pytest.approx(24.0, abs=0.1)


@pytest.mark.parametrize("tema", TEMAS)
def test_tem_som_e_nao_estoura(tema: str) -> None:
    _, valores = amostras(tema)
    pico = max(abs(v) for v in valores)
    rms = math.sqrt(sum(v * v for v in valores) / len(valores))
    assert 0.02 < rms < 0.3, f"nível estranho: rms={rms}"
    assert pico < 0.95, "está clipando"
    assert pico > 0.2, "está quase mudo"


@pytest.mark.parametrize("tema", TEMAS)
def test_a_volta_do_loop_nao_estala(tema: str) -> None:
    """O fim tem que desembocar no começo.

    Um degrau grande entre o último e o primeiro quadro vira um clique audível
    a cada volta, que num som que fica horas tocando é insuportável.
    """
    _, valores = amostras(tema)
    rms = math.sqrt(sum(v * v for v in valores) / len(valores))
    degrau = abs(valores[-1] - valores[0])
    assert degrau < 6 * rms, f"degrau de {degrau:.4f} contra rms {rms:.4f}"


@pytest.mark.parametrize("tema", TEMAS)
def test_nao_comeca_nem_termina_em_silencio(tema: str) -> None:
    """Silêncio nas pontas viraria um buraco a cada volta do loop."""
    _, valores = amostras(tema)
    janela = 2000
    for nome, trecho in (("começo", valores[:janela]), ("fim", valores[-janela:])):
        rms = math.sqrt(sum(v * v for v in trecho) / len(trecho))
        assert rms > 0.01, f"{nome} silencioso demais: {rms}"


def test_a_chuva_tem_mais_agudo_que_a_tarde() -> None:
    """A noite é chuva no vidro; a tarde é o ar da sala. Não podem se parecer."""

    def energia_aguda(tema: str) -> float:
        taxa, valores = amostras(tema)
        rc = 1.0 / (2 * math.pi * 1500.0)
        dt = 1.0 / taxa
        a = dt / (rc + dt)
        y = 0.0
        agudo = total = 0.0
        for x in valores:
            y += a * (x - y)
            agudo += (x - y) ** 2
            total += x * x
        return agudo / (total or 1.0)

    assert energia_aguda("noite") > energia_aguda("tarde") * 1.5


@pytest.mark.parametrize("tema", TEMAS)
def test_o_servico_encontra_o_arquivo_do_tema(tema: str) -> None:
    """Se o gerador mudar de nome, o app fica mudo em silêncio. Não pode."""
    achado = audio._find((f"ambiente_{tema}", "ambiente"))
    assert achado is not None
    assert achado.name == f"ambiente_{tema}.wav"


def test_temas_diferentes_dao_arquivos_diferentes() -> None:
    assert caminho("noite").read_bytes() != caminho("tarde").read_bytes()
