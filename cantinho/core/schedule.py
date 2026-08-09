"""O expediente, como dado.

Este arquivo existe para um motivo só: o app sabia que horas são, mas não sabia
o que essas horas significam para quem usa. Sete da manhã e sete da noite eram
a mesma coisa para ele — "dia" — quando na prática uma é o começo do turno e a
outra é depois do jantar.

Tudo aqui é função pura sobre horário **local de parede**, e é isso que o
distingue do resto do `core`: os demais módulos trabalham em UTC, porque
timestamp de evento não tem fuso. Expediente tem. Ninguém trabalha "das 10h
UTC"; trabalha das sete da manhã, seja lá qual for o fuso da máquina.

A jornada é uma constante e não uma configuração. É um app pessoal de uma
pessoa com um horário fixo; um painel de preferências para editar isto seria
mais código do que a informação que ele guarda. Mudou de turno, muda aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

__all__ = [
    "Stretch",
    "WORKDAYS",
    "STRETCHES",
    "SHIFT_START",
    "SHIFT_END",
    "NIGHT_FROM_HOUR",
    "NIGHT_UNTIL_HOUR",
    "is_workday",
    "stretch_at",
    "in_shift",
    "is_daylight",
    "next_boundary",
    "minutes_of",
]


@dataclass(frozen=True)
class Stretch:
    """Um trecho contínuo de trabalho, com nome."""

    start: time
    end: time
    name: str

    def contains(self, moment: time) -> bool:
        return self.start <= moment < self.end


# Segunda a sexta. `weekday()` conta a partir de segunda = 0.
WORKDAYS = frozenset({0, 1, 2, 3, 4})

# Os dois trechos do turno diurno, com o almoço no meio.
STRETCHES: tuple[Stretch, ...] = (
    Stretch(time(7, 0), time(12, 15), "manhã"),
    Stretch(time(13, 15), time(16, 43), "tarde"),
)

# O turno inteiro, almoço incluído.
#
# O envelope existe separado dos trechos porque o tema usa um e o relógio usa
# o outro: o quarto não pode escurecer no almoço — a pessoa voltou uma hora
# depois, não anoiteceu.
SHIFT_START = STRETCHES[0].start
SHIFT_END = STRETCHES[-1].end

# Regra de relógio, usada quando não há expediente que valha: fim de semana,
# feriado, ou a máquina de casa à noite.
NIGHT_FROM_HOUR = 18
NIGHT_UNTIL_HOUR = 6


def is_workday(day: date) -> bool:
    return day.weekday() in WORKDAYS


def stretch_at(moment: datetime) -> Stretch | None:
    """Em qual trecho do turno o instante cai, ou None fora deles.

    O almoço devolve None: não é trecho de trabalho.
    """
    if not is_workday(moment.date()):
        return None
    agora = moment.time()
    for stretch in STRETCHES:
        if stretch.contains(agora):
            return stretch
    return None


def in_shift(moment: datetime) -> bool:
    """Dentro do turno, contando o almoço como parte dele."""
    if not is_workday(moment.date()):
        return False
    return SHIFT_START <= moment.time() < SHIFT_END


def is_daylight(moment: datetime) -> bool:
    """Se o quarto deve estar claro neste instante.

    Em dia útil quem manda é o turno: o quarto acende quando o dia da pessoa
    começa e vira noite quando ele termina, em vez de esperar uma hora
    arbitrária. É o que faz a travessia de tema significar alguma coisa — ela
    acontece junto com o fim do expediente, não às seis em ponto.

    Fora de dia útil cai na regra do relógio, que é o que serve para o uso de
    casa e para o fim de semana.
    """
    if is_workday(moment.date()):
        return in_shift(moment)
    hora = moment.hour
    return NIGHT_UNTIL_HOUR <= hora < NIGHT_FROM_HOUR


def minutes_of(momento: time) -> int:
    """Minutos desde a meia-noite. É assim que a marca chega ao relógio."""
    return momento.hour * 60 + momento.minute


def next_boundary(moment: datetime) -> time | None:
    """A próxima virada do dia de trabalho, ou None se não há mais nenhuma.

    São quatro por dia útil: entrar, parar para o almoço, voltar e sair. De
    manhã a próxima é o almoço; à tarde, o fim do expediente.

    É deliberadamente "a próxima" e não "o fim do turno". Saber que faltam duas
    horas para ir embora não ajuda ninguém às oito da manhã; saber onde termina
    o trecho em que se está, ajuda.
    """
    if not is_workday(moment.date()):
        return None
    agora = moment.time()
    viradas = [limite for stretch in STRETCHES for limite in (stretch.start, stretch.end)]
    for virada in viradas:
        if agora < virada:
            return virada
    return None
