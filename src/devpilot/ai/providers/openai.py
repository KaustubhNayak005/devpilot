"""OpenAI provider implementation."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from tenacity import Retrying, stop_after_attempt, wait_exponential

from devpilot.ai.base import ASK_PROMPT, DIAGNOSE_PROMPT, AIProvider, DiagnosisResult


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

    def _run_with_retry(self, client: OpenAI, messages: list[ChatCompletionMessageParam]) -> Any:
        for attempt in Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        ):
            with attempt:
                return client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
        raise RuntimeError("Unexpected: retry loop exited without result")

    def diagnose(
        self, failures: list[dict[str, str]], context: dict[str, Any]
    ) -> list[DiagnosisResult]:
        client = self._get_client()

        prompt = DIAGNOSE_PROMPT.format(
            failures_json=json.dumps(failures, indent=2),
            context_json=json.dumps(context, indent=2),
        )

        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionUserMessageParam(role="user", content=prompt),
        ]

        response = self._run_with_retry(client, messages)

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

    def ask(self, question: str, context: dict[str, Any]) -> str:
        from rich.console import Console
        from rich.live import Live
        from rich.markdown import Markdown

        client = self._get_client()

        prompt = ASK_PROMPT.format(
            context_json=json.dumps(context, indent=2),
            question=question,
        )

        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionUserMessageParam(role="user", content=prompt),
        ]

        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            stream=True,
        )

        console = Console()
        full_response: str = ""
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    live.update(Markdown(full_response))

        return full_response
