"""Regression test: doctor --fix must recompute the score after fixing."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from devpilot.doctor.runner import run_all_doctors
from devpilot.modules.base import BaseModule, CheckResult

FAIL = [CheckResult(name="git check", passed=False, message="missing")]
PASS = [CheckResult(name="git check", passed=True, message="OK")]


@patch("devpilot.doctor.fixes.run_command")
def test_score_reflects_state_after_successful_fix(mock_run):
    """A module that fails, gets fixed, and passes re-check must score 100."""
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    module = MagicMock(spec=BaseModule)
    module.name = "git"
    module.dependencies = []
    # First doctor() run fails; after the fix, the re-run passes.
    module.doctor.side_effect = [list(FAIL), list(PASS)]
    module.verify.return_value = list(PASS)

    with patch("logging.getLogger", return_value=logging.getLogger("test")):
        results, score = run_all_doctors([module], fix=True)

    assert score == 100
    assert all(r.passed for r in results)
    assert module.doctor.call_count == 2


def test_no_rescore_when_everything_passes():
    """fix=True on a healthy system must not trigger a second doctor pass."""
    module = MagicMock(spec=BaseModule)
    module.name = "git"
    module.dependencies = []
    module.doctor.return_value = list(PASS)
    module.verify.return_value = list(PASS)

    results, score = run_all_doctors([module], fix=True)

    assert score == 100
    assert module.doctor.call_count == 1
