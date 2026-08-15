"""As propriedades que valem para **toda** projeção, conferidas sobre todas.

`CLAUDE.md`, regra 4: "projeção é função pura: `events -> estado`, idempotente
e determinística". Isto aqui é essa frase transformada em teste, e a diferença
está no alcance — cada propriedade abaixo roda sobre as treze projeções
públicas, a partir de um log de prova montado uma vez (`projecoes.py`).

Antes, cada propriedade tinha a sua lista escrita à mão, e nenhuma lista era a
mesma: log vazio cobria seis projeções, a pureza seis, o iterador esgotável
duas, o `device_id` cinco. Não era rigor a menos por descuido — é o que
acontece quando cada teste escolhe a sua amostra. Aqui a amostra é o módulo
inteiro, e o teste de completude não deixa uma projeção nova ficar de fora.

O que **não** está aqui é o comportamento de cada projeção: quantos objetos a
estante põe, em que ordem o mural sai, onde a janela de 14 dias corta. Isso é o
que `test_projections.py` e `test_projections_ui.py` fazem, um caso por vez,
porque são regras diferentes umas das outras. Estas são as que são a mesma.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Iterator

import pytest

from cantinho.core.events import Event

from projecoes import NOMES, chamadas, estado, log_de_prova, projecoes_publicas

# ---------------------------------------------------------------- a montagem


@pytest.fixture(scope="module")
def prova() -> tuple[list[Event], datetime]:
    """O log de prova, montado uma vez para o arquivo inteiro.

    Escopo de módulo porque nada aqui escreve nele — é justamente o que estes
    testes provam. `test_a_entrada_nao_e_consumida_nem_alterada` é o que
    garante que compartilhar o log entre os testes é seguro, e ele roda sobre
    a mesma lista que os outros.
    """
    return log_de_prova()


# --------------------------------------------------------------- completude
#
# As duas provas que fazem as outras valerem alguma coisa.


def test_o_registro_cobre_toda_projecao_publica() -> None:
    """Uma projeção nova entra em todas as provas deste arquivo, ou o teste cai.

    É o que impede o problema de origem: a lista escrita à mão que envelhece
    sem avisar. `projections.__all__` é quem manda.
    """
    registradas = set(NOMES)
    publicas = projecoes_publicas()

    assert publicas - registradas == set(), (
        "projeção pública fora do banco de provas: registre em tests/projecoes.py"
    )
    assert registradas - publicas == set(), "registrada e não exportada por __all__"


def test_toda_projecao_fala_no_log_de_prova(prova: tuple[list[Event], datetime]) -> None:
    """Propriedade conferida sobre resultado vazio passa sem provar nada.

    Este é o guarda contra a bateria inteira virar decoração: se o log de prova
    deixar de exercitar uma projeção — um kind que sai, uma data que escorrega
    para outro dia —, é aqui que se descobre, e não no dia em que a propriedade
    deveria ter pegado um defeito.
    """
    eventos, agora = prova
    vazias = [
        nome
        for nome, resultado in estado(eventos, agora).items()
        if not resultado  # lista vazia, dict vazio, 0, 0.0 ou None
    ]
    assert vazias == [], f"o log de prova não faz estas projeções dizerem nada: {vazias}"


# ---------------------------------------------------------------- as provas


@pytest.mark.parametrize("nome", NOMES)
def test_log_vazio_nao_quebra(nome: str, prova: tuple[list[Event], datetime]) -> None:
    """Primeira abertura do app: o log está vazio e a tela tem que montar."""
    _, agora = prova
    chamadas(agora)[nome]([])


@pytest.mark.parametrize("nome", NOMES)
def test_aceita_iterador_esgotavel(nome: str, prova: tuple[list[Event], datetime]) -> None:
    """Quem varre a entrada duas vezes recebe nada na segunda, e mente calado.

    O tipo declarado é `Iterable[Event]`, e um gerador satisfaz o tipo sem
    satisfazer a suposição de quem escreveu duas passadas.
    """
    eventos, agora = prova
    chamada = chamadas(agora)[nome]
    esgotavel: Iterator[Event] = iter(eventos)
    # Comparado com o resultado da lista, e não só "devolveu alguma coisa":
    # quem varre duas vezes acha a segunda vazia e responde um estado pela
    # metade, que é uma resposta plausível e errada.
    assert chamada(esgotavel) == chamada(eventos)


@pytest.mark.parametrize("nome", NOMES)
def test_e_deterministica(nome: str, prova: tuple[list[Event], datetime]) -> None:
    """Mesma entrada, mesmo resultado, quantas vezes for.

    O `_recomputar` do backend reprojeta o log inteiro a cada evento gravado:
    uma projeção que variasse entre chamadas faria a tela mudar sozinha.
    """
    eventos, agora = prova
    chamada = chamadas(agora)[nome]
    referencia = chamada(eventos)
    for _ in range(3):
        assert chamada(eventos) == referencia


@pytest.mark.parametrize("nome", NOMES)
def test_a_ordem_de_chegada_nao_importa(
    nome: str, prova: tuple[list[Event], datetime]
) -> None:
    """O log é ordenado por `(occurred_at, uuid)` dentro da projeção.

    É o que permitiria juntar dois logs sem ordenar nada antes — e o que faz a
    leitura do banco poder mudar de estratégia sem mudar a tela.
    """
    eventos, agora = prova
    chamada = chamadas(agora)[nome]
    embaralhado = list(eventos)
    random.Random(7).shuffle(embaralhado)

    assert embaralhado != eventos, "o embaralhamento não embaralhou nada"
    assert chamada(embaralhado) == chamada(eventos)


@pytest.mark.parametrize("nome", NOMES)
def test_a_entrada_nao_e_consumida_nem_alterada(
    nome: str, prova: tuple[list[Event], datetime]
) -> None:
    """Projeção que mexe na lista que recebeu quebra a seguinte, não a si mesma.

    É o pior tipo de acoplamento: o defeito aparece longe de onde foi causado,
    e depende da ordem em que as projeções foram chamadas.
    """
    eventos, agora = prova
    copia = list(eventos)
    chamadas(agora)[nome](eventos)
    assert eventos == copia


@pytest.mark.parametrize("nome", NOMES)
def test_o_lote_repetido_nao_muda_nada(
    nome: str, prova: tuple[list[Event], datetime]
) -> None:
    """Idempotência de merge, projeção por projeção.

    O mesmo log aplicado duas vezes é o que aconteceria se dois dispositivos
    trocassem tudo o que têm. No banco quem protege é o `INSERT OR IGNORE`; na
    projeção, tem que ser o desenho — chaveado por id de domínio, não contando
    eventos.
    """
    eventos, agora = prova
    chamada = chamadas(agora)[nome]
    assert chamada(list(eventos) + list(eventos)) == chamada(eventos)
