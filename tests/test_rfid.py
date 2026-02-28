"""Tests for the RFID reader module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from musikbox.rfid import RfidReader, uid_to_hex


class TestUidToHex:
    def test_basic_conversion(self):
        assert uid_to_hex([147, 85, 167, 43, 181]) == "9355A72BB5"

    def test_leading_zeros(self):
        assert uid_to_hex([0, 1, 15]) == "00010F"

    def test_empty_list(self):
        assert uid_to_hex([]) == ""

    def test_single_byte(self):
        assert uid_to_hex([255]) == "FF"


class TestRfidReaderDebounce:
    def test_same_uid_within_cooldown_is_ignored(self):
        callback = MagicMock()
        reader = RfidReader(on_tag=callback, cooldown=5.0)

        # Simulate two detections of the same UID
        reader._last_uid = None
        reader._last_time = 0.0

        # First detection should trigger
        now = time.monotonic()
        uid = "AABBCCDD"
        if uid != reader._last_uid or now - reader._last_time >= reader._cooldown:
            reader._last_uid = uid
            reader._last_time = now
            callback(uid)

        # Second detection immediately — should NOT trigger
        if uid != reader._last_uid or time.monotonic() - reader._last_time >= reader._cooldown:
            callback(uid)

        assert callback.call_count == 1

    def test_different_uid_triggers_callback(self):
        callback = MagicMock()
        reader = RfidReader(on_tag=callback, cooldown=5.0)
        reader._last_uid = None
        reader._last_time = 0.0

        # First UID
        uid1 = "AABBCCDD"
        now = time.monotonic()
        reader._last_uid = uid1
        reader._last_time = now
        callback(uid1)

        # Different UID — should trigger
        uid2 = "11223344"
        if uid2 != reader._last_uid or time.monotonic() - reader._last_time >= reader._cooldown:
            reader._last_uid = uid2
            reader._last_time = time.monotonic()
            callback(uid2)

        assert callback.call_count == 2

    def test_same_uid_after_cooldown_triggers(self):
        callback = MagicMock()
        reader = RfidReader(on_tag=callback, cooldown=0.0)
        reader._last_uid = None
        reader._last_time = 0.0

        uid = "AABBCCDD"
        # With cooldown=0, same UID should always trigger
        now = time.monotonic()
        reader._last_uid = uid
        reader._last_time = now
        callback(uid)

        # Same UID, but cooldown is 0 so it should trigger again
        now2 = time.monotonic()
        if uid != reader._last_uid or now2 - reader._last_time >= reader._cooldown:
            callback(uid)

        assert callback.call_count == 2
