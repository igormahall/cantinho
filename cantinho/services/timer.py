"""Timer de sessão.

Só conta o tempo e avisa a UI. Quem grava `session.started` e `session.ended`
é o backend: o timer não conhece o log.

O tempo decorrido vem do `Clock`, não da contagem de ticks. Um QTimer atrasa,
perde tick quando a máquina engasga e para junto com a suspensão do sistema —
contar tick daria uma sessão mais curta do que foi.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from cantinho.core.clock import Clock

__all__ = ["SessionTimer"]


class SessionTimer(QObject):
    """Cronômetro crescente, sem meta e sem cobrança."""

    tick = Signal()

    def __init__(self, clock: Clock, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._clock = clock
        self._started_at: datetime | None = None
        self._session_id: str | None = None
        self._task_id: str | None = None

        self._pulse = QTimer(self)
        self._pulse.setInterval(1000)
        self._pulse.timeout.connect(self.tick)

    @property
    def running(self) -> bool:
        return self._started_at is not None

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def task_id(self) -> str | None:
        return self._task_id

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def elapsed(self) -> timedelta:
        if self._started_at is None:
            return timedelta(0)
        return max(self._clock.now() - self._started_at, timedelta(0))

    def start(self, session_id: str, task_id: str | None, started_at: datetime) -> None:
        self._session_id = session_id
        self._task_id = task_id
        self._started_at = started_at
        self._pulse.start()
        self.tick.emit()

    def stop(self) -> None:
        self._pulse.stop()
        self._started_at = None
        self._session_id = None
        self._task_id = None
        self.tick.emit()
