"""Tests for devpilot.ai.context and devpilot.ai.client."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

from devpilot.ai.base import DiagnosisResult
from devpilot.ai.client import ask, diagnose
from devpilot.ai.context import _get_path_entries, _read_os_release, gather_context


class TestContext:
    """Tests for system context gathering."""

    def test_read_os_release_parses_correctly(self, tmp_path):
        """_read_os_release parses a valid os-release file."""
        os_release = tmp_path / "os-release"
        os_release.write_text(
            'ID=ubuntu\nVERSION_ID="22.04"\nPRETTY_NAME="Ubuntu 22.04.3 LTS"\n',
            encoding="utf-8",
        )
        with patch("devpilot.ai.context.Path") as mock_path:
            mock_path.return_value.read_text.return_value = os_release.read_text(encoding="utf-8")
            result = _read_os_release()
        assert result.get("ID") == "ubuntu"
        assert result.get("VERSION_ID") == "22.04"

    def test_read_os_release_file_missing(self):
        """_read_os_release returns empty dict when file is missing."""
        with patch("devpilot.ai.context.Path") as mock_path:
            mock_path.return_value.read_text.side_effect = OSError("No such file")
            result = _read_os_release()
        assert result == {}

    def test_get_path_entries_returns_list(self):
        """_get_path_entries returns a list of path strings."""
        with patch.dict(os.environ, {"PATH": "/usr/bin:/bin:/usr/local/bin"}):
            result = _get_path_entries()
        assert isinstance(result, list)
        assert "/usr/bin" in result

    def test_get_path_entries_missing_key(self):
        """_get_path_entries returns empty list when PATH is not set."""
        with patch.dict(os.environ, clear=True):
            result = _get_path_entries()
        assert result == []

    def test_gather_context_returns_expected_keys(self):
        """gather_context returns a dict with all expected top-level keys."""
        with (
            patch("devpilot.ai.context._read_os_release", return_value={"ID": "ubuntu"}),
            patch("devpilot.ai.context._get_path_entries", return_value=["/usr/bin"]),
            patch("devpilot.ai.context._get_relevant_env", return_value={}),
            patch("devpilot.ai.context._get_installed_packages", return_value=["git"]),
        ):
            result = gather_context()
        assert "os_release" in result
        assert "path_entries" in result
        assert "relevant_env" in result
        assert "installed_packages" in result

    def test_gather_context_survives_failures(self):
        """gather_context returns partial data when a step fails."""
        with (
            patch("devpilot.ai.context._read_os_release", side_effect=Exception("boom")),
            patch("devpilot.ai.context._get_path_entries", return_value=["/usr/bin"]),
            patch("devpilot.ai.context._get_relevant_env", return_value={}),
            patch("devpilot.ai.context._get_installed_packages", side_effect=Exception("boom")),
        ):
            result = gather_context()
        assert result["path_entries"] == ["/usr/bin"]


class TestClient:
    """Tests for AI client functions."""

    def test_diagnose_parses_valid_response(self):
        """diagnose returns a list of DiagnosisResult from a valid JSON response."""
        fake_response_data = {
            "diagnoses": [
                {
                    "module": "git",
                    "root_cause": "git binary not in PATH",
                    "explanation": "Git was not found. You need to install it.",
                    "suggested_fix": "sudo apt-get install -y git",
                }
            ]
        }
        fake_choice = MagicMock()
        fake_choice.message.content = json.dumps(fake_response_data)
        fake_response = MagicMock()
        fake_response.choices = [fake_choice]

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch("devpilot.ai.providers.openai.OpenAI") as mock_openai,
        ):
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = fake_response
            mock_openai.return_value = mock_client

            results = diagnose(
                [{"module": "git", "check_name": "git installed", "message": "not found"}],
                {
                    "os_release": {},
                    "path_entries": [],
                    "relevant_env": {},
                    "installed_packages": [],
                },
            )

        assert len(results) == 1
        assert isinstance(results[0], DiagnosisResult)
        assert results[0].module_name == "git"
        assert results[0].suggested_fix == "sudo apt-get install -y git"

    def test_diagnose_handles_empty_response(self):
        """diagnose returns empty list when API response is empty."""
        fake_choice = MagicMock()
        fake_choice.message.content = None
        fake_response = MagicMock()
        fake_response.choices = [fake_choice]

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch("devpilot.ai.providers.openai.OpenAI") as mock_openai,
        ):
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = fake_response
            mock_openai.return_value = mock_client

            results = diagnose([], {})

        assert results == []

    def test_diagnose_handles_invalid_json(self):
        """diagnose returns empty list when response is not valid JSON."""
        fake_choice = MagicMock()
        fake_choice.message.content = "not valid json"
        fake_response = MagicMock()
        fake_response.choices = [fake_choice]

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch("devpilot.ai.providers.openai.OpenAI") as mock_openai,
        ):
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = fake_response
            mock_openai.return_value = mock_client

            results = diagnose([], {})

        assert results == []

    def test_ask_returns_response(self):
        """ask returns the streamed response as a string."""
        fake_chunk1 = MagicMock()
        fake_chunk1.choices = [MagicMock()]
        fake_chunk1.choices[0].delta.content = "Hello"
        fake_chunk2 = MagicMock()
        fake_chunk2.choices = [MagicMock()]
        fake_chunk2.choices[0].delta.content = " world!"

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch("devpilot.ai.providers.openai.OpenAI") as mock_openai,
            patch("rich.live.Live") as mock_live,
        ):
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = [fake_chunk1, fake_chunk2]
            mock_openai.return_value = mock_client

            mock_live_instance = MagicMock()
            mock_live.return_value.__enter__.return_value = mock_live_instance

            result = ask("test question", {})

        assert "Hello" in result
        assert "world!" in result


