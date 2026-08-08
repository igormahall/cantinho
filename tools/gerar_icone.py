"""Monta o ícone do app a partir da planta do quarto.

O ícone não é arte nova: é o mesmo vaso que fica no canto da cena. Nos tamanhos
grandes ele aparece sobre um ladrilho quente com a luz do abajur atrás — o
cômodo inteiro reduzido ao que cabe num quadrado. Nos pequenos o ladrilho sai e
a planta ocupa o quadro, porque em 16 px o ladrilho engole tudo.

    python tools/gerar_icone.py

Escreve:
    assets/icon/cantinho.ico   multi-resolução, usado pelo .exe e pelo Windows
    assets/icon/cantinho.png   256 px, para o Linux e para a documentação

O estágio da planta usado é o do meio: o ícone do executável é fixo, então
mostra uma planta claramente formada. Quem cresce junto com o foco é o ícone da
bandeja, que `services/tray.py` regera a cada mudança de estágio.
"""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication, QImage

from cantinho.services import scene

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "assets" / "icon"

# O que o Windows pede na prática: bandeja e lista de detalhes usam 16, a barra
# de tarefas 24 ou 32 conforme a escala, o alt-tab 48, e 256 é o ícone grande
# do Explorer.
TAMANHOS = (16, 24, 32, 48, 64, 128, 256)

# Estágio fixo do ícone do app. Nem broto (irreconhecível), nem o maior
# (folhagem espalhada demais para um quadrado pequeno).
ESTAGIO_IDENTIDADE = 3


def _para_png(imagem: QImage) -> bytes:
    """Serializa em PNG na memória, sem passar por arquivo temporário."""
    dados = QByteArray()
    buffer = QBuffer(dados)
    buffer.open(QIODevice.WriteOnly)
    imagem.save(buffer, "PNG")
    buffer.close()
    return bytes(dados)


def escrever_ico(caminho: Path, imagens: list[QImage]) -> None:
    """Escreve um .ico com vários tamanhos.

    O Qt não tem gravador de ICO, e o formato é simples o bastante para montar
    aqui: um cabeçalho, uma entrada de diretório por tamanho, e os dados. Cada
    quadro vai como PNG, que o Windows aceita desde o Vista e que evita ter de
    montar máscara AND de BMP na mão.
    """
    quadros = [(imagem, _para_png(imagem)) for imagem in imagens]

    # ICONDIR: reservado, tipo 1 (ícone), quantidade.
    cabecalho = struct.pack("<HHH", 0, 1, len(quadros))

    # Cada ICONDIRENTRY tem 16 bytes, e todas vêm antes dos dados.
    deslocamento = len(cabecalho) + 16 * len(quadros)
    diretorio = b""
    for imagem, png in quadros:
        lado = imagem.width()
        diretorio += struct.pack(
            "<BBBBHHII",
            0 if lado >= 256 else lado,  # 0 significa 256
            0 if lado >= 256 else lado,
            0,  # paleta: 0 para cor direta
            0,  # reservado
            1,  # planos
            32,  # bits por pixel
            len(png),
            deslocamento,
        )
        deslocamento += len(png)

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(
        cabecalho + diretorio + b"".join(png for _, png in quadros)
    )


def main() -> int:
    # QGuiApplication é necessária antes de qualquer render de SVG.
    app = QGuiApplication.instance() or QGuiApplication([])

    imagens = [scene.render_icon(ESTAGIO_IDENTIDADE, lado) for lado in TAMANHOS]
    for lado, imagem in zip(TAMANHOS, imagens):
        assert imagem.width() == lado, f"{lado} saiu com {imagem.width()}"

    ico = DESTINO / "cantinho.ico"
    escrever_ico(ico, imagens)
    print(f"  {ico.relative_to(RAIZ)}  {', '.join(str(t) for t in TAMANHOS)} px"
          f"  ({ico.stat().st_size / 1024:.0f} KB)")

    png = DESTINO / "cantinho.png"
    imagens[-1].save(str(png), "PNG")
    print(f"  {png.relative_to(RAIZ)}  256 px ({png.stat().st_size / 1024:.0f} KB)")

    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
