"""Medir uma imagem de uma passada só, em vez de varrê-la a cada pergunta.

O quarto e o ícone são desenho: o que se testa neles é onde a tinta caiu, se
ela caiu, e quanto dela é verde. Cada teste fazia a sua própria varredura com
`pixelColor` em laço aninhado — a mesma varredura escrita seis vezes, cada uma
com o seu limiar de alfa e o seu passo de amostragem.

Duas consequências, e a segunda é a que importa:

- **Custo.** `pixelColor` é uma chamada Python→C++ por pixel. Varrer 128x128
  cinco vezes, em dois testes, é meio milhão de chamadas para responder duas
  perguntas.
- **Amostragem.** Para não ficar caro, as varreduras pulavam de dois em dois ou
  de quatro em quatro pixels — então "não desenhou nada" queria dizer "não
  desenhou nada nos pixels pares". Um objeto de um pixel de largura passava
  despercebido.

`medir()` resolve os dois: percorre o alfa **inteiro** com operações de bytes,
que rodam em C, e devolve de uma vez tudo o que os testes perguntam. As contas
que exigem olhar cor por cor (`verdes`, `tons`) ficam separadas, porque só valem
para o ícone e só em tamanho pequeno.
"""

from __future__ import annotations

from dataclasses import dataclass

# Um pixel "opaco" — o que aparece em qualquer fundo, claro ou escuro.
OPACO = 200


@dataclass(frozen=True)
class Medida:
    """O que uma imagem tem a dizer sobre onde desenhou.

    `caixa` é `(x_min, y_min, x_max, y_max)` dos pixels acima do limiar, ou
    `None` quando não há nenhum — a diferença entre "desenhou ali" e "não
    desenhou".
    """

    largura: int
    altura: int
    visiveis: int
    caixa: tuple[int, int, int, int] | None
    base_opaca: int

    @property
    def desenhou(self) -> bool:
        return self.visiveis > 0

    @property
    def cobertura(self) -> float:
        return self.visiveis / (self.largura * self.altura)

    def fracao_da_largura(self) -> float:
        if self.caixa is None:
            return 0.0
        return (self.caixa[2] - self.caixa[0] + 1) / self.largura

    def fracao_da_altura(self) -> float:
        if self.caixa is None:
            return 0.0
        return (self.caixa[3] - self.caixa[1] + 1) / self.altura


def _rgba(imagem):
    """Os bytes da imagem em RGBA8888, sem enchimento de linha.

    O formato é fixado aqui para o resto do módulo poder fatiar por índice.
    Em RGBA8888 a linha já é múltiplo de 4 bytes, então não há padding — mas a
    conta é conferida, porque um dia pode não ser.
    """
    from PySide6.QtGui import QImage

    convertida = imagem.convertToFormat(QImage.Format.Format_RGBA8888)
    largura, altura = convertida.width(), convertida.height()
    assert convertida.bytesPerLine() == largura * 4, "linha com enchimento"
    return bytes(convertida.constBits()), largura, altura


def _tabela(limiar: int) -> bytes:
    """Tradução de alfa para 0/1, para as contas rodarem dentro do C."""
    return bytes(0 if valor <= limiar else 1 for valor in range(256))


def medir(imagem, limiar: int = 8) -> Medida:
    """Percorre o alfa inteiro e devolve onde a imagem desenhou.

    `limiar` é o alfa acima do qual o pixel conta como desenhado. Cada teste
    tem o seu: 8 para "tem alguma coisa aí", 40 para a silhueta do ícone, 30
    para a folhagem da planta contra a cena.
    """
    dados, largura, altura = _rgba(imagem)
    alfas = dados[3::4]
    visivel = _tabela(limiar)
    opaco = _tabela(OPACO)

    visiveis = 0
    x_min = largura
    x_max = -1
    y_min = -1
    y_max = -1
    base_opaca = -1

    for y in range(altura):
        linha = alfas[y * largura : (y + 1) * largura]

        marcada = linha.translate(visivel)
        primeiro = marcada.find(1)
        if primeiro >= 0:
            visiveis += marcada.count(1)
            ultimo = marcada.rfind(1)
            x_min = min(x_min, primeiro)
            x_max = max(x_max, ultimo)
            y_max = y
            if y_min < 0:
                y_min = y

        # A varredura vai de cima para baixo, então a última linha com pixel
        # opaco é o pé do desenho — a base do vaso, no caso do ícone.
        if 1 in linha.translate(opaco):
            base_opaca = y

    caixa = None if x_max < 0 else (x_min, y_min, x_max, y_max)
    return Medida(
        largura=largura,
        altura=altura,
        visiveis=visiveis,
        caixa=caixa,
        base_opaca=base_opaca,
    )


def verdes(imagem, limiar_alfa: int = 128) -> int:
    """Pixels em que o verde domina — a folhagem, e só ela.

    Aqui não dá para escapar de olhar cor por cor: a pergunta compara canais do
    mesmo pixel. Vale porque só é feita no ícone, que é pequeno.
    """
    dados, largura, altura = _rgba(imagem)
    total = 0
    for base in range(0, largura * altura * 4, 4):
        if dados[base + 3] <= limiar_alfa:
            continue
        vermelho, verde, azul = dados[base], dados[base + 1], dados[base + 2]
        if verde > vermelho and verde > azul:
            total += 1
    return total


def tons(imagem) -> tuple[int, int]:
    """Quantos pixels opacos são claros e quantos são escuros.

    A luminosidade é a do HSL, que é a mesma conta do `QColor.lightness()`:
    a média entre o canal mais alto e o mais baixo. É o que responde se o
    desenho aparece numa barra clara **e** numa escura.
    """
    dados, largura, altura = _rgba(imagem)
    claros = escuros = 0
    for base in range(0, largura * altura * 4, 4):
        if dados[base + 3] <= OPACO:
            continue
        canais = (dados[base], dados[base + 1], dados[base + 2])
        luz = (max(canais) + min(canais)) // 2
        if luz > 140:
            claros += 1
        elif luz < 90:
            escuros += 1
    return claros, escuros
