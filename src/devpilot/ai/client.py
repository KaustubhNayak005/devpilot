"""OpenAI client wrapper for AI-powered doctor diagnostics and Q&A."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from tenacity import Retrying, stop_after_attempt, wait_exponential

from devpilot.config.manager import ConfigManager

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

console = Console()


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


def _get_api_key() -> str | None:
    """Retrieve the OpenAI API key from environment or config.

    Checks OPENAI_API_KEY env var first, then falls back to
    ~/.config/devpilot/config.yaml key ai.openai_api_key.

    Returns:
        The API key string, or None if not configured.
    """
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key

    try:
        config = ConfigManager()
        return config.get_preference("ai.openai_api_key") or None
    except Exception:
        return None


def _get_client() -> OpenAI:
    """Create an OpenAI client, or exit gracefully if no API key.

    Returns:
        OpenAI client instance, or exits the process if no key is configured.
    """
    api_key = _get_api_key()
    if not api_key:
        console.print(
            Panel.fit(
                "[yellow]AI features require OPENAI_API_KEY. "
                "Set it in your environment or in ~/.config/devpilot/config.yaml[/yellow]",
                border_style="yellow",
            )
        )
        sys.exit(0)
    return OpenAI(api_key=api_key)


def _run_with_retry(client: OpenAI, messages: list[ChatCompletionMessageParam]) -> Any:
    """Call the OpenAI API with retry logic.

    Uses tenacity with 3 attempts and exponential backoff.

    Args:
        client: OpenAI client instance.
        messages: Chat completion messages.

    Returns:
        The API response completion object.

    Raises:
        Exception: If all retries are exhausted.
    """
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    ):
        with attempt:
            return client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
    raise RuntimeError("Unexpected: retry loop exited without result")


def diagnose(
    failures: list[dict[str, str]],
    context: dict[str, Any],
) -> list[DiagnosisResult]:
    """Send failure data and context to OpenAI for diagnosis.

    Args:
        failures: List of failed check dicts with keys: module, check_name, message.
        context: System context dict from gather_context().

    Returns:
        List of DiagnosisResult objects with root cause and suggested fixes.
    """
    client = _get_client()

    prompt = DIAGNOSE_PROMPT.format(
        failures_json=json.dumps(failures, indent=2),
        context_json=json.dumps(context, indent=2),
    )

    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionUserMessageParam(role="user", content=prompt),
    ]

    response = _run_with_retry(client, messages)

    content: str | None = response.choices[0].message.content
    if not content:
        return []

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


def ask(question: str, context: dict[str, Any]) -> str:
    """Send a free-form question with system context to OpenAI and stream the response.

    Args:
        question: The user's question about their dev environment.
        context: System context dict from gather_context().

    Returns:
        The full AI response string.
    """
    client = _get_client()

    prompt = ASK_PROMPT.format(
        context_json=json.dumps(context, indent=2),
        question=question,
    )

    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionUserMessageParam(role="user", content=prompt),
    ]

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        stream=True,
    )

    full_response: str = ""
    with Live(Markdown(""), console=console, refresh_per_second=10) as live:
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
                live.update(Markdown(full_response))

    return full_response
