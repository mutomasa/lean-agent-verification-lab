"""テスト用の偽物。"""

from __future__ import annotations

from src.agent.client import LLMUnavailableError, ToolCall
from src.verification.results import VerificationResult


class FakeVerifier:
    """Lean を呼ばず、生成したチェックの主張をそのまま返す。"""

    def __init__(self):
        self.checks = []

    def verify(self, check, details=None):
        self.checks.append(check)
        return VerificationResult(check.claim, "fake", lean_source=check.source,
                                  details=details or {})


class ScriptedClient:
    """あらかじめ決めた応答を順に返す LLM。"""

    def __init__(self, responses, tool_calls=None, explanation="説明です"):
        self.responses = list(responses)
        self.tool_calls = list(tool_calls or [])
        self.explanation = explanation
        self.calls = []

    def is_available(self):
        return True

    def complete(self, messages, json_schema=None, max_tokens=512):
        self.calls.append(messages)
        if json_schema is None and messages[0]["content"].startswith("あなたは形式検証の結果"):
            return self.explanation
        return self.responses.pop(0)

    def complete_with_tools(self, messages, tools):
        self.calls.append(messages)
        return self.tool_calls.pop(0)


class DownClient:
    def is_available(self):
        return False

    def complete(self, *a, **k):
        raise LLMUnavailableError("down")

    def complete_with_tools(self, *a, **k):
        raise LLMUnavailableError("down")


__all__ = ["FakeVerifier", "ScriptedClient", "DownClient", "ToolCall"]
