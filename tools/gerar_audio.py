"""Sintetiza os loops de ambiente.

Não é música gerada por IA — não há modelo de áudio disponível aqui, e um
serviço de streaming não serviria a um app que precisa rodar offline em rede
corporativa. Isto é síntese por DSP com a biblioteca padrão: ruído filtrado,
alguns senos e estalo de vinil. Zero dependência nova, e o resultado é
determinístico, então regerar dá byte a byte o mesmo arquivo.

    python tools/gerar_audio.py

Escreve `assets/audio/ambiente_noite.wav` e `ambiente_tarde.wav`, que é
exatamente onde `services/audio.py` procura.

O loop é emendado por crossfade: sintetiza-se um pedaço a mais no fim e
mistura-se com o começo, para que o fim do arquivo desemboque no início sem
estalo audível na volta.
"""

from __future__ import annotations

import array
import math
import random
import wave
from pathlib import Path

TAXA = 22050
DURACAO = 24.0
CROSSFADE = 2.0

# Semente fixa: o arquivo tem que sair igual em qualquer máquina, senão dois
# builds da mesma revisão produzem áudios diferentes.
SEMENTE = 20260808

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "assets" / "audio"


class PassaBaixa:
    """Um polo. Suficiente para tirar o brilho do ruído branco."""

    def __init__(self, corte: float) -> None:
        rc = 1.0 / (2 * math.pi * corte)
        dt = 1.0 / TAXA
        self.a = dt / (rc + dt)
        self.y = 0.0

    def __call__(self, x: float) -> float:
        self.y += self.a * (x - self.y)
        return self.y


def _afinar(frequencia: float, total: int) -> float:
    """Ajusta a frequência para caber um número inteiro de ciclos no loop.

    Sem isso o seno chega no fim do arquivo com a fase quebrada e a emenda
    estala, por mais suave que seja o crossfade.
    """
    ciclos = max(1, round(frequencia * total / TAXA))
    return ciclos * TAXA / total


def _acorde(total: int, parciais, ganho: float) -> list[float]:
    """Camada harmônica bem discreta, com tremolo lento em cada voz."""
    saida = [0.0] * total
    for indice, (frequencia, peso) in enumerate(parciais):
        f = _afinar(frequencia, total)
        # Tremolos com períodos diferentes, para as vozes nunca pulsarem juntas.
        f_lfo = _afinar(0.03 + 0.017 * indice, total)
        for n in range(total):
            t = n / TAXA
            lfo = 0.72 + 0.28 * math.sin(2 * math.pi * f_lfo * t)
            saida[n] += peso * lfo * math.sin(2 * math.pi * f * t)
    return [v * ganho for v in saida]


def _estalo_de_vinil(total: int, rng: random.Random, densidade: float,
                     ganho: float) -> list[float]:
    """Assinatura lo-fi: clique esparso com decaimento curtíssimo."""
    saida = [0.0] * total
    n = 0
    while n < total:
        n += int(rng.expovariate(densidade / TAXA))
        if n >= total:
            break
        amplitude = rng.uniform(0.25, 1.0) * (1 if rng.random() < 0.5 else -1)
        comprimento = rng.randint(int(0.0008 * TAXA), int(0.004 * TAXA))
        for k in range(comprimento):
            if n + k >= total:
                break
            saida[n + k] += amplitude * math.exp(-6.0 * k / comprimento) * rng.uniform(0.6, 1.0)
    return [v * ganho for v in saida]


def _chuva(total: int, rng: random.Random) -> list[float]:
    """Ruído em banda, respirando devagar, com gotas ocasionais."""
    # Dois polos, não um: com 6 dB/oitava sobra chiado acima de 4 kHz e o
    # resultado soa como ruído branco. Chuva atrás do vidro é abafada.
    corpo1 = PassaBaixa(2400)
    corpo2 = PassaBaixa(2400)
    grave = PassaBaixa(160)
    rumor = PassaBaixa(70)
    f_lfo = _afinar(0.055, total)

    saida = [0.0] * total
    for n in range(total):
        branco = rng.uniform(-1.0, 1.0)
        # Passa-alta = sinal menos a passa-baixa. Tira o barro do ruído.
        banda = corpo2(corpo1(branco)) * 2.2 - grave(branco)
        respiro = 0.78 + 0.22 * math.sin(2 * math.pi * f_lfo * n / TAXA)
        saida[n] = banda * respiro * 0.9 + rumor(rng.uniform(-1.0, 1.0)) * 0.55
    return saida


