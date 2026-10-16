"""Demo 3 タブ: Verified Optimization。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.demos.optimization import OptimizationDemo, sample_problem
from src.optimization.staffing import StaffingProblem, total_cost
from src.ui.components import log, log_result, render_lean_result, render_logs, render_spec

DEMO = "optimization"


def render(demo: OptimizationDemo) -> None:
    st.subheader("Demo 3 — Verified Optimization（人員配置）")
    st.caption("OR-Tools CP-SAT で配置を求め、その具体解が制約を満たすことを Lean で検証します。"
               "最適性は OR-Tools のステータス表示のみで、Lean では証明しません。")
    problem = _problem_editor()
    if st.button("最適化して Lean で検証", key="opt_run"):
        _run(demo, problem)
    _render_solution(demo, problem)
    render_spec("Optimization.lean")
    render_logs(DEMO)


def _problem_editor() -> StaffingProblem:
    base = sample_problem()
    st.markdown("**社員**（稼働上限 h / 時間単価 / スキル適合）")
    emp = st.data_editor(employees_frame(base), key="opt_employees", hide_index=True)
    st.markdown("**案件**（必要時間 h）")
    proj = st.data_editor(projects_frame(base), key="opt_projects", hide_index=True,
                          disabled=["project"])
    return frames_to_problem(emp, proj, base.projects)


def employees_frame(p: StaffingProblem) -> pd.DataFrame:
    rows = [{"employee": e, "capacity": p.capacity[i], "rate": p.rate[i],
             **{proj: p.skilled[i][j] for j, proj in enumerate(p.projects)}}
            for i, e in enumerate(p.employees)]
    return pd.DataFrame(rows)


def projects_frame(p: StaffingProblem) -> pd.DataFrame:
    return pd.DataFrame({"project": p.projects, "demand": p.demand})


def frames_to_problem(emp: pd.DataFrame, proj: pd.DataFrame, projects: list[str]) -> StaffingProblem:
    return StaffingProblem(
        employees=[str(e) for e in emp["employee"]],
        projects=list(projects),
        capacity=[int(v) for v in emp["capacity"]],
        demand=[int(v) for v in proj["demand"]],
        rate=[int(v) for v in emp["rate"]],
        skilled=[[bool(row[p]) for p in projects] for _, row in emp.iterrows()],
    )


def hours_frame(problem: StaffingProblem, hours: list[list[int]]) -> pd.DataFrame:
    return pd.DataFrame(hours, index=problem.employees, columns=problem.projects)


def _run(demo: OptimizationDemo, problem: StaffingProblem) -> None:
    solution, result = demo.run(problem)
    log(DEMO, f"OR-Tools: {solution.status} ({solution.wall_time_ms} ms)")
    log_result(DEMO, result)
    run_id = st.session_state.get("opt_state", {}).get("run_id", 0) + 1
    st.session_state["opt_state"] = {"solution": solution, "result": result,
                                     "problem": problem, "run_id": run_id}


def _render_solution(demo: OptimizationDemo, problem: StaffingProblem) -> None:
    state = st.session_state.get("opt_state")
    if not state:
        return
    solution, result = state["solution"], state["result"]
    st.metric("OR-Tools ステータス", solution.status)
    if solution.has_solution:
        result = _render_assignment(demo, state, solution) or result
    _render_violations(result.details.get("violations", []))
    render_lean_result(result)


def _render_assignment(demo: OptimizationDemo, state: dict, solution):
    problem = state["problem"]
    st.markdown("**配置行列 hours[社員, 案件]**（編集して再検証できます）")
    # 再最適化のたびに編集状態をリセットするため run_id をキーに含める
    edited = st.data_editor(hours_frame(problem, solution.hours),
                            key=f"opt_hours_{state['run_id']}")
    hours = [[int(v) for v in row] for row in edited.to_numpy().tolist()]
    st.metric("総コスト", total_cost(problem, hours), help=f"OR-Tools 最適値: {solution.total_cost}")
    if st.button("編集した配置を Lean で検証", key="opt_reverify"):
        result = demo.verify_staffing(problem, hours)
        log_result(DEMO, result)
        st.session_state["opt_state"]["result"] = result
        return result
    return None


def _render_violations(violations: list[str]) -> None:
    if violations:
        st.write("**検出した制約違反（Python 列挙 / 各違反を Lean で証明）**")
        st.write("\n".join(f"- {v}" for v in violations))
