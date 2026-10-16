"""OR-Tools CP-SAT による人員配置（整数時間の割当）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from src.verification.checks.optimization import ConstraintViolation, StaffingData


@dataclass(frozen=True)
class StaffingProblem:
    employees: list[str]
    projects: list[str]
    capacity: list[int]
    demand: list[int]
    rate: list[int]
    skilled: list[list[bool]]

    def to_data(self, hours: list[list[int]]) -> StaffingData:
        return StaffingData(capacity=list(self.capacity), demand=list(self.demand),
                            rate=list(self.rate), skilled=[list(r) for r in self.skilled],
                            hours=[list(r) for r in hours])


@dataclass
class StaffingSolution:
    status: str
    hours: list[list[int]] = field(default_factory=list)
    total_cost: int | None = None
    wall_time_ms: int = 0

    @property
    def has_solution(self) -> bool:
        return self.status in ("OPTIMAL", "FEASIBLE")


def validate_problem(p: StaffingProblem) -> list[str]:
    n, m = len(p.employees), len(p.projects)
    errors = []
    if not (len(p.capacity) == len(p.rate) == len(p.skilled) == n):
        errors.append("社員ごとのデータ数が一致しません")
    if len(p.demand) != m or any(len(r) != m for r in p.skilled):
        errors.append("案件ごとのデータ数が一致しません")
    if any(v < 0 for v in [*p.capacity, *p.demand, *p.rate]):
        errors.append("稼働上限・需要・単価は 0 以上の整数で指定してください")
    return errors


def solve(problem: StaffingProblem, time_limit_sec: float = 10.0) -> StaffingSolution:
    model = cp_model.CpModel()
    x = _add_variables(model, problem)
    _add_constraints(model, problem, x)
    model.minimize(_cost_expr(problem, x))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_sec
    status = solver.solve(model)
    return _to_solution(solver, status, x)


def _add_variables(model: cp_model.CpModel, p: StaffingProblem) -> list[list[cp_model.IntVar]]:
    return [[model.new_int_var(0, p.capacity[i] if p.skilled[i][j] else 0, f"h_{i}_{j}")
             for j in range(len(p.projects))] for i in range(len(p.employees))]


def _add_constraints(model: cp_model.CpModel, p: StaffingProblem, x) -> None:
    for i, row in enumerate(x):
        model.add(sum(row) <= p.capacity[i])
    for j, need in enumerate(p.demand):
        model.add(sum(x[i][j] for i in range(len(x))) >= need)


def _cost_expr(p: StaffingProblem, x):
    return sum(p.rate[i] * v for i, row in enumerate(x) for v in row)


def _to_solution(solver: cp_model.CpSolver, status, x) -> StaffingSolution:
    name = solver.status_name(status)
    wall = int(solver.wall_time * 1000)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return StaffingSolution(status=name, wall_time_ms=wall)
    hours = [[int(solver.value(v)) for v in row] for row in x]
    return StaffingSolution(name, hours, int(solver.objective_value), wall)


def assigned(hours: list[list[int]], i: int) -> int:
    return sum(hours[i])


def covered(hours: list[list[int]], j: int) -> int:
    return sum(row[j] for row in hours)


def total_cost(problem: StaffingProblem, hours: list[list[int]]) -> int:
    return sum(problem.rate[i] * assigned(hours, i) for i in range(len(hours)))


def shape_ok(problem: StaffingProblem, hours: list[list[int]]) -> bool:
    return len(hours) == len(problem.employees) and all(
        len(row) == len(problem.projects) for row in hours)


def find_violations(problem: StaffingProblem, hours: list[list[int]]) -> list[ConstraintViolation]:
    """具体的な割当に対する制約違反を列挙する（Lean で独立に検証される）。"""
    if not shape_ok(problem, hours):
        return [ConstraintViolation("shape")]
    return [*_capacity_violations(problem, hours), *_demand_violations(problem, hours),
            *_skill_violations(problem, hours)]


def _capacity_violations(p: StaffingProblem, hours) -> list[ConstraintViolation]:
    return [ConstraintViolation("capacity", employee=i)
            for i in range(len(hours)) if assigned(hours, i) > p.capacity[i]]


def _demand_violations(p: StaffingProblem, hours) -> list[ConstraintViolation]:
    return [ConstraintViolation("demand", project=j)
            for j in range(len(p.projects)) if covered(hours, j) < p.demand[j]]


def _skill_violations(p: StaffingProblem, hours) -> list[ConstraintViolation]:
    return [ConstraintViolation("skill", i, j)
            for i, row in enumerate(hours) for j, h in enumerate(row)
            if h > 0 and not p.skilled[i][j]]
