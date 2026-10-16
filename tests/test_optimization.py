import dataclasses

import pytest

from src.demos.optimization import OptimizationDemo, sample_problem
from src.optimization.staffing import find_violations, solve, total_cost, validate_problem
from src.verification.results import Status


def test_solve_sample_is_optimal_and_satisfies_constraints():
    p = sample_problem()
    sol = solve(p)
    assert sol.status == "OPTIMAL"
    assert find_violations(p, sol.hours) == []
    assert sol.total_cost == total_cost(p, sol.hours)


def test_solve_prefers_cheaper_employee():
    p = dataclasses.replace(sample_problem(), demand=[10, 0, 0])
    sol = solve(p)
    assert sol.hours[3][0] == 10  # 田中（単価40）が最安


def test_infeasible_when_demand_exceeds_capacity():
    p = dataclasses.replace(sample_problem(), demand=[100, 100, 100])
    assert solve(p).status == "INFEASIBLE"


def test_find_violations_kinds():
    p = sample_problem()
    hours = [[50, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
    hours[0][2] = 1  # 佐藤は案件C不適合
    kinds = {v.kind for v in find_violations(p, hours)}
    assert kinds == {"capacity", "demand", "skill"}


def test_shape_violation():
    assert [v.kind for v in find_violations(sample_problem(), [[1, 2, 3]])] == ["shape"]


def test_validate_problem():
    assert validate_problem(dataclasses.replace(sample_problem(), rate=[1])) != []
    assert validate_problem(sample_problem()) == []


@pytest.mark.lean
class TestOptimizationDemo:
    def test_run_pass(self, verifier):
        sol, r = OptimizationDemo(verifier).run(sample_problem())
        assert sol.status == "OPTIMAL" and r.status == Status.PASS
        assert r.details["total_cost"] == sol.total_cost

    def test_solution_is_reflected_in_lean(self, verifier):
        sol, r = OptimizationDemo(verifier).run(sample_problem())
        hours = "[" + ", ".join("[" + ", ".join(map(str, row)) + "]" for row in sol.hours) + "]"
        assert f"hours := {hours}" in r.lean_source

    def test_manual_edit_violation(self, verifier):
        p = sample_problem()
        sol = solve(p)
        hours = [row[:] for row in sol.hours]
        hours[0][2] = 5
        r = OptimizationDemo(verifier).verify_staffing(p, hours)
        assert r.status == Status.VIOLATION
        assert any("スキル不適合" in v for v in r.details["violations"])

    def test_infeasible(self, verifier):
        p = dataclasses.replace(sample_problem(), demand=[100, 100, 100])
        sol, r = OptimizationDemo(verifier).run(p)
        assert r.status == Status.INFEASIBLE and "超過" in r.summary

    def test_negative_hours_is_error(self, verifier):
        r = OptimizationDemo(verifier).verify_staffing(sample_problem(), [[-1, 0, 0]] * 5)
        assert r.status == Status.ERROR
