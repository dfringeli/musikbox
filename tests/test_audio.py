"""Tests for the AudioPlayer mpg123 backend."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from musikbox.audio import AudioPlayer


def _make_player(
    stdout_lines: list[str] | None = None,
    device: str = "default",
) -> tuple[AudioPlayer, MagicMock]:
    """Return a player backed by a mock mpg123 process."""
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdout = iter(stdout_lines or [])
    with patch("musikbox.audio.subprocess.Popen", return_value=proc):
        player = AudioPlayer(device=device)
    return player, proc


def _sent(proc: MagicMock) -> list[str]:
    """All strings written to process stdin."""
    return [c.args[0] for c in proc.stdin.write.call_args_list]


class TestInit:
    def test_launches_mpg123_remote(self):
        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.stdout = iter([])
        with patch("musikbox.audio.subprocess.Popen", return_value=proc) as popen:
            AudioPlayer()
        cmd = popen.call_args.args[0]
        assert cmd[0] == "mpg123"
        assert "--remote" in cmd

    def test_default_device_omits_audiodevice_flag(self):
        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.stdout = iter([])
        with patch("musikbox.audio.subprocess.Popen", return_value=proc) as popen:
            AudioPlayer()
        cmd = popen.call_args.args[0]
        assert "--audiodevice" not in cmd

    def test_custom_device_passed_to_mpg123(self):
        device = "bluealsa:DEV=00:1D:DF:AE:57:F3,PROFILE=a2dp"
        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.stdout = iter([])
        with patch("musikbox.audio.subprocess.Popen", return_value=proc) as popen:
            AudioPlayer(device=device)
        cmd = popen.call_args.args[0]
        assert "--audiodevice" in cmd
        assert device in cmd


class TestPlay:
    def test_sends_load_command(self):
        player, proc = _make_player()
        player.play(Path("/music/track.mp3"))
        assert any("LOAD" in s and "track.mp3" in s for s in _sent(proc))

    def test_clears_paused_flag(self):
        player, _ = _make_player()
        player._paused = True
        player.play(Path("/music/track.mp3"))
        assert not player._paused

    def test_clears_track_ended_event(self):
        player, _ = _make_player()
        player._track_ended.set()
        player.play(Path("/music/track.mp3"))
        assert not player._track_ended.is_set()


class TestPause:
    def test_sends_pause_command(self):
        player, proc = _make_player()
        player.pause()
        assert any("PAUSE" in s for s in _sent(proc))

    def test_sets_paused_flag(self):
        player, _ = _make_player()
        player.pause()
        assert player._paused

    def test_noop_when_already_paused(self):
        player, proc = _make_player()
        player.pause()
        proc.stdin.write.reset_mock()
        player.pause()
        assert not any("PAUSE" in s for s in _sent(proc))


class TestUnpause:
    def test_sends_pause_toggle_when_paused(self):
        player, proc = _make_player()
        player._paused = True
        player.unpause()
        assert any("PAUSE" in s for s in _sent(proc))

    def test_clears_paused_flag(self):
        player, _ = _make_player()
        player._paused = True
        player.unpause()
        assert not player._paused

    def test_noop_when_already_playing(self):
        player, proc = _make_player()
        player.unpause()
        assert not any("PAUSE" in s for s in _sent(proc))


class TestStop:
    def test_sends_stop_command(self):
        player, proc = _make_player()
        player.stop()
        assert any("STOP" in s for s in _sent(proc))

    def test_sets_explicit_stop_flag(self):
        player, _ = _make_player()
        player.stop()
        assert player._explicit_stop

    def test_clears_paused_flag(self):
        player, _ = _make_player()
        player._paused = True
        player.stop()
        assert not player._paused


class TestEndCallback:
    def test_callback_fires_via_check_events(self):
        player, _ = _make_player()
        callback = MagicMock()
        player.set_end_callback(callback)
        player._track_ended.set()
        player.check_events()
        callback.assert_called_once()

    def test_track_ended_flag_cleared_after_check(self):
        player, _ = _make_player()
        player._track_ended.set()
        player.check_events()
        assert not player._track_ended.is_set()

    def test_no_callback_no_crash(self):
        player, _ = _make_player()
        player._track_ended.set()
        player.check_events()  # should not raise

    def test_check_events_noop_when_no_track_ended(self):
        player, _ = _make_player()
        callback = MagicMock()
        player.set_end_callback(callback)
        player.check_events()
        callback.assert_not_called()

    def test_p0_line_signals_track_end(self):
        player, _ = _make_player(stdout_lines=["@P 0\n"])
        time.sleep(0.05)  # let monitor thread process the line
        assert player._track_ended.is_set()

    def test_p0_suppressed_when_explicit_stop(self):
        # explicit_stop set before monitor reads the line
        player, _ = _make_player(stdout_lines=["@P 0\n"])
        player._explicit_stop = True
        time.sleep(0.05)
        assert not player._track_ended.is_set()
        assert not player._explicit_stop  # flag was consumed
