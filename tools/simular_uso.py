"""Percorre o app inteiro com mouse e teclado sintéticos.

A suíte do pytest cobre o `core` e o `services`. Ela não cobre o QML, que é
onde mora a parte mais frágil da interface — foi um arrasto que parecia
funcionar, e não funcionava, que motivou este script.

Ele não chama slot do backend: acha o item no QML, calcula onde ele está na
tela e clica ali. No fim fecha tudo, reabre o banco do zero e confere que o log
tem exatamente os eventos que aqueles cliques deveriam ter gerado.

Precisa de tela de verdade — as janelas aparecem enquanto roda. Com
`QT_QPA_PLATFORM=offscreen` o Qt fica sem nenhuma fonte e o script continua
válido, mas as capturas saem com tofu no lugar do texto.

    python tools/simular_uso.py                 # só verifica
    python tools/simular_uso.py build/simulacao # e guarda as capturas
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QPointF,
    Qt,
    QTimer,
    QUrl,
    qInstallMessageHandler,
)
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cantinho.backend import Backend
from cantinho.core.clock import SystemClock
from cantinho.core.projections import open_tasks, shelf_objects
from cantinho.core.store import EventStore
from cantinho.services import scene

TAREFAS = ["revisar o capítulo 3", "responder o orientador", "comprar café"]
IDEIA = "trocar a fonte do editor"

SAIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if SAIDA:
    SAIDA.mkdir(parents=True, exist_ok=True)

# console.log do QML e aviso do Qt não chegam ao stderr do Python sozinhos.
# Sem este handler, um erro de binding passa despercebido.
mensagens: list[str] = []
qInstallMessageHandler(lambda tipo, contexto, texto: mensagens.append(texto))

app = QApplication([])
PASTA = Path(tempfile.mkdtemp())
BANCO = PASTA / "simulacao.db"
store = EventStore(BANCO, device_id="simulacao")
backend = Backend(store, SystemClock())

engine = QQmlApplicationEngine()
engine.addImageProvider("cena", scene.SceneImageProvider())
ui = Path(__file__).resolve().parents[1] / "cantinho" / "ui"
engine.addImportPath(str(ui))
engine.rootContext().setContextProperty("backend", backend)
for arquivo in ("Main.qml", "Mini.qml"):
    engine.load(QUrl.fromLocalFile(str(ui / arquivo)))

if len(engine.rootObjects()) != 2:
    print("as janelas não carregaram")
    raise SystemExit(2)

principal, mini = engine.rootObjects()
principal.requestActivate()
falhas: list[str] = []


# ------------------------------------------------------------------ utilidades


def caminhar(item):
    yield item
    for filho in item.childItems():
        yield from caminhar(filho)


def visiveis():
    return [
        it
        for it in caminhar(principal.contentItem())
        if it.isVisible() and it.width() > 0 and it.height() > 0
    ]


def centro(item) -> QPoint:
    ponto = item.mapToItem(None, QPointF(item.width() / 2, item.height() / 2))
    return QPoint(round(ponto.x()), round(ponto.y()))


def achar(texto, perto_de_y=None, max_y=None):
    achados = [it for it in visiveis() if it.property("text") == texto]
    if max_y is not None:
        achados = [it for it in achados if centro(it).y() < max_y]
    if not achados:
        raise LookupError(f"não achei item com texto {texto!r}")
    if perto_de_y is not None:
        achados.sort(key=lambda it: abs(centro(it).y() - perto_de_y))
    return achados[0]


def achar_campo(placeholder):
    for item in visiveis():
        if item.property("placeholder") == placeholder:
            return item
    raise LookupError(f"não achei campo {placeholder!r}")


def clicar(item, dx=0, dy=0):
    QTest.mouseClick(principal, Qt.LeftButton, Qt.NoModifier, centro(item) + QPoint(dx, dy))
    # Painel entra com animação. Procurar item antes dela terminar não acha nada.
    QTest.qWait(350)


def digitar(texto):
    # QTest.keyClicks só aceita QWidget. Numa QQuickWindow o caminho é mandar o
    # QKeyEvent com o texto e deixar a janela rotear para quem tem foco.
    for caractere in texto:
        for tipo in (QEvent.KeyPress, QEvent.KeyRelease):
            app.sendEvent(
                principal, QKeyEvent(tipo, Qt.Key_unknown, Qt.NoModifier, caractere)
            )
        QTest.qWait(6)


def arrastar(de_item, para_item):
    """Gesto de arrasto de verdade: pressiona, move em passos, solta.

    `QTest.mouseMove` manda o evento sem estado de botão pressionado, e aí o
    MouseArea nunca entende que virou arrasto. Por isso o move é montado à mão
    com `buttons=LeftButton`.
    """
    origem, destino = centro(de_item), centro(para_item)
    QTest.mousePress(principal, Qt.LeftButton, Qt.NoModifier, origem)
    QTest.qWait(80)
    etapas = 14
    for i in range(1, etapas + 1):
        y = origem.y() + (destino.y() - origem.y()) * i // etapas
        app.sendEvent(
            principal,
            QMouseEvent(
                QEvent.MouseMove,
                QPointF(origem.x(), y),
                Qt.NoButton,
                Qt.LeftButton,
                Qt.NoModifier,
            ),
        )
        QTest.qWait(25)
    QTest.mouseRelease(
        principal, Qt.LeftButton, Qt.NoModifier, QPoint(origem.x(), destino.y())
    )
    QTest.qWait(500)


def foto(nome):
    if SAIDA:
        principal.grabWindow().save(str(SAIDA / f"{nome}.png"))


def checar(condicao, descricao):
    if not condicao:
        falhas.append(descricao)
    print(f"  {'ok   ' if condicao else 'FALHA'} {descricao}")


passos = []


def passo(fn):
    passos.append(fn)
    return fn


# ---------------------------------------------------------------------- roteiro


@passo
def abrir_hoje():
    print("\n-- abre o painel 'hoje'")
    clicar(achar("hoje"))


@passo
def escrever_tarefas():
    print("-- escreve três tarefas")
    campo = achar_campo("o que você quer fazer?")
    for rotulo in TAREFAS:
        clicar(campo)
        digitar(rotulo)
        QTest.keyClick(principal, Qt.Key_Return)
    checar(len(backend.backlog) == 3, "três tarefas no backlog")
    checar(
        [t["label"] for t in backend.backlog] == TAREFAS,
        "ficaram na ordem em que foram escritas",
    )
    foto("01_backlog")


@passo
def comecar_sessao():
    print("-- começa uma sessão pela primeira tarefa")
    alvo = achar(TAREFAS[0])
    clicar(achar("começar", perto_de_y=centro(alvo).y(), max_y=560))
    checar(backend.timerRunning, "o timer está rodando")
    checar(backend.currentTaskLabel == TAREFAS[0], "ligada à tarefa certa")


@passo
def encerrar_sessao():
    print("-- encerra pela barra de baixo")
    clicar(achar("encerrar"))
    checar(not backend.timerRunning, "o timer parou")
    checar(len(backend.todaySessions) == 1, "a sessão apareceu no dia")


@passo
def concluir_tarefa():
    print("-- conclui a primeira tarefa")
    antes = len(backend.shelf)
    rotulo = achar(TAREFAS[0])
    ponto = rotulo.mapToItem(None, QPointF(0, rotulo.height() / 2))
    QTest.mouseClick(
        principal,
        Qt.LeftButton,
        Qt.NoModifier,
        QPoint(round(ponto.x()) - 20, round(ponto.y())),
    )
    QTest.qWait(300)
    checar(len(backend.shelf) == antes + 1, "entrou um objeto na estante")
    checar(len(backend.backlog) == 2, "saiu do backlog")
    checar(TAREFAS[0] in backend.todayCompleted, "consta como entrega de hoje")
    foto("02_apos_concluir")


@passo
def capturar_ideia():
    print("-- Ctrl+Shift+C e escreve uma ideia")
    QTest.keyClick(principal, Qt.Key_C, Qt.ControlModifier | Qt.ShiftModifier)
    QTest.qWait(500)
    clicar(achar_campo("escreva e aperte Enter"))
    digitar(IDEIA)
    QTest.keyClick(principal, Qt.Key_Return)
    QTest.qWait(400)
    checar(len(backend.ideas) == 1, "a ideia foi guardada")
    checar(backend.ideas[0]["text"] == IDEIA, "guardou o texto certo")


@passo
def arrastar_backlog():
    print("-- arrasta a segunda tarefa para cima da primeira")
    antes = [t["label"] for t in backend.backlog]
    arrastar(achar(antes[1]), achar(antes[0]))
    depois = [t["label"] for t in backend.backlog]
    checar(depois == [antes[1], antes[0]], f"a ordem virou {depois}")
    foto("03_apos_arrasto")


@passo
def fechar_o_dia():
    print("-- fecha o dia com humor e energia")
    clicar(achar("fechar o dia"))
    escalas = [it for it in visiveis() if it.property("rotulo") in ("humor", "energia")]
    checar(len(escalas) == 2, "as duas escalas apareceram")
    foto("04_retrospectiva")
    clicar(achar("guardar o dia"))
    checar(backend.todayReview is not None, "a retrospectiva foi guardada")


@passo
def trocar_tema():
    print("-- troca o tema")
    antes = backend.themeName
    backend.setThemeMode("noite" if antes == "tarde" else "tarde")
    # O crossfade de cenário leva três segundos; espera ele terminar para a
    # captura não sair no meio da transição.
    QTest.qWait(3200)
    checar(backend.themeName != antes, "o tema mudou")
    foto("05_tema_trocado")


@passo
def mini_janela():
    print("-- abre a mini janela")
    clicar(achar("mini"))
    checar(backend.miniVisible, "a mini está visível")
    QTest.qWait(400)
    if SAIDA:
        mini.grabWindow().save(str(SAIDA / "06_mini.png"))


@passo
def conferir_o_log():
    print("\n-- reabre o banco do zero e confere o log")
    store.close()
    relido = EventStore(BANCO, device_id="simulacao")
    eventos = relido.read_all()

    contagem: dict[str, int] = {}
    for evento in eventos:
        contagem[evento.kind] = contagem.get(evento.kind, 0) + 1

    esperado = {
        "task.created": 3,
        "session.started": 1,
        "session.ended": 1,
        "task.completed": 1,
        "idea.captured": 1,
        "backlog.reordered": 1,
        "day.review": 1,
    }
    checar(contagem == esperado, f"o log é exatamente {esperado}")
    checar(
        [t.label for t in open_tasks(eventos)] == [TAREFAS[2], TAREFAS[1]],
        "o backlog reconstruído mantém a ordem arrastada",
    )
    checar(len(shelf_objects(eventos)) == 1, "a estante reconstruída tem o objeto")
    relido.close()


@passo
def conferir_avisos():
    print("-- procura erro de binding no QML")
    ruins = [m for m in mensagens if "TypeError" in m or "is not defined" in m]
    for aviso in ruins[:10]:
        print("     !", aviso)
    checar(not ruins, "nenhum erro de binding no QML")


# ------------------------------------------------------------------- execução

indice = 0


def rodar():
    global indice
    if indice < len(passos):
        atual = passos[indice]
        indice += 1
        try:
            atual()
        except Exception as erro:
            falhas.append(f"{atual.__name__}: {erro}")
            print(f"  FALHA {atual.__name__}: {erro}")
        QTimer.singleShot(600, rodar)
        return

    print("\n" + "=" * 60)
    if falhas:
        print(f"{len(falhas)} FALHA(S):")
        for falha in falhas:
            print("  -", falha)
    else:
        print("todos os passos passaram")
    print("=" * 60)
    shutil.rmtree(PASTA, ignore_errors=True)
    app.exit(1 if falhas else 0)


QTimer.singleShot(1500, rodar)
raise SystemExit(app.exec())
