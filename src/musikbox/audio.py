"""Audio playback backend using pygame.mixer.

Drives pygame.mixer.music for pause/resume without re-opening the audio device.
Sets SDL_VIDEODRIVER=dummy so no display is required on headless systems.

Note: device selection maps to SDL_AUDIODEV; ALSA device strings like
'bluealsa:...' require the SDL ALSA backend and may need SDL_AUDIODRIVER=alsa.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import pygame

_MUSIC_END = pygame.USEREVENT + 1


class AudioPlayer:
    """Drives pygame.mixer.music for audio output."""

    def __init__(self, device: str = "default") -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        if device != "default":
            os.environ["SDL_AUDIODEV"] = device
        pygame.init()
        pygame.mixer.music.set_endevent(_MUSIC_END)
        self._end_callback: Callable[[], None] | None = None
        self._explicit_stop = False

    # -- playback controls ---------------------------------------------------

    def play(self, file_path: Path) -> None:
        """Load and play an audio file, interrupting any current playback."""
        self._explicit_stop = False
        pygame.mixer.music.load(str(file_path))
        pygame.mixer.music.play()
        print(f"Audio: {file_path.name}")

    def pause(self) -> None:
        """Pause the currently playing track."""
        pygame.mixer.music.pause()

    def unpause(self) -> None:
        """Resume a paused track."""
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        """Stop playback entirely."""
        self._explicit_stop = True
        pygame.mixer.music.stop()

    # -- end-of-track callback -----------------------------------------------

    def set_end_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when a track finishes playing."""
        self._end_callback = callback

    def check_events(self) -> None:
        """Fire the end-of-track callback if the last track finished.

        Must be called periodically (e.g. from the main loop).
        """
        for event in pygame.event.get(eventtype=_MUSIC_END):
            if self._explicit_stop:
                self._explicit_stop = False
                continue
            if self._end_callback is not None:
                self._end_callback()
