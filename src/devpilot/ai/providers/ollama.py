"""Ollama provider implementation."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from devpilot.ai.base import ASK_PROMPT, DIAGNOSE_PROMPT, AIProvider, DiagnosisResult


class OllamaProvider(AIProvider):
    """AI provider backed by a local Ollama instance."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3")

    def is_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return bool(response.status_code == 200)
        except Exception:
            return False

    def _call_api(self, prompt: str, stream: bool = False) -> requests.Response:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
            },
            stream=stream,
            timeout=120,
        )
        response.raise_for_status()
        return response

    def _parse_diagnosis_response(self, text: str) -> list[DiagnosisResult]:
        try:
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
        prompt = DIAGNOSE_PROMPT.format(
            failures_json=json.dumps(failures, indent=2),
            context_json=json.dumps(context, indent=2),
        )

        response = self._call_api(prompt, stream=False)
        data = response.json()
        output: str = data.get("response", "")

        if not output:
            return []

        return self._parse_diagnosis_response(output)

    def ask(self, question: str, context: dict[str, Any]) -> str:
        from rich.console import Console
        from rich.live import Live
        from rich.markdown import Markdown

        prompt = ASK_PROMPT.format(
            context_json=json.dumps(context, indent=2),
            question=question,
        )

        console = Console()
        full_response: str = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            response = self._call_api(prompt, stream=True)
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if chunk.get("response"):
                        full_response += chunk["response"]
                        live.update(Markdown(full_response))

        return full_response