def _pingos(total: int, rng: random.Random) -> list[float]:
    """Gotas soltas batendo no vidro, bem espaçadas."""
    saida = [0.0] * total
    n = 0
    while n < total:
        n += int(rng.expovariate(2.2 / TAXA))
        if n >= total:
            break
        f = rng.uniform(700, 2100)
        comprimento = int(rng.uniform(0.02, 0.06) * TAXA)
        amplitude = rng.uniform(0.05, 0.16)
        for k in range(comprimento):
            if n + k >= total:
                break
            t = k / TAXA
            saida[n + k] += (amplitude * math.exp(-38 * t)
                             * math.sin(2 * math.pi * f * t))
    return saida


def _ar_de_sala(total: int, rng: random.Random) -> list[float]:
    """O quarto por dentro: ruído bem grave, quase inaudível, e um sopro fino."""
    grave = PassaBaixa(110)
    sopro_baixa = PassaBaixa(900)
    sopro_grave = PassaBaixa(300)
    saida = [0.0] * total
    for n in range(total):
        # Grave contido: o ar da sala é presença, não zumbido de subwoofer.
        saida[n] = (grave(rng.uniform(-1.0, 1.0)) * 0.55
                    + (sopro_baixa(rng.uniform(-1.0, 1.0))
                       - sopro_grave(rng.uniform(-1.0, 1.0))) * 0.55)
    return saida


def _misturar(camadas: list[list[float]], total: int) -> list[float]:
    saida = [0.0] * total
    for camada in camadas:
        for n in range(total):
            saida[n] += camada[n]
    return saida


def _emendar(bruto: list[float], total: int, fade: int) -> list[float]:
    """Fecha o loop: mistura a cauda extra sobre o começo."""
    saida = bruto[:total]
    for j in range(fade):
        peso = j / fade
        saida[j] = saida[j] * peso + bruto[total + j] * (1.0 - peso)
    return saida


def _normalizar(amostras: list[float], pico_alvo: float) -> list[float]:
    pico = max(abs(v) for v in amostras) or 1.0
    fator = pico_alvo / pico
    return [v * fator for v in amostras]


