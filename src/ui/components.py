"""Streamlit 共通部品。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from config.settings import load_settings
from src.verification.results import Status, VerificationResult

STATUS_STYLE = {
    Status.PASS: ("success", "✅"),
    Status.VIOLATION: ("error", "🚫"),
    Status.PROOF_FAILED: ("warning", "⚠️"),
    Status.ERROR: ("error", "💥"),
    Status.TIMEOUT: ("warning", "⏱️"),
    Status.INFEASIBLE: ("info", "∅"),
}


def render_lean_result(result: VerificationResult) -> None:
    kind, icon = STATUS_STYLE[result.status]
    getattr(st, kind)(f"{icon} **Lean 検証: {result.status.value}** — {result.summary}")
    cols = st.columns(2)
    cols[0].metric("Lean 実行時間", f"{result.elapsed_ms} ms")
    cols[1].metric("終了コード", "-" if result.exit_code is None else result.exit_code)
    _render_lean_output(result)


def _render_lean_output(result: VerificationResult) -> None:
    if result.lean_source:
        with st.expander("生成された Lean 検証ソース（読み取り専用）"):
            st.code(result.lean_source, language="lean")
    if result.lean_stdout or result.lean_stderr:
        with st.expander("Lean 出力"):
            st.code(result.lean_stdout + result.lean_stderr, language="text")


def render_spec(lean_file: str) -> None:
    path = load_settings().lean.project_dir / "Demo" / lean_file
    with st.expander(f"レビュー済み Lean 仕様: Demo/{lean_file}（読み取り専用）"):
        st.code(Path(path).read_text(encoding="utf-8"), language="lean")


def log(demo: str, message: str) -> None:
    logs = st.session_state.setdefault("logs", [])
    logs.append(f"{datetime.now():%H:%M:%S} [{demo}] {message}")


def log_result(demo: str, result: VerificationResult) -> None:
    log(demo, f"{result.status.value}: {result.summary} ({result.elapsed_ms} ms)")


def render_logs(demo: str) -> None:
    with st.expander("実行ログ"):
        entries = [e for e in st.session_state.get("logs", []) if f"[{demo}]" in e]
        st.code("\n".join(entries) or "(ログなし)", language="text")
