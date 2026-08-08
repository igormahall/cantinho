from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cantinho.core.clock import Clock, FakeClock, SystemClock, ensure_utc


def test_system_clock_devolve_utc_aware() -> None:
    agora = SystemClock().now()
    assert agora.tzinfo is not None
    assert agora.utcoffset() == timedelta(0)


def test_ambos_satisfazem_o_protocolo() -> None:
    assert isinstance(SystemClock(), Clock)
    assert isinstance(FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc)), Clock)


def test_fake_clock_nao_anda_sozinho(clock: FakeClock) -> None:
    assert clock.now() == clock.now()


def test_fake_clock_avanca(clock: FakeClock) -> None:
    antes = clock.now()
    depois = clock.advance(timedelta(hours=3))
    assert depois - antes == timedelta(hours=3)
    assert clock.now() == depois


def test_fake_clock_recusa_andar_para_tras(clock: FakeClock) -> None:
    with pytest.raises(ValueError):
        clock.advance(timedelta(seconds=-1))


def test_datetime_ingenuo_e_recusado() -> None:
    with pytest.raises(ValueError):
        ensure_utc(datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 1, 1))


def test_ensure_utc_converte_de_outro_fuso() -> None:
    saopaulo = timezone(timedelta(hours=-3))
    convertido = ensure_utc(datetime(2026, 1, 1, 9, 0, tzinfo=saopaulo))
    assert convertido == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert convertido.utcoffset() == timedelta(0)


def test_set_reposiciona(clock: FakeClock) -> None:
    alvo = datetime(2030, 6, 1, tzinfo=timezone.utc)
    clock.set(alvo)
    assert clock.now() == alvo
