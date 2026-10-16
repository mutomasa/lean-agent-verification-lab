"""評価用の固定ケース。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo, sample_problem
from src.demos.security import SecurityDemo, default_policy
from src.optimization.staffing import solve
from src.verification.results import Status, VerificationResult


@dataclass(frozen=True)
class LeanCase:
    name: str
    expected: Status
    run: Callable[[], VerificationResult]


@dataclass(frozen=True)
class AgentCase:
    request: str
    tool: str
    expected: Status


def lean_cases(coding: CodingDemo, security: SecurityDemo, opt: OptimizationDemo) -> list[LeanCase]:
    return [*_coding_cases(coding), *_security_cases(security), *_optimization_cases(opt)]


def _coding_cases(d: CodingDemo) -> list[LeanCase]:
    return [
        LeanCase("送金 100→80（正常）", Status.PASS, lambda: d.verify_transfer(100, 80)),
        LeanCase("送金 100→100（境界）", Status.PASS, lambda: d.verify_transfer(100, 100)),
        LeanCase("送金 100→120（違反）", Status.VIOLATION, lambda: d.verify_transfer(100, 120)),
        LeanCase("送金 負の額（違反）", Status.VIOLATION, lambda: d.verify_transfer(100, -10)),
        LeanCase("送金 負の残高（入力エラー）", Status.ERROR, lambda: d.verify_transfer(-1, 0)),
    ]


def _security_cases(d: SecurityDemo) -> list[LeanCase]:
    leaky = {**default_policy(), ("viewer", "write"): True, ("editor", "delete"): True}
    strict = {**default_policy(), ("editor", "write"): False}
    return [
        LeanCase("RBAC 既定（正常）", Status.PASS, lambda: d.verify_rbac(default_policy())),
        LeanCase("RBAC 権限を絞る（正常）", Status.PASS, lambda: d.verify_rbac(strict)),
        LeanCase("RBAC 過剰権限（違反）", Status.VIOLATION, lambda: d.verify_rbac(leaky)),
    ]


def _optimization_cases(d: OptimizationDemo) -> list[LeanCase]:
    p = sample_problem()
    bad = [row[:] for row in solve(p).hours]
    bad[0][2] = 5
    over = dataclasses.replace(p, demand=[100, 100, 100])
    return [
        LeanCase("配置 最適解（正常）", Status.PASS, lambda: d.run(p)[1]),
        LeanCase("配置 手編集（違反）", Status.VIOLATION, lambda: d.verify_staffing(p, bad)),
        LeanCase("配置 需要超過（実行不能）", Status.INFEASIBLE, lambda: d.run(over)[1]),
    ]


AGENT_CASES: list[AgentCase] = [
    AgentCase("残高100円から120円送金しても大丈夫？", "verify_transfer", Status.VIOLATION),
    AgentCase("残高5000円で3000円を送金したい。安全か検証して", "verify_transfer", Status.PASS),
    AgentCase("口座に300円あります。300円全部送っても問題ない？", "verify_transfer", Status.PASS),
    AgentCase("残高50円なのに200円振り込もうとしています。チェックして", "verify_transfer", Status.VIOLATION),
    AgentCase("Viewer に書き込み権限を付けたら問題ある？", "verify_rbac", Status.VIOLATION),
    AgentCase("Editor にも削除権限を与えたい。セキュリティ的に大丈夫？", "verify_rbac", Status.VIOLATION),
    AgentCase("Editor の書き込み権限を外しても安全か確認して", "verify_rbac", Status.PASS),
    AgentCase("今の権限設定がセキュアか検証して", "verify_rbac", Status.PASS),
    AgentCase("案件Cの必要時間を90時間にして人員配置を最適化して", "optimize_staffing", Status.PASS),
    AgentCase("案件Aの工数を70時間に増やした場合の最適な割当を出して", "optimize_staffing", Status.PASS),
    AgentCase("全案件の必要時間を100時間にしたら配置できる？", "optimize_staffing", Status.INFEASIBLE),
    AgentCase("佐藤さんの稼働上限を20時間にして配置を計算して", "optimize_staffing", Status.PASS),
]
