"""O `core` tem que ser testável sem instanciar aplicação Qt.

Não é preferência de estilo. Se uma projeção passar a depender de Qt, ela deixa
de rodar em teste puro e a regra de "projeção é função pura" morre na prática
antes de morrer no papel. A mesma coisa vale para a direção da dependência:
`services` conhece `core`, e `core` não conhece `services`.

**Os módulos são descobertos, não listados.** A versão anterior importava quatro
nomes escritos à mão, e o `core` tinha seis — `schedule.py` e `export.py` podiam
arrastar Qt para dentro sem que nada reclamasse. Um módulo novo nasceria fora da
lista pela mesma razão, e essa é a hora em que o descuido entra: quem escreve um
módulo de `core` está pensando no que ele faz, não em ir atualizar um teste que
não sabe que existe.

A verificação roda num **subprocesso**, e isso é o ponto: dentro da suíte o
PySide6 já foi importado por outros testes: `sys.modules` mostraria Qt carregado
mesmo com o `core` inocente. Um Python limpo é o único lugar onde a pergunta
tem resposta.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# O que o subprocesso faz: descobre os módulos de `cantinho/core`, importa
# todos, e conta o que entrou junto. Uma execução responde as duas perguntas.
SCRIPT = """
import importlib
import pkgutil
import sys

import cantinho.core

nomes = sorted(
    info.name for info in pkgutil.iter_modules(cantinho.core.__path__)
    if not info.name.startswith("_")
)
for nome in nomes:
    importlib.import_module(f"cantinho.core.{nome}")

qt = sorted(m for m in sys.modules if m.split('.')[0] == 'PySide6')
servicos = sorted(m for m in sys.modules if m.startswith('cantinho.services'))
print('|'.join(nomes))
print('|'.join(qt))
print('|'.join(servicos))
"""


def _importar_o_core_num_python_limpo() -> tuple[list[str], list[str], list[str]]:
    resultado = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    # Sem `strip()` no todo: as duas últimas linhas são vazias quando nada
    # vazou, que é o caso bom — e aí elas somem e a leitura desanda.
    linhas = (resultado.stdout.splitlines() + ["", "", ""])[:3]
    modulos, qt, servicos = (
        [parte for parte in linha.split("|") if parte] for linha in linhas
    )
    return modulos, qt, servicos


@pytest.fixture(scope="module")
def limpo() -> tuple[list[str], list[str], list[str]]:
    """Uma execução só, lida por três testes.

    Subir um interpretador custa mais do que tudo o que se confere aqui, e as
    três perguntas são sobre o mesmo `sys.modules`.
    """
    return _importar_o_core_num_python_limpo()


def test_todo_modulo_do_core_foi_conferido(limpo) -> None:
    """A descoberta tem que achar o que está lá — senão as outras duas passam
    conferindo o vazio."""
    modulos, _, _ = limpo
    assert len(modulos) >= 6, f"achei só {modulos}"
    assert {"events", "projections", "store", "clock"} <= set(modulos)

    em_disco = {
        arquivo.stem
        for arquivo in (RAIZ / "cantinho" / "core").glob("*.py")
        if not arquivo.stem.startswith("_")
    }
    assert set(modulos) == em_disco


def test_core_nao_arrasta_pyside6(limpo) -> None:
    _, qt, _ = limpo
    assert qt == [], f"core importou Qt: {qt}"


def test_core_nao_importa_services(limpo) -> None:
    """A dependência anda numa direção só: services conhece core, core não."""
    _, _, servicos = limpo
    assert servicos == [], f"core importou services: {servicos}"
