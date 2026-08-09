"""A variável de ambiente que impede o Qt Quick de subir.

Este é um teste de ambiente, não de lógica: o que ele protege é a decisão de
mexer no `os.environ` de quem roda o app — e principalmente os limites dela.
Apagar variável alheia demais é pior que o bug que motivou a limpeza.
"""

from __future__ import annotations

import os

import pytest

from cantinho.services.graphics import GL_INTEGRATION_VAR, ensure_gl_integration


@pytest.fixture
def no_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """A limpeza só existe no Linux; no Windows a variável é inerte."""
    monkeypatch.setattr("sys.platform", "linux")


def test_remove_o_none_herdado_do_conda(
    monkeypatch: pytest.MonkeyPatch, no_linux: None
) -> None:
    """`none` desliga a integração GL e o app morre ao abrir a primeira janela."""
    monkeypatch.setenv(GL_INTEGRATION_VAR, "none")
    assert ensure_gl_integration() is True
    assert GL_INTEGRATION_VAR not in os.environ


@pytest.mark.parametrize("valor", ["NONE", " none ", "None"])
def test_none_e_reconhecido_com_qualquer_grafia(
    monkeypatch: pytest.MonkeyPatch, no_linux: None, valor: str
) -> None:
    monkeypatch.setenv(GL_INTEGRATION_VAR, valor)
    assert ensure_gl_integration() is True
    assert GL_INTEGRATION_VAR not in os.environ


@pytest.mark.parametrize("valor", ["xcb_glx", "xcb_egl"])
def test_escolha_legitima_passa_intacta(
    monkeypatch: pytest.MonkeyPatch, no_linux: None, valor: str
) -> None:
    """Quem pediu GLX ou EGL de propósito continua com o que pediu.

    A limpeza é para um valor só. Tratá-la como "o app sabe melhor" tiraria de
    quem depura a única alavanca que tem para escolher a integração.
    """
    monkeypatch.setenv(GL_INTEGRATION_VAR, valor)
    assert ensure_gl_integration() is False
    assert os.environ[GL_INTEGRATION_VAR] == valor


def test_ambiente_limpo_fica_como_esta(
    monkeypatch: pytest.MonkeyPatch, no_linux: None
) -> None:
    monkeypatch.delenv(GL_INTEGRATION_VAR, raising=False)
    assert ensure_gl_integration() is False
    assert GL_INTEGRATION_VAR not in os.environ


def test_fora_do_linux_nao_mexe(monkeypatch: pytest.MonkeyPatch) -> None:
    """No Windows a variável não faz mal, e remexer nela seria à toa."""
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv(GL_INTEGRATION_VAR, "none")
    assert ensure_gl_integration() is False
    assert os.environ[GL_INTEGRATION_VAR] == "none"
