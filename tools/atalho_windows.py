"""Atalho do Cantinho na Área de Trabalho, no Windows.

O irmão Windows de `cantinho/services/desktop_entry.py`, e mora em `tools/`
porque a diferença é quando cada um roda: o `.desktop` do Linux é criado pelo
app na primeira abertura, e este aqui é passo de instalação.

    python tools/atalho_windows.py            # cria (ou refaz) o atalho
    python tools/atalho_windows.py --remover   # tira o atalho

Fora do Windows é no-op, como o `hotkey.py`: quem chama não precisa saber onde
está rodando.

## Para onde o atalho aponta, e por quê

Para `.venv\\Scripts\\pythonw.exe -m cantinho.main`, com a raiz do repositório
como diretório de trabalho. **Não** para um executável gerado aqui.

O `pythonw.exe` do venv é uma cópia do binário oficial da Python Software
Foundation e carrega a assinatura dela — `Get-AuthenticodeSignature` responde
`Valid`, com `CN=Python Software Foundation`. O `Cantinho.exe` do PyInstaller
não tem assinatura nenhuma, e nesta máquina o **Smart App Control** recusa
carregá-lo: eventos 3033 e 3077 no log `Microsoft-Windows-CodeIntegrity`,
disparados pelo `explorer.exe`, ou seja, pelo duplo clique. Rebuildar não
resolve, porque o problema não é o build — é que todo binário novo nasce sem
assinatura e sem reputação.

É a mesma estratégia do `tools/empacotar_portatil.py`, aplicada onde o
repositório já está clonado: em vez de construir um binário que precisa se
justificar, roda-se o interpretador que já vem justificado. A diferença é que
lá o runtime é baixado do python.org, e aqui ele já existe no venv.

O `pythonw.exe` (e não o `python.exe`) é o que abre sem janela de console.

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
LANCADOR = RAIZ / ".venv" / "Scripts" / "pythonw.exe"
ICONE = RAIZ / "assets" / "icon" / "cantinho.ico"
ARGUMENTOS = "-m cantinho.main"
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


def script_de_criacao(
    lancador: Path,
    pasta: Path | None = None,
    icone: Path | None = None,
    nome: str = NOME_DO_ATALHO,
) -> str:
    """O comando que cria o atalho.

    A pasta da Área de Trabalho **não** é montada como `%USERPROFILE%\\Desktop`.
    Em português ela se chama "Área de Trabalho", e numa máquina com OneDrive
    corporativo ela costuma estar redirecionada para dentro do OneDrive — que é
    justamente o caso da máquina de trabalho a que este projeto se destina.
    `GetFolderPath` pergunta ao Windows onde ela está de verdade.

    `pasta` é o diretório de trabalho, e com `-m` ele é também de onde o pacote
    `cantinho` é importado: apontar para outro lugar produz um atalho que abre e
    morre com `ModuleNotFoundError`, sem terminal onde reclamar. O ícone vem do
    asset, porque o interpretador não tem o desenho do app dentro dele.
    """
    pasta = pasta or RAIZ
    icone = icone or ICONE
    return (
        "$mesa = [Environment]::GetFolderPath('Desktop'); "
        f"$alvo = Join-Path $mesa '{nome}'; "
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($alvo); "
        f"$s.TargetPath = '{lancador}'; "
        f"$s.Arguments = '{ARGUMENTOS}'; "
        f"$s.WorkingDirectory = '{pasta}'; "
        f"$s.IconLocation = '{icone}'; "
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


def instalar(lancador: Path | None = None) -> bool:
    """Cria o atalho. Devolve False quando não havia o que fazer.

    Diferente do `.desktop` do Linux, aqui **refazer é o certo**. Lá a regra é
    criar uma vez e nunca sobrescrever, porque qualquer clone de teste poderia
    sequestrar o atalho do menu apontando para si; aqui quem chama é a
    instalação, a pedido, e o alvo é o venv desta pasta — que é exatamente o que
    precisa ser corrigido quando a pasta muda de lugar ou o ambiente é refeito.
    """
    if not sys.platform.startswith("win"):
        print("atalho na Área de Trabalho: só no Windows, nada a fazer aqui.")
        return False

    alvo = lancador or LANCADOR
    if not alvo.is_file():
        print(f"não achei o interpretador do venv em {alvo}")
        print("crie o ambiente antes com:  cantinho.bat instalar")
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
    # Criar é o último passo da instalação, e falhar aqui não pode derrubar uma
    # instalação que deu certo: sem atalho o app ainda abre pelo `cantinho.bat`.
    # O `cantinho.bat` ignora este código de saída de propósito.
    instalar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
