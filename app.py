"""Lean Agent Verification Lab — Streamlit エントリポイント。"""

from __future__ import annotations

import streamlit as st

from config.settings import load_settings
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo
from src.demos.security import SecurityDemo
from src.agent.client import VLLMClient
from src.agent.orchestrator import Agent
from src.agent.tools import ToolRegistry
from src.ui import agent_tab, coding_tab, optimization_tab, security_tab
from src.verification.lean_runner import LeanRunner
from src.verification.verifier import LeanVerifier


@st.cache_resource
def build_services() -> dict:
    settings = load_settings()
    lean, llm = settings.lean, settings.llm
    runner = LeanRunner(lean.project_dir, lean.work_dir, lean.timeout_sec)
    build = runner.build()
    verifier = LeanVerifier(runner)
    coding, security = CodingDemo(verifier), SecurityDemo(verifier)
    optimization = OptimizationDemo(verifier)
    registry = ToolRegistry(coding, security, optimization)
    agent = Agent(VLLMClient(llm), registry, llm.max_retries, llm.tool_mode, llm.guided_json)
    return {
        "build_ok": build.exit_code == 0,
        "build_log": build.stdout + build.stderr,
        "coding": coding,
        "security": security,
        "optimization": optimization,
        "agent": agent,
    }


@st.cache_data(ttl=10, show_spinner=False)
def vllm_available() -> bool:
    return build_services()["agent"].client.is_available()


def main() -> None:
    st.set_page_config(page_title="Lean Agent Verification Lab", layout="wide")
    st.title("Lean Agent Verification Lab")
    services = build_services()
    if not services["build_ok"]:
        st.error("Lean ライブラリのビルドに失敗しました")
        st.code(services["build_log"])
    tabs = st.tabs(["1. Verified Coding", "2. RBAC Security", "3. Verified Optimization",
                    "4. AI Agent"])
    with tabs[0]:
        coding_tab.render(services["coding"])
    with tabs[1]:
        security_tab.render(services["security"])
    with tabs[2]:
        optimization_tab.render(services["optimization"])
    with tabs[3]:
        agent_tab.render(services["agent"], vllm_available())


main()
