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
from cantinho.core.projections import ideas, open_tasks, shelf_objects
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


def visiveis(raiz=None):
    return [
        it
        for it in caminhar(raiz if raiz is not None else principal.contentItem())
        if it.isVisible() and it.width() > 0 and it.height() > 0
    ]


def centro(item) -> QPoint:
    ponto = item.mapToItem(None, QPointF(item.width() / 2, item.height() / 2))
    return QPoint(round(ponto.x()), round(ponto.y()))


def achar(texto, perto_de_y=None, max_y=None, raiz=None):
    achados = [it for it in visiveis(raiz) if it.property("text") == texto]
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


def achar_por_nome(nome):
    for item in caminhar(principal.contentItem()):
        if item.objectName() == nome:
            return item
    raise LookupError(f"não achei item chamado {nome!r}")


def na_barra(texto):
    """Desambigua o botão da barra de baixo.

    O bilhete da parede também tem um rótulo "hoje", e ele aparece antes na
    varredura. Procurar pelo texto sozinho pegaria o papel em vez do botão.
    """
    return achar(texto, perto_de_y=principal.height() - 60)


def na_gaveta(texto, **kwargs):
    """Procura só dentro do painel lateral.

    O bilhete da parede mostra os mesmos rótulos das tarefas do dia e vem antes
    na varredura da cena. Sem restringir a raiz, clicar em "a tarefa X" acerta
    o papel pendurado e a lista nunca recebe o clique.
    """
    return achar(texto, raiz=achar_por_nome("gaveta"), **kwargs)


@passo
def abrir_hoje():
    print("\n-- abre o painel 'hoje'")
    clicar(na_barra("hoje"))


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
    alvo = na_gaveta(TAREFAS[0])
    clicar(na_gaveta("começar", perto_de_y=centro(alvo).y(), max_y=560))
    checar(backend.timerRunning, "o timer está rodando")
    checar(backend.currentTaskLabel == TAREFAS[0], "ligada à tarefa certa")


@passo
def encerrar_sessao():
    print("-- encerra pela barra de baixo")
    clicar(na_barra("encerrar"))
    checar(not backend.timerRunning, "o timer parou")
    checar(len(backend.todaySessions) == 1, "a sessão apareceu no dia")


@passo
def concluir_tarefa():
    print("-- conclui a primeira tarefa")
    antes = len(backend.shelf)
    rotulo = na_gaveta(TAREFAS[0])
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
    arrastar(na_gaveta(antes[1]), na_gaveta(antes[0]))
    depois = [t["label"] for t in backend.backlog]
    checar(depois == [antes[1], antes[0]], f"a ordem virou {depois}")
    foto("03_apos_arrasto")


@passo
def aproveitar_ideia():
    print("-- transforma a ideia do mural em tarefa")
    clicar(na_barra("ideias"))
    # O botão só aparece com o mouse em cima do cartaz.
    cartaz = na_gaveta(IDEIA)
    QTest.mouseMove(principal, centro(cartaz))
    QTest.qWait(300)
    clicar(na_gaveta("virar tarefa"))
    checar(backend.ideas[0]["used"], "a ideia consta como aproveitada")
    checar(backend.ideas[0]["taskId"] != "", "aponta para a tarefa que nasceu")
    checar(
        [t["label"] for t in backend.backlog][-1] == IDEIA,
        "a tarefa entrou no fim do backlog",
    )
    foto("04_mural")
    clicar(na_barra("ideias"))


@passo
def alternar_som():
    print("-- desliga e liga o som pela barra")
    clicar(na_barra("som"))
    checar(not backend.soundOn, "o som foi desligado")
    clicar(na_barra("mudo"))
    checar(backend.soundOn, "o som voltou")


@passo
def redimensionar():
    """A regressão que motivou este passo.

    As camadas do quarto usam `PreserveAspectFit`, então o desenho é
    centralizado e sobra faixa vazia. Enquanto a janela ficou em 1100x700 a
    folga era zero e o erro não aparecia; ao maximizar, a chuva e a poeira, que
    se posicionam por conta própria, ficavam ancoradas no canto do Item e
    saíam de dentro da janela do quarto.
    """
    print("-- estica a janela e confere os efeitos dentro da cena")
    principal.setWidth(1400)
    principal.setHeight(760)
    # As camadas do cenário são rasterizadas de novo no tamanho novo, fora da
    # thread da UI. O app repinta em uns 300 ms, mas `grabWindow` logo depois de
    # um resize pega quadro velho e a captura sai com o quarto vazio.
    QTest.qWait(3500)

    quarto = achar_por_nome("chuva").parentItem()
    escala = min(quarto.width() / 1100, quarto.height() / 700)
    folga_x = (quarto.width() - 1100 * escala) / 2
    folga_y = (quarto.height() - 700 * escala) / 2

    for nome, (vx, vy) in (("chuva", (424, 94)), ("poeira", (400, 94))):
        item = achar_por_nome(nome)
        esperado_x = folga_x + vx * escala
        esperado_y = folga_y + vy * escala
        checar(
            abs(item.x() - esperado_x) < 1.5 and abs(item.y() - esperado_y) < 1.5,
            f"{nome} acompanhou a cena ({item.x():.0f},{item.y():.0f})"
            f" ~ ({esperado_x:.0f},{esperado_y:.0f})",
        )
    foto("06_esticada")
    principal.setWidth(1100)
    principal.setHeight(700)
    QTest.qWait(400)


@passo
def fechar_o_dia():
    print("-- fecha o dia com humor e energia")
    clicar(na_barra("fechar o dia"))
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
    clicar(na_barra("mini"))
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
        "task.created": 4,
        "session.started": 1,
        "session.ended": 1,
        "task.completed": 1,
        "idea.captured": 1,
        "idea.promoted": 1,
        "backlog.reordered": 1,
        "day.review": 1,
    }
    checar(contagem == esperado, f"o log é exatamente {esperado}")
    checar(
        [t.label for t in open_tasks(eventos)] == [TAREFAS[2], TAREFAS[1], IDEIA],
        "o backlog reconstruído mantém a ordem arrastada",
    )
    reidratadas = ideas(eventos)
    checar(
        len(reidratadas) == 1 and reidratadas[0].used,
        "a ideia reconstruída continua no mural, aproveitada",
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
