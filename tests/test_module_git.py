"""Tests for devpilot.modules.git.GitModule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.modules.git.module import GitModule


def test_verify_git_found() -> None:
    module = GitModule()

    def mock_which(program: str) -> MagicMock | None:
        if program == "git":
            return MagicMock()
        return None

    with patch("devpilot.modules.git.module.which", side_effect=mock_which):
        with patch("devpilot.modules.git.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.43.0", stderr="")
            results = module.verify()

    assert len(results) == 3
    assert results[0].passed is True
    assert results[0].name == "git installed"
    assert "2.43.0" in results[0].message


def test_verify_git_missing() -> None:
    module = GitModule()

    with patch("devpilot.modules.git.module.which", return_value=None):
        results = module.verify()

    assert results[0].passed is False
    assert results[0].name == "git installed"
    assert results[0].fix is not None


def test_verify_git_config_set() -> None:
    module = GitModule()
    module._get_git_config = MagicMock(return_value="Test User")  # type: ignore[method-assign]

    with patch("devpilot.modules.git.module.which", return_value=MagicMock()):
        with patch("devpilot.modules.git.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.43.0", stderr="")
            results = module.verify()

    assert results[1].passed is True
    assert "Test User" in results[1].message
    assert results[2].passed is True
    assert "Test User" in results[2].message


def test_verify_git_config_missing() -> None:
    module = GitModule()
    module._get_git_config = MagicMock(return_value="")  # type: ignore[method-assign]

    with patch("devpilot.modules.git.module.which", return_value=MagicMock()):
        with patch("devpilot.modules.git.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="git version 2.43.0", stderr="")
            results = module.verify()

    assert results[1].passed is False
    assert results[1].name == "git user.name"
    assert results[1].fix is not None
    assert results[2].passed is False
    assert results[2].name == "git user.email"
    assert results[2].fix is not None
