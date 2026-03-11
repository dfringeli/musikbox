"""Music player.

Loads albums and plays their tracks in sequence.  Navigation (next/prev)
wraps around within the current album.

Special RFID action tags (configurable UIDs):
    play_uid             → resumes playback when paused
    pause_uid            → toggles pause / resume
    next_uid             → advances to the next title
    prev_uid             → goes back to the previous title
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from musikbox.audio import AudioPlayer
    from musikbox.library import MusicLibrary


class MusicPlayer:
    """A folder-based music player."""

    def __init__(
        self,
        library: MusicLibrary,
        audio: AudioPlayer | None = None,
        *,
        play_uid: str | None = None,
        pause_uid: str | None = None,
        next_uid: str | None = None,
        prev_uid: str | None = None,
    ) -> None:
        self._library = library
        self._audio = audio
        self._play_uid = play_uid
        self._pause_uid = pause_uid
        self._next_uid = next_uid
        self._prev_uid = prev_uid
        self._current_album: str | None = None
        self._current_title: str | None = None
        self._current_uid: str | None = None
        self._titles: list[str] = []
        self._title_index: int = 0
        self._is_paused: bool = False

        if self._audio is not None:
            self._audio.set_end_callback(self.on_title_end)

    # -- public properties ---------------------------------------------------

    @property
    def current_album(self) -> str | None:
        return self._current_album

    @property
    def current_title(self) -> str | None:
        return self._current_title

    @property
    def current_uid(self) -> str | None:
        return self._current_uid

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    # -- controls ------------------------------------------------------------

    def play(self, album: str | None = None) -> None:
        """Start or resume playback.

        Parameters
        ----------
        album:
            Name of the album folder to load.  Required when no album has
            been loaded yet.  If ``None``, resumes the current album.
        """
        if album is not None:
            self._load_album(album)
            self._is_paused = False
            self._play_current()
            return

        if self._current_album is None:
            raise ValueError("Cannot resume without an album. Use play(album) first.")
        if self._audio is not None:
            self._audio.unpause()
        self._is_paused = False

    def pause(self) -> None:
        """Pause playback."""
        if self._audio is not None:
            self._audio.pause()
        self._is_paused = True

    def next_title(self) -> None:
        """Advance to the next title in the current album.

        Wraps around to the first title when the end is reached.
        Requires an album to be loaded.
        """
        if self._current_album is None:
            raise ValueError("next_title() requires an album to be loaded.")
        self._title_index = (self._title_index + 1) % len(self._titles)
        self._current_title = self._titles[self._title_index]
        self._is_paused = False
        self._play_current()

    def previous_title(self) -> None:
        """Go back to the previous title in the current album.

        Wraps around to the last title when the beginning is reached.
        Requires an album to be loaded.
        """
        if self._current_album is None:
            raise ValueError("previous_title() requires an album to be loaded.")
        self._title_index = (self._title_index - 1) % len(self._titles)
        self._current_title = self._titles[self._title_index]
        self._is_paused = False
        self._play_current()

    def on_rfid_scan(self, uid: str) -> None:
        """Handle an RFID tag scan.

        Special action UIDs (pause/next/prev) are handled first.
        For album UIDs, if the same UID is scanned again the call is
        silently ignored so that playback continues uninterrupted.
        Raises ``ValueError`` if no matching album is found.
        """
        if self._play_uid is not None and uid == self._play_uid:
            if self._is_paused and self._current_album is not None:
                self.play()
            return

        if self._pause_uid is not None and uid == self._pause_uid:
            if self._is_paused:
                self.play()
            elif self._current_album is not None:
                self.pause()
            return

        if self._next_uid is not None and uid == self._next_uid:
            self.next_title()
            return

        if self._prev_uid is not None and uid == self._prev_uid:
            self.previous_title()
            return

        if uid == self._current_uid:
            return
        album = self._library.find_album_by_uid(uid)
        if album is None:
            raise ValueError(f"No album found for RFID UID '{uid}'.")
        self._current_uid = uid
        self.play(album)

    def on_title_end(self) -> None:
        """Handle end-of-track event from the audio backend.

        Auto-advances to the next title.  Stops after the last title.
        """
        if self._current_album is None:
            return
        if self._title_index < len(self._titles) - 1:
            self._title_index += 1
            self._current_title = self._titles[self._title_index]
            self._play_current()

    # -- internal helpers ----------------------------------------------------

    def _play_current(self) -> None:
        """Tell the audio backend to play the current title (if available)."""
        if self._audio is not None and self._current_album is not None:
            path = self._library.get_title_path(
                self._current_album, self._current_title  # type: ignore[arg-type]
            )
            self._audio.play(path)

    def _load_album(self, album: str) -> None:
        titles = self._library.get_titles(album)
        if not titles:
            raise ValueError(f"Album '{album}' contains no playable titles.")
        self._current_album = album
        self._titles = titles
        self._title_index = 0
        self._current_title = self._titles[self._title_index]
