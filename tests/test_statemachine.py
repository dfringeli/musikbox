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

class TestOnRfidScan:
    def test_scan_from_paused_plays_album(self, player, music_dir):
        (music_dir / "AABB Album A").mkdir()
        (music_dir / "AABB Album A" / "song.mp3").touch()
        player.on_rfid_scan("AABB")
        assert player.state is State.PLAYING
        assert player.current_album == "AABB Album A"
        assert player.current_uid == "AABB"

    def test_scan_from_playing_switches_album(self, player, music_dir):
        player.play("Album A")
        (music_dir / "CCDD Album C").mkdir()
        (music_dir / "CCDD Album C" / "track.flac").touch()
        player.on_rfid_scan("CCDD")
        assert player.state is State.PLAYING
        assert player.current_album == "CCDD Album C"
        assert player.current_uid == "CCDD"

    def test_scan_same_uid_is_ignored(self, player, music_dir):
        (music_dir / "AABB Album A").mkdir()
        (music_dir / "AABB Album A" / "song1.mp3").touch()
        (music_dir / "AABB Album A" / "song2.mp3").touch()
        player.on_rfid_scan("AABB")
        player.next_title()
        assert player.current_title == "song2.mp3"
        # Scanning the same tag again should NOT restart the album
        player.on_rfid_scan("AABB")
        assert player.current_title == "song2.mp3"
        assert player.state is State.PLAYING

    def test_scan_unknown_uid_raises(self, player):
        with pytest.raises(ValueError, match="No album found"):
            player.on_rfid_scan("DEADBEEF")

    def test_scan_unknown_uid_keeps_state(self, player):
        player.play("Album A")
        with pytest.raises(ValueError):
            player.on_rfid_scan("DEADBEEF")
        assert player.state is State.PLAYING
        assert player.current_album == "Album A"

    def test_initial_uid_is_none(self, player):
        assert player.current_uid is None


class TestRfidActionTags:
    """Tests for special RFID action tags (pause, next, prev)."""

    @pytest.fixture()
    def action_player(self, library):
        return MusicPlayerStateMachine(
            library,
            pause_uid="PAUSE1",
            next_uid="NEXT1",
            prev_uid="PREV1",
        )

    def test_pause_tag_pauses_playback(self, action_player):
        action_player.play("Album A")
        assert action_player.state is State.PLAYING
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.state is State.PAUSED

    def test_pause_tag_resumes_playback(self, action_player):
        action_player.play("Album A")
        action_player.pause()
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.state is State.PLAYING

    def test_pause_tag_ignored_without_album(self, action_player):
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.state is State.PAUSED

    def test_next_tag_advances_title(self, action_player):
        action_player.play("Album A")
        assert action_player.current_title == "01 - First.mp3"
        action_player.on_rfid_scan("NEXT1")
        assert action_player.current_title == "02 - Second.mp3"

    def test_prev_tag_goes_back(self, action_player):
        action_player.play("Album A")
        action_player.next_title()
        assert action_player.current_title == "02 - Second.mp3"
        action_player.on_rfid_scan("PREV1")
        assert action_player.current_title == "01 - First.mp3"

    def test_action_tags_do_not_set_current_uid(self, action_player):
        action_player.play("Album A")
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.current_uid is None

    def test_action_tags_not_treated_as_albums(self, action_player, music_dir):
        """Scanning an action tag should never trigger an album lookup."""
        # Even if a folder named PAUSE1 existed, the action takes priority
        (music_dir / "PAUSE1 Album").mkdir()
        (music_dir / "PAUSE1 Album" / "song.mp3").touch()
        action_player.play("Album A")
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.current_album == "Album A"
        assert action_player.state is State.PAUSED


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
