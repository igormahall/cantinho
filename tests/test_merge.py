"""A porta que o `device_id` guarda, e o cadeado que a mantém utilizável.

**Este arquivo não implementa sync, e o projeto não deve implementar.** Nuvem,
conta de usuário e sincronização estão fora do escopo por decisão, e o
`CLAUDE.md` diz isso com todas as letras.

O que ele faz é outra coisa: o desenho do log foi feito de modo que um merge
entre dispositivos **seria** possível um dia — `device_id` em toda linha, uuid
como chave primária, `INSERT OR IGNORE` na escrita, ordem estável por
`(occurred_at, uuid)`. Custou um campo e preservou uma opção.

Opção preservada por acidente é opção que se perde por acidente. Basta uma
projeção passar a filtrar por `device_id`, ou a ordem do log passar a depender
de quem escreveu, e a porta fecha sem ninguém perceber — e só se descobre no dia
em que alguém precisar dela, que é o pior dia possível para descobrir.

Estes testes são o cadeado. Eles falham se alguém gastar a opção.
"""

from __future__ import annotations

from datetime import timedelta

from cantinho.core import events as ev
from cantinho.core import projections as proj
from cantinho.core.clock import FakeClock
from cantinho.core.store import EventStore

# `estado()` chama **todas** as projeções públicas de uma vez
# (`tests/projecoes.py`). Aqui havia uma tupla com cinco escolhidas à mão, e o
# cadeado valia só para elas — as outras oito não estavam certas nem erradas,
# estavam sem cadeado, que é a situação que este arquivo existe para impedir.
# Com o registro, uma projeção nova nasce trancada.
from projecoes import estado

CASA = "device-casa"
TRABALHO = "device-trabalho"


def _um_dia(clock: FakeClock, device: str, rotulo: str) -> list[ev.Event]:
    """Um pedaço de uso: tarefa criada, trabalhada e entregue."""
    tarefa = ev.task_created(clock, device, label=rotulo)
    clock.advance(timedelta(minutes=5))
    sessao = ev.session_started(clock, device, task_id=tarefa.payload["id"])
    clock.advance(timedelta(minutes=50))
    fim = ev.session_ended(clock, device, id=sessao.payload["id"])
    concluida = ev.task_completed(clock, device, id=tarefa.payload["id"])
    clock.advance(timedelta(minutes=5))
    return [tarefa, sessao, fim, concluida]


def test_o_merge_e_comutativo(clock: FakeClock) -> None:
    """**A propriedade central.** A ordem em que os logs se encontram não importa.

    É o que permitiria juntar duas máquinas sem resolução de conflito: não há
    "quem venceu", porque o resultado é o mesmo dos dois lados.
    """
    casa = _um_dia(clock, CASA, "escrever a tese")
    trabalho = _um_dia(clock, TRABALHO, "responder o orientador")
    agora = clock.now()

    assert estado(casa + trabalho, agora) == estado(trabalho + casa, agora)


def test_o_merge_e_idempotente(clock: FakeClock) -> None:
    """Juntar duas vezes é igual a juntar uma. É o `INSERT OR IGNORE` na prática."""
    casa = _um_dia(clock, CASA, "uma coisa")
    trabalho = _um_dia(clock, TRABALHO, "outra coisa")
    agora = clock.now()

    uma_vez = estado(casa + trabalho, agora)
    duas_vezes = estado(casa + trabalho + casa + trabalho, agora)
    assert uma_vez == duas_vezes


