"""OpenAI provider implementation."""

from __future__ import annotations

import os
from collections.abc import Iterator

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from devpilot.ai.base import AIProvider


class OpenAIProvider(AIProvider):
    """AI provider backed by OpenAI GPT models."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> OpenAI:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        return OpenAI(api_key=self.api_key)

    def _messages(self, prompt: str) -> list[ChatCompletionMessageParam]:
        return [ChatCompletionUserMessageParam(role="user", content=prompt)]

    def _complete(self, prompt: str) -> str:
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=self._messages(prompt),
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    def _stream(self, prompt: str) -> Iterator[str]:
        stream = self._get_client().chat.completions.create(
            model=self.model,
            messages=self._messages(prompt),
            temperature=0.3,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
