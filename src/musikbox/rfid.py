"""RFID tag reader with background polling thread.

Uses the pirc522 library to read MFRC522 RFID tags on a Raspberry Pi.
Detected UIDs are delivered to a callback as uppercase hex strings.
"""

from __future__ import annotations

import threading
import time
from typing import Callable


def uid_to_hex(uid: list[int]) -> str:
    """Convert a UID byte list to an uppercase hex string.

    Example: ``[147, 85, 167, 43, 181]`` → ``"9355A72BB5"``
    """
    return "".join(f"{byte:02X}" for byte in uid)


class RfidReader:
    """Polls an MFRC522 reader in a background thread.

    Parameters
    ----------
    on_tag:
        Called with the UID hex string whenever a *new* tag is detected.
    cooldown:
        Minimum seconds before the same UID triggers the callback again.
    pin_rst:
        RST pin for the MFRC522 reader (default 22).
    poll_interval:
        Seconds between poll attempts (default 0.5).
    """

    def __init__(
        self,
        on_tag: Callable[[str], None],
        *,
        cooldown: float = 3.0,
        pin_rst: int = 22,
        poll_interval: float = 0.5,
    ) -> None:
        self._on_tag = on_tag
        self._cooldown = cooldown
        self._pin_rst = pin_rst
        self._poll_interval = poll_interval
        self._last_uid: str | None = None
        self._last_time: float = 0.0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background polling thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the polling thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _poll_loop(self) -> None:
        from pirc522 import RFID

        rdr = RFID(pin_rst=self._pin_rst, pin_irq=None)
        try:
            while not self._stop_event.is_set():
                (error, _tag_type) = rdr.request()
                if not error:
                    (error, uid) = rdr.anticoll()
                    if not error:
                        hex_uid = uid_to_hex(uid)
                        now = time.monotonic()
                        if (
                            hex_uid != self._last_uid
                            or now - self._last_time >= self._cooldown
                        ):
                            self._last_uid = hex_uid
                            self._last_time = now
                            self._on_tag(hex_uid)
                self._stop_event.wait(self._poll_interval)
        finally:
            rdr.cleanup()
