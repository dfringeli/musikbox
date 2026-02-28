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
- `current_uid` – RFID UID of the currently loaded album, or `None` when no
  album has been loaded via RFID yet. Scanning the same UID again is silently
  ignored so playback continues uninterrupted.

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

### RFID action tags

In addition to album tags, you can assign dedicated RFID tags for player
controls. These are configured via CLI flags or the config file (see below).
When scanned, they trigger the corresponding action instead of loading an
album:

| Action tag     | Behaviour                                                     |
|----------------|---------------------------------------------------------------|
| `--pause-uid`  | Toggles between PLAYING and PAUSED.                           |
| `--next-uid`   | Advances to the next title in the current album.              |
| `--prev-uid`   | Goes back to the previous title in the current album.         |

Action tags always take priority over album folders, even if a folder name
happens to start with the same UID.

## Configuration file

Settings can be stored in a TOML file so you don't need to pass CLI flags
every time. The default location is `/etc/musikbox.toml`.

```toml
music-dir = "/home/pi/Music"
rfid = true

[action-tags]
pause-uid = "AABBCCDD"
next-uid = "11223344"
prev-uid = "55667788"
```

All keys are optional — missing keys use built-in defaults. CLI flags always
override config file values when explicitly provided.

To use a config file in a different location:

```bash
musikbox --config /path/to/my-config.toml
```

If the config file does not exist, musikbox starts with defaults (no error).

## systemd service

To run musikbox automatically on boot, install the provided systemd unit file:

```bash
sudo cp musikbox.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable musikbox
sudo systemctl start musikbox
```

The service runs as user `pi` and reads its settings from `/etc/musikbox.toml`.
Check logs with:

```bash
journalctl -u musikbox -f
```

## Project structure

```
musikbox/
├── pyproject.toml
├── README.md
├── musikbox.service          # systemd unit file
├── src/
│   └── musikbox/
│       ├── __init__.py
│       ├── audio.py          # Audio playback backend (pygame.mixer)
│       ├── cli.py            # Interactive command-line interface
│       ├── config.py         # TOML config file loader
│       ├── library.py        # Music library scanner
│       ├── rfid.py           # RFID tag reader (background thread)
│       └── statemachine.py   # State machine (states, transitions)
└── tests/
    ├── __init__.py
    ├── test_audio.py
    ├── test_config.py
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

### Scanning RFID tags

To find out the hex UID of a tag (for naming album folders or configuring
action tags), use the `--scan` flag:

```bash
musikbox --scan
```

Hold a tag to the reader and its UID will be printed. Press Ctrl+C to stop.
Use the printed UID as the folder name prefix (e.g. `9355A72BB5 My Album/`).

### Running

```bash
# Use the default music directory (/home/username/Music)
musikbox

# Or specify a custom path
musikbox --music-dir /home/pi/Music

# Enable RFID tag reader (requires pirc522 and an MFRC522 reader connected via SPI)
musikbox --music-dir /home/pi/Music --rfid

# Configure RFID action tags for pause, next, and previous
musikbox --music-dir /home/pi/Music --rfid \
    --pause-uid AABBCCDD \
    --next-uid 11223344 \
    --prev-uid 55667788
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
