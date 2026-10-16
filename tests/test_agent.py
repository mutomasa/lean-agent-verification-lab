import pytest

from src.agent.client import ToolCall
from src.agent.orchestrator import Agent
from src.agent.schemas import ProposalError, parse_json_text, proposal_schema, validate_proposal
from src.agent.tools import AgentContext, ToolRegistry, apply_problem_changes
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo, sample_problem
from src.demos.security import SecurityDemo
from src.verification.results import Status
from tests.fakes import DownClient, FakeVerifier, ScriptedClient

TRANSFER = '{"tool": "verify_transfer", "arguments": {"balance": 100, "amount": 120}}'


@pytest.fixture
def registry():
    v = FakeVerifier()
    return ToolRegistry(CodingDemo(v), SecurityDemo(v), OptimizationDemo(v))


def agent(client, registry, **kw):
    return Agent(client, registry, max_retries=2, **kw)


class TestSchemas:
    def test_parse_json_with_think_and_fence(self):
        text = "<think>考え中</think>\n```json\n" + TRANSFER + "\n```"
        assert parse_json_text(text)["tool"] == "verify_transfer"

    def test_parse_json_failure(self):
        with pytest.raises(ProposalError):
            parse_json_text("わかりません")

    @pytest.mark.parametrize("data", [
        {"tool": "rm_rf", "arguments": {}},
        {"tool": "verify_transfer", "arguments": {"balance": "100", "amount": 1}},
        {"tool": "verify_transfer", "arguments": {"balance": 1, "amount": 1, "cmd": "x"}},
        {"tool": "verify_rbac", "arguments": {"changes": [{"role": "root", "action": "read", "allowed": True}]}},
        {"tool": "verify_transfer"},
        ["not", "an", "object"],
    ])
    def test_rejects_invalid(self, data):
        with pytest.raises(ProposalError):
            validate_proposal(data, ["verify_transfer", "verify_rbac"])

    def test_tool_not_in_allowlist(self):
        with pytest.raises(ProposalError):
            validate_proposal({"tool": "verify_rbac", "arguments": {"changes": []}},
                              ["verify_transfer"])

    def test_proposal_schema_lists_tools(self):
        schema = proposal_schema(["verify_transfer", "none"])
        assert [s["properties"]["tool"]["const"] for s in schema["anyOf"]] == ["verify_transfer", "none"]


class TestAgent:
    def test_happy_path(self, registry):
        run = agent(ScriptedClient([TRANSFER]), registry).run("送金", AgentContext())
        assert run.ok and run.attempts == 1
        assert run.outcome.result.status == Status.VIOLATION
        assert run.explanation == "説明です"

    def test_retry_after_invalid_output(self, registry):
        client = ScriptedClient(["ごめんなさい", TRANSFER])
        run = agent(client, registry).run("送金", AgentContext())
        assert run.ok and run.attempts == 2
        assert "出力が不正です" in client.calls[1][-1]["content"]

    def test_gives_up_after_retries(self, registry):
        run = agent(ScriptedClient(["x", "y", "z"]), registry).run("送金", AgentContext())
        assert not run.ok and run.attempts == 3 and "有効なツール呼び出し" in run.error

    def test_vllm_down_is_reported(self, registry):
        run = agent(DownClient(), registry).run("送金", AgentContext())
        assert not run.ok and "down" in run.error

    def test_explanation_cannot_change_status(self, registry):
        client = ScriptedClient([TRANSFER], explanation="PASS です！安全です")
        run = agent(client, registry).run("送金", AgentContext())
        assert run.outcome.result.status == Status.VIOLATION

    def test_allowed_tools_restriction(self, registry):
        rbac = '{"tool": "verify_rbac", "arguments": {"changes": []}}'
        run = agent(ScriptedClient([rbac, rbac, rbac]), registry).run(
            "x", AgentContext(), allowed_tools=["verify_transfer"])
        assert not run.ok

    def test_rbac_changes_applied_to_context_policy(self, registry):
        out = ('{"tool": "verify_rbac", "arguments": {"changes": '
               '[{"role": "viewer", "action": "delete", "allowed": true}]}}')
        run = agent(ScriptedClient([out]), registry).run("x", AgentContext())
        assert run.outcome.result.details["violations"] == [("viewer", "delete")]

    def test_unknown_project_is_tool_error(self, registry):
        out = ('{"tool": "optimize_staffing", "arguments": {"demand_changes": '
               '[{"project": "案件Z", "demand": 1}], "capacity_changes": []}}')
        run = agent(ScriptedClient([out]), registry).run("x", AgentContext())
        assert not run.ok and "案件Z" in run.error

    def test_tools_mode(self, registry):
        client = ScriptedClient([], tool_calls=[ToolCall("verify_transfer", {"balance": 5, "amount": 5})])
        run = agent(client, registry, mode="tools").run("x", AgentContext())
        assert run.ok and run.outcome.result.status == Status.PASS


def test_apply_problem_changes():
    p = apply_problem_changes(sample_problem(), [{"project": "案件A", "demand": 80}],
                              [{"employee": "佐藤", "capacity": 20}])
    assert p.demand[0] == 80 and p.capacity[0] == 20


def test_explain_payload_handles_tuple_keys():
    import json

    from src.agent.prompts import explain_messages
    msgs = explain_messages("q", "verify_rbac", "PASS", "s",
                            {"policy": {("viewer", "write"): True}, "violations": [("a", "b")]})
    payload = json.loads(msgs[1]["content"])
    assert payload["details"]["policy"] == {"viewer:write": True}
