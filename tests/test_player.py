"""Tests for the music player."""

from __future__ import annotations

import pytest

from musikbox.library import MusicLibrary
from musikbox.player import MusicPlayer


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
    return MusicPlayer(library)


# ---------------------------------------------------------------------------
# Initial state (no album loaded)
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_no_album(self, player):
        assert player.current_album is None

    def test_no_title(self, player):
        assert player.current_title is None

    def test_not_paused(self, player):
        assert player.is_paused is False


# ---------------------------------------------------------------------------
# play()
# ---------------------------------------------------------------------------

class TestPlay:
    def test_play_album_loads_first_title(self, player):
        player.play("Album A")
        assert player.current_album == "Album A"
        assert player.current_title == "01 - First.mp3"

    def test_play_without_album_raises_when_no_album_loaded(self, player):
        with pytest.raises(ValueError):
            player.play()

    def test_play_resumes_after_pause(self, player):
        player.play("Album A")
        player.next_title()  # 02
        player.pause()
        assert player.is_paused is True
        player.play()
        assert player.is_paused is False
        assert player.current_title == "02 - Second.mp3"

    def test_switch_album(self, player):
        player.play("Album A")
        player.play("Album B")
        assert player.current_album == "Album B"
        assert player.current_title == "track1.flac"

    def test_switch_album_from_paused(self, player):
        player.play("Album A")
        player.pause()
        player.play("Album B")
        assert player.current_album == "Album B"
        assert player.is_paused is False


# ---------------------------------------------------------------------------
# pause()
# ---------------------------------------------------------------------------

class TestPause:
    def test_pause_sets_is_paused(self, player):
        player.play("Album A")
        player.pause()
        assert player.is_paused is True
        assert player.current_album == "Album A"
        assert player.current_title == "01 - First.mp3"

    def test_pause_then_resume(self, player):
        player.play("Album A")
        player.pause()
        player.play()
        assert player.is_paused is False


# ---------------------------------------------------------------------------
# next_title / previous_title
# ---------------------------------------------------------------------------

class TestNavigation:
    def test_next_title(self, player):
        player.play("Album A")
        player.next_title()
        assert player.current_title == "02 - Second.mp3"

    def test_previous_title(self, player):
        player.play("Album A")
        player.next_title()  # 02
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

    def test_next_without_album_raises(self, player):
        with pytest.raises(ValueError):
            player.next_title()

    def test_previous_without_album_raises(self, player):
        with pytest.raises(ValueError):
            player.previous_title()

    def test_next_from_paused_resumes(self, player):
        player.play("Album A")
        player.pause()
        player.next_title()
        assert player.is_paused is False
        assert player.current_title == "02 - Second.mp3"

    def test_previous_from_paused_resumes(self, player):
        player.play("Album A")
        player.next_title()
        player.pause()
        player.previous_title()
        assert player.is_paused is False
        assert player.current_title == "01 - First.mp3"


# ---------------------------------------------------------------------------
# on_rfid_scan
# ---------------------------------------------------------------------------

class TestOnRfidScan:
    def test_scan_plays_album(self, player, music_dir):
        (music_dir / "AABB Album A").mkdir()
        (music_dir / "AABB Album A" / "song.mp3").touch()
        player.on_rfid_scan("AABB")
        assert player.current_album == "AABB Album A"
        assert player.current_uid == "AABB"

    def test_scan_switches_album(self, player, music_dir):
        player.play("Album A")
        (music_dir / "CCDD Album C").mkdir()
        (music_dir / "CCDD Album C" / "track.flac").touch()
        player.on_rfid_scan("CCDD")
        assert player.current_album == "CCDD Album C"
        assert player.current_uid == "CCDD"

    def test_scan_same_uid_is_ignored(self, player, music_dir):
        (music_dir / "AABB Album A").mkdir()
        (music_dir / "AABB Album A" / "song1.mp3").touch()
        (music_dir / "AABB Album A" / "song2.mp3").touch()
        player.on_rfid_scan("AABB")
        player.next_title()
        assert player.current_title == "song2.mp3"
        player.on_rfid_scan("AABB")
        assert player.current_title == "song2.mp3"

    def test_scan_unknown_uid_raises(self, player):
        with pytest.raises(ValueError, match="No album found"):
            player.on_rfid_scan("DEADBEEF")

    def test_scan_unknown_uid_keeps_album(self, player):
        player.play("Album A")
        with pytest.raises(ValueError):
            player.on_rfid_scan("DEADBEEF")
        assert player.current_album == "Album A"

    def test_initial_uid_is_none(self, player):
        assert player.current_uid is None


# ---------------------------------------------------------------------------
# RFID action tags
# ---------------------------------------------------------------------------

class TestRfidActionTags:
    @pytest.fixture()
    def action_player(self, library):
        return MusicPlayer(
            library,
            pause_uid="PAUSE1",
            next_uid="NEXT1",
            prev_uid="PREV1",
        )

    def test_pause_tag_pauses_playback(self, action_player):
        action_player.play("Album A")
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.is_paused is True

    def test_pause_tag_resumes_playback(self, action_player):
        action_player.play("Album A")
        action_player.pause()
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.is_paused is False

    def test_pause_tag_ignored_without_album(self, action_player):
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.is_paused is False

    def test_next_tag_advances_title(self, action_player):
        action_player.play("Album A")
        action_player.on_rfid_scan("NEXT1")
        assert action_player.current_title == "02 - Second.mp3"

    def test_prev_tag_goes_back(self, action_player):
        action_player.play("Album A")
        action_player.next_title()
        action_player.on_rfid_scan("PREV1")
        assert action_player.current_title == "01 - First.mp3"

    def test_action_tags_do_not_set_current_uid(self, action_player):
        action_player.play("Album A")
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.current_uid is None

    def test_action_tags_not_treated_as_albums(self, action_player, music_dir):
        (music_dir / "PAUSE1 Album").mkdir()
        (music_dir / "PAUSE1 Album" / "song.mp3").touch()
        action_player.play("Album A")
        action_player.on_rfid_scan("PAUSE1")
        assert action_player.current_album == "Album A"
        assert action_player.is_paused is True


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
