"""Ícone de bandeja.

`QSystemTrayIcon` mora em QtWidgets, que o projeto não usa para UI. A exceção
está confinada aqui de propósito: bandeja é integração com o sistema, não
interface. Nenhum widget é criado nem mostrado — a UI segue inteira em QML.

É também por isso que `main.py` instancia `QApplication` em vez de
`QGuiApplication`: sem ela a bandeja não sobe.
"""

from __future__ import annotations

import logging
import subprocess
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from cantinho.services import scene

logger = logging.getLogger(__name__)

__all__ = ["Tray"]


# Tamanhos que o Windows pede da bandeja conforme a escala da tela.
_TAMANHOS_BANDEJA = (16, 20, 24, 32)


def _plant_icon(stage: int) -> QIcon:
    """A planta do quarto, no estágio de agora.

    A bandeja é o único lugar onde o ícone é vivo: ele acompanha o crescimento.
    O ícone do executável é fixo, porque identidade não pode mudar sozinha.

    Entrega vários tamanhos em vez de um só. Deixar o Windows reduzir um ícone
    de 64 para 16 sozinho borra o desenho — e em 16 px o `render_icon` ainda
    troca a composição, largando o ladrilho para a planta caber.
    """
    icone = QIcon()
    for lado in _TAMANHOS_BANDEJA:
        icone.addPixmap(QPixmap.fromImage(scene.render_icon(stage, lado)))
    return icone


# Quanto tempo a notificação fica na tela, quando o sistema deixa escolher.
#
# Doze segundos, o mesmo do toque dentro da janela. Vale como pedido e não como
# garantia: no Linux quem decide é o serviço de notificação do desktop, e no
# Windows a Central de Ações usa o tempo dela.
NOTIFY_MS = 12_000

# Nome do `.desktop` que `services/desktop_entry.py` instala. Vai como dica na
# notificação do Linux, e é o que faz duas coisas: o balão aparece com o ícone
# da planta em vez do (i) genérico, e clicar nele ativa o atalho — que cai na
# trava de instância única e traz a janela que já existe para a frente.
DESKTOP_ENTRY = "cantinho"


def _notificar_por_dbus(texto: str) -> bool:
    """Balão pelo serviço de notificação do desktop. Só no Linux.

    Existe porque `QSystemTrayIcon.showMessage` **não abre balão no GNOME**.
    Ele entrega a mensagem — ela aparece na lista de notificações, o ponto
    acende ao lado do relógio —, mas banner nenhum sobe. Num aviso que existe
    para alcançar quem não está olhando para o app, chegar só na lista é o
    mesmo que não chegar.

    Foi medido nas duas pontas, com a fila de notificações vazia: pelo Qt, nada
    na tela; por este caminho, o balão aparece.

    A conversa é por `gdbus` e não por `QtDBus` porque `Notify` pede
    `replaces_id` como uint32, e o PySide6 converte todo `int` do Python para
    int32 — o barramento recusa a chamada por assinatura errada e não há como
    marcar o tipo pelas classes que ele expõe. `gdbus` vem no glib, que está em
    qualquer desktop que tenha serviço de notificação para começo de conversa.
    Chamada externa em melhor-esforço é o mesmo padrão do
    `update-desktop-database` em `desktop_entry.py`.
    """
    if not sys.platform.startswith("linux"):
        return False
    try:
        resultado = subprocess.run(
            [
                "gdbus", "call", "--session",
                "--dest", "org.freedesktop.Notifications",
                "--object-path", "/org/freedesktop/Notifications",
                "--method", "org.freedesktop.Notifications.Notify",
                "Cantinho",          # app_name
                "0",                 # replaces_id: sempre novo, nunca substitui
                DESKTOP_ENTRY,       # app_icon
                "Cantinho",          # summary
                texto,               # body
                "[]",                # actions
                "{'desktop-entry': <'%s'>}" % DESKTOP_ENTRY,
                str(NOTIFY_MS),
            ],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        logger.debug("gdbus indisponível para notificar", exc_info=True)
        return False
    if resultado.returncode != 0:
        logger.debug("gdbus recusou a notificação: %s", resultado.stderr)
        return False
    return True


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
        # Clicar na notificação abre o quarto. É o que a torna útil: ela existe
        # para dar um caminho de volta, não para informar.
        self._icon.messageClicked.connect(self.openRequested)
        self._icon.show()
        return True

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.openRequested.emit()

    @property
    def supports_messages(self) -> bool:
        """Se o sistema mostra balão de notificação.

        Separado de `available` porque são coisas diferentes: há ambiente que
        aceita o ícone e engole a mensagem. Quando engole, `showMessage` não
        falha nem avisa — simplesmente não acontece nada.
        """
        return QSystemTrayIcon.supportsMessages()

    def notify(self, texto: str) -> bool:
        """Um balão de notificação. Devolve se algum caminho aceitou.

        Dois caminhos, e a ordem importa. No Linux vai pelo serviço de
        notificação do desktop, porque o do Qt entrega a mensagem para a lista
        sem abrir balão nenhum — ver `_notificar_por_dbus`. Nos demais sistemas
        (o Windows, que é a prioridade do projeto) o caminho do Qt é o certo e
        o único: é ele que vira torrada da Central de Ações.

        O ícone é o da bandeja, não o `Information` do sistema: um (i) azul
        seria a única coisa deste app com cara de alerta.
        """
        if _notificar_por_dbus(texto):
            return True
        if self._icon is None or not self.supports_messages:
            return False
        self._icon.showMessage("Cantinho", texto, self._icon.icon(), NOTIFY_MS)
        return True

    def set_stage(self, stage: int) -> None:
        if self._icon is not None:
            self._icon.setIcon(_plant_icon(stage))

    def hide(self) -> None:
        if self._icon is not None:
            self._icon.hide()
