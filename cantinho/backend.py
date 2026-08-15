"""Fronteira entre o log de eventos e o QML.

Este é o único objeto exposto ao QML, e as duas janelas se ligam à mesma
instância. Sem IPC e sem estado duplicado: a mini janela e a principal leem as
mesmas propriedades e chamam os mesmos slots.

O padrão de escrita é sempre o mesmo: montar o evento, gravar, recalcular as
projeções, avisar. Nunca alterar estado em memória por fora do log — se um
caminho fizer isso, reabrir o app mostra outra coisa.
"""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from cantinho.core import events as ev
from cantinho.core import export
from cantinho.core import projections as proj
from cantinho.core import schedule
from cantinho.core.clock import Clock
from cantinho.core.store import EventStore
from cantinho.services import scene
from cantinho.services.heartbeat import HEARTBEAT_FILENAME, Heartbeat
from cantinho.services.timer import SessionTimer

logger = logging.getLogger(__name__)

__all__ = ["Backend"]

# Quantas linhas cabem no bilhete da parede. É a folha que limita, não a
# projeção: uma lista que rola na parede deixaria de ser um bilhete.
BOARD_LIMIT = 6

# Quantos bilhetinhos de ideia cabem no mural da parede.
#
# Três, e o número é do desenho: são papeizinhos pregados num quarto, não uma
# lista. O mural inteiro continua a um clique dali — o que a parede mostra é que
# **existe** alguma coisa esperando, e o que é, não quantas são.
WALL_IDEAS_LIMIT = 3

# Quantas intenções `day.checkin` aceita numa lista só.
#
# Existe porque `LABEL_LIMIT` limita cada item e não a lista: com itens no
# tamanho máximo, algumas centenas deles passam do `PAYLOAD_LIMIT` e o evento
# se recusa a nascer — dentro de um slot, que é onde exceção derruba o app.
# Cinquenta itens de 200 caracteres dão 10 KB contra um teto de 64 KB, com
# folga de sobra. O outro kind de lista, `backlog.reordered`, não precisa de
# corte: são uuids gerados pelo app a partir do próprio backlog, e caberiam
# cerca de mil e seiscentos antes de o teto chegar perto.
CHECKIN_LIMIT = 50

# Modos de som, na ordem em que o botão gira.
#
# O do meio existe porque as duas pontas não davam conta: quem está numa
# chamada não quer chuva tocando, mas continua querendo o retorno do clique.
# "Sussurro" é o quarto calado com as mãos ainda fazendo barulho.
SOUND_MODES: tuple[str, ...] = ("tudo", "sussurro", "mudo")

# E é o do meio que abre o app.
#
# Som ambiente é a única coisa aqui que ocupa a sala sem ninguém ter pedido:
# quem abre o app às nove da manhã numa mesa compartilhada leva chuva tocando
# até achar onde desligar. O retorno do clique não tem esse problema — ele só
# soa em resposta a um gesto. Então o padrão é o quarto calado com a interface
# respondendo, e a música é uma escolha de quem quer companhia.
DEFAULT_SOUND_MODE = "sussurro"

# A partir de quanto tempo o app pergunta se mais alguma coisa se fechou junto.
#
# Uma hora de foco raramente é uma coisa só: no meio dela chega o pedido
# urgente, resolve-se o e-mail que estava travando outra pessoa, termina-se o
# que já estava quase pronto. Nada disso vira entrega, porque o gesto de
# registrar acontece no fim da sessão e a essa altura já se esqueceu.
#
# Não é cobrança e a diferença está na direção da pergunta: ela oferece crédito
# por trabalho já feito, e a resposta padrão é "só isso" sem nenhum custo.
LONG_SESSION_MINUTES = 60

# Quando o quarto lembra que o relógio ficou correndo, e de quanto em quanto.
#
# Duas horas é mais do que qualquer sessão de foco que alguém conduza de
# propósito; daí para cima o caso comum é timer esquecido. Insistir de meia em
# meia hora é o que faz isto servir para o caso real — quem saiu da mesa às
# 19h50 não estava lá para ver o primeiro aviso.
NUDGE_AFTER_MINUTES = 120
NUDGE_REPEAT_MINUTES = 30

# As frases, na ordem em que aparecem, girando quando acabam.
#
# São observações do quarto, não avisos de sistema: nenhuma diz quanto tempo
# passou, nenhuma pergunta se você ainda está trabalhando e nenhuma sugere que
# devia estar. O relógio da barra já mostra o número para quem quiser olhar.
#
# **Nenhuma passa de 36 caracteres**, e o limite é a mini: lá o toque ocupa a
# faixa do nome da tarefa, numa janela de 300 px, e o que não couber é elidido.
# Cortar a frase no meio come justamente o fim, que é onde ela diz alguma coisa
# — "Você ainda está por…" não é o texto que se escreveu.
NUDGES: tuple[str, ...] = (
    "O relógio ainda está correndo.",
    "Faz um tempo que ninguém passa aqui.",
    "A chuva não parou. Você parou?",
    "O abajur continua aceso.",
    "A planta pode esperar. Você também.",
)


class _RelogioFixo:
    """Relógio de um instante só, para datar um evento no passado.

    A recuperação de queda grava o fim de uma sessão na hora em que ele
    aconteceu, não na hora em que se descobriu que tinha acontecido — senão o
    evento entraria no log com o timestamp da reabertura e a sessão apareceria
    no dia errado. É o mesmo recurso que `tools/semear.py` usa.
    """

    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


def _texto(valor: str, limite: int) -> str:
    """Texto de entrada pronto para virar payload: sem folga nas pontas e cortado.

    Cortar aqui é o que garante que `check_limits` nunca dispare vindo da tela.
    A diferença importa: um slot que levanta exceção morre dentro do laço de
    eventos do Qt, e o usuário perde o app inteiro por ter colado um texto
    grande demais no campo errado.

    No caminho normal isto nunca corta nada, porque o campo da tela já recusa o
    que passa do limite (`CampoTexto.limite`). Isto é a rede para o resto: o
    atalho global, o roteiro de simulação, um caminho futuro que ninguém ligou
    a um campo.
    """
    limpo = valor.strip()
    return limpo if len(limpo) <= limite else limpo[:limite].strip()


