"""Qual checklist a suíte roda, e por que não é a mesma nos dois sistemas.

Quase tudo aqui roda em qualquer lugar: o `core` não importa Qt, e o que é de
plataforma finge o `sys.platform` com `monkeypatch` e é conferido nas duas
pontas de dentro de um sistema só. O que **não** dá para fingir é o sistema de
arquivos — o `pathlib` escolheu `WindowsPath` ou `PosixPath` na importação, e o
`chmod` do Windows não tem bit de execução para ligar.

Esses poucos testes não são "testes que faltam" no outro sistema: eles não
existem lá. Marcados com `@pytest.mark.posix` ou `@pytest.mark.windows`, ficam
**fora da coleta** de quem não é o sistema deles, em vez de virarem pulados.

A diferença importa porque um pulado é uma pergunta em aberto — "isto deveria
ter rodado?" — que reaparece em toda execução e nunca tem resposta nova. A
suíte do Windows terminava com "3 pulados" para sempre, e quem lesse aquilo sem
o comentário ao lado concluiria que a suíte estava incompleta. Fora da coleta,
cada sistema termina com o seu checklist inteiro e nada pendurado; quantos
testes ficaram de fora, e por qual sistema, o cabeçalho da coleta diz.

O `conftest.py` faz a filtragem. Aqui fica só a decisão, que é função pura e
tem teste (`test_checklist.py`).
"""

from __future__ import annotations

import os
from collections.abc import Iterable

# Os nomes são os dois valores possíveis de `os.name` traduzidos para o
# vocabulário de quem escreve o teste. `posix` e não `linux` porque o que estes
# testes exigem é semântica POSIX — separador de caminho, bit de permissão —, e
# não uma distribuição.
POSIX = "posix"
WINDOWS = "windows"

SISTEMAS = (POSIX, WINDOWS)


def sistema_atual() -> str:
    """O sistema em que a suíte está rodando agora.

    Vem de `os.name` e não de `sys.platform` de propósito: `sys.platform` é o
    que os testes de plataforma fingem com `monkeypatch`, e a coleta acontece
    antes de qualquer fixture. Confundir os dois faria a suíte inteira mudar de
    checklist por causa de um teste.
    """
    return WINDOWS if os.name == "nt" else POSIX


def exclusivo_de(marcas: Iterable[str]) -> str | None:
    """O sistema a que um teste pertence, ou `None` se ele vale nos dois."""
    presentes = [nome for nome in SISTEMAS if nome in set(marcas)]
    return presentes[0] if presentes else None


def no_checklist(marcas: Iterable[str], sistema: str) -> bool:
    """Se este teste faz parte do checklist do sistema informado."""
    alvo = exclusivo_de(marcas)
    return alvo is None or alvo == sistema
