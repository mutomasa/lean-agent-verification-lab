"""Demo 2 タブ: Security Policy Verifier。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.demos.security import RULES_TEXT, SecurityDemo, default_policy
from src.verification.checks.security import ACTIONS, ROLES
from src.ui.components import log_result, render_lean_result, render_logs, render_spec

DEMO = "security"


def render(demo: SecurityDemo) -> None:
    st.subheader("Demo 2 — Security Policy Verifier（RBAC）")
    st.markdown("禁止ルール:\n" + "\n".join(f"- {r}" for r in RULES_TEXT))
    edited = st.data_editor(policy_to_frame(default_policy()), key="rbac_editor",
                            disabled=["role"], hide_index=True)
    if st.button("Lean で検証", key="rbac_verify"):
        result = demo.verify_rbac(frame_to_policy(edited))
        log_result(DEMO, result)
        st.session_state["rbac_result"] = result
    if result := st.session_state.get("rbac_result"):
        _render_violations(result.details.get("violations", []))
        render_lean_result(result)
    render_spec("Security.lean")
    render_logs(DEMO)


def policy_to_frame(policy: dict) -> pd.DataFrame:
    rows = [{"role": r, **{a: policy[(r, a)] for a in ACTIONS}} for r in ROLES]
    return pd.DataFrame(rows)


def frame_to_policy(frame: pd.DataFrame) -> dict[tuple[str, str], bool]:
    return {(row["role"], a): bool(row[a]) for _, row in frame.iterrows() for a in ACTIONS}


def _render_violations(violations: list[tuple[str, str]]) -> None:
    if not violations:
        st.write("**検出した違反（Python 列挙）**: なし")
        return
    st.write("**検出した違反（Python 列挙 / Lean で完全一致を検証）**")
    st.table(pd.DataFrame(violations, columns=["role", "action"]))
