"""Regera as capturas do README.

As imagens de `docs/` são versionadas prontas, como o áudio e o ícone, para que
o README funcione num clone limpo. Mas capturar à mão significa que elas
envelhecem em silêncio: a primeira versão delas ficou meses mostrando um quarto
sem calendário, sem relógio e sem o bilhete da parede.

    python tools/gerar_capturas.py

Abre o app sobre um banco semeado na hora, num diretório temporário, e
fotografa os dois temas. Precisa de tela de verdade — com
`QT_QPA_PLATFORM=offscreen` o Qt fica sem nenhuma família de fonte e o texto
sai como tofu.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from cantinho.backend import Backend
from cantinho.core.clock import SystemClock
from cantinho.core.store import EventStore
from cantinho.services import scene

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semear import semear  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs"

# O crossfade de cenário leva três segundos. Fotografar antes disso pega a
# tela no meio da travessia, com os dois temas sobrepostos.
ESPERA_TEMA = 4000


def main() -> int:
    pasta = Path(tempfile.mkdtemp())
    banco = pasta / "capturas.db"
    semear(banco)

    app = QApplication([])
    store = EventStore(banco, device_id="capturas")
    backend = Backend(store, SystemClock())

    engine = QQmlApplicationEngine()
    engine.addImageProvider("cena", scene.SceneImageProvider())
    ui = RAIZ / "cantinho" / "ui"
    engine.addImportPath(str(ui))
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(ui / "Main.qml")))

    if not engine.rootObjects():
        print("a janela não carregou")
        return 1
    janela = engine.rootObjects()[0]
    DESTINO.mkdir(parents=True, exist_ok=True)

    def fotografar(nome: str) -> None:
        caminho = DESTINO / f"{nome}.png"
        janela.grabWindow().save(str(caminho))
        print(f"  -> {caminho.relative_to(RAIZ)} "
              f"({caminho.stat().st_size / 1024:.0f} KB)")

    def encerrar() -> None:
        engine.deleteLater()
        app.quit()

    # A de tarde mostra a gaveta aberta; a da noite mostra o quarto limpo. As
    # duas juntas dão as duas caras do app numa tela só cada.
    roteiro = [
        (1200, lambda: backend.setThemeMode("noite")),
        (1200 + ESPERA_TEMA, lambda: fotografar("quarto-noite")),
        (1400 + ESPERA_TEMA, lambda: (backend.setThemeMode("tarde"),
                                      janela.setProperty("aba", "backlog"))),
        (1400 + 2 * ESPERA_TEMA, lambda: fotografar("quarto-tarde")),
        (2000 + 2 * ESPERA_TEMA, encerrar),
    ]
    for atraso, acao in roteiro:
        QTimer.singleShot(atraso, acao)

    print("capturando os dois temas")
    codigo = app.exec()
    store.close()
    shutil.rmtree(pasta, ignore_errors=True)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
