"""実機の vLLM で Agent を 1 回ずつ試すスクリプト。"""

import sys

from config.settings import load_settings
from src.agent.client import VLLMClient
from src.agent.orchestrator import Agent
from src.agent.tools import AgentContext, ToolRegistry
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo
from src.demos.security import SecurityDemo
from src.verification.verifier import default_verifier


def main() -> None:
    llm = load_settings().llm
    v = default_verifier()
    registry = ToolRegistry(CodingDemo(v), SecurityDemo(v), OptimizationDemo(v))
    mode = sys.argv[1] if len(sys.argv) > 1 else llm.tool_mode
    agent = Agent(VLLMClient(llm), registry, llm.max_retries, mode, llm.guided_json)
    for text in sys.argv[2:]:
        run = agent.run(text, AgentContext())
        tool = run.proposal.tool if run.proposal else None
        status = run.outcome.result.status.value if run.outcome else None
        print(f"[{mode}] {text}\n  tool={tool} args={run.proposal.arguments if run.proposal else None}"
              f" attempts={run.attempts} {run.propose_ms}ms status={status} error={run.error}\n"
              f"  説明: {run.explanation}\n  警告: {run.warnings}")


if __name__ == "__main__":
    main()
