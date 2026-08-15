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
import struct
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "ENTRY_NAME",
    "ICON_NAME",
    "entry_path",
    "icon_path",
    "installed_icons",
    "install_icons",
    "desktop_entry_text",
    "install",
    "ensure_installed",
    "remove",
]

ENTRY_NAME = "cantinho.desktop"
ICON_NAME = "cantinho"

# O tamanho "de referência", que é o que `icon_path()` devolve sem argumento.
# **Não é o único instalado** — ver `install_icons`.
_ICON_SIZE = 256


def _data_home() -> Path:
    """`XDG_DATA_HOME`, com o padrão da especificação quando ela não está posta."""
    bruto = os.environ.get("XDG_DATA_HOME")
    if bruto:
        return Path(bruto)
    return Path.home() / ".local" / "share"


def entry_path() -> Path:
    return _data_home() / "applications" / ENTRY_NAME


def icon_path(size: int = _ICON_SIZE) -> Path:
    pasta = f"{size}x{size}"
    return _data_home() / "icons" / "hicolor" / pasta / "apps" / f"{ICON_NAME}.png"


def _quadros_do_ico(bruto: bytes) -> dict[int, bytes]:
    """Os PNGs de dentro do `.ico`, indexados pelo lado.

    **É de propósito que o Linux beba do arquivo do Windows.** O `.ico` já
    carrega os sete tamanhos, cada um com a arte feita para ele — e a razão de
    ele ter sete é que o desenho *muda* com o tamanho: de 32 px para cima é a
    planta sobre um ladrilho quente; abaixo disso o ladrilho sai e a planta
    ocupa o quadro inteiro. Lendo daqui, os dois sistemas mostram literalmente
    os mesmos bytes, que é o que "igual ao do Windows" quer dizer.

    O formato permite BMP ou PNG por quadro; `tools/gerar_icone.py` grava PNG
    em todos, então quadro que não comece com a assinatura de PNG é ignorado em
    vez de virar erro — um `.ico` de outra procedência não deve derrubar a
    instalação do atalho.

    Sem Qt de propósito: este módulo é chamado antes de a aplicação existir, e
    `struct` dá conta de um cabeçalho de seis bytes e entradas de dezesseis.
    """
    assinatura = b"\x89PNG\r\n\x1a\n"
    quadros: dict[int, bytes] = {}

    if len(bruto) < 6:
        return quadros
    reservado, tipo, quantidade = struct.unpack_from("<HHH", bruto, 0)
    if reservado != 0 or tipo != 1:
        return quadros

    for indice in range(quantidade):
        inicio = 6 + 16 * indice
        if inicio + 16 > len(bruto):
            break
        largura, _altura, _cores, _res, _planos, _bpp, tamanho, deslocamento = (
            struct.unpack_from("<BBBBHHII", bruto, inicio)
        )
        # No formato, 0 quer dizer 256: o campo tem um byte só.
        lado = largura or 256
        fim = deslocamento + tamanho
        if fim > len(bruto):
            continue
        dados = bruto[deslocamento:fim]
        if dados.startswith(assinatura):
            quadros[lado] = dados

    return quadros


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

    São dois modos. Num executável congelado (`sys.frozen`), `sys.executable`
    já é o próprio Cantinho e basta — este projeto não gera nenhum, mas a
    checagem custa uma linha e evita um `Exec=` sem sentido se um dia gerar.
    Rodando do repositório, que é o caso real, é o Python do venv com
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


def _source_ico() -> Path | None:
    from cantinho.services import scene

    origem = scene.assets_dir() / "icon" / f"{ICON_NAME}.ico"
    return origem if origem.is_file() else None


def installed_icons() -> dict[int, Path]:
    """Os tamanhos que estão em disco agora, por lado."""
    achados: dict[int, Path] = {}
    raiz = _data_home() / "icons" / "hicolor"
    if not raiz.is_dir():
        return achados
    for pasta in raiz.iterdir():
        nome = pasta.name
        if "x" not in nome:
            continue
        lado, _, resto = nome.partition("x")
        if not lado.isdigit() or lado != resto:
            continue
        arquivo = pasta / "apps" / f"{ICON_NAME}.png"
        if arquivo.is_file():
            achados[int(lado)] = arquivo
    return achados


