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

from tools import atalho_windows  # noqa: E402


EXE = Path(r"C:\Users\alguem\Documents\cantinho\dist\Cantinho\Cantinho.exe")


def test_o_comando_pergunta_ao_windows_onde_e_a_area_de_trabalho() -> None:
    """E não monta `%USERPROFILE%\\Desktop` na mão.

    Em português a pasta se chama "Área de Trabalho", e numa máquina com
    OneDrive corporativo ela costuma estar redirecionada para dentro do
    OneDrive — que é justamente o tipo de máquina a que isto se destina. O
    caminho montado à mão criaria o atalho numa pasta que ninguém vê.
    """
    script = atalho_windows.script_de_criacao(EXE)
    assert "[Environment]::GetFolderPath('Desktop')" in script
    assert "Desktop'" not in script.replace("GetFolderPath('Desktop')", "")


def test_o_atalho_aponta_para_o_executavel_e_para_a_pasta_dele() -> None:
    """Sem `WorkingDirectory`, o app abre com o diretório de trabalho errado."""
    script = atalho_windows.script_de_criacao(EXE)
    assert f"$s.TargetPath = '{EXE}'" in script
    assert f"$s.WorkingDirectory = '{EXE.parent}'" in script
    assert f"$s.IconLocation = '{EXE}'" in script
    assert "$s.Save()" in script


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


def test_sem_executavel_avisa_onde_gerar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A mensagem tem que dizer o comando, não só que faltou o arquivo: quem
    está seguindo o roteiro não sabe deduzir o passo que pulou."""
    monkeypatch.setattr("sys.platform", "win32")

    assert atalho_windows.instalar(tmp_path / "nao-existe.exe") is False
    assert "cantinho.bat empacotar" in capsys.readouterr().out


def test_falha_do_powershell_nao_vira_excecao(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Roda junto do build: falhar aqui não pode derrubar um build que deu certo."""
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr(
        atalho_windows, "_powershell", lambda s: (False, "politica de execucao")
    )
    exe = tmp_path / "Cantinho.exe"
    exe.write_text("", encoding="utf-8")

    assert atalho_windows.instalar(exe) is False
    assert "politica de execucao" in capsys.readouterr().out


def test_o_main_nao_falha_quando_o_atalho_nao_sai(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """O `cantinho.bat` chama isto depois do build. Um atalho que não deu
    certo é um aviso, não um build perdido."""
    monkeypatch.setattr("sys.platform", "linux")
    assert atalho_windows.main([]) == 0
