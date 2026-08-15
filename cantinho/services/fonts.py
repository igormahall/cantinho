"""Registra as fontes do app e define a padrão da aplicação.

Antes disto o projeto **não definia fonte em lugar nenhum**. O app usava o
padrão do sistema, o que quer dizer Segoe UI no Windows e Cantarell ou DejaVu
no Ubuntu — e as duas máquinas são os dois contextos de uso deste projeto. Ou
seja: era outro programa em cada uma, com outro desenho de letra, outra métrica
e outras larguras de botão.

## Por que aqui e também no `Theme.qml`

Os dois carregam os mesmos arquivos, e cada um resolve uma metade:

- **Este módulo** define a fonte **padrão da aplicação** (`QApplication.setFont`).
  É o que faz cada `Text` do QML herdar a família certa sem precisar declarar
  nada — e, mais importante, faz o código novo nascer certo em vez de depender
  de alguém lembrar de escrever `font.family`.
- **O `FontLoader` do `Theme.qml`** garante que a família exista para o QML
  mesmo sem passar por aqui, e expõe o nome dela em `Theme.fonte` /
  `Theme.fontePapel` para os poucos lugares que trocam de família de propósito
  (o bilhete e o calendário, que usam o serif).

Registrar o mesmo arquivo duas vezes é inofensivo: o `QFontDatabase` resolve
pela família, e a segunda chamada não cria uma família nova.

## As duas famílias

- **Inter** (`FONTE_UI`) — a interface. Sans humanista de contraste baixo, que
  acompanha a ilustração do quarto sem disputar com ela.
- **EB Garamond** (`FONTE_PAPEL`) — as superfícies de papel do quarto: o
  bilhete e o calendário.

Ambas SIL OFL 1.1. A licença de cada uma vai junto em `assets/fonts/`.

Não é dependência nova: é asset, como os SVGs e os WAVs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from cantinho.services.scene import assets_dir

__all__ = ["load_fonts", "fonts_dir", "FONTE_UI", "FONTE_PAPEL", "ARQUIVOS"]

logger = logging.getLogger(__name__)

FONTE_UI = "Inter"
FONTE_PAPEL = "EB Garamond"

ARQUIVOS = ("Inter.ttf", "EBGaramond.ttf")


def fonts_dir() -> Path:
    return assets_dir() / "fonts"


def load_fonts(app: object | None = None) -> list[str]:
    """Registra as fontes e, com `app`, define a padrão. Devolve as famílias.

    Melhor-esforço de propósito: fonte que não carrega degrada a aparência e
    não impede o app de abrir. Sem os arquivos, o Qt volta ao padrão do
    sistema — que é exatamente o estado que este módulo existe para corrigir,
    mas é um estado em que o app funciona.
    """
    familias: list[str] = []
    for nome in ARQUIVOS:
        caminho = fonts_dir() / nome
        if not caminho.is_file():
            logger.warning("fonte não encontrada: %s", caminho)
            continue
        identificador = QFontDatabase.addApplicationFont(str(caminho))
        if identificador < 0:
            logger.warning("o Qt recusou a fonte %s", caminho)
            continue
        familias.extend(QFontDatabase.applicationFontFamilies(identificador))

    if app is not None and FONTE_UI in familias:
        # A partir daqui todo `Text` do QML sem `font.family` herda a Inter.
        app.setFont(QFont(FONTE_UI))
        logger.info("fonte padrão da aplicação: %s", FONTE_UI)

    return familias
