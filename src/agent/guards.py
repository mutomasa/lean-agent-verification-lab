"""LLM 出力の事後チェック（スキーマ検証では捕まらない誤りの検出）。"""

from __future__ import annotations

import re
from typing import Any

from src.verification.results import Status

# 数値の根拠チェックを行うツール（verify_staffing は行列全体を渡すため対象外）
GROUNDED_TOOLS = frozenset({"verify_transfer", "optimize_staffing"})

# ステータスと矛盾する表現
CONTRADICTIONS: dict[Status, tuple[str, ...]] = {
    Status.PASS: ("違反", "証明できな", "許可されていません", "許可されません", "できません", "危険", "安全ではありません"),
    Status.VIOLATION: ("証明できな", "問題ありません", "安全です", "満たすことを証明"),
    Status.PROOF_FAILED: ("違反が見つか", "違反を証明", "安全です"),
}

_NUM_RE = re.compile(r"-?\d+")


def ungrounded_numbers(tool: str, request: str, arguments: Any) -> list[int]:
    """引数中の整数のうち、要求文に現れないものを返す。"""
    if tool not in GROUNDED_TOOLS:
        return []
    in_request = {int(n) for n in _NUM_RE.findall(_normalize_digits(request))}
    return [n for n in _ints(arguments) if n not in in_request]


def explanation_consistent(status: Status, text: str) -> bool:
    return not any(word in text for word in CONTRADICTIONS.get(status, ()))


def _ints(value: Any) -> list[int]:
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _ints(v)]
    if isinstance(value, list):
        return [n for v in value for n in _ints(v)]
    return []


def _normalize_digits(text: str) -> str:
    return text.translate(str.maketrans("０１２３４５６７８９－", "0123456789-")).replace(",", "").replace("，", "")
