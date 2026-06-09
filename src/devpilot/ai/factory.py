"""Provider factory — selects the configured AI provider."""

from __future__ import annotations

import os

from devpilot.ai.base import AIProvider


def _try_import_openai():
    from devpilot.ai.providers.openai import OpenAIProvider

    return OpenAIProvider


def _try_import_anthropic():
    from devpilot.ai.providers.anthropic import AnthropicProvider

    return AnthropicProvider


def _try_import_gemini():
    from devpilot.ai.providers.gemini import GeminiProvider

    return GeminiProvider


def _try_import_ollama():
    from devpilot.ai.providers.ollama import OllamaProvider

    return OllamaProvider


def get_provider() -> AIProvider:
    """Return the configured AI provider based on DEVPILOT_AI_PROVIDER env var.

    Falls back to the first available provider if the env var is not set.
    Raises SystemExit with a helpful message if no provider is available.
    """
    providers: dict[str, AIProvider] = {}

    for name, importer in [
        ("openai", _try_import_openai),
        ("anthropic", _try_import_anthropic),
        ("gemini", _try_import_gemini),
        ("ollama", _try_import_ollama),
    ]:
        try:
            providers[name] = importer()()
        except ImportError:
            continue

    if not providers:
        print(
            "[red]No AI provider could be loaded.[/red]\n"
            "Install at least one: pip install openai anthropic google-generativeai\n"
            "Or install ollama locally for the ollama provider."
        )
        raise SystemExit(1)

    requested = os.environ.get("DEVPILOT_AI_PROVIDER", "").lower()

    if requested:
        if requested not in providers:
            print(
                f"[red]Unknown or unavailable provider: {requested}. "
                f"Available: {', '.join(providers)}"
            )
            raise SystemExit(1)
        provider = providers[requested]
        if not provider.is_available():
            print(f"[red]Provider '{requested}' is not configured. " "Check your .env file.")
            raise SystemExit(1)
        return provider

    # Auto-detect: return first available
    for name, provider in providers.items():
        if provider.is_available():
            return provider

    print(
        "[red]No AI provider configured.[/red]\n"
        "Set DEVPILOT_AI_PROVIDER and the corresponding API key in your .env file.\n"
        "See .env.example for all options."
    )
    raise SystemExit(1)
