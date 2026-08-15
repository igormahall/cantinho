"""A página que sai do app.

O que se prova aqui é o contrato de uma saída de emergência: que ela contém o
que o usuário escreveu, que respeita o recorte de período em horário local, e
que **não** contém a linguagem de desempenho que o projeto recusa na tela — a
regra vale mais forte num arquivo, porque arquivo dura mais que tela.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from cantinho.core import events as ev
from cantinho.core import export
from cantinho.core.clock import FakeClock

from conftest import DEVICE

# São Paulo, que é o fuso das duas máquinas do projeto. Fixo de propósito: o
# recorte por dia é local, e um teste que usasse o fuso da máquina passaria ou
# falharia dependendo de onde roda.
SAOPAULO = timezone(timedelta(hours=-3))


def _log(clock: FakeClock) -> list[ev.Event]:
    """Um dia de uso: uma tarefa entregue, uma sessão com nota, ideia, revisão."""
    tarefa = ev.task_created(clock, DEVICE, label="revisar o capítulo 3")
    clock.advance(timedelta(hours=1))
    sessao = ev.session_started(clock, DEVICE, task_id=tarefa.payload["id"])
    clock.advance(timedelta(minutes=80))
    fim = ev.session_ended(
        clock, DEVICE, id=sessao.payload["id"], note="travou na bibliografia"
    )
    concluida = ev.task_completed(clock, DEVICE, id=tarefa.payload["id"])
    ideia = ev.idea_captured(clock, DEVICE, text="trocar a fonte do editor")
    revisao = ev.day_review(
        clock,
        DEVICE,
        date=clock.now().astimezone(SAOPAULO).date().isoformat(),
        mood=4,
        energy=3,
        note="dia bom",
    )
    return [tarefa, sessao, fim, concluida, ideia, revisao]


def test_a_pagina_traz_o_que_o_usuario_escreveu(clock: FakeClock) -> None:
    pagina = export.diary_markdown(_log(clock), SAOPAULO)
    assert "revisar o capítulo 3" in pagina
    assert "travou na bibliografia" in pagina
    assert "trocar a fonte do editor" in pagina
    assert "dia bom" in pagina


def test_as_tres_partes_aparecem_na_ordem_do_app(clock: FakeClock) -> None:
    """A estante abre a página: é a razão de o app existir."""
    pagina = export.diary_markdown(_log(clock), SAOPAULO)
    assert pagina.index("## A estante") < pagina.index("## Os dias")
    assert pagina.index("## Os dias") < pagina.index("## O mural")


def test_parte_sem_conteudo_nao_aparece_vazia(clock: FakeClock) -> None:
    """Cabeçalho seguido de nada é cobrança silenciosa por não ter nada ali."""
    so_ideia = [ev.idea_captured(clock, DEVICE, text="uma ideia solta")]
    pagina = export.diary_markdown(so_ideia, SAOPAULO)
    assert "## O mural" in pagina
    assert "## A estante" not in pagina
    assert "## Os dias" not in pagina


def test_log_vazio_diz_isso_em_vez_de_entregar_cabecalhos(clock: FakeClock) -> None:
    pagina = export.diary_markdown([], SAOPAULO)
    assert "Ainda não há nada guardado" in pagina
    assert "##" not in pagina


def test_a_pagina_nao_tem_linguagem_de_desempenho(clock: FakeClock) -> None:
    """**A regra do projeto, num arquivo que dura mais que a tela.**

    Sem média, sem percentual, sem meta, sem sequência. O único número é a soma
    de minutos de um dia, que é a mesma conta que o bilhete da parede já faz.
    """
    pagina = export.diary_markdown(_log(clock), SAOPAULO).lower()
    for proibida in (
        "%",
        "média",
        "media ",
        "meta",
        "streak",
        "sequência",
        "produtividade",
        "desempenho",
        "progresso",
    ):
        assert proibida not in pagina, f"a página não deveria falar em {proibida!r}"


def test_o_recorte_de_periodo_e_em_horario_local(clock: FakeClock) -> None:
    """22h em São Paulo é o dia seguinte em UTC — o recorte segue o usuário."""
    # 2026-03-02 09:00 UTC é 06:00 em São Paulo, ainda dia 2.
    tarde = FakeClock(datetime(2026, 3, 3, 1, 30, tzinfo=timezone.utc))
    # 01:30 UTC do dia 3 é 22:30 do dia 2 em São Paulo.
    tarefa = ev.task_created(tarde, DEVICE, label="entrega da noite")
    concluida = ev.task_completed(tarde, DEVICE, id=tarefa.payload["id"])

    do_dia_2 = export.diary_markdown(
        [tarefa, concluida], SAOPAULO, inicio=date(2026, 3, 2), fim=date(2026, 3, 2)
    )
    assert "entrega da noite" in do_dia_2

    do_dia_3 = export.diary_markdown(
        [tarefa, concluida], SAOPAULO, inicio=date(2026, 3, 3), fim=date(2026, 3, 3)
    )
    assert "entrega da noite" not in do_dia_3


def test_o_periodo_recorta_de_verdade(clock: FakeClock) -> None:
    dentro = _log(clock)
    clock.advance(timedelta(days=40))
    fora = ev.task_created(clock, DEVICE, label="muito depois")
    depois = ev.task_completed(clock, DEVICE, id=fora.payload["id"])

    hoje = dentro[0].occurred_at.astimezone(SAOPAULO).date()
    pagina = export.diary_markdown(
        dentro + [fora, depois], SAOPAULO, inicio=hoje, fim=hoje
    )
    assert "revisar o capítulo 3" in pagina
    assert "muito depois" not in pagina


def test_a_ideia_aproveitada_sai_riscada(clock: FakeClock) -> None:
    """Como na tela: aproveitada não some do mural, fica riscada."""
    ideia = ev.idea_captured(clock, DEVICE, text="virou trabalho")
    tarefa = ev.task_created(clock, DEVICE, label="o trabalho")
    promovida = ev.idea_promoted(
        clock, DEVICE, id=ideia.payload["id"], task_id=tarefa.payload["id"]
    )
    pagina = export.diary_markdown([ideia, tarefa, promovida], SAOPAULO)
    assert "~~virou trabalho~~" in pagina
    assert "virou tarefa" in pagina


@pytest.mark.parametrize(
    "inicio,fim,esperado",
    [
        (None, None, "cantinho-tudo.md"),
        (date(2026, 8, 10), date(2026, 8, 16), "cantinho-2026-08-10-a-2026-08-16.md"),
        (date(2026, 8, 10), date(2026, 8, 10), "cantinho-2026-08-10.md"),
    ],
)
def test_o_nome_do_arquivo_ordena_sozinho(
    inicio: date | None, fim: date | None, esperado: str
) -> None:
    assert export.suggested_filename(inicio, fim) == esperado


def test_o_titulo_do_periodo_encolhe_quando_da(clock: FakeClock) -> None:
    assert export.period_title(None, None) == "tudo o que o cantinho guardou"
    # Mesmo mês: o mês aparece uma vez só.
    assert (
        export.period_title(date(2026, 8, 10), date(2026, 8, 16))
        == "10 a 16 de agosto de 2026"
    )
    # Mês diferente, ano igual: o ano aparece uma vez só.
    assert (
        export.period_title(date(2026, 7, 27), date(2026, 8, 2))
        == "27 de julho a 2 de agosto de 2026"
    )
    # Ano diferente: os dois anos aparecem.
    assert "2025" in export.period_title(date(2025, 12, 29), date(2026, 1, 4))


def test_week_bounds_bate_com_o_painel() -> None:
    """A semana começa na segunda, como em `_inicio_da_semana` do backend."""
    inicio, fim = export.week_bounds(date(2026, 8, 14))  # sexta
    assert inicio == date(2026, 8, 10)
    assert fim == date(2026, 8, 16)
    assert inicio.weekday() == 0 and fim.weekday() == 6


def test_a_sessao_interrompida_e_dita_sem_julgamento(clock: FakeClock) -> None:
    tarefa = ev.task_created(clock, DEVICE, label="algo")
    sessao = ev.session_started(clock, DEVICE, task_id=tarefa.payload["id"])
    clock.advance(timedelta(minutes=25))
    fim = ev.session_ended(clock, DEVICE, id=sessao.payload["id"], interrupted=True)
    pagina = export.diary_markdown([tarefa, sessao, fim], SAOPAULO)
    assert "uma sessão, 25 min, interrompida." in pagina
    # "uma delas" só existe quando há mais de uma para escolher.
    assert "uma delas" not in pagina
    # E nada que sugira que isso foi um erro.
    assert "perdid" not in pagina.lower()


def test_com_varias_sessoes_a_concordancia_muda(clock: FakeClock) -> None:
    eventos: list[ev.Event] = []
    for indice in range(3):
        sessao = ev.session_started(clock, DEVICE)
        clock.advance(timedelta(minutes=20))
        eventos += [
            sessao,
            ev.session_ended(
                clock, DEVICE, id=sessao.payload["id"], interrupted=indice == 0
            ),
        ]
        clock.advance(timedelta(minutes=5))
    pagina = export.diary_markdown(eventos, SAOPAULO)
    assert "3 sessões" in pagina
    assert "uma delas interrompida" in pagina


def test_o_modulo_e_puro(clock: FakeClock) -> None:
    """`core/` não instancia Qt e não toca disco. Este é o guarda."""
    import inspect

    fonte = inspect.getsource(export)
    assert "PySide6" not in fonte
    assert "open(" not in fonte
    assert "Path" not in fonte
