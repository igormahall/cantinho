"""A fronteira entre o log e o QML.

O backend não é testado pela tela — quem faz isso é `tools/simular_uso.py`. O
que se confere aqui é a regra que a tela apenas mostra: qual tarefa o botão
"começar" pega, o que o interruptor de som devolve, e o que encerrar o dia
guarda.

O relógio é falso, mas parte de *agora*: "hoje" e "esta semana" são calculados
em horário local pelo relógio de parede do sistema, não pelo clock injetado, e
um evento datado de 2026 não cairia em nenhum dos dois.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest

from cantinho.backend import DEFAULT_SOUND_MODE, Backend
from cantinho.core.clock import FakeClock
from cantinho.core.store import EventStore

from conftest import DEVICE


class RelogioQueAnda(FakeClock):
    """Relógio falso que avança um segundo a cada leitura.

    O `FakeClock` parado empata o `created_at` de todas as tarefas criadas em
    seguida, e aí a ordem do backlog cai no desempate por uuid — que é sorteio.
    Aqui o que importa é justamente a ordem, então cada evento precisa de um
    instante próprio, como acontece no uso real.
    """

    def now(self) -> datetime:
        agora = super().now()
        self.advance(timedelta(seconds=1))
        return agora


@pytest.fixture
def backend(tmp_path: Path) -> Iterator[Backend]:
    with EventStore(tmp_path / "cantinho.db", device_id=DEVICE) as store:
        yield Backend(store, RelogioQueAnda(datetime.now(timezone.utc)))


def semear(backend: Backend, *rotulos: str) -> list[str]:
    for rotulo in rotulos:
        backend.addTask(rotulo)
    return [task["id"] for task in backend.backlog]


# ---------------------------------------------------------------------- som


def test_o_app_abre_com_o_quarto_calado(backend: Backend) -> None:
    """Só os toques da interface.

    O ambiente é a única coisa aqui que ocupa a sala sem ninguém ter pedido:
    quem abre o app numa mesa compartilhada levaria chuva tocando até achar
    onde desligar. O retorno do clique só soa em resposta a um gesto.
    """
    assert backend.soundMode == DEFAULT_SOUND_MODE == "sussurro"
    assert not backend.ambienceOn
    assert backend.touchesOn
    assert not backend.muted


def test_o_interruptor_da_mini_devolve_o_estado_anterior(backend: Backend) -> None:
    backend.setSoundMode("tudo")

    backend.toggleMute()
    assert backend.muted and not backend.touchesOn

    backend.toggleMute()
    assert backend.soundMode == "tudo"


def test_o_interruptor_da_mini_nao_passa_pelo_ciclo(backend: Backend) -> None:
    """Duas posições, não três: calar e devolver como estava."""
    assert backend.soundMode == "sussurro"
    backend.toggleMute()
    backend.toggleMute()
    assert backend.soundMode == "sussurro"


def test_o_menu_do_quarto_gira_os_tres(backend: Backend) -> None:
    backend.setSoundMode("tudo")
    for esperado in ("sussurro", "mudo", "tudo"):
        backend.cycleSoundMode()
        assert backend.soundMode == esperado


# ------------------------------------------------------------ tarefa em foco


def test_sem_escolha_o_foco_e_o_topo_do_hoje(backend: Backend) -> None:
    ids = semear(backend, "a", "b", "c")
    assert backend.focusedTaskId == ids[0]
    assert backend.focusedTaskLabel == "a"


def test_backlog_vazio_nao_tem_foco(backend: Backend) -> None:
    assert backend.focusedTaskId == ""
    assert backend.focusedTaskLabel == ""


def test_a_escolha_vale_sobre_o_topo(backend: Backend) -> None:
    ids = semear(backend, "a", "b", "c")
    backend.setFocusedTask(ids[2])
    assert backend.focusedTaskLabel == "c"


def test_o_foco_cai_no_topo_quando_a_escolhida_sai(backend: Backend) -> None:
    """Concluir a escolhida não pode deixar o botão apontando para o vazio."""
    ids = semear(backend, "a", "b")
    backend.setFocusedTask(ids[1])
    backend.completeTask(ids[1])
    assert backend.focusedTaskId == ids[0]


def test_sessao_livre_e_escolha_explicita(backend: Backend) -> None:
    semear(backend, "a")
    backend.setFocusedTask("")
    assert backend.focusedTaskId == ""
    assert backend.freeSessionChosen


def test_tarefa_de_fora_do_backlog_nao_vira_foco(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.setFocusedTask("nao-existe")
    assert backend.focusedTaskId == ids[0]


def test_comecar_pega_a_tarefa_em_foco(backend: Backend) -> None:
    """O bug que motivou tudo isto: o botão grande abria sessão sem dono."""
    ids = semear(backend, "a", "b")
    backend.setFocusedTask(ids[1])
    backend.startFocused()
    assert backend.timerRunning
    assert backend.currentTaskId == ids[1]


def test_comecar_sem_tarefa_ainda_abre_sessao_livre(backend: Backend) -> None:
    backend.startFocused()
    assert backend.timerRunning
    assert backend.currentTaskId == ""


def test_comecar_por_uma_tarefa_a_deixa_em_foco(backend: Backend) -> None:
    """Parar não pode devolver o foco para outra coisa."""
    ids = semear(backend, "a", "b")
    backend.startSession(ids[1])
    backend.endSession(False, "")
    assert backend.focusedTaskId == ids[1]


def test_avancar_o_foco_circula_pelo_hoje(backend: Backend) -> None:
    ids = semear(backend, "a", "b", "c")
    backend.focusNext()
    assert backend.focusedTaskId == ids[1]
    backend.focusNext()
    backend.focusNext()
    assert backend.focusedTaskId == ids[0]


def test_avancar_com_o_backlog_vazio_nao_quebra(backend: Backend) -> None:
    backend.focusNext()
    assert backend.focusedTaskId == ""


# ------------------------------------------------------------------ renomear


def test_renomear_troca_o_rotulo(backend: Backend) -> None:
    ids = semear(backend, "revisar o capitulo 3")
    backend.renameTask(ids[0], "revisar o capítulo 3")
    assert [t["label"] for t in backend.backlog] == ["revisar o capítulo 3"]


def test_renomear_nao_muda_o_objeto_da_estante(backend: Backend) -> None:
    """O desenho vem do id, não do texto: corrigir não troca o enfeite."""
    ids = semear(backend, "a")
    backend.completeTask(ids[0])
    antes = list(backend.shelf)

    outros = semear(backend, "b")
    backend.renameTask(outros[0], "a")
    backend.completeTask(outros[0])
    assert backend.shelf[0] == antes[0]


def test_renomear_para_o_mesmo_texto_nao_grava(backend: Backend) -> None:
    ids = semear(backend, "a")
    antes = len(backend._events)
    backend.renameTask(ids[0], "a")
    backend.renameTask(ids[0], "   ")
    assert len(backend._events) == antes


def test_renomear_tarefa_que_nao_esta_aberta_nao_grava(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.completeTask(ids[0])
    antes = len(backend._events)
    backend.renameTask(ids[0], "b")
    assert len(backend._events) == antes


# ------------------------------------------------------------ encerrar o dia


def test_encerrar_o_dia_guarda_a_sessao_aberta(backend: Backend) -> None:
    """O timer esquecido ligado era o jeito mais fácil de sujar a semana."""
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend.endDay(4, 3, "deu para andar")

    assert not backend.timerRunning
    assert backend.dayClosed
    assert backend.todayReview["mood"] == 4
    assert len(backend.todaySessions) == 1


def test_encerrar_o_dia_sem_sessao_so_guarda(backend: Backend) -> None:
    backend.endDay(2, 2)
    assert backend.dayClosed
    assert backend.todaySessions == []


# ---------------------------------------------------------------- a semana


def test_a_semana_tem_sete_dias_de_segunda_a_domingo(backend: Backend) -> None:
    dias = backend.weekDays
    assert len(dias) == 7
    assert [dia["weekday"] for dia in dias] == [
        "seg", "ter", "qua", "qui", "sex", "sáb", "dom",
    ]
    assert sum(1 for dia in dias if dia["today"]) == 1


def test_a_semana_lista_as_entregas_do_dia(backend: Backend) -> None:
    ids = semear(backend, "a", "b")
    backend.completeTask(ids[0])

    hoje = next(dia for dia in backend.weekDays if dia["today"])
    assert hoje["delivered"] == ["a"]
    assert backend.weekDelivered == 1


def test_dias_que_ainda_nao_chegaram_ficam_marcados(backend: Backend) -> None:
    """Dia futuro não é dia vazio: ele não tem nada a dizer ainda."""
    dias = backend.weekDays
    depois_de_hoje = False
    for dia in dias:
        assert dia["ahead"] == depois_de_hoje
        if dia["today"]:
            depois_de_hoje = True


def test_a_semana_passada_esta_vazia_e_da_para_voltar(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.completeTask(ids[0])

    backend.previousWeek()
    assert backend.weekOffset == 1
    assert backend.weekTitle == "a semana passada"
    assert backend.weekDelivered == 0

    backend.nextWeek()
    assert backend.weekOffset == 0
    assert backend.weekDelivered == 1


def test_a_semana_nao_passa_do_presente(backend: Backend) -> None:
    backend.nextWeek()
    assert backend.weekOffset == 0


def test_o_periodo_da_semana_e_o_das_datas(backend: Backend) -> None:
    inicio = backend._inicio_da_semana()
    fim = inicio + timedelta(days=6)
    assert str(inicio.day) in backend.weekRange
    assert str(fim.day) in backend.weekRange
    assert inicio.weekday() == 0
