"""O atalho do Linux, na grade de aplicativos.

Um `.desktop` em `~/.local/share/applications` é o que faz o app aparecer na
tela inicial do GNOME, ser fixável na barra e abrir sem terminal. É a única
parte do projeto que escreve fora da pasta de dados, e por isso escreve pouco:
dois arquivos, uma vez, e nunca por cima do que já existe.

**Criar uma vez e nunca sobrescrever** é a regra que sustenta o resto. O
alternativa — revalidar o `Exec=` a cada abertura — sobreviveria a mover o
repositório sozinha, mas daria a qualquer clone de teste o poder de roubar o
atalho do menu apontando para si. Aqui, quem chegou primeiro fica; para mudar
de ideia existe `tools/instalar_atalho.py --de-novo`.

Windows e macOS não têm nada disto e todas as funções viram no-op, como em
`hotkey.py`: o resto do app não precisa saber em que sistema está.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "ENTRY_NAME",
    "ICON_NAME",
    "entry_path",
    "icon_path",
    "desktop_entry_text",
    "install",
    "ensure_installed",
    "remove",
]

ENTRY_NAME = "cantinho.desktop"
ICON_NAME = "cantinho"

# O tamanho em que o ícone é versionado. Uma pasta só: o `hicolor` aceita um
# tamanho isolado, e o app não tem arte de ícone em mais nenhum.
_ICON_SIZE = "256x256"


def _data_home() -> Path:
    """`XDG_DATA_HOME`, com o padrão da especificação quando ela não está posta."""
    bruto = os.environ.get("XDG_DATA_HOME")
    if bruto:
        return Path(bruto)
    return Path.home() / ".local" / "share"


def entry_path() -> Path:
    return _data_home() / "applications" / ENTRY_NAME


def icon_path() -> Path:
    return _data_home() / "icons" / "hicolor" / _ICON_SIZE / "apps" / f"{ICON_NAME}.png"


def _quote(argumento: str) -> str:
    """Cita um argumento do `Exec=` como a especificação manda.

    Caminho com espaço não é hipótese remota: o repositório vive em
    `~/Documentos`, e uma pasta com acento ou espaço no caminho quebraria a
    linha inteira em silêncio — o atalho apareceria no menu e não abriria nada.
    """
    escapado = argumento.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escapado}"'


def _launch_command() -> tuple[str, Path | None]:
    """A linha de `Exec=` e o diretório de trabalho, conforme como o app roda.

    São dois modos. Empacotado pelo PyInstaller, `sys.executable` já é o
    próprio Cantinho e basta. Rodando do repositório, é o Python do venv com
    `-m cantinho.main` — e aí o diretório de trabalho importa, porque é dele
    que sai o `cantinho` no `sys.path`.
    """
    # `sys.executable` já é absoluto, e **não** se resolve o symlink: o
    # `.venv/bin/python` aponta para o Python do sistema, e seguir esse link
    # entrega um interpretador sem PySide6. O atalho apareceria no menu e
    # morreria com `ModuleNotFoundError`, sem terminal onde reclamar.
    executavel = Path(sys.executable)

    if getattr(sys, "frozen", False):
        return _quote(str(executavel)), None

    raiz = Path(__file__).resolve().parents[2]
    return f"{_quote(str(executavel))} -m cantinho.main", raiz


def desktop_entry_text() -> str:
    """O conteúdo do `.desktop`.

    Sem `--db` e sem `--device-id`, mesmo que a sessão atual tenha usado os
    dois: são flags de teste, e um atalho permanente apontando para um banco
    descartável seria a pior herança possível de uma execução de experimento.
    """
    exec_line, working_dir = _launch_command()

    linhas = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Cantinho",
        "Comment=Um cômodo ilustrado que fica aberto enquanto você trabalha",
        f"Exec={exec_line}",
        f"Icon={ICON_NAME}",
        "Terminal=false",
        "Categories=Utility;",
        # Casa a janela com este atalho na barra do GNOME. Sem isto a janela
        # aberta aparece como um segundo ícone, genérico, ao lado do atalho.
        "StartupWMClass=Cantinho",
    ]
    if working_dir is not None:
        linhas.insert(-1, f"Path={working_dir}")

    return "\n".join(linhas) + "\n"


def _source_icon() -> Path | None:
    # Importado aqui e não no topo: `scene` carrega Qt, e este módulo é
    # chamado antes de a aplicação existir.
    from cantinho.services import scene

    origem = scene.assets_dir() / "icon" / f"{ICON_NAME}.png"
    return origem if origem.is_file() else None


def _refresh_desktop_database() -> None:
    """Avisa o ambiente que a pasta de atalhos mudou.

    Sem isto o GNOME Shell continua servindo o que tinha em memória, e um
    atalho corrigido em disco segue abrindo pela linha antiga. O sintoma é
    cruel: o arquivo está certo, `gtk-launch` funciona, e clicar no ícone da
    grade falha do mesmo jeito de antes — o que manda procurar o defeito
    exatamente onde ele não está.

    É melhor-esforço de propósito. O binário faz parte do `desktop-file-utils`
    e pode não existir; quando não existe, o atalho continua correto e só
    demora mais a ser notado. Falhar a instalação por causa disso seria trocar
    um incômodo por um impedimento.
    """
    ferramenta = shutil.which("update-desktop-database")
    if ferramenta is None:
        logger.debug("update-desktop-database não encontrado; cache não atualizado")
        return

    try:
        subprocess.run(
            [ferramenta, str(entry_path().parent)],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        logger.debug("update-desktop-database falhou: %s", erro)


def install(force: bool = False) -> bool:
    """Escreve atalho e ícone. Devolve se escreveu.

    Sem `force`, um atalho existente é respeitado — inclusive um que você tenha
    editado à mão.
    """
    if not sys.platform.startswith("linux"):
        return False

    alvo = entry_path()
    if alvo.exists() and not force:
        return False

    origem = _source_icon()
    if origem is None:
        logger.warning("ícone não encontrado: o atalho não foi criado")
        return False

    alvo.parent.mkdir(parents=True, exist_ok=True)
    icone = icon_path()
    icone.parent.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(origem, icone)
    alvo.write_text(desktop_entry_text(), encoding="utf-8")
    # Sem o bit de execução, o GNOME marca o atalho como não confiável.
    alvo.chmod(0o755)
    _refresh_desktop_database()

    logger.info("atalho criado em %s", alvo)
    return True


def ensure_installed() -> bool:
    """Cria o atalho na primeira vez, em silêncio nas seguintes."""
    return install(force=False)


def remove() -> bool:
    """Apaga atalho e ícone. Devolve se havia o que apagar."""
    if not sys.platform.startswith("linux"):
        return False

    achou = False
    for caminho in (entry_path(), icon_path()):
        if caminho.exists():
            caminho.unlink()
            achou = True

    if achou:
        _refresh_desktop_database()
    return achou
