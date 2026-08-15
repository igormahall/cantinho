"""Roda o qmllint sobre a UI, com o import path certo.

Existe por causa do import path, e não é detalhe: sem `-I cantinho/ui` o
`theme` não resolve, o `Theme` vira tipo desconhecido e o relatório enche de
"Unqualified access" que só existem porque a ferramenta foi mal chamada. Uma
auditoria deste projeto reportou 569 avisos assim — com o caminho certo eram
313, e todos do `backend`, que é context property e o qmllint nunca vai
conhecer. Os que sobraram depois de `.qmllint.ini` desligar essa categoria
foram 2, e os 2 eram defeito de verdade.

Ou seja: chamar errado não deixa a ferramenta rigorosa, deixa ela inútil.

O que ele **não** cobre é o comportamento — para isso é `tools/simular_uso.py`,
que clica de verdade. Este aqui é análise estática, e pega o que uma execução
feliz não pega: propriedade que não existe no tipo, sinal com parâmetro errado,
`import` que não resolve.
"""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
UI = RAIZ / "cantinho" / "ui"


def qmllint() -> Path:
    """O qmllint do venv, ao lado do Python que está rodando.

    Pelo `sys.executable` e não pelo PATH: o PATH pode ter o Python do sistema,
    que não tem PySide6 — é a mesma armadilha que faz `python tools/x.py`
    falhar quando não se usa o Python do venv.
    """
    binario = Path(sys.executable).parent
    for nome in ("pyside6-qmllint", "pyside6-qmllint.exe"):
        caminho = binario / nome
        if caminho.exists():
            return caminho
    raise SystemExit(
        "pyside6-qmllint não encontrado ao lado de "
        f"{sys.executable}. Rode com o Python do venv."
    )


def main() -> int:
    arquivos = sorted(UI.rglob("*.qml"))
    if not arquivos:
        raise SystemExit(f"nenhum .qml em {UI}")

    comando = [
        str(qmllint()),
        "-I",
        str(UI),
        *(str(caminho) for caminho in arquivos),
    ]
    print(f"qmllint em {len(arquivos)} arquivos de {UI.relative_to(RAIZ)}\n")
    # O qmllint escreve os avisos no stderr e não usa o código de saída para
    # distinguir "limpo" de "tem aviso" de forma confiável entre versões, então
    # quem decide é a saída.
    resultado = subprocess.run(comando, capture_output=True, text=True, cwd=RAIZ)
    saida = (resultado.stdout + resultado.stderr).strip()

    if not saida:
        print("limpo.")
        return 0

    print(saida)
    avisos = sum(1 for linha in saida.splitlines() if linha.startswith("Warning:"))
    erros = sum(1 for linha in saida.splitlines() if linha.startswith("Error:"))
    print(f"\n{avisos} aviso(s), {erros} erro(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
