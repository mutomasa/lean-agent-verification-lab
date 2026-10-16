"""Demo 2: RBAC 検証の Lean チェック生成。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.verification.results import Status
from src.verification.source_builder import LeanCheck, SourceAssembler, lean_bool

ROLES: tuple[str, ...] = ("admin", "editor", "viewer")
ACTIONS: tuple[str, ...] = ("read", "write", "delete")
DECIDE = "by decide +kernel"

Policy = Mapping[tuple[str, str], bool]
Pair = tuple[str, str]


def rbac_check(policy: Policy, violations: Sequence[Pair]) -> LeanCheck:
    """ユーザー編集後のポリシーと、Python が列挙した違反一覧を Lean で検証する。

    違反一覧は「完全に一致すること」まで Lean で証明する。
    """
    asm = SourceAssembler(imports=["Demo.Security"], opens=["Demo.Security"])
    asm.define(policy_definition(policy))
    asm.prove("check_violations", f"violations userPolicy = {_lean_pairs(violations)}", DECIDE)
    if not violations:
        asm.prove("check_secure", "Secure userPolicy",
                  f"checkSecure_sound userPolicy ({DECIDE})")
        return asm.build(Status.PASS)
    asm.prove("check_not_secure", "¬ Secure userPolicy",
              f"not_secure_of_violations userPolicy ({DECIDE})")
    return asm.build(Status.VIOLATION)


def policy_definition(policy: Policy) -> str:
    arms = "\n".join(
        f"    | .{_role(r)}, .{_action(a)} => {lean_bool(policy[(r, a)])}"
        for r in ROLES for a in ACTIONS
    )
    return f"def userPolicy : Policy := ⟨fun r a =>\n  match r, a with\n{arms}⟩"


def _lean_pairs(pairs: Sequence[Pair]) -> str:
    return "[" + ", ".join(f"(.{_role(r)}, .{_action(a)})" for r, a in pairs) + "]"


def _role(name: str) -> str:
    if name not in ROLES:
        raise ValueError(f"未知のロール: {name!r}")
    return name


def _action(name: str) -> str:
    if name not in ACTIONS:
        raise ValueError(f"未知のアクション: {name!r}")
    return name
