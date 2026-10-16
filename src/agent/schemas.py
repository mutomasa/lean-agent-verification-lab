"""Agent が提案するツール呼び出しの JSON スキーマと検証。

LLM の出力はこのスキーマで検証してから Python 側で実行する。
スキーマに合わない出力は実行しない。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from src.verification.checks.security import ACTIONS, ROLES

NAT = {"type": "integer", "minimum": 0}
INT = {"type": "integer", "minimum": -(10**12), "maximum": 10**12}

VERIFY_TRANSFER = {
    "type": "object",
    "properties": {"balance": INT, "amount": INT},
    "required": ["balance", "amount"],
    "additionalProperties": False,
}

VERIFY_RBAC = {
    "type": "object",
    "properties": {"changes": {"type": "array", "maxItems": 9, "items": {
        "type": "object",
        "properties": {"role": {"enum": list(ROLES)}, "action": {"enum": list(ACTIONS)},
                       "allowed": {"type": "boolean"}},
        "required": ["role", "action", "allowed"],
        "additionalProperties": False,
    }}},
    "required": ["changes"],
    "additionalProperties": False,
}

OPTIMIZE_STAFFING = {
    "type": "object",
    "properties": {
        "demand_changes": {"type": "array", "maxItems": 20, "items": {
            "type": "object",
            "properties": {"project": {"type": "string", "maxLength": 50}, "demand": NAT},
            "required": ["project", "demand"], "additionalProperties": False}},
        "capacity_changes": {"type": "array", "maxItems": 20, "items": {
            "type": "object",
            "properties": {"employee": {"type": "string", "maxLength": 50}, "capacity": NAT},
            "required": ["employee", "capacity"], "additionalProperties": False}},
    },
    "required": [],
    "additionalProperties": False,
}

VERIFY_STAFFING = {
    "type": "object",
    "properties": {"hours": {"type": "array", "maxItems": 20,
                             "items": {"type": "array", "maxItems": 20, "items": NAT}}},
    "required": ["hours"],
    "additionalProperties": False,
}

NO_TOOL = {
    "type": "object",
    "properties": {"reason": {"type": "string", "maxLength": 500}},
    "required": ["reason"],
    "additionalProperties": False,
}

TOOL_SCHEMAS: dict[str, dict] = {
    "verify_transfer": VERIFY_TRANSFER,
    "verify_rbac": VERIFY_RBAC,
    "optimize_staffing": OPTIMIZE_STAFFING,
    "verify_staffing": VERIFY_STAFFING,
    "none": NO_TOOL,
}


@dataclass(frozen=True)
class ToolProposal:
    tool: str
    arguments: dict[str, Any]


class ProposalError(ValueError):
    """LLM の出力がスキーマに合わない。"""


def proposal_schema(tool_names: list[str]) -> dict:
    """ツール名と引数をまとめた応答スキーマ（構造化出力用）。"""
    return {"anyOf": [{
        "type": "object",
        "properties": {"tool": {"const": name}, "arguments": TOOL_SCHEMAS[name]},
        "required": ["tool", "arguments"],
        "additionalProperties": False,
    } for name in tool_names]}


def validate_proposal(data: Any, allowed_tools: list[str]) -> ToolProposal:
    if not isinstance(data, dict) or set(data) != {"tool", "arguments"}:
        raise ProposalError('{"tool": ..., "arguments": {...}} の形式で出力してください')
    tool = data["tool"]
    if tool not in allowed_tools:
        raise ProposalError(f"許可されていないツールです: {tool!r}（利用可能: {allowed_tools}）")
    validate_arguments(tool, data["arguments"])
    return ToolProposal(tool, data["arguments"])


def validate_arguments(tool: str, arguments: Any) -> None:
    errors = sorted(Draft202012Validator(TOOL_SCHEMAS[tool]).iter_errors(arguments),
                    key=lambda e: list(e.path))
    if errors:
        msgs = "; ".join(f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors)
        raise ProposalError(f"{tool} の引数が不正です: {msgs}")


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json_text(text: str) -> Any:
    """LLM の応答テキストから JSON を取り出す（思考ブロック・コードフェンス対応）。"""
    cleaned = _THINK_RE.sub("", text).strip()
    fence = _FENCE_RE.search(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ProposalError("JSON オブジェクトが見つかりません")
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ProposalError(f"JSON として解析できません: {exc}") from exc
