"""Demo 2: Security Policy Verifier — RBAC 検証サービス。"""

from __future__ import annotations

from collections.abc import Mapping

from src.verification.checks.security import ACTIONS, ROLES, rbac_check
from src.verification.results import Status, VerificationResult
from src.verification.verifier import LeanVerifier

Pair = tuple[str, str]
Policy = Mapping[Pair, bool]

FORBIDDEN: frozenset[Pair] = frozenset({
    ("viewer", "write"), ("viewer", "delete"), ("editor", "delete"),
})

RULES_TEXT = [
    "Viewer は Write / Delete できない",
    "Editor は Delete できない",
    "Delete できるなら Admin である",
]


def default_policy() -> dict[Pair, bool]:
    return {(r, a): (r, a) not in FORBIDDEN for r in ROLES for a in ACTIONS}


def all_pairs() -> list[Pair]:
    """Lean の `violations` と同じ順序（ロール → アクション）。"""
    return [(r, a) for r in ROLES for a in ACTIONS]


def find_violations(policy: Policy) -> list[Pair]:
    """有限な 9 組を列挙し、許可されている禁止組を返す。"""
    return [p for p in all_pairs() if p in FORBIDDEN and policy[p]]


def validate_policy(policy: Policy) -> list[str]:
    missing = [p for p in all_pairs() if p not in policy]
    non_bool = [p for p in all_pairs() if p in policy and not isinstance(policy[p], bool)]
    extra = [p for p in policy if p not in all_pairs()]
    return ([f"未定義: {missing}"] if missing else []) + \
           ([f"bool でない値: {non_bool}"] if non_bool else []) + \
           ([f"未知の組: {extra}"] if extra else [])


class SecurityDemo:
    def __init__(self, verifier: LeanVerifier) -> None:
        self.verifier = verifier

    def verify_rbac(self, policy: Policy) -> VerificationResult:
        errors = validate_policy(policy)
        if errors:
            return VerificationResult(Status.ERROR, "入力エラー: " + " / ".join(errors))
        violations = find_violations(policy)
        details = {"violations": violations, "policy": dict(policy)}
        return self.verifier.verify(rbac_check(policy, violations), details)
