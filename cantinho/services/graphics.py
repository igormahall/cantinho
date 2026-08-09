"""O ambiente gráfico, antes do Qt subir.

Este módulo conserta uma coisa só, e é uma coisa que não é do app: um ambiente
de terceiro que desliga o OpenGL do Qt por baixo do pano.

**Não importa PySide6, de propósito.** O que ele ajusta é lido pelo Qt no
momento em que a aplicação é construída, então precisa acontecer antes — e
qualquer import de Qt aqui convidaria alguém a inverter essa ordem depois.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

__all__ = ["GL_INTEGRATION_VAR", "ensure_gl_integration"]

GL_INTEGRATION_VAR = "QT_XCB_GL_INTEGRATION"

# O único valor que quebra: manda o xcb não carregar integração GL nenhuma.
# "xcb_glx" e "xcb_egl" são escolhas legítimas e passam intactas.
_DESLIGADO = "none"


def ensure_gl_integration() -> bool:
    """Remove `QT_XCB_GL_INTEGRATION=none` do ambiente. Devolve se mexeu.

    Quem escreve essa variável é o `qt-main` do conda, em
    `etc/conda/activate.d/qt-main_activate.sh`. Com o ambiente `base` ativado
    por padrão ela vale para todo terminal do usuário, e não está no `.bashrc`
    — que é o primeiro lugar onde se procura.

    O efeito é o app morrer logo depois de abrir:

        QXcbIntegration: Cannot create platform OpenGL context, neither GLX
        nor EGL are enabled
        Failed to initialize graphics backend for OpenGL.

    O sintoma imita o de biblioteca de sistema faltando, que é uma falha comum
    e documentada no README — e leva a instalar pacote atrás de pacote sem
    nada mudar, porque não falta nenhum. O que separa os dois casos é que aqui
    o `QT_DEBUG_PLUGINS=1` **nem chega a varrer** o diretório
    `xcbglintegrations`; no caso de `.so` ausente ele varre e falha ao
    carregar.

    Desfazer configuração de ambiente alheia é uma liberdade que só se toma
    com motivo. O motivo é que `none` não tem leitura válida aqui: o app é Qt
    Quick inteiro, não existe modo degradado em que ele funcione sem
    integração GL. Então isto não é preferência sobreposta, é ambiente que
    proíbe o programa de existir. Por isso também o log: mexer no ambiente de
    alguém em silêncio seria pior que a falha.

    Só toca em Linux. No Windows a variável não tem efeito, e apagar coisa do
    ambiente onde ela não faz mal é remexer à toa.
    """
    if not sys.platform.startswith("linux"):
        return False

    valor = os.environ.get(GL_INTEGRATION_VAR)
    if valor is None or valor.strip().lower() != _DESLIGADO:
        return False

    del os.environ[GL_INTEGRATION_VAR]
    logger.warning(
        "%s=%s foi removido do ambiente: com ele o Qt Quick não sobe. "
        "Costuma vir do qt-main do conda, com o ambiente base ativo.",
        GL_INTEGRATION_VAR,
        valor,
    )
    return True
