"""Agent 用プロンプト。"""

from __future__ import annotations

import json

from src.agent.schemas import TOOL_SCHEMAS
from src.agent.tools import TOOL_DESCRIPTIONS, AgentContext

SYSTEM_PROPOSE = """あなたは形式検証デモのアシスタントです。
ユーザーの要求を読み、下記のツールから 1 つを選び、その引数を JSON で提案してください。
あなたは判定を行いません。判定は Lean 4 による検証ツールが行います。
出力は次の形式の JSON オブジェクトのみ: {{"tool": "<ツール名>", "arguments": {{...}}}}

# ツール
{tools}

# 現在の状態
{context}

# 例
要求: 残高100円から80円送金しても安全？
出力: {{"tool": "verify_transfer", "arguments": {{"balance": 100, "amount": 80}}}}
要求: Viewer に書き込み権限を付けたら問題ある？
出力: {{"tool": "verify_rbac", "arguments": {{"changes": [{{"role": "viewer", "action": "write", "allowed": true}}]}}}}
要求: 現在の権限設定は安全？
出力: {{"tool": "verify_rbac", "arguments": {{"changes": []}}}}
要求: 案件Aの必要時間を80時間にして配置して
出力: {{"tool": "optimize_staffing", "arguments": {{"demand_changes": [{{"project": "案件A", "demand": 80}}], "capacity_changes": []}}}}
要求: 鈴木さんの稼働上限を30時間にして配置して
出力: {{"tool": "optimize_staffing", "arguments": {{"demand_changes": [], "capacity_changes": [{{"employee": "鈴木", "capacity": 30}}]}}}}
"""

SYSTEM_TOOLS = """あなたは形式検証デモのアシスタントです。
ユーザーの要求に合う検証ツールを必ず 1 つ呼び出してください。判定はツール（Lean 4）が行います。
送金 → verify_transfer、権限・ロール → verify_rbac、人員配置・案件・工数 → optimize_staffing、
配置行列の確認 → verify_staffing。どれにも当てはまらない場合のみ none。

# 現在の状態
{context}

# 例
- 「Viewer に書き込み権限を付けたら問題ある？」→ verify_rbac(changes=[{{"role": "viewer", "action": "write", "allowed": true}}])
- 「案件Aの必要時間を80時間にして配置して」→ optimize_staffing(demand_changes=[{{"project": "案件A", "demand": 80}}], capacity_changes=[])
"""

STATUS_MEANING = {
    "PASS": "入力は仕様を満たす（Lean が証明した）",
    "VIOLATION": "入力は業務ルールに違反している（Lean が違反を証明した）",
    "PROOF_FAILED": "Lean で証明できなかった（違反が見つかったという意味ではない）",
    "ERROR": "入力または実行環境のエラー",
    "TIMEOUT": "Lean の実行が時間切れ",
    "INFEASIBLE": "最適化問題に実行可能解がない",
}

SYSTEM_EXPLAIN = """あなたは形式検証の結果を日本語で簡潔に説明するアシスタントです。
与えられた検証結果 JSON の status と status_meaning に従って説明し、判定を変更・否定してはいけません。
PROOF_FAILED は「違反が見つかった」ではなく「証明できなかった」という意味です。
3 文以内で説明してください。"""


def tool_catalog(tool_names: list[str]) -> str:
    return "\n".join(
        f"- {n}: {TOOL_DESCRIPTIONS[n]}\n  引数スキーマ: {json.dumps(TOOL_SCHEMAS[n], ensure_ascii=False)}"
        for n in tool_names)


def describe_context(ctx: AgentContext) -> str:
    p = ctx.problem
    granted = [f"{r}:{a}" for (r, a), v in ctx.policy.items() if v]
    return (f"- RBAC で許可中: {', '.join(granted)}\n"
            f"- 社員: {', '.join(f'{e}(上限{c}h)' for e, c in zip(p.employees, p.capacity))}\n"
            f"- 案件: {', '.join(f'{n}(需要{d}h)' for n, d in zip(p.projects, p.demand))}")


def propose_messages(user_text: str, tool_names: list[str], ctx: AgentContext) -> list[dict]:
    system = SYSTEM_PROPOSE.format(tools=tool_catalog(tool_names), context=describe_context(ctx))
    return [{"role": "system", "content": system}, {"role": "user", "content": user_text}]


def tools_messages(user_text: str, ctx: AgentContext) -> list[dict]:
    system = SYSTEM_TOOLS.format(context=describe_context(ctx))
    return [{"role": "system", "content": system}, {"role": "user", "content": user_text}]


def openai_tools(tool_names: list[str]) -> list[dict]:
    return [{"type": "function", "function": {
        "name": n, "description": TOOL_DESCRIPTIONS[n], "parameters": TOOL_SCHEMAS[n]}}
        for n in tool_names]


def explain_messages(user_text: str, tool: str, status: str, summary: str,
                     details: dict) -> list[dict]:
    payload = {"request": user_text, "tool": tool, "status": status,
               "status_meaning": STATUS_MEANING.get(status, ""), "summary": summary,
               "details": to_jsonable(details)}
    return [{"role": "system", "content": SYSTEM_EXPLAIN},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}]


def to_jsonable(value):
    """タプルキーの dict などを JSON 化できる形に変換する。"""
    if isinstance(value, dict):
        return {_key(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)


def _key(key) -> str:
    return ":".join(map(str, key)) if isinstance(key, tuple) else str(key)
