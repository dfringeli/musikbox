# musikbox

Like Toniebox, but with privacy.

A folder-based music player controlled by a state machine, designed to run on
a **Raspberry Pi 5** with Raspbian as a systemd daemon service.

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

## Project structure

```
musikbox/
├── pyproject.toml
├── README.md
├── musikbox.service          # systemd unit file
├── src/
│   └── musikbox/
│       ├── __init__.py
│       ├── audio.py          # Audio playback backend (sounddevice + soundfile)
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

## Setup on Raspberry Pi

### Hardware prerequisites

| Component            | Interface | Purpose                       |
|----------------------|-----------|-------------------------------|
| MFRC522 RFID reader  | SPI       | Scan RFID tags to select albums |
| Bluetooth speaker     | Bluetooth | Wireless audio output         |
| 3.5 mm / HDMI / I2S  | ALSA      | Wired audio output (alternative) |

### Enable SPI and Bluetooth

Open the Raspberry Pi configuration tool:

```bash
sudo raspi-config
```

1. Go to **Interface Options → SPI** and enable it.
2. Go to **Interface Options → Serial Port** — disable the login shell but
   keep the serial port hardware enabled (needed by some HATs).
3. Bluetooth is enabled by default on Raspberry Pi OS. Verify:

```bash
systemctl status bluetooth
```

Reboot after changing any interface settings:

```bash
sudo reboot
```

### System dependencies

Install the native libraries that `sounddevice` and `soundfile` need, plus
Bluetooth audio support via BlueALSA:

```bash
sudo apt update
sudo apt install -y \
    libportaudio2 \
    libsndfile1 \
    bluez \
    bluealsa
```

- **libportaudio2** – PortAudio backend used by `sounddevice` to talk to ALSA.
- **libsndfile1** – decodes MP3, FLAC, OGG, WAV (used by `soundfile`).
- **bluez** – Linux Bluetooth stack.
- **bluealsa** – routes Bluetooth A2DP audio through ALSA (no PulseAudio
  required).

### Pair a Bluetooth speaker

```bash
bluetoothctl
```

Inside the Bluetooth shell:

```
power on
agent on
default-agent
scan on
# Wait until you see your speaker, then:
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
quit
```

Replace `XX:XX:XX:XX:XX:XX` with your speaker's MAC address.

To verify audio output, run a quick test:

```bash
speaker-test -D bluealsa -c 2 -t wav
```

If you use a wired output (3.5 mm jack, HDMI, or I2S DAC), skip BlueALSA and
use the default ALSA device instead.

### Installation

```bash
# Clone the repository
git clone <repo-url> ~/musikbox
cd ~/musikbox

# Install system-wide with RFID support
sudo pip install -e ".[rfid]" --break-system-packages
```

If you don't need RFID, a plain `sudo pip install -e .` is enough.

On Raspberry Pi 5 the `pirc522` RFID library depends on `RPi.GPIO`, which
must be replaced by `rpi-lgpio`:

```bash
sudo pip install rpi-lgpio --break-system-packages
```

### Scanning RFID tags

To find out the hex UID of a tag (for naming album folders or configuring
action tags), use the `--scan` flag:

```bash
musikbox --scan
```

Hold a tag to the reader and its UID will be printed. Press Ctrl+C to stop.
Use the printed UID as the folder name prefix (e.g. `9355A72BB5 My Album/`).

### Running interactively

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

## Daemon service (systemd)

The included `musikbox.service` unit file runs musikbox as a system daemon on
boot. It starts the player in RFID mode so albums are selected by scanning
tags — no interactive terminal required.

### What the service configures

| Concern      | How it is handled                                                |
|--------------|------------------------------------------------------------------|
| **Audio**    | Runs as member of the `audio` group — direct ALSA access, no PulseAudio. |
| **Bluetooth**| Member of the `bluetooth` group; service starts after `bluetooth.target`. |
| **SPI**      | Member of the `spi` group; device access to `/dev/spidev*`.     |
| **GPIO**     | Member of the `gpio` group; device access to `/dev/gpiochip*`.  |
| **Security** | `ProtectSystem=strict`, `NoNewPrivileges=true`, read-only home except music dir. |

### Install the service

```bash
# Copy the unit file
sudo cp musikbox.service /etc/systemd/system/

# Reload systemd so it picks up the new file
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable musikbox

# Start the service now
sudo systemctl start musikbox
```

### Check status and logs

```bash
# Service status
sudo systemctl status musikbox

# Follow the live log
journalctl -u musikbox -f

# Show logs since last boot
journalctl -u musikbox -b
```

### Restart / stop the service

```bash
sudo systemctl restart musikbox
sudo systemctl stop musikbox
```

### Ensure the `pi` user belongs to the required groups

The service runs as user `pi`. Make sure this user is in the necessary groups:

```bash
sudo usermod -aG audio,bluetooth,spi,gpio pi
```

Log out and back in (or reboot) for group changes to take effect.

### Verify hardware access

After starting the service, check that the required devices are accessible:

```bash
# SPI device (RFID reader)
ls -l /dev/spidev0.*

# GPIO chip (RFID RST pin)
ls -l /dev/gpiochip*

# ALSA sound devices
ls -l /dev/snd/
```

## Troubleshooting

### `sudo: musikbox: command not found`

If you installed with `pip install --break-system-packages` as a regular user,
the `musikbox` binary ends up in `~/.local/bin/` which `sudo` cannot see.
Install system-wide instead:

```bash
sudo pip install -e ".[rfid]" --break-system-packages
```

This puts `musikbox` into `/usr/local/bin/`. Verify with `which musikbox`.

### `GPIO.setup` RuntimeError on Raspberry Pi 5

The `pirc522` library depends on `RPi.GPIO`, which does not support the
Raspberry Pi 5. Install `rpi-lgpio` as a drop-in replacement:

```bash
sudo pip install rpi-lgpio --break-system-packages
```

This provides the `RPi.GPIO` API on top of `lgpio`, which works on Pi 5.

### `ModuleNotFoundError: No module named 'pirc522'`

You installed without the RFID extra. Reinstall with:

```bash
sudo pip install -e ".[rfid]" --break-system-packages
```

### No sound from Bluetooth speaker

1. Make sure `bluealsa` is running:

   ```bash
   systemctl status bluealsa
   ```

2. Check that the speaker is connected:

   ```bash
   bluetoothctl info XX:XX:XX:XX:XX:XX
   ```

3. Test audio directly:

   ```bash
   speaker-test -D bluealsa -c 2 -t wav
   ```

4. If `bluealsa` is not installed:

   ```bash
   sudo apt install bluealsa
   ```

### No sound at all (wired output)

List available ALSA devices and make sure one is present:

```bash
aplay -l
```

Test audio with the default device:

```bash
speaker-test -c 2 -t wav
```

### Service fails to start

Check the journal for details:

```bash
journalctl -u musikbox -b --no-pager
```

Common causes:
- `musikbox` not installed system-wide (`which musikbox` returns nothing).
- User `pi` is missing from required groups (`id pi` to check).
- SPI not enabled (`ls /dev/spidev*` — if empty, enable SPI via `raspi-config`).
- Music directory does not exist or is empty.

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```
