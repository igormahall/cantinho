"""A página: o log virando texto que se lê sem o app.

## Por que isto existe

Um log pessoal de anos sem exportação é um refém. O banco é SQLite e o esquema
é simples, mas "abra o sqlite3 e escreva um SELECT" não é uma saída — é a
ausência de uma. O que faz este arquivo é a diferença entre um app que guarda o
seu histórico e um app que o **retém**.

## Por que Markdown, e não HTML

Por longevidade, não por gosto. O ponto de uma saída de emergência é ser legível
sem nenhuma ferramenta, daqui a dez anos, por quem não tem o Cantinho instalado
— e um `.md` continua sendo texto num bloco de notas mesmo que nada mais
funcione. HTML seria mais bonito e menos útil exatamente onde importa; e quem
quiser o bonito converte um Markdown em HTML com qualquer coisa, enquanto o
caminho inverso perde a legibilidade crua.

## O que a página não é

Não é relatório. Não tem média, não tem percentual, não compara períodos e não
diz nada sobre dia vazio além de que ele está vazio — as mesmas regras que
valem na tela valem aqui, e por um motivo mais forte: um arquivo dura mais que
uma tela, e um número de cobrança impresso num arquivo cobra por mais tempo.

O único número é o mesmo que o bilhete da parede e o rodapé da semana já fazem:
a soma dos minutos de um dia. Somar não cobra; comparar cobraria.

## Também é a resposta ao horizonte longo

Ver mais que uma semana é **gerar a página daquele período**, não abrir um
painel maior. A semana é a costura por onde este projeto poderia virar planilha,
e a regra que a segura está aqui: a saída não é um gráfico melhor, é um
artefato que sai do app, se lê e se fecha. Não existe aba de mês, e não deve
existir.

Módulo puro: `events -> str`. Sem I/O, sem Qt, sem saber onde o arquivo vai
parar — quem escreve em disco é o backend.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, tzinfo
from typing import Iterable

from cantinho.core import projections as proj
from cantinho.core.events import Event

__all__ = [
    "MESES",
    "diary_markdown",
    "period_title",
    "suggested_filename",
    "week_bounds",
]

MESES: tuple[str, ...] = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

DIAS: tuple[str, ...] = (
    "segunda",
    "terça",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "domingo",
)


def _duracao(minutos: float) -> str:
    """Igual à da tela: `45 min`, `2h`, `3h20`. Nunca segundos, nunca decimal."""
    total = int(round(minutos))
    if total < 60:
        return f"{total} min"
    horas, resto = divmod(total, 60)
    return f"{horas}h" if resto == 0 else f"{horas}h{resto:02d}"


def _dia_por_extenso(dia: date) -> str:
    return f"{DIAS[dia.weekday()]}, {dia.day} de {MESES[dia.month - 1]} de {dia.year}"


def period_title(inicio: date | None, fim: date | None) -> str:
    """Como o período se apresenta no alto da página.

    `None` nos dois lados é "tudo", que é o caso da exportação do quarto
    inteiro. É o único lugar da página onde o intervalo aparece, e ele aparece
    porque um arquivo sem período é um arquivo que não se sabe reencontrar.
    """
    if inicio is None and fim is None:
        return "tudo o que o cantinho guardou"
    if inicio is not None and fim is not None:
        if inicio == fim:
            return _dia_por_extenso(inicio)
        if inicio.year == fim.year and inicio.month == fim.month:
            return (
                f"{inicio.day} a {fim.day} de {MESES[fim.month - 1]} de {fim.year}"
            )
        if inicio.year == fim.year:
            return (
                f"{inicio.day} de {MESES[inicio.month - 1]}"
                f" a {fim.day} de {MESES[fim.month - 1]} de {fim.year}"
            )
        return (
            f"{inicio.day} de {MESES[inicio.month - 1]} de {inicio.year}"
            f" a {fim.day} de {MESES[fim.month - 1]} de {fim.year}"
        )
    if inicio is not None:
        return f"de {_dia_por_extenso(inicio)} em diante"
    assert fim is not None
    return f"até {_dia_por_extenso(fim)}"


def suggested_filename(inicio: date | None, fim: date | None) -> str:
    """Nome de arquivo que ordena sozinho e diz o que tem dentro.

    Data em ISO no começo porque é o único formato que ordena alfabeticamente
    na mesma ordem em que ordena cronologicamente — numa pasta com dois anos de
    páginas, é a diferença entre uma lista e uma bagunça.
    """
    if inicio is None and fim is None:
        return "cantinho-tudo.md"
    if inicio is not None and fim is not None and inicio != fim:
        return f"cantinho-{inicio.isoformat()}-a-{fim.isoformat()}.md"
    unico = inicio or fim
    assert unico is not None
    return f"cantinho-{unico.isoformat()}.md"


def _no_periodo(dia: date, inicio: date | None, fim: date | None) -> bool:
    if inicio is not None and dia < inicio:
        return False
    return not (fim is not None and dia > fim)


def diary_markdown(
    events: Iterable[Event],
    tz: tzinfo,
    *,
    inicio: date | None = None,
    fim: date | None = None,
    gerado_em: datetime | None = None,
) -> str:
    """A página inteira, em Markdown.

    Três partes, na ordem em que o app as valoriza:

    1. **a estante** — o que foi entregue. É a razão de o app existir, então
       abre a página;
    2. **os dias** — o diário, dia a dia, com o que se fez, o tempo e a nota;
    3. **o mural** — as ideias, com as aproveitadas marcadas.

    Parte que não tem conteúdo no período **não aparece**, em vez de aparecer
    vazia: um cabeçalho seguido de nada é uma cobrança silenciosa por não ter
    nada ali.

    `events` é o log; o fatiamento por data acontece aqui, em horário local,
    porque dia é do usuário e o banco é UTC.
    """
    materializados = list(events)

    entregas = [
        task
        for task in proj.completed_tasks(materializados)
        if task.completed_at is not None
        and _no_periodo(task.completed_at.astimezone(tz).date(), inicio, fim)
    ]

    # Os dias que têm alguma coisa: sessão encerrada, entrega ou revisão.
    revisoes = proj.day_reviews(materializados)
    dias: set[date] = set()
    for task in entregas:
        assert task.completed_at is not None
        dias.add(task.completed_at.astimezone(tz).date())
    for sessao in proj.sessions(materializados):
        if sessao.ended_at is None:
            continue
        dia = sessao.ended_at.astimezone(tz).date()
        if _no_periodo(dia, inicio, fim):
            dias.add(dia)
    for texto_data in revisoes:
        dia = date.fromisoformat(texto_data)
        if _no_periodo(dia, inicio, fim):
            dias.add(dia)

    ideias = [
        ideia
        for ideia in proj.ideas(materializados)
        if _no_periodo(ideia.captured_at.astimezone(tz).date(), inicio, fim)
    ]

    linhas: list[str] = []
    linhas.append("# O cantinho")
    linhas.append("")
    linhas.append(period_title(inicio, fim))
    if gerado_em is not None:
        local = gerado_em.astimezone(tz)
        linhas.append("")
        linhas.append(
            f"*Página escrita em {local.day} de {MESES[local.month - 1]}"
            f" de {local.year}, às {local.strftime('%H:%M')}.*"
        )
    linhas.append("")

    if not entregas and not dias and not ideias:
        # Nada guardado ainda. Dizer isso é melhor que entregar um arquivo com
        # três cabeçalhos vazios — e a frase não cobra nada.
        linhas.append("Ainda não há nada guardado neste período.")
        linhas.append("")
        return "\n".join(linhas)

    if entregas:
        linhas.append("## A estante")
        linhas.append("")
        if len(entregas) == 1:
            linhas.append("O que foi entregue. É uma.")
        else:
            linhas.append(
                "O que foi entregue, na ordem em que entrou."
                f" São {len(entregas)}."
            )
        linhas.append("")
        for task in entregas:
            assert task.completed_at is not None
            quando = task.completed_at.astimezone(tz).date()
            linhas.append(f"- {task.label}  \n  *{_dia_por_extenso(quando)}*")
        linhas.append("")

    if dias:
        linhas.append("## Os dias")
        linhas.append("")
        for dia in sorted(dias):
            linhas.append(f"### {_dia_por_extenso(dia)}")
            linhas.append("")

            feitas = proj.completed_on(materializados, dia, tz)
            if feitas:
                for task in feitas:
                    linhas.append(f"- {task.label}")
                linhas.append("")

            sessoes = proj.sessions_on(materializados, dia, tz)
            minutos = proj.minutes_on(materializados, dia, tz)
            if sessoes:
                interrompidas = sum(1 for s in sessoes if s.interrupted)
                uma_so = len(sessoes) == 1
                quantas = "uma sessão" if uma_so else f"{len(sessoes)} sessões"
                # "uma delas" só existe quando há mais de uma para escolher.
                marca = ""
                if uma_so and interrompidas:
                    marca = ", interrompida"
                elif interrompidas == 1:
                    marca = ", uma delas interrompida"
                elif interrompidas > 1:
                    marca = f", {interrompidas} delas interrompidas"
                linhas.append(f"{quantas}, {_duracao(minutos)}{marca}.")
                linhas.append("")

                notas = [s.note for s in sessoes if s.note]
                for nota in notas:
                    linhas.append(f"> {nota}")
                if notas:
                    linhas.append("")

            revisao = revisoes.get(dia.isoformat())
            if revisao is not None:
                linhas.append(
                    f"Humor {revisao.mood} de 5, energia {revisao.energy} de 5."
                )
                linhas.append("")
                if revisao.note:
                    linhas.append(f"> {revisao.note}")
                    linhas.append("")

    if ideias:
        linhas.append("## O mural")
        linhas.append("")
        for ideia in sorted(ideias, key=lambda i: (i.captured_at, i.id)):
            quando = ideia.captured_at.astimezone(tz).date()
            # Aproveitada continua no mural, riscada — como na tela. O mural é
            # memória, não fila de trabalho.
            texto = f"~~{ideia.text}~~" if ideia.used else ideia.text
            sufixo = " — virou tarefa" if ideia.used else ""
            linhas.append(f"- {texto}  \n  *{quando.isoformat()}{sufixo}*")
        linhas.append("")

    return "\n".join(linhas)


def week_bounds(day: date) -> tuple[date, date]:
    """Segunda e domingo da semana de `day`. A mesma conta do painel."""
    segunda = day - timedelta(days=day.weekday())
    return segunda, segunda + timedelta(days=6)
