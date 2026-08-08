"""Projeções: `events -> estado`.

Funções puras. Nenhuma toca banco, arquivo, relógio global ou Qt. O instante
"agora" entra como argumento justamente para que a janela móvel seja testável.

Nada aqui é persistido. O estado é recalculado no startup e a cada evento novo.
Toda função ordena a entrada por conta própria, então a ordem em que os eventos
chegam não muda o resultado.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, tzinfo
from typing import Iterable

from cantinho.core.clock import ensure_utc
from cantinho.core.events import Event

__all__ = [
    "Task",
    "Session",
    "Idea",
    "DayReview",
    "ShelfObject",
    "SHELF_OBJECT_TYPES",
    "FOCUS_WINDOW",
    "PLANT_THRESHOLDS_MINUTES",
    "TODAY_LIMIT",
    "open_tasks",
    "today_tasks",
    "completed_tasks",
    "sessions",
    "sessions_on",
    "focus_minutes_14d",
    "plant_stage",
    "shelf_objects",
    "ideas",
    "day_reviews",
    "review_for",
]

FOCUS_WINDOW = timedelta(days=14)

# "Hoje" são os primeiros itens do backlog, e são no máximo cinco. O limite é
# a feature: uma lista de hoje que aceita tudo não é uma lista de hoje.
TODAY_LIMIT = 5

# Cortes de estágio da planta em minutos: 0h / 3h / 8h / 16h / 30h.
PLANT_THRESHOLDS_MINUTES: tuple[int, ...] = (0, 180, 480, 960, 1800)

# Catálogo da estante: são os ids dos objetos desenhados na camada
# `objetos_estante` dos SVGs de cena. O tipo é literalmente qual arte usar.
#
# Só pode crescer no fim. Inserir ou reordenar mudaria o objeto de tarefas já
# concluídas, e o quarto tem que ser sempre o mesmo.
SHELF_OBJECT_TYPES: tuple[str, ...] = (
    "obj_0",
    "obj_1",
    "obj_2",
    "obj_3",
    "obj_4",
    "obj_5",
)


@dataclass(frozen=True)
class Task:
    id: str
    label: str
    project: str | None
    created_at: datetime
    completed_at: datetime | None = None
    archived_at: datetime | None = None


@dataclass(frozen=True)
class Session:
    id: str
    task_id: str | None
    started_at: datetime
    ended_at: datetime | None = None
    interrupted: bool = False
    note: str | None = None

    @property
    def duration(self) -> timedelta | None:
        """Duração da sessão, ou None se ela ainda está aberta.

        Nunca negativa: se o relógio do sistema andar para trás no meio de uma
        sessão, o resultado é zero em vez de lixo.
        """
        if self.ended_at is None:
            return None
        return max(self.ended_at - self.started_at, timedelta(0))

    @property
    def duration_minutes(self) -> float:
        delta = self.duration
        return 0.0 if delta is None else delta.total_seconds() / 60.0


@dataclass(frozen=True)
class Idea:
    """Uma linha do mural.

    Uma ideia aproveitada não sai do mural: ela continua lá, riscada. Some do
    mural só o que foi descartado de propósito — e mesmo isso é um evento novo,
    não um apagamento.
    """

    id: str
    text: str
    captured_at: datetime
    task_id: str | None = None
    promoted_at: datetime | None = None
    archived_at: datetime | None = None

    @property
    def used(self) -> bool:
        return self.promoted_at is not None


@dataclass(frozen=True)
class DayReview:
    date: str
    mood: int
    energy: int
    note: str | None
    reviewed_at: datetime


@dataclass(frozen=True)
class ShelfObject:
    task_id: str
    object_type: str
    label: str
    placed_at: datetime


def _ordered(events: Iterable[Event]) -> list[Event]:
    return sorted(events, key=lambda event: event.sort_key)


def _index_tasks(events: Iterable[Event]) -> dict[str, Task]:
    """Reduz o log ao estado atual de cada tarefa.

    Duas passadas, e não uma. A criação e a conclusão de uma tarefa podem cair
    no mesmo microssegundo — timer rápido, relógio grosso — e aí o desempate
    por uuid é sorteio: metade das vezes a conclusão viria antes da criação e
    seria descartada por falar de uma tarefa que "ainda não existe". Coletando
    todas as criações primeiro, a ordem relativa entre um evento e o que ele
    referencia deixa de importar.

    Dentro de cada passada o primeiro evento vence. O log é append-only e não
    deveria ter duplicata, mas se tiver, ignorar as repetições mantém a
    projeção idempotente.
    """
    ordenados = _ordered(events)

    tasks: dict[str, Task] = {}
    for event in ordenados:
        if event.kind == "task.created":
            task_id = event.payload["id"]
            if task_id not in tasks:
                tasks[task_id] = Task(
                    id=task_id,
                    label=event.payload["label"],
                    project=event.payload.get("project"),
                    created_at=event.occurred_at,
                )

    for event in ordenados:
        if event.kind not in ("task.completed", "task.archived"):
            continue
        atual = tasks.get(event.payload["id"])
        if atual is None:
            # Referência a tarefa que não existe no log. Dado corrompido:
            # ignorar é melhor que inventar uma tarefa sem rótulo.
            continue
        if event.kind == "task.completed" and atual.completed_at is None:
            tasks[atual.id] = replace(atual, completed_at=event.occurred_at)
        elif event.kind == "task.archived" and atual.archived_at is None:
            tasks[atual.id] = replace(atual, archived_at=event.occurred_at)

    return tasks


def _manual_order(events: Iterable[Event]) -> list[str]:
    """Última ordem escolhida à mão, ou lista vazia se nunca arrastaram nada."""
    ultima: list[str] = []
    for event in _ordered(events):
        if event.kind == "backlog.reordered":
            ultima = list(event.payload["order"])
    return ultima


def open_tasks(events: Iterable[Event]) -> list[Task]:
    """Backlog: criadas, não concluídas e não arquivadas.

    A ordem é a que o usuário arrastou. Tarefa criada depois do último arrasto
    entra no fim, por ordem de criação — aparecer no meio da lista sem ninguém
    ter pedido seria pior que aparecer no fim.
    """
    materializados = _ordered(events)
    abertas = {
        task.id: task
        for task in _index_tasks(materializados).values()
        if task.completed_at is None and task.archived_at is None
    }

    ordenadas: list[Task] = []
    for task_id in _manual_order(materializados):
        task = abertas.pop(task_id, None)
        if task is not None:
            ordenadas.append(task)

    restantes = sorted(abertas.values(), key=lambda task: (task.created_at, task.id))
    return ordenadas + restantes


def today_tasks(events: Iterable[Event]) -> list[Task]:
    """O topo do backlog, limitado a cinco itens."""
    return open_tasks(events)[:TODAY_LIMIT]


def completed_tasks(events: Iterable[Event]) -> list[Task]:
    """Concluídas, em ordem de conclusão.

    Arquivar depois de concluir não remove a tarefa daqui: a entrega aconteceu.
    """
    concluidas = [
        task for task in _index_tasks(events).values() if task.completed_at is not None
    ]
    return sorted(concluidas, key=lambda task: (task.completed_at, task.id))  # type: ignore[arg-type]


def sessions(events: Iterable[Event]) -> list[Session]:
    """Sessões do log, com duração calculada. Inclui as ainda abertas.

    `session.ended` sem `session.started` correspondente é descartado: sem
    início não há duração.

    Duas passadas pelo mesmo motivo de `_index_tasks`: início e fim podem
    compartilhar timestamp, e o fim não pode depender de sortear a ordem certa.
    """
    ordenados = _ordered(events)

    encontradas: dict[str, Session] = {}
    for event in ordenados:
        if event.kind == "session.started":
            session_id = event.payload["id"]
            if session_id not in encontradas:
                encontradas[session_id] = Session(
                    id=session_id,
                    task_id=event.payload.get("task_id"),
                    started_at=event.occurred_at,
                )

    for event in ordenados:
        if event.kind != "session.ended":
            continue
        atual = encontradas.get(event.payload["id"])
        if atual is not None and atual.ended_at is None:
            encontradas[atual.id] = replace(
                atual,
                ended_at=event.occurred_at,
                interrupted=event.payload["interrupted"],
                note=event.payload.get("note"),
            )

    return sorted(encontradas.values(), key=lambda s: (s.started_at, s.id))


def focus_minutes_14d(events: Iterable[Event], now: datetime) -> float:
    """Minutos de sessão encerrada na janela móvel de 14 dias.

    Duas decisões que valem explicitar:

    - Sessão interrompida conta. O tempo foi gasto, e zerar o esforço de quem
      parou aos 24 de 25 minutos seria penalidade explícita — que é justamente
      o que o decaimento da janela dispensa.
    - A sessão é atribuída ao instante em que terminou, inteira. Sessão aberta
      ainda não conta; ela entra quando encerrar.

    A janela é `(now - 14d, now]`.
    """
    momento = ensure_utc(now)
    inicio = momento - FOCUS_WINDOW
    total = 0.0
    for session in sessions(events):
        if session.ended_at is None:
            continue
        if inicio < session.ended_at <= momento:
            total += session.duration_minutes
    return total


def plant_stage(events: Iterable[Event], now: datetime) -> int:
    """Estágio da planta, 0 a 4, a partir do foco dos últimos 14 dias.

    Cai sozinho quando o foco sai da janela. Não existe penalidade além disso.
    """
    minutos = focus_minutes_14d(events, now)
    estagio = 0
    for indice, corte in enumerate(PLANT_THRESHOLDS_MINUTES):
        if minutos >= corte:
            estagio = indice
    return estagio


def _object_type_for(task_id: str) -> str:
    """Escolhe o objeto da estante pelo uuid da tarefa.

    blake2s e não `hash()`: o hash embutido do Python é aleatorizado por
    processo (PYTHONHASHSEED), o que trocaria os objetos da estante a cada
    abertura do app.
    """
    digest = hashlib.blake2s(task_id.encode("utf-8"), digest_size=8).digest()
    return SHELF_OBJECT_TYPES[int.from_bytes(digest, "big") % len(SHELF_OBJECT_TYPES)]


def sessions_on(events: Iterable[Event], day: date, tz: tzinfo) -> list[Session]:
    """Sessões encerradas em um dia do calendário local.

    O banco guarda UTC; o dia é o do usuário. A conversão acontece aqui, na
    apresentação, e não na gravação.
    """
    return [
        session
        for session in sessions(events)
        if session.ended_at is not None
        and session.ended_at.astimezone(tz).date() == day
    ]


def ideas(events: Iterable[Event]) -> list[Idea]:
    """Mural de ideias: as ainda soltas primeiro, as aproveitadas depois.

    Dentro de cada grupo, da mais recente para a mais antiga. Descartadas não
    aparecem.

    Duas passadas pelo mesmo motivo de `_index_tasks`: capturar uma ideia e
    promovê-la podem cair no mesmo microssegundo, e a promoção não pode depender
    de sortear a ordem certa.
    """
    ordenados = _ordered(events)

    capturadas: dict[str, Idea] = {}
    for event in ordenados:
        if event.kind == "idea.captured":
            ideia_id = event.payload["id"]
            if ideia_id not in capturadas:
                capturadas[ideia_id] = Idea(
                    id=ideia_id,
                    text=event.payload["text"],
                    captured_at=event.occurred_at,
                )

    for event in ordenados:
        if event.kind not in ("idea.promoted", "idea.archived"):
            continue
        atual = capturadas.get(event.payload["id"])
        if atual is None:
            continue
        if event.kind == "idea.promoted" and atual.promoted_at is None:
            capturadas[atual.id] = replace(
                atual,
                promoted_at=event.occurred_at,
                task_id=event.payload["task_id"],
            )
        elif event.kind == "idea.archived" and atual.archived_at is None:
            capturadas[atual.id] = replace(atual, archived_at=event.occurred_at)

    vivas = [ideia for ideia in capturadas.values() if ideia.archived_at is None]
    soltas = sorted(
        (ideia for ideia in vivas if not ideia.used),
        key=lambda ideia: (ideia.captured_at, ideia.id),
        reverse=True,
    )
    usadas = sorted(
        (ideia for ideia in vivas if ideia.used),
        key=lambda ideia: (ideia.promoted_at, ideia.id),  # type: ignore[arg-type]
        reverse=True,
    )
    return soltas + usadas


def day_reviews(events: Iterable[Event]) -> dict[str, DayReview]:
    """Retrospectivas por data. A última do dia vence: revisar de novo corrige."""
    revisoes: dict[str, DayReview] = {}
    for event in _ordered(events):
        if event.kind != "day.review":
            continue
        revisoes[event.payload["date"]] = DayReview(
            date=event.payload["date"],
            mood=event.payload["mood"],
            energy=event.payload["energy"],
            note=event.payload.get("note"),
            reviewed_at=event.occurred_at,
        )
    return revisoes


def review_for(events: Iterable[Event], day: date) -> DayReview | None:
    return day_reviews(events).get(day.isoformat())


def shelf_objects(events: Iterable[Event]) -> list[ShelfObject]:
    """Estante: um objeto por tarefa concluída, em ordem de conclusão.

    Objetos são permanentes. Arquivar a tarefa depois não tira o objeto.
    """
    return [
        ShelfObject(
            task_id=task.id,
            object_type=_object_type_for(task.id),
            label=task.label,
            placed_at=task.completed_at,  # type: ignore[arg-type]
        )
        for task in completed_tasks(events)
    ]
