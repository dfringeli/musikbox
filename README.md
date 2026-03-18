# musikbox

Like Toniebox, but with privacy.

A folder-based music player designed to run on a **Raspberry Pi 5** with
Raspbian as a systemd daemon service.

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

## RFID action tags

In addition to album tags, you can assign dedicated RFID tags for player
controls. These are configured via CLI flags or the config file (see below).
When scanned, they trigger the corresponding action instead of loading an
album:

| Action tag     | Behaviour                                                     |
|----------------|---------------------------------------------------------------|
| `--play-uid`   | Resumes playback when paused (no-op if already playing).      |
| `--pause-uid`  | Toggles between playing and paused.                           |
| `--next-uid`   | Advances to the next title in the current album.              |
| `--prev-uid`   | Goes back to the previous title in the current album.         |

Action tags always take priority over album folders, even if a folder name
happens to start with the same UID.

## Configuration file

Settings can be stored in a TOML file so you don't need to pass CLI flags
every time. The default location is `/etc/musikbox.toml`.

```toml
music-dir = "/home/pi/Music"
audio-device = "bluealsa:DEV=XX:XX:XX:XX:XX:XX,PROFILE=a2dp"
rfid = true

[action-tags]
play-uid  = "00112233"
pause-uid = "AABBCCDD"
next-uid  = "11223344"
prev-uid  = "55667788"
```

`audio-device` sets the ALSA output device passed to `mpg123`. Use a
BlueALSA device string for Bluetooth output (replace the MAC address with
your speaker's), or omit the key entirely to use the ALSA default device.

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
│       ├── audio.py          # Audio playback backend (mpg123 via ALSA)
│       ├── cli.py            # Interactive command-line interface
│       ├── config.py         # TOML config file loader
│       ├── library.py        # Music library scanner
│       ├── player.py         # Music player (album loading, navigation)
│       └── rfid.py           # RFID tag reader (background thread)
└── tests/
    ├── __init__.py
    ├── test_audio.py
    ├── test_config.py
    ├── test_library.py
    ├── test_player.py
    └── test_rfid.py
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

Install the native libraries needed for audio playback and Bluetooth support:

```bash
sudo apt update
sudo apt install -y \
    mpg123 \
    bluez \
    bluez-alsa-utils
```

- **mpg123** – audio player used as the playback backend; talks directly to
  ALSA without PortAudio.
- **bluez** – Linux Bluetooth stack.
- **bluez-alsa-utils** – routes Bluetooth A2DP audio through ALSA (no
  PulseAudio required).

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

### Audio routing

musikbox uses `mpg123` as its audio backend, which talks directly to ALSA —
no PulseAudio or PipeWire session required.

For **Bluetooth output**, set `audio-device` in `/etc/musikbox.toml` to the
BlueALSA device string for your speaker:

```toml
audio-device = "bluealsa:DEV=00:1D:DF:AE:57:F3,PROFILE=a2dp"
```

Replace the MAC address with your speaker's (`bluetoothctl info` shows it).

For **wired output** (3.5 mm jack, HDMI, or I2S DAC), omit `audio-device`
or set it to `"default"` to use the ALSA default device.

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

# Configure RFID action tags for pause, next, play (resume) and previous
musikbox --music-dir /home/pi/Music --rfid \
    --pause-uid AABBCCDD \
    --next-uid 11223344 \
    --play-uid 00112233 \
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

### Ensure the service user belongs to the required groups

The service runs as the user specified in `User=` in the unit file. Make sure
that user is in the necessary groups:

```bash
sudo usermod -aG audio,bluetooth,spi,gpio <username>
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

### `GPIO.setup` / `Cannot determine SOC peripheral base address` on Raspberry Pi 5

The `pirc522` library depends on `RPi.GPIO`, which does not support the
Raspberry Pi 5. `rpi-lgpio` provides a drop-in replacement, but the original
`RPi.GPIO` must be removed first or it will take precedence:

```bash
sudo apt remove python3-rpi.gpio
sudo pip install rpi-lgpio --break-system-packages
```

Verify that `rpi-lgpio` is the one being loaded:

```bash
python3 -c "import RPi.GPIO; print(RPi.GPIO.__file__)"
```

The path should reference `rpi_lgpio`, not `RPi`.

### `ModuleNotFoundError: No module named 'pirc522'`

You installed without the RFID extra. Reinstall with:

```bash
sudo pip install -e ".[rfid]" --break-system-packages
```

### No sound from Bluetooth speaker

1. Make sure `bluealsa` is running:

   ```bash
   systemctl status bluealsa-aplay
   ```

2. Check that the speaker is connected:

   ```bash
   bluetoothctl info XX:XX:XX:XX:XX:XX
   ```

3. Test audio directly:

   ```bash
   speaker-test -D bluealsa -c 2 -t wav
   ```

4. If BlueALSA is not installed:

   ```bash
   sudo apt install bluez-alsa-utils
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
