"""vLLM（OpenAI 互換 API）クライアント。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from openai import OpenAI

from config.settings import LLMSettings

# Qwen3 の思考モードを無効化（短い構造化出力を優先）
NO_THINKING = {"chat_template_kwargs": {"enable_thinking": False}}


class LLMUnavailableError(RuntimeError):
    """vLLM に接続できない。"""


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Any


class ChatClient(Protocol):
    def complete(self, messages: list[dict], json_schema: dict | None = None,
                 max_tokens: int = 512) -> str: ...

    def complete_with_tools(self, messages: list[dict], tools: list[dict]) -> ToolCall | None: ...

    def is_available(self) -> bool: ...


class VLLMClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        self._client = OpenAI(base_url=settings.base_url, api_key=settings.api_key,
                              timeout=settings.timeout_sec, max_retries=0)

    def is_available(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:  # noqa: BLE001 - 接続可否のみ判定
            return False

    def complete(self, messages: list[dict], json_schema: dict | None = None,
                 max_tokens: int = 512) -> str:
        kwargs: dict[str, Any] = {}
        if json_schema is not None:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "tool_proposal", "schema": json_schema}}
        resp = self._call(messages=messages, max_tokens=max_tokens, **kwargs)
        return resp.choices[0].message.content or ""

    def complete_with_tools(self, messages: list[dict], tools: list[dict]) -> ToolCall | None:
        resp = self._call(messages=messages, tools=tools, tool_choice="required", max_tokens=512)
        calls = resp.choices[0].message.tool_calls or []
        if not calls:
            return None
        fn = calls[0].function
        return ToolCall(fn.name, _loads_or_raw(fn.arguments))

    def _call(self, **kwargs: Any):
        try:
            return self._client.chat.completions.create(
                model=self.settings.model, temperature=0.1, extra_body=NO_THINKING, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if _is_connection_error(exc):
                raise LLMUnavailableError(f"vLLM に接続できません: {exc}") from exc
            raise


def _loads_or_raw(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text


def _is_connection_error(exc: Exception) -> bool:
    from openai import APIConnectionError, APITimeoutError

    return isinstance(exc, (APIConnectionError, APITimeoutError))
