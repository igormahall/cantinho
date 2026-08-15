"""Põe o Cantinho na grade de aplicativos do Linux.

O app já cria o atalho sozinho na primeira abertura. Esta ferramenta existe
para os casos em que aquilo não basta:

- o repositório mudou de pasta e o `Exec=` do atalho aponta para o lugar
  antigo — `--de-novo` reescreve;
- você quer o atalho sem abrir o app;
- você quer o atalho fora do caminho — `--remover` leva junto o ícone.

O app nunca sobrescreve um atalho existente, então depois de mover o
repositório é aqui que se conserta.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# O Python põe no sys.path o diretório do script, não o diretório atual: sem
# isto, `import cantinho` falha mesmo rodando da raiz do repositório.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cantinho.services import desktop_entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="instalar_atalho",
        description="cria o atalho do Cantinho na grade de aplicativos",
    )
    parser.add_argument(
        "--de-novo",
        action="store_true",
        help="reescreve um atalho que já existe (use depois de mover o repositório)",
    )
    parser.add_argument(
        "--remover",
        action="store_true",
        help="apaga o atalho e o ícone",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if not sys.platform.startswith("linux"):
        print("atalho .desktop só existe no Linux; nada a fazer")
        return 0

    if args.remover:
        if desktop_entry.remove():
            print(f"atalho removido de {desktop_entry.entry_path()}")
        else:
            print("não havia atalho instalado")
        return 0

    criado = desktop_entry.install(force=args.de_novo)

    # Os ícones são reinstalados por `install` mesmo quando o atalho já existe:
    # são asset do app, não configuração do usuário. Por isso o relatório deles
    # vem antes de saber se o `.desktop` foi escrito.
    tamanhos = sorted(desktop_entry.installed_icons())
    if tamanhos:
        lista = ", ".join(f"{lado}x{lado}" for lado in tamanhos)
        print(f"ícone  em {desktop_entry.icon_path().parent.parent.parent}")
        print(f"       nos tamanhos {lista}")

    if criado:
        print(f"atalho em {desktop_entry.entry_path()}")
    else:
        print(f"o atalho já existe em {desktop_entry.entry_path()}")
        print("use --de-novo para reescrevê-lo, ou --remover para apagá-lo")

    print()
    print("pode levar alguns segundos para aparecer na grade de aplicativos")
    print("se o ícone continuar se comportando como antes, o GNOME está")
    print("servindo o atalho antigo da memória: Alt+F2, r, Enter recarrega")
    print("a interface no X11; no Wayland, é sair e entrar na sessão")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
