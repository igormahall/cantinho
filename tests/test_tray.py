"""A bandeja, e a notificação que ela dispara.

O ícone em si quase não é testável: em `offscreen` não existe bandeja nenhuma e
`install()` recusa na primeira linha. O que se confere aqui é o caminho da
notificação — qual dos dois é escolhido, e que nenhum deles explode quando o
sistema não colabora. Quem chama `notify` é um sinal que dispara sozinho depois
de duas horas de sessão, longe de qualquer clique que revelasse o erro.

Nenhum teste manda notificação de verdade: o `gdbus` é sempre substituído, para
a suíte não encher a tela de quem a roda.
"""

from __future__ import annotations

import subprocess

import pytest

from cantinho.services import tray as tray_mod
from cantinho.services.tray import DESKTOP_ENTRY, NOTIFY_MS, Tray


@pytest.fixture(scope="module")
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def gdbus(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Substitui o `gdbus` e guarda o que teria sido chamado."""
    chamadas: list[list[str]] = []

    def falso(cmd, **kwargs):  # type: ignore[no-untyped-def]
        chamadas.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, b"(uint32 1,)", b"")

    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(tray_mod.subprocess, "run", falso)
    return chamadas


def test_no_linux_o_balao_vai_pelo_desktop(gdbus: list[list[str]]) -> None:
    """E não pelo Qt, que entrega para a lista sem abrir balão no GNOME.

    Num aviso que existe para alcançar quem não está olhando para o app,
    chegar só na lista de notificações é o mesmo que não chegar.
    """
    assert Tray().notify("O abajur continua aceso.") is True

    assert len(gdbus) == 1
    comando = gdbus[0]
    assert comando[0] == "gdbus"
    assert "O abajur continua aceso." in comando
    assert str(NOTIFY_MS) in comando


def test_a_notificacao_se_apresenta_como_o_atalho(gdbus: list[list[str]]) -> None:
    """A dica `desktop-entry` é o que põe a planta no balão em vez do (i) azul,
    e o que faz clicar nele cair na trava de instância única, que traz a janela
    que já existe para a frente."""
    Tray().notify("A chuva não parou. Você parou?")

    comando = gdbus[0]
    assert DESKTOP_ENTRY in comando
    assert any("desktop-entry" in parte for parte in comando)


def test_notificacao_nunca_substitui_a_anterior(gdbus: list[list[str]]) -> None:
    """`replaces_id` é sempre 0: o toque das 2h30 não apaga o das 2h."""
    Tray().notify("O relógio ainda está correndo.")
    assert gdbus[0][gdbus[0].index("Cantinho") + 1] == "0"


def test_sem_gdbus_cai_no_caminho_do_qt(monkeypatch: pytest.MonkeyPatch, qt_app) -> None:
    """Sistema sem glib, ou sem serviço de notificação. Sem bandeja instalada
    aqui, o resultado é um False honesto — nunca uma exceção."""
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(
        tray_mod.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("gdbus")),
    )
    assert Tray().notify("O abajur continua aceso.") is False


def test_gdbus_que_recusa_cai_no_caminho_do_qt(
    monkeypatch: pytest.MonkeyPatch, qt_app
) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(
        tray_mod.subprocess,
        "run",
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, b"", b"sem servico"),
    )
    assert Tray().notify("O abajur continua aceso.") is False


def test_fora_do_linux_nem_tenta_o_dbus(
    monkeypatch: pytest.MonkeyPatch, qt_app
) -> None:
    """No Windows quem notifica é o Qt, e é o caminho certo lá: vira torrada da
    Central de Ações."""
    chamou = []
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(
        tray_mod.subprocess, "run", lambda *a, **k: chamou.append(a) or None
    )

    Tray().notify("O abajur continua aceso.")
    assert chamou == []


def test_esconder_sem_instalar_nao_explode(qt_app) -> None:
    Tray().hide()


def test_trocar_o_estagio_sem_instalar_nao_explode(qt_app) -> None:
    Tray().set_stage(3)


def test_o_balao_dura_o_mesmo_que_a_tira_da_janela() -> None:
    """Doze segundos, como o toque dentro do quarto.

    Vale como pedido e não como garantia — quem decide é o serviço de
    notificação do desktop —, mas o número não pode divergir do outro caminho
    sem motivo.
    """
    assert NOTIFY_MS == 12_000
