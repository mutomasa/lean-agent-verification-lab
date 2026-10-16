"""Agent の状態遷移: 提案 → スキーマ検証（失敗時は再試行）→ ツール実行 → 説明。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from src.agent.guards import explanation_consistent, ungrounded_numbers
from src.agent.client import ChatClient, LLMUnavailableError
from src.agent.prompts import explain_messages, openai_tools, propose_messages, tools_messages
from src.agent.schemas import (
    ProposalError,
    ToolProposal,
    parse_json_text,
    proposal_schema,
    validate_proposal,
)
from src.agent.tools import AgentContext, ToolOutcome, ToolRegistry

Mode = Literal["json", "tools"]


@dataclass
class AgentRun:
    request: str
    proposal: ToolProposal | None = None
    outcome: ToolOutcome | None = None
    explanation: str = ""
    error: str | None = None
    attempts: int = 0
    log: list[str] = field(default_factory=list)
    propose_ms: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None and self.outcome is not None


class Agent:
    def __init__(self, client: ChatClient, registry: ToolRegistry, max_retries: int = 2,
                 mode: Mode = "json", guided: bool = True) -> None:
        self.client = client
        self.registry = registry
        self.max_retries = max_retries
        self.mode = mode
        self.guided = guided

    def run(self, request: str, context: AgentContext,
            allowed_tools: list[str] | None = None) -> AgentRun:
        tools = allowed_tools or self.registry.names
        run = AgentRun(request)
        try:
            run.proposal = self._propose_with_retry(request, tools, context, run)
        except LLMUnavailableError as exc:
            run.error = str(exc)
            return run
        if run.proposal is None:
            run.error = f"{run.attempts} 回試行しても有効なツール呼び出しを得られませんでした"
            return run
        return self._execute(run, context)

    def _propose_with_retry(self, request: str, tools: list[str], ctx: AgentContext,
                            run: AgentRun) -> ToolProposal | None:
        messages = (tools_messages(request, ctx) if self.mode == "tools"
                    else propose_messages(request, tools, ctx))
        start = time.monotonic()
        for _ in range(self.max_retries + 1):
            run.attempts += 1
            try:
                return self._propose_once(messages, tools, run)
            except ProposalError as exc:
                run.log.append(f"試行{run.attempts}: スキーマ検証失敗: {exc}")
                messages = [*messages, {"role": "user", "content": f"出力が不正です: {exc}。修正した JSON のみを出力してください。"}]
            finally:
                run.propose_ms = int((time.monotonic() - start) * 1000)
        return None

    def _propose_once(self, messages: list[dict], tools: list[str], run: AgentRun) -> ToolProposal:
        if self.mode == "tools":
            call = self.client.complete_with_tools(messages, openai_tools(tools))
            if call is None:
                raise ProposalError("ツール呼び出しがありません")
            data = {"tool": call.name, "arguments": call.arguments}
        else:
            schema = proposal_schema(tools) if self.guided else None
            text = self.client.complete(messages, json_schema=schema)
            run.log.append(f"試行{run.attempts}: LLM 出力: {text[:300]}")
            data = parse_json_text(text)
        proposal = validate_proposal(data, tools)
        run.log.append(f"試行{run.attempts}: 提案 {proposal.tool} {proposal.arguments}")
        return proposal

    def _execute(self, run: AgentRun, context: AgentContext) -> AgentRun:
        assert run.proposal is not None
        self._check_grounding(run)
        try:
            run.outcome = self.registry.execute(run.proposal.tool, run.proposal.arguments, context)
        except (KeyError, ValueError) as exc:
            run.error = f"ツール実行エラー: {exc}"
            return run
        run.log.append(f"検証結果: {run.outcome.result.status.value}")
        run.explanation = self._explain(run)
        return run

    @staticmethod
    def _check_grounding(run: AgentRun) -> None:
        assert run.proposal is not None
        missing = ungrounded_numbers(run.proposal.tool, run.request, run.proposal.arguments)
        if missing:
            run.warnings.append(f"引数の数値 {missing} は要求文に含まれていません。"
                                "LLM の抽出誤りの可能性があるため、引数を確認してください")

    def _explain(self, run: AgentRun) -> str:
        assert run.outcome is not None
        r = run.outcome.result
        fallback = f"[{r.status.value}] {r.summary}"
        try:
            text = self.client.complete(explain_messages(
                run.request, run.outcome.tool, r.status.value, r.summary, r.details),
                max_tokens=300).strip()
        except Exception as exc:  # noqa: BLE001 - 説明は任意。判定には影響しない
            run.log.append(f"説明生成に失敗: {exc}")
            return fallback
        if not explanation_consistent(r.status, text):
            run.warnings.append(f"LLM の説明が判定 {r.status.value} と矛盾したため定型文に置換しました: {text}")
            return fallback
        return text
