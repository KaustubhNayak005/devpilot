"""Abstract base class and shared types for AI providers.

Providers implement only three primitives — ``is_available``, ``_complete``,
and ``_stream``. The base class builds ``diagnose`` and ``ask`` on top of
them: prompt construction, retry with exponential backoff, JSON parsing
(tolerant of markdown fences and surrounding prose), and live Markdown
rendering of streamed answers.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from tenacity import Retrying, stop_after_attempt, wait_exponential


@dataclass
class DiagnosisResult:
    """AI-generated diagnosis for a failed health check.

    Attributes:
        module_name: Name of the module that failed.
        root_cause: Technical one-sentence root cause.
        explanation: Plain English explanation (2-3 sentences).
        suggested_fix: Single safe shell command, or None if no safe auto-fix.
    """

    module_name: str
    root_cause: str
    explanation: str
    suggested_fix: str | None = None


DIAGNOSE_PROMPT = """
You are a Linux developer environment expert specializing in WSL2 Ubuntu.

The following modules failed their health checks:
{failures_json}

System context:
{context_json}

Respond ONLY with valid JSON in this exact structure:
{{
  "diagnoses": [
    {{
      "module": "<module name>",
      "root_cause": "<one sentence, technical>",
      "explanation": "<2-3 sentences, plain English>",
      "suggested_fix": "<single shell command or null if no safe auto-fix exists>"
    }}
  ]
}}

Rules:
- suggested_fix must be a single safe, non-destructive shell command.
- If the fix requires multiple steps, set suggested_fix to null and explain in explanation.
- Never suggest `rm -rf`, destructive commands, or commands needing sudo
  unless absolutely required.
"""

ASK_PROMPT = """You are a Linux developer environment expert specializing in WSL2 Ubuntu.
You help developers understand their environment and solve problems.

System context:
{context_json}

Answer the following question clearly and concisely. Use Markdown formatting when helpful.
If suggesting commands, format them as inline code blocks.

Question: {question}"""


def strip_code_fences(text: str) -> str:
    """Remove a surrounding markdown code fence from a model reply, if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def parse_diagnosis_response(text: str) -> list[DiagnosisResult]:
    """Parse a model's diagnosis reply into DiagnosisResult objects.

    Tolerates markdown code fences and prose surrounding the JSON object —
    local models in particular rarely reply with bare JSON.

    Args:
        text: Raw model output.

    Returns:
        Parsed results; empty list if no valid JSON could be extracted.
    """
    cleaned = strip_code_fences(text)
    data: Any
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return []
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return []

    if not isinstance(data, dict):
        return []

    results: list[DiagnosisResult] = []
    diagnoses = data.get("diagnoses", [])
    if not isinstance(diagnoses, list):
        return []
    for item in diagnoses:
        if not isinstance(item, dict):
            continue
        results.append(
            DiagnosisResult(
                module_name=item.get("module", "unknown"),
                root_cause=item.get("root_cause", "No root cause provided."),
                explanation=item.get("explanation", "No explanation provided."),
                suggested_fix=item.get("suggested_fix") or None,
            )
        )
    return results


def render_markdown_stream(chunks: Iterable[str]) -> str:
    """Render streamed text chunks as live-updating Markdown in the terminal.

    Args:
        chunks: Iterable of text fragments from a streaming model reply.

    Returns:
        The accumulated full response.
    """
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown

    console = Console()
    full_response = ""
    with Live(Markdown(""), console=console, refresh_per_second=10) as live:
        for chunk in chunks:
            if chunk:
                full_response += chunk
                live.update(Markdown(full_response))
    return full_response


class AIProvider(ABC):
    """Abstract base for all AI providers."""

    #: Retry attempts for non-streaming completions.
    max_attempts: int = 3

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is configured and reachable."""

    @abstractmethod
    def _complete(self, prompt: str) -> str:
        """Return the full text reply for a prompt (used for structured JSON replies)."""

    @abstractmethod
    def _stream(self, prompt: str) -> Iterator[str]:
        """Yield text chunks of the reply for a prompt as they arrive."""

    def diagnose(
        self, failures: list[dict[str, str]], context: dict[str, Any]
    ) -> list[DiagnosisResult]:
        """Diagnose environment failures and return structured results."""
        prompt = DIAGNOSE_PROMPT.format(
            failures_json=json.dumps(failures, indent=2),
            context_json=json.dumps(context, indent=2),
        )
        content = self._complete_with_retry(prompt)
        if not content:
            return []
        return parse_diagnosis_response(content)

    def ask(self, question: str, context: dict[str, Any]) -> str:
        """Answer a free-form question, rendering the reply live as it streams."""
        prompt = ASK_PROMPT.format(
            context_json=json.dumps(context, indent=2),
            question=question,
        )
        return render_markdown_stream(self._stream(prompt))

    def _complete_with_retry(self, prompt: str) -> str:
        for attempt in Retrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        ):
            with attempt:
                return self._complete(prompt)
        return ""  # unreachable — Retrying either returns or reraises
