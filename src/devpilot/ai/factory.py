"""Provider factory — selects the configured AI provider."""

from __future__ import annotations

import os

from devpilot.ai.base import AIProvider


def get_provider() -> AIProvider:
    """Return the configured AI provider based on DEVPILOT_AI_PROVIDER env var.

    Falls back to the first available provider if the env var is not set.
    Raises SystemExit with a helpful message if no provider is available.
    """
    from devpilot.ai.providers.anthropic import AnthropicProvider
    from devpilot.ai.providers.gemini import GeminiProvider
    from devpilot.ai.providers.ollama import OllamaProvider
    from devpilot.ai.providers.openai import OpenAIProvider

    requested = os.environ.get("DEVPILOT_AI_PROVIDER", "").lower()

    providers: dict[str, AIProvider] = {
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "gemini": GeminiProvider(),
        "ollama": OllamaProvider(),
    }

    if requested:
        if requested not in providers:
            print(f"[red]Unknown provider: {requested}. " f"Choose from: {', '.join(providers)}")
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
