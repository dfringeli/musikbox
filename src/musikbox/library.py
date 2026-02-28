"""Music library: discovers albums and titles from the filesystem.

Expected directory layout::

    <basepath>/
        Album A/
            01 - First Track.mp3
            02 - Second Track.flac
        Album B/
            song.ogg
            ...

Each direct sub-directory of *basepath* is treated as an album.
Files inside an album directory that carry a recognised audio extension are
treated as titles.  Titles are returned sorted alphabetically so that
track-number prefixes produce the expected order.
"""

from __future__ import annotations

import os
from pathlib import Path

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".wma", ".opus"}
)


class MusicLibrary:
    """Read-only view on a folder-based music collection."""

    def __init__(self, basepath: str | Path) -> None:
        self._basepath = Path(basepath)

    @property
    def basepath(self) -> Path:
        return self._basepath

    def list_albums(self) -> list[str]:
        """Return sorted list of album folder names."""
        if not self._basepath.is_dir():
            return []
        return sorted(
            entry.name
            for entry in self._basepath.iterdir()
            if entry.is_dir()
        )

    def get_titles(self, album: str) -> list[str]:
        """Return sorted list of audio file names in *album*."""
        album_path = self._basepath / album
        if not album_path.is_dir():
            return []
        return sorted(
            entry.name
            for entry in album_path.iterdir()
            if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS
        )

    def find_album_by_uid(self, uid: str) -> str | None:
        """Find an album whose folder name starts with *uid* (case-insensitive).

        Returns the album folder name, or ``None`` if no match is found.
        """
        uid_upper = uid.upper()
        for album in self.list_albums():
            if album.upper().startswith(uid_upper):
                return album
        return None

    def get_title_path(self, album: str, title: str) -> Path:
        """Return the full path to a title inside an album."""
        return self._basepath / album / title
