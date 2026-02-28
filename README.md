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

### RFID-tagged albums

To associate an album with an RFID tag, prefix the folder name with the tag's
UID as an uppercase hex string followed by a space:

```
/home/username/Music/
    9355A72BB5 ACDC/
        01 - Highway to Hell.mp3
    A1B2C3D4E5 Beatles/
        01 - Come Together.flac
```

When a tag is scanned, the player looks up the album whose folder name starts
with the scanned UID (case-insensitive match) and begins playback.

## State machine

The player has two states and a set of allowed transitions between them.
On startup the player enters the **PAUSED** state with no album loaded.

### States

| State       | Description                                                       |
|-------------|-------------------------------------------------------------------|
| **PAUSED**  | Playback is paused. This is the initial state on startup.         |
| **PLAYING** | An album is loaded and a title is being played.                   |

### State properties

- `current_album` – name of the currently loaded album (folder name), or
  `None` when no album has been loaded yet.
- `current_title` – file name of the currently active title, or `None` when
  no album has been loaded yet.

### Transitions

```
                play(album)
  ┌──────────────────────────────────┐
  │         play() / play(album)     │
  │  PAUSED ◄──────────────── PLAYING
  │    │                        ▲  │
  │    │  play(album)           │  │ pause()
  │    └────────────────────────┘  │
  │                                │
  └────────────────────────────────┘
       next / prev / play(album)
```

| From        | Action             | To        | Notes                                                       |
|-------------|--------------------|-----------|-------------------------------------------------------------|
| PAUSED      | `play(album)`      | PLAYING   | Loads album, starts at first title.                         |
| PAUSED      | `play()`           | PLAYING   | Resumes playback (requires an album to be loaded already).  |
| PAUSED      | `next_title()`     | PLAYING   | Advances to next title and resumes (requires album loaded). |
| PAUSED      | `previous_title()` | PLAYING   | Goes to previous title and resumes (requires album loaded). |
| PLAYING     | `pause()`          | PAUSED    | Remembers current album and title position.                 |
| PLAYING     | `next_title()`     | PLAYING   | Advances to the next title; wraps at end of album.          |
| PLAYING     | `previous_title()` | PLAYING   | Goes back to the previous title; wraps at beginning.        |
| PLAYING     | `play(album)`      | PLAYING   | Switches to a different album (starts at first title).      |
| Any         | `on_rfid_scan(uid)`| PLAYING   | Looks up album by RFID UID and starts playback.             |

When no album is loaded yet, `play()` without an album argument, `next_title()`,
`previous_title()`, and `pause()` raise an `InvalidTransitionError`.

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
│       ├── rfid.py           # RFID tag reader (background thread)
│       └── statemachine.py   # State machine (states, transitions)
└── tests/
    ├── __init__.py
    ├── test_library.py
    ├── test_rfid.py
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

# Enable RFID tag reader (requires pirc522 and an MFRC522 reader connected via SPI)
musikbox --music-dir /home/pi/Music --rfid
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
