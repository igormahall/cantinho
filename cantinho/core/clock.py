"""Relógio injetável.

Tudo que depende de tempo no `core` recebe um `Clock`. Sem isso a janela móvel
de 14 dias não é testável: seria preciso esperar 14 dias de verdade.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

__all__ = ["Clock", "SystemClock", "FakeClock", "ensure_utc"]


def ensure_utc(moment: datetime) -> datetime:
    """Normaliza para UTC, recusando datetime ingênuo.

    Datetime sem tzinfo é ambíguo e é a origem clássica de erro de janela
    móvel. Melhor falhar na entrada do que calcular foco errado.
    """
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("datetime precisa ser tz-aware; recebido ingênuo")
    return moment.astimezone(timezone.utc)


@runtime_checkable
class Clock(Protocol):
    """Fonte de tempo. Sempre devolve UTC tz-aware."""

    def now(self) -> datetime:  # pragma: no cover - protocolo
        ...


class SystemClock:
    """Relógio real. O único que vai para produção."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock:
    """Relógio controlado, para testes.

    Não avança sozinho: só se mexe via `advance` ou `set`.
    """

    def __init__(self, start: datetime) -> None:
        self._now: datetime = ensure_utc(start)

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> datetime:
        """Avança o relógio. Delta negativo é recusado: o tempo não volta."""
        if delta < timedelta(0):
            raise ValueError("FakeClock não anda para trás")
        self._now += delta
        return self._now

    def set(self, moment: datetime) -> datetime:
        """Reposiciona o relógio em um instante absoluto."""
        self._now = ensure_utc(moment)
        return self._now

    def __repr__(self) -> str:
        return f"FakeClock({self._now.isoformat()})"
