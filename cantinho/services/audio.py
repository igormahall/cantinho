"""Som ambiente.

Toca um arquivo local em loop, se existir um. O projeto não versiona áudio, e
adicionar binário grande ao repositório é decisão que não me cabe tomar
sozinho — então o serviço nasce funcionando e silencioso: sem arquivo em
`assets/audio/`, ele simplesmente não toca e não reclama em runtime.

Para ligar o som, basta soltar um `.wav`, `.mp3` ou `.ogg` em `assets/audio/`
com um destes nomes:

    ambiente_noite.*   toca no tema noite (chuva, por exemplo)
    ambiente_tarde.*   toca no tema fim de tarde
    ambiente.*         usado quando não existe um específico do tema
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from cantinho.services import scene

logger = logging.getLogger(__name__)

__all__ = ["Ambience"]

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
