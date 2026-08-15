"""O atalho da grade de aplicativos.

O que estes testes protegem é a promessa de escrever pouco: dois arquivos, uma
vez, nunca por cima do que já existe. Um atalho errado falha do jeito mais
chato possível — ele aparece no menu e simplesmente não abre nada.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cantinho.services import desktop_entry


@pytest.fixture
def data_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Um `XDG_DATA_HOME` de mentira, para não escrever no menu de quem testa."""
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    return tmp_path


# A fixture finge o `sys.platform`, mas não dá para fingir o sistema de
# arquivos: o `pathlib` já escolheu `WindowsPath` na importação, e o `chmod` do
# Windows não tem bit de execução para ligar. O que estes três checam é
# semântica POSIX de verdade — separador `/` e permissão —, então no Windows
# eles falhariam mesmo com o código certo, que é o pior tipo de teste vermelho.
# Os demais deste arquivo são texto e escrita de arquivo, e rodam nos dois.
posix = pytest.mark.skipif(os.name != "posix", reason="depende de caminho e permissão POSIX")


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


@posix
def test_caminho_com_espaco_sai_citado(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`~/Documentos` já tem acento; espaço no caminho não é hipótese remota."""
    monkeypatch.setattr("sys.executable", "/home/eu/uma pasta/.venv/bin/python")
    linha = next(
        texto
        for texto in desktop_entry.desktop_entry_text().splitlines()
        if texto.startswith("Exec=")
    )
    assert '"/home/eu/uma pasta/.venv/bin/python"' in linha


@posix
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
        texto
        for texto in desktop_entry.desktop_entry_text().splitlines()
        if texto.startswith("Exec=")
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


@posix
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


# --------------------------------------------------------- o cache do ambiente


def test_avisa_o_ambiente_ao_instalar(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem este aviso o GNOME serve da memória e ignora o arquivo corrigido.

    Foi exatamente o que aconteceu: um `Exec=` errado ficou em cache, e clicar
    no ícone continuou falhando depois de o arquivo em disco já estar certo.
    """
    chamadas: list[list[str]] = []
    monkeypatch.setattr(desktop_entry.shutil, "which", lambda nome: f"/usr/bin/{nome}")
    monkeypatch.setattr(
        desktop_entry.subprocess, "run", lambda cmd, **k: chamadas.append(cmd)
    )

    desktop_entry.install()

    # São dois avisos, e o segundo faltava: o dos ícones. Sem ele, um tamanho
    # recém-instalado fica em disco e não é encontrado, porque o GTK continua
    # servindo o `icon-theme.cache` antigo.
    ferramentas = [chamada[0] for chamada in chamadas]
    assert "/usr/bin/update-desktop-database" in ferramentas
    assert "/usr/bin/gtk-update-icon-cache" in ferramentas

    atalhos = next(c for c in chamadas if c[0].endswith("update-desktop-database"))
    assert atalhos[1] == str(desktop_entry.entry_path().parent)

    # A raiz do tema: .../hicolor/<lado>x<lado>/apps/cantinho.png -> hicolor
    raiz = desktop_entry.icon_path().parent.parent.parent
    icones = next(c for c in chamadas if c[0].endswith("gtk-update-icon-cache"))
    assert str(raiz) in icones


def test_sem_a_ferramenta_o_atalho_ainda_e_criado(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`desktop-file-utils` pode não estar instalado; isso não impede nada."""
    monkeypatch.setattr(desktop_entry.shutil, "which", lambda _: None)

    assert desktop_entry.install() is True
    assert desktop_entry.entry_path().is_file()


def test_ferramenta_quebrada_nao_derruba_a_instalacao(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_args: object, **_kwargs: object) -> None:
        raise OSError("sem permissão")

    monkeypatch.setattr(desktop_entry.shutil, "which", lambda _: "/usr/bin/upd")
    monkeypatch.setattr(desktop_entry.subprocess, "run", explode)

    assert desktop_entry.install() is True
    assert desktop_entry.entry_path().is_file()


# ------------------------------------------------------------ outros sistemas


def test_no_windows_e_no_op(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Como em `hotkey.py`: o resto do app não precisa saber onde está rodando."""
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert desktop_entry.install() is False
    assert desktop_entry.remove() is False
    assert not (tmp_path / "applications").exists()


# ------------------------------------------------------- os tamanhos do ícone
#
# O defeito: só o 256 era instalado, e o ambiente reduzia esse arquivo único
# para os 22-24 px da bandeja e os 48-64 do dock. A arte do 256 é a planta
# sobre um ladrilho escuro — reduzida a 24 px vira um quadrado escuro com um
# borrão dentro, que na barra do Ubuntu lê como ícone genérico. No Windows
# nunca apareceu porque lá o `.ico` entrega os sete tamanhos.


def test_instala_todos_os_tamanhos_do_ico(data_home: Path) -> None:
    from cantinho.services import scene

    tamanhos = desktop_entry.install_icons()

    esperados = sorted(
        desktop_entry._quadros_do_ico(
            (scene.assets_dir() / "icon" / "cantinho.ico").read_bytes()
        )
    )
    assert tamanhos == esperados
    # E não é só um: se voltar a ser, o defeito voltou.
    assert len(tamanhos) > 1
    assert 256 in tamanhos
    assert min(tamanhos) <= 32, "falta tamanho pequeno, que é onde o defeito doía"

    for lado in tamanhos:
        assert desktop_entry.icon_path(lado).is_file()


def test_os_bytes_sao_os_mesmos_do_windows(data_head: None = None) -> None:
    """O Linux instala literalmente os quadros do `.ico`, não uma reamostragem.

    É o que faz "igual ao que aparece no Windows" ser verdade e não aproximação:
    os dois sistemas leem o mesmo desenho, feito para aquele tamanho.
    """
    from cantinho.services import scene

    bruto = (scene.assets_dir() / "icon" / "cantinho.ico").read_bytes()
    quadros = desktop_entry._quadros_do_ico(bruto)
    assert quadros, "o .ico não entregou quadro nenhum"
    for dados in quadros.values():
        assert dados.startswith(b"\x89PNG\r\n\x1a\n")


def test_o_icone_e_reparado_com_o_atalho_ja_no_lugar(data_home: Path) -> None:
    """**A parte que fazia a correção não chegar em quem já tinha instalado.**

    `install` sai cedo quando o `.desktop` existe, e antes o ícone saía junto —
    então uma instalação antiga jamais ganharia os tamanhos que faltam. A regra
    de "criar uma vez e nunca sobrescrever" protege o `Exec=`; o ícone é asset
    do app e ninguém o edita à mão.
    """
    assert desktop_entry.install() is True

    # Simula a instalação antiga: só o 256 em disco.
    for lado, caminho in desktop_entry.installed_icons().items():
        if lado != 256:
            caminho.unlink()
    assert list(desktop_entry.installed_icons()) == [256]

    # O atalho continua lá, então `install` devolve False — e mesmo assim
    # reinstala os ícones.
    assert desktop_entry.install() is False
    assert len(desktop_entry.installed_icons()) > 1


def test_remover_leva_todos_os_tamanhos(data_home: Path) -> None:
    desktop_entry.install()
    assert len(desktop_entry.installed_icons()) > 1

    assert desktop_entry.remove() is True
    assert desktop_entry.installed_icons() == {}


def test_ico_ilegivel_nao_derruba_a_instalacao(
    data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem o `.ico`, o 256 sozinho ainda é melhor que ícone nenhum."""
    monkeypatch.setattr(desktop_entry, "_source_ico", lambda: None)

    tamanhos = desktop_entry.install_icons()
    assert tamanhos == [256]
    assert desktop_entry.icon_path().is_file()


@pytest.mark.parametrize(
    "bruto",
    [b"", b"xx", b"\x00\x00\x02\x00\x01\x00", b"\x00\x00\x01\x00\xff\xff"],
    ids=["vazio", "curto demais", "tipo errado", "conta mais do que tem"],
)
def test_ico_malformado_devolve_vazio_em_vez_de_estourar(bruto: bytes) -> None:
    """Um `.ico` de outra procedência não pode derrubar a abertura do app."""
    assert desktop_entry._quadros_do_ico(bruto) == {}
