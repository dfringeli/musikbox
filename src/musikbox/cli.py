"""Simple interactive CLI for the musikbox player."""

from __future__ import annotations

import argparse
import sys

from musikbox.audio import AudioPlayer
from musikbox.library import MusicLibrary
from musikbox.statemachine import InvalidTransitionError, MusicPlayerStateMachine


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
        "--music-dir",
        default="/home/username/Music",
        help="Base path to the music library (default: /home/username/Music)",
    )
    parser.add_argument(
        "--rfid",
        action="store_true",
        help="Enable RFID tag reader (requires pirc522, Raspberry Pi only)",
    )
    args = parser.parse_args(argv)

    library = MusicLibrary(args.music_dir)
    audio = AudioPlayer()
    player = MusicPlayerStateMachine(library, audio=audio)

    rfid_reader = None
    if args.rfid:
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
        print(f"No albums found in {args.music_dir}")
        sys.exit(1)

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
