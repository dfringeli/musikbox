"""Audio playback backend using pygame.mixer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pygame


MUSIC_END = pygame.USEREVENT + 1


class AudioPlayer:
    """Thin wrapper around ``pygame.mixer.music`` for audio playback."""

    def __init__(self) -> None:
        pygame.mixer.init()
        pygame.mixer.music.set_endevent(MUSIC_END)
        self._end_callback: Callable[[], None] | None = None

    def play(self, file_path: Path) -> None:
        """Load and play an audio file from the beginning."""
        pygame.mixer.music.load(str(file_path))
        pygame.mixer.music.play()

    def pause(self) -> None:
        """Pause the currently playing track."""
        pygame.mixer.music.pause()

    def unpause(self) -> None:
        """Resume a paused track."""
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        """Stop playback entirely."""
        pygame.mixer.music.stop()

    def set_end_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when a track finishes playing."""
        self._end_callback = callback

    def check_events(self) -> None:
        """Pump pygame events and fire the end-of-track callback if needed.

        Must be called periodically (e.g. from the CLI loop).
        """
        for event in pygame.event.get():
            if event.type == MUSIC_END and self._end_callback is not None:
                self._end_callback()
