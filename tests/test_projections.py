from __future__ import annotations

import os
import random
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from cantinho.core import events as ev
from cantinho.core.clock import FakeClock
from cantinho.core.events import Event
from cantinho.core.projections import (
    PLANT_THRESHOLDS_MINUTES,
    SHELF_OBJECT_TYPES,
    completed_tasks,
    focus_minutes_14d,
    open_tasks,
    plant_stage,
    sessions,
    shelf_objects,
)

from conftest import DEVICE

RAIZ = Path(__file__).resolve().parents[1]


def sessao(clock: FakeClock, minutos: float, *, task_id: str | None = None,
           interrupted: bool = False) -> list[Event]:
    """Uma sessão completa de `minutos`, terminando no relógio atual."""
    inicio = ev.session_started(clock, DEVICE, task_id=task_id)
    clock.advance(timedelta(minutes=minutos))
    fim = ev.session_ended(clock, DEVICE, id=inicio.payload["id"], interrupted=interrupted)
    return [inicio, fim]


# -------------------------------------------------------------------- tarefas


def test_open_tasks_exclui_concluida_e_arquivada(clock: FakeClock) -> None:
    aberta = ev.task_created(clock, DEVICE, label="aberta")
    feita = ev.task_created(clock, DEVICE, label="feita")
    guardada = ev.task_created(clock, DEVICE, label="guardada")
    log = [
        aberta,
        feita,
        guardada,
        ev.task_completed(clock, DEVICE, id=feita.payload["id"]),
        ev.task_archived(clock, DEVICE, id=guardada.payload["id"]),
    ]
    assert [t.label for t in open_tasks(log)] == ["aberta"]


def test_open_tasks_em_ordem_de_criacao(clock: FakeClock) -> None:
    log = []
    for indice in range(5):
        log.append(ev.task_created(clock, DEVICE, label=f"t{indice}"))
        clock.advance(timedelta(minutes=1))
    assert [t.label for t in open_tasks(log)] == ["t0", "t1", "t2", "t3", "t4"]


def test_task_created_carrega_projeto_e_data(clock: FakeClock) -> None:
    criada = ev.task_created(clock, DEVICE, label="tese", project="doutorado")
    (task,) = open_tasks([criada])
    assert task.project == "doutorado"
    assert task.created_at == clock.now()
    assert task.completed_at is None


def test_task_sem_projeto_fica_none(clock: FakeClock) -> None:
    (task,) = open_tasks([ev.task_created(clock, DEVICE, label="a")])
    assert task.project is None


def test_arquivar_depois_de_concluir_nao_apaga_a_entrega(clock: FakeClock) -> None:
    """Objetos são permanentes: a entrega aconteceu."""
    criada = ev.task_created(clock, DEVICE, label="entregue")
    log = [
        criada,
        ev.task_completed(clock, DEVICE, id=criada.payload["id"]),
        ev.task_archived(clock, DEVICE, id=criada.payload["id"]),
    ]
    assert [t.label for t in completed_tasks(log)] == ["entregue"]
    assert len(shelf_objects(log)) == 1


def test_conclusao_repetida_conta_uma_vez(clock: FakeClock) -> None:
    criada = ev.task_created(clock, DEVICE, label="a")
    concluida = ev.task_completed(clock, DEVICE, id=criada.payload["id"])
    clock.advance(timedelta(hours=2))
    de_novo = ev.task_completed(clock, DEVICE, id=criada.payload["id"])

    (task,) = completed_tasks([criada, concluida, de_novo])
    assert task.completed_at == concluida.occurred_at
    assert len(shelf_objects([criada, concluida, de_novo])) == 1


def test_evento_sobre_tarefa_inexistente_e_ignorado(clock: FakeClock) -> None:
    log = [ev.task_completed(clock, DEVICE, id="nunca-criada")]
    assert completed_tasks(log) == []
    assert shelf_objects(log) == []


# -------------------------------------------------------------------- sessões


def test_sessao_calcula_duracao(clock: FakeClock) -> None:
    (s,) = sessions(sessao(clock, 25))
    assert s.duration == timedelta(minutes=25)
    assert s.duration_minutes == 25.0
    assert s.interrupted is False


def test_sessao_aberta_fica_sem_duracao(clock: FakeClock) -> None:
    (s,) = sessions([ev.session_started(clock, DEVICE)])
    assert s.ended_at is None
    assert s.duration is None
    assert s.duration_minutes == 0.0


