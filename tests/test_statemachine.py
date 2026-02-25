"""Tests for the music player state machine."""

from __future__ import annotations

import pytest

from musikbox.library import MusicLibrary
from musikbox.statemachine import InvalidTransitionError, MusicPlayerStateMachine, State


# ---------------------------------------------------------------------------
# Fixture: in-memory library backed by a temporary directory
# ---------------------------------------------------------------------------

@pytest.fixture()
def music_dir(tmp_path):
    """Create a small fake music library on disk."""
    album_a = tmp_path / "Album A"
    album_a.mkdir()
    (album_a / "01 - First.mp3").touch()
    (album_a / "02 - Second.mp3").touch()
    (album_a / "03 - Third.mp3").touch()

    album_b = tmp_path / "Album B"
    album_b.mkdir()
    (album_b / "track1.flac").touch()
    (album_b / "track2.flac").touch()

    return tmp_path


@pytest.fixture()
def library(music_dir):
    return MusicLibrary(music_dir)


@pytest.fixture()
def player(library):
    return MusicPlayerStateMachine(library)


# ---------------------------------------------------------------------------
# Initial state (starts in PAUSED, no album loaded)
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_starts_in_paused(self, player):
        assert player.state is State.PAUSED

    def test_no_album(self, player):
        assert player.current_album is None

    def test_no_title(self, player):
        assert player.current_title is None


# ---------------------------------------------------------------------------
# Transitions from PAUSED without album loaded
# ---------------------------------------------------------------------------

class TestFromPausedNoAlbum:
    def test_play_album_transitions_to_playing(self, player):
        player.play("Album A")
        assert player.state is State.PLAYING
        assert player.current_album == "Album A"
        assert player.current_title == "01 - First.mp3"

    def test_play_without_album_raises(self, player):
        with pytest.raises(InvalidTransitionError):
            player.play()

    def test_pause_from_initial_paused_raises(self, player):
        with pytest.raises(InvalidTransitionError):
            player.pause()

    def test_next_without_album_raises(self, player):
        with pytest.raises(InvalidTransitionError):
            player.next_title()

    def test_previous_without_album_raises(self, player):
        with pytest.raises(InvalidTransitionError):
            player.previous_title()


# ---------------------------------------------------------------------------
# Transitions from PLAYING
# ---------------------------------------------------------------------------

class TestFromPlaying:
    def test_next_title(self, player):
        player.play("Album A")
        player.next_title()
        assert player.current_title == "02 - Second.mp3"
        assert player.state is State.PLAYING

    def test_previous_title(self, player):
        player.play("Album A")
        player.next_title()  # now at "02 - Second.mp3"
        player.previous_title()
        assert player.current_title == "01 - First.mp3"

    def test_next_wraps_around(self, player):
        player.play("Album A")
        player.next_title()  # 02
        player.next_title()  # 03
        player.next_title()  # wraps → 01
        assert player.current_title == "01 - First.mp3"

    def test_previous_wraps_around(self, player):
        player.play("Album A")
        player.previous_title()  # wraps → 03
        assert player.current_title == "03 - Third.mp3"

    def test_pause(self, player):
        player.play("Album A")
        player.pause()
        assert player.state is State.PAUSED
        assert player.current_album == "Album A"
        assert player.current_title == "01 - First.mp3"

    def test_switch_album(self, player):
        player.play("Album A")
        player.play("Album B")
        assert player.state is State.PLAYING
        assert player.current_album == "Album B"
        assert player.current_title == "track1.flac"


# ---------------------------------------------------------------------------
# Transitions from PAUSED (with album loaded)
# ---------------------------------------------------------------------------

class TestFromPaused:
    def test_resume(self, player):
        player.play("Album A")
        player.next_title()  # 02
        player.pause()
        player.play()  # resume
        assert player.state is State.PLAYING
        assert player.current_title == "02 - Second.mp3"

    def test_switch_album_from_paused(self, player):
        player.play("Album A")
        player.pause()
        player.play("Album B")
        assert player.state is State.PLAYING
        assert player.current_album == "Album B"

    def test_next_from_paused(self, player):
        player.play("Album A")
        player.pause()
        player.next_title()
        assert player.state is State.PLAYING
        assert player.current_title == "02 - Second.mp3"

    def test_previous_from_paused(self, player):
        player.play("Album A")
        player.next_title()
        player.pause()
        player.previous_title()
        assert player.state is State.PLAYING
        assert player.current_title == "01 - First.mp3"

    def test_pause_from_paused_raises(self, player):
        player.play("Album A")
        player.pause()
        with pytest.raises(InvalidTransitionError):
            player.pause()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_play_nonexistent_album_raises(self, player):
        with pytest.raises(ValueError, match="no playable titles"):
            player.play("Does Not Exist")

    def test_empty_album_raises(self, player, music_dir):
        (music_dir / "Empty Album").mkdir()
        with pytest.raises(ValueError, match="no playable titles"):
            player.play("Empty Album")

    def test_non_audio_files_ignored(self, player, music_dir):
        album = music_dir / "Mixed"
        album.mkdir()
        (album / "cover.jpg").touch()
        (album / "notes.txt").touch()
        (album / "song.mp3").touch()
        player.play("Mixed")
        assert player.current_title == "song.mp3"
