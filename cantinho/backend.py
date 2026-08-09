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
from datetime import date, datetime, timedelta

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from cantinho.core import events as ev
from cantinho.core import projections as proj
from cantinho.core.clock import Clock
from cantinho.core.store import EventStore
from cantinho.services.timer import SessionTimer

logger = logging.getLogger(__name__)

__all__ = ["Backend"]

# Depois desta hora o tema vira noite; antes das seis da manhã ainda é noite.
NIGHT_FROM_HOUR = 18
NIGHT_UNTIL_HOUR = 6

# Quantas linhas cabem no bilhete da parede. É a folha que limita, não a
# projeção: uma lista que rola na parede deixaria de ser um bilhete.
BOARD_LIMIT = 6

# Modos de som, na ordem em que o botão gira.
#
# O do meio existe porque as duas pontas não davam conta: quem está numa
# chamada não quer chuva tocando, mas continua querendo o retorno do clique.
# "Sussurro" é o quarto calado com as mãos ainda fazendo barulho.
SOUND_MODES: tuple[str, ...] = ("tudo", "sussurro", "mudo")


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
    # Reação curta de interface (passar o mouse, clicar, concluir). Quem toca é
    # `services/audio.py`; o backend só avisa, para o QML não precisar conhecer
    # o serviço de áudio.
    sfxRequested = Signal(str)
    quitRequested = Signal()

    def __init__(
        self,
        store: EventStore,
        clock: Clock,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._clock = clock
        self._events: list[ev.Event] = store.read_all()

        self._timer = SessionTimer(clock, self)
        self._timer.tick.connect(self.timerChanged)

        self._theme_mode = "auto"
        self._mini_visible = False
        self._main_visible = True
        # Só nesta sessão. Preferência de som não vai a disco: `events` é a
        # única tabela persistida, e "liguei o som" não é fato do histórico.
        self._sound_mode = "tudo"

        # Reavalia o tema de tempos em tempos. Um minuto é folgado de sobra
        # para uma transição que leva três segundos.
        self._relogio_tema = QTimer(self)
        self._relogio_tema.setInterval(60_000)
        self._relogio_tema.timeout.connect(self._reavaliar_tema)
        self._relogio_tema.start()
        self._era_noite = self._noite_pelo_relogio()

        self._recomputar()

    # ------------------------------------------------------------------ log

    def _registrar(self, evento: ev.Event) -> None:
        """Grava e recalcula. Único caminho de escrita do app."""
        if self._store.append(evento):
            self._events.append(evento)
            self._recomputar()
        else:
            logger.warning("evento duplicado ignorado: %s", evento.uuid)

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

    @property
    def device_id(self) -> str:
        return self._store.device_id

    def _hoje(self) -> date:
        return datetime.now().astimezone().date()

    def _fuso(self):  # type: ignore[no-untyped-def]
        return datetime.now().astimezone().tzinfo

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

    @Property(bool, notify=stateChanged)
    def backlogEmpty(self) -> bool:
        return not self._backlog

    @Slot(str)
    @Slot(str, str)
    def addTask(self, label: str, project: str = "") -> None:
        label = label.strip()
        if not label:
            return
        self._registrar(
            ev.task_created(
                self._clock,
                self.device_id,
                label=label,
                project=project.strip() or None,
            )
        )

    @Slot(str)
    def completeTask(self, task_id: str) -> None:
        if not task_id:
            return
        self._registrar(ev.task_completed(self._clock, self.device_id, id=task_id))

    @Slot(str)
    def archiveTask(self, task_id: str) -> None:
        """Some da lista sem virar entrega. Não apaga nada: é um evento novo."""
        if not task_id:
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

    @Property(str, notify=timerChanged)
    def currentTaskLabel(self) -> str:
        task_id = self._timer.task_id
        if not task_id:
            return ""
        for task in self._backlog:
            if task.id == task_id:
                return task.label
        for task in self._concluidas:
            if task.id == task_id:
                return task.label
        return ""

    @Slot()
    @Slot(str)
    def startSession(self, task_id: str = "") -> None:
        if self._timer.running:
            return
        evento = ev.session_started(
            self._clock, self.device_id, task_id=task_id.strip() or None
        )
        self._registrar(evento)
        self._timer.start(
            evento.payload["id"], evento.payload.get("task_id"), evento.occurred_at
        )
        self.timerChanged.emit()

    @Slot()
    @Slot(bool)
    @Slot(bool, str)
    def endSession(self, interrupted: bool = False, note: str = "") -> None:
        session_id = self._timer.session_id
        if session_id is None:
            return
        self._registrar(
            ev.session_ended(
                self._clock,
                self.device_id,
                id=session_id,
                interrupted=bool(interrupted),
                note=note.strip() or None,
            )
        )
        self._timer.stop()
        self.timerChanged.emit()

    @Slot()
    def endSessionAndComplete(self) -> None:
        """Encerra a sessão e conclui a tarefa dela, num gesto só.

        Sem isto, terminar de trabalhar em algo eram dois movimentos em lugares
        diferentes: encerrar na barra e depois abrir a lista para marcar o
        círculo. O objeto só ia para a estante no segundo, e é o objeto que dá
        o retorno — então a metade que importa dependia de lembrar de fazê-la.

        Dois eventos, não um: `session.ended` e `task.completed` são fatos
        distintos e continuam separados no log. O que mudou é o gesto.
        """
        task_id = self._timer.task_id
        self.endSession(False, "")
        if task_id:
            self.completeTask(task_id)

    # -------------------------------------------------------------- estante

    @Property("QVariantList", notify=stateChanged)
    def shelf(self) -> list[str]:
        return [objeto.object_type for objeto in self._estante]

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

    @Slot(str)
    def captureIdea(self, text: str) -> None:
        text = text.strip()
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
        """
        ideia = next((item for item in self._ideias if item.id == idea_id), None)
        if ideia is None or ideia.used:
            return
        tarefa = ev.task_created(self._clock, self.device_id, label=ideia.text)
        self._registrar(tarefa)
        self._registrar(
            ev.idea_promoted(
                self._clock,
                self.device_id,
                id=ideia.id,
                task_id=tarefa.payload["id"],
            )
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
                note=note.strip() or None,
            )
        )

    @Slot("QVariantList")
    def saveCheckin(self, intents: list) -> None:
        textos = [str(item).strip() for item in intents if str(item).strip()]
        self._registrar(
            ev.day_checkin(
                self._clock,
                self.device_id,
                date=self._hoje().isoformat(),
                intents=textos,
            )
        )

    # ----------------------------------------------------------------- tema

    def _noite_pelo_relogio(self) -> bool:
        hora = datetime.now().astimezone().hour
        return hora >= NIGHT_FROM_HOUR or hora < NIGHT_UNTIL_HOUR

    def _reavaliar_tema(self) -> None:
        agora = self._noite_pelo_relogio()
        if agora != self._era_noite:
            self._era_noite = agora
            if self._theme_mode == "auto":
                self.themeChanged.emit()

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

    @Slot(str)
    def setSoundMode(self, modo: str) -> None:
        if modo in SOUND_MODES and modo != self._sound_mode:
            self._sound_mode = modo
            self.soundChanged.emit()

    @Slot()
    def cycleSoundMode(self) -> None:
        atual = SOUND_MODES.index(self._sound_mode)
        self.setSoundMode(SOUND_MODES[(atual + 1) % len(SOUND_MODES)])

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
