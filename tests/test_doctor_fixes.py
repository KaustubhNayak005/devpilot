"""Tests for devpilot.doctor.fixes — known fix functions and runner integration."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from devpilot.doctor.fixes import (
    FIXES,
    fix_git,
    fix_node,
    fix_python,
    fix_vscode,
)
from devpilot.doctor.runner import run_all_doctors
from devpilot.modules.base import BaseModule, CheckResult


class TestFixFunctions:
    """Tests for individual fix functions."""

    @patch("devpilot.doctor.fixes.run_command")
    def test_fix_git_runs_correct_command(self, mock_run):
        """fix_git installs git via apt."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        logger = logging.getLogger("test")
        result = fix_git(logger)
        assert result is True
        args = mock_run.call_args[0][0]
        assert "git" in args

    @patch("devpilot.doctor.fixes.run_command")
    def test_fix_python_runs_correct_command(self, mock_run):
        """fix_python installs python3 via apt."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        logger = logging.getLogger("test")
        result = fix_python(logger)
        assert result is True
        args = mock_run.call_args[0][0]
        assert "python3" in args

    @patch("devpilot.doctor.fixes.run_command")
    def test_fix_node_runs_correct_command(self, mock_run):
        """fix_node installs nodejs via apt."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        logger = logging.getLogger("test")
        result = fix_node(logger)
        assert result is True
        args = mock_run.call_args[0][0]
        assert "nodejs" in args

    def test_fix_vscode_returns_false(self):
        """fix_vscode always returns False — requires manual install."""
        logger = logging.getLogger("test")
        result = fix_vscode(logger)
        assert result is False

    def test_fixes_registry_has_all_expected_modules(self):
        """FIXES dict has entries for all 6 modules."""
        assert set(FIXES.keys()) == {"git", "python", "node", "ccpp", "vscode", "neovim"}

    def test_fixes_registry_entries_are_callable(self):
        """Every entry in FIXES is a callable function."""
        for name, func in FIXES.items():
            assert callable(func), f"FIXES['{name}'] is not callable"


class TestDoctorWithFix:
    """Tests for run_all_doctors with fix=True."""

    def _make_passing_module(self, name: str) -> BaseModule:
        module = MagicMock(spec=BaseModule)
        module.name = name
        module.dependencies = []
        module.doctor.return_value = [CheckResult(name=f"{name} check", passed=True, message="OK")]
        module.verify.return_value = [CheckResult(name=f"{name} check", passed=True, message="OK")]
        return module

    def _make_failing_module(self, name: str) -> BaseModule:
        module = MagicMock(spec=BaseModule)
        module.name = name
        module.dependencies = []
        module.doctor.return_value = [
            CheckResult(name=f"{name} check", passed=False, message="Missing")
        ]
        module.verify.return_value = [
            CheckResult(name=f"{name} check", passed=False, message="Still missing")
        ]
        return module

    @patch("logging.getLogger")
    @patch("devpilot.doctor.fixes.run_command")
    def test_fix_runs_on_failing_module(self, mock_run, mock_get_logger):
        """When fix=True, the fix function is called for failing modules."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_get_logger.return_value = logging.getLogger("test")

        modules = [self._make_failing_module("git")]
        run_all_doctors(modules, fix=True)

        module = modules[0]
        assert module.verify.call_count >= 1

    def test_passing_module_not_fixed(self):
        """Passing modules are not sent to fix."""
        modules = [self._make_passing_module("git")]
        results, score = run_all_doctors(modules, fix=True)
        assert score == 100

    def test_unknown_module_skipped_in_fix(self):
        """A module without a fix entry is skipped gracefully."""
        module = MagicMock(spec=BaseModule)
        module.name = "unknown_mod"
        module.dependencies = []
        module.doctor.return_value = [CheckResult(name="check", passed=False, message="fail")]
        module.verify.return_value = [
            CheckResult(name="check", passed=False, message="still fails")
        ]

        # Should not raise
        results, score = run_all_doctors([module], fix=True)
        assert score == 0
