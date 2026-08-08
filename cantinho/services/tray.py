"""Ícone de bandeja.

`QSystemTrayIcon` mora em QtWidgets, que o projeto não usa para UI. A exceção
está confinada aqui de propósito: bandeja é integração com o sistema, não
interface. Nenhum widget é criado nem mostrado — a UI segue inteira em QML.

É também por isso que `main.py` instancia `QApplication` em vez de
`QGuiApplication`: sem ela a bandeja não sobe.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from cantinho.services import scene

logger = logging.getLogger(__name__)

__all__ = ["Tray"]


def _plant_icon(stage: int) -> QIcon:
    """Ícone tirado do próprio desenho da planta, no estágio atual.

    Sem asset novo: a bandeja mostra o mesmo que o vaso do quarto.
    """
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    imagem = QImage(64, 64, QImage.Format_ARGB32_Premultiplied)
    imagem.fill(Qt.transparent)
    renderer = QSvgRenderer(str(scene.plant_path(stage)))
    if renderer.isValid():
        painter = QPainter(imagem)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter, QRectF(2, 2, 60, 60))
        painter.end()
    return QIcon(QPixmap.fromImage(imagem))


class Tray(QObject):
    """Bandeja com o mínimo: abrir, alternar a mini janela, sair."""

    openRequested = Signal()
    miniToggleRequested = Signal()
    quitRequested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._icon: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def install(self, stage: int = 0) -> bool:
        if not self.available:
            logger.info("bandeja indisponível neste sistema")
            return False

        self._menu = QMenu()
        abrir = QAction("Abrir o cantinho", self._menu)
        abrir.triggered.connect(self.openRequested)
        mini = QAction("Mostrar/esconder a mini", self._menu)
        mini.triggered.connect(self.miniToggleRequested)
        sair = QAction("Sair", self._menu)
        sair.triggered.connect(self.quitRequested)

        self._menu.addAction(abrir)
        self._menu.addAction(mini)
        self._menu.addSeparator()
        self._menu.addAction(sair)

        self._icon = QSystemTrayIcon(_plant_icon(stage))
        self._icon.setToolTip("Cantinho")
        self._icon.setContextMenu(self._menu)
        self._icon.activated.connect(self._on_activated)
        self._icon.show()
        return True

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.openRequested.emit()

    def set_stage(self, stage: int) -> None:
        if self._icon is not None:
            self._icon.setIcon(_plant_icon(stage))

    def hide(self) -> None:
        if self._icon is not None:
            self._icon.hide()
