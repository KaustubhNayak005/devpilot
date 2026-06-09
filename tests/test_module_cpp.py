"""Tests for devpilot.modules.cpp.CppModule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.modules.cpp.module import CppModule


def test_verify_all_tools_found() -> None:
    module = CppModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("gcc", "g++", "clang", "cmake", "gdb", "make"):
            return MagicMock()
        return None

    with patch("devpilot.modules.cpp.module.which", side_effect=mock_which):
        with patch("devpilot.modules.cpp.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="tool version 1.0", stderr="")
            # Also need to mock tempfile and Path for the compile check
            with patch("devpilot.modules.cpp.module.tempfile.mktemp", return_value="/tmp/test.cpp"):
                with patch("devpilot.modules.cpp.module.Path") as mock_path_class:
                    mock_path = MagicMock()
                    mock_path_class.return_value = mock_path
                    results = module.verify()

    # 6 tool checks + compile check = 7
    assert len(results) == 7
    assert all(r.passed for r in results[:-1])  # first 6: all tools found
    assert results[6].name == "g++ can compile"


def test_verify_tools_missing() -> None:
    module = CppModule()

    with patch("devpilot.modules.cpp.module.which", return_value=None):
        with patch("devpilot.modules.cpp.module.tempfile.mktemp", return_value="/tmp/test.cpp"):
            with patch("devpilot.modules.cpp.module.Path") as mock_path_class:
                mock_path = MagicMock()
                mock_path_class.return_value = mock_path
                results = module.verify()

    for r in results[:6]:
        assert r.passed is False
        assert r.fix is not None
