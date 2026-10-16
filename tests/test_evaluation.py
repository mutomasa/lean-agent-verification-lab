import pytest

from scripts.evaluate import evaluate_agent, evaluate_lean, render_summary
from src.agent.orchestrator import Agent
from src.agent.tools import ToolRegistry
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo
from src.demos.security import SecurityDemo
from src.evaluation.cases import AGENT_CASES
from src.evaluation.metrics import rate, timing
from tests.fakes import DownClient, FakeVerifier


def test_timing_and_rate():
    t = timing([10, 20, 30])
    assert t.mean_ms == 20 and t.p50_ms == 20 and t.max_ms == 30
    assert timing([]) is None
    assert rate(1, 4) == 0.25 and rate(0, 0) == 0.0


@pytest.mark.lean
def test_all_lean_samples_match_expected(verifier):
    demos = (CodingDemo(verifier), SecurityDemo(verifier), OptimizationDemo(verifier))
    result = evaluate_lean(demos)
    assert result["accuracy"] == 1.0, [c for c in result["cases"] if not c["ok"]]


def test_agent_eval_with_vllm_down_counts_failures():
    v = FakeVerifier()
    agent = Agent(DownClient(), ToolRegistry(CodingDemo(v), SecurityDemo(v), OptimizationDemo(v)))
    result = evaluate_agent(agent)
    assert result["tool_selection_rate"] == 0.0
    assert all(r["error"] for r in result["cases"])
    assert len(result["cases"]) == len(AGENT_CASES)
    summary = render_summary({"timestamp": "t", "lean": {"accuracy": 1.0, "cases": [],
                              "lean_timing": None}, "gpu_memory_used_mib": None,
                              "agent": [result]})
    assert "Agent[json]" in summary
