"""Marca de vida do app, para fechar sessão que uma queda deixou aberta.

Um `session.started` sem `session.ended` não conta em projeção nenhuma: nem no
foco de 14 dias, nem no bilhete, nem na semana. Saída normal já grava o fim
(ver `endOpenSession`), mas falta de energia, sessão do sistema derrubada e
processo morto não avisam ninguém — e é justamente aí que fica o tempo mais
longo, porque foi o que ninguém encerrou.

Fechar essa sessão "agora", na próxima abertura, seria inventar: a máquina pode
ter passado a noite desligada, e o log ganharia catorze horas de foco que não
existiram. Este arquivo é o que torna a conta honesta — ele guarda **o último
instante em que o app comprovadamente estava vivo**, e é até aí que a sessão é
fechada. O que se perde é o trecho entre a última marca e a queda, no máximo um
minuto.

## Por que um arquivo, se `events` é a única tabela

É a exceção que a regra 1 do projeto não previa, e ela é estreita de propósito:

- **Não é estado.** Nenhuma projeção lê isto. `events -> estado` continua sendo
  função pura, e o arquivo só decide *qual evento escrever* na recuperação.
- **Não sobrevive ao uso.** É apagado quando a sessão termina e quando o app
  fecha direito. Um heartbeat em disco significa, sempre, "o app morreu de pé".
- **Não cabia no log.** A alternativa seria um evento por minuto, o que enche o
  histórico de ruído para registrar que nada aconteceu.

Já há precedente de arquivo ao lado do banco: o `device_id`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from cantinho.core.events import format_timestamp, parse_timestamp

__all__ = ["Heartbeat", "HEARTBEAT_FILENAME"]

logger = logging.getLogger(__name__)

HEARTBEAT_FILENAME = "heartbeat"


class Heartbeat:
    """O último instante conhecido de vida, num arquivo ao lado do banco."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def beat(self, moment: datetime) -> None:
        """Registra que o app estava vivo em `moment`."""
        try:
            self._path.write_text(format_timestamp(moment), encoding="utf-8")
        except OSError:
            # Perder a marca degrada a recuperação, não quebra o app: sem ela a
            # sessão órfã é fechada no próprio começo.
            logger.warning("não deu para gravar a marca de vida", exc_info=True)

    def last(self) -> datetime | None:
        """A última marca, ou None se não há nenhuma legível.

        Leitura defensiva de propósito: o arquivo é escrito de um jeito que uma
        queda no meio da escrita deixa conteúdo pela metade, e um timestamp
        truncado não pode virar exceção no caminho de abertura do app.
        """
        try:
            bruto = self._path.read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            return None
        if not bruto:
            return None
        try:
            return parse_timestamp(bruto)
        except Exception:
            logger.warning("marca de vida ilegível: %r", bruto)
            return None

    def clear(self) -> None:
        """Apaga a marca. Chamado ao encerrar a sessão e ao fechar o app."""
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning("não deu para apagar a marca de vida", exc_info=True)
