"""Fixtures compartilhadas.

Nenhum teste do `core` pode depender do relógio real nem do banco real. Aqui
ficam o relógio congelado e o store em diretório temporário.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest

from cantinho.core.clock import FakeClock
from cantinho.core.store import EventStore

# Instante fixo e arbitrário. Segunda-feira, para que qualquer teste que venha
# a olhar dia da semana não fique dependendo de quando a suíte roda.
INICIO = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

DEVICE = "device-de-teste"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(INICIO)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[EventStore]:
    with EventStore(tmp_path / "cantinho.db", device_id=DEVICE) as aberto:
        yield aberto
