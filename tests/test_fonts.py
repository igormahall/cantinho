"""As fontes embutidas.

O que se prova aqui é que o app **tem** tipografia própria — antes disto ele
não definia fonte em lugar nenhum e herdava a do sistema, o que fazia dele um
programa diferente em cada uma das duas máquinas do projeto.
"""

from __future__ import annotations

import pytest

from cantinho.services import fonts


@pytest.fixture(scope="module")
def qt_app() -> object:
    """Uma aplicação Qt, como em `test_scene.py` e `test_icone.py`.

    O `QFontDatabase` precisa de aplicação viva para registrar fonte.
    """
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication([])


def test_os_arquivos_estao_versionados() -> None:
    """Clone limpo tem que ter fonte, sem etapa de build."""
    for nome in fonts.ARQUIVOS:
        caminho = fonts.fonts_dir() / nome
        assert caminho.is_file(), f"falta {caminho}"
        assert caminho.stat().st_size > 10_000


def test_a_licenca_vai_junto() -> None:
    """SIL OFL 1.1 exige a licença junto do arquivo redistribuído."""
    licencas = sorted(fonts.fonts_dir().glob("OFL-*.txt"))
    assert len(licencas) == len(fonts.ARQUIVOS)
    for licenca in licencas:
        assert "SIL OPEN FONT LICENSE" in licenca.read_text(encoding="utf-8").upper()


def test_o_qt_aceita_as_duas_familias(qt_app: object) -> None:
    familias = fonts.load_fonts()
    assert fonts.FONTE_UI in familias
    assert fonts.FONTE_PAPEL in familias


def test_a_fonte_da_interface_tem_algarismos_tabulares(qt_app: object) -> None:
    """**O cronômetro depende disto.**

    Por padrão os algarismos da Inter são proporcionais — o "1" é mais estreito
    que o "0" —, então `00:00` e `11:11` teriam larguras diferentes e o relógio
    se mexeria a cada segundo. O `tnum` iguala os dez. O QML aplica por
    `Theme.digitos`; aqui se prova que a fonte de fato oferece o recurso.
    """
    from PySide6.QtGui import QFont, QFontMetricsF

    fonts.load_fonts()

    solto = QFont(fonts.FONTE_UI)
    solto.setPixelSize(30)
    larguras_soltas = {QFontMetricsF(solto).horizontalAdvance(d) for d in "0123456789"}

    tabular = QFont(fonts.FONTE_UI)
    tabular.setPixelSize(30)
    tabular.setFeature(QFont.Tag("tnum"), 1)
    metrica = QFontMetricsF(tabular)
    larguras_tabulares = {metrica.horizontalAdvance(d) for d in "0123456789"}

    # A premissa do problema: sem `tnum` os algarismos divergem mesmo.
    assert len(larguras_soltas) > 1
    # E a solução: com ele, todos medem igual.
    assert len(larguras_tabulares) == 1
    assert metrica.horizontalAdvance("00:00") == metrica.horizontalAdvance("11:11")


def test_load_fonts_sem_arquivos_nao_quebra(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fonte que falta piora a aparência e não impede o app de abrir."""
    from pathlib import Path

    monkeypatch.setattr(fonts, "fonts_dir", lambda: Path("/nao/existe"))
    assert fonts.load_fonts() == []
