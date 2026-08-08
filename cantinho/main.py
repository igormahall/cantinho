"""Ponto de entrada.

Uma `QQmlApplicationEngine`, dois `Window` QML, um backend só. As janelas se
ligam à mesma instância exposta como context property — sem IPC, sem estado
duplicado.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine

# QApplication, e não QGuiApplication, por causa da bandeja. Ver services/tray.py.
from PySide6.QtWidgets import QApplication

from cantinho.backend import Backend
from cantinho.core.clock import SystemClock
from cantinho.core.store import DATABASE_FILENAME, EventStore, default_data_dir
from cantinho.services import scene
from cantinho.services.audio import Ambience, Sfx
from cantinho.services.hotkey import create_hotkey
from cantinho.services.single_instance import SingleInstance
from cantinho.services.tray import Tray

logger = logging.getLogger(__name__)

UI_DIR = Path(__file__).resolve().parent / "ui"


def _ui_dir() -> Path:
    empacotado = getattr(sys, "_MEIPASS", None)
    if empacotado:
        return Path(empacotado) / "cantinho" / "ui"
    return UI_DIR


def _caminho(bruto: str) -> Path:
    """Caminho da linha de comando, com `~` resolvido aqui.

    O PowerShell não expande `~` em argumento de executável nativo — ele chega
    como um til literal, e `Path("~/x")` vira uma pasta chamada `~` dentro do
    diretório atual. O sintoma é o pior possível: o app abre, funciona e grava
    num banco vazio que não é o que se pediu.
    """
    return Path(bruto).expanduser()


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="cantinho", description="Cantinho")
    parser.add_argument(
        "--db",
        type=_caminho,
        default=None,
        help="caminho do banco (padrão: pasta de dados do sistema)",
    )
    parser.add_argument(
        "--device-id",
        default=None,
        help="força o device_id, útil para testar",
    )
    parser.add_argument(
        "--log",
        default="INFO",
        help="nível de log (DEBUG, INFO, WARNING...)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Cantinho")
    app.setOrganizationName("Cantinho")
    # Fechar a janela principal não encerra o app: ele continua na bandeja.
    app.setQuitOnLastWindowClosed(False)

    # Janela, barra de tarefas e alt-tab. Fixo, ao contrário do da bandeja:
    # o ícone que identifica o app não pode mudar sozinho.
    icone = scene.assets_dir() / "icon" / "cantinho.ico"
    if icone.is_file():
        app.setWindowIcon(QIcon(str(icone)))
    else:
        logger.warning("ícone não encontrado em %s", icone)

    db_path = args.db if args.db is not None else default_data_dir() / DATABASE_FILENAME

    # Antes de abrir o banco e antes de qualquer janela: se já existe uma cópia
    # sobre este mesmo banco, o certo é trazer a dela para a frente e sair.
    trava = SingleInstance(db_path)
    if trava.already_running():
        logger.info("já existe um cantinho aberto em %s", db_path)
        return 0
    trava.listen()

    store = EventStore(db_path, device_id=args.device_id)
    logger.info("banco em %s", store.db_path)

    clock = SystemClock()
    backend = Backend(store, clock)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("cena", scene.SceneImageProvider())
    engine.addImportPath(str(_ui_dir()))
    engine.rootContext().setContextProperty("backend", backend)

    ui = _ui_dir()
    for arquivo in ("Main.qml", "Mini.qml"):
        engine.load(QUrl.fromLocalFile(str(ui / arquivo)))

    if len(engine.rootObjects()) != 2:
        logger.error("as janelas não carregaram")
        return 1

    # Uma cópia já aberta traz a janela para a frente quando alguém tenta abrir
    # outra — inclusive pelo ícone da barra de tarefas.
    trava.activated.connect(backend.showMain)

    ambiente = Ambience(app)
    ambiente.set_theme(backend.themeName)
    backend.themeChanged.connect(lambda: ambiente.set_theme(backend.themeName))

    # Um interruptor só para o ambiente e para as reações de clique: dois
    # controles de som numa tela que quer ser um quarto já seria um painel.
    efeitos = Sfx(app)
    backend.sfxRequested.connect(efeitos.play)

    def _aplicar_som() -> None:
        mudo = not backend.soundOn
        ambiente.set_muted(mudo)
        efeitos.set_muted(mudo)

    backend.soundChanged.connect(_aplicar_som)
    _aplicar_som()

    bandeja = Tray(app)
    if bandeja.install(backend.plantStage):
        bandeja.openRequested.connect(backend.showMain)
        bandeja.miniToggleRequested.connect(backend.toggleMini)
        bandeja.quitRequested.connect(app.quit)
        backend.stateChanged.connect(lambda: bandeja.set_stage(backend.plantStage))
    else:
        # Sem bandeja não há como reabrir a janela: fechar precisa encerrar.
        logger.info("sem bandeja: fechar a janela encerra o app")
        app.setQuitOnLastWindowClosed(True)

    atalho = create_hotkey()
    if atalho.install():
        atalho.triggered.connect(backend.requestCapture)

    codigo = app.exec()
    atalho.remove()
    ambiente.stop()
    trava.close()

    # Derruba o QML antes do backend. Na ordem inversa, as janelas ainda
    # existem enquanto a context property já virou nulo, e cada binding da
    # tela reclama de ler propriedade de null no caminho da saída.
    engine.deleteLater()
    del engine

    store.close()
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
