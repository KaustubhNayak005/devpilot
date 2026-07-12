"""Tests for devpilot.ai.base — shared parsing, streaming, and retry logic."""

from __future__ import annotations

import json
from collections.abc import Iterator
from unittest.mock import patch

import pytest

from devpilot.ai.base import (
    AIProvider,
    DiagnosisResult,
    parse_diagnosis_response,
    strip_code_fences,
)

VALID_PAYLOAD = {
    "diagnoses": [
        {
            "module": "git",
            "root_cause": "git binary not in PATH",
            "explanation": "Git was not found.",
            "suggested_fix": "sudo apt-get install -y git",
        }
    ]
}


class TestStripCodeFences:
    def test_plain_text_unchanged(self):
        assert strip_code_fences("hello") == "hello"

    def test_strips_bare_fence(self):
        assert strip_code_fences("```\n{}\n```") == "{}"

    def test_strips_language_fence(self):
        assert strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_unterminated_fence(self):
        assert strip_code_fences('```json\n{"a": 1}') == '{"a": 1}'


class TestParseDiagnosisResponse:
    def test_parses_bare_json(self):
        results = parse_diagnosis_response(json.dumps(VALID_PAYLOAD))
        assert len(results) == 1
        assert results[0].module_name == "git"
        assert results[0].suggested_fix == "sudo apt-get install -y git"

    def test_parses_fenced_json(self):
        text = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"
        results = parse_diagnosis_response(text)
        assert len(results) == 1

    def test_parses_json_with_surrounding_prose(self):
        text = f"Here is my diagnosis:\n{json.dumps(VALID_PAYLOAD)}\nHope this helps!"
        results = parse_diagnosis_response(text)
        assert len(results) == 1
        assert results[0].module_name == "git"

    def test_invalid_json_returns_empty(self):
        assert parse_diagnosis_response("not json at all") == []

    def test_non_dict_json_returns_empty(self):
        assert parse_diagnosis_response("[1, 2, 3]") == []

    def test_diagnoses_not_a_list_returns_empty(self):
        assert parse_diagnosis_response('{"diagnoses": "oops"}') == []

    def test_non_dict_items_skipped(self):
        payload = {"diagnoses": ["nope", VALID_PAYLOAD["diagnoses"][0]]}
        results = parse_diagnosis_response(json.dumps(payload))
        assert len(results) == 1

    def test_null_suggested_fix_becomes_none(self):
        payload = {
            "diagnoses": [
                {"module": "x", "root_cause": "r", "explanation": "e", "suggested_fix": None}
            ]
        }
        results = parse_diagnosis_response(json.dumps(payload))
        assert results[0].suggested_fix is None


class FakeProvider(AIProvider):
    """Minimal provider for exercising the template methods."""

    max_attempts = 2

    def __init__(self, replies: list[str | Exception], chunks: list[str] | None = None):
        self.replies = list(replies)
        self.chunks = chunks or []
        self.complete_calls = 0

    def is_available(self) -> bool:
        return True

    def _complete(self, prompt: str) -> str:
        self.complete_calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def _stream(self, prompt: str) -> Iterator[str]:
        yield from self.chunks


class TestAIProviderTemplate:
    def test_diagnose_end_to_end(self):
        provider = FakeProvider([json.dumps(VALID_PAYLOAD)])
        results = provider.diagnose(
            [{"module": "git", "check_name": "git installed", "message": "not found"}],
            {"os_release": {}},
        )
        assert len(results) == 1
        assert isinstance(results[0], DiagnosisResult)

    def test_diagnose_empty_reply_returns_empty(self):
        provider = FakeProvider([""])
        assert provider.diagnose([], {}) == []

    def test_complete_retries_on_failure(self):
        provider = FakeProvider([RuntimeError("boom"), json.dumps(VALID_PAYLOAD)])
        results = provider.diagnose([], {})
        assert provider.complete_calls == 2
        assert len(results) == 1

    def test_complete_reraises_after_max_attempts(self):
        provider = FakeProvider([RuntimeError("boom"), RuntimeError("boom")])
        with pytest.raises(RuntimeError):
            provider.diagnose([], {})
        assert provider.complete_calls == 2

    def test_ask_accumulates_stream(self):
        provider = FakeProvider([], chunks=["Hello", " ", "world"])
        with patch("rich.live.Live"):
            result = provider.ask("question", {})
        assert result == "Hello world"
