"""Enche um banco descartável com duas semanas de uso plausível.

Serve para olhar o app com o quarto vivo — estante ocupada, planta crescida,
mural com ideias riscadas — sem precisar usar o app por duas semanas nem sujar
o banco de verdade.

    python tools/semear.py                    # escreve em build/demo.db
    python tools/semear.py ~/cantinho/x.db    # ou onde você quiser

Depois:

    python -m cantinho.main --db build/demo.db

Tudo é escrito pelos construtores de evento de verdade, então passa pela mesma
validação do app: o banco que sai daqui é um log legítimo, não um fixture. E
como o relógio é injetado, os eventos ficam espalhados para trás no tempo — que
é o que faz a janela móvel de 14 dias ter o que mostrar.

Escrever com `--device-id` fixo é de propósito: dá para reconhecer no log o que
veio da semeadura e o que você fez à mão depois.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cantinho.core import events as ev
from cantinho.core.clock import FakeClock
from cantinho.core.store import EventStore

RAIZ = Path(__file__).resolve().parents[1]
PADRAO = RAIZ / "build" / "demo.db"

DEVICE = "semeadura"
AGORA = datetime.now(timezone.utc)

# Ficam abertas no backlog. As primeiras são o "hoje" que aparece no bilhete.
ABERTAS = [
    "revisar o capítulo 3",
    "responder o e-mail do orientador",
    "fechar a revisão bibliográfica",
    "trocar a correia da bicicleta",
]

# (rótulo, dias atrás em que foi concluída). Uma por objeto na estante — oito
# enchem a prateleira de cima e começam a de baixo, que é o que mostra as duas.
FEITAS = [
    ("montar o cronograma do semestre", 12),
    ("ler o artigo do Bourdieu", 10),
    ("escrever a introdução", 8),
    ("organizar as referências", 6),
    ("mandar o resumo para o congresso", 4),
    ("revisar o capítulo 2", 1),
    ("comprar café", 0),
    ("regar as plantas", 0),
]

# (texto, dias atrás, virou tarefa?). As que viraram aparecem riscadas no mural.
IDEIAS = [
    ("e se o capítulo 4 virasse dois capítulos menores", 5, False),
    ("procurar aquele paper sobre ritmo de escrita", 3, False),
    ("trocar a fonte do editor para algo mais quente", 9, True),
    ("perguntar ao orientador sobre o prazo do qualifying", 7, True),
]

# (dias atrás, minutos da sessão). Somam umas dezessete horas: o bastante para
# a planta chegar ao estágio 3 e ainda ter para onde crescer.
RITMO = [
    (13, 95), (12, 50), (11, 80), (10, 45), (9, 110), (8, 60),
    (7, 75), (6, 55), (5, 90), (4, 40), (3, 85), (2, 65),
    (1, 100), (0, 70),
]

# Sessões que foram interrompidas. Contam no foco do mesmo jeito: o tempo foi
# gasto. Estão aqui só para o log não sair artificialmente limpo.
INTERROMPIDAS = {10, 4}

RETROSPECTIVAS = [
    (3, 4, 3, "dia rendeu, mas cansei cedo"),
    (2, 3, 2, None),
    (1, 5, 4, "capítulo 2 finalmente saiu"),
]


def semear(caminho: Path) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    store = EventStore(caminho, device_id=DEVICE)
    relogio = FakeClock(AGORA - timedelta(days=14))
    lote: list[ev.Event] = []

    def em(dias_atras: float, hora: int, minuto: int = 0) -> None:
        alvo = AGORA - timedelta(days=dias_atras)
        relogio.set(alvo.replace(hour=hora, minute=minuto, second=0, microsecond=0))

    for indice, (rotulo, dias) in enumerate(FEITAS):
        em(dias + 0.5, hora=9, minuto=indice * 3)
        criada = ev.task_created(relogio, DEVICE, label=rotulo)
        lote.append(criada)
        em(dias, hora=17, minuto=indice * 5)
        lote.append(ev.task_completed(relogio, DEVICE, id=criada.payload["id"]))

    for dias, minutos in RITMO:
        em(dias, hora=14)
        inicio = ev.session_started(relogio, DEVICE)
        lote.append(inicio)
        relogio.advance(timedelta(minutes=minutos))
        lote.append(
            ev.session_ended(
                relogio,
                DEVICE,
                id=inicio.payload["id"],
                interrupted=dias in INTERROMPIDAS,
            )
        )

    no_backlog: list[str] = []
    for indice, rotulo in enumerate(ABERTAS):
        em(2, hora=11, minuto=indice * 7)
        criada = ev.task_created(relogio, DEVICE, label=rotulo)
        lote.append(criada)
        no_backlog.append(criada.payload["id"])

    for texto, dias, virou in IDEIAS:
        em(dias, hora=21, minuto=30)
        ideia = ev.idea_captured(relogio, DEVICE, text=texto)
        lote.append(ideia)
        if not virou:
            continue
        # Aproveitar uma ideia é sempre dois eventos: a tarefa nasce e a ideia
        # passa a apontar para ela. É o que a deixa riscada no mural.
        relogio.advance(timedelta(days=1))
        tarefa = ev.task_created(relogio, DEVICE, label=texto)
        lote.append(tarefa)
        lote.append(
            ev.idea_promoted(
                relogio, DEVICE,
                id=ideia.payload["id"], task_id=tarefa.payload["id"],
            )
        )
        relogio.advance(timedelta(hours=6))
        lote.append(ev.task_completed(relogio, DEVICE, id=tarefa.payload["id"]))
        no_backlog.append(tarefa.payload["id"])

    # Ordem escolhida à mão, para o "hoje" não ser só ordem de criação.
    em(1, hora=8)
    lote.append(ev.backlog_reordered(relogio, DEVICE, order=no_backlog))

    for dias, humor, energia, nota in RETROSPECTIVAS:
        em(dias, hora=22)
        data_local = (AGORA - timedelta(days=dias)).astimezone().date().isoformat()
        lote.append(
            ev.day_review(
                relogio, DEVICE, date=data_local,
                mood=humor, energy=energia, note=nota,
            )
        )

    gravados = store.append_many(lote)
    store.close()
    return gravados


def main(argv: list[str]) -> int:
    caminho = Path(argv[0]).expanduser() if argv else PADRAO
    gravados = semear(caminho)

    # Relata pelas projeções, não pela contagem de eventos: o que interessa
    # saber é o que vai aparecer na tela.
    from cantinho.core import projections as proj

    store = EventStore(caminho, device_id=DEVICE)
    eventos = store.read_all()
    store.close()

    print(f"{gravados} eventos em {caminho}")
    print(f"  backlog   {len(proj.open_tasks(eventos))} tarefas abertas")
    print(f"  estante   {len(proj.shelf_objects(eventos))} objetos")
    print(f"  foco 14d  {proj.focus_minutes_14d(eventos, AGORA) / 60:.1f} h")
    print(f"  planta    estágio {proj.plant_stage(eventos, AGORA)}")
    mural = proj.ideas(eventos)
    riscadas = sum(1 for ideia in mural if ideia.used)
    print(f"  mural     {len(mural)} ideias, {riscadas} riscadas")
    print(f"\npara abrir:  python -m cantinho.main --db {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
