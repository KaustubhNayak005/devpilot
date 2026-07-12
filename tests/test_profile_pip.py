"""Tests for the profile installer's PEP 668-aware pip invocation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.profiles.definitions import Profile
from devpilot.profiles.installer import _pip_install, install_profile


def _proc(returncode: int, stderr: str = "") -> MagicMock:
    return MagicMock(returncode=returncode, stderr=stderr, stdout="")


class TestPipInstall:
    @patch("devpilot.profiles.installer.subprocess.run")
    def test_uses_python3_dash_m_pip_user_scoped(self, mock_run):
        mock_run.return_value = _proc(0)
        ok, error = _pip_install(["ruff"])
        assert ok is True
        cmd = mock_run.call_args[0][0]
        assert cmd[:5] == ["python3", "-m", "pip", "install", "--user"]
        assert "ruff" in cmd

    @patch("devpilot.profiles.installer.subprocess.run")
    def test_retries_with_break_system_packages_on_pep668(self, mock_run):
        mock_run.side_effect = [
            _proc(1, "error: externally-managed-environment"),
            _proc(0),
        ]
        ok, error = _pip_install(["ruff"])
        assert ok is True
        assert mock_run.call_count == 2
        second_cmd = mock_run.call_args_list[1][0][0]
        assert "--break-system-packages" in second_cmd

    @patch("devpilot.profiles.installer.subprocess.run")
    def test_other_failures_do_not_retry(self, mock_run):
        mock_run.return_value = _proc(1, "No matching distribution found")
        ok, error = _pip_install(["definitely-not-a-package"])
        assert ok is False
        assert mock_run.call_count == 1
        assert "No matching distribution" in error


class TestInstallProfileUsesPipHelper:
    @patch("devpilot.profiles.installer._pip_install", return_value=(True, ""))
    def test_pip_packages_route_through_helper(self, mock_pip):
        profile = Profile(
            name="t",
            description="test",
            apt_packages=[],
            pip_packages=["ruff", "mypy"],
            npm_packages=[],
            post_install_notes=[],
        )
        assert install_profile(profile) is True
        mock_pip.assert_called_once_with(["ruff", "mypy"])
