"""Gemini provider implementation."""

from __future__ import annotations

import os
from collections.abc import Iterator

import google.generativeai as genai

from devpilot.ai.base import AIProvider


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

    def _complete(self, prompt: str) -> str:
        response = self._get_model().generate_content(prompt)
        return response.text or ""

    def _stream(self, prompt: str) -> Iterator[str]:
        response = self._get_model().generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
