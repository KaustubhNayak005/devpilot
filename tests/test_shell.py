"""Tests for devpilot.utils.shell."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from devpilot.utils.shell import apt_install, run_command, which


def test_run_command_pass_through() -> None:
    """run_command calls subprocess.run with the correct arguments."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        _ = run_command(["echo", "hello"])
        mock_run.assert_called_once()
        call_args, call_kwargs = mock_run.call_args
        assert call_args[0] == ["echo", "hello"]
        assert call_kwargs.get("text") is True


def test_run_command_with_cwd() -> None:
    """run_command passes cwd as a string to subprocess.run."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        run_command(["ls"], cwd=Path("/tmp"))
        call_args, call_kwargs = mock_run.call_args
        cwd_val = call_kwargs.get("cwd")
        assert cwd_val is not None
        assert Path(cwd_val).as_posix() == "/tmp"


def test_run_command_check_raises() -> None:
    """run_command with check=True raises CalledProcessError on failure."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["bad"])
        try:
            run_command(["bad"], check=True)
            assert False, "Expected CalledProcessError"
        except subprocess.CalledProcessError:
            pass


def test_which_found() -> None:
    """which returns a Path when the program exists."""
    with patch("shutil.which", return_value="/usr/bin/git"):
        result = which("git")
        assert result == Path("/usr/bin/git")


def test_which_not_found() -> None:
    """which returns None when the program is not in PATH."""
    with patch("shutil.which", return_value=None):
        result = which("nonexistent")
        assert result is None


def test_apt_install_success() -> None:
    """apt_install returns True when apt succeeds."""
    with patch("devpilot.utils.shell.run_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = apt_install(["curl", "wget"])
        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "sudo" in call_args
        assert "apt-get" in call_args
        assert "curl" in call_args
        assert "wget" in call_args


def test_apt_install_failure() -> None:
    """apt_install returns False when apt fails."""
    with patch("devpilot.utils.shell.run_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = apt_install(["nonexistent-pkg"])
        assert result is False


def test_apt_install_timeout() -> None:
    """apt_install returns False on timeout."""
    with patch(
        "devpilot.utils.shell.run_command",
        side_effect=subprocess.TimeoutExpired("apt", 600),
    ):
        result = apt_install(["some-pkg"])
        assert result is False
