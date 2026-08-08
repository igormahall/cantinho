"""O `core` tem que ser testável sem instanciar aplicação Qt.

Não é preferência de estilo. Se uma projeção passar a depender de Qt, ela deixa
de rodar em teste puro e a regra de "projeção é função pura" morre na prática
antes de morrer no papel.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

SCRIPT = """
import sys
import cantinho.core.clock
import cantinho.core.events
import cantinho.core.projections
import cantinho.core.store

vazados = sorted(m for m in sys.modules if m.split('.')[0] == 'PySide6')
print('|'.join(vazados))
"""


def test_core_nao_arrasta_pyside6() -> None:
    resultado = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    vazados = [m for m in resultado.stdout.strip().split("|") if m]
    assert vazados == [], f"core importou Qt: {vazados}"


def test_core_nao_importa_services() -> None:
    """A dependência anda numa direção só: services conhece core, core não."""
    script = (
        "import sys, cantinho.core.projections, cantinho.core.store;"
        "print('|'.join(sorted(m for m in sys.modules"
        " if m.startswith('cantinho.services'))))"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", script],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    assert resultado.stdout.strip() == ""
