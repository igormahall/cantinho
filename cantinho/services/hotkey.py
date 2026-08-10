"""Atalho global para a captura de ideias.

Interface única, duas implementações. Windows é a que funciona hoje; Linux é um
no-op deliberado, para que o resto do app não precise saber em que sistema está.

Registrar atalho global é a parte mais específica de plataforma do projeto
inteiro. Ela fica atrás desta interface justamente para que o port do Linux
seja escrever uma classe aqui, e não caçar Win32 espalhado pela UI.
"""

from __future__ import annotations

import logging
import sys
from typing import Protocol

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

logger = logging.getLogger(__name__)

__all__ = ["GlobalHotkey", "create_hotkey"]

# MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, tecla I.
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_NOREPEAT = 0x4000
_VK_I = 0x49
_WM_HOTKEY = 0x0312
_HOTKEY_ID = 0xC0DE


class GlobalHotkey(Protocol):
    """Atalho de sistema. `triggered` dispara mesmo com o app sem foco."""

    triggered: Signal

    def install(self) -> bool: ...

    def remove(self) -> None: ...


class _NullHotkey(QObject):
    """Sem atalho global. O app funciona, só não captura ideia de fora."""

    triggered = Signal()

    def install(self) -> bool:
        logger.info("atalho global não implementado nesta plataforma")
        return False

    def remove(self) -> None:
        return None


class _WindowsHotkey(QObject, QAbstractNativeEventFilter):
    """Ctrl+Shift+I via RegisterHotKey.

    O filtro de evento nativo é instalado na aplicação porque a mensagem
    WM_HOTKEY chega na fila da thread, não em uma janela específica — o atalho
    precisa funcionar com todas as janelas escondidas.
    """

    triggered = Signal()

    def __init__(self) -> None:
        QObject.__init__(self)
        QAbstractNativeEventFilter.__init__(self)
        self._registered = False

    def install(self) -> bool:
        import ctypes
        from PySide6.QtCore import QCoreApplication

        user32 = ctypes.windll.user32
        modificadores = _MOD_CONTROL | _MOD_SHIFT | _MOD_NOREPEAT
        if not user32.RegisterHotKey(None, _HOTKEY_ID, modificadores, _VK_I):
            # Outro programa já tomou a combinação. Não é motivo para derrubar
            # o app: só não vai existir captura global.
            logger.warning("não foi possível registrar Ctrl+Shift+I")
            return False

        QCoreApplication.instance().installNativeEventFilter(self)
        self._registered = True
        logger.info("atalho global Ctrl+Shift+I registrado")
        return True

    def nativeEventFilter(self, eventType, message):  # type: ignore[no-untyped-def]
        if self._registered and eventType == "windows_generic_MSG":
            import ctypes
            from ctypes import wintypes

            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == _WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                self.triggered.emit()
        return False, 0

    def remove(self) -> None:
        if not self._registered:
            return
        import ctypes
        from PySide6.QtCore import QCoreApplication

        ctypes.windll.user32.UnregisterHotKey(None, _HOTKEY_ID)
        aplicacao = QCoreApplication.instance()
        if aplicacao is not None:
            aplicacao.removeNativeEventFilter(self)
        self._registered = False


def create_hotkey() -> GlobalHotkey:
    """Devolve a implementação da plataforma atual."""
    if sys.platform == "win32":
        return _WindowsHotkey()  # type: ignore[return-value]
    return _NullHotkey()  # type: ignore[return-value]
