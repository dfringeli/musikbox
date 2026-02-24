"""Tests for the music library module."""

from __future__ import annotations

from musikbox.library import MusicLibrary


class TestListAlbums:
    def test_returns_sorted_album_names(self, tmp_path):
        (tmp_path / "Zebra").mkdir()
        (tmp_path / "Alpha").mkdir()
        lib = MusicLibrary(tmp_path)
        assert lib.list_albums() == ["Alpha", "Zebra"]

    def test_ignores_files_in_basepath(self, tmp_path):
        (tmp_path / "not_an_album.txt").touch()
        (tmp_path / "RealAlbum").mkdir()
        lib = MusicLibrary(tmp_path)
        assert lib.list_albums() == ["RealAlbum"]

    def test_empty_directory(self, tmp_path):
        lib = MusicLibrary(tmp_path)
        assert lib.list_albums() == []

    def test_nonexistent_basepath(self, tmp_path):
        lib = MusicLibrary(tmp_path / "nope")
        assert lib.list_albums() == []


class TestGetTitles:
    def test_returns_sorted_audio_files(self, tmp_path):
        album = tmp_path / "MyAlbum"
        album.mkdir()
        (album / "02 - B.mp3").touch()
        (album / "01 - A.mp3").touch()
        lib = MusicLibrary(tmp_path)
        assert lib.get_titles("MyAlbum") == ["01 - A.mp3", "02 - B.mp3"]

    def test_filters_non_audio_files(self, tmp_path):
        album = tmp_path / "Mix"
        album.mkdir()
        (album / "cover.jpg").touch()
        (album / "track.flac").touch()
        lib = MusicLibrary(tmp_path)
        assert lib.get_titles("Mix") == ["track.flac"]

    def test_nonexistent_album(self, tmp_path):
        lib = MusicLibrary(tmp_path)
        assert lib.get_titles("Ghost") == []


class TestGetTitlePath:
    def test_returns_full_path(self, tmp_path):
        lib = MusicLibrary(tmp_path)
        path = lib.get_title_path("Album", "song.mp3")
        assert path == tmp_path / "Album" / "song.mp3"
