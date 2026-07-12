"""Tests for the Docker module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from devpilot.modules.docker.module import DockerModule


def _run_command_stub(healthy: bool):
    """Build a run_command side effect simulating a docker host."""

    def stub(cmd, **kwargs):
        if cmd[:2] == ["docker", "--version"]:
            return MagicMock(returncode=0, stdout="Docker version 26.0.0")
        if cmd[:2] == ["docker", "info"]:
            return MagicMock(returncode=0 if healthy else 1, stdout="")
        if cmd[:2] == ["id", "-nG"]:
            groups = "user adm docker" if healthy else "user adm"
            return MagicMock(returncode=0, stdout=groups)
        return MagicMock(returncode=0, stdout="")

    return stub


class TestDockerVerify:
    @patch("devpilot.modules.docker.module.run_command")
    @patch("devpilot.modules.docker.module.which")
    def test_verify_healthy(self, mock_which, mock_run):
        mock_which.return_value = Path("/usr/bin/docker")
        mock_run.side_effect = _run_command_stub(healthy=True)
        results = DockerModule().verify()
        assert len(results) == 3
        assert all(r.passed for r in results)

    @patch("devpilot.modules.docker.module.run_command")
    @patch("devpilot.modules.docker.module.which")
    def test_verify_daemon_down_and_no_group(self, mock_which, mock_run):
        mock_which.return_value = Path("/usr/bin/docker")
        mock_run.side_effect = _run_command_stub(healthy=False)
        results = DockerModule().verify()
        by_name = {r.name: r for r in results}
        assert by_name["docker installed"].passed
        assert not by_name["docker daemon"].passed
        assert not by_name["docker group"].passed

    @patch("devpilot.modules.docker.module.which", return_value=None)
    def test_verify_missing_short_circuits(self, mock_which):
        results = DockerModule().verify()
        assert len(results) == 1
        assert not results[0].passed


class TestDockerInstall:
    @patch("devpilot.modules.docker.module.run_command")
    @patch("devpilot.modules.docker.module.apt_install")
    @patch("devpilot.modules.docker.module.which")
    def test_already_installed_skips_apt(self, mock_which, mock_apt, mock_run):
        mock_which.return_value = Path("/usr/bin/docker")
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        with patch.dict(os.environ, {"USER": "testuser"}):
            assert DockerModule().install() is True
        mock_apt.assert_not_called()
        usermod_calls = [
            c for c in mock_run.call_args_list if "usermod" in c[0][0]
        ]
        assert len(usermod_calls) == 1

    @patch("devpilot.modules.docker.module.apt_install", return_value=False)
    @patch("devpilot.modules.docker.module.which", return_value=None)
    def test_apt_failure_returns_false(self, mock_which, mock_apt):
        assert DockerModule().install() is False
