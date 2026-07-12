"""Tests for snapshot v2 — content capture, real restore, and deletion."""

from __future__ import annotations

import json
from unittest.mock import patch

from devpilot.snapshot.capture import (
    MAX_CONFIG_CONTENT_BYTES,
    Snapshot,
    _capture_config_file_contents,
)
from devpilot.snapshot.restore import _restore_config_file
from devpilot.snapshot.storage import (
    _dict_to_snapshot,
    _snapshot_to_dict,
    delete_snapshot,
    save_snapshot,
)


def _make_snapshot(**overrides) -> Snapshot:
    defaults = dict(
        name="test",
        timestamp="2026-07-12T00:00:00+00:00",
        devpilot_version="0.3.0",
        system={},
        installed_apt_packages=[],
        git_config={},
        environment_variables={},
        config_files={},
        devpilot_config={},
        config_file_contents={},
    )
    defaults.update(overrides)
    return Snapshot(**defaults)


class TestContentCapture:
    def test_captures_small_text_file(self, tmp_path):
        target = tmp_path / "bashrc"
        target.write_bytes(b"export FOO=bar\n")
        with patch("devpilot.snapshot.capture.CONFIG_FILES_TO_HASH", [str(target)]):
            contents = _capture_config_file_contents()
        assert contents[str(target)] == "export FOO=bar\n"

    def test_skips_oversized_file(self, tmp_path):
        target = tmp_path / "big"
        target.write_bytes(b"x" * (MAX_CONFIG_CONTENT_BYTES + 1))
        with patch("devpilot.snapshot.capture.CONFIG_FILES_TO_HASH", [str(target)]):
            contents = _capture_config_file_contents()
        assert contents == {}

    def test_skips_binary_file(self, tmp_path):
        target = tmp_path / "bin"
        target.write_bytes(b"\xff\xfe\x00\x01")
        with patch("devpilot.snapshot.capture.CONFIG_FILES_TO_HASH", [str(target)]):
            contents = _capture_config_file_contents()
        assert contents == {}

    def test_skips_missing_file(self, tmp_path):
        with patch(
            "devpilot.snapshot.capture.CONFIG_FILES_TO_HASH", [str(tmp_path / "absent")]
        ):
            assert _capture_config_file_contents() == {}


class TestStorageRoundTrip:
    def test_contents_survive_serialization(self):
        snap = _make_snapshot(config_file_contents={"~/.bashrc": "alias ll='ls -la'\n"})
        data = _snapshot_to_dict(snap)
        restored = _dict_to_snapshot(json.loads(json.dumps(data)))
        assert restored.config_file_contents == {"~/.bashrc": "alias ll='ls -la'\n"}

    def test_legacy_snapshot_without_contents_loads(self):
        data = _snapshot_to_dict(_make_snapshot())
        del data["config_file_contents"]
        restored = _dict_to_snapshot(data)
        assert restored.config_file_contents == {}


class TestRestoreConfigFile:
    def test_restores_content_with_backup(self, tmp_path):
        target = tmp_path / "gitconfig"
        target.write_text("old content", encoding="utf-8")
        snap = _make_snapshot(config_file_contents={str(target): "snapshot content"})

        with patch("devpilot.snapshot.restore.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True
            _restore_config_file(snap, str(target))

        assert target.read_text(encoding="utf-8") == "snapshot content"
        backup = tmp_path / "gitconfig.devpilot.bak"
        assert backup.read_text(encoding="utf-8") == "old content"

    def test_recreates_missing_file(self, tmp_path):
        target = tmp_path / "sub" / "init.lua"
        snap = _make_snapshot(config_file_contents={str(target): "-- config"})

        with patch("devpilot.snapshot.restore.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True
            _restore_config_file(snap, str(target))

        assert target.read_text(encoding="utf-8") == "-- config"

    def test_declining_leaves_file_alone(self, tmp_path):
        target = tmp_path / "zshrc"
        target.write_text("keep me", encoding="utf-8")
        snap = _make_snapshot(config_file_contents={str(target): "other"})

        with patch("devpilot.snapshot.restore.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = False
            _restore_config_file(snap, str(target))

        assert target.read_text(encoding="utf-8") == "keep me"

    def test_legacy_snapshot_does_not_write(self, tmp_path):
        target = tmp_path / "profile"
        target.write_text("keep me", encoding="utf-8")
        snap = _make_snapshot()  # no stored contents

        with patch("devpilot.snapshot.restore.Confirm") as mock_confirm:
            _restore_config_file(snap, str(target))

        mock_confirm.ask.assert_not_called()
        assert target.read_text(encoding="utf-8") == "keep me"


class TestDeleteSnapshot:
    def test_deletes_matching_files_only(self, tmp_path):
        with patch("devpilot.snapshot.storage.SNAPSHOT_DIR", tmp_path):
            save_snapshot(_make_snapshot(name="alpha"))
            save_snapshot(
                _make_snapshot(name="alpha", timestamp="2026-07-12T01:00:00+00:00")
            )
            save_snapshot(_make_snapshot(name="beta"))

            assert delete_snapshot("alpha") == 2
            remaining = list(tmp_path.glob("*.json"))
            assert len(remaining) == 1
            assert remaining[0].name.startswith("beta_")

    def test_delete_nonexistent_returns_zero(self, tmp_path):
        with patch("devpilot.snapshot.storage.SNAPSHOT_DIR", tmp_path):
            assert delete_snapshot("ghost") == 0
