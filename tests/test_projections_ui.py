"""Projeções que alimentam a UI: ordem do backlog, hoje, ideias, retrospectiva."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from cantinho.core import events as ev
from cantinho.core.clock import FakeClock
from cantinho.core.events import Event
from cantinho.core.projections import (
    TODAY_LIMIT,
    completed_on,
    day_reviews,
    ideas,
    minutes_on,
    open_tasks,
    review_for,
    sessions_on,
    shelf_objects,
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


def _ideia(clock: FakeClock, texto: str) -> tuple[list, str]:
    evento = ev.idea_captured(clock, DEVICE, text=texto)
    return [evento], evento.payload["id"]


def test_ideia_aproveitada_continua_no_mural(clock: FakeClock) -> None:
    """Riscada, não apagada: o mural é o registro de onde a tarefa veio."""
    log, ideia_id = _ideia(clock, "trocar a fonte")
    clock.advance(timedelta(minutes=5))
    log.append(ev.idea_promoted(clock, DEVICE, id=ideia_id, task_id="task-9"))

    mural = ideas(log)
    assert len(mural) == 1
    assert mural[0].used
    assert mural[0].task_id == "task-9"


def test_ideia_descartada_sai_do_mural(clock: FakeClock) -> None:
    log, ideia_id = _ideia(clock, "não era nada")
    clock.advance(timedelta(minutes=1))
    log.append(ev.idea_archived(clock, DEVICE, id=ideia_id))
    assert ideas(log) == []


def test_aproveitadas_descem_para_o_fim_do_mural(clock: FakeClock) -> None:
    """O que ainda está solto fica em cima; o que já rendeu, embaixo."""
    log: list = []
    ids = {}
    for texto in ["primeira", "segunda", "terceira"]:
        evento = ev.idea_captured(clock, DEVICE, text=texto)
        log.append(evento)
        ids[texto] = evento.payload["id"]
        clock.advance(timedelta(minutes=2))

    log.append(ev.idea_promoted(clock, DEVICE, id=ids["terceira"], task_id="t1"))

    assert [i.text for i in ideas(log)] == ["segunda", "primeira", "terceira"]


def test_promocao_repetida_nao_muda_o_mural(clock: FakeClock) -> None:
    """Idempotência: o mesmo lote reaplicado dá o mesmo mural."""
    log, ideia_id = _ideia(clock, "uma ideia")
    clock.advance(timedelta(minutes=1))
    primeira = ev.idea_promoted(clock, DEVICE, id=ideia_id, task_id="task-1")
    clock.advance(timedelta(minutes=1))
    segunda = ev.idea_promoted(clock, DEVICE, id=ideia_id, task_id="task-2")

    assert ideas(log + [primeira])[0].task_id == "task-1"
    assert ideas(log + [primeira, segunda])[0].task_id == "task-1"


def test_promocao_de_ideia_inexistente_e_ignorada(clock: FakeClock) -> None:
    log = [ev.idea_promoted(clock, DEVICE, id="não existe", task_id="task-1")]
    assert ideas(log) == []


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


# ------------------------------------------------------------------ renomear
#
# Corrigir o texto de uma tarefa é um fato novo, e não uma edição: o
# `task.created` continua no log exatamente como foi escrito.


def test_renomear_troca_o_rotulo(clock: FakeClock) -> None:
    criacao = ev.task_created(clock, DEVICE, label="revisar o capitulo 3")
    task_id = criacao.payload["id"]
    clock.advance(timedelta(minutes=1))
    log = [criacao, ev.task_renamed(clock, DEVICE, id=task_id, label="revisar o capítulo 3")]

    assert [t.label for t in open_tasks(log)] == ["revisar o capítulo 3"]
    assert log[0].payload["label"] == "revisar o capitulo 3"


def test_o_ultimo_renome_vence(clock: FakeClock) -> None:
    """Ao contrário do resto da projeção: corrigir duas vezes vale a segunda."""
    criacao = ev.task_created(clock, DEVICE, label="a")
    task_id = criacao.payload["id"]
    log = [criacao]
    for texto in ("b", "c"):
        clock.advance(timedelta(minutes=1))
        log.append(ev.task_renamed(clock, DEVICE, id=task_id, label=texto))

    assert [t.label for t in open_tasks(log)] == ["c"]


def test_renomear_nao_muda_o_objeto_da_estante(clock: FakeClock) -> None:
    """O desenho vem do hash do id. O texto não entra na conta."""
    criacao = ev.task_created(clock, DEVICE, label="a")
    task_id = criacao.payload["id"]
    clock.advance(timedelta(minutes=1))
    conclusao = ev.task_completed(clock, DEVICE, id=task_id)

    sem_renome = shelf_objects([criacao, conclusao])[0].object_type
    com_renome = shelf_objects(
        [criacao, ev.task_renamed(clock, DEVICE, id=task_id, label="outro"), conclusao]
    )[0].object_type
    assert sem_renome == com_renome


def test_renome_de_tarefa_inexistente_e_ignorado(clock: FakeClock) -> None:
    log = [ev.task_renamed(clock, DEVICE, id="fantasma", label="x")]
    assert open_tasks(log) == []


# --------------------------------------------------------------- dia a dia


def test_entregas_do_dia_saem_pelo_calendario_local(clock: FakeClock) -> None:
    """O banco guarda UTC; o dia é o de quem está olhando."""
    saopaulo = timezone(timedelta(hours=-3))
    criacao = ev.task_created(clock, DEVICE, label="a")
    # 2026-03-02 09:00 UTC é ainda 06:00 em São Paulo, mesmo dia.
    log = [criacao, ev.task_completed(clock, DEVICE, id=criacao.payload["id"])]

    assert [t.label for t in completed_on(log, date(2026, 3, 2), saopaulo)] == ["a"]
    assert completed_on(log, date(2026, 3, 1), saopaulo) == []


def test_entrega_de_madrugada_conta_no_dia_de_ca(clock: FakeClock) -> None:
    saopaulo = timezone(timedelta(hours=-3))
    criacao = ev.task_created(clock, DEVICE, label="a")
    # 02:00 UTC do dia 3 é 23:00 do dia 2 em São Paulo.
    clock.set(datetime(2026, 3, 3, 2, 0, tzinfo=timezone.utc))
    log = [criacao, ev.task_completed(clock, DEVICE, id=criacao.payload["id"])]

    assert len(completed_on(log, date(2026, 3, 2), saopaulo)) == 1
    assert completed_on(log, date(2026, 3, 3), saopaulo) == []


def test_minutos_do_dia_somam_as_sessoes(clock: FakeClock) -> None:
    log = []
    for minutos in (25, 35):
        inicio = ev.session_started(clock, DEVICE)
        clock.advance(timedelta(minutes=minutos))
        log += [inicio, ev.session_ended(clock, DEVICE, id=inicio.payload["id"])]
        clock.advance(timedelta(minutes=5))

    assert minutes_on(log, date(2026, 3, 2), timezone.utc) == pytest.approx(60)
    assert minutes_on(log, date(2026, 3, 3), timezone.utc) == 0
