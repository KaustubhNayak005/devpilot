"""Ollama provider implementation."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import requests

from devpilot.ai.base import AIProvider


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

    def _call_api(self, prompt: str, stream: bool, json_mode: bool = False) -> requests.Response:
        payload: dict[str, str | bool] = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
        }
        if json_mode:
            # Constrains local models to emit valid JSON for diagnosis parsing.
            payload["format"] = "json"
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=stream,
            timeout=120,
        )
        response.raise_for_status()
        return response

    def _complete(self, prompt: str) -> str:
        response = self._call_api(prompt, stream=False, json_mode=True)
        data = response.json()
        return str(data.get("response", ""))

    def _stream(self, prompt: str) -> Iterator[str]:
        response = self._call_api(prompt, stream=True)
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk.get("response"):
                    yield chunk["response"]
