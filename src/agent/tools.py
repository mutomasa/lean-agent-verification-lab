"""Agent が呼び出せる許可済みツール（allowlist）。

ツールは検証済みの引数のみを受け取り、デモサービスを呼び出す。
最終判定は常にツール（Python + Lean）が行い、LLM は判定しない。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo, sample_problem
from src.demos.security import SecurityDemo, default_policy
from src.optimization.staffing import StaffingProblem
from src.verification.results import Status, VerificationResult

TOOL_DESCRIPTIONS = {
    "verify_transfer": "送金（残高 balance, 送金額 amount）が安全かを Lean で検証する",
    "verify_rbac": "RBAC 権限表の変更 changes を現在のポリシーに適用し、禁止ルールを Lean で検証する（changes が空なら現在のポリシーを検証）",
    "optimize_staffing": "案件の必要時間 demand_changes・社員の稼働上限 capacity_changes の変更を適用して人員配置を最適化し、解の制約充足を Lean で検証する",
    "verify_staffing": "社員×案件の配置行列 hours が制約を満たすかを Lean で検証する",
    "none": "検証ツールで扱えない要求の場合に理由を返す",
}


@dataclass
class AgentContext:
    """UI の現在状態。ツールはここを基準に変更を適用する。"""

    policy: dict = field(default_factory=default_policy)
    problem: StaffingProblem = field(default_factory=sample_problem)


@dataclass
class ToolOutcome:
    tool: str
    arguments: dict[str, Any]
    result: VerificationResult
    extra: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self, coding: CodingDemo, security: SecurityDemo,
                 optimization: OptimizationDemo) -> None:
        self._handlers: dict[str, Callable[[dict, AgentContext], ToolOutcome]] = {
            "verify_transfer": lambda a, c: self._transfer(coding, a),
            "verify_rbac": lambda a, c: self._rbac(security, a, c),
            "optimize_staffing": lambda a, c: self._optimize(optimization, a, c),
            "verify_staffing": lambda a, c: self._verify_staffing(optimization, a, c),
            "none": lambda a, c: self._none(a),
        }

    @property
    def names(self) -> list[str]:
        return list(self._handlers)

    def execute(self, tool: str, arguments: dict, context: AgentContext) -> ToolOutcome:
        if tool not in self._handlers:
            raise KeyError(f"未登録のツール: {tool}")
        return self._handlers[tool](arguments, context)

    @staticmethod
    def _transfer(demo: CodingDemo, a: dict) -> ToolOutcome:
        return ToolOutcome("verify_transfer", a, demo.verify_transfer(a["balance"], a["amount"]))

    @staticmethod
    def _rbac(demo: SecurityDemo, a: dict, ctx: AgentContext) -> ToolOutcome:
        policy = apply_policy_changes(ctx.policy, a["changes"])
        return ToolOutcome("verify_rbac", a, demo.verify_rbac(policy), {"policy": policy})

    @staticmethod
    def _optimize(demo: OptimizationDemo, a: dict, ctx: AgentContext) -> ToolOutcome:
        problem = apply_problem_changes(ctx.problem, a.get("demand_changes", []),
                                        a.get("capacity_changes", []))
        solution, result = demo.run(problem)
        return ToolOutcome("optimize_staffing", a, result,
                           {"problem": problem, "solution": solution})

    @staticmethod
    def _verify_staffing(demo: OptimizationDemo, a: dict, ctx: AgentContext) -> ToolOutcome:
        return ToolOutcome("verify_staffing", a, demo.verify_staffing(ctx.problem, a["hours"]))

    @staticmethod
    def _none(a: dict) -> ToolOutcome:
        result = VerificationResult(Status.ERROR, f"検証ツール対象外: {a['reason']}")
        return ToolOutcome("none", a, result)


def apply_policy_changes(policy: dict, changes: list[dict]) -> dict:
    updated = dict(policy)
    for c in changes:
        updated[(c["role"], c["action"])] = c["allowed"]
    return updated


def apply_problem_changes(problem: StaffingProblem, demand_changes: list[dict],
                          capacity_changes: list[dict]) -> StaffingProblem:
    demand = _apply_named(problem.projects, problem.demand, demand_changes, "project", "demand")
    capacity = _apply_named(problem.employees, problem.capacity, capacity_changes,
                            "employee", "capacity")
    return dataclasses.replace(problem, demand=demand, capacity=capacity)


def _apply_named(names: list[str], values: list[int], changes: list[dict],
                 key: str, field_name: str) -> list[int]:
    updated = list(values)
    for c in changes:
        if c[key] not in names:
            raise ValueError(f"未知の{key}: {c[key]!r}（候補: {names}）")
        updated[names.index(c[key])] = c[field_name]
    return updated
