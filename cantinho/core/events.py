"""Eventos do log append-only.

Este módulo não faz I/O. Ele define o que é um evento válido, como construir um
de cada `kind` e como serializar para linha de banco. Persistência é problema do
`store`.

Um evento nunca é editado. Correção é um evento novo.
"""

from __future__ import annotations

import json
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Iterable, Mapping

from cantinho.core.clock import Clock, ensure_utc

__all__ = [
    "Event",
    "EventError",
    "UnknownKind",
    "InvalidPayload",
    "KINDS",
    "validate_payload",
    "make_event",
    "new_id",
    "format_timestamp",
    "parse_timestamp",
    "task_created",
    "task_completed",
    "task_archived",
    "session_started",
    "session_ended",
    "idea_captured",
    "day_checkin",
    "day_review",
]


class EventError(ValueError):
    """Base de todo erro de evento."""


class UnknownKind(EventError):
    """Kind que não existe no vocabulário do log."""


class InvalidPayload(EventError):
    """Payload que não bate com o formato do kind."""


# ---------------------------------------------------------------- timestamps

# Formato canônico: largura fixa, sempre UTC, sempre com microssegundos.
#
# A largura fixa importa. `occurred_at` é TEXT no SQLite, então a ordenação é
# lexicográfica; se o sufixo variasse ("+00:00" vs "Z") ou os microssegundos
# fossem omitidos quando zero, a ordem do log sairia errada.
#
# O sufixo é "+00:00" e não "Z" porque `fromisoformat` só aceita "Z" a partir
# do 3.11, e o alvo é 3.10+.
_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f+00:00"


def format_timestamp(moment: datetime) -> str:
    """Serializa para o formato canônico do banco."""
    return ensure_utc(moment).strftime(_TIMESTAMP_FORMAT)


def parse_timestamp(raw: str) -> datetime:
    """Lê um timestamp do banco de volta para datetime UTC."""
    try:
        return ensure_utc(datetime.fromisoformat(raw))
    except ValueError as exc:
        raise InvalidPayload(f"timestamp inválido: {raw!r}") from exc


def new_id() -> str:
    """Identificador novo. Usado para o uuid do evento e para ids de domínio."""
    return str(uuid_module.uuid4())


# --------------------------------------------------------------- validadores

_Check = Callable[[str, str, Any], None]


def _fail(kind: str, name: str, expected: str, value: Any) -> None:
    raise InvalidPayload(
        f"{kind}: campo {name!r} esperava {expected}, recebeu {value!r}"
    )


