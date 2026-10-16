"""AI Agent タブ: 自然言語 → ツール提案 → Lean 検証 → 説明。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.agent.orchestrator import Agent, AgentRun
from src.agent.tools import AgentContext
from src.ui.components import log, render_lean_result, render_logs

DEMO = "agent"
EXAMPLES = [
    "残高100円から120円送金しても大丈夫？",
    "残高5000円で3000円を送金したい。安全か検証して",
    "Viewer に書き込み権限を付けたら問題ある？",
    "Editor から削除権限を外しておけば安全か確認して",
    "案件Cの必要時間を90時間にして人員配置を最適化して",
]


def render(agent: Agent, available: bool) -> None:
    st.subheader("AI Agent（vLLM + Qwen）")
    st.caption("Qwen は要求文から検証ツールと引数を提案するだけです。"
               "引数は JSON スキーマで検証し、判定は Python + Lean が行います。")
    _render_status(agent, available)
    request = _request_input()
    if st.button("Agent に依頼", key="agent_run", disabled=not available or not request):
        _run(agent, request)
    if run := st.session_state.get("agent_result"):
        render_run(run)
    render_logs(DEMO)


def _render_status(agent: Agent, available: bool) -> None:
    model = getattr(getattr(agent.client, "settings", None), "model", "?")
    if available:
        st.success(f"vLLM 接続中: {model}（モード: {agent.mode}）")
    else:
        st.warning("vLLM に接続できません。Lean 単体デモ（タブ 1〜3）は引き続き利用できます。")


def _request_input() -> str:
    example = st.selectbox("例文", ["（自由入力）", *EXAMPLES], key="agent_example")
    default = "" if example == "（自由入力）" else example
    return st.text_area("要求文", value=default, key=f"agent_text_{example}")


def _run(agent: Agent, request: str) -> None:
    with st.spinner("Agent 実行中..."):
        run = agent.run(request, AgentContext())
    for line in run.log:
        log(DEMO, line)
    st.session_state["agent_result"] = run


def render_run(run: AgentRun) -> None:
    if run.proposal:
        st.markdown(f"**提案されたツール**: `{run.proposal.tool}`（試行 {run.attempts} 回, {run.propose_ms} ms）")
        st.json(run.proposal.arguments)
    for w in run.warnings:
        st.warning(w)
    if run.error:
        st.error(run.error)
        return
    _render_extra(run)
    render_lean_result(run.outcome.result)
    st.markdown("**Qwen による説明**（参考。判定は上の Lean 結果）")
    st.write(run.explanation)


def _render_extra(run: AgentRun) -> None:
    solution = run.outcome.extra.get("solution")
    if solution is not None and solution.has_solution:
        problem = run.outcome.extra["problem"]
        st.metric("OR-Tools", solution.status, help=f"総コスト {solution.total_cost}")
        st.dataframe(pd.DataFrame(solution.hours, index=problem.employees,
                                  columns=problem.projects))
    violations = run.outcome.result.details.get("violations")
    if violations:
        st.write("**検出した違反**", violations)
