"""Som: o loop de ambiente e as reações curtas de interface.

Tudo é arquivo local em `assets/audio/`, gerado por `tools/gerar_audio.py` e
versionado pronto. Ausência de arquivo nunca é erro: o serviço nasce
funcionando e silencioso, e um clone sem os wavs roda mudo sem reclamar em
runtime.

Nomes procurados (qualquer extensão de `EXTENSOES`):

    ambiente_noite.*   loop do tema noite (chuva)
    ambiente_tarde.*   loop do tema fim de tarde
    ambiente.*         usado quando não existe um específico do tema
    ui_toque.*         mouse passando por cima
    ui_clique.*        clique
    ui_entrega.*       tarefa concluída
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect

from cantinho.services import scene

logger = logging.getLogger(__name__)

__all__ = ["Ambience", "Sfx"]

EXTENSOES = (".ogg", ".wav", ".mp3", ".m4a")
VOLUME_PADRAO = 0.35


def _find(nomes: tuple[str, ...]) -> Path | None:
    pasta = scene.assets_dir() / "audio"
    if not pasta.is_dir():
        return None
    for nome in nomes:
        for extensao in EXTENSOES:
            caminho = pasta / f"{nome}{extensao}"
            if caminho.is_file():
                return caminho
    return None


class Ambience(QObject):
    """Loop de fundo, trocado junto com o tema."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._output = QAudioOutput(self)
        self._output.setVolume(VOLUME_PADRAO)
        self._player.setAudioOutput(self._output)
        self._player.setLoops(QMediaPlayer.Infinite)
        self._atual: Path | None = None
        self._mudo = False

    @property
    def playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def set_theme(self, theme: str) -> None:
        caminho = _find((f"ambiente_{theme}", "ambiente"))
        if caminho is None:
            if self._atual is not None:
                self._player.stop()
                self._atual = None
            logger.debug("sem áudio para o tema %s", theme)
            return
        if caminho == self._atual:
            return
        self._atual = caminho
        self._player.setSource(QUrl.fromLocalFile(str(caminho)))
        if not self._mudo:
            self._player.play()

    def set_muted(self, mudo: bool) -> None:
        self._mudo = mudo
        self._output.setMuted(mudo)
        if mudo:
            self._player.pause()
        elif self._atual is not None:
            self._player.play()

    def set_volume(self, volume: float) -> None:
        self._output.setVolume(max(0.0, min(1.0, volume)))

    def stop(self) -> None:
        self._player.stop()


# Reações de interface. Volumes bem separados de propósito: passar o mouse tem
# que ficar no limite do perceptível, senão vira barulho; concluir uma tarefa é
# o único momento que pode soar como recompensa.
SFX_VOLUMES: dict[str, float] = {
    "toque": 0.10,
    "clique": 0.26,
    "entrega": 0.38,
}

# Intervalo mínimo entre dois toques. Sem isso, arrastar o mouse por uma fileira
# de botões dispara uma metralhadora de cliques.
SFX_INTERVALO = 0.075


class Sfx(QObject):
    """Sons curtos de interação.

    `QSoundEffect` e não `QMediaPlayer`: o efeito fica decodificado em memória e
    dispara na hora. O player de mídia leva dezenas de milissegundos para
    começar, o que num retorno de clique é atraso audível.

    Sem arquivo em `assets/audio/`, cada nome vira um no-op silencioso — igual
    ao ambiente, o serviço nasce funcionando e mudo.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mudo = False
        self._ultimo = 0.0
        self._efeitos: dict[str, QSoundEffect] = {}
        for nome, volume in SFX_VOLUMES.items():
            caminho = _find((f"ui_{nome}",))
            if caminho is None:
                logger.debug("sem som de interface para %s", nome)
                continue
            efeito = QSoundEffect(self)
            efeito.setSource(QUrl.fromLocalFile(str(caminho)))
            efeito.setVolume(volume)
            self._efeitos[nome] = efeito

    def set_muted(self, mudo: bool) -> None:
        self._mudo = bool(mudo)

    def play(self, nome: str) -> None:
        if self._mudo:
            return
        efeito = self._efeitos.get(nome)
        if efeito is None:
            return
        agora = time.monotonic()
        if agora - self._ultimo < SFX_INTERVALO:
            return
        self._ultimo = agora
        efeito.play()
