"""Tests for devpilot.doctor.runner."""

from __future__ import annotations

from devpilot.doctor.runner import run_all_doctors
from devpilot.modules.base import BaseModule, CheckResult


class _AllPassingModule(BaseModule):
    """A test module whose doctor always passes."""

    name: str = "test-all-pass"

    def install(self) -> bool:
        return True

    def verify(self) -> list[CheckResult]:
        return [
            CheckResult(name="check a", passed=True, message="ok"),
            CheckResult(name="check b", passed=True, message="ok"),
        ]

    def doctor(self) -> list[CheckResult]:
        return self.verify()


class _AllFailingModule(BaseModule):
    """A test module whose doctor always fails."""

    name: str = "test-all-fail"

    def install(self) -> bool:
        return False

    def verify(self) -> list[CheckResult]:
        return [
            CheckResult(name="check x", passed=False, message="broken", fix="do something"),
            CheckResult(name="check y", passed=False, message="also broken", fix="do more"),
        ]

    def doctor(self) -> list[CheckResult]:
        return self.verify()


class _MixedModule(BaseModule):
    """A test module whose doctor has mixed results."""

    name: str = "test-mixed"

    def install(self) -> bool:
        return True

    def verify(self) -> list[CheckResult]:
        return [
            CheckResult(name="good check", passed=True, message="ok"),
            CheckResult(name="bad check", passed=False, message="nope", fix="fix it"),
        ]

    def doctor(self) -> list[CheckResult]:
        return self.verify()


def test_run_all_doctors_all_passing() -> None:
    """Health score is 100 when everything passes."""
    modules = [_AllPassingModule()]
    results, score = run_all_doctors(modules)
    assert len(results) == 2
    assert score == 100


def test_run_all_doctors_all_failing() -> None:
    """Health score is 0 when everything fails."""
    modules = [_AllFailingModule()]
    results, score = run_all_doctors(modules)
    assert len(results) == 2
    assert score == 0


def test_run_all_doctors_mixed() -> None:
    """Health score reflects the proportion of passing checks."""
    modules = [_AllPassingModule(), _AllFailingModule()]
    results, score = run_all_doctors(modules)
    assert len(results) == 4
    assert score == 50


def test_run_all_doctors_empty_modules() -> None:
    """Health score is 100 when there are no modules to check."""
    results, score = run_all_doctors([])
    assert results == []
    assert score == 100


def test_run_all_doctors_mixed_single_module() -> None:
    """Single module with mixed checks yields correct score."""
    modules = [_MixedModule()]
    results, score = run_all_doctors(modules)
    assert len(results) == 2
    assert score == 50