def test_o_store_absorve_o_log_do_outro_sem_conflito(
    tmp_path: object, clock: FakeClock
) -> None:
    """O merge, se um dia existir, é um `append_many`. Nada mais."""
    from pathlib import Path

    pasta = Path(str(tmp_path))
    casa = _um_dia(clock, CASA, "de casa")
    trabalho = _um_dia(clock, TRABALHO, "do trabalho")

    with EventStore(pasta / "casa.db", device_id=CASA) as a:
        a.append_many(casa)
        # Chega o log do outro lado.
        entraram = a.append_many(trabalho)
        assert entraram == len(trabalho)
        # E de novo: nada entra.
        assert a.append_many(trabalho) == 0
        assert a.count() == len(casa) + len(trabalho)
        juntos = a.read_all()

    # A ordem de leitura é a mesma independentemente de quem chegou primeiro.
    with EventStore(pasta / "trabalho.db", device_id=TRABALHO) as b:
        b.append_many(trabalho)
        b.append_many(casa)
        assert [e.uuid for e in b.read_all()] == [e.uuid for e in juntos]


def test_a_procedencia_sobrevive_a_ida_e_volta(clock: FakeClock) -> None:
    """Cada evento continua sabendo de que máquina veio, depois de juntar."""
    casa = _um_dia(clock, CASA, "de casa")
    trabalho = _um_dia(clock, TRABALHO, "do trabalho")

    juntos = [ev.Event.from_row(e.to_row()) for e in casa + trabalho]
    origens = {e.device_id for e in juntos}
    assert origens == {CASA, TRABALHO}


def test_nenhuma_projecao_olha_o_device_id(clock: FakeClock) -> None:
    """**O cadeado de verdade.**

    Se uma projeção passasse a filtrar ou desempatar por `device_id`, dois
    dispositivos com o mesmo log dariam telas diferentes — e o merge deixaria de
    ser um `INSERT OR IGNORE` para virar resolução de conflito.

    A prova é direta: trocar o `device_id` de todo evento não pode mudar nada do
    que a tela mostra.
    """
    eventos = _um_dia(clock, CASA, "escrever a tese")
    eventos.append(ev.idea_captured(clock, CASA, text="uma ideia"))
    agora = clock.now()

    trocados = [
        ev.Event(
            uuid=e.uuid,
            device_id="outro-aparelho-qualquer",
            occurred_at=e.occurred_at,
            kind=e.kind,
            payload=e.payload,
        )
        for e in eventos
    ]

    assert estado(eventos, agora) == estado(trocados, agora)


def test_a_ordem_do_log_nao_depende_de_quem_escreveu(clock: FakeClock) -> None:
    """O desempate é por uuid, não por dispositivo.

    Se fosse por `device_id`, uma máquina veria a ordem de outra maneira — e a
    ordem é o que as projeções leem.
    """
    momento = clock.now()
    a = ev.Event(
        uuid="00000000-aaaa",
        device_id=TRABALHO,
        occurred_at=momento,
        kind="task.created",
        payload={"id": "t1", "label": "primeira"},
    )
    b = ev.Event(
        uuid="11111111-bbbb",
        device_id=CASA,
        occurred_at=momento,
        kind="task.created",
        payload={"id": "t2", "label": "segunda"},
    )
    # Mesmo instante, dispositivos diferentes: quem manda é o uuid.
    assert [t.id for t in proj.open_tasks([a, b])] == ["t1", "t2"]
    assert [t.id for t in proj.open_tasks([b, a])] == ["t1", "t2"]


def test_os_ids_de_dominio_nao_colidem_entre_maquinas(clock: FakeClock) -> None:
    """Tarefa criada em duas máquinas não vira a mesma tarefa.

    O id de domínio é uuid4, sorteado sem coordenação — é o que torna possível
    escrever nos dois lados sem combinar nada antes.
    """
    de_casa = [ev.task_created(clock, CASA, label="a mesma frase") for _ in range(20)]
    do_trabalho = [
        ev.task_created(clock, TRABALHO, label="a mesma frase") for _ in range(20)
    ]
    ids = {e.payload["id"] for e in de_casa + do_trabalho}
    assert len(ids) == 40
    # E o log inteiro continua sem uuid repetido.
    assert len({e.uuid for e in de_casa + do_trabalho}) == 40
