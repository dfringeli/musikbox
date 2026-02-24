# musikbox

Like Toniebox, but with privacy.

A folder-based music player controlled by a state machine, designed to run on
a **Raspberry Pi Zero 2 W** with Raspbian.

## Music library layout

The player expects your music to be organised as one folder per album under a
single base path (default `/home/username/Music`):

```
/home/username/Music/
    Album A/
        01 - First Track.mp3
        02 - Second Track.flac
    Album B/
        song.ogg
        another.wav
```

Recognised audio extensions: `.mp3`, `.flac`, `.ogg`, `.wav`, `.m4a`, `.aac`,
`.wma`, `.opus`.  Non-audio files (artwork, playlists, etc.) are ignored.

## State machine

The player has three states and a set of allowed transitions between them.

### States

| State       | Description                                      |
|-------------|--------------------------------------------------|
| **IDLE**    | No album loaded. Player is silent.               |
| **PLAYING** | An album is loaded and a title is being played.  |
| **PAUSED**  | An album is loaded but playback is paused.       |

### State properties

- `current_album` – name of the currently loaded album (folder name), or
  `None` when idle.
- `current_title` – file name of the currently active title, or `None` when
  idle.

### Transitions

```
           play(album)
  IDLE ──────────────────► PLAYING
                            │  ▲
                     pause  │  │  play() / play(album)
                            ▼  │
                           PAUSED
```

| From        | Action             | To        | Notes                                                  |
|-------------|--------------------|-----------|--------------------------------------------------------|
| IDLE        | `play(album)`      | PLAYING   | Album is required because no album is loaded yet.      |
| PLAYING     | `pause()`          | PAUSED    | Remembers current album and title position.            |
| PLAYING     | `next_title()`     | PLAYING   | Advances to the next title; wraps at end of album.     |
| PLAYING     | `previous_title()` | PLAYING   | Goes back to the previous title; wraps at beginning.   |
| PLAYING     | `play(album)`      | PLAYING   | Switches to a different album (starts at first title). |
| PAUSED      | `play()`           | PLAYING   | Resumes playback of the current title.                 |
| PAUSED      | `play(album)`      | PLAYING   | Switches album and starts playing.                     |
| PAUSED      | `next_title()`     | PLAYING   | Advances to next title and resumes playback.           |
| PAUSED      | `previous_title()` | PLAYING   | Goes to previous title and resumes playback.           |

Invalid transitions (e.g. `pause()` from IDLE, or `next_title()` from IDLE)
raise an `InvalidTransitionError`.

## Project structure

```
musikbox/
├── pyproject.toml
├── README.md
├── src/
│   └── musikbox/
│       ├── __init__.py
│       ├── cli.py            # Interactive command-line interface
│       ├── library.py        # Music library scanner
│       └── statemachine.py   # State machine (states, transitions)
└── tests/
    ├── __init__.py
    ├── test_library.py
    └── test_statemachine.py
```

## Setup on Raspberry Pi Zero 2 W

### Prerequisites

Raspbian (latest) ships with Python 3.11+. Verify:

```bash
python3 --version
```

### Installation

```bash
# Clone the repository
git clone <repo-url> ~/musikbox
cd ~/musikbox

# Install in editable mode (no virtualenv needed for a dedicated Pi)
pip install -e .
```

### Running

```bash
# Use the default music directory (/home/username/Music)
musikbox

# Or specify a custom path
musikbox --music-dir /home/pi/Music
```

### Interactive commands

| Command            | Description                                 |
|--------------------|---------------------------------------------|
| `albums`           | List all available albums.                  |
| `play <album>`     | Load an album and start playing.            |
| `play`             | Resume playback (when paused).              |
| `pause`            | Pause the current playback.                 |
| `next`             | Skip to the next title in the album.        |
| `prev`             | Go back to the previous title.              |
| `status`           | Show current state, album, and title.       |
| `quit`             | Exit musikbox.                              |

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```
