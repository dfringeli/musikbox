"""Load musikbox configuration from a TOML file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("/etc/musikbox.toml")


@dataclass
class Config:
    """Musikbox configuration."""

    music_dir: str = "/home/pi/Music"
    rfid: bool = False
    pause_uid: str | None = None
    next_uid: str | None = None
    prev_uid: str | None = None


def load_config(path: Path | str) -> Config:
    """Load configuration from a TOML file.

    Returns a :class:`Config` with defaults for any missing keys.
    If the file does not exist, returns a default :class:`Config`.
    """
    path = Path(path)
    if not path.is_file():
        return Config()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    action_tags = data.get("action-tags", {})

    return Config(
        music_dir=data.get("music-dir", Config.music_dir),
        rfid=data.get("rfid", Config.rfid),
        pause_uid=action_tags.get("pause-uid"),
        next_uid=action_tags.get("next-uid"),
        prev_uid=action_tags.get("prev-uid"),
    )
