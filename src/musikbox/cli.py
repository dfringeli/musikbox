"""Simple interactive CLI for the musikbox player."""

from __future__ import annotations

import argparse
import signal
import sys
import time

from musikbox.audio import AudioPlayer
from musikbox.config import DEFAULT_CONFIG_PATH, load_config
from musikbox.library import MusicLibrary
from musikbox.statemachine import InvalidTransitionError, MusicPlayerStateMachine


def _run_scan_mode() -> None:
    """Read RFID tags and print their hex UIDs until interrupted."""
    from musikbox.rfid import RfidReader

    print("Hold an RFID tag to the reader...")
    print("Press Ctrl+C to stop.\n")

    def _on_tag(uid: str) -> None:
        print(f"  UID: {uid}")

    reader = RfidReader(on_tag=_on_tag)
    reader.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
    finally:
        reader.stop()


def _print_status(player: MusicPlayerStateMachine) -> None:
    print(
        f"  [{player.state.name}]"
        f"  album: {player.current_album or '–'}"
        f"  title: {player.current_title or '–'}"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="musikbox – a folder-based music player state machine",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to TOML config file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--music-dir",
        default=None,
        help="Base path to the music library",
    )
    parser.add_argument(
        "--rfid",
        action="store_true",
        default=None,
        help="Enable RFID tag reader (requires pirc522, Raspberry Pi only)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan RFID tags and print their hex UIDs, then exit (Ctrl+C to stop)",
    )
    parser.add_argument(
        "--pause-uid",
        default=None,
        help="RFID UID for the pause/resume action tag",
    )
    parser.add_argument(
        "--next-uid",
        default=None,
        help="RFID UID for the next-title action tag",
    )
    parser.add_argument(
        "--prev-uid",
        default=None,
        help="RFID UID for the previous-title action tag",
    )
    args = parser.parse_args(argv)

    if args.scan:
        _run_scan_mode()
        return

    # Load config file (silently skip if not found)
    cfg = load_config(args.config)

    # CLI flags override config values (only when explicitly provided)
    music_dir = args.music_dir if args.music_dir is not None else cfg.music_dir
    rfid = args.rfid if args.rfid is not None else cfg.rfid
    pause_uid = args.pause_uid if args.pause_uid is not None else cfg.pause_uid
    next_uid = args.next_uid if args.next_uid is not None else cfg.next_uid
    prev_uid = args.prev_uid if args.prev_uid is not None else cfg.prev_uid

    library = MusicLibrary(music_dir)
    audio = AudioPlayer()
    player = MusicPlayerStateMachine(
        library,
        audio=audio,
        pause_uid=pause_uid,
        next_uid=next_uid,
        prev_uid=prev_uid,
    )

    rfid_reader = None
    if rfid:
        from musikbox.rfid import RfidReader

        def _on_tag(uid: str) -> None:
            try:
                player.on_rfid_scan(uid)
                _print_status(player)
            except ValueError as exc:
                print(f"  RFID: {exc}")

        rfid_reader = RfidReader(on_tag=_on_tag)
        rfid_reader.start()
        print("RFID reader enabled.")

    albums = library.list_albums()
    if not albums:
        print(f"No albums found in {music_dir}")
        sys.exit(1)

    # When running with RFID (e.g. as a daemon), skip the interactive loop
    if rfid:
        print("musikbox – running in RFID mode (Ctrl+C to stop)")
        stop = False

        def _handle_signal(signum: int, frame: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, _handle_signal)
        try:
            while not stop:
                audio.check_events()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print()
        finally:
            if rfid_reader is not None:
                rfid_reader.stop()
        return

    print("musikbox – interactive mode")
    print("Available commands: albums, play <album>, pause, next, prev, status, quit")
    print()

    try:
        while True:
            try:
                raw = input("musikbox> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            audio.check_events()

            if not raw:
                continue

            parts = raw.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            try:
                if cmd == "quit":
                    break
                elif cmd == "albums":
                    for album in library.list_albums():
                        print(f"  {album}")
                elif cmd == "play":
                    player.play(album=arg)
                    _print_status(player)
                elif cmd == "pause":
                    player.pause()
                    _print_status(player)
                elif cmd == "next":
                    player.next_title()
                    _print_status(player)
                elif cmd == "prev":
                    player.previous_title()
                    _print_status(player)
                elif cmd == "status":
                    _print_status(player)
                else:
                    print(f"  Unknown command: {cmd}")
            except (InvalidTransitionError, ValueError) as exc:
                print(f"  Error: {exc}")
    finally:
        if rfid_reader is not None:
            rfid_reader.stop()


if __name__ == "__main__":
    main()
