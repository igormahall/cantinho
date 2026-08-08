"""Uma instância por banco.

Duas cópias do app sobre o mesmo log é problema real, não zelo: cada uma
carrega as projeções na memória no startup e não fica sabendo do que a outra
grava. A tela de uma some com a tarefa que a outra ainda mostra, e um timer
aberto em cada janela vira duas sessões contando o mesmo tempo.

A trava é por banco, e não por máquina, de propósito: `--db` existe justamente
para experimentar sem sujar o banco real, e travar por máquina proibiria abrir
o app de teste com o app de verdade rodando na bandeja.

`QLocalServer` e não arquivo de lock: além de detectar, ele serve de campainha.
A segunda cópia avisa a primeira e sai, e quem apertou o ícone vê a janela
aparecer em vez de nada acontecer. É named pipe no Windows e socket de domínio
no Linux, sem código de plataforma dos dois lados.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)

__all__ = ["SingleInstance"]

# Tempo de espera ao falar com a instância que já existe. Local e sem I/O de
# disco no caminho: se não responder nisso, ela está travada ou morta.
TIMEOUT_MS = 500


def _nome_para(db_path: Path) -> str:
    """Nome do canal, derivado do caminho do banco.

    Hash e não o caminho: nome de named pipe tem limite de tamanho e não aceita
    barra. `casefold` porque no Windows dois caminhos que só diferem em caixa
    são o mesmo arquivo.
    """
    alvo = str(Path(db_path).resolve()).casefold().encode("utf-8")
    return "cantinho-" + hashlib.blake2s(alvo, digest_size=8).hexdigest()


class SingleInstance(QObject):
    """Servidor local que garante uma cópia do app por banco."""

    activated = Signal()

    def __init__(self, db_path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nome = _nome_para(db_path)
        self._server: QLocalServer | None = None

    def already_running(self) -> bool:
        """True se outra cópia atendeu — e, nesse caso, já foi avisada."""
        socket = QLocalSocket()
        socket.connectToServer(self._nome)
        if not socket.waitForConnected(TIMEOUT_MS):
            return False
        socket.write(b"abrir")
        socket.waitForBytesWritten(TIMEOUT_MS)
        socket.disconnectFromServer()
        return True

    def listen(self) -> bool:
        """Passa a atender. Chamar só depois de `already_running()` dar False."""
        # Sobra de processo que morreu sem fechar o canal. Só é seguro remover
        # porque `already_running()` acabou de provar que ninguém atende nele.
        QLocalServer.removeServer(self._nome)
        server = QLocalServer(self)
        if not server.listen(self._nome):
            logger.warning(
                "não foi possível abrir a trava de instância: %s",
                server.errorString(),
            )
            return False
        server.newConnection.connect(self._on_connection)
        self._server = server
        return True

    def _on_connection(self) -> None:
        server = self._server
        if server is None:
            return
        socket = server.nextPendingConnection()
        if socket is not None:
            socket.disconnected.connect(socket.deleteLater)
        self.activated.emit()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