def _non_empty_str(kind: str, name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        _fail(kind, name, "texto não vazio", value)


def _any_str(kind: str, name: str, value: Any) -> None:
    if not isinstance(value, str):
        _fail(kind, name, "texto", value)


def _strict_bool(kind: str, name: str, value: Any) -> None:
    if not isinstance(value, bool):
        _fail(kind, name, "booleano", value)


def _strict_int(kind: str, name: str, value: Any) -> None:
    # bool é subclasse de int; aceitar True como nota de humor seria bug.
    if not isinstance(value, int) or isinstance(value, bool):
        _fail(kind, name, "inteiro", value)


def _iso_date(kind: str, name: str, value: Any) -> None:
    if not isinstance(value, str):
        _fail(kind, name, "data AAAA-MM-DD", value)
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail(kind, name, "data AAAA-MM-DD", value)


def _list_of_str(kind: str, name: str, value: Any) -> None:
    # Lista vazia é legítima: dia sem intenção declarada.
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        _fail(kind, name, "lista de textos não vazios", value)


@dataclass(frozen=True)
class _Spec:
    required: Mapping[str, _Check]
    optional: Mapping[str, _Check] = field(default_factory=dict)


KINDS: Mapping[str, _Spec] = {
    "task.created": _Spec(
        required={"id": _non_empty_str, "label": _non_empty_str},
        optional={"project": _non_empty_str},
    ),
    "task.completed": _Spec(required={"id": _non_empty_str}),
    "task.archived": _Spec(required={"id": _non_empty_str}),
    "session.started": _Spec(
        required={"id": _non_empty_str},
        optional={"task_id": _non_empty_str},
    ),
    "session.ended": _Spec(
        required={"id": _non_empty_str, "interrupted": _strict_bool},
        optional={"note": _any_str},
    ),
    "idea.captured": _Spec(
        required={"id": _non_empty_str, "text": _non_empty_str},
    ),
    "day.checkin": _Spec(
        required={"date": _iso_date, "intents": _list_of_str},
    ),
    "day.review": _Spec(
        required={"date": _iso_date, "mood": _strict_int, "energy": _strict_int},
        optional={"note": _any_str},
    ),
}


def validate_payload(kind: str, payload: Mapping[str, Any]) -> None:
    """Valida payload contra o spec do kind.

    Campo desconhecido é erro, não é ignorado: quase sempre é typo de nome de
    campo, e um evento gravado com typo fica no log para sempre.
    """
    spec = KINDS.get(kind)
    if spec is None:
        raise UnknownKind(f"kind desconhecido: {kind!r}")
    if not isinstance(payload, Mapping):
        raise InvalidPayload(f"{kind}: payload precisa ser objeto, recebeu {payload!r}")

    for name, check in spec.required.items():
        if name not in payload:
            raise InvalidPayload(f"{kind}: campo obrigatório {name!r} ausente")
        check(kind, name, payload[name])

    for name, check in spec.optional.items():
        if name in payload and payload[name] is not None:
            check(kind, name, payload[name])

    conhecidos = set(spec.required) | set(spec.optional)
    extras = sorted(set(payload) - conhecidos)
    if extras:
        raise InvalidPayload(f"{kind}: campos desconhecidos {extras}")


# -------------------------------------------------------------------- evento


@dataclass(frozen=True)
class Event:
    """Uma linha do log. Imutável por construção e por regra."""

    uuid: str
    device_id: str
    occurred_at: datetime
    kind: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        _non_empty_str("event", "uuid", self.uuid)
        _non_empty_str("event", "device_id", self.device_id)
        if not isinstance(self.occurred_at, datetime):
            _fail("event", "occurred_at", "datetime", self.occurred_at)
        validate_payload(self.kind, self.payload)
        # Normaliza para UTC e corta o alias com o dict de quem construiu.
        object.__setattr__(self, "occurred_at", ensure_utc(self.occurred_at))
        object.__setattr__(self, "payload", dict(self.payload))

    @property
    def sort_key(self) -> tuple[datetime, str]:
        """Ordem estável do log: tempo e, em empate, uuid."""
        return (self.occurred_at, self.uuid)

    def to_row(self) -> tuple[str, str, str, str, str]:
        """Serializa para a tupla de INSERT, na ordem das colunas."""
        return (
            self.uuid,
            self.device_id,
            format_timestamp(self.occurred_at),
            self.kind,
            json.dumps(self.payload, ensure_ascii=False, sort_keys=True),
        )

    @classmethod
    def from_row(cls, row: Iterable[Any]) -> "Event":
        """Reconstrói a partir de uma linha do banco."""
        try:
            uuid, device_id, occurred_at, kind, payload = tuple(row)
        except ValueError as exc:
            raise InvalidPayload(f"linha com formato inesperado: {row!r}") from exc
        try:
            decoded = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise InvalidPayload(f"payload não é JSON válido: {payload!r}") from exc
        return cls(
            uuid=uuid,
            device_id=device_id,
            occurred_at=parse_timestamp(occurred_at),
            kind=kind,
            payload=decoded,
        )


def make_event(
    clock: Clock,
    device_id: str,
    kind: str,
    payload: Mapping[str, Any],
) -> Event:
    """Monta um evento agora, pelo relógio injetado.

    Campos opcionais em `None` são descartados em vez de gravados como nulo:
    ausência e nulo devem ser a mesma coisa no log.
    """
    limpo = {name: value for name, value in payload.items() if value is not None}
    return Event(
        uuid=new_id(),
        device_id=device_id,
        occurred_at=clock.now(),
        kind=kind,
        payload=limpo,
    )


# ------------------------------------------------------ construtores por kind
#
# Os kinds que criam uma entidade geram o id do domínio quando ele é omitido.
# Os que se referem a algo existente exigem o id.


def task_created(
    clock: Clock,
    device_id: str,
    *,
    label: str,
    project: str | None = None,
    id: str | None = None,
) -> Event:
    return make_event(
        clock,
        device_id,
        "task.created",
        {"id": id or new_id(), "label": label, "project": project},
    )


def task_completed(clock: Clock, device_id: str, *, id: str) -> Event:
    return make_event(clock, device_id, "task.completed", {"id": id})


def task_archived(clock: Clock, device_id: str, *, id: str) -> Event:
    return make_event(clock, device_id, "task.archived", {"id": id})


def session_started(
    clock: Clock,
    device_id: str,
    *,
    task_id: str | None = None,
    id: str | None = None,
) -> Event:
    return make_event(
        clock,
        device_id,
        "session.started",
        {"id": id or new_id(), "task_id": task_id},
    )


def session_ended(
    clock: Clock,
    device_id: str,
    *,
    id: str,
    interrupted: bool = False,
    note: str | None = None,
) -> Event:
    return make_event(
        clock,
        device_id,
        "session.ended",
        {"id": id, "interrupted": interrupted, "note": note},
    )


def idea_captured(
    clock: Clock,
    device_id: str,
    *,
    text: str,
    id: str | None = None,
) -> Event:
    return make_event(
        clock,
        device_id,
        "idea.captured",
        {"id": id or new_id(), "text": text},
    )


def day_checkin(
    clock: Clock,
    device_id: str,
    *,
    date: str,
    intents: list[str],
) -> Event:
    return make_event(
        clock,
        device_id,
        "day.checkin",
        {"date": date, "intents": list(intents)},
    )


def day_review(
    clock: Clock,
    device_id: str,
    *,
    date: str,
    mood: int,
    energy: int,
    note: str | None = None,
) -> Event:
    return make_event(
        clock,
        device_id,
        "day.review",
        {"date": date, "mood": mood, "energy": energy, "note": note},
    )
