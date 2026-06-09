"""Anthropic provider implementation."""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

from devpilot.ai.base import ASK_PROMPT, DIAGNOSE_PROMPT, AIProvider, DiagnosisResult


class AnthropicProvider(AIProvider):
    """AI provider backed by Anthropic Claude models."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> anthropic.Anthropic:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return anthropic.Anthropic(api_key=self.api_key)

    def _parse_diagnosis_response(self, content: str) -> list[DiagnosisResult]:
        try:
            data: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            return []

        results: list[DiagnosisResult] = []
        for item in data.get("diagnoses", []):
            results.append(
                DiagnosisResult(
                    module_name=item.get("module", "unknown"),
                    root_cause=item.get("root_cause", "No root cause provided."),
                    explanation=item.get("explanation", "No explanation provided."),
                    suggested_fix=item.get("suggested_fix") or None,
                )
            )
        return results

    def diagnose(
        self, failures: list[dict[str, str]], context: dict[str, Any]
    ) -> list[DiagnosisResult]:
        client = self._get_client()

        prompt = DIAGNOSE_PROMPT.format(
            failures_json=json.dumps(failures, indent=2),
            context_json=json.dumps(context, indent=2),
        )

        response = client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        content: str = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        if not content:
            return []

        return self._parse_diagnosis_response(content)

    def ask(self, question: str, context: dict[str, Any]) -> str:
        from rich.console import Console
        from rich.live import Live
        from rich.markdown import Markdown

        client = self._get_client()

        prompt = ASK_PROMPT.format(
            context_json=json.dumps(context, indent=2),
            question=question,
        )

        console = Console()
        full_response: str = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            with client.messages.stream(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    live.update(Markdown(full_response))

        return full_response
