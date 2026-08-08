"""Argumentos de linha de comando e trava de instância.

Os dois bugs que motivaram estes testes aparecem juntos e são invisíveis: o app
abre, funciona, e grava no banco errado — ou duas cópias gravam no mesmo banco
sem uma saber da outra.
"""

from __future__ import annotations

from pathlib import Path

from cantinho import main
from cantinho.services.single_instance import _nome_para


# ------------------------------------------------------------------ caminhos


def test_til_vira_a_pasta_do_usuario() -> None:
    """O PowerShell não expande `~` para executável nativo.

    Sem `expanduser`, `--db ~/teste/x.db` cria uma pasta chamada `~` dentro do
    diretório atual e o app abre num banco vazio, sem erro nenhum.
    """
    resolvido = main._caminho("~/cantinho-teste/teste.db")
    assert "~" not in resolvido.parts
    assert resolvido.is_absolute()
    assert resolvido == Path.home() / "cantinho-teste" / "teste.db"


def test_caminho_comum_passa_intacto(tmp_path: Path) -> None:
    alvo = tmp_path / "banco.db"
    assert main._caminho(str(alvo)) == alvo


# --------------------------------------------------------- trava de instância


def test_bancos_diferentes_travam_separado(tmp_path: Path) -> None:
    """`--db` existe para testar sem sujar o banco real.

    Travar por máquina proibiria abrir o app de teste com o de verdade rodando
    na bandeja, que é exatamente o fluxo de quem está mexendo no projeto.
    """
    assert _nome_para(tmp_path / "a.db") != _nome_para(tmp_path / "b.db")


def test_o_mesmo_banco_da_o_mesmo_nome(tmp_path: Path) -> None:
    banco = tmp_path / "sub" / ".." / "cantinho.db"
    assert _nome_para(banco) == _nome_para(tmp_path / "cantinho.db")


def test_nome_serve_como_named_pipe(tmp_path: Path) -> None:
    """Nome de pipe do Windows não aceita barra e tem limite de tamanho."""
    nome = _nome_para(tmp_path / "cantinho.db")
    assert "/" not in nome and "\\" not in nome
    assert 0 < len(nome) < 64
