"""Tests for devpilot.snapshot.capture, storage, restore, and diff."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from devpilot.snapshot.capture import Snapshot, capture_snapshot
from devpilot.snapshot.diff import diff_snapshots
from devpilot.snapshot.storage import (
    _sanitize_name,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)


def _make_snapshot(name: str = "test", **overrides: object) -> Snapshot:
    """Create a minimal Snapshot for testing."""
    kwargs: dict[str, object] = {
        "name": name,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "devpilot_version": "0.1.0",
        "system": {"hostname": "test"},
        "installed_apt_packages": ["git", "python3"],
        "git_config": {"user.name": "test"},
        "environment_variables": {"SHELL": "/bin/bash"},
        "config_files": {"~/.gitconfig": "abc123"},
        "devpilot_config": {"installed_modules": []},
    }
    kwargs.update(overrides)
    return Snapshot(**kwargs)  # type: ignore[arg-type]


class TestCapture:
    """Tests for snapshot capture."""

    def test_capture_returns_snapshot(self):
        """capture_snapshot returns a Snapshot instance with a name."""
        with (
            patch("devpilot.snapshot.capture._capture_system", return_value={"hostname": "test"}),
            patch("devpilot.snapshot.capture._capture_apt_packages", return_value=["git"]),
            patch("devpilot.snapshot.capture._capture_git_config", return_value={}),
            patch("devpilot.snapshot.capture._capture_env_vars", return_value={}),
            patch("devpilot.snapshot.capture._capture_config_file_hashes", return_value={}),
            patch("devpilot.snapshot.capture._capture_devpilot_config", return_value={}),
            patch("devpilot.snapshot.capture._get_devpilot_version", return_value="0.1.0"),
        ):
            result = capture_snapshot("test-snap")
        assert isinstance(result, Snapshot)
        assert result.name == "test-snap"
        assert result.timestamp

    def test_capture_includes_timestamp(self):
        """capture_snapshot timestamps are ISO format."""
        with (
            patch("devpilot.snapshot.capture._capture_system", return_value={}),
            patch("devpilot.snapshot.capture._capture_apt_packages", return_value=[]),
            patch("devpilot.snapshot.capture._capture_git_config", return_value={}),
            patch("devpilot.snapshot.capture._capture_env_vars", return_value={}),
            patch("devpilot.snapshot.capture._capture_config_file_hashes", return_value={}),
            patch("devpilot.snapshot.capture._capture_devpilot_config", return_value={}),
            patch("devpilot.snapshot.capture._get_devpilot_version", return_value="0.1.0"),
        ):
            result = capture_snapshot("ts-test")
        assert "T" in result.timestamp
        assert "+" in result.timestamp or "Z" in result.timestamp


class TestStorage:
    """Tests for snapshot storage (save/load/list)."""

    def test_sanitize_name(self):
        """_sanitize_name replaces unsafe characters."""
        assert _sanitize_name("my snapshot") == "my_snapshot"
        assert _sanitize_name("abc/def") == "abc_def"
        assert _sanitize_name("ok-name") == "ok-name"
        assert _sanitize_name("hello.world") == "hello_world"

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """Saving a snapshot and loading it back returns equivalent data."""
        snapshot = _make_snapshot("roundtrip")
        with patch("devpilot.snapshot.storage.SNAPSHOT_DIR", tmp_path):
            filepath = save_snapshot(snapshot)
            assert filepath.exists()

            loaded = load_snapshot("roundtrip")
        assert loaded.name == snapshot.name
        assert loaded.installed_apt_packages == snapshot.installed_apt_packages
        assert loaded.config_files == snapshot.config_files

    def test_load_by_path(self, tmp_path: Path):
        """load_snapshot with a .json path loads that file directly."""
        snapshot = _make_snapshot("direct")
        with patch("devpilot.snapshot.storage.SNAPSHOT_DIR", tmp_path):
            filepath = save_snapshot(snapshot)
            loaded = load_snapshot(str(filepath))
        assert loaded.name == "direct"

    def test_load_snapshot_not_found(self, tmp_path: Path):
        """load_snapshot raises FileNotFoundError when no match exists."""
        with patch("devpilot.snapshot.storage.SNAPSHOT_DIR", tmp_path):
            with patch("devpilot.snapshot.storage._ensure_dir"):
                import pytest

                with pytest.raises(FileNotFoundError):
                    load_snapshot("nonexistent")

    def test_list_snapshots(self, tmp_path: Path):
        """list_snapshots returns all saved snapshots."""
        snap1 = _make_snapshot("snap-a", timestamp="2026-01-01T00:00:00+00:00")
        snap2 = _make_snapshot("snap-b", timestamp="2026-02-01T00:00:00+00:00")
        with patch("devpilot.snapshot.storage.SNAPSHOT_DIR", tmp_path):
            save_snapshot(snap1)
            save_snapshot(snap2)
            results = list_snapshots()
        assert len(results) == 2


class TestDiff:
    """Tests for snapshot diffing."""

    def test_diff_detects_added_packages(self):
        """diff_snapshots identifies packages that were added."""
        saved = _make_snapshot("saved", installed_apt_packages=["git"])
        current = _make_snapshot("current", installed_apt_packages=["git", "python3"])
        diff = diff_snapshots(saved, current)
        assert diff.added_packages == ["python3"]
        assert diff.removed_packages == []

    def test_diff_detects_removed_packages(self):
        """diff_snapshots identifies packages that were removed."""
        saved = _make_snapshot("saved", installed_apt_packages=["git", "python3"])
        current = _make_snapshot("current", installed_apt_packages=["git"])
        diff = diff_snapshots(saved, current)
        assert diff.removed_packages == ["python3"]
        assert diff.added_packages == []

    def test_diff_detects_changed_env_vars(self):
        """diff_snapshots identifies environment variable changes."""
        saved = _make_snapshot("saved", environment_variables={"JAVA_HOME": "/old/path"})
        current = _make_snapshot("current", environment_variables={"JAVA_HOME": "/new/path"})
        diff = diff_snapshots(saved, current)
        assert "JAVA_HOME" in diff.changed_env_vars
        assert diff.changed_env_vars["JAVA_HOME"] == ("/old/path", "/new/path")

    def test_diff_detects_config_file_changes(self):
        """diff_snapshots identifies config files with changed hashes."""
        saved = _make_snapshot("saved", config_files={"~/.gitconfig": "hash-old"})
        current = _make_snapshot("current", config_files={"~/.gitconfig": "hash-new"})
        diff = diff_snapshots(saved, current)
        assert "~/.gitconfig" in diff.changed_config_files

    def test_diff_no_changes(self):
        """diff_snapshots returns empty diff when nothing changed."""
        snap = _make_snapshot("same")
        diff = diff_snapshots(snap, snap)
        assert diff.added_packages == []
        assert diff.removed_packages == []
        assert diff.changed_env_vars == {}
        assert diff.changed_config_files == []
