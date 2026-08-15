"""O atalho da Área de Trabalho, no Windows.

Não dá para criar um `.lnk` de verdade aqui — o `WScript.Shell` só existe lá.
O que se confere é o que este arquivo controla de fato: o comando que vai para
o PowerShell, e o comportamento fora do Windows.

Importa porque este é o último passo da instalação de quem não tem experiência
técnica. Se ele falhar em silêncio, a pessoa termina o roteiro inteiro e não
acha o programa em lugar nenhum.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import atalho_windows


PASTA = Path(r"C:\Users\alguem\Documents\cantinho")
LANCADOR = PASTA / ".venv" / "Scripts" / "pythonw.exe"
ICONE = PASTA / "assets" / "icon" / "cantinho.ico"


def test_o_comando_pergunta_ao_windows_onde_e_a_area_de_trabalho() -> None:
    """E não monta `%USERPROFILE%\\Desktop` na mão.

    Em português a pasta se chama "Área de Trabalho", e numa máquina com
    OneDrive corporativo ela costuma estar redirecionada para dentro do
    OneDrive — que é justamente o tipo de máquina a que isto se destina. O
    caminho montado à mão criaria o atalho numa pasta que ninguém vê.
    """
    script = atalho_windows.script_de_criacao(LANCADOR, PASTA, ICONE)
    assert "[Environment]::GetFolderPath('Desktop')" in script
    assert "Desktop'" not in script.replace("GetFolderPath('Desktop')", "")


def test_o_atalho_aponta_para_o_interpretador_assinado_e_nao_para_um_exe() -> None:
    """Esta é a correção inteira, e é o que o teste existe para segurar.

    O `Cantinho.exe` do PyInstaller nasce sem assinatura, e o Smart App Control
    recusa carregá-lo — o duplo clique não faz nada e não diz nada. O
    `pythonw.exe` do venv é cópia do binário da Python Software Foundation e
    carrega a assinatura dela. Um atalho que voltasse a apontar para um
    executável gerado aqui reintroduziria o defeito inteiro, e em silêncio.
    """
    script = atalho_windows.script_de_criacao(LANCADOR, PASTA, ICONE)
    assert f"$s.TargetPath = '{LANCADOR}'" in script
    assert "pythonw.exe" in script
    assert "Cantinho.exe" not in script


def test_o_atalho_leva_o_modulo_e_a_pasta_de_onde_importa_lo() -> None:
    """Com `-m`, o diretório de trabalho é também o `sys.path[0]`.

    Apontar para outro lugar produz um atalho que abre e morre com
    `ModuleNotFoundError`, sem terminal onde a mensagem apareça — o mesmo erro
    que o `Exec=` do `.desktop` já tinha cometido no Linux.
    """
    script = atalho_windows.script_de_criacao(LANCADOR, PASTA, ICONE)
    assert "$s.Arguments = '-m cantinho.main'" in script
    assert f"$s.WorkingDirectory = '{PASTA}'" in script
    assert f"$s.IconLocation = '{ICONE}'" in script
    assert "$s.Save()" in script


def test_o_icone_nao_vem_do_interpretador() -> None:
    """Senão o atalho na Área de Trabalho é o logo do Python, e não a planta."""
    script = atalho_windows.script_de_criacao(LANCADOR, PASTA, ICONE)
    assert f"$s.IconLocation = '{LANCADOR}'" not in script


def test_os_padroes_apontam_para_o_venv_desta_pasta() -> None:
    """Quem chama sem argumento — o `cantinho.bat` — tem que acertar sozinho."""
    raiz = atalho_windows.RAIZ
    assert atalho_windows.LANCADOR == raiz / ".venv" / "Scripts" / "pythonw.exe"
    assert atalho_windows.ICONE == raiz / "assets" / "icon" / "cantinho.ico"


def test_o_comando_de_remocao_nao_reclama_se_nao_ha_atalho() -> None:
    script = atalho_windows.script_de_remocao()
    assert "Test-Path" in script
    assert "Remove-Item" in script


@pytest.mark.parametrize("acao", ["instalar", "remover"])
def test_fora_do_windows_e_no_op(acao: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Como em `hotkey.py`: quem chama não precisa saber onde está rodando."""
    monkeypatch.setattr("sys.platform", "linux")
    chamou: list = []
    monkeypatch.setattr(
        atalho_windows, "_powershell", lambda s: chamou.append(s) or (True, "")
    )

    assert getattr(atalho_windows, acao)() is False
    assert chamou == []


def test_sem_ambiente_avisa_qual_comando_cria_ele(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A mensagem tem que dizer o comando, não só que faltou o arquivo: quem
    está seguindo o roteiro não sabe deduzir o passo que pulou."""
    monkeypatch.setattr("sys.platform", "win32")

    assert atalho_windows.instalar(tmp_path / "nao-existe.exe") is False
    assert "cantinho.bat instalar" in capsys.readouterr().out


def test_falha_do_powershell_nao_vira_excecao(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Roda no fim da instalação: falhar aqui não pode derrubar o que deu certo."""
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(
        atalho_windows, "_powershell", lambda s: (False, "politica de execucao")
    )
    lancador = tmp_path / "pythonw.exe"
    lancador.write_text("", encoding="utf-8")

    assert atalho_windows.instalar(lancador) is False
    assert "politica de execucao" in capsys.readouterr().out


def test_o_main_nao_falha_quando_o_atalho_nao_sai(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """O `cantinho.bat` chama isto no fim da instalação. Um atalho que não deu
    certo é um aviso, não uma instalação perdida."""
    monkeypatch.setattr("sys.platform", "linux")
    assert atalho_windows.main([]) == 0
