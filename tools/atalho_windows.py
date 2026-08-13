"""Atalho do Cantinho na Área de Trabalho, no Windows.

O irmão Windows de `cantinho/services/desktop_entry.py`, e mora em `tools/`
porque a diferença é quando cada um roda: o `.desktop` do Linux é criado pelo
app na primeira abertura, e este aqui é passo de instalação — só existe algo
para apontar depois que `dist\\Cantinho\\Cantinho.exe` foi gerado.

    python tools/atalho_windows.py            # cria (ou atualiza) o atalho
    python tools/atalho_windows.py --remover   # tira o atalho

Fora do Windows é no-op, como o `hotkey.py`: quem chama não precisa saber onde
está rodando.

## Por que PowerShell

Um `.lnk` não é texto — é um formato binário com um cabeçalho de 76 bytes e uma
lista de estruturas encadeadas. Escrevê-lo à mão daria mais código do que o app
inteiro tem de integração com sistema, e o `pywin32`, que resolveria numa
linha, é dependência nova. O `WScript.Shell` faz isso desde sempre e já está em
qualquer Windows.

A chamada vai por `-Command` e não por arquivo `.ps1` de propósito: em máquina
gerenciada a política de execução costuma vir como `Restricted`, que bloqueia
**script em arquivo** e continua deixando passar comando na linha. A máquina de
destino deste projeto é exatamente esse tipo de máquina.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EXECUTAVEL = RAIZ / "dist" / "Cantinho" / "Cantinho.exe"
NOME_DO_ATALHO = "Cantinho.lnk"

__all__ = ["instalar", "remover", "script_de_criacao", "script_de_remocao"]


def _powershell(script: str) -> tuple[bool, str]:
    """Roda um comando no PowerShell. Devolve (deu certo, saída)."""
    try:
        resultado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        return False, str(erro)
    saida = (resultado.stdout or "").strip() or (resultado.stderr or "").strip()
    return resultado.returncode == 0, saida


def script_de_criacao(executavel: Path, nome: str = NOME_DO_ATALHO) -> str:
    """O comando que cria o atalho.

    A pasta da Área de Trabalho **não** é montada como `%USERPROFILE%\\Desktop`.
    Em português ela se chama "Área de Trabalho", e numa máquina com OneDrive
    corporativo ela costuma estar redirecionada para dentro do OneDrive — que é
    justamente o caso da máquina de trabalho a que este projeto se destina.
    `GetFolderPath` pergunta ao Windows onde ela está de verdade.
    """
    pasta = executavel.parent
    return (
        "$mesa = [Environment]::GetFolderPath('Desktop'); "
        f"$alvo = Join-Path $mesa '{nome}'; "
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($alvo); "
        f"$s.TargetPath = '{executavel}'; "
        f"$s.WorkingDirectory = '{pasta}'; "
        f"$s.IconLocation = '{executavel}'; "
        "$s.Description = 'Cantinho'; "
        "$s.Save(); "
        "Write-Output $alvo"
    )


def script_de_remocao(nome: str = NOME_DO_ATALHO) -> str:
    return (
        "$mesa = [Environment]::GetFolderPath('Desktop'); "
        f"$alvo = Join-Path $mesa '{nome}'; "
        "if (Test-Path $alvo) { Remove-Item $alvo; Write-Output $alvo } "
        "else { Write-Output 'nada' }"
    )


def instalar(executavel: Path | None = None) -> bool:
    """Cria o atalho. Devolve False quando não havia o que fazer."""
    if not sys.platform.startswith("win"):
        print("atalho na Área de Trabalho: só no Windows, nada a fazer aqui.")
        return False

    alvo = executavel or EXECUTAVEL
    if not alvo.is_file():
        print(f"não achei o executável em {alvo}")
        print("gere ele antes com:  cantinho.bat empacotar")
        return False

    deu_certo, saida = _powershell(script_de_criacao(alvo))
    if not deu_certo:
        print("não deu para criar o atalho:")
        print(f"  {saida}")
        return False

    print(f"atalho criado: {saida}")
    return True


def remover() -> bool:
    if not sys.platform.startswith("win"):
        print("atalho na Área de Trabalho: só no Windows, nada a fazer aqui.")
        return False

    deu_certo, saida = _powershell(script_de_remocao())
    if not deu_certo:
        print("não deu para remover o atalho:")
        print(f"  {saida}")
        return False

    print("atalho removido." if saida != "nada" else "não havia atalho.")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atalho_windows",
        description="Cria o atalho do Cantinho na Área de Trabalho (Windows).",
    )
    parser.add_argument(
        "--remover", action="store_true", help="tira o atalho em vez de criar"
    )
    args = parser.parse_args(argv)

    if args.remover:
        return 0 if remover() else 1
    # Criar é o caminho da instalação, e ele roda junto do build: falhar aqui
    # não pode derrubar um `empacotar` que deu certo. O `cantinho.bat` ignora
    # este código de saída de propósito.
    instalar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
