"""Audio playback backend using pygame.mixer.

Drives pygame.mixer.music for pause/resume without re-opening the audio device.
Audio device selection is handled via ALSA configuration (e.g. /etc/asound.conf).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import pygame


class AudioPlayer:
    """Drives pygame.mixer.music for audio output."""

    def __init__(self) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        self._mixer_ready = False
        self._playing = False
        self._paused = False
        self._end_callback: Callable[[], None] | None = None
        self._explicit_stop = False

    def _ensure_mixer(self) -> None:
        """Initialise the mixer on first use (lazy)."""
        if self._mixer_ready:
            return
        pygame.mixer.init()
        self._mixer_ready = True

    # -- playback controls ---------------------------------------------------

    def play(self, file_path: Path) -> None:
        """Load and play an audio file, interrupting any current playback."""
        self._ensure_mixer()
        self._explicit_stop = False
        self._paused = False
        pygame.mixer.music.load(str(file_path))
        pygame.mixer.music.play()
        self._playing = True
        print(f"Audio: {file_path.name}")

    def pause(self) -> None:
        """Pause the currently playing track."""
        pygame.mixer.music.pause()
        self._paused = True

    def unpause(self) -> None:
        """Resume a paused track."""
        pygame.mixer.music.unpause()
        self._paused = False

    def stop(self) -> None:
        """Stop playback entirely."""
        self._explicit_stop = True
        self._playing = False
        self._paused = False
        pygame.mixer.music.stop()

    # -- end-of-track callback -----------------------------------------------

    def set_end_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when a track finishes playing."""
        self._end_callback = callback

    def check_events(self) -> None:
        """Fire the end-of-track callback if the last track finished.

        Must be called periodically (e.g. from the main loop).
        """
        if not self._playing or self._paused:
            return
        if not pygame.mixer.music.get_busy():
            self._playing = False
            if self._explicit_stop:
                self._explicit_stop = False
                return
            if self._end_callback is not None:
                self._end_callback()
