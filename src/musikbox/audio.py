"""Audio playback backend using sounddevice and soundfile.

Uses ALSA directly via PortAudio — no PulseAudio dependency.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import sounddevice as sd
import soundfile as sf

# Number of frames to read per chunk during streaming playback.
_BLOCK_SIZE = 2048


class AudioPlayer:
    """Streams audio files through ALSA via sounddevice."""

    def __init__(self) -> None:
        self._end_callback: Callable[[], None] | None = None
        self._paused = threading.Event()
        self._paused.set()  # starts in "not paused" state
        self._stop_event = threading.Event()
        self._track_ended = threading.Event()
        self._playback_thread: threading.Thread | None = None

    # -- playback controls ---------------------------------------------------

    def play(self, file_path: Path) -> None:
        """Load and play an audio file from the beginning."""
        self.stop()
        self._stop_event.clear()
        self._track_ended.clear()
        self._paused.set()
        self._playback_thread = threading.Thread(
            target=self._stream_file,
            args=(file_path,),
            daemon=True,
        )
        self._playback_thread.start()

    def pause(self) -> None:
        """Pause the currently playing track."""
        self._paused.clear()

    def unpause(self) -> None:
        """Resume a paused track."""
        self._paused.set()

    def stop(self) -> None:
        """Stop playback entirely."""
        self._stop_event.set()
        self._paused.set()  # unblock the thread if it is waiting on pause
        if self._playback_thread is not None:
            self._playback_thread.join(timeout=2.0)
            self._playback_thread = None

    # -- end-of-track callback -----------------------------------------------

    def set_end_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when a track finishes playing."""
        self._end_callback = callback

    def check_events(self) -> None:
        """Fire the end-of-track callback if the last track finished.

        Must be called periodically (e.g. from the main loop).
        """
        if self._track_ended.is_set():
            self._track_ended.clear()
            if self._end_callback is not None:
                self._end_callback()

    # -- internal ------------------------------------------------------------

    def _stream_file(self, file_path: Path) -> None:
        """Worker that streams *file_path* through an ALSA output stream."""
        try:
            with sf.SoundFile(str(file_path)) as f:
                stream = sd.OutputStream(
                    samplerate=f.samplerate,
                    channels=f.channels,
                    dtype="float32",
                )
                stream.start()
                try:
                    while True:
                        self._paused.wait()
                        if self._stop_event.is_set():
                            return
                        data = f.read(_BLOCK_SIZE, dtype="float32")
                        if len(data) == 0:
                            break
                        stream.write(data)
                finally:
                    stream.stop()
                    stream.close()
        except Exception as exc:
            print(f"Audio: playback error: {exc}")
            return

        # Only signal track-end when playback finished naturally.
        if not self._stop_event.is_set():
            self._track_ended.set()
