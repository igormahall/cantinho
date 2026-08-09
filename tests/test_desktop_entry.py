"""O atalho da grade de aplicativos.

O que estes testes protegem é a promessa de escrever pouco: dois arquivos, uma
vez, nunca por cima do que já existe. Um atalho errado falha do jeito mais
chato possível — ele aparece no menu e simplesmente não abre nada.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cantinho.services import desktop_entry


@pytest.fixture
def data_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Um `XDG_DATA_HOME` de mentira, para não escrever no menu de quem testa."""
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------- o conteúdo


def test_o_atalho_tem_o_que_o_gnome_exige(data_home: Path) -> None:
    texto = desktop_entry.desktop_entry_text()
    for chave in ("[Desktop Entry]", "Type=Application", "Name=Cantinho", "Exec="):
        assert chave in texto


def test_nao_carrega_o_db_de_teste_para_dentro_do_atalho(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Um atalho permanente apontando para banco descartável é a pior herança.

    O `--db` existe para experimentar; se ele vazasse para o `Exec=`, o ícone
    do menu abriria para sempre num banco de teste sem nada dizer.
    """
    monkeypatch.setattr("sys.argv", ["cantinho", "--db", "/tmp/descartavel.db"])
    texto = desktop_entry.desktop_entry_text()
    assert "--db" not in texto
    assert "descartavel" not in texto


def test_caminho_com_espaco_sai_citado(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`~/Documentos` já tem acento; espaço no caminho não é hipótese remota."""
    monkeypatch.setattr("sys.executable", "/home/eu/uma pasta/.venv/bin/python")
    linha = next(
        l for l in desktop_entry.desktop_entry_text().splitlines() if l.startswith("Exec=")
    )
    assert '"/home/eu/uma pasta/.venv/bin/python"' in linha


def test_o_venv_sobrevive_ao_atalho(
    data_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """O `Exec=` guarda o Python do venv, não o alvo do symlink.

    `.venv/bin/python` é um link para o Python do sistema, que não tem
    PySide6. Resolver esse link desfaz o venv, e o estrago é silencioso do
    pior jeito: o atalho aparece na grade, abre, e morre com
    `ModuleNotFoundError` sem nenhum terminal onde reclamar.
    """
    real = tmp_path / "python3.10"
    real.write_text("#!/bin/sh\n")
    venv = tmp_path / "python"
    venv.symlink_to(real)
    monkeypatch.setattr("sys.executable", str(venv))

    linha = next(
        l for l in desktop_entry.desktop_entry_text().splitlines() if l.startswith("Exec=")
    )
    assert str(venv) in linha
    assert str(real) not in linha


def test_a_janela_casa_com_o_atalho(data_home: Path) -> None:
    """Sem `StartupWMClass` a janela vira um segundo ícone, genérico, na barra."""
    assert "StartupWMClass=Cantinho" in desktop_entry.desktop_entry_text()


# ------------------------------------------------------------------ escrita


def test_instala_atalho_e_icone(data_home: Path) -> None:
    assert desktop_entry.install() is True
    assert desktop_entry.entry_path().is_file()
    assert desktop_entry.icon_path().is_file()


def test_o_atalho_e_executavel(data_home: Path) -> None:
    """Sem o bit de execução o GNOME marca o atalho como não confiável."""
    desktop_entry.install()
    assert desktop_entry.entry_path().stat().st_mode & 0o111


def test_nao_sobrescreve_o_que_ja_existe(data_home: Path) -> None:
    """A regra que impede um clone de teste de roubar o atalho do menu."""
    desktop_entry.install()
    desktop_entry.entry_path().write_text("editado à mão\n", encoding="utf-8")

    assert desktop_entry.ensure_installed() is False
    assert desktop_entry.entry_path().read_text(encoding="utf-8") == "editado à mão\n"


def test_de_novo_reescreve(data_home: Path) -> None:
    """É o conserto de quem moveu o repositório de pasta."""
    desktop_entry.install()
    desktop_entry.entry_path().write_text("velho\n", encoding="utf-8")

    assert desktop_entry.install(force=True) is True
    assert "[Desktop Entry]" in desktop_entry.entry_path().read_text(encoding="utf-8")


def test_remover_leva_o_icone_junto(data_home: Path) -> None:
    desktop_entry.install()

    assert desktop_entry.remove() is True
    assert not desktop_entry.entry_path().exists()
    assert not desktop_entry.icon_path().exists()


def test_remover_sem_nada_instalado_nao_reclama(data_home: Path) -> None:
    assert desktop_entry.remove() is False


# ------------------------------------------------------------ outros sistemas


def test_no_windows_e_no_op(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Como em `hotkey.py`: o resto do app não precisa saber onde está rodando."""
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert desktop_entry.install() is False
    assert desktop_entry.remove() is False
    assert not (tmp_path / "applications").exists()
