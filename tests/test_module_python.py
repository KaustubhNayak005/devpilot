"""Tests for devpilot.modules.python.PythonModule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.modules.python.module import PythonModule


def test_verify_python_found() -> None:
    module = PythonModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("python3", "pip3"):
            return MagicMock()
        return None

    with patch("devpilot.modules.python.module.which", side_effect=mock_which):
        with patch("devpilot.modules.python.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Python 3.12.3", stderr="")
            results = module.verify()

    assert len(results) == 3
    assert results[0].passed is True
    assert results[0].name == "python3 installed"


def test_verify_python_missing() -> None:
    module = PythonModule()

    with patch("devpilot.modules.python.module.which", return_value=None):
        results = module.verify()

    assert results[0].passed is False
    assert results[0].name == "python3 installed"
    assert results[1].passed is False
    assert results[1].name == "pip installed"


def test_verify_venv_available() -> None:
    module = PythonModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("python3", "pip3"):
            return MagicMock()
        return None

    ver_responses = {
        0: MagicMock(returncode=0, stdout="Python 3.12.3"),
        1: MagicMock(returncode=0, stdout="pip 24.0"),
        2: MagicMock(returncode=0, stdout="usage: venv ..."),
    }

    call_count = 0

    def mock_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        result = ver_responses.get(call_count, MagicMock(returncode=0, stdout=""))
        call_count += 1
        return result

    with patch("devpilot.modules.python.module.which", side_effect=mock_which):
        with patch("devpilot.modules.python.module.run_command", side_effect=mock_run):
            results = module.verify()

    assert results[2].passed is True
    assert results[2].name == "venv module"
