"""Tests for the AudioPlayer wrapper around sounddevice/soundfile."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Patch sounddevice and soundfile before importing AudioPlayer so the tests
# work without the native libraries installed.
sd_mock = MagicMock()
sf_mock = MagicMock()
with patch.dict("sys.modules", {"sounddevice": sd_mock, "soundfile": sf_mock}):
    from musikbox.audio import AudioPlayer


@pytest.fixture()
def player():
    """Create an AudioPlayer with fully mocked backends."""
    sd_mock.reset_mock()
    sf_mock.reset_mock()
    return AudioPlayer()


class TestPlay:
    def test_opens_file_and_starts_stream(self, player):
        path = Path("/music/Album/track.mp3")

        # Set up the soundfile context-manager mock
        fake_sf = MagicMock()
        fake_sf.samplerate = 44100
        fake_sf.channels = 2
        # First read returns data, second returns empty (end of file)
        fake_sf.read.side_effect = [MagicMock(__len__=lambda s: 2048), MagicMock(__len__=lambda s: 0)]
        sf_mock.SoundFile.return_value.__enter__ = MagicMock(return_value=fake_sf)
        sf_mock.SoundFile.return_value.__exit__ = MagicMock(return_value=False)

        fake_stream = MagicMock()
        sd_mock.OutputStream.return_value = fake_stream

        player.play(path)
        # Give the playback thread a moment to run
        import time
        time.sleep(0.1)

        sf_mock.SoundFile.assert_called_with(str(path))

    def test_stop_before_new_play(self, player):
        """Calling play() again stops the previous playback first."""
        # The internal stop_event should be set then cleared
        player.play(Path("/a.mp3"))
        player.play(Path("/b.mp3"))
        # Should not raise — previous thread is joined


class TestPause:
    def test_pause_clears_event(self, player):
        player.pause()
        assert not player._paused.is_set()

    def test_unpause_sets_event(self, player):
        player.pause()
        player.unpause()
        assert player._paused.is_set()


class TestStop:
    def test_stop_sets_event(self, player):
        player.stop()
        assert player._stop_event.is_set()

    def test_stop_unblocks_paused_thread(self, player):
        player.pause()
        player.stop()
        # _paused must be set so the thread can wake up and exit
        assert player._paused.is_set()


class TestEndCallback:
    def test_callback_fires_via_check_events(self, player):
        callback = MagicMock()
        player.set_end_callback(callback)

        # Simulate the playback thread signalling track-end
        player._track_ended.set()
        player.check_events()

        callback.assert_called_once()

    def test_track_ended_flag_cleared_after_check(self, player):
        player._track_ended.set()
        player.check_events()
        assert not player._track_ended.is_set()

    def test_no_callback_no_crash(self, player):
        player._track_ended.set()
        player.check_events()  # should not raise

    def test_check_events_noop_when_no_track_ended(self, player):
        callback = MagicMock()
        player.set_end_callback(callback)
        player.check_events()
        callback.assert_not_called()
