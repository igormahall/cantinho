"""Fixtures compartilhadas e o checklist do sistema.

Nenhum teste do `core` pode depender do relógio real nem do banco real. Aqui
ficam o relógio congelado e o store em diretório temporário.

Aqui fica também a filtragem por sistema: os testes marcados com `posix` ou
`windows` só são coletados no sistema deles. O porquê está em `checklist.py`,
que é a decisão em forma de função pura; isto aqui é só o encanamento do
pytest.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pytest

from cantinho.core.clock import FakeClock
from cantinho.core.store import EventStore

# O vizinho de pasta: `tests/` entra no `sys.path` quando o pytest importa este
# conftest, então o helper é importável pelo nome, daqui e dos testes.
from checklist import exclusivo_de, no_checklist, sistema_atual

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


# ------------------------------------------------------- o checklist do sistema

# O que ficou de fora nesta execução, para o cabeçalho contar. Guardado por
# sistema: dizer "3 fora" sem dizer de quem eles são não explica nada.
_FORA: Counter[str] = Counter()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Deixa passar só o checklist deste sistema.

    Os outros saem da coleta em vez de virarem pulados — e sem chamar o hook de
    "deselected", porque não foram descartados por escolha de quem rodou: no
    sistema errado eles simplesmente não existem.
    """
    sistema = sistema_atual()
    dentro = []
    for item in items:
        marcas = {marca.name for marca in item.iter_markers()}
        if no_checklist(marcas, sistema):
            dentro.append(item)
            continue
        # `exclusivo_de` e não "a marca que sobrou": `iter_markers` traz também
        # as do pytest, e `parametrize` viraria nome de sistema. Aqui ele nunca
        # devolve None — `no_checklist` só é falso quando há marca de outro.
        alvo = exclusivo_de(marcas)
        assert alvo is not None
        _FORA[alvo] += 1
    items[:] = dentro


def pytest_report_collectionfinish(items: list[pytest.Item]) -> str:
    """A linha que faz o número da suíte se explicar sozinho.

    Sem ela, a mesma suíte terminando com contagens diferentes em cada máquina
    é motivo para desconfiar de uma das duas. E ela reconcilia com o "collected
    N items" logo acima, que o pytest conta antes desta filtragem: o número
    maior é o que existe na árvore, o menor é o que este sistema tem para
    rodar.
    """
    total = len(items) + sum(_FORA.values())
    linha = f"checklist: {sistema_atual()} — {len(items)} testes"
    if not _FORA:
        return f"{linha}, nenhum exclusivo de outro sistema"
    partes = [
        f"{quantos} exclusivo{'s' if quantos > 1 else ''} de {alvo}"
        for alvo, quantos in sorted(_FORA.items())
    ]
    return f"{linha} dos {total} coletados; fora: {', '.join(partes)}"
