from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from cantinho.core.clock import FakeClock
from cantinho.core import events as ev
from cantinho.core.events import Event, InvalidPayload, UnknownKind

from conftest import DEVICE


def test_construtor_usa_o_relogio_injetado(clock: FakeClock) -> None:
    evento = ev.task_created(clock, DEVICE, label="escrever tese")
    assert evento.occurred_at == clock.now()

    clock.advance(timedelta(hours=1))
    depois = ev.task_created(clock, DEVICE, label="outra")
    assert depois.occurred_at == clock.now()
    assert depois.occurred_at > evento.occurred_at


def test_cada_evento_tem_uuid_proprio(clock: FakeClock) -> None:
    uuids = {ev.task_created(clock, DEVICE, label="a").uuid for _ in range(50)}
    assert len(uuids) == 50


def test_kinds_que_criam_entidade_geram_id(clock: FakeClock) -> None:
    assert ev.task_created(clock, DEVICE, label="a").payload["id"]
    assert ev.session_started(clock, DEVICE).payload["id"]
    assert ev.idea_captured(clock, DEVICE, text="ideia").payload["id"]


def test_id_de_dominio_pode_ser_fornecido(clock: FakeClock) -> None:
    evento = ev.task_created(clock, DEVICE, label="a", id="task-1")
    assert evento.payload["id"] == "task-1"


def test_opcional_ausente_nao_vira_nulo(clock: FakeClock) -> None:
    """Ausência e nulo têm que ser a mesma coisa no log."""
    evento = ev.task_created(clock, DEVICE, label="a")
    assert "project" not in evento.payload

    com_projeto = ev.task_created(clock, DEVICE, label="a", project="doutorado")
    assert com_projeto.payload["project"] == "doutorado"


def test_evento_e_imutavel(clock: FakeClock) -> None:
    evento = ev.task_created(clock, DEVICE, label="a")
    with pytest.raises(Exception):
        evento.kind = "task.completed"  # type: ignore[misc]


def test_payload_nao_fica_aliasado(clock: FakeClock) -> None:
    """Mexer no dict de origem não pode alterar um evento já construído."""
    origem: dict[str, Any] = {"id": "task-1", "label": "a"}
    evento = Event(
        uuid="u1",
        device_id=DEVICE,
        occurred_at=clock.now(),
        kind="task.created",
        payload=origem,
    )
    origem["label"] = "alterado"
    assert evento.payload["label"] == "a"


def test_occurred_at_normalizado_para_utc() -> None:
    saopaulo = timezone(timedelta(hours=-3))
    evento = Event(
        uuid="u1",
        device_id=DEVICE,
        occurred_at=datetime(2026, 3, 2, 6, 0, tzinfo=saopaulo),
        kind="task.completed",
        payload={"id": "task-1"},
    )
    assert evento.occurred_at == datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------- serialização


def _um_de_cada(clock: FakeClock) -> list[Event]:
    return [
        ev.task_created(clock, DEVICE, label="tese", project="doutorado"),
        ev.task_completed(clock, DEVICE, id="task-1"),
        ev.task_archived(clock, DEVICE, id="task-1"),
        ev.session_started(clock, DEVICE, task_id="task-1"),
        ev.session_ended(clock, DEVICE, id="s-1", interrupted=True, note="telefone"),
        ev.idea_captured(clock, DEVICE, text="trocar a fonte"),
        ev.day_checkin(clock, DEVICE, date="2026-03-02", intents=["ler", "escrever"]),
        ev.day_review(clock, DEVICE, date="2026-03-02", mood=4, energy=2, note="ok"),
    ]


def test_todos_os_kinds_tem_construtor(clock: FakeClock) -> None:
    assert {evento.kind for evento in _um_de_cada(clock)} == set(ev.KINDS)


@pytest.mark.parametrize("indice", range(8))
def test_round_trip_por_kind(clock: FakeClock, indice: int) -> None:
    original = _um_de_cada(clock)[indice]
    assert Event.from_row(original.to_row()) == original


def test_to_row_segue_a_ordem_das_colunas(clock: FakeClock) -> None:
    evento = ev.task_completed(clock, DEVICE, id="task-1")
    uuid, device_id, occurred_at, kind, payload = evento.to_row()
    assert uuid == evento.uuid
    assert device_id == DEVICE
    assert kind == "task.completed"
    assert payload == '{"id": "task-1"}'
    assert occurred_at == "2026-03-02T09:00:00.000000+00:00"