def _format_elapsed(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    horas, resto = divmod(total, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segundos:02d}"
    return f"{minutos:02d}:{segundos:02d}"


class Backend(QObject):
    stateChanged = Signal()
    timerChanged = Signal()
    themeChanged = Signal()
    ideaSaved = Signal()
    captureRequested = Signal()
    miniVisibleChanged = Signal()
    mainVisibleChanged = Signal()
    soundChanged = Signal()
    motionChanged = Signal()
    routineChanged = Signal()
    focusChanged = Signal()
    weekChanged = Signal()
    recoveredChanged = Signal()
    tourChanged = Signal()
    # Uma sessão longa acabou de ser encerrada: leva os minutos dela.
    extraAsked = Signal(int)
    # O quarto lembrando que o relógio ficou correndo. Leva a frase.
    nudged = Signal(str)
    # Reação curta de interface (passar o mouse, clicar, concluir). Quem toca é
    # `services/audio.py`; o backend só avisa, para o QML não precisar conhecer
    # o serviço de áudio.
    sfxRequested = Signal(str)
    quitRequested = Signal()
    # A página foi escrita: leva o caminho dela.
    exported = Signal(str)
    exportFailed = Signal()

    def __init__(
        self,
        store: EventStore,
        clock: Clock,
        parent: QObject | None = None,
        heartbeat: Heartbeat | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._clock = clock
        self._events: list[ev.Event] = store.read_all()
        self._heartbeat = heartbeat or Heartbeat(
            store.db_path.parent / HEARTBEAT_FILENAME
        )

        self._timer = SessionTimer(clock, self)
        self._timer.tick.connect(self.timerChanged)

        self._theme_mode = "auto"
        self._mini_visible = False
        self._main_visible = True
        # Só nesta sessão. Preferência de som não vai a disco: `events` é a
        # única tabela persistida, e "liguei o som" não é fato do histórico.
        self._sound_mode = DEFAULT_SOUND_MODE
        # Para o interruptor da mini, que só tem duas posições: ele desliga
        # tudo e devolve exatamente o estado anterior, sem passar pelo ciclo
        # de três do menu.
        self._sound_before_mute = DEFAULT_SOUND_MODE
        # O quarto respira. Mesma natureza do som: preferência da sessão, não
        # fato do histórico, então não vai para o log.
        self._motion = True

        # Qual tarefa o botão "começar" vai pegar. Vazio significa "a primeira
        # do hoje" — ver `focusedTaskId`.
        self._focused_task = ""
        self._free_session = False

        # Quantas semanas atrás o painel da semana está olhando. 0 é esta.
        self._week_offset = 0

        # Em que marca de minutos o próximo toque do quarto vai soar.
        self._proximo_toque = NUDGE_AFTER_MINUTES
        self._toques_dados = 0

        # O passeio da primeira abertura. Ver `showTour`.
        self._passeio = not self._events

        # Reavalia o que depende do relógio de tempos em tempos. Um minuto é
        # folgado de sobra para uma transição que leva três segundos, e é fino
        # o bastante para a virada do dia não passar despercebida.
        self._relogio_tema = QTimer(self)
        self._relogio_tema.setInterval(60_000)
        self._relogio_tema.timeout.connect(self._reavaliar_relogio)
        self._relogio_tema.start()
        self._era_noite = self._noite_pelo_relogio()
        self._marca = self._proxima_virada()
        self._dia = self._hoje()

        # Antes do primeiro `_recomputar`: a recuperação escreve eventos, e a
        # projeção tem que já nascer contando com eles.
        self._recuperada: proj.Session | None = None
        self._recuperar_sessoes_orfas()

        self._recomputar()

    # ------------------------------------------------------------------ log

    def _registrar(self, evento: ev.Event) -> None:
        """Grava e recalcula. Único caminho de escrita do app."""
        if self._store.append(evento):
            self._events.append(evento)
            self._recomputar()
        else:
            logger.warning("evento duplicado ignorado: %s", evento.uuid)

    def _registrar_lote(self, eventos: list[ev.Event]) -> None:
        """Grava vários eventos e recalcula uma vez só.

        Não é sobre atomicidade: o log é append-only justamente para que cada
        evento seja um fato independente, e um lote pela metade continua sendo
        um estado legítimo e corrigível. O que se ganha aqui é o estado final
        único — "entreguei" gravava dois eventos e reprojetava duas vezes,
        emitindo duas rajadas de sinal, e a tela via um quadro intermediário
        onde a sessão já tinha acabado e a tarefa ainda não. É esse quadro que
        estraga qualquer animação de chegada na estante.
        """
        if not eventos:
            return
        inseridos = self._store.append_many(eventos)
        if inseridos != len(eventos):
            # Só acontece com uuid repetido, que aqui é sempre recém-sorteado.
            logger.warning(
                "lote de %d eventos gravou %d", len(eventos), inseridos
            )
        self._events.extend(eventos)
        self._recomputar()

    def _recomputar(self) -> None:
        """Reprojeta tudo do zero.

        Recalcular a lista inteira a cada evento parece desperdício e não é: o
        log de uso pessoal é pequeno, e qualquer atalho incremental abriria a
        porta para o estado da tela divergir do log.
        """
        eventos = self._events
        self._backlog = proj.open_tasks(eventos)
        self._concluidas = proj.completed_tasks(eventos)
        self._estante = proj.shelf_objects(eventos)
        self._ideias = proj.ideas(eventos)
        self._estagio = proj.plant_stage(eventos, self._clock.now())
        self.stateChanged.emit()
        # A tarefa em foco é derivada do backlog: concluir a que estava
        # escolhida faz a próxima assumir sozinha.
        self.focusChanged.emit()
        self.weekChanged.emit()

    @property
    def device_id(self) -> str:
        return self._store.device_id

    @property
    def on_tray(self) -> bool:
        """As duas janelas escondidas: o app existe só como ícone.

        É um estado legítimo, e o único em que o quarto não tem onde falar —
        nem a tira acima da barra, nem a faixa da mini. Quem decide o que fazer
        com isso é `main.py`, que tem a bandeja na mão; aqui fica só a pergunta,
        porque ela é sobre as janelas e as janelas são daqui.
        """
        return not self._main_visible and not self._mini_visible

    def _agora_local(self) -> datetime:
        """Horário de parede, derivado do relógio injetado.

        Pelo `datetime.now()` direto, nada que dependa de "hoje" — o bilhete, a
        semana, a virada da meia-noite — era testável sem esperar a meia-noite
        chegar de verdade. O clock devolve UTC; a conversão para local acontece
        aqui, que é a fronteira de apresentação.
        """
        return self._clock.now().astimezone()

    def _hoje(self) -> date:
        return self._agora_local().date()

    def _fuso(self):  # type: ignore[no-untyped-def]
        return self._agora_local().tzinfo

    # ------------------------------------------------------------- backlog

    def _task_dict(self, task: proj.Task) -> dict:
        return {
            "id": task.id,
            "label": task.label,
            "project": task.project or "",
        }

    @Property("QVariantList", notify=stateChanged)
    def backlog(self) -> list[dict]:
        return [self._task_dict(task) for task in self._backlog]

    @Property("QVariantList", notify=stateChanged)
    def today(self) -> list[dict]:
        return [self._task_dict(task) for task in self._backlog[: proj.TODAY_LIMIT]]

    @Property(int, constant=True)
    def todayLimit(self) -> int:
        return proj.TODAY_LIMIT

    # Os limites de texto, para os campos da tela recusarem o que o log não
    # aceitaria. Ficam aqui em vez de repetidos no QML porque quem manda é o
    # contrato do evento, não a caixa de texto.
    @Property(int, constant=True)
    def labelLimit(self) -> int:
        return ev.LABEL_LIMIT

    @Property(int, constant=True)
    def textLimit(self) -> int:
        return ev.TEXT_LIMIT

    @Property(bool, notify=stateChanged)
    def backlogEmpty(self) -> bool:
        return not self._backlog

    @Slot(str)
    @Slot(str, str)
    def addTask(self, label: str, project: str = "") -> None:
        label = _texto(label, ev.LABEL_LIMIT)
        if not label:
            return
        self._registrar(
            ev.task_created(
                self._clock,
                self.device_id,
                label=label,
                project=_texto(project, ev.LABEL_LIMIT) or None,
            )
        )

    @Slot(str)
    def addAndCompleteTask(self, label: str) -> None:
        """Registra algo que já foi feito e nunca esteve na lista.

        É a resposta à pergunta do fim da sessão longa: no meio de duas horas
        aparece o pedido urgente que ninguém teve tempo de anotar antes de
        atender. Sem isto, registrá-lo exigiria criar a tarefa e concluí-la em
        dois gestos, com a linha aparecendo no "hoje" no meio do caminho.

        Dois eventos no mesmo lote, como todo composto: `task.created` e
        `task.completed` continuam sendo fatos distintos no log.
        """
        label = _texto(label, ev.LABEL_LIMIT)
        if not label:
            return
        tarefa = ev.task_created(self._clock, self.device_id, label=label)
        self._registrar_lote(
            [
                tarefa,
                ev.task_completed(
                    self._clock, self.device_id, id=tarefa.payload["id"]
                ),
            ]
        )

    @Slot(str, str)
    def renameTask(self, task_id: str, label: str) -> None:
        """Corrige o texto de uma tarefa.

        Não é edição: `task.created` continua no log como foi escrito, e o
        rótulo novo é um evento posterior. O id não muda, então o objeto que a
        tarefa vai deixar na estante continua sendo o mesmo desenho.

        Rótulo vazio ou igual ao atual não gera evento — um log cheio de
        renomeações que não mudaram nada é ruído.
        """
        label = _texto(label, ev.LABEL_LIMIT)
        if not task_id or not label:
            return
        atual = next((task for task in self._backlog if task.id == task_id), None)
        if atual is None or atual.label == label:
            return
        self._registrar(
            ev.task_renamed(self._clock, self.device_id, id=task_id, label=label)
        )

    def _esta_aberta(self, task_id: str) -> bool:
        """Se a tarefa existe e ainda está no backlog.

        Concluir ou arquivar o que não está aberto é um evento que nenhuma
        projeção lê — e que fica no log para sempre, porque não há DELETE.
        Barato de recusar aqui, impossível de tirar depois.
        """
        return any(task.id == task_id for task in self._backlog)

    @Slot(str)
    def completeTask(self, task_id: str) -> None:
        if not self._esta_aberta(task_id):
            return
        self._registrar(ev.task_completed(self._clock, self.device_id, id=task_id))

    @Slot(str)
    def archiveTask(self, task_id: str) -> None:
        """Some da lista sem virar entrega. Não apaga nada: é um evento novo."""
        if not self._esta_aberta(task_id):
            return
        self._registrar(ev.task_archived(self._clock, self.device_id, id=task_id))

    @Slot("QVariantList")
    def reorderBacklog(self, ordem: list) -> None:
        ids = [str(item) for item in ordem if str(item).strip()]
        if not ids or ids == [task.id for task in self._backlog]:
            return
        self._registrar(
            ev.backlog_reordered(self._clock, self.device_id, order=ids)
        )

    # ------------------------------------------------------- tarefa em foco
    #
    # "Começar" precisava saber o que começar.
    #
    # Antes o botão da barra abria sempre uma sessão livre, e a única forma de
    # prender o timer a uma tarefa era abrir o "hoje" e mirar a palavra
    # "começar" na linha certa. Quem apertasse o botão grande — que é o gesto
    # óbvio — gravava tempo que não ia para tarefa nenhuma e não podia ser
    # concluído: o "entreguei" nem aparecia.
    #
    # A tarefa em foco resolve isso sem inventar estado persistido: ela é
    # derivada do backlog. Vazia significa "a primeira do hoje", e escolher
    # outra é preferência da sessão, não fato do histórico — se o app fechar,
    # o foco volta a ser o topo da lista, que é o que a lista já diz.

    @Property(str, notify=focusChanged)
    def focusedTaskId(self) -> str:
        """A tarefa que o "começar" vai pegar. Vazio = sessão livre."""
        if self._timer.running:
            return self._timer.task_id or ""
        if self._free_session:
            return ""
        abertas = {task.id for task in self._backlog}
        if self._focused_task in abertas:
            return self._focused_task
        # A escolhida saiu do backlog (foi concluída ou arquivada). Em vez de
        # apontar para o vazio, o foco cai no topo do "hoje".
        return self._backlog[0].id if self._backlog else ""

    @Property(str, notify=focusChanged)
    def focusedTaskLabel(self) -> str:
        alvo = self.focusedTaskId
        if not alvo:
            return ""
        for task in self._backlog:
            if task.id == alvo:
                return task.label
        return self.currentTaskLabel

    @Property(bool, notify=focusChanged)
    def freeSessionChosen(self) -> bool:
        """Sessão livre pedida de propósito, e não por falta de tarefa."""
        return self._free_session and not self._timer.running

    @Slot(str)
    def setFocusedTask(self, task_id: str) -> None:
        """Escolhe o que vem agora. String vazia pede uma sessão livre."""
        task_id = task_id.strip()
        if task_id and task_id not in {task.id for task in self._backlog}:
            return
        self._focused_task = task_id
        self._free_session = not task_id
        self.focusChanged.emit()

    @Slot()
    def focusNext(self) -> None:
        """Passa para a próxima tarefa do "hoje", e da última volta à primeira.

        É o que a mini usa: numa janela de 300 pixels não cabe uma lista, e
        avançar de uma em uma resolve o caso real — trocar do item de cima para
        o de baixo sem abrir a janela grande.
        """
        if not self._backlog:
            return
        ids = [task.id for task in self._backlog[: proj.TODAY_LIMIT]]
        atual = self.focusedTaskId
        proximo = ids[(ids.index(atual) + 1) % len(ids)] if atual in ids else ids[0]
        self.setFocusedTask(proximo)

    # --------------------------------------------------------------- timer

    @Property(bool, notify=timerChanged)
    def timerRunning(self) -> bool:
        return self._timer.running

    @Property(str, notify=timerChanged)
    def elapsedText(self) -> str:
        return _format_elapsed(self._timer.elapsed)

    @Property(str, notify=timerChanged)
    def currentTaskId(self) -> str:
        return self._timer.task_id or ""

    def _rotulo(self, task_id: str | None) -> str:
        """O texto de uma tarefa, esteja ela aberta ou já concluída."""
        if not task_id:
            return ""
        for task in self._backlog:
            if task.id == task_id:
                return task.label
        for task in self._concluidas:
            if task.id == task_id:
                return task.label
        return ""

    @Property(str, notify=timerChanged)
    def currentTaskLabel(self) -> str:
        return self._rotulo(self._timer.task_id)

    @Slot()
    @Slot(str)
    def startSession(self, task_id: str = "") -> None:
        if self._timer.running:
            return
        task_id = task_id.strip()
        evento = ev.session_started(
            self._clock, self.device_id, task_id=task_id or None
        )
        self._registrar(evento)
        self._timer.start(
            evento.payload["id"], evento.payload.get("task_id"), evento.occurred_at
        )
        # Marca de vida já no começo: uma queda aos trinta segundos precisa ter
        # onde fechar a sessão.
        self._heartbeat.beat(evento.occurred_at)
        self._proximo_toque = NUDGE_AFTER_MINUTES
        self._toques_dados = 0
        # Começar algo novo responde ao aviso da queda: quem escolheu o que
        # fazer agora já leu o que aconteceu com a sessão de antes.
        self.dismissRecovered()
        # Começar por uma tarefa é escolhê-la: sem isto, encerrar a sessão
        # devolveria o foco ao topo da lista e o botão passaria a apontar para
        # outra coisa que não a que se acabou de trabalhar.
        if task_id:
            self._focused_task = task_id
            self._free_session = False
        self.timerChanged.emit()
        self.focusChanged.emit()

    @Slot()
    def startFocused(self) -> None:
        """O que o botão grande faz: começa pela tarefa em foco.

        Sem tarefa nenhuma em foco — backlog vazio, ou sessão livre escolhida
        de propósito — vira uma sessão solta, que continua sendo um uso
        legítimo: às vezes o trabalho não estava na lista.
        """
        self.startSession(self.focusedTaskId)

    def _evento_de_fim(self, interrupted: bool, note: str) -> ev.Event | None:
        """O `session.ended` da sessão corrente, ou None se não há nenhuma."""
        session_id = self._timer.session_id
        if session_id is None:
            return None
        return ev.session_ended(
            self._clock,
            self.device_id,
            id=session_id,
            interrupted=bool(interrupted),
            note=_texto(note, ev.TEXT_LIMIT) or None,
        )

    def _parar_timer(self) -> None:
        self._timer.stop()
        # Sem sessão correndo não há o que recuperar: a marca sai junto, e é o
        # que faz "existe heartbeat em disco" significar "o app morreu de pé".
        self._heartbeat.clear()
        self._proximo_toque = NUDGE_AFTER_MINUTES
        self._toques_dados = 0
        self.timerChanged.emit()
        self.focusChanged.emit()

    def _talvez_perguntar_extra(self, decorrido: timedelta) -> None:
        """Depois de uma sessão longa, pergunta se mais algo se fechou junto.

        Uma hora raramente é uma coisa só. No meio dela chega o pedido urgente,
        resolve-se o e-mail que travava outra pessoa, termina-se o que já estava
        quase pronto — e nada disso vira entrega, porque o gesto de registrar
        acontece no fim e a essa altura já se esqueceu.

        Traz a janela grande de volta se for preciso: quem começou pelo "hoje"
        está na mini, e uma pergunta que ninguém vê não é uma pergunta.
        """
        minutos = int(round(decorrido.total_seconds() / 60))
        if minutos < LONG_SESSION_MINUTES:
            return
        self.setMainVisible(True)
        self.extraAsked.emit(minutos)

    @Slot()
    @Slot(bool)
    @Slot(bool, str)
    def endSession(self, interrupted: bool = False, note: str = "") -> None:
        evento = self._evento_de_fim(interrupted, note)
        if evento is None:
            return
        decorrido = self._timer.elapsed
        self._registrar(evento)
        self._parar_timer()
        self._talvez_perguntar_extra(decorrido)

    @Slot()
    def endOpenSession(self) -> None:
        """Fecha a sessão aberta antes de o app morrer.

        Ligado ao `aboutToQuit` da aplicação, e é lá que ele tem que estar: há
        três caminhos de saída — o botão da tela, o menu da bandeja e, quando
        não há bandeja, fechar a última janela — e só o primeiro passava pelo
        backend. Nos outros dois o `session.started` ficava órfão no log, e
        sessão sem fim não conta em lugar nenhum: nem no foco de 14 dias, nem
        no bilhete, nem na semana. O tempo simplesmente sumia.

        É a mesma decisão que `endDay` já tomava — encerrar é um gesto que
        guarda o que estava correndo, não um que o descarta.
        """
        if self._timer.running:
            logger.info("guardando a sessão aberta antes de sair")
            self.endSession(False, "")

    @Slot()
    def endSessionAndComplete(self) -> None:
        """Encerra a sessão e conclui a tarefa dela, num gesto só.

        Sem isto, terminar de trabalhar em algo eram dois movimentos em lugares
        diferentes: encerrar na barra e depois abrir a lista para marcar o
        círculo. O objeto só ia para a estante no segundo, e é o objeto que dá
        o retorno — então a metade que importa dependia de lembrar de fazê-la.

        Dois eventos, não um: `session.ended` e `task.completed` são fatos
        distintos e continuam separados no log. O que mudou é o gesto — hoje
        ele se chama "entreguei", que é o verbo da estante: quem lê a palavra
        já sabe onde a tarefa vai parar.

        Os dois vão no mesmo lote para a tela pular direto ao estado final. Em
        duas gravações separadas havia um quadro no meio em que a sessão já
        tinha acabado e a tarefa ainda não estava na estante.
        """
        fim = self._evento_de_fim(False, "")
        if fim is None:
            return
        task_id = self._timer.task_id
        decorrido = self._timer.elapsed
        eventos = [fim]
        if task_id and self._esta_aberta(task_id):
            eventos.append(
                ev.task_completed(self._clock, self.device_id, id=task_id)
            )
        self._registrar_lote(eventos)
        self._parar_timer()
        self._talvez_perguntar_extra(decorrido)

    # -------------------------------------------------- recuperação de queda
    #
    # Nenhuma sessão fica aberta para sempre.
    #
    # Saída normal já grava o fim, por qualquer um dos três caminhos (ver
    # `endOpenSession`). O que sobra é o que ninguém controla: falta de energia,
    # sessão do sistema derrubada, processo morto. Nesses casos o log fica com
    # um `session.started` sem par, e sessão sem fim não conta em lugar nenhum
    # — some do foco de 14 dias, do bilhete e da semana.
    #
    # O fim é gravado na **última marca de vida** (`services/heartbeat.py`), que
    # é o último instante em que o app comprovadamente estava rodando. É a única
    # hora de término que não é chute: fechar "agora", na reabertura, daria
    # catorze horas de foco a uma máquina que passou a noite desligada.
    #
    # Sem marca legível — primeira execução depois de atualizar, disco cheio,
    # arquivo truncado pela queda —, a sessão é fechada no próprio começo. Zero
    # minuto é uma perda honesta; o inverso não é.
    #
    # A sessão vai como `interrupted`, que é literalmente o que aconteceu, e o
    # tempo continua contando no foco: o projeto não desconta esforço de quem
    # foi interrompido, e uma queda de energia é a interrupção mais legítima que
    # existe.

    def _recuperar_sessoes_orfas(self) -> None:
        """Fecha toda sessão que ficou aberta, na última marca de vida."""
        abertas = [s for s in proj.sessions(self._events) if s.ended_at is None]
        if not abertas:
            self._heartbeat.clear()
            return

        marca = self._heartbeat.last()
        agora = self._clock.now()
        if marca is None:
            logger.info("sem marca de vida: sessões órfãs fecham no começo")
        elif marca > agora:
            # Relógio do sistema andou para trás entre a queda e agora. A marca
            # deixa de ser um limite superior confiável, então não se usa.
            logger.warning("marca de vida no futuro (%s): ignorada", marca)
            marca = None

        eventos: list[ev.Event] = []
        for sessao in abertas:
            fim = sessao.started_at if marca is None else max(marca, sessao.started_at)
            eventos.append(
                ev.session_ended(
                    _RelogioFixo(fim),
                    self.device_id,
                    id=sessao.id,
                    interrupted=True,
                    note=None,
                )
            )
            logger.info(
                "sessão órfã %s fechada em %s", sessao.id, fim.isoformat()
            )

        # A última é a que a tela conta, já com o fim que acabou de ser gravado.
        ultima = abertas[-1]
        fim_da_ultima = (
            ultima.started_at if marca is None else max(marca, ultima.started_at)
        )
        self._recuperada = replace(ultima, ended_at=fim_da_ultima, interrupted=True)

        self._heartbeat.clear()
        self._registrar_lote(eventos)

    @Property(bool, notify=recoveredChanged)
    def hasRecoveredSession(self) -> bool:
        return self._recuperada is not None

    @Property(str, notify=recoveredChanged)
    def recoveredLabel(self) -> str:
        if self._recuperada is None:
            return ""
        return self._rotulo(self._recuperada.task_id)

    @Property(str, notify=recoveredChanged)
    def recoveredTaskId(self) -> str:
        if self._recuperada is None:
            return ""
        return self._recuperada.task_id or ""

    @Property(str, notify=recoveredChanged)
    def recoveredUntil(self) -> str:
        """Até que hora ela foi guardada. Com a data quando não foi hoje."""
        if self._recuperada is None or self._recuperada.ended_at is None:
            return ""
        fim = self._recuperada.ended_at.astimezone(self._fuso())
        if fim.date() == self._hoje():
            return fim.strftime("%H:%M")
        return fim.strftime("%d/%m às %H:%M")

    @Property(int, notify=recoveredChanged)
    def recoveredMinutes(self) -> int:
        if self._recuperada is None:
            return 0
        return int(round(self._recuperada.duration_minutes))

    @Slot()
    def dismissRecovered(self) -> None:
        """Tira o aviso da tela. O que estava para gravar já foi gravado."""
        if self._recuperada is not None:
            self._recuperada = None
            self.recoveredChanged.emit()

    @Slot()
    def continueRecovered(self) -> None:
        """Abre uma sessão nova na mesma tarefa, do zero.

        Não é "retomar": a sessão de antes já está fechada no log, com o tempo
        que dava para provar. Continuar é começar de novo o que se estava
        fazendo, que é o que o usuário quer dizer ao voltar para a mesa.
        """
        task_id = self.recoveredTaskId
        self.dismissRecovered()
        if not self._timer.running:
            self.startSession(task_id)

    # -------------------------------------------------------- o passeio
    #
    # A primeira abertura precisa explicar o quarto, porque nada aqui se
    # anuncia: não há rótulo de "produtividade", nem menu de arquivo, nem lugar
    # óbvio para clicar primeiro. Quem abre pela primeira vez vê um cômodo
    # bonito e não sabe que a estante é a razão de tudo.
    #
    # **Nenhuma flag de "já viu" vai a disco**, e não é preguiça: o sinal de
    # primeira abertura já existe e é exato — o log está vazio. Não há evento
    # nenhum, então ninguém escreveu tarefa, ideia ou sessão neste banco.
    # Guardar um booleano ao lado disso seria uma segunda fonte de verdade
    # sobre a mesma pergunta, com a chance de as duas discordarem.
    #
    # A consequência: quem abre, dispensa o passeio e fecha o app sem fazer
    # nada, vê o passeio de novo na vez seguinte. É a leitura honesta do estado
    # — essa pessoa de fato ainda não começou. Basta uma tarefa, uma ideia ou
    # uma sessão para ele nunca mais aparecer sozinho.
    #
    # E não some para sempre: `startTour` traz ele de volta pelo menu do quarto.

    @Property(bool, notify=tourChanged)
    def showTour(self) -> bool:
        return self._passeio

    @Property(int, notify=tourChanged)
    def tourAvatarStage(self) -> int:
        """O estágio da planta que guia o passeio: fixo, como o do ícone.

        Não acompanha `plantStage` de propósito. Numa primeira abertura ele
        seria 0 — um vaso com terra —, e a figura que apresenta o app não pode
        ser a versão mais murcha dele. É o mesmo estágio 2 do ícone da janela,
        então quem aprende o app com esta figura reconhece o programa na barra
        de tarefas depois.
        """
        return 2

    @Slot()
    def dismissTour(self) -> None:
        if self._passeio:
            self._passeio = False
            self.tourChanged.emit()

    @Slot()
    def startTour(self) -> None:
        """Rever o passeio, pelo menu do quarto."""
        if not self._passeio:
            self._passeio = True
            self.tourChanged.emit()

    # -------------------------------------------------------------- estante

    @Property("QVariantList", notify=stateChanged)
    def shelf(self) -> list[str]:
        return [objeto.object_type for objeto in self._estante]

    @Property("QVariantList", notify=stateChanged)
    def shelfSlots(self) -> list[dict]:
        """Onde cada objeto está e o que ele é, em coordenada do viewBox.

        Existe para o quarto poder dizer **qual tarefa** é cada objeto quando o
        mouse passa por cima. A estante é o retorno central do app e era a única
        coisa da tela que não sabia se explicar: um objeto na prateleira é
        recompensa, e recompensa que não se sabe do quê é decoração.

        A posição vem de `scene.shelf_slots`, a mesma função que o provedor usa
        para desenhar — se as duas contas divergissem, o rótulo apareceria ao
        lado do objeto errado, que é pior do que não aparecer. O QML converte
        para pixel de tela por `Room.cx`/`cy`, porque a cena é centralizada e
        escalada.

        A lista é cortada na lotação do desenho, não na do log: a projeção
        guarda todas as entregas para sempre, e é a arte que comporta doze. Sem
        o corte, `zip(..., strict=True)` estoura na décima terceira — dentro de
        uma propriedade lida pelo QML, que é onde exceção vira tela quebrada.
        """
        posicoes = scene.shelf_slots(len(self._estante))
        return [
            {"label": objeto.label, "x": x, "y": y}
            for objeto, (x, y) in zip(
                self._estante[: len(posicoes)], posicoes, strict=True
            )
        ]

    @Property(int, notify=stateChanged)
    def plantStage(self) -> int:
        return self._estagio

    # --------------------------------------------------------------- ideias

    @Property("QVariantList", notify=stateChanged)
    def ideas(self) -> list[dict]:
        return [
            {
                "id": ideia.id,
                "text": ideia.text,
                "when": ideia.captured_at.astimezone().strftime("%d/%m %H:%M"),
                "used": ideia.used,
                "taskId": ideia.task_id or "",
            }
            for ideia in self._ideias
        ]

    @Property("QVariantList", notify=stateChanged)
    def wallIdeas(self) -> list[dict]:
        """As ideias que ainda esperam, prontas para o mural da parede.

        Só as soltas. As aproveitadas continuam no painel, riscadas e com a
        data — é lá que elas contam a história de que a ideia virou tarefa. Na
        parede seriam ruído: um papelzinho pregado que já foi resolvido é um
        papelzinho que se tira.

        A projeção já entrega as soltas primeiro e da mais recente para a mais
        antiga, então cortar no começo dá as últimas três. O corte é do desenho,
        como o do bilhete — ver `WALL_IDEAS_LIMIT`.
        """
        return [
            {"id": ideia.id, "text": ideia.text}
            for ideia in self._ideias
            if not ideia.used
        ][:WALL_IDEAS_LIMIT]

    @Slot(str)
    def captureIdea(self, text: str) -> None:
        text = _texto(text, ev.TEXT_LIMIT)
        if not text:
            return
        self._registrar(ev.idea_captured(self._clock, self.device_id, text=text))
        self.ideaSaved.emit()

    @Slot(str)
    def ideaToTask(self, idea_id: str) -> None:
        """Uma ideia vira tarefa quando o usuário decide, não na captura.

        Dois eventos, nesta ordem: a tarefa nasce e a ideia é marcada como
        aproveitada, apontando para ela. A ideia continua no mural, riscada —
        o mural é o registro de onde as tarefas vieram.

        No mesmo lote, para a tela não ver o quadro em que a tarefa já existe e
        a ideia ainda está por riscar.
        """
        ideia = next((item for item in self._ideias if item.id == idea_id), None)
        if ideia is None or ideia.used:
            return
        tarefa = ev.task_created(self._clock, self.device_id, label=ideia.text)
        self._registrar_lote(
            [
                tarefa,
                ev.idea_promoted(
                    self._clock,
                    self.device_id,
                    id=ideia.id,
                    task_id=tarefa.payload["id"],
                ),
            ]
        )

    @Slot(str)
    def archiveIdea(self, idea_id: str) -> None:
        """Tira a ideia do mural. Não apaga nada: é um evento novo."""
        if not idea_id:
            return
        self._registrar(ev.idea_archived(self._clock, self.device_id, id=idea_id))

    # -------------------------------------------------------- retrospectiva

    @Property(str, notify=stateChanged)
    def todayDate(self) -> str:
        return self._hoje().isoformat()

    @Property("QVariantList", notify=stateChanged)
    def todaySessions(self) -> list[dict]:
        rotulos = {task.id: task.label for task in self._backlog + self._concluidas}
        do_dia = proj.sessions_on(self._events, self._hoje(), self._fuso())
        return [
            {
                "label": rotulos.get(sessao.task_id or "", "sem tarefa"),
                "minutes": int(round(sessao.duration_minutes)),
                "interrupted": sessao.interrupted,
                "at": sessao.started_at.astimezone().strftime("%H:%M"),
            }
            for sessao in do_dia
        ]

    def _minutos_por_tarefa_hoje(self) -> dict[str, float]:
        """Minutos de sessão encerrada hoje, somados por tarefa.

        Sessão sem tarefa cai na chave vazia. Sessão ainda aberta não entra: a
        que está correndo agora é o relógio da barra, não um número que se
        soma.
        """
        total: dict[str, float] = {}
        for sessao in proj.sessions_on(self._events, self._hoje(), self._fuso()):
            chave = sessao.task_id or ""
            total[chave] = total.get(chave, 0.0) + sessao.duration_minutes
        return total

    @Property("QVariantList", notify=stateChanged)
    def todayBoard(self) -> list[dict]:
        """As linhas do bilhete pregado na parede.

        Primeiro o que ainda está aberto no "Hoje", depois o que foi concluído
        hoje — que fica na folha, riscado, até o dia virar. Riscar é o que dá
        peso ao que foi feito; some da lista amanhã, sozinho.

        Cada linha leva os minutos que a tarefa recebeu hoje. É o que faz o
        tempo aparecer sem precisar abrir nada: até aqui ele só existia dentro
        da retrospectiva, no fim do dia, que é tarde demais para servir de
        informação.
        """
        fuso = self._fuso()
        hoje = self._hoje()
        minutos = self._minutos_por_tarefa_hoje()
        abertas = [
            {
                "id": task.id,
                "label": task.label,
                "done": False,
                "minutes": int(round(minutos.get(task.id, 0.0))),
            }
            for task in self._backlog[: proj.TODAY_LIMIT]
        ]
        feitas = [
            {
                "id": task.id,
                "label": task.label,
                "done": True,
                "minutes": int(round(minutos.get(task.id, 0.0))),
            }
            for task in reversed(self._concluidas)
            if task.completed_at is not None
            and task.completed_at.astimezone(fuso).date() == hoje
        ]
        return (abertas + feitas)[:BOARD_LIMIT]

    @Property(int, notify=stateChanged)
    def todayMinutes(self) -> int:
        """Tudo que foi registrado hoje, inclusive sessão sem tarefa."""
        return int(round(sum(self._minutos_por_tarefa_hoje().values())))

    @Property("QVariantList", notify=stateChanged)
    def todayCompleted(self) -> list[str]:
        fuso = self._fuso()
        hoje = self._hoje()
        return [
            task.label
            for task in self._concluidas
            if task.completed_at is not None
            and task.completed_at.astimezone(fuso).date() == hoje
        ]

    @Property("QVariant", notify=stateChanged)
    def todayReview(self) -> dict | None:
        revisao = proj.review_for(self._events, self._hoje())
        if revisao is None:
            return None
        return {
            "mood": revisao.mood,
            "energy": revisao.energy,
            "note": revisao.note or "",
        }

    @Slot(int, int)
    @Slot(int, int, str)
    def saveReview(self, mood: int, energy: int, note: str = "") -> None:
        self._registrar(
            ev.day_review(
                self._clock,
                self.device_id,
                date=self._hoje().isoformat(),
                mood=int(mood),
                energy=int(energy),
                note=_texto(note, ev.TEXT_LIMIT) or None,
            )
        )

    @Property(bool, notify=stateChanged)
    def dayClosed(self) -> bool:
        """O dia já foi guardado no diário."""
        return proj.review_for(self._events, self._hoje()) is not None

    @Slot(int, int)
    @Slot(int, int, str)
    def endDay(self, mood: int, energy: int, note: str = "") -> None:
        """Encerra o dia: para o relógio, se estiver correndo, e guarda a nota.

        O botão que faltava. "Guardar o dia" escrevia a revisão e deixava a
        sessão rodando — quem fechava o app em seguida perdia o tempo aberto, e
        quem esquecia o timer ligado voltava no dia seguinte com uma sessão de
        catorze horas. Encerrar o dia é um gesto só: o que estava correndo é
        guardado, e o diário fecha.

        Gesto só na tela e lote só no log: o dia não fecha pela metade.

        Pergunta o que mais se fechou junto, pela mesma razão que "entreguei" e
        "parar" perguntam: uma sessão longa raramente é uma coisa só, e o gesto
        de registrar acontece no fim, quando já se esqueceu. Encerrar o dia com
        três horas correndo é o caso mais forte disso, não o mais fraco — era a
        única saída de sessão que não perguntava nada.
        """
        decorrido = self._timer.elapsed
        fim = self._evento_de_fim(False, "")
        eventos = [] if fim is None else [fim]
        eventos.append(
            ev.day_review(
                self._clock,
                self.device_id,
                date=self._hoje().isoformat(),
                mood=int(mood),
                energy=int(energy),
                note=_texto(note, ev.TEXT_LIMIT) or None,
            )
        )
        self._registrar_lote(eventos)
        if fim is not None:
            self._parar_timer()
            self._talvez_perguntar_extra(decorrido)

    @Slot("QVariantList")
    def saveCheckin(self, intents: list) -> None:
        # Limitar cada item não limita a lista, e é ela que pode estourar o
        # teto do payload — com o limite por item respeitado, item por item.
        # Aqui a lista é cortada; quem recusa de vez é `check_limits`, e a
        # divisão é a mesma do texto: o slot nunca levanta, o contrato nunca
        # cede. O corte é folgado de propósito — não é opinião sobre quantas
        # intenções cabem num dia, é o ponto onde deixou de ser uma lista.
        textos = [
            texto
            for texto in (_texto(str(item), ev.LABEL_LIMIT) for item in intents)
            if texto
        ][:CHECKIN_LIMIT]
        self._registrar(
            ev.day_checkin(
                self._clock,
                self.device_id,
                date=self._hoje().isoformat(),
                intents=textos,
            )
        )

    # -------------------------------------------------------------- a semana
    #
    # O que a semana mostra é o que foi entregue, dia a dia — os mesmos objetos
    # que estão na estante, com a data em que chegaram lá. É o oposto de um
    # painel de métricas: não tem barra, não tem percentual, não compara um dia
    # com o outro e não diz nada sobre os dias em branco além de que estão em
    # branco.
    #
    # O único número é a soma de horas no rodapé, que é o mesmo tipo de conta
    # que o bilhete da parede já faz para um dia. Somar não é cobrar; comparar
    # é, e é por isso que os minutos não aparecem linha a linha.

    _MESES = (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    )
    _DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")

    def _inicio_da_semana(self) -> date:
        """Segunda-feira da semana que o painel está olhando."""
        hoje = self._hoje()
        segunda = hoje - timedelta(days=hoje.weekday())
        return segunda - timedelta(weeks=self._week_offset)

    def _semana(self) -> tuple[list[dict], int]:
        """Os sete dias e os minutos da semana, numa passada só pelo log.

        **Este método é a correção de um custo que doía de verdade.** A versão
        anterior tinha três propriedades independentes, e cada uma reprojetava
        o log inteiro várias vezes: `weekDays` chamava `completed_on` sete
        vezes (sete `completed_tasks`), `weekMinutes` chamava `minutes_on`
        outras sete (sete `sessions`), e `weekDelivered` chamava `weekDays`
        de novo por completo, só para contar.

        Como as três são propriedades notificadas por `weekChanged`, e
        `_recomputar` emite `weekChanged` a cada evento gravado, a conta toda
        rodava **a cada clique que escrevia no log** — com o painel da semana
        fechado, porque os bindings ficam vivos de qualquer jeito. Medido: 95 ms
        por clique com um ano de uso, 301 ms com três anos, justamente no gesto
        em que a estante deveria animar suave.

        Aqui `completed_tasks` e `sessions` rodam uma vez cada, e os sete dias
        saem de um agrupamento em memória. As três propriedades passaram a ler
        deste resultado.
        """
        fuso = self._fuso()
        hoje = self._hoje()
        inicio = self._inicio_da_semana()
        fim = inicio + timedelta(days=6)
        revisoes = proj.day_reviews(self._events)

        entregas: dict[date, list[str]] = {}
        for task in proj.completed_tasks(self._events):
            if task.completed_at is None:
                continue
            dia = task.completed_at.astimezone(fuso).date()
            if inicio <= dia <= fim:
                entregas.setdefault(dia, []).append(task.label)

        minutos = 0.0
        for sessao in proj.sessions(self._events):
            if sessao.ended_at is None:
                continue
            dia = sessao.ended_at.astimezone(fuso).date()
            if inicio <= dia <= fim:
                minutos += sessao.duration_minutes

        dias: list[dict] = []
        for passo in range(7):
            dia = inicio + timedelta(days=passo)
            revisao = revisoes.get(dia.isoformat())
            dias.append(
                {
                    "date": dia.isoformat(),
                    "weekday": self._DIAS[passo],
                    "day": dia.day,
                    "today": dia == hoje,
                    # Dia que ainda não chegou não é dia vazio: ele não tem
                    # nada a dizer, e escrever "em branco" nele soaria como
                    # cobrança antecipada.
                    "ahead": dia > hoje,
                    "delivered": entregas.get(dia, []),
                    "mood": revisao.mood if revisao else 0,
                    "note": (revisao.note or "") if revisao else "",
                }
            )
        return dias, int(round(minutos))

    @Property("QVariantList", notify=weekChanged)
    def weekDays(self) -> list[dict]:
        return self._semana()[0]

    @Property(str, notify=weekChanged)
    def weekTitle(self) -> str:
        if self._week_offset == 0:
            return "esta semana"
        if self._week_offset == 1:
            return "a semana passada"
        return f"{self._week_offset} semanas atrás"

    @Property(str, notify=weekChanged)
    def weekRange(self) -> str:
        """As datas da semana. Com o ano quando ele não é o de hoje.

        Sem o ano, "9 a 15 de novembro" deixa de identificar a semana assim que
        se anda algumas para trás — e navegar para trás é a razão de este painel
        ter setas. No ano corrente ele fica de fora, porque aí é ruído: ninguém
        precisa que o app diga em que ano está hoje.
        """
        inicio = self._inicio_da_semana()
        fim = inicio + timedelta(days=6)
        sufixo = "" if fim.year == self._hoje().year else f" de {fim.year}"
        if inicio.month == fim.month:
            return f"{inicio.day} a {fim.day} de {self._MESES[fim.month - 1]}{sufixo}"
        return (
            f"{inicio.day} de {self._MESES[inicio.month - 1]}"
            f" a {fim.day} de {self._MESES[fim.month - 1]}{sufixo}"
        )

    @Property(int, notify=weekChanged)
    def weekDelivered(self) -> int:
        return sum(len(dia["delivered"]) for dia in self._semana()[0])

    @Property(int, notify=weekChanged)
    def weekMinutes(self) -> int:
        return self._semana()[1]

    @Property(int, notify=weekChanged)
    def weekOffset(self) -> int:
        return self._week_offset

    # Quanto se pode voltar mesmo sem log nenhum atrás.
    #
    # Uma semana, e a assimetria com o futuro é de propósito: a semana passada
    # **aconteceu**, ainda que o app não estivesse lá para ver. Vazia, ela diz
    # uma coisa verdadeira — "nada aqui" —, enquanto a semana que vem não diz
    # nada, porque ainda não é. É a mesma razão de `weekDays` marcar `ahead` em
    # vez de tratar dia futuro como dia em branco.
    _RECUO_MINIMO = 1

    def _recuo_maximo(self) -> int:
        """Quantas semanas atrás a navegação ainda vai.

        O fim do passado é o primeiro evento do log: antes dele o cantinho não
        tem o que dizer, que é o argumento que já barra o futuro do outro lado
        da linha. Sem este limite a navegação ia para sempre — trezentos cliques
        levavam a 2020, sete dias vazios em cada tela e uma reprojeção do log
        inteiro em cada passo.

        O piso de uma semana é o que preserva a leitura honesta de quem começou
        ontem: a semana passada existe e está vazia, e ver isso é diferente de
        não poder olhar.
        """
        if not self._events:
            return self._RECUO_MINIMO
        primeiro = min(evento.occurred_at for evento in self._events)
        dia = primeiro.astimezone(self._fuso()).date()
        semana_do_primeiro = dia - timedelta(days=dia.weekday())
        hoje = self._hoje()
        semana_atual = hoje - timedelta(days=hoje.weekday())
        semanas = (semana_atual - semana_do_primeiro).days // 7
        return max(self._RECUO_MINIMO, semanas)

    @Property(bool, notify=weekChanged)
    def hasPreviousWeek(self) -> bool:
        """Se ainda há semana atrás desta. É o que apaga a seta no fim."""
        return self._week_offset < self._recuo_maximo()

    @Slot()
    def previousWeek(self) -> None:
        if self._week_offset >= self._recuo_maximo():
            return
        self._week_offset += 1
        self.weekChanged.emit()

    @Slot()
    def nextWeek(self) -> None:
        """Não passa desta semana: o cantinho não tem nada a dizer do futuro."""
        if self._week_offset > 0:
            self._week_offset -= 1
            self.weekChanged.emit()

    @Slot()
    def thisWeek(self) -> None:
        if self._week_offset != 0:
            self._week_offset = 0
            self.weekChanged.emit()

    # ----------------------------------------------------------------- tema

    def _noite_pelo_relogio(self) -> bool:
        return not schedule.is_daylight(self._agora_local())

    def _reavaliar_relogio(self) -> None:
        """O que muda sozinho com a passagem do tempo, sem evento nenhum.

        São três coisas, e todas ficavam paradas até alguém escrever no log: o
        tema, a marca do expediente e — a que doía — o dia. O app fica aberto a
        noite inteira, e à meia-noite o bilhete continuava mostrando as tarefas
        de ontem, a semana continuava na semana passada e a planta segurava um
        estágio que a janela de 14 dias já tinha desfeito.

        Emite só quando alguma delas de fato mudou. Um `stateChanged` por
        minuto reavaliaria todo binding da tela a troco de nada.
        """
        agora = self._noite_pelo_relogio()
        if agora != self._era_noite:
            self._era_noite = agora
            if self._theme_mode == "auto":
                self.themeChanged.emit()

        # A marca do relógio de parede anda junto: ela muda quatro vezes por
        # dia útil, então reavaliar de minuto em minuto é de sobra.
        marca = self._proxima_virada()
        if marca != self._marca:
            self._marca = marca
            self.routineChanged.emit()

        # A marca de vida e o toque do quarto andam neste mesmo tique, que é o
        # único laço de um minuto que o app tem.
        if self._timer.running:
            self._heartbeat.beat(self._clock.now())
            self._talvez_tocar()

        hoje = self._hoje()
        if hoje != self._dia:
            logger.info("o dia virou: %s", hoje.isoformat())
            self._dia = hoje
            # Reprojeta inteiro: o que mudou não foi o log, foi a data que
            # todas as projeções do dia recebem como argumento.
            self._recomputar()
            return

        # A planta não espera a meia-noite: a janela de 14 dias desliza a
        # qualquer hora, e o estágio cai no instante em que a sessão mais
        # antiga sai dela. É uma função pura sobre um log pequeno — barato o
        # bastante para conferir de minuto em minuto.
        estagio = proj.plant_stage(self._events, self._clock.now())
        if estagio != self._estagio:
            self._estagio = estagio
            self.stateChanged.emit()

    def _talvez_tocar(self) -> None:
        """O quarto lembrando que o relógio ficou correndo.

        Duas horas é mais do que qualquer sessão de foco conduzida de propósito;
        daí para cima o caso comum é timer esquecido. Insiste de meia em meia
        hora porque quem saiu da mesa às 19h50 não estava lá para ver o
        primeiro aviso — e é essa pessoa que o toque existe para alcançar.

        As frases são observações do quarto, não avisos de sistema: nenhuma diz
        quanto tempo passou e nenhuma sugere que se devia estar trabalhando.
        """
        minutos = self._timer.elapsed.total_seconds() / 60
        if minutos < self._proximo_toque:
            return
        frase = NUDGES[self._toques_dados % len(NUDGES)]
        self._toques_dados += 1
        self._proximo_toque += NUDGE_REPEAT_MINUTES
        logger.info("toque do quarto aos %d minutos", int(minutos))
        self.nudged.emit(frase)

    def _proxima_virada(self) -> int:
        virada = schedule.next_boundary(self._agora_local())
        return -1 if virada is None else schedule.minutes_of(virada)

    @Property(int, notify=routineChanged)
    def nextBoundaryMinutes(self) -> int:
        """Minutos desde a meia-noite da próxima virada do expediente.

        -1 quando não há nenhuma pela frente — fim de semana, ou depois do fim
        do turno. É o que o relógio de parede marca.
        """
        return self._marca

    @Property(bool, notify=routineChanged)
    def inShift(self) -> bool:
        return schedule.in_shift(self._agora_local())

    @Property(bool, notify=themeChanged)
    def isNight(self) -> bool:
        if self._theme_mode == "noite":
            return True
        if self._theme_mode == "tarde":
            return False
        return self._noite_pelo_relogio()

    @Property(str, notify=themeChanged)
    def themeName(self) -> str:
        return "noite" if self.isNight else "tarde"

    @Property(str, notify=themeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @Slot(str)
    def setThemeMode(self, mode: str) -> None:
        if mode not in ("auto", "tarde", "noite") or mode == self._theme_mode:
            return
        self._theme_mode = mode
        self.themeChanged.emit()

    @Slot()
    def cycleThemeMode(self) -> None:
        ordem = ("auto", "tarde", "noite")
        atual = ordem.index(self._theme_mode)
        self.setThemeMode(ordem[(atual + 1) % len(ordem)])

    # ------------------------------------------------------------------ som

    @Property(str, notify=soundChanged)
    def soundMode(self) -> str:
        return self._sound_mode

    @Property(bool, notify=soundChanged)
    def ambienceOn(self) -> bool:
        return self._sound_mode == "tudo"

    @Property(bool, notify=soundChanged)
    def touchesOn(self) -> bool:
        return self._sound_mode != "mudo"

    @Property(bool, notify=soundChanged)
    def muted(self) -> bool:
        return self._sound_mode == "mudo"

    @Slot(str)
    def setSoundMode(self, modo: str) -> None:
        if modo in SOUND_MODES and modo != self._sound_mode:
            if modo != "mudo":
                self._sound_before_mute = modo
            self._sound_mode = modo
            self.soundChanged.emit()

    @Slot()
    def cycleSoundMode(self) -> None:
        atual = SOUND_MODES.index(self._sound_mode)
        self.setSoundMode(SOUND_MODES[(atual + 1) % len(SOUND_MODES)])

    @Slot()
    def toggleMute(self) -> None:
        """Interruptor de duas posições, para a mini.

        Lá não cabe — nem faz sentido — o ciclo de três estados: a mini é o app
        reduzido ao relógio, e quem a está usando quer calar o som ou devolvê-lo
        como estava, não configurar o ambiente. O ajuste fino continua no menu
        do quarto, na janela grande.
        """
        self.setSoundMode("mudo" if not self.muted else self._sound_before_mute)

    # ------------------------------------------------------------ movimento

    @Property(bool, notify=motionChanged)
    def motionOn(self) -> bool:
        """Se o cenário se mexe sozinho.

        Cinco laços rodam para sempre no quarto: a luz do abajur respirando, as
        folhas balançando, a chuva, a poeira no feixe e o grão. São o ambiente
        — a razão de o app existir —, e ao mesmo tempo a única coisa aqui que
        gasta máquina sem ninguém ter pedido nada. O grão sozinho repinta a
        janela inteira a cada 900 ms, a tarde toda, mesmo com o app parado.

        Desligar é um ajuste do quarto, como a luz e o som, e vive só na
        sessão. O que continua é a reação ao mouse: botão que não responde ao
        toque não é quarto quieto, é app quebrado.
        """
        return self._motion

    @Slot(bool)
    def setMotion(self, ligado: bool) -> None:
        ligado = bool(ligado)
        if ligado != self._motion:
            self._motion = ligado
            self.motionChanged.emit()

    @Slot()
    def toggleMotion(self) -> None:
        self.setMotion(not self._motion)

    @Slot(str)
    def sfx(self, nome: str) -> None:
        """Pede uma reação curta. Muda só no modo `mudo`."""
        if self.touchesOn and nome:
            self.sfxRequested.emit(nome)

    # -------------------------------------------------------------- janelas

    # As duas janelas são a mesma coisa em dois tamanhos, e nunca ficam na tela
    # ao mesmo tempo. Mostrar uma esconde a outra.
    #
    # Ter as duas juntas era o pior dos dois mundos: dois relógios contando o
    # mesmo tempo, um por cima do outro, e a mini — que existe para ocupar um
    # canto enquanto você trabalha em outra coisa — competindo com a janela que
    # ela deveria substituir.
    #
    # As duas escondidas é um estado legítimo: é o app na bandeja.

    @Property(bool, notify=miniVisibleChanged)
    def miniVisible(self) -> bool:
        return self._mini_visible

    @Slot(bool)
    def setMiniVisible(self, visivel: bool) -> None:
        visivel = bool(visivel)
        if visivel != self._mini_visible:
            self._mini_visible = visivel
            self.miniVisibleChanged.emit()
        if visivel:
            self.setMainVisible(False)

    @Slot()
    def showMini(self) -> None:
        self.setMiniVisible(True)

    @Slot()
    def toggleMini(self) -> None:
        """Alterna entre as duas formas.

        Fechar a mini traz a principal de volta em vez de deixar a tela vazia:
        quem apertou "mini" estava com o app aberto e não pediu para escondê-lo.
        Para sumir com tudo existe o × da mini.
        """
        if self._mini_visible:
            self.showMain()
        else:
            self.showMini()

    @Property(bool, notify=mainVisibleChanged)
    def mainVisible(self) -> bool:
        return self._main_visible

    @Slot(bool)
    def setMainVisible(self, visivel: bool) -> None:
        visivel = bool(visivel)
        if visivel != self._main_visible:
            self._main_visible = visivel
            self.mainVisibleChanged.emit()
        if visivel:
            self.setMiniVisible(False)

    @Slot()
    def showMain(self) -> None:
        self.setMainVisible(True)

    @Slot()
    def hideAll(self) -> None:
        """Tudo para a bandeja."""
        self.setMainVisible(False)
        self.setMiniVisible(False)

    @Slot()
    def requestCapture(self) -> None:
        """Chamado pelo atalho global: abre o app já no campo de ideia."""
        self.setMainVisible(True)
        self.captureRequested.emit()

    @Slot()
    def requestQuit(self) -> None:
        """Encerrar de verdade. Quem confirma é a tela; aqui já é decisão."""
        self.quitRequested.emit()

    # ----------------------------------------------------------- a página
    #
    # Levar o quarto embora.
    #
    # Um log pessoal de anos sem exportação é um refém: o banco é SQLite e o
    # esquema é simples, mas "abra o sqlite3 e escreva um SELECT" não é uma
    # saída, é a ausência de uma.
    #
    # **A página é também a resposta ao horizonte longo.** Ver mais que uma
    # semana é gerar o diário daquele período e lê-lo como texto — não abrir um
    # painel de mês, que seria mais tela dentro do mesmo lugar e com a mesma
    # pressão de virar comparação. Daí os dois caminhos: a semana exporta o que
    # está na tela, o menu do quarto exporta tudo.
    #
    # O arquivo vai para uma pasta ao lado do banco, e não para a Área de
    # Trabalho ou os Documentos: descobrir onde essas pastas ficam é código de
    # plataforma (em português elas têm outro nome, e com OneDrive corporativo
    # estão redirecionadas), e o app abre a pasta em seguida, então onde ela
    # fica deixa de importar. Também é o que mantém de pé a regra de que o app
    # só escreve na própria pasta de dados.

    @Property(str, notify=stateChanged)
    def exportFolder(self) -> str:
        return str(self._store.db_path.parent / "paginas")

    @Slot(result=str)
    def exportEverything(self) -> str:
        """Escreve a página com tudo. Devolve o caminho, ou vazio se falhou."""
        return self._escrever_pagina(None, None)

    @Slot(result=str)
    def exportCurrentWeek(self) -> str:
        """Escreve a página da semana que o painel está mostrando."""
        inicio = self._inicio_da_semana()
        return self._escrever_pagina(inicio, inicio + timedelta(days=6))

    def _escrever_pagina(self, inicio: date | None, fim: date | None) -> str:
        texto = export.diary_markdown(
            self._events,
            self._fuso(),
            inicio=inicio,
            fim=fim,
            gerado_em=self._clock.now(),
        )
        destino = Path(self.exportFolder) / export.suggested_filename(inicio, fim)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            # Escrita atômica, pela mesma razão da marca de vida: uma queda no
            # meio deixaria meia página no lugar de uma página inteira, e a
            # anterior — que estava certa — já teria sido truncada.
            temporario = destino.with_name(destino.name + ".novo")
            temporario.write_text(texto, encoding="utf-8")
            os.replace(temporario, destino)
        except OSError:
            logger.warning("não deu para escrever a página", exc_info=True)
            self.exportFailed.emit()
            return ""

        logger.info("página escrita em %s", destino)
        self.exported.emit(str(destino))
        return str(destino)

    @Slot()
    def openExportFolder(self) -> None:
        """Abre a pasta das páginas no gerenciador de arquivos.

        `QDesktopServices` é a abstração do próprio Qt e funciona nos dois
        sistemas — não é código de plataforma e por isso não precisa morar em
        `services/`. É ela que torna aceitável guardar as páginas ao lado do
        banco: o caminho deixa de ser algo que alguém tem que decorar.
        """
        pasta = Path(self.exportFolder)
        try:
            pasta.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning("não deu para criar %s", pasta, exc_info=True)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))
