"""Tests for musikbox.config."""

from __future__ import annotations

from pathlib import Path

from musikbox.config import Config, load_config


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg == Config()


def test_load_config_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.toml"
    p.write_text("")
    cfg = load_config(p)
    assert cfg == Config()


def test_load_config_full(tmp_path: Path) -> None:
    p = tmp_path / "musikbox.toml"
    p.write_text(
        'music-dir = "/home/pi/Albums"\n'
        "rfid = true\n"
        "\n"
        "[action-tags]\n"
        'pause-uid = "AABBCCDD"\n'
        'next-uid = "11223344"\n'
        'prev-uid = "55667788"\n'
    )
    cfg = load_config(p)
    assert cfg.music_dir == "/home/pi/Albums"
    assert cfg.rfid is True
    assert cfg.pause_uid == "AABBCCDD"
    assert cfg.next_uid == "11223344"
    assert cfg.prev_uid == "55667788"


def test_load_config_partial(tmp_path: Path) -> None:
    p = tmp_path / "musikbox.toml"
    p.write_text('music-dir = "/data/music"\n')
    cfg = load_config(p)
    assert cfg.music_dir == "/data/music"
    assert cfg.rfid is False
    assert cfg.pause_uid is None
    assert cfg.next_uid is None
    assert cfg.prev_uid is None


def test_load_config_action_tags_partial(tmp_path: Path) -> None:
    p = tmp_path / "musikbox.toml"
    p.write_text('[action-tags]\npause-uid = "DEADBEEF"\n')
    cfg = load_config(p)
    assert cfg.pause_uid == "DEADBEEF"
    assert cfg.next_uid is None
