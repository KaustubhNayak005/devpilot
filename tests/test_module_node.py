"""Tests for devpilot.modules.node.NodeModule."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from devpilot.modules.node.module import NodeModule


def test_verify_node_found() -> None:
    module = NodeModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("node", "npm", "tsc"):
            return MagicMock()
        return None

    ver_responses = {
        "node": MagicMock(returncode=0, stdout="v22.14.0", stderr=""),
        "npm": MagicMock(returncode=0, stdout="10.9.0", stderr=""),
    }

    def mock_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if "node" in cmd and "--version" in cmd:
            return ver_responses["node"]
        if "npm" in cmd and "--version" in cmd:
            return ver_responses["npm"]
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("devpilot.modules.node.module.which", side_effect=mock_which):
        with patch("devpilot.modules.node.module.run_command", side_effect=mock_run):
            results = module.verify()

    assert len(results) == 3
    assert results[0].passed is True
    assert results[1].passed is True
    assert results[2].passed is True


def test_verify_node_missing() -> None:
    module = NodeModule()

    with patch("devpilot.modules.node.module.which", return_value=None):
        results = module.verify()

    assert results[0].passed is False
    assert results[0].name == "node installed"
    assert results[0].fix is not None


def test_verify_tsc_missing() -> None:
    module = NodeModule()

    def mock_which(program: str) -> MagicMock | None:
        if program in ("node", "npm"):
            return MagicMock()
        return None

    with patch("devpilot.modules.node.module.which", side_effect=mock_which):
        with patch("devpilot.modules.node.module.run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            results = module.verify()

    assert results[2].passed is False
    assert results[2].name == "TypeScript installed"