def test_sessao_guarda_nota_e_interrupcao(clock: FakeClock) -> None:
    inicio = ev.session_started(clock, DEVICE)
    clock.advance(timedelta(minutes=10))
    fim = ev.session_ended(
        clock, DEVICE, id=inicio.payload["id"], interrupted=True, note="telefone"
    )
    (s,) = sessions([inicio, fim])
    assert s.interrupted is True
    assert s.note == "telefone"


def test_fim_sem_inicio_e_descartado(clock: FakeClock) -> None:
    assert sessions([ev.session_ended(clock, DEVICE, id="fantasma")]) == []


def test_sessao_vinculada_a_tarefa(clock: FakeClock) -> None:
    (s,) = sessions(sessao(clock, 15, task_id="t1"))
    assert s.task_id == "t1"
    (avulsa,) = sessions(sessao(clock, 15))
    assert avulsa.task_id is None


def test_relogio_para_tras_nao_gera_duracao_negativa(clock: FakeClock) -> None:
    inicio = ev.session_started(clock, DEVICE)
    fim = Event(
        uuid="fim",
        device_id=DEVICE,
        occurred_at=inicio.occurred_at - timedelta(minutes=5),
        kind="session.ended",
        payload={"id": inicio.payload["id"], "interrupted": False},
    )
    (s,) = sessions([inicio, fim])
    assert s.duration == timedelta(0)


# ----------------------------------------------------------------- foco 14d


def test_foco_soma_sessoes_encerradas(clock: FakeClock) -> None:
    log = sessao(clock, 30) + sessao(clock, 45)
    assert focus_minutes_14d(log, clock.now()) == 75.0


def test_sessao_aberta_nao_conta(clock: FakeClock) -> None:
    log = sessao(clock, 30) + [ev.session_started(clock, DEVICE)]
    assert focus_minutes_14d(log, clock.now()) == 30.0


def test_sessao_interrompida_conta(clock: FakeClock) -> None:
    """Falhar não destrói nada: o tempo gasto continua valendo."""
    log = sessao(clock, 24, interrupted=True)
    assert focus_minutes_14d(log, clock.now()) == 24.0


def test_bordas_da_janela(clock: FakeClock) -> None:
    log = sessao(clock, 60)
    fim = clock.now()

    assert focus_minutes_14d(log, fim) == 60.0
    assert focus_minutes_14d(log, fim + timedelta(days=14) - timedelta(microseconds=1)) == 60.0
    # Exatamente 14 dias depois a sessão já saiu: a janela é (now-14d, now].
    assert focus_minutes_14d(log, fim + timedelta(days=14)) == 0.0


def test_sessao_no_futuro_nao_conta(clock: FakeClock) -> None:
    log = sessao(clock, 60)
    assert focus_minutes_14d(log, clock.now() - timedelta(days=1)) == 0.0


def test_foco_ignora_eventos_que_nao_sao_sessao(clock: FakeClock) -> None:
    criada = ev.task_created(clock, DEVICE, label="a")
    log = [
        criada,
        ev.task_completed(clock, DEVICE, id=criada.payload["id"]),
        ev.idea_captured(clock, DEVICE, text="uma ideia"),
        ev.day_review(clock, DEVICE, date="2026-03-02", mood=4, energy=3),
    ]
    assert focus_minutes_14d(log, clock.now()) == 0.0


# --------------------------------------------------------------------- planta


@pytest.mark.parametrize(
    "minutos,estagio",
    [
        (0, 0), (1, 0), (179, 0),
        (180, 1), (479, 1),
        (480, 2), (959, 2),
        (960, 3), (1799, 3),
        (1800, 4), (5000, 4),
    ],
)
def test_cortes_da_planta(clock: FakeClock, minutos: float, estagio: int) -> None:
    log = sessao(clock, minutos) if minutos else []
    assert plant_stage(log, clock.now()) == estagio


def test_cortes_sao_os_do_documento() -> None:
    """0h / 3h / 8h / 16h / 30h."""
    assert PLANT_THRESHOLDS_MINUTES == (0, 180, 480, 960, 1800)


def test_planta_sem_log_nenhum(clock: FakeClock) -> None:
    assert plant_stage([], clock.now()) == 0


