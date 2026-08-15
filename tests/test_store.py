from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from cantinho.core import events as ev
from cantinho.core import store as store_module
from cantinho.core.clock import FakeClock
from cantinho.core.events import Event
from cantinho.core.store import DEVICE_ID_FILENAME, EventStore, default_data_dir

from conftest import DEVICE
from projecoes import estado, log_de_prova


# --------------------------------------------------------------------- setup


def test_schema_criado_no_primeiro_uso(store: EventStore) -> None:
    tabelas = {
        linha[0]
        for linha in store._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "events" in tabelas
    # Regra 1: events é a única tabela persistida.
    assert tabelas - {"events"} == set()

    indices = {
        linha[0]
        for linha in store._conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    }
    assert "idx_events_time" in indices


def test_wal_ligado(store: EventStore) -> None:
    modo = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert modo.lower() == "wal"


def test_abrir_duas_vezes_nao_quebra(tmp_path: Path) -> None:
    caminho = tmp_path / "cantinho.db"
    with EventStore(caminho):
        pass
    with EventStore(caminho) as segundo:
        assert segundo.count() == 0


def test_cria_diretorio_que_nao_existe(tmp_path: Path) -> None:
    caminho = tmp_path / "fundo" / "do" / "poco" / "cantinho.db"
    with EventStore(caminho) as aberto:
        assert aberto.db_path.exists()


# ----------------------------------------------------------------- device_id


def test_device_id_persistido_ao_lado_do_banco(tmp_path: Path) -> None:
    caminho = tmp_path / "cantinho.db"
    with EventStore(caminho) as primeiro:
        gerado = primeiro.device_id
        assert primeiro.device_id_path == tmp_path / DEVICE_ID_FILENAME
        assert primeiro.device_id_path.read_text(encoding="utf-8").strip() == gerado

    with EventStore(caminho) as segundo:
        assert segundo.device_id == gerado


def test_device_id_explicito_vence(tmp_path: Path) -> None:
    with EventStore(tmp_path / "cantinho.db", device_id="fixo") as aberto:
        assert aberto.device_id == "fixo"


def test_device_id_com_arquivo_vazio_e_regenerado(tmp_path: Path) -> None:
    (tmp_path / DEVICE_ID_FILENAME).write_text("   \n", encoding="utf-8")
    with EventStore(tmp_path / "cantinho.db") as aberto:
        assert aberto.device_id.strip()


def test_default_data_dir_no_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(store_module.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_data_dir() == tmp_path / "Cantinho"


def test_default_data_dir_no_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store_module.sys, "platform", "linux")
    assert default_data_dir() == Path.home() / ".local" / "share" / "cantinho"


# ------------------------------------------------------------- idempotência


def test_append_devolve_falso_no_duplicado(store: EventStore, clock: FakeClock) -> None:
    evento = ev.task_created(clock, DEVICE, label="tese")
    assert store.append(evento) is True
    assert store.append(evento) is False
    assert store.count() == 1


def test_append_many_ignora_os_ja_conhecidos(store: EventStore, clock: FakeClock) -> None:
    primeiro = ev.task_created(clock, DEVICE, label="a")
    clock.advance(timedelta(minutes=1))
    segundo = ev.task_created(clock, DEVICE, label="b")

    assert store.append_many([primeiro]) == 1
    assert store.append_many([primeiro, segundo]) == 1
    assert store.append_many([primeiro, segundo]) == 0
    assert store.count() == 2


def test_reaplicar_o_lote_inteiro_e_no_op(store: EventStore, clock: FakeClock) -> None:
    """É isto que permitiria um merge futuro sem resolução de conflito."""
    lote = []
    for indice in range(20):
        lote.append(ev.task_created(clock, DEVICE, label=f"tarefa {indice}"))
        clock.advance(timedelta(seconds=30))

    store.append_many(lote)
    depois_do_primeiro = store.read_all()

    for _ in range(3):
        assert store.append_many(lote) == 0

    assert store.read_all() == depois_do_primeiro


def test_mesmo_uuid_nao_sobrescreve(store: EventStore, clock: FakeClock) -> None:
    """INSERT OR IGNORE tem que ignorar, não substituir."""
    original = ev.task_created(clock, DEVICE, label="original", id="t1")
    impostor = Event(
        uuid=original.uuid,
        device_id=DEVICE,
        occurred_at=clock.now(),
        kind="task.created",
        payload={"id": "t1", "label": "adulterado"},
    )

    store.append(original)
    assert store.append(impostor) is False

    (guardado,) = store.read_all()
    assert guardado == original
    assert guardado.payload["label"] == "original"


def test_append_many_vazio(store: EventStore) -> None:
    assert store.append_many([]) == 0


def test_nenhum_caminho_de_escrita_usa_update_ou_delete(
    store: EventStore, clock: FakeClock
) -> None:
    """Regra 2: o log é append-only.

    Em vez de olhar o código, nega UPDATE e DELETE no próprio sqlite e exercita
    as escritas. Se algum caminho passar a editar, o teste quebra na hora.
    """
    negados: list[int] = []

    def auditor(acao: int, *_resto: object) -> int:
        if acao in (sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            negados.append(acao)
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    store._conn.set_authorizer(auditor)
    try:
        evento = ev.task_created(clock, DEVICE, label="a")
        store.append(evento)
        store.append(evento)
        clock.advance(timedelta(minutes=1))
        store.append_many([ev.task_completed(clock, DEVICE, id=evento.payload["id"])])
        assert store.count() == 2
        assert len(store.read_all()) == 2
    finally:
        store._conn.set_authorizer(None)

    assert negados == []


# ---------------------------------------------------------------- leitura


def test_read_all_em_ordem_cronologica(store: EventStore, clock: FakeClock) -> None:
    esperados = []
    for indice in range(10):
        esperados.append(ev.task_created(clock, DEVICE, label=f"t{indice}"))
        clock.advance(timedelta(minutes=7))

    # Grava fora de ordem de propósito.
    store.append_many(reversed(esperados))
    assert store.read_all() == esperados


def test_ordem_estavel_no_mesmo_instante(store: EventStore, clock: FakeClock) -> None:
    """Sem desempate por uuid, eventos simultâneos sairiam em ordem arbitrária."""
    simultaneos = [ev.task_created(clock, DEVICE, label=f"t{i}") for i in range(25)]
    store.append_many(simultaneos)

    primeira = store.read_all()
    assert primeira == sorted(simultaneos, key=lambda e: e.sort_key)
    assert primeira == store.read_all()


def test_read_since_inclui_a_borda(store: EventStore, clock: FakeClock) -> None:
    antigo = ev.task_created(clock, DEVICE, label="antigo")
    clock.advance(timedelta(days=1))
    corte = clock.now()
    na_borda = ev.task_created(clock, DEVICE, label="na borda")
    clock.advance(timedelta(days=1))
    novo = ev.task_created(clock, DEVICE, label="novo")

    store.append_many([antigo, na_borda, novo])

    assert store.read_since(corte) == [na_borda, novo]
    assert store.read_since(corte + timedelta(microseconds=1)) == [novo]
    assert store.read_since(antigo.occurred_at) == [antigo, na_borda, novo]


def test_read_all_vazio(store: EventStore) -> None:
    assert store.read_all() == []


# ----------------------------------------------- reconstrução a partir do log


def test_estado_reconstruido_do_zero_apos_reabrir(tmp_path: Path) -> None:
    """Nada de derivado vai a disco: fechar e reabrir tem que dar o mesmo estado.

    A comparação é do estado **inteiro** — as treze projeções públicas de uma
    vez, pelo banco de provas (`tests/projecoes.py`). Antes eram três escolhidas
    à mão, e é justamente uma projeção esquecida que teria como divergir aqui
    sem ninguém ver: a ida ao disco passa por serialização de JSON e de
    timestamp, e o que ela deforma não é o que se lembra de conferir.
    """
    caminho = tmp_path / "cantinho.db"
    log, agora = log_de_prova(DEVICE)

    with EventStore(caminho, device_id=DEVICE) as primeiro:
        primeiro.append_many(log)
        estado_antes = estado(log, agora)

    with EventStore(caminho, device_id=DEVICE) as segundo:
        relido = segundo.read_all()
        assert relido == sorted(log, key=lambda e: e.sort_key)
        estado_depois = estado(relido, agora)

    assert estado_depois == estado_antes
    # E não é um estado vazio comparado com outro vazio: o log de prova faz
    # toda projeção falar, e há teste disso junto com o banco de provas.
    assert [t.label for t in estado_depois["open_tasks"]] == ["ler o artigo novo"]
    assert [t.label for t in estado_depois["completed_tasks"]] == ["revisar o capítulo 3"]
    assert estado_depois["focus_minutes_14d"] == 240.0
