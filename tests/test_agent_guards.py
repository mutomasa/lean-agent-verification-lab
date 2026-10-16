import pytest

from src.agent.guards import explanation_consistent, ungrounded_numbers
from src.agent.orchestrator import Agent
from src.agent.tools import AgentContext, ToolRegistry
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo
from src.demos.security import SecurityDemo
from src.verification.results import Status
from tests.fakes import FakeVerifier, ScriptedClient


def test_grounded_numbers_ok():
    assert ungrounded_numbers("verify_transfer", "残高100円から120円", {"balance": 100, "amount": 120}) == []


def test_detects_misextracted_amount():
    assert ungrounded_numbers("verify_transfer", "残高100円から120円", {"balance": 100, "amount": 20}) == [20]


def test_fullwidth_and_commas():
    assert ungrounded_numbers("verify_transfer", "残高１，０００円から5,000円",
                              {"balance": 1000, "amount": 5000}) == []


def test_rbac_not_checked():
    assert ungrounded_numbers("verify_rbac", "x", {"changes": []}) == []


@pytest.mark.parametrize("status,text,ok", [
    (Status.VIOLATION, "証明できなかった。", False),
    (Status.VIOLATION, "送金額が残高を超えるためルール違反です。", True),
    (Status.PASS, "送金は許可されていません。", False),
    (Status.PASS, "安全に送金できます。", True),
])
def test_explanation_consistency(status, text, ok):
    assert explanation_consistent(status, text) is ok


def _agent(client):
    v = FakeVerifier()
    return Agent(client, ToolRegistry(CodingDemo(v), SecurityDemo(v), OptimizationDemo(v)))


def test_agent_replaces_contradicting_explanation():
    out = '{"tool": "verify_transfer", "arguments": {"balance": 100, "amount": 120}}'
    run = _agent(ScriptedClient([out], explanation="証明できなかった。")).run(
        "残高100円から120円", AgentContext())
    assert run.explanation.startswith("[VIOLATION]")
    assert any("矛盾" in w for w in run.warnings)


def test_agent_warns_on_ungrounded_argument():
    out = '{"tool": "verify_transfer", "arguments": {"balance": 100, "amount": 20}}'
    run = _agent(ScriptedClient([out])).run("残高100円から120円", AgentContext())
    assert any("[20]" in w for w in run.warnings)