def test_planta_decai_ao_avancar_14_dias(clock: FakeClock) -> None:
    """A janela móvel já é o decaimento. Não existe penalidade além dela."""
    log: list[Event] = []
    for _ in range(30):
        log += sessao(clock, 60)
        clock.advance(timedelta(hours=6))

    plantada = clock.now()
    assert plant_stage(log, plantada) == 4

    # Sem nenhum evento novo, o tempo sozinho desfaz o crescimento.
    assert plant_stage(log, plantada + timedelta(days=7)) < 4
    assert plant_stage(log, plantada + timedelta(days=14)) == 0
    assert focus_minutes_14d(log, plantada + timedelta(days=14)) == 0.0


def test_planta_volta_a_crescer_depois_de_zerar(clock: FakeClock) -> None:
    """Some sozinho e volta rápido: nada foi destruído."""
    log = sessao(clock, 200)
    assert plant_stage(log, clock.now()) == 1

    clock.advance(timedelta(days=20))
    assert plant_stage(log, clock.now()) == 0

    log += sessao(clock, 500)
    assert plant_stage(log, clock.now()) == 2


# -------------------------------------------------------------------- estante


def test_um_objeto_por_tarefa_concluida(clock: FakeClock) -> None:
    log: list[Event] = []
    for indice in range(6):
        criada = ev.task_created(clock, DEVICE, label=f"t{indice}")
        log.append(criada)
        if indice % 2 == 0:
            log.append(ev.task_completed(clock, DEVICE, id=criada.payload["id"]))
        clock.advance(timedelta(minutes=1))

    estante = shelf_objects(log)
    assert [o.label for o in estante] == ["t0", "t2", "t4"]
    assert all(o.object_type in SHELF_OBJECT_TYPES for o in estante)


def test_shelf_objects_e_deterministico_na_mesma_entrada(clock: FakeClock) -> None:
    log: list[Event] = []
    for indice in range(20):
        criada = ev.task_created(clock, DEVICE, label=f"t{indice}")
        log += [criada, ev.task_completed(clock, DEVICE, id=criada.payload["id"])]
        clock.advance(timedelta(minutes=3))

    referencia = shelf_objects(log)
    for _ in range(5):
        assert shelf_objects(log) == referencia


def test_ordem_de_chegada_nao_muda_a_estante(clock: FakeClock) -> None:
    log: list[Event] = []
    for indice in range(20):
        criada = ev.task_created(clock, DEVICE, label=f"t{indice}")
        log += [criada, ev.task_completed(clock, DEVICE, id=criada.payload["id"])]
        clock.advance(timedelta(minutes=3))

    referencia = shelf_objects(log)
    embaralhado = log[:]
    random.Random(7).shuffle(embaralhado)

    assert embaralhado != log
    assert shelf_objects(embaralhado) == referencia


def test_objeto_depende_so_do_uuid_da_tarefa(clock: FakeClock) -> None:
    """Mesmo id de tarefa, tudo o resto diferente: mesmo objeto."""
    def estante_para(label: str, quando: FakeClock) -> str:
        criada = ev.task_created(quando, DEVICE, label=label, id="task-fixa")
        concluida = ev.task_completed(quando, DEVICE, id="task-fixa")
        (objeto,) = shelf_objects([criada, concluida])
        return objeto.object_type

    primeiro = estante_para("um rótulo", clock)
    clock.advance(timedelta(days=400))
    segundo = estante_para("outro rótulo completamente diferente", clock)
    assert primeiro == segundo


def test_tipos_de_objeto_sao_valores_fixos() -> None:
    """Trava o catálogo e o mapeamento.

    Reordenar SHELF_OBJECT_TYPES ou trocar o algoritmo de hash mudaria o quarto
    de quem já tem tarefas concluídas. O catálogo só pode crescer no fim.
    """
    from cantinho.core.projections import _object_type_for

    assert SHELF_OBJECT_TYPES[:4] == ("mug", "book", "small_vase", "box")
    assert _object_type_for("task-fixa") == "succulent"
    assert _object_type_for("00000000-0000-0000-0000-000000000000") == "box"
    assert _object_type_for("outra") == "teapot"


