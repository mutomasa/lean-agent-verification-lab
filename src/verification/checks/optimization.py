"""Demo 3: 人員配置の制約充足を検証する Lean チェック生成。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.verification.results import Status
from src.verification.source_builder import (
    LeanCheck,
    SourceAssembler,
    lean_bool_list,
    lean_nat,
    lean_nat_list,
)

DECIDE = "by decide +kernel"


@dataclass(frozen=True)
class StaffingData:
    capacity: list[int]
    demand: list[int]
    rate: list[int]
    skilled: list[list[bool]]
    hours: list[list[int]]


@dataclass(frozen=True)
class ConstraintViolation:
    """kind: "capacity" | "demand" | "skill" | "shape" """

    kind: str
    employee: int | None = None
    project: int | None = None


def staffing_check(data: StaffingData, total_cost: int,
                   violations: Sequence[ConstraintViolation]) -> LeanCheck:
    asm = SourceAssembler(imports=["Demo.Optimization"],
                          opens=["Demo.Optimization", "Staffing"])
    asm.define(staffing_definition(data))
    if not violations:
        asm.prove("check_feasible", "sol.Feasible", DECIDE)
        asm.prove("check_cost", f"sol.totalCost = {lean_nat(total_cost)}", DECIDE)
        return asm.build(Status.PASS)
    asm.prove("check_infeasible", "¬ sol.Feasible", DECIDE)
    for idx, v in enumerate(violations):
        asm.prove(f"check_violation_{idx}", violation_statement(v), DECIDE)
    return asm.build(Status.VIOLATION)


def staffing_definition(d: StaffingData) -> str:
    skilled = "[" + ", ".join(lean_bool_list(row) for row in d.skilled) + "]"
    hours = "[" + ", ".join(lean_nat_list(row) for row in d.hours) + "]"
    return (
        "def sol : Staffing := {\n"
        f"  capacity := {lean_nat_list(d.capacity)},\n"
        f"  demand := {lean_nat_list(d.demand)},\n"
        f"  rate := {lean_nat_list(d.rate)},\n"
        f"  skilled := {skilled},\n"
        f"  hours := {hours} }}"
    )


def violation_statement(v: ConstraintViolation) -> str:
    builders = {
        "capacity": lambda: _capacity(v),
        "demand": lambda: _demand(v),
        "skill": lambda: _skill(v),
        "shape": lambda: "¬ sol.WellFormed",
    }
    if v.kind not in builders:
        raise ValueError(f"未知の制約種別: {v.kind!r}")
    return builders[v.kind]()


def _capacity(v: ConstraintViolation) -> str:
    i = lean_nat(_req(v.employee))
    return f"{i} < sol.numEmployees ∧ ¬ (sol.assigned {i} ≤ sol.capacity.getD {i} 0)"


def _demand(v: ConstraintViolation) -> str:
    j = lean_nat(_req(v.project))
    return f"{j} < sol.numProjects ∧ ¬ (sol.demand.getD {j} 0 ≤ sol.covered {j})"


def _skill(v: ConstraintViolation) -> str:
    i, j = lean_nat(_req(v.employee)), lean_nat(_req(v.project))
    return f"0 < sol.h {i} {j} ∧ sol.sk {i} {j} = false"


def _req(value: int | None) -> int:
    if value is None:
        raise ValueError("インデックスが必要です")
    return value