def install_icons() -> list[int]:
    """Escreve o ícone em todos os tamanhos que o `.ico` carrega.

    **Este era o defeito.** Só o 256 era instalado, e o ambiente reduzia esse
    único arquivo para os 22-24 px da bandeja e os 48-64 do dock. Só que a arte
    do 256 é a planta sobre um ladrilho escuro: reduzida a 24 px ela vira um
    quadrado escuro com um borrão dentro — que na barra lê como ícone genérico,
    exatamente o sintoma relatado. No Windows isso nunca apareceu porque lá o
    `.ico` entrega os sete tamanhos e o sistema escolhe o certo.

    Ao contrário do `.desktop`, o ícone **é sempre reescrito**. A regra de
    "criar uma vez e nunca sobrescrever" existe para proteger o `Exec=` de ser
    sequestrado por um clone de teste, e para respeitar um atalho editado à
    mão — nada disso vale para o ícone, que é asset do app e ninguém edita.
    Congelá-lo junto significaria que uma instalação antiga nunca ganharia os
    tamanhos que faltam, que é justamente o caso que se está consertando.
    """
    ico = _source_ico()
    quadros: dict[int, bytes] = {}
    if ico is not None:
        try:
            quadros = _quadros_do_ico(ico.read_bytes())
        except OSError:
            logger.warning("não deu para ler %s", ico, exc_info=True)

    if not quadros:
        # Sem o `.ico` legível, o 256 sozinho ainda é melhor que ícone nenhum.
        origem = _source_icon()
        if origem is None:
            return []
        try:
            quadros = {_ICON_SIZE: origem.read_bytes()}
        except OSError:
            logger.warning("não deu para ler %s", origem, exc_info=True)
            return []

    escritos: list[int] = []
    for lado, dados in sorted(quadros.items()):
        destino = icon_path(lado)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            if not destino.is_file() or destino.read_bytes() != dados:
                destino.write_bytes(dados)
            escritos.append(lado)
        except OSError:
            logger.warning("não deu para escrever %s", destino, exc_info=True)

    if escritos:
        _refresh_icon_cache()
    return escritos


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


def _refresh_icon_cache() -> None:
    """Avisa o GTK que a pasta de ícones mudou.

    É o irmão de `_refresh_desktop_database`, e faltava. Sem ele, ambiente que
    já tenha um `icon-theme.cache` na árvore local continua servindo o índice
    antigo, e um tamanho recém-instalado não é encontrado — o sintoma é o ícone
    certo em disco e o genérico na tela, que é o pior tipo de defeito para
    diagnosticar.

    Melhor-esforço pela mesma razão do outro: o binário vem do `gtk-update-icon-cache`
    e pode não existir. `--ignore-theme-index` porque a árvore local não tem
    `index.theme` próprio (ela se apoia no `hicolor` do sistema), e sem a flag a
    ferramenta recusa a pasta.
    """
    ferramenta = shutil.which("gtk-update-icon-cache")
    if ferramenta is None:
        logger.debug("gtk-update-icon-cache não encontrado; cache não atualizado")
        return

    raiz = _data_home() / "icons" / "hicolor"
    try:
        subprocess.run(
            [ferramenta, "--ignore-theme-index", "--quiet", str(raiz)],
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as erro:
        logger.debug("gtk-update-icon-cache falhou: %s", erro)


def install(force: bool = False) -> bool:
    """Escreve atalho e ícone. Devolve se escreveu.

    Sem `force`, um atalho existente é respeitado — inclusive um que você tenha
    editado à mão.
    """
    if not sys.platform.startswith("linux"):
        return False

    # O ícone é reparado sempre, mesmo com o atalho já no lugar. São coisas de
    # naturezas diferentes: o `.desktop` pode ter sido editado à mão e aponta
    # para um executável, enquanto o ícone é asset do app. Ver `install_icons`.
    tamanhos = install_icons()

    alvo = entry_path()
    if alvo.exists() and not force:
        return False

    if not tamanhos:
        logger.warning("ícone não encontrado: o atalho não foi criado")
        return False

    alvo.parent.mkdir(parents=True, exist_ok=True)
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
    alvos = [entry_path(), *installed_icons().values()]
    for caminho in alvos:
        if caminho.exists():
            caminho.unlink()
            achou = True

    if achou:
        _refresh_desktop_database()
        _refresh_icon_cache()
    return achou