def test_estante_nao_muda_entre_processos() -> None:
    """`hash()` é aleatorizado por processo; blake2s não é.

    Se alguém trocar blake2s por hash(), os objetos da estante passariam a
    mudar a cada abertura do app. Este teste roda em processos separados com
    PYTHONHASHSEED diferente, que é a única forma de pegar isso.
    """
    script = (
        "from cantinho.core.projections import _object_type_for;"
        "print([_object_type_for(f'task-{i}') for i in range(12)])"
    )
    saidas = set()
    for seed in ("0", "1", "424242"):
        ambiente = {**os.environ, "PYTHONHASHSEED": seed}
        resultado = subprocess.run(
            [sys.executable, "-c", script],
            cwd=RAIZ,
            env=ambiente,
            capture_output=True,
            text=True,
            check=True,
        )
        saidas.add(resultado.stdout.strip())

    assert len(saidas) == 1, f"estante mudou entre processos: {saidas}"


def test_estante_em_ordem_de_conclusao(clock: FakeClock) -> None:
    primeira = ev.task_created(clock, DEVICE, label="primeira")
    segunda = ev.task_created(clock, DEVICE, label="segunda")
    clock.advance(timedelta(hours=1))
    # Concluídas na ordem inversa da criação.
    fim_segunda = ev.task_completed(clock, DEVICE, id=segunda.payload["id"])
    clock.advance(timedelta(hours=1))
    fim_primeira = ev.task_completed(clock, DEVICE, id=primeira.payload["id"])

    estante = shelf_objects([primeira, segunda, fim_segunda, fim_primeira])
    assert [o.label for o in estante] == ["segunda", "primeira"]
    assert [o.placed_at for o in estante] == [
        fim_segunda.occurred_at,
        fim_primeira.occurred_at,
    ]


# --------------------------------------------- eventos no mesmo microssegundo


def test_criar_e_concluir_no_mesmo_instante(clock: FakeClock) -> None:
    """Regressão: a conclusão não pode depender de sortear a ordem certa.

    Com timestamps iguais o desempate é por uuid, que é aleatório. Numa
    passada só, metade das repetições descartava a conclusão por falar de uma
    tarefa que "ainda não existia".
    """
    for _ in range(50):
        criada = ev.task_created(clock, DEVICE, label="relâmpago")
        concluida = ev.task_completed(clock, DEVICE, id=criada.payload["id"])
        assert criada.occurred_at == concluida.occurred_at

        log = [criada, concluida]
        assert open_tasks(log) == []
        assert len(completed_tasks(log)) == 1
        assert len(shelf_objects(log)) == 1


def test_sessao_de_duracao_zero(clock: FakeClock) -> None:
    """Começar e parar no mesmo microssegundo: sessão encerrada, zero minuto."""
    for _ in range(50):
        inicio = ev.session_started(clock, DEVICE)
        fim = ev.session_ended(clock, DEVICE, id=inicio.payload["id"])
        assert inicio.occurred_at == fim.occurred_at

        (s,) = sessions([inicio, fim])
        assert s.ended_at is not None
        assert s.duration == timedelta(0)
        assert focus_minutes_14d([inicio, fim], clock.now()) == 0.0


# --------------------------------------------------------------------- pureza


def test_projecoes_nao_consomem_nem_alteram_a_entrada(clock: FakeClock) -> None:
    criada = ev.task_created(clock, DEVICE, label="a")
    log = [criada, ev.task_completed(clock, DEVICE, id=criada.payload["id"])]
    log += sessao(clock, 20)
    copia = list(log)

    agora = clock.now()
    for _ in range(2):
        open_tasks(log)
        completed_tasks(log)
        sessions(log)
        focus_minutes_14d(log, agora)
        plant_stage(log, agora)
        shelf_objects(log)

    assert log == copia


def test_projecoes_aceitam_iterador_esgotavel(clock: FakeClock) -> None:
    criada = ev.task_created(clock, DEVICE, label="a")
    log = [criada, ev.task_completed(clock, DEVICE, id=criada.payload["id"])]
    assert len(completed_tasks(iter(log))) == 1
    assert len(shelf_objects(iter(log))) == 1


def test_log_vazio_nao_quebra_nenhuma_projecao(clock: FakeClock) -> None:
    agora = clock.now()
    assert open_tasks([]) == []
    assert completed_tasks([]) == []
    assert sessions([]) == []
    assert focus_minutes_14d([], agora) == 0.0
    assert plant_stage([], agora) == 0
    assert shelf_objects([]) == []