def test_timestamp_tem_largura_fixa(clock: FakeClock) -> None:
    """occurred_at é TEXT e a ordenação do log é lexicográfica.

    Se o formato encolhesse quando os microssegundos são zero, a ordem sairia
    errada. Este teste é o que segura isso.
    """
    redondo = ev.format_timestamp(datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc))
    quebrado = ev.format_timestamp(
        datetime(2026, 3, 2, 9, 0, 0, 123456, tzinfo=timezone.utc)
    )
    assert len(redondo) == len(quebrado)
    assert redondo < quebrado

    ordenado = sorted([quebrado, redondo])
    assert ordenado == [redondo, quebrado]


def test_from_row_recusa_json_invalido() -> None:
    with pytest.raises(InvalidPayload):
        Event.from_row(("u1", DEVICE, "2026-03-02T09:00:00.000000+00:00", "task.completed", "{"))


def test_from_row_recusa_timestamp_invalido() -> None:
    with pytest.raises(InvalidPayload):
        Event.from_row(("u1", DEVICE, "ontem", "task.completed", '{"id": "x"}'))


# ----------------------------------------------------------------- validação


def test_kind_desconhecido_levanta(clock: FakeClock) -> None:
    with pytest.raises(UnknownKind):
        ev.make_event(clock, DEVICE, "task.deleted", {"id": "task-1"})


PAYLOADS_INVALIDOS: list[tuple[str, dict[str, Any], str]] = [
    ("task.created", {"id": "t1"}, "label obrigatório ausente"),
    ("task.created", {"id": "t1", "label": ""}, "label vazio"),
    ("task.created", {"id": "t1", "label": "  "}, "label só com espaço"),
    ("task.created", {"id": "", "label": "a"}, "id vazio"),
    ("task.created", {"id": "t1", "label": 42}, "label não é texto"),
    ("task.created", {"id": "t1", "label": "a", "titulo": "x"}, "campo desconhecido"),
    ("task.created", {"id": "t1", "label": "a", "project": 7}, "opcional com tipo errado"),
    ("task.completed", {}, "id ausente"),
    ("session.ended", {"id": "s1"}, "interrupted ausente"),
    ("session.ended", {"id": "s1", "interrupted": "sim"}, "interrupted é texto"),
    ("session.ended", {"id": "s1", "interrupted": 1}, "interrupted é int"),
    ("idea.captured", {"id": "i1", "text": ""}, "texto vazio"),
    ("day.checkin", {"date": "02/03/2026", "intents": []}, "data fora do ISO"),
    ("day.checkin", {"date": "2026-13-45", "intents": []}, "data inexistente"),
    ("day.checkin", {"date": "2026-03-02", "intents": "ler"}, "intents não é lista"),
    ("day.checkin", {"date": "2026-03-02", "intents": [1]}, "intents com não texto"),
    ("day.review", {"date": "2026-03-02", "mood": 4}, "energy ausente"),
    ("day.review", {"date": "2026-03-02", "mood": True, "energy": 2}, "mood é bool"),
    ("day.review", {"date": "2026-03-02", "mood": 4.5, "energy": 2}, "mood é float"),
]


@pytest.mark.parametrize(
    "kind,payload,motivo",
    PAYLOADS_INVALIDOS,
    ids=[caso[2] for caso in PAYLOADS_INVALIDOS],
)
def test_payload_malformado_levanta(
    clock: FakeClock, kind: str, payload: dict[str, Any], motivo: str
) -> None:
    with pytest.raises(InvalidPayload):
        ev.make_event(clock, DEVICE, kind, payload)


def test_lista_de_intencoes_vazia_e_valida(clock: FakeClock) -> None:
    """Dia sem intenção declarada é um dia legítimo."""
    evento = ev.day_checkin(clock, DEVICE, date="2026-03-02", intents=[])
    assert evento.payload["intents"] == []


def test_evento_sem_device_id_levanta(clock: FakeClock) -> None:
    with pytest.raises(InvalidPayload):
        ev.make_event(clock, "", "task.completed", {"id": "t1"})
