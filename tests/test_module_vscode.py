"""Tests for devpilot.modules.vscode.VSCodeModule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.modules.vscode.module import VSCodeModule


def test_verify_code_found_with_wsl_extension() -> None:
    module = VSCodeModule()

    with patch("devpilot.modules.vscode.module.which", return_value=MagicMock()):
        with patch("devpilot.modules.vscode.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1.90.0\ne281d9f\nx64\nms-vscode-remote.remote-wsl\nother.ext",
                stderr="",
            )
            results = module.verify()

    assert len(results) == 2
    assert results[0].passed is True
    assert results[0].name == "VS Code CLI"
    assert results[1].passed is True
    assert results[1].name == "WSL extension"


def test_verify_code_missing() -> None:
    module = VSCodeModule()

    with patch("devpilot.modules.vscode.module.which", return_value=None):
        results = module.verify()

    assert len(results) == 2
    assert results[0].passed is False
    assert results[0].name == "VS Code CLI"
    assert results[1].passed is False
    assert results[1].name == "WSL extension"


def test_verify_wsl_extension_missing() -> None:
    module = VSCodeModule()

    with patch("devpilot.modules.vscode.module.which", return_value=MagicMock()):
        with patch("devpilot.modules.vscode.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1.90.0\ne281d9f\nx64\nsome.other.ext",
                stderr="",
            )
            results = module.verify()

    assert results[0].passed is True
    assert results[1].passed is False
    assert results[1].fix is not None
