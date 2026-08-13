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

import os
import shutil
import sys
import tempfile
from pathlib import Path

# Render loop no thread principal, e não o `threaded` que o Qt usa por padrão
# no Windows.
#
# O loop threaded avança as animações junto com a apresentação de quadros. Com
# a tela apagada ou a sessão bloqueada, o Windows para de apresentar, o thread
# de render fica parado e **toda animação congela** — inclusive os `Behavior`
# que abrem a gaveta e os painéis.
#
# O efeito é cruel de diagnosticar: os cliques funcionam, as propriedades
# mudam, `aba` vira "backlog" — e a gaveta continua com opacidade zero, então
# o roteiro não acha nada lá dentro e falha em cascata como se a interface
# estivesse quebrada. Foi exatamente o que aconteceu quando esta suíte passou
# a rodar sem ninguém na frente do monitor.
#
# `basic` desenha no thread principal e avança as animações pelo relógio, sem
# depender do compositor. Vale para a ferramenta, não para o app: lá o loop
# threaded é o que dá a suavidade.
os.environ.setdefault("QSG_RENDER_LOOP", "basic")

# `python tools/simular_uso.py` põe `tools/` no sys.path, não a raiz do
# repositório — o Python usa o diretório do script, não o diretório atual. Sem
# esta linha, `import cantinho` falha mesmo rodando da raiz, que é exatamente o
# que a documentação manda fazer. O projeto não tem `pyproject.toml` de
# propósito; esta é a alternativa de uma linha.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Mesma razão do app: com o `base` do conda ativo, o ambiente traz
# `QT_XCB_GL_INTEGRATION=none` e o Qt Quick não sobe. Aqui a falha seria lida
# como regressão da interface, que é o que esta ferramenta existe para achar.
from cantinho.services.graphics import ensure_gl_integration  # noqa: E402

ensure_gl_integration()

