"""Tests for devpilot.modules.nvim.NvimModule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.modules.nvim.module import NvimModule


def test_verify_nvim_found() -> None:
    module = NvimModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("nvim", "rg", "fd", "fdfind"):
            return MagicMock()
        return None

    mock_path = MagicMock()
    mock_path.exists.return_value = True

    with patch("devpilot.modules.nvim.module.which", side_effect=mock_which):
        with patch("devpilot.modules.nvim.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NVIM v0.10.0", stderr="")
            with patch("devpilot.modules.nvim.module.INIT_LUA_PATH", mock_path):
                results = module.verify()

    assert len(results) == 4
    assert results[0].passed is True
    assert results[0].name == "neovim installed"
    assert results[1].passed is True
    assert results[1].name == "ripgrep installed"
    assert results[2].passed is True
    assert results[2].name == "fd-find installed"
    assert results[3].passed is True
    assert results[3].name == "nvim config deployed"


def test_verify_nvim_missing() -> None:
    module = NvimModule()

    mock_path = MagicMock()
    mock_path.exists.return_value = False

    with patch("devpilot.modules.nvim.module.which", return_value=None):
        with patch("devpilot.modules.nvim.module.INIT_LUA_PATH", mock_path):
            results = module.verify()

    assert results[0].passed is False
    assert results[1].passed is False
    assert results[2].passed is False
    assert results[3].passed is False


def test_verify_fd_only_as_fdfind() -> None:
    module = NvimModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("nvim", "rg", "fdfind"):
            return MagicMock()
        return None

    mock_path = MagicMock()
    mock_path.exists.return_value = True

    with patch("devpilot.modules.nvim.module.which", side_effect=mock_which):
        with patch("devpilot.modules.nvim.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NVIM v0.10.0", stderr="")
            with patch("devpilot.modules.nvim.module.INIT_LUA_PATH", mock_path):
                results = module.verify()

    assert results[2].passed is True
    assert results[2].name == "fd-find installed"
