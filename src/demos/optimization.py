"""Demo 3: Verified Optimization — 最適化 + Lean による制約充足検証。"""

from __future__ import annotations

from src.optimization.staffing import (
    StaffingProblem,
    StaffingSolution,
    find_violations,
    shape_ok,
    solve,
    total_cost,
    validate_problem,
)
from src.verification.checks.optimization import staffing_check
from src.verification.results import Status, VerificationResult
from src.verification.verifier import LeanVerifier


def sample_problem() -> StaffingProblem:
    return StaffingProblem(
        employees=["佐藤", "鈴木", "高橋", "田中", "伊藤"],
        projects=["案件A", "案件B", "案件C"],
        capacity=[40, 40, 40, 40, 40],
        demand=[60, 50, 70],
        rate=[50, 45, 60, 40, 55],
        skilled=[[True, True, False], [True, False, True], [False, True, True],
                 [True, True, True], [True, False, True]],
    )


def describe_violation(problem: StaffingProblem, v) -> str:
    if v.kind == "capacity":
        return f"{problem.employees[v.employee]} の稼働時間が上限を超過"
    if v.kind == "demand":
        return f"{problem.projects[v.project]} の必要時間が不足"
    if v.kind == "skill":
        return f"{problem.employees[v.employee]} は {problem.projects[v.project]} のスキル不適合"
    return "割当行列の形状が不正"


class OptimizationDemo:
    def __init__(self, verifier: LeanVerifier, time_limit_sec: float = 10.0) -> None:
        self.verifier = verifier
        self.time_limit_sec = time_limit_sec

    def optimize_staffing(self, problem: StaffingProblem) -> StaffingSolution:
        if validate_problem(problem):
            return StaffingSolution(status="MODEL_INVALID")
        return solve(problem, self.time_limit_sec)

    def verify_staffing(self, problem: StaffingProblem, hours: list[list[int]]) -> VerificationResult:
        errors = validate_problem(problem) + _validate_hours(hours)
        if errors:
            return VerificationResult(Status.ERROR, "入力エラー: " + " / ".join(errors))
        violations = find_violations(problem, hours)
        cost = total_cost(problem, hours) if shape_ok(problem, hours) else 0
        details = {"violations": [describe_violation(problem, v) for v in violations],
                   "total_cost": cost}
        return self.verifier.verify(staffing_check(problem.to_data(hours), cost, violations), details)

    def run(self, problem: StaffingProblem) -> tuple[StaffingSolution, VerificationResult]:
        solution = self.optimize_staffing(problem)
        if solution.status == "INFEASIBLE":
            return solution, _infeasible_result(problem)
        if not solution.has_solution:
            return solution, VerificationResult(Status.ERROR, f"OR-Tools: {solution.status}")
        return solution, self.verify_staffing(problem, solution.hours)


def _validate_hours(hours: list[list[int]]) -> list[str]:
    flat = [v for row in hours for v in row]
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in flat):
        return ["割当時間は 0 以上の整数で指定してください"]
    return []


def _infeasible_result(problem: StaffingProblem) -> VerificationResult:
    demand, capacity = sum(problem.demand), sum(problem.capacity)
    reason = (f"総需要 {demand}h が総稼働可能時間 {capacity}h を超過"
              if demand > capacity else "スキル・稼働上限の組合せで需要を満たせない")
    return VerificationResult(
        Status.INFEASIBLE,
        f"OR-Tools が実行可能解なしと判定（{reason}）。Lean による実行不能性の証明は未対応",
        details={"total_demand": demand, "total_capacity": capacity},
    )