from PySide6.QtCore import (  # noqa: E402
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
CORRIGIDA = "responder o orientador amanhã"
EXTRA = "resolver o e-mail do financeiro"

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


def comecar_pelo_hoje(rotulo):
    """Clica em "começar" na linha da tarefa, dentro da gaveta do "hoje".

    Começar por ali manda a janela grande embora e deixa a mini — o gesto de
    escolher na lista é o último antes de trabalhar, e o quarto inteiro na
    frente depois disso teria que ser fechado à mão toda vez.

    Como o roteiro continua clicando na janela grande, este helper confere a
    troca e traz a principal de volta.
    """
    linha = na_gaveta(rotulo)
    clicar(na_gaveta("começar", perto_de_y=centro(linha).y(), max_y=560))
    checar(backend.miniVisible, "começar pelo hoje passou a bola para a mini")
    checar(not backend.mainVisible, "e a janela grande saiu da frente")
    backend.showMain()
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


def achar_escala(rotulo):
    """Uma EscalaPontos pelo rótulo. Os pontos não têm texto para procurar."""
    for item in visiveis():
        if item.property("rotulo") == rotulo:
            return item
    raise LookupError(f"não achei a escala {rotulo!r}")


def no_seletor(texto, **kwargs):
    """Procura só dentro da lista de "o que vem agora"."""
    return achar(texto, raiz=achar_por_nome("seletor"), **kwargs)


def open_tasks_do_log():
    """Os eventos que já estão em memória no backend."""
    return backend._events


def no_extra(texto, **kwargs):
    """Procura só dentro do painel que pergunta o que mais se fechou junto.

    Mesma razão do `na_gaveta`: o bilhete da parede mostra os mesmos rótulos e
    vem antes na varredura. Aqui o erro é pior — o clique cai no véu atrás do
    painel, que fecha a pergunta, e o passo seguinte não acha mais nada.
    """
    return achar(texto, raiz=achar_por_nome("extra"), **kwargs)


def na_gaveta(texto, **kwargs):
    """Procura só dentro do painel lateral.

    O bilhete da parede mostra os mesmos rótulos das tarefas do dia e vem antes
    na varredura da cena. Sem restringir a raiz, clicar em "a tarefa X" acerta
    o papel pendurado e a lista nunca recebe o clique.
    """
    return achar(texto, raiz=achar_por_nome("gaveta"), **kwargs)


def no_passeio(texto, **kwargs):
    """Procura só dentro do balão do passeio."""
    return achar(texto, raiz=achar_por_nome("passeio"), **kwargs)


@passo
def fazer_o_passeio():
    """A primeira abertura explica o quarto, e é a primeira coisa na tela.

    Ele aparece porque o log está vazio — é esse o sinal de primeira abertura,
    e não uma flag em disco. Como o banco desta simulação nasce vazio, o
    passeio é literalmente a primeira coisa que o roteiro encontra, do mesmo
    jeito que será para quem instalar.
    """
    print("\n-- percorre o passeio da primeira abertura")
    checar(backend.showTour, "o passeio abriu sozinho no log vazio")
    checar(achar_por_nome("passeio").isVisible(), "e está na tela")

    antes = len(open_tasks_do_log())
    voltas = 0
    while not backend.showTour is False and voltas < 12:
        try:
            clicar(no_passeio("próximo"))
        except LookupError:
            break
        voltas += 1
    checar(voltas > 0, f"passou por {voltas} balões")

    clicar(no_passeio("entendi"))
    checar(not backend.showTour, "e o último botão fechou o passeio")
    checar(
        len(open_tasks_do_log()) == antes,
        "o passeio não escreveu nada no log",
    )


@passo
def rever_o_passeio():
    """Ele some assim que a primeira coisa é escrita, mas não some para sempre."""
    print("-- traz o passeio de volta pelo menu do quarto")
    clicar(na_barra("o quarto"))
    clicar(achar("ver de novo"))
    checar(backend.showTour, "o menu trouxe o passeio de volta")

    clicar(no_passeio("pular"))
    checar(not backend.showTour, "e 'pular' fecha de qualquer passo")


@passo
def abrir_hoje():
    print("\n-- abre o painel 'hoje'")
    clicar(na_barra("hoje"))
    checar(principal.property("aba") == "backlog", "a gaveta do hoje abriu")


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
    comecar_pelo_hoje(TAREFAS[0])
    checar(backend.timerRunning, "o timer está rodando")
    checar(backend.currentTaskLabel == TAREFAS[0], "ligada à tarefa certa")


@passo
def encerrar_sessao():
    print("-- encerra pela barra de baixo")
    clicar(na_barra("parar"))
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
    print("-- Ctrl+Shift+I e escreve uma ideia")
    QTest.keyClick(principal, Qt.Key_I, Qt.ControlModifier | Qt.ShiftModifier)
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
def terminar_pela_barra():
    """O gesto que faltava: encerrar a sessão já concluindo a tarefa.

    Antes, "encerrar" parava o relógio e deixava a tarefa aberta, então o
    objeto só ia para a estante se o usuário lembrasse de voltar à lista e
    marcar o círculo.
    """
    print("-- começa e termina uma tarefa pela barra")
    alvo = backend.backlog[-1]["label"]
    antes = len(backend.shelf)
    clicar(na_barra("hoje"))
    comecar_pelo_hoje(alvo)
    checar(backend.timerRunning, "a sessão começou")

    clicar(na_barra("entreguei"))
    checar(not backend.timerRunning, "a sessão foi encerrada")
    checar(len(backend.shelf) == antes + 1, "e a tarefa foi para a estante")
    checar(
        alvo not in [t["label"] for t in backend.backlog],
        "saiu do backlog no mesmo gesto",
    )
    clicar(na_barra("hoje"))


@passo
def escolher_o_que_vem_agora():
    """O botão grande da barra tem que pegar uma tarefa, não o vazio.

    Antes ele abria sempre uma sessão livre: o tempo era gravado sem dono, o
    "entreguei" nem aparecia, e prender o timer a uma tarefa só era possível
    mirando a palavra "começar" dentro da linha certa do painel "hoje".
    """
    print("-- escolhe a tarefa pelo seletor e começa pelo botão da barra")
    alvo = backend.backlog[1]["label"]
    checar(
        backend.focusedTaskLabel == backend.backlog[0]["label"],
        "sem escolher nada, o foco é o topo do hoje",
    )

    clicar(achar("▾", perto_de_y=principal.height() - 40))
    clicar(no_seletor(alvo))
    checar(backend.focusedTaskLabel == alvo, f"o foco passou para {alvo!r}")

    clicar(na_barra("começar"))
    checar(backend.timerRunning, "a sessão começou pelo botão da barra")
    checar(backend.currentTaskLabel == alvo, "e ficou presa à tarefa escolhida")
    clicar(na_barra("parar"))
    checar(not backend.timerRunning, "e para sem concluir a tarefa")
    checar(
        alvo in [t["label"] for t in backend.backlog],
        "a tarefa continua na lista",
    )


@passo
def renomear_tarefa():
    """Corrigir o texto sem arquivar e reescrever."""
    print("-- corrige o texto de uma tarefa")
    clicar(na_barra("hoje"))
    linha = na_gaveta(TAREFAS[1])
    clicar(na_gaveta("editar", perto_de_y=centro(linha).y(), max_y=560))
    QTest.qWait(200)
    digitar(CORRIGIDA)
    QTest.keyClick(principal, Qt.Key_Return)
    QTest.qWait(400)
    rotulos = [t["label"] for t in backend.backlog]
    checar(CORRIGIDA in rotulos, f"o rótulo virou {CORRIGIDA!r}")
    checar(TAREFAS[1] not in rotulos, "e o texto antigo saiu da lista")
    clicar(na_barra("hoje"))


@passo
def som_pelo_menu():
    print("-- gira os três estados de som pelo menu do quarto")
    clicar(na_barra("o quarto"))
    # O app abre em "sussurro": o quarto calado, a interface respondendo.
    for rotulo, esperado in (
        ("só os toques", "mudo"),
        ("nenhum", "tudo"),
        ("ambiente e toques", "sussurro"),
    ):
        clicar(achar(rotulo))
        checar(backend.soundMode == esperado, f"passou para {esperado}")
    foto("07_menu")
    clicar(na_barra("o quarto"))


@passo
def movimento_pelo_menu():
    """O quarto pode ficar quieto.

    Cinco coisas se mexem sozinhas para sempre — luz, folhas, chuva, poeira e o
    grão, que repinta a janela a cada 900 ms a tarde inteira. O que se confere
    aqui é que o ajuste chega de fato ao cenário, e não só ao backend: a chuva
    sai da tela junto.
    """
    print("-- deixa o quarto quieto pelo menu")
    antes = backend.themeMode
    backend.setThemeMode("noite")
    QTest.qWait(400)
    chuva = achar_por_nome("chuva")
    checar(chuva.isVisible(), "com o quarto respirando, chove na janela")

    clicar(na_barra("o quarto"))
    clicar(achar("o quarto respira"))
    checar(not backend.motionOn, "o quarto ficou quieto")
    QTest.qWait(300)
    checar(not chuva.isVisible(), "e a chuva parou em vez de congelar")

    clicar(achar("o quarto quieto"))
    checar(backend.motionOn, "e volta a respirar")
    QTest.qWait(300)
    checar(chuva.isVisible(), "com a chuva de volta")
    clicar(na_barra("o quarto"))
    backend.setThemeMode(antes)
    QTest.qWait(400)


@passo
def botoes_da_barra_entram():
    """Motion gap: os botões da sessão apareciam de estalo.

    `visible:` no controle mais usado do app — a cada sessão que começa, dois
    botões surgiam do nada e empurravam os vizinhos. A fileira do backlog já
    fazia por opacidade; a barra não fazia.
    """
    print("-- os botões da sessão entram e saem por largura")
    alvo = backend.backlog[0]["label"]
    clicar(na_barra("hoje"))
    comecar_pelo_hoje(alvo)
    clicar(na_barra("hoje"))

    entreguei = na_barra("entreguei")
    checar(entreguei.width() > 1, "com sessão correndo, 'entreguei' tem largura")

    backend.endSession(False, "")
    QTest.qWait(60)
    parcial = entreguei.width()
    QTest.qWait(400)
    checar(
        0 < parcial < entreguei.parentItem().width(),
        f"ao parar, ele encolhe em vez de sumir ({parcial:.0f} px no meio)",
    )
    checar(entreguei.width() < 1, "e chega a zero no fim")


@passo
def humor_pelo_menu():
    """Humor e energia sem passar pelo painel do dia."""
    print("-- marca humor e energia pelo menu")
    clicar(na_barra("o quarto"))
    escala = achar_escala("humor")
    # Os pontos ficam depois do rótulo de 60px, com 14 de lado e 10 de espaço.
    ponto = escala.mapToItem(None, QPointF(60 + 4 * 24 + 7, escala.height() / 2))
    QTest.mouseClick(
        principal, Qt.LeftButton, Qt.NoModifier,
        QPoint(round(ponto.x()), round(ponto.y())),
    )
    QTest.qWait(350)
    checar(backend.todayReview is not None, "a revisão do dia foi criada")
    checar(
        backend.todayReview and backend.todayReview["mood"] == 5,
        "o humor foi para o quinto ponto",
    )
    clicar(na_barra("o quarto"))


@passo
def marca_do_expediente():
    """O traço do fim do trecho no relógio de parede.

    A marca depende do calendário de verdade — só aparece em dia útil dentro do
    turno — e a suíte roda a qualquer hora, inclusive no sábado. Por isso o
    valor é forçado aqui: o que se confere é o desenho, não a regra, que tem
    teste próprio em `tests/test_schedule.py`.
    """
    print("-- marca do expediente no relógio de parede")
    relogio = achar_por_nome("relogioParede")
    marca = achar_por_nome("marcaExpediente")

    relogio.setProperty("marca", -1)
    QTest.qWait(200)
    checar(not marca.isVisible(), "sem expediente, o relógio não marca nada")

    # 16h43 no mostrador de 12 horas: 4h43 -> 141,5 graus.
    relogio.setProperty("marca", 16 * 60 + 43)
    QTest.qWait(700)
    checar(marca.isVisible(), "com expediente, a marca aparece")
    checar(
        abs(marca.rotation() - 141.5) < 1.0,
        f"e aponta para o fim do turno ({marca.rotation():.1f} graus)",
    )
    relogio.setProperty("marca", -1)
    QTest.qWait(200)


@passo
def confirmar_saida():
    """A confirmação abre e dá para desistir. Sair de verdade mataria a suíte."""
    print("-- abre a confirmação de saída e desiste")
    clicar(na_barra("o quarto"))
    clicar(achar("fechar o cantinho"))
    checar(
        achar("fechar o cantinho?") is not None,
        "a confirmação apareceu",
    )
    clicar(achar("ficar"))
    QTest.qWait(300)
    achados = [it for it in visiveis() if it.property("text") == "fechar o cantinho?"]
    checar(not achados, "e some ao desistir")


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
    clicar(na_barra("o dia"))
    escalas = [it for it in visiveis() if it.property("rotulo") in ("humor", "energia")]
    checar(len(escalas) == 2, "as duas escalas apareceram")
    foto("04_retrospectiva")
    # O menu do quarto já gravou humor e energia neste roteiro, então o painel
    # do dia oferece regravar em vez de guardar pela primeira vez.
    clicar(achar("encerrar de novo"))
    checar(backend.todayReview is not None, "a retrospectiva foi guardada")


@passo
def ver_a_semana():
    """O calendário da parede abre a semana."""
    print("-- abre a semana pelo calendário e navega para trás")
    clicar(achar_por_nome("calendario"))
    checar(principal.property("aba") == "semana", "a semana abriu")
    checar(backend.weekDelivered >= 2, "as entregas de hoje estão lá")
    foto("08_semana")

    clicar(achar("‹"))
    checar(backend.weekOffset == 1, "voltou uma semana")
    checar(backend.weekDelivered == 0, "e a semana passada está vazia")
    clicar(achar("›"))
    checar(backend.weekOffset == 0, "e volta para esta")
    # "o dia" e "a semana" são duas abas do mesmo painel: o primeiro clique
    # troca de aba, o segundo fecha a gaveta.
    clicar(na_barra("o dia"))
    clicar(na_barra("o dia"))


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
    print("-- alterna entre a janela grande e a mini")
    clicar(na_barra("mini"))
    checar(backend.miniVisible, "a mini apareceu")
    checar(not backend.mainVisible, "e a principal saiu da tela")
    QTest.qWait(400)
    if SAIDA:
        mini.grabWindow().save(str(SAIDA / "06_mini.png"))

    backend.showMain()
    QTest.qWait(400)
    checar(backend.mainVisible, "voltar para a grande funciona")
    checar(not backend.miniVisible, "e a mini sai junto")
    checar(
        principal.visibility != 3,  # Window.Minimized
        "a principal volta em tamanho normal",
    )


@passo
def minimizar():
    """Minimizar minimiza, e só.

    A versão anterior trocava a janela pela mini. O gesto de minimizar quer
    dizer "sai da frente agora", e o app respondia pondo outra janela na
    frente — sempre por cima de tudo, ainda por cima.
    """
    print("-- minimiza a janela principal")
    principal.showMinimized()
    QTest.qWait(700)
    checar(not backend.miniVisible, "a mini não aparece sozinha")

    principal.showNormal()
    QTest.qWait(700)
    checar(backend.mainVisible, "e volta ao normal ao reabrir")
    checar(principal.visibility != 3, "sem ficar minimizada")


@passo
def toque_do_quarto():
    """Duas horas correndo, e o quarto comenta.

    A regra do limiar é do pytest; o que se confere aqui é a tira aparecendo na
    tela e o botão dela encerrando a sessão de verdade. Esperar duas horas não
    é opção, então o sinal é disparado à mão — é o backend falando com o QML
    pelo mesmo caminho de sempre.
    """
    print("-- o quarto lembra que o relógio ficou correndo")
    backend.startSession(backend.backlog[0]["id"])
    QTest.qWait(200)

    backend.nudged.emit("O relógio ainda está correndo.")
    QTest.qWait(700)
    tira = achar("O relógio ainda está correndo.")
    checar(tira.isVisible(), "a tira do toque apareceu")

    clicar(achar("parar", perto_de_y=centro(tira).y()))
    checar(not backend.timerRunning, "e o botão dela encerrou a sessão")


@passo
def perguntar_pelo_extra():
    """Depois de uma sessão longa, o que mais se fechou junto.

    Uma hora raramente é uma coisa só: no meio dela chega o pedido urgente que
    ninguém teve tempo de anotar antes de atender. O limiar é do pytest; aqui
    se confere que a lista marca uma tarefa aberta e que o campo registra o que
    nunca esteve na lista.
    """
    print("-- pergunta o que mais se fechou junto")
    alvo = backend.today[0]["label"]
    antes = len(backend.shelf)

    backend.extraAsked.emit(75)
    QTest.qWait(700)
    checar(no_extra("foi um bom tempo por aqui").isVisible(), "a pergunta apareceu")

    clicar(no_extra(alvo))
    checar(len(backend.shelf) == antes + 1, "marcar na lista fecha a tarefa")

    clicar(achar_campo("ou escreva o que apareceu no caminho"))
    digitar(EXTRA)
    QTest.keyClick(principal, Qt.Key_Return)
    QTest.qWait(400)
    checar(len(backend.shelf) == antes + 2, "e o que não estava na lista também")
    checar(EXTRA in backend.todayCompleted, "com o texto que foi escrito")

    clicar(no_extra("só isso"))


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
        # A última nasce já concluída, pela pergunta do fim da sessão longa.
        "task.created": 5,
        "task.renamed": 1,
        # A última é aberta só para o toque do quarto ter o que encerrar.
        "session.started": 5,
        "session.ended": 5,
        # Círculo da lista, "entreguei" da barra, e as duas da pergunta.
        "task.completed": 4,
        "idea.captured": 1,
        "idea.promoted": 1,
        "backlog.reordered": 1,
        # Uma pelo menu do quarto, outra pelo painel do dia.
        "day.review": 2,
    }
    checar(contagem == esperado, f"o log é exatamente {esperado}")
    checar(
        [t.label for t in open_tasks(eventos)] == [CORRIGIDA],
        "o backlog reconstruído mantém o texto corrigido",
    )
    reidratadas = ideas(eventos)
    checar(
        len(reidratadas) == 1 and reidratadas[0].used,
        "a ideia reconstruída continua no mural, aproveitada",
    )
    checar(
        len(shelf_objects(eventos)) == 4,
        "a estante reconstruída tem os quatro objetos",
    )
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
