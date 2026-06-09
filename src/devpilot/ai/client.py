"""AI client — public API for diagnostics and Q&A, provider-agnostic."""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel

from devpilot.ai.base import DiagnosisResult

console = Console()


def _check_availability() -> None:
    """Exit gracefully if no AI provider is available."""
    try:
        from devpilot.ai.factory import get_provider

        provider = get_provider()
        if not provider.is_available():
            console.print(
                Panel.fit(
                    "[yellow]AI features require a configured provider. "
                    "Set DEVPILOT_AI_PROVIDER and the corresponding API key "
                    "in your .env file. See .env.example for all options.[/yellow]",
                    border_style="yellow",
                )
            )
            sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        console.print(
            Panel.fit(
                "[yellow]AI features require a configured provider. "
                "Set DEVPILOT_AI_PROVIDER and the corresponding API key "
                "in your .env file.[/yellow]",
                border_style="yellow",
            )
        )
        sys.exit(0)


def diagnose(
    failures: list[dict[str, str]],
    context: dict[str, Any],
) -> list[DiagnosisResult]:
    """Send failure data and context to the configured AI provider for diagnosis.

    Args:
        failures: List of failed check dicts with keys: module, check_name, message.
        context: System context dict from gather_context().

    Returns:
        List of DiagnosisResult objects with root cause and suggested fixes.
    """
    from devpilot.ai.factory import get_provider

    provider = get_provider()
    return provider.diagnose(failures, context)


def ask(question: str, context: dict[str, Any]) -> str:
    """Send a free-form question with system context to the configured AI provider.

    Args:
        question: The user's question about their dev environment.
        context: System context dict from gather_context().

    Returns:
        The full AI response string.
    """
    from devpilot.ai.factory import get_provider

    provider = get_provider()
    return provider.ask(question, context)
