"""Um banco de provas para **todas** as projeções, montado uma vez.

As projeções são o coração do projeto: `events -> estado`, função pura,
idempotente e determinística. Várias propriedades valem para todas elas ao
mesmo tempo — log vazio não quebra, a entrada não é consumida nem alterada, a
ordem de chegada não importa, o `device_id` não é olhado — e cada uma dessas
propriedades estava sendo conferida com uma lista escrita à mão.

O problema de lista escrita à mão não é o tamanho, é o que ela **não** diz: o
cadeado do merge (`test_merge.py`) provava que cinco projeções ignoram o
`device_id`, e havia treze. As oito de fora não estavam certas nem erradas —
estavam sem cadeado, que é a situação que o arquivo inteiro existe para evitar.
E uma projeção nova nasceria fora de todas as listas, em silêncio.

Aqui o registro é um só, e um teste de completude falha enquanto uma projeção
pública não estiver nele. De uma montagem saem muitas confirmações: cada
propriedade roda sobre as treze, e uma projeção nova entra em todas as provas
de uma vez.

Quem usa: `test_projecoes_invariantes.py` (a bateria de propriedades),
`test_merge.py` (o cadeado do `device_id`) e `test_store.py` (o estado
reconstruído depois de reabrir o banco).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Callable, Iterable

from cantinho.core import events as ev
from cantinho.core import projections as proj
from cantinho.core.clock import FakeClock
from cantinho.core.events import Event

# O fuso das duas máquinas do projeto. Fixo de propósito: o recorte por dia é
# local, e um teste que usasse o fuso da máquina passaria ou falharia conforme
# onde roda.
SAOPAULO = timezone(timedelta(hours=-3))

# Meio-dia em São Paulo, para que todo o log de prova caia no mesmo dia local
# tanto em UTC quanto aqui — as projeções por dia (`completed_on`, `minutes_on`,
# `sessions_on`, `review_for`) precisam disso para dizer alguma coisa.
INICIO_DA_PROVA = datetime(2026, 3, 2, 15, 0, tzinfo=timezone.utc)

Projecao = Callable[[Iterable[Event]], object]


def log_de_prova(device: str = "device-de-prova") -> tuple[list[Event], datetime]:
    """Um dia de uso que faz **toda** projeção ter algo a dizer.

    Passa por todos os kinds do log, e não por conveniência: uma propriedade
    conferida sobre um resultado vazio passa sem provar nada. Quem garante que
    isso continua verdade é `test_toda_projecao_fala_no_log_de_prova`.

    Devolve o log e o instante final, que é o "agora" das projeções que
    precisam de um.
    """
    clock = FakeClock(INICIO_DA_PROVA)
    log: list[Event] = []

    entregue = ev.task_created(clock, device, label="revisar o capitulo 3")
    pendente = ev.task_created(clock, device, label="ler o artigo novo", project="doutorado")
    largada = ev.task_created(clock, device, label="ideia velha")
    log += [entregue, pendente, largada]

    clock.advance(timedelta(minutes=1))
    log.append(ev.task_renamed(clock, device, id=entregue.payload["id"],
                               label="revisar o capítulo 3"))
    log.append(ev.backlog_reordered(clock, device,
                                    order=[pendente.payload["id"], entregue.payload["id"]]))
    log.append(ev.day_checkin(clock, device,
                              date=clock.now().astimezone(SAOPAULO).date().isoformat(),
                              intents=["escrever", "ler"]))

    # Quatro horas de foco: o bastante para a planta sair do estágio 0.
    for minutos, interrompida in ((60, False), (60, False), (60, True), (60, False)):
        inicio = ev.session_started(clock, device, task_id=entregue.payload["id"])
        clock.advance(timedelta(minutes=minutos))
        log += [inicio, ev.session_ended(clock, device, id=inicio.payload["id"],
                                         interrupted=interrompida,
                                         note="travou na bibliografia" if interrompida else None)]
        clock.advance(timedelta(minutes=2))

    log.append(ev.task_completed(clock, device, id=entregue.payload["id"]))
    log.append(ev.task_archived(clock, device, id=largada.payload["id"]))

    aproveitada = ev.idea_captured(clock, device, text="trocar a fonte do editor")
    solta = ev.idea_captured(clock, device, text="mudar o abajur de lugar")
    descartada = ev.idea_captured(clock, device, text="não era nada")
    log += [aproveitada, solta, descartada]

    clock.advance(timedelta(minutes=1))
    log.append(ev.idea_promoted(clock, device, id=aproveitada.payload["id"],
                                task_id=pendente.payload["id"]))
    log.append(ev.idea_archived(clock, device, id=descartada.payload["id"]))

    log.append(ev.day_review(clock, device,
                             date=clock.now().astimezone(SAOPAULO).date().isoformat(),
                             mood=4, energy=3, note="dia bom"))

    return log, clock.now()


def dia_da_prova(agora: datetime) -> date:
    """O dia local a que o log de prova pertence."""
    return agora.astimezone(SAOPAULO).date()


def chamadas(agora: datetime) -> dict[str, Projecao]:
    """Toda projeção pública reduzida à mesma forma: `eventos -> resultado`.

    As que precisam de `now`, de `day` ou de fuso recebem os do banco de provas
    aqui, e não de quem chama — assim cada propriedade se escreve uma vez só,
    sem saber a assinatura de ninguém.
    """
    dia = dia_da_prova(agora)
    return {
        "open_tasks": proj.open_tasks,
        "today_tasks": proj.today_tasks,
        "completed_tasks": proj.completed_tasks,
        "sessions": proj.sessions,
        "ideas": proj.ideas,
        "day_reviews": proj.day_reviews,
        "shelf_objects": proj.shelf_objects,
        "focus_minutes_14d": lambda eventos: proj.focus_minutes_14d(eventos, agora),
        "plant_stage": lambda eventos: proj.plant_stage(eventos, agora),
        "completed_on": lambda eventos: proj.completed_on(eventos, dia, SAOPAULO),
        "sessions_on": lambda eventos: proj.sessions_on(eventos, dia, SAOPAULO),
        "minutes_on": lambda eventos: proj.minutes_on(eventos, dia, SAOPAULO),
        "review_for": lambda eventos: proj.review_for(eventos, dia),
    }


# Os nomes do registro, em ordem fixa: é por eles que a bateria de
# propriedades se parametriza, e id de teste que muda de ordem entre execuções
# atrapalha justamente quem está lendo uma falha.
NOMES: tuple[str, ...] = tuple(sorted(chamadas(INICIO_DA_PROVA)))


def projecoes_publicas() -> set[str]:
    """As funções de `projections.__all__` — o que o registro tem que cobrir.

    Sai de `__all__` e não de uma lista escrita aqui: é o próprio módulo
    dizendo o que ele oferece, então uma projeção nova aparece sozinha e o
    teste de completude cobra o registro dela.
    """
    return {
        nome
        for nome in proj.__all__
        if callable(getattr(proj, nome)) and not isinstance(getattr(proj, nome), type)
    }


def estado(eventos: Iterable[Event], agora: datetime) -> dict[str, object]:
    """Tudo o que as projeções dizem sobre um log, de uma vez.

    É o que torna comparável "este log e aquele dão a mesma tela": duas
    chamadas, uma igualdade, treze projeções dentro.
    """
    materializado = list(eventos)
    return {nome: chamada(materializado) for nome, chamada in chamadas(agora).items()}
