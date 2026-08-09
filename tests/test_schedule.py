"""O expediente.

Turno diurno de segunda a sexta: 7h00 às 12h15, almoço, 13h15 às 16h43.

Estes testes fixam as bordas — que é onde toda regra de horário quebra — e o
comportamento fora do turno, que é o uso de casa e o de fim de semana.
"""

from __future__ import annotations

from datetime import datetime, time

import pytest

from cantinho.core import schedule as sch

# 2026-08-10 é uma segunda-feira; 2026-08-15, um sábado.
SEGUNDA = "2026-08-10"
QUINTA = "2026-08-13"
SABADO = "2026-08-15"
DOMINGO = "2026-08-16"


def em(dia: str, hora: str) -> datetime:
    return datetime.fromisoformat(f"{dia}T{hora}")


# --------------------------------------------------------------- dias úteis


@pytest.mark.parametrize("dia", [SEGUNDA, QUINTA])
def test_dia_de_semana_e_util(dia: str) -> None:
    assert sch.is_workday(em(dia, "09:00").date())


@pytest.mark.parametrize("dia", [SABADO, DOMINGO])
def test_fim_de_semana_nao_e_util(dia: str) -> None:
    assert not sch.is_workday(em(dia, "09:00").date())


# ------------------------------------------------------------------- trechos


@pytest.mark.parametrize(
    "hora,esperado",
    [
        ("06:59", None),
        ("07:00", "manhã"),
        ("12:14", "manhã"),
        # A borda pertence ao próximo, não ao anterior: às 12h15 já é almoço.
        ("12:15", None),
        ("13:14", None),
        ("13:15", "tarde"),
        ("16:42", "tarde"),
        ("16:43", None),
    ],
)
def test_trecho_do_turno(hora: str, esperado: str | None) -> None:
    trecho = sch.stretch_at(em(SEGUNDA, hora))
    assert (trecho.name if trecho else None) == esperado


def test_almoco_nao_e_trecho_mas_esta_dentro_do_turno() -> None:
    """A distinção que o tema depende.

    O almoço não é trabalho, mas o quarto não pode escurecer nele: quem saiu
    para comer volta uma hora depois, não anoiteceu.
    """
    meio_dia = em(SEGUNDA, "12:40")
    assert sch.stretch_at(meio_dia) is None
    assert sch.in_shift(meio_dia)


def test_sabado_nao_tem_trecho_nem_turno() -> None:
    assert sch.stretch_at(em(SABADO, "10:00")) is None
    assert not sch.in_shift(em(SABADO, "10:00"))


# --------------------------------------------------------------------- luz


@pytest.mark.parametrize(
    "hora,claro",
    [
        ("06:30", False),
        ("07:00", True),
        ("12:40", True),
        ("16:42", True),
        # O fim do turno é o que apaga a luz, não uma hora redonda arbitrária.
        ("16:43", False),
        ("19:00", False),
    ],
)
def test_em_dia_util_a_luz_segue_o_turno(hora: str, claro: bool) -> None:
    assert sch.is_daylight(em(SEGUNDA, hora)) is claro


@pytest.mark.parametrize(
    "hora,claro",
    [("05:00", False), ("06:00", True), ("17:30", True), ("18:00", False)],
)
def test_fora_de_dia_util_vale_o_relogio(hora: str, claro: bool) -> None:
    """Fim de semana e uso de casa caem na regra antiga, de 6h às 18h."""
    assert sch.is_daylight(em(SABADO, hora)) is claro


# ---------------------------------------------------------------- viradas


@pytest.mark.parametrize(
    "hora,esperado",
    [
        ("06:00", time(7, 0)),
        ("09:00", time(12, 15)),
        ("12:30", time(13, 15)),
        ("14:00", time(16, 43)),
        ("17:00", None),
        ("23:59", None),
    ],
)
def test_proxima_virada(hora: str, esperado: time | None) -> None:
    assert sch.next_boundary(em(SEGUNDA, hora)) == esperado


def test_fim_de_semana_nao_tem_virada() -> None:
    assert sch.next_boundary(em(DOMINGO, "10:00")) is None


def test_virada_na_hora_exata_aponta_para_a_seguinte() -> None:
    """Em cima da borda, o que interessa é a próxima, não a que acabou."""
    assert sch.next_boundary(em(SEGUNDA, "12:15")) == time(13, 15)


def test_minutos_desde_a_meia_noite() -> None:
    assert sch.minutes_of(time(16, 43)) == 16 * 60 + 43
    assert sch.minutes_of(time(0, 0)) == 0


def test_o_turno_cobre_os_trechos() -> None:
    """Coerência interna: o envelope tem que abraçar os dois trechos."""
    assert sch.SHIFT_START == sch.STRETCHES[0].start
    assert sch.SHIFT_END == sch.STRETCHES[-1].end
    for trecho in sch.STRETCHES:
        assert sch.SHIFT_START <= trecho.start < trecho.end <= sch.SHIFT_END
