"""Projeções que alimentam a UI: ordem do backlog, hoje, ideias, retrospectiva."""

from __future__ import annotations

from datetime import timedelta, timezone

import pytest

from cantinho.core import events as ev
from cantinho.core.clock import FakeClock
from cantinho.core.events import Event
from cantinho.core.projections import (
    TODAY_LIMIT,
    day_reviews,
    ideas,
    open_tasks,
    review_for,
    sessions_on,
    today_tasks,
)

from conftest import DEVICE


def criar(clock: FakeClock, quantidade: int) -> tuple[list[Event], list[str]]:
    log: list[Event] = []
    ids: list[str] = []
    for indice in range(quantidade):
        evento = ev.task_created(clock, DEVICE, label=f"t{indice}")
        log.append(evento)
        ids.append(evento.payload["id"])
        clock.advance(timedelta(minutes=1))
    return log, ids


# ------------------------------------------------------------ ordem manual


def test_sem_arrasto_a_ordem_e_a_de_criacao(clock: FakeClock) -> None:
    log, _ = criar(clock, 4)
    assert [t.label for t in open_tasks(log)] == ["t0", "t1", "t2", "t3"]


def test_arrasto_define_a_ordem(clock: FakeClock) -> None:
    log, ids = criar(clock, 4)
    log.append(
        ev.backlog_reordered(clock, DEVICE, order=[ids[3], ids[0], ids[2], ids[1]])
    )
    assert [t.label for t in open_tasks(log)] == ["t3", "t0", "t2", "t1"]


def test_ultimo_arrasto_vence(clock: FakeClock) -> None:
    log, ids = criar(clock, 3)
    log.append(ev.backlog_reordered(clock, DEVICE, order=[ids[2], ids[1], ids[0]]))
    clock.advance(timedelta(minutes=5))
    log.append(ev.backlog_reordered(clock, DEVICE, order=[ids[1], ids[0], ids[2]]))
    assert [t.label for t in open_tasks(log)] == ["t1", "t0", "t2"]


def test_tarefa_nova_entra_no_fim(clock: FakeClock) -> None:
    """Aparecer no meio da lista sem ninguém ter pedido seria pior."""
    log, ids = criar(clock, 3)
    log.append(ev.backlog_reordered(clock, DEVICE, order=[ids[2], ids[1], ids[0]]))
    clock.advance(timedelta(minutes=5))
    log.append(ev.task_created(clock, DEVICE, label="recem-chegada"))
    assert [t.label for t in open_tasks(log)] == ["t2", "t1", "t0", "recem-chegada"]


def test_ordem_ignora_id_que_saiu_do_backlog(clock: FakeClock) -> None:
    """Concluir uma tarefa não invalida a ordem das outras."""
    log, ids = criar(clock, 3)
    log.append(ev.backlog_reordered(clock, DEVICE, order=[ids[2], ids[1], ids[0]]))
    log.append(ev.task_completed(clock, DEVICE, id=ids[1]))
    assert [t.label for t in open_tasks(log)] == ["t2", "t0"]


def test_ordem_com_id_inexistente_nao_quebra(clock: FakeClock) -> None:
    log, ids = criar(clock, 2)
    log.append(
        ev.backlog_reordered(clock, DEVICE, order=["fantasma", ids[1], ids[0]])
    )
    assert [t.label for t in open_tasks(log)] == ["t1", "t0"]


# -------------------------------------------------------------------- hoje


def test_hoje_para_em_cinco(clock: FakeClock) -> None:
    log, _ = criar(clock, 9)
    assert len(today_tasks(log)) == TODAY_LIMIT
    assert [t.label for t in today_tasks(log)] == ["t0", "t1", "t2", "t3", "t4"]


def test_hoje_com_backlog_curto(clock: FakeClock) -> None:
    log, _ = criar(clock, 2)
    assert len(today_tasks(log)) == 2


def test_hoje_segue_o_arrasto(clock: FakeClock) -> None:
    log, ids = criar(clock, 7)
    log.append(ev.backlog_reordered(clock, DEVICE, order=list(reversed(ids))))
    assert [t.label for t in today_tasks(log)] == ["t6", "t5", "t4", "t3", "t2"]


# ------------------------------------------------------------------ ideias


def test_ideias_da_mais_recente_para_a_mais_antiga(clock: FakeClock) -> None:
    log = []
    for texto in ["primeira", "segunda", "terceira"]:
        log.append(ev.idea_captured(clock, DEVICE, text=texto))
        clock.advance(timedelta(minutes=2))
    assert [i.text for i in ideas(log)] == ["terceira", "segunda", "primeira"]


def test_ideia_nao_vira_tarefa_sozinha(clock: FakeClock) -> None:
    """Captura é captura. Virar tarefa é decisão posterior do usuário."""
    log = [ev.idea_captured(clock, DEVICE, text="uma ideia")]
    assert open_tasks(log) == []
    assert len(ideas(log)) == 1


# --------------------------------------------------------------- sessões do dia


def test_sessoes_do_dia_usam_o_fuso_local(clock: FakeClock) -> None:
    """23h em São Paulo é 02h UTC do dia seguinte. O dia é o do usuário."""
    saopaulo = timezone(timedelta(hours=-3))
    inicio = ev.session_started(clock, DEVICE)
    clock.advance(timedelta(minutes=30))
    fim = ev.session_ended(clock, DEVICE, id=inicio.payload["id"])
    log = [inicio, fim]

    dia_local = fim.occurred_at.astimezone(saopaulo).date()
    assert len(sessions_on(log, dia_local, saopaulo)) == 1
    assert sessions_on(log, dia_local + timedelta(days=1), saopaulo) == []


def test_sessao_aberta_fica_fora_do_dia(clock: FakeClock) -> None:
    log = [ev.session_started(clock, DEVICE)]
    hoje = clock.now().date()
    assert sessions_on(log, hoje, timezone.utc) == []


# ------------------------------------------------------------ retrospectiva


def test_revisar_de_novo_corrige(clock: FakeClock) -> None:
    log = [ev.day_review(clock, DEVICE, date="2026-03-02", mood=2, energy=2)]
    clock.advance(timedelta(hours=1))
    log.append(
        ev.day_review(clock, DEVICE, date="2026-03-02", mood=4, energy=3, note="melhorou")
    )

    revisao = day_reviews(log)["2026-03-02"]
    assert (revisao.mood, revisao.energy, revisao.note) == (4, 3, "melhorou")
    # Correção é evento novo, não edição: os dois continuam no log.
    assert len([e for e in log if e.kind == "day.review"]) == 2


def test_review_for_sem_revisao(clock: FakeClock) -> None:
    assert review_for([], clock.now().date()) is None


def test_revisoes_de_dias_diferentes_nao_se_misturam(clock: FakeClock) -> None:
    log = [
        ev.day_review(clock, DEVICE, date="2026-03-02", mood=2, energy=2),
        ev.day_review(clock, DEVICE, date="2026-03-03", mood=5, energy=4),
    ]
    revisoes = day_reviews(log)
    assert revisoes["2026-03-02"].mood == 2
    assert revisoes["2026-03-03"].mood == 5