def _gravar(caminho: Path, amostras: list[float]) -> None:
    dados = array.array(
        "h", (max(-32768, min(32767, int(v * 32767))) for v in amostras)
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(dados.tobytes())


def _construir(tema: str) -> list[float]:
    total = int(DURACAO * TAXA)
    fade = int(CROSSFADE * TAXA)
    bruto = total + fade
    # Semente derivada do tema: os dois arquivos não podem sair idênticos.
    rng = random.Random(SEMENTE + sum(ord(c) for c in tema))

    if tema == "noite":
        # Lá menor com nona: fechado, sem brilho, combina com abajur e chuva.
        acorde = [(110.0, 0.34), (164.81, 0.20), (261.63, 0.15),
                  (329.63, 0.11), (493.88, 0.06)]
        camadas = [
            _chuva(bruto, rng),
            _pingos(bruto, rng),
            _acorde(bruto, acorde, 0.16),
            _estalo_de_vinil(bruto, rng, densidade=7.0, ganho=0.05),
        ]
    else:
        # Fá maior com sétima: mais aberto, luz de fim de tarde.
        acorde = [(87.31, 0.32), (174.61, 0.20), (261.63, 0.16),
                  (349.23, 0.12), (440.0, 0.07)]
        camadas = [
            _ar_de_sala(bruto, rng),
            _acorde(bruto, acorde, 0.30),
            _estalo_de_vinil(bruto, rng, densidade=3.5, ganho=0.035),
        ]

    misturado = _misturar(camadas, bruto)
    # Pico baixo de propósito: é som de fundo. Quem quiser mais sobe o volume.
    return _normalizar(_emendar(misturado, total, fade), 0.42)


# --------------------------------------------------------- reações de mouse
#
# Os três sons curtos de interface. A regra que os une: nada de ataque seco.
# Todos entram com uma rampa de alguns milissegundos, porque começar em zero e
# saltar para o pico é exatamente o que faz um som de UI soar como bipe de
# eletrodoméstico. Ninguém repara no ataque; só repara em não incomodar.


def _envelope(k: int, comprimento: int, ataque: int, decaimento: float) -> float:
    subida = min(1.0, k / ataque) if ataque else 1.0
    return subida * math.exp(-decaimento * k / comprimento)


def _toque(rng: random.Random) -> list[float]:
    """Mouse passando por cima: quase só ar, com um fundo grave curtíssimo."""
    comprimento = int(0.055 * TAXA)
    ataque = int(0.004 * TAXA)
    filtro = PassaBaixa(1500)
    saida = []
    for k in range(comprimento):
        t = k / TAXA
        ar = filtro(rng.uniform(-1.0, 1.0)) * 0.9
        corpo = math.sin(2 * math.pi * 320 * t) * 0.35
        saida.append((ar + corpo) * _envelope(k, comprimento, ataque, 7.0))
    return saida


def _clique(rng: random.Random) -> list[float]:
    """Clique: madeira batendo em madeira, não plástico.

    Duas parciais em intervalo não harmônico e um sopro de ruído por cima. Uma
    parcial sozinha sai afinada demais e vira nota musical no meio da tela.
    """
    comprimento = int(0.085 * TAXA)
    ataque = int(0.002 * TAXA)
    filtro = PassaBaixa(3200)
    saida = []
    for k in range(comprimento):
        t = k / TAXA
        corpo = (math.sin(2 * math.pi * 430 * t) * 0.55
                 + math.sin(2 * math.pi * 651 * t) * 0.30)
        batida = filtro(rng.uniform(-1.0, 1.0)) * math.exp(-90 * t) * 0.7
        saida.append((corpo + batida) * _envelope(k, comprimento, ataque, 9.0))
    return saida


def _entrega() -> list[float]:
    """Tarefa concluída: o único som que pode soar como recompensa.

    Uma terça maior com a quinta em cima, decaindo devagar. O corte é longo o
    bastante para respirar e curto o bastante para não virar jingle.
    """
    comprimento = int(0.9 * TAXA)
    ataque = int(0.010 * TAXA)
    parciais = ((523.25, 0.50, 3.2), (659.25, 0.34, 4.0), (783.99, 0.22, 5.2))
    saida = []
    for k in range(comprimento):
        t = k / TAXA
        valor = 0.0
        for frequencia, peso, decaimento in parciais:
            valor += peso * math.sin(2 * math.pi * frequencia * t) * math.exp(
                -decaimento * t
            )
        saida.append(valor * _envelope(k, comprimento, ataque, 0.4))
    return saida


def _apagar_fim(amostras: list[float], quadros: int) -> list[float]:
    """Zera os últimos quadros.

    `QSoundEffect` toca o arquivo até o último quadro e corta. Se o sinal ainda
    tiver amplitude ali, o corte é um estalo — o mesmo problema da emenda do
    loop, na outra ponta.
    """
    saida = list(amostras)
    for j in range(min(quadros, len(saida))):
        indice = len(saida) - 1 - j
        saida[indice] *= j / quadros
    return saida


def _conferir(nome: str, amostras: list[float]) -> None:
    quadros = len(amostras)
    rms = math.sqrt(sum(v * v for v in amostras) / quadros)
    # A emenda do loop: a diferença entre o último e o primeiro quadro tem que
    # ser da ordem do próprio sinal, não um degrau.
    degrau = abs(amostras[-1] - amostras[0])
    print(
        f"  {nome:6} {quadros / TAXA:.1f}s  pico={max(abs(v) for v in amostras):.3f}"
        f"  rms={rms:.4f}  emenda={degrau:.4f}"
    )
    if degrau > 6 * rms:
        print(f"  AVISO: a volta do loop pode estalar em {nome}")


def _construir_reacoes() -> dict[str, list[float]]:
    """Os três sons de interação, com pico bem abaixo do ambiente.

    Cada um tem semente própria e derivada da fixa: mexer num não pode mudar o
    ruído dos outros.
    """
    corte = int(0.006 * TAXA)
    return {
        "toque": _apagar_fim(
            _normalizar(_toque(random.Random(SEMENTE + 1)), 0.30), corte
        ),
        "clique": _apagar_fim(
            _normalizar(_clique(random.Random(SEMENTE + 2)), 0.55), corte
        ),
        "entrega": _apagar_fim(_normalizar(_entrega(), 0.62), corte),
    }


def main() -> int:
    print(f"sintetizando {DURACAO:.0f}s a {TAXA} Hz, mono 16 bits")
    for tema in ("noite", "tarde"):
        amostras = _construir(tema)
        _conferir(tema, amostras)
        caminho = DESTINO / f"ambiente_{tema}.wav"
        _gravar(caminho, amostras)
        print(f"  -> {caminho.relative_to(RAIZ)} "
              f"({caminho.stat().st_size / 1024:.0f} KB)")

    print("reações de interface")
    for nome, amostras in _construir_reacoes().items():
        caminho = DESTINO / f"ui_{nome}.wav"
        _gravar(caminho, amostras)
        print(f"  {nome:8} {len(amostras) / TAXA * 1000:.0f} ms"
              f"  pico={max(abs(v) for v in amostras):.2f}"
              f"  -> {caminho.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
