"""Gemini provider implementation."""

from __future__ import annotations

import json
import os
from typing import Any

import google.generativeai as genai

from devpilot.ai.base import ASK_PROMPT, DIAGNOSE_PROMPT, AIProvider, DiagnosisResult


class GeminiProvider(AIProvider):
    """AI provider backed by Google Gemini models."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_model(self) -> genai.GenerativeModel:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(model_name=self.model_name)

    def _parse_diagnosis_response(self, text: str) -> list[DiagnosisResult]:
        try:
            text = text.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                lines = lines[1:] if lines[0].startswith("```") else lines
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines)
            data: dict[str, Any] = json.loads(text)
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
        model = self._get_model()

        prompt = DIAGNOSE_PROMPT.format(
            failures_json=json.dumps(failures, indent=2),
            context_json=json.dumps(context, indent=2),
        )

        response = model.generate_content(prompt)

        if not response.text:
            return []

        return self._parse_diagnosis_response(response.text)

    def ask(self, question: str, context: dict[str, Any]) -> str:
        from rich.console import Console
        from rich.live import Live
        from rich.markdown import Markdown

        model = self._get_model()

        prompt = ASK_PROMPT.format(
            context_json=json.dumps(context, indent=2),
            question=question,
        )

        console = Console()
        full_response: str = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    live.update(Markdown(full_response))

        return full_response
