"""Audio playback backend using mpg123 via ALSA.

Drives mpg123 in remote-control mode so pause/resume work without
re-opening the audio device.  Works with any ALSA device string,
including BlueALSA virtual devices.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Callable


class AudioPlayer:
    """Drives mpg123 in remote-control mode for ALSA/BlueALSA output."""

    def __init__(self, device: str = "default") -> None:
        self._device = device
        self._end_callback: Callable[[], None] | None = None
        self._track_ended = threading.Event()
        self._paused = False
        self._explicit_stop = False
        self._lock = threading.Lock()
        self._process = self._start_mpg123()
        self._monitor_thread = threading.Thread(
            target=self._monitor_output, daemon=True
        )
        self._monitor_thread.start()

    # -- internal ------------------------------------------------------------

    def _start_mpg123(self) -> subprocess.Popen:
        cmd = ["mpg123", "--remote", "--quiet"]
        if self._device != "default":
            cmd += ["--audiodevice", self._device]
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def _send(self, cmd: str) -> None:
        try:
            if self._process.stdin:
                self._process.stdin.write(cmd + "\n")
                self._process.stdin.flush()
        except BrokenPipeError:
            pass

    def _monitor_output(self) -> None:
        """Read mpg123 status lines; detect natural track end via '@P 0'."""
        for line in self._process.stdout:
            if line.strip() == "@P 0":
                with self._lock:
                    if self._explicit_stop:
                        self._explicit_stop = False
                        continue
                self._track_ended.set()

    # -- playback controls ---------------------------------------------------

    def play(self, file_path: Path) -> None:
        """Load and play an audio file, interrupting any current playback."""
        with self._lock:
            self._paused = False
        self._track_ended.clear()
        self._send(f"LOAD {file_path}")
        print(f"Audio: {file_path.name}")

    def pause(self) -> None:
        """Pause the currently playing track."""
        with self._lock:
            if not self._paused:
                self._send("PAUSE")
                self._paused = True

    def unpause(self) -> None:
        """Resume a paused track."""
        with self._lock:
            if self._paused:
                self._send("PAUSE")
                self._paused = False

    def stop(self) -> None:
        """Stop playback entirely."""
        with self._lock:
            self._explicit_stop = True
            self._paused = False
        self._send("STOP")

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
