"""Persistência do log append-only.

`events` é a única tabela. Só existe INSERT: nenhum caminho deste módulo emite
UPDATE ou DELETE, e nenhum outro módulo deve emitir.

Idempotência vem do `INSERT OR IGNORE` na chave primária. Reaplicar o mesmo
evento é uma operação sem efeito, o que é o que torna um merge futuro entre
dispositivos possível sem resolução de conflito.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from cantinho.core.events import Event, format_timestamp, new_id

__all__ = ["EventStore", "default_data_dir", "DEVICE_ID_FILENAME", "DATABASE_FILENAME"]

logger = logging.getLogger(__name__)

DATABASE_FILENAME = "cantinho.db"
DEVICE_ID_FILENAME = "device_id"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  uuid        TEXT PRIMARY KEY,
  device_id   TEXT NOT NULL,
  occurred_at TEXT NOT NULL,   -- ISO8601 UTC
  kind        TEXT NOT NULL,
  payload     TEXT NOT NULL    -- JSON
);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(occurred_at);
"""

_COLUMNS = "uuid, device_id, occurred_at, kind, payload"
# Ordem estável do log: tempo e, em empate, uuid. Sem o desempate, dois eventos
# no mesmo microssegundo sairiam em ordem arbitrária e a projeção deixaria de
# ser determinística.
_ORDER = "ORDER BY occurred_at, uuid"


def default_data_dir() -> Path:
    """Diretório de dados por plataforma.

    Windows é a prioridade atual; Linux é o caminho de casa. Qualquer outra
    plataforma cai no layout do Linux.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "Cantinho"
    return Path.home() / ".local" / "share" / "cantinho"


class EventStore:
    """Log de eventos sobre sqlite3.

    O schema é criado no primeiro uso e o `device_id` é resolvido uma vez e
    guardado em arquivo ao lado do banco.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        *,
        device_id: str | None = None,
    ) -> None:
        self._db_path = (
            Path(db_path) if db_path is not None else default_data_dir() / DATABASE_FILENAME
        )
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._device_id = device_id or self._resolve_device_id()
        self._conn = sqlite3.connect(self._db_path, isolation_level=None)
        self._configure()
        self._create_schema()

    # ------------------------------------------------------------ propriedades

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def device_id_path(self) -> Path:
        return self._db_path.parent / DEVICE_ID_FILENAME

    # ------------------------------------------------------------------ setup

    def _resolve_device_id(self) -> str:
        """Lê o device_id do disco, criando na primeira execução.

        Escrita com modo exclusivo: se duas instâncias subirem juntas, a
        perdedora relê em vez de sobrescrever. O device_id precisa ser estável
        para sempre, então uma troca silenciosa seria pior que o erro.
        """
        path = self.device_id_path
        try:
            existente = path.read_text(encoding="utf-8").strip()
            if existente:
                return existente
        except FileNotFoundError:
            pass

        candidato = new_id()
        try:
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(candidato)
            return candidato
        except FileExistsError:
            gravado = path.read_text(encoding="utf-8").strip()
            return gravado or candidato

    def _configure(self) -> None:
        modo = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()
        obtido = (modo[0] if modo else "").lower()
        if obtido != "wal":
            # Acontece em perfil de rede: WAL exige memória compartilhada, que
            # não existe em share SMB. O app continua correto, só mais lento.
            logger.warning(
                "WAL indisponível em %s, journal_mode=%s", self._db_path, obtido
            )
        self._conn.execute("PRAGMA synchronous=NORMAL")

    def _create_schema(self) -> None:
        self._conn.executescript(SCHEMA)

    # --------------------------------------------------------------- escrita

    def append(self, event: Event) -> bool:
        """Grava um evento. Devolve False se o uuid já estava no log."""
        inseridos = self.append_many((event,))
        return inseridos == 1

    def append_many(self, events: Iterable[Event]) -> int:
        """Grava vários eventos em uma transação. Devolve quantos entraram.

        Duplicados são ignorados, não são erro: reaplicar o mesmo lote duas
        vezes tem que dar o mesmo resultado.
        """
        linhas: Sequence[tuple[str, str, str, str, str]] = [
            event.to_row() for event in events
        ]
        if not linhas:
            return 0
        cursor = self._conn.cursor()
        try:
            cursor.execute("BEGIN")
            cursor.executemany(
                f"INSERT OR IGNORE INTO events ({_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
                linhas,
            )
            inseridos = cursor.rowcount
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.close()
        return max(inseridos, 0)

    # --------------------------------------------------------------- leitura

    def read_all(self) -> list[Event]:
        """Log inteiro, em ordem. Entrada das projeções no startup."""
        return list(self._read(f"SELECT {_COLUMNS} FROM events {_ORDER}"))

    def read_since(self, moment: datetime) -> list[Event]:
        """Eventos a partir de `moment`, inclusive."""
        return list(
            self._read(
                f"SELECT {_COLUMNS} FROM events WHERE occurred_at >= ? {_ORDER}",
                (format_timestamp(moment),),
            )
        )

    def count(self) -> int:
        linha = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return int(linha[0]) if linha else 0

    def _read(self, sql: str, params: tuple = ()) -> Iterator[Event]:
        for linha in self._conn.execute(sql, params):
            yield Event.from_row(linha)

    # ---------------------------------------------------------------- ciclo

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
