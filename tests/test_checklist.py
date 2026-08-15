"""O checklist que a suíte escolhe, conferido nos dois sistemas de dentro de um.

Esta é a peça que decide o que roda e o que nem é coletado, então um defeito
aqui não aparece como teste vermelho: aparece como teste **ausente**, que é o
jeito mais silencioso de uma suíte encolher. Daí ela ser função pura em
`checklist.py`, e daí este arquivo poder conferir o comportamento do Windows
rodando no Linux e vice-versa.
"""

from __future__ import annotations

import os

import pytest

from checklist import POSIX, SISTEMAS, WINDOWS, exclusivo_de, no_checklist, sistema_atual


def test_o_sistema_sai_de_os_name_e_nao_de_sys_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`sys.platform` é justamente o que os testes de plataforma fingem.

    Meia dúzia deles troca `sys.platform` com `monkeypatch` para exercitar o
    outro sistema. Se a coleta lesse dali, um teste mudaria o checklist da
    suíte inteira — e como a coleta acontece antes de qualquer fixture, o
    estrago seria intermitente e sem causa aparente.
    """
    monkeypatch.setattr("sys.platform", "win32")
    esperado = WINDOWS if os.name == "nt" else POSIX
    assert sistema_atual() == esperado


def test_o_sistema_e_um_dos_dois() -> None:
    assert sistema_atual() in SISTEMAS


def test_sem_marca_roda_em_qualquer_sistema() -> None:
    """O caso de quase toda a suíte: `core` não sabe onde está rodando."""
    for sistema in SISTEMAS:
        assert no_checklist(set(), sistema)
        assert no_checklist({"parametrize", "usefixtures"}, sistema)


@pytest.mark.parametrize("marca", SISTEMAS)
def test_com_marca_so_roda_no_sistema_dela(marca: str) -> None:
    outro = next(nome for nome in SISTEMAS if nome != marca)
    assert no_checklist({marca}, marca)
    assert not no_checklist({marca}, outro)


def test_a_marca_do_sistema_e_achada_entre_as_do_pytest() -> None:
    """`iter_markers` traz `parametrize` junto, e ela não é nome de sistema."""
    assert exclusivo_de({"parametrize", POSIX}) == POSIX
    assert exclusivo_de({"parametrize", "usefixtures"}) is None


@pytest.mark.posix
def test_a_marca_posix_so_e_coletada_no_posix() -> None:
    """A prova de ponta a ponta: se este rodar no Windows, a filtragem falhou."""
    assert os.name == "posix"


@pytest.mark.windows
def test_a_marca_windows_so_e_coletada_no_windows() -> None:
    """O par do de cima, e a razão de as duas marcas existirem.

    Hoje é o único teste exclusivo de Windows do repositório — o resto do que é
    de lá (`tools/atalho_windows.py`) é montagem de texto e roda nos dois. Ele
    fica porque a filtragem tem duas direções, e a direção que ninguém exercita
    é a que apodrece.
    """
    assert os.name == "nt"
