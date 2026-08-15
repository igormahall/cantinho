"""A fronteira entre o log e o QML.

O backend não é testado pela tela — quem faz isso é `tools/simular_uso.py`. O
que se confere aqui é a regra que a tela apenas mostra: qual tarefa o botão
"começar" pega, o que o interruptor de som devolve, e o que encerrar o dia
guarda.

O relógio é falso, mas parte de *agora*. "Hoje" e "esta semana" saem do clock
injetado, convertido para horário local — é o que permite testar a virada da
meia-noite sem esperar por ela —, e um relógio parado num 2026 arbitrário faria
a semana do teste não conter nenhum evento do teste.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest

from cantinho.backend import (
    CHECKIN_LIMIT,
    _RelogioFixo,
    DEFAULT_SOUND_MODE,
    LONG_SESSION_MINUTES,
    NUDGE_AFTER_MINUTES,
    NUDGE_REPEAT_MINUTES,
    NUDGES,
    WALL_IDEAS_LIMIT,
    Backend,
)
from cantinho.core import events as ev
from cantinho.core import projections as proj
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


# ----------------------------------------------------------------- movimento


def test_o_quarto_abre_respirando(backend: Backend) -> None:
    assert backend.motionOn


def test_o_quarto_pode_ficar_quieto(backend: Backend) -> None:
    """Cinco laços rodam para sempre; o grão repinta a janela a cada 900 ms."""
    backend.toggleMotion()
    assert not backend.motionOn
    backend.toggleMotion()
    assert backend.motionOn


def test_movimento_nao_vai_para_o_log(backend: Backend) -> None:
    """Ajuste de ambiente é da sessão, como o som. Não é fato do histórico."""
    antes = len(backend._events)
    backend.setMotion(False)
    backend.setMotion(True)
    assert len(backend._events) == antes


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


# ----------------------------------------------------------- sair com o timer


def test_sair_guarda_a_sessao_aberta(backend: Backend) -> None:
    """O tempo aberto não pode depender de por onde se sai do app.

    Havia três caminhos para fora — o menu do quarto, a bandeja e fechar a
    última janela sem bandeja — e dois não passavam pelo backend. Sessão sem
    `session.ended` não conta em projeção nenhuma: o tempo sumia inteiro.
    """
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend.endOpenSession()

    assert not backend.timerRunning
    assert len(backend.todaySessions) == 1
    assert backend.todaySessions[0]["interrupted"] is False


def test_sair_sem_sessao_nao_grava_nada(backend: Backend) -> None:
    antes = len(backend._events)
    backend.endOpenSession()
    assert len(backend._events) == antes


# --------------------------------------------------------- queda e retomada


def reabrir(backend: Backend) -> Backend:
    """Outro backend sobre o mesmo store, como quem reabre o app."""
    return Backend(backend._store, backend._clock)


def test_sessao_orfa_fecha_na_ultima_marca_de_vida(backend: Backend) -> None:
    """A queda não pode nem apagar o tempo nem inventá-lo.

    Fechar "agora", na reabertura, daria catorze horas de foco a uma máquina
    que passou a noite desligada. A marca de vida é o último instante em que o
    app comprovadamente estava rodando, e é até aí que a sessão vai.
    """
    ids = semear(backend, "escrever a introdução")
    backend.startSession(ids[0])
    inicio = backend._timer.started_at

    # O app viveu mais quinze minutos, marcou presença, e morreu de pé.
    backend._clock.advance(timedelta(minutes=20))
    backend._heartbeat.beat(inicio + timedelta(minutes=15))

    depois = reabrir(backend)
    assert depois.hasRecoveredSession
    assert depois.recoveredLabel == "escrever a introdução"
    assert depois.recoveredMinutes == 15
    assert depois.recoveredUntil != ""
    # E não sobrou nada aberto no log.
    assert not any(s.ended_at is None for s in proj.sessions(depois._events))


def test_a_sessao_recuperada_conta_como_interrompida(backend: Backend) -> None:
    """Queda de energia é a interrupção mais legítima que existe.

    E o tempo continua contando no foco: o projeto não desconta esforço de
    quem foi interrompido.
    """
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    inicio = backend._timer.started_at
    backend._clock.advance(timedelta(minutes=20))
    backend._heartbeat.beat(inicio + timedelta(minutes=15))

    depois = reabrir(backend)
    fim = depois._events[-1]
    assert fim.kind == "session.ended"
    assert fim.payload["interrupted"] is True
    assert depois.todaySessions[0]["interrupted"] is True


def test_o_fim_recuperado_e_datado_quando_aconteceu(backend: Backend) -> None:
    """E não na hora em que se descobriu que tinha acontecido.

    Com o timestamp da reabertura, a sessão de ontem à noite apareceria no
    dia de hoje.
    """
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    inicio = backend._timer.started_at
    backend._clock.advance(timedelta(minutes=20))
    marca = inicio + timedelta(minutes=15)
    backend._heartbeat.beat(marca)

    depois = reabrir(backend)
    assert depois._events[-1].occurred_at == marca


def test_sem_marca_de_vida_a_sessao_fecha_no_comeco(backend: Backend) -> None:
    """Zero minuto é uma perda honesta; o contrário não é."""
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend._heartbeat.clear()

    depois = reabrir(backend)
    assert depois.hasRecoveredSession
    assert depois.recoveredMinutes == 0
    assert not any(s.ended_at is None for s in proj.sessions(depois._events))


def test_marca_no_futuro_e_ignorada(backend: Backend) -> None:
    """Relógio do sistema que andou para trás deixa de ser limite confiável."""
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend._heartbeat.beat(backend._clock.now() + timedelta(hours=6))

    depois = reabrir(backend)
    assert depois.recoveredMinutes == 0


def test_a_marca_some_quando_a_sessao_termina(backend: Backend) -> None:
    """Marca em disco significa, sempre, "o app morreu de pé"."""
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    assert backend._heartbeat.last() is not None

    backend.endSession()
    assert backend._heartbeat.last() is None
    assert not reabrir(backend).hasRecoveredSession


def test_sem_sessao_aberta_nao_ha_aviso(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend.endSession()
    assert not reabrir(backend).hasRecoveredSession


def test_continuar_abre_sessao_nova(backend: Backend) -> None:
    """Não é retomar: a de antes já está fechada, com o tempo que dava provar."""
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend._clock.advance(timedelta(minutes=20))
    backend._heartbeat.beat(backend._timer.started_at + timedelta(minutes=15))

    depois = reabrir(backend)
    depois.continueRecovered()

    assert depois.timerRunning
    assert depois.currentTaskId == ids[0]
    assert not depois.hasRecoveredSession
    assert depois._events[-1].kind == "session.started"


def test_dispensar_o_aviso_nao_grava_nada(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.startSession(ids[0])

    depois = reabrir(backend)
    antes = len(depois._events)
    depois.dismissRecovered()

    assert not depois.hasRecoveredSession
    assert len(depois._events) == antes


def test_comecar_algo_novo_dispensa_o_aviso(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.startSession(ids[0])

    depois = reabrir(backend)
    depois.startSession(ids[0])
    assert not depois.hasRecoveredSession


# ------------------------------------------------------------ a virada do dia


def test_a_virada_do_dia_esvazia_o_bilhete(backend: Backend) -> None:
    """O app fica aberto a noite toda, e a meia-noite não gera evento nenhum.

    Sem isto, o bilhete da parede amanhecia com as tarefas de ontem riscadas e
    o diário continuava dizendo que o dia estava fechado.
    """
    ids = semear(backend, "a")
    backend.completeTask(ids[0])
    backend.endDay(3, 3)
    assert backend.todayCompleted == ["a"]
    assert backend.dayClosed

    backend._clock.advance(timedelta(days=1))
    backend._reavaliar_relogio()

    assert backend.todayCompleted == []
    assert not backend.dayClosed
    assert backend.todaySessions == []


def test_a_planta_decai_sem_evento_novo(tmp_path: Path) -> None:
    """A janela de 14 dias desliza a qualquer hora, não à meia-noite.

    O estágio caía só na próxima escrita no log — ou seja, a planta ficava
    parada num estágio que o histórico já tinha desfeito até alguém mexer no
    app. Aqui o dia é o mesmo nas duas leituras, para que o que se está
    testando seja o decaimento e não a virada.
    """
    # Meio-dia local, para que ±4 horas continuem caindo no mesmo dia.
    agora = datetime.now(timezone.utc)
    local = agora.astimezone()
    meio_dia = agora - timedelta(
        hours=local.hour - 12,
        minutes=local.minute,
        seconds=local.second,
        microseconds=local.microsecond,
    )

    with EventStore(tmp_path / "cantinho.db", device_id=DEVICE) as store:
        relogio = FakeClock(meio_dia)
        backend = Backend(store, relogio)
        backend.addTask("a")
        backend.startSession(backend.backlog[0]["id"])
        relogio.advance(timedelta(hours=3))
        backend.endSession()
        assert backend.plantStage == 1

        # Ainda dentro da janela: a sessão terminou em +3h, e a janela começa
        # em +2h.
        relogio.set(meio_dia + timedelta(days=14, hours=2))
        backend._reavaliar_relogio()
        assert backend.plantStage == 1

        # Mesmo dia local, e agora a sessão ficou para trás da janela.
        relogio.set(meio_dia + timedelta(days=14, hours=4))
        backend._reavaliar_relogio()
        assert backend.plantStage == 0


# ------------------------------------------------------------------- entregar


def test_entreguei_grava_o_fim_e_a_conclusao(backend: Backend) -> None:
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend.endSessionAndComplete()

    kinds = [evento.kind for evento in backend._events]
    assert kinds[-2:] == ["session.ended", "task.completed"]
    assert not backend.timerRunning
    assert backend.backlog == []
    assert len(backend.shelf) == 1


def test_entreguei_em_sessao_livre_so_encerra(backend: Backend) -> None:
    backend.startSession("")
    backend.endSessionAndComplete()

    assert backend._events[-1].kind == "session.ended"
    assert backend.shelf == []


def test_concluir_tarefa_que_nao_esta_aberta_nao_grava(backend: Backend) -> None:
    """Evento inerte é evento que fica no log para sempre: não há DELETE."""
    ids = semear(backend, "a")
    backend.completeTask(ids[0])
    antes = len(backend._events)

    backend.completeTask(ids[0])
    backend.completeTask("nao-existe")
    backend.archiveTask("nao-existe")

    assert len(backend._events) == antes


# ------------------------------------------------- a pergunta da sessão longa


def espiar(sinal) -> list:
    """Guarda o que um sinal emitiu, para conferir depois."""
    recebidos: list = []
    sinal.connect(lambda *args: recebidos.append(args[0] if args else None))
    return recebidos


def test_sessao_longa_pergunta_pelo_extra(backend: Backend) -> None:
    """Uma hora raramente é uma coisa só.

    No meio dela chega o pedido urgente e resolve-se o e-mail que travava
    outra pessoa — e nada disso vira entrega, porque o gesto de registrar
    acontece no fim, quando já se esqueceu.
    """
    perguntas = espiar(backend.extraAsked)
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend._clock.advance(timedelta(minutes=LONG_SESSION_MINUTES + 5))
    backend.endSession()

    assert len(perguntas) == 1
    assert perguntas[0] >= LONG_SESSION_MINUTES


def test_sessao_curta_nao_pergunta_nada(backend: Backend) -> None:
    perguntas = espiar(backend.extraAsked)
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend._clock.advance(timedelta(minutes=LONG_SESSION_MINUTES - 10))
    backend.endSession()

    assert perguntas == []


def test_entregar_depois_de_muito_tempo_tambem_pergunta(backend: Backend) -> None:
    perguntas = espiar(backend.extraAsked)
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend._clock.advance(timedelta(minutes=LONG_SESSION_MINUTES + 5))
    backend.endSessionAndComplete()

    assert len(perguntas) == 1
    assert len(backend.shelf) == 1


def test_a_pergunta_traz_a_janela_grande_de_volta(backend: Backend) -> None:
    """Quem começou pelo "hoje" está na mini, e pergunta que ninguém vê não é
    pergunta."""
    ids = semear(backend, "a")
    backend.startSession(ids[0])
    backend.showMini()
    assert not backend.mainVisible

    backend._clock.advance(timedelta(minutes=LONG_SESSION_MINUTES + 1))
    backend.endSession()
    assert backend.mainVisible


def test_registrar_o_que_nunca_esteve_na_lista(backend: Backend) -> None:
    """A atividade que surgiu no meio e ninguém teve tempo de anotar antes."""
    backend.addAndCompleteTask("resolver o e-mail do financeiro")

    kinds = [evento.kind for evento in backend._events]
    assert kinds[-2:] == ["task.created", "task.completed"]
    assert backend.backlog == []
    assert backend.todayCompleted == ["resolver o e-mail do financeiro"]
    assert len(backend.shelf) == 1


def test_registrar_extra_vazio_nao_grava(backend: Backend) -> None:
    antes = len(backend._events)
    backend.addAndCompleteTask("   ")
    assert len(backend._events) == antes


# --------------------------------------------------------- o toque do quarto


def test_o_quarto_toca_quando_o_relogio_e_esquecido(backend: Backend) -> None:
    """Duas horas é mais do que qualquer sessão conduzida de propósito."""
    toques = espiar(backend.nudged)
    ids = semear(backend, "a")
    backend.startSession(ids[0])

    backend._clock.advance(timedelta(minutes=NUDGE_AFTER_MINUTES - 5))
    backend._reavaliar_relogio()
    assert toques == []

    backend._clock.advance(timedelta(minutes=10))
    backend._reavaliar_relogio()
    assert len(toques) == 1
    assert toques[0]


def test_o_toque_insiste_de_meia_em_meia_hora(backend: Backend) -> None:
    """Quem saiu da mesa às 19h50 não estava lá para ver o primeiro."""
    toques = espiar(backend.nudged)
    ids = semear(backend, "a")
    backend.startSession(ids[0])

    backend._clock.advance(timedelta(minutes=NUDGE_AFTER_MINUTES))
    backend._reavaliar_relogio()
    backend._clock.advance(timedelta(minutes=NUDGE_REPEAT_MINUTES))
    backend._reavaliar_relogio()
    backend._clock.advance(timedelta(minutes=NUDGE_REPEAT_MINUTES))
    backend._reavaliar_relogio()

    assert len(toques) == 3
    # Frases diferentes: o mesmo aviso repetido vira ruído de sistema.
    assert len(set(toques)) == 3


def test_sem_sessao_o_quarto_nao_toca(backend: Backend) -> None:
    toques = espiar(backend.nudged)
    backend._clock.advance(timedelta(hours=6))
    backend._reavaliar_relogio()
    assert toques == []


def test_o_toque_recomeca_a_cada_sessao(backend: Backend) -> None:
    toques = espiar(backend.nudged)
    ids = semear(backend, "a", "b")
    backend.startSession(ids[0])
    backend._clock.advance(timedelta(minutes=NUDGE_AFTER_MINUTES))
    backend._reavaliar_relogio()
    backend.endSession()
    assert len(toques) == 1

    backend.startSession(ids[1])
    backend._clock.advance(timedelta(minutes=NUDGE_AFTER_MINUTES - 5))
    backend._reavaliar_relogio()
    assert len(toques) == 1


def test_as_frases_do_toque_cabem_na_mini() -> None:
    """O limite é a janela de 300 px, e ele corta pelo fim.

    Na mini o toque ocupa a faixa do nome da tarefa e o que não couber é
    elidido — o que come justamente o fim da frase, que é onde ela diz alguma
    coisa. "Você ainda está por…" não é o texto que se escreveu.
    """
    assert NUDGES
    assert all(len(frase) <= 36 for frase in NUDGES)


def test_as_frases_do_toque_nao_se_repetem() -> None:
    """O mesmo aviso duas vezes vira ruído de sistema."""
    assert len(set(NUDGES)) == len(NUDGES)


def test_as_duas_escondidas_e_o_app_na_bandeja(backend: Backend) -> None:
    """O único estado em que o quarto não tem onde falar.

    Nem a tira acima da barra nem a faixa da mini existem, e é justamente aí
    que o toque mais importa: app na bandeja com o relógio correndo é o retrato
    do timer esquecido. Quem resolve isso é a notificação, em `main.py`.
    """
    assert backend.mainVisible and not backend.on_tray

    backend.showMini()
    assert not backend.on_tray

    backend.hideAll()
    assert backend.on_tray

    backend.showMain()
    assert not backend.on_tray


# ------------------------------------------------------------------ o passeio


def test_o_passeio_abre_no_log_vazio(backend: Backend) -> None:
    """O sinal de primeira abertura já existe e é exato: não há evento nenhum.

    Guardar um booleano de "já viu" ao lado disso seria uma segunda fonte de
    verdade sobre a mesma pergunta, com a chance de as duas discordarem.
    """
    assert backend._events == []
    assert backend.showTour


def test_o_passeio_nao_abre_com_log_usado(backend: Backend, tmp_path: Path) -> None:
    semear(backend, "a")

    with EventStore(backend._store.db_path, device_id=DEVICE) as store:
        assert not Backend(store, backend._clock).showTour


def test_dispensar_o_passeio_nao_grava_nada(backend: Backend) -> None:
    backend.dismissTour()
    assert not backend.showTour
    assert backend._events == []


def test_o_passeio_volta_pelo_menu(backend: Backend) -> None:
    """Ele some assim que a primeira coisa é escrita, e isso é certo — mas
    deixaria quem dispensou cedo demais sem caminho de volta."""
    semear(backend, "a")
    backend.dismissTour()

    backend.startTour()
    assert backend.showTour


def test_o_rosto_do_passeio_nao_e_o_da_planta_de_agora(backend: Backend) -> None:
    """Numa primeira abertura `plantStage` é 0 — um vaso com terra.

    A figura que apresenta o app não pode ser a versão mais murcha dele, e é o
    mesmo estágio fixo do ícone da janela: quem aprende o cantinho por este
    rosto reconhece o programa na barra de tarefas depois.
    """
    assert backend.plantStage == 0
    assert backend.tourAvatarStage == 2


# ------------------------------------------------- limites de texto na entrada
#
# A regra destes: **nenhum slot pode levantar exceção.** Exceção em slot morre
# dentro do laço de eventos do Qt, e perder o app inteiro por ter colado um
# texto grande no campo errado é pior do que perder o excedente do texto. Quem
# recusa de vez é `check_limits`, em `core/events.py`; aqui o que se prova é que
# a fronteira corta antes de chegar lá.


def test_rotulo_gigante_e_cortado_em_vez_de_derrubar(backend: Backend) -> None:
    backend.addTask("t" * (ev.LABEL_LIMIT * 10))
    assert len(backend.backlog) == 1
    assert len(backend.backlog[0]["label"]) == ev.LABEL_LIMIT


def test_ideia_gigante_e_cortada(backend: Backend) -> None:
    backend.captureIdea("i" * (ev.TEXT_LIMIT * 10))
    assert len(backend.ideas) == 1
    assert len(backend.ideas[0]["text"]) == ev.TEXT_LIMIT


def test_renomear_com_texto_gigante_nao_derruba(backend: Backend) -> None:
    [task_id] = semear(backend, "original")
    backend.renameTask(task_id, "r" * (ev.LABEL_LIMIT * 10))
    assert len(backend.backlog[0]["label"]) == ev.LABEL_LIMIT


def test_nota_gigante_na_revisao_e_cortada(backend: Backend) -> None:
    backend.saveReview(3, 3, "n" * (ev.TEXT_LIMIT * 10))
    assert len(backend.todayReview["note"]) == ev.TEXT_LIMIT


def test_checkin_corta_a_lista_e_cada_item(backend: Backend) -> None:
    """Limitar cada item não limita a lista, e é ela que estoura o payload."""
    backend.saveCheckin(["i" * (ev.LABEL_LIMIT * 2)] * (CHECKIN_LIMIT * 4))
    [evento] = [e for e in backend._events if e.kind == "day.checkin"]
    assert len(evento.payload["intents"]) == CHECKIN_LIMIT
    assert all(len(texto) == ev.LABEL_LIMIT for texto in evento.payload["intents"])


def test_reordenar_um_backlog_grande_nao_esbarra_no_teto(backend: Backend) -> None:
    """`backlog.reordered` não é cortado, e a folga do teto é a razão."""
    ids = semear(backend, *(f"tarefa {n}" for n in range(60)))
    backend.reorderBacklog(list(reversed(ids)))
    assert [tarefa["id"] for tarefa in backend.backlog] == list(reversed(ids))


# ------------------------------------------------------- os limites da semana


def test_a_semana_nao_anda_para_antes_do_log(backend: Backend) -> None:
    """O passado tem fim, e ele é o primeiro evento — com um piso de uma semana.

    A semana passada aconteceu mesmo que o app não estivesse lá, e vazia ela diz
    uma coisa verdadeira. É a assimetria deliberada com o futuro, que não diz
    nada porque ainda não é.
    """
    semear(backend, "uma tarefa")
    for _ in range(300):
        backend.previousWeek()
    assert backend.weekOffset == 1
    assert not backend.hasPreviousWeek


def test_a_semana_anda_ate_o_primeiro_evento(backend: Backend) -> None:
    from datetime import datetime as _dt

    # Um evento de cinco semanas atrás: o recuo passa a ir até lá, e para.
    antigo = _dt.now(timezone.utc) - timedelta(weeks=5)
    backend._events.insert(
        0,
        ev.task_created(_RelogioFixo(antigo), DEVICE, label="tarefa velha"),
    )
    for _ in range(50):
        backend.previousWeek()
    assert backend.weekOffset == 5
    assert not backend.hasPreviousWeek

    backend.nextWeek()
    assert backend.hasPreviousWeek


def test_semana_de_log_vazio_para_na_semana_passada(backend: Backend) -> None:
    for _ in range(10):
        backend.previousWeek()
    assert backend.weekOffset == 1
    assert not backend.hasPreviousWeek


def test_o_periodo_diz_o_ano_quando_nao_e_o_de_hoje(backend: Backend) -> None:
    from datetime import datetime as _dt

    antigo = _dt.now(timezone.utc) - timedelta(weeks=80)
    backend._events.insert(
        0,
        ev.task_created(_RelogioFixo(antigo), DEVICE, label="tarefa velha"),
    )
    while backend.hasPreviousWeek:
        backend.previousWeek()
    assert str(antigo.year) in backend.weekRange

    backend.thisWeek()
    assert str(datetime.now(timezone.utc).year) not in backend.weekRange


def test_as_tres_propriedades_da_semana_concordam(backend: Backend) -> None:
    """`weekDelivered` e `weekMinutes` saem da mesma passada que `weekDays`."""
    [task_id] = semear(backend, "entregar isso")
    backend.startSession(task_id)
    backend.endSessionAndComplete()

    assert backend.weekDelivered == sum(
        len(dia["delivered"]) for dia in backend.weekDays
    )
    entregues = [rotulo for dia in backend.weekDays for rotulo in dia["delivered"]]
    assert "entregar isso" in entregues


# ------------------------------------------------------ a estante se explica


def test_a_estante_diz_de_qual_tarefa_e_cada_objeto(backend: Backend) -> None:
    """Objeto sem nome é decoração; com nome é a lembrança do que se fez."""
    ids = semear(backend, "primeira", "segunda")
    for task_id in ids:
        backend.completeTask(task_id)

    slots = backend.shelfSlots
    assert [slot["label"] for slot in slots] == ["primeira", "segunda"]
    # A posição vem do mesmo lugar que desenha a imagem: se divergisse, o rótulo
    # apareceria ao lado do objeto errado.
    from cantinho.services import scene

    assert [(slot["x"], slot["y"]) for slot in slots] == scene.shelf_slots(2)


def test_a_estante_lotada_nao_estoura_os_slots(backend: Backend) -> None:
    """A projeção guarda tudo para sempre; é o desenho que lota."""
    from cantinho.services import scene

    ids = semear(backend, *(f"entrega {n}" for n in range(scene.SHELF_CAPACITY + 4)))
    for task_id in ids:
        backend.completeTask(task_id)

    assert len(backend.shelf) == len(ids)
    assert len(backend.shelfSlots) == scene.SHELF_CAPACITY


# ------------------------------------------------------------------ a página
#
# Levar o quarto embora. E, junto, a regra que segura a semana: o horizonte
# mais longo é respondido por uma página, não por um painel maior.


def test_exportar_tudo_escreve_a_pagina(backend: Backend) -> None:
    [task_id] = semear(backend, "escrever a tese")
    backend.completeTask(task_id)
    backend.captureIdea("trocar a fonte do editor")

    caminho = Path(backend.exportEverything())
    assert caminho.is_file()
    texto = caminho.read_text(encoding="utf-8")
    assert "escrever a tese" in texto
    assert "trocar a fonte do editor" in texto


def test_a_pagina_fica_ao_lado_do_banco(backend: Backend) -> None:
    """A regra de que o app só escreve na própria pasta de dados continua de pé."""
    semear(backend, "algo")
    caminho = Path(backend.exportEverything())
    assert caminho.parent == Path(backend.exportFolder)
    assert caminho.parent.parent == backend._store.db_path.parent


def test_a_semana_exporta_o_periodo_que_esta_na_tela(backend: Backend) -> None:
    """C2: ver mais que uma semana é gerar a página, não abrir outro painel."""
    [task_id] = semear(backend, "entrega desta semana")
    backend.completeTask(task_id)

    desta = Path(backend.exportCurrentWeek())
    assert "entrega desta semana" in desta.read_text(encoding="utf-8")

    # Andando para trás, a página é a daquele período — e não tem o de agora.
    backend.previousWeek()
    passada = Path(backend.exportCurrentWeek())
    assert passada != desta
    assert "entrega desta semana" not in passada.read_text(encoding="utf-8")


def test_exportar_avisa_com_o_caminho(backend: Backend) -> None:
    """Exportação sem retorno na tela é igual a exportação que não aconteceu."""
    avisos: list[str] = []
    backend.exported.connect(avisos.append)
    semear(backend, "algo")
    caminho = backend.exportEverything()
    assert avisos == [caminho]


def test_exportar_com_a_pasta_bloqueada_nao_derruba(backend: Backend) -> None:
    """Slot que levanta exceção morre dentro do laço de eventos do Qt."""
    falhas: list[int] = []
    backend.exportFailed.connect(lambda: falhas.append(1))

    # Um arquivo onde deveria haver uma pasta: `mkdir` falha com OSError.
    pasta = Path(backend.exportFolder)
    pasta.parent.mkdir(parents=True, exist_ok=True)
    pasta.write_text("nao sou uma pasta", encoding="utf-8")

    assert backend.exportEverything() == ""
    assert falhas == [1]


def test_exportar_duas_vezes_sobrescreve_a_mesma_pagina(backend: Backend) -> None:
    """O nome vem do período, então a página do período é uma só."""
    ids = semear(backend, "primeira", "segunda")
    backend.completeTask(ids[0])
    primeiro = backend.exportEverything()

    backend.completeTask(ids[1])
    segundo = backend.exportEverything()

    assert primeiro == segundo
    texto = Path(segundo).read_text(encoding="utf-8")
    assert "primeira" in texto and "segunda" in texto


# ------------------------------------------------------- o mural da parede
#
# Os papeizinhos pregados no quarto. O que se prova aqui é o corte e o filtro:
# a parede mostra o que ainda espera, e mostra pouco. O resto — quem abre, onde
# fica — é da tela, e quem cobre é o `tools/simular_uso.py`.


def test_o_mural_da_parede_mostra_as_ultimas_ideias(backend: Backend) -> None:
    """Da mais recente para a mais antiga, que é a ordem da projeção."""
    for texto in ("primeira", "segunda", "terceira"):
        backend.captureIdea(texto)

    assert [i["text"] for i in backend.wallIdeas] == ["terceira", "segunda", "primeira"]


def test_o_mural_da_parede_para_no_limite_do_desenho(backend: Backend) -> None:
    """É a folha que limita, como no bilhete: mural que rola não é mural."""
    for i in range(WALL_IDEAS_LIMIT + 4):
        backend.captureIdea(f"ideia {i}")

    assert len(backend.wallIdeas) == WALL_IDEAS_LIMIT


def test_a_ideia_aproveitada_sai_da_parede(backend: Backend) -> None:
    """E continua no painel, riscada — é lá que ela conta que virou tarefa.

    Na parede, um papel já resolvido é um papel que se tira: o mural mostra o
    que ainda espera, não o histórico.
    """
    backend.captureIdea("virar tarefa")
    backend.captureIdea("ficar esperando")
    [ideia] = [i for i in backend.ideas if i["text"] == "virar tarefa"]

    backend.ideaToTask(ideia["id"])

    assert [i["text"] for i in backend.wallIdeas] == ["ficar esperando"]
    assert [i["text"] for i in backend.ideas] == ["ficar esperando", "virar tarefa"]


def test_sem_ideia_solta_a_parede_fica_lisa(backend: Backend) -> None:
    """Zero, e não uma lista vazia com moldura: o QML esconde o objeto."""
    assert backend.wallIdeas == []


# ------------------------------------------- a superfície que o QML enxerga
#
# O `Backend` é a única coisa exposta ao QML, e são 52 propriedades. Cada teste
# deste arquivo lê as poucas de que precisa; ninguém lia todas — e a que
# levantasse exceção na primeira abertura derrubaria o app antes da primeira
# janela, que é o pior defeito possível e o mais fácil de não ter teste.
#
# A varredura abaixo sai do `staticMetaObject`, que é a mesma lista que o QML
# enxerga. Propriedade nova entra sozinha.


def propriedades() -> list[str]:
    """Os nomes que o QML pode ler, direto do metaobjeto do Qt."""
    meta = Backend.staticMetaObject
    return [
        meta.property(indice).name()
        for indice in range(meta.propertyOffset(), meta.propertyCount())
    ]


def test_a_varredura_alcanca_a_superficie_inteira() -> None:
    """Guarda das duas provas seguintes: lista vazia passaria calada."""
    nomes = propriedades()
    assert len(nomes) >= 50, f"achei só {len(nomes)} propriedades"
    # Uma de cada canto da tela, para o caso de o metaobjeto vir pela metade.
    assert {"backlog", "shelf", "weekDays", "plantStage", "soundMode"} <= set(nomes)


def _o_que_estourou(backend: Backend) -> list[str]:
    """Lê a superfície inteira e devolve o que levantou, com o motivo.

    Uma varredura e não um teste por propriedade: montar 52 backends para ler
    52 atributos custa mais do que a suíte inteira, e a falha interessa junta —
    "estas três propriedades quebram no log vazio" é o diagnóstico, não a
    primeira delas em ordem alfabética.
    """
    quebradas = []
    for nome in propriedades():
        try:
            getattr(backend, nome)
        # Captura larga de propósito: o que se procura é qualquer coisa
        # que estoure na leitura, não uma exceção prevista.
        except Exception as erro:
            quebradas.append(f"{nome}: {type(erro).__name__}: {erro}")
    return quebradas


def test_a_tela_inteira_monta_no_log_vazio(backend: Backend) -> None:
    """Primeira abertura: o log está vazio e o QML lê tudo isto de uma vez.

    Uma propriedade que estourasse aqui não daria erro de teste: daria um app
    que não abre, na máquina de quem acabou de instalar.
    """
    assert backend._events == []
    assert _o_que_estourou(backend) == []


def test_a_tela_inteira_monta_depois_de_um_dia_de_uso(backend: Backend) -> None:
    """E de novo com o quarto cheio: tarefa, sessão, entrega, ideia, revisão.

    Os dois extremos são o que importa, porque quase toda propriedade daqui
    projeta o log: as que quebram em lista vazia e as que quebram com conteúdo
    são defeitos diferentes.
    """
    ids = semear(backend, "entregar", "continuar")
    backend.startSession(ids[0])
    backend._clock.advance(timedelta(minutes=30))
    backend.endSessionAndComplete()
    backend.captureIdea("uma ideia")
    backend.saveReview(4, 3, "foi bom")

    assert _o_que_estourou(backend) == []


def test_ler_uma_propriedade_nao_muda_nada(tmp_path: Path) -> None:
    """Binding de QML relê o tempo todo, e leitura tem que ser leitura.

    Uma propriedade que gravasse evento, mexesse no foco ou virasse a página da
    semana ao ser lida faria a tela mudar sozinha — e o culpado seria
    procurado em qualquer lugar menos numa leitura.
    """
    with EventStore(tmp_path / "cantinho.db", device_id=DEVICE) as store:
        # Relógio parado: com o que anda, o cronômetro muda entre as duas
        # leituras por motivo legítimo e a comparação perde o sentido.
        backend = Backend(store, FakeClock(datetime.now(timezone.utc)))
        backend.addTask("uma tarefa")

        antes = len(backend._events)
        primeira = {nome: repr(getattr(backend, nome)) for nome in propriedades()}
        segunda = {nome: repr(getattr(backend, nome)) for nome in propriedades()}

        assert primeira == segunda
        assert len(backend._events) == antes
