"""Anthropic provider implementation."""

from __future__ import annotations

import os
from collections.abc import Iterator

import anthropic

from devpilot.ai.base import AIProvider


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

    def _complete(self, prompt: str) -> str:
        response = self._get_client().messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def _stream(self, prompt: str) -> Iterator[str]:
        client = self._get_client()
        with client.messages.stream(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            yield from stream.text_stream
