"""Tests for the AudioPlayer wrapper around pygame.mixer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Patch pygame before importing AudioPlayer so it works without pygame installed.
pygame_mock = MagicMock()
with patch.dict("sys.modules", {"pygame": pygame_mock}):
    from musikbox.audio import AudioPlayer


@pytest.fixture()
def player():
    """Create an AudioPlayer with a fully mocked pygame."""
    pygame_mock.reset_mock()
    return AudioPlayer()


class TestInit:
    def test_mixer_init_called(self, player):
        pygame_mock.mixer.init.assert_called_once()

    def test_end_event_registered(self, player):
        pygame_mock.mixer.music.set_endevent.assert_called_once()


class TestPlay:
    def test_loads_and_plays_file(self, player):
        path = Path("/music/Album/track.mp3")
        player.play(path)
        pygame_mock.mixer.music.load.assert_called_once_with(str(path))
        pygame_mock.mixer.music.play.assert_called_once()


class TestPause:
    def test_pauses_playback(self, player):
        player.pause()
        pygame_mock.mixer.music.pause.assert_called_once()


class TestUnpause:
    def test_unpauses_playback(self, player):
        player.unpause()
        pygame_mock.mixer.music.unpause.assert_called_once()


class TestStop:
    def test_stops_playback(self, player):
        player.stop()
        pygame_mock.mixer.music.stop.assert_called_once()


class TestEndCallback:
    def test_callback_fires_on_music_end(self, player):
        callback = MagicMock()
        player.set_end_callback(callback)

        # Simulate a MUSIC_END event
        end_event = MagicMock()
        end_event.type = pygame_mock.USEREVENT.__add__.return_value
        pygame_mock.event.get.return_value = [end_event]

        player.check_events()
        callback.assert_called_once()

    def test_no_callback_no_crash(self, player):
        end_event = MagicMock()
        end_event.type = pygame_mock.USEREVENT.__add__.return_value
        pygame_mock.event.get.return_value = [end_event]

        player.check_events()  # should not raise

    def test_unrelated_events_ignored(self, player):
        callback = MagicMock()
        player.set_end_callback(callback)

        other_event = MagicMock()
        other_event.type = 999
        pygame_mock.event.get.return_value = [other_event]

        player.check_events()
        callback.assert_not_called()
