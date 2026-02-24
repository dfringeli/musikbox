"""Music player state machine.

States
------
- idle    : No album is loaded. The player is silent.
- playing : An album is loaded and a title is being played.
- paused  : An album is loaded but playback is paused.

State properties
----------------
- current_album : str | None  – name of the album currently loaded.
- current_title : str | None  – file-name of the title currently active.

Allowed transitions
-------------------
From *idle*:
    play(album)          → playing   (loads album, starts at first title)

From *playing*:
    pause()              → paused
    next_title()         → playing   (advances to the next title in the album)
    previous_title()     → playing   (goes back to the previous title)
    play(album)          → playing   (switches to a different album, first title)

From *paused*:
    play()               → playing   (resumes; or play(album) to switch album)
    next_title()         → playing
    previous_title()     → playing
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from musikbox.library import MusicLibrary


class State(Enum):
    IDLE = auto()
    PLAYING = auto()
    PAUSED = auto()


class InvalidTransitionError(Exception):
    """Raised when a transition is not allowed from the current state."""


class MusicPlayerStateMachine:
    """A minimal state machine for a folder-based music player."""

    def __init__(self, library: MusicLibrary) -> None:
        self._library = library
        self._state: State = State.IDLE
        self._current_album: str | None = None
        self._current_title: str | None = None
        self._titles: list[str] = []
        self._title_index: int = 0

    # -- public properties ---------------------------------------------------

    @property
    def state(self) -> State:
        return self._state

    @property
    def current_album(self) -> str | None:
        return self._current_album

    @property
    def current_title(self) -> str | None:
        return self._current_title

    # -- transitions ---------------------------------------------------------

    def play(self, album: str | None = None) -> None:
        """Start or resume playback.

        Parameters
        ----------
        album:
            Name of the album folder to load.  Required when in *idle* state.
            Optional when in *playing* or *paused* – if given, switches album;
            if ``None``, resumes the current album.
        """
        if self._state is State.IDLE:
            if album is None:
                raise InvalidTransitionError(
                    "Cannot play from idle without specifying an album."
                )
            self._load_album(album)
            self._state = State.PLAYING
            return

        if self._state in (State.PLAYING, State.PAUSED):
            if album is not None:
                self._load_album(album)
            self._state = State.PLAYING
            return

        raise InvalidTransitionError(
            f"play() is not allowed in state {self._state.name}."
        )

    def pause(self) -> None:
        """Pause playback.  Only allowed from *playing*."""
        if self._state is not State.PLAYING:
            raise InvalidTransitionError(
                f"pause() is only allowed in PLAYING state, "
                f"current state is {self._state.name}."
            )
        self._state = State.PAUSED

    def next_title(self) -> None:
        """Advance to the next title in the current album.

        Wraps around to the first title when the end is reached.
        Only allowed from *playing* or *paused*.
        """
        if self._state not in (State.PLAYING, State.PAUSED):
            raise InvalidTransitionError(
                f"next_title() is not allowed in state {self._state.name}."
            )
        self._title_index = (self._title_index + 1) % len(self._titles)
        self._current_title = self._titles[self._title_index]
        self._state = State.PLAYING

    def previous_title(self) -> None:
        """Go back to the previous title in the current album.

        Wraps around to the last title when the beginning is reached.
        Only allowed from *playing* or *paused*.
        """
        if self._state not in (State.PLAYING, State.PAUSED):
            raise InvalidTransitionError(
                f"previous_title() is not allowed in state {self._state.name}."
            )
        self._title_index = (self._title_index - 1) % len(self._titles)
        self._current_title = self._titles[self._title_index]
        self._state = State.PLAYING

    # -- internal helpers ----------------------------------------------------

    def _load_album(self, album: str) -> None:
        titles = self._library.get_titles(album)
        if not titles:
            raise ValueError(f"Album '{album}' contains no playable titles.")
        self._current_album = album
        self._titles = titles
        self._title_index = 0
        self._current_title = self._titles[0]
