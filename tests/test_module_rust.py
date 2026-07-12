"""Tests for the Rust module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from devpilot.modules.rust.module import RustModule


class TestRustVerify:
    @patch("devpilot.modules.rust.module.run_command")
    @patch("devpilot.modules.rust.module._find_tool")
    def test_verify_all_present(self, mock_find, mock_run):
        mock_find.return_value = Path("/home/u/.cargo/bin/rustc")
        mock_run.return_value = MagicMock(returncode=0, stdout="rustc 1.79.0")
        results = RustModule().verify()
        assert len(results) == 2
        assert all(r.passed for r in results)
        assert "rustc 1.79.0" in results[0].message

    @patch("devpilot.modules.rust.module._find_tool", return_value=None)
    def test_verify_missing(self, mock_find):
        results = RustModule().verify()
        assert len(results) == 2
        assert not any(r.passed for r in results)
        assert all(r.fix for r in results)


class TestRustInstall:
    @patch("devpilot.modules.rust.module._find_tool")
    @patch("devpilot.modules.rust.module.run_command")
    def test_already_installed_skips_download(self, mock_run, mock_find):
        mock_find.return_value = Path("/home/u/.cargo/bin/cargo")
        assert RustModule().install() is True
        mock_run.assert_not_called()

    @patch("devpilot.modules.rust.module._find_tool", return_value=None)
    @patch("devpilot.modules.rust.module.run_command")
    def test_download_failure_returns_false(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert RustModule().install() is False

    @patch("devpilot.modules.rust.module._find_tool")
    @patch("devpilot.modules.rust.module.run_command")
    def test_successful_install(self, mock_run, mock_find):
        mock_find.side_effect = [None, Path("/home/u/.cargo/bin/cargo")]
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="#!/bin/sh\necho rustup"),  # curl
            MagicMock(returncode=0, stdout=""),  # sh rustup.sh -y
        ]
        assert RustModule().install() is True
        sh_call = mock_run.call_args_list[1][0][0]
        assert sh_call[0] == "sh"
        assert "-y" in sh_call

    @patch("devpilot.modules.rust.module._find_tool")
    @patch("devpilot.modules.rust.module.run_command")
    def test_installer_failure_returns_false(self, mock_run, mock_find):
        mock_find.return_value = None
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="#!/bin/sh"),
            MagicMock(returncode=1, stdout=""),
        ]
        assert RustModule().install() is False
