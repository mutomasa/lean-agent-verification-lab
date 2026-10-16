"""Demo 1 タブ: Verified Coding。"""

from __future__ import annotations

import streamlit as st

from src.demos.coding import RULE_TEXT, CodingDemo
from src.ui.components import log_result, render_lean_result, render_logs, render_spec

DEMO = "coding"


def render(demo: CodingDemo) -> None:
    st.subheader("Demo 1 — Verified Coding（送金）")
    st.caption(f"ルール: {RULE_TEXT}")
    balance, amount = _inputs()
    if st.button("Lean で検証", key="coding_verify"):
        result = demo.verify_transfer(balance, amount)
        log_result(DEMO, result)
        st.session_state["coding_result"] = result
    if result := st.session_state.get("coding_result"):
        _render_business(result.details)
        render_lean_result(result)
    st.info("このデモは Lean 上のモデルについての保証です。実際の送金プログラムの検証ではありません。")
    render_spec("Coding.lean")
    render_logs(DEMO)


def _inputs() -> tuple[int, int]:
    c1, c2 = st.columns(2)
    balance = c1.number_input("残高 balance", value=100, step=10, key="coding_balance")
    amount = c2.number_input("送金額 amount", value=80, step=10, key="coding_amount")
    return int(balance), int(amount)


def _render_business(details: dict) -> None:
    if not details:
        return
    if details["allowed"]:
        st.write(f"**業務判定（Python）**: 送金許可 → 送金後残高 {details['new_balance']}")
    else:
        st.write("**業務判定（Python）**: 送金拒否（ルール違反）")
