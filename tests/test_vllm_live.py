"""起動中の vLLM を使う実機テスト。`uv run pytest -m vllm` で実行する。"""

import pytest

from config.settings import load_settings
from src.agent.client import VLLMClient
from src.agent.orchestrator import Agent
from src.agent.tools import AgentContext, ToolRegistry
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo
from src.demos.security import SecurityDemo
from src.verification.results import Status

pytestmark = [pytest.mark.vllm, pytest.mark.lean]


@pytest.fixture(scope="module")
def live_agent(verifier):
    client = VLLMClient(load_settings().llm)
    if not client.is_available():
        pytest.skip("vLLM が起動していません")
    registry = ToolRegistry(CodingDemo(verifier), SecurityDemo(verifier), OptimizationDemo(verifier))
    return Agent(client, registry, max_retries=2, mode="json")


@pytest.mark.parametrize("request_text,tool,status", [
    ("残高100円から120円送金しても大丈夫？", "verify_transfer", Status.VIOLATION),
    ("残高5000円で3000円を送金したい。安全か検証して", "verify_transfer", Status.PASS),
    ("Viewer に書き込み権限を付けたら問題ある？", "verify_rbac", Status.VIOLATION),
    ("案件Cの必要時間を90時間にして人員配置を最適化して", "optimize_staffing", Status.PASS),
])
def test_live_agent(live_agent, request_text, tool, status):
    run = live_agent.run(request_text, AgentContext())
    assert run.ok, run.error
    assert run.proposal.tool == tool
    assert run.outcome.result.status == status
