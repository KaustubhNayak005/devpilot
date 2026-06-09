"""Abstract base class and shared types for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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


class AIProvider(ABC):
    """Abstract base for all AI providers."""

    @abstractmethod
    def diagnose(
        self, failures: list[dict[str, str]], context: dict[str, Any]
    ) -> list[DiagnosisResult]:
        """Diagnose environment failures and return structured results."""

    @abstractmethod
    def ask(self, question: str, context: dict[str, Any]) -> str:
        """Answer a free-form question about the developer environment."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is configured and reachable."""
