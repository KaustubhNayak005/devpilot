"""Tests for CLI commands — status, doctor --json/--fail-under, snapshot delete."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from devpilot.cli.main import ALL_MODULES, MODULE_KEY_BINARY, app
from devpilot.modules.base import CheckResult

runner = CliRunner()

FAKE_RESULTS = [
    CheckResult(name="git installed", passed=True, message="git version 2.43"),
    CheckResult(
        name="node installed", passed=False, message="not found", fix="devpilot setup node"
    ),
]


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "DevPilot version" in result.output


class TestStatus:
    def test_status_runs_and_lists_all_modules(self):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        for name in ALL_MODULES:
            assert name in result.output

    def test_every_module_has_a_key_binary(self):
        assert set(MODULE_KEY_BINARY.keys()) >= set(ALL_MODULES.keys())


class TestDoctorJson:
    @patch("devpilot.cli.main.run_all_doctors", return_value=(FAKE_RESULTS, 50))
    def test_json_output_parses(self, mock_run):
        result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["score"] == 50
        assert len(payload["checks"]) == 2
        assert payload["checks"][1]["fix"] == "devpilot setup node"

    @patch("devpilot.cli.main.run_all_doctors", return_value=(FAKE_RESULTS, 50))
    def test_fail_under_exits_nonzero(self, mock_run):
        result = runner.invoke(app, ["doctor", "--json", "--fail-under", "60"])
        assert result.exit_code == 1

    @patch("devpilot.cli.main.run_all_doctors", return_value=(FAKE_RESULTS, 50))
    def test_fail_under_passes_when_met(self, mock_run):
        result = runner.invoke(app, ["doctor", "--json", "--fail-under", "40"])
        assert result.exit_code == 0

    def test_json_rejects_ai(self):
        result = runner.invoke(app, ["doctor", "--json", "--ai"])
        assert result.exit_code == 2

    def test_json_rejects_fix(self):
        result = runner.invoke(app, ["doctor", "--json", "--fix"])
        assert result.exit_code == 2


class TestSnapshotDelete:
    @patch("devpilot.snapshot.storage.delete_snapshot", return_value=2)
    def test_delete_with_yes(self, mock_delete):
        result = runner.invoke(app, ["snapshot", "delete", "mysnap", "--yes"])
        assert result.exit_code == 0
        assert "Deleted 2" in result.output
        mock_delete.assert_called_once_with("mysnap")

    @patch("devpilot.snapshot.storage.delete_snapshot", return_value=0)
    def test_delete_missing_exits_nonzero(self, mock_delete):
        result = runner.invoke(app, ["snapshot", "delete", "nope", "--yes"])
        assert result.exit_code == 1

    @patch("devpilot.snapshot.storage.delete_snapshot")
    def test_delete_aborts_without_confirmation(self, mock_delete):
        result = runner.invoke(app, ["snapshot", "delete", "mysnap"], input="n\n")
        assert result.exit_code == 0
        assert "Aborted" in result.output
        mock_delete.assert_not_called()
