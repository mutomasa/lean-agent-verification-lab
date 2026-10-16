"""評価スクリプト: Lean 全サンプル検証 + Agent ツール選択成功率 + 応答時間 + VRAM。

uv run python -m scripts.evaluate [--modes json tools] [--skip-agent]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime
from pathlib import Path

from config.settings import PROJECT_ROOT, load_settings
from src.agent.client import VLLMClient
from src.agent.orchestrator import Agent
from src.agent.tools import AgentContext, ToolRegistry
from src.demos.coding import CodingDemo
from src.demos.optimization import OptimizationDemo
from src.demos.security import SecurityDemo
from src.evaluation.cases import AGENT_CASES, lean_cases
from src.evaluation.metrics import gpu_memory_used_mib, rate, timing
from src.verification.verifier import default_verifier


def evaluate_lean(demos: tuple) -> dict:
    rows = []
    for case in lean_cases(*demos):
        r = case.run()
        rows.append({"case": case.name, "expected": case.expected.value,
                     "actual": r.status.value, "ok": r.status == case.expected,
                     "elapsed_ms": r.elapsed_ms})
    lean_ms = [row["elapsed_ms"] for row in rows if row["elapsed_ms"]]
    return {"cases": rows, "accuracy": rate(sum(r["ok"] for r in rows), len(rows)),
            "lean_timing": _asdict(timing(lean_ms))}


def evaluate_agent(agent: Agent) -> dict:
    rows = [_agent_row(agent, case) for case in AGENT_CASES]
    n = len(rows)
    return {
        "mode": agent.mode, "cases": rows,
        "tool_selection_rate": rate(sum(r["tool_ok"] for r in rows), n),
        "end_to_end_rate": rate(sum(r["status_ok"] for r in rows), n),
        "first_try_rate": rate(sum(r["attempts"] == 1 and r["tool_ok"] for r in rows), n),
        "warning_rate": rate(sum(bool(r["warnings"]) for r in rows), n),
        "propose_timing": _asdict(timing([r["propose_ms"] for r in rows])),
    }


def _agent_row(agent: Agent, case) -> dict:
    run = agent.run(case.request, AgentContext())
    tool = run.proposal.tool if run.proposal else None
    status = run.outcome.result.status.value if run.outcome else None
    return {"request": case.request, "expected_tool": case.tool, "tool": tool,
            "arguments": run.proposal.arguments if run.proposal else None,
            "expected_status": case.expected.value, "status": status,
            "tool_ok": tool == case.tool, "status_ok": status == case.expected.value,
            "attempts": run.attempts, "propose_ms": run.propose_ms,
            "warnings": run.warnings, "error": run.error}


def _asdict(value):
    return dataclasses.asdict(value) if value is not None else None


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    settings = load_settings()
    v = default_verifier()
    demos = (CodingDemo(v), SecurityDemo(v), OptimizationDemo(v))
    report = {"timestamp": datetime.now().isoformat(timespec="seconds"),
              "model": settings.llm.model, "lean": evaluate_lean(demos),
              "gpu_memory_used_mib": gpu_memory_used_mib(), "agent": []}
    if not args.skip_agent:
        report["agent"] = _evaluate_modes(settings, demos, args.modes)
    path = _save(report)
    print(render_summary(report))
    print(f"\n保存先: {path}")
    return 0 if report["lean"]["accuracy"] == 1.0 else 1


def _evaluate_modes(settings, demos, modes: list[str]) -> list[dict]:
    client = VLLMClient(settings.llm)
    if not client.is_available():
        print("vLLM に接続できないため Agent 評価をスキップします", file=sys.stderr)
        return []
    registry = ToolRegistry(*demos)
    return [evaluate_agent(Agent(client, registry, settings.llm.max_retries, mode,
                                 settings.llm.guided_json)) for mode in modes]


def _parse(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--modes", nargs="+", default=["json", "tools"], choices=["json", "tools"])
    p.add_argument("--skip-agent", action="store_true")
    return p.parse_args(argv)


def _save(report: dict) -> Path:
    out = PROJECT_ROOT / "results"
    out.mkdir(exist_ok=True)
    path = out / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def render_summary(report: dict) -> str:
    lean = report["lean"]
    lines = [f"# 評価結果 {report['timestamp']}", "",
             f"- Lean サンプル判定一致率: {lean['accuracy']:.0%} ({len(lean['cases'])} 件)",
             f"- Lean 実行時間: {_fmt_timing(lean['lean_timing'])}",
             f"- GPU メモリ使用量: {report['gpu_memory_used_mib']} MiB"]
    for a in report["agent"]:
        lines += [f"- Agent[{a['mode']}] ツール選択 {a['tool_selection_rate']:.0%} / "
                  f"判定まで一致 {a['end_to_end_rate']:.0%} / 1回目成功 {a['first_try_rate']:.0%} / "
                  f"警告 {a['warning_rate']:.0%} / 提案時間 {_fmt_timing(a['propose_timing'])}"]
    return "\n".join(lines)


def _fmt_timing(t: dict | None) -> str:
    return "-" if not t else f"平均 {t['mean_ms']:.0f}ms / 中央 {t['p50_ms']:.0f}ms / 最大 {t['max_ms']:.0f}ms"


if __name__ == "__main__":
    sys.exit(main())
